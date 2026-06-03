# Phase 51Q-1 — POST /scenarios/{scenario_id}/archive route golden characterization

> **Phase 51Q-1** — golden characterization (Agent A).
> Pins current behavior of `POST /scenarios/{scenario_id}/archive`
> (`archive_scenario_endpoint`) in `main_web.py` BEFORE the future
> 51Q-2 vertical extraction.

## Summary

- **Path:** `POST /scenarios/{scenario_id}/archive`
- **Handler:** `archive_scenario_endpoint`
- **Location:** `main_web.py` (route body, 47 non-blank lines)
- **Risk:** MEDIUM

## Behavior summary

### 1. Route existence
- `POST /scenarios/{scenario_id}/archive` exists in main_web.py.
- Handler `archive_scenario_endpoint(request: Request, scenario_id: str)`.

### 2. Auth/session behavior
- Auth check via `get_current_user(request)`.
- Unauthenticated → 302 redirect to `/login`.

### 3. Path parameter behavior
- `scenario_id: str` is the path parameter.

### 4. Scenario lookup
- `get_scenario(scenario_id, user.user_id)` (positional).
- If `record is None` → 404 JSONResponse `"Scenario not found"`.

### 5. Archive side effect
- `archive_scenario(user.user_id, scenario_id)` (no third arg).

### 6. Workspace re-render
After archive, the route re-renders the entire scenario workspace:
- `get_project_by_code(user.user_id, record.project_code)`
- `list_scenarios(user.user_id, project_id=record.project_id, include_archived=False, limit=12)`
- `get_scenario_history(user.user_id, project_id=record.project_id, limit=20)`
- `list_exports(user.user_id, project_id=record.project_id, limit=8)`
- `build_export_lineage(user.user_id, project_id=record.project_id, limit=8)`
- `get_workspace_state(user.user_id, record.project_id)`
- `scenario_summary_cards` built by iterating `scenarios` and aggregating
  `export_count` from `export_lineage`.

### 7. Response behavior
- Success → `_render_scenario_workspace(...)` with `message=f"Archived {record.scenario_name}."`
- 404 → JSONResponse

### 8. Forbidden side effects (all absent)
- `record_export` family
- `save_run`, `run_project`, model execution
- Excel export builders
- `add_scenario`, `rename_scenario`, `create_scenario` (this is archive, not add/rename)
- Direct `db.add`/`db.commit`/`db.flush`, `session.add`/`session.commit`

### 9. Intended persistence side effects

| Side effect | Count | Notes |
|---|---|---|
| `get_scenario` | 1 | Scenario lookup |
| `archive_scenario` | 1 | Soft-archive write |

### 10. Behavior quirks (10)

1. SOFT archive (no delete; `archive_scenario` is the call).
2. After archive, the entire workspace is re-rendered.
3. `list_scenarios` called with `include_archived=False` (archived scenario won't show).
4. `scenario_summary_cards` built by iterating scenarios.
5. `export_count` aggregated from `export_lineage`.
6. Success message uses `record.scenario_name`.
7. No HTMX-specific headers.
8. No form input is read (archive takes no body).
9. Positional `get_scenario(scenario_id, user.user_id)`.
10. `archive_scenario(user.user_id, scenario_id)` — no name arg.

### 11. Recommended 51Q-2 extraction boundary

**New module:** `app/services/scenario_archive_service.py`

**Public dataclasses:**

- `@dataclass class ScenarioArchiveRouteOutcome` (status_code, payload, rendered_response)
- `@dataclass class ScenarioArchiveRouteDeps` (~9 callables: get_scenario, archive_scenario, get_project_by_code, list_scenarios, get_scenario_history, list_exports, build_export_lineage, get_workspace_state, render_scenario_workspace)
- `async def execute_scenario_archive_route(*, request, scenario_id, user, deps)`

**Expected route thinned:** 47 → ~30 non-blank (~-36%).

## Phase 51F guardrail status

- Engine-output golden: unchanged
- Parity-core lock: unchanged
- No-service-imports: N/A (no service yet)

## Tests

- 53 tests in `tests/test_phase51q1_scenario_archive_route_golden_characterization.py`
- All passed in 51Q-1 development

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51Q-1.**

## Recommendation

**Ready for 51Q-2 extraction.** Characterization complete. No
ambiguous behavior.
