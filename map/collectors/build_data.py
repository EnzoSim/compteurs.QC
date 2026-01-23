#!/usr/bin/env python3
"""
Pipeline unifié de construction des données AquaMap QC.

Ce script:
1. Collecte les données depuis les sources (MAMH, StatCan)
2. Standardise les identifiants (CSD UID)
3. Calcule et normalise les indicateurs
4. Exécute les contrôles qualité
5. Génère les fichiers de sortie

Usage:
    python -m collectors.build_data
    python -m collectors.build_data --year 2023
    python -m collectors.build_data --skip-qa
"""

import argparse
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .config import config
from .mamh_collector import MAMHCollector
from .bil_collector import BILCollector
from .statcan_csd_collector import StatCanCSDCollector
from .data_merger import DataMerger
from .qa_validator import QAValidator

logger = logging.getLogger(__name__)


class DataPipeline:
    """Pipeline unifié de construction des données."""

    def __init__(self, year: Optional[int] = None, bil_path: Optional[str] = None):
        """
        Initialise le pipeline.

        Args:
            year: Année des données (optionnel, utilise la plus récente par défaut)
            bil_path: Chemin vers le fichier BIL Excel (optionnel)
        """
        self.year = year or 2023
        self.bil_path = bil_path
        self.bil_collector = BILCollector(filepath=Path(bil_path) if bil_path else None)
        self.mamh_collector = MAMHCollector()
        self.statcan_collector = StatCanCSDCollector()
        self.merger = DataMerger()
        self.qa_validator = QAValidator()

        self.results = {
            "statcan_csd": {"success": False, "error": None, "count": 0},
            "bil": {"success": False, "error": None, "count": 0},
            "merge": {"success": False, "error": None, "total_features": 0},
        }

    def collect_statcan(self) -> Optional[dict]:
        """Collecte les données géographiques StatCan."""
        logger.info("Collecting StatCan CSD data...")
        try:
            geojson = self.statcan_collector.collect_all()
            if geojson and geojson.get("features"):
                self.results["statcan_csd"]["success"] = True
                self.results["statcan_csd"]["count"] = len(geojson["features"])
                logger.info(f"Collected {len(geojson['features'])} CSD features")
                return geojson
            else:
                self.results["statcan_csd"]["error"] = "No features returned"
        except Exception as e:
            logger.error(f"StatCan collection failed: {e}")
            self.results["statcan_csd"]["error"] = str(e)
        return None

    def collect_bil(self) -> Optional[Dict[str, Any]]:
        """Collecte les données BIL (Bilan infrastructures eau)."""
        logger.info("Collecting BIL data...")
        try:
            bil_data = self.bil_collector.collect_all()
            if bil_data:
                self.results["bil"]["success"] = True
                self.results["bil"]["count"] = len(bil_data)
                logger.info(f"Collected BIL data for {len(bil_data)} municipalities")
                return bil_data
        except Exception as e:
            logger.error(f"BIL collection failed: {e}")
            self.results["bil"]["error"] = str(e)
        return None

    def collect_mamh(self) -> Optional[Dict[str, Any]]:
        """Collecte les données MAMH LPCD (fallback)."""
        logger.info("Collecting MAMH LPCD data...")
        try:
            mamh_data = self.mamh_collector.collect_all(year=self.year)
            if mamh_data:
                logger.info(f"Collected MAMH data for {len(mamh_data)} municipalities")
                return mamh_data
        except Exception as e:
            logger.error(f"MAMH collection failed: {e}")
        return None

    def merge_data(self, geojson: dict, mamh_data: Dict[str, Any]) -> dict:
        """Fusionne les données géographiques et LPCD."""
        logger.info("Merging data...")
        try:
            merged = self.merger.merge(geojson=geojson, lpcd_data=mamh_data)
            self.results["merge"]["success"] = True
            self.results["merge"]["total_features"] = len(merged.get("features", []))

            # Count matches
            lpcd_count = sum(
                1 for f in merged.get("features", [])
                if f.get("properties", {}).get("lpcd") is not None
            )
            self.results["merge"]["lpcd_matched"] = lpcd_count

            logger.info(f"Merged data: {self.results['merge']['total_features']} features, {lpcd_count} with LPCD")
            return merged
        except Exception as e:
            logger.error(f"Merge failed: {e}")
            self.results["merge"]["error"] = str(e)
            return geojson

    def run_qa(self, geojson: dict, mamh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute les contrôles qualité."""
        logger.info("Running QA validation...")
        qa_results = self.qa_validator.validate(geojson, mamh_data)
        return qa_results

    def generate_stats(self, geojson: dict) -> Dict[str, Any]:
        """Génère le fichier municipalities-stats.json."""
        stats = {}
        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            csd_uid = props.get("csd_uid") or props.get("CSDUID")
            if not csd_uid:
                continue

            stats[csd_uid] = {
                "csd_uid": csd_uid,
                "name": props.get("name") or props.get("CSDNAME"),
                "population": props.get("population"),
                "households": props.get("households"),
                "household_size": props.get("household_size"),
                "lpcd": props.get("lpcd"),
                "lpcd_status": props.get("lpcd_status", "missing" if props.get("lpcd") is None else "exact"),
                "lpcd_total": props.get("lpcd_total"),
                "consommation": props.get("consommation"),
                "population_desservie": props.get("population_desservie"),
                "nb_branchements": props.get("nb_branchements"),
                "pers_par_residence": props.get("pers_par_residence"),
                "nb_reseaux": props.get("nb_reseaux"),
                "indice_fuites": props.get("indice_fuites"),
                "longueur_reseau_km": props.get("longueur_reseau_km"),
                "lpcd_data_year": props.get("lpcd_data_year"),
            }
        return stats

    def generate_metadata(self, qa_results: Dict[str, Any]) -> Dict[str, Any]:
        """Génère le fichier metadata.json enrichi."""
        # Calculate coverage
        total = self.results["merge"].get("total_features", 0)
        lpcd_count = self.results["merge"].get("lpcd_matched", 0)
        lpcd_coverage = round((lpcd_count / total * 100), 1) if total > 0 else 0

        metadata = {
            "last_update": datetime.now().isoformat(),
            "version": f"{self.year}.1.0",
            "sources": {
                "bil": {
                    "name": "BIL - Bilan des infrastructures en eau",
                    "file": str(self.bil_collector.filepath),
                    "date": f"{self.year}",
                    "count": self.results["bil"]["count"],
                    "success": self.results["bil"]["success"],
                    "error": self.results["bil"]["error"],
                },
                "statcan": {
                    "url": "https://www12.statcan.gc.ca/",
                    "date": "2021",
                    "count": self.results["statcan_csd"]["count"],
                    "success": self.results["statcan_csd"]["success"],
                    "error": self.results["statcan_csd"]["error"],
                },
                "merge": self.results["merge"],
            },
            "coverage": {
                "lpcd": lpcd_coverage,
                "total_municipalities": total,
                "with_lpcd": lpcd_count,
            },
            "warnings": qa_results.get("warnings", []),
            "qa_summary": qa_results.get("summary", {}),
            "data_dictionary": {
                "lpcd": {
                    "unit": "L/pers/jour",
                    "definition": "Consommation résidentielle d'eau potable en litres par personne par jour",
                    "source": "MAMH SQEEP - champ consom_resid",
                },
                "consommation": {
                    "unit": "ML/an (stocké), m³/jour (affiché)",
                    "definition": "Volume total d'eau distribué par le réseau municipal",
                    "source": "MAMH SQEEP - champ vol_eau_dist",
                    "conversion": "m³/jour = ML/an × 1000 ÷ 365",
                },
                "population": {
                    "unit": "habitants",
                    "definition": "Population de la municipalité selon le recensement",
                    "source": "Statistique Canada, Recensement 2021",
                },
                "population_desservie": {
                    "unit": "habitants",
                    "definition": "Population desservie par le réseau d'eau potable",
                    "source": "MAMH SQEEP",
                },
            },
            "total_municipalities": total,
        }
        return metadata

    def save_outputs(
        self,
        geojson: dict,
        stats: Dict[str, Any],
        mamh_data: Dict[str, Any],
        metadata: Dict[str, Any],
    ):
        """Sauvegarde tous les fichiers de sortie."""
        logger.info("Saving output files...")

        # Save to current/
        current_dir = config.CURRENT_DIR
        current_dir.mkdir(parents=True, exist_ok=True)

        # GeoJSON
        geojson_path = current_dir / config.GEOJSON_FILE
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False)
        logger.info(f"Saved {geojson_path}")

        # Stats
        stats_path = current_dir / config.STATS_FILE
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {stats_path}")

        # BIL data (also save as mamh-data.json for compatibility)
        bil_path = current_dir / "bil-data.json"
        with open(bil_path, "w", encoding="utf-8") as f:
            json.dump(mamh_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {bil_path}")

        # Also save as mamh-data.json for map.js compatibility
        mamh_compat_path = current_dir / "mamh-data.json"
        with open(mamh_compat_path, "w", encoding="utf-8") as f:
            json.dump(mamh_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {mamh_compat_path}")

        # Metadata
        metadata_path = current_dir / config.METADATA_FILE
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {metadata_path}")

        # Save to history/YYYY/
        year = self.year or datetime.now().year
        history_dir = config.get_history_dir(year)
        for src_file in [geojson_path, stats_path]:
            dst_file = history_dir / src_file.name
            shutil.copy2(src_file, dst_file)
            logger.info(f"Archived to {dst_file}")

    def run(self, skip_qa: bool = False) -> Dict[str, Any]:
        """
        Exécute le pipeline complet.

        Args:
            skip_qa: Ignorer les contrôles qualité

        Returns:
            Résultats du pipeline
        """
        logger.info("=" * 60)
        logger.info("Starting AquaMap QC data pipeline")
        logger.info("=" * 60)

        # 1. Collect data
        geojson = self.collect_statcan()
        if not geojson:
            logger.error("Failed to collect StatCan data, aborting")
            return self.results

        # Try BIL first, then MAMH as fallback
        bil_data = self.collect_bil()
        if not bil_data:
            logger.warning("BIL collection failed, trying MAMH as fallback...")
            bil_data = self.collect_mamh()
        if not bil_data:
            logger.warning("No water data available, continuing with geographic data only")
            bil_data = {}

        # 2. Merge data
        merged_geojson = self.merge_data(geojson, bil_data)

        # 3. Run QA
        qa_results = {}
        if not skip_qa:
            qa_results = self.run_qa(merged_geojson, bil_data)
            if qa_results.get("errors"):
                logger.warning(f"QA found {len(qa_results['errors'])} errors")
            if qa_results.get("warnings"):
                logger.warning(f"QA found {len(qa_results['warnings'])} warnings")
        else:
            logger.info("Skipping QA validation")

        # 4. Generate outputs
        stats = self.generate_stats(merged_geojson)
        metadata = self.generate_metadata(qa_results)

        # 5. Save files
        self.save_outputs(merged_geojson, stats, bil_data, metadata)

        logger.info("=" * 60)
        logger.info("Pipeline completed successfully")
        logger.info(f"Total municipalities: {metadata['coverage']['total_municipalities']}")
        logger.info(f"LPCD coverage: {metadata['coverage']['lpcd']}%")
        logger.info("=" * 60)

        return {
            "success": True,
            "metadata": metadata,
            "qa_results": qa_results,
        }


def main():
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(
        description="Build AquaMap QC data files"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Year for MAMH data (default: latest available)",
    )
    parser.add_argument(
        "--skip-qa",
        action="store_true",
        help="Skip QA validation",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    pipeline = DataPipeline(year=args.year)
    results = pipeline.run(skip_qa=args.skip_qa)

    if not results.get("success"):
        exit(1)


if __name__ == "__main__":
    main()
