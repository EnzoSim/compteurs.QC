# Guide d'Implémentation Complet
## Application Web Interactive — Compteurs d'Eau Québec

**Objectif**: Transformer le modèle Python `analyse_compteurs_eau.py` en application web interactive avec sliders, calculs en temps réel, et déploiement cloud.

**Auteur**: Enzo Simier (HEC Montréal)
**Version**: 1.0 — Janvier 2026

---

## Table des matières

1. [Architecture](#1-architecture)
2. [Fichiers à créer](#2-fichiers-à-créer)
3. [Phase 1: API FastAPI](#3-phase-1-api-fastapi)
4. [Phase 2: Frontend interactif](#4-phase-2-frontend-interactif)
5. [Phase 3: Déploiement](#5-phase-3-déploiement)
6. [Commandes récapitulatives](#6-commandes-récapitulatives)

---

## 1. Architecture

### 1.1 Schéma global

```
┌─────────────────────────────────────────────────────────────────┐
│                        UTILISATEUR                               │
│                    (navigateur web)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (index.html)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Sliders   │  │  Sélecteurs │  │      Graphiques         │  │
│  │  - Ménages  │  │  - Ville    │  │  - VAN cumulative       │  │
│  │  - LPCD     │  │  - Compteur │  │  - Tornado sensibilité  │  │
│  │  - Coûts    │  │  - Persist. │  │  - Comparaison types    │  │
│  │  - Alpha    │  │  - Fuites   │  │  - Eco vs Financier     │  │
│  │  - Fuites   │  │  - Mode     │  │  - Courbes alpha        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                              │                                   │
│                     fetch('/api/calculate')                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (api.py)                             │
│                        FastAPI                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  POST /api/calculate                                        ││
│  │    - Reçoit: tous les paramètres (JSON)                     ││
│  │    - Appelle: executer_modele()                             ││
│  │    - Retourne: VAN, RBC, payback, séries temporelles        ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  POST /api/sensitivity                                      ││
│  │    - Reçoit: paramètres de base                             ││
│  │    - Calcule: variation ±10% de chaque paramètre            ││
│  │    - Retourne: impacts sur VAN (tornado chart)              ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  GET /api/presets                                           ││
│  │    - Retourne: presets villes (Longueuil, Montréal, etc.)   ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                   import analyse_compteurs_eau                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              MODÈLE PYTHON (analyse_compteurs_eau.py)            │
│                    SOURCE UNIQUE DE VÉRITÉ                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  executer_modele(params, compteur, persistance, fuites...)  ││
│  │    → ResultatsModele (VAN, RBC, séries, économies...)       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Flux de données

```
1. Utilisateur bouge un slider (ex: LPCD = 280)
                    │
                    ▼
2. JavaScript collecte TOUS les paramètres actuels
   {
     "nb_menages": 116258,
     "taille_menage": 2.18,
     "lpcd": 280,              ← modifié
     "horizon": 20,
     "taux_actualisation": 3.0,
     "type_compteur": "ami",
     "cout_compteur": 250,
     ...
   }
                    │
                    ▼
3. fetch('https://api.example.com/api/calculate', {
     method: 'POST',
     body: JSON.stringify(params)
   })
                    │
                    ▼
4. FastAPI reçoit, valide, appelle Python:

   result = executer_modele(
       ParametresModele(...),
       ParametresCompteur(...),
       persistance=PERSISTANCE_REALISTE,
       params_fuites=FUITES_QUEBEC_DEUX_STOCKS,
       mode_compte=ModeCompte.ECONOMIQUE,
       valeur_eau=VALEUR_EAU_QUEBEC
   )
                    │
                    ▼
5. FastAPI retourne JSON:
   {
     "van": 15234567.89,
     "rbc": 1.15,
     "payback": 14.2,
     "lcsw": 4.12,
     "van_cumulative": [-78000000, -65000000, ...],
     "economie_totale_menage": 18.5,
     ...
   }
                    │
                    ▼
6. JavaScript met à jour:
   - Métriques (VAN, RBC, Payback, LCSW)
   - Graphiques (Chart.js)
   - Recommandation (viable/non viable)
```

---

## 2. Fichiers à créer

### 2.1 Structure du projet

```
/Users/enzo_simier/Desktop/Water/
│
├── analyse_compteurs_eau.py    # Modèle existant (NE PAS MODIFIER)
├── api.py                      # NOUVEAU: API FastAPI
├── index.html                  # NOUVEAU: Frontend interactif
├── requirements.txt            # NOUVEAU: Dépendances Python
├── render.yaml                 # NOUVEAU: Config déploiement Render
├── Procfile                    # NOUVEAU: Config déploiement Heroku
│
├── generate_scenarios_json.py  # Existant (backup/validation)
├── validation_scenarios.py     # Existant (tests)
└── IMPLEMENTATION_GUIDE.md     # Ce fichier
```

### 2.2 Dépendances

**requirements.txt**:
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
numpy>=1.24.0
pandas>=2.0.0
python-multipart==0.0.6
```

---

## 3. Phase 1: API FastAPI

### 3.1 Fichier `api.py` complet

```python
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
```

---

## 4. Phase 2: Frontend interactif

### 4.1 Fichier `index.html` complet

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analyse Coûts-Bénéfices — Compteurs d'Eau Québec</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #1a5f7a;
            --primary-light: #2d8bba;
            --secondary: #57c5b6;
            --accent: #159895;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #1e293b;
            --text-light: #64748b;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border: #e2e8f0;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }

        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            padding: 1.5rem 2rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }

        .header h1 { font-size: 1.75rem; font-weight: 600; }
        .header p { opacity: 0.9; font-size: 0.95rem; margin-top: 0.25rem; }

        .container {
            display: grid;
            grid-template-columns: 400px 1fr;
            gap: 1.5rem;
            padding: 1.5rem;
            max-width: 1900px;
            margin: 0 auto;
        }

        @media (max-width: 1200px) {
            .container { grid-template-columns: 1fr; }
        }

        .sidebar { display: flex; flex-direction: column; gap: 1rem; }

        .card {
            background: var(--card);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid var(--border);
        }

        .card-title {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .card-title::before {
            content: '';
            width: 4px;
            height: 16px;
            background: var(--secondary);
            border-radius: 2px;
        }

        .input-group { margin-bottom: 1rem; }
        .input-group:last-child { margin-bottom: 0; }

        .input-group label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            color: var(--text-light);
            margin-bottom: 0.35rem;
        }

        .input-group .value {
            font-weight: 600;
            color: var(--text);
            font-family: 'SF Mono', 'Consolas', monospace;
        }

        input[type="range"] {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: var(--border);
            outline: none;
            -webkit-appearance: none;
        }

        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: var(--primary);
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transition: transform 0.15s;
        }

        input[type="range"]::-webkit-slider-thumb:hover { transform: scale(1.1); }

        select {
            width: 100%;
            padding: 0.5rem 0.75rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.9rem;
            background: white;
            cursor: pointer;
        }

        select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(26,95,122,0.1);
        }

        .main { display: flex; flex-direction: column; gap: 1.5rem; }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }

        .metric-card {
            background: var(--card);
            border-radius: 12px;
            padding: 1.25rem;
            border: 1px solid var(--border);
            text-align: center;
        }

        .metric-card.highlight {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            border: none;
        }

        .metric-card.highlight .metric-label { color: rgba(255,255,255,0.85); }

        .metric-value { font-size: 1.75rem; font-weight: 700; line-height: 1.2; }
        .metric-label {
            font-size: 0.75rem;
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 0.25rem;
        }

        .metric-card.positive .metric-value { color: var(--success); }
        .metric-card.negative .metric-value { color: var(--danger); }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
        }

        @media (max-width: 900px) {
            .charts-grid { grid-template-columns: 1fr; }
        }

        .chart-container {
            background: var(--card);
            border-radius: 12px;
            padding: 1.25rem;
            border: 1px solid var(--border);
        }

        .chart-container h3 {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text);
        }

        .chart-wrapper { position: relative; height: 280px; }

        .recommendation {
            padding: 1rem 1.25rem;
            border-radius: 8px;
            font-size: 0.95rem;
        }

        .recommendation.positive {
            background: #ecfdf5;
            border: 1px solid #a7f3d0;
            color: #065f46;
        }

        .recommendation.negative {
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #991b1b;
        }

        .recommendation.warning {
            background: #fffbeb;
            border: 1px solid #fde68a;
            color: #92400e;
        }

        .toggle-container {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.5rem 0;
        }

        .toggle {
            position: relative;
            width: 48px;
            height: 26px;
            background: var(--border);
            border-radius: 13px;
            cursor: pointer;
            transition: background 0.3s;
        }

        .toggle.active { background: var(--primary); }

        .toggle::after {
            content: '';
            position: absolute;
            top: 3px;
            left: 3px;
            width: 20px;
            height: 20px;
            background: white;
            border-radius: 50%;
            transition: transform 0.3s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .toggle.active::after { transform: translateX(22px); }

        .toggle-label { font-size: 0.85rem; color: var(--text-light); }

        .preset-buttons {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 1rem;
        }

        .preset-btn {
            padding: 0.4rem 0.75rem;
            border: 1px solid var(--border);
            background: white;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .preset-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
        }

        .preset-btn.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .loading {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--primary);
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 0.3s;
            z-index: 1000;
        }

        .loading.active { transform: scaleX(1); }

        .footer {
            text-align: center;
            padding: 1.5rem;
            color: var(--text-light);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 1rem;
        }

        .footer a { color: var(--primary); text-decoration: none; }

        .breakdown-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            margin-top: 1rem;
        }

        .breakdown-table th,
        .breakdown-table td {
            padding: 0.5rem 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }

        .breakdown-table th {
            background: var(--bg);
            font-weight: 600;
            color: var(--text-light);
            text-transform: uppercase;
            font-size: 0.75rem;
        }

        .breakdown-table td:last-child {
            text-align: right;
            font-family: 'SF Mono', 'Consolas', monospace;
        }

        .api-status {
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            margin-left: auto;
        }

        .api-status.connected {
            background: #dcfce7;
            color: #166534;
        }

        .api-status.disconnected {
            background: #fee2e2;
            color: #991b1b;
        }
    </style>
