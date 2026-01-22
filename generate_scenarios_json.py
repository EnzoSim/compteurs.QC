#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur JSON pour l'interface HTML — Option A (Python source unique)

Ce script précalcule tous les scénarios et exporte les résultats en JSON.
L'HTML devient un simple viewer qui affiche les données sans recalculer.

Avantages:
- Équivalence garantie Python/HTML (même code calcule tout)
- Traçabilité complète (JSON vérifiable, reproductible)
- Pas de serveur requis (HTML statique)

Usage:
    python generate_scenarios_json.py

Output:
    scenarios_output.json — données précalculées pour le viewer HTML

Auteur: Enzo Simier
Version: 1.0.0 (janvier 2026)
"""

import json
import numpy as np
from datetime import datetime
from itertools import product
from typing import Any

from analyse_compteurs_eau import (
    # Version
    __version__ as MODEL_VERSION,
    # Classes et structures
    ParametresModele,
    ParametresCompteur,
    TypeCompteur,
    ModeCompte,
    ParametresValeurEau,
    ParametresPersistance,
    ModePersistance,
    ParametresFuites,
    ModeRepartitionCouts,
    ConfigEconomiesEchelle,
    ParametresAdoption,
    ModeAdoption,
    # Fonctions
    executer_modele,
    calculer_alpha_comportement,
    # Préréglages
    DEFAUTS_LONGUEUIL,
    COMPTEUR_LONGUEUIL_AMI,
    PERSISTANCE_OPTIMISTE,
    PERSISTANCE_REALISTE,
    PERSISTANCE_PESSIMISTE,
    FUITES_SANS_COUT,
    FUITES_CONTEXTE_QUEBEC,
    FUITES_QUEBEC_DEUX_STOCKS,
    VALEUR_EAU_QUEBEC,
)


# =============================================================================
# CONFIGURATION DES SCÉNARIOS À PRÉCALCULER
# =============================================================================

# Préréglages de villes (données SQEEP 2023)
PRESETS_VILLES = {
    "longueuil": {
        "nb_menages": 116258,
        "taille_menage": 2.18,
        "lpcd": 236,
        "nom": "Longueuil",
    },
    "montreal": {
        "nb_menages": 750000,
        "taille_menage": 2.1,
        "lpcd": 332,
        "nom": "Montréal",
    },
    "quebec": {
        "nb_menages": 180000,
        "taille_menage": 2.15,
        "lpcd": 280,
        "nom": "Québec (ville)",
    },
    "winnipeg": {
        "nb_menages": 221000,
        "taille_menage": 2.3,
        "lpcd": 250,
        "nom": "Winnipeg",
    },
}

# Types de compteurs à comparer
TYPES_COMPTEURS = {
    "ami": {
        "type": TypeCompteur.AMI,
        "cout_compteur": 250.0,
        "heures_installation": 3.0,
        "taux_horaire": 125.0,
        "cout_reseau": 50.0,
        "nom": "AMI (intelligent)",
    },
    "amr": {
        "type": TypeCompteur.AMR,
        "cout_compteur": 150.0,
        "heures_installation": 3.0,
        "taux_horaire": 125.0,
        "cout_reseau": 0.0,
        "nom": "AMR (lecture auto)",
    },
    "manuel": {
        "type": TypeCompteur.MANUEL,
        "cout_compteur": 75.0,
        "heures_installation": 3.0,
        "taux_horaire": 125.0,
        "cout_reseau": 0.0,
        "nom": "Manuel",
    },
}

# Scénarios de persistance comportementale
SCENARIOS_PERSISTANCE = {
    "optimiste": {
        "params": PERSISTANCE_OPTIMISTE,
        "nom": "Optimiste (effet constant)",
        "description": "L'effet comportemental reste constant à 8% sur tout l'horizon",
    },
    "realiste": {
        "params": PERSISTANCE_REALISTE,
        "nom": "Réaliste (plateau 2.5%)",
        "description": "Décroissance exponentielle vers un plateau de 2.5%",
    },
    "pessimiste": {
        "params": PERSISTANCE_PESSIMISTE,
        "nom": "Pessimiste (fadeout 10 ans)",
        "description": "Érosion linéaire complète en 10 ans",
    },
    "ultra": {
        "params": ParametresPersistance(
            mode=ModePersistance.CONSTANT,
            alpha_initial=0.0,
            alpha_plateau=0.0,
            nom="Ultra-pessimiste",
        ),
        "nom": "Ultra-pessimiste (aucun effet)",
        "description": "Aucun effet comportemental, seules les fuites comptent",
    },
}

# Scénarios de fuites — utilise les préréglages de analyse_compteurs_eau.py
# pour garantir la cohérence entre le JSON et les calculs directs
SCENARIOS_FUITES = {
    "standard": {
        "params": FUITES_SANS_COUT,
        "nom": "Standard sans coût (20%, 4 ans)",
    },
    "quebec": {
        "params": FUITES_CONTEXTE_QUEBEC,
        "nom": "Contexte Québec (35%, 7 ans, coûts inclus)",
    },
    "deux_stocks": {
        "params": FUITES_QUEBEC_DEUX_STOCKS,
        "nom": "Différencié QC",
    },
}


# =============================================================================
# FONCTIONS DE GÉNÉRATION
# =============================================================================

def numpy_to_list(obj: Any) -> Any:
    """Convertir récursivement les arrays numpy en listes Python."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, dict):
        return {k: numpy_to_list(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [numpy_to_list(item) for item in obj]
    return obj


def creer_params_modele(preset_ville: dict, **overrides) -> ParametresModele:
    """Créer les paramètres du modèle à partir d'un preset de ville."""
    base = DEFAUTS_LONGUEUIL  # On part des défauts et on override

    # Calculer usage_base_lpcd si non fourni
    lpcd = overrides.get("lpcd", preset_ville.get("lpcd", base.lpcd))

    return ParametresModele(
        nb_menages=overrides.get("nb_menages", preset_ville.get("nb_menages", base.nb_menages)),
        taille_menage=overrides.get("taille_menage", preset_ville.get("taille_menage", base.taille_menage)),
        lpcd=lpcd,
        horizon_analyse=overrides.get("horizon", 20),
        taux_actualisation_pct=overrides.get("taux_actualisation", 3.0),
        reduction_comportement_pct=overrides.get("reduction_comportement", 8.0),
    )


def creer_params_compteur(preset_compteur: dict) -> ParametresCompteur:
    """Créer les paramètres du compteur à partir d'un preset."""
    return ParametresCompteur(
        type_compteur=preset_compteur["type"],
        cout_compteur=preset_compteur["cout_compteur"],
        heures_installation=preset_compteur["heures_installation"],
        taux_horaire_installation=preset_compteur["taux_horaire"],
        cout_reseau_par_compteur=preset_compteur["cout_reseau"],
    )


def generer_serie_alpha(persistance: ParametresPersistance, horizon: int) -> list:
    """Générer la série alpha(t) pour la courbe de persistance."""
    return [
        calculer_alpha_comportement(t, persistance)
        for t in range(1, horizon + 1)
    ]


def calculer_scenario(
    params: ParametresModele,
    compteur: ParametresCompteur,
    persistance: ParametresPersistance,
    fuites: ParametresFuites,
    mode: ModeCompte,
    valeur_eau: ParametresValeurEau,
) -> dict:
    """Calculer un scénario complet et retourner les résultats formatés."""

    result = executer_modele(
        params=params,
        compteur=compteur,
        persistance=persistance,
        params_fuites=fuites,
        mode_compte=mode,
        valeur_eau=valeur_eau,
    )

    return {
        # Métriques principales
        "van": float(result.van),
        "rbc": float(result.rbc),
        "payback": float(result.periode_recuperation) if result.periode_recuperation != float('inf') else None,
        "lcsw": float(result.lcsw),

        # Investissement et coûts
        "investissement_initial": float(result.investissement_initial),
        "va_benefices": float(result.va_benefices),
        "va_couts_exploitation": float(result.va_couts_exploitation),
        "va_couts_totaux": float(result.va_couts_totaux),

        # Économies par ménage
        "economie_totale_menage": float(result.economie_totale_menage),
        "economie_comportement_menage": float(result.economie_comportement_menage),
        "economie_fuite_menage": float(result.economie_fuite_menage),
        "usage_base_menage": float(result.usage_base_menage),

        # Coût par compteur
        "cout_par_compteur": float(result.cout_par_compteur_ajuste),

        # Séries temporelles
        "annees": result.annees.tolist(),
        "van_cumulative": result.van_cumulative.tolist(),
    }


def generer_scenarios_complets() -> dict:
    """
    Générer tous les scénarios précalculés pour le viewer HTML.

    Structure de sortie:
    {
        "metadata": {...},
        "presets": {
            "villes": {...},
            "compteurs": {...},
            "persistance": {...},
            "fuites": {...}
        },
        "scenarios": {
            "<ville>_<compteur>_<persistance>_<fuites>_<mode>": {...}
        },
        "courbes_alpha": {...},
        "sensibilite": {...}
    }
    """

    output = {
        "metadata": {
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "model_version": MODEL_VERSION,
            "description": "Scénarios précalculés pour l'analyse coûts-bénéfices des compteurs d'eau",
        },
        "presets": {
            "villes": {},
            "compteurs": {},
            "persistance": {},
            "fuites": {},
        },
        "scenarios": {},
        "courbes_alpha": {},
        "sensibilite": {},
    }

    # 1. Copier les métadonnées des presets
    for key, preset in PRESETS_VILLES.items():
        output["presets"]["villes"][key] = {
            "nom": preset["nom"],
            "nb_menages": preset["nb_menages"],
            "taille_menage": preset["taille_menage"],
            "lpcd": preset["lpcd"],
        }

    for key, preset in TYPES_COMPTEURS.items():
        output["presets"]["compteurs"][key] = {
            "nom": preset["nom"],
            "cout_compteur": preset["cout_compteur"],
            "heures_installation": preset["heures_installation"],
            "taux_horaire": preset["taux_horaire"],
            "cout_reseau": preset["cout_reseau"],
        }

    for key, scenario in SCENARIOS_PERSISTANCE.items():
        output["presets"]["persistance"][key] = {
            "nom": scenario["nom"],
            "description": scenario.get("description", ""),
        }

    for key, scenario in SCENARIOS_FUITES.items():
        output["presets"]["fuites"][key] = {
            "nom": scenario["nom"],
        }

    # 2. Générer les courbes alpha pour chaque scénario de persistance
    horizon = 20
    for pers_key, pers_scenario in SCENARIOS_PERSISTANCE.items():
        output["courbes_alpha"][pers_key] = generer_serie_alpha(
            pers_scenario["params"], horizon
        )

    # 3. Générer les scénarios principaux (combinatoire limitée pour taille raisonnable)
    # On calcule: ville × compteur × persistance × fuites × mode

    valeur_eau = VALEUR_EAU_QUEBEC
    total_scenarios = 0

    for ville_key, ville_preset in PRESETS_VILLES.items():
        for compteur_key, compteur_preset in TYPES_COMPTEURS.items():
            for pers_key, pers_scenario in SCENARIOS_PERSISTANCE.items():
                for fuites_key, fuites_scenario in SCENARIOS_FUITES.items():
                    for mode in [ModeCompte.ECONOMIQUE, ModeCompte.FINANCIER]:

                        # Créer les paramètres
                        params = creer_params_modele(ville_preset)
                        compteur = creer_params_compteur(compteur_preset)
                        persistance = pers_scenario["params"]
                        fuites = fuites_scenario["params"]

                        # Clé du scénario
                        mode_key = "eco" if mode == ModeCompte.ECONOMIQUE else "fin"
                        scenario_key = f"{ville_key}_{compteur_key}_{pers_key}_{fuites_key}_{mode_key}"

                        # Calculer
                        try:
                            result = calculer_scenario(
                                params, compteur, persistance, fuites, mode, valeur_eau
                            )
                            output["scenarios"][scenario_key] = result
                            total_scenarios += 1
                        except Exception as e:
                            print(f"Erreur pour {scenario_key}: {e}")

    print(f"Générés: {total_scenarios} scénarios")

    # 4. Analyse de sensibilité (variation ±10% des paramètres clés)
    # Scénario de base: Longueuil, AMI, réaliste, deux_stocks, économique
    base_params = creer_params_modele(PRESETS_VILLES["longueuil"])
    base_compteur = creer_params_compteur(TYPES_COMPTEURS["ami"])
    base_persistance = PERSISTANCE_REALISTE
    base_fuites = FUITES_QUEBEC_DEUX_STOCKS

    base_result = calculer_scenario(
        base_params, base_compteur, base_persistance, base_fuites,
        ModeCompte.ECONOMIQUE, valeur_eau
    )
    base_van = base_result["van"]

    sensibilite_params = [
        ("valeur_sociale", "Valeur eau", None),
        ("reduction_comportement", "Réduction comportement", None),
        ("lpcd", "LPCD", None),
        ("cout_compteur", "Coût compteur", None),
        ("nb_menages", "Nb ménages", None),
        ("prevalence_petites_fuites", "Prévalence petites fuites", None),
        ("prevalence_grandes_fuites", "Prévalence grandes fuites", None),
    ]

    output["sensibilite"] = {
        "base_van": base_van,
        "parametres": [],
    }

    for param_key, param_nom, special_handler in sensibilite_params:

        if param_key == "valeur_sociale":
            # Variation de la valeur sociale de l'eau
            base_val = valeur_eau.valeur_sociale_m3

            # -10%
            valeur_low = ParametresValeurEau(valeur_sociale_m3=base_val * 0.9)
            result_low = calculer_scenario(
                base_params, base_compteur, base_persistance, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_low
            )

            # +10%
            valeur_high = ParametresValeurEau(valeur_sociale_m3=base_val * 1.1)
            result_high = calculer_scenario(
                base_params, base_compteur, base_persistance, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_high
            )

        elif param_key == "reduction_comportement":
            # BUG FIX: Le modèle utilise persistance.alpha_initial, pas params.reduction_comportement_pct
            # On doit créer de nouvelles instances de ParametresPersistance avec alpha_initial modifié
            base_alpha = base_persistance.alpha_initial  # 0.08 = 8%

            # -10% de l'effet comportemental
            persistance_low = ParametresPersistance(
                mode=base_persistance.mode,
                alpha_initial=base_alpha * 0.9,
                alpha_plateau=base_persistance.alpha_plateau * 0.9,  # Proportionnel
                lambda_decay=base_persistance.lambda_decay,
                annees_fadeout=base_persistance.annees_fadeout,
                nom="Sensibilité -10%",
            )
            result_low = calculer_scenario(
                base_params, base_compteur, persistance_low, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

            # +10% de l'effet comportemental
            persistance_high = ParametresPersistance(
                mode=base_persistance.mode,
                alpha_initial=base_alpha * 1.1,
                alpha_plateau=base_persistance.alpha_plateau * 1.1,  # Proportionnel
                lambda_decay=base_persistance.lambda_decay,
                annees_fadeout=base_persistance.annees_fadeout,
                nom="Sensibilité +10%",
            )
            result_high = calculer_scenario(
                base_params, base_compteur, persistance_high, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

        elif param_key == "lpcd":
            base_val = base_params.lpcd

            params_low = creer_params_modele(PRESETS_VILLES["longueuil"], lpcd=base_val * 0.9)
            result_low = calculer_scenario(
                params_low, base_compteur, base_persistance, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

            params_high = creer_params_modele(PRESETS_VILLES["longueuil"], lpcd=base_val * 1.1)
            result_high = calculer_scenario(
                params_high, base_compteur, base_persistance, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

        elif param_key == "cout_compteur":
            base_val = base_compteur.cout_compteur

            compteur_low = ParametresCompteur(
                type_compteur=TypeCompteur.AMI,
                cout_compteur=base_val * 0.9,
                heures_installation=base_compteur.heures_installation,
                taux_horaire_installation=base_compteur.taux_horaire_installation,
                cout_reseau_par_compteur=base_compteur.cout_reseau_par_compteur,
            )
            result_low = calculer_scenario(
                base_params, compteur_low, base_persistance, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

            compteur_high = ParametresCompteur(
                type_compteur=TypeCompteur.AMI,
                cout_compteur=base_val * 1.1,
                heures_installation=base_compteur.heures_installation,
                taux_horaire_installation=base_compteur.taux_horaire_installation,
                cout_reseau_par_compteur=base_compteur.cout_reseau_par_compteur,
            )
            result_high = calculer_scenario(
                base_params, compteur_high, base_persistance, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

        elif param_key == "nb_menages":
            base_val = base_params.nb_menages

            params_low = creer_params_modele(PRESETS_VILLES["longueuil"], nb_menages=int(base_val * 0.9))
            result_low = calculer_scenario(
                params_low, base_compteur, base_persistance, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

            params_high = creer_params_modele(PRESETS_VILLES["longueuil"], nb_menages=int(base_val * 1.1))
            result_high = calculer_scenario(
                params_high, base_compteur, base_persistance, base_fuites,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

        elif param_key == "prevalence_petites_fuites":
            # Variation de la prévalence des petites fuites (any leaks: 30% base)
            base_val = base_fuites.part_menages_fuite_any_pct  # 30%

            # -10%
            fuites_low = ParametresFuites(
                utiliser_prevalence_differenciee=True,
                part_menages_fuite_pct=base_fuites.part_menages_fuite_pct,
                debit_fuite_m3_an=base_fuites.debit_fuite_m3_an,
                part_menages_fuite_any_pct=base_val * 0.9,  # Modifié
                part_menages_fuite_significative_pct=base_fuites.part_menages_fuite_significative_pct,
                debit_fuite_any_m3_an=base_fuites.debit_fuite_any_m3_an,
                debit_fuite_significative_m3_an=base_fuites.debit_fuite_significative_m3_an,
                cout_reparation_any=base_fuites.cout_reparation_any,
                cout_reparation_sig=base_fuites.cout_reparation_sig,
                part_fuites_persistantes_pct=base_fuites.part_fuites_persistantes_pct,
                facteur_duree_longue_traine=base_fuites.facteur_duree_longue_traine,
                taux_detection_pct=base_fuites.taux_detection_pct,
                taux_reparation_pct=base_fuites.taux_reparation_pct,
                inclure_cout_reparation=base_fuites.inclure_cout_reparation,
                mode_repartition=base_fuites.mode_repartition,
                nom="Sensibilité petites fuites -10%",
            )
            result_low = calculer_scenario(
                base_params, base_compteur, base_persistance, fuites_low,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

            # +10%
            fuites_high = ParametresFuites(
                utiliser_prevalence_differenciee=True,
                part_menages_fuite_pct=base_fuites.part_menages_fuite_pct,
                debit_fuite_m3_an=base_fuites.debit_fuite_m3_an,
                part_menages_fuite_any_pct=base_val * 1.1,  # Modifié
                part_menages_fuite_significative_pct=base_fuites.part_menages_fuite_significative_pct,
                debit_fuite_any_m3_an=base_fuites.debit_fuite_any_m3_an,
                debit_fuite_significative_m3_an=base_fuites.debit_fuite_significative_m3_an,
                cout_reparation_any=base_fuites.cout_reparation_any,
                cout_reparation_sig=base_fuites.cout_reparation_sig,
                part_fuites_persistantes_pct=base_fuites.part_fuites_persistantes_pct,
                facteur_duree_longue_traine=base_fuites.facteur_duree_longue_traine,
                taux_detection_pct=base_fuites.taux_detection_pct,
                taux_reparation_pct=base_fuites.taux_reparation_pct,
                inclure_cout_reparation=base_fuites.inclure_cout_reparation,
                mode_repartition=base_fuites.mode_repartition,
                nom="Sensibilité petites fuites +10%",
            )
            result_high = calculer_scenario(
                base_params, base_compteur, base_persistance, fuites_high,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

        elif param_key == "prevalence_grandes_fuites":
            # Variation de la prévalence des grandes fuites (significatives: 6% base)
            base_val = base_fuites.part_menages_fuite_significative_pct  # 6%

            # -10%
            fuites_low = ParametresFuites(
                utiliser_prevalence_differenciee=True,
                part_menages_fuite_pct=base_fuites.part_menages_fuite_pct,
                debit_fuite_m3_an=base_fuites.debit_fuite_m3_an,
                part_menages_fuite_any_pct=base_fuites.part_menages_fuite_any_pct,
                part_menages_fuite_significative_pct=base_val * 0.9,  # Modifié
                debit_fuite_any_m3_an=base_fuites.debit_fuite_any_m3_an,
                debit_fuite_significative_m3_an=base_fuites.debit_fuite_significative_m3_an,
                cout_reparation_any=base_fuites.cout_reparation_any,
                cout_reparation_sig=base_fuites.cout_reparation_sig,
                part_fuites_persistantes_pct=base_fuites.part_fuites_persistantes_pct,
                facteur_duree_longue_traine=base_fuites.facteur_duree_longue_traine,
                taux_detection_pct=base_fuites.taux_detection_pct,
                taux_reparation_pct=base_fuites.taux_reparation_pct,
                inclure_cout_reparation=base_fuites.inclure_cout_reparation,
                mode_repartition=base_fuites.mode_repartition,
                nom="Sensibilité grandes fuites -10%",
            )
            result_low = calculer_scenario(
                base_params, base_compteur, base_persistance, fuites_low,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

            # +10%
            fuites_high = ParametresFuites(
                utiliser_prevalence_differenciee=True,
                part_menages_fuite_pct=base_fuites.part_menages_fuite_pct,
                debit_fuite_m3_an=base_fuites.debit_fuite_m3_an,
                part_menages_fuite_any_pct=base_fuites.part_menages_fuite_any_pct,
                part_menages_fuite_significative_pct=base_val * 1.1,  # Modifié
                debit_fuite_any_m3_an=base_fuites.debit_fuite_any_m3_an,
                debit_fuite_significative_m3_an=base_fuites.debit_fuite_significative_m3_an,
                cout_reparation_any=base_fuites.cout_reparation_any,
                cout_reparation_sig=base_fuites.cout_reparation_sig,
                part_fuites_persistantes_pct=base_fuites.part_fuites_persistantes_pct,
                facteur_duree_longue_traine=base_fuites.facteur_duree_longue_traine,
                taux_detection_pct=base_fuites.taux_detection_pct,
                taux_reparation_pct=base_fuites.taux_reparation_pct,
                inclure_cout_reparation=base_fuites.inclure_cout_reparation,
                mode_repartition=base_fuites.mode_repartition,
                nom="Sensibilité grandes fuites +10%",
            )
            result_high = calculer_scenario(
                base_params, base_compteur, base_persistance, fuites_high,
                ModeCompte.ECONOMIQUE, valeur_eau
            )

        output["sensibilite"]["parametres"].append({
            "nom": param_nom,
            "cle": param_key,
            "impact_low": result_low["van"] - base_van,
            "impact_high": result_high["van"] - base_van,
            "van_low": result_low["van"],
            "van_high": result_high["van"],
        })

    # Trier par impact (range)
    output["sensibilite"]["parametres"].sort(
        key=lambda x: abs(x["impact_high"] - x["impact_low"]),
        reverse=True
    )

    return output


def exporter_json(output: dict, filepath: str) -> None:
    """Exporter les résultats en JSON."""
    # Convertir les numpy arrays
    output_clean = numpy_to_list(output)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_clean, f, ensure_ascii=False, indent=2)

    print(f"Exporté: {filepath}")

    # Statistiques
    size_mb = len(json.dumps(output_clean)) / 1024 / 1024
    print(f"Taille: {size_mb:.2f} MB")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GÉNÉRATION DES SCÉNARIOS PRÉCALCULÉS")
    print("=" * 60)
    print()

    output = generer_scenarios_complets()

    output_path = "/Users/enzo_simier/Desktop/Water/scenarios_output.json"
    exporter_json(output, output_path)

    print()
    print("=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    print(f"Scénarios générés: {len(output['scenarios'])}")
    print(f"Paramètres de sensibilité: {len(output['sensibilite']['parametres'])}")
    print(f"Fichier de sortie: {output_path}")
    print()
    print("Prochaine étape: ouvrir le viewer HTML avec ce fichier JSON")
