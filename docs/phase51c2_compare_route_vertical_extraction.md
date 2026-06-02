# Phase 51C-2 — /compare route vertical extraction

## Base SHA

`26afe76c0d9f0c28494e58ca63ec323fb852361e` (origin/main @ PR #381 merge)

## Objective

Extract `POST /compare` orchestration from `main_web.py` into
`app/services/compare_service.py` using the same behavior-first
pattern as Phase 51B, while fixing the two documented latent
snapshot binding bugs from Phase 51C-1.

This is a behavior-preserving production refactor EXCEPT for the
two explicitly allowed bug fixes from Phase 51C-1:

1. `user_created` path no longer raises `NameError` because
   `runtime_snapshot` is now defined (resolved via
   `deps.resolve_runtime_snapshot_source`).
2. `saved_state` + `active_scenario` path no longer bypasses
   `resolve_runtime_snapshot_source` — it now uses the resolved
   snapshot, not raw form values.

## What moved

| Concern | Before | After |
|---|---|---|
| `CompareRouteOutcome` / `CompareRouteDeps` | n/a | `app/services/compare_service.py` |
| `execute_compare_route(...)` | n/a | `app/services/compare_service.py` |
| `user_created` snapshot resolution | free `runtime_snapshot` ref (NameError) | `deps.resolve_runtime_snapshot_source(...)` early in `execute_compare_route` |
| `saved_state` snapshot resolution | free `runtime_snapshot` ref (always None in this branch) | `deps.resolve_runtime_snapshot_source(...)` early in `execute_compare_route` |
| `/compare` route body | 95 lines (~89 non-blank) | 33 lines (31 non-blank) |
| Form parsing | inline in route | inside `execute_compare_route` |
| Override construction (user_created / template-seeded) | inline in route | inside `execute_compare_route` |
| Project key resolution (TUHO / Oborovo / Solar / Wind) | inline in route | inside `execute_compare_route` |
| Scenario loop (3 scenarios, 6 KPIs each) | inline in route | inside `execute_compare_route` |
| Soft-error per-scenario semantics | inline in route | inside `execute_compare_route` |
| Template response assembly | inline in route | inside `execute_compare_route` |

## What did NOT move

| Concern | Status |
|---|---|
| Auth redirect (`get_current_user` → `RedirectResponse("/login")`) | stays in main_web.py (route-owned) |
| `await request.form()` | stays in main_web.py (route-owned) |
| `templates.TemplateResponse(...)` rendering | stays in main_web.py (route-owned) |
| `CompareRouteDeps` construction with all 13 callables | stays in main_web.py (route wires deps) |
| `/run` route from Phase 51B | untouched |
| `run_service.py` from Phase 51B | untouched |
| `scenario_state_service.py` | untouched |
| `_collect_form_snapshot`, `_project_workspace_from_snapshot`, `_normalize_template_source`, `_canonical_project_type`, `_resolve_runtime_snapshot_source`, `_build_schema_from_form` | all stay in main_web.py (passed as deps) |
| `build_projectinputs`, `build_projectinputs_from_snapshot`, `run_project` | all stay as module-scope imports in main_web.py (passed as deps) |
| `SCENARIOS` / `PROJECT_TYPES` constants | stay in main_web.py module scope (passed as deps) |
| `SnapshotInputError` | stays as imported class in main_web.py (passed as dep) |
| Financial formulas / model / project factories / fixture CSVs / schema migrations | unchanged |
| JS financial calculations | unchanged (none added) |

## Allowed bug fixes

### Bug A — user_created runtime_snapshot NameError

The legacy `/compare` route's `user_created` branch (line ~1612 of
pre-refactor main_web.py) referenced `runtime_snapshot` without ever
defining it:

```python
if project_record.project_origin == "user_created":
    try:
        override = build_projectinputs_from_snapshot(runtime_snapshot)  # NameError
    except SnapshotInputError as e:
        ...
```

