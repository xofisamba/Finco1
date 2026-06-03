# Phase 51R-1 — POST /scenarios/{scenario_id}/update-overrides route golden characterization

> **Phase 51R-1** — golden characterization (Agent A). This is the
> most state-sensitive remaining scenario route.

## Summary

- **Path:** `POST /scenarios/{scenario_id}/update-overrides`
- **Handler:** `update_overrides_endpoint`
- **Location:** `main_web.py` (route body, 25 non-blank lines)
- **Risk:** MEDIUM/state-sensitive

## Behavior summary

### 1. Route existence
- `POST /scenarios/{scenario_id}/update-overrides` exists in main_web.py.
- Handler `update_overrides_endpoint(request: Request, scenario_id: str)`.

### 2. Auth/session behavior
- Auth check via `get_current_user(request)`.
- Unauthenticated → 302 redirect to `/login`.

### 3. Path parameter behavior
- `scenario_id: str` is the path parameter.

### 4. JSON body input
- Body read via `await request.json()` (NOT `await request.form()`).
- `overrides = body if isinstance(body, dict) else {}` (Quirk 2: typecheck).

### 5. Scenario lookup and gates
- `get_scenario(scenario_id, user.user_id)` (positional).
- 404 if not found.
- **400 if `record.is_base_case`** (Quirk 3: cannot override Base Case).

### 6. update_scenario_overrides call
- `update_scenario_overrides(user.user_id, scenario_id, overrides)`.
- 500 if returns None (Quirk 4).

### 7. Response behavior
- `templates.TemplateResponse(name="partials/scenario_tab.html", context=..., headers={"HX-Trigger": "overridesUpdated"})`.
- Uses `_build_scenario_tab_context` (NOT `_render_scenario_workspace`).

### 8. HTMX headers
- `HX-Trigger: "overridesUpdated"` (unique to this route).
- No HX-Redirect.

### 9. Forbidden side effects (all absent)
- `record_export` family, `save_run`, `run_project`, export builders
- `add_scenario`, `rename_scenario`, `archive_scenario`, `create_scenario`
- Direct `db.add`/`db.commit`/`db.flush`, `session.add`/`session.commit`

### 10. Intended persistence side effects

| Side effect | Count | Notes |
|---|---|---|
| `get_scenario` | 1 | Scenario lookup |
| `update_scenario_overrides` | 1 | Override write |
| `get_project_record` | 1 | Project lookup |
| `get_workspace_state` | 1 | Workspace state |
| `list_scenarios` | 1 | Scenarios list |

### 11. Behavior quirks (10)

1. Body is JSON (not form).
2. `overrides = body if isinstance(body, dict) else {}` (typecheck).
3. 400 if `record.is_base_case`.
4. 500 if `update_scenario_overrides` returns None.
5. Partial template: `partials/scenario_tab.html` (NOT full workspace).
6. HX-Trigger `"overridesUpdated"` (unique to this route).
7. No HX-Redirect.
8. Uses `_build_scenario_tab_context` (NOT `_render_scenario_workspace`).
9. Positional `get_scenario(scenario_id, user.user_id)`.
10. Keyword `get_project_record(user_id=..., project_code=...)`.

### 12. Recommended 51R-2 extraction boundary

**New module:** `app/services/scenario_update_overrides_service.py`

**Public dataclasses:**

- `@dataclass class ScenarioUpdateOverridesRouteOutcome` (template_name, context, payload, status_code, headers)
- `@dataclass class ScenarioUpdateOverridesRouteDeps` (~6 callables: get_scenario, update_scenario_overrides, get_project_record, get_workspace_state, list_scenarios, _build_scenario_tab_context)
- `async def execute_scenario_update_overrides_route(*, request, scenario_id, overrides, user, deps)`

**Expected route thinned:** 25 → ~15 non-blank.

## Phase 51F guardrail status

- Engine-output golden: unchanged
- Parity-core lock: unchanged
- No-service-imports: N/A (no service yet)

## Tests

- 56 tests in `tests/test_phase51r1_scenario_update_overrides_route_golden_characterization.py`
- All passed in 51R-1 development

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51R-1.**

## Recommendation

**Ready for 51R-2 extraction.** No ambiguous behavior. The
is_base_case gate and 500-on-None failure path are clear.
