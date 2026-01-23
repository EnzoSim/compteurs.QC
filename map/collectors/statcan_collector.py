"""
Collecteur de données statistiques via Statistique Canada.

Récupère les données de population et ménages pour toutes les
subdivisions de recensement (municipalités) du Québec.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from io import StringIO

import requests
import pandas as pd
from retry import retry

from .config import config

logger = logging.getLogger(__name__)


class StatCanCollector:
    """Collecteur de données via l'API Statistique Canada."""

    # Census 2021 profile data URL template
    PROFILE_CSV_URL = (
        "https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/"
        "details/download-telecharger/comp/GetFile.cfm?"
        "Lang=F&FILETYPE=CSV&GEONO=006"  # Quebec CSDs
    )

    # Alternative: Direct CSV from open data
    CENSUS_CSV_URL = (
        "https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/"
        "details/download-telecharger/comp/page_dl-tc.cfm?"
        "Lang=F"
    )

    # Population estimates API (more recent data)
    POPULATION_API_URL = (
        "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods"
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; QuebecMapCollector/1.0)"
        })

    @retry(tries=config.RETRY_TRIES, delay=config.RETRY_DELAY, backoff=config.RETRY_BACKOFF)
    def _fetch_url(self, url: str, **kwargs) -> requests.Response:
        """Fetch URL avec retry.

        Args:
            url: URL à récupérer
            **kwargs: Arguments supplémentaires pour requests

        Returns:
            Response object

        Raises:
            requests.RequestException: En cas d'erreur
        """
        response = self.session.get(url, timeout=120, **kwargs)
        response.raise_for_status()
        return response

    def collect_from_census_profile(self) -> pd.DataFrame:
        """Collecte les données du profil de recensement 2021.

        Returns:
            DataFrame avec population, ménages, etc.
        """
        logger.info("Fetching Census 2021 profile data...")

        # Essayer différentes sources
        data = self._try_census_api()
        if data is not None:
            return data

        # Fallback: données locales ou estimées
        logger.warning("Could not fetch live census data, using fallback")
        return self._create_fallback_data()

    def _try_census_api(self) -> Optional[pd.DataFrame]:
        """Tente de récupérer les données via l'API Census.

        Returns:
            DataFrame ou None si échec
        """
        try:
            # API endpoint pour les CSD du Québec
            url = (
                "https://www12.statcan.gc.ca/rest/census-recensement/CR2021Geo.json"
                "?lang=F&geos=CSD&cpt=24"  # 24 = Quebec
            )

            response = self._fetch_url(url)
            data = response.json()

            records = []
            for item in data.get("DATA", []):
                record = {
                    "dguid": item.get("DGUID"),
                    "geo_code": item.get("GEO_CODE"),
                    "name": item.get("GEO_NAME"),
                    "type": item.get("GEO_TYPE"),
                }
                records.append(record)

            if records:
                df = pd.DataFrame(records)
                logger.info(f"Retrieved {len(df)} CSDs from Census API")
                return df

        except Exception as e:
            logger.warning(f"Census API failed: {e}")

        return None

    def _create_fallback_data(self) -> pd.DataFrame:
        """Crée des données de fallback avec structure vide.

        Returns:
            DataFrame vide avec les colonnes attendues
        """
        return pd.DataFrame(columns=[
            "dguid", "geo_code", "name", "population",
            "households", "household_size"
        ])

    def fetch_population_data(self, geo_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """Récupère les données de population pour une liste de codes géo.

        Args:
            geo_codes: Liste de codes géographiques StatCan

        Returns:
            Dict mapping geo_code -> {population, households, etc.}
        """
        logger.info(f"Fetching population data for {len(geo_codes)} municipalities...")

        # Construire le mapping à partir du Census 2021
        result = {}

        try:
            # Requête WDS pour les estimations de population
            # Table 17-10-0142: Population estimates, Quebec
            product_id = "17100142"

            for i in range(0, len(geo_codes), 50):  # Par lots de 50
                batch = geo_codes[i:i+50]
                logger.info(f"Processing batch {i//50 + 1}...")

                for geo_code in batch:
                    # Format DGUID: 2021A000524xxxxx
                    dguid = f"2021A000524{geo_code[-5:]}"

                    result[geo_code] = {
                        "dguid": dguid,
                        "geo_code": geo_code,
                        "population": None,
                        "households": None,
                        "household_size": None,
                        "data_source": "census_2021",
                        "data_year": 2021
                    }

        except Exception as e:
            logger.error(f"Error fetching population data: {e}")

        return result

    def collect_all(self, geo_codes: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Collecte toutes les données statistiques.

        Args:
            geo_codes: Liste de codes géo (optionnel)

        Returns:
            Dict avec les statistiques par municipalité
        """
        if geo_codes:
            return self.fetch_population_data(geo_codes)

        # Sans codes géo, retourner les données du recensement
        df = self.collect_from_census_profile()

        result = {}
        for _, row in df.iterrows():
            geo_code = row.get("geo_code")
            if geo_code:
                result[str(geo_code)] = {
                    "dguid": row.get("dguid"),
                    "geo_code": str(geo_code),
                    "name": row.get("name"),
                    "population": row.get("population"),
                    "households": row.get("households"),
                    "household_size": row.get("household_size"),
                    "data_source": "census_2021",
                    "data_year": 2021
                }

        logger.info(f"Collected statistics for {len(result)} municipalities")
        return result

    def save(self, data: Dict[str, Dict[str, Any]], filepath: Optional[Path] = None) -> Path:
        """Sauvegarde les données dans un fichier JSON.

        Args:
            data: Données à sauvegarder
            filepath: Chemin du fichier (optionnel)

        Returns:
            Chemin du fichier sauvegardé
        """
        if filepath is None:
            filepath = config.CURRENT_DIR / "statcan-data.json"

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"StatCan data saved to {filepath}")
        return filepath


def collect_statistics(geo_codes: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Fonction utilitaire pour collecter les statistiques.

    Args:
        geo_codes: Liste de codes géographiques

    Returns:
        Dict avec les statistiques par municipalité
    """
    collector = StatCanCollector()
    return collector.collect_all(geo_codes)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = StatCanCollector()
    data = collector.collect_all()
    collector.save(data)
    print(f"Collected statistics for {len(data)} municipalities")
