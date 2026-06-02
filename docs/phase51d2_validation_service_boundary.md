# Phase 51D-2 — validation_service API boundary

## Base SHA

`ca194114b0482308e45bba6bb1415da1df5d3ad3` (origin/main @ PR #383 merge,
Phase 51D-1 /validate golden characterization)

## Module

`app/services/validation_service.py`

## Public API

### `ValidateRouteOutcome`

```python
@dataclass
class ValidateRouteOutcome:
    """Result of POST /validate orchestration.

    The route in ``main_web.py`` translates this into a FastAPI response.
    """

    template_name: str
    context: dict
    status_code: int = 200
    headers: dict = field(default_factory=dict)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `template_name` | `str` | required | The Jinja2 template to render (e.g. `partials/validation.html`, `partials/errors.html`). |
| `context` | `dict` | required | Template context dict (e.g. `{"valid": True, "errors": [], "form_data": {...}}` on success; `{"errors": [...]}` on error). |
| `status_code` | `int` | `200` | HTTP status code. Always 200 for /validate in current code; reserved for future use. |
| `headers` | `dict` | `{}` | Optional response headers. Reserved for future use. |

### `ValidateRouteDeps`

```python
@dataclass
class ValidateRouteDeps:
    """Dependencies that ``execute_validate_route`` needs from the route.

    The route in ``main_web.py`` owns these helpers; passing them in as
    callables (rather than importing from ``main_web``) keeps the
    ``main_web`` -> ``validation_service`` import direction clean and lets
    future test code inject test doubles.
    """

    # Form / snapshot helpers (used)
    collect_form_snapshot: Callable[[Any], dict]
    project_workspace_from_snapshot: Callable[[Any, dict], tuple]

    # Project / template normalization (parity with compare_service;
    # NOT used by /validate today)
    canonical_project_type: Callable[[Any], str]
    normalize_template_source: Callable[..., str]

    # Runtime guard + resolution (parity call IS used)
    check_runtime_allowed: Callable[..., tuple]
    resolve_runtime_snapshot_source: Callable[..., tuple]

    # Schema / input adapters (used)
    build_schema_from_form: Callable[..., Any]
    validate_numeric_field: Callable[..., tuple]

    # Constants (moved out of main_web globals)
    project_types: list[str]
    scenarios: list[str]

    # Snapshot error class (parity with compare_service; NOT used by
    # /validate today)
    snapshot_input_error: type
```

#### Dependency contract

| Dep | Main_web symbol | Signature (input → output) | Notes |
|---|---|---|---|
| `collect_form_snapshot` | `_collect_form_snapshot` | `(form) -> dict` | Wraps `_collect_form_snapshot(form)`. |
| `project_workspace_from_snapshot` | `_project_workspace_from_snapshot` | `(user, snapshot) -> (project_record, workspace_state)` | Mirrors `_project_workspace_from_snapshot`. |
| `canonical_project_type` | `_canonical_project_type` | `(project_type) -> str` | Returns `"Solar"` / `"Wind"`. **NOT used by /validate today; kept for parity with `compare_service`.** |
| `normalize_template_source` | `_normalize_template_source` | `(template_source, project_type) -> str` | Returns `"tuho"` / `"oborovo"` / `"generic_solar"` / `"generic_wind"`. **NOT used by /validate today; kept for parity.** |
| `check_runtime_allowed` | `check_runtime_allowed` (imported from `scenario_state_service`) | `(workspace_state, snapshot) -> (allow: bool, runtime_origin: str, guard_message: str)` | |
| `resolve_runtime_snapshot_source` | `_resolve_runtime_snapshot_source` | `(user, project_record, workspace_state, runtime_origin) -> (snapshot, scenario_record, warning, effective_runtime_origin)` | **Parity call: the service calls this when (saved_state + active_scenario_id) OR (user_created), captures only the first tuple element, discards the rest. The captured snapshot is NOT used downstream.** |
| `build_schema_from_form` | `_build_schema_from_form` | `(project_type, scenario, 10 numeric fields) -> ProjectInputsSchema` | Pydantic schema. Used in Stage C. |
| `validate_numeric_field` | `_validate_numeric_field` | `(name, val, max_val) -> (value, error_message)` | Per-field helper, NOT whole-form. Used in Stage B. Returns `(None, None)` for empty input. |
| `project_types` | `PROJECT_TYPES` (constant) | `["Solar", "Wind"]` | Used in Stage A. |
| `scenarios` | `SCENARIOS` (constant) | `["Base", "Downside", "Upside"]` | Used in Stage A. |
| `snapshot_input_error` | `SnapshotInputError` (imported from `app.input_adapter`) | `type` | **NOT used by /validate today; kept for parity with `compare_service`.** |

### `execute_validate_route(...)`

```python
async def execute_validate_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    deps: ValidateRouteDeps,
) -> ValidateRouteOutcome:
    """Execute the /validate orchestration and return a ValidateRouteOutcome.
    ...
    """
