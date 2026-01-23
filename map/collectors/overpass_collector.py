"""
Collecteur de données géographiques via l'API Overpass (OpenStreetMap).

Récupère les polygones de toutes les municipalités du Québec (~1100)
avec leurs propriétés (nom, code StatCan, type, etc.).
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

import requests
from retry import retry

from .config import config

logger = logging.getLogger(__name__)


class OverpassCollector:
    """Collecteur de données géographiques via Overpass API."""

    def __init__(self):
        self.url = config.OVERPASS_URL
        self.timeout = config.OVERPASS_TIMEOUT
        self.regions = config.QUEBEC_REGIONS

    def _build_query(self, bbox: Optional[tuple] = None) -> str:
        """Construit la requête Overpass pour une bounding box ou tout le Québec.

        Args:
            bbox: Tuple (south, west, north, east) de la bounding box (optionnel)

        Returns:
            Requête Overpass formatée
        """
        if bbox:
            # Requête pour une bounding box spécifique
            south, west, north, east = bbox
            return f'''
[out:json][timeout:{self.timeout}];
area["ISO3166-2"="CA-QC"]->.quebec;
(
  relation["admin_level"="8"]["boundary"="administrative"](area.quebec)({south},{west},{north},{east});
);
out body;
>;
out skel qt;
'''
        else:
            # Requête pour tout le Québec via l'aire ISO
            return f'''
[out:json][timeout:{self.timeout}];
area["ISO3166-2"="CA-QC"]->.quebec;
(
  relation["admin_level"="8"]["boundary"="administrative"](area.quebec);
);
out body;
>;
out skel qt;
'''

    @retry(tries=config.RETRY_TRIES, delay=config.RETRY_DELAY, backoff=config.RETRY_BACKOFF)
    def _fetch_overpass(self, query: str) -> Dict[str, Any]:
        """Exécute une requête Overpass avec retry.

        Args:
            query: Requête Overpass

        Returns:
            Données JSON de la réponse

        Raises:
            requests.RequestException: En cas d'erreur HTTP
        """
        logger.info(f"Executing Overpass query ({len(query)} chars)")
        response = requests.post(
            self.url,
            data={"data": query},
            timeout=self.timeout + 30
        )
        response.raise_for_status()
        return response.json()

    def _osm_to_geojson(self, osm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convertit les données OSM en GeoJSON.

        Args:
            osm_data: Données brutes de l'API Overpass

        Returns:
            GeoJSON FeatureCollection
        """
        # Indexer les nodes par ID pour construire les polygones
        nodes = {}
        ways = {}
        relations = []

        for element in osm_data.get("elements", []):
            if element["type"] == "node":
                nodes[element["id"]] = (element["lon"], element["lat"])
            elif element["type"] == "way":
                ways[element["id"]] = element.get("nodes", [])
            elif element["type"] == "relation":
                relations.append(element)

        features = []
        for relation in relations:
            feature = self._relation_to_feature(relation, nodes, ways)
            if feature:
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }

    def _relation_to_feature(
        self,
        relation: Dict[str, Any],
        nodes: Dict[int, tuple],
        ways: Dict[int, List[int]]
    ) -> Optional[Dict[str, Any]]:
        """Convertit une relation OSM en Feature GeoJSON.

        Args:
            relation: Relation OSM
            nodes: Index des nodes
            ways: Index des ways

        Returns:
            Feature GeoJSON ou None si conversion impossible
        """
        tags = relation.get("tags", {})

        # Extraire les propriétés
        properties = {
            "osm_id": relation["id"],
            "name": tags.get("name", tags.get("name:fr", "Sans nom")),
            "name_fr": tags.get("name:fr", tags.get("name")),
            "type": tags.get("boundary", "administrative"),
            "admin_level": tags.get("admin_level", "8"),
            "ref_statcan": tags.get("ref:statcan"),
            "ref_mamh": tags.get("ref:mamh"),
            "wikidata": tags.get("wikidata"),
            "wikipedia": tags.get("wikipedia"),
            "population": self._parse_int(tags.get("population")),
            "designation": tags.get("designation"),
        }

        # Construire le polygone
        coordinates = self._build_polygon(relation, nodes, ways)
        if not coordinates:
            logger.warning(f"Could not build polygon for {properties['name']}")
            return None

        # Déterminer le type de géométrie
        if len(coordinates) == 1:
            polygon = coordinates[0]
            if self._is_ring(polygon):
                polygon = [polygon]
            geometry = {
                "type": "Polygon",
                "coordinates": polygon
            }
        else:
            polygons = []
            for poly in coordinates:
                if self._is_ring(poly):
                    polygons.append([poly])
                else:
                    polygons.append(poly)
            geometry = {
                "type": "MultiPolygon",
                "coordinates": polygons
            }

        return {
            "type": "Feature",
            "properties": properties,
            "geometry": geometry
        }

    def _is_ring(self, value: Any) -> bool:
        """Retourne True si value ressemble à un ring GeoJSON."""
        return (
            isinstance(value, list)
            and len(value) > 0
            and isinstance(value[0], (list, tuple))
            and len(value[0]) >= 2
            and isinstance(value[0][0], (int, float))
        )

    def _build_polygon(
        self,
        relation: Dict[str, Any],
        nodes: Dict[int, tuple],
        ways: Dict[int, List[int]]
    ) -> List[List[tuple]]:
        """Construit les coordonnées d'un polygone à partir des ways.

        Args:
            relation: Relation OSM
            nodes: Index des nodes
            ways: Index des ways

        Returns:
            Liste de rings (outer et inner)
        """
        outer_rings = []
        inner_rings = []

        for member in relation.get("members", []):
            if member["type"] != "way":
                continue

            way_id = member["ref"]
            if way_id not in ways:
                continue

            # Convertir les node IDs en coordonnées
            coords = []
            for node_id in ways[way_id]:
                if node_id in nodes:
                    coords.append(nodes[node_id])

            if len(coords) < 3:
                continue

            role = member.get("role", "outer")
            if role == "inner":
                inner_rings.append(coords)
            else:
                outer_rings.append(coords)

        # Fusionner les outer rings si nécessaire
        merged_rings = self._merge_rings(outer_rings)

        # Combiner outer et inner rings
        result = []
        for outer in merged_rings:
            ring = [outer]
            # Ajouter les inner rings qui sont dans ce outer
            for inner in inner_rings:
                ring.append(inner)
            result.append(ring[0] if len(ring) == 1 else ring)

        return result if result else [[]]

    def _merge_rings(self, rings: List[List[tuple]]) -> List[List[tuple]]:
        """Fusionne les rings non fermés.

        Args:
            rings: Liste de rings potentiellement non fermés

        Returns:
            Liste de rings fermés
        """
        if not rings:
            return []

        # Séparer rings fermés et ouverts
        closed = [r for r in rings if r and r[0] == r[-1]]
        open_rings = [r for r in rings if r and r[0] != r[-1]]

        if not open_rings:
            return closed

        # Tenter de fusionner les rings ouverts
        while open_rings:
            current = open_rings.pop(0)
            merged = False

            for i, other in enumerate(open_rings):
                # Vérifier si on peut connecter
                if current[-1] == other[0]:
                    open_rings[i] = current + other[1:]
                    merged = True
                    break
                elif current[-1] == other[-1]:
                    open_rings[i] = current + list(reversed(other))[1:]
                    merged = True
                    break
                elif current[0] == other[-1]:
                    open_rings[i] = other + current[1:]
                    merged = True
                    break
                elif current[0] == other[0]:
                    open_rings[i] = list(reversed(current)) + other[1:]
                    merged = True
                    break

            if not merged:
                # Ring isolé, le fermer si possible
                if len(current) >= 3:
                    current.append(current[0])
                    closed.append(current)

        # Vérifier les rings fusionnés
        for ring in open_rings:
            if ring and ring[0] == ring[-1]:
                closed.append(ring)
            elif len(ring) >= 3:
                ring.append(ring[0])
                closed.append(ring)

        return closed

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse une valeur en entier.

        Args:
            value: Valeur à parser

        Returns:
            Entier ou None
        """
        if not value:
            return None
        try:
            return int(value.replace(",", "").replace(" ", ""))
        except (ValueError, AttributeError):
            return None

    def collect_all(self, by_bbox: bool = True) -> Dict[str, Any]:
        """Collecte toutes les municipalités du Québec.

        Args:
            by_bbox: Si True, effectue plusieurs requêtes par bounding box
                    pour éviter les timeouts. Sinon, une seule requête.

        Returns:
            GeoJSON FeatureCollection avec toutes les municipalités
        """
        all_features = []

        # Bounding boxes du Québec (divisé en 6 zones pour éviter timeouts)
        # Format: (south, west, north, east)
        quebec_bboxes = [
            # Sud du Québec (Montérégie, Estrie, Centre-du-Québec)
            (44.9, -79.8, 46.5, -70.0),
            # Montréal et Laurentides
            (45.2, -74.8, 47.0, -73.0),
            # Capitale-Nationale et Chaudière-Appalaches
            (46.0, -72.5, 48.0, -68.0),
            # Saguenay-Lac-Saint-Jean et Côte-Nord sud
            (47.5, -75.0, 50.0, -66.0),
            # Abitibi-Témiscamingue et Nord-du-Québec sud
            (47.0, -80.0, 50.0, -75.0),
            # Côte-Nord et Gaspésie
            (48.0, -70.0, 51.5, -56.0),
        ]

        if by_bbox:
            logger.info(f"Collecting municipalities by bounding box ({len(quebec_bboxes)} zones)")
            for i, bbox in enumerate(quebec_bboxes):
                logger.info(f"[{i+1}/{len(quebec_bboxes)}] Fetching bbox {bbox}...")
                try:
                    query = self._build_query(bbox)
                    osm_data = self._fetch_overpass(query)
                    geojson = self._osm_to_geojson(osm_data)
                    all_features.extend(geojson["features"])
                    logger.info(f"  -> {len(geojson['features'])} municipalities found")

                    # Pause entre les requêtes pour respecter les limites de l'API
                    if i < len(quebec_bboxes) - 1:
                        time.sleep(3)

                except Exception as e:
                    logger.error(f"Error fetching bbox {bbox}: {e}")
                    continue
        else:
            logger.info("Collecting all municipalities in a single query...")
            query = self._build_query()
            osm_data = self._fetch_overpass(query)
            geojson = self._osm_to_geojson(osm_data)
            all_features = geojson["features"]

        # Dédupliquer par osm_id
        seen_ids = set()
        unique_features = []
        for feature in all_features:
            osm_id = feature["properties"].get("osm_id")
            if osm_id and osm_id not in seen_ids:
                seen_ids.add(osm_id)
                unique_features.append(feature)

        logger.info(f"Total: {len(unique_features)} unique municipalities collected")

        return {
            "type": "FeatureCollection",
            "features": unique_features
        }

    def save(self, geojson: Dict[str, Any], filepath: Optional[Path] = None) -> Path:
        """Sauvegarde le GeoJSON dans un fichier.

        Args:
            geojson: Données GeoJSON
            filepath: Chemin du fichier (optionnel)

        Returns:
            Chemin du fichier sauvegardé
        """
        if filepath is None:
            filepath = config.CURRENT_DIR / config.GEOJSON_FILE

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        logger.info(f"GeoJSON saved to {filepath} ({len(geojson['features'])} features)")
        return filepath


def collect_geojson(by_region: bool = True) -> Dict[str, Any]:
    """Fonction utilitaire pour collecter le GeoJSON.

    Args:
        by_region: Collecter par région pour éviter les timeouts

    Returns:
        GeoJSON FeatureCollection
    """
    collector = OverpassCollector()
    return collector.collect_all(by_region=by_region)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = OverpassCollector()
    geojson = collector.collect_all(by_region=True)
    collector.save(geojson)
    print(f"Collected {len(geojson['features'])} municipalities")