</head>
<body>
    <div class="loading" id="loading"></div>

    <div class="header">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div>
                <h1>Analyse Coûts-Bénéfices — Compteurs d'Eau</h1>
                <p>Modèle interactif v3.10 — Python backend</p>
            </div>
            <span class="api-status disconnected" id="api-status">API: Connexion...</span>
        </div>
    </div>

    <div class="container">
        <div class="sidebar">
            <!-- Presets -->
            <div class="card">
                <div class="card-title">Préréglages</div>
                <div class="preset-buttons">
                    <button class="preset-btn active" onclick="loadPreset('longueuil')">Longueuil</button>
                    <button class="preset-btn" onclick="loadPreset('montreal')">Montréal</button>
                    <button class="preset-btn" onclick="loadPreset('quebec')">Québec</button>
                    <button class="preset-btn" onclick="loadPreset('winnipeg')">Winnipeg</button>
                </div>
            </div>

            <!-- Paramètres du projet -->
            <div class="card">
                <div class="card-title">Paramètres du projet</div>

                <div class="input-group">
                    <label>Nombre de ménages <span class="value" id="val-menages">116,258</span></label>
                    <input type="range" id="nb-menages" min="10000" max="1000000" step="1000" value="116258" oninput="onParamChange()">
                </div>

                <div class="input-group">
                    <label>Taille ménage (pers) <span class="value" id="val-taille">2.18</span></label>
                    <input type="range" id="taille-menage" min="1.5" max="4" step="0.01" value="2.18" oninput="onParamChange()">
                </div>

                <div class="input-group">
                    <label>LPCD (L/pers/jour) <span class="value" id="val-lpcd">236</span></label>
                    <input type="range" id="lpcd" min="150" max="450" step="1" value="236" oninput="onParamChange()">
                </div>

                <div class="input-group">
                    <label>Horizon d'analyse (ans) <span class="value" id="val-horizon">20</span></label>
                    <input type="range" id="horizon" min="10" max="30" step="1" value="20" oninput="onParamChange()">
                </div>

                <div class="input-group">
                    <label>Taux d'actualisation (%) <span class="value" id="val-taux">3.0</span></label>
                    <input type="range" id="taux-actualisation" min="1" max="8" step="0.1" value="3" oninput="onParamChange()">
                </div>
            </div>

            <!-- Coûts du compteur -->
            <div class="card">
                <div class="card-title">Coûts du compteur</div>

                <div class="input-group">
                    <label>Type de compteur</label>
                    <select id="type-compteur" onchange="onParamChange()">
                        <option value="ami">AMI (intelligent)</option>
                        <option value="amr">AMR (lecture auto)</option>
                        <option value="manuel">Manuel</option>
                    </select>
                </div>

                <div class="input-group">
                    <label>Coût compteur ($) <span class="value" id="val-cout-compteur">250</span></label>
                    <input type="range" id="cout-compteur" min="50" max="600" step="10" value="250" oninput="onParamChange()">
                </div>

                <div class="input-group">
                    <label>Heures installation <span class="value" id="val-heures">3.0</span></label>
                    <input type="range" id="heures-install" min="0.5" max="8" step="0.5" value="3" oninput="onParamChange()">
                </div>

                <div class="input-group">
                    <label>Taux horaire ($/h) <span class="value" id="val-taux-horaire">125</span></label>
                    <input type="range" id="taux-horaire" min="75" max="200" step="5" value="125" oninput="onParamChange()">
                </div>

                <div class="input-group" id="cout-reseau-group">
                    <label>Coût réseau/compteur ($) <span class="value" id="val-cout-reseau">50</span></label>
                    <input type="range" id="cout-reseau" min="0" max="200" step="10" value="50" oninput="onParamChange()">
                </div>
            </div>

            <!-- Comportement & Fuites -->
            <div class="card">
                <div class="card-title">Comportement & Fuites</div>

                <div class="input-group">
                    <label>Réduction comportementale (%) <span class="value" id="val-reduction">8.0</span></label>
                    <input type="range" id="reduction-comportement" min="0" max="15" step="0.5" value="8" oninput="onParamChange()">
                </div>

                <div class="input-group">
                    <label>Scénario de persistance</label>
                    <select id="persistance" onchange="onParamChange()">
                        <option value="optimiste">Optimiste (effet constant)</option>
                        <option value="realiste" selected>Réaliste (plateau 2.5%)</option>
                        <option value="pessimiste">Pessimiste (fadeout 10 ans)</option>
                        <option value="ultra">Ultra-pessimiste (aucun effet)</option>
                    </select>
                </div>

                <div class="input-group">
                    <label>Scénario de fuites</label>
                    <select id="scenario-fuites" onchange="onParamChange()">
                        <option value="standard">Standard (20%, 35 m³/an)</option>
                        <option value="quebec">Contexte Québec (35%, 35 m³/an)</option>
                        <option value="deux_stocks" selected>Deux-stocks Québec</option>
                    </select>
                </div>
            </div>

            <!-- Paramètres économiques -->
            <div class="card">
                <div class="card-title">Paramètres économiques</div>

                <div class="toggle-container">
                    <div class="toggle" id="mode-toggle" onclick="toggleMode()"></div>
                    <span class="toggle-label" id="mode-label">Mode Économique (valeur sociale)</span>
                </div>

                <div class="input-group">
                    <label>Valeur sociale eau ($/m³) <span class="value" id="val-valeur-sociale">4.69</span></label>
                    <input type="range" id="valeur-sociale" min="1" max="12" step="0.1" value="4.69" oninput="onParamChange()">
                </div>

                <div class="input-group">
                    <label>Coût variable ($/m³) <span class="value" id="val-cout-variable">0.50</span></label>
                    <input type="range" id="cout-variable" min="0.1" max="2" step="0.05" value="0.5" oninput="onParamChange()">
                </div>
            </div>
        </div>

        <div class="main">
            <!-- Métriques principales -->
            <div class="metrics-grid">
                <div class="metric-card highlight">
                    <div class="metric-value" id="metric-van">—</div>
                    <div class="metric-label">VAN (20 ans)</div>
                </div>
                <div class="metric-card positive">
                    <div class="metric-value" id="metric-rbc">—</div>
                    <div class="metric-label">Ratio B/C</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="metric-payback">—</div>
                    <div class="metric-label">Récupération (ans)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="metric-lcsw">—</div>
                    <div class="metric-label">LCSW ($/m³)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="metric-invest">—</div>
                    <div class="metric-label">Investissement</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="metric-economies">—</div>
                    <div class="metric-label">Économies (m³/mén/an)</div>
                </div>
            </div>

            <!-- Recommandation -->
            <div class="recommendation positive" id="recommendation">
                Chargement...
            </div>

            <!-- Graphiques -->
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>VAN Cumulative</h3>
                    <div class="chart-wrapper">
                        <canvas id="chart-van"></canvas>
                    </div>
                </div>

                <div class="chart-container">
                    <h3>Comparaison Types de Compteurs</h3>
                    <div class="chart-wrapper">
                        <canvas id="chart-types"></canvas>
                    </div>
                </div>

                <div class="chart-container">
                    <h3>Scénarios de Persistance</h3>
                    <div class="chart-wrapper">
                        <canvas id="chart-persistance"></canvas>
                    </div>
                </div>

                <div class="chart-container">
                    <h3>Sensibilité des Paramètres</h3>
                    <div class="chart-wrapper">
                        <canvas id="chart-sensitivity"></canvas>
                    </div>
                </div>

                <div class="chart-container">
                    <h3>Courbe α Comportement</h3>
                    <div class="chart-wrapper">
                        <canvas id="chart-alpha"></canvas>
                    </div>
                </div>

                <div class="chart-container">
                    <h3>Économique vs Financier</h3>
                    <div class="chart-wrapper">
                        <canvas id="chart-perspectives"></canvas>
                    </div>
                </div>
            </div>

            <!-- Détail des flux -->
            <div class="card">
                <div class="card-title">Détail des flux (calculés par Python)</div>
                <table class="breakdown-table">
                    <thead>
                        <tr>
                            <th>Composante</th>
                            <th>Valeur</th>
                        </tr>
                    </thead>
                    <tbody id="breakdown-body">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="footer">
        Modèle développé par Enzo Simier (HEC Montréal) — Projet Mitacs / Réseau Environnement<br>
        Backend Python v3.10 — <a href="https://github.com/EnzoSim/compteurs.QC">GitHub</a>
    </div>

    <script>
        // ============================================================
        // CONFIGURATION
        // ============================================================

        // URL de l'API - À MODIFIER selon le déploiement
        // Local: 'http://localhost:8000'
        // Render: 'https://votre-app.onrender.com'
        const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? `http://${window.location.hostname}:8000`
            : '';  // Même origine si déployé ensemble

        let modeEconomique = true;
        let debounceTimer = null;
        let charts = {};

        // ============================================================
        // INITIALISATION
        // ============================================================

        document.addEventListener('DOMContentLoaded', async () => {
            initCharts();
            await checkApiHealth();
            await updateModel();
        });

        async function checkApiHealth() {
            try {
                const response = await fetch(`${API_URL}/api/health`);
                if (response.ok) {
                    document.getElementById('api-status').textContent = 'API: Connecté';
                    document.getElementById('api-status').className = 'api-status connected';
                }
            } catch (e) {
                document.getElementById('api-status').textContent = 'API: Déconnecté';
                document.getElementById('api-status').className = 'api-status disconnected';
            }
        }

        // ============================================================
        // COLLECTE DES PARAMÈTRES
        // ============================================================

        function collectParams() {
            return {
                nb_menages: parseInt(document.getElementById('nb-menages').value),
                taille_menage: parseFloat(document.getElementById('taille-menage').value),
                lpcd: parseInt(document.getElementById('lpcd').value),
                horizon: parseInt(document.getElementById('horizon').value),
                taux_actualisation: parseFloat(document.getElementById('taux-actualisation').value),
                type_compteur: document.getElementById('type-compteur').value,
                cout_compteur: parseFloat(document.getElementById('cout-compteur').value),
                heures_installation: parseFloat(document.getElementById('heures-install').value),
                taux_horaire: parseFloat(document.getElementById('taux-horaire').value),
                cout_reseau: parseFloat(document.getElementById('cout-reseau').value),
                reduction_comportement: parseFloat(document.getElementById('reduction-comportement').value),
                persistance: document.getElementById('persistance').value,
                scenario_fuites: document.getElementById('scenario-fuites').value,
                mode_economique: modeEconomique,
                valeur_sociale: parseFloat(document.getElementById('valeur-sociale').value),
                cout_variable: parseFloat(document.getElementById('cout-variable').value),
            };
        }

        // ============================================================
        // APPELS API
        // ============================================================

        async function apiCall(endpoint, data = null) {
            const loading = document.getElementById('loading');
            loading.classList.add('active');

            try {
                const options = {
                    method: data ? 'POST' : 'GET',
                    headers: { 'Content-Type': 'application/json' },
                };
                if (data) options.body = JSON.stringify(data);

                const response = await fetch(`${API_URL}${endpoint}`, options);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return await response.json();
            } catch (e) {
                console.error('API Error:', e);
                throw e;
            } finally {
                loading.classList.remove('active');
            }
        }

        // ============================================================
        // MISE À JOUR DU MODÈLE
        // ============================================================

        function onParamChange() {
            // Debounce pour éviter trop d'appels API
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(updateModel, 150);

            // Mise à jour immédiate des labels
            updateLabels();
        }

        function updateLabels() {
            document.getElementById('val-menages').textContent = parseInt(document.getElementById('nb-menages').value).toLocaleString('fr-CA');
            document.getElementById('val-taille').textContent = parseFloat(document.getElementById('taille-menage').value).toFixed(2);
            document.getElementById('val-lpcd').textContent = document.getElementById('lpcd').value;
            document.getElementById('val-horizon').textContent = document.getElementById('horizon').value;
            document.getElementById('val-taux').textContent = parseFloat(document.getElementById('taux-actualisation').value).toFixed(1);
            document.getElementById('val-cout-compteur').textContent = document.getElementById('cout-compteur').value;
            document.getElementById('val-heures').textContent = parseFloat(document.getElementById('heures-install').value).toFixed(1);
            document.getElementById('val-taux-horaire').textContent = document.getElementById('taux-horaire').value;
            document.getElementById('val-cout-reseau').textContent = document.getElementById('cout-reseau').value;
            document.getElementById('val-reduction').textContent = parseFloat(document.getElementById('reduction-comportement').value).toFixed(1);
            document.getElementById('val-valeur-sociale').textContent = parseFloat(document.getElementById('valeur-sociale').value).toFixed(2);
            document.getElementById('val-cout-variable').textContent = parseFloat(document.getElementById('cout-variable').value).toFixed(2);

            // Afficher/masquer coût réseau selon type compteur
            document.getElementById('cout-reseau-group').style.display =
                document.getElementById('type-compteur').value === 'ami' ? 'block' : 'none';
        }

        async function updateModel() {
            try {
                const params = collectParams();

                // Appel principal
                const result = await apiCall('/api/calculate', params);
                updateDisplay(result);

                // Appels secondaires en parallèle
                const [sensitivity, meters, persistence] = await Promise.all([
                    apiCall('/api/sensitivity', params),
                    apiCall('/api/compare_meters', params),
                    apiCall('/api/compare_persistence', params),
                ]);

                updateSensitivityChart(sensitivity);
                updateMetersChart(meters);
                updatePersistenceChart(persistence, result);
                await updatePerspectivesChart(params);

            } catch (e) {
                document.getElementById('recommendation').className = 'recommendation negative';
                document.getElementById('recommendation').innerHTML =
                    `<strong>Erreur de connexion à l'API</strong><br>Vérifiez que le serveur Python est lancé: <code>uvicorn api:app --reload</code>`;
            }
        }

        // ============================================================
        // AFFICHAGE DES RÉSULTATS
        // ============================================================

        function formatMoney(value) {
            if (Math.abs(value) >= 1e9) return (value / 1e9).toFixed(1) + ' G$';
            if (Math.abs(value) >= 1e6) return (value / 1e6).toFixed(1) + ' M$';
            if (Math.abs(value) >= 1e3) return (value / 1e3).toFixed(0) + ' k$';
            return value.toFixed(0) + ' $';
        }

        function updateDisplay(result) {
            // Métriques
            document.getElementById('metric-van').textContent = formatMoney(result.van);
            document.getElementById('metric-rbc').textContent = result.rbc.toFixed(2);
            document.getElementById('metric-payback').textContent = result.payback ? result.payback.toFixed(1) : '>20';
            document.getElementById('metric-lcsw').textContent = result.lcsw.toFixed(2);
            document.getElementById('metric-invest').textContent = formatMoney(result.investissement_initial);
            document.getElementById('metric-economies').textContent = result.economie_totale_menage.toFixed(1);

            // Couleur RBC
            const rbcCard = document.getElementById('metric-rbc').parentElement;
            rbcCard.className = 'metric-card ' + (result.rbc >= 1 ? 'positive' : 'negative');

            // Recommandation
            const recEl = document.getElementById('recommendation');
            if (result.viable) {
                recEl.className = 'recommendation positive';
                recEl.innerHTML = `<strong>PROJET VIABLE</strong> — ${result.recommandation}`;
            } else if (result.van > 0) {
                recEl.className = 'recommendation warning';
                recEl.innerHTML = `<strong>PROJET MARGINAL</strong> — ${result.recommandation}`;
            } else {
                recEl.className = 'recommendation negative';
                recEl.innerHTML = `<strong>PROJET NON RENTABLE</strong> — ${result.recommandation}`;
            }

            // Graphique VAN cumulative
            charts.van.data.labels = result.annees;
            charts.van.data.datasets[0].data = result.van_cumulative.map(v => v / 1e6);
            charts.van.update('none');

            // Graphique Alpha
            charts.alpha.data.labels = result.annees;
            charts.alpha.data.datasets[0].data = result.serie_alpha;
            charts.alpha.update('none');

            // Tableau de détail
            document.getElementById('breakdown-body').innerHTML = `
                <tr><td>Bénéfices eau (VA)</td><td>${formatMoney(result.va_benefices)}</td></tr>
                <tr><td>Investissement initial</td><td>${formatMoney(-result.investissement_initial)}</td></tr>
                <tr><td>Coûts exploitation (VA)</td><td>${formatMoney(-result.va_couts_exploitation)}</td></tr>
                <tr><td>Économie comportement/ménage</td><td>${result.economie_comportement_menage.toFixed(2)} m³/an</td></tr>
                <tr><td>Économie fuites/ménage</td><td>${result.economie_fuite_menage.toFixed(2)} m³/an</td></tr>
                <tr><td>Usage base/ménage</td><td>${result.usage_base_menage.toFixed(1)} m³/an</td></tr>
                <tr><td>Coût par compteur</td><td>${result.cout_par_compteur.toFixed(0)} $</td></tr>
                <tr style="font-weight:600;border-top:2px solid var(--primary)">
                    <td>Valeur Actualisée Nette</td><td>${formatMoney(result.van)}</td>
                </tr>
            `;
        }

        function updateSensitivityChart(data) {
            charts.sensitivity.data.labels = data.parametres.map(p => p.nom);
            charts.sensitivity.data.datasets[0].data = data.parametres.map(p => p.impact_low / 1e6);
            charts.sensitivity.data.datasets[1].data = data.parametres.map(p => p.impact_high / 1e6);
            charts.sensitivity.update('none');
        }

        function updateMetersChart(data) {
            charts.types.data.datasets[0].data = [
                data.ami.van / 1e6,
                data.amr.van / 1e6,
                data.manuel.van / 1e6
            ];
            charts.types.update('none');
        }

        function updatePersistenceChart(data, currentResult) {
            const years = currentResult.annees;
            charts.persistance.data.labels = years;
            charts.persistance.data.datasets[0].data = data.optimiste.van_cumulative.map(v => v / 1e6);
            charts.persistance.data.datasets[1].data = data.realiste.van_cumulative.map(v => v / 1e6);
            charts.persistance.data.datasets[2].data = data.pessimiste.van_cumulative.map(v => v / 1e6);
            charts.persistance.update('none');
        }

        async function updatePerspectivesChart(params) {
            const paramsEco = { ...params, mode_economique: true };
            const paramsFin = { ...params, mode_economique: false };

            const [resEco, resFin] = await Promise.all([
                apiCall('/api/calculate', paramsEco),
                apiCall('/api/calculate', paramsFin),
            ]);

            charts.perspectives.data.datasets[0].data = [
                resEco.va_benefices / 1e6,
                resEco.va_couts_totaux / 1e6,
                resEco.van / 1e6
            ];
            charts.perspectives.data.datasets[1].data = [
                resFin.va_benefices / 1e6,
                resFin.va_couts_totaux / 1e6,
                resFin.van / 1e6
            ];
            charts.perspectives.update('none');
        }

        // ============================================================
        // PRESETS ET TOGGLE
        // ============================================================

        async function loadPreset(ville) {
            const presets = {
                longueuil: { nb_menages: 116258, taille_menage: 2.18, lpcd: 236 },
                montreal: { nb_menages: 750000, taille_menage: 2.1, lpcd: 332 },
                quebec: { nb_menages: 180000, taille_menage: 2.15, lpcd: 280 },
                winnipeg: { nb_menages: 221000, taille_menage: 2.3, lpcd: 250 },
            };

            const preset = presets[ville];
            if (!preset) return;

            document.getElementById('nb-menages').value = preset.nb_menages;
            document.getElementById('taille-menage').value = preset.taille_menage;
            document.getElementById('lpcd').value = preset.lpcd;

            // Update buttons
            document.querySelectorAll('.preset-btn').forEach(btn => {
                btn.classList.toggle('active', btn.textContent.toLowerCase().includes(ville));
            });

            updateLabels();
            await updateModel();
        }

        function toggleMode() {
            modeEconomique = !modeEconomique;
            const toggle = document.getElementById('mode-toggle');
            const label = document.getElementById('mode-label');

            toggle.classList.toggle('active', !modeEconomique);
            label.textContent = modeEconomique
                ? 'Mode Économique (valeur sociale)'
                : 'Mode Financier (coût variable)';

            updateModel();
        }

        // ============================================================
        // INITIALISATION DES GRAPHIQUES
        // ============================================================

        function initCharts() {
            // VAN Cumulative
            charts.van = new Chart(document.getElementById('chart-van').getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'VAN Cumulative',
                        data: [],
                        borderColor: '#1a5f7a',
                        backgroundColor: 'rgba(26, 95, 122, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { title: { display: true, text: 'Année' } },
                        y: { title: { display: true, text: 'M$' } }
                    }
                }
            });

            // Types de compteurs
            charts.types = new Chart(document.getElementById('chart-types').getContext('2d'), {
                type: 'bar',
                data: {
                    labels: ['AMI', 'AMR', 'Manuel'],
                    datasets: [{
                        data: [],
                        backgroundColor: ['#1a5f7a', '#2d8bba', '#57c5b6']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { title: { display: true, text: 'VAN (M$)' } } }
                }
            });

            // Persistance
            charts.persistance = new Chart(document.getElementById('chart-persistance').getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'Optimiste', data: [], borderColor: '#10b981', tension: 0.4, pointRadius: 0 },
                        { label: 'Réaliste', data: [], borderColor: '#3b82f6', tension: 0.4, pointRadius: 0 },
                        { label: 'Pessimiste', data: [], borderColor: '#ef4444', tension: 0.4, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { title: { display: true, text: 'Année' } },
                        y: { title: { display: true, text: 'VAN (M$)' } }
                    }
                }
            });

            // Sensibilité
            charts.sensitivity = new Chart(document.getElementById('chart-sensitivity').getContext('2d'), {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [
                        { label: '-10%', data: [], backgroundColor: '#ef4444' },
                        { label: '+10%', data: [], backgroundColor: '#10b981' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    scales: { x: { title: { display: true, text: 'Impact VAN (M$)' } } }
                }
            });

            // Alpha
            charts.alpha = new Chart(document.getElementById('chart-alpha').getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'α (%)',
                        data: [],
                        borderColor: '#3b82f6',
                        tension: 0.4,
                        pointRadius: 0,
                        fill: true,
                        backgroundColor: 'rgba(59, 130, 246, 0.1)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { title: { display: true, text: 'Année' } },
                        y: { title: { display: true, text: 'α (%)' }, min: 0 }
                    }
                }
            });

            // Perspectives
            charts.perspectives = new Chart(document.getElementById('chart-perspectives').getContext('2d'), {
                type: 'bar',
                data: {
                    labels: ['Bénéfices', 'Coûts', 'VAN'],
                    datasets: [
                        { label: 'Économique', data: [], backgroundColor: '#1a5f7a' },
                        { label: 'Financier', data: [], backgroundColor: '#57c5b6' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { title: { display: true, text: 'M$' } } }
                }
            });
        }
    </script>
