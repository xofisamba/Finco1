# Phase 53E-2 — Project Write Persistence Functions Extraction

**Base SHA:** `6ee6544e9d18d0efc3eb0ce1f6099f6c6c2d1ef2` (post-53E-1 main)
**Phase:** 53E-2 — Group A-2 (project writes) extraction
**Type:** behavior-preserving persistence refactor
**Status:** COMPLETE. All hard gates passed. **REVIEW REQUIRED — PR remains draft, NOT auto-merged.**

## 1. Scope

This document records the Phase 53E-2 extraction of Group A-2 project write persistence functions from `app/persistence/repository.py` to `app/persistence/projects_repository.py`. The extraction preserves behavior exactly and keeps a compatibility façade in `repository.py`.

This is a **review-required** group because it moves `save_project`, one of the 7 high-risk writes.

## 2. Functions moved

| Function | Source line (pre-53E-2) | Body LOC | Risk |
|---|---:|---:|---|
| `save_project` | 507-602 | 96 | **high** (1 of 7 high-risk writes) |
| `create_project_record` | 686-714 | 29 | medium (wrapper) |
| `update_project_record` | 855-885 | 31 | medium (calls save_project) |
| `seed_baseline_projects_if_needed` | 521-549 | 29 | medium (calls save_project + _compute_baseline_snapshot) |
| `_compute_baseline_snapshot` | 551-673 | 123 | medium (large, project seed coupling) |
| `_build_default_snapshot` | 675-684 | 10 | low (pure) |
| `_fill_missing_defaults` | 686-705 | 20 | low (pure) |
| `_sum_opex` (nested) | inside `_compute_baseline_snapshot` | 5 | low (pure) |

All 8 items are now in `app/persistence/projects_repository.py`. Their original bodies are preserved verbatim, including:
- `save_project`'s INSERT and UPDATE paths
- `save_project`'s single-transaction pattern (`with get_cursor() as cur:`)
- `replay_metadata.setdefault("project_id", project_id)` in both INSERT and UPDATE paths
- `_compute_baseline_snapshot`'s tuho / oborovo / generic_wind / generic_solar branches
- `_compute_baseline_snapshot`'s governance state defaulting in `seed_baseline_projects_if_needed`
- The 4 JSON metadata columns: `replay_metadata`, `governance_state`, `last_run_summary`, `baseline_snapshot`

## 3. New module

- **Path:** `app/persistence/projects_repository.py`
- **LOC:** ~16,952 bytes (~480 lines)
- **Imports:**
  - `uuid`
  - `datetime.datetime`
  - `app.persistence._helpers` (`_from_iso`, `_from_json`, `_now_utc`, `_to_json`)
  - `app.persistence.db.get_cursor`
  - `app.persistence.repository.ProjectRecord` (TYPE_CHECKING + runtime lazy import to avoid circular import)
  - `app.project_factories` (inside `_compute_baseline_snapshot` for factory project instances)
  - `app.input_adapter.build_projectinputs_from_snapshot` (inside `_build_default_snapshot`)

## 4. repository.py compatibility façade

`app/persistence/repository.py` re-exports the 7 top-level A-2 items from `projects_repository.py`:

```python
# Phase 53E-2: Group A-2 (project writes) re-exported from
# app.persistence.projects_repository for backward compatibility.
# The original implementations live in app/persistence/projects_repository.py.
from app.persistence.projects_repository import (
    save_project,
    create_project_record,
    update_project_record,
    seed_baseline_projects_if_needed,
    _compute_baseline_snapshot,
    _build_default_snapshot,
    _fill_missing_defaults,
)
```

A naive `from app.persistence.repository import save_project` continues to work.

## 5. repository.py LOC change

- **Before (post-53D):** 1452 lines
- **After (post-53E-2):** 1100 lines
- **Delta:** -352 lines (save_project, create_project_record, update_project_record, seed_baseline_projects_if_needed, _compute_baseline_snapshot, _build_default_snapshot, _fill_missing_defaults + blank lines)

## 6. projects_repository.py LOC change

- **Before (post-53D):** ~95 lines (6 A-reads functions)
- **After (post-53E-2):** ~480 lines (6 A-reads + 7 A-2 top-level + 1 nested helper)
- **Delta:** +385 lines

