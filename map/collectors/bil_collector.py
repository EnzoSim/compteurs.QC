"""
Collecteur de données BIL (Bilan des infrastructures en eau).

Lit le fichier Excel BIL qui contient des données complètes sur la
consommation d'eau des municipalités du Québec.
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import pandas as pd

from .config import config

logger = logging.getLogger(__name__)


class BILCollector:
    """Collecteur de données depuis le fichier Excel BIL."""

    # Mapping des colonnes BIL vers nos champs normalisés
    COLUMN_MAPPING = {
        'Code géo': 'code_mun',
        'Municipalité': 'nom_mun',
        'Région': 'region',
        'R_validation.Statut': 'statut',
        'T_mun.mun_ae_qte_eau_distribuee': 'lpcd_total',
        'T_mun.mun_ae_consm_residentielle': 'lpcd',
        'T_mun.mun_ae_obj_consm_residentielle': 'objectif_lpcd',
        'T_mun.mun_ae_ind_fuite_infra': 'indice_fuites',
        'T_mun.mun_ae_result_valid_donnees': 'validation_pct',
        'T_mun.mun_ae_nb_res_distr_eau_pot_distinct': 'nb_reseaux',
        'T_mun.mun_ae_loge_resid_dess': 'nb_branchements',
        'T_mun.mun_ae_nb_pers_loge': 'pers_par_residence',
        'T_mun.mun_ae_pop_dess_res_distr': 'population_desservie',
        'T_mun.mun_ae_long_tot_res_distr': 'longueur_reseau_km',
        'T_mun.mun_ae_nb_branch_serv': 'nb_branchements_service',
        'T_mun.mun_ae_vol_eau_distr': 'volume_distribue_ml',
        'T_mun.mun_ae_consm_res': 'consommation_res_ml',
        'T_mun.mun_ae_perte_eau_reel': 'pertes_reelles_ml',
        'T_mun.mun_ae_perte_eau_reel__inevit': 'pertes_inevitables_ml',
    }

    def __init__(self, filepath: Optional[Path] = None):
        """
        Initialise le collecteur.

        Args:
            filepath: Chemin vers le fichier BIL Excel
        """
        self.filepath = filepath or Path('/Users/enzo_simier/Desktop/BIL_base_donnees_2023.xlsx')
        self.data_year = 2023

    def collect_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Collecte toutes les données du fichier BIL.

        Returns:
            Dict mapping code_mun -> données municipalité
        """
        logger.info(f"Collecting BIL data from {self.filepath}...")

        try:
            # Lire le fichier Excel
            df = pd.read_excel(
                self.filepath,
                sheet_name='Données par municipalité',
                header=8  # Les données commencent à la ligne 9
            )

            logger.info(f"Loaded {len(df)} rows from BIL Excel")

            result = {}
            for _, row in df.iterrows():
                code_mun = str(row.get('Code géo', '')).strip()
                if not code_mun or code_mun == 'nan':
                    continue

                # Extraire et normaliser les données
                record = self._extract_record(row)
                if record:
                    result[code_mun] = record

            logger.info(f"Collected data for {len(result)} municipalities")
            return result

        except Exception as e:
            logger.error(f"Error collecting BIL data: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _extract_record(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Extrait un enregistrement depuis une ligne du DataFrame.

        Args:
            row: Ligne du DataFrame

        Returns:
            Dict avec les données normalisées ou None
        """
        code_mun = str(row.get('Code géo', '')).strip()
        nom_mun = row.get('Municipalité', '')
        statut = row.get('R_validation.Statut', '')

        # Ignorer les lignes sans code ou avec statut incomplet
        if not code_mun or code_mun == 'nan':
            return None

        # LPCD résidentiel
        lpcd = self._parse_float(row.get('T_mun.mun_ae_consm_residentielle'))
        lpcd_status = 'exact' if lpcd is not None else 'missing'

        # Volume distribué en ML/an (pour conversion en m³/j)
        volume_ml = self._parse_float(row.get('T_mun.mun_ae_vol_eau_distr'))

        record = {
            "code_mun": code_mun,
            "nom_mun": nom_mun,
            "region": self._parse_int(row.get('Région')),
            "statut": statut,
            "lpcd": lpcd,
            "lpcd_status": lpcd_status,
            "lpcd_total": self._parse_float(row.get('T_mun.mun_ae_qte_eau_distribuee')),
            "objectif_lpcd": str(row.get('T_mun.mun_ae_obj_consm_residentielle', '')),
            "indice_fuites": self._parse_float(row.get('T_mun.mun_ae_ind_fuite_infra')),
            "validation_pct": self._parse_float(row.get('T_mun.mun_ae_result_valid_donnees')),
            "nb_reseaux": self._parse_int(row.get('T_mun.mun_ae_nb_res_distr_eau_pot_distinct')),
            "nb_branchements": self._parse_int(row.get('T_mun.mun_ae_loge_resid_dess')),
            "pers_par_residence": self._parse_float(row.get('T_mun.mun_ae_nb_pers_loge')),
            "population_desservie": self._parse_int(row.get('T_mun.mun_ae_pop_dess_res_distr')),
            "longueur_reseau_km": self._parse_float(row.get('T_mun.mun_ae_long_tot_res_distr')),
            "nb_branchements_service": self._parse_int(row.get('T_mun.mun_ae_nb_branch_serv')),
            # Volume en ML/an - sera converti en m³/j à l'affichage
            "consommation": volume_ml,
            "consommation_res_ml": self._parse_float(row.get('T_mun.mun_ae_consm_res')),
            "pertes_reelles_ml": self._parse_float(row.get('T_mun.mun_ae_perte_eau_reel')),
            "pertes_inevitables_ml": self._parse_float(row.get('T_mun.mun_ae_perte_eau_reel__inevit')),
            "data_year": self.data_year,
            "data_source": "bil_2023"
        }

        return record

    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse une valeur en float."""
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse une valeur en entier."""
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def save(self, data: Dict[str, Dict[str, Any]], filepath: Optional[Path] = None) -> Path:
        """
        Sauvegarde les données dans un fichier JSON.

        Args:
            data: Données à sauvegarder
            filepath: Chemin du fichier (optionnel)

        Returns:
            Chemin du fichier sauvegardé
        """
        if filepath is None:
            filepath = config.CURRENT_DIR / "bil-data.json"

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"BIL data saved to {filepath}")
        return filepath


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = BILCollector()
    data = collector.collect_all()
    collector.save(data)
    print(f"Collected data for {len(data)} municipalities")
