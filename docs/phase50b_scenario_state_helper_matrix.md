# Phase 50B — Scenario State Helper Extraction Matrix

## Base SHA
`83d4388f8a6272c2a51b8646a59f6f26cb703358`

## Functions Extracted

### build_workspace_state_metadata

| Input State | Output Shape | Notes |
|------------|-------------|-------|
| `workspace_state=None` | 8-field dict, all empty/False | Clean empty state |
| `last_runtime_origin="saved_state"` | `last_runtime_origin_label="Runtime bound to saved scenario snapshot"` | Scenario snapshot bound |
| `last_runtime_origin="workspace_base"` | `last_runtime_origin_label="Runtime bound to clean workspace base"` | Workspace base bound |
| `last_runtime_origin="preview_only"` | `last_runtime_origin_label="Preview only; runtime not executed"` | Preview only |
| `last_runtime_origin=""` | `last_runtime_origin_label="No runtime bound yet"` | No runtime |
| `dirty=True + last_runtime_snapshot_id set` | Label appended with "(older than current draft)" | Stale runtime warning |
| `dirty=False` | `dirty_label="Clean saved state"` | Clean |
| `dirty=True` | `dirty_label="Unsaved edits"` | Dirty |

### scenario_provenance_for_record

| project_record | scenario_record | Output | Notes |
|---------------|-----------------|--------|-------|
| present | present | `get_scenario_provenance(...)` dict | Full provenance |
| present | None | `None` | Early exit, passthrough |
| None | present | `None` | Early exit, avoids AttributeError |
| None | None | `None` | Both None → None |

## Comparison: Before vs After

| Aspect | Before (main_web.py) | After (Phase 50B) |
|--------|---------------------|-------------------|
| Implementation location | `_workspace_state_meta()` inline | `scenario_state_service.build_workspace_state_metadata()` |
| Implementation location | `_scenario_provenance_for_record()` inline | `scenario_state_service.scenario_provenance_for_record()` |
| Thin wrappers in main_web.py | Yes (just delegate) | Same |
| `_resolve_runtime_snapshot_source` location | main_web.py | main_web.py (unchanged) |
| `/run` route | unchanged | unchanged |
| `/download` POST route | unchanged | unchanged |
| GET `/download` route | unchanged | unchanged |
| `record_export` calls in main_web.py | 0 | 0 |

## Phase 50B Changed Files

| File | Change |
|------|--------|
| `app/services/scenario_state_service.py` | **NEW** — 2 helpers + 2 internal duplicates |
| `app/services/__init__.py` | Added `build_workspace_state_metadata`, `scenario_provenance_for_record` exports |
| `main_web.py` | Import new helpers, thin wrapper `_workspace_state_meta` → `build_workspace_state_metadata`, thin wrapper `_scenario_provenance_for_record` → `scenario_provenance_for_record` |
| `tests/test_phase50b_scenario_state_helper_extraction.py` | **NEW** — 25 tests |
| `docs/phase50b_scenario_state_helper_extraction.md` | **NEW** |
| `docs/phase50b_scenario_state_helper_matrix.md` | **NEW** (this file) |
| `reports/phase50b_scenario_state_helper_extraction_summary.json` | **NEW** |

## Not Changed (Deferred to 50C)

- `_resolve_runtime_snapshot_source` — still in main_web.py, unchanged
- `resolve_active_scenario_runtime_snapshot` — still called from main_web.py
- `runtime_guard_for_snapshot` — still called from main_web.py
- `/run` route logic — unchanged
- `/download` POST route logic — unchanged
- Form parsing helpers — unchanged

## Service Module Structure

```
app/services/scenario_state_service.py
├── build_workspace_state_metadata(workspace_state) -> dict
├── _normalize_template_source(template_source, project_type) -> str  [internal duplicate]
├── _template_origin_for_record(project_record) -> str               [internal duplicate]
└── scenario_provenance_for_record(project_record, scenario_record) -> dict | None
```