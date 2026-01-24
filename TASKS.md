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

---

## Section 4: UI Improvements Roadmap

### Phase 1: Critical Accessibility Fixes (High Priority)

#### Task UI-1: Form Labels and ARIA Associations
**Status:** [ ] TODO
**Priority:** HIGH (Accessibility compliance)

**Problem:** Range inputs lack proper `for` attributes and ARIA associations. Screen readers may not associate labels correctly.

**Location:** Lines 1600-1700 (`input-group` elements)

**Current code:**
```html
<label><span data-i18n="param.households">Nombre de ménages</span> <span class="value" id="val-menages">116 258</span></label>
<input type="range" id="nb-menages" ...>
```

**Solution:**
- Add `for="nb-menages"` to labels
- Add `aria-describedby` for help text
- Add `aria-valuemin`, `aria-valuemax`, `aria-valuenow` to range inputs

```html
<label for="nb-menages"><span data-i18n="param.households">Nombre de ménages</span> <span class="value" id="val-menages">116 258</span></label>
<input type="range" id="nb-menages" aria-valuemin="1000" aria-valuemax="500000" aria-valuenow="116258" ...>
```

---

#### Task UI-2: Keyboard Navigation for Custom Controls
**Status:** [ ] TODO
**Priority:** HIGH (Accessibility compliance)

**Problem:** Toggle switches and collapsible sections use `onclick` without keyboard handlers.

**Location:** `.toggle` elements, `.advanced-header` elements (lines 2945-2948)

**Current code:**
```html
<div class="toggle" id="mode-toggle" onclick="toggleMode()"></div>
```

**Solution:**
- Add `role="switch"` and `aria-checked` to toggle elements
- Add `tabindex="0"` and `onkeydown` handlers for Enter/Space
- Use `<button>` elements instead of `<div>` for clickable elements

```html
<button type="button" class="toggle" id="mode-toggle" role="switch" aria-checked="false"
        onclick="toggleMode()" onkeydown="if(event.key==='Enter'||event.key===' ')toggleMode()">
</button>
```

---

#### Task UI-3: Modal Accessibility
**Status:** [ ] TODO
**Priority:** HIGH (Accessibility compliance)

**Problem:** Modals do not trap focus, have no escape key handling, and lack proper ARIA attributes.

**Location:** Map modal and calibration modal (lines 5022-5102)

**Solution:**
- Add `role="dialog"` and `aria-modal="true"`
- Implement focus trap within modals
- Add escape key handler to close modals
- Return focus to trigger element on close

```js
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.style.display = 'flex';

  // Store trigger element
  modal._triggerElement = document.activeElement;

  // Focus first focusable element
  const focusable = modal.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
  if (focusable.length) focusable[0].focus();

  // Escape key handler
  modal._escHandler = (e) => { if (e.key === 'Escape') closeModal(modalId); };
  document.addEventListener('keydown', modal._escHandler);
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.style.display = 'none';
  document.removeEventListener('keydown', modal._escHandler);
  if (modal._triggerElement) modal._triggerElement.focus();
}
```

---

#### Task UI-4: Chart Accessibility
**Status:** [ ] TODO
**Priority:** HIGH (Accessibility compliance)

**Problem:** Canvas-based charts (Chart.js) are not accessible to screen readers. No alternative text or data tables provided.

**Location:** All chart elements (lines 2472-2617)

**Solution:**
- Add `aria-label` describing each chart's purpose
- Provide hidden data tables as accessible alternatives
- Use Chart.js accessibility plugin

```html
<div class="chart-container" role="img" aria-label="Graphique VAN cumulée sur 20 ans">
  <canvas id="van-chart"></canvas>
  <table class="sr-only" aria-label="Données VAN cumulée">
    <!-- Populated dynamically -->
  </table>
</div>
```

---

#### Task UI-5: Color-Only Status Indicators
**Status:** [ ] TODO
**Priority:** MEDIUM (Accessibility)

**Problem:** API status and recommendation banners use color alone to convey status (green=good, red=bad).

**Location:** `.api-status`, `.recommendation` classes (lines 152-164)

