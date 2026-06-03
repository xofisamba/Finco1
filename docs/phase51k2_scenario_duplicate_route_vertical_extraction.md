# Phase 51K-2 — POST /scenarios/{scenario_id}/duplicate vertical extraction

Phase 51K-2 extracts the orchestration body of
`POST /scenarios/{scenario_id}/duplicate` from `main_web.py` into a
new route-orchestration service module:
`app/services/scenario_duplicate_service.py`. The route handler in
`main_web.py` is now a thin wrapper that handles auth, path
parameter, deps bundle construction, and the final response
translation (success → response; 404 → JSONResponse).

## What moved to `scenario_duplicate_service.py`

The full orchestration body that previously lived inline in
`duplicate_scenario_endpoint` in `main_web.py`:

- `original = get_scenario(scenario_id, user.user_id)` lookup.
- 404 early return: if `original is None`, return
  `ScenarioDuplicateRouteOutcome` with `status_code=404` and
  `payload={"error": "Scenario not found"}`.
- `duplicate_scenario(user.user_id, scenario_id)` call (Quirk 1:
  no replay_metadata, no governance_state — the repository
  function is the single source of truth).
- `project_record = get_project_by_code(user.user_id,
  original.project_code)` resolution.
- Read-only queries: `list_scenarios`, `get_scenario_history`,
  `list_exports`, `build_export_lineage` (each called once per
  success).
- `scenario_summary_cards` assembly with 10 specific fields
  including `export_count` (computed per scenario_name from
  export_lineage).
- `workspace_state` resolution inline in the render call
  (`get_workspace_state(user.user_id, original.project_id)`,
  Quirk 5).
- `render_scenario_workspace(...)` call (with success message
  `f"Duplicated {original.scenario_name}."`).

## What stayed in `main_web.py`

- The `@app.post("/scenarios/{scenario_id}/duplicate")` decorator
  and the `duplicate_scenario_endpoint` function signature.
- The `get_current_user(request)` auth check (302 redirect to
  `/login` if unauth).
- Local import of the service module (one-way import direction).
- Construction of the `ScenarioDuplicateRouteDeps` instance with
  the 9 callables from main_web module scope.
- Final `await execute_scenario_duplicate_route(...)` call.
- Translation of the result: pass-through if it's a FastAPI
  response (success path) or convert to `JSONResponse` (404 path).

## Why `scenario_state_service.py` was NOT extended

`scenario_state_service.py` is data-layer only. It does not take
`Request`, scenario_id, or auth arguments. It exposes 4 pure
helpers used by the route orchestration:

- `build_workspace_state_metadata`
- `scenario_provenance_for_record`
- `resolve_runtime_snapshot`
- `RuntimeSnapshotResolution`
- `check_runtime_allowed`

Adding route orchestration (auth, deps bundle, 404 handling, etc.)
to this module would mix data-layer and route-orchestration
concerns, increase import-cycle risk, and complicate test
isolation.

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

`/scenarios/{scenario_id}/duplicate`, by contrast, calls
`duplicate_scenario` (which COPIES an existing `ScenarioRecord`).
The persistence side effect is fundamentally different from
draft/discard.

## Why `scenarios_save_service.py` was NOT reused

`scenarios_save_service.py` is for `/scenarios/save` (creates a
new `ScenarioRecord` from a form snapshot). `/scenarios/{id}/
duplicate` copies an EXISTING `ScenarioRecord`. Different concern:

- Save: `save_scenario(...)` with a snapshot dict.
- Duplicate: `duplicate_scenario(...)` (no kwargs, no replay_metadata).

Mixing these in one service would create a fat service with two
unrelated responsibility groups.

## Final POST /scenarios/{scenario_id}/duplicate route size

| Phase | Non-blank lines | Total lines |
|---|---|---|
| 51K-1 (pre-extraction) | 67 | 73 |
| **51K-2 (post-extraction)** | **58** | **65** |

Note: the route non-blank count includes a 12-line docstring
explaining the thin-route pattern. The actual code is
approximately 30 non-blank lines (auth + deps bundle + service
call + result translation). The 51K-1 hotspot estimate of 67
non-blank is now down by ~9 lines (with the large docstring
absorbing the rest).

## `ScenarioDuplicateRouteOutcome` API

```python
@dataclass
class ScenarioDuplicateRouteOutcome:
    template_name: str = "scenarios/_workspace_partial.html"
    context: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    is_redirect: bool = False
    redirect_url: Optional[str] = None
```

The service returns the outcome for the 404 path (not-found
scenario) and returns the rendered response directly for the
success path (via `deps.render_scenario_workspace(...)`).

## `ScenarioDuplicateRouteDeps` API

```python
@dataclass
class ScenarioDuplicateRouteDeps:
    # Original scenario lookup
    get_scenario: Callable[..., Any]

    # Persistence (intended write)
    duplicate_scenario: Callable[..., Any]

    # Project resolution
    get_project_by_code: Callable[..., Any]

    # Read-only queries for response render
    list_scenarios: Callable[..., Any]
    get_scenario_history: Callable[..., Any]
    list_exports: Callable[..., Any]
    build_export_lineage: Callable[..., Any]

    # Workspace state resolution
    get_workspace_state: Callable[..., Any]

    # Response render
    render_scenario_workspace: Callable[..., Any]
```

**9 callables**. No constants — the route is path-parameter-only
(Quirk 8) and does not validate the form.

