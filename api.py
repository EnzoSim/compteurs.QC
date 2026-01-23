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
from dataclasses import replace
import numpy as np
import math
import os

# Import du modèle
from analyse_compteurs_eau import (
    __version__ as MODEL_VERSION,
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
    STRATEGIES_ADOPTION,
    ADOPTION_OBLIGATOIRE,
    ModeAdoption,
    ParametresFuitesReseau,
    ModeReductionReseau,
    PRESETS_VALEUR_EAU,
    valider_parametres_vs_calibration,
    executer_modele,
    calculer_alpha_comportement,
    calculer_dynamique_fuites,
    calculer_economies_fuites_menage,
    decomposer_par_payeur,
    PERSISTANCE_OPTIMISTE,
    PERSISTANCE_REALISTE,
    PERSISTANCE_PESSIMISTE,
    FUITES_SANS_COUT,
    FUITES_QUEBEC_DEUX_STOCKS,
    FUITES_CONTEXTE_QUEBEC,
    FUITES_MENAGE_SEUL,
    FUITES_SUBVENTION_50,
    FUITES_VILLE_SEULE,
    FUITES_MENAGE_SANS_TARIF,
    FUITES_QUEBEC_SANS_TARIF,
    FUITES_QUEBEC_DEUX_STOCKS_SANS_TARIF,
    VALEUR_EAU_QUEBEC,
    # Monte Carlo
    ParametresMonteCarlo,
    ResultatsMonteCarlo,
    simuler_monte_carlo,
    DISTRIBUTIONS_DEFAUT,
)

# =============================================================================
# APPLICATION FASTAPI
# =============================================================================

app = FastAPI(
    title="API Compteurs d'Eau Québec",
    description="Analyse coûts-bénéfices des compteurs d'eau intelligents",
    version=MODEL_VERSION,
)

