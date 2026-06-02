# Phase 51D-2 — /validate route vertical extraction

## Base SHA

`ca194114b0482308e45bba6bb1415da1df5d3ad3` (origin/main @ PR #383 merge,
Phase 51D-1 /validate golden characterization)

## Objective

Extract `POST /validate` orchestration from `main_web.py` into
`app/services/validation_service.py` using the same behavior-first
vertical extraction pattern as Phase 51B (`run_service`) and Phase
51C-2 (`compare_service`).

This is a behavior-preserving production refactor with **NO production
behavior changes**. The runtime-snapshot parity call documented in
Phase 51D-1 is preserved EXACTLY.

## What moved

| Concern | Before | After |
|---|---|---|
| `ValidateRouteOutcome` / `ValidateRouteDeps` | n/a | `app/services/validation_service.py` |
| `execute_validate_route(...)` | n/a | `app/services/validation_service.py` |
| Form parsing (12 fields) | inline in route | inside `execute_validate_route` |
| Snapshot + project/workspace resolution | inline in route | inside `execute_validate_route` |
| Runtime guard semantics | inline in route | inside `execute_validate_route` |
| **Runtime snapshot resolution (parity call)** | inline in route | inside `execute_validate_route` (parity preserved exactly) |
| Stage A: enum validation | inline in route | inside `execute_validate_route` |
| Stage B: numeric field validation (9 fields, exact max values) | inline in route | inside `execute_validate_route` |
| Stage C: schema build validation (`if not errors:` gate, `ValueError` catch) | inline in route | inside `execute_validate_route` |
| Template response assembly | inline in route | inside `execute_validate_route` |
| `/validate` route body | 77 lines | 35 lines (-54.5%) |

## What did NOT move

| Concern | Status |
|---|---|
| Auth redirect (`get_current_user` → `RedirectResponse("/login")`) | stays in `main_web.py` (route-owned) |
| `await request.form()` | stays in `main_web.py` |
| `templates.TemplateResponse(...)` rendering | stays in `main_web.py` |
| `ValidateRouteDeps` construction with all 11 callables | stays in `main_web.py` (route wires deps) |
| `/run` route from Phase 51B | untouched (68 → 68 lines) |
| `run_service.py` from Phase 51B | untouched |
| `/compare` route from Phase 51C-2 | untouched (36 → 36 lines) |
| `compare_service.py` from Phase 51C-2 | untouched |
| `scenario_state_service.py` | untouched |
| `_collect_form_snapshot`, `_project_workspace_from_snapshot`, `_canonical_project_type`, `_normalize_template_source`, `_resolve_runtime_snapshot_source`, `_build_schema_from_form`, `_validate_numeric_field` | all stay in `main_web.py` (passed as deps) |
| `check_runtime_allowed` (imported from `scenario_state_service`) | stays imported in `main_web.py` (passed as dep) |
| `SnapshotInputError` (parity dep, NOT used by /validate today) | stays imported in `main_web.py` (passed as dep) |
| `PROJECT_TYPES` / `SCENARIOS` constants | stay in `main_web.py` module scope (passed as deps) |
| Financial formulas / model / project factories / fixture CSVs / schema migrations | unchanged |
| JS financial calculations | unchanged (none added) |
| Validation behavior (Stage A → B → C, error accumulation, etc.) | unchanged |
| Numeric max values (9 fields) | unchanged |
| Runtime-snapshot parity call | unchanged (preserved exactly) |

## Allowed behavior changes

**None.** This is a behavior-preserving refactor. No production
behavior changes are allowed or made.

In particular, the following Phase 51D-1 characterization points are
preserved EXACTLY:

* **Stage A** — `project_type in deps.project_types`, `scenario in
  deps.scenarios`. Errors accumulate.
* **Stage B** — 9 numeric fields with exact max values:
  capacity_mw=2000.0, tariff_eur_mwh=1000.0, p50_hours=10000.0,
  total_capex_keur=1_000_000.0, opex_y1_keur=500_000.0,
  gearing_pct=100.0, target_dscr=10.0, interest_rate_pct=30.0,
  tenor_years=50.0. Empty numeric field passes Stage B (treated as
  optional).
* **Stage C** — gated by `if not errors:` (only runs when Stage A and
  B have no errors); catches `ValueError` specifically (NOT bare
  `Exception`); appends `str(ve)`.
* **Runtime-snapshot parity call** — `_resolve_runtime_snapshot_source`
  is called when (saved_state + active_scenario_id) OR
  (user_created). The first tuple element is captured as
  `runtime_snapshot`; the rest are discarded. The captured snapshot
  is intentionally unused downstream (preserved as the
  `noqa: F841` annotation in the service).

