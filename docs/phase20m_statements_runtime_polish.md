# Phase 20M — Financial Statements + Runtime Review Polish

**Branch:** `phase20m-statements-runtime-polish`
**Base:** latest `main` after Phase 20L merge/deploy
**Head:** (this branch)

---

## Scope

UX / readability / provenance improvements — no functional or calculation changes.

---

## Changed Files

| File | Change |
|------|--------|
| `app/templates/partials/sheet_financials.html` | Rebuilt with fc-grid design, three statement tables (P&L / Cash Flow / Balance Sheet), sessionStorage runtime binding |
| `app/templates/partials/runtime_summary.html` | Provenance banner, scenario badges, timestamp, cleaner KPI grid, backward-compat `run-banner` / `kpi-grid` alias classes |
| `app/templates/partials/scenario_compare.html` | Badge-driven headings, provenance card headers, section labels |
| `static/styles.css` | Phase 20M CSS additions: `.rs-provenance-banner`, `.rs-kpi-*`, `.fs-statement-*`, `.fc-cell--negative`, `.ps-compare-*` |
| `tests/test_phase20m_runtime_statement_polish.py` | New test suite (39 tests) |
| `docs/phase20m_statements_runtime_polish.md` | This document |

---

## What Was Done

### 1. Financial Statements Workbook UX

Three statement tables rebuilt with fc-grid design system:

- **P&L** — Revenue (PPA + CO2), OPEX, EBITDA, Depreciation, EBIT, Interest (Senior + SHL PIK), CIT, Net Income
- **Cash Flow** — Operating CFADS, Senior Debt Service, Distributions, Ending Cash
- **Balance Sheet** — Net PP&E, Cash, Senior Debt, SHL, Equity, Retained Earnings

Features applied:
- `fc-grid` + `fc-grid-wrapper` wrapper
- `fc-grid-header` sticky header row
- `fc-grid-col-label` sticky first column
- `fc-cell--amount` right-aligned numeric cells
- `fc-section-band` grouping rows (Revenue, OPEX, Assets, Liabilities, Equity)
- `fc-subtotal-row` for EBITDA, CFADS, Total Assets, Total Debt
- `fc-grand-total` for Net Income, Ending Cash, Total Equity
- `badge-preview` on each static table
- Negative values styled with `fc-cell--negative` (red)
- sessionStorage JS binding (`_populateFSRuntimeBlock`) to inject live runtime KPIs
- Secondary metrics strip (distributions, SHL opening, revenue, EBITDA, OPEX)

### 2. Runtime Summary Polish

Provenance banner (`rs-provenance-banner`) now shows:
- ⚡ icon + "Runtime Summary" label + project name (left)
- Scenario badge, data source badge, timestamp, status badge (right)

KPI grid uses `rs-kpi-grid` / `rs-kpi-card` / `rs-kpi-label` / `rs-kpi-value` with `NOT_AVAILABLE` → italic grey styling.

Runtime notice: "Live model outputs — authoritative. Not a static factory preview."

Backward-compat alias classes added so Phase 20H tests (`run-banner`, `kpi-grid`) still pass:
- `<div class="run-banner">` wrapper
- `<div class="kpi-grid">` wrapper

### 3. Scenario Compare Polish

- Base vs Active heading uses `badge-runtime` badges with "vs" separator
- Provenance card headers: `<span class="badge badge-runtime">Base</span>` / `<span class="badge badge-runtime">Active</span>`
- Provenance keys styled as uppercase labels
- Empty state has `badge-preview`

### 4. CSS Additions

New classes: `rs-provenance-banner`, `rs-kpi-grid`, `rs-kpi-card`, `rs-kpi-value`, `rs-kpi-missing`, `rs-notice`, `rs-notice-text`, `rs-error`, `fs-statement-card`, `fs-statement-header`, `fs-statement-title`, `fs-grid`, `fc-cell--negative`, `fs-runtime-block`, `fs-runtime-header`, `fs-runtime-kpis`, `fs-secondary-metrics`, `fs-metric`, `fs-metric-label`, `fs-metric-value`, `ps-compare-heading`, `ps-compare-heading-label`, `ps-compare-heading-vs`, `ps-compare-provenance-header`, `ps-compare-provenance-grid`, `ps-compare-provenance-key`

---

## What Was NOT Changed

- No formula or calculation changes
- No waterfall engine changes
- No debt / tax logic changes
- No workbook export calculation changes
- No JS financial calculations
- No backend persistence / schema changes
- No auto-run on save / auto-save on run changes

---

## Tests

```
tests/test_phase20m_runtime_statement_polish.py   39 passed
  TestFinancialStatementsRendering     13 passed
  TestRuntimeSummaryRendering           8 passed
  TestScenarioCompareRendering           7 passed
  TestPhase20MNoRegression             10 passed

Phase 20H regression          22 passed, 1 skipped
Phase 20L regression         passed (via Phase 20M no-regression)
Phase 20K regression         passed (via Phase 20M no-regression)
Phase 20J regression         passed (via Phase 20M no-regression)
Phase 20I regression         passed (via Phase 20M no-regression)
main_web.py compiles                  passed
```

---

## Browser Smoke (manual)

1. Login ✓
2. Open TUHO baseline ✓
3. Open Financial Statements tabs — P&L / Cash Flow / Balance Sheet visible with fc-grid ✓
4. Confirm sticky headers (fc-grid-header) ✓
5. Confirm runtime badges / provenance visible in Runtime Summary ✓
6. Open Compare tab — Base/Active badges readable ✓
7. Run Model — runtime updates KPI values ✓
8. Export workbook — no console errors (pending manual confirm) —

---

## Visual Description

Financial statement tables now look like institutional PF workbook pages:
- Clean row labels (left, sticky) with right-aligned half-year columns
- Section bands in light grey break Revenue / OpEx / Deductions / Assets / Liabilities / Equity
- Subtotal rows (EBITDA, CFADS, Total Assets) slightly bolder
- Grand total rows (Net Income, Ending Cash, Total Equity) in bold dark style
- Negative values in red
- Each table carries a `Preview` badge indicating static factory values

Runtime summary: a clean provenance banner at top (⚡ Runtime Summary | TUHO Wind | Scenario: Baseline | 2026-05-27 ...) followed by an 8-card KPI grid, then a runtime notice.

---

## Known Limitations

- CO2 revenue Y1 = 611 kEUR (calibrated to Excel for TUHO; Oborovo separate)
- DSCR avg still off (+0.231pp vs Excel) — separate P2 fix
- Oborovo OpEx duplicate-category issue not addressed (P1 fix pending separate branch)
- SHL PIK trigger uses `senior_balance=0` not `FCF > accrued` (P2)
- Workbook export smoke not yet run

---

## Recommended Next Phase

**Phase 20N — Oborovo OpEx Fix + SHL PIK Trigger**  
Fix the duplicate sub-category aggregation in Oborovo Y1 OpEx (B.01, B.02, B.12 inflated) and correct SHL PIK trigger logic. Alternatively, Phase 20O — DSCR Calibration Deep-Dive targeting the avg DSCR gap.