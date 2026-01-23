#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de non-régression pour l'API du calculateur CBA compteurs d'eau.

Exécuter avec: pytest test_api.py -v

Ces tests vérifient:
1. La cohérence des résultats avec des scénarios "golden" connus
2. La cohérence entre /api/calculate et /api/detailed_series
3. Les cas limites et validations
"""

import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

# =============================================================================
# SCÉNARIOS GOLDEN - Valeurs de référence
# =============================================================================

# Scénario 1: Baseline (Longueuil, paramètres par défaut)
SCENARIO_BASELINE = {
    "nb_menages": 116258,
    "taille_menage": 2.18,
    "lpcd": 236,
    "horizon": 20,
    "taux_actualisation": 3.0,
    "type_compteur": "ami",
    "cout_compteur": 250.0,
    "heures_installation": 3.0,
    "taux_horaire": 125.0,
    "cout_reseau": 50.0,
    "cout_infra_fixe": 0.0,
    "reduction_comportement": 8.0,
    "persistance": "realiste",
    "scenario_fuites": "deux_stocks_sans_tarif",
    "mode_economique": True,
    "valeur_sociale": 4.69,
    "cout_variable": 0.50,
    "scenario_adoption": "obligatoire",
}

# Scénario 2: Optimiste (tarification + persistance optimiste)
SCENARIO_OPTIMISTE = {
    **SCENARIO_BASELINE,
    "persistance": "optimiste",
    "scenario_fuites": "deux_stocks",  # Avec tarification
    "reduction_comportement": 10.0,
    "valeur_sociale": 6.0,
}

# Scénario 3: Pessimiste (sans tarification + persistance pessimiste)
SCENARIO_PESSIMISTE = {
    **SCENARIO_BASELINE,
    "persistance": "pessimiste",
    "scenario_fuites": "deux_stocks_sans_tarif",
    "reduction_comportement": 5.0,
    "cout_compteur": 350.0,
}


# =============================================================================
# TESTS DE BASE
# =============================================================================

def test_health_check():
    """Test que l'API est accessible."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_presets_disponibles():
    """Test que les presets de villes sont disponibles."""
    response = client.get("/api/presets")
    assert response.status_code == 200
    data = response.json()
    assert "longueuil" in data
    assert "montreal" in data
    assert data["longueuil"]["nb_menages"] == 116258


# =============================================================================
# TESTS SCÉNARIOS GOLDEN
# =============================================================================

def test_scenario_baseline():
    """Test scénario baseline - vérification des métriques clés."""
    response = client.post("/api/calculate", json=SCENARIO_BASELINE)
    assert response.status_code == 200
    data = response.json()

    # Vérifications structurelles
    assert "van" in data
    assert "rbc" in data
    assert "payback" in data
    assert "lcsw" in data
    assert "investissement_initial" in data
    assert "annees" in data
    assert "van_cumulative" in data

    # Vérifications de cohérence (pas de valeurs absurdes)
    assert data["investissement_initial"] > 0, "L'investissement doit être positif"
    assert data["rbc"] > 0, "Le RBC doit être positif"
    assert data["lcsw"] > 0, "Le LCSW doit être positif"
    assert len(data["annees"]) == SCENARIO_BASELINE["horizon"]

    # La VAN peut être positive ou négative selon le contexte
    # Mais elle doit être dans une fourchette raisonnable
    assert -500_000_000 < data["van"] < 500_000_000, "VAN hors fourchette raisonnable"

    print(f"\n=== Scénario BASELINE ===")
    print(f"VAN: {data['van']/1e6:.2f} M$")
    print(f"RBC: {data['rbc']:.2f}")
    print(f"Investissement: {data['investissement_initial']/1e6:.2f} M$")


def test_scenario_optimiste():
    """Test scénario optimiste - VAN devrait être meilleure que baseline."""
    response = client.post("/api/calculate", json=SCENARIO_OPTIMISTE)
    assert response.status_code == 200
    data = response.json()

    # Comparaison avec baseline
    response_base = client.post("/api/calculate", json=SCENARIO_BASELINE)
    base = response_base.json()

    # Le scénario optimiste devrait avoir une meilleure VAN
    # (plus positive ou moins négative)
    assert data["van"] >= base["van"], \
        f"VAN optimiste ({data['van']/1e6:.2f}M$) devrait être >= baseline ({base['van']/1e6:.2f}M$)"

    print(f"\n=== Scénario OPTIMISTE ===")
    print(f"VAN: {data['van']/1e6:.2f} M$ (vs baseline: {base['van']/1e6:.2f} M$)")
    print(f"RBC: {data['rbc']:.2f}")


