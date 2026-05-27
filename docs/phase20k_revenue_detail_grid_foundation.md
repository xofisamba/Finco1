# Phase 20K — Revenue Detail Grid Foundation

**Branch:** `phase20k-revenue-detail-grid-foundation`
**Base:** `4253f259a0639c0258821882717ac81f134780a6` (Phase 20J merge)
**Date:** 2026-05-27
**Status:** Implemented, pending review

---

## Goal

Implement the Revenue workbook grid — the counterpart to Phase 20I CAPEX and Phase 20J OPEX grids — using the Phase 20H `fc-*` design system.

---

## What was built

### 1. Revenue Detail Grid UI (`app/templates/partials/sheet_revenue.html`)

Complete redesign of the Revenue tab into a workbook-style grid matching CAPEX/OPEX UX.

**Structure:**
```
┌──────────────────────────────────┬──────────┬──────────┬──────┬─────────────────┬────────────────┐
│ Line Item                   [sticky │ Code     │ Value   │ Unit │ Group           │ Hint           │
├──────────────────────────────────┼──────────┼──────────┼──────┼─────────────────┼────────────────┤
│ Production                  [BAND] │          │         │      │                 │                │
│  Installed Capacity               │ capacit… │ 35.0     │ MW   │ Production       │ Set via inputs │
│  P50 Hours / Year                 │ operat… │ 4164.0   │ h/yr │ Production       │ Set via inputs │
│  Plant Availability               │ plant_… │ 1.0      │ %    │ Production       │ Set via inputs │
│  Grid Availability                │ grid_… │ 1.0      │ %    │ Production       │ Set via inputs │
├──────────────────────────────────┼──────────┼──────────┼──────┼─────────────────┼────────────────┤
│ PPA / Tariff                 [BAND] │          │         │      │                 │                │
│  Base Tariff (PPA)                │ ppa_ba… │ 60.00    │ EUR… │ PPA / Tariff     │                │ ← editable
│  Tariff Escalation               │ ppa_in… │ 0.02     │ %/yr │ PPA / Tariff     │ Set via inputs │
│  PPA Term                         │ ppa_te… │ 12       │ year…│ PPA / Tariff     │ Set via inputs │
│  PPA Production Share             │ ppa_pr… │ 1.0      │ %    │ PPA / Tariff     │ Set via inputs │
│ Tariff Y1 (PPA) subtotal         │          │ 60.00    │      │                 │                │
├──────────────────────────────────┼──────────┼──────────┼──────┼─────────────────┼────────────────┤
│ Market / Merchant            [BAND] │          │         │      │                 │                │
│  Balancing Cost                    │ balanc… │ 8.0      │ EUR… │ Market / Merchant│ Set via inputs │
│  First Merchant Period            │ first_… │ 24       │ peri…│ Market / Merchant│ Set via inputs │
├──────────────────────────────────┼──────────┼──────────┼──────┼─────────────────┼────────────────┤
│ CO2 / Certificates           [BAND] │          │         │      │                 │                │
│  CO2 Certificates Enabled         │ co2_en… │ Yes      │ flag │ CO2 / Certificates│ Set via inputs │
│  CO2 Price (Y1)                    │ co2_pr… │ 4.191    │ EUR… │ CO2 / Certificates│ Set via inputs │
├──────────────────────────────────┼──────────┼──────────┼──────┼─────────────────┼────────────────┤
│ Revenue Summary              [BAND] │          │         │      │                 │                │
│  Y1 PPA Revenue (kEUR)             │          │ 139,914  │      │ Informational   │                │
│  Y1 CO2 Revenue (kEUR)             │          │ 9,808    │      │ Informational   │                │
│  Est. Total Y1 Revenue        [TOT] │          │ 149,722  │ kEUR │ runtime model auth│               │
└──────────────────────────────────┴──────────┴──────────┴──────┴─────────────────┴────────────────┘
```

**Design features:**
- `fc-grid` + `fc-grid-wrapper` for sticky positioning
- Sticky header row + sticky first column (Line Item)
- `fc-section-band` for each revenue group
- `fc-subtotal-row` for Tariff Y1 subtotal
- `fc-grand-total` for Est. Total Y1 Revenue
- `fc-cell-runtime` for readonly cells
- `fc-input-native` for editable cells (baseline: none, user project: ppa_base_tariff only)
- Numeric right-alignment via `fc-cell--amount`
- Informational footer with tariff/escalation/ppa term summary

### 2. Data Model (`app/ui/project_context.py`)