**Solution:**
- Add text labels ("Connected", "Error") alongside color
- Add icons for status indication
- Ensure 4.5:1 contrast ratio for all text

```html
<span class="api-status connected">
  <i data-lucide="check-circle"></i>
  <span data-i18n="status.connected">Connecté</span>
</span>
```

---

### Phase 2: UX Improvements (High Priority)

#### Task UI-6: Sidebar Reorganization
**Status:** [ ] TODO
**Priority:** HIGH (Usability)

**Problem:** The sidebar contains 9+ collapsible cards with over 50 input controls. Users must scroll extensively to find specific parameters.

**Location:** Lines 1555-2288 (sidebar cards)

**Solution Options:**
1. **Tabbed interface**: Group related sections into tabs (Basic, Advanced, Economic, Simulation)
2. **Single-expand accordion**: Only one section open at a time
3. **Quick Settings panel**: Most common params at top with "More options" expansion

**Recommended approach:**
```html
<div class="sidebar-tabs">
  <button class="tab active" data-tab="basic">Paramètres</button>
  <button class="tab" data-tab="economic">Économique</button>
  <button class="tab" data-tab="simulation">Simulation</button>
</div>
<div class="tab-content" id="tab-basic">
  <!-- Municipality, Project, Technology, Behavior cards -->
</div>
<div class="tab-content hidden" id="tab-economic">
  <!-- Economic, Network Losses cards -->
</div>
<div class="tab-content hidden" id="tab-simulation">
  <!-- Monte Carlo, Optimization cards -->
</div>
```

---

#### Task UI-7: Input Validation Feedback
**Status:** [ ] TODO
**Priority:** HIGH (Usability)

**Problem:** Range sliders have no visual indication of valid ranges or constraints. No error messages for invalid inputs.

**Location:** All range inputs (lines 1600-2000)

**Solution:**
- Add min/max labels at slider endpoints
- Show validation errors inline
- Add visual feedback (red border, warning icon) for out-of-range values

```html
<div class="slider-group">
  <label for="nb-menages">Nombre de ménages</label>
  <div class="slider-container">
    <span class="slider-min">1 000</span>
    <input type="range" id="nb-menages" min="1000" max="500000" value="116258">
    <span class="slider-max">500 000</span>
  </div>
  <span class="slider-value" id="val-menages">116 258</span>
  <span class="validation-error" id="err-menages" style="display:none"></span>
</div>
```

---

#### Task UI-8: Loading States with Progress
**Status:** [ ] TODO
**Priority:** HIGH (Usability)

**Problem:** The loading overlay shows generic messages. Users do not know which calculation is running or how long it will take.

**Location:** Lines 2768-2820 (DOMContentLoaded handler), lines 1530-1539 (overlay)

**Solution:**
- Add progress indication for multi-step operations
- Show estimated time for Monte Carlo simulations
- Display which charts are being updated

```js
function showLoading(message, progress = null) {
  const overlay = document.getElementById('loading-overlay');
  const text = overlay.querySelector('.loading-text');
  const progressBar = overlay.querySelector('.progress-bar');

  text.textContent = message;
  if (progress !== null) {
    progressBar.style.display = 'block';
    progressBar.value = progress;
  } else {
    progressBar.style.display = 'none';
  }
  overlay.style.display = 'flex';
}

// Usage for Monte Carlo
for (let i = 0; i < numSimulations; i++) {
  showLoading(`Simulation ${i+1}/${numSimulations}...`, (i/numSimulations)*100);
  // ...
}
```

---

#### Task UI-9: Restore Actions Bar Visibility
**Status:** [ ] TODO
**Priority:** MEDIUM (Usability)

**Problem:** Export buttons (JSON, CSV, PDF, etc.) are hidden with `style="display: none;"`, reducing discoverability.

**Location:** Lines 2329-2337

**Solution:**
- Remove `display: none` from actions bar
- Move export actions to a visible toolbar or floating action button
- Add a share/export menu in the header

