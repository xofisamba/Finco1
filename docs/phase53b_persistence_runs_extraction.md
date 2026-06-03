# Phase 53B — Run Persistence Functions Extraction

**Base SHA:** `bcdd687fb3e0f459b8a88cdcee91701b898f7507` (post-53A main)
**Phase:** 53B — Group D (runs) extraction
**Type:** behavior-preserving persistence refactor
**Status:** COMPLETE. All hard gates passed. Auto-merged.

## 1. Scope

This document records the Phase 53B extraction of Group D run-related persistence functions from `app/persistence/repository.py` to a new module `app/persistence/runs_repository.py`. The extraction preserves behavior exactly and keeps a compatibility façade in `repository.py`.

## 2. Functions moved

| Function/class | Source line (pre-53B) | Body LOC | Risk |
|---|---:|---:|---|
| `RunRecord` (dataclass) | 266-303 | 38 | low (data class) |
| `save_run` | 536-585 | 50 | medium (writes to runs table) |
| `get_run` | 586-592 | 7 | low (read) |
| `list_runs` | 593-601 | 9 | low (read) |
| `delete_run` | 602-606 | 5 | low (DELETE) |
| `count_runs` | 608-613 | 6 | low (read) |

All 6 items are now in `app/persistence/runs_repository.py`. Their original bodies are preserved verbatim.

## 3. New module

- **Path:** `app/persistence/runs_repository.py`
- **LOC:** ~140 lines
- **Imports:** `uuid`, `dataclasses.dataclass`, `datetime.datetime`, `app.persistence._helpers` (for `_from_iso`, `_from_json`, `_now_utc`, `_to_json`), `app.persistence.db.get_cursor`
- **Functions/classes:** the 6 above

## 4. repository.py compatibility façade

`app/persistence/repository.py` re-exports the 6 items from `runs_repository.py`:

```python
# Phase 53B: Group D (runs) re-exported from app.persistence.runs_repository
# for backward compatibility. The original implementations live in
# app/persistence/runs_repository.py.
from app.persistence.runs_repository import (
    RunRecord,
    save_run,
    get_run,
    list_runs,
    delete_run,
    count_runs,
)
```

A naive `from app.persistence.repository import save_run` continues to work. The `RunRecord` class is also re-exported.

## 5. repository.py LOC change

- **Before (post-53A):** 1953 lines
- **After (post-53B):** 1846 lines
- **Delta:** -107 lines (RunRecord class + 5 functions + blank lines)
- The new `runs_repository.py` adds ~140 lines, of which ~30 are docstring + imports.

## 6. Behavior preservation

- **No function signatures changed.** Same name, same parameters, same return type, same defaults.
- **No SQL text changed.** All INSERT, SELECT, DELETE, COUNT statements are byte-for-byte identical.
- **No imports of new modules from production code.** repository.py only imports from `runs_repository.py`; no service or route is touched.
- **No transaction semantics changed.** The single-transaction `with get_cursor() as cur:` pattern is preserved.
- **`replay_metadata` shape:** not touched (still defaulting `run_id` and `runtime_timestamp` exactly as before).

## 7. Tests

A new test file `tests/test_phase53b_persistence_runs_extraction.py` proves:

- All 6 items remain importable from `app.persistence.repository`
- All 6 items are also importable from `app.persistence.runs_repository`
- The repository re-export is the same object as the `runs_repository` definition
- `RunRecord` is a dataclass with the expected fields
- `RunRecord.to_dict()` produces a complete dict
- `count_runs` is callable (returns int)
- `save_run`, `get_run`, `list_runs`, `delete_run` are callable with expected signatures
- `runs_repository` module has 6 top-level definitions (1 class + 5 functions)
- `replay_metadata` defaulting in `save_run` still sets `run_id` and `runtime_timestamp`
- `_from_json`/`_to_json` from `_helpers` are used (verified by inspecting imports)
- All Phase 52F guardrails (G1-G6) pass
- Phase 51F guardrails pass
- All existing Phase 52 + 53A tests pass

## 8. Hard gates verification

| Gate | Status |
|---|---|
| PR based on current main | ✓ (branched from bcdd687f) |
| PR mergeable | ✓ |
| CI passes | ✓ |
| Parity Guardrails (Phase 51F) pass | ✓ |
| Phase 52F G1-G6 persistence guardrails pass | ✓ |
| All new Phase 53B tests pass | ✓ |
| Changed files match expected scope | ✓ (1 new module + repo.py + docs/test) |
| No model/parity-core/schema/JS/formula/fixture changes | ✓ |
| No financial formula changes | ✓ |
| No runtime flag promotions | ✓ |
| No rc1 changes | ✓ (rc1 SHA b425a07 still in history) |
| No direct DB/sqlite imports outside app/persistence | ✓ |
| No service imports main_web/main_api | ✓ |
| No new direct get_cursor imports outside allowed persistence internals | ✓ (only runs_repository.py uses get_cursor; same as before) |
| repository.py remains a compatibility façade for moved functions | ✓ |
| Public import paths remain compatible | ✓ |
| Behavior is unchanged | ✓ |
| No SQL text changes unless purely moved with identical content | ✓ |
| No replay_metadata/governance_state/last_run_summary shape changes | ✓ |
| No route/service behavior changes | ✓ (no service touched) |
| No high-risk write behavior changes | ✓ (save_run is not in the 7-high-risk list) |

## 9. Recommended next step

**Phase 53C — Group E (exports+audit) extraction.** Move 11 export/audit functions to `app/persistence/exports_repository.py`. Note: `record_export` is in the 7-high-risk list, but the Phase 52 plan classified Group E as auto-merge eligible only if existing audit-pipeline coverage is sufficient. The Phase 49 audit tests + Phase 14 lineage tests already cover the surface, so the move is safe.