```

#### Parameters

| Param | Type | Description |
|---|---|---|
| `request` | `Any` | A FastAPI `Request` (or any object exposing the standard interface). The service does not use it for anything other than passing through. |
| `form` | `Any` | An async form result (`await request.form()`). The service extracts form fields from this object. |
| `user` | `Any` | The authenticated user object (must have `user_id`). |
| `deps` | `ValidateRouteDeps` | Bundle of dependencies from the route. See `ValidateRouteDeps` table above. |

#### Return value

A `ValidateRouteOutcome` dataclass. The route in `main_web.py`
translates this into a FastAPI response via
`templates.TemplateResponse(request, name=outcome.template_name, context=outcome.context, status_code=outcome.status_code)`.

#### Behavior

The service executes the following steps in order:

1. **Form parsing** — reads 12 form fields (project_type, scenario,
   capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur,
   opex_y1_keur, gearing_pct, target_dscr, interest_rate_pct,
   tenor_years).
2. **Snapshot + project/workspace resolution** —
   `deps.collect_form_snapshot(form)` →
   `deps.project_workspace_from_snapshot(user, snapshot)`.
3. **Runtime guard** — `deps.check_runtime_allowed(workspace_state, snapshot)`.
   On block: returns `ValidateRouteOutcome(template_name="partials/errors.html", context={"errors": [guard_message]})`.
4. **Runtime snapshot resolution (PARITY CALL)** — if
   `runtime_origin == "saved_state" and workspace_state.active_scenario_id`
   OR `project_record.project_origin == "user_created"`, the service
   calls `deps.resolve_runtime_snapshot_source(user, project_record, workspace_state, runtime_origin)`
   and captures only the first tuple element as `runtime_snapshot`
   (the rest discarded). **The captured snapshot is intentionally
   unused downstream** — this is the Phase 51D-1 parity quirk
   preserved EXACTLY.
5. **Stage A: enum validation** —
   `project_type in deps.project_types` AND
   `scenario in deps.scenarios`. Errors accumulate (no
   short-circuit).
6. **Stage B: numeric field validation** — for each of 9 numeric
   fields in the pinned max-value list, call
   `deps.validate_numeric_field(name, val, max_val)`. Empty field
   passes (returns `(None, None)`).
7. **Stage C: schema build validation (gated by `if not errors:`)** —
   only runs when Stage A and B have no errors. Calls
   `deps.build_schema_from_form(...)`. Catches `ValueError`
   specifically (NOT bare `Exception`); appends `str(ve)`.
8. **Template response** — returns
   `ValidateRouteOutcome(template_name="partials/validation.html", context={"valid": len(errors) == 0, "errors": errors, "form_data": {"project_type": project_type, "scenario": scenario}})`.

## Import direction

`main_web.py` → `app.services.validation_service` (one-way).
`app.services.validation_service` does NOT import `main_web` (would
create a circular dependency).

## Module location

```
Finco1/
  app/
    services/
      validation_service.py   # NEW (Phase 51D-2)
      compare_service.py      # existing (Phase 51C-2)
      run_service.py          # existing (Phase 51B)
      scenario_state_service.py   # existing (Phase 50C)
      export_service.py       # existing
      export_audit_service.py # existing
