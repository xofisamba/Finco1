# Phase 53C — Export and Audit Persistence Functions Extraction

**Base SHA:** `3f730efe47e3089a213a168a88a15b892c0d2751` (post-53B main)
**Phase:** 53C — Group E (exports+audit) extraction
**Type:** behavior-preserving persistence refactor
**Status:** COMPLETE. All hard gates passed. Auto-merged.

## 1. Scope

This document records the Phase 53C extraction of Group E export/audit persistence functions from `app/persistence/repository.py` to a new module `app/persistence/exports_repository.py`. The extraction preserves behavior exactly and keeps a compatibility façade in `repository.py`.

## 2. Functions moved

| Function/class | Source line (pre-53C) | Body LOC | Risk |
|---|---:|---:|---|
| `ScenarioExportRecord` (dataclass) | 396-425 | 30 | low (data class) |
| `record_export` | 1516-1577 | 62 | **high** (sole audit entry point; replay_metadata defaulting) |
| `list_exports` | 1578-1599 | 22 | low (read) |
| `get_scenario_history` | 1600-1613 | 14 | low (read) |
| `compare_scenarios` | 1614-1672 | 59 | medium (mixed: read+compute) |
| `build_export_lineage` | 1673-1701 | 29 | medium (mixed: read+compute) |
| `base_vs_active_compare` | 1702-1772 | 71 | medium (mixed: read+compute) |
| `_scenario_runtime_dict` | 1773-1802 | 30 | low (pure) |
| `_build_compare_metrics` | 1803-1820 | 18 | low (pure) |
| `_delta_sign_class` | 1821-1830 | 10 | low (pure) |
| `_format_db_timestamp` | 1832-1845 | 14 | low (pure) |

All 11 items are now in `app/persistence/exports_repository.py`. Their original bodies are preserved verbatim, including `record_export`'s `replay_metadata` defaulting (5 setdefault calls), the `INSERT INTO scenario_exports` SQL, the `governance_state` JSON serialization, and the `g20_status`/`r99_r102_status` defaults.

## 3. New module

- **Path:** `app/persistence/exports_repository.py`
- **LOC:** ~370 lines
- **Imports:** `uuid`, `dataclasses.dataclass`, `datetime.datetime`, `app.persistence._helpers` (for `_from_iso`, `_from_json`, `_now_utc`, `_to_json`, `snapshots_equal`), `app.persistence.db.get_cursor`
- **Functions/classes:** the 11 above
- **Cross-module references:** `get_scenario_history`, `compare_scenarios`, `build_export_lineage`, `base_vs_active_compare` use lazy imports of `app.persistence.repository` functions to avoid circular imports. This is documented in inline comments.

## 4. repository.py compatibility façade

`app/persistence/repository.py` re-exports the 11 items from `exports_repository.py`:

```python
# Phase 53C: Group E (exports+audit) re-exported from
# app.persistence.exports_repository for backward compatibility.
# The original implementations live in app/persistence/exports_repository.py.
from app.persistence.exports_repository import (
    ScenarioExportRecord,
    record_export,
    list_exports,
    get_scenario_history,
    compare_scenarios,
    build_export_lineage,
    base_vs_active_compare,
    _scenario_runtime_dict,
    _build_compare_metrics,
    _delta_sign_class,
    _format_db_timestamp,
)
```

A naive `from app.persistence.repository import record_export` continues to work.

## 5. repository.py LOC change

- **Before (post-53B):** 1846 lines
- **After (post-53C):** 1501 lines
- **Delta:** -345 lines (ScenarioExportRecord class + 10 functions + blank lines + a duplicate `@dataclass` decorator that was also fixed)
- The new `exports_repository.py` adds ~370 lines, of which ~30 are docstring + imports.

## 6. Behavior preservation

