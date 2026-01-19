#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation des scénarios — Tests de non-régression

Ce script génère 10 scénarios canoniques avec les résultats attendus.
Utilisable pour:
1. Valider que le JSON exporté est cohérent avec le modèle Python
2. Annexe de mémoire: documentation des résultats de référence
3. Tests automatisés lors de modifications du modèle

Usage:
    python validation_scenarios.py

Auteur: Enzo Simier
Version: 1.0.0 (janvier 2026)
"""

import json
from dataclasses import dataclass
from typing import Optional

from analyse_compteurs_eau import (
    ParametresModele,
    ParametresCompteur,
    TypeCompteur,
    ModeCompte,
    ParametresValeurEau,
    executer_modele,
    DEFAUTS_LONGUEUIL,
    COMPTEUR_LONGUEUIL_AMI,
    PERSISTANCE_OPTIMISTE,
    PERSISTANCE_REALISTE,
    PERSISTANCE_PESSIMISTE,
    FUITES_SANS_COUT,
    FUITES_QUEBEC_DEUX_STOCKS,
    FUITES_CONTEXTE_QUEBEC,
    VALEUR_EAU_QUEBEC,
)


# =============================================================================
# DÉFINITION DES 10 SCÉNARIOS CANONIQUES
# =============================================================================

@dataclass
class ScenarioTest:
    """Définition d'un scénario de test."""
    nom: str
    description: str
    ville: str
    nb_menages: int
    taille_menage: float
    lpcd: int
    type_compteur: TypeCompteur
    persistance: str  # 'optimiste', 'realiste', 'pessimiste'
    fuites: str  # 'sans_cout', 'deux_stocks', 'quebec'
    mode: ModeCompte

    # Résultats attendus (seront calculés)
    van_attendue: Optional[float] = None
    rbc_attendu: Optional[float] = None
    payback_attendu: Optional[float] = None
    lcsw_attendu: Optional[float] = None