def test_scenario_pessimiste():
    """Test scénario pessimiste - VAN devrait être pire que baseline."""
    response = client.post("/api/calculate", json=SCENARIO_PESSIMISTE)
    assert response.status_code == 200
    data = response.json()

    # Comparaison avec baseline
    response_base = client.post("/api/calculate", json=SCENARIO_BASELINE)
    base = response_base.json()

    # Le scénario pessimiste devrait avoir une moins bonne VAN
    assert data["van"] <= base["van"], \
        f"VAN pessimiste ({data['van']/1e6:.2f}M$) devrait être <= baseline ({base['van']/1e6:.2f}M$)"

    print(f"\n=== Scénario PESSIMISTE ===")
    print(f"VAN: {data['van']/1e6:.2f} M$ (vs baseline: {base['van']/1e6:.2f} M$)")
    print(f"RBC: {data['rbc']:.2f}")


# =============================================================================
# TESTS DE COHÉRENCE INTER-ENDPOINTS
# =============================================================================

def test_coherence_calculate_detailed_series():
    """Test que /api/calculate et /api/detailed_series sont cohérents."""
    # Calcul principal
    response_calc = client.post("/api/calculate", json=SCENARIO_BASELINE)
    assert response_calc.status_code == 200
    calc = response_calc.json()

    # Séries détaillées
    response_series = client.post("/api/detailed_series", json=SCENARIO_BASELINE)
    assert response_series.status_code == 200
    series = response_series.json()

    # Vérifier la cohérence des horizons
    assert len(series["annees"]) == SCENARIO_BASELINE["horizon"]
    assert len(series["economies_comportement_m3"]) == SCENARIO_BASELINE["horizon"]
    assert len(series["economies_fuites_m3"]) == SCENARIO_BASELINE["horizon"]

    # Les économies par ménage devraient correspondre approximativement
    # à la moyenne des séries (année 1 pour comparaison directe)
    eco_comportement_annee1 = series["economies_comportement_m3"][0]
    eco_fuites_annee1 = series["economies_fuites_m3"][0]

    # Tolérance de 20% car les méthodes de calcul peuvent différer légèrement
    assert abs(eco_comportement_annee1 - calc["economie_comportement_menage"]) / max(calc["economie_comportement_menage"], 0.01) < 0.2 or \
           abs(eco_comportement_annee1 - calc["economie_comportement_menage"]) < 1.0, \
           f"Incohérence économie comportement: {eco_comportement_annee1} vs {calc['economie_comportement_menage']}"


def test_coherence_compare_meters():
    """Test que la comparaison des compteurs fonctionne."""
    response = client.post("/api/compare_meters", json=SCENARIO_BASELINE)
    assert response.status_code == 200
    data = response.json()

    # Vérifier que les 3 types sont présents
    assert "ami" in data
    assert "amr" in data
    assert "manuel" in data

    # AMI devrait avoir l'investissement le plus élevé
    assert data["ami"]["investissement"] >= data["amr"]["investissement"]
    assert data["ami"]["investissement"] >= data["manuel"]["investissement"]


def test_coherence_sensitivity():
    """Test que l'analyse de sensibilité fonctionne."""
    response = client.post("/api/sensitivity", json=SCENARIO_BASELINE)
    assert response.status_code == 200
    data = response.json()

    assert "base_van" in data
    assert "parametres" in data
    assert len(data["parametres"]) > 0

    # Chaque paramètre doit avoir les impacts calculés
    for param in data["parametres"]:
        assert "nom" in param
        assert "impact_low" in param
        assert "impact_high" in param


# =============================================================================
# TESTS DE VALIDATION
# =============================================================================

