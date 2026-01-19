#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API FastAPI pour le modèle CBA Compteurs d'Eau

Expose le modèle Python via des endpoints REST.
Le frontend appelle ces endpoints pour calculer en temps réel.

Usage local:
    uvicorn api:app --reload --port 8000

Usage production:
    uvicorn api:app --host 0.0.0.0 --port $PORT
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import numpy as np

# Import du modèle
from analyse_compteurs_eau import (
    ParametresModele,
    ParametresCompteur,
    TypeCompteur,
    ModeCompte,
    ParametresValeurEau,
    ParametresPersistance,
    ModePersistance,
    ParametresFuites,
    ModeRepartitionCouts,
    executer_modele,
    calculer_alpha_comportement,
    PERSISTANCE_OPTIMISTE,
    PERSISTANCE_REALISTE,
    PERSISTANCE_PESSIMISTE,
    FUITES_SANS_COUT,
    FUITES_QUEBEC_DEUX_STOCKS,
    VALEUR_EAU_QUEBEC,
)

# =============================================================================
# APPLICATION FASTAPI
# =============================================================================

app = FastAPI(
    title="API Compteurs d'Eau Québec",
    description="Analyse coûts-bénéfices des compteurs d'eau intelligents",
    version="3.10.0",
)

# CORS pour permettre les appels depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, restreindre aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# MODÈLES PYDANTIC (validation des entrées)
# =============================================================================

class CalculRequest(BaseModel):
    """Paramètres pour le calcul principal."""

    # Paramètres de la ville
    nb_menages: int = Field(116258, ge=1000, le=2000000, description="Nombre de ménages")
    taille_menage: float = Field(2.18, ge=1.0, le=5.0, description="Personnes par ménage")
    lpcd: int = Field(236, ge=100, le=500, description="Litres par personne par jour")

    # Paramètres financiers
    horizon: int = Field(20, ge=5, le=40, description="Horizon d'analyse (années)")
    taux_actualisation: float = Field(3.0, ge=0.5, le=10.0, description="Taux d'actualisation (%)")

    # Paramètres du compteur
    type_compteur: str = Field("ami", description="Type: ami, amr, manuel")
    cout_compteur: float = Field(250.0, ge=50, le=800, description="Coût du compteur ($)")
    heures_installation: float = Field(3.0, ge=0.5, le=8.0, description="Heures d'installation")
    taux_horaire: float = Field(125.0, ge=50, le=250, description="Taux horaire installation ($/h)")
    cout_reseau: float = Field(50.0, ge=0, le=300, description="Coût réseau par compteur ($)")

    # Paramètres comportementaux
    reduction_comportement: float = Field(8.0, ge=0, le=20, description="Réduction comportementale (%)")
    persistance: str = Field("realiste", description="Scénario: optimiste, realiste, pessimiste, ultra")

    # Paramètres fuites
    scenario_fuites: str = Field("deux_stocks", description="Scénario: standard, quebec, deux_stocks")

    # Mode d'analyse
    mode_economique: bool = Field(True, description="True=économique, False=financier")
    valeur_sociale: float = Field(4.69, ge=0.5, le=15.0, description="Valeur sociale eau ($/m³)")
    cout_variable: float = Field(0.50, ge=0.1, le=3.0, description="Coût variable eau ($/m³)")


class CalculResponse(BaseModel):
    """Résultats du calcul."""

    # Métriques principales
    van: float
    rbc: float
    payback: Optional[float]
    lcsw: float

    # Investissement et coûts
    investissement_initial: float
    va_benefices: float
    va_couts_exploitation: float
    va_couts_totaux: float

    # Économies par ménage
    economie_totale_menage: float
    economie_comportement_menage: float
    economie_fuite_menage: float
    usage_base_menage: float

    # Coût par compteur
    cout_par_compteur: float

    # Séries temporelles
    annees: List[int]
    van_cumulative: List[float]
    serie_alpha: List[float]

    # Recommandation
    viable: bool
    recommandation: str


class SensitivityResponse(BaseModel):
    """Résultats de l'analyse de sensibilité."""

    base_van: float
    parametres: List[dict]


