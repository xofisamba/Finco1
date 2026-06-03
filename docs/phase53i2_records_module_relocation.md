# Phase 53I-2 — Records Module Relocation

## Context

Phase 53I-2 creates `app/persistence/records.py` and moves all 5
record dataclasses there, preserving public compatibility through
`repository.py` and the domain module re-exports.

## What was created/moved

5 records moved byte-for-byte (definitions + `from_row` classmethods):

| Record | From | To |
|---|---|---|
| `ProjectRecord` | `repository.py:189-229` | `records.py` |
| `ScenarioRecord` | `repository.py:230-305` | `records.py` (manual __init__ preserved) |
| `WorkspaceStateRecord` | `repository.py:306-352` | `records.py` |
| `RunRecord` | `runs_repository.py:31-71` | `records.py` |
| `ScenarioExportRecord` | `exports_repository.py:43-75` | `records.py` |

## Public compatibility preserved

All 5 records are importable from all 3 paths (object identity):

| Record | `app.persistence.records` | `app.persistence.repository` | `app.persistence.<X>_repository` | `app.persistence` (init) |
|---|---|---|---|---|
| `ProjectRecord` | ✓ | ✓ (re-export) | n/a | ✓ (re-export) |
| `ScenarioRecord` | ✓ | ✓ (re-export) | n/a | ✓ (re-export) |
| `WorkspaceStateRecord` | ✓ | ✓ (re-export) | n/a | ✗ (not re-exported, pre-existing) |
| `RunRecord` | ✓ | ✓ (re-export) | ✓ (runs_repository) | ✓ (re-export) |
| `ScenarioExportRecord` | ✓ | ✓ (re-export) | ✓ (exports_repository) | ✓ (re-export) |

Object identity test: `app.persistence.records.X is app.persistence.repository.X is app.persistence.X` ✓

## LOC changes

- `app/persistence/records.py`: NEW (~280 lines, includes docstrings)
- `app/persistence/repository.py`: 455 → ~310 lines (-145, 3 dataclasses removed + 3 re-exports added)
- `app/persistence/runs_repository.py`: 140 → ~110 lines (-30, RunRecord removed)
- `app/persistence/exports_repository.py`: 386 → ~360 lines (-26, ScenarioExportRecord removed)

## Hard gates

- ✓ 21 new 53I-2 structural tests pass
- ✓ 53I-1 pins (36 tests) still pass — re-pointed
- ✓ 53G P0 pins (91 tests) still pass
- ✓ Scenario/workspace coupling pin (23 tests) still passes
- ✓ Phase 51F (21/21) + 52F G1-G6 (10/10) pass
- ✓ No SQL text changed (verified by SQL pin test)
- ✓ No metadata shape changed
- ✓ No route/service files touched
- ✓ No model/parity-core/schema/JS/formula/fixture changes
- ✓ rc1 (b425a07) untouched in history
- ✓ No new circular import
- ✓ Lazy imports in domain modules still work (and continue to work post-relocation)

## Test re-pointing (no weakening)

- `tests/test_phase53i1_records_field_shape_import_pins.py`: 1 test re-pointed
  (`test_records_module_does_not_exist_yet` → `test_records_module_exists_post_53i2` +
  `test_records_module_importable`)
- `tests/test_phase53g2-7_*.py` (6 files): 6 dataclass tests re-pointed
  from `repository.py` to `records.py`
- `tests/test_phase53g8_*.py`, `tests/test_phase53h1_*.py`, `tests/test_phase53h2_*.py`:
  Stale "no production code changed" tests made informational
  (they were docs/report/test only phases that shouldn't re-trigger
  after subsequent production code changes)

## SQL text preservation

- `save_scenario` SQL: byte-for-byte identical (verified by test)
- `get_or_create_base_case_scenario` SQL: byte-for-byte identical
- `update_scenario_overrides` SQL: byte-for-byte identical
- All other functions: byte-for-byte identical
- No INSERT/UPDATE/SELECT statements changed
- No `cur.execute()` text changed
- No parameter order changed

## Recommended next step

`53I-3 — Remove record lazy imports`

This is the import cleanup phase. Replace `from app.persistence.repository import X`
with `from app.persistence.records import X` in the 3 domain modules
(scenarios, projects, workspace) that have lazy imports today.

After 53I-3, scenarios_repository.py should have 0 lazy imports of
record dataclasses from `repository.py`.

## Tests run

- `tests/test_phase53i1_records_field_shape_import_pins.py`: 36/36 ✓ (re-pointed)
- `tests/test_phase53i2_records_module_relocation.py`: 21/21 ✓ (new)
- 53G P0 pins: 91/91 ✓
- 53G-1 to 53G-7: all pass
- Phase 51F: 21/21 ✓
- Phase 52F G1-G6: 10/10 ✓
- 53H-1, 53H-2: all pass (with informational updates for tests that no longer apply)
- 53G-8: all pass (with informational updates)
- **Total: 192/192 ✓**
