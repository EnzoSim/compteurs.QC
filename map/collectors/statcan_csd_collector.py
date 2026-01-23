"""
Collecteur des limites officielles StatCan (CSD) via ArcGIS REST.

Remplace Overpass par les frontières officielles des municipalités.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import requests
from retry import retry

from .config import config

logger = logging.getLogger(__name__)


class StatCanCSDCollector:
    """Collecteur des limites de subdivisions de recensement (CSD)."""

    def __init__(self):
        self.base_url = config.STATCAN_CSD_SERVICE_URL.rstrip("/")
        self.pruid = config.STATCAN_CSD_PRUID
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; QuebecMapCollector/1.0)"
        })

    @retry(tries=config.RETRY_TRIES, delay=config.RETRY_DELAY, backoff=config.RETRY_BACKOFF)
    def _get(self, url: str, params: Dict[str, Any]) -> requests.Response:
        response = self.session.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response

    def _query_url(self) -> str:
        return f"{self.base_url}/query"

    def _count(self) -> int:
        params = {
            "where": f"PRUID='{self.pruid}'",
            "returnCountOnly": "true",
            "f": "json"
        }
        resp = self._get(self._query_url(), params=params)
        data = resp.json()
        return int(data.get("count", 0))

    def _fetch_page(self, offset: int, limit: int) -> Dict[str, Any]:
        params = {
            "where": f"PRUID='{self.pruid}'",
            "outFields": "*",
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": limit,
            "orderByFields": "OBJECTID"
        }
        resp = self._get(self._query_url(), params=params)
        return resp.json()

    def _get_prop(self, props: Dict[str, Any], names: List[str]) -> Optional[Any]:
        for name in names:
            if name in props:
                return props.get(name)
        # Fallback: case-insensitive search
        upper = {k.upper(): k for k in props.keys()}
        for name in names:
            key = upper.get(name.upper())
            if key:
                return props.get(key)
        return None

    def _convert_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        props = feature.get("properties", {}) or {}
        geometry = feature.get("geometry")

        csd_uid = self._get_prop(props, ["CSDUID", "CSDUID_2021", "CSDUID_2023", "CSDUID_2016"])
        csd_name = self._get_prop(props, ["CSDNAME", "CSDNAME_2021", "CSDNAME_2023", "CSDNAME_2016"])
        csd_type = self._get_prop(props, ["CSDTYPE", "CSDTYPE_2021", "CSDTYPE_2023", "CSDTYPE_2016"])
        pruid = self._get_prop(props, ["PRUID", "PRUID_2021", "PRUID_2023", "PRUID_2016"])

        ref_mamh = None
        if csd_uid:
            csd_uid_str = str(csd_uid)
            if len(csd_uid_str) >= 5:
                ref_mamh = csd_uid_str[-5:]

        properties = {
            "csd_uid": str(csd_uid) if csd_uid is not None else None,
            "name": csd_name,
            "name_fr": csd_name,
            "csd_type": csd_type,
            "pruid": str(pruid) if pruid is not None else None,
            "ref_statcan": str(csd_uid) if csd_uid is not None else None,
            "ref_mamh": ref_mamh,
            "source": "statcan_csd"
        }

        return {
            "type": "Feature",
            "properties": properties,
            "geometry": geometry
        }

    def collect_all(self, page_size: int = 500) -> Dict[str, Any]:
        logger.info("Fetching StatCan CSD boundaries...")

        total = self._count()
        logger.info(f"StatCan CSD count: {total}")
        features: List[Dict[str, Any]] = []

        offset = 0
        while offset < total:
            geojson = self._fetch_page(offset, page_size)
            page_features = geojson.get("features", [])
            logger.info(f"Fetched {len(page_features)} features (offset {offset})")
            for feature in page_features:
                features.append(self._convert_feature(feature))
            offset += page_size

        return {
            "type": "FeatureCollection",
            "features": features
        }

    def save(self, geojson: Dict[str, Any], filepath: Optional[Path] = None) -> Path:
        if filepath is None:
            filepath = config.CURRENT_DIR / config.GEOJSON_FILE

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False)

        logger.info(f"StatCan CSD GeoJSON saved to {filepath} ({len(geojson['features'])} features)")
        return filepath


def collect_statcan_csd() -> Dict[str, Any]:
    collector = StatCanCSDCollector()
    return collector.collect_all()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = StatCanCSDCollector()
    data = collector.collect_all()
    collector.save(data)
    print(f"Collected {len(data['features'])} StatCan CSD features")
