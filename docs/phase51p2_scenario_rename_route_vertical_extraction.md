# Phase 51P-2 — POST /scenarios/{scenario_id}/rename route vertical extraction

> **Phase 51P-2** — vertical extraction of the
> `/scenarios/{scenario_id}/rename` route family
> (single canonical POST route, handler
> `rename_scenario_endpoint`) into a new dedicated service module.

## Summary

**New module:** `app/services/scenario_rename_service.py`
(~8,750 bytes, 9 callables).

**Service API:**

```python
@dataclass
class ScenarioRenameRouteOutcome:
    """Result of POST /scenarios/{scenario_id}/rename orchestration.

    Two forms:
    - Error (status_code >= 400): JSONResponse(payload, status_code)
    - Success (status_code == 200): outcome.rendered_response (TemplateResponse)
    """
    status_code: int = 200
    payload: dict = field(default_factory=dict)
    rendered_response: Any = None

@dataclass
class ScenarioRenameRouteDeps:  # 9 callables
    get_scenario
    rename_scenario
    get_project_by_code
    list_scenarios
    get_scenario_history
    list_exports
    build_export_lineage
    get_workspace_state
    render_scenario_workspace

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

## Route thinned

| Metric | Pre-P-2 (P-1) | Post-P-2 (51P-2) | Delta |
|---|---|---|---|
| `/scenarios/{id}/rename` total lines | 55 | 75 | +20 (+36%) |
| `/scenarios/{id}/rename` non-blank | 51 | 69 | +18 (+35%) |

> **Note:** The route did NOT shrink significantly because the
> extraction kept the inline `_render_with_summary_cards` wrapper
> in the route (which builds the `scenario_summary_cards` list
> from `scenarios` + `export_lineage`). The **orchestration body**
> (the scenario lookup, gate, rename call, project/scenario/history
> /exports/lineage lookups, workspace state lookup, render call)
> has moved to the service.

## Behaviors preserved (12, from Phase 51P-1)

1. POST /scenarios/{scenario_id}/rename exists.
2. Auth check via `get_current_user(request)`.
3. Unauthenticated → 302 redirect to `/login`.
4. Path parameter `scenario_id`.
5. Form input: `scenario_name` (string, stripped by route).
6. Empty `scenario_name` → 400 JSONResponse.
7. Scenario lookup: `get_scenario(scenario_id, user.user_id)` (positional).
8. Scenario not found → 404 JSONResponse.
9. Rename side effect: `rename_scenario(user.user_id, scenario_id, new_name)`.
10. Workspace re-render (full, not partial).
11. Response via `_render_scenario_workspace(...)` with success message.
12. No HTMX-specific headers.

## Quirks preserved (10, from Phase 51P-1)

1. Form read via `await request.form()` (in route).
2. After rename, the entire workspace is re-rendered.
3. `scenario_summary_cards` built by iterating scenarios (in route's `_render_with_summary_cards`).
4. `export_count` aggregated from `export_lineage`.
5. Success message includes the new scenario name.
6. No HTMX-specific headers.
7. Positional `get_scenario(scenario_id, user.user_id)`.
8. `list_scenarios(include_archived=False, limit=12)`.
9. `get_scenario_history(limit=20)`.
10. `list_exports` + `build_export_lineage` use `limit=8` (×2).

## Intended persistence side effects (preserved)

| Side effect | Count | Notes |
|---|---|---|
| `deps.get_scenario` | 1 | Scenario lookup |
| `deps.rename_scenario` | 1 | Rename write |
| `deps.get_project_by_code` | 1 | Project lookup |
| `deps.list_scenarios` | 1 | Scenarios list |
| `deps.get_scenario_history` | 1 | History list |
| `deps.list_exports` | 1 | Exports list |
| `deps.build_export_lineage` | 1 | Export lineage |
| `deps.get_workspace_state` | 1 | Workspace state |

## Forbidden side effects (absent)

- `record_export` family
- `save_run`, `run_project`, model execution
- Excel export builders
- `add_scenario`, `create_scenario` (this is rename, not add)
- Direct `db.add` / `db.commit` / `db.flush`, `session.add` / `session.commit`

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS |
| Parity-core lock (4 SHA-256 files) | ✓ PASS |
| No-service-imports-main_web/main_api | ✓ PASS |

The new `scenario_rename_service.py` module does NOT import
`main_web` or `main_api`. The 15-service inventory is clean.

## Tests

| Module | Tests | Pass | Notes |
|---|---|---|---|
| `test_phase51p2_scenario_rename_route_vertical_extraction.py` (new) | 43 | 43 | All passed |
| `test_phase51p1_scenario_rename_route_golden_characterization.py` (re-pointed) | 55 | 55 | All passed |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 | All passed |

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51P-2.**

## Why a separate service module

- `scenario_duplicate_service.py` is for `/scenarios/{id}/duplicate`.
  Different concern (creates a copy, not a rename).
- `scenarios_save_service.py` is for `/scenarios/save`. Different
  concern (creates a new scenario from form snapshot).
- `scenarios_add_service.py` is for `/scenarios/add`. Different
  concern (adds scenario with parent inheritance).

The new `scenario_rename_service.py` is the right place for the
scenario rename + workspace re-render orchestration.

## Recommendation

**Ready for merge.** Behavior preserved exactly. No production
code changes outside the route + new service. No forbidden side
effects. All 10 quirks preserved. All 55+43+21=119 tests pass.
Phase 51F guardrails remain green.
