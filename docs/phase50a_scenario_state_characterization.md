# Phase 50A — Scenario State Service Characterization

## Base SHA
`c17208638b68240f3ea68c72e441eaee629409ac` (after PR #370 merge)

## Objective
Characterize the current scenario state / runtime snapshot binding logic in main_web.py before extracting it into `app/services/scenario_state_service.py`.

**This phase is characterization only. Do not change production code.**

## Functions Inspected

| Function | Location | Purpose |
|----------|---------|---------|
| `_resolve_runtime_snapshot_source()` | `main_web.py:1042` | Resolves the clean backend-authored snapshot used for runtime/export binding |
| `_workspace_state_meta()` | `main_web.py:683` | Returns dirty/stale/runtime state metadata for UI |
| `_scenario_provenance_for_record()` | `main_web.py` | Builds scenario provenance dict |
| `runtime_guard_for_snapshot` | `app.persistence.repository` (imported) | Blocks runtime if workspace is dirty |
| `resolve_active_scenario_runtime_snapshot` | `app.persistence.repository` (imported) | Resolves active scenario record + snapshot |
| `_project_workspace_from_snapshot()` | `main_web.py` | Resolves project record + workspace state from form snapshot |
| `_collect_form_snapshot()` | `main_web.py` | Collects form fields into a snapshot dict |

## Routes Inspected

| Route | Method | Scenario State Dependencies |
|-------|--------|------------------------------|
| `/run` | POST | `runtime_guard_for_snapshot`, `_resolve_runtime_snapshot_source`, `active_scenario_record` |
| `/compare` | POST | `runtime_guard_for_snapshot`, `_resolve_runtime_snapshot_source`, `active_scenario_record` |
| `/download` | GET | `runtime_guard_for_snapshot`, `_resolve_runtime_snapshot_source`, `active_scenario_record` |
| `/download` | POST | `runtime_guard_for_snapshot`, `_resolve_runtime_snapshot_source`, `active_scenario_record` |
| `/scenarios/{scenario_id}/select` | POST | `select_scenario` (repository), workspace state update |
| `/scenarios/save` | POST | `save_scenario`, workspace state update |
| `/scenarios/state/draft` | POST | `save_workspace_state` with draft state |
| `/scenarios/state/discard` | POST | `save_workspace_state` to discard dirty state |
| `/runs` | GET | `list_runs`, workspace state for run history |
| `/save-run` | POST | `save_run`, `update_scenario_last_run_summary`, workspace state |

## Current Scenario State Responsibilities in main_web.py

### 1. Runtime Snapshot Source Resolution
`_resolve_runtime_snapshot_source()` implements a priority chain:
1. **saved_state + active_scenario_id**: Resolve from active scenario record via `resolve_active_scenario_runtime_snapshot()`
2. **saved_state fallback**: Use `workspace_state.saved_snapshot` or `project_record.baseline_snapshot`
3. **user_created**: Use `workspace_state.saved_snapshot` if available, else `project_record.baseline_snapshot` or workspace saved_snapshot
4. **factory_base_runtime**: Route handles separately (no snapshot binding needed)

Returns: `(source_snapshot, scenario_record, warning, effective_runtime_origin)`

### 2. Runtime Guard
`runtime_guard_for_snapshot(workspace_state, snapshot)` — imported from repository:
- Returns `(allow_run, runtime_origin, guard_message)`
- Blocks execution if workspace is dirty (unsaved changes)
- Sets `runtime_origin` to `"saved_state"` or `"workspace_base"`

### 3. Active Scenario Binding
`resolve_active_scenario_runtime_snapshot(user_id, project_id, scenario_id)` — imported from repository:
- Returns `(scenario_record, resolved_snapshot, warning)`
- scenario_record=None if scenario invalid/missing → fallback to workspace_base

### 4. Workspace State Metadata
`_workspace_state_meta(workspace_state)`:
- `dirty`: bool — True if workspace has unsaved changes
- `dirty_label`: "Clean saved state" | "Dirty — unsaved changes"
- `active_scenario_id`, `active_scenario_name`
- `last_runtime_origin`, `last_runtime_snapshot_id`
- `runtime_label`: human-readable runtime state

### 5. Scenario Provenance
`_scenario_provenance_for_record(project_record, scenario_record)`:
- Builds provenance dict for scenario records
- Used by scenario management endpoints

## Runtime Snapshot Source Decision Tree

```
runtime_origin (from runtime_guard) + active_scenario_id
    │
    ├─ saved_state + active_scenario_id exists
    │       └─ resolve_active_scenario_runtime_snapshot()
    │           ├─ scenario_record found + resolved_snapshot
    │           │   → use resolved_snapshot (clean scenario snapshot)
    │           ├─ scenario_record None
    │           │   → fallback to workspace_base (warning: "scenario unavailable")
    │           └─ resolved_snapshot None
    │               → use workspace_state.saved_snapshot or baseline_snapshot
    │
    ├─ saved_state + NO active_scenario_id
    │       └─ use workspace_state.saved_snapshot or project_record.baseline_snapshot
    │
    ├─ user_created
    │   ├─ saved_state + workspace_state.saved_snapshot
    │   │   → use workspace_state.saved_snapshot
    │   └─ otherwise
    │       → use project_record.baseline_snapshot or workspace_state.saved_snapshot or {}
    │
    └─ factory_base_runtime / workspace_base
            → snapshot=None, route uses form-driven behavior
```

## Scenario Provenance Fields

| Field | Source | Notes |
|-------|--------|-------|
| `scenario_id` | DB | Primary key |
| `scenario_name` | User input | Display name |
| `project_id` | DB | FK to project |
| `override_values` | JSON | Per-scenario overrides |
| `created_at` | DB | Timestamp |
| `runtime_snapshot_id` | DB | Linked runtime snapshot |
| `is_active` | bool | Active scenario flag |

## Active Project / Active Scenario Behavior

- **active_project**: Hidden form field set by JS when user switches project in UI
- **active_scenario_id**: Stored in workspace_state, resolved from `workspace_state.active_scenario_id`
- When user switches project via `active_project`, a new workspace_state is resolved
- Active scenario is project-scoped: switching project may change which scenario is active
- `workspace_state.dirty` flag indicates unsaved browser changes vs clean saved state

## Dirty/Stale/Runtime State Behavior

| State | dirty flag | last_runtime_snapshot_id | Meaning |
|-------|-----------|------------------------|---------|
| Clean saved state | False | set/unset | No unsaved changes, runtime bound to snapshot |
| Dirty (unsaved) | True | set | Browser has changes not yet saved |
| No runtime bound | False | None | Fresh workspace, no runtime ever run |
| Stale runtime | (dirty check) | set | Runtime snapshot ID doesn't match current saved_snapshot |

**Dirty guard**: `runtime_guard_for_snapshot` blocks `/run`, `/compare`, `/download` if workspace is dirty.
Users must save or discard before running.

## Saved State vs Saved Baseline vs User Created

| Path | project_origin | workspace behavior | snapshot source |
|------|--------------|-------------------|----------------|
| Factory template | `None` or factory seed | No saved_snapshot | Form-driven |
| Saved baseline | `saved_baseline` | May have saved_snapshot | baseline_snapshot |
| User-created project | `user_created` | saved_snapshot available | workspace_state or baseline |
| Active scenario | any | active_scenario_id bound | resolved from scenario DB |

**runtime_origin values** (returned by `runtime_guard_for_snapshot`):
- `"saved_state"` — workspace has active scenario or saved snapshot
- `"user_created"` — project_origin == "user_created"
- `"factory_base_runtime"` — no saved state, form-driven
- `"workspace_base"` — fallback when scenario unavailable

## Routes Depending on Scenario State

### `/run` (POST)
1. `runtime_guard_for_snapshot(workspace_state, snapshot)` → allow_run/runtime_origin/guard_message
2. If blocked → error response
3. If `saved_state + active_scenario_id` or `user_created` → `_resolve_runtime_snapshot_source()`
4. Override from resolved snapshot → `build_projectinputs_from_snapshot()`
5. `run_project()` or `run_demo_project()`
6. `save_run()` + `save_project()` + `update_scenario_last_run_summary()`

### `/compare` (POST)
1. Same guard + resolution pattern as `/run`
2. Runs multiple scenarios (Base/Downside/Upside)
3. Same persistence pattern

### `/download` (GET)
1. `runtime_guard_for_snapshot()` → allow_run check
2. `_resolve_runtime_snapshot_source()` for scenario binding
3. `record_download_export()` via audit service
4. Returns `build_values_only_export_for_project()` bytes

### `/download` (POST)
1. Same guard + resolution pattern
2. Uses `build_excel_export_for_post_request()` for bytes
3. `record_download_export()` with `scenario_id=active_scenario_record.scenario_id`

### Scenario Management Routes
- `/scenarios/save`: saves scenario with overrides, updates workspace active_scenario_id
- `/scenarios/{id}/select`: sets workspace active_scenario_id
- `/scenarios/state/draft`: saves workspace with dirty state
- `/scenarios/state/discard`: clears dirty state

## Extraction Risks

| Risk | Description | Mitigation |
|------|-------------|-----------|
| Circular dependency | scenario_state_service imports repository functions that use it | Extract interface contract, not implementation |
| Snapshot format coupling | Snapshot dict structure is implicit (no schema) | Document snapshot shape before extraction |
| Guard/test coverage | runtime_guard has behavioral branches | Characterization tests before change |
| Route coupling | Routes build provenance before calling service | Routes keep provenance building, pass pre-built dicts |
| Active scenario binding | `resolve_active_scenario_runtime_snapshot` is in repository | Don't extract repository; extract callers |

## Proposed scenario_state_service Boundary

```python
# app/services/scenario_state_service.py

def resolve_runtime_snapshot(
    user, project_record, workspace_state, runtime_origin: str
) -> tuple[dict, ScenarioRecord | None, str | None, str]:
    """
    Public interface for runtime snapshot resolution.
    Returns: (snapshot, scenario_record, warning, effective_runtime_origin)
    """
    ...

def build_workspace_state_metadata(workspace_state) -> dict:
    """Build UI-visible dirty/runtime state metadata."""
    ...

def check_runtime_allowed(workspace_state, snapshot) -> tuple[bool, str, str]:
    """
    Returns: (allow_run, runtime_origin, guard_message)
    Alias for runtime_guard_for_snapshot with additional preprocessing.
    """
    ...

def scenario_provenance_for_record(project_record, scenario_record) -> dict:
    ...
```

**What stays in main_web.py:**
- Route handlers (orchestration)
- Provenance dict building (`_replay_metadata_for_project`)
- Form snapshot collection (`_collect_form_snapshot`)
- Project/workspace resolution (`_project_workspace_from_snapshot`)

**What goes to scenario_state_service:**
- `_resolve_runtime_snapshot_source` logic
- `_workspace_state_meta` logic
- Wrapper/alias for `runtime_guard_for_snapshot` (optional)
- `_scenario_provenance_for_record`

## Required Phase 50B Extraction Contract

```python
def resolve_runtime_snapshot(
    user,
    project_record,
    workspace_state,
    runtime_origin: str,
) -> tuple[dict, ScenarioRecord | None, str | None, str]:
    """
    snapshot: dict — clean backend-authored inputs dict
    scenario_record: ScenarioRecord | None — bound active scenario
    warning: str | None — if scenario was unavailable/fell back
    effective_runtime_origin: str — actual origin used (may differ from input)
    """
```

## Guardrails (50A)

- ✅ No production code changes
- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No model output changes
- ✅ No route behavior changes
- ✅ No export behavior changes
- ✅ No fixture CSV changes
- ✅ No schema migrations
- ✅ G20 BLOCKED | R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted | flat/min DSCR not promoted
- ✅ Backend remains source of truth