```

## How to use the service from a route

```python
# main_web.py
from app.services.validation_service import ValidateRouteDeps, execute_validate_route

@app.post("/validate")
async def validate(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    deps = ValidateRouteDeps(
        collect_form_snapshot=_collect_form_snapshot,
        project_workspace_from_snapshot=_project_workspace_from_snapshot,
        canonical_project_type=_canonical_project_type,
        normalize_template_source=_normalize_template_source,
        check_runtime_allowed=check_runtime_allowed,
        resolve_runtime_snapshot_source=_resolve_runtime_snapshot_source,
        build_schema_from_form=_build_schema_from_form,
        validate_numeric_field=_validate_numeric_field,
        project_types=PROJECT_TYPES,
        scenarios=SCENARIOS,
        snapshot_input_error=SnapshotInputError,
    )
    outcome = await execute_validate_route(
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
from app.services.validation_service import (
    ValidateRouteDeps, ValidateRouteOutcome, execute_validate_route,
)


def _validate_numeric_field(name, val, max_val):
    """Mirror main_web._validate_numeric_field for tests."""
    if not val or val.strip() == "":
        return None, None
    try:
        f = float(val)
        if f < 0:
            return None, f"{name} must be non-negative"
        if max_val is not None and f > max_val:
            return None, f"{name} must be <= {max_val}"
        return f, None
    except ValueError:
        return None, f"{name} must be a number"


@pytest.mark.asyncio
async def test_validate_stage_a_invalid_project_type():
    deps = ValidateRouteDeps(
        collect_form_snapshot=lambda f: {"scenario": "Base"},
        project_workspace_from_snapshot=lambda u, s: (
            SimpleNamespace(
                project_code="X", project_type="Solar",
                project_origin="factory",
                template_source="generic_solar",
                source_project_template="generic_solar",
            ),
            SimpleNamespace(active_scenario_id=None, saved_snapshot=None),
        ),
        canonical_project_type=lambda t: "Solar",
        normalize_template_source=lambda ts, pt: "generic_solar",
        check_runtime_allowed=lambda ws, s: (True, "workspace_base", ""),
        resolve_runtime_snapshot_source=lambda u, p, w, o: (None, None, None, o),
        build_schema_from_form=lambda *a, **kw: SimpleNamespace(),
        validate_numeric_field=_validate_numeric_field,
        project_types=["Solar", "Wind"],
        scenarios=["Base", "Downside", "Upside"],
        snapshot_input_error=ValueError,
    )
    form = SimpleNamespace(get=lambda k, d="": d)
    form.get = lambda k, d="": "Nuclear" if k == "project_type" else d
    request = SimpleNamespace()
    user = SimpleNamespace(user_id=1)
    outcome = await execute_validate_route(
        request=request, form=form, user=user, deps=deps,
    )
    assert outcome.template_name == "partials/validation.html"
    assert outcome.context["valid"] is False
    assert any("project_type must be one of" in e for e in outcome.context["errors"])
```

## Summary

| Item | Value |
|---|---|
| Module path | `app/services/validation_service.py` |
| Public dataclasses | `ValidateRouteOutcome`, `ValidateRouteDeps` |
| Public entry point | `execute_validate_route(...)` (async) |
| Required deps | 11 (see table above) |
| Allowed behavior changes | None (this is a behavior-preserving refactor) |
| Runtime-snapshot parity call | Preserved exactly (parity quirk from Phase 51D-1) |
| Stage A → B → C order | Preserved exactly |
| Numeric max values | Preserved exactly (9 fields) |
| Read-only invariant | Preserved (no persistence side effects) |
| Import direction | `main_web` → `validation_service` (one-way) |
| Test doubles | Injectable via `ValidateRouteDeps` |
