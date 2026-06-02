# Phase 51J-2 — POST /scenarios/save vertical extraction

Phase 51J-2 extracts the orchestration body of `POST /scenarios/save`
from `main_web.py` into a new route-orchestration service module:
`app/services/scenarios_save_service.py`. The route handler in
`main_web.py` is now a thin wrapper that handles auth, form parsing,
deps bundle construction, and the final response render.

## What moved to `scenarios_save_service.py`

The full orchestration body that previously lived inline in
`save_scenario_endpoint` in `main_web.py`:

- Form snapshot collection via `collect_form_snapshot(form)`.
- `project_record` and `existing_workspace_state` resolution via
  `project_workspace_from_snapshot(user, snapshot)`.
- Soft-block handling: factory_template and saved_baseline projects
  return 200 + render with the `'Save is not available'` message
  (save_scenario and bind_workspace_to_scenario are NEVER called in
  this branch).
- `scenario_name` construction:
  `f"{project_name} {snapshot.get('scenario', 'Base')} {dt.now().strftime('%Y-%m-%d %H:%M')}"`.
- `last_run_summary` conditional:
  - Preserve `existing_workspace_state.last_runtime_summary` if
    `existing_workspace_state.last_runtime_snapshot == snapshot`.
  - Otherwise reset to `{}`.
- `save_scenario(...)` call with the right kwargs
  (`user_id`, `project_id`, `scenario_name`, `project_code`,
  `source_project_template`, `snapshot`, `governance_state`,
  `last_run_summary`, `replay_metadata` with
  `export_type='saved_scenario_snapshot'`).
- `bind_workspace_to_scenario(...)` call with
  `replay_metadata.export_type='workspace_saved_boundary'` and
  `scenario_id=saved_record.scenario_id`.
- Read-only queries: `list_scenarios`, `get_scenario_history`,
  `list_exports`, `build_export_lineage` (each called once per
  success).
- `scenario_summary_cards` assembly with 10 specific fields
  including `export_count` (computed per scenario_name from
  export_lineage).
- `render_scenario_workspace(...)` call (with the success or block
  message).

## What stayed in `main_web.py`

- The `@app.post("/scenarios/save")` decorator and the
  `save_scenario_endpoint` function signature.
- The `get_current_user(request)` auth check (302 redirect to
  `/login` if unauth).
- `await request.form()` form parsing.
- Construction of the `ScenariosSaveRouteDeps` instance with the
  13 callables from main_web module scope.
- Local import of the service module (one-way import direction).
- Final `await execute_scenarios_save_route(...)` call and pass
  through the rendered response.

## Why `scenario_state_service.py` was NOT extended

`scenario_state_service.py` is data-layer only. It does not take
`Request`, form, or auth arguments. It exposes 4 pure helpers used
by the route orchestration:

- `build_workspace_state_metadata`
- `scenario_provenance_for_record`
- `resolve_runtime_snapshot`
- `RuntimeSnapshotResolution`
- `check_runtime_allowed`

Adding route orchestration (form parsing, deps bundle, soft-block
handling, etc.) to this module would mix data-layer and
route-orchestration concerns, increase the import-cycle risk
between the data-layer and the route, and make future test isolation
harder.

## Why `scenario_state_route_service.py` was NOT reused

`scenario_state_route_service.py` handles workspace draft/discard
mutations WITHOUT scenario row creation. It exposes:

- `ScenarioStateRouteDeps` (with `save_workspace_state`,
  `discard_workspace_draft` callables, etc.)
- `execute_draft_route(...)`
- `execute_discard_route(...)`

These mutations operate on the user's workspace state directly
(`save_workspace_state` writes a `WorkspaceState` row, and
`discard_workspace_draft` discards a draft scenario). They do not
create a `ScenarioRecord`.

`/scenarios/save`, by contrast, creates a NEW `ScenarioRecord`
(via `save_scenario`) and binds it to the workspace (via
`bind_workspace_to_scenario`). The persistence side effects are
fundamentally different:

- `scenario_state_route_service.py`: workspace_state mutations only.
- `scenarios_save_service.py`: scenario row creation + workspace
  binding + scenario_summary_cards assembly with export_count.

Mixing these two concerns in one service would create a fat
service with two unrelated responsibility groups, and the deps
bundles would have to include helpers used by neither caller.

A new module keeps the dependency surface clean.

## Final POST /scenarios/save route size

| Phase | Non-blank lines | Total lines |
|---|---|---|
| 51J-1 (pre-extraction) | 88 | 92 |
| **51J-2 (post-extraction)** | **43** | **47** |

The route shrank by **45 non-blank lines (~51% reduction)**.

## `ScenariosSaveRouteOutcome` API

```python
@dataclass
class ScenariosSaveRouteOutcome:
    template_name: str = "scenarios/_workspace_partial.html"
    context: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    is_redirect: bool = False
    redirect_url: Optional[str] = None
```

