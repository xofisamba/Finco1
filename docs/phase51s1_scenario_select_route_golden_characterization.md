# Phase 51S-1 — POST /scenarios/{scenario_id}/select route golden characterization

## Summary

- **Path:** `POST /scenarios/{scenario_id}/select`
- **Handler:** `select_scenario_endpoint`
- **Location:** `main_web.py` (route body, 21 non-blank lines)
- **Risk:** MEDIUM/LOW

## Behavior summary

### 1. Route existence
- `POST /scenarios/{scenario_id}/select` exists.
- Handler `select_scenario_endpoint(request: Request, scenario_id: str)`.

### 2. Auth/session
- Auth check via `get_current_user(request)`.
- Unauthenticated → 302 redirect to `/login`.

### 3. Path parameter
- `scenario_id: str` is the path parameter.

### 4. Scenario lookup
- `get_scenario(scenario_id, user.user_id)` (positional).
- 404 if not found.

### 5. select_scenario call
- `select_scenario(user.user_id, record.project_id, scenario_id)` — Quirk 1: takes `project_id` second.
- Returns bool (Quirk 2).
- 500 if returns False (Quirk 3).

### 6. Response behavior
- `templates.TemplateResponse(name="partials/scenario_tab.html", context=...)`.
- Uses `_build_scenario_tab_context` (NOT `_render_scenario_workspace`).

### 7. HTMX headers
- `HX-Trigger: f"scenarioSelected:{{\"scenario_id\": \"{scenario_id}\"}}"` — Quirk 5: JSON in header.
- No HX-Redirect.

### 8. Workspace state lookup
- `get_workspace_state`, `get_project_record`, `list_scenarios` (all for the re-render).

### 9. Forbidden side effects (absent)
- `record_export` family, `save_run`, `run_project`, export builders
- `add_scenario`, `rename_scenario`, `archive_scenario`, `update_scenario_overrides`, `create_scenario`
- Direct `db.add`/`db.commit`/`db.flush`, `session.add`/`session.commit`

### 10. Intended persistence side effects

| Side effect | Count | Notes |
|---|---|---|
| `get_scenario` | 1 | Scenario lookup |
| `select_scenario` | 1 | Active scenario write |
| `get_workspace_state` | 1 | Workspace state |
| `get_project_record` | 1 | Project lookup |
| `list_scenarios` | 1 | Scenarios list |

### 11. Behavior quirks (10)

1. `select_scenario(user_id, project_id, scenario_id)` — `project_id` second.
2. Returns bool (not the record).
3. 500 if returns False.
4. Partial template: `partials/scenario_tab.html`.
5. HX-Trigger `scenarioSelected:{"scenario_id": "..."}` (JSON in header).
6. Uses `_build_scenario_tab_context` (NOT `_render_scenario_workspace`).
7. No HX-Redirect.
8. Positional `get_scenario(scenario_id, user.user_id)`.
9. Keyword `get_project_record(user_id=..., project_code=...)`.
10. No form input, no JSON body.

### 12. Recommended 51S-2 extraction boundary

**New module:** `app/services/scenario_select_service.py`

**Public dataclasses:**
- `@dataclass class ScenarioSelectRouteOutcome` (template_name, context, payload, status_code, headers)
- `@dataclass class ScenarioSelectRouteDeps` (~6 callables)
- `async def execute_scenario_select_route(*, request, scenario_id, user, deps)`

**Expected route thinned:** 21 → ~15 non-blank.

## Tests

- 54 tests in `tests/test_phase51s1_scenario_select_route_golden_characterization.py`
- All passed

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4` — NOT touched

## Recommendation

**Ready for 51S-2 extraction.** No ambiguous behavior.
