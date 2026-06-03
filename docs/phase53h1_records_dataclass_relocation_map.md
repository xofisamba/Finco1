# Phase 53H-1 — Records/Dataclass Relocation Map

## Context

Phase 53H-1 is a **docs/report/test only** mapping plan for the
remaining 3 dataclasses in `app/persistence/repository.py`. It does
NOT move any code. It maps the relocation options and recommends
the next phase.

This is a planning deliverable to inform the user (or Claude review)
about the cost/benefit of each option before any actual relocation.

## Current main SHA

`fdfb7c92097d239d65f58f1e89ac298104965169` (post-53G-8 closeout)

## Current dataclass inventory

| Dataclass | Defined in | Lines | Used by (in app/persistence) | Used by (in app/services) | Re-exported from app.persistence? |
|---|---|---:|---|---|---|
| `ProjectRecord` | `repository.py:191` | ~40 | `projects_repository.py` (5x lazy imports) | `project_save_as_service.py`, `projects_create_service.py`, `save_run_service.py` | ✓ |
| `ScenarioRecord` | `repository.py:231` | ~80 | `scenarios_repository.py` (5x lazy imports) | `scenario_duplicate_service.py`, `scenario_state_service.py` | ✓ |
| `WorkspaceStateRecord` | `repository.py:308` | ~30 | `workspace_repository.py` (3x lazy imports) | (none found) | (no — only `WorkspaceStateRecord` from re-export, not direct) |
| `RunRecord` | `runs_repository.py:31` | ~30 | (none — used by callers) | `save_run_service.py` | ✓ |
| `ScenarioExportRecord` | `exports_repository.py:43` | ~30 | (none — used by callers) | (none found) | ✓ |

## Exact file location for each record

| Dataclass | Absolute path |
|---|---|
| `ProjectRecord` | `/workspace/Finco1/app/persistence/repository.py:191` |
| `ScenarioRecord` | `/workspace/Finco1/app/persistence/repository.py:231` |
| `WorkspaceStateRecord` | `/workspace/Finco1/app/persistence/repository.py:308` |
| `RunRecord` | `/workspace/Finco1/app/persistence/runs_repository.py:31` |
| `ScenarioExportRecord` | `/workspace/Finco1/app/persistence/exports_repository.py:43` |

3 of 5 records are in `repository.py` (deferred per Phase 53 spec).
2 of 5 are already in their owner module (RunRecord → runs_repository,
ScenarioExportRecord → exports_repository). These 2 don't need moving.

## Modules that import each record

### `ProjectRecord` (5 in-app lazy imports + 1 in __init__)

In `app/persistence/projects_repository.py`:
- 5 lazy imports: `from app.persistence.repository import ProjectRecord` (inside function bodies)

In `app/persistence/__init__.py`:
- Direct re-export: `from app.persistence.repository import (ProjectRecord, ...)`

In `app/services/`:
- `project_save_as_service.py`
- `projects_create_service.py`
- `save_run_service.py`

### `ScenarioRecord` (5 in-app lazy imports + 1 in __init__)

In `app/persistence/scenarios_repository.py`:
- 5 lazy imports: `from app.persistence.repository import ScenarioRecord`

In `app/persistence/__init__.py`:
- Direct re-export: `from app.persistence.repository import (ScenarioRecord, ...)`

In `app/services/`:
- `scenario_duplicate_service.py`
- `scenario_state_service.py`

### `WorkspaceStateRecord` (3 in-app lazy imports)

In `app/persistence/workspace_repository.py`:
- 3 lazy imports: `from app.persistence.repository import WorkspaceStateRecord` (or with ScenarioRecord)

In `app/persistence/__init__.py`:
- NOT directly re-exported (only `ScenarioRecord` is re-exported from the 3 dataclasses)

In `app/services/`:
- Not found in service files (only used internally)

### `RunRecord`

In `app/persistence/__init__.py`:
- Direct re-export: `from app.persistence.repository import (RunRecord, ...)` (via runs_repository re-export)

In `app/services/`:
- `save_run_service.py`

### `ScenarioExportRecord`

In `app/persistence/__init__.py`:
- Direct re-export: `from app.persistence.repository import (ScenarioExportRecord, ...)` (via exports_repository re-export)

In `app/services/`:
- Not found in service files

## Lazy import patterns

All 5 dataclasses are imported via `TYPE_CHECKING` + runtime lazy
import pattern to avoid circular imports:

```python
# At module top:
if TYPE_CHECKING:
    from app.persistence.repository import ScenarioRecord, WorkspaceStateRecord

# Inside function body:
from app.persistence.repository import ScenarioRecord
```

