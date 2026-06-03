# Phase 53G-7 — Base-Case Scenario Persistence Extraction

## Context

Phase 53G-7 extracts the FINAL high-risk scenario write function
(`get_or_create_base_case_scenario`) and its tightly-coupled helper
(`get_base_case_scenario`) from `app/persistence/repository.py` to
`app/persistence/scenarios_repository.py`.

This is the LAST extraction in the 53G-4..53G-7 stack.

This is **DRAFT ONLY** — must not be auto-merged. Requires explicit
user sign-off.

## What was extracted

| Function | Risk |
|---|---|
| `get_or_create_base_case_scenario` | **high** (last of the 4 high-risk scenario writes) |
| `get_base_case_scenario` | low (helper, tightly coupled to `get_or_create_base_case_scenario` and `resolve_active_scenario_runtime_snapshot`) |

### Why `get_base_case_scenario` was moved

`get_base_case_scenario` is referenced from `resolve_active_scenario_runtime_snapshot`
(which lives in `scenarios_repository.py` since 53G-2). Per the spec:
> If `record_workspace_runtime` or `runtime_guard_for_snapshot` appears necessary, STOP and report instead of moving.

These two are NOT moved (they don't appear in this PR's scope).
`get_base_case_scenario` is a base-case scenario helper and is safe to move
alongside `get_or_create_base_case_scenario` (it is the read counterpart).

### Functions NOT in this PR (stay in `repository.py`)

- `seed_scenarios_if_needed` (workshop seeding, NOT Group B)
- `get_scenario_provenance` (provenance metadata, NOT Group B)
- `record_workspace_runtime` (workspace runtime, NOT Group B)
- `runtime_guard_for_snapshot` (runtime guard, NOT Group B)
- `update_scenario_last_run_summary` (NOT Group B)

### Dataclasses remain in `repository.py`

`ProjectRecord`, `ScenarioRecord`, `WorkspaceStateRecord` (deferred until
after Group B per spec).

## Public compatibility

Both functions re-exported from `app.persistence.repository`:

- `from app.persistence.repository import get_or_create_base_case_scenario` ✓
- `from app.persistence.repository import get_base_case_scenario` ✓

## LOC changes

- `app/persistence/repository.py`: 552 → 453 lines (-99, -18%)
- `app/persistence/scenarios_repository.py`: 478 → 600 lines (+122)

## Hard gates

- ✓ 638/638 tests pass + 10 skipped (10 new 53G-7 + 17 53G-1 base_case re-pointed + 611 previous)
- ✓ 53G-1 base_case P0 pin re-pointed and still passes
- ✓ 53G-1 scenario/workspace coupling pin still passes
- ✓ 53G-4/53G-5/53G-6 pins still pass
- ✓ Phase 51F guardrails pass (21/21)
- ✓ Phase 52F G1-G6 pass (10/10)
- ✓ No SQL text changes (byte-for-byte identical)
- ✓ No replay_metadata/governance_state/last_run_summary shape changes
- ✓ No route/service changes
- ✓ rc1 untouched (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged)
- ✓ **No high-risk scenario writes remain in repository.py** (all 4 moved to scenarios_repository)
- ✓ Dataclasses untouched

## After this PR — completion of Group B

After 53G-7, **all 4 high-risk scenario writes are in scenarios_repository.py**:

- ✓ `save_scenario` (moved 53G-4)
- ✓ `add_scenario` (moved 53G-5)
- ✓ `update_scenario_overrides` (moved 53G-6)
- ✓ `get_or_create_base_case_scenario` (moved 53G-7)

`repository.py` is now a pure façade + unrelated helpers (seed/provenance/runtime).

## Test re-pointing

- `tests/test_phase53g1_base_case_p0_behavior_pin.py`: 17 tests, all re-pointed
  to read from `scenarios_repository.py`. Added 2 new tests.
- 10 existing test files updated to remove `get_or_create_base_case_scenario`
  from "still in repository" high-risk lists.

## Stack dependency

This PR is the LAST in the stack:
- 53G-4 (DRAFT, PR #441): save_scenario
- 53G-5 (DRAFT, PR #442): add_scenario
- 53G-6 (DRAFT, PR #443): update_scenario_overrides
- 53G-7 (this PR, DRAFT): get_or_create_base_case_scenario + get_base_case_scenario

Base: 53G-6 head (`899bf0d273ead6ba5203003b046279b65b911ca5`)

## Recommended next step

Per spec: **DO NOT create 53G-8 closeout until the four high-risk PRs are reviewed and merged.**
Per spec: **DO NOT start records.py cleanup.**
Per spec: **DO NOT start UI/pilot/security/deployment work.**
Per spec: **DO NOT start Agent B docs work.**

User should review PRs #441, #442, #443, #444 in order. Each will need rebase/retarget
onto updated main after the previous PR is merged.

## Rebase/retarget note

Since this is a stacked PR sequence where each PR is based on the previous PR's head,
the user will need to:
1. Merge 53G-4 (PR #441) into main
2. Rebase 53G-5 (PR #442) onto updated main (or just retarget to main; the diff is small)
3. Merge 53G-5
4. Repeat for 53G-6, 53G-7

Since the diffs are small and the PRs are well-isolated, the rebase should be clean.
