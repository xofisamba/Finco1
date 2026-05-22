# Phase 9.5 — Excel-like Sheet Content Foundation

## Overview

Phase 9.5 replaces placeholder panels in the workspace tabs with real project finance content using TUHO Wind 1 factory assumptions embedded as static UI seed data.

## Goal

- Replace placeholder-only UI with structured, realistic project finance workspace content
- Embed TUHO factory data as static template content (not live calculated results)
- Provide institutional Excel-like table layouts for all major model sections
- Clearly label all content as template preview, not live output

## What Was Implemented

### New Sheet Partials (10 files)

| File | Content |
|------|---------|
| `partials/sheet_inputs.html` | Project metadata, key dates, capacity, revenue assumptions |
| `partials/sheet_construction.html` | CAPEX summary (70,692 kEUR hard + IDC/fees), construction schedule |
| `partials/sheet_production.html` | Semiannual generation table (~72,870 MWh/period, P50) |
| `partials/sheet_revenue.html` | PPA 60 EUR/MWh, 12yr, CO2 4.191, 4-period preview |
| `partials/sheet_opex.html` | 12-item schedule (1,998 kEUR Y1 total, 2%/6% inflation) |
| `partials/sheet_capex.html` | CAPEX items with Y0 spend profile, debt/equity split |
| `partials/sheet_senior_debt.html` | 43,359 kEUR, 20yr, 8%, 1.20x DSCR, 4-period preview |
| `partials/sheet_shl.html` | 32,704 kEUR opening, 7.93% PIK, pik_then_sweep |
| `partials/sheet_tax.html` | CIT=0 (Phase 9 convention), 20yr depreciation, MISSING_EVIDENCE flags |
| `partials/sheet_financials.html` | P&L + Cash Flow + Balance Sheet (6 semiannual periods) |

### Modified Files

| File | Change |
|------|--------|
| `workspace_shell.html` | All placeholder panels replaced with `{% include partials/sheet_*.html %}` |
| `static/styles.css` | ~150 lines: `.sheet-banner`, `.sheet-table`, `.assumption-grid`, `.badge-preview`, `.subsection-label`, etc. |

## Data Embedded

All values are **hardcoded UI seed data from the TUHO Wind 1 factory** (`create_default_tuho_wind1()` in `app/project_factories.py`):

- Project: TUHO Wind 1, 35 MW wind, COD 2030-01-01
- Total CAPEX: 72,994 kEUR (Hard 70,692 + IDC 1,520 + fees 783)
- Senior Debt: 43,359 kEUR, Equity: 29,635 kEUR
- OPEX Y1: 1,998 kEUR (12 items)
- SHL opening: 32,704 kEUR, PIK 7.93%
- Revenue: PPA 60 EUR/MWh × 12yr + CO2 4.191 EUR/MWh
- CIT: 0 throughout (Phase 9 accepted convention)

## Key Design Decisions

### 1. Static Template Data Only

All tab content is **static HTML** embedded in Jinja2 templates. No runtime model values are fetched. This is intentional — the goal is a UI shell with realistic structure, not a live calculator.

### 2. Template Preview Badges

Every sheet partial includes a prominent banner:
```
[badge: Template preview]  Static TUHO factory snapshot — not live run output
```

Financial statement tables include:
```
Preview financial statements — static illustrative TUHO schedule, not live calculated output
```

### 3. No Runtime Binding

These partials do NOT call Python functions, do NOT fetch from the model engine, and do NOT use HTMX to load live data. Future branches will wire live runtime context.

### 4. Tax: MISSING_EVIDENCE Flags

Tax bridge (R35/R67) is labeled `MISSING_EVIDENCE` since Phase 9 tax bridge wiring is not yet confirmed against the TUHO Excel model.

### 5. UI Layers Distinction

The UI now has three clearly distinct layers:

| Layer | Type | Description |
|-------|------|-------------|
| Editable inputs | Sidebar form | Actual input fields (project_type, scenario, etc.) |
| Read-only template values | Sheet partials | TUHO factory static preview data |
| Future live output tables | Placeholder/coming-soon | Runtime waterfall results |

## Future Work

### Live Runtime Binding (Future Branch)

The template partials will be replaced with HTMX-driven live data:
- Active project context from `project_factories` runtime
- TUHO or Oborovo project switching via `switchProject()`
- Live KPI updates via HTMX partial replacement
- Real OPEX, CAPEX, debt service, tax figures from waterfall engine

### Persistence Backend (Future Branch)

- Save/load project configurations
- Run history persistence
- Named scenarios

### Runtime Model Completions (Separate Branches)

- R35/R67 tax bridge validation against Excel
- Full financial statement parity (P&L, CF, BS)
- Distribution schedule
- Sponsor waterfall

## No Runtime Changes

**This branch does NOT change:**
- `app/models/*` — no schema, domain, or calculation changes
- `app/core/*` — no runtime engine changes
- `app/calculations/*` — no formula changes
- `app/domain/*` — no entity changes
- `app/project_factories.py` — no factory logic changes
- `app/ui_runner.py` — no UI runner changes
- `persistence/` — no persistence added

## Tests

`tests/test_phase9_5_excel_like_sheet_content_foundation.py` — 15+ smoke tests:
- "Template preview" phrase present in all 10 sheet partials
- "static TUHO factory snapshot" present in all 10 partials
- "not live run output" present in all 10 partials
- Inputs: TUHO Wind 1, 35 MW, PPA
- OPEX: Total 1,998 kEUR
- Senior Debt: 43,359 kEUR, DSCR
- SHL: 32,704 kEUR, PIK
- Tax: CIT=0
- Financial statements: P&L, CF, BS tables exist
- G20 BLOCKED / R99/R102 NOT APPROVED visible
- TUHO and Oborovo project selector visible
- No runtime files changed (git diff check)

## Files Changed (Whitelist)

```
app/templates/partials/sheet_inputs.html       [NEW]
app/templates/partials/sheet_construction.html [NEW]
app/templates/partials/sheet_production.html   [NEW]
app/templates/partials/sheet_revenue.html      [NEW]
app/templates/partials/sheet_opex.html        [NEW]
app/templates/partials/sheet_capex.html       [NEW]
app/templates/partials/sheet_senior_debt.html  [NEW]
app/templates/partials/sheet_shl.html         [NEW]
app/templates/partials/sheet_tax.html          [NEW]
app/templates/partials/sheet_financials.html   [NEW]
app/templates/partials/workspace_shell.html    [MODIFIED]
static/styles.css                              [MODIFIED]
docs/phase9_5_excel_like_sheet_content_foundation.md [NEW]
tests/.../test_phase9_5_excel_like_sheet_content_foundation.py [NEW]
```