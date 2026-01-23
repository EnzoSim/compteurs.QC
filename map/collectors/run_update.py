"""
Point d'entrée pour la mise à jour des données (cron annuel).

Ce script orchestre le pipeline complet:
1. Archive les données actuelles dans l'historique
2. Collecte les nouvelles données de chaque source
3. Fusionne les données
4. Met à jour le cache et les métadonnées

Usage:
    python -m map.collectors.run_update
    python -m map.collectors.run_update --force  # Force la mise à jour
    python -m map.collectors.run_update --source overpass  # Une seule source
"""

import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

from .config import config
from .statcan_csd_collector import StatCanCSDCollector
from .data_merger import DataMerger
from .cache_manager import CacheManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def collect_statcan_csd(cache: CacheManager) -> Dict[str, Any]:
    """Collecte les limites officielles StatCan (CSD).

    Args:
        cache: Gestionnaire de cache

    Returns:
        Résultat de la collecte
    """
    result = {"success": False, "error": None, "count": 0}

    try:
        collector = StatCanCSDCollector()
        geojson = collector.collect_all()

        if geojson and len(geojson.get("features", [])) > 0:
            collector.save(geojson)
            cache.save_to_cache("geojson", geojson)
            result["success"] = True
            result["count"] = len(geojson["features"])
            logger.info(f"StatCan CSD: {result['count']} municipalities collected")
        else:
            raise ValueError("No features returned from StatCan CSD")

    except Exception as e:
        logger.error(f"StatCan CSD collection failed: {e}")
        result["error"] = str(e)

        # Fallback depuis le cache
        cached = cache.load_from_cache("geojson")
        if cached:
            filepath = config.CURRENT_DIR / config.GEOJSON_FILE
            with open(filepath, 'w', encoding='utf-8') as f:
                import json
                json.dump(cached, f, ensure_ascii=False)
            result["fallback"] = True
            result["count"] = len(cached.get("features", []))
            logger.warning(f"Using cached GeoJSON ({result['count']} features)")

    return result


def collect_overpass(cache: CacheManager) -> Dict[str, Any]:
    """Collecte les données GeoJSON via Overpass (fallback)."""
    result = {"success": False, "error": None, "count": 0}

    try:
        from .overpass_collector import OverpassCollector
        collector = OverpassCollector()
        geojson = collector.collect_all(by_bbox=True)

        if geojson and len(geojson.get("features", [])) > 0:
            collector.save(geojson)
            cache.save_to_cache("geojson", geojson)
            result["success"] = True
            result["count"] = len(geojson["features"])
            logger.info(f"Overpass: {result['count']} municipalities collected")
        else:
            raise ValueError("No features returned from Overpass")

    except Exception as e:
        logger.error(f"Overpass collection failed: {e}")
        result["error"] = str(e)

    return result


def collect_statcan(cache: CacheManager) -> Dict[str, Any]:
    """Collecte les données StatCan.

    Args:
        cache: Gestionnaire de cache

    Returns:
        Résultat de la collecte
    """
    result = {"success": False, "error": None, "count": 0}

    try:
        from .statcan_collector import StatCanCollector
        collector = StatCanCollector()
        data = collector.collect_all()

        if data:
            collector.save(data)
            cache.save_to_cache("statcan", data)
            result["success"] = True
            result["count"] = len(data)
            logger.info(f"StatCan: {result['count']} records collected")
        else:
            raise ValueError("No data returned from StatCan")

    except Exception as e:
        logger.error(f"StatCan collection failed: {e}")
        result["error"] = str(e)

        # Fallback depuis le cache
        cached = cache.load_from_cache("statcan")
        if cached:
            filepath = config.CURRENT_DIR / "statcan-data.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                import json
                json.dump(cached, f, ensure_ascii=False)
            result["fallback"] = True
            result["count"] = len(cached)
            logger.warning(f"Using cached StatCan data ({result['count']} records)")

    return result


def collect_mamh(cache: CacheManager) -> Dict[str, Any]:
    """Collecte les données MAMH (LPCD).

    Args:
        cache: Gestionnaire de cache

    Returns:
        Résultat de la collecte
    """
    result = {"success": False, "error": None, "count": 0}

    try:
        from .mamh_collector import MAMHCollector
        collector = MAMHCollector()
        data = collector.collect_all()

        if data:
            collector.save(data)
            cache.save_to_cache("mamh", data)
            result["success"] = True
            result["count"] = len(data)
            logger.info(f"MAMH: {result['count']} records collected")
        else:
            raise ValueError("No data returned from MAMH")

    except Exception as e:
        logger.error(f"MAMH collection failed: {e}")
        result["error"] = str(e)

        # Fallback depuis le cache
        cached = cache.load_from_cache("mamh")
        if cached:
            filepath = config.CURRENT_DIR / "mamh-data.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                import json
                json.dump(cached, f, ensure_ascii=False)
            result["fallback"] = True
            result["count"] = len(cached)
            logger.warning(f"Using cached MAMH data ({result['count']} records)")

    return result


