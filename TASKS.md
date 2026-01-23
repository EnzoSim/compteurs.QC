# Water Project - Integration & Optimization Tasks

## Overview
This document tracks all fixes and improvements for the frontend HTML/JS ↔ FastAPI integration, plus VAN optimization guidance.

---

## Section 1: Integration Fixes (Priority: High)

### Task A: Fix API_URL Configuration
**Status:** [x] COMPLETED

**Problem:** Hardcoded API URL will break if domain changes or frontend is hosted elsewhere.

**Current code:**
```js
const API_URL = isLocal ? 'http://localhost:8000' : 'https://compteurs-qc.onrender.com';
```

**Solution:** Use current origin by default with optional override.
```js
const isLocal = ['localhost','127.0.0.1'].includes(window.location.hostname);

const urlParams = new URLSearchParams(window.location.search);
const apiOverride = urlParams.get('api') || localStorage.getItem('api_url');

const API_URL = apiOverride || (isLocal ? 'http://localhost:8000' : window.location.origin);
```

**Benefits:**
- Same code for dev/prod
- Separate frontend possible via `?api=https://your-api...`
- Zero CORS if same origin in prod

---

### Task B: Fix checkApiHealth() Timeout
**Status:** [x] COMPLETED

**Problem:** `fetch` ignores the `timeout` option - API can hang indefinitely.

**Current code:**
```js
await fetch(`${API_URL}/api/health`, { timeout: 10000 });
```

**Solution:** Use AbortController for proper timeout handling.
```js
async function checkApiHealth() {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const response = await fetch(`${API_URL}/api/health`, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const health = await response.json();
    // ... rest of function
  } catch (err) {
    clearTimeout(timeoutId);
    // ... error handling
  }
}
```

---

### Task C: Sync Leak Presets Between JS and Python
**Status:** [x] COMPLETED

**Problem:** `fuitesDefaults` in JS doesn't match actual Python model presets. UI shows different values than what API calculates.

**Discrepancy examples:**
- Model: `standard`/`quebec` have `taux_reparation_pct = 85`, `taux_detection_pct = 90`
- JS displays: 55% and 85% in some cases

**Option 1 (Quick fix):** Correct hardcoded table to match model:
- `standard`: detection 90, repair 85
- `quebec`: detection 90, repair 85
- `deux_stocks_sans_tarif`: detection 90, repair 55

**Option 2 (Better - single source of truth):**
- Use `detailed.params_fuites` from `/api/detailed_series` response
- Display leak hypotheses from API response instead of JS tables
- Frontend and backend can never diverge

---

### Task D: Sync Water Value Preset Sliders
**Status:** [x] COMPLETED

**Problem:** When `valeur_eau_preset` changes, sliders don't update. User thinks sliders are used but API uses preset values.

**Solution:** On preset change, fetch `/api/valeur_eau_presets` and sync inputs.

```js
let VALEUR_EAU_PRESETS = null;

async function getValeurEauPresets() {
  if (VALEUR_EAU_PRESETS) return VALEUR_EAU_PRESETS;
  VALEUR_EAU_PRESETS = await apiCall('/api/valeur_eau_presets');
  return VALEUR_EAU_PRESETS;
}

async function onValeurEauPresetChange() {
  const key = document.getElementById('valeur-eau-preset').value;
  const vs = document.getElementById('valeur-sociale');
  const cv = document.getElementById('cout-variable');

  if (key === 'custom') {
    vs.disabled = false; cv.disabled = false;
    onParamChange();
    return;
  }

  const presets = await getValeurEauPresets();
  const p = presets[key];
  if (!p) return;

  vs.value = p.valeur_sociale_m3;
  cv.value = p.cout_variable_m3;
  vs.disabled = true; cv.disabled = true;

  updateLabels();
  onParamChange();
}
```

---

### Task E: Fix Dockerfile Asset Copying
**Status:** [x] COMPLETED

