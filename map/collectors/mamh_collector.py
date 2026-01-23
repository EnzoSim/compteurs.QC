"""
Collecteur de données de consommation d'eau via MAMH (CSV directs).

Récupère les données LPCD (Litres Par Capita par Jour) pour toutes les
municipalités du Québec depuis les fichiers CSV du SQEEP.

Source: https://donneesouvertes.affmunqc.net/sqeep_2019_2025/
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


class MAMHCollector:
    """Collecteur de données de consommation d'eau via CSV MAMH."""

    def __init__(self):
        self.base_url = config.MAMH_BASE_URL
        self.years = config.MAMH_YEARS
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; QuebecMapCollector/1.0)"
        })

    def _get_csv_url(self, year: int, dataset: str = "consommation") -> str:
        """Construit l'URL du CSV MAMH.

        Args:
            year: Année des données
            dataset: 'consommation' ou 'fuites'

        Returns:
            URL complète du fichier CSV
        """
        return f"{self.base_url}/{dataset}_classe_{year}.csv"

    @retry(tries=config.RETRY_TRIES, delay=config.RETRY_DELAY, backoff=config.RETRY_BACKOFF)
    def _fetch_csv(self, url: str) -> pd.DataFrame:
        """Télécharge et parse un fichier CSV.

        Args:
            url: URL du fichier CSV

        Returns:
            DataFrame avec les données

        Raises:
            requests.RequestException: En cas d'erreur HTTP
        """
        logger.info(f"Fetching CSV: {url}")
        response = self.session.get(url, timeout=60)
        response.raise_for_status()

        # Essayer différents encodages
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                content = response.content.decode(encoding)
                df = pd.read_csv(StringIO(content), sep=None, engine='python')
                logger.info(f"Successfully parsed CSV with {encoding} ({len(df)} rows)")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue

        raise ValueError(f"Could not parse CSV from {url}")

    def _find_latest_year(self) -> int:
        """Trouve l'année la plus récente avec des données disponibles.

        Returns:
            Année la plus récente
        """
        for year in sorted(self.years, reverse=True):
            try:
                url = self._get_csv_url(year)
                response = self.session.head(url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"Latest available year: {year}")
                    return year
            except Exception:
                continue

        logger.warning("No MAMH data found, using default year 2023")
        return 2023

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalise les noms de colonnes du CSV.

        Args:
            df: DataFrame brut

        Returns:
            DataFrame avec colonnes normalisées
        """
        # Mapping des colonnes MAMH SQEEP
        # Source: https://donneesouvertes.affmunqc.net/sqeep_2019_2025/
        column_mapping = {
            # Code municipal
            'mun_c': 'code_mun',
            'code_mun': 'code_mun',
            'code_municipal': 'code_mun',

            # Nom de la municipalité
            'mun_n': 'nom_mun',
            'nom_mun': 'nom_mun',
            'municipalite': 'nom_mun',

            # Type de municipalité
            'mun_d': 'type_mun',

            # Volume d'eau distribué (ML/an)
            'vol_eau_dist': 'consommation',
            'consommation': 'consommation',

            # Population desservie
            'pop_desservie': 'population_desservie',
            'population': 'population_desservie',

            # LPCD - Consommation résidentielle par personne (litres/personne/jour)
            # On utilise consom_resid car qte_eau_pers inclut les pertes et usage non-résidentiel
            'consom_resid': 'lpcd',
            'lpcd': 'lpcd',

            # Quantité totale distribuée (incluant pertes, commercial, industriel)
            'qte_eau_pers': 'lpcd_total',

            # Nombre de branchements/résidences desservies
            'nb_resid_desservi': 'nb_branchements',

            # Personnes par résidence
            'nb_pers_resid': 'pers_par_residence',

            # Nombre de réseaux de distribution
            'nb_reseau_dist': 'nb_reseaux',

            # Année
            'annee': 'annee',
        }

        # Normaliser les colonnes
        df.columns = df.columns.str.lower().str.strip()
        df = df.rename(columns={
            col: column_mapping.get(col, col)
            for col in df.columns
            if col in column_mapping
        })

        return df

    def _calculate_lpcd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule le LPCD si non présent dans les données.

        LPCD = (Consommation m³/jour * 1000) / Population

        Args:
            df: DataFrame avec consommation et population

        Returns:
            DataFrame avec colonne LPCD
        """
        if 'lpcd' in df.columns:
            return df

        if 'consommation' in df.columns and 'population' in df.columns:
            # Supposer consommation annuelle en m³, convertir en L/jour
            df['lpcd'] = (df['consommation'] * 1000 / 365) / df['population']
            df['lpcd'] = df['lpcd'].round(1)
            logger.info("Calculated LPCD from consumption and population")

        return df

    def collect_year(self, year: int) -> Dict[str, Dict[str, Any]]:
        """Collecte les données de consommation pour une année.

        Args:
            year: Année des données

        Returns:
            Dict mapping code_mun -> données
        """
        logger.info(f"Collecting MAMH data for year {year}...")

        result = {}

        try:
            # Télécharger le CSV de consommation
            url = self._get_csv_url(year, "consommation")
            df = self._fetch_csv(url)
            df = self._normalize_columns(df)

            logger.info(f"Columns after normalization: {list(df.columns)}")

            # Calculer LPCD si non présent
            df = self._calculate_lpcd(df)

            # Parser les données
            for _, row in df.iterrows():
                code_mun = str(row.get('code_mun', '')).strip()
                if not code_mun:
                    continue

                # Parser le LPCD (peut être "Non disponible" ou un nombre)
                lpcd_raw = row.get('lpcd')
                lpcd = self._parse_float(lpcd_raw)

                # Déterminer le statut LPCD
                if lpcd is not None:
                    lpcd_status = "exact"
                elif str(lpcd_raw).lower() in ['non disponible', 'nd', 'n/a', '']:
                    lpcd_status = "missing"
                else:
                    lpcd_status = "missing"

                record = {
                    "code_mun": code_mun,
                    "nom_mun": row.get('nom_mun'),
                    "type_mun": row.get('type_mun'),
                    "lpcd": lpcd,
                    "lpcd_status": lpcd_status,
                    "lpcd_total": self._parse_float(row.get('lpcd_total')),
                    "consommation": self._parse_float(row.get('consommation')),
                    "population_desservie": self._parse_int(row.get('population_desservie')),
                    "nb_branchements": self._parse_int(row.get('nb_branchements')),
                    "pers_par_residence": self._parse_float(row.get('pers_par_residence')),
                    "nb_reseaux": self._parse_int(row.get('nb_reseaux')),
                    "data_year": year,
                    "data_source": "mamh_sqeep"
                }

                result[code_mun] = record

            logger.info(f"Collected LPCD data for {len(result)} municipalities")

        except Exception as e:
            logger.error(f"Error collecting MAMH data for {year}: {e}")
            import traceback
            traceback.print_exc()

        return result

    def collect_all(self, year: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """Collecte toutes les données de consommation.

        Args:
            year: Année spécifique (optionnel, sinon la plus récente)

        Returns:
            Dict avec les données LPCD par municipalité
        """
        if year is None:
            year = self._find_latest_year()

        return self.collect_year(year)

    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse une valeur en float.

        Args:
            value: Valeur à parser

        Returns:
            Float ou None
        """
        if pd.isna(value):
            return None
        try:
            return float(str(value).replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            return None

    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse une valeur en entier.

        Args:
            value: Valeur à parser

        Returns:
            Entier ou None
        """
        if pd.isna(value):
            return None
        try:
            return int(float(str(value).replace(",", ".").replace(" ", "")))
        except (ValueError, TypeError):
            return None

    def save(self, data: Dict[str, Dict[str, Any]], filepath: Optional[Path] = None) -> Path:
        """Sauvegarde les données dans un fichier JSON.

        Args:
            data: Données à sauvegarder
            filepath: Chemin du fichier (optionnel)

        Returns:
            Chemin du fichier sauvegardé
        """
        if filepath is None:
            filepath = config.CURRENT_DIR / "mamh-data.json"

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"MAMH data saved to {filepath}")
        return filepath


def collect_lpcd(year: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """Fonction utilitaire pour collecter les données LPCD.

    Args:
        year: Année des données (optionnel)

    Returns:
        Dict avec les données LPCD par municipalité
    """
    collector = MAMHCollector()
    return collector.collect_all(year)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = MAMHCollector()
    data = collector.collect_all()
    collector.save(data)
    print(f"Collected LPCD data for {len(data)} municipalities")
