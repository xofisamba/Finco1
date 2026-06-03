# Phase 51P-1 — POST /scenarios/{scenario_id}/rename route golden characterization

> **Phase 51P-1** — golden characterization (Agent A).
> Pins current behavior of `POST /scenarios/{scenario_id}/rename`
> (`rename_scenario_endpoint`) in `main_web.py` BEFORE the future
> 51P-2 vertical extraction.

## Summary

- **Path:** `POST /scenarios/{scenario_id}/rename`
- **Handler:** `rename_scenario_endpoint`
- **Location:** `main_web.py` (route body, 51 non-blank lines)
- **Risk:** MEDIUM

## Behavior summary

### 1. Route existence
- `POST /scenarios/{scenario_id}/rename` exists in main_web.py.
- Handler `rename_scenario_endpoint(request: Request, scenario_id: str)`.

### 2. Auth/session behavior
- Auth check via `get_current_user(request)`.
- Unauthenticated → 302 redirect to `/login`.

### 3. Path parameter behavior
- `scenario_id: str` is the path parameter.

### 4. Form input
- Form read via `await request.form()`.
- `scenario_name` field, default `""`, stripped.
- Empty `scenario_name` → 400 JSONResponse `"Scenario name is required"`.

### 5. Scenario lookup
- `get_scenario(scenario_id, user.user_id)` (positional).
- If `record is None` → 404 JSONResponse `"Scenario not found"`.

### 6. Rename side effect
- `rename_scenario(user.user_id, scenario_id, new_name)`.

### 7. Workspace re-render
After rename, the route re-renders the entire scenario workspace:
- `get_project_by_code(user.user_id, record.project_code)`
- `list_scenarios(user.user_id, project_id=record.project_id, include_archived=False, limit=12)`
- `get_scenario_history(user.user_id, project_id=record.project_id, limit=20)`
- `list_exports(user.user_id, project_id=record.project_id, limit=8)`
- `build_export_lineage(user.user_id, project_id=record.project_id, limit=8)`
- `get_workspace_state(user.user_id, record.project_id)`
- `scenario_summary_cards` built by iterating `scenarios` and aggregating
  `export_count` from `export_lineage`.

### 8. Response behavior
- Success → `_render_scenario_workspace(...)` with `message=f"Renamed scenario to {new_name}."`
- 400 → JSONResponse
- 404 → JSONResponse

### 9. HTMX headers
- No `HX-Trigger`, no `HX-Redirect`.

### 10. Forbidden side effects (all absent)
- `record_export` family
- `save_run`, `run_project`, model execution
- Excel export builders
- `add_scenario`, `create_scenario` (this is rename, not add)
- Direct `db.add`/`db.commit`/`db.flush`, `session.add`/`session.commit`

### 11. Intended persistence side effects

| Side effect | Count | Notes |
|---|---|---|
| `get_scenario` | 1 | Scenario lookup |
| `rename_scenario` | 1 | Rename write |

### 12. Behavior quirks (10)

1. Form read via `await request.form()` (not FastAPI Form injection).
2. After rename, the entire workspace is re-rendered (not a partial).
3. `scenario_summary_cards` built by iterating scenarios.
4. `export_count` aggregated from `export_lineage`.
5. Success message includes the new scenario name.
6. No HTMX-specific headers.
7. Scenario lookup uses `get_scenario(scenario_id, user.user_id)` (positional).
8. `list_scenarios` called with `include_archived=False, limit=12`.
9. `get_scenario_history` called with `limit=20`.
10. `list_exports` and `build_export_lineage` called with `limit=8` (×2).

### 13. Recommended 51P-2 extraction boundary

**New module:** `app/services/scenario_rename_service.py`

**Public dataclasses:**

- `@dataclass class ScenarioRenameRouteOutcome`
  - `template_name: str` (the partial template for the workspace)
  - `context: dict` (workspace render context)
  - `status_code: int` (200 success, 400, 404)
  - plus standard fields

- `@dataclass class ScenarioRenameRouteDeps` (~10 callables)
  - `get_scenario`
  - `rename_scenario`
  - `get_project_by_code`
  - `list_scenarios`
  - `get_scenario_history`
  - `list_exports`
  - `build_export_lineage`
  - `get_workspace_state`
  - `build_scenario_summary_cards` (or `build_workspace_render_context` — combines summary_cards, exports, etc.)
  - `render_scenario_workspace` (returns TemplateResponse or dict)

**Service entry point:**

```python
async def execute_scenario_rename_route(
    *,
    request: Any,
    scenario_id: str,
    new_name: str,
    user: Any,
    deps: ScenarioRenameRouteDeps,
) -> ScenarioRenameRouteOutcome:
    ...
```

**Expected route thinned:** 51 → ~30 non-blank (~-40%).

## Phase 51F guardrail status

- Engine-output golden: unchanged
- Parity-core lock: unchanged
- No-service-imports: N/A (no service yet)

## Tests

- 55 tests in `tests/test_phase51p1_scenario_rename_route_golden_characterization.py`
- All passed in 51P-1 development

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51P-1.**

## Recommendation

**Ready for 51P-2 extraction.** Characterization complete. No
ambiguous behavior, no latent bugs.
