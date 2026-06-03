# Phase 53F-2 — Workspace State Persistence Functions Extraction

## Context

Phase 53F-2 is the Group C extraction phase for `workspace_state` persistence
functions. It follows Phase 53F-1, which pinned the current behavior of
`save_workspace_state` (one of the 7 high-risk writes).

The extraction moves 4 functions from `app/persistence/repository.py`
to a new module `app/persistence/workspace_repository.py`, while
preserving public compatibility through a re-export block in
`repository.py`.

## What was extracted (behavior-preserving)

4 functions moved byte-for-byte from `app/persistence/repository.py`
to `app/persistence/workspace_repository.py`:

| Function | Risk |
|---|---|
| `save_workspace_state` | **high** (1 of 7 high-risk writes, P0 pinned in 53F-1) |
| `get_workspace_state` | low (read) |
| `discard_workspace_draft` | medium (calls save_workspace_state) |
| `bind_workspace_to_scenario` | medium (calls save_workspace_state) |

### Functions NOT in Group C (remain in `repository.py`)

| Function | Reason |
|---|---|
| `record_workspace_runtime` | Runtime helper, not a workspace_state CRUD |
| `runtime_guard_for_snapshot` | Runtime guard, not a workspace_state CRUD |

## Public compatibility

All 4 functions re-exported from `app.persistence.repository`:

- `from app.persistence.repository import save_workspace_state` ✓
- `from app.persistence.repository import get_workspace_state` ✓
- `from app.persistence.repository import discard_workspace_draft` ✓
- `from app.persistence.repository import bind_workspace_to_scenario` ✓
- `from app.persistence.repository import WorkspaceStateRecord` ✓

`WorkspaceStateRecord` dataclass remains in `app/persistence/repository.py`
(used by reads and other groups).

## LOC changes

- `app/persistence/repository.py`: 1100 → ~920 lines (-180)
- `app/persistence/workspace_repository.py`: NEW (~250 lines)

## Hard gates

- ✓ 475/475 tests pass (40 new 53F-2 + 39 53F-1 re-pointed + 396 previous)
- ✓ 53F-1 P0 pin re-pointed and still passes (39 tests)
- ✓ Phase 51F guardrails pass (21/21)
- ✓ Phase 52F G1-G6 pass (10/10)
- ✓ No SQL text changes (byte-for-byte identical)
- ✓ No replay_metadata/governance_state/last_run_summary shape changes
- ✓ No route/service changes
- ✓ rc1 untouched (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged in history)
- ✓ Other high-risk writes untouched:
  - `save_scenario`, `add_scenario`, `update_scenario_overrides`,
    `get_or_create_base_case_scenario` (Group B, future)
  - `save_project` (Group A-2, moved in 53E-2)
  - `record_export` (Group E, moved in 53C)

## Test re-pointing

- `tests/test_phase53f1_save_workspace_state_p0_behavior_pin.py`: 1 test
  re-pointed (`TestNoCallerChanges.test_save_workspace_state_callers_unchanged`
  → `TestNoCallerChanges.test_save_workspace_state_defined_in_workspace_repository`
  + `TestNoCallerChanges.test_save_workspace_state_not_defined_in_repository`).
  All other tests in this file re-pointed to read SQL fragments and body
  text from `workspace_repository.py` instead of `repository.py`.

- `tests/test_phase53a_persistence_helpers_extraction.py`: removed
  `save_workspace_state` from the `test_high_risk_write_still_in_repository`
  parametrize list (now in workspace_repository).

- `tests/test_phase53b_persistence_runs_extraction.py`: same.

- `tests/test_phase53c_persistence_exports_audit_extraction.py`: same + new
  `test_save_workspace_state_moved_to_workspace_repository`.

- `tests/test_phase53e2_project_write_persistence_extraction.py`: same.

## Type annotation quirks

- `WorkspaceStateRecord` is a string forward ref (`"WorkspaceStateRecord"`)
  with lazy import inside function bodies. The dataclass itself is in
  `app/persistence/repository.py` and is referenced via `TYPE_CHECKING` +
  runtime lazy import to avoid circular import at module load time.

## Recommended next step (REVIEW REQUIRED)

Per Phase 52E plan, Group C is "review required" because `save_workspace_state`
is a high-risk write. PR #437 (53F-2) is opened as DRAFT and is **NOT
auto-merged**. The user must explicitly approve and merge.

After merge, the next group is Group B (scenarios), which requires 5
P0 pins + user sign-off.
