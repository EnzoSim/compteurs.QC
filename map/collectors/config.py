"""Configuration centralisée pour les collecteurs de données."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Configuration pour le pipeline de collecte de données."""

    # Chemins
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    CURRENT_DIR: Path = DATA_DIR / "current"
    CACHE_DIR: Path = DATA_DIR / "cache"
    HISTORY_DIR: Path = DATA_DIR / "history"

    # Fichiers de sortie
    GEOJSON_FILE: str = "quebec-municipalities.geojson"
    STATS_FILE: str = "municipalities-stats.json"
    METADATA_FILE: str = "metadata.json"

    # Overpass API
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_TIMEOUT: int = 600  # secondes

    # Régions administratives du Québec (pour requêtes Overpass par région)
    QUEBEC_REGIONS: List[str] = None

    # StatCan API
    STATCAN_API_URL: str = "https://www12.statcan.gc.ca/rest/census-recensement/CR2021Geo.json"
    STATCAN_PROFILE_URL: str = "https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/download-telecharger.cfm"
    STATCAN_CSD_SERVICE_URL: str = "https://geo.statcan.gc.ca/geo_wa/rest/services/2021/Digital_boundary_files/MapServer/9"
    STATCAN_CSD_PRUID: str = "24"

    # MAMH CSV
    MAMH_BASE_URL: str = "https://donneesouvertes.affmunqc.net/sqeep_2019_2025"
    MAMH_YEARS: List[int] = None

    # Retry configuration
    RETRY_TRIES: int = 3
    RETRY_DELAY: int = 5  # secondes
    RETRY_BACKOFF: int = 2  # multiplicateur

    def __post_init__(self):
        """Initialisation des valeurs par défaut."""
        if self.QUEBEC_REGIONS is None:
            self.QUEBEC_REGIONS = [
                "Bas-Saint-Laurent",
                "Saguenay–Lac-Saint-Jean",
                "Capitale-Nationale",
                "Mauricie",
                "Estrie",
                "Montréal",
                "Outaouais",
                "Abitibi-Témiscamingue",
                "Côte-Nord",
                "Nord-du-Québec",
                "Gaspésie–Îles-de-la-Madeleine",
                "Chaudière-Appalaches",
                "Laval",
                "Lanaudière",
                "Laurentides",
                "Montérégie",
                "Centre-du-Québec"
            ]

        if self.MAMH_YEARS is None:
            self.MAMH_YEARS = [2023, 2022, 2021, 2020, 2019, 2018]

        # Créer les répertoires si nécessaire
        for dir_path in [self.CURRENT_DIR, self.CACHE_DIR, self.HISTORY_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_mamh_csv_url(self, year: int, dataset: str = "consommation") -> str:
        """Retourne l'URL du CSV MAMH pour une année donnée.

        Args:
            year: Année des données (2018-2023)
            dataset: 'consommation' ou 'fuites'

        Returns:
            URL complète du fichier CSV
        """
        return f"{self.MAMH_BASE_URL}/{dataset}_classe_{year}.csv"

    def get_history_dir(self, year: int) -> Path:
        """Retourne le chemin du répertoire d'historique pour une année.

        Args:
            year: Année de l'historique

        Returns:
            Chemin du répertoire
        """
        history_year_dir = self.HISTORY_DIR / str(year)
        history_year_dir.mkdir(parents=True, exist_ok=True)
        return history_year_dir


# Instance globale de configuration
config = Config()