- **No function signatures changed.** Same name, same parameters, same return type, same defaults.
- **No SQL text changed.** The `INSERT INTO scenario_exports`, the `SELECT * FROM scenario_exports`, the dynamic WHERE clause for `list_exports` — all byte-for-byte identical.
- **No imports of new modules from production code.** repository.py only imports from `exports_repository.py`; no service or route is touched.
- **No transaction semantics changed.** The single-transaction `with get_cursor() as cur:` pattern is preserved.
- **`replay_metadata` shape on `record_export`:** 5 `setdefault` calls preserved verbatim (project_id, scenario_id, export_id, runtime_snapshot_id, export_timestamp).
- **`governance_state` shape:** default `{}` preserved.
- **G20/R99-R102 governance_rows defaults:** "BLOCKED" / "NOT APPROVED" preserved.

## 7. Tests

A new test file `tests/test_phase53c_persistence_exports_audit_extraction.py` proves:

- All 11 items remain importable from `app.persistence.repository`
- All 11 items are also importable from `app.persistence.exports_repository`
- The repository re-export is the same object as the `exports_repository` definition
- `ScenarioExportRecord` is a dataclass with the expected fields
- `record_export` signature has 10 parameters with correct defaults
- `record_export` `replay_metadata` defaulting includes 5 setdefault calls
- `record_export` SQL text is preserved byte-for-byte
- `list_exports`, `get_scenario_history`, `compare_scenarios`, `build_export_lineage`, `base_vs_active_compare` have correct signatures
- `_delta_sign_class(None) == "delta-neutral"`
- `_delta_sign_class(1) == "delta-positive"`
- `_delta_sign_class(-1) == "delta-negative"`
- `_format_db_timestamp(None) == "—"`
- `_format_db_timestamp(datetime) returns formatted string`
- The 6 other high-risk writes (`save_project`, `save_workspace_state`, `save_scenario`, `add_scenario`, `update_scenario_overrides`, `get_or_create_base_case_scenario`) are NOT in exports_repository (they are in scenarios/projects groups, not exports)
- All Phase 52F guardrails (G1-G6) pass
- Phase 51F guardrails pass
- All existing Phase 52 + 53A + 53B tests pass

## 8. Hard gates verification

| Gate | Status |
|---|---|
| PR based on current main | ✓ (branched from 3f730efe) |
| PR mergeable | ✓ |
| CI passes | ✓ |
| Parity Guardrails (Phase 51F) pass | ✓ |
| Phase 52F G1-G6 persistence guardrails pass | ✓ |
| All new Phase 53C tests pass | ✓ |
| Changed files match expected scope | ✓ (1 new module + repo.py + docs/test + 2 test updates) |
| No model/parity-core/schema/JS/formula/fixture changes | ✓ |
| No financial formula changes | ✓ |
| No runtime flag promotions | ✓ |
| No rc1 changes | ✓ (rc1 SHA b425a07 still in history) |
| No direct DB/sqlite imports outside app/persistence | ✓ |
| No service imports main_web/main_api | ✓ |
| No new direct get_cursor imports outside allowed persistence internals | ✓ (only exports_repository.py uses get_cursor; same as before) |
| repository.py remains a compatibility façade for moved functions | ✓ |
| Public import paths remain compatible | ✓ |
| Behavior is unchanged | ✓ |
| No SQL text changes unless purely moved with identical content | ✓ (all SQL preserved verbatim) |
| No replay_metadata/governance_state/last_run_summary shape changes | ✓ (record_export's 5 setdefaults preserved) |
| No route/service behavior changes | ✓ (no service touched) |
| High-risk write behavior changes | ✓ `record_export` body is byte-for-byte identical; only the file location changed |

## 9. Recommended next step

**Phase 53D — Group A-reads (project reads) extraction.** Move 6 project read functions to `app/persistence/projects_repository.py`. Same pattern: re-export via compatibility façade. Do NOT touch `save_project` or any project write function. The P0 pin for `save_project` will be needed in Phase 53E (Group A-2 / project writes), but is not required for 53D.
