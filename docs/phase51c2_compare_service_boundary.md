# Phase 51C-2 — compare_service API boundary

## Base SHA

`26afe76c0d9f0c28494e58ca63ec323fb852361e` (origin/main @ PR #381 merge)

## Module

`app/services/compare_service.py`

## Public API

### `CompareRouteOutcome`

```python
@dataclass
class CompareRouteOutcome:
    """Result of POST /compare orchestration.

    The route in ``main_web.py`` translates this into a FastAPI response.
    """

    template_name: str
    context: dict
    status_code: int = 200
    headers: dict = field(default_factory=dict)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `template_name` | `str` | required | The Jinja2 template to render (e.g. `partials/comparison.html`, `partials/errors.html`). |
| `context` | `dict` | required | Template context dict (e.g. `{"project_type": ..., "scenarios": [...], "results": {...}}` on success; `{"errors": [...]}` on error). |
| `status_code` | `int` | `200` | HTTP status code. Always 200 for /compare in current code; reserved for future use. |
| `headers` | `dict` | `{}` | Optional response headers. Reserved for future use. |

### `CompareRouteDeps`

```python
@dataclass
class CompareRouteDeps:
    """Dependencies that ``execute_compare_route`` needs from the route.

    The route in ``main_web.py`` owns these helpers; passing them in as
    callables (rather than importing from ``main_web``) keeps the
    ``main_web`` -> ``compare_service`` import direction clean and lets
    future test code inject test doubles.
    """

    # Form / snapshot helpers
    collect_form_snapshot: Callable[[Any], dict]
    project_workspace_from_snapshot: Callable[[Any, dict], tuple]

    # Project / template normalization
    canonical_project_type: Callable[[Any], str]
    normalize_template_source: Callable[..., str]

    # Runtime guard + resolution (resolution is the key Bug B fix)
    check_runtime_allowed: Callable[..., tuple]
    resolve_runtime_snapshot_source: Callable[..., tuple]

    # Schema / input adapters
    build_schema_from_form: Callable[..., Any]
    build_projectinputs: Callable[..., Any]
    build_projectinputs_from_snapshot: Callable[..., Any]

    # Scenarios / project types (moved out of main_web globals for the
    # /compare service so it has no implicit module-scope dependencies).
    scenarios: list[str]
    project_types: list[str]

    # Snapshot error class (used for narrow except in user_created path)
    snapshot_input_error: type

    # Model execution
    run_project: Callable[..., dict]
```

#### Dependency contract

| Dep | Main_web symbol | Signature (input → output) | Notes |
|---|---|---|---|
| `collect_form_snapshot` | `_collect_form_snapshot` | `(form) -> dict` | Wraps `_collect_form_snapshot(form)`. |
| `project_workspace_from_snapshot` | `_project_workspace_from_snapshot` | `(user, snapshot) -> (project_record, workspace_state)` | Mirrors `_project_workspace_from_snapshot`. |
| `canonical_project_type` | `_canonical_project_type` | `(project_type) -> str` | Returns `"Solar"` / `"Wind"`. |
| `normalize_template_source` | `_normalize_template_source` | `(template_source, project_type) -> str` | Returns `"tuho"` / `"oborovo"` / `"generic_solar"` / `"generic_wind"`. |
| `check_runtime_allowed` | `check_runtime_allowed` (imported from `scenario_state_service`) | `(workspace_state, snapshot) -> (allow: bool, runtime_origin: str, guard_message: str)` | |
| `resolve_runtime_snapshot_source` | `_resolve_runtime_snapshot_source` | `(user, project_record, workspace_state, runtime_origin) -> (snapshot, scenario_record, warning, effective_runtime_origin)` | **Critical for Bug A + Bug B fixes**. |
| `build_schema_from_form` | `_build_schema_from_form` | `(project_type, scenario, capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur, opex_y1_keur, gearing_pct, target_dscr, interest_rate_pct, tenor_years) -> ProjectInputsSchema` | Pydantic schema with 10 numeric fields. |
| `build_projectinputs` | `build_projectinputs` (imported from `app.input_adapter`) | `(schema) -> ProjectInputs` | Adapter for schema → ProjectInputs. |
| `build_projectinputs_from_snapshot` | `build_projectinputs_from_snapshot` (imported from `app.input_adapter`) | `(snapshot: dict) -> ProjectInputs` | Adapter for snapshot → ProjectInputs. May raise `SnapshotInputError` (passed as `snapshot_input_error` dep). |
| `scenarios` | `SCENARIOS` (constant) | `["Base", "Downside", "Upside"]` | |
| `project_types` | `PROJECT_TYPES` (constant) | `["Solar", "Wind"]` | |
| `snapshot_input_error` | `SnapshotInputError` (imported from `app.input_adapter`) | `type` | Exception class to catch narrowly on user_created path. |
| `run_project` | `run_project` (imported from `app.api.project_runner`) | `(project_key, scenario, project_inputs_override=...) -> dict` | Executes the model; returns dict with `kpis` etc. |

### `execute_compare_route(...)`

```python
async def execute_compare_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    deps: CompareRouteDeps,
) -> CompareRouteOutcome:
    """Execute the /compare orchestration and return a CompareRouteOutcome.
    ...
    """