**New function:** `_build_revenue_items(revenue, technical, technology) → tuple[dict, ...]`
- Builds 12 serializable revenue items from `RevenueParams` + `TechnicalParams`
- Groups: Production, PPA/Tariff, Market/Merchant, CO2/Certificates
- Each item: `code`, `name`, `value`, `unit`, `group`, `editable`, `hint`
- Backward-compatible: only uses existing domain fields, no new schema

**New field:** `ProjectContext.revenue_items: tuple[dict[str, Any], ...]`
- Wired into `_build_context_from_project_inputs()`

**Revenue items (TUHO Wind, 12 total):**

| Code | Name | Value | Unit | Editable |
|------|------|-------|------|----------|
| `capacity_mw` | Installed Capacity | 35.0 | MW | No |
| `operating_hours_p50` | P50 Hours / Year | 4164.0 | h/yr | No |
| `plant_availability` | Plant Availability | 1.0 | % | No |
| `grid_availability` | Grid Availability | 1.0 | % | No |
| `ppa_base_tariff` | Base Tariff (PPA) | 60.0 | EUR/MWh | **Yes** |
| `ppa_index` | Tariff Escalation | 0.02 | %/yr | No |
| `ppa_term_years` | PPA Term | 12 | years | No |
| `ppa_production_share` | PPA Production Share | 1.0 | % | No |
| `balancing_cost` | Balancing Cost | 8.0 | EUR/MWh | No |
| `first_merchant_period` | First Merchant Period | 24 | period index | No |
| `co2_enabled` | CO2 Certificates Enabled | 1.0 | flag | No |
| `co2_price` | CO2 Price (Y1) | 4.191 | EUR/MWh | No |

### 3. Snapshot Persistence (`main_web.py`)

**New fields in `_collect_form_snapshot()`:**
- `rev_ppa_base_tariff`
- `rev_ppa_index`
- `rev_ppa_term_years`
- `rev_ppa_production_share`
- `rev_balancing_cost`
- `rev_co2_enabled`
- `rev_co2_price`

### 4. CSS (`static/styles.css`)

**Phase 20K block (+95 lines):**
- `.fc-revenue-grid-wrapper` — overflow positioning
- `.inp-dirty-indicator` — unsaved edits indicator
- `.inp-readonly-notice--revenue` — baseline readonly notice
- `.fc-input-native` — revenue editable input styling
- `.fc-subtotal-row` — subtotal row background
- `.fc-grand-total` — grand total row with accent border
- `.fc-cell--notes` — hint/notes column styling
- Numeric right-alignment via `.fc-cell--amount`

---

## What was NOT changed

- ❌ No formula changes in any engine
- ❌ No workbook calculation changes
- ❌ No Excel export/build logic changes
- ❌ No JS financial calculations
- ❌ No domain model changes
- ❌ No construction/debt/IDC changes
- ❌ No G20/R99/R102 changes
- ❌ No React/Tailwind

---

## Backend remains source of truth

Revenue totals in the grid (Y1 PPA Revenue, CO2 Revenue, Est. Total) are **informational estimates** computed client-side from `ppa_tariff × operating_hours × capacity × availability`. The actual runtime revenue is computed by the backend engine after `Run` and displayed in the Runtime Summary.

---

## Scope guard

Only TUHO and Oborovo revenue items defined in `app/project_factories.py` are wired. Generic wind/solar use factory defaults.

---

## Tests: 14 new + regression suite

| Test class | Tests |
|------------|-------|
| `TestRevenueGridRendering` | 20 |
| `TestRevenueReadonlyBaseline` | 3 |
| `TestOborovoRevenueGrid` | 2 |
| `TestRevenueSnapshotPersistence` | 3 |
| `TestPhase20KNoRegression` | 5 (subprocess) |
| **Total** | **33+ subprocess** |

Regression: Phase 20J, 20I, 20H, auth (via subprocess)

---

## Known limitations

1. **Only ppa_base_tariff is editable** — all other revenue items are readonly (set via Inputs tab)
2. **Y1 revenue is informational estimate** — not the authoritative runtime value
3. **No per-line scenario compare** for revenue (future phase)
4. **No dirty indicator JS** — CSS/hTML structure present, JS wiring not implemented
5. **No CO2 sub-items** — CO2 is shown as two rows; detailed schedule not exposed
6. **Merchant share / capture rate** — not exposed in current domain model

---

## Recommended next phase

**Phase 20L — Revenue Detail Grid: Dirty Indicator + Full Editability**

Wire the dirty indicator JS for revenue edits, add remaining editable fields (ppa_index, balancing_cost), and implement delta warnings between draft and saved values for all revenue items.