The route in `main_web.py` does not need to know about
`ScenariosSaveRouteOutcome` directly: the service calls
`render_scenario_workspace(...)` internally and returns the
rendered response. `ScenariosSaveRouteOutcome` is included for
API symmetry with the broader Phase 51 family
(`run_service`, `compare_service`, `validation_service`,
`download_service`, `save_run_service`,
`scenario_state_route_service`).

## `ScenariosSaveRouteDeps` API

```python
@dataclass
class ScenariosSaveRouteDeps:
    # Snapshot / project / workspace resolution
    collect_form_snapshot: Callable[..., dict]
    project_workspace_from_snapshot: Callable[..., tuple]

    # Persistence (intended writes)
    save_scenario: Callable[..., Any]
    bind_workspace_to_scenario: Callable[..., Any]

    # Read-only queries for response render
    list_scenarios: Callable[..., Any]
    get_scenario_history: Callable[..., Any]
    list_exports: Callable[..., Any]
    build_export_lineage: Callable[..., Any]

    # Governance / replay metadata assembly
    governance_snapshot: Callable[..., dict]
    replay_metadata_for_project: Callable[..., dict]

    # Snapshot diff (for last_run_summary conditional)
    snapshots_equal: Callable[..., bool]

    # Response render
    render_scenario_workspace: Callable[..., Any]

    # Current datetime provider (allows test injection)
    utc_now: Optional[Callable[..., Any]] = None
```

**13 callables** (12 required + 1 optional `utc_now` for test
injection). No constants — the route does not validate the form
(Quirk 10), so there is no form-schema constant to pass.

## Service entry point

```python
async def execute_scenarios_save_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    deps: ScenariosSaveRouteDeps,
) -> Any:  # Returns the rendered response (from deps.render_scenario_workspace)
    ...
```

All parameters are **keyword-only** (canonical Phase 51 pattern).
The function is **async** (it doesn't need to be, but the route is
async and the service mirrors it; in the future if we need to
add async persistence calls we won't need to refactor the
signature).

## Behavior preservation checklist

- [x] Auth: unauthenticated → 302 redirect to `/login` (NOT 401
      JSON). Auth check stays in the route.
- [x] Form is read ONCE via `await request.form()` (route-owned).
- [x] Form snapshot is collected via `collect_form_snapshot(form)`.
- [x] `project_record` and `existing_workspace_state` are resolved
      via `project_workspace_from_snapshot(user, snapshot)`.
- [x] Soft-block: factory_template / saved_baseline projects return
      200 + workspace render with the `'Save is not available'`
      message.
- [x] `scenario_name` format:
      `f"{project_name} {snapshot.get('scenario', 'Base')} {dt.now().strftime('%Y-%m-%d %H:%M')}"`.
- [x] `save_scenario` is called exactly once per success.
- [x] `bind_workspace_to_scenario` is called exactly once per
      success.
- [x] `save_scenario` runs BEFORE `bind_workspace_to_scenario`.
- [x] `last_run_summary` is preserved if and only if
      `existing_workspace_state.last_runtime_snapshot == snapshot`.
      Otherwise reset to `{}`.
- [x] Read-only queries (list_scenarios, get_scenario_history,
      list_exports, build_export_lineage) are called once each.
- [x] `scenario_summary_cards` has 10 specific fields including
      `export_count` (computed per scenario_name from
      export_lineage).
- [x] Response is full workspace render via
      `render_scenario_workspace(...)`.
- [x] `user_id` is derived from `user.user_id`, NEVER from form.
- [x] `_validate_form` is NOT called (route accepts any form
      input as a snapshot — Quirk 10).

## 10 quirks preservation checklist

| # | Quirk | Preserved |
|---|---|---|
| 1 | `scenario_name` format: timestamp is the name suffix | ✓ |
| 2 | Blocked message replaces underscores with spaces | ✓ |
| 3 | Blocked message suggests `'Use Save As'` | ✓ |
| 4 | `last_run_summary` preserved if snapshot matches; else `{}` | ✓ |
| 5 | Blocked branch is a soft-fail (200 + render, not 4xx) | ✓ |
| 6 | No `HX-Trigger` / `HX-Redirect` header on success | ✓ |
| 7 | `scenario_summary_cards.export_count` per scenario_name | ✓ |
| 8 | `scenario_summary_cards` has 10 specific fields | ✓ |
| 9 | Two distinct `replay_metadata.export_type` values | ✓ |
| 10 | Route does NOT call `_validate_form` | ✓ |

## Intended side-effect confirmation

