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

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from dataclasses import replace
from datetime import datetime, timezone
from collections import defaultdict
import numpy as np
import math
import os
import time
import logging
import json

# =============================================================================
# OBSERVABILITÉ: LOGGING STRUCTURÉ & MÉTRIQUES
# =============================================================================

class StructuredLogger:
    """Logger qui produit des logs JSON structurés."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)

    def _log(self, level: str, message: str, **kwargs):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logger.log(getattr(logging, level.upper()), json.dumps(log_entry))

    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)

logger = StructuredLogger("api")

class MetricsCollector:
    """Collecteur de métriques pour monitoring."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.request_count: Dict[str, int] = defaultdict(int)
        self.request_latency: Dict[str, List[float]] = defaultdict(list)
        self.error_count: Dict[str, int] = defaultdict(int)
        self.last_error: Optional[Dict[str, Any]] = None
        self._max_latency_samples = 1000  # Limiter mémoire

    def record_request(self, endpoint: str, latency_ms: float, status_code: int):
        self.request_count[endpoint] += 1
        latencies = self.request_latency[endpoint]
        latencies.append(latency_ms)
        if len(latencies) > self._max_latency_samples:
            self.request_latency[endpoint] = latencies[-self._max_latency_samples:]

        if status_code >= 400:
            error_key = f"{endpoint}_{status_code}"
            self.error_count[error_key] += 1

    def record_error(self, endpoint: str, error_type: str, error_message: str):
        self.last_error = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "error_type": error_type,
            "error_message": error_message[:500]
        }

    def get_uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def get_metrics_prometheus(self) -> str:
        """Exporter métriques au format Prometheus."""
        lines = []
        lines.append("# HELP api_requests_total Total number of API requests")
        lines.append("# TYPE api_requests_total counter")
        for endpoint, count in self.request_count.items():
            safe_endpoint = endpoint.replace("/", "_").replace("-", "_")
            lines.append(f'api_requests_total{{endpoint="{endpoint}"}} {count}')

        lines.append("# HELP api_request_latency_ms Request latency in milliseconds")
        lines.append("# TYPE api_request_latency_ms summary")
        for endpoint, latencies in self.request_latency.items():
            if latencies:
                avg = sum(latencies) / len(latencies)
                p50 = sorted(latencies)[len(latencies) // 2]
                p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 20 else max(latencies)
                lines.append(f'api_request_latency_ms{{endpoint="{endpoint}",quantile="0.5"}} {p50:.2f}')
                lines.append(f'api_request_latency_ms{{endpoint="{endpoint}",quantile="0.95"}} {p95:.2f}')
                lines.append(f'api_request_latency_ms_avg{{endpoint="{endpoint}"}} {avg:.2f}')

        lines.append("# HELP api_errors_total Total number of API errors")
        lines.append("# TYPE api_errors_total counter")
        for error_key, count in self.error_count.items():
            lines.append(f'api_errors_total{{error="{error_key}"}} {count}')

        lines.append("# HELP api_uptime_seconds API uptime in seconds")
        lines.append("# TYPE api_uptime_seconds gauge")
        lines.append(f"api_uptime_seconds {self.get_uptime_seconds():.0f}")

        return "\n".join(lines)

metrics = MetricsCollector()

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
    DistributionParametre,
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

# Middleware pour collecter les métriques et ajouter headers
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        # Ajouter header version API
        response.headers["X-API-Version"] = MODEL_VERSION
        return response
    except Exception as e:
        metrics.record_error(request.url.path, type(e).__name__, str(e))
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        endpoint = request.url.path
        status_code = response.status_code if response else 500
        metrics.record_request(endpoint, latency_ms, status_code)
        if status_code >= 400:
            logger.warning(
                "request_error",
                endpoint=endpoint,
                method=request.method,
                status_code=status_code,
                latency_ms=round(latency_ms, 2)
            )
        else:
            logger.info(
                "request_completed",
                endpoint=endpoint,
                method=request.method,
                status_code=status_code,
                latency_ms=round(latency_ms, 2)
            )


# =============================================================================
# MODÈLES PYDANTIC (validation des entrées)
# =============================================================================

class DistributionConfig(BaseModel):
    """Configuration d'une distribution pour Monte Carlo."""
    nom: str = Field(..., description="Nom du paramètre (alpha0, lpcd, cout_compteur, etc.)")
    type_distribution: str = Field("triangular", description="triangular, normal, uniform")
    min_val: Optional[float] = Field(None, description="Valeur minimum (triangular/uniform)")
    mode_val: Optional[float] = Field(None, description="Mode/valeur probable (triangular)")
    max_val: Optional[float] = Field(None, description="Valeur maximum (triangular/uniform)")
    moyenne: Optional[float] = Field(None, description="Moyenne (normal)")
    ecart_type: Optional[float] = Field(None, description="Écart-type (normal)")


class MonteCarloRequest(BaseModel):
    """Paramètres pour Monte Carlo avancé."""
    params: dict = Field(..., description="Paramètres de calcul (même format que CalculRequest)")
    n_simulations: int = Field(500, ge=100, le=2000, description="Nombre de simulations")
    seed: int = Field(42, ge=0, description="Seed pour reproductibilité")
    distributions_custom: Optional[List[DistributionConfig]] = Field(
        None,
        description="Distributions personnalisées (remplacent les défauts)"
    )


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

    # -----------------------------
    # Mode Expert (optionnel)
    # -----------------------------
    # Persistance comportementale avancée
    expert_lambda_decay: Optional[float] = Field(
        default=None,
        ge=0.05,
        le=0.40,
        description="Vitesse de déclin vers le plateau (remplace valeur preset si fourni)"
    )
    expert_alpha_plateau: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Réduction résiduelle long terme en % (remplace valeur preset si fourni)"
    )

    # MCF - Coût Marginal des Fonds publics (optionnel, désactivé par défaut)
    appliquer_mcf: bool = Field(
        default=False,
        description="Appliquer le MCF aux dépenses publiques (CAPEX)"
    )
    mcf: float = Field(
        default=0.20,
        ge=0.05,
        le=0.50,
        description="Coût marginal des fonds publics (Treasury Board: 0.20)"
    )


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

