# CLAUDE.md - AI Assistant Guide for compteurs.QC

## Project Overview

**Compteurs d'Eau Quebec** - A cost-benefit analysis (CBA) tool for intelligent water metering (AMI - Advanced Metering Infrastructure) in Quebec municipalities. The tool evaluates economic viability of installing smart water meters by modeling consumption savings, leak detection, infrastructure benefits, and deployment strategies over a 20-year horizon.

**Current Version**: 3.11.0

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn api:app --reload --port 8000

# Run tests
pytest test_api.py -v

# Run validation scenarios (non-regression tests)
python validation_scenarios.py

# Update data pipeline (manual)
python -m map.collectors.build_data
```

## Repository Structure

```
compteurs.QC/
├── api.py                       # FastAPI backend (REST API)
├── analyse_compteurs_eau.py     # Core economic model (single source of truth)
├── index.html                   # Frontend SPA (calculator interface)
├── translations.js              # i18n (French/English)
├── test_api.py                  # API integration tests
├── validation_scenarios.py      # Non-regression tests with golden scenarios
├── generate_scenarios_json.py   # Pre-compute scenarios for static export
├── scenarios_output.json        # Pre-computed scenarios data
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render.com deployment config
├── TASKS.md                     # Architecture decisions & optimization notes
│
└── map/                         # Municipality data & visualization
    ├── index.html               # Leaflet-based map interface
    ├── map.js                   # Map component logic
    ├── data/
    │   ├── current/             # Active datasets
    │   │   ├── quebec-municipalities.geojson
    │   │   ├── municipalities-stats.json
    │   │   ├── mamh-data.json
    │   │   ├── bil-data.json
    │   │   └── metadata.json
    │   ├── history/             # Archived yearly versions
    │   ├── cache/               # Fallback data
    │   └── DATA_DICTIONARY.md   # Field definitions
    │
    └── collectors/              # Data pipeline scripts
        ├── config.py            # Centralized configuration
        ├── overpass_collector.py
        ├── statcan_collector.py
        ├── mamh_collector.py
        ├── data_merger.py
        ├── cache_manager.py
        ├── qa_validator.py
        ├── build_data.py        # Local pipeline orchestration
        └── run_update.py        # Cron entry point
```

## Key Files & Responsibilities

| File | LOC | Purpose |
|------|-----|---------|
| `analyse_compteurs_eau.py` | ~10,200 | Core CBA economic simulation engine |
| `api.py` | ~1,860 | FastAPI REST API serving the calculator |
| `index.html` | ~5,000 | Single-page application frontend |
| `test_api.py` | ~350 | API integration tests (pytest) |
| `validation_scenarios.py` | ~480 | Non-regression tests with golden scenarios |

## Architecture

### Core Economic Model (`analyse_compteurs_eau.py`)

This is the **single source of truth** for all economic calculations. Key components:

- **Enums**: `TypeCompteur`, `ModeCompte`, `ModePersistance`, `ModeAdoption`, etc.
- **Dataclasses**: `ParametresModele`, `ParametresCompteur`, `ParametresPersistance`, `ParametresFuites`, `ParametresAdoption`
- **Presets**: `FUITES_*`, `PERSISTANCE_*`, `VALEUR_EAU_*`, `STRATEGIES_ADOPTION`
- **Main function**: `executer_modele()` - orchestrates full 20-year simulation

### API Layer (`api.py`)

FastAPI REST endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/calculate` | POST | Main calculation (live on slider change) |
| `/api/sensitivity` | POST | ±10% sensitivity analysis |
| `/api/detailed_series` | POST | Time-series data (leaks, behavior) |
| `/api/monte_carlo` | POST | Uncertainty analysis (default 500 sims) |
| `/api/compare_meters` | POST | Compare AMI vs AMR vs Manuel |
| `/api/compare_persistence` | POST | Compare persistence scenarios |
| `/api/compare_fuites` | POST | Compare leak scenarios |
| `/api/perspectives` | POST | VAN decomposition by perspective |
| `/api/presets` | GET | City presets |
| `/api/optimize_deployment` | POST | Optimal deployment scheduling |
| `/api/health` | GET | Health check with metrics |
| `/api/metrics` | GET | Prometheus-format metrics |

### Frontend (`index.html`)

SPA with reactive patterns:
- Sliders trigger `onParamChange()` with debounced API calls
- Global `globalRequestId` prevents stale responses
- Chart.js for data visualization
- All strings via `TRANSLATIONS` object (FR/EN)

## Code Conventions

### Python

1. **Language**: French for variables/functions, English for class names
   ```python
   # Good
   def calculer_alpha_comportement(annee: int, lambda_decay: float) -> float:
   class ParametresModele:

   # Variables
   nb_menages, taux_actualisation, horizon, lpcd
   ```

2. **Type Hints**: Required on all functions
   ```python
   def executer_modele(params: ParametresModele, ...) -> Dict[str, Any]:
   ```

3. **Dataclasses**: Use for configuration objects
   ```python
   @dataclass
   class ParametresCompteur:
       type_compteur: TypeCompteur = TypeCompteur.AMI
       cout_compteur: float = 250.0
   ```