This pattern works **regardless of where the dataclass is defined**,
as long as `app.persistence.repository` re-exports it (which it does
via the compatibility façade pattern).

## Circular import risks

Current: **0 circular imports** in the persistence layer (Phase 53C
introduced the lazy import pattern that resolved all prior circular
issues).

If we move records to `app/persistence/records.py`:

- `records.py` itself has no imports from other persistence modules
- Other persistence modules continue to use lazy imports
- `repository.py` would re-export from `records.py`
- `__init__.py` would re-export from `records.py`
- **No circular import risk introduced** (the lazy pattern is preserved)

If we leave records in `repository.py`:
- No change to current import structure
- No risk, no benefit

## Which dataclasses are still in repository.py

3 of 5 dataclasses are still in `app/persistence/repository.py`:

- `ProjectRecord` (line 191)
- `ScenarioRecord` (line 231)
- `WorkspaceStateRecord` (line 308)

The other 2 (`RunRecord`, `ScenarioExportRecord`) were moved to their
owner modules in earlier Phase 53 work (53B and 53C respectively).

## Whether repository.py can remain compatibility façade without moving records

**Yes, it can.**

`repository.py` already re-exports 12 functions from 6 modules. Adding
re-exports for 3 dataclasses is a trivial change. The compatibility
façade is stable and does not need to be split.

The current state is:
- 455 lines of `repository.py` = 3 dataclasses (150 lines) + 12 re-exports (~30 lines) + 5 NOT-Group-B functions (~165 lines) + module docstring/imports (~110 lines)
- The 3 dataclasses represent ~33% of the file's current size
- Moving them out would shrink `repository.py` to ~305 lines

## Options

### Option A: Move all 3 records to `app/persistence/records.py`

**Benefits:**
- One single source of truth for all 5 records
- `repository.py` shrinks from 455 to ~305 lines
- Matches the pattern of `db.py`, `provenance.py` (infrastructure files)
- Easy to find for new contributors

**Risks:**
- New module = more files to track
- Service files would need to update import paths
- Any direct `app.persistence.repository.ProjectRecord` would need
  to be `app.persistence.records.ProjectRecord` (but compatibility
  re-export keeps backward compat)

**Likely changed files:**
- `app/persistence/records.py` (NEW)
- `app/persistence/repository.py` (remove 3 dataclasses, add 3 re-exports)
- `app/persistence/projects_repository.py` (lazy imports)
- `app/persistence/scenarios_repository.py` (lazy imports)
- `app/persistence/workspace_repository.py` (lazy imports)
- `app/persistence/__init__.py` (re-exports)
- `app/services/project_save_as_service.py` (potentially)
- `app/services/projects_create_service.py` (potentially)
- `app/services/save_run_service.py` (potentially)
- `app/services/scenario_duplicate_service.py` (potentially)
- `app/services/scenario_state_service.py` (potentially)
- `tests/` (~5-10 test files if they import directly)

**Tests required:**
- P0 pin for each record (signature, fields, from_row)
- Compatibility test: `from app.persistence.repository import ProjectRecord` still works
- Re-export test: same object identity
- Lazy import cycle test

**Auto-merge eligibility:** **Yes** (with strong P0 pin and compatibility tests; all changes are behavior-preserving re-exports)

**Recommendation:** ✓ **Recommended** — cleanest design, lowest risk, fits Phase 53 pattern

### Option B: Move only scenario/workspace records to scenarios_repository/workspace_repository

**Benefits:**
- Each module owns its data classes (ScenarioRecord in scenarios_repository, WorkspaceStateRecord in workspace_repository, ProjectRecord in projects_repository)
- Symmetry with `RunRecord` (already in runs_repository) and `ScenarioExportRecord` (already in exports_repository)
- All 5 records in their owner modules
- No new `records.py` file

**Risks:**
- `ProjectRecord` ownership is unclear (projects_repository owns the writes but `ProjectRecord` is a "shared" type)
- Multiple owners = more places to look
- Some symmetry with current state (only 2 records already in owner modules)

**Likely changed files:**
- `app/persistence/scenarios_repository.py` (add `ScenarioRecord` dataclass)
- `app/persistence/workspace_repository.py` (add `WorkspaceStateRecord` dataclass)
- `app/persistence/projects_repository.py` (add `ProjectRecord` dataclass)
- `app/persistence/repository.py` (remove 3 dataclasses, add 3 re-exports)
- `app/persistence/__init__.py` (potentially re-export from new owners)
- Service files (potentially)