## Service entry point

```python
async def execute_scenario_duplicate_route(
    *,
    request: Any,
    scenario_id: str,
    user: Any,
    deps: ScenarioDuplicateRouteDeps,
) -> Any:  # Returns the rendered response (success) or
            # ScenarioDuplicateRouteOutcome (404 not found)
    ...
```

All parameters are **keyword-only** (canonical Phase 51 pattern).
The function is **async**.

## Behavior preservation checklist (20 behaviors)

- [x] Auth: unauth → 302 redirect to `/login` (NOT 401 JSON)
- [x] `get_current_user(request)` is the auth check
- [x] `scenario_id` is the path parameter
- [x] `scenario_id` is passed to `get_scenario(scenario_id, user.user_id)`
- [x] `scenario_id` is passed to `duplicate_scenario(user.user_id, scenario_id)`
- [x] `user_id` derived from `user.user_id` (NEVER from form)
- [x] `get_scenario` called exactly once per request
- [x] `duplicate_scenario` called exactly once per success (after None check)
- [x] If `original is None` → 404 JSON `{"error": "Scenario not found"}`
- [x] `project_record` resolved via
      `get_project_by_code(user.user_id, original.project_code)`
- [x] Read-only queries (list_scenarios, get_scenario_history,
      list_exports, build_export_lineage) called once each
- [x] `scenario_summary_cards` has 10 specific fields including
      `export_count`
- [x] `workspace_state` resolved inline in the render call
- [x] No `replay_metadata` passed to `duplicate_scenario` (Quirk 1)
- [x] No `_governance_snapshot` call (Quirk 4)
- [x] Success response is full workspace render via
      `render_scenario_workspace(...)`
- [x] 404 response is JSON
- [x] No `HX-Trigger` / `HX-Redirect` headers
- [x] Success message is `f"Duplicated {original.scenario_name}."`
- [x] No broad `except Exception:` in the route

## 10 quirks preservation checklist

| # | Quirk | Preserved |
|---|---|---|
| 1 | `duplicate_scenario` called WITHOUT `replay_metadata` | ✓ |
| 2 | 404 response is JSON, NOT HTML / NOT redirect / NOT template | ✓ |
| 3 | Success message is `f"Duplicated {original.scenario_name}."` | ✓ |
| 4 | Route does NOT call `_governance_snapshot` | ✓ |
| 5 | `workspace_state` resolved inline in render call | ✓ |
| 6 | `scenario_summary_cards` has 10 specific fields | ✓ |
| 7 | `scenario_summary_cards.export_count` per scenario_name | ✓ |
| 8 | Route is path-parameter-only; no `await request.form()` | ✓ |
| 9 | No `HX-Trigger` / `HX-Redirect` header | ✓ |
| 10 | Route uses `execute_scenario_duplicate_route(...)` | ✓ |

## Intended side-effect confirmation

| Side effect | Per success | Per 404 |
|---|---|---|
| `get_scenario(scenario_id, user.user_id)` | 1 | 1 |
| `duplicate_scenario(user.user_id, scenario_id)` | 1 | 0 |
| `get_project_by_code(user.user_id, original.project_code)` | 1 | 0 |
| `list_scenarios(user.user_id, project_id=..., include_archived=False, limit=12)` | 1 | 0 |
| `get_scenario_history(user.user_id, project_id=..., limit=20)` | 1 | 0 |
| `list_exports(user.user_id, project_id=..., limit=8)` | 1 | 0 |
| `build_export_lineage(user.user_id, project_id=..., limit=8)` | 1 | 0 |
| `get_workspace_state(user.user_id, original.project_id)` | 1 | 0 |
| `render_scenario_workspace(...)` | 1 | 0 |
| `JSONResponse(...)` (404) | 0 | 1 |

No `replay_metadata` or `governance_state` is passed to
`duplicate_scenario` (Quirks 1 and 4).

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
- `run_project` / model execution
- `build_institutional_workbook_export`
- `build_excel_export_for_post_request`
- `build_runtime_summary_csv_export`
- `build_values_only_export_for_project`
- `db.add` / `db.commit` / `db.flush`
- `session.add` / `session.commit`
- `_validate_form` (route is path-parameter-only; Quirk 8)
- `await request.form()` (Quirk 8)

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS (no change) |
| Parity-core lock (4 SHA-256 files) | ✓ PASS (no change) |
| No-service-imports-main_web/main_api | ✓ PASS (11 services clean) |

## Tests run and results

| Test module | Tests | Pass |
|---|---|---|
| `test_phase51k1_scenario_duplicate_route_golden_characterization.py` | 80 | 80 |
| `test_phase51k2_scenario_duplicate_route_vertical_extraction.py` | 44 | 44 |
| `test_phase51i_route_extraction_checkpoint_hotspot_map.py` | 63 | 63 |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 |

**124 new tests** (K1 + K2 combined). All 11 phase51 service
modules verified clean (no main_web or main_api imports).

## Known failures

Pre-existing out-of-scope failures (UNCHANGED by this phase):

- `tests/test_persistence.py`: `ImportError: No module named 'persistence'`.
- `tests/test_repository.py`: `ImportError: No module named 'persistence'`.

## Recommended next phase

**Phase 51L-1** — `/scenarios/add` golden characterization (62
non-blank, HIGH risk, persistence-heavy).
