# Phase 53D — Project Read Persistence Functions Extraction

**Base SHA:** `868b99e2671aa3ecadcb1dc3f711c0cd38747795` (post-53C main)
**Phase:** 53D — Group A-reads (project reads) extraction
**Type:** behavior-preserving persistence refactor
**Status:** COMPLETE. All hard gates passed. Auto-merged.

## 1. Scope

This document records the Phase 53D extraction of Group A-reads (project read) persistence functions from `app/persistence/repository.py` to a new module `app/persistence/projects_repository.py`. The extraction preserves behavior exactly and keeps a compatibility façade in `repository.py`. **Project write functions (including `save_project`) are NOT touched** — they will move in Group A-2 with the P0 pin for `save_project`.

## 2. Functions moved

| Function | Source line (pre-53D) | Body LOC | Risk |
|---|---:|---:|---|
| `get_project` | 610-616 | 7 | low (read) |
| `get_project_by_code` | 617-626 | 10 | low (read) |
| `list_projects` | 627-635 | 9 | low (read) |
| `list_baseline_records` | 636-646 | 11 | low (read, returns saved-baseline records) |
| `get_project_record` | 861-873 | 13 | low (dispatcher) |
| `list_project_records` | 875-889 | 15 | low (read) |

All 6 items are now in `app/persistence/projects_repository.py`. Their original bodies are preserved verbatim, including the SQL text and the dispatcher logic in `get_project_record` (which falls back to `get_project` or `get_project_by_code` based on which arg is provided).

## 3. New module

- **Path:** `app/persistence/projects_repository.py`
- **LOC:** ~95 lines
- **Imports:** `app.persistence.db.get_cursor`; lazy import of `ProjectRecord` to avoid circular import
- **Functions:** the 6 above
- **Type annotations:** use string forward references (`"Optional[ProjectRecord]"`) with `TYPE_CHECKING` block to avoid circular import at module load time

## 4. repository.py compatibility façade

`app/persistence/repository.py` re-exports the 6 items from `projects_repository.py`:

```python
# Phase 53D: Group A-reads (project reads) re-exported from
# app.persistence.projects_repository for backward compatibility.
# The original implementations live in app/persistence/projects_repository.py.
# Project writes (save_project, create_project_record, update_project_record,
# seed_baseline_projects_if_needed, etc.) remain in repository.py for now
# and will move in Group A-2 with the P0 pin for save_project.
from app.persistence.projects_repository import (
    get_project,
    get_project_by_code,
    list_projects,
    list_baseline_records,
    get_project_record,
    list_project_records,
)
```

A naive `from app.persistence.repository import get_project` continues to work.

## 5. repository.py LOC change

- **Before (post-53C):** 1501 lines
- **After (post-53D):** 1452 lines
- **Delta:** -49 lines (6 functions + blank lines)

## 6. Behavior preservation

- **No function signatures changed.** Same name, same parameters, same return type, same defaults.
- **No SQL text changed.** All SELECT statements are byte-for-byte identical.
- **`get_project_record` dispatcher logic preserved:** falls back to `get_project` or `get_project_by_code` based on which kwarg is provided; returns None if neither is provided.
- **No imports of new modules from production code.** repository.py only imports from `projects_repository.py`; no service or route is touched.
- **No transaction semantics changed.** All reads use `with get_cursor() as cur:`.
- **Project writes (`save_project`, `seed_baseline_projects_if_needed`, `create_project_record`, `update_project_record`) are NOT touched** — they remain defined in `repository.py` for Phase 53E (Group A-2).

## 7. Tests

A new test file `tests/test_phase53d_persistence_project_reads_extraction.py` proves:

- All 6 A-reads functions remain importable from `app.persistence.repository`
- All 6 A-reads functions are also importable from `app.persistence.projects_repository`
- The repository re-export is the same object as the `projects_repository` definition
- `save_project` is NOT in `projects_repository` (it stays in repository.py)
- `save_project` is still defined in `repository.py` (not re-exported)
- The dispatcher `get_project_record` still routes to `get_project` or `get_project_by_code`
- `list_project_records` respects the `include_archived` parameter
- The Phase 52F G5 guardrail (≥20 `with get_cursor()` blocks total in app/persistence) passes (now sums across all 4 module files)
- All Phase 52F guardrails (G1-G6) pass
- Phase 51F guardrails pass
- All existing Phase 52 + 53A + 53B + 53C tests pass

## 8. Hard gates verification

| Gate | Status |
|---|---|
| PR based on current main | ✓ (branched from 868b99e) |
| PR mergeable | ✓ |
| CI passes | ✓ |
| Parity Guardrails (Phase 51F) pass | ✓ |
| Phase 52F G1-G6 persistence guardrails pass | ✓ (G5 updated to sum across all persistence modules) |
| All new Phase 53D tests pass | ✓ |
| Changed files match expected scope | ✓ (1 new module + repo.py + docs/test + 1 guardrail test update) |
| No model/parity-core/schema/JS/formula/fixture changes | ✓ |
| No financial formula changes | ✓ |
| No runtime flag promotions | ✓ |
| No rc1 changes | ✓ (rc1 SHA b425a07 still in history) |
| No direct DB/sqlite imports outside app/persistence | ✓ |
| No service imports main_web/main_api | ✓ |
| No new direct get_cursor imports outside allowed persistence internals | ✓ |
| repository.py remains a compatibility façade for moved functions | ✓ |
| Public import paths remain compatible | ✓ |
| Behavior is unchanged | ✓ |
| No SQL text changes unless purely moved with identical content | ✓ |
| No replay_metadata/governance_state/last_run_summary shape changes | ✓ (not applicable) |
| No route/service behavior changes | ✓ (no service touched) |
| **No project write behavior changes** | ✓ `save_project` still in repository.py; will move in 53E with the P0 pin |

## 9. Recommended next step

**Phase 53 Block 1 is COMPLETE.** Stop after this PR.

The next phases in Phase 53 are:
- **53E (Group A-2 / project writes):** requires the P0 pin for `save_project` (must-pin item 1 from Phase 52D). The pin should be added BEFORE this work begins. This is a **review-required** group.
- **53F (Group C / workspace_state):** requires the P0 pin for `save_workspace_state`. **Review-required**.
- **53G (Group B / scenarios):** requires 5 P0 pins. **Sign-off required**.

The user should review the Block 1 result before authorizing 53E, or run a Claude architecture review of the post-53D state.
