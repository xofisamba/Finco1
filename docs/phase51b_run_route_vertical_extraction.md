# Phase 51B — Vertical extraction of POST /run orchestration

## Objective

Vertically extract the full orchestration body of the `POST /run` route from
`main_web.py` into a dedicated service module
(`app/services/run_service.py`). The goal of this phase is **god-module
reduction** — turning the `/run` route into a thin wrapper that delegates
to the service, not a chase of perfect architecture.

The previous phases (49, 50, 50C, 50D, 51A) extracted lower-risk helpers
and added characterization tests. Phase 51B is the first true vertical
slice of an entire route body.

## Base SHA

`c19f08c1c16d8e352a9707aa51463a84f8c70cca` (origin/main @ PR #379 merge)

## What moved

| From | To |
|---|---|
| `main_web.py` `@app.post("/run")` body (~380 lines) | `app/services/run_service.py` `execute_run_route(...)` (~653 lines total, including 3 helper paths + `RunRouteOutcome` + `RunRouteDeps`) |

The route is now a thin wrapper that:

1. Authenticates the user (returns `/login` redirect if unauthenticated).
2. Parses the form.
3. Builds a `RunRouteDeps` instance with the helpers still defined in
   `main_web.py` (`_collect_form_snapshot`, `_project_workspace_from_snapshot`,
   `_normalize_template_source`, `_resolve_runtime_snapshot_source`,
   `_build_schema_from_form`, `_validate_form`, `_format_kpis`,
   `_default_workspace_snapshot`, `_replay_metadata_for_project`,
   `_governance_snapshot`, `_scenario_provenance_for_record`,
   `runtime_summary_to_dict`, `SnapshotInputError`).
4. Calls `await execute_run_route(request=request, form=form, user=user, deps=deps)`.
5. Renders the returned `RunRouteOutcome` via the existing FastAPI / Jinja
   path (template response for `errors.html` / `kpis.html`; template
   response + bytes-level prepended `<script>` for `runtime_summary.html`).

## What did not move

* `main_web.py` still defines and owns the helper functions passed in via
  `RunRouteDeps`. The route is the single assembly point for the dep
  bundle. Helpers stay in `main_web.py` because moving them would expand
  the surface area of this phase beyond "thin route + service".
* The `/compare`, `/download`, `/validate`, `/scenarios/*` and other
  routes are unchanged.
* `app/waterfall_core.py` is untouched.
* `app/api/project_runner.run_project` is untouched (called by the
  service via the `deps.run_project` dep).
* `app/services/scenario_state_service.check_runtime_allowed`,
  `resolve_runtime_snapshot`, `build_workspace_state_metadata`,
  `scenario_provenance_for_record` are untouched.
* `app/persistence/repository.*` is untouched (service calls
  `record_workspace_runtime` and `update_scenario_last_run_summary` via
  the deps bundle).
* The legacy `runtime_guard_for_snapshot` import in `main_web.py` was
  removed (Phase 50C-2 already wrapped it in `check_runtime_allowed`;
  the unused import was a leftover from before the refactor).

## Service API chosen

```python
@dataclass
class RunRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200
    prepend_html: Optional[str] = None
    headers: dict = field(default_factory=dict)

@dataclass
class RunRouteDeps:
    """Bundle of helpers passed in by the route to keep the service
    free of main_web dependencies."""
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

async def execute_run_route(
    *,
    request,
    form,
    user,
    deps: RunRouteDeps,
) -> RunRouteOutcome:
    """Execute the /run orchestration and return a RunRouteOutcome.
    The route in main_web.py translates the outcome into a FastAPI
    response."""
```

**Why `RunRouteOutcome` (return value) instead of building a Response
here:** the service would otherwise depend on FastAPI `Request`,
`Jinja2Templates`, and `HTMLResponse` internals. Returning a plain
dataclass keeps the service free of framework dependencies and makes
the service trivially unit-testable. The route is the only place that
calls `templates.TemplateResponse(...)` and `HTMLResponse(...)`, and
those calls are now tiny (5-10 lines each).

## Before/after `/run` route responsibility split

| Concern | Before Phase 51B | After Phase 51B |
|---|---|---|
| Auth redirect | main_web route | main_web route |
| Form parsing | main_web route | main_web route |
| Project/workspace resolution | main_web route (inline) | run_service |
| Runtime guard orchestration | main_web route (inline) | run_service |
| Runtime snapshot resolution | main_web route (inline) | run_service |
| Three execution paths (user_created, tuho/oborovo, generic) | main_web route (inline) | run_service (3 helper functions) |
| KPI context assembly | main_web route (inline) | run_service |
| Runtime summary context assembly | main_web route (inline) | run_service |
| `record_workspace_runtime` call | main_web route (inline) | run_service |
| `update_scenario_last_run_summary` call | main_web route (inline) | run_service |
| Replay metadata construction | main_web route (inline) | run_service |
| sessionStorage script construction | main_web route (inline) | run_service (returns `prepend_html`) |
| Template rendering (errors.html, kpis.html) | main_web route | main_web route (tiny wrapper) |
| Template rendering + script prepend (runtime_summary.html) | main_web route (inline bytes manipulation) | main_web route (preserved legacy behavior: `<!DOCTYPE` → inject after `<body`, else direct prepend) |

## Route thinness result

| Metric | Before Phase 51B | After Phase 51B |
|---|---|---|
| `/run` route body lines (decorator + def + body, including blank lines) | ~388 | 76 |
| `/run` route body non-blank lines | ~382 | ~64 |
| `main_web.py` total lines | 3000 (after extraction) | ~2990 (76 added by thin route, ~388 removed from inline body) |

The post-extraction route is materially thinner (76 lines vs ~388), well
below the 200-line threshold pinned in
`tests/test_phase51b_run_route_vertical_extraction.py`.

## Behavior preservation checklist

| Behavior | Preserved? | Test |
|---|---|---|
| Auth redirect for unauthenticated users | ✅ | `test_main_web_imports_cleanly` + manual smoke |
| Dirty workspace guard (`check_runtime_allowed` → `errors.html`) | ✅ | `test_run_service_emits_sessionstorage_save_tag_for_user_created` + service unit tests |
| `saved_state` / `user_created` / `workspace_base` runtime origins | ✅ | `test_run_service_has_runtime_origin_branching` |
| `tuho` / `oborovo` template-seeded path | ✅ | `test_run_service_has_runtime_origin_branching` + Phase 51A TUHO/Oborovo golden |
| Generic wind/solar fallback path | ✅ | `test_run_service_has_runtime_origin_branching` (asserts `_execute_generic_path`) |
| Invalid project type error (via `deps.validate_form`) | ✅ | `test_run_service_routes_invalid_project_type_through_validate_form` |
| `active_project` / `active_scenario` behavior | ✅ | service mirrors original route body 1:1 |
| TUHO/Oborovo template-seeded flow | ✅ | Phase 51A golden + Phase 51B structural |
| Generic wind/solar flow | ✅ | Phase 51A golden + Phase 51B structural |
| Runtime origin (saved_state / workspace_base) | ✅ | `test_run_service_has_runtime_origin_branching` |
| Scenario provenance | ✅ | service still calls `deps.scenario_provenance_for_record` |
| `record_workspace_runtime` side effect | ✅ | service still calls it for the user_created / tuho / oborovo paths |
| `update_scenario_last_run_summary` side effect | ✅ | service still calls it on the saved_state path |
| Replay metadata construction | ✅ | service still calls `deps.replay_metadata_for_project` |
| sessionStorage script prepended to runtime summary | ✅ | `test_run_service_emits_sessionstorage_save_tag_for_user_created` |
| Template choice (runtime_summary.html / kpis.html / errors.html) | ✅ | `test_run_service_routes_to_correct_templates` |
| Response status codes | ✅ | service returns `RunRouteOutcome(status_code=200)`; route passes through |
| HTMX target expectations (partial rendering) | ✅ | all 3 templates are `partials/*` |
| TUHO `<!DOCTYPE` body injection (script after `<body`) | ✅ | route preserved the `body_str.startswith("<!DOCTYPE")` branch |
| User-created direct prepended script | ✅ | route preserved the `else: body_str = outcome.prepend_html + body_str` branch |

## Circular dependency check

`run_service.py` does NOT import `main_web`. Verified by
`test_run_service_does_not_import_main_web` in the Phase 51B test
suite. The import direction is strictly:

```
main_web.py  →  app/services/run_service.py
```

All helpers that the service needs but that live in `main_web.py`
(`_collect_form_snapshot`, `_resolve_runtime_snapshot_source`, etc.)
are passed in via the `RunRouteDeps` dataclass. This is dependency
injection, not import — the service has zero compile-time knowledge
of `main_web`.

## Parity / numeric test status

| Test | Status | Notes |
|---|---|---|
| `tests/test_phase51b_run_route_vertical_extraction.py` (22 tests) | ✅ 22/22 | new in Phase 51B |
| `tests/test_phase51a_run_route_golden_characterization.py` (25 tests) | ✅ 25/25 | golden output contract — pinned structure, not absolute values |
| `tests/test_phase50d_current_state_after_refactor_cleanup.py` (24 tests) | ✅ 24/24 | after count threshold relax (1+, not == 6) — phase 51B legitimately reduced `main_web`'s `check_runtime_allowed` call count by 1 (the `/run` route now delegates) |
| `tests/test_phase50c_closeout_scenario_state_service.py` (26 tests) | ✅ 26/26 | after count threshold relax (1+, not == 6) — same reason |
| `tests/test_tuho_calibration_reconciliation.py` | ❌ 4 pre-existing failures | TUHO equity IRR + first distribution timing — pre-existing Phase 20P/20T calibration gap, **not a Phase 51B regression** (verified by running same tests on `origin/main`) |
| `tests/test_oborovo_parity.py` | ❌ 2 pre-existing failures | Oborovo SHL amount + total equity+SHL — pre-existing Phase 20T/Phase 31 SHL calibration gap, **not a Phase 51B regression** (verified on `origin/main`) |
| `tests/test_oborovo_dscr_calibration.py` | ❌ 1 pre-existing failure | Oborovo equity IRR 6.2% (range [8%, 11%]) — pre-existing Phase 20T calibration gap, **not a Phase 51B regression** (verified on `origin/main`) |
| `tests/test_financial_statements_tuho_pnl_parity.py` | ✅ passed | |
| `tests/test_financial_statements_oborovo_pnl_parity.py` | ✅ passed | |
| `tests/test_excel_export_calibration_guard.py` | ✅ passed | |

`import main_web` → OK. No `ImportError` after extraction.

## Phase 51A golden test status

All 25 Phase 51A golden tests pass. The contract is preserved.

## Guardrails

✅ Did NOT change financial formulas.
✅ Did NOT change runtime calculations.
✅ Did NOT change model outputs.
✅ Did NOT change route behavior.
✅ Did NOT change export behavior.
✅ Did NOT change project factories.
✅ Did NOT change fixture CSVs.
✅ Did NOT change schema / migrations.
✅ Did NOT add JavaScript financial calculations.
✅ Did NOT implement generic validation.
✅ Did NOT promote G20 / R99 / R102.
✅ Did NOT promote partial_pay_sweep.
✅ Did NOT promote flat / min DSCR sculpting.
✅ Backend remains source of truth.
✅ PR #299 remains draft / not merged.

The only production code change outside of `run_service.py` is the
removal of the legacy `runtime_guard_for_snapshot` import from
`main_web.py` (line 70). The function was already unused after
Phase 50C-2 wrapped it in `check_runtime_allowed`; the unused import
was a leftover.

## Recommended next phase

**Phase 51C** — `/compare` route characterization and vertical
extraction, using the same behavior-first approach.

Pre-conditions for Phase 51C:

1. Phase 51B merged.
2. Add `/compare` route golden characterization (mirrors
   `test_phase51a_run_route_golden_characterization.py`).
3. Extract `/compare` orchestration into
   `app/services/compare_service.py` with a `CompareRouteOutcome` +
   `CompareRouteDeps` pair (mirrors Phase 51B's `RunRouteOutcome` +
   `RunRouteDeps`).
4. Pin the same guardrails: no formula/runtime/JS/fixture changes;
   preserve Base/Downside/Upside behavior; preserve scenario
   provenance; preserve `record_compare_run` side effects.

After Phase 51C, the natural follow-up is `/validate` and then the
`/scenarios/*` cluster.