```html
<div class="actions-bar">
  <button onclick="exportJSON()" title="Export JSON">
    <i data-lucide="file-json"></i>
  </button>
  <button onclick="exportCSV()" title="Export CSV">
    <i data-lucide="file-spreadsheet"></i>
  </button>
  <button onclick="exportPDF()" title="Export PDF">
    <i data-lucide="file-text"></i>
  </button>
</div>
```

---

#### Task UI-10: Reset/Undo Functionality
**Status:** [ ] TODO
**Priority:** MEDIUM (Usability)

**Problem:** No way to reset to defaults or undo parameter changes. Users can only reload the page.

**Solution:**
- Add a "Reset to Defaults" button per section and globally
- Implement undo/redo stack for parameter changes
- Auto-save current state periodically to localStorage

```js
const paramHistory = [];
let historyIndex = -1;

function saveState() {
  const state = collectAllParams();
  paramHistory.splice(historyIndex + 1);
  paramHistory.push(state);
  historyIndex = paramHistory.length - 1;
}

function undo() {
  if (historyIndex > 0) {
    historyIndex--;
    applyState(paramHistory[historyIndex]);
  }
}

function resetToDefaults(section = null) {
  if (section) {
    applyDefaults(section);
  } else {
    location.reload(); // or apply full defaults
  }
}
```

---

### Phase 3: Performance Optimization (Medium Priority)

#### Task UI-11: Script Loading Optimization
**Status:** [ ] TODO
**Priority:** MEDIUM (Performance)

**Problem:** Chart.js, Lucide icons, and Google Fonts loaded synchronously in `<head>`, blocking initial render.

**Location:** Lines 8-11

**Solution:**
- Add `defer` to non-critical scripts
- Lazy-load Chart.js until needed
- Consider bundling Lucide icons instead of loading from CDN

```html
<!-- Before -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- After -->
<script src="https://cdn.jsdelivr.net/npm/chart.js" defer></script>
```

---

#### Task UI-12: Extract JavaScript to External File
**Status:** [ ] TODO
**Priority:** MEDIUM (Performance, Maintainability)

**Problem:** Over 2500 lines of JavaScript inline in the HTML file. This cannot be cached separately and increases HTML parsing time.

**Location:** Lines 2720-5020

**Solution:**
- Extract JavaScript to external `app.js` file
- Implement code splitting for large features (Monte Carlo, calibration)
- Consider using a module bundler for future

**File structure:**
```
compteurs.QC/
├── index.html
├── app.js           # Main application logic
├── charts.js        # Chart initialization and updates
├── monte-carlo.js   # Monte Carlo simulation (lazy-loaded)
└── translations.js  # Already external
```

---

#### Task UI-13: Increase Debounce Timer
**Status:** [ ] TODO
**Priority:** MEDIUM (Performance)

**Problem:** Parameter changes trigger model updates with only 200ms debounce, causing excessive API calls during slider dragging.

**Location:** Line 3269 (`debounceTimer = setTimeout(updateModel, 200);`)

**Solution:**
- Increase debounce to 300-400ms for sliders
- Use `requestAnimationFrame` for visual updates
- Show "calculating..." state to indicate pending update

```js
// Before
debounceTimer = setTimeout(updateModel, 200);

// After
debounceTimer = setTimeout(() => {
  showCalculatingState();
  updateModel();
}, 350);
```

---

#### Task UI-14: API Request Batching
**Status:** [ ] TODO
**Priority:** LOW (Performance)

**Problem:** `updateModel()` makes 5+ parallel API calls. Each call has overhead.

**Location:** Lines 3385-3408

**Solution:**
- Create a composite `/api/calculate_full` endpoint that returns all data in one call
- Or use GraphQL for flexible queries
- Cache more aggressively on frontend

```python
# api.py
@app.post("/api/calculate_full")
async def calculate_full(request: CalculRequest):
    """Combined endpoint returning calculate + sensitivity + detailed_series"""
    base = await calculate(request)
    sensitivity = await sensitivity_analysis(request)
    detailed = await detailed_series(request)
    return {
        "calculate": base,
        "sensitivity": sensitivity,
        "detailed_series": detailed
    }
```

---

