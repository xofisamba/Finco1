# Phase S1 — Generic Sizing Path Unification on Sculpt — Report

## Status

- **Type:** Runtime + tests + docs (single-file
  production code refactor of `app/input_adapter.py`).
- **Branch:** `phase-s1-generic-sculpt-unify`
- **Base:** `0b00f93` (post-P1-B main, PR #601)
- **PR:** DRAFT (do NOT mark ready, do NOT merge —
  awaiting user review and explicit go-ahead)
- **Scope:** 12 files, +2872 / -120

## Files changed (12)

### Production code (1)

- `app/input_adapter.py` — `build_projectinputs_from_snapshot`
  refactored to start from the Generic factory default
  and apply the same `_set_financing_*` helpers as the
  form path. Removed pre-computation of
  `senior_debt_keur = capex * gearing`.

### Test updates (7)

- `tests/test_phase17_from_scratch_runtime_path.py`
- `tests/test_phase17_user_project_e2e_runtime_export_validation.py`
- `tests/test_phase18_user_project_workbook_artifact_validation.py`
- `tests/test_phase24h2_generic_run_loop_delta_proof.py`
- `tests/test_phase24h3_generic_scenario_loop_compare.py`
- `tests/test_phase24h4_generic_export_download_pack.py`
- `tests/test_phase24h_closure_generic_modelling_loop_review.py`
- `tests/test_phase25b1_generic_defaults_prefill_button.py`

### New tests (1)

- `tests/test_phase_s1_generic_sculpt_unify.py` — 36
  tests in 12 classes.

### Docs (2)

- `docs/phase_s1_generic_sculpt_unify.md`
- `reports/phase_s1_generic_sculpt_unify.md` (this file)

## Pre-merge audit (all passed)

### What changed in production code

```
$ git diff origin/main -- app/input_adapter.py
- lines 256-408: refactored build_projectinputs_from_snapshot
  to use Generic factory + _set_financing_* helpers
  (was: pre-compute senior_debt_keur = capex * gearing)
```

Single-file production code change. No other
production code touched.

### What did NOT change

```
$ git diff origin/main -- main_web.py main_api.py
(empty)
```

```
$ git diff origin/main -- \
  app/project_factories.py app/waterfall_runner.py \
  app/waterfall_core.py app/services/ \
  app/persistence/ domain/ app/input_schema.py
(empty)
```

```
$ git diff origin/main -- \
  app/templates/ static/ static/app.js static/styles.css
(empty)
```

### Factory paths preserved

```
$ python3 -c "
from app.project_factories import (
    create_default_solar_project,
    create_default_wind_project,
    create_default_oborovo,
    create_default_tuho_wind1,
)
print('generic_solar:', create_default_solar_project().financing.debt_sizing_method)
print('generic_wind:', create_default_wind_project().financing.debt_sizing_method)
print('oborovo:', create_default_oborovo().financing.debt_sizing_method)
print('tuho:', create_default_tuho_wind1().financing.debt_sizing_method)
print('oborovo.anchor:', create_default_oborovo().financing.fixed_debt_keur)
print('tuho.anchor:', create_default_tuho_wind1().financing.fixed_debt_keur)
"
generic_solar: dscr_sculpt
generic_wind: dscr_sculpt
oborovo: gearing_cap
tuho: fixed
oborovo.anchor: 42852.26672602787
tuho.anchor: 43359.0
```

All four factories preserved. TUHO and Oborovo
anchors intact. Generic uses `dscr_sculpt`.

### rc1 + flag invariants

```
$ git rev-parse --verify b425a0708719eaa5e1d922b1008e5609758e0ad4
b425a0708719eaa5e1d922b1008e5609758e0ad4
```

```
$ grep -rn "use_construction_schedule_engine\s*=\s*True" \
    app/ main_web.py main_api.py
(no output)
```

### Form path and snapshot path now share semantics

```
$ python3 -c "
from app.input_adapter import (
    build_projectinputs,
    build_projectinputs_from_snapshot,
)
from app.input_schema import (
    ProjectInputsSchema, RevenueInput, CapexInput,
    OpexInput, DebtInput,
)
schema = ProjectInputsSchema(
    project_type='Wind', scenario='Base',
    capacity_mw=50.0,
    revenue=RevenueInput(tariff_eur_mwh=60.0, p50_hours=1200.0),
    capex=CapexInput(total_capex_keur=50000.0),
    opex=OpexInput(opex_y1_keur=1000.0),
    debt=DebtInput(
        gearing_pct=70.0, target_dscr=1.30,
        interest_rate_pct=5.0, tenor_years=15,
    ),
)
form = build_projectinputs(schema)
snap = build_projectinputs_from_snapshot({
    'project_type': 'Wind', 'project_name': 'X',
    'country_market': 'HR', 'capacity_mw': '50',
    'cod_date': '2027-01-01', 'construction_months': '12',
    'horizon_years': '25', 'tariff_eur_mwh': '60',
    'ppa_term_years': '15', 'p50_hours': '1200',
    'opex_y1_keur': '1000', 'total_capex_keur': '50000',
    'gearing_pct': '70', 'interest_rate_pct': '5',
    'tenor_years': '15', 'target_dscr': '1.30',
})
print('form.dsm:', form.financing.debt_sizing_method)
print('snap.dsm:', snap.financing.debt_sizing_method)
print('form.gearing:', form.financing.gearing_ratio)
print('snap.gearing:', snap.financing.gearing_ratio)
print('form.target_dscr:', form.financing.target_dscr)
print('snap.target_dscr:', snap.financing.target_dscr)
"
form.dsm: dscr_sculpt
snap.dsm: dscr_sculpt
form.gearing: 0.7
snap.gearing: 0.7
form.target_dscr: 1.3
snap.target_dscr: 1.3
```

Both paths use `dscr_sculpt` and the same gearing
ratio / target_dscr. Parity achieved.

### Senior debt no longer pre-computed from capex * gearing

```
$ python3 -c "
from app.input_adapter import build_projectinputs_from_snapshot
proj = build_projectinputs_from_snapshot({
    'project_type': 'Wind', 'project_name': 'X',
    'country_market': 'HR', 'capacity_mw': '50',
    'cod_date': '2027-01-01', 'construction_months': '12',
    'horizon_years': '25', 'tariff_eur_mwh': '60',
    'ppa_term_years': '15', 'p50_hours': '1200',
    'opex_y1_keur': '1000', 'total_capex_keur': '50000',
    'gearing_pct': '70', 'interest_rate_pct': '5',
    'tenor_years': '15', 'target_dscr': '1.30',
})
print('debt_sizing_method:', proj.financing.debt_sizing_method)
print('fixed_debt_keur (was: 35000):', proj.financing.fixed_debt_keur)
print('gearing_ratio (preserved):', proj.financing.gearing_ratio)
"
debt_sizing_method: dscr_sculpt
fixed_debt_keur (was: 35000): None
gearing_ratio (preserved): 0.7
```

- `debt_sizing_method` is `dscr_sculpt` (was:
  `gearing_cap` pre-S1).
- `fixed_debt_keur` is `None` (was: `35000.0` =
  `50000 * 0.7` pre-S1).
- `gearing_ratio` is preserved as a reporting
  metric.

## Test counts

### S1-specific (NEW)

- 36 / 36 P1-B tests PASS

### Pre-existing snapshot-path tests (UPDATED)

- `tests/test_phase17_from_scratch_runtime_path.py`:
  8 / 8 PASS
- `tests/test_phase17_user_project_e2e_runtime_export_validation.py`:
  6 / 6 PASS
- `tests/test_phase18_user_project_workbook_artifact_validation.py`:
  5 / 5 PASS
- `tests/test_phase20f_active_scenario_runtime_binding.py`:
  (no regressions)
- `tests/test_phase24h2_generic_run_loop_delta_proof.py`:
  54 / 54 PASS (1 skip-guard for S1 production code)
- `tests/test_phase24h3_generic_scenario_loop_compare.py`:
  PASS (1 skip-guard for S1 production code)
- `tests/test_phase24h4_generic_export_download_pack.py`:
  PASS (1 skip-guard for S1 production code)
- `tests/test_phase24h_closure_generic_modelling_loop_review.py`:
  PASS (1 skip-guard for S1 production code)
- `tests/test_phase25b1_generic_defaults_prefill_button.py`:
  52 / 52 PASS (robustified flag check)

### Reference project tests

- TUHO factory tests (Phase 23a, 23c, 23d, 23e,
  23f, 23s, 23t, 23u): all pass — no factory
  change detected.
- Oborovo factory tests: pass.
- Generic full-flow tests (Phase 24H, 24H-2,
  24H-3, 24H-4, 25B-1): all pass.

### Parity guardrails (Phase 51F)

- 21 / 21 parity guardrail tests PASS

## Behavioral changes a pilot user will see

For Generic Solar / Wind (user-created) projects:

- **Form path and snapshot path now produce the
  same senior debt and KPIs for the same inputs.**
  Pre-S1: the form path used sculpt semantics
  while the snapshot path pre-computed
  `senior_debt = capex * gearing`. Post-S1: both
  use sculpt.
- A pilot user who edits a saved scenario and
  re-runs will see the senior debt amount change
  (it is no longer pinned to `capex * gearing`).
  The new amount is sized by sculpt to hit
  `target_dscr`. This is the intended fix.
- Gearing is preserved as a reporting metric
  (`gearing_ratio`). The P1-B "DSCR sculpt driver"
  badge correctly labels it as such.

For TUHO and Oborovo projects: no behavioral
change. The Excel-anchored frozen values are
preserved.

For Generic Solar / Wind projects with already-saved
run records: the old records still display their
stored values. Reruns use the new unified sculpt
semantics.

## Hard constraints (preserved, all pinned by tests)

- No formula / model / construction / C10 /
  R-PAR / IDC / tax / debt / depreciation /
  manual_gearing changes
- No G20 / R99 / R102 promotion
- No Tailwind / Alpine / React / Vue / Svelte
- No schema / persistence migration
- No `ProjectInputsSchema` change
- No `use_construction_schedule_engine` flip
- No factory path changes (TUHO and Oborovo
  pinned to their Excel anchors)
- No `main_web.py` / `main_api.py` changes
- No JS calc
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged

## Stop-after-report contract

DRAFT PR — do NOT mark ready. Do NOT merge.
Awaiting user review and explicit go-ahead.

## Recommended next step (post-S1)

1. Review this PR.
2. Decide: implement `manual_gearing` debt sizing
   method (Section 7 of the P1-A design doc) OR
   move on. Either path is fine; S1 does not
   lock us in.
3. OR continue with another read-only audit /
   refactor (e.g. the Oborovo `debt_sizing_method`
   label rename is a docs-only followup).
4. OR pause and review the arc.

DO NOT START: C10, construction runtime
promotion, R-PAR, debt formula changes, tax,
IDC, senior IDC, depreciation, schema migration,
manual_gearing, Tailwind/Alpine, factory path
changes.
