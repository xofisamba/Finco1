# Phase 53G-4 — save_scenario Persistence Extraction

## Context

Phase 53G-4 extracts the FIRST high-risk scenario write function
(`save_scenario`) from `app/persistence/repository.py` to
`app/persistence/scenarios_repository.py`.

This is **DRAFT ONLY** — must not be auto-merged. Requires explicit
user sign-off.

## What was extracted

| Function | Risk |
|---|---|
| `save_scenario` | **high** (1 of 4 remaining high-risk scenario writes) |

### Functions NOT in this PR (stay in `repository.py`)

- `add_scenario` (53G-5, next)
- `update_scenario_overrides` (53G-6)
- `get_or_create_base_case_scenario` (53G-7)

### Dataclasses remain in `repository.py`

`ProjectRecord`, `ScenarioRecord`, `WorkspaceStateRecord` (deferred until
after Group B per spec).

## Public compatibility

`save_scenario` re-exported from `app.persistence.repository`:

- `from app.persistence.repository import save_scenario` ✓
- `from app.persistence import save_scenario` ✓ (via `__init__.py`)

## LOC changes

- `app/persistence/repository.py`: 743 → 680 lines (-63, -8%)
- `app/persistence/scenarios_repository.py`: 280 → 346 lines (+66)

## Hard gates

- ✓ 628/628 tests pass (13 new 53G-4 + 16 53G-1 save_scenario re-pointed + 599 previous)
- ✓ 53G-1 save_scenario P0 pin re-pointed and still passes
- ✓ 53G-1 scenario/workspace coupling pin still passes (re-pointed TestSaveScenarioCoupling)
- ✓ Other 53G-1 P0 pins (add, update_overrides, base_case, coupling) untouched
- ✓ 53G-2/53G-3 structural tests pass (re-pointed to remove save_scenario from "still in repo" lists)
- ✓ Phase 51F guardrails pass (21/21)
- ✓ Phase 52F G1-G6 pass (10/10)
- ✓ No SQL text changes (byte-for-byte identical)
- ✓ No replay_metadata/governance_state/last_run_summary shape changes
- ✓ No route/service changes
- ✓ rc1 untouched (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged)
- ✓ Other high-risk scenario writes untouched
- ✓ Dataclasses untouched

## Test re-pointing

- `tests/test_phase53g1_save_scenario_p0_behavior_pin.py`: 16 tests, all re-pointed
  to read SQL fragments and body text from `scenarios_repository.py`.
  Added 2 new tests: `test_function_defined_in_scenarios_repository` +
  `test_function_not_defined_in_repository`.
- `tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py`: 2 tests
  re-pointed (`TestSaveScenarioCoupling.test_save_scenario_uses_insert_not_upsert`
  + `TestSaveScenarioCoupling.test_save_scenario_sets_replay_metadata_keys`).
- `tests/test_phase53g2_scenario_read_persistence_extraction.py`: removed
  `save_scenario` from `TestHighRiskScenarioWritesUntouched` parametrize list.
- `tests/test_phase53g3_low_risk_scenario_actions_extraction.py`: same.
- `tests/test_phase53a_persistence_helpers_extraction.py`: same.
- `tests/test_phase53b_persistence_runs_extraction.py`: same.
- `tests/test_phase53c_persistence_exports_audit_extraction.py`: same.
- `tests/test_phase53e2_project_write_persistence_extraction.py`: same.
- `tests/test_phase53f2_workspace_state_persistence_extraction.py`: same.

## Type annotation quirks

- `ScenarioRecord` is a string forward ref (`"ScenarioRecord"`)
  with lazy import inside function body.
- `uuid` imported at top-level of `scenarios_repository.py`.

## Stack dependency

This PR is part of a stack:
- 53G-4 (this PR, draft): save_scenario
- 53G-5 (next, draft): add_scenario
- 53G-6 (next, draft): update_scenario_overrides
- 53G-7 (last, draft): get_or_create_base_case_scenario

Each PR will need rebase/retarget onto updated main after the previous
PR is merged.

## Recommended next step

Continue to 53G-5 (extract `add_scenario`) as another stacked draft PR.