class PresetResponse(BaseModel):
    """Preset d'une ville."""

    nom: str
    nb_menages: int
    taille_menage: float
    lpcd: int


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_persistance(nom: str, alpha_initial: float) -> ParametresPersistance:
    """Créer les paramètres de persistance selon le scénario."""

    if nom == "optimiste":
        return ParametresPersistance(
            mode=ModePersistance.CONSTANT,
            alpha_initial=alpha_initial / 100,
            alpha_plateau=alpha_initial / 100,
            nom="Optimiste",
        )
    elif nom == "realiste":
        return ParametresPersistance(
            mode=ModePersistance.EXPONENTIEL_PLATEAU,
            alpha_initial=alpha_initial / 100,
            alpha_plateau=0.025,
            lambda_decay=0.15,
            nom="Réaliste",
        )
    elif nom == "pessimiste":
        return ParametresPersistance(
            mode=ModePersistance.FADEOUT_LINEAIRE,
            alpha_initial=alpha_initial / 100,
            alpha_plateau=0.0,
            annees_fadeout=10,
            nom="Pessimiste",
        )
    else:  # ultra
        return ParametresPersistance(
            mode=ModePersistance.CONSTANT,
            alpha_initial=0.0,
            alpha_plateau=0.0,
            nom="Ultra-pessimiste",
        )


def get_fuites(nom: str) -> ParametresFuites:
    """Récupérer les paramètres de fuites selon le scénario."""

    if nom == "standard":
        return ParametresFuites(
            part_menages_fuite_pct=20.0,
            debit_fuite_m3_an=35.0,
            taux_reparation_pct=85.0,
            mode_repartition=ModeRepartitionCouts.SANS_COUT,
            utiliser_prevalence_differenciee=False,
        )
    elif nom == "quebec":
        return ParametresFuites(
            part_menages_fuite_pct=35.0,
            debit_fuite_m3_an=35.0,
            taux_reparation_pct=85.0,
            mode_repartition=ModeRepartitionCouts.SANS_COUT,
            utiliser_prevalence_differenciee=False,
        )
    else:  # deux_stocks
        return FUITES_QUEBEC_DEUX_STOCKS


def get_compteur(req: CalculRequest) -> ParametresCompteur:
    """Créer les paramètres du compteur."""

    type_map = {
        "ami": TypeCompteur.AMI,
        "amr": TypeCompteur.AMR,
        "manuel": TypeCompteur.MANUEL,
    }

    return ParametresCompteur(
        type_compteur=type_map.get(req.type_compteur, TypeCompteur.AMI),
        cout_compteur=req.cout_compteur,
        heures_installation=req.heures_installation,
        taux_horaire_installation=req.taux_horaire,
        cout_reseau_par_compteur=req.cout_reseau if req.type_compteur == "ami" else 0,
    )


def numpy_to_python(obj):
    """Convertir les types numpy en types Python natifs."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, dict):
        return {k: numpy_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [numpy_to_python(item) for item in obj]
    return obj


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Servir le frontend."""
    return FileResponse("index.html")


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "3.10.0"}


