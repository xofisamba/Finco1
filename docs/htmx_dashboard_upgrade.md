# HTMX Dashboard UI Upgrade

**Date:** 2026-05-07
**Branch:** `feature/htmx-dashboard-ui` (merged to main `e7768e7`)
**Target:** `app.finco.one` — Contabo private deployment

---

## Overview

Upgraded the HTMX internal demo from functional prototype to professional internal dashboard.

**Reference feel:** Stripe Dashboard, Linear, modern private-equity internal tools.

**Constraints:** No React, No Node/npm, No database/auth/persistence, UI/UX layer only, HTMX/Jinja2/vanilla CSS, Chart.js CDN.

---

## Layout Philosophy

### Desktop-first, mobile-safe
- Fixed top header (56px)
- Sticky sidebar (300px) with scrollable form
- Content area fills remaining width
- Collapses to stacked layout on mobile (< 700px)

### Typography hierarchy
- Brand logo → section labels → field labels → hints
- Font scale: 0.65rem (badges) → 0.75rem (labels) → 0.85rem (inputs) → 1.4rem (KPI values)

### Visual language
- Clean white surfaces, subtle 1px borders
- Color-coded semantic states (positive=green, warning=amber, negative=red)
- No flashy animations — professional and fast

---

## Files Changed (8 files, +864 −289 lines)

| File | Change |
|------|--------|
| `app/templates/base.html` | Full rewrite — fixed header, Chart.js CDN, HTMX loading script |
| `app/templates/index.html` | Simplified to single block extending base |
| `app/templates/partials/kpis.html` | Cleaner cards, semantic coloring |
| `app/templates/partials/comparison.html` | Professional table with best/worst highlighting |
| `app/templates/partials/validation.html` | Cleaner inline validation feedback |
| `app/templates/partials/errors.html` | Minimal error display |
| `static/styles.css` | Full rewrite — 619 net additions, CSS variables, responsive |
| `tests/test_htmx_internal_demo.py` | 1 test fix (validation assertion) |

---

## UI Components Added

### Header
- Fixed top bar with brand logo + name + "Internal Advisory Platform" subtitle
- `INTERNAL DEMO` warning badge (yellow)
- `v1.5.0` version badge

### Form (sidebar)
Organized into labeled sections:
1. **Project** — type, scenario, capacity
2. **Revenue** — tariff, p50 hours
3. **CAPEX** — total CAPEX
4. **OPEX** — OPEX Y1
5. **Debt** — gearing, tenor, interest rate, target DSCR

Two-column field rows for paired inputs.

### Status Banner
Green dot + "Model Active" + "Screening-grade — not audited financial advice"

### Caveats Banner
Amber warning box listing known model caveats (TUHO CO2, Oborovo OpEx).

### KPI Cards
- Grid of cards with large typography
- Color-coded: positive (green), warning (amber), negative (red)
- Project IRR, Equity IRR, Min DSCR, Avg DSCR, Revenue, EBITDA

### Scenario Comparison Table
- Sticky column headers
- Best value highlighted green, worst red
- Metrics: Project IRR, Equity IRR, Min DSCR, Avg DSCR, Revenue, EBITDA

### Empty State
Dashed-border placeholder with icon and instructions.

### Loading Indicators
- HTMX `htmx-indicator` spans below buttons
- Disabled state on buttons during request

---

## Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| > 900px | Full sidebar + content |
| 700–900px | Narrower sidebar |
| < 700px | Stacked (sidebar on top, content below) |

---

## Charts (Phase 5 — Deferred)

Chart.js CDN included in `base.html` for future use. Charts not implemented yet — deferred to `feature/charts` branch.

---

## Model Status Panel

Status banner shows:
- Green dot + "Model Active"
- Disclaimer: "Screening-grade — not audited financial advice"
- Caveats banner lists known TUHO/Oborovo issues

---

## UX Improvements

- Form buttons disable during HTMX requests (`hx-disabled-elt`)
- `htmx-indicator` shows "Validating..." / "Running model..." / "Comparing..."
- Inline validation feedback (green checkmark or red errors)
- Smooth loading state (`htmx-loading` class on targets)

---

## Tests

- `test_validate_valid_solar_returns_200` fixed to match new validation text
- All 1253 tests pass
- No CSS snapshot tests (brittle — not added)

---

## What Was NOT Changed

- ❌ `rc1` — untouched
- ❌ Model formulas — unchanged
- ❌ Waterfall logic — unchanged
- ❌ Depreciation runtime — unchanged
- ❌ Database/auth/persistence — not in scope
- ❌ Streamlit app — not touched

---

## Known Limitations

1. No real auth (Basic Auth via nginx — interim only)
2. No persistence (no database, no project save/load)
3. No charts yet (Chart.js CDN loaded, charts not implemented)
4. No run history or audit log
5. No mobile-optimized form (stacked layout works, not designed for touch-first)

---

## Future Phases (Not in This Branch)

- `feature/charts` — Chart.js revenue/EBITDA/debt/DSCR over time
- `feature/auth-lite` — Session-based auth with bcrypt
- `feature/project-persistence` — Save/load projects to database
- `feature/model-calibration-cleanup` — Fix TUHO CO2, Oborovo OpEx
- `feature/bess-hybrid` — BESS/hybrid project types

---

## Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /` | Basic Auth | Main dashboard |
| `GET /public-health` | None | Public health check |
| `GET /health` | Basic Auth | Private health |
| `POST /validate` | Basic Auth | Inline validation |
| `POST /run` | Basic Auth | Run model |
| `POST /compare` | Basic Auth | Scenario comparison |
| GET/POST `/download` | Basic Auth | Excel export |

---

## Smoke Test

```bash
# Public (no auth)
curl https://app.finco.one/public-health
# → {"status":"ok","app":"fincogpt","mode":"internal-demo"}

# With auth
curl -u admin:fincoGPT2026! https://app.finco.one/health
# → {"status":"ok"}

# Run model
curl -X POST -u admin:fincoGPT2026! \
  -d "project_type=Solar&scenario=Base" \
  https://app.finco.one/run | head -c 200
```