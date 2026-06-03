# Phase 51L-2 — POST /scenarios/add vertical extraction

Phase 51L-2 extracts the orchestration body of
`POST /scenarios/add` from `main_web.py` into a new
route-orchestration service module:
`app/services/scenarios_add_service.py`. The route handler in
`main_web.py` is now a thin wrapper that handles auth, form
parsing, deps bundle construction, and the final response
translation (success → TemplateResponse; error path →
JSONResponse; auth → RedirectResponse).

## What moved to `scenarios_add_service.py`

The full orchestration body that previously lived inline in
`add_scenario_endpoint` in `main_web.py`:

- Form input read (Quirk 1): individual `form.get("project_code",
  "").strip()` and `form.get("scenario_name", "").strip()`
  calls.
- Validation: missing `project_code` → 400 JSON
  `{error: "project_code is required"}`; missing `scenario_name`
  → 400 JSON `{error: "scenario_name is required"}`.
- `get_project_record(user_id=user.user_id, project_code=project_code)`
  resolution.
- 404 early return: if `project_record is None` → 404 JSON
  `{error: "Project not found"}`.
- 403 early return: if `project_origin != "user_created"` → 403
  JSON `{error: "Add Scenario is only available for user-created projects"}`.
  (Quirk 8.)
- Base case lookup: list scenarios and find the one with
  `is_base_case=True`.
- Fallback: if no base_case but other scenarios exist, promote
  the oldest via
  `_get_least_created_scenario_for_project` +
  `promote_scenario_to_base_case`. (Quirk 4.)
- `add_scenario(...)` call with:
  - `user_id=user.user_id`
  - `project_id=project_record.project_id`
  - `project_code=project_record.project_code`
  - `scenario_name=scenario_name` (from form)
  - `parent_scenario_id=base_case.scenario_id`
  - `base_input_set=base_case.snapshot or base_case.base_input_set or {}`
    (Quirk 9)
  - `overrides={}` (Quirk 7)
  - `governance_state={}` (Quirk 6)
  - `replay_metadata={"action": "add_scenario", "parent_scenario_id": base_case.scenario_id, "project_code": project_code}`
    (Quirk 5)
- 500 early return: if `new_scenario is None` → 500 JSON
  `{error: "Failed to create scenario"}`.
- Re-read scenarios (with `limit=12`) and workspace_state for
  the render context. (Quirk 10.)
- Build template context via
  `_build_scenario_tab_context(user, project_record, scenarios, ws)`.
- Return the success render with HX-Trigger header
  (`HX-Trigger: scenarioAdded`, Quirk 2) and template
  `partials/scenario_tab.html` (Quirk 3).

## What stayed in `main_web.py`

- The `@app.post("/scenarios/add")` decorator and the
  `add_scenario_endpoint` function signature.
- The `get_current_user(request)` auth check (302 redirect to
  `/login` if unauth).
- Local import of the service module (one-way import direction).
- Construction of the `ScenariosAddRouteDeps` instance with the
  7 callables from main_web module scope.
- `await request.form()` form parsing.
- Translation of the result: if the result has a `payload`, it's
  an error path → JSONResponse; otherwise it's a success →
  `templates.TemplateResponse(...)`.

## Why `scenario_state_service.py` was NOT extended

`scenario_state_service.py` is data-layer only. It does not take
`Request`, `form`, or auth arguments. Adding route orchestration
would mix data-layer and route-orchestration concerns.

## Why `scenario_state_route_service.py` was NOT reused

`scenario_state_route_service.py` handles workspace draft/discard
mutations WITHOUT scenario row creation. `/scenarios/add` calls
`add_scenario` (which creates a new ScenarioRecord); this is a
different concern.

## Why `scenarios_save_service.py` was NOT reused

`scenarios_save_service.py` is for `/scenarios/save` (creates a
new ScenarioRecord from form snapshot). `/scenarios/add` creates
a new non-base scenario with parent inheritance from the base
case. Different concern (no form snapshot, no save_scenario
call).

## Why `scenario_duplicate_service.py` was NOT reused

`scenario_duplicate_service.py` is for
`/scenarios/{scenario_id}/duplicate` (copies an existing
ScenarioRecord). `/scenarios/add` creates a new non-base
scenario. Different concern.

## Final POST /scenarios/add route size

| Phase | Non-blank lines | Total lines |
|---|---|---|
| 51L-1 (pre-extraction) | 62 | 72 |
| **51L-2 (post-extraction)** | **49** | **54** |

The route shrank by **13 non-blank lines (~21% reduction)**.

## `ScenariosAddRouteOutcome` API

```python
@dataclass
class ScenariosAddRouteOutcome:
    template_name: str = "partials/scenario_tab.html"
    context: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    is_redirect: bool = False
    redirect_url: Optional[str] = None
```

The service returns the outcome for error paths (4xx/5xx with
`status_code` + `payload`) and returns nothing (the route
constructs the `TemplateResponse` directly) on success... actually
the service returns the outcome for both success AND error paths:
- Success: `template_name="partials/scenario_tab.html"`,
  `context={...}`, `status_code=200`,
  `headers={"HX-Trigger": "scenarioAdded"}`, no `payload`.
- Error: `payload={...}`, `status_code=4xx/5xx`, no `template_name`.

The route translates both cases to a `TemplateResponse` (success)
or `JSONResponse` (error).

## `ScenariosAddRouteDeps` API