# CORS pour permettre les appels depuis le frontend
# En production, définir CORS_ORIGINS="https://monsite.com,https://autre.com"
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
if CORS_ORIGINS == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
    cout_infra_fixe: float = Field(0.0, ge=0, le=5_000_000, description="Coût infrastructure fixe ($)")

    # OPEX AMI non-technique (cyber, logiciels, stockage, télécom)
    cout_opex_non_tech_ami: float = Field(
        15.0,
        ge=0,
        le=50,
        description="OPEX AMI non-technique ($/compteur/an). Bas=10, Médian=15, Haut=35"
    )

    # Paramètres comportementaux
    reduction_comportement: float = Field(8.0, ge=0, le=20, description="Réduction comportementale (%)")
    persistance: str = Field("realiste", description="Scénario: optimiste, realiste, pessimiste, ultra")

    # Paramètres fuites - scénario prédéfini
    scenario_fuites: str = Field(
        "deux_stocks",
        description="Scénario fuites: deux_stocks, quebec, standard (avec tarif) | "
                    "deux_stocks_sans_tarif, quebec_sans_tarif, menage_sans_tarif (sans tarif) | custom"
    )

    # === PARAMÈTRES AVANCÉS FUITES (utilisés si scenario_fuites = "custom") ===
    # Petites fuites (toilettes, robinets)
    prevalence_petites_pct: float = Field(
        24.0,
        ge=0,
        le=40,
        description="% ménages avec petite fuite",
    )
    debit_petites_m3: float = Field(10.0, ge=1, le=30, description="Débit petites fuites (m³/an)")
    # Grosses fuites (conduites, chauffe-eau)
    prevalence_grosses_pct: float = Field(6.0, ge=0, le=20, description="% ménages avec grosse fuite")
    debit_grosses_m3: float = Field(50.0, ge=20, le=150, description="Débit grosses fuites (m³/an)")
    # Taux de réparation et détection
    taux_reparation_pct: float = Field(55.0, ge=20, le=100, description="% fuites réparées après détection")
    taux_detection_pct: float = Field(90.0, ge=50, le=100, description="% fuites détectées par AMI")
    # Facteurs différenciés pour grosses fuites
    facteur_detection_sig: float = Field(1.2, ge=0.5, le=2.0, description="Multiplicateur détection grosses fuites")
    facteur_reparation_sig: float = Field(1.4, ge=0.5, le=2.0, description="Multiplicateur réparation grosses fuites")
    # Nouvelles fuites annuelles
    taux_nouvelles_fuites_pct: float = Field(5.0, ge=0, le=15, description="% ménages avec nouvelle fuite/an")
    # Fuites persistantes (jamais réparées)
    part_persistantes_pct: float = Field(10.0, ge=0, le=30, description="% fuites jamais réparées")
    # Longue traîne
    facteur_duree_longue_traine: float = Field(5.0, ge=1.0, le=10.0, description="Facteur ralentissement réparations")
    # Coûts de réparation
    cout_reparation_petite: float = Field(150.0, ge=50, le=500, description="Coût réparation petite fuite ($)")
    cout_reparation_grosse: float = Field(600.0, ge=200, le=2000, description="Coût réparation grosse fuite ($)")
    inclure_cout_reparation: bool = Field(True, description="Inclure coûts réparation dans VAN")
    # Partage des coûts
    part_ville_pct: float = Field(0.0, ge=0, le=100, description="% coûts réparation payés par la ville")

    # Mode d'analyse
    mode_economique: bool = Field(True, description="True=économique, False=financier")
    valeur_sociale: float = Field(4.69, ge=0.5, le=15.0, description="Valeur sociale eau ($/m³)")
    cout_variable: float = Field(0.50, ge=0.1, le=3.0, description="Coût variable eau ($/m³)")

    # Économies d'échelle (grands déploiements >10k compteurs)
    activer_economies_echelle: bool = Field(False, description="Activer économies d'échelle")

    # -----------------------------
    # Valeur de l'eau (preset)
    # -----------------------------
    valeur_eau_preset: str = Field(
        default="custom",
        description="custom | quebec | conservateur | rarete | quebec_mcf"
    )

    # -----------------------------
    # Déploiement / adoption
    # -----------------------------
    scenario_adoption: str = Field(
        default="obligatoire",
        description="obligatoire | rapide | progressive | lent | nouveaux | par_secteur | custom | none"
    )
    adoption_mode: Optional[str] = Field(
        default=None,
        description="logistique | nouveaux | secteur (utilisé si scenario_adoption=custom)"
    )
    adoption_max_pct: Optional[float] = Field(default=None, ge=0, le=100)
    adoption_k_vitesse: Optional[float] = Field(default=None, ge=0.0)
    adoption_t0_point_median: Optional[float] = Field(default=None, ge=0.0)
    adoption_etaler_capex: Optional[bool] = Field(default=None)
    adoption_fraction_premiere_annee: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    adoption_cout_incitatif_par_menage: Optional[float] = Field(default=None, ge=0.0)
    adoption_duree_incitatif_ans: Optional[int] = Field(default=None, ge=0)
    adoption_taux_nouveaux_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    adoption_nb_secteurs: Optional[int] = Field(default=None, ge=1)
    adoption_annees_par_secteur: Optional[int] = Field(default=None, ge=1)
    adoption_annee_demarrage: Optional[int] = Field(default=None, ge=1)

    # -----------------------------
    # Fuites réseau
    # -----------------------------
    reseau_activer: bool = Field(default=False)
    reseau_volume_pertes_m3_an: float = Field(default=0.0, ge=0.0)
    reseau_reduction_max_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    reseau_mode_reduction: str = Field(default="lineaire", description="lineaire | exponentiel")
    reseau_annees_atteinte: int = Field(default=5, ge=1)
    reseau_lambda_reduction: float = Field(default=0.5, ge=0.0)
    reseau_annee_demarrage: int = Field(default=1, ge=1)
    reseau_cout_programme_annuel: float = Field(default=0.0, ge=0.0)
    reseau_cout_reparation_m3: float = Field(default=0.0, ge=0.0)
    reseau_cout_capex_initial: float = Field(default=0.0, ge=0.0)
    reseau_annee_capex: int = Field(default=1, ge=1)
    reseau_pondere_par_adoption: bool = Field(default=True)

    # -----------------------------
    # Report d'infrastructure (optionnel)
    # -----------------------------
    benefice_report_infra_annuel: float = Field(
        default=0.0,
        ge=0.0,
        le=10_000_000,
        description="Bénéfice annuel fixe du report d'infrastructure ($/an)"
    )
    benefice_report_infra_par_m3: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Bénéfice par m³ économisé lié au report d'infrastructure ($/m³)"
    )

    # -----------------------------
    # Monte Carlo (optionnel)
    # -----------------------------
    mc_seed: int = Field(default=42, ge=0)
    mc_n_simulations: int = Field(default=500, ge=100)


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

    # Décomposition des bénéfices (pour waterfall)
    va_benefices_eau: float = 0.0
    va_benefices_report_infra: float = 0.0
    va_benefices_cout_variable: float = 0.0

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
    elif nom in ("ultra", "ultra_pessimiste"):
        # Accepte les deux noms pour compatibilité UI/Core
        return ParametresPersistance(
            mode=ModePersistance.CONSTANT,
            alpha_initial=0.0,
            alpha_plateau=0.0,
            nom="Ultra-pessimiste",
        )
    else:
        raise ValueError(f"Scénario de persistance inconnu: {nom}")


