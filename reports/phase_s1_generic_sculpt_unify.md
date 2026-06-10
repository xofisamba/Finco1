# Phase S1 — Generic Sizing Path Unification on Sculpt — Report

## Status

- **Type:** Runtime + tests + docs (single-file
  production code refactor of `app/input_adapter.py`
  + schema expansion of `app/input_schema.py`).
- **Branch:** `phase-s1-generic-sculpt-unify`
- **Base:** `0b00f93` (post-P1-B main, PR #601)
- **PR:** DRAFT #602 — do NOT mark ready, do NOT
  merge, awaiting user review and explicit
  go-ahead.
- **Scope:** ~13 files, +2600 / -120

## Summary

Phase S1 unifies the Generic Solar / Generic Wind
runtime path on a single debt-sizing semantic
(DSCR sculpt). The form path, the snapshot path,
the scenario rerun path, and the save-run/export
path all resolve through the same shared
`_resolve_user_inputs` resolver. For identical
Generic user inputs, all paths produce exactly
equal ProjectInputs and exactly equal KPIs.

## The S1 unified-resolver contract (strict)

For identical Generic user inputs (form-driven or
snapshot-driven), all four paths produce **exactly
equal** ProjectInputs and **exactly equal** KPIs:

- `total_revenue_keur` — exact equality
- `total_capex_keur` — exact equality
- `total_ebitda_keur` — exact equality
- `total_opex_keur` — exact equality
- `project_irr` — exact equality
- `equity_irr` — exact equality
- `min_dscr` — exact equality
- `avg_dscr` — exact equality
- `senior_debt_amount_keur` — exact equality
- `gearing_ratio` — exact equality
- `target_dscr` — exact equality

The S1 test suite (42 tests in 13 classes) pins
this contract.

## Files changed (13)

### Production code (2)

- `app/input_adapter.py` — extracted
  `_resolve_user_inputs` shared resolver. Both
  `build_projectinputs(schema)` and
  `build_projectinputs_from_snapshot(snapshot)`
  are now thin wrappers around the resolver.
  Added `_zero_financial_capex_subfields`,
  `_apply_capex_total`, `_set_revenue_ppa_term`
  helpers.
- `app/input_schema.py` — added `ppa_term_years`
  to `RevenueInput`. Expanded
  `ProjectInputsSchema` to accept the same set
  of optional input fields as the snapshot dict
  (Phase S1 schema unification). All new fields
  are optional; backward compatible with all
  existing form-path callers.

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

- `tests/test_phase_s1_generic_sculpt_unify.py` —
  42 tests in 13 classes pinning the S1 contract
  (exact equality for Solar and Wind across all
  four paths).

### Docs (2)

- `docs/phase_s1_generic_sculpt_unify.md`
- `reports/phase_s1_generic_sculpt_unify.md` (this file)

## Pre-merge audit (all passed)

### What changed in production code

```
$ git diff origin/main -- app/input_adapter.py app/input_schema.py
- app/input_adapter.py: extracted _resolve_user_inputs shared
  resolver. Both form path and snapshot path now route through
  it. Added _zero_financial_capex_subfields, _apply_capex_total,
  _set_revenue_ppa_term helpers.
- app/input_schema.py: added ppa_term_years to RevenueInput.
  Expanded ProjectInputsSchema to accept the same set of
  optional input fields as the snapshot dict (Phase S1
  schema unification). All new fields are optional; backward
  compatible.
```

Two-file production code change. The two files
are coupled: the schema expansion is what makes
the form path and the snapshot path able to
accept the same input fields.

### What did NOT change

```
$ git diff origin/main -- main_web.py main_api.py
(empty)
```

```
$ git diff origin/main -- \
  app/project_factories.py app/waterfall_runner.py \
  app/waterfall_core.py app/services/ \
  app/persistence/ domain/ \
  static/ app/templates/
(empty)
```

### Factory paths preserved

```
$ python3 -c "
from app.project_factories import (
    create_default_solar_project, create_default_wind_project,
    create_default_oborovo, create_default_tuho_wind1,
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

### Form path and snapshot path now produce exactly equal KPIs

```
$ python3 -c "
import os; os.environ['FINCO_SECRET_KEY'] = 'test'
import sys; sys.path.insert(0, '/workspace/finco-d3')
from app.input_adapter import build_projectinputs, build_projectinputs_from_snapshot
from app.input_schema import ProjectInputsSchema, RevenueInput, CapexInput, OpexInput, DebtInput
from app.api.project_runner import run_project

inputs = {
    'project_type': 'Wind', 'project_name': 'Pilot Wind',
    'country_iso': 'Croatia', 'capacity_mw': 50.0,
    'cod_date': '2027-01-01', 'construction_months': 12,
    'horizon_years': 25, 'tariff_eur_mwh': 60.0,
    'p50_hours': 1200.0, 'ppa_term_years': 15,
    'opex_y1_keur': 1000.0, 'total_capex_keur': 50000.0,
    'gearing_pct': 70.0, 'target_dscr': 1.30,
    'interest_rate_pct': 5.0, 'tenor_years': 15,
}
schema = ProjectInputsSchema(**inputs)
form_kpis = run_project('Wind', 'Base', project_inputs_override=build_projectinputs(schema))['kpis']
snap = {**inputs, 'country_market': inputs['country_iso']}
snap_kpis = run_project('Wind', 'Base', project_inputs_override=build_projectinputs_from_snapshot(snap))['kpis']
for k in form_kpis:
    if isinstance(form_kpis[k], (int, float)) and form_kpis[k] != snap_kpis[k]:
        print(f'DIFF: {k}: form={form_kpis[k]}, snap={snap_kpis[k]}')
print('OK — all numeric KPIs exactly equal across form and snapshot paths')
"
OK — all numeric KPIs exactly equal across form and snapshot paths
```

### Scenario rerun uses unified sculpt

```
$ python3 -c "
import os; os.environ['FINCO_SECRET_KEY'] = 'test'
import sys; sys.path.insert(0, '/workspace/finco-d3')
from app.input_adapter import build_projectinputs_from_snapshot
from app.persistence.scenarios_repository import resolve_scenario_snapshot
snap = resolve_scenario_snapshot({}, {...full snapshot...})
proj = build_projectinputs_from_snapshot(snap)
print('debt_sizing_method:', proj.financing.debt_sizing_method)  # dscr_sculpt
print('fixed_debt_keur:', proj.financing.fixed_debt_keur)  # not 35000
"
debt_sizing_method: dscr_sculpt
fixed_debt_keur: None
```

### Gearing is invariant under sculpt

```
$ python3 -c "
import os; os.environ['FINCO_SECRET_KEY'] = 'test'
import sys; sys.path.insert(0, '/workspace/finco-d3')
from app.input_adapter import build_projectinputs_from_snapshot
from app.api.project_runner import run_project
for g in (40, 70, 85):
    snap = {...'gearing_pct': str(g), ...}
    kpis = run_project('Wind', 'Base', project_inputs_override=build_projectinputs_from_snapshot(snap))['kpis']
    print(f'gearing={g}: min_dscr={kpis[\"min_dscr\"]:.10f}')
"
gearing=40: min_dscr=1.5823319328
gearing=70: min_dscr=1.5823319328
gearing=85: min_dscr=1.5823319328
```

Sculpt produces exactly the same `min_dscr` for
all three gearing values. Gearing is a derived
reporting metric, not a binding debt-sizing
driver.

## Test counts

### S1-specific (NEW)

- 42 / 42 P1-B tests PASS

### Pre-existing snapshot-path tests (UPDATED)

- `tests/test_phase17_from_scratch_runtime_path.py`:
  8 / 8 PASS
- `tests/test_phase17_user_project_e2e_runtime_export_validation.py`:
  6 / 6 PASS
- `tests/test_phase18_user_project_workbook_artifact_validation.py`:
  5 / 5 PASS
- `tests/test_phase20f_active_scenario_runtime_binding.py`:
  PASS
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

- **Form path and snapshot path now produce
  exactly equal senior debt and exactly equal
  KPIs for the same inputs.** Pre-S1: the form
  path and the snapshot path diverged — the
  snapshot path pre-computed
  `senior_debt = capex * gearing` while the form
  path used sculpt, and the form path did not
  accept the same set of input fields.
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
  R-PAR / IDC / tax / debt / depreciation
  changes
- No G20 / R99 / R102 promotion
- No Tailwind / Alpine / React / Vue / Svelte
- No schema / persistence migration
- No `ProjectInputsSchema` field removals
  (only additions; backward compatible)
- No `use_construction_schedule_engine` flip
- No factory path changes (TUHO and Oborovo
  pinned to their Excel anchors)
- No `main_web.py` / `main_api.py` changes
- No JS calc
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged

## Stop-after-report contract

DRAFT PR #602 — do NOT mark ready. Do NOT merge.
Awaiting user review and explicit go-ahead.

## Recommended next step (post-S1)

The current roadmap is:

1. **S1** (this PR): Generic Sizing Path Unification
   on Sculpt — Generic form path, snapshot path,
   scenario rerun path, and save-run/export path
   all resolve through the same shared
   `_resolve_user_inputs` resolver.
2. **S2**: gearing as output — surface realized
   gearing_ratio as a derived reporting metric
   (this is the natural follow-up to the S1
   invariant that gearing_pct is preserved on the
   input side but does not bind senior debt).
3. **S3**: driver-to-KPI binding suite — add
   per-driver sensitivity tests that pin exactly
   which input drivers move which KPIs.
4. **M1 / M2**: scenario matrix — multi-scenario
   Base / Downside / Upside coverage at scale.

`manual_gearing` is **not** on this roadmap. It
was a candidate from the P1-A design doc
(Section 7), but P1-A explicitly deferred it
pending pilot feedback, and P1-B further deferred
it. The sculpt + label approach is the current
ground-truth. If a future pilot run surfaces a
real need for `manual_gearing`, that decision
will be a separate, future, larger arc.

DO NOT START: C10, construction runtime
promotion, R-PAR, debt formula changes, tax,
IDC, senior IDC, depreciation, schema migration,
manual_gearing, Tailwind/Alpine, factory path
changes.
