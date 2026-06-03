# Phase 53I-1 — Records Field Shape and Import Compatibility Pins

## Context

Phase 53I-1 pins the current record dataclass shapes and import paths
BEFORE the records.py relocation (53I-2). These pins are the
behavior-preservation contract: the relocation must not change any
field, type, default, slots, or import path that this phase pins.

This is a **test/docs/report only** phase. NO production code is
changed. NO `records.py` is created yet.

## Current main SHA

`258f870416cf4348a9d8658a2d6fc7a86abcad7e` (post-53H-2)

## Record inventory

5 records total:

| Record | Defined in | LOC | Field count | Dataclass | Slots |
|---|---|---:|---:|---|---|
| `ProjectRecord` | `app/persistence/repository.py:191` | ~40 | 16 | ✓ | ✓ |
| `ScenarioRecord` | `app/persistence/repository.py:231` | ~80 | 19 | ✗ (manual) | ✓ |
| `WorkspaceStateRecord` | `app/persistence/repository.py:308` | ~30 | 19 | ✓ | ✓ |
| `RunRecord` | `app/persistence/runs_repository.py:31` | ~30 | 10 | ✓ | ✓ |
| `ScenarioExportRecord` | `app/persistence/exports_repository.py:43` | ~30 | 12 | ✓ | ✓ |

## Field shapes (pinned)

### `ProjectRecord` (16 fields)
`project_id, user_id, project_code, project_name, project_type, project_origin, source_project_template, template_source, baseline_snapshot, archived, is_readonly, governance_state, last_run_summary, replay_metadata, created_at, updated_at`

### `ScenarioRecord` (19 fields)
`scenario_id, project_id, user_id, scenario_name, project_code, source_project_template, copied_from_scenario_id, archived, is_base_case, parent_scenario_id, base_input_set, overrides, schema_version, snapshot, governance_state, last_run_summary, replay_metadata, created_at, updated_at`

### `WorkspaceStateRecord` (19 fields)
`workspace_id, project_id, user_id, project_code, active_scenario_id, active_scenario_name, draft_snapshot, saved_snapshot, last_runtime_snapshot, last_runtime_summary, last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id, dirty, governance_state, replay_metadata, created_at, updated_at, last_runtime_at`

### `RunRecord` (10 fields)
`run_id, user_id, project_type, scenario, created_at, inputs, kpis, excel_path, notes, replay_metadata`

### `ScenarioExportRecord` (12 fields)
`export_id, scenario_id, project_id, user_id, export_type, artifact_name, artifact_path, project_code, governance_state, runtime_snapshot_id, replay_metadata, created_at`

## Import paths (pinned)

| Record | From app.persistence.repository | From app.persistence | From domain module |
|---|---|---|---|
| `ProjectRecord` | ✓ | ✓ (re-export) | n/a (still in repository) |
| `ScenarioRecord` | ✓ | ✓ (re-export) | n/a (still in repository) |
| `WorkspaceStateRecord` | ✓ | ✗ (not re-exported) | n/a (still in repository) |
| `RunRecord` | ✓ (re-export) | ✓ (re-export) | ✓ (runs_repository) |
| `ScenarioExportRecord` | ✓ (re-export) | ✓ (re-export) | ✓ (exports_repository) |

## Object identity pins (must be preserved)

- `from app.persistence.repository import ProjectRecord` must be the
  same class object as `from app.persistence import ProjectRecord` (A is B)
- Same for `ScenarioRecord` and `WorkspaceStateRecord`
- Same for `RunRecord` and `ScenarioExportRecord`

## Lazy imports pinned (current state)

In `app/persistence/scenarios_repository.py` (current state):
- 5+ lazy imports of `ScenarioRecord` and `WorkspaceStateRecord`
  from `app.persistence.repository`
- These exist because the records live in `repository.py`, creating
  a circular import risk
- After 53I-3, these should drop to 0

In `app/persistence/projects_repository.py`:
- 5 lazy imports of `ProjectRecord` from `app.persistence.repository`

In `app/persistence/workspace_repository.py`:
- 3 lazy imports of `WorkspaceStateRecord` from `app.persistence.repository`

## from_row methods (pinned)

All 5 records have a `from_row` classmethod:
- `ProjectRecord.from_row(row) -> "ProjectRecord"`
- `ScenarioRecord.from_row(row) -> "ScenarioRecord"`
- `WorkspaceStateRecord.from_row(row) -> "WorkspaceStateRecord"`
- `RunRecord.from_row(row) -> "RunRecord"`
- `ScenarioExportRecord.from_row(row) -> "ScenarioExportRecord"`

## Slots and dataclass options (pinned)

All 5 records use `__slots__`. The behavior must be preserved through
relocation (4 of 5 are `@dataclass`; 1 `ScenarioRecord` is manual with
`__init__` and `__slots__`).

## Compatibility requirements for 53I-2

After records.py is created and the 3 records are moved:

1. All 5 records must be importable from `app.persistence.records` (NEW path)
2. `from app.persistence.repository import <Record>` must still work (compatibility façade)
3. `from app.persistence import <Record>` must still work for the 4 re-exported records
4. Object identity preserved: `app.persistence.records.ProjectRecord is app.persistence.repository.ProjectRecord`
5. Field shapes preserved exactly
6. `from_row` methods preserved exactly
7. `__slots__` preserved
8. Lazy imports in `scenarios_repository.py` for records → drop to 0

## Tests run
- `tests/test_phase53i1_records_field_shape_import_pins.py`: 35/35 ✓
- All Phase 51F (21/21) + 52F G1-G6 (10/10) + 53G P0 (91/91) pass

## Hard gates
- ✓ test/docs/report only (no production code changed)
- ✓ No `records.py` created yet (53I-2's job)
- ✓ No SQL changed
- ✓ No metadata shape changed
- ✓ No route/service changes
- ✓ No model/parity-core/schema/JS/formula/fixture changes
- ✓ rc1 (b425a07) untouched in history
- ✓ 53G P0 pins still pass
- ✓ Scenario/workspace coupling pin still passes
- ✓ Phase 51F (21/21) + 52F G1-G6 (10/10) + 53G P0 (91/91) pass

## Recommended next step

`53I-2 — Create records.py and move record dataclasses`

This is the mechanical move. All 5 records move to `app/persistence/records.py`,
`repository.py` re-exports them, object identity is preserved, all 53I-1
pins continue to pass. Auto-merge allowed if all hard gates pass.
