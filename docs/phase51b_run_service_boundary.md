# Phase 51B — run_service boundary

This document describes the boundary between the
`app/services/run_service.py` module and the `main_web.py` web layer
after the Phase 51B vertical extraction.

## Layering

```
HTTP layer         main_web.py        (FastAPI route, Jinja templates, cookies, CSRF)
  ↓ uses
Service layer      app/services/run_service.py
                   app/services/scenario_state_service.py
                   app/services/export_service.py
                   app/services/export_audit_service.py
  ↓ uses
Domain layer       app/api/project_runner.py (run_project)
                   app/persistence/repository.py (record_workspace_runtime, …)
                   app/waterfall_core.py  (NOT touched by Phase 51B)
```

`run_service` is a thin orchestration layer. It does not implement
financial math; it does not write to the database directly; it does
not render templates. It coordinates calls to the domain layer and
returns a plain dataclass describing what the HTTP layer should
render.

## What `run_service` owns

* Three execution paths: user_created, template-seeded (tuho/oborovo),
  generic wind/solar fallback.
* Per-path orchestration: which inputs to use, which model to call,
  which persistence side effects to fire.
* sessionStorage save script construction (the script that gets
  prepended to the `runtime_summary.html` response so the front-end
  state stays in sync).
* Replay metadata construction for the persistence layer.

## What `run_service` does NOT own

* HTTP concerns (Request, Response, status codes, cookies, CSRF).
* Template rendering (`templates.TemplateResponse(...)`).
* `HTMLResponse` bytes-level manipulation (`<body` injection).
* Auth (`get_current_user`).
* Form parsing (`await request.form()`).
* The `login` redirect.
* Persistence schema, migrations, or DDL.
* Financial math (delegated to `run_project` via `deps.run_project`).
* The `runtime_guard_for_snapshot` / `check_runtime_allowed` policy
  (delegated to `scenario_state_service` via `deps.check_runtime_allowed`).

## API surface

### `RunRouteOutcome` (return type)

```python
@dataclass
class RunRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200
    prepend_html: Optional[str] = None
    headers: dict = field(default_factory=dict)
```

The route translates this into either a `TemplateResponse(...)` (for
`errors.html` / `kpis.html`) or a `TemplateResponse(...)` whose
rendered bytes are then prepended with `prepend_html` (for
`runtime_summary.html`).

### `RunRouteDeps` (dependency injection bundle)

The route constructs one of these and passes it to the service. Each
field is a callable or a class reference. The service does not import
`main_web` to obtain them; the route is the single assembly point.

```python
@dataclass
class RunRouteDeps:
    collect_form_snapshot: Callable
    project_workspace_from_snapshot: Callable
    normalize_template_source: Callable
    canonical_project_type: Callable
    check_runtime_allowed: Callable
    resolve_runtime_snapshot_source: Callable
    build_schema_from_form: Callable
    validate_form: Callable
    format_kpis: Callable
    default_workspace_snapshot: Callable
    replay_metadata_for_project: Callable
    governance_snapshot: Callable
    scenario_provenance_for_record: Callable
    run_project: Callable
    build_projectinputs: Callable
    build_projectinputs_from_snapshot: Callable
    record_workspace_runtime: Callable
    update_scenario_last_run_summary: Callable
    runtime_summary_to_dict: Callable
    snapshot_input_error: type
```

### `execute_run_route(...)` (public entry point)

```python
async def execute_run_route(
    *,
    request,
    form,
    user,
    deps: RunRouteDeps,
) -> RunRouteOutcome:
    ...
```

This is the single public function. The three execution paths
(`_execute_user_created_path`, `_execute_template_seeded_path`,
`_execute_generic_path`) are module-private helpers used by
`execute_run_route`.

## Why dependency injection, not direct imports

* `main_web.py` defines the helpers (`_collect_form_snapshot`,
  `_resolve_runtime_snapshot_source`, etc.) as module-private
  functions. They cannot be imported across the
  `app/services/run_service.py` boundary without making them public.
* Moving those helpers into a new module would expand the surface
  area of this phase beyond "thin route + service".
* DI keeps the import direction clean: `main_web → run_service` and
  never the reverse. The service has zero compile-time knowledge of
  `main_web`.
* DI also makes the service trivially unit-testable: a test can
  construct a `RunRouteDeps` with stub callables and exercise the
  three execution paths without spinning up FastAPI.

## Boundary invariants

1. `run_service.py` MUST NOT import `main_web`. Pinned by
   `test_run_service_does_not_import_main_web`.
2. `run_service.py` MUST NOT call `run_project` directly — it must
   call it via `deps.run_project`. (Implementation detail; the
   current `execute_run_route` calls `deps.run_project(...)`.)
3. `run_service.py` MUST NOT render templates — it returns
   `RunRouteOutcome` and the route renders.
4. The route MUST be a thin wrapper: < 200 non-blank body lines
   (pinned by `test_run_route_body_is_materially_thinner`).
5. The route MUST NOT call `run_project` or
   `record_workspace_runtime` directly. Pinned by
   `test_run_route_does_not_call_run_project_directly` and
   `test_run_route_does_not_call_record_workspace_runtime_directly`.

## What this boundary buys us

* `main_web.py` shrinks by ~322 lines (388 inline body → 76 thin
  wrapper) and the god-module grows by 0 lines.
* The `/run` orchestration is now testable as a service: the
  `RunRouteDeps` dataclass is the seam.
* The next phases (51C `/compare`, then `/validate`, then
  `/scenarios/*`) have a clear template to follow.
* `run_service` is the place to add cross-cutting concerns later
  (logging, telemetry, retries) without touching the route.