The `/run` handler defines `runtime_snapshot` via
`resolve_runtime_snapshot_source(...)`; the `/compare` handler did not.
This means the `user_created` path in `/compare` would raise
`NameError: name 'runtime_snapshot' is not defined` on first
execution.

**Fix (Phase 51C-2):** The service resolves the snapshot early in
`execute_compare_route` and uses it consistently. The `user_created`
branch now receives a properly-resolved snapshot:

```python
if (runtime_origin == "saved_state" and workspace_state.active_scenario_id) \
        or project_record.project_origin == "user_created":
    (
        runtime_snapshot,
        active_scenario_record,
        runtime_warning,
        effective_runtime_origin,
    ) = deps.resolve_runtime_snapshot_source(
        user, project_record, workspace_state, runtime_origin,
    )

# ... later, in the user_created branch:
if project_record.project_origin == "user_created":
    try:
        override = deps.build_projectinputs_from_snapshot(runtime_snapshot)
    except deps.snapshot_input_error as e:
        ...
```

The `SnapshotInputError` is caught narrowly (via
`deps.snapshot_input_error`) — this mirrors the `run_service.py`
pattern.

### Bug B — saved_state + active_scenario resolves snapshot

The legacy `/compare` route's non-`user_created` branch checked
`runtime_snapshot and runtime_origin == "saved_state"` but
`runtime_snapshot` was never set in that code path (the resolver was
never called for `/compare`). This means the saved_state +
active_scenario path silently fell through to the form-driven schema
build, using raw form values instead of the resolved snapshot.

**Fix (Phase 51C-2):** The same early resolution (shown above) makes
`runtime_snapshot` properly defined for ALL branches, including the
saved_state + active_scenario path:

```python
else:  # template-seeded (non-user_created) path
    try:
        if runtime_snapshot and runtime_origin == "saved_state" and workspace_state.active_scenario_id:
            override = deps.build_projectinputs_from_snapshot(runtime_snapshot)
        else:
            schema = deps.build_schema_from_form(...)
            override = deps.build_projectinputs(schema)
    except (ValueError, Exception) as e:
        ...
```

The factory / generic form-driven path still works for the
non-saved_state case.

## compare_service API

```python
@dataclass
class CompareRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200
    headers: dict = field(default_factory=dict)


@dataclass
class CompareRouteDeps:
    collect_form_snapshot: Callable
    project_workspace_from_snapshot: Callable
    canonical_project_type: Callable
    normalize_template_source: Callable
    check_runtime_allowed: Callable
    resolve_runtime_snapshot_source: Callable
    build_schema_from_form: Callable
    build_projectinputs: Callable
    build_projectinputs_from_snapshot: Callable
    scenarios: list[str]
    project_types: list[str]
    snapshot_input_error: type
    run_project: Callable


async def execute_compare_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    deps: CompareRouteDeps,
) -> CompareRouteOutcome:
    ...
```

Full API documentation: `docs/phase51c2_compare_service_boundary.md`.

## /compare route — before / after

### Before (Phase 51C-1, pre-extraction)

```python
@app.post("/compare")
async def compare(request: Request):
    """Run Base/Downside/Upside comparison. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    snapshot = _collect_form_snapshot(form)
    project_type = form.get("project_type", "")
    capacity_mw = form.get("capacity_mw", "")
    # ... 10 form fields ...
    project_record, workspace_state = _project_workspace_from_snapshot(user, snapshot)
    # ... 89 non-blank lines total: runtime guard, validation, override
    # construction (user_created + template-seeded), project key resolution,
    # scenario loop with 6 KPIs, soft-error per scenario, template render ...
    return templates.TemplateResponse(...)
```

Total: **95 lines / ~89 non-blank**.

### After (Phase 51C-2, post-extraction)