4. **Constants**: SCREAMING_SNAKE_CASE for presets
   ```python
   FUITES_DEUX_STOCKS = ParametresFuites(...)
   PERSISTANCE_OPTIMISTE = ParametresPersistance(...)
   ```

5. **Docstrings**: French, explaining purpose and parameters
   ```python
   def calculer_dynamique_fuites(annee: int, params_fuites: ParametresFuites) -> Dict:
       """
       Calcule la dynamique des fuites pour une année donnée.

       Args:
           annee: Année de simulation (1-20)
           params_fuites: Paramètres du modèle de fuites

       Returns:
           Dict contenant taux_detection, taux_reparation, economies
       """
   ```

### API Patterns

1. **POST for calculations**: Stateless, body contains all parameters
2. **Pydantic Models**: Request/response validation with Field descriptions
3. **Error handling**: HTTPException with descriptive messages
4. **Observability**: StructuredLogger + MetricsCollector

### Frontend Patterns

1. **Debouncing**: Prevent rapid API calls on slider changes
2. **Request cancellation**: Use `globalRequestId` to ignore stale responses
3. **Translation**: All UI strings via `TRANSLATIONS[currentLanguage]`

## Testing

### API Tests (`test_api.py`)

```bash
pytest test_api.py -v
```

- Uses FastAPI TestClient
- Golden scenarios for regression testing
- Cross-endpoint coherence validation

### Validation Scenarios (`validation_scenarios.py`)

```bash
python validation_scenarios.py
```

- 10 canonical scenarios (cities × configurations)
- ±1% tolerance for numerical comparisons
- Generates human-readable validation report

## Key Domain Concepts

### Meter Types
- **AMI** (Advanced Metering Infrastructure): Smart meters with real-time data
- **AMR** (Automatic Meter Reading): Drive-by reading
- **Manuel**: Traditional manual reading

### Persistence Models
- **Optimiste**: Behavioral changes persist longer
- **Realiste**: Moderate decay over time
- **Pessimiste**: Rapid return to baseline behavior
- **Ultra**: Extreme pessimistic decay

### Leak Scenarios
- **deux_stocks**: With tarification incentive
- **deux_stocks_sans_tarif**: Without tarification
- **baseline_simple**: Basic leak model

### Adoption Strategies
- **obligatoire**: Mandatory installation Year 1
- **rapide**: Fast rollout (3 years)
- **progressive**: Gradual (5 years)
- **lente**: Slow rollout (7-10 years)
- **par_secteur**: Sector-by-sector deployment

## Important Constraints

1. **Single Source of Truth**: All presets and calculations defined in `analyse_compteurs_eau.py`. Never duplicate logic.

2. **Path Traversal Protection**: API validates file paths in static file serving using `Path.resolve()`.

3. **Race Condition Handling**: Frontend uses `globalRequestId` to prevent stale API responses.

4. **Numerical Precision**: Use `math.isclose()` or ±1% tolerance for comparing calculated values.

5. **Data Pipeline Resilience**: Collectors must use cache fallback if sources fail.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CORS_ORIGINS` | `*` | CORS allowed origins |
| `PORT` | `8000` | Server port (Render sets this) |
| `PYTHON_VERSION` | `3.10.0` | Python version for deployment |

## Common Tasks

### Adding a New Preset

1. Define in `analyse_compteurs_eau.py` (e.g., `FUITES_NEW_SCENARIO`)
2. Export in `api.py` preset endpoint if needed
3. Add to frontend dropdown in `index.html`
4. Add test case in `test_api.py`

### Adding a New API Endpoint

1. Define Pydantic request/response models in `api.py`
2. Implement endpoint function with proper error handling
3. Add test in `test_api.py`
4. Document in this file

### Updating Data Pipeline

1. Modify collector in `map/collectors/`
2. Update `data_merger.py` if schema changes
3. Run `python -m map.collectors.build_data` to test
4. Update `DATA_DICTIONARY.md` if fields change

## Deployment

- **Platform**: Render.com (see `render.yaml`)
- **Auto-deploy**: Pushes to main trigger deployment
- **Data updates**: Cron job runs `python -m map.collectors.run_update`

## Files to Never Modify

- `map/data/cache/` - Auto-generated cache
- `map/data/history/` - Archived historical data
- `scenarios_output.json` - Generated by `generate_scenarios_json.py`

## Common Gotchas

1. **French vs English**: Variable names are French, class names English
2. **Percentage handling**: Some params are percentages (0-100), others decimals (0-1). Check docstrings.
3. **LPCD units**: Liters per capita per day (not m³)
4. **Horizon**: Always 20 years for standard analysis
5. **Discount rate**: Stored as percentage (3.0 = 3%), converted internally

## Version History Highlights

- **v3.11**: Race condition fix in parallel API requests
- **v3.10**: Expert mode for persistence parameters
- **v3.9**: Monte Carlo with custom distributions
- **v3.8**: Deployment optimization endpoint
- **v3.7**: Multi-perspective VAN decomposition

See changelog in `analyse_compteurs_eau.py` for complete history.