SCENARIOS_CANONIQUES = [
    # 1. Longueuil AMI réaliste deux-stocks économique (cas de base)
    ScenarioTest(
        nom="longueuil_ami_realiste_deuxstocks_eco",
        description="Cas de base Longueuil: AMI, persistance réaliste, deux-stocks, mode économique",
        ville="Longueuil",
        nb_menages=116258,
        taille_menage=2.18,
        lpcd=236,
        type_compteur=TypeCompteur.AMI,
        persistance="realiste",
        fuites="deux_stocks",
        mode=ModeCompte.ECONOMIQUE,
    ),

    # 2. Longueuil AMI réaliste deux-stocks financier (comparaison eco/fin)
    ScenarioTest(
        nom="longueuil_ami_realiste_deuxstocks_fin",
        description="Comparaison financière: même config que #1 mais mode financier",
        ville="Longueuil",
        nb_menages=116258,
        taille_menage=2.18,
        lpcd=236,
        type_compteur=TypeCompteur.AMI,
        persistance="realiste",
        fuites="deux_stocks",
        mode=ModeCompte.FINANCIER,
    ),

    # 3. Longueuil AMI optimiste (borne haute)
    ScenarioTest(
        nom="longueuil_ami_optimiste_deuxstocks_eco",
        description="Borne haute: persistance optimiste (effet constant)",
        ville="Longueuil",
        nb_menages=116258,
        taille_menage=2.18,
        lpcd=236,
        type_compteur=TypeCompteur.AMI,
        persistance="optimiste",
        fuites="deux_stocks",
        mode=ModeCompte.ECONOMIQUE,
    ),

    # 4. Longueuil AMI pessimiste (borne basse)
    ScenarioTest(
        nom="longueuil_ami_pessimiste_deuxstocks_eco",
        description="Borne basse: persistance pessimiste (fadeout 10 ans)",
        ville="Longueuil",
        nb_menages=116258,
        taille_menage=2.18,
        lpcd=236,
        type_compteur=TypeCompteur.AMI,
        persistance="pessimiste",
        fuites="deux_stocks",
        mode=ModeCompte.ECONOMIQUE,
    ),

    # 5. Longueuil Manuel réaliste (comparaison types compteurs)
    ScenarioTest(
        nom="longueuil_manuel_realiste_deuxstocks_eco",
        description="Comparaison compteurs: manuel vs AMI",
        ville="Longueuil",
        nb_menages=116258,
        taille_menage=2.18,
        lpcd=236,
        type_compteur=TypeCompteur.MANUEL,
        persistance="realiste",
        fuites="deux_stocks",
        mode=ModeCompte.ECONOMIQUE,
    ),

    # 6. Longueuil AMR réaliste (comparaison types compteurs)
    ScenarioTest(
        nom="longueuil_amr_realiste_deuxstocks_eco",
        description="Comparaison compteurs: AMR vs AMI",
        ville="Longueuil",
        nb_menages=116258,
        taille_menage=2.18,
        lpcd=236,
        type_compteur=TypeCompteur.AMR,
        persistance="realiste",
        fuites="deux_stocks",
        mode=ModeCompte.ECONOMIQUE,
    ),

    # 7. Montréal AMI réaliste (grande ville)
    ScenarioTest(
        nom="montreal_ami_realiste_deuxstocks_eco",
        description="Grande ville: Montréal avec LPCD élevé",
        ville="Montréal",
        nb_menages=750000,
        taille_menage=2.1,
        lpcd=332,
        type_compteur=TypeCompteur.AMI,
        persistance="realiste",
        fuites="deux_stocks",
        mode=ModeCompte.ECONOMIQUE,
    ),

    # 8. Longueuil AMI réaliste fuites standard (comparaison scénarios fuites)
    ScenarioTest(
        nom="longueuil_ami_realiste_standard_eco",
        description="Comparaison fuites: scénario standard (20%, 35 m³)",
        ville="Longueuil",
        nb_menages=116258,
        taille_menage=2.18,
        lpcd=236,
        type_compteur=TypeCompteur.AMI,
        persistance="realiste",
        fuites="standard",
        mode=ModeCompte.ECONOMIQUE,
    ),

    # 9. Longueuil AMI réaliste fuites Québec (comparaison scénarios fuites)
    ScenarioTest(
        nom="longueuil_ami_realiste_quebec_eco",
        description="Comparaison fuites: contexte Québec (35%, 35 m³)",
        ville="Longueuil",
        nb_menages=116258,
        taille_menage=2.18,
        lpcd=236,
        type_compteur=TypeCompteur.AMI,
        persistance="realiste",
        fuites="quebec",
        mode=ModeCompte.ECONOMIQUE,
    ),

    # 10. Winnipeg AMI réaliste (ville externe au Québec)
    ScenarioTest(
        nom="winnipeg_ami_realiste_deuxstocks_eco",
        description="Benchmark externe: Winnipeg (données publiques)",
        ville="Winnipeg",
        nb_menages=221000,
        taille_menage=2.3,
        lpcd=250,
        type_compteur=TypeCompteur.AMI,
        persistance="realiste",
        fuites="deux_stocks",
        mode=ModeCompte.ECONOMIQUE,
    ),
]


# =============================================================================
# FONCTIONS DE CALCUL
# =============================================================================

def get_persistance_params(nom: str):
    """Récupérer les paramètres de persistance."""
    mapping = {
        "optimiste": PERSISTANCE_OPTIMISTE,
        "realiste": PERSISTANCE_REALISTE,
        "pessimiste": PERSISTANCE_PESSIMISTE,
    }
    return mapping.get(nom, PERSISTANCE_REALISTE)


def get_fuites_params(nom: str):
    """Récupérer les paramètres de fuites."""
    mapping = {
        "sans_cout": FUITES_SANS_COUT,
        "deux_stocks": FUITES_QUEBEC_DEUX_STOCKS,
        "standard": FUITES_SANS_COUT,  # Standard = sans coût mais prévalence 20%
        "quebec": FUITES_CONTEXTE_QUEBEC,
    }
    return mapping.get(nom, FUITES_SANS_COUT)


