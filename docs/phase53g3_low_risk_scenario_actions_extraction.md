# Phase 53G-3 — Low-Risk Scenario Actions Extraction

## Context

Phase 53G-3 extracts 5 low-risk scenario action functions from
`app/persistence/repository.py` to `app/persistence/scenarios_repository.py`,
preserving public compatibility through re-exports.

The 4 high-risk scenario writes (`save_scenario`, `add_scenario`,
`update_scenario_overrides`, `get_or_create_base_case_scenario`)
remain in `repository.py` until their own extraction PRs
(53G-4, 53G-5, 53G-6, 53G-7).

## What was extracted

5 functions moved byte-for-byte from `app/persistence/repository.py`
to `app/persistence/scenarios_repository.py`:

| Function | Risk |
|---|---|
| `rename_scenario` | low (1-column UPDATE) |
| `archive_scenario` | low (1-column UPDATE) |
| `select_scenario` | medium (calls save_workspace_state) |
| `duplicate_scenario` | medium (calls save_scenario) |
| `promote_scenario_to_base_case` | medium (2 UPDATEs) |

### Functions NOT in this module (stay in `repository.py`)

| Function | Reason |
|---|---|
| `save_scenario` | high-risk write, 53G-4 |
| `add_scenario` | high-risk write, 53G-5 |
| `update_scenario_overrides` | high-risk write, 53G-6 |
| `get_or_create_base_case_scenario` | high-risk write, 53G-7 |
| `seed_scenarios_if_needed` | NOT Group B |
| `get_scenario_provenance` | NOT Group B |
| `get_base_case_scenario` | NOT Group B |
| `record_workspace_runtime` | NOT Group B |
| `runtime_guard_for_snapshot` | NOT Group B |
| `update_scenario_last_run_summary` | NOT Group B |

## Public compatibility

All 5 functions re-exported from `app.persistence.repository`:

- `from app.persistence.repository import rename_scenario` ✓
- `from app.persistence.repository import archive_scenario` ✓
- `from app.persistence.repository import select_scenario` ✓
- `from app.persistence.repository import duplicate_scenario` ✓
- `from app.persistence.repository import promote_scenario_to_base_case` ✓

`app/persistence/__init__.py` updated: rename/archive/duplicate re-exported
from `scenarios_repository`. select_scenario and promote_scenario_to_base_case
are not in `__init__.py` (they're internal use only).

## LOC changes

- `app/persistence/repository.py`: 826 → 743 lines (-83, -10%)
- `app/persistence/scenarios_repository.py`: 200 → 280 lines

## Hard gates

- ✓ 621/621 tests pass (34 new 53G-3 + 31 53G-2 + 81 53G-1 + 475 previous)
- ✓ 53G-1 P0 pins still pass
- ✓ 53G-2 read extraction still passes
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

## Type annotation quirks

- `ScenarioRecord` is a string forward ref (`"ScenarioRecord"`)
  with lazy import inside function bodies.
- `select_scenario` lazy-imports `get_workspace_state` and `save_workspace_state`
  (workspace module, not scenario module).
- `duplicate_scenario` lazy-imports `save_scenario` (still in repository.py
  until 53G-4).
- `promote_scenario_to_base_case` lazy-imports `get_scenario` (already in
  scenarios_repository).

## Stop signal

Per the spec, **STOP after 53G-3 and return combined report.**
**Do not start 53G-4 (save_scenario), 53G-5 (add_scenario),
53G-6 (update_scenario_overrides), 53G-7 (get_or_create_base_case_scenario)**
automatically. Those require user sign-off.

## Recommended next step

User review of PR #440 (53G-3) and decision on:
- 53G-4 through 53G-7 are **REVIEW REQUIRED** (per spec). They should
  be planned, not auto-executed.
- After 53G-3 merge, recommend a **Claude architecture review** of the
  post-Group-B state before tackling the high-risk writes.
- Records/dataclass relocation should be deferred until after Group B
  is complete.

## Current Group B state (post-53G-3)

- `repository.py`: 743 lines (was 2,042 pre-Phase 53; total -64%)
- `scenarios_repository.py`: 280 lines (4 reads + 5 low-risk actions)
- 4 high-risk scenario writes still in `repository.py`:
  - `save_scenario` (53G-4)
  - `add_scenario` (53G-5)
  - `update_scenario_overrides` (53G-6)
  - `get_or_create_base_case_scenario` (53G-7)
