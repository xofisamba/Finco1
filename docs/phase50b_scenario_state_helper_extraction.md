# Phase 50B — Scenario State Helper Extraction Summary

## Base SHA
`83d4388f8a6272c2a51b8646a59f6f26cb703358` (after PR #371 merge)

## Objective
Extract low-risk, pure scenario state helpers from main_web.py into `app/services/scenario_state_service.py`. This is a narrow behavior-preserving production refactor.

**Do NOT extract `_resolve_runtime_snapshot_source` — deferred to Phase 50C.**

## What Moved

### app/services/scenario_state_service.py (NEW)

| Function | Equivalent in main_web.py | Description |
|----------|--------------------------|-------------|
| `build_workspace_state_metadata()` | `_workspace_state_meta()` | Build UI-visible dirty/runtime state metadata dict |
| `scenario_provenance_for_record()` | `_scenario_provenance_for_record()` | Build scenario provenance dict for UI context |
| `_normalize_template_source()` | (duplicated) | Normalize template source string (needed by provenance) |
| `_template_origin_for_record()` | (duplicated) | Build template origin string (needed by provenance) |

**Total: 2 public functions + 2 internal helpers**

## What Did NOT Move (Deferred to Phase 50C)

- `_resolve_runtime_snapshot_source()` — complex decision tree with runtime binding
- `resolve_active_scenario_runtime_snapshot` integration
- `runtime_guard_for_snapshot` wrapper (`check_runtime_allowed`)
- `/run` route orchestration
- `/download` route orchestration
- Form parsing helpers (`_collect_form_snapshot`, `_project_workspace_from_snapshot`)

## Service API Summary

### build_workspace_state_metadata(workspace_state) -> dict
```python
{
    "dirty": bool,
    "dirty_label": "Unsaved edits" | "Clean saved state",
    "active_scenario_id": str,
    "active_scenario_name": str,
    "last_runtime_origin": str,
    "last_runtime_origin_label": str,
    "last_runtime_snapshot_id": str,
}
```
- Returns same dict when `workspace_state` is `None`
- Returns same dict for all `last_runtime_origin` values: `saved_state`, `workspace_base`, `preview_only`, `""`
- Handles dirty flag + stale runtime warning correctly

### scenario_provenance_for_record(project_record, scenario_record) -> dict | None
- Returns `None` if `scenario_record` is `None` (passthrough behavior preserved)
- Returns `None` if `project_record` is `None` (early exit, avoids AttributeError)
- Calls `get_scenario_provenance()` from `app.persistence.repository` with template origin

## Behavior Preservation Checklist

- ✅ `build_workspace_state_metadata(None)` → same dict as `_workspace_state_meta(None)`
- ✅ `build_workspace_state_metadata(mock_ws)` for all states (clean, dirty, workspace_base, preview_only) → identical dict
- ✅ `scenario_provenance_for_record(project, scenario)` → identical dict to `_scenario_provenance_for_record(project, scenario)`
- ✅ `scenario_provenance_for_record(project, None)` → `None` (preserved)
- ✅ `scenario_provenance_for_record(None, scenario)` → `None` (preserved, no AttributeError)
- ✅ `scenario_provenance_for_record(None, None)` → `None` (preserved)
- ✅ `/run` route: `runtime_guard_for_snapshot` still called in place
- ✅ `/run` route: `_resolve_runtime_snapshot_source` still called in place
- ✅ `/download` POST: `runtime_guard_for_snapshot` + `_resolve_runtime_snapshot_source` still called in place
- ✅ GET `/download`: unchanged (factory_base_runtime path)
- ✅ Export service/audit service: intact, unchanged
- ✅ `main_web.py` still has 0 direct `record_export` calls

## Why _resolve_runtime_snapshot_source Is Deferred

The function implements a complex priority-based decision tree with multiple conditional branches:
- `runtime_origin` check (`saved_state` vs `user_created` vs factory path)
- `active_scenario_id` resolution with fallback to `workspace_base`
- `resolve_active_scenario_runtime_snapshot` from repository
- `project_record.project_origin` checks
- Fallback chains between `saved_snapshot` and `baseline_snapshot`

This complexity requires full characterization tests and careful wiring verification before extraction. Phase 50B takes the low-risk helpers first to establish the pattern.

## Test Results

| Suite | Result |
|-------|--------|
| `test_phase50b_scenario_state_helper_extraction.py` | **25 passed** |
| Phase 50A characterization tests | **28 passed** |
| Phase 49 closeout tests | **28 passed** |
| `python -c "import main_web"` | ✅ OK |

## Guardrails Confirmed

- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No model output changes
- ✅ No fixture CSV changes
- ✅ No schema migrations
- ✅ No JS financial calculations
- ✅ G20 BLOCKED | R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted | flat/min DSCR not promoted
- ✅ Backend remains source of truth

## Recommended Next Phase

**Phase 50C — Extract `_resolve_runtime_snapshot_source`:**
- Extract the full priority-based decision tree
- Wire into `/run` and `/download` routes (replace inline logic with service call)
- Integration tests for saved_state/saved_baseline/user_created/factory_base_runtime paths
- Verify runtime_guard + snapshot resolution end-to-end