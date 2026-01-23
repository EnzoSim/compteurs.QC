"""
Gestionnaire de cache et fallback pour les données.

Gère:
- Le cache des dernières données valides
- Le fallback en cas d'échec des collecteurs
- L'historique annuel des données
- Les métadonnées de mise à jour
"""

import json
import shutil
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .config import config

logger = logging.getLogger(__name__)


class CacheManager:
    """Gestionnaire de cache et historique des données."""

    def __init__(self):
        self.cache_dir = config.CACHE_DIR
        self.history_dir = config.HISTORY_DIR
        self.current_dir = config.CURRENT_DIR
        self.metadata_file = self.cache_dir / config.METADATA_FILE

        # Créer les répertoires
        for dir_path in [self.cache_dir, self.history_dir, self.current_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def save_to_cache(self, data_type: str, data: Dict[str, Any]) -> Path:
        """Sauvegarde des données dans le cache.

        Args:
            data_type: Type de données ('geojson', 'statcan', 'mamh')
            data: Données à cacher

        Returns:
            Chemin du fichier cache
        """
        filename = f"{data_type}_backup.json"
        filepath = self.cache_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        logger.info(f"Cached {data_type} data to {filepath}")
        return filepath

    def load_from_cache(self, data_type: str) -> Optional[Dict[str, Any]]:
        """Charge des données depuis le cache.

        Args:
            data_type: Type de données ('geojson', 'statcan', 'mamh')

        Returns:
            Données du cache ou None si non disponible
        """
        filename = f"{data_type}_backup.json"
        filepath = self.cache_dir / filename

        if not filepath.exists():
            logger.warning(f"No cache found for {data_type}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded {data_type} from cache")
            return data
        except Exception as e:
            logger.error(f"Error loading cache for {data_type}: {e}")
            return None

    def archive_to_history(self, year: Optional[int] = None) -> Path:
        """Archive les données actuelles dans l'historique.

        Args:
            year: Année de l'archive (optionnel, défaut: année courante)

        Returns:
            Chemin du répertoire d'archive
        """
        if year is None:
            year = datetime.now().year

        history_year_dir = self.history_dir / str(year)
        history_year_dir.mkdir(parents=True, exist_ok=True)

        # Copier les fichiers actuels
        files_to_archive = [
            config.GEOJSON_FILE,
            config.STATS_FILE,
        ]

        for filename in files_to_archive:
            src = self.current_dir / filename
            if src.exists():
                dst = history_year_dir / filename
                shutil.copy2(src, dst)
                logger.info(f"Archived {filename} to {history_year_dir}")

        return history_year_dir

    def save_metadata(self, results: Dict[str, Dict[str, Any]]) -> Path:
        """Sauvegarde les métadonnées de mise à jour.

        Args:
            results: Résultats des collecteurs

        Returns:
            Chemin du fichier metadata
        """
        metadata = {
            "last_update": datetime.now().isoformat(),
            "sources": results,
            "warnings": [
                source for source, info in results.items()
                if not info.get("success", False)
            ]
        }

        # Compter les municipalités
        geojson_path = self.current_dir / config.GEOJSON_FILE
        if geojson_path.exists():
            try:
                with open(geojson_path, 'r', encoding='utf-8') as f:
                    geojson = json.load(f)
                metadata["total_municipalities"] = len(geojson.get("features", []))
            except Exception:
                pass

        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # Copier aussi dans current/
        current_metadata = self.current_dir / config.METADATA_FILE
        with open(current_metadata, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"Metadata saved to {self.metadata_file}")
        return self.metadata_file

    def load_metadata(self) -> Dict[str, Any]:
        """Charge les métadonnées de mise à jour.

        Returns:
            Métadonnées ou dict vide si non disponible
        """
        if not self.metadata_file.exists():
            return {}

        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            return {}

    def get_last_update(self) -> Optional[datetime]:
        """Retourne la date de dernière mise à jour.

        Returns:
            Date ou None
        """
        metadata = self.load_metadata()
        last_update = metadata.get("last_update")

        if last_update:
            try:
                return datetime.fromisoformat(last_update)
            except ValueError:
                pass

        return None

    def needs_update(self, days: int = 365) -> bool:
        """Vérifie si une mise à jour est nécessaire.

        Args:
            days: Nombre de jours avant mise à jour

        Returns:
            True si mise à jour nécessaire
        """
        last_update = self.get_last_update()

        if last_update is None:
            return True

        age = datetime.now() - last_update
        return age.days >= days

    def get_available_years(self) -> list:
        """Retourne les années disponibles dans l'historique.

        Returns:
            Liste des années
        """
        years = []
        for entry in self.history_dir.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                years.append(int(entry.name))
        return sorted(years, reverse=True)

    def load_history(self, year: int) -> Optional[Dict[str, Any]]:
        """Charge les données d'une année historique.

        Args:
            year: Année à charger

        Returns:
            GeoJSON ou None
        """
        history_year_dir = self.history_dir / str(year)
        geojson_path = history_year_dir / config.GEOJSON_FILE

        if not geojson_path.exists():
            logger.warning(f"No history found for year {year}")
            return None

        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history for {year}: {e}")
            return None

    def cleanup_old_history(self, keep_years: int = 10):
        """Nettoie les archives trop anciennes.

        Args:
            keep_years: Nombre d'années à garder
        """
        years = self.get_available_years()

        if len(years) <= keep_years:
            return

        years_to_delete = years[keep_years:]
        for year in years_to_delete:
            year_dir = self.history_dir / str(year)
            try:
                shutil.rmtree(year_dir)
                logger.info(f"Deleted old history: {year}")
            except Exception as e:
                logger.error(f"Error deleting history {year}: {e}")


# Instance globale
cache_manager = CacheManager()


def get_metadata() -> Dict[str, Any]:
    """Fonction utilitaire pour récupérer les métadonnées.

    Returns:
        Métadonnées de mise à jour
    """
    return cache_manager.load_metadata()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = CacheManager()

    print("Available years in history:", manager.get_available_years())
    print("Last update:", manager.get_last_update())
    print("Needs update:", manager.needs_update())
