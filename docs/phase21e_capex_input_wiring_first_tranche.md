# Phase 21E — CAPEX Input Wiring First Tranche

## Executive Summary
Applies Phase 21D schema design (`CapexScope`) to the CAPEX detail grid display/data layer in `project_context.py`. EPC C.02 now carries `payment_batch` scope on all children. Grid C.03 shows `fee_only` on GPA fee (C.03.01). C.16 Project Rights shows `project_rights` scope. M1-M18 schedule rows carry `timing_only=True` and `schedule_note`. All changes are display-only; no runtime calculations, CFADS, IRR, debt, tax, revenue, or OPEX are affected.

## What Changed

### `app/ui/project_context.py`
- **Import**: `CapexScope` from `app.domain.capex.source_model`
- **`_derive_scope()`** (Phase 21E, nested in `_build_capex_detail_items`):
  - `C.02` + `runtime_field == "epc_contract"` → `AGGREGATE_TOTAL`
  - `C.02` + otherwise (C.02.01–04) → `PAYMENT_BATCH`
  - `C.03` + `runtime_field == "grid_connection"` → `AGGREGATE_TOTAL`
  - `C.03` + `excel_code == "C.03.01"` → `FEE_ONLY`
  - `C.03` + otherwise (C.03.02 zero row) → `GENERIC`
  - `C.16` (any) → `PROJECT_RIGHTS`
  - backend rows → `FINANCING_COST`
  - `C.18` → `RESERVE_ACCOUNT`
  - `C.07` → `LAND`
  - default → `GENERIC`
- **`timing_only`** / **`schedule_note`**: rows whose `monthly_schedule_source in ("excel_m1_m18", "app_profile")` get `timing_only=True` and `schedule_note = "M1-M18 schedule is timing-only — used for construction draw/IDC timing, not a duplicate CAPEX total."`
- All child rows now include `scope`, `timing_only`, `schedule_note` in their returned dict

### `app/templates/partials/sheet_capex_detail.html`
- **Scope badges** added after runtime impact dot (lines 359-376):
  - `badge-scope-aggregate` (blue "agg✓") — `scope == 'aggregate_total'`
  - `badge-scope-payment-batch` (purple "pymt") — `scope == 'payment_batch'`
  - `badge-scope-fee-only` (gray "fee") — `scope == 'fee_only'`
  - `badge-scope-project-rights` (orange "rights") — `scope == 'project_rights'`
  - `badge-scope-timing-only` (teal "tim") — `scope == 'timing_only'`
- **CSS** added for all 5 scope badge classes
- **Legend** extended with Phase 21E scope section listing all 5 scope types

## What Did NOT Change
- No CAPEX totals changed
- No runtime calculations changed
- No line editing implemented
- No wiring to construction IDC
- No changes to CFADS, IRR, debt, SHL, DSCR, tax, revenue, OPEX
- EPC C.02 app aggregate (52,800 kEUR) shown indirectly via `payment_batch` scope on existing children — NOT as a separate synthetic row (requires C.02 aggregated category row to have children in `_EXCEL_ROWS` structure, which it does not; see Architecture Notes below)
- `epc_contract` amount is not separately rendered as an `aggregate_total` row in C.02 (C.02 category row has no children mapped to `epc_contract` directly)

## Architecture Notes

### Why C.02 Shows `payment_batch` (Not `aggregate_total`) on Existing Children
The `_EXCEL_ROWS` data loop populates C.02 with children C.02.01–C.02.04. None of these map directly to `epc_contract` — they resolve via `epc_other` (C.02.01–03) or `grid_connection` (C.02.04). The `epc_contract` field is only accessible at the category level (`cap_code == "C.02"` → runtime_field `"epc_contract"`). To inject a true `aggregate_total` row for the full 52,800 kEUR EPC value as a separate child, a synthetic row would need to be inserted into the children list in the category loop. This is planned for a future tranche.

### C.03 GPA Fee — `fee_only` on C.03.01
Excel C.03.01 (GPA administrative fee, 30 kEUR) is now explicitly tagged `fee_only`. This distinguishes it from the app's `grid_connection` field (6,200 kEUR full interconnection), which the `affects_runtime=False` status already separates. The `≠scp` badge (already present) signals `scope_mismatch` on C.03.01 to users.

### C.16 Project Rights Scope
C.16.01–03 map to `backend_acquisition` field (app=0), resulting in `scope_mismatch` authority status. The explicit `project_rights` scope makes the intended treatment (accounting/tax/funding) clear to users reviewing the grid.

## Recommended Next Phase
Phase 21F: Enable line editing for `app_mapped` rows, wire C.16 to runtime after accounting confirmation, inject synthetic `aggregate_total` row for EPC C.02, and bridge M1-M18 to construction IDC draw schedule.

## Tests
- 19/19 Phase 21E tests pass (`tests/test_phase21e_capex_input_wiring_first_tranche.py`)
- 13/13 Phase 21D tests pass
- 32/32 Phase 21C tests pass
- 47/47 Phase 21B tests pass
- 31/31 revenue + OPEX tests pass

## Branch & Commit
- Branch: `phase21e-capex-input-wiring-first-tranche`
- Base: `origin/main` @ `8b72b6a`
- Files changed: `app/ui/project_context.py` (`_derive_scope` + scope/timing fields), `app/templates/partials/sheet_capex_detail.html` (scope badges + CSS + legend), `tests/test_phase21e_capex_input_wiring_first_tranche.py` (new), `docs/phase21e_capex_input_wiring_first_tranche.md` (this file)