**Problem:** Dockerfile doesn't copy required assets that `index.html` needs:
- `translations.js` (script loaded by index.html)
- `map/` folder (iframe `map/index.html`)
- Other potential assets

**Result:** In Docker deployment:
- `GET /translations.js` returns `index.html` (via catch-all) → JS error
- Map doesn't display

**Solution:** Add to Dockerfile:
```dockerfile
COPY index.html translations.js ./
COPY map ./map
# optional: COPY docs ./docs
```

---

### Task F: Security - Fix Path Traversal Vulnerability
**Status:** [x] COMPLETED
**Priority:** CRITICAL

**Problem:** Static file catch-all can expose files outside project directory via path traversal (`../../...`).

**Current vulnerable code:**
```py
safe_path = os.path.join(os.getcwd(), path)
if os.path.exists(safe_path) and os.path.isfile(safe_path):
    return FileResponse(safe_path)
```

**Solution:** Resolve path and verify it stays within allowed directory.
```py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

@app.get("/{path:path}")
async def serve_static(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, detail="API path")

    requested = (BASE_DIR / path).resolve()

    # Block traversal
    if not str(requested).startswith(str(BASE_DIR)):
        raise HTTPException(404, detail="Not found")

    if requested.is_file():
        return FileResponse(str(requested))

    # If requesting an asset (has dot) that doesn't exist, return 404
    if "." in path:
        raise HTTPException(404, detail="Asset not found")

    return FileResponse(str(BASE_DIR / "index.html"))
```

---

### Task G: Minor Fixes (Non-blocking)
**Status:** [x] COMPLETED

#### G1: Fix exportJSON() apiCall [COMPLETED]
**Problem:** Third param is boolean (`useAbort`), not method. Works by accident.
```js
// Current (wrong):
apiCall('/api/health', null, 'GET')

// Correct:
apiCall('/api/health')
```
**Resolution:** Code was already correct - no erroneous third parameter found.

#### G2: Request Race Condition [COMPLETED]
**Problem:** Only `/api/calculate` is aborted. Other calls (sensitivity, detailed_series) can arrive out of order if user moves sliders fast.

**Solution:** Added `globalRequestId` and `fetchWithRequestId()` helper to ignore stale responses.

---

## Section 2: Architecture Decisions (Clarifications Needed)

### Decision A: Frontend Deployment Strategy
- [x] **Option 1 (Recommended):** All on FastAPI - same domain, API_URL = `window.location.origin`, minimal CORS ✅ CHOSEN
- [ ] **Option 2:** Separate frontend (GitHub Pages, Netlify) - configurable API_URL, strict CORS
- [ ] **Option 3:** Reverse proxy (Nginx) - `/api` → FastAPI, `/` → static

### Decision B: Which VAN to Optimize
- [x] **Economic VAN:** Full social value of water - easier to make positive (higher $/m³) ✅ PRIMARY (UI implemented)
- [x] **Financial VAN:** Variable cost avoided - harder, needs infrastructure deferral benefits ✅ SECONDARY (shown below Economic)
- [ ] **VAN by Actor:** City vs households (use `/api/perspectives`)

### Decision C: Tariff Strategy
- [ ] **With price signal:** Higher repairs, faster benefits (more demanding politically)
- [x] **Without tariff:** Compensate with incentives, monitoring, engagement, repair programs ✅ RECOMMENDED (no code change - user choice)

### Decision D: Define "Fast" Goal
- [x] **Shorter payback:** ROI in fewer years ✅ CHOSEN (UI highlights payback with amber styling)
- [ ] **Positive VAN early:** Net positive cash flows quickly
- [ ] **Higher total VAN at 20 years:** Even if payback is long

---

## Section 3: VAN Optimization Levers

### Reference Baseline
With values close to defaults (Longueuil 116,258 households, AMI $250, 3h at $125/h, "QC differentiated no tariff" leak scenario, realistic persistence, 8% behavior, economic mode):
- **VAN:** ~-$36M
- **RBC:** ~0.74
- **Payback:** Infinite

