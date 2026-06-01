# Phase 50C-1 — Runtime Snapshot Source Resolver Characterization

## Base SHA
`dd6124814ccdcd9a36486c3909acd91f9446dca3` (after PR #372 merge)

## Objective
Characterize `_resolve_runtime_snapshot_source` in detail before Phase 50C-2 extraction. This phase is characterization/contract only. **Do NOT move the function.**

## Function Signature

```python
def _resolve_runtime_snapshot_source(
    user,
    project_record,
    workspace_state,
    runtime_origin: str,
) -> tuple[dict, object | None, str | None, str]:
    """
    Returns: (snapshot, scenario_record, warning, effective_runtime_origin)
    - snapshot: dict — clean backend-authored inputs dict
    - scenario_record: ScenarioRecord | None — bound active scenario
    - warning: str | None — if scenario was unavailable/fell back
    - effective_runtime_origin: str — actual origin used (may differ from input)
    """
```

## Callers

| Route | Usage Pattern |
|-------|--------------|
| `POST /run` | `runtime_snapshot, active_scenario_record, runtime_warning, effective_runtime_origin = _resolve_runtime_snapshot_source(...)` |
| `POST /compare` | Same pattern as POST /run |
| `POST /download` | Same pattern; used when `runtime_guard_for_snapshot` returns `saved_state` + `active_scenario_id` OR `user_created` path |
| `GET /download` | **Does NOT call** `_resolve_runtime_snapshot_source` — uses factory_base_runtime path |

### Runtime Origin Return Paths

`runtime_origin` comes from `runtime_guard_for_snapshot(workspace_state, snapshot)`:
- Returns `(allow_run, runtime_origin, guard_message)` — `runtime_origin` is set by the guard
- `runtime_origin` values: `"saved_state"`, `"workspace_base"`, `"factory_base_runtime"`

`effective_runtime_origin` is what the function actually uses — it can differ from input `runtime_origin` when scenario is unavailable (falls back to `"workspace_base"`).

## Input Objects/Fields

### user
- `user.user_id` — passed to `resolve_active_scenario_runtime_snapshot`

### project_record
- `project_record.project_id` — passed to `resolve_active_scenario_runtime_snapshot`
- `project_record.project_origin` — checked for `"user_created"`
- `project_record.project_name` — setdefault into snapshot
- `project_record.project_type` — setdefault into snapshot
- `project_record.project_origin` — setdefault into snapshot
- `project_record.template_source` — setdefault into snapshot
- `project_record.source_project_template` — fallback for template_source
- `project_record.baseline_snapshot` — used in fallback chains

### workspace_state
- `workspace_state.active_scenario_id` — checked for saved_state + active_scenario_id branch
- `workspace_state.saved_snapshot` — used in fallback chains
- `workspace_state.dirty` — NOT directly checked in this function (checked by runtime_guard)

### runtime_origin (input)
- `"saved_state"` — active scenario or saved snapshot exists
- `"workspace_base"` — fallback when scenario unavailable
- `"factory_base_runtime"` — form-driven path (this function not called for factory path)
- `"preview_only"` — possible from runtime_guard

## Branch-by-Branch Behavior

### Branch A: `runtime_origin == "saved_state"` AND `workspace_state.active_scenario_id` set

**Condition:** `runtime_origin == "saved_state" and workspace_state and workspace_state.active_scenario_id`

**Action:**
1. Call `resolve_active_scenario_runtime_snapshot(user.user_id, project_record.project_id, workspace_state.active_scenario_id)`
2. Returns: `(scenario_record, resolved_snapshot, warning_from_resolver)`

**Sub-branches:**

#### A1: `scenario_record` is None (scenario unavailable/invalid)
- `effective_origin = "workspace_base"` (overrides input runtime_origin!)
- `scenario_record = None`
- `warning = warning_from_resolver or "Selected saved scenario was unavailable, so runtime fell back to the last clean saved boundary."`
- `source = workspace_state.saved_snapshot or project_record.baseline_snapshot or {}`

#### A2: `scenario_record` found AND `resolved_snapshot` exists
- `effective_origin = "saved_state"` (unchanged)
- `scenario_record` (from DB)
- `warning = warning_from_resolver` (may be None)
- `source = dict(resolved_snapshot)` (clean scenario snapshot)

#### A3: `scenario_record` found BUT `resolved_snapshot` is None
- `effective_origin = "saved_state"` (unchanged)
- `scenario_record` (from DB)
- `warning = warning_from_resolver` (may be None)
- `source = workspace_state.saved_snapshot or project_record.baseline_snapshot or {}`

### Branch B: `project_record.project_origin == "user_created"`

**Condition:** `project_record.project_origin == "user_created"` (no check on runtime_origin)

**Note:** This branch fires when `project_origin == "user_created"` regardless of `runtime_origin`.

**Sub-branches:**

#### B1: `runtime_origin == "saved_state"` AND `workspace_state.saved_snapshot` exists
- `source = workspace_state.saved_snapshot`
- `effective_origin = runtime_origin` (unchanged, "saved_state")
- `scenario_record = None`

#### B2: otherwise (including when `runtime_origin != "saved_state"`)
- `source = project_record.baseline_snapshot or workspace_state.saved_snapshot or {}`
- `effective_origin = runtime_origin` (unchanged)
- `scenario_record = None`

### Branch C: else (fallback)

**Condition:** Neither A nor B matched — typically `runtime_origin in {"workspace_base", "factory_base_runtime", "preview_only"}` or saved_state with no active_scenario_id

**Action:**
- `source = workspace_state.saved_snapshot or {}`
- `effective_origin = runtime_origin` (unchanged)
- `scenario_record = None`
- `warning = None`

## Fallback Chain Summary

```
if runtime_origin == "saved_state" and workspace_state.active_scenario_id:
    resolve from scenario DB
    ├─ scenario_record=None → workspace_base fallback
    │   source = saved_snapshot OR baseline_snapshot
    ├─ scenario_record found + resolved_snapshot → use resolved_snapshot
    └─ scenario_record found + no resolved_snapshot → saved_snapshot OR baseline_snapshot
elif project_origin == "user_created":
    ├─ runtime_origin=="saved_state" and saved_snapshot → use saved_snapshot
    └─ otherwise → baseline_snapshot OR saved_snapshot
else:
    source = saved_snapshot or {}
```

## Snapshot Post-processing (all branches)

After source dict is built, `source.setdefault(...)` is called:
```python
source.setdefault("project_name", project_record.project_name)
source.setdefault("project_type", project_record.project_type)
source.setdefault("project_origin", project_record.project_origin)
source.setdefault("template_source", project_record.template_source or project_record.source_project_template)
source.setdefault("active_project", project_record.project_code.lower())
```

## Effective Runtime Origin Behavior

| Branch | Input runtime_origin | effective_runtime_origin |
|--------|---------------------|------------------------|
| A1 (scenario unavailable) | `"saved_state"` | `"workspace_base"` (OVERRIDDEN!) |
| A2 (resolved_snapshot exists) | `"saved_state"` | `"saved_state"` |
| A3 (no resolved_snapshot) | `"saved_state"` | `"saved_state"` |
| B1 (user_created + saved_state) | `"saved_state"` | `"saved_state"` |
| B2 (user_created, otherwise) | any | unchanged |
| C (else) | any | unchanged |

## Warning Behavior

| Situation | warning value |
|-----------|--------------|
| `resolve_active_scenario_runtime_snapshot` returns warning | `warning_from_resolver` (forwarded) |
| A1: scenario unavailable + no warning from resolver | `"Selected saved scenario was unavailable, so runtime fell back to the last clean saved boundary."` |
| A2, A3 | `warning_from_resolver` (from resolver, may be None) |
| B1, B2 | `None` |
| C | `None` |

## Extraction Risks

| Risk | Level | Description |
|------|-------|-------------|
| effective_runtime_origin override | HIGH | A1 overrides input `"saved_state"` → `"workspace_base"` — caller behavior changes |
| B branch fires on `project_origin=="user_created"` regardless of runtime_origin | HIGH | user_created path bypasses runtime_origin check, may shadow A path |
| snapshot post-processing relies on project_record fields | MEDIUM | all 6 setdefault fields come from project_record |
| resolve_active_scenario_runtime_snapshot is a repository call | MEDIUM | importing it in service creates circular dependency risk |
| workspace_state.saved_snapshot vs baseline_snapshot priority | MEDIUM | Order matters: B2 uses `baseline_snapshot or saved_snapshot`, A uses `saved_snapshot or baseline_snapshot` |
| Active scenario binding depends on workspace_state.active_scenario_id | HIGH | Different behavior when active_scenario_id is set vs not |

## Proposed Phase 50C-2 Service Contract

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class RuntimeSnapshotResolution:
    snapshot: dict[str, Any]
    scenario_record: Any | None  # ScenarioRecord | None
    warning: str | None
    effective_runtime_origin: str

def resolve_runtime_snapshot(
    *,
    user,
    project_record,
    workspace_state,
    runtime_origin: str,
) -> RuntimeSnapshotResolution:
    """
    Resolve the clean backend-authored snapshot used for runtime/export binding.

    Parameters
    ----------
    user : User
        Current user (needs user.user_id)
    project_record : ProjectRecord
        Project record (needs project_id, project_origin, project_name, project_type, etc.)
    workspace_state : WorkspaceStateRecord | None
        Workspace state (needs active_scenario_id, saved_snapshot, baseline_snapshot)
    runtime_origin : str
        Runtime origin from runtime_guard_for_snapshot

    Returns
    -------
    RuntimeSnapshotResolution
        snapshot: dict — clean backend-authored inputs (with project_name/project_type/etc. setdefaulted)
        scenario_record: ScenarioRecord | None — bound active scenario
        warning: str | None — if scenario unavailable/fell back
        effective_runtime_origin: str — actual origin used (may differ from input)
    """
    ...
```

**Service module:** `app/services/scenario_state_service.py` (already exists from Phase 50B)

## Guardrails (50C-1)

- ✅ No production code changes (characterization only)
- ✅ `_resolve_runtime_snapshot_source` stays in main_web.py
- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No model output changes
- ✅ No fixture CSV changes
- ✅ G20 BLOCKED | R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted | flat/min DSCR not promoted
- ✅ Backend remains source of truth