def get_fuites(nom: str, req: CalculRequest = None) -> ParametresFuites:
    """Récupérer les paramètres de fuites selon le scénario.

    Utilise les presets du cœur pour garantir la cohérence.

    Scénarios disponibles:
    - Avec tarification (ou hypothèse incitatif fort):
        standard, quebec, deux_stocks
    - Sans tarification (contexte québécois typique):
        menage_sans_tarif, quebec_sans_tarif, deux_stocks_sans_tarif
    - Personnalisé: custom (utilise les paramètres avancés)
    """
    # Mapping des scénarios vers les presets
    scenarios_map = {
        # Avec tarification
        "standard": FUITES_SANS_COUT,
        "sans_cout": FUITES_SANS_COUT,
        "quebec": FUITES_CONTEXTE_QUEBEC,
        "deux_stocks": FUITES_QUEBEC_DEUX_STOCKS,
        "quebec_deux_stocks": FUITES_QUEBEC_DEUX_STOCKS,
        "menage": FUITES_MENAGE_SEUL,
        "subvention_50": FUITES_SUBVENTION_50,
        "ville": FUITES_VILLE_SEULE,
        # Sans tarification (taux réparation réduit, persistance augmentée)
        "menage_sans_tarif": FUITES_MENAGE_SANS_TARIF,
        "quebec_sans_tarif": FUITES_QUEBEC_SANS_TARIF,
        "deux_stocks_sans_tarif": FUITES_QUEBEC_DEUX_STOCKS_SANS_TARIF,
        "quebec_deux_stocks_sans_tarif": FUITES_QUEBEC_DEUX_STOCKS_SANS_TARIF,
    }

    if nom in scenarios_map:
        return scenarios_map[nom]
    elif nom == "custom" and req is not None:
        # Calculer le total = petites + grosses
        prevalence_totale = req.prevalence_petites_pct + req.prevalence_grosses_pct

        # Validation: total ne doit pas dépasser 60%
        if prevalence_totale > 60:
            raise HTTPException(
                status_code=422,
                detail=f"Erreur de validation: la prévalence totale ({prevalence_totale:.1f}%) "
                       f"dépasse le maximum réaliste de 60%."
            )
        # Déterminer le mode de répartition des coûts
        if not req.inclure_cout_reparation:
            mode_rep = ModeRepartitionCouts.SANS_COUT
        elif req.part_ville_pct >= 100:
            mode_rep = ModeRepartitionCouts.VILLE_SEULE
        elif req.part_ville_pct > 0:
            mode_rep = ModeRepartitionCouts.SUBVENTION_PARTIELLE
        else:
            mode_rep = ModeRepartitionCouts.MENAGE_SEUL

        # Utiliser les paramètres avancés personnalisés
        # Total = petites + grosses (calculé ci-dessus)
        return ParametresFuites(
            utiliser_prevalence_differenciee=True,
            part_menages_fuite_any_pct=prevalence_totale,  # Total = petites + grosses
            debit_fuite_any_m3_an=req.debit_petites_m3,
            part_menages_fuite_significative_pct=req.prevalence_grosses_pct,
            debit_fuite_significative_m3_an=req.debit_grosses_m3,
            taux_reparation_pct=req.taux_reparation_pct,
            taux_detection_pct=req.taux_detection_pct,
            facteur_detection_sig=req.facteur_detection_sig,
            facteur_reparation_sig=req.facteur_reparation_sig,
            taux_nouvelles_fuites_pct=req.taux_nouvelles_fuites_pct,
            part_fuites_persistantes_pct=req.part_persistantes_pct,
            facteur_duree_longue_traine=req.facteur_duree_longue_traine,
            cout_reparation_any=req.cout_reparation_petite,
            cout_reparation_sig=req.cout_reparation_grosse,
            inclure_cout_reparation=req.inclure_cout_reparation,
            mode_repartition=mode_rep,
            part_ville_pct=req.part_ville_pct,
            nom="Personnalisé",
        )
    else:
        # Scénario inconnu → erreur explicite (pas de fallback silencieux)
        valid_scenarios = list(scenarios_map.keys()) + ["custom"]
        raise HTTPException(
            status_code=400,
            detail=f"Scénario de fuites inconnu: '{nom}'. "
                   f"Valeurs acceptées: {', '.join(valid_scenarios)}"
        )