```python
@dataclass
class ScenariosAddRouteDeps:
    # Project resolution
    get_project_record: Callable[..., Any]

    # Scenario lookup / base case management
    list_scenarios: Callable[..., Any]
    get_least_created_scenario_for_project: Callable[..., Any]
    promote_scenario_to_base_case: Callable[..., Any]

    # Persistence (intended write)
    add_scenario: Callable[..., Any]

    # Workspace state resolution
    get_workspace_state: Callable[..., Any]

    # Render context assembly
    build_scenario_tab_context: Callable[..., Any]
```

**7 callables**. No constants — the route reads individual form
fields (Quirk 1), so there is no form-schema constant to pass.

## Service entry point

```python
async def execute_scenarios_add_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    deps: ScenariosAddRouteDeps,
) -> ScenariosAddRouteOutcome:
    ...
```

All parameters are **keyword-only** (canonical Phase 51 pattern).
The function is **async**.

## Behavior preservation checklist (15 behaviors + 10 quirks)

- [x] Auth: unauth → 302 redirect to `/login` (route-owned)
- [x] `await request.form()` (route-owned)
- [x] `get_current_user(request)` is the auth check
- [x] `project_code = form.get("project_code", "").strip()`
- [x] `scenario_name = form.get("scenario_name", "").strip()`
- [x] Validation: missing `project_code` → 400 JSON
- [x] Validation: missing `scenario_name` → 400 JSON
- [x] `get_project_record(user_id=user.user_id, project_code=project_code)`
- [x] 404 early return: project not found
- [x] 403 early return: non-`user_created` project
- [x] `list_scenarios` for base case lookup
- [x] Fallback: promote oldest to base case (Quirk 4)
- [x] `add_scenario(...)` called once per success
- [x] 500 early return: `add_scenario` failure
- [x] Re-read scenarios for render (Quirk 10)
- [x] `get_workspace_state` for render
- [x] `build_scenario_tab_context(...)` for context
- [x] Success: `templates.TemplateResponse(name="partials/scenario_tab.html", ...)` with HX-Trigger
- [x] No broad `except Exception:` in route
- [x] No `HX-Trigger` on error paths

## 10 quirks preservation checklist

| # | Quirk | Preserved |
|---|---|---|
| 1 | Form input via individual `form.get()` calls | ✓ |
| 2 | `HX-Trigger: scenarioAdded` on success | ✓ |
| 3 | Partial template render (`partials/scenario_tab.html`) | ✓ |
| 4 | Fallback: promote oldest scenario to base case | ✓ |
| 5 | `replay_metadata` uses `action="add_scenario"`, NOT `export_type` | ✓ |
| 6 | `governance_state={}` (empty dict) | ✓ |
| 7 | `overrides={}` (empty dict) | ✓ |
| 8 | Only `user_created` projects can add scenarios (403) | ✓ |
| 9 | `base_input_set` fallback chain: `snapshot → base_input_set → {}` | ✓ |
| 10 | Re-read scenarios list after add (with `limit=12`) | ✓ |

## Intended side-effect confirmation

| Side effect | Per success | Per 400 | Per 404 | Per 403 | Per 500 |
|---|---|---|---|---|---|
| `get_project_record` | 1 | 1 | 1 | 1 | 1 |
| `list_scenarios` (base case) | 1 | 0 | 0 | 0 | 1 |
| `get_least_created_scenario_for_project` | 0 or 1 | 0 | 0 | 0 | 0 or 1 |
| `promote_scenario_to_base_case` | 0 or 1 | 0 | 0 | 0 | 0 or 1 |
| `add_scenario` | 1 | 0 | 0 | 0 | 1 |
| `list_scenarios` (render) | 1 | 0 | 0 | 0 | 0 |
| `get_workspace_state` | 1 | 0 | 0 | 0 | 0 |
| `build_scenario_tab_context` | 1 | 0 | 0 | 0 | 0 |
| `JSONResponse` (error) | 0 | 1 | 1 | 1 | 1 |
| `TemplateResponse` (success) | 1 | 0 | 0 | 0 | 0 |

## Forbidden side-effect confirmation

The following helpers are NOT called in the service:
- `record_export` family
- `update_scenario_last_run_summary`
- `save_run` / `save_project` / `run_project`
- `build_*_export` family
- `db.add` / `db.commit` / `db.flush` (direct)
- `session.add` / `session.commit` (direct)
- `_validate_form` (Quirk 1)
- `_collect_form_snapshot` (Quirk 1)

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS (no change) |
| Parity-core lock (4 SHA-256 files) | ✓ PASS (no change) |
| No-service-imports-main_web/main_api | ✓ PASS (12 services clean) |

## Tests run and results

| Test module | Tests | Pass |
|---|---|---|
| `test_phase51l1_scenario_add_route_golden_characterization.py` | 86 | 86 |
| `test_phase51l2_scenarios_add_route_vertical_extraction.py` | 42 | 42 |
| `test_phase51i_route_extraction_checkpoint_hotspot_map.py` | 63 | 63 |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 |

**212 new tests** (L1 re-pointed + L2 new). 12 service modules
verified clean (no main_web or main_api imports).

## Known failures

Pre-existing out-of-scope failures (UNCHANGED by this phase):
- `tests/test_persistence.py`: `ImportError: No module named 'persistence'`.
- `tests/test_repository.py`: `ImportError: No module named 'persistence'`.

## Recommended next phase

**Phase 51M-1** — `/projects/create` golden characterization
(117 non-blank, HIGH risk, largest remaining inline route).