def merge_data() -> Dict[str, Any]:
    """Fusionne toutes les données.

    Returns:
        Résultat de la fusion
    """
    result = {"success": False, "error": None}

    try:
        merger = DataMerger()
        merger.load_geojson()
        merger.load_statcan()
        merger.load_mamh()

        geojson = merger.merge()
        merger.save(geojson)

        result["success"] = True
        result["total_features"] = len(geojson.get("features", []))

        # Statistiques de fusion
        metadata = geojson.get("metadata", {})
        result["stats_matched"] = metadata.get("stats_matched", 0)
        result["lpcd_matched"] = metadata.get("lpcd_matched", 0)

        logger.info(
            f"Merge complete: {result['total_features']} features, "
            f"{result['stats_matched']} with stats, {result['lpcd_matched']} with LPCD"
        )

    except Exception as e:
        logger.error(f"Data merge failed: {e}")
        result["error"] = str(e)

    return result


def run_update(force: bool = False, sources: list = None):
    """Exécute le pipeline complet de mise à jour.

    Args:
        force: Force la mise à jour même si pas nécessaire
        sources: Liste des sources à mettre à jour (optionnel)
    """
    logger.info("=" * 60)
    logger.info("STARTING DATA UPDATE PIPELINE")
    logger.info(f"Date: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    cache = CacheManager()

    # Vérifier si mise à jour nécessaire
    if not force and not cache.needs_update():
        logger.info("Data is up to date, skipping update")
        return

    # Archiver les données actuelles
    logger.info("\n--- Archiving current data ---")
    try:
        archive_dir = cache.archive_to_history()
        logger.info(f"Archived to {archive_dir}")
    except Exception as e:
        logger.warning(f"Could not archive: {e}")

    # Résultats des collectes
    results = {}

    # Définir les sources à collecter
    all_sources = ["statcan_csd", "statcan", "mamh"]
    sources_to_collect = sources if sources else all_sources

    # Collecter les données
    if "statcan_csd" in sources_to_collect:
        logger.info("\n--- Collecting GeoJSON (StatCan CSD) ---")
        results["statcan_csd"] = collect_statcan_csd(cache)

    if "overpass" in sources_to_collect:
        logger.info("\n--- Collecting GeoJSON (Overpass fallback) ---")
        results["overpass"] = collect_overpass(cache)

    if "statcan" in sources_to_collect:
        logger.info("\n--- Collecting Statistics (StatCan) ---")
        results["statcan"] = collect_statcan(cache)

    if "mamh" in sources_to_collect:
        logger.info("\n--- Collecting LPCD (MAMH) ---")
        results["mamh"] = collect_mamh(cache)

    # Fusionner les données
    logger.info("\n--- Merging data ---")
    results["merge"] = merge_data()

    # Sauvegarder les métadonnées
    logger.info("\n--- Saving metadata ---")
    cache.save_metadata(results)

    # Résumé
    logger.info("\n" + "=" * 60)
    logger.info("UPDATE COMPLETE")
    logger.info("=" * 60)

    for source, result in results.items():
        status = "✓" if result.get("success") else "✗"
        fallback = " (fallback)" if result.get("fallback") else ""
        error = f" - {result.get('error')}" if result.get("error") else ""
        count = f" ({result.get('count', result.get('total_features', 0))} items)"
        logger.info(f"{status} {source}: {count}{fallback}{error}")

    # Warnings
    warnings = [src for src, res in results.items() if not res.get("success")]
    if warnings:
        logger.warning(f"\nWarnings: {', '.join(warnings)} had issues")

    return results


def main():
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(
        description="Update Quebec municipalities data"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force update even if data is fresh"
    )
    parser.add_argument(
        "--source", "-s",
        choices=["statcan_csd", "overpass", "statcan", "mamh"],
        action="append",
        help="Update only specific source(s)"
    )

    args = parser.parse_args()

    run_update(force=args.force, sources=args.source)


if __name__ == "__main__":
    main()