def get_compteur_params(type_compteur: TypeCompteur) -> ParametresCompteur:
    """Créer les paramètres du compteur."""
    if type_compteur == TypeCompteur.AMI:
        return COMPTEUR_LONGUEUIL_AMI
    elif type_compteur == TypeCompteur.AMR:
        return ParametresCompteur(
            type_compteur=TypeCompteur.AMR,
            cout_compteur=150.0,
            heures_installation=3.0,
            taux_horaire_installation=125.0,
        )
    else:
        return ParametresCompteur(
            type_compteur=TypeCompteur.MANUEL,
            cout_compteur=75.0,
            heures_installation=3.0,
            taux_horaire_installation=125.0,
        )


def calculer_scenario(scenario: ScenarioTest) -> dict:
    """Calculer les résultats d'un scénario."""

    # Créer les paramètres du modèle
    params = ParametresModele(
        nb_menages=scenario.nb_menages,
        taille_menage=scenario.taille_menage,
        lpcd=scenario.lpcd,
        horizon_analyse=20,
        taux_actualisation_pct=3.0,
        reduction_comportement_pct=8.0,
    )

    compteur = get_compteur_params(scenario.type_compteur)
    persistance = get_persistance_params(scenario.persistance)
    fuites = get_fuites_params(scenario.fuites)

    # Exécuter le modèle
    result = executer_modele(
        params=params,
        compteur=compteur,
        persistance=persistance,
        params_fuites=fuites,
        mode_compte=scenario.mode,
        valeur_eau=VALEUR_EAU_QUEBEC,
    )

    return {
        "van": float(result.van),
        "rbc": float(result.rbc),
        "payback": float(result.periode_recuperation) if result.periode_recuperation != float('inf') else None,
        "lcsw": float(result.lcsw),
        "investissement": float(result.investissement_initial),
        "economie_totale_menage": float(result.economie_totale_menage),
        "economie_comportement_menage": float(result.economie_comportement_menage),
        "economie_fuite_menage": float(result.economie_fuite_menage),
    }


# =============================================================================
# VALIDATION
# =============================================================================

def valider_contre_json(json_path: str = "scenarios_output.json") -> dict:
    """
    Valider les résultats du JSON contre les calculs directs.

    Retourne un rapport de validation.
    """

    # Charger le JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rapport = {
        "total_tests": len(SCENARIOS_CANONIQUES),
        "passes": 0,
        "echecs": 0,
        "details": [],
    }

    tolerance = 0.01  # 1% de tolérance

    for scenario in SCENARIOS_CANONIQUES:
        # Calculer directement
        result_direct = calculer_scenario(scenario)

        # Construire la clé JSON
        type_str = scenario.type_compteur.value
        mode_str = "eco" if scenario.mode == ModeCompte.ECONOMIQUE else "fin"
        ville_str = scenario.ville.lower().replace(" ", "_").replace("(ville)", "").strip()
        if ville_str == "québec":
            ville_str = "quebec"

        fuites_str = scenario.fuites
        if fuites_str == "standard":
            fuites_str = "standard"
        elif fuites_str == "quebec":
            fuites_str = "quebec"

        json_key = f"{ville_str}_{type_str}_{scenario.persistance}_{fuites_str}_{mode_str}"

        # Récupérer du JSON
        result_json = data["scenarios"].get(json_key)

        if result_json is None:
            rapport["echecs"] += 1
            rapport["details"].append({
                "scenario": scenario.nom,
                "status": "ECHEC",
                "raison": f"Clé '{json_key}' non trouvée dans le JSON",
            })
            continue

        # Comparer
        ecarts = []
        for metric in ["van", "rbc", "lcsw"]:
            val_direct = result_direct[metric]
            val_json = result_json[metric]

            if val_direct != 0:
                ecart_pct = abs(val_direct - val_json) / abs(val_direct) * 100
            else:
                ecart_pct = 0 if val_json == 0 else 100

            if ecart_pct > tolerance * 100:
                ecarts.append(f"{metric}: {ecart_pct:.2f}% (direct={val_direct:.2f}, json={val_json:.2f})")

        if ecarts:
            rapport["echecs"] += 1
            rapport["details"].append({
                "scenario": scenario.nom,
                "status": "ECHEC",
                "raison": "; ".join(ecarts),
            })
        else:
            rapport["passes"] += 1
            rapport["details"].append({
                "scenario": scenario.nom,
                "status": "OK",
                "van": result_direct["van"],
                "rbc": result_direct["rbc"],
            })

    return rapport


