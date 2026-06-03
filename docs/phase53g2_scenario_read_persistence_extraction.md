# Phase 53G-2 — Scenario Read Persistence Functions Extraction

## Context

Phase 53G-2 is the read-only scenario extraction phase. It follows
Phase 53G-1, which pinned the current behavior of the 4 high-risk
scenario writes and the scenario/workspace coupling.

The extraction moves 4 read functions from `app/persistence/repository.py`
to a new module `app/persistence/scenarios_repository.py`, while
preserving public compatibility through re-exports.

## What was extracted (behavior-preserving)

4 functions moved byte-for-byte from `app/persistence/repository.py`
to `app/persistence/scenarios_repository.py`:

| Function | Risk |
|---|---|
| `get_scenario` | low (read) |
| `list_scenarios` | low (read) |
| `resolve_scenario_snapshot` | low (pure function) |
| `resolve_active_scenario_runtime_snapshot` | low (read with warning) |

### Functions NOT in this module (stay in `repository.py`)

| Function | Reason |
|---|---|
| `save_scenario` | high-risk write, 53G-4 |
| `add_scenario` | high-risk write, 53G-5 |
| `update_scenario_overrides` | high-risk write, 53G-6 |
| `get_or_create_base_case_scenario` | high-risk write, 53G-7 |
| `promote_scenario_to_base_case` | low-risk action, 53G-3 |
| `duplicate_scenario` | low-risk action, 53G-3 |
| `rename_scenario` | low-risk action, 53G-3 |
| `archive_scenario` | low-risk action, 53G-3 |
| `select_scenario` | low-risk action, 53G-3 |
| `seed_scenarios_if_needed` | NOT Group B (workshop seeding) |
| `get_scenario_provenance` | NOT Group B (provenance metadata) |
| `get_base_case_scenario` | NOT Group B (used by resolve_active...) |
| `record_workspace_runtime` | NOT Group B (workspace runtime) |
| `runtime_guard_for_snapshot` | NOT Group B (runtime guard) |

## Public compatibility

All 4 functions re-exported from `app.persistence.repository`:

- `from app.persistence.repository import get_scenario` ✓
- `from app.persistence.repository import list_scenarios` ✓
- `from app.persistence.repository import resolve_scenario_snapshot` ✓
- `from app.persistence.repository import resolve_active_scenario_runtime_snapshot` ✓

`ScenarioRecord` dataclass remains in `app/persistence/repository.py`
(deferred until after Group B per the spec).

`app/persistence/__init__.py` updated to re-export from `scenarios_repository`.

## LOC changes

- `app/persistence/repository.py`: 922 → 826 lines (-96, -10%)
- `app/persistence/scenarios_repository.py`: NEW, ~200 lines

## Hard gates

- ✓ 587/587 tests pass (31 new 53G-2 + 81 53G-1 re-pointed + 475 previous)
- ✓ 53G-1 P0 pin re-pointed and still passes (81 tests, 1 re-pointed)
- ✓ Phase 51F guardrails pass (21/21)
- ✓ Phase 52F G1-G6 pass (10/10)
- ✓ No SQL text changes (byte-for-byte identical)
- ✓ No replay_metadata/governance_state/last_run_summary shape changes
- ✓ No route/service changes
- ✓ rc1 untouched (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged)
- ✓ Other high-risk scenario writes untouched:
  - `save_scenario`, `add_scenario`, `update_scenario_overrides`,
    `get_or_create_base_case_scenario` (Group B, 53G-4..53G-7)
- ✓ Dataclasses untouched:
  - `ProjectRecord`, `ScenarioRecord`, `WorkspaceStateRecord` (deferred)
- ✓ No new lazy import cycle (TYPE_CHECKING + lazy import used)

## Test re-pointing

- `tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py`: 1 test
  re-pointed (`TestResolveScenarioSnapshotCoupling.test_resolve_scenario_snapshot_in_repository`
  → `test_resolve_scenario_snapshot_in_scenarios_repository`).

## Type annotation quirks

- `ScenarioRecord` is a string forward ref (`"ScenarioRecord"`)
  with lazy import inside function bodies. The dataclass itself is in
  `app/persistence/repository.py` and is referenced via `TYPE_CHECKING` +
  runtime lazy import to avoid circular import at module load time.

## Recommended next step

`Phase 53G-3 — Extract low-risk scenario actions` (auto-merge allowed).

Move the following functions to `app/persistence/scenarios_repository.py`:
- `rename_scenario`
- `archive_scenario`
- `select_scenario`
- `duplicate_scenario`
- `promote_scenario_to_base_case` (only if tests show it is low-risk)

`get_or_create_base_case_scenario` and `update_scenario_overrides` are
high-risk and stay in `repository.py` until 53G-6/53G-7.