</body>
</html>
```

---

## 5. Phase 3: Déploiement

### 5.1 Option A: Local (développement)

```bash
cd /Users/enzo_simier/Desktop/Water

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
uvicorn api:app --reload --port 8000

# Ouvrir http://localhost:8000
```

### 5.2 Option B: Render.com (gratuit, recommandé)

**Fichier `render.yaml`**:
```yaml
services:
  - type: web
    name: compteurs-eau-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
```

**Étapes**:
1. Push tous les fichiers sur GitHub
2. Aller sur https://render.com
3. New > Web Service
4. Connecter le repo GitHub
5. Render détecte automatiquement `render.yaml`
6. Deploy

**URL finale**: `https://compteurs-eau-api.onrender.com`

### 5.3 Option C: Railway.app (gratuit)

```bash
# Installer Railway CLI
npm install -g @railway/cli

# Login et déployer
railway login
railway init
railway up
```

### 5.4 Option D: Heroku

**Fichier `Procfile`**:
```
web: uvicorn api:app --host 0.0.0.0 --port $PORT
```

```bash
heroku create compteurs-eau-qc
git push heroku main
```

---

## 6. Commandes récapitulatives

### Développement local

```bash
cd /Users/enzo_simier/Desktop/Water

# 1. Créer requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
numpy>=1.24.0
pandas>=2.0.0
python-multipart==0.0.6
EOF

# 2. Installer
pip install -r requirements.txt

# 3. Lancer
uvicorn api:app --reload --port 8000

# 4. Ouvrir
open http://localhost:8000
```

### Push GitHub

```bash
git add api.py index.html requirements.txt render.yaml IMPLEMENTATION_GUIDE.md
git commit -m "Add interactive web app with FastAPI backend"
git push origin main
```

### Déploiement Render

1. Aller sur https://dashboard.render.com
2. New > Web Service
3. Connect GitHub repo `EnzoSim/compteurs.QC`
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
5. Create Web Service
6. Attendre le déploiement (~2-3 min)
7. URL: `https://compteurs-qc.onrender.com`

---

## Checklist finale

- [ ] `api.py` créé et testé localement
- [ ] `index.html` créé et testé localement
- [ ] `requirements.txt` créé
- [ ] `render.yaml` créé
- [ ] Tous les fichiers pushés sur GitHub
- [ ] Déploiement Render configuré
- [ ] URL finale fonctionnelle
- [ ] Tests avec différents paramètres
- [ ] Documentation mise à jour

---

**Fin du guide d'implémentation**