def get_valeur_eau(req: CalculRequest) -> ParametresValeurEau:
    preset = (req.valeur_eau_preset or "custom").strip().lower()
    if preset != "custom" and preset in PRESETS_VALEUR_EAU:
        return PRESETS_VALEUR_EAU[preset]
    return ParametresValeurEau(
        valeur_sociale_m3=req.valeur_sociale,
        cout_variable_m3=req.cout_variable,
    )


def get_adoption(req: CalculRequest) -> Optional[ParametresAdoption]:
    key = (req.scenario_adoption or "obligatoire").strip().lower()
    if key in ("none", "aucune", "off", "0"):
        return None

    alias = {
        "progressive": "progressif",
        "par_secteur": "secteur",
        "par-secteur": "secteur",
    }
    key = alias.get(key, key)

    if key != "custom":
        base = STRATEGIES_ADOPTION.get(key, ADOPTION_OBLIGATOIRE)
    else:
        mode_str = (req.adoption_mode or "logistique").strip().lower()
        if mode_str.startswith("nou"):
            mode = ModeAdoption.NOUVEAUX_BRANCHEMENTS
        elif mode_str.startswith("sec"):
            mode = ModeAdoption.PAR_SECTEUR
        else:
            mode = ModeAdoption.VOLONTAIRE_INCITATIF
        base = ParametresAdoption(mode=mode, nom="Personnalisé", description="")

    overrides = {}
    if req.adoption_max_pct is not None:
        overrides["adoption_max_pct"] = req.adoption_max_pct
    if req.adoption_k_vitesse is not None:
        overrides["k_vitesse"] = req.adoption_k_vitesse
    if req.adoption_t0_point_median is not None:
        overrides["t0_point_median"] = req.adoption_t0_point_median
    if req.adoption_etaler_capex is not None:
        overrides["etaler_capex"] = req.adoption_etaler_capex
    if req.adoption_fraction_premiere_annee is not None:
        overrides["fraction_premiere_annee"] = req.adoption_fraction_premiere_annee
    if req.adoption_cout_incitatif_par_menage is not None:
        overrides["cout_incitatif_par_menage"] = req.adoption_cout_incitatif_par_menage
    if req.adoption_duree_incitatif_ans is not None:
        overrides["duree_incitatif_ans"] = req.adoption_duree_incitatif_ans
    if req.adoption_taux_nouveaux_pct is not None:
        overrides["taux_nouveaux_pct"] = req.adoption_taux_nouveaux_pct
    if req.adoption_nb_secteurs is not None:
        overrides["nb_secteurs"] = req.adoption_nb_secteurs
    if req.adoption_annees_par_secteur is not None:
        overrides["annees_par_secteur"] = req.adoption_annees_par_secteur
    if req.adoption_annee_demarrage is not None:
        overrides["annee_demarrage"] = req.adoption_annee_demarrage

    if overrides:
        base = replace(base, **overrides)

    return base