**Tests required:**
- P0 pin for each moved record
- Compatibility test: `from app.persistence.repository import X` still works
- Re-export identity test

**Auto-merge eligibility:** **Yes** (with strong P0 pin)

**Recommendation:** ⚠️ **Viable but less clean** — splits records across 3 modules

### Option C: Leave records in repository.py (status quo)

**Benefits:**
- No change, no risk
- Compatibility façade already works
- Defer the decision

**Risks:**
- `repository.py` stays at 455 lines (still a façade, but bigger)
- 3 records in a module that has no real "owner" semantics
- Future work might re-introduce complexity

**Likely changed files:** None

**Tests required:** None

**Auto-merge eligibility:** N/A (no change)

**Recommendation:** ✗ **Defers the inevitable** — if a future phase needs to split `repository.py` further, the records will be in the way

### Option D: Move records gradually with compatibility re-exports

**Benefits:**
- Phase 53G-style: one record at a time, each as its own PR
- Lower per-PR risk
- Each PR has its own P0 pin

**Risks:**
- More PRs = more review burden
- More test re-pointing churn
- More "stacked draft PR" risk

**Likely changed files (per PR):**
- One module change + re-export + 2-3 test file re-pointings
- 3 PRs total (one per record)

**Tests required:**
- P0 pin per record
- Compatibility re-export test

**Auto-merge eligibility:** **Per-PR** — same as Option A/B, but split into 3 smaller PRs

**Recommendation:** ⚠️ **Same as A but slower** — only useful if a single PR is too risky

## Comparison summary

| Option | Files | PRs | Risk | Auto-merge | Rec. |
|---|---|---|---|---|---|
| A: All to records.py | ~12 | 1 (or 3) | low | Yes | ✓ |
| B: One per owner module | ~10 | 1 (or 3) | medium | Yes | ⚠️ |
| C: Status quo | 0 | 0 | none | N/A | ✗ |
| D: Gradual (sub of A or B) | ~3-5 per PR | 3 | low | Yes per PR | ⚠️ |

## Recommended option

**Option A: Move all 3 records to `app/persistence/records.py`** (single PR or 3-PR stack).

This matches the Phase 53 pattern (one module per concern, compatibility
façade, byte-for-byte preservation, P0 pin per moved item). The change
is mechanical: 3 dataclasses move, 3 re-exports added to
`repository.py`, lazy import paths update, `__init__.py` updates.
Risk is low because the lazy import pattern already works.

## Required tests for future records refactor

If Option A is approved:

1. **P0 pin per record** (3 files):
   - `test_phase53i1_project_record_p0_behavior_pin.py` — 15+ tests
   - `test_phase53i1_scenario_record_p0_behavior_pin.py` — 15+ tests
   - `test_phase53i1_workspace_state_record_p0_behavior_pin.py` — 15+ tests

2. **Compatibility test** (1 file):
   - `test_phase53i1_records_compatibility_facade.py` — verify
     `from app.persistence.repository import ProjectRecord` still works,
     same object identity as `app.persistence.records.ProjectRecord`

3. **Lazy import cycle test** (1 file):
   - `test_phase53i1_records_no_circular_import.py` — verify all
     modules can be imported in any order

4. **Structural test** (1 file):
   - `test_phase53i1_records_extraction.py` — verify the dataclasses
     are in `records.py`, not in `repository.py`

5. **Test re-pointing** (3-5 files):
   - Existing test files that import from `repository.py` for these
     records: minor changes

**Total: ~5-7 new test files, ~5 re-pointed test files**

## Stop conditions for future records refactor

STOP and report if:

- Any service file change required (route/service files are out of scope)
- Any circular import appears after move
- Any P0 pin fails
- Re-export object identity changes (would break `is` comparisons)
- Field shape changes
- Test weakening needed
- Any new direct DB/sqlite import introduced
- Behavior change in any existing function

## Recommended next phase if approved

After Claude review:

- **Option A** is the cleanest: single PR `Phase 53I-1: Extract record dataclasses to records.py`
- Stack as **draft PR only** (records relocation is data-shape change
  even if mechanical, so it should be reviewed)
- Use the same P0 pin + compatibility test pattern from 53G-4..53G-7
- **NO auto-merge** (records relocation is a structural change, should
  be reviewed)

## Recommended decision path

1. Run Claude review (53H-2) on the post-Group-B state
2. Based on Claude review feedback, decide:
   - Proceed to records relocation (Option A or B)
   - Defer records relocation and move to UI/pilot hardening
   - Defer everything and continue with other work
