# Phase 9.5 — HTMX UI/UX Product Polish

## Summary
UI/UX product polish of the existing HTMX Finco One web dashboard. Pure UI-only changes — no financial model calculations, no waterfall logic changes, no runtime behavior changes.

## Goal
Upgrade the existing FincoGPT HTMX dashboard toward a bankable clean-energy project finance dashboard with clearer navigation, better KPI cards, governance status surfaced, and organized input groups.

## What Was Changed

### Files Changed

| File | Change |
|---|---|
| `static/styles.css` | Complete rewrite — dark navy sidebar, bankable palette, status badge system, new component styles |
| `app/templates/base.html` | Added dark navy sidebar navigation with all model sections, new layout structure |
| `app/templates/index.html` | Reorganized into dashboard + input accordion groups, new governance banner, downloads panel |
| `app/templates/partials/kpis.html` | Light styling refresh, card header with PASS badge |
| `tests/test_auth_lite.py` | Updated brand name assertion: "FincoGPT" → "Finco One" |

### CSS Changes
- **Dark navy sidebar** (`--sidebar-bg: #0f1b2d`) with left navigation
- **Bankable color palette** — primary blue (#1a56db), accent green (#059669), teal (#0891b2)
- **Status badge system**: PASS, WARN, BLOCKED, ACCEPTED_CONVENTION, MISSING_EVIDENCE, NOT APPROVED
- New components: governance banner, audit panel, downloads grid, input accordion groups
- KPI cards: compact, white cards with subtle borders
- Responsive layout with mobile support

### Base Template Changes
- Added `sidebar-nav` with dark navy background and section navigation:
  - Overview: Dashboard, Audit/Parity
  - Inputs: Project Setup, Dates/COD, Production, Revenue, OPEX, CAPEX
  - Financing: Senior Debt, SHL, Tax, Distributions, Sponsor/Equity
  - Outputs: P&L, Cash Flow, Balance Sheet, Debt Schedule, Returns, Warnings
  - Downloads: Model Export, Parity Workbook, Gap Register, Source Map
  - Governance: G20/Gates with BLOCKED badge
- Header updated to "Finco One — Clean-Energy Project Finance"

### Index Template Changes
- **Dashboard section** with:
  - G20 BLOCKED governance banner (explains 0.29pp is within ±1.0pp tolerance, G20 blocked due to stakeholder decision)
  - 8 KPI cards: Project IRR, Equity IRR, Avg DSCR, Senior Debt, Total Revenue, EBITDA, Distributions, Warnings
  - Governance status card (G20/R99/R102/Equity IRR/TUHO Parity)
  - TUHO Phase 9 parity summary card (PASS/WARN/ACCEPTED_CONVENTION/MISSING_EVIDENCE badges)
  - Downloads grid panel
- **Input accordion groups** (collapsible `<details>`):
  - Project Setup (project type, scenario, capacity)
  - Dates/COD (placeholder fields for COD, construction, horizon)
  - Production (P50 hours, capacity factor)
  - Revenue/Tariff (tariff, PPA term)
  - OPEX
  - CAPEX
  - Senior Debt
  - SHL (placeholder — labeled "Not in UI")
  - Tax (placeholder — labeled "MISSING_EVIDENCE")
  - Distributions (placeholder — labeled "AUDIT-ONLY")
  - Sponsor/Equity (placeholder — R99/R102 "NOT APPROVED")

### UI Labels and Status
- G20: BLOCKED — equity IRR 0.29pp is **within** ±1.0pp tolerance; blocked due to stakeholder/reconciliation-IRR governance decision
- R99/R102: NOT APPROVED — runtime flags not validated for production promotion
- SHL: Not in UI — managed via waterfall defaults
- Tax: MISSING_EVIDENCE — R35/R69 period-level wiring incomplete in committed extract
- Distributions: AUDIT-ONLY — DA-wired staging shown separately from legacy runtime

## What Was NOT Changed

- No financial model calculations changed
- No waterfall runtime logic changed
- No SHL mechanics changed
- No TaxBridge runtime changed
- No DistributionAccount changed
- No R99/R102 logic changed
- No new frontend framework added (no React, Vue, Streamlit)
- No new routes added
- No calculation outputs changed
- G20 NOT approved — BLOCKED status maintained
- R99/R102 NOT approved — NOT APPROVED status maintained

## Pages / Routes Unchanged
All existing HTMX routes continue to work at their existing endpoints:
- `GET /` — main dashboard
- `POST /login` — authentication
- `POST /logout` — sign out
- `POST /run` — model runner
- `POST /compare` — scenario comparison
- `POST /validate` — input validation
- `GET /runs` — run history
- `POST /save-run` — save result
- `POST/GET /download` — Excel export

## Test Results
```
pytest tests/test_auth_lite.py -v
============================= 32 passed ==============================
```
All auth/route tests pass. Brand name updated from "FincoGPT" to "Finco One" in test assertions.

## Sections Surfaced

### Inputs Surfaced
- Project type and scenario (Solar/Wind, Base/Downside/Upside)
- Capacity (MW)
- COD date, construction months, horizon years
- P50 hours, capacity factor
- Tariff (EUR/MWh), PPA term
- OPEX Y1
- CAPEX total
- Senior debt: gearing, target DSCR, interest rate, tenor

### Outputs Surfaced
- P&L tab (placeholder — future module)
- Cash Flow tab (placeholder — future module)
- Balance Sheet tab (placeholder — future module)
- Debt Schedule tab (placeholder — future module)
- Returns tab (placeholder — future module)
- Warnings tab (placeholder — future module)

### Governance Surfaced
- G20 BLOCKED banner on dashboard
- TUHO Phase 9 parity card (PASS/WARN/MISSING_EVIDENCE)
- Download links (Model Export, Parity Workbook, Gap Register, Source Map)
- R99/R102 status badge

## Pending / Future Modules
The following are labeled as "Future module" or "AUDIT-ONLY" or "Not in UI":
- SHL inputs (runtime-managed via waterfall defaults)
- Tax inputs (MISSING_EVIDENCE — R35/R69 period mapping incomplete)
- Distributions inputs (AUDIT-ONLY — DA-wired staging)
- P&L tab view
- Cash Flow tab view
- Balance Sheet tab view
- Debt Schedule tab view
- Tax Bridge tab
- SHL Schedule tab
- Sponsor Cashflows tab
- Full Returns tab with charts

## Screenshots
Not captured in this PR. The visual change is substantial — run the app locally to review.

## How to Test
```bash
cd finco1
# Start the web app
python main_web.py
# Open browser at http://localhost:8000
# Login with demo credentials (demo / demo)
# Observe: dark navy sidebar, governance banner, KPI cards, accordion inputs
```

## Next Steps After Merge
1. Run independent UI review (manual browser testing)
2. Return to G20 stakeholder/gate workflow — implement reconciliation IRR or obtain formal acceptance
3. Complete R35/R69 period-level mapping from Excel extract for Tax/CFADS evidence
4. Wire P&L, Cash Flow, Balance Sheet output tabs (future module)