## validation_service API

```python
@dataclass
class ValidateRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200
    headers: dict = field(default_factory=dict)


@dataclass
class ValidateRouteDeps:
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
    validate_numeric_field: Callable[..., tuple]  # per-field helper, NOT whole-form

    # Constants (moved out of main_web globals)
    project_types: list[str]
    scenarios: list[str]

    # Snapshot error class (parity with compare_service; NOT used by
    # /validate today)
    snapshot_input_error: type


async def execute_validate_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    deps: ValidateRouteDeps,
) -> ValidateRouteOutcome:
    ...
```

Full API documentation: `docs/phase51d2_validation_service_boundary.md`.

## /validate route — before / after

### Before (Phase 51D-1, pre-extraction)

```python
@app.post("/validate")
async def validate(request: Request):
    """Validate form inputs. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # Parse form data
    form = await request.form()
    snapshot = _collect_form_snapshot(form)
    project_type = form.get("project_type", "")
    # ... 10 more form fields ...
    project_record, workspace_state = _project_workspace_from_snapshot(user, snapshot)
    project_code = project_record.project_code
    allow_run, runtime_origin, guard_message = check_runtime_allowed(workspace_state, snapshot)
    if not allow_run:
        return templates.TemplateResponse(...)

    runtime_snapshot = None
    if (runtime_origin == "saved_state" and workspace_state.active_scenario_id) or project_record.project_origin == "user_created":
        runtime_snapshot, _, _, _ = _resolve_runtime_snapshot_source(...)

    errors = []
    # Stage A
    if project_type not in PROJECT_TYPES: errors.append(...)
    if scenario not in SCENARIOS: errors.append(...)
    # Stage B
    numeric_checks = [...]  # 9 fields with exact max values
    for ... in numeric_checks: ...
    # Stage C (gated by `if not errors:`)
    if not errors:
        try: schema = _build_schema_from_form(...)
        except ValueError as ve: errors.append(str(ve))
    # Render
    return templates.TemplateResponse(...)
```

Total: **77 lines / 77 non-blank**.

### After (Phase 51D-2, post-extraction)