# =============================================================================
# GÉNÉRATION DU RAPPORT POUR MÉMOIRE
# =============================================================================

def generer_rapport_memoire():
    """
    Génère un rapport formaté pour inclusion dans le mémoire.
    """

    print("=" * 80)
    print("RAPPORT DE VALIDATION — SCÉNARIOS CANONIQUES")
    print("Modèle Python v3.10 — Analyse Coûts-Bénéfices Compteurs d'Eau")
    print("=" * 80)
    print()

    # Tableau des résultats
    print("TABLEAU A1 — Résultats des 10 scénarios canoniques")
    print("-" * 80)
    print(f"{'#':<3} {'Scénario':<50} {'VAN (M$)':<12} {'RBC':<8} {'Payback':<8}")
    print("-" * 80)

    resultats = []
    for i, scenario in enumerate(SCENARIOS_CANONIQUES, 1):
        result = calculer_scenario(scenario)
        resultats.append((scenario, result))

        van_str = f"{result['van']/1e6:.1f}"
        rbc_str = f"{result['rbc']:.2f}"
        payback_str = f"{result['payback']:.1f}" if result['payback'] else ">20"

        print(f"{i:<3} {scenario.nom:<50} {van_str:<12} {rbc_str:<8} {payback_str:<8}")

    print("-" * 80)
    print()

    # Statistiques
    vans = [r[1]["van"] for r in resultats]
    rbcs = [r[1]["rbc"] for r in resultats]

    print("STATISTIQUES DESCRIPTIVES")
    print(f"  VAN moyenne:     {sum(vans)/len(vans)/1e6:.1f} M$")
    print(f"  VAN min:         {min(vans)/1e6:.1f} M$")
    print(f"  VAN max:         {max(vans)/1e6:.1f} M$")
    print(f"  RBC moyen:       {sum(rbcs)/len(rbcs):.2f}")
    print()

    # Validation contre JSON
    print("VALIDATION CONTRE JSON EXPORTÉ")
    print("-" * 40)
    try:
        rapport = valider_contre_json()
        print(f"  Tests passés:    {rapport['passes']}/{rapport['total_tests']}")
        print(f"  Tests échoués:   {rapport['echecs']}/{rapport['total_tests']}")

        if rapport["echecs"] > 0:
            print("\n  Détails des échecs:")
            for detail in rapport["details"]:
                if detail["status"] == "ECHEC":
                    print(f"    - {detail['scenario']}: {detail['raison']}")
    except FileNotFoundError:
        print("  JSON non trouvé — exécuter d'abord: python generate_scenarios_json.py")

    print()
    print("=" * 80)

    return resultats


def exporter_resultats_json():
    """Exporte les résultats dans un fichier JSON pour référence."""

    resultats = {}
    for scenario in SCENARIOS_CANONIQUES:
        result = calculer_scenario(scenario)
        resultats[scenario.nom] = {
            "description": scenario.description,
            "ville": scenario.ville,
            "type_compteur": scenario.type_compteur.value,
            "persistance": scenario.persistance,
            "fuites": scenario.fuites,
            "mode": scenario.mode.value,
            "resultats": result,
        }

    output_path = "/Users/enzo_simier/Desktop/Water/validation_resultats.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    print(f"Résultats exportés: {output_path}")
    return output_path


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    resultats = generer_rapport_memoire()
    print()
    exporter_resultats_json()