@app.post("/api/calculate", response_model=CalculResponse)
async def calculate(req: CalculRequest):
    """
    Calcul principal — appelé à chaque changement de slider.

    Reçoit tous les paramètres, appelle le modèle Python,
    retourne les résultats formatés pour le frontend.
    """

    try:
        # Créer les paramètres du modèle
        params = ParametresModele(
            nb_menages=req.nb_menages,
            taille_menage=req.taille_menage,
            lpcd=req.lpcd,
            horizon_analyse=req.horizon,
            taux_actualisation_pct=req.taux_actualisation,
            reduction_comportement_pct=req.reduction_comportement,
        )

        # Créer les autres paramètres
        compteur = get_compteur(req)
        persistance = get_persistance(req.persistance, req.reduction_comportement)
        fuites = get_fuites(req.scenario_fuites)

        # Mode d'analyse
        mode = ModeCompte.ECONOMIQUE if req.mode_economique else ModeCompte.FINANCIER
        valeur_eau = ParametresValeurEau(
            valeur_sociale_m3=req.valeur_sociale,
            cout_variable_m3=req.cout_variable,
        )

        # Exécuter le modèle
        result = executer_modele(
            params=params,
            compteur=compteur,
            persistance=persistance,
            params_fuites=fuites,
            mode_compte=mode,
            valeur_eau=valeur_eau,
        )

        # Générer la série alpha
        serie_alpha = [
            calculer_alpha_comportement(t, persistance) * 100
            for t in range(1, req.horizon + 1)
        ]

        # Déterminer la viabilité et recommandation
        viable = result.van > 0 and result.rbc > 1
        if viable:
            recommandation = f"PROJET VIABLE — VAN positive de {result.van/1e6:.1f} M$ sur {req.horizon} ans"
        elif result.van > 0:
            recommandation = f"PROJET MARGINAL — VAN positive mais RBC < 1"
        else:
            recommandation = f"PROJET NON RENTABLE — VAN négative de {result.van/1e6:.1f} M$"

        # Retourner les résultats
        return CalculResponse(
            van=float(result.van),
            rbc=float(result.rbc),
            payback=float(result.periode_recuperation) if result.periode_recuperation != float('inf') else None,
            lcsw=float(result.lcsw),
            investissement_initial=float(result.investissement_initial),
            va_benefices=float(result.va_benefices),
            va_couts_exploitation=float(result.va_couts_exploitation),
            va_couts_totaux=float(result.va_couts_totaux),
            economie_totale_menage=float(result.economie_totale_menage),
            economie_comportement_menage=float(result.economie_comportement_menage),
            economie_fuite_menage=float(result.economie_fuite_menage),
            usage_base_menage=float(result.usage_base_menage),
            cout_par_compteur=float(result.cout_par_compteur_ajuste),
            annees=list(result.annees.astype(int)),
            van_cumulative=list(result.van_cumulative),
            serie_alpha=serie_alpha,
            viable=viable,
            recommandation=recommandation,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sensitivity", response_model=SensitivityResponse)
async def sensitivity(req: CalculRequest):
    """
    Analyse de sensibilité — variation ±10% des paramètres clés.

    Retourne l'impact de chaque paramètre sur la VAN.
    """

    try:
        # Calcul de base
        base_response = await calculate(req)
        base_van = base_response.van

        # Paramètres à varier
        params_to_vary = [
            ("valeur_sociale", "Valeur eau", req.valeur_sociale),
            ("lpcd", "LPCD", req.lpcd),
            ("reduction_comportement", "Réduction comportement", req.reduction_comportement),
            ("cout_compteur", "Coût compteur", req.cout_compteur),
            ("nb_menages", "Nb ménages", req.nb_menages),
        ]

        results = []

        for param_key, param_nom, base_val in params_to_vary:
            # -10%
            req_low = req.model_copy()
            setattr(req_low, param_key, base_val * 0.9 if param_key != "nb_menages" else int(base_val * 0.9))
            result_low = await calculate(req_low)

            # +10%
            req_high = req.model_copy()
            setattr(req_high, param_key, base_val * 1.1 if param_key != "nb_menages" else int(base_val * 1.1))
            result_high = await calculate(req_high)

            results.append({
                "nom": param_nom,
                "cle": param_key,
                "impact_low": result_low.van - base_van,
                "impact_high": result_high.van - base_van,
                "van_low": result_low.van,
                "van_high": result_high.van,
            })

        # Trier par impact
        results.sort(key=lambda x: abs(x["impact_high"] - x["impact_low"]), reverse=True)

        return SensitivityResponse(
            base_van=base_van,
            parametres=results,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/presets")
async def get_presets():
    """Retourner les presets des villes."""

    return {
        "longueuil": PresetResponse(
            nom="Longueuil",
            nb_menages=116258,
            taille_menage=2.18,
            lpcd=236,
        ),
        "montreal": PresetResponse(
            nom="Montréal",
            nb_menages=750000,
            taille_menage=2.1,
            lpcd=332,
        ),
        "quebec": PresetResponse(
            nom="Québec (ville)",
            nb_menages=180000,
            taille_menage=2.15,
            lpcd=280,
        ),
        "winnipeg": PresetResponse(
            nom="Winnipeg",
            nb_menages=221000,
            taille_menage=2.3,
            lpcd=250,
        ),
    }


@app.post("/api/compare_meters")
async def compare_meters(req: CalculRequest):
    """Comparer les trois types de compteurs."""

    results = {}

    for meter_type in ["ami", "amr", "manuel"]:
        req_copy = req.model_copy()
        req_copy.type_compteur = meter_type

        # Ajuster les coûts selon le type
        if meter_type == "amr":
            req_copy.cout_compteur = 150.0
            req_copy.cout_reseau = 0.0
        elif meter_type == "manuel":
            req_copy.cout_compteur = 75.0
            req_copy.cout_reseau = 0.0

        result = await calculate(req_copy)
        results[meter_type] = {
            "van": result.van,
            "rbc": result.rbc,
            "payback": result.payback,
            "investissement": result.investissement_initial,
        }

    return results


@app.post("/api/compare_persistence")
async def compare_persistence(req: CalculRequest):
    """Comparer les scénarios de persistance."""

    results = {}

    for pers in ["optimiste", "realiste", "pessimiste"]:
        req_copy = req.model_copy()
        req_copy.persistance = pers
        result = await calculate(req_copy)
        results[pers] = {
            "van": result.van,
            "rbc": result.rbc,
            "van_cumulative": result.van_cumulative,
            "serie_alpha": result.serie_alpha,
        }

    return results


# =============================================================================
# SERVIR LES FICHIERS STATIQUES
# =============================================================================

# Si index.html existe dans le même dossier, le servir
import os
if os.path.exists("index.html"):
    @app.get("/{path:path}")
    async def serve_static(path: str):
        if path == "" or path == "index.html":
            return FileResponse("index.html")
        elif os.path.exists(path):
            return FileResponse(path)
        else:
            return FileResponse("index.html")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