---

### Lever 1: Increase Water Savings (Behavior)
**Parameters:** `reduction_comportement`, persistence choice, expert mode (lambda_decay/alpha_plateau)

**Impact:** 8% → 14% (with coherent realistic persistence)
- VAN: **+$15M**
- Payback: ~13 years

**Field Actions:**
- More frequent feedback (monthly/weekly)
- Alerts, neighbor comparisons, goals
- Nudges, gamification
- Early deployment support

---

### Lever 2: Leak Detection & Repair
**Impact:** Switch to "Quebec 35% / 50 m³ / high repair" scenario
- VAN: **+$9M**
- Payback: ~17 years

**Field Actions:**
- Clear alert + follow-up protocol until repair
- Plumber partnerships, repair assistance
- Targeted campaigns for high consumers and high-incidence areas

---

### Lever 3: Reduce Installation Costs (CAPEX)
**Parameters:** `heures_installation`, `cout_compteur`, `cout_reseau`

**Impact:**
- 3h → 1.5h: **+$22M VAN**
- $250 → $150 meter: **+$12M VAN**

**Field Actions:**
- Standardize procedures, pre-visits, homogeneous batches
- Framework contracts, group purchases, optimized logistics
- Trained installation crews

---

### Lever 4: Reduce AMI Non-Technical OPEX
**Parameter:** `cout_opex_non_tech_ami`

**Impact:** $15 → $10/meter/year: **+$9M VAN**

**Field Actions:**
- Negotiate telecom
- Shared infrastructure
- Optimize storage/retention
- Balance cybersecurity vs cost

---

### Lever 5: Network Losses
**Parameter:** `reseau_activer` block

**Impact:** Can make VAN very positive (economic mode)
- Example: 5M m³/year losses, -30% in 5 years, $1M/year program + $2M capex → strongly positive VAN

**Caution:** Financial VAN (variable cost) effect much weaker

**Field Actions:**
- Sectorization, DMA
- Pressure/leak correlation
- Active detection
- Critical pipe prioritization

---

### Lever 6: Economies of Scale
**Parameter:** `activer_economies_echelle`

**Impact:** ~**+$5M VAN**

---

### Winning Combination Example
This combo achieved payback < 7 years with strongly positive VAN:
- Behavior reduction: ~14% (realistic persistence)
- Meter cost: ~$200
- Installation hours: ~2h
- Non-technical OPEX: ~$10
- Economies of scale: enabled

**Key insight:** Single lever = fighting gravity. 2-3 aligned levers = VAN takes off.

---

### Built-in Analysis Tools
- `/api/sensitivity`: Identify 3 dominant parameters (where to negotiate/act)
- `/api/monte_carlo`: Verify if winning only in optimistic cases or robust under uncertainty
- `/api/optimize_deployment`: Set objective on payback with constraints (annual budget, install capacity) → coherent deployment rhythm

---

## Task Checklist Summary

### Critical (Do First)
- [x] Task F: Security - Path Traversal Fix ✅
- [x] Task E: Dockerfile Asset Copying ✅
- [x] Task B: checkApiHealth() Timeout Fix ✅

### High Priority
- [x] Task A: API_URL Configuration ✅
- [x] Task C: Leak Presets Sync ✅
- [x] Task D: Water Value Preset Sync ✅

### Medium Priority
- [x] Task G1: exportJSON() apiCall fix ✅
- [x] Task G2: Request Race Condition ✅

### Decisions (Resolved)
- [x] Decision A: Frontend Deployment Strategy → Option 1 (FastAPI)
- [x] Decision B: Which VAN to Optimize → Economic (primary) + Financial (secondary)
- [x] Decision C: Tariff Strategy → Sans tarif (recommandé, pas de changement code)
- [x] Decision D: Define "Fast" Goal → Payback court (UI mise en avant)