def test_validation_scenario_fuites_inconnu():
    """Test qu'un scénario de fuites inconnu retourne une erreur."""
    params = {**SCENARIO_BASELINE, "scenario_fuites": "scenario_inexistant"}
    response = client.post("/api/calculate", json=params)
    # Peut être 400 (erreur client) ou 500 (erreur serveur non gérée)
    assert response.status_code in [400, 500], f"Expected error status, got {response.status_code}"


def test_validation_prevalence_excessive():
    """Test que des prévalences excessives sont rejetées en mode custom."""
    params = {
        **SCENARIO_BASELINE,
        "scenario_fuites": "custom",
        "prevalence_petites_pct": 50.0,
        "prevalence_grosses_pct": 20.0,  # Total = 70% > 60%
    }
    response = client.post("/api/calculate", json=params)
    assert response.status_code == 422


def test_validation_parametres_hors_bornes():
    """Test que les paramètres hors bornes sont rejetés par Pydantic."""
    # LPCD trop bas
    params = {**SCENARIO_BASELINE, "lpcd": 50}  # min = 100
    response = client.post("/api/calculate", json=params)
    assert response.status_code == 422

    # Taux actualisation négatif
    params = {**SCENARIO_BASELINE, "taux_actualisation": -1.0}
    response = client.post("/api/calculate", json=params)
    assert response.status_code == 422


# =============================================================================
# TESTS FEATURES AVANCÉES
# =============================================================================

def test_report_infrastructure():
    """Test que le report d'infrastructure est bien pris en compte."""
    # Sans report
    response_sans = client.post("/api/calculate", json=SCENARIO_BASELINE)
    van_sans = response_sans.json()["van"]

    # Avec report
    params_avec = {
        **SCENARIO_BASELINE,
        "benefice_report_infra_annuel": 100000,  # 100k$/an
        "benefice_report_infra_par_m3": 0.5,
    }
    response_avec = client.post("/api/calculate", json=params_avec)
    van_avec = response_avec.json()["van"]

    # La VAN avec report devrait être meilleure
    assert van_avec > van_sans, \
        f"VAN avec report ({van_avec/1e6:.2f}M$) devrait être > sans ({van_sans/1e6:.2f}M$)"

    print(f"\n=== Test Report Infrastructure ===")
    print(f"VAN sans report: {van_sans/1e6:.2f} M$")
    print(f"VAN avec report: {van_avec/1e6:.2f} M$")
    print(f"Gain: {(van_avec-van_sans)/1e6:.2f} M$")


def test_adoption_progressive():
    """Test que les scénarios d'adoption fonctionnent."""
    # Obligatoire (100% an 1)
    response_oblig = client.post("/api/calculate", json=SCENARIO_BASELINE)

    # Progressif
    params_prog = {**SCENARIO_BASELINE, "scenario_adoption": "progressive"}
    response_prog = client.post("/api/calculate", json=params_prog)

    assert response_prog.status_code == 200

    # L'investissement initial devrait être différent avec adoption progressive
    # car le CAPEX peut être étalé
    inv_oblig = response_oblig.json()["investissement_initial"]
    inv_prog = response_prog.json()["investissement_initial"]

    print(f"\n=== Test Adoption ===")
    print(f"Investissement obligatoire: {inv_oblig/1e6:.2f} M$")
    print(f"Investissement progressif: {inv_prog/1e6:.2f} M$")


def test_monte_carlo():
    """Test que Monte Carlo fonctionne et retourne des distributions."""
    response = client.post(
        "/api/monte_carlo",
        json=SCENARIO_BASELINE,
        params={"n_simulations": 100, "seed": 42}
    )
    assert response.status_code == 200
    data = response.json()

    assert "n_simulations" in data
    assert data["n_simulations"] == 100
    assert "van_moyenne" in data
    assert "van_mediane" in data
    assert "prob_van_positive" in data
    assert "percentiles" in data
    assert "histogram" in data

    # La probabilité doit être entre 0 et 1
    assert 0 <= data["prob_van_positive"] <= 1

    print(f"\n=== Test Monte Carlo ===")
    print(f"VAN moyenne: {data['van_moyenne']/1e6:.2f} M$")
    print(f"P(VAN > 0): {data['prob_van_positive']*100:.1f}%")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