```

#### Parameters

| Param | Type | Description |
|---|---|---|
| `request` | `Any` | A FastAPI `Request` (or any object exposing the standard interface). The service does not use it for anything other than passing through. |
| `form` | `Any` | An async form result (`await request.form()`). The service extracts form fields from this object. |
| `user` | `Any` | The authenticated user object (must have `user_id`). |
| `deps` | `CompareRouteDeps` | Bundle of dependencies from the route. See `CompareRouteDeps` table above. |

#### Return value

A `CompareRouteOutcome` dataclass. The route in `main_web.py`
translates this into a FastAPI response via
`templates.TemplateResponse(request, name=outcome.template_name, context=outcome.context, status_code=outcome.status_code)`.

#### Behavior

The service executes the following steps in order:

1. **Form parsing** — reads 10 form fields (project_type, capacity_mw,
   tariff_eur_mwh, p50_hours, total_capex_keur, opex_y1_keur,
   gearing_pct, target_dscr, interest_rate_pct, tenor_years).
2. **Snapshot + project/workspace resolution** —
   `deps.collect_form_snapshot(form)` → `deps.project_workspace_from_snapshot(user, snapshot)`.
3. **Runtime guard** — `deps.check_runtime_allowed(workspace_state, snapshot)`.
   On block: returns `CompareRouteOutcome(template_name="partials/errors.html", context={"errors": [guard_message]})`.
4. **Project type validation** — `effective_project_type` must be in
   `deps.project_types`. On invalid: returns errors.html with
   `"project_type must be one of {project_types}"`.
5. **Runtime snapshot resolution (BUG FIX B)** — if
   `runtime_origin == "saved_state" and workspace_state.active_scenario_id`
   OR `project_record.project_origin == "user_created"`, the service
   calls `deps.resolve_runtime_snapshot_source(user, project_record, workspace_state, runtime_origin)`
   to get a clean resolved snapshot, scenario record, warning, and
   effective runtime origin.
6. **Override construction** — two paths:
   - `user_created` (BUG FIX A: uses the resolved snapshot from step 5):
     `deps.build_projectinputs_from_snapshot(runtime_snapshot)`,
     catching `deps.snapshot_input_error` narrowly.
   - template-seeded (BUG FIX B: saved_state branch uses the resolved
     snapshot from step 5): `build_projectinputs_from_snapshot` if
     saved_state + active_scenario, else
     `build_schema_from_form(...)` + `build_projectinputs(schema)`.
     Catches `ValueError` and the bare `Exception` (preserved
     overly-broad except from legacy /compare).
7. **Project key resolution** — `runtime_project_key ∈ {"TUHO",
   "Oborovo", "Solar", "Wind"}` based on
   `deps.normalize_template_source(template_source, project_type)`.
8. **Model execution loop** — `for sc in deps.scenarios: deps.run_project(runtime_project_key, sc, project_inputs_override=override)`,
   capturing 6 KPIs per scenario. **Soft-error semantics:** on
   per-scenario exception, `results[sc] = {"error": str(e)}` and the
   loop continues.
9. **Template response** — returns
   `CompareRouteOutcome(template_name="partials/comparison.html", context={"project_type": effective_project_type, "scenarios": list(deps.scenarios), "results": results})`.

## Import direction

`main_web.py` → `app.services.compare_service` (one-way).
`app.services.compare_service` does NOT import `main_web` (would
create a circular dependency).

## Module location

```
Finco1/
  app/
    services/
      compare_service.py    # NEW (Phase 51C-2)
      run_service.py        # existing (Phase 51B)
      scenario_state_service.py  # existing (Phase 50C)
      export_service.py     # existing
      export_audit_service.py    # existing