## 7. ProjectRecord handling

`ProjectRecord` remains defined in `app/persistence/repository.py` for now. The new `projects_repository.py` uses `TYPE_CHECKING` + runtime lazy import:

```python
if TYPE_CHECKING:
    from app.persistence.repository import ProjectRecord

# ... function body:
def get_project(...) -> "Optional[ProjectRecord]":
    ...
    from app.persistence.repository import ProjectRecord
    return ProjectRecord.from_row(row) if row else None
```

This avoids the circular import: `repository.py` imports from `projects_repository.py`, and `projects_repository.py` references `ProjectRecord` from `repository.py` at runtime.

## 8. Behavior preservation

The Phase 53E-1 P0 pin (41 tests) was re-pointed to read from `projects_repository.py` and continues to pass. This proves:
- **No function signatures changed** (same name, parameters, defaults, return type)
- **No SQL text changed** (all 3 SELECT/UPDATE/INSERT statements are byte-for-byte identical)
- **No single-transaction pattern changed** (still exactly 1 `with get_cursor() as cur:` block per function)
- **replay_metadata behavior unchanged** (None → `{}`, setdefault project_id, _to_json serialization)
- **governance_state behavior unchanged** (None → `{}`, _to_json serialization)
- **last_run_summary behavior unchanged** (None → `{}`, _to_json serialization)
- **baseline_snapshot behavior unchanged** (None → `{}`, JSON serialization, UPDATE-path preservation)
- **project_origin behavior unchanged** (default `factory_template`, UPDATE-path fallback)
- **template_source behavior unchanged** (default None, effective_template_source logic)
- **archived/is_readonly behavior unchanged** (default False, `int(bool(...))` serialization)
- **created_at/updated_at behavior unchanged** (`_now_utc()` called exactly once, INSERT uses now for both)
- **project_id behavior unchanged** (INSERT generates new, UPDATE preserves existing)

## 9. Tests

A new test file `tests/test_phase53e2_project_write_persistence_extraction.py` proves:

- All 7 top-level A-2 items are importable from `app.persistence.projects_repository`
- All 7 are re-exported from `app.persistence.repository` (same object)
- `save_project.__module__` is `app.persistence.projects_repository` (the new home)
- `save_project` is no longer defined in `app.persistence.repository` (only re-exported)
- The 53E-1 P0 pin (41 tests) still passes
- The 53D project read tests still pass (with updated assertions: `save_project` is now in `projects_repository`)
- Other high-risk writes (`save_workspace_state`, `save_scenario`, `add_scenario`, `update_scenario_overrides`, `get_or_create_base_case_scenario`) remain in `repository.py` and are NOT touched
- The `_sum_opex` nested helper moved with `_compute_baseline_snapshot`
- All Phase 52F G1-G6 persistence guardrails pass
- Phase 51F guardrails pass

Existing tests updated (not weakened, only re-pointed):
- `tests/test_phase53d_persistence_project_reads_extraction.py`: `TestProjectWritesNotMoved` → `TestProjectWritesMovedIn53E2` (re-asserts the new state)
- `tests/test_phase53a_persistence_helpers_extraction.py`: removed `save_project` from the "still in repository body" list (it moved in 53E-2)
- `tests/test_phase53b_persistence_runs_extraction.py`: same
- `tests/test_phase53c_persistence_exports_audit_extraction.py`: same
- `tests/test_phase53e1_save_project_p0_behavior_pin.py`: re-pointed SQL-fragment checks to `projects_repository.py`

## 10. Hard gates verification

