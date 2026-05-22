# Phase 9.5 — Excel-like Sheet Content Foundation

**Branch:** `phase9_5-excel-like-sheet-content-foundation`
**Status:** Implemented ✅

---

## What Was Implemented

Replaced all placeholder panels in the workspace tab interface with real project finance content for the TUHO Wind 1 project, using hardcoded factory data embedded directly in HTML templates.

### New Partial Files Created

| File | Tab | Content |
|---|---|---|
| `partials/sheet_inputs.html` | Inputs | Project metadata, key dates, capacity & production, revenue assumptions, OPEX/CAPEX anchors |
| `partials/sheet_construction.html` | Construction | CAPEX summary table (70,692 kEUR hard + IDC + fees), IDC summary, construction timeline |
| `partials/sheet_production.html` | Production | Annual/semiannual generation table, 35 MW × P50 hours basis, first 8 periods |
| `partials/sheet_revenue.html` | Revenue | PPA tariff (60 EUR/MWh, 12yr), CO2 revenue (4.191 EUR/MWh), 4-period preview table |
| `partials/sheet_opex.html` | OPEX | 12-item OPEX schedule (1,998 kEUR Y1 total), inflation rates per category |
| `partials/sheet_capex.html` | CAPEX | CAPEX breakdown with Y0 spend profile, senior debt 43,359 / equity 29,635 split |
| `partials/sheet_senior_debt.html` | Senior Debt | Facility 43,359 kEUR, 20yr tenor, 8% rate, 1.20x DSCR target, 4-period debt service preview |
| `partials/sheet_shl.html` | SHL | Opening 32,704 kEUR, 7.93% PIK rate, pik_then_sweep, 4-period PIK accrual preview |
| `partials/sheet_tax.html` | Tax | CIT=0 throughout (Phase 9 convention), straight-line 20yr depreciation, 10-period CIT schedule |
| `partials/sheet_financials.html` | P&L, Cash Flow, Balance Sheet | Full 3-statement set, first 6 semiannual periods each |

### Modified Files

- **`app/templates/partials/workspace_shell.html`** — Replaced all placeholder panels with `{% include %}` references to the new partials
- **`static/styles.css`** — Added Excel-like table styles: `.sheet-table`, `.assumption-grid`, `.section-divider`, `.num-col`, `.period-col`, `.total-row`, `.table-note`, `.metric-label`

### Tabs Remaining as Placeholders (OK per spec)

- `panel-overview` — KPIs driven by runtime
- `panel-sponsor` — R99/R102 not approved
- `panel-distributions` — waterfall logic pending
- `panel-audit` — already had real content (TUHO parity status)
- `panel-downloads` — already had real content (download links)

---

## TUHO Wind 1 Data Embedded

All content uses TUHO Wind 1 factory defaults:

- **Project:** TUHO Wind 1, Akuo Energy Med, TUHO-WIND-1, HR
- **Capacity:** 35 MW | **COD:** 2030-01-01 | **Horizon:** 30 years, Semestrial
- **P50 Hours:** 4,164 hrs/yr → 72,870 MWh/semestrial period
- **PPA:** 60 EUR/MWh, 12yr term, 2% index
- **CO2:** 4.191 EUR/MWh (Y1–Y4)
- **Total CAPEX:** 72,994 kEUR (IDC 1,520 + Bank Fees 783)
- **Senior Debt:** 43,359 kEUR | **Equity:** 29,635 kEUR
- **SHL Opening:** 32,704 kEUR | **PIK Rate:** 7.93% p.a.
- **DSCR Target:** 1.20x | **Senior Rate:** 8% p.a.

---

## What Was NOT Changed (per rules)

- No runtime model files modified (`app/models/`, `app/core/`, `app/calculations/`, `app/domain/`)
- No persistence backend added
- No Streamlit, React, or Vue introduced — existing HTMX/Jinja/static CSS architecture preserved
- No model formula changes
- No Python import of TUHO data — content is hardcoded in HTML templates

---

## Future Work

- **Live runtime binding:** Replace hardcoded values with `{{ project.capacity }}`-style Jinja2 expressions wired to the project factory
- **Persistence:** Add database-backed project save/load (portfolio entities already scaffolded in `feature/project-persistence`)
- **Inline editing:** Convert read-only displays to editable forms per tab
- **Charts:** Add SVG/canvas chart components for DSCR, revenue waterfall, debt amortisation

---

## Files Changed Summary

```
NEW:
  app/templates/partials/sheet_inputs.html
  app/templates/partials/sheet_construction.html
  app/templates/partials/sheet_production.html
  app/templates/partials/sheet_revenue.html
  app/templates/partials/sheet_opex.html
  app/templates/partials/sheet_capex.html
  app/templates/partials/sheet_senior_debt.html
  app/templates/partials/sheet_shl.html
  app/templates/partials/sheet_tax.html
  app/templates/partials/sheet_financials.html
  docs/phase9_5_excel_like_sheet_content_foundation.md
  tests/test_phase9_5_excel_like_sheet_content_foundation.py

MODIFIED:
  app/templates/partials/workspace_shell.html
  static/styles.css
```