def get_persistance(
    nom: str,
    alpha_initial: float,
    expert_lambda_decay: Optional[float] = None,
    expert_alpha_plateau: Optional[float] = None
) -> ParametresPersistance:
    """Créer les paramètres de persistance selon le scénario.

    Args:
        nom: Nom du scénario (optimiste, realiste, pessimiste, ultra)
        alpha_initial: Réduction comportementale initiale (%)
        expert_lambda_decay: Valeur custom pour lambda (remplace preset si fourni)
        expert_alpha_plateau: Valeur custom pour alpha plateau en % (remplace preset si fourni)
    """

    if nom == "optimiste":
        return ParametresPersistance(
            mode=ModePersistance.CONSTANT,
            alpha_initial=alpha_initial / 100,
            alpha_plateau=alpha_initial / 100,
            nom="Optimiste",
        )
    elif nom == "realiste":
        # Utiliser les valeurs expert si fournies, sinon les defaults
        lambda_val = expert_lambda_decay if expert_lambda_decay is not None else 0.15
        plateau_val = (expert_alpha_plateau / 100) if expert_alpha_plateau is not None else 0.025
        return ParametresPersistance(
            mode=ModePersistance.EXPONENTIEL_PLATEAU,
            alpha_initial=alpha_initial / 100,
            alpha_plateau=plateau_val,
            lambda_decay=lambda_val,
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
        base = PRESETS_VALEUR_EAU[preset]
        appliquer_mcf = base.appliquer_mcf or req.appliquer_mcf
        mcf_val = req.mcf if req.appliquer_mcf else base.mcf
        if appliquer_mcf == base.appliquer_mcf and mcf_val == base.mcf:
            return base
        return replace(base, appliquer_mcf=appliquer_mcf, mcf=mcf_val)
    return ParametresValeurEau(
        valeur_sociale_m3=req.valeur_sociale,
        cout_variable_m3=req.cout_variable,
        appliquer_mcf=req.appliquer_mcf,
        mcf=req.mcf,
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
    """Health check enrichi avec métriques de production."""
    total_requests = sum(metrics.request_count.values())
    total_errors = sum(metrics.error_count.values())

    return {
        "status": "ok",
        "version": MODEL_VERSION,
        "uptime_seconds": round(metrics.get_uptime_seconds()),
        "started_at": metrics.start_time.isoformat(),
        "total_requests": total_requests,
        "total_errors": total_errors,
        "last_error": metrics.last_error,
    }


@app.get("/api/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Endpoint métriques au format Prometheus."""
    return metrics.get_metrics_prometheus()


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
        persistance = get_persistance(
            req.persistance,
            req.reduction_comportement,
            expert_lambda_decay=req.expert_lambda_decay,
            expert_alpha_plateau=req.expert_alpha_plateau
        )
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
        persistance = get_persistance(
            req.persistance,
            req.reduction_comportement,
            expert_lambda_decay=req.expert_lambda_decay,
            expert_alpha_plateau=req.expert_alpha_plateau
        )
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

        persistance = get_persistance(
            req.persistance,
            req.reduction_comportement,
            expert_lambda_decay=req.expert_lambda_decay,
            expert_alpha_plateau=req.expert_alpha_plateau
        )
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
        persistance = get_persistance(
            req.persistance,
            req.reduction_comportement,
            expert_lambda_decay=req.expert_lambda_decay,
            expert_alpha_plateau=req.expert_alpha_plateau
        )
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


@app.get("/api/monte_carlo/distributions")
async def get_distributions():
    """
    Retourner les distributions Monte Carlo par défaut.

    Utile pour l'UI de configuration des distributions personnalisées.
    """
    result = {}
    for nom, distrib in DISTRIBUTIONS_DEFAUT.items():
        result[nom] = {
            "nom": distrib.nom,
            "type_distribution": distrib.type_distribution,
            "min_val": distrib.min_val,
            "mode_val": distrib.mode_val,
            "max_val": distrib.max_val,
            "moyenne": distrib.moyenne,
            "ecart_type": distrib.ecart_type,
            "description": distrib.description,
        }
    return result


@app.post("/api/monte_carlo_advanced")
async def monte_carlo_advanced(req: MonteCarloRequest):
    """
    Monte Carlo avec distributions personnalisées.

    Permet de configurer les distributions pour chaque paramètre.
    """
    try:
        # Convertir les params dict en CalculRequest
        calc_req = CalculRequest(**req.params)

        # Créer les paramètres de base
        params = ParametresModele(
            nb_menages=calc_req.nb_menages,
            taille_menage=calc_req.taille_menage,
            lpcd=calc_req.lpcd,
            horizon_analyse=calc_req.horizon,
            taux_actualisation_pct=calc_req.taux_actualisation,
            reduction_comportement_pct=calc_req.reduction_comportement,
            benefice_report_infra_annuel=calc_req.benefice_report_infra_annuel,
            benefice_report_infra_par_m3=calc_req.benefice_report_infra_par_m3,
        )

        compteur = get_compteur(calc_req)
        persistance = get_persistance(
            calc_req.persistance,
            calc_req.reduction_comportement,
            expert_lambda_decay=calc_req.expert_lambda_decay,
            expert_alpha_plateau=calc_req.expert_alpha_plateau
        )
        fuites = get_fuites(calc_req.scenario_fuites, calc_req)

        mode = ModeCompte.ECONOMIQUE if calc_req.mode_economique else ModeCompte.FINANCIER
        valeur_eau = get_valeur_eau(calc_req)

        params_adoption = get_adoption(calc_req)
        params_fuites_reseau = get_fuites_reseau(calc_req)

        # Construire les distributions
        distributions = DISTRIBUTIONS_DEFAUT.copy()

        if req.distributions_custom:
            for d in req.distributions_custom:
                distributions[d.nom] = DistributionParametre(
                    nom=d.nom,
                    type_distribution=d.type_distribution,
                    min_val=d.min_val,
                    mode_val=d.mode_val,
                    max_val=d.max_val,
                    moyenne=d.moyenne,
                    ecart_type=d.ecart_type,
                )

        # Configuration Monte Carlo
        config_mc = ParametresMonteCarlo(
            distributions=distributions,
            n_simulations=min(req.n_simulations, 2000),
            seed=req.seed,
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

        # Calculer l'histogramme
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
                )[:8]
            ] if resultats_mc.correlations else [],
            "distributions_used": {
                nom: {
                    "type": d.type_distribution,
                    "min": d.min_val,
                    "mode": d.mode_val,
                    "max": d.max_val,
                }
                for nom, d in distributions.items()
            }
        }

    except Exception as e:
        metrics.record_error("/api/monte_carlo_advanced", type(e).__name__, str(e))
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
        persistance = get_persistance(
            req.persistance,
            req.reduction_comportement,
            expert_lambda_decay=req.expert_lambda_decay,
            expert_alpha_plateau=req.expert_alpha_plateau
        )
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


class CalibrationData(BaseModel):
    """Données de consommation pour calibrage automatique."""
    data: List[dict] = Field(..., description="Liste de {mois/date, consommation_m3}")
    nb_menages: int = Field(..., ge=1, description="Nombre de ménages dans les données")
    taille_menage: float = Field(2.2, ge=1.0, le=5.0, description="Taille moyenne du ménage")


class OptimizationRequest(BaseModel):
    """Paramètres pour l'optimisation du déploiement."""
    params: dict = Field(..., description="Paramètres de calcul de base")
    budget_annuel_max: float = Field(..., ge=100000, description="Budget annuel maximum ($)")
    capacite_installation_max: int = Field(..., ge=1000, description="Compteurs installables par an")
    objectif: str = Field("van", description="Objectif: van (maximiser) ou payback (minimiser)")
    horizon_deploiement: int = Field(10, ge=1, le=20, description="Horizon de déploiement (années)")


@app.post("/api/calibrate_from_data")
async def calibrate_from_data(req: CalibrationData):
    """
    Calibrer les paramètres à partir de données de consommation.

    Analyse les données CSV importées et suggère des valeurs pour:
    - LPCD moyen
    - Variance saisonnière
    - Détection d'anomalies (fuites probables)
    - Estimation prévalence fuites
    """
    try:
        data = req.data
        if len(data) < 3:
            raise HTTPException(status_code=422, detail="Au moins 3 mois de données requis")

        # Extraire les consommations
        consommations = []
        for row in data:
            val = row.get('consommation_m3') or row.get('valeur') or row.get('value')
            if val is not None:
                consommations.append(float(val))

        if len(consommations) < 3:
            raise HTTPException(status_code=422, detail="Données de consommation invalides")

        consommations = np.array(consommations)

        # Calculs statistiques
        moyenne = float(np.mean(consommations))
        mediane = float(np.median(consommations))
        ecart_type = float(np.std(consommations))
        coef_variation = ecart_type / moyenne if moyenne > 0 else 0

        # LPCD: consommation / (nb_menages * taille_menage * jours_par_mois * 1000 L/m³)
        jours_mois_moyen = 30.44
        lpcd = (moyenne * 1000) / (req.nb_menages * req.taille_menage * jours_mois_moyen)

        # Variance saisonnière (ratio max/min)
        variance_saisonniere = float(np.max(consommations) / np.min(consommations)) if np.min(consommations) > 0 else 1.0

        # Détection anomalies (valeurs > moyenne + 2*sigma)
        seuil_anomalie = moyenne + 2 * ecart_type
        anomalies = [i for i, v in enumerate(consommations) if v > seuil_anomalie]
        nb_anomalies = len(anomalies)

        # Estimation prévalence fuites basée sur la variance
        # Hypothèse: haute variance = plus de fuites intermittentes
        if coef_variation > 0.3:
            prevalence_estimee = min(35, 20 + (coef_variation - 0.3) * 50)
        elif coef_variation > 0.15:
            prevalence_estimee = 15 + (coef_variation - 0.15) * 33
        else:
            prevalence_estimee = max(10, coef_variation * 100)

        # Intervalles de confiance (95%)
        n = len(consommations)
        t_value = 1.96 if n > 30 else 2.0  # Approximation
        margin = t_value * ecart_type / np.sqrt(n)

        lpcd_low = (moyenne - margin) * 1000 / (req.nb_menages * req.taille_menage * jours_mois_moyen)
        lpcd_high = (moyenne + margin) * 1000 / (req.nb_menages * req.taille_menage * jours_mois_moyen)

        return {
            "lpcd": {
                "valeur": round(lpcd, 0),
                "intervalle_confiance": [round(lpcd_low, 0), round(lpcd_high, 0)],
                "description": "Litres par personne par jour"
            },
            "consommation_mensuelle": {
                "moyenne_m3": round(moyenne, 0),
                "mediane_m3": round(mediane, 0),
                "ecart_type_m3": round(ecart_type, 0),
                "coef_variation": round(coef_variation, 3)
            },
            "saisonnalite": {
                "variance_ratio": round(variance_saisonniere, 2),
                "description": "Ratio max/min mensuel"
            },
            "anomalies": {
                "nombre": nb_anomalies,
                "mois_suspects": anomalies,
                "seuil_m3": round(seuil_anomalie, 0),
                "description": "Mois avec consommation anormalement élevée (fuites probables)"
            },
            "fuites_estimees": {
                "prevalence_pct": round(prevalence_estimee, 1),
                "intervalle": [max(10, round(prevalence_estimee - 10, 0)), min(40, round(prevalence_estimee + 10, 0))],
                "confiance": "moyenne" if 0.15 < coef_variation < 0.35 else "faible",
                "description": "Estimation basée sur la variabilité des données"
            },
            "recommandations": {
                "lpcd_suggere": round(lpcd, 0),
                "prevalence_fuites_suggeree": round(prevalence_estimee, 0),
                "qualite_donnees": "bonne" if n >= 12 else "limitée" if n >= 6 else "insuffisante"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        metrics.record_error("/api/calibrate_from_data", type(e).__name__, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/optimize_deployment")
async def optimize_deployment(req: OptimizationRequest):
    """
    Trouver la trajectoire de déploiement optimale sous contraintes.

    Optimise le rythme de déploiement pour maximiser la VAN
    ou minimiser le payback sous contraintes de budget et capacité.
    """
    try:
        calc_req = CalculRequest(**req.params)

        # Coût par compteur
        cout_unitaire = (
            calc_req.cout_compteur +
            calc_req.heures_installation * calc_req.taux_horaire +
            calc_req.cout_reseau
        )

        # Calcul du nombre max de compteurs par an selon contraintes
        compteurs_budget = int(req.budget_annuel_max / cout_unitaire)
        compteurs_par_an = min(compteurs_budget, req.capacite_installation_max)

        # Années nécessaires pour déployer tous les compteurs
        annees_deploiement = math.ceil(calc_req.nb_menages / compteurs_par_an)

        # Générer plusieurs scénarios de déploiement
        scenarios = []

        for vitesse in [0.5, 0.75, 1.0, 1.25, 1.5]:
            compteurs_scenario = int(compteurs_par_an * vitesse)
            if compteurs_scenario < 1000:
                continue

            annees = math.ceil(calc_req.nb_menages / compteurs_scenario)
            if annees > req.horizon_deploiement:
                continue

            # Calculer avec ce scénario d'adoption
            params_scenario = req.params.copy()
            params_scenario['scenario_adoption'] = 'custom'
            params_scenario['adoption_mode'] = 'secteur'
            params_scenario['adoption_nb_secteurs'] = annees
            params_scenario['adoption_annees_par_secteur'] = 1
            params_scenario['adoption_max_pct'] = 100

            try:
                calc_req_scenario = CalculRequest(**params_scenario)
                result = await calculate(calc_req_scenario)

                scenarios.append({
                    "compteurs_par_an": compteurs_scenario,
                    "annees_deploiement": annees,
                    "budget_annuel": compteurs_scenario * cout_unitaire,
                    "van": result.van,
                    "rbc": result.rbc,
                    "payback": result.payback,
                    "investissement_initial": result.investissement_initial,
                })
            except Exception:
                continue

        if not scenarios:
            raise HTTPException(status_code=422, detail="Aucun scénario viable trouvé")

        # Trouver l'optimal selon l'objectif
        if req.objectif == "van":
            optimal = max(scenarios, key=lambda s: s["van"])
        else:  # payback
            valides = [s for s in scenarios if s["payback"] is not None]
            if valides:
                optimal = min(valides, key=lambda s: s["payback"])
            else:
                optimal = scenarios[0]

        return {
            "optimal": optimal,
            "scenarios": sorted(scenarios, key=lambda s: -s["van"]),
            "contraintes": {
                "budget_annuel_max": req.budget_annuel_max,
                "capacite_installation_max": req.capacite_installation_max,
                "cout_unitaire": cout_unitaire,
                "compteurs_max_budget": compteurs_budget,
                "compteurs_effectifs": compteurs_par_an,
            },
            "recommandation": f"Déployer {optimal['compteurs_par_an']:,} compteurs/an sur {optimal['annees_deploiement']} ans"
        }

    except HTTPException:
        raise
    except Exception as e:
        metrics.record_error("/api/optimize_deployment", type(e).__name__, str(e))
        raise HTTPException(status_code=500, detail=str(e))


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