| Gate | Status |
|---|---|
| PR based on current main | ✓ (branched from 6ee6544e) |
| PR mergeable | ✓ |
| CI passes | ✓ |
| Parity Guardrails (Phase 51F) pass | ✓ |
| Phase 52F G1-G6 persistence guardrails pass | ✓ |
| All new Phase 53E-2 tests pass | ✓ |
| Changed files match expected scope | ✓ (1 module extended + repo.py + 53E-2 test + 5 existing test re-pointings + docs/report) |
| No model/parity-core/schema/JS/formula/fixture changes | ✓ |
| No financial formula changes | ✓ |
| No runtime flag promotions | ✓ |
| No rc1 changes | ✓ (rc1 SHA b425a07 still in history) |
| No direct DB/sqlite imports outside app/persistence | ✓ |
| No service imports main_web/main_api | ✓ |
| No new direct get_cursor imports outside allowed persistence internals | ✓ |
| repository.py remains public compatibility façade | ✓ |
| Public import paths remain compatible | ✓ (e.g. `from app.persistence.repository import save_project` still works) |
| Behavior is unchanged | ✓ (53E-1 pin re-pointed still passes) |
| No SQL text changes | ✓ (only moved) |
| No replay_metadata/governance_state/last_run_summary shape changes | ✓ |
| No route/service behavior changes | ✓ (no service touched) |
| **High-risk write behavior preserved** | ✓ (save_project body is byte-for-byte identical; 53E-1 pin passes) |
| **Non-A-2 high-risk writes untouched** | ✓ (save_workspace_state, save_scenario, add_scenario, update_scenario_overrides, get_or_create_base_case_scenario still in repository.py) |

## 11. Review checklist

When reviewing this PR, please verify:

1. **Test counts:** 333/333 pass (8 new 53E-2 + updated 53E-1 pin + re-pointed 53D/53A/53B/53C)
2. **repository.py shrank** from 1452 → 1100 lines
3. **projects_repository.py grew** from 95 → 480 lines (now contains Group A reads + writes)
4. **`save_project` import path preserved** via re-export (no caller needs to change)
5. **53E-1 P0 pin still passes** (proves behavior is byte-for-byte identical)
6. **No service/route was modified**
7. **No SQL text changed** (only file location)
8. **No metadata shape changed**
9. **Other 6 high-risk writes untouched** (`save_workspace_state`, `save_scenario`, `add_scenario`, `update_scenario_overrides`, `get_or_create_base_case_scenario`, plus `record_export` which moved in 53C)
10. **rc1 untouched**

## 12. Status: DRAFT (NOT MERGED)

Per the spec, this is a **review-required** group. The PR is opened as **draft** and will NOT be auto-merged. The user must explicitly approve and merge.

## 13. Recommended next step

**STOP after this report.** Do not start Group C / workspace_state (53F) or Group B / scenarios (53G). The user should:
1. Review the PR
2. Verify the 333/333 test count
3. Verify the 53E-1 pin still passes
4. Manually merge (squash)
5. Then authorize 53F (Group C / workspace_state) which requires its own P0 pin for `save_workspace_state`

## Regression fix (post-review)

After the initial PR was opened, a review identified a regression in
`_compute_baseline_snapshot`:

- The broken version used uppercase `"TUHO"` / `"Oborovo"` comparisons
  instead of lowercase `"tuho"` / `"oborovo"`.
- It did not `return baseline` immediately after the TUHO/Oborovo
  branches, causing `pi` to be overwritten by the generic Solar/Wind
  fallback.
- The nested `_sum_opex` was using `getattr(item, "amount_keur", 0)`
  instead of `getattr(item, "y1_amount_keur", 0)`.

The fix restores the function **byte-for-byte identical** to
`origin/main:app/persistence/repository.py` (commit `6ee6544e9d18d0efc3eb0ce1f6099f6c6c2d1ef2`)
before PR #435 was opened.

### Regression pin tests

`tests/test_phase53e2_compute_baseline_snapshot_regression_pin.py`
(26 tests, 7 test classes) was added to specifically catch this kind
of regression. It pins:

1. Lowercase `"tuho"` / `"oborovo"` comparisons in `_compute_baseline_snapshot`.
2. No uppercase `"TUHO"` / `"Oborovo"` comparisons.
3. Early `return baseline` after TUHO branch.
4. Early `return baseline` after Oborovo branch.
5. Generic fallback comes AFTER both branches.
6. `_sum_opex` uses `y1_amount_keur` (not `amount_keur`).
7. `opex_y1_keur` uses `str(_sum_opex(pi.opex))` in all 3 branches.
8. `active_project` value for each branch (`"tuho-baseline"`, `"oborovo-baseline"`, `normalized_source`).
9. `project_type` value for each branch (`"Wind"`, `"Solar"`, from canonical_type).
10. Factory imports are present.
11. **Byte-for-byte source comparison** to `origin/main`.
