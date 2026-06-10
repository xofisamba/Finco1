# Phase 25C-1 — First-User Pilot Script (Generic Solar / Wind)

**Type**: UI only. **No** autosave. **No** backend
change. **No** feature flag enablement. **No** schema
change. **No** model formula change. **No** model
output computation (the helper is a read-side script
lister; the runtime is the source of truth for all
outputs).

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT
merge. Do NOT start any further runtime work before
review and explicit go-ahead.

**Base**: `c80fa3391e1c475d575c981244812e16c859a8dc` (post-25B
Closure merge).

**Branch**: `phase25c-1-pilot-script`

## 1. Goal

Provide a "Try this workflow" panel for exploratory
Generic Solar / Generic Wind users. The panel
shows the 9 canonical steps in order, with a clear
hint for each step, and a pre-existing route the
user can navigate to. No new routes are invented.
The helper does not claim Excel parity, lender
readiness, audit readiness, or bank approval.

## 2. The 9 steps (per the user's 25C-1 brief)

1. **Create Generic Solar** — `/projects/create`
2. **Use generic defaults** — `/scenarios/tab`
3. **Save Base** — `/scenarios/save`
4. **Run** — `/scenarios/run`
5. **Duplicate Downside** — `/scenarios/add`
6. **Change tariff / OPEX / CAPEX** — `/scenarios/tab`
7. **Run Downside** — `/scenarios/run`
8. **Compare Base vs Downside** — `/scenarios/compare`
9. **Export** — `/download`

## 3. Exploratory disclaimer

The helper exposes a single ``EXPLORATORY_DISCLAIMER``
string that the partial renders at the top of the
panel. The disclaimer explicitly says the workflow is
exploratory; outputs are **not** Excel-parity
validated, **not** lender-ready, **not** audit-ready,
and **not** bank-approved. This is descriptive scope
language, not a no-go claim.

## 4. Changed files (4 files, +1358 / -0)

| Status | File | Lines |
|---|---|---|
| A | `app/ui/generic_pilot_script.py` | +230 |
| A | `app/templates/partials/_generic_pilot_script_panel.html` | +60 |
| A | `tests/test_phase25c1_pilot_script_helpers.py` | +330 |
| A | `tests/test_phase25c1_pilot_script_factory_safety.py` | +360 |
| A | `docs/phase25c1_first_user_pilot_script.md` | this file |
| A | `reports/phase25c1_first_user_pilot_script.json` | summary |

**ZERO changes to**:
- `app/persistence/`
- `app/services/`
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `app/construction/`, `app/debt/`, `app/tax/`,
  `app/depreciation/`, `app/idc/`
- `static/app.js`, `static/styles.css`
- `main_web.py`, `main_api.py`, `domain/`
- `app/excel_export.py`

## 5. Self-review findings

- The 9 steps all map to **pre-existing** app routes;
  we never invent new ones. The `STEP_ROUTES`
  vocabulary is a frozen tuple that the test
  `test_all_routes_match_expected` pins.
- The exploratory disclaimer mentions
  "Excel-parity" and "validated" only in the
  *negation* ("not Excel-parity validated", "not
  lender-ready"). The helper never claims a project
  IS validated; the test `test_disclaimer_does_not_
  claim_lender_approval` pins this.
- The helper does not import `app.persistence` /
  `app.services` / `app.construction` / `app.debt` /
  `app.tax` / `app.idc` / `app.depreciation` /
  `app.waterfall`. The test
  `test_forbidden_module_not_imported` is
  parametrized over all 8 forbidden modules.
- The helper does not produce any numerical output.
  It does not call the runtime, does not compute
  IRR / DSCR / NPV, and does not invent run IDs.
  The test `test_helper_does_not_invent_outputs`
  pins this.

## 6. Pre-merge audit (all green)

- **Scope**: UI only. No backend change. No autosave.
- **Forbidden paths**: zero changes (all forbidden-paths tests pass)
- **Feature flags**: none enabled
  (`use_construction_schedule_engine=False`)
- **Schema**: zero migrations
- **rc1 SHA**: `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified
  untouched
- **Tests**: 37 helper tests + 22 factory safety tests = **59/59 new tests
  PASS**
- **No regressions**: 25B Closure 30/30 + 51F 21/21 + route
  smoke 50/17 = **139 passed / 38 skipped** in the focused run
- **Factory safety**: TUHO / Oborovo inputs unchanged;
  helper is a pure read-side classifier

## 7. Hard no-go (15 items, all verified pre-push)

1. no_autosave
2. no_persistence_schema_change
3. no_feature_flag_enablement
4. no_formula_changes
5. no_depreciation_changes
6. no_tax_changes
7. no_debt_changes
8. no_idc_changes
9. no_construction_promotion
10. no_rpar_changes
11. no_waterfall_core_changes
12. no_waterfall_runner_changes
13. no_services_changes
14. no_generic_depreciation_claims
15. rc1_frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)

## 8. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do
NOT start any further work before review and explicit
go-ahead. After approval, the recommended next step
is **Phase 25C-2 — User-Facing Error / Empty State
Cleanup** as a separate DRAFT PR.