### Phase 4: Visual Polish (Medium Priority)

#### Task UI-15: Standardize Icon Usage
**Status:** [ ] TODO
**Priority:** MEDIUM (Visual consistency)

**Problem:** Mixed emoji icons (🏢, 💧, ⚡) in card headers and Lucide icons in buttons.

**Location:** Various card-icon elements (lines 1559, 2004, 2220, 2241)

**Solution:**
- Replace all emojis with Lucide icons
- Create consistent icon style guide

```html
<!-- Before -->
<span class="card-icon">🏢</span>

<!-- After -->
<span class="card-icon"><i data-lucide="building-2"></i></span>
```

**Icon mapping:**
| Current | Lucide Replacement |
|---------|-------------------|
| 🏢 | `building-2` |
| 💧 | `droplets` |
| ⚡ | `zap` |
| 🔧 | `wrench` |
| 📊 | `bar-chart-3` |
| 🎯 | `target` |
| 💰 | `coins` |
| 🔬 | `flask-conical` |

---

#### Task UI-16: Complete Dark Mode Support
**Status:** [ ] TODO
**Priority:** LOW (Visual)

**Problem:** Dark mode only modifies CSS variables. Charts, modals, and some components do not adapt.

**Location:** `@media (prefers-color-scheme: dark)` block (lines 1507-1517)

**Solution:**
- Complete dark mode support for all components
- Add manual dark mode toggle in header
- Update Chart.js themes for dark mode

```js
function updateChartTheme(isDark) {
  const textColor = isDark ? '#e5e7eb' : '#374151';
  const gridColor = isDark ? '#374151' : '#e5e7eb';

  Chart.defaults.color = textColor;
  Chart.defaults.borderColor = gridColor;

  // Update existing charts
  Object.values(charts).forEach(chart => chart.update());
}
```

---

#### Task UI-17: Improve Tooltip Positioning
**Status:** [ ] TODO
**Priority:** LOW (Visual)

**Problem:** Tooltips appear above elements with fixed width (250px), which can overflow on mobile or cause layout shifts.

**Location:** `.help-icon` CSS rules (lines 306-356)

**Solution:**
- Implement smart tooltip positioning (flip to bottom if near top edge)
- Make tooltip width responsive
- Consider using a tooltip library (Tippy.js) for better accessibility

```css
.help-icon .tooltip {
  width: min(250px, 80vw);
  /* Smart positioning via JS */
}
```

---

#### Task UI-18: Enhance Metrics Visual Hierarchy
**Status:** [ ] TODO
**Priority:** LOW (Visual)

**Problem:** All metric cards have similar visual weight. Only Payback card has special styling.

**Location:** Lines 459-601 (metrics grid styles)

**Solution:**
- Use size differentiation for primary metrics (VAN should be larger)
- Add trend indicators (arrows up/down)
- Group related metrics visually

```css
.metric-card.primary {
  grid-column: span 2;
  font-size: 1.25em;
}

.metric-card .trend-up::after {
  content: '↑';
  color: var(--success);
  margin-left: 0.25rem;
}
```

---

### Phase 5: Functionality Enhancements (Lower Priority)

#### Task UI-19: Improved Error Handling UX
**Status:** [ ] TODO
**Priority:** MEDIUM (Functionality)

**Problem:** API errors show generic messages in the recommendation banner. No retry mechanism or detailed error info.

**Location:** Lines 3416-3425 (catch block in updateModel)

**Solution:**
- Show specific error messages with suggested actions
- Add automatic retry with exponential backoff
- Provide offline mode with cached data

```js
async function apiCallWithRetry(endpoint, body, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await apiCall(endpoint, body);
    } catch (err) {
      if (i === retries - 1) throw err;
      await sleep(Math.pow(2, i) * 1000); // Exponential backoff
      showLoading(`Retry ${i + 1}/${retries}...`);
    }
  }
}
```

---

#### Task UI-20: Monte Carlo Progress and Cancellation
**Status:** [ ] TODO
**Priority:** MEDIUM (Functionality)

**Problem:** No progress indicator during Monte Carlo runs. Users cannot cancel a running simulation.