```python
@app.post("/compare")
async def compare(request: Request):
    """Run Base/Downside/Upside comparison. Requires auth.

    Phase 51C-2: orchestration extracted into
    ``app.services.compare_service.execute_compare_route``. The route is
    now thin: auth, form parse, deps bundle, service call, render.
    """
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

Total: **33 lines / 31 non-blank** — a ~65% reduction.

## Read-only invariant

The `/compare` route remains purely read-only. There is NO
persistence side effect on the `/compare` execution path:

* No `record_compare_run` (does not exist in the codebase).
* No `record_workspace_runtime` (only used by `/run`).
* No `record_export` (only used by export routes).
* No `update_scenario_last_run_summary` (only used by `/run`).
* No `db.add` / `db.commit` / `db.flush` / `session.add` /
  `session.commit`.

The /compare path executes model logic, formats KPI results, and
returns them in the template context. Nothing is written to the
database.

## Test results

| Suite | Tests | Pass | Fail | xfail | Skip |
|---|---|---|---|---|---|
| Phase 51A (/run golden) | 25 | 25 | 0 | 0 | 0 |
| Phase 51B (/run extraction) | 22 | 22 | 0 | 0 | 0 |
| Phase 51C-1 (/compare golden) | 37 | 37 | 0 | 0 | 0 |
| Phase 51C-2 (/compare extraction) | 49 | 49 | 0 | 0 | 0 |
| **Total Phase 51** | **133** | **133** | **0** | **0** | **0** |

* All 133 phase51 tests pass locally.
* The Phase 51C-1 xfail `test_compare_user_created_path_does_not_raise_nameerror`
  was converted to a passing test in this phase
  (`test_compare_user_created_path_resolves_runtime_snapshot_via_service`).
* The Phase 51C-1 `test_compare_route_references_undefined_runtime_snapshot`
  was updated to `test_compare_route_no_longer_references_undefined_runtime_snapshot`
  to reflect the fixed behavior.
* Two pre-existing collection errors in `tests/test_persistence.py` and
  `tests/test_repository.py` (legacy import error: `from persistence.models`
  is broken on origin/main HEAD as well) were not introduced by this
  phase and are out of scope.
* Local `import main_web` and `import app.services.compare_service`
  both work.

## Guardrails preserved

✅ No changes to financial formulas.
✅ No changes to model calculation logic.
✅ No changes to project factories.
✅ No changes to fixture CSVs.
✅ No changes to schema / migrations.
✅ No new JavaScript financial calculations.
✅ No generic validation framework.
✅ Did NOT promote G20 / R99 / R102.
✅ Did NOT promote partial_pay_sweep.
✅ Did NOT promote flat / min DSCR sculpting.
✅ Backend remains source of truth.
✅ Generic solar / wind remain exploratory / unvalidated.
✅ No lender / bank / audit / certification / SaaS claims.
✅ /run route from Phase 51B remains thin (< 200 non-blank body lines).
✅ run_service.py from Phase 51B remains intact.
✅ compare_service.py does NOT import main_web (one-way import direction).
✅ compare_service.py does NOT import main_api (service is web-layer).
✅ main_web.py has zero direct `record_export` calls.
✅ /compare route has zero direct persistence / record_* calls.
✅ /compare service has zero direct persistence / record_* calls.
✅ PR #299 remains draft / not merged (verified post-merge / pre-merge).

## Recommended next phase

**Phase 51D-1** — Apply the same vertical extraction pattern to the
next god-module hotspot in `main_web.py`. Candidate targets (in
order of body size, all > 50 non-blank lines):

* `POST /validate` (line 1427)
* `POST /scenarios/state/draft` (line 2181)
* `POST /scenarios/save` (line 2316)

`/download` (line 1688) and `/projects/create` (line 2030) are
already mid-sized and were partially decomposed in earlier phases.

For each, the proposed pattern is:
1. Characterization (e.g. phase5x1_*) — pin current behavior, no
   production code change.
2. Vertical extraction (e.g. phase5x2_*) — extract orchestration
   body into a service module, keep the route thin, write
   characterization + extraction test suites.

`/compare` and `/run` will serve as the canonical templates.
