# Phase 53G-6 — update_scenario_overrides Persistence Extraction

## Context

Phase 53G-6 extracts the THIRD high-risk scenario write function
(`update_scenario_overrides`) from `app/persistence/repository.py` to
`app/persistence/scenarios_repository.py`.

This is **DRAFT ONLY** — must not be auto-merged. Requires explicit
user sign-off.

## What was extracted

| Function | Risk |
|---|---|
| `update_scenario_overrides` | **high** (1 of 2 remaining high-risk scenario writes) |

### Functions NOT in this PR (stay in `repository.py`)

- `get_or_create_base_case_scenario` (53G-7, last)

### Dataclasses remain in `repository.py`

`ProjectRecord`, `ScenarioRecord`, `WorkspaceStateRecord` (deferred until
after Group B per spec).

## Public compatibility

`update_scenario_overrides` re-exported from `app.persistence.repository`:

- `from app.persistence.repository import update_scenario_overrides` ✓
- `from app.persistence import update_scenario_overrides` ✓

## LOC changes

- `app/persistence/repository.py`: 600 → 552 lines (-48, -8%)
- `app/persistence/scenarios_repository.py`: 432 → 478 lines (+46)

## Hard gates

- ✓ 632/632 tests pass (7 new 53G-6 + 16 53G-1 update_overrides re-pointed + 609 previous)
- ✓ 53G-1 update_overrides P0 pin re-pointed and still passes
- ✓ 53G-1 scenario/workspace coupling pin: 3 update_overrides tests re-pointed
- ✓ 53G-4/53G-5 pins still pass
- ✓ Phase 51F guardrails pass (21/21)
- ✓ Phase 52F G1-G6 pass (10/10)
- ✓ No SQL text changes (byte-for-byte identical)
- ✓ No replay_metadata/governance_state/last_run_summary shape changes
- ✓ No route/service changes
- ✓ rc1 untouched (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged)
- ✓ Other high-risk scenario writes untouched
- ✓ Dataclasses untouched

## Test re-pointing

- `tests/test_phase53g1_update_overrides_p0_behavior_pin.py`: 16 tests, all re-pointed
  to read from `scenarios_repository.py`. Added 2 new tests.
- `tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py`: 3 tests
  re-pointed (`TestUpdateScenarioOverridesCoupling`).
- 9 existing test files updated to remove `update_scenario_overrides`
  from "still in repository" high-risk lists.

## Stack dependency

This PR is part of a stack:
- 53G-4 (DRAFT, PR #441): save_scenario
- 53G-5 (DRAFT, PR #442): add_scenario
- 53G-6 (this PR, DRAFT): update_scenario_overrides
- 53G-7 (next, DRAFT): get_or_create_base_case_scenario

Base: 53G-5 head (`c0ea96e5007e649dd59cb051e3e5a5897b027803`)

## Recommended next step

Continue to 53G-7 (extract `get_or_create_base_case_scenario` and
base-case helpers) as the final stacked draft PR.