**Location:** Lines 4333-4401 (runMonteCarlo function)

**Solution:**
- Add progress bar for simulation
- Implement cancellation support via AbortController
- Show estimated completion time

```js
let monteCarloController = null;

async function runMonteCarlo() {
  monteCarloController = new AbortController();

  try {
    const result = await fetch('/api/monte_carlo', {
      method: 'POST',
      body: JSON.stringify(params),
      signal: monteCarloController.signal
    });
    // ...
  } catch (err) {
    if (err.name === 'AbortError') {
      showMessage('Simulation cancelled');
    }
  }
}

function cancelMonteCarlo() {
  if (monteCarloController) {
    monteCarloController.abort();
  }
}
```

---

#### Task UI-21: Enhanced Chart Interactions
**Status:** [ ] TODO
**Priority:** LOW (Functionality)

**Problem:** Charts are view-only. No zoom, pan, or point selection.

**Location:** All chart configurations

**Solution:**
- Add zoom/pan plugin for time-series charts
- Implement click-to-drill-down for bar charts
- Add data point tooltips with more context

```js
import zoomPlugin from 'chartjs-plugin-zoom';
Chart.register(zoomPlugin);

const chartConfig = {
  // ...
  options: {
    plugins: {
      zoom: {
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          mode: 'x'
        },
        pan: {
          enabled: true,
          mode: 'x'
        }
      }
    }
  }
};
```

---

#### Task UI-22: Improved PDF Export
**Status:** [ ] TODO
**Priority:** LOW (Functionality)

**Problem:** PDF export uses `window.print()` which gives limited control over output quality.

**Location:** Lines 4507-4578 (exportPDF function)

**Solution:**
- Use a proper PDF library (jsPDF, pdfmake)
- Include charts as images in PDF
- Add professional formatting and branding

```js
async function exportPDF() {
  const { jsPDF } = await import('jspdf');
  const doc = new jsPDF();

  // Add header
  doc.setFontSize(20);
  doc.text('Analyse Coût-Bénéfice - Compteurs d\'Eau', 20, 20);

  // Add metrics
  doc.setFontSize(12);
  doc.text(`VAN: ${formatCurrency(results.van)}`, 20, 40);

  // Add charts as images
  const chartCanvas = document.getElementById('van-chart');
  const chartImage = chartCanvas.toDataURL('image/png');
  doc.addImage(chartImage, 'PNG', 20, 60, 170, 80);

  doc.save('analyse-compteurs-eau.pdf');
}
```

---

## UI Tasks Checklist Summary

### Phase 1: Accessibility (Critical)
- [ ] UI-1: Form Labels and ARIA Associations
- [ ] UI-2: Keyboard Navigation for Custom Controls
- [ ] UI-3: Modal Accessibility
- [ ] UI-4: Chart Accessibility
- [ ] UI-5: Color-Only Status Indicators

### Phase 2: UX Improvements (High)
- [ ] UI-6: Sidebar Reorganization (tabs/accordion)
- [ ] UI-7: Input Validation Feedback
- [ ] UI-8: Loading States with Progress
- [ ] UI-9: Restore Actions Bar Visibility
- [ ] UI-10: Reset/Undo Functionality

### Phase 3: Performance (Medium)
- [ ] UI-11: Script Loading Optimization (defer)
- [ ] UI-12: Extract JavaScript to External File
- [ ] UI-13: Increase Debounce Timer (200→350ms)
- [ ] UI-14: API Request Batching

### Phase 4: Visual Polish (Medium)
- [ ] UI-15: Standardize Icon Usage (Lucide only)
- [ ] UI-16: Complete Dark Mode Support
- [ ] UI-17: Improve Tooltip Positioning
- [ ] UI-18: Enhance Metrics Visual Hierarchy

### Phase 5: Functionality (Lower)
- [ ] UI-19: Improved Error Handling UX
- [ ] UI-20: Monte Carlo Progress and Cancellation
- [ ] UI-21: Enhanced Chart Interactions (zoom/pan)
- [ ] UI-22: Improved PDF Export (jsPDF)