```

## How to use the service from a route

```python
# main_web.py
from app.services.compare_service import CompareRouteDeps, execute_compare_route

@app.post("/compare")
async def compare(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    deps = CompareRouteDeps(
        collect_form_snapshot=_collect_form_snapshot,
        project_workspace_from_snapshot=_project_workspace_from_snapshot,
        canonical_project_type=_canonical_project_type,
        normalize_template_source=_normalize_template_source,
        check_runtime_allowed=check_runtime_allowed,
        resolve_runtime_snapshot_source=_resolve_runtime_snapshot_source,
        build_schema_from_form=_build_schema_from_form,
        build_projectinputs=build_projectinputs,
        build_projectinputs_from_snapshot=build_projectinputs_from_snapshot,
        scenarios=SCENARIOS,
        project_types=PROJECT_TYPES,
        snapshot_input_error=SnapshotInputError,
        run_project=run_project,
    )
    outcome = await execute_compare_route(
        request=request, form=form, user=user, deps=deps,
    )
    return templates.TemplateResponse(
        request=request,
        name=outcome.template_name,
        context=outcome.context,
        status_code=outcome.status_code,
    )
```

## How to use the service in tests (DI with test doubles)

```python
import pytest
from app.services.compare_service import (
    CompareRouteDeps, CompareRouteOutcome, execute_compare_route,
)

@pytest.mark.asyncio
async def test_compare_user_created_branch_does_not_raise_nameerror():
    # Build a CompareRouteDeps with controlled callables.
    deps = CompareRouteDeps(
        collect_form_snapshot=lambda f: {"scenario": "Base"},
        project_workspace_from_snapshot=lambda u, s: (
            SimpleNamespace(
                project_code="X", project_type="Solar",
                project_origin="user_created",
                template_source="generic_solar",
                source_project_template="generic_solar",
            ),
            SimpleNamespace(active_scenario_id=None, saved_snapshot=None),
        ),
        canonical_project_type=lambda t: "Solar",
        normalize_template_source=lambda ts, pt: "generic_solar",
        check_runtime_allowed=lambda ws, s: (True, "workspace_base", ""),
        # KEY: this is the function whose absence caused the NameError.
        resolve_runtime_snapshot_source=lambda u, p, w, o: (
            {"scenario": "Base", "project_type": "Solar"},
            None, None, o,
        ),
        build_schema_from_form=lambda *a, **kw: None,
        build_projectinputs=lambda schema: None,
        build_projectinputs_from_snapshot=lambda snap: "OVERRIDE",
        scenarios=["Base", "Downside", "Upside"],
        project_types=["Solar", "Wind"],
        snapshot_input_error=ValueError,
        run_project=lambda key, sc, project_inputs_override=None: {
            "kpis": {"project_irr": None, "equity_irr": None,
                      "min_dscr": None, "avg_dscr": None,
                      "total_revenue_keur": None, "total_ebitda_keur": None},
        },
    )
    form = SimpleNamespace(get=lambda k, d="": d)
    request = SimpleNamespace()
    user = SimpleNamespace(user_id=1)
    outcome = await execute_compare_route(
        request=request, form=form, user=user, deps=deps,
    )
    # If we reach here, the user_created branch did not raise NameError.
    assert outcome.template_name == "partials/comparison.html"
```

## Summary

| Item | Value |
|---|---|
| Module path | `app/services/compare_service.py` |
| Public dataclasses | `CompareRouteOutcome`, `CompareRouteDeps` |
| Public entry point | `execute_compare_route(...)` (async) |
| Required deps | 13 (see table above) |
| Bug fixes included | Bug A (user_created NameError), Bug B (saved_state resolved snapshot) |
| Read-only invariant | Preserved (no persistence side effects) |
| Import direction | `main_web` → `compare_service` (one-way) |
| Test doubles | Injectable via `CompareRouteDeps` |
