"""
Fusion des données de différentes sources.

Combine les données GeoJSON (Overpass), statistiques (StatCan)
et consommation d'eau (MAMH) en un seul fichier GeoJSON enrichi.
"""

import json
import logging
import re
import unicodedata
from math import fabs
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

from .config import config

logger = logging.getLogger(__name__)


class DataMerger:
    """Fusionne les données de différentes sources."""

    def __init__(self):
        self.stats = {}
        self.lpcd_data = {}
        self.geojson = None
        self._stats_by_name = None
        self._mamh_by_name = None

    def load_geojson(self, filepath: Optional[Path] = None) -> Dict[str, Any]:
        """Charge le fichier GeoJSON.

        Args:
            filepath: Chemin du fichier (optionnel)

        Returns:
            GeoJSON FeatureCollection
        """
        if filepath is None:
            filepath = config.CURRENT_DIR / config.GEOJSON_FILE

        with open(filepath, 'r', encoding='utf-8') as f:
            self.geojson = json.load(f)

        logger.info(f"Loaded GeoJSON with {len(self.geojson.get('features', []))} features")
        return self.geojson

    def load_statcan(self, filepath: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
        """Charge les données StatCan.

        Args:
            filepath: Chemin du fichier (optionnel)

        Returns:
            Dict des statistiques par code géo
        """
        if filepath is None:
            filepath = config.CURRENT_DIR / "statcan-data.json"

        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                self.stats = json.load(f)
            logger.info(f"Loaded StatCan data for {len(self.stats)} municipalities")
        else:
            logger.warning("StatCan data file not found")
            self.stats = {}

        return self.stats

    def load_mamh(self, filepath: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
        """Charge les données MAMH.

        Args:
            filepath: Chemin du fichier (optionnel)

        Returns:
            Dict des données LPCD par code municipal
        """
        if filepath is None:
            filepath = config.CURRENT_DIR / "mamh-data.json"

        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                self.lpcd_data = json.load(f)
            logger.info(f"Loaded MAMH data for {len(self.lpcd_data)} municipalities")
        else:
            logger.warning("MAMH data file not found")
            self.lpcd_data = {}

        return self.lpcd_data

    def _find_matching_codes(
        self,
        feature: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Trouve les codes correspondants pour une feature.

        Args:
            feature: Feature GeoJSON

        Returns:
            Tuple (code_statcan, code_mamh)
        """
        props = feature.get("properties", {})

        # Codes disponibles dans la feature
        ref_statcan = props.get("ref_statcan")
        ref_mamh = props.get("ref_mamh")
        osm_id = props.get("osm_id")
        name = props.get("name", "")
        name_fr = props.get("name_fr", "")
        name_key = self._normalize_name(name) if name else ""
        name_fr_key = self._normalize_name(name_fr) if name_fr else ""

        # Build name indexes once
        if self._stats_by_name is None:
            self._stats_by_name = {}
            for code, data in self.stats.items():
                key = self._normalize_name(data.get("name", ""))
                if key and key not in self._stats_by_name:
                    self._stats_by_name[key] = code
        if self._mamh_by_name is None:
            self._mamh_by_name = {}
            for code, data in self.lpcd_data.items():
                key = self._normalize_name(data.get("nom_mun", ""))
                if key and key not in self._mamh_by_name:
                    self._mamh_by_name[key] = code

        # Chercher correspondance StatCan
        code_statcan = None
        if ref_statcan and ref_statcan in self.stats:
            code_statcan = ref_statcan
        else:
            if name_key and name_key in self._stats_by_name:
                code_statcan = self._stats_by_name[name_key]
            elif name_fr_key and name_fr_key in self._stats_by_name:
                code_statcan = self._stats_by_name[name_fr_key]

        # Chercher correspondance MAMH
        code_mamh = None
        if ref_mamh and ref_mamh in self.lpcd_data:
            code_mamh = ref_mamh
        else:
            if name_key and name_key in self._mamh_by_name:
                code_mamh = self._mamh_by_name[name_key]
            elif name_fr_key and name_fr_key in self._mamh_by_name:
                code_mamh = self._mamh_by_name[name_fr_key]
            elif ref_statcan:
                # Dériver code MAMH depuis CSDUID (derniers 5 chiffres)
                ref_str = str(ref_statcan)
                if len(ref_str) >= 5:
                    derived = ref_str[-5:]
                    if derived in self.lpcd_data:
                        code_mamh = derived

        return code_statcan, code_mamh

    def _normalize_name(self, name: str) -> str:
        """Normalise un nom de municipalité pour le matching."""
        if not name:
            return ""
        cleaned = (
            unicodedata.normalize("NFD", name)
            .encode("ascii", "ignore")
            .decode("ascii")
            .lower()
        )
        cleaned = re.sub(r"[-–—'’./(),]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def merge(
        self,
        geojson: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Dict[str, Any]]] = None,
        lpcd_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Fusionne toutes les sources de données.

        Args:
            geojson: GeoJSON FeatureCollection (optionnel)
            stats: Données StatCan (optionnel)
            lpcd_data: Données MAMH (optionnel)

        Returns:
            GeoJSON enrichi avec toutes les données
        """
        if geojson:
            self.geojson = geojson
        if stats:
            self.stats = stats
        if lpcd_data:
            self.lpcd_data = lpcd_data

        if not self.geojson:
            raise ValueError("No GeoJSON data to merge")

        self._normalize_geojson_geometry(self.geojson)
        logger.info("Merging data sources...")

        merged_features = []
        stats_matched = 0
        lpcd_matched = 0

        for feature in self.geojson.get("features", []):
            # Trouver les codes correspondants
            code_statcan, code_mamh = self._find_matching_codes(feature)

            # Enrichir les propriétés
            props = feature.get("properties", {}).copy()
            ratio = self._compute_shape_ratio(feature.get("geometry"))
            if ratio is not None:
                props["shape_ratio"] = ratio

            # Ajouter données StatCan
            if code_statcan and code_statcan in self.stats:
                stat_data = self.stats[code_statcan]
                props["population"] = stat_data.get("population")
                props["households"] = stat_data.get("households")
                props["household_size"] = stat_data.get("household_size")
                props["stat_data_year"] = stat_data.get("data_year")
                props["stat_data_source"] = stat_data.get("data_source")
                props["dguid"] = stat_data.get("dguid")
                stats_matched += 1
            else:
                props["population"] = props.get("population")  # Garder valeur OSM si existante
                props["households"] = None
                props["household_size"] = None
                props["stat_data_year"] = None
                props["stat_data_source"] = None

            # Ajouter données BIL/MAMH (LPCD et autres)
            if code_mamh and code_mamh in self.lpcd_data:
                water_data = self.lpcd_data[code_mamh]
                props["lpcd"] = water_data.get("lpcd")
                props["lpcd_status"] = water_data.get("lpcd_status", "exact")
                props["lpcd_total"] = water_data.get("lpcd_total")
                props["consommation"] = water_data.get("consommation")
                props["population_desservie"] = water_data.get("population_desservie")
                props["nb_branchements"] = water_data.get("nb_branchements")
                props["pers_par_residence"] = water_data.get("pers_par_residence")
                props["nb_reseaux"] = water_data.get("nb_reseaux")
                props["indice_fuites"] = water_data.get("indice_fuites")
                props["longueur_reseau_km"] = water_data.get("longueur_reseau_km")
                props["pertes_reelles_ml"] = water_data.get("pertes_reelles_ml")
                props["lpcd_data_year"] = water_data.get("data_year")
                props["lpcd_data_source"] = water_data.get("data_source")
                lpcd_matched += 1
            else:
                # Pas d'estimation - marquer comme manquant
                props["lpcd"] = None
                props["lpcd_status"] = "missing"
                props["lpcd_total"] = None
                props["consommation"] = None
                props["population_desservie"] = None
                props["nb_branchements"] = None
                props["pers_par_residence"] = None
                props["nb_reseaux"] = None
                props["indice_fuites"] = None
                props["longueur_reseau_km"] = None
                props["pertes_reelles_ml"] = None
                props["lpcd_data_year"] = None
                props["lpcd_data_source"] = None

            merged_features.append({
                "type": "Feature",
                "properties": props,
                "geometry": feature.get("geometry")
            })

        result = {
            "type": "FeatureCollection",
            "features": merged_features,
            "metadata": {
                "total_features": len(merged_features),
                "stats_matched": stats_matched,
                "lpcd_matched": lpcd_matched,
                "merge_date": datetime.now().isoformat(),
            }
        }

        logger.info(
            f"Merged {len(merged_features)} features "
            f"(StatCan: {stats_matched}, LPCD: {lpcd_matched})"
        )

        return result

    def _compute_shape_ratio(self, geometry: Optional[Dict[str, Any]]) -> Optional[float]:
        """Calcule le ratio aire / aire bbox pour détecter les slivers."""
        if not geometry or "coordinates" not in geometry:
            return None

        coords = geometry.get("coordinates")
        if not coords:
            return None

        polygons = [coords] if geometry.get("type") == "Polygon" else coords
        minx = miny = float("inf")
        maxx = maxy = float("-inf")
        area = 0.0

        for poly in polygons:
            if not isinstance(poly, list):
                continue
            for ring in poly:
                if not isinstance(ring, list):
                    continue
                for point in ring:
                    if not isinstance(point, (list, tuple)) or len(point) < 2:
                        continue
                    x, y = point[0], point[1]
                    if x < minx:
                        minx = x
                    if x > maxx:
                        maxx = x
                    if y < miny:
                        miny = y
                    if y > maxy:
                        maxy = y
            area += self._polygon_area(poly)

        if minx == float("inf") or miny == float("inf"):
            return None

        bbox_area = (maxx - minx) * (maxy - miny)
        if bbox_area <= 0:
            return None

        return area / bbox_area

    def _polygon_area(self, polygon: Any) -> float:
        if not isinstance(polygon, list) or not polygon:
            return 0.0
        outer = self._ring_area(polygon[0])
        inner = 0.0
        for ring in polygon[1:]:
            inner += self._ring_area(ring)
        area = outer - inner
        return area if area > 0 else 0.0

    def _ring_area(self, ring: Any) -> float:
        if not isinstance(ring, list) or len(ring) < 4:
            return 0.0
        area = 0.0
        for i in range(len(ring) - 1):
            p1 = ring[i]
            p2 = ring[i + 1]
            area += p1[0] * p2[1] - p2[0] * p1[1]
        return fabs(area) / 2.0

    def _normalize_geojson_geometry(self, geojson: Dict[str, Any]) -> None:
        """Corrige les géométries Polygon/MultiPolygon avec un niveau de nesting en trop."""
        for feature in geojson.get("features", []):
            geom = feature.get("geometry")
            if not geom or "coordinates" not in geom:
                continue
            coords = geom.get("coordinates")
            if geom.get("type") == "Polygon":
                if isinstance(coords, list) and len(coords) == 1 and self._is_ring_list(coords[0]):
                    geom["coordinates"] = coords[0]
                # Garder uniquement le ring externe pour la lisibilité
                if isinstance(geom.get("coordinates"), list) and len(geom["coordinates"]) > 1:
                    geom["coordinates"] = [geom["coordinates"][0]]
            elif geom.get("type") == "MultiPolygon":
                if not isinstance(coords, list):
                    continue
                fixed = []
                changed = False
                for poly in coords:
                    if isinstance(poly, list) and len(poly) == 1 and self._is_ring_list(poly[0]):
                        fixed.append(poly[0])
                        changed = True
                    else:
                        fixed.append(poly)
                if changed:
                    geom["coordinates"] = fixed
                # Garder uniquement le ring externe par polygone
                if isinstance(geom.get("coordinates"), list):
                    geom["coordinates"] = [
                        [poly[0]] if isinstance(poly, list) and len(poly) > 1 else poly
                        for poly in geom["coordinates"]
                    ]

    def _is_ring_list(self, value: Any) -> bool:
        return isinstance(value, list) and len(value) > 0 and self._is_ring(value[0])

    def _is_ring(self, value: Any) -> bool:
        return isinstance(value, list) and len(value) > 0 and self._is_point(value[0])

    def _is_point(self, value: Any) -> bool:
        return isinstance(value, (list, tuple)) and len(value) >= 2 and isinstance(value[0], (int, float))

    def generate_stats_file(self, geojson: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Génère le fichier de statistiques séparé.

        Args:
            geojson: GeoJSON fusionné

        Returns:
            Dict avec les statistiques par municipalité
        """
        stats = {}

        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            name = props.get("name", "Unknown")
            osm_id = props.get("osm_id")
            csd_uid = props.get("csd_uid") or props.get("ref_statcan")

            key = str(csd_uid) if csd_uid else (str(osm_id) if osm_id else name)

            stats[key] = {
                "name": name,
                "osm_id": osm_id,
                "csd_uid": csd_uid,
                "population": props.get("population"),
                "households": props.get("households"),
                "household_size": props.get("household_size"),
                "lpcd": props.get("lpcd"),
                "lpcd_status": props.get("lpcd_status"),
                "lpcd_total": props.get("lpcd_total"),
                "consommation": props.get("consommation"),
                "population_desservie": props.get("population_desservie"),
                "nb_branchements": props.get("nb_branchements"),
                "pers_par_residence": props.get("pers_par_residence"),
                "nb_reseaux": props.get("nb_reseaux"),
                "stat_data_year": props.get("stat_data_year"),
                "lpcd_data_year": props.get("lpcd_data_year"),
            }

        return stats

    def save(
        self,
        geojson: Dict[str, Any],
        geojson_path: Optional[Path] = None,
        stats_path: Optional[Path] = None
    ) -> Tuple[Path, Path]:
        """Sauvegarde les fichiers fusionnés.

        Args:
            geojson: GeoJSON fusionné
            geojson_path: Chemin du fichier GeoJSON (optionnel)
            stats_path: Chemin du fichier de stats (optionnel)

        Returns:
            Tuple (chemin GeoJSON, chemin stats)
        """
        if geojson_path is None:
            geojson_path = config.CURRENT_DIR / config.GEOJSON_FILE
        if stats_path is None:
            stats_path = config.CURRENT_DIR / config.STATS_FILE

        # Sauvegarder GeoJSON
        geojson_path.parent.mkdir(parents=True, exist_ok=True)
        with open(geojson_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False)

        logger.info(f"GeoJSON saved to {geojson_path}")

        # Générer et sauvegarder stats
        stats = self.generate_stats_file(geojson)
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        logger.info(f"Stats saved to {stats_path}")

        return geojson_path, stats_path


def merge_all_data() -> Dict[str, Any]:
    """Fonction utilitaire pour fusionner toutes les données.

    Returns:
        GeoJSON enrichi
    """
    merger = DataMerger()
    merger.load_geojson()
    merger.load_statcan()
    merger.load_mamh()
    return merger.merge()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    merger = DataMerger()

    # Charger les données
    merger.load_geojson()
    merger.load_statcan()
    merger.load_mamh()

    # Fusionner
    result = merger.merge()

    # Sauvegarder
    merger.save(result)

    print(f"Merged {len(result['features'])} municipalities")
