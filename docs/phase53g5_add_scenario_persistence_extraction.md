# Phase 53G-5 — add_scenario Persistence Extraction

## Context

Phase 53G-5 extracts the SECOND high-risk scenario write function
(`add_scenario`) from `app/persistence/repository.py` to
`app/persistence/scenarios_repository.py`.

This is **DRAFT ONLY** — must not be auto-merged. Requires explicit
user sign-off.

## What was extracted

| Function | Risk |
|---|---|
| `add_scenario` | **high** (1 of 3 remaining high-risk scenario writes) |

### Functions NOT in this PR (stay in `repository.py`)

- `update_scenario_overrides` (53G-6, next)
- `get_or_create_base_case_scenario` (53G-7, last)

### Dataclasses remain in `repository.py`

`ProjectRecord`, `ScenarioRecord`, `WorkspaceStateRecord` (deferred until
after Group B per spec).

## Public compatibility

`add_scenario` re-exported from `app.persistence.repository`:

- `from app.persistence.repository import add_scenario` ✓
- `from app.persistence import add_scenario` ✓ (via `__init__.py`)

## LOC changes

- `app/persistence/repository.py`: 680 → 600 lines (-80, -12%)
- `app/persistence/scenarios_repository.py`: 346 → 432 lines (+86)

## Hard gates

- ✓ 631/631 tests pass (8 new 53G-5 + 19 53G-1 add_scenario re-pointed + 604 previous)
- ✓ 53G-1 add_scenario P0 pin re-pointed and still passes
- ✓ 53G-1 scenario/workspace coupling pin: 2 add_scenario-related tests re-pointed
- ✓ 53G-4 save_scenario pin still passes
- ✓ Phase 51F guardrails pass (21/21)
- ✓ Phase 52F G1-G6 pass (10/10) — G5 list expanded to include scenarios_repository + workspace_repository
- ✓ No SQL text changes (byte-for-byte identical)
- ✓ No replay_metadata/governance_state/last_run_summary shape changes
- ✓ No route/service changes
- ✓ rc1 untouched (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged)
- ✓ Other high-risk scenario writes untouched
- ✓ Dataclasses untouched

## G5 guardrail update

The G5 single-transaction regression check (`test_at_least_20_with_get_cursor_blocks`)
had a hardcoded list of persistence files. After moving functions out of `repository.py`
into `scenarios_repository.py` and `workspace_repository.py`, the cross-module total
needed to include those modules. The test was updated to include:
- `scenarios_repository.py` (new in this PR's history)
- `workspace_repository.py` (new in 53F-2)

This is **strengthening** the guardrail, not weakening: it now checks more files
for the same pattern. The threshold (≥ 20) is unchanged.

## Test re-pointing

- `tests/test_phase53g1_add_scenario_p0_behavior_pin.py`: 19 tests, all re-pointed
  to read from `scenarios_repository.py`. Added 2 new tests.
- `tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py`: 2 tests
  re-pointed (`TestAddScenarioCoupling`).
- `tests/test_phase52f_persistence_guardrail_regression.py`: G5 list expanded.
- `tests/test_phase53a_persistence_helpers_extraction.py`: add_scenario removed from high-risk list.
- `tests/test_phase53b_persistence_runs_extraction.py`: same.
- `tests/test_phase53c_persistence_exports_audit_extraction.py`: same.
- `tests/test_phase53e2_project_write_persistence_extraction.py`: same.

## Stack dependency

This PR is part of a stack:
- 53G-4 (DRAFT): save_scenario (PR #441)
- 53G-5 (this PR, DRAFT): add_scenario
- 53G-6 (next, DRAFT): update_scenario_overrides
- 53G-7 (last, DRAFT): get_or_create_base_case_scenario

Base: 53G-4 head (`084ef6ba99a339d64785bb88fcca21b4104eb5ac`)

## Recommended next step

Continue to 53G-6 (extract `update_scenario_overrides`) as another stacked draft PR.