```python
@app.post("/validate")
async def validate(request: Request):
    """Validate form inputs. Requires auth.

    Phase 51D-2: orchestration extracted into
    ``app.services.validation_service.execute_validate_route``. The
    route is now thin: auth, form parse, deps bundle, service call,
    render.
    """
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

Total: **35 lines / 35 non-blank** — a 54.5% reduction.

## Stage preservation summary

| Stage | Behavior | Preserved in 51D-2? |
|---|---|---|
| Stage A — enum validation | `project_type in PROJECT_TYPES`, `scenario in SCENARIOS`; errors accumulate | ✅ exact |
| Stage B — numeric field validation | 9 fields with exact max values; `_validate_numeric_field` per field; empty field passes | ✅ exact |
| Stage C — schema build validation | `if not errors:` gate; `ValueError` catch; `str(ve)` appended | ✅ exact |
| Stage order | A → B → C, errors accumulate (no short-circuit) | ✅ exact |
| Stage C `if not errors:` gate | Prevents Stage C from running when Stage A or B has errors | ✅ exact |
| Stage C `ValueError` catch | Catches `ValueError` specifically, NOT bare `Exception` | ✅ exact |

## Numeric max preservation summary

| Field | Max value | Preserved in 51D-2? |
|---|---|---|
| `capacity_mw` | 2000.0 | ✅ exact |
| `tariff_eur_mwh` | 1000.0 | ✅ exact |
| `p50_hours` | 10000.0 | ✅ exact |
| `total_capex_keur` | 1_000_000.0 | ✅ exact |
| `opex_y1_keur` | 500_000.0 | ✅ exact |
| `gearing_pct` | 100.0 | ✅ exact |
| `target_dscr` | 10.0 | ✅ exact |
| `interest_rate_pct` | 30.0 | ✅ exact |
| `tenor_years` | 50.0 | ✅ exact |

## Runtime-snapshot parity call preservation

The Phase 51D-1 characterized runtime-snapshot parity quirk is
preserved EXACTLY in Phase 51D-2. The service:

1. Resolves the snapshot via `deps.resolve_runtime_snapshot_source(...)`
   when (saved_state + active_scenario_id) OR (user_created).
2. Captures only the first tuple element as `runtime_snapshot`.
3. Discards the other three elements (`scenario_record`, `warning`,
   `effective_runtime_origin`).
4. **Does NOT use** the captured `runtime_snapshot` downstream
   (annotated with `noqa: F841` to make this explicit).

The same exact behavior as the legacy /validate route is preserved
down to the variable name and tuple-unpacking shape:

```python
runtime_snapshot, _, _, _ = deps.resolve_runtime_snapshot_source(
    user, project_record, workspace_state, runtime_origin,
)
```

## Read-only invariant

The `/validate` route remains purely read-only. There is NO
persistence side effect on the `/validate` execution path:

* No `record_compare_run` (does not exist in the codebase).
* No `record_workspace_runtime` (only used by `/run`).
* No `record_export` (only used by export routes).
* No `update_scenario_last_run_summary` (only used by `/run`).
* No `db.add` / `db.commit` / `db.flush` / `session.add` /
  `session.commit`.

The validation path executes the form parsing, runtime guard,
runtime snapshot resolution (parity), three validation stages, and
returns a structured outcome. Nothing is written to the database.

## Test results

| Suite | Tests | Pass | Fail | xfail | Skip |
|---|---|---|---|---|---|
| Phase 51A (/run golden) | 25 | 25 | 0 | 0 | 0 |
| Phase 51B (/run extraction) | 22 | 22 | 0 | 0 | 0 |
| Phase 51C-1 (/compare golden) | 37 | 37 | 0 | 0 | 0 |
| Phase 51C-2 (/compare extraction) | 49 | 49 | 0 | 0 | 0 |
| Phase 51D-1 (/validate golden) | 51 | 51 | 0 | 0 | 0 |
| Phase 51D-2 (/validate extraction) | 52 | 52 | 0 | 0 | 0 |
| **Total Phase 51** | **236** | **236** | **0** | **0** | **0** |

* All 236 phase51 tests pass locally.
* The Phase 51D-1 characterization tests had structural tests
  re-pointed to `validation_service.py` (not weakened, just
  re-targeted). Behavioral assertions on live integration tests are
  unchanged.
* Local `import main_web` and `from app.services import
  validation_service` both work.
* Two pre-existing collection errors in `tests/test_persistence.py`
  and `tests/test_repository.py` (legacy import error: `from
  persistence.models` is broken on `origin/main` HEAD as well) were
  not introduced by this phase and are out of scope.

## Guardrails preserved

✅ No changes to financial formulas.
✅ No changes to model calculation logic.
✅ No changes to project factories.
✅ No changes to fixture CSVs.
✅ No changes to schema / migrations.
✅ No new JavaScript financial calculations.
✅ No generic validation framework.
✅ Did NOT promote G20 / R99 / R102.
✅ Did NOT promote `partial_pay_sweep`.
✅ Did NOT promote flat / min DSCR sculpting.
✅ Backend remains source of truth.
✅ Generic solar / wind remain exploratory / unvalidated.
✅ No lender / bank / audit / certification / SaaS claims.
✅ `/run` route from Phase 51B remains thin (< 200 non-blank body lines; 68 → 68).
✅ `/compare` route from Phase 51C-2 remains thin (< 50 non-blank body lines; 36 → 36).
✅ `run_service.py` from Phase 51B remains intact.
✅ `compare_service.py` from Phase 51C-2 remains intact.
✅ `validation_service.py` does NOT import `main_web` (one-way import direction).
✅ `validation_service.py` does NOT import `main_api` (service is web-layer).
✅ `main_web.py` has zero direct `record_export` calls.
✅ `/validate` route has zero direct persistence / `record_*` calls.
✅ `/validate` service has zero direct persistence / `record_*` calls.
✅ PR #299 remains draft / not merged (verified post-extraction).

## Recommended next phase

**Phase 51E-1** — Apply the same vertical extraction pattern to the
next god-module hotspot in `main_web.py`. Candidate targets (in
order of body size, all > 50 non-blank lines):

* `POST /scenarios/state/draft` (line 2181)
* `POST /scenarios/save` (line 2316)
* `POST /scenarios/{scenario_id}/duplicate` (line 2446)
* `POST /scenarios/add` (line 2520)
* `POST /projects/create` (line 2030)

For each, the proposed pattern is:
1. Characterization (e.g. phase5x1_*) — pin current behavior, no
   production code change.
2. Vertical extraction (e.g. phase5x2_*) — extract orchestration
   body into a service module, keep the route thin, write
   characterization + extraction test suites.

`/run`, `/compare`, and `/validate` will serve as the canonical
templates. All three follow the same shape: thin route (auth + form
+ deps + service call + render), service owns orchestration, deps
bundle injects helpers from main_web module scope.