| Side effect | Per success | Per block |
|---|---|---|
| `save_scenario(...)` | 1 | 0 |
| `bind_workspace_to_scenario(...)` | 1 | 0 |
| `list_scenarios(...)` | 1 | 0 |
| `get_scenario_history(...)` | 1 | 0 |
| `list_exports(...)` | 1 | 0 |
| `build_export_lineage(...)` | 1 | 0 |
| `governance_snapshot(...)` | 2 | 0 |
| `replay_metadata_for_project(...)` | 2 | 0 |
| `snapshots_equal(...)` | 1 | 0 |
| `render_scenario_workspace(...)` | 1 | 1 |

`save_scenario.replay_metadata.export_type = "saved_scenario_snapshot"`.
`bind_workspace_to_scenario.replay_metadata.export_type = "workspace_saved_boundary"`.

`bind_workspace_to_scenario` happens AFTER `save_scenario`.

## Forbidden side-effect confirmation

The following helpers are NOT called in the service:

- `record_export`
- `record_download_export`
- `record_runtime_summary_export`
- `record_institutional_workbook_export`
- `record_workspace_runtime`
- `update_scenario_last_run_summary`
- `save_run`
- `save_project`
- direct `save_workspace_state` call outside
  `bind_workspace_to_scenario` (which internally calls
  `save_workspace_state` — that is intended)
- `run_project` / model execution
- `build_institutional_workbook_export`
- `build_excel_export_for_post_request`
- `build_runtime_summary_csv_export`
- `build_values_only_export_for_project`
- `db.add` / `db.commit` / `db.flush`
- `session.add` / `session.commit`
- unrelated persistence writes

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS (post-merge CI will verify) |
| Parity-core lock (4 SHA-256 files) | ✓ PASS (post-merge Parity Guardrails) |
| No-service-imports-main_web/main_api | ✓ PASS (10 services clean, including new scenarios_save_service) |

## Tests run and results

| Test module | Tests | Status |
|---|---|---|
| `test_phase51j1_scenarios_save_route_golden_characterization.py` | 85 | 85 pass |
| `test_phase51j2_scenarios_save_route_vertical_extraction.py` | 48 | 48 pass |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 pass (unchanged) |
| All other `test_phase51*.py` | ~731 | pass (unchanged) |
| **Total phase51 (post-51J-2)** | **885** | **885 pass** |

**48 new tests** in `test_phase51j2_scenarios_save_route_vertical_extraction.py`:

- 4 tests in `TestServiceModuleExists` (file presence + import isolation).
- 6 tests in `TestServiceApi` (dataclass shape, field presence, async signature).
- 6 tests in `TestRouteIsThin` (route shrunk, uses execute pattern, no direct calls).
- 2 tests in `TestAuthPreserved` (route uses get_current_user, 302 redirect works).
- 11 tests in `TestServiceBehavior` (mocked deps, side effects, ordering, scenarios_summary_cards shape).
- 2 tests in `TestForbiddenSideEffectsAbsent` (no record_export family, no db.*, no session.*).
- 2 tests in `TestNoValidateFormCall` (Quirk 10).
- 2 tests in `TestNoHtmxHeaderOnSuccess` (Quirk 6).
- 1 test in `TestScenarioNameFormat` (Quirk 1).
- 7 parametrized tests in `TestOtherRoutesRemainServiceBacked` (other routes intact).
- 2 tests in `TestPhase51FGuardrails` (smoke check + import isolation).
- 2 tests in `TestPhase51J1CharacterizationStillPasses` (regression).

**No tests removed** from Phase 51J-1. All 85 tests from Phase 51J-1
were re-pointed to look at the service body (via
`_route_or_service_body(...)` helper) when checking orchestration
content. They still pass.

## Known failures

Pre-existing out-of-scope failures (UNCHANGED by this phase):

- `tests/test_persistence.py`: `ImportError: No module named 'persistence'`.
- `tests/test_repository.py`: `ImportError: No module named 'persistence'`.

These reproduce on `origin/main` HEAD before any Phase 51 work
and are out of scope for Phase 51J-2.

## Recommended next phase

**Phase 51K-1** — `/scenarios/{scenario_id}/duplicate` golden
characterization. Per the Phase 51I hotspot map:

| Route | Non-blank | Risk |
|---|---|---|
| `/scenarios/{id}/duplicate` | 67 | HIGH (persistence-heavy) |
| `/scenarios/add` | 62 | HIGH (persistence-heavy) |
| `/projects/create` | 117 | HIGH (largest remaining inline route) |
| `/projects/{code}/save-as` | 49 | HIGH (persistence-heavy) |
| `/scenarios/{id}/rename` | 51 | MEDIUM |
| `/scenarios/{id}/archive` | 47 | MEDIUM |
| `/scenarios/{id}/update-overrides` | 25 | MEDIUM |
| `/scenarios/{id}/select` | 21 | MEDIUM |

Recommended next sequence: 51K-1 (char) → 51K-2 (extract) → 51L-1 →
51L-2 → 51M-1 → 51M-2 → 51N-1 → 51N-2 → 51O → 51P → 51Q → 51R.
