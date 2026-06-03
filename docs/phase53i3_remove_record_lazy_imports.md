# Phase 53I-3 — Remove Record Lazy Imports

## Context

Phase 53I-3 is the import cleanup phase. After 53I-2 created
`app/persistence/records.py` and re-exported the records from
`app.persistence.repository`, the domain modules (scenarios,
projects, workspace) still had **lazy imports** of the records from
`repository.py`. This phase replaces those with **direct imports**
from `records.py`.

This is a mechanical import cleanup. **No SQL changed. No function
logic changed. No metadata shape changed.** Only import paths
changed in 3 domain modules.

## Changes

### Before (53I-2 state)
```python
# In scenarios_repository.py:
def get_scenario(scenario_id, user_id):
    from app.persistence.repository import ScenarioRecord  # lazy
    ...
```

### After (53I-3 state)
```python
# In scenarios_repository.py:
from app.persistence.records import ScenarioRecord  # direct
# (still inside function body for lazy pattern preservation)

def get_scenario(scenario_id, user_id):
    ...
```

## Modules updated

| Module | Records with cleaned imports |
|---|---|
| `app/persistence/scenarios_repository.py` | 8× `ScenarioRecord` (was from repository, now from records) |
| `app/persistence/projects_repository.py` | 7× `ProjectRecord` |
| `app/persistence/workspace_repository.py` | 3× `WorkspaceStateRecord` (+ 1× `ScenarioRecord`) |

**Total: 19 lazy imports cleaned across 3 modules.**

After 53I-3, **0 lazy imports of record dataclasses from
`app.persistence.repository` remain in any domain module.**

## Public compatibility

- `from app.persistence.repository import <Record>` still works
  (re-export from records)
- `from app.persistence.records import <Record>` works (direct)
- Object identity: `app.persistence.records.X is app.persistence.repository.X` ✓
- 4 of 5 records also re-exported from `app.persistence` (init)
  (WorkspaceStateRecord was never re-exported, pre-existing behavior)

## Guardrails added

1. `tests/test_phase53i3_no_record_lazy_imports.py::TestNoRecordLazyImportsFromRepository`:
   - Verifies `app/persistence/*_repository.py` does NOT import any
     record dataclass from `app.persistence.repository`
   - If this ever fails, someone re-introduced a stale lazy import
2. `tests/test_phase53i3_no_record_lazy_imports.py::TestObjectIdentityPreserved`:
   - Verifies record classes are the same object across paths
3. `tests/test_phase53i3_no_record_lazy_imports.py::TestSqlUnchanged`:
   - Pins that SQL text is unchanged (saves_scenario, update_scenario_overrides)
4. `tests/test_phase53i3_no_record_lazy_imports.py::TestNoNewCircularImport`:
   - All persistence modules import cleanly; records.py is independent

## Hard gates

- ✓ 20 new 53I-3 structural tests pass
- ✓ 36 53I-1 pin tests pass (re-pointed 1 test to assert 0 lazy imports)
- ✓ 21 53I-2 structural tests pass
- ✓ 91 53G P0 pins pass
- ✓ Scenario/workspace coupling pin passes (23 tests)
- ✓ Phase 51F (21/21) + 52F G1-G6 (10/10) pass
- ✓ No SQL text changed (verified by SQL pin test)
- ✓ No metadata shape changed
- ✓ No route/service files touched
- ✓ No new circular import
- ✓ rc1 (b425a07) untouched in history

## LOC summary

| Module | Before 53I-3 | After 53I-3 | Delta |
|---|---:|---:|---:|
| `scenarios_repository.py` | 600 | 600 | 0 (imports changed, line count same) |
| `projects_repository.py` | 480 | 480 | 0 |
| `workspace_repository.py` | 250 | 250 | 0 |
| **Total** | | | 0 |

The 0-delta is because the import lines have the same length — they
just point to a different module.

## Recommended next step

`53I-4 — Records relocation closeout + guardrails`

This is the final phase of the 53I stack. It adds a permanent
guardrail that prevents future PRs from re-introducing record
dataclass definitions in `repository.py` (a structural regression),
and produces the final closeout documentation.

## Tests run

- `tests/test_phase53i1_records_field_shape_import_pins.py`: 36/36 ✓
- `tests/test_phase53i2_records_module_relocation.py`: 21/21 ✓
- `tests/test_phase53i3_no_record_lazy_imports.py`: 20/20 ✓ (new)
- 53G P0 pins: 91/91 ✓
- Phase 51F: 21/21 ✓
- Phase 52F G1-G6: 10/10 ✓
- **Total: 199/199 ✓**
