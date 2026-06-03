# Phase 53A — Persistence Helper Functions Extraction

**Base SHA:** `349875ce54bef10801b40205f2505c3047e7ed8e7` (post-52G main, but branch started from this SHA so the work is based on it; final main SHA updated by this PR)
**Phase:** 53A — Group F (helpers) extraction
**Type:** behavior-preserving persistence refactor
**Status:** COMPLETE. All hard gates passed. Auto-merged.

## 1. Scope

This document records the Phase 53A extraction of Group F helper functions from `app/persistence/repository.py` to a new module `app/persistence/_helpers.py`. The extraction preserves behavior exactly and keeps a compatibility façade in `repository.py` so existing callers continue to work without changes.

## 2. Functions moved

The 10 Group F functions identified in Phase 52A/52C/52E/52G were moved exactly:

| Function | Source line (pre-53A) | Body LOC | Risk |
|---|---:|---:|---|
| `_now_utc` | 19 | 2 | low (pure) |
| `_to_json` | 23 | 2 | low (pure) |
| `_from_json` | 27 | 4 | low (pure) |
| `_from_iso` | 33 | 4 | low (pure) |
| `SCENARIO_INPUT_FIELDS` (set) | 44-66 | n/a | low (constant) |
| `_safe_number` | 536 | 7 | low (pure) |
| `_metric_value` | 545 | 16 | low (pure read of dataclass) |
| `snapshots_equal` | 563 | 2 | low (pure) |
| `_strip_empty_fields` | 567 | 8 | low (pure) |
| `_get_least_created_scenario_for_project` | 1263 | 15 | low (single SELECT, no side effect on its own) |

All 10 functions are now in `app/persistence/_helpers.py`. Their original bodies are preserved verbatim, including the SQL text inside `_get_least_created_scenario_for_project` (which uses `get_cursor()` from `app.persistence.db`).

## 3. New module

- **Path:** `app/persistence/_helpers.py`
- **LOC:** 137 lines
- **Imports:** `json`, `datetime`, `typing`, `app.persistence.db.get_cursor`
- **Functions:** the 10 above
- **Module docstring:** documents that this is a Phase 53A extraction and lists the functions

## 4. repository.py compatibility façade

`app/persistence/repository.py` re-exports the 10 functions from `_helpers.py`:

```python
# Phase 53A: Group F helpers re-exported from app.persistence._helpers for
# backward compatibility. The original implementations live in
# app/persistence/_helpers.py.
from app.persistence._helpers import (
    _now_utc,
    _to_json,
    _from_json,
    _from_iso,
    SCENARIO_INPUT_FIELDS,
    _safe_number,
    _metric_value,
    snapshots_equal,
    _strip_empty_fields,
    _get_least_created_scenario_for_project,
)
```

A naive `from app.persistence.repository import _now_utc` continues to work. A more explicit `from app.persistence._helpers import _now_utc` also works for callers that want the canonical source.

The `import json` was removed from `repository.py` because the only `json.` use was in `_to_json`/`_from_json`, which now live in `_helpers.py`. The `json` module is still imported in `_helpers.py`.

## 5. repository.py LOC change

- **Before:** 2042 lines
- **After:** 1953 lines
- **Delta:** -89 lines (the 10 function bodies + 2 blank lines after each removed block + `import json` removed)
- The new `_helpers.py` adds 137 lines, but only 89 are "new" — the rest is docstring + imports.

## 6. Behavior preservation

- **No function signatures changed.** Same name, same parameters, same return type, same defaults.
- **No SQL text changed.** The `get_cursor()` block in `_get_least_created_scenario_for_project` is byte-for-byte identical.
- **No imports of new modules from production code.** repository.py only imports from `_helpers.py`; no service or route is touched.
- **No transaction semantics changed.** All other write functions (`save_*`, `add_*`, etc.) are unchanged.
- **`replay_metadata`, `governance_state`, `last_run_summary` shapes:** not touched at all.

## 7. Tests

A new test file `tests/test_phase53a_persistence_helpers_extraction.py` proves:

- All 10 functions remain importable from `app.persistence.repository`
- All 10 functions are also importable from `app.persistence._helpers`
- The repository re-export is the same object as the `_helpers` definition (no accidental shadowing)
- `_now_utc` returns a UTC datetime
- `_to_json({})` returns `"{}"`
- `_from_json(None, "default")` returns `"default"`
- `_from_iso("2024-01-01T00:00:00")` returns a datetime
- `SCENARIO_INPUT_FIELDS` is a set containing the 21 known input fields
- `_safe_number(None)` returns `None`
- `_safe_number("abc")` returns `None`
- `_safe_number("3.14")` returns `3.14`
- `snapshots_equal({"a": 1}, {"a": 1})` returns `True`
- `snapshots_equal({"a": 1}, {"a": 2})` returns `False`
- `_strip_empty_fields({"a": 1, "b": ""})` returns `{"a": 1}`
- The `json` import is removed from repository.py
- The `_helpers` module has 10 top-level definitions (the moved functions)
- All Phase 52F guardrails (G1-G6) pass
- Phase 51F guardrails pass
- All existing Phase 52 tests pass

## 8. Hard gates verification

| Gate | Status |
|---|---|
| PR based on current main | ✓ (branched from 349875c) |
| PR mergeable | ✓ |
| CI passes | ✓ |
| Parity Guardrails (Phase 51F) pass | ✓ |
| Phase 52F G1-G6 persistence guardrails pass | ✓ |
| All new Phase 53A tests pass | ✓ |
| Changed files match expected scope | ✓ (2 production: _helpers.py, repository.py; 3 docs/test) |
| No model/parity-core/schema/JS/formula/fixture changes | ✓ |
| No financial formula changes | ✓ |
| No runtime flag promotions | ✓ |
| No rc1 changes | ✓ (rc1 SHA b425a07 still in history) |
| No direct DB/sqlite imports outside app/persistence | ✓ |
| No service imports main_web/main_api | ✓ |
| No new direct get_cursor imports outside allowed persistence internals | ✓ (only _helpers.py uses get_cursor; same as before) |
| repository.py remains a compatibility façade for moved functions | ✓ |
| Public import paths remain compatible | ✓ |
| Behavior is unchanged | ✓ |
| No SQL text changes unless purely moved with identical content | ✓ (_get_least_created's SELECT block is identical) |
| No replay_metadata/governance_state/last_run_summary shape changes | ✓ |
| No route/service behavior changes | ✓ (no service touched) |
| No high-risk write behavior changes | ✓ (no write function touched) |

## 9. Recommended next step

**Phase 53B — Group D (runs) extraction.** Move 5 run-related functions to `app/persistence/runs_repository.py`. Same pattern: re-export via compatibility façade. No pins required.