def get_fuites_reseau(req: CalculRequest) -> Optional[ParametresFuitesReseau]:
    if not req.reseau_activer:
        return None

    mode_str = (req.reseau_mode_reduction or "lineaire").strip().lower()
    mode = ModeReductionReseau.EXPONENTIEL if mode_str.startswith("exp") else ModeReductionReseau.LINEAIRE

    return ParametresFuitesReseau(
        activer=True,
        volume_pertes_m3_an=req.reseau_volume_pertes_m3_an,
        reduction_max_pct=req.reseau_reduction_max_pct,
        mode_reduction=mode,
        annees_atteinte=req.reseau_annees_atteinte,
        lambda_reduction=req.reseau_lambda_reduction,
        annee_demarrage=req.reseau_annee_demarrage,
        cout_programme_annuel=req.reseau_cout_programme_annuel,
        cout_reparation_m3=req.reseau_cout_reparation_m3,
        cout_capex_initial=req.reseau_cout_capex_initial,
        annee_capex=req.reseau_annee_capex,
        pondere_par_adoption=req.reseau_pondere_par_adoption,
    )


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
        cout_infra_fixe=req.cout_infra_fixe if req.type_compteur == "ami" else 0,
        cout_opex_non_tech_ami=req.cout_opex_non_tech_ami if req.type_compteur == "ami" else 0,
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
    return {"status": "ok", "version": MODEL_VERSION}


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
            benefice_report_infra_annuel=req.benefice_report_infra_annuel,
            benefice_report_infra_par_m3=req.benefice_report_infra_par_m3,
        )

        # Créer les autres paramètres
        compteur = get_compteur(req)
        persistance = get_persistance(req.persistance, req.reduction_comportement)
        fuites = get_fuites(req.scenario_fuites, req)

        # Mode d'analyse
        mode = ModeCompte.ECONOMIQUE if req.mode_economique else ModeCompte.FINANCIER
        valeur_eau = get_valeur_eau(req)

        # Économies d'échelle
        config_echelle = ConfigEconomiesEchelle(activer=req.activer_economies_echelle)

        params_adoption = get_adoption(req)
        params_fuites_reseau = get_fuites_reseau(req)

        # Exécuter le modèle
        result = executer_modele(
            params=params,
            compteur=compteur,
            mode_compte=mode,
            valeur_eau=valeur_eau,
            config_echelle=config_echelle,
            persistance=persistance,
            params_fuites=fuites,
            params_adoption=params_adoption,
            params_fuites_reseau=params_fuites_reseau,
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
            va_benefices_eau=float(result.va_benefices_eau),
            va_benefices_report_infra=float(result.va_benefices_report_infra),
            va_benefices_cout_variable=float(result.va_benefices_cout_variable),
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


@app.get("/api/valeur_eau_presets")
def valeur_eau_presets():
    return {
        k: {
            "nom": v.nom,
            "description": v.description,
            "valeur_sociale_m3": v.valeur_sociale_m3,
            "cout_variable_m3": v.cout_variable_m3,
            "appliquer_mcf": getattr(v, "appliquer_mcf", False),
            "mcf": getattr(v, "mcf", 1.0),
        }
        for k, v in PRESETS_VALEUR_EAU.items()
    }


@app.post("/api/validate_calibration")
async def validate_calibration(req: CalculRequest):
    try:
        params = ParametresModele(
            nb_menages=req.nb_menages,
            taille_menage=req.taille_menage,
            lpcd=req.lpcd,
            horizon_analyse=req.horizon,
            taux_actualisation_pct=req.taux_actualisation,
            reduction_comportement_pct=req.reduction_comportement,
            benefice_report_infra_annuel=req.benefice_report_infra_annuel,
            benefice_report_infra_par_m3=req.benefice_report_infra_par_m3,
        )
        persistance = get_persistance(req.persistance, req.reduction_comportement)
        fuites = get_fuites(req.scenario_fuites, req)
        valeur_eau = get_valeur_eau(req)

        if fuites.utiliser_prevalence_differenciee:
            petites = fuites.part_menages_fuite_any_pct
            grosses = fuites.part_menages_fuite_significative_pct
            total = petites + grosses
            if total > 0:
                debit_m3 = (
                    (petites * fuites.debit_fuite_any_m3_an) +
                    (grosses * fuites.debit_fuite_significative_m3_an)
                ) / total
            else:
                debit_m3 = fuites.debit_fuite_any_m3_an
            prevalence = total
        else:
            prevalence = fuites.part_menages_fuite_pct
            debit_m3 = fuites.debit_fuite_m3_an

        params = replace(
            params,
            part_menages_fuite_pct=prevalence,
            debit_fuite_m3_an=debit_m3,
            valeur_eau_m3=valeur_eau.valeur_sociale_m3,
        )

        checks = valider_parametres_vs_calibration(params, persistance, fuites)

        return {
            "warnings": [
                {"param": nom, "ok": ok, "message": msg}
                for (nom, ok, msg) in checks
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.post("/api/detailed_series")
async def detailed_series(req: CalculRequest):
    """
    Retourner les séries détaillées pour les graphiques avancés.

    Inclut:
    - Dynamique des fuites (stock restant par année)
    - Décomposition des économies (comportement vs fuites)
    - Paramètres de fuites utilisés
    """
    try:
        # Créer les paramètres
        params = ParametresModele(
            nb_menages=req.nb_menages,
            taille_menage=req.taille_menage,
            lpcd=req.lpcd,
            horizon_analyse=req.horizon,
            taux_actualisation_pct=req.taux_actualisation,
            reduction_comportement_pct=req.reduction_comportement,
            benefice_report_infra_annuel=req.benefice_report_infra_annuel,
            benefice_report_infra_par_m3=req.benefice_report_infra_par_m3,
        )

        persistance = get_persistance(req.persistance, req.reduction_comportement)
        fuites = get_fuites(req.scenario_fuites, req)

        # Calculer la dynamique des fuites
        resultats_fuites = calculer_dynamique_fuites(
            params_fuites=fuites,
            nb_menages=req.nb_menages,
            horizon=req.horizon,
        )

        # Générer la série alpha (comportement)
        serie_alpha = [
            calculer_alpha_comportement(t, persistance) * 100
            for t in range(1, req.horizon + 1)
        ]

        # Calculer les économies comportementales par année
        usage_base = params.taille_menage * params.lpcd * 365.25 / 1000  # m³/an/ménage
        economies_comportement_par_an = [
            usage_base * (alpha / 100)
            for alpha in serie_alpha
        ]

        # Économies fuites par ménage par année (approximation basée sur les économies totales)
        economies_fuites_par_an = list(resultats_fuites.economies_eau_par_an / req.nb_menages)

        # Stock de fuites restant (pourcentage du stock initial)
        # Modèle: dL/dt = nouvelles - (détection × réparation) × L
        # Solution: L(t) = L_eq + (L_0 - L_eq) × exp(-λt)
        # où L_eq = nouvelles / λ et λ = taux_correction

        if fuites.utiliser_prevalence_differenciee:
            # Deux stocks: petites + grosses
            stock_initial = fuites.part_menages_fuite_any_pct + fuites.part_menages_fuite_significative_pct
        else:
            stock_initial = fuites.part_menages_fuite_pct

        taux_correction = (fuites.taux_detection_pct / 100) * (fuites.taux_reparation_pct / 100)
        taux_nouvelles = fuites.taux_nouvelles_fuites_pct  # En % par an

        # Équilibre à long terme
        stock_equilibre = taux_nouvelles / taux_correction if taux_correction > 0 else stock_initial

        stock_fuites = [stock_initial]  # Année 0: stock initial
        for t in range(1, req.horizon + 1):
            # Décroissance exponentielle vers l'équilibre
            stock_t = stock_equilibre + (stock_initial - stock_equilibre) * math.exp(-taux_correction * t)
            stock_fuites.append(stock_t)

        # Paramètres de fuites utilisés (pour affichage)
        params_fuites_info = {
            "scenario": req.scenario_fuites,
            "mode_deux_stocks": fuites.utiliser_prevalence_differenciee,
            "prevalence_petites_pct": fuites.part_menages_fuite_any_pct if fuites.utiliser_prevalence_differenciee else fuites.part_menages_fuite_pct,
            "debit_petites_m3": fuites.debit_fuite_any_m3_an if fuites.utiliser_prevalence_differenciee else fuites.debit_fuite_m3_an,
            "prevalence_grosses_pct": fuites.part_menages_fuite_significative_pct if fuites.utiliser_prevalence_differenciee else 0,
            "debit_grosses_m3": fuites.debit_fuite_significative_m3_an if fuites.utiliser_prevalence_differenciee else 0,
            "taux_detection_pct": fuites.taux_detection_pct,
            "taux_reparation_pct": fuites.taux_reparation_pct,
            "taux_nouvelles_fuites_pct": fuites.taux_nouvelles_fuites_pct,
            "part_persistantes_pct": fuites.part_fuites_persistantes_pct,
            "cout_reparation_moyen": fuites.cout_reparation_moyen,
        }

        # Info persistance comportementale
        params_persistance_info = {
            "scenario": req.persistance,
            "alpha_initial_pct": req.reduction_comportement,
            "alpha_plateau_pct": persistance.alpha_plateau * 100 if hasattr(persistance, 'alpha_plateau') else req.reduction_comportement,
            "mode": persistance.mode.value if hasattr(persistance.mode, 'value') else str(persistance.mode),
        }

        return {
            "annees": list(range(1, req.horizon + 1)),  # 1 à horizon pour économies
            "annees_fuites": list(range(0, req.horizon + 1)),  # 0 à horizon pour stock fuites
            # Économies par ménage par année
            "economies_comportement_m3": economies_comportement_par_an,
            "economies_fuites_m3": economies_fuites_par_an,
            # Stock de fuites (% ménages avec fuite active)
            "stock_fuites_pct": stock_fuites,
            # Série alpha
            "serie_alpha_pct": serie_alpha,
            # Paramètres utilisés
            "params_fuites": params_fuites_info,
            "params_persistance": params_persistance_info,
            # Totaux
            "total_reparations": int(resultats_fuites.total_reparations),
            "economies_eau_total_m3": float(resultats_fuites.economies_eau_total),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare_fuites")
async def compare_fuites(req: CalculRequest):
    """
    Comparer les trois scénarios de fuites.

    Retourne la VAN cumulative pour chaque scénario de fuites.
    """
    results = {}

    sans_tarif = (req.scenario_fuites or "").endswith("_sans_tarif")

    if sans_tarif:
        scenarios = [
            ("menage_sans_tarif", "Ménage (sans tarif)"),
            ("quebec_sans_tarif", "Québec (sans tarif)"),
            ("deux_stocks_sans_tarif", "QC différencié (sans tarif)"),
        ]
    else:
        scenarios = [
            ("standard", "Standard sans coûts (20%)"),
            ("quebec", "Québec (35%)"),
            ("deux_stocks", "Différencié QC"),
        ]

    out_keys = ["standard", "quebec", "deux_stocks"]
    for out_key, (scenario_key, scenario_nom) in zip(out_keys, scenarios):
        req_copy = req.model_copy()
        req_copy.scenario_fuites = scenario_key
        result = await calculate(req_copy)
        results[out_key] = {
            "nom": scenario_nom,
            "van": result.van,
            "rbc": result.rbc,
            "payback": result.payback,
            "van_cumulative": result.van_cumulative,
            "economie_fuite_menage": result.economie_fuite_menage,
        }

    return results


@app.post("/api/monte_carlo")
async def monte_carlo(req: CalculRequest, n_simulations: int = 500, seed: int = 42):
    """
    Exécuter une simulation Monte Carlo.

    Retourne la distribution de la VAN et les statistiques associées.
    """
    try:
        # Créer les paramètres de base
        params = ParametresModele(
            nb_menages=req.nb_menages,
            taille_menage=req.taille_menage,
            lpcd=req.lpcd,
            horizon_analyse=req.horizon,
            taux_actualisation_pct=req.taux_actualisation,
            reduction_comportement_pct=req.reduction_comportement,
            benefice_report_infra_annuel=req.benefice_report_infra_annuel,
            benefice_report_infra_par_m3=req.benefice_report_infra_par_m3,
        )

        compteur = get_compteur(req)
        persistance = get_persistance(req.persistance, req.reduction_comportement)
        fuites = get_fuites(req.scenario_fuites, req)

        mode = ModeCompte.ECONOMIQUE if req.mode_economique else ModeCompte.FINANCIER
        valeur_eau = get_valeur_eau(req)

        params_adoption = get_adoption(req)
        params_fuites_reseau = get_fuites_reseau(req)

        # Configuration Monte Carlo
        config_mc = ParametresMonteCarlo(
            distributions=DISTRIBUTIONS_DEFAUT,
            n_simulations=min(n_simulations, 1000),  # Limiter pour performance
            seed=seed,
        )

        # Exécuter Monte Carlo
        resultats_mc = simuler_monte_carlo(
            params_base=params,
            compteur_base=compteur,
            config_mc=config_mc,
            mode_compte=mode,
            valeur_eau=valeur_eau,
            afficher_progression=False,
            persistance=persistance,
            params_fuites=fuites,
            params_adoption=params_adoption,
            params_fuites_reseau=params_fuites_reseau,
        )

        # Calculer l'histogramme pour le frontend
        van_values = resultats_mc.van_simulations
        hist, bin_edges = np.histogram(van_values, bins=30)
        bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(hist))]

        return {
            "n_simulations": resultats_mc.n_simulations,
            "van_moyenne": float(resultats_mc.van_moyenne),
            "van_mediane": float(resultats_mc.van_mediane),
            "van_std": float(resultats_mc.van_ecart_type),
            "prob_van_positive": float(resultats_mc.prob_van_positive),
            "percentiles": {
                "p5": float(resultats_mc.percentile_5),
                "p25": float(resultats_mc.percentile_25),
                "p50": float(resultats_mc.van_mediane),
                "p75": float(resultats_mc.percentile_75),
                "p95": float(resultats_mc.percentile_95),
            },
            "histogram": {
                "counts": hist.tolist(),
                "bin_centers": [float(x) for x in bin_centers],
                "bin_edges": [float(x) for x in bin_edges],
            },
            "correlations": [
                {"param": k, "correlation": float(v)}
                for k, v in sorted(
                    resultats_mc.correlations.items(),
                    key=lambda x: abs(x[1]),
                    reverse=True
                )[:8]  # Top 8 paramètres
            ] if resultats_mc.correlations else [],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/perspectives")
async def perspectives(req: CalculRequest):
    """
    Retourner la décomposition de la VAN par payeur: économique, ville, ménages.

    Permet l'analyse distributive: qui paie, qui gagne.
    """
    try:
        params = ParametresModele(
            nb_menages=req.nb_menages,
            taille_menage=req.taille_menage,
            lpcd=req.lpcd,
            horizon_analyse=req.horizon,
            taux_actualisation_pct=req.taux_actualisation,
            reduction_comportement_pct=req.reduction_comportement,
            benefice_report_infra_annuel=req.benefice_report_infra_annuel,
            benefice_report_infra_par_m3=req.benefice_report_infra_par_m3,
        )

        compteur = get_compteur(req)
        persistance = get_persistance(req.persistance, req.reduction_comportement)
        fuites = get_fuites(req.scenario_fuites, req)
        valeur_eau = get_valeur_eau(req)
        config_echelle = ConfigEconomiesEchelle(activer=req.activer_economies_echelle)
        params_adoption = get_adoption(req)

        # Décomposition par payeur
        result = decomposer_par_payeur(
            params=params,
            compteur=compteur,
            config_echelle=config_echelle,
            persistance=persistance,
            params_fuites=fuites,
            valeur_eau=valeur_eau,
            params_adoption=params_adoption,
        )

        return {
            "van_economique": float(result.van_economique),
            "van_ville": float(result.van_ville),
            "van_menages": float(result.van_menages),
            "va_couts_ville": float(result.va_couts_ville),
            "va_benefices_ville": float(result.va_benefices_ville),
            "va_externalites": float(result.va_externalites),
            "va_benefices_report_infra": float(result.va_benefices_report_infra),
            "description": {
                "economique": "Bien-être social total (externalités incluses)",
                "ville": "Budget municipal (CAPEX, OPEX, économies coût variable)",
                "menages": "Perspective citoyens (coûts réparations, économies si tarif)",
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scenario_name")
async def get_scenario_name(persistance: str = "realiste", fuites: str = "deux_stocks"):
    """Retourner le nom complet du scénario."""

    persistance_noms = {
        "optimiste": "Optimiste",
        "realiste": "Réaliste",
        "pessimiste": "Pessimiste",
        "ultra": "Ultra-pessimiste",
    }

    fuites_noms = {
        "standard": "Standard (sans coûts)",
        "quebec": "Québec",
        "deux_stocks": "Différencié",
        "deux_stocks_sans_tarif": "Différencié (sans tarif)",
        "quebec_sans_tarif": "Québec (sans tarif)",
        "menage_sans_tarif": "Standard (sans tarif)",
        "custom": "Personnalisé",
    }

    p_nom = persistance_noms.get(persistance, persistance)
    f_nom = fuites_noms.get(fuites, fuites)

    return {
        "nom_complet": f"{p_nom} + {f_nom}",
        "persistance": p_nom,
        "fuites": f_nom,
    }


# =============================================================================
# SERVIR LES FICHIERS STATIQUES
# =============================================================================

# Si index.html existe dans le même dossier, le servir
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
