"""
Collecteurs de données pour la carte des municipalités du Québec.

Modules:
- overpass_collector: GeoJSON des limites municipales via OpenStreetMap
- statcan_collector: Population et ménages via Statistique Canada
- mamh_collector: Consommation d'eau (LPCD) via MAMH CSV
- data_merger: Fusion des sources de données
- cache_manager: Gestion du cache et fallback
- run_update: Point d'entrée pour le cron annuel
"""

from .config import Config

__all__ = ['Config']
