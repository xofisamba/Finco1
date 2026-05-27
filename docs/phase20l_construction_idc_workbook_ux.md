# Phase 20L — Construction / IDC Workbook UX Foundation

**Branch:** `phase20l-construction-idc-workbook-ux`
**Base:** `5e9aabc7cff2c9e008ab1abd8c6689845941dafe` (Phase 20K merge)
**Date:** 2026-05-27
**Status:** Implemented, pending review

---

## Goal

Add workbook-style Construction and IDC tabs to the UI — the fifth and sixth sheets in the fc-grid workbook family — using the Phase 20H `fc-*` design system, without rewriting any engine logic.

---

## What was built

### 1. Construction Workbook Grid (`app/templates/partials/sheet_construction.html`)

Redesigned from 76-line summary card layout to a full fc-grid workbook:

**Construction Summary Cards:**
- Financial Close, COD, Construction Period, Total CAPEX
- Senior Debt, SHL Amount, SHL Rate, IDC (Total)

**Monthly Drawdown Schedule (Audit/Preview):**
```
┌────────────┬──────┬──────────┬─────────┬─────────┬────────────────┬───────────┬─────────────┐
│ Line Item │ Unit │ Equity   │ SHL     │ Junior  │ Senior Debt    │ Total Draw│ Cumul. Uses│
├────────────┼──────┼──────────┼─────────┼─────────┼────────────────┼───────────┼─────────────┤
│ Month 1       │ kEUR │ 500.0   │ 23,727  │  0.0    │  0.0           │ 24,227    │ 24,227     │
│ Month 2       │ kEUR │ 500.0   │  8,869  │  0.0    │  0.0           │  9,369    │ 33,596     │
│ ...           │ ...  │ ...     │ ...     │ ...     │ ...            │ ...       │ ...        │
│ Funding Summary [BAND]                                                                             │
│ Total Equity Draw      │  3,000  kEUR                                                          │
│ Total SHL Principal    │ 29,135  kEUR                                                             │
│ Total Senior Principal │ 43,359  kEUR                                                             │
│ Total Junior Draw      │  0      kEUR                                                             │
│ Total Uses (CAPEX)     │ 72,994  kEUR ← grand total                                               │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- `fc-grid` + `fc-grid-wrapper--scroll-x` for horizontal scrolling
- Monthly rows: equity, SHL, junior, senior draw + total + cumulative uses
- `fc-section-band` for Funding Summary
- `fc-subtotal-row` for each funding source total
- `fc-grand-total` for Total Uses
- "Audit / Preview" badge on monthly grid
- Backend remains authoritative

### 2. IDC Workbook Grid (`app/templates/partials/sheet_idc.html`)

New dedicated IDC tab with summary grid + monthly detail:

**IDC Summary Grid:**
```
┌──────────────────────────────────┬──────────┬───────────┬──────┬──────────────────┬─────────────┐
│ Line Item                   [sticky│ Code     │ Value     │ Unit │ Group            │ Note        │
├──────────────────────────────────┼──────────┼───────────┼──────┼──────────────────┼─────────────┤
│ Senior Debt                 [BAND]│          │           │      │                  │             │
│  Senior Debt Principal Draw         │ senior… │ 43,359   │ kEUR │ Senior Debt      │ Runtime     │
│  Senior Debt IDC                    │ senior… │  1,520   │ kEUR │ Senior Debt      │ Runtime     │
│  Opening Senior Balance (COD)       │ open…   │ 43,359   │ kEUR │ Senior Debt      │ Runtime     │
│ SHL                          [BAND]│          │           │      │                  │             │
│  SHL Principal Draw                │ shl_p…  │ 29,135   │ kEUR │ SHL              │ Runtime     │
│  SHL IDC                           │ shl_i…  │  3,569   │ kEUR │ SHL              │ Runtime     │
│  Opening SHL Balance (COD)         │ open…   │ 32,704   │ kEUR │ SHL              │ Runtime     │
│ IDC Summary                   [BAND]│          │           │      │                  │             │
│  Total IDC                          │ total…  │  5,088   │ kEUR │ IDC Summary      │ SHL+Senior  │
│  Opening Senior Excl. IDC           │ open…   │ 41,840   │ kEUR │ IDC Summary      │ Runtime     │
│ Total IDC (kEUR)              [TOT] │          │  5,088   │ kEUR │                  │             │
└──────────────────────────────────┴──────────┴───────────┴──────┴──────────────────┴─────────────┘
```

**Monthly IDC Detail (Audit/Preview):**
- Month-by-month Senior IDC accrual
- Cumulative Senior IDC running total

### 3. Data Model (`app/ui/project_context.py`)

**New function:** `_build_construction_items(project_inputs) → tuple[dict, ...]`
- Calls `build_runtime_construction_schedule(project_inputs)` for TUHO/Oborovo
- Returns 18 monthly rows (TUHO) / 12 monthly rows (Oborovo) + 5 summary rows
- Monthly: `equity_draw`, `shl_draw`, `junior_draw`, `senior_draw`, `total_draw`, `cumulative_uses`
- Summary: Total Equity, SHL Principal, Senior Principal, Junior, Total Uses
- Marked `audit_only=True` for monthly rows

**New function:** `_build_idc_items(project_inputs) → tuple[dict, ...]`
- Returns 8 IDC summary items + monthly IDC entries
- Senior: `senior_principal_draw`, `senior_idc`, `opening_senior_balance`
- SHL: `shl_principal_draw`, `shl_idc`, `opening_shl_balance`
- Summary: `total_idc`, `opening_senior_excl_idc`
- Monthly: `monthly_idc` entries with `senior_idc_keur`, `cumulative_senior_idc_keur`

**New fields in `ProjectContext`:**
- `construction_items: tuple[dict[str, Any], ...]`
- `idc_items: tuple[dict[str, Any], ...]`

### 4. Snapshot Persistence (`main_web.py`)

**New fields in `_collect_form_snapshot()`:**
- `construction_months`
- `idc_keur`

### 5. CSS (`static/styles.css`) — +100 lines Phase 20L block

- `.fc-grid-wrapper--scroll-x` — horizontal scroll
- `.fc-const-idc-cards` — construction summary card grid
- `.inp-readonly-notice--construction`, `.inp-readonly-notice--idc`
- `.badge-audit` — audit/preview badge
- `.fc-construction-grid-wrapper .fc-section-band` — section band background
- `.fc-idc-grid-wrapper .fc-grand-total` — IDC grand total styling

---

## What was NOT changed

- ❌ No formula changes in any engine
- ❌ No workbook calculation changes
- ❌ No Excel export/build logic changes
- ❌ No JS financial calculations
- ❌ No domain model changes
- ❌ No construction/debt/SHL engine rewrites
- ❌ No React/Tailwind

---

## Monthly grids are "Audit / Preview"

The monthly construction drawdown and IDC detail grids are clearly labeled "Audit / Preview" because:
- They are computed by the **offline** construction engine (`domain/construction/engine.py`)
- The offline engine is used for diagnostics and UI display
- The runtime waterfall model is the authoritative source
- Backend remains the single source of truth for all financial calculations

---

## TUHO data

| Metric | Value |
|--------|-------|
| Construction months (engine) | 18 |
| Total Uses (CAPEX) | 72,994 kEUR |
| Total Equity Draw | 3,000 kEUR |
| Total SHL Principal | 29,135 kEUR |
| Total Senior Principal | 43,359 kEUR |
| Senior IDC | 1,520 kEUR |
| SHL IDC | 3,569 kEUR |
| **Total IDC** | **5,088 kEUR** |

---

## Tests: 37 new + regression suite

| Suite | Result |
|-------|--------|
| `test_phase20l_construction_idc_ux.py` (37 new) | 37 passed |
| `test_phase20k_revenue_grid.py` | 29 passed |
| `test_phase20j_opex_grid.py` | 14 passed |
| `test_phase20i_capex_grid.py` | 10 passed |
| `test_phase20h_design_system_rendering.py` | 23 passed, 1 skipped |
| `test_phase20g_scenario_compare_history.py` | 26 passed |
| `test_phase20f_active_scenario_runtime_binding.py` | 7 passed |
| `test_phase20e_base_case_promotion.py` | 12 passed |
| `test_auth_lite.py` | 32 passed |
| **Total** | **171 passed, 1 skipped** |

*(5 auth failures are pre-existing on `main`, unrelated to this phase)*

---

## Known limitations

1. **Monthly grids are audit/preview only** — not yet runtime-authoritative
2. **No editable fields in Construction/IDC** — all fields are readonly
3. **Generic wind/solar projects** — fallback to empty items (not wired to generic factories)
4. **No IDC recalculation in UI** — IDC values come from offline engine, displayed as-is
5. **No per-funding-source monthly detail** for SHL junior/monthly IDC (future phase)
6. **No scenario compare** for Construction/IDC tabs (future phase)

---

## Recommended next phase

**Phase 20M — Debt Schedule Workbook Grid Foundation**

Build the Debt/Financing tabs (senior debt, SHL) as fc-grid workbook sheets, showing the sculpted debt schedule, DSCR, and reserve accounts — the next logical workbook grid counterpart to CAPEX/OPEX/Revenue/Construction/IDC.
