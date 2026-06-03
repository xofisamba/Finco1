# Phase 51K-1 — POST /scenarios/{scenario_id}/duplicate golden characterization

Phase 51K-1 is a characterization-only phase that pins the current
behavior of `POST /scenarios/{scenario_id}/duplicate`
(`duplicate_scenario_endpoint`) in `main_web.py` BEFORE the 51K-2
vertical extraction.

## Route location and size

- **Route:** `POST /scenarios/{scenario_id}/duplicate`
- **Handler:** `duplicate_scenario_endpoint`
- **Location:** `main_web.py:2248-2320` (pre-extraction)
- **Total lines:** 73
- **Non-blank lines:** 67 (matches Phase 51I hotspot estimate)
- **Risk:** HIGH, persistence-heavy

## Auth/session behavior

- Auth check via `get_current_user(request)` (route-owned).
- Unauthenticated → 302 redirect to `/login` (NOT 401 JSON, NOT
  200 + render, NOT HX-Redirect). This is the canonical HTMX-
  redirect auth pattern.
- The auth check happens FIRST in the route body, before any
  other logic.

## Path parameter behavior

- Route signature:
  `async def duplicate_scenario_endpoint(request: Request, scenario_id: str)`.
- `scenario_id` is the path parameter from the URL.
- `scenario_id` is passed to:
  - `get_scenario(scenario_id, user.user_id)` — for original lookup.
  - `duplicate_scenario(user.user_id, scenario_id)` — for the
    duplication call.
- The path parameter is NOT a form field. The route does NOT call
  `await request.form()` (Quirk 8).

## user_id source

- `user_id` is derived from `user.user_id` (session-based).
- Never read from the form (no form input at all).
- All persistence calls take `user.user_id` as their user-scoping
  argument.

## Active project behavior

- `project_record` is resolved via
  `get_project_by_code(user.user_id, original.project_code)`.
- All read-only queries use `original.project_id` (not
  `project_record.project_id` — they are equivalent but the route
  uses the field on the original scenario).
- The route does NOT call `get_active_project(...)` or similar —
  the active project is implicit in the scenario lookup.

## Active scenario behavior

- The route does NOT explicitly track an "active scenario" beyond
  the original.
- After duplicate_scenario, the workspace is rendered with the
  current scenarios list (which now includes the duplicate).
- There is no `set_active_scenario` call — the duplicate is
  available via the scenario list.

## Original scenario lookup behavior

- `original = get_scenario(scenario_id, user.user_id)`.
- If `original is None`, the route returns
  `JSONResponse({"error": "Scenario not found"}, status_code=404)`.
- This is the ONLY explicit error path in the route. Other errors
  propagate to FastAPI's default 500.
- `get_scenario` is called exactly once.

## Duplicate scenario naming/coding

- The route does NOT construct a new `scenario_name` (unlike
  `/scenarios/save` which builds one as
  `f"{project_name} {snapshot.get('scenario', 'Base')} {dt.now().strftime('%Y-%m-%d %H:%M')}"`).
- The route delegates the duplicate naming to the repository
  function `duplicate_scenario(user.user_id, scenario_id)`, which
  is the single source of truth for the duplicate's name and code.
- The repository function may append a "(copy)" or "(copy N)"
  suffix (or similar) to disambiguate. The exact naming
  convention is the repository's responsibility.

## Snapshot/workspace behavior

- `workspace_state` is resolved inline in the
  `_render_scenario_workspace` call:
  `get_workspace_state(user.user_id, original.project_id)`.
- It is NOT stored in a separate variable. (Quirk 5.)
- The route does NOT write a new snapshot or update the
  workspace_state directly — the repository function
  `duplicate_scenario` handles all persistence.

## Scenario/project persistence behavior

Intended persistence calls (per success):

- `get_scenario(scenario_id, user.user_id)` × 1 (read, lookup).
- `duplicate_scenario(user.user_id, scenario_id)` × 1 (write, the
  duplication).
- `get_project_by_code(user.user_id, original.project_code)` × 1
  (read, project resolution).
- `list_scenarios(user.user_id, project_id=original.project_id,
  include_archived=False, limit=12)` × 1 (read, for response
  render).
- `get_scenario_history(user.user_id, project_id=..., limit=20)` × 1.
- `list_exports(user.user_id, project_id=..., limit=8)` × 1.
- `build_export_lineage(user.user_id, project_id=..., limit=8)` × 1.
- `get_workspace_state(user.user_id, original.project_id)` × 1.

If `get_scenario` returns `None`, NONE of the above write/read
calls after the None check are made. The route short-circuits with
the 404 JSON.

## replay_metadata behavior

- The route does NOT pass `replay_metadata` to `duplicate_scenario`.
- The repository function `duplicate_scenario` is the single source
  of truth for the duplicate's metadata.
- This is a behavior DIFFERENCE from `/scenarios/save` (which
  passes `export_type='saved_scenario_snapshot'`) and from
  `/scenarios/state/draft` (which passes full replay metadata).
- (Quirk 1.)

## governance_state behavior

- The route does NOT call `_governance_snapshot` or
  `governance_snapshot(...)`. (Quirk 4.)
- The repository function `duplicate_scenario` is the single
  source of truth for the duplicate's governance state.

## Response behavior

- Success: full workspace HTML render via
  `_render_scenario_workspace(request, user, project_record,
  get_workspace_state(user.user_id, original.project_id),
  scenarios, history, exports, export_lineage,
  scenario_summary_cards, message=...)`.
- The render call has 9 positional args + 1 keyword arg
  (`message=...`).
- 404 (scenario not found): JSON `{"error": "Scenario not found"}`
  with status code 404.
- The 404 response does NOT use HTMX headers or redirect.

## HTMX headers

- The success response does NOT set `HX-Trigger` or `HX-Redirect`.
- The 404 response does NOT set `HX-Trigger` or `HX-Redirect`.
- The full workspace render is returned as-is, not as an HTMX
  partial. (Quirk 9.)

## Redirects/status codes

| Outcome | Status | Response |
|---|---|---|
| Unauth | 302 | Redirect to `/login` |
| Scenario not found | 404 | JSON `{"error": "Scenario not found"}` |
| Success | 200 | Full workspace render |
| Other errors | (propagate) | FastAPI default 500 |

## Error/fallback behavior

- The only explicit error path is the 404 JSON (Scenario not
  found).
- The route does NOT wrap the body in a broad `except Exception:`.
  Other errors propagate to FastAPI's default 500 handling.
- The 302 redirect for unauthenticated requests is the canonical
  HTMX-redirect auth pattern.

## Intended side effects

Per success:

| Side effect | Count | Notes |
|---|---|---|
| `get_scenario(scenario_id, user.user_id)` | 1 | read, lookup |
| `duplicate_scenario(user.user_id, scenario_id)` | 1 | write, the duplication |
| `get_project_by_code(user.user_id, original.project_code)` | 1 | read |
| `list_scenarios(user.user_id, project_id=..., include_archived=False, limit=12)` | 1 | read |
| `get_scenario_history(user.user_id, project_id=..., limit=20)` | 1 | read |
| `list_exports(user.user_id, project_id=..., limit=8)` | 1 | read |
| `build_export_lineage(user.user_id, project_id=..., limit=8)` | 1 | read |
| `get_workspace_state(user.user_id, original.project_id)` | 1 | read |
| `_render_scenario_workspace(...)` | 1 | response render |

Per 404 (scenario not found):

| Side effect | Count |
|---|---|
| `get_scenario(scenario_id, user.user_id)` | 1 |
| All other persistence calls | 0 |
| `JSONResponse(...)` | 1 |

## Forbidden side effects

The following helpers are NOT called in the route:

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
- unrelated persistence writes

## Behavior quirks (10 quirks to be preserved in 51K-2)

| # | Quirk |
|---|---|
| 1 | `duplicate_scenario` is called WITHOUT `replay_metadata` (different from `/scenarios/save`) |
| 2 | 404 response is JSON, NOT HTML, NOT redirect, NOT template render |
| 3 | Success message is `f"Duplicated {original.scenario_name}."` (with period) |
| 4 | The route does NOT call `_governance_snapshot` (different from `/scenarios/save`) |
| 5 | `workspace_state` is resolved inline in the render call, not stored in a variable |
| 6 | `scenario_summary_cards` has 10 specific fields (same shape as `/scenarios/save`) |
| 7 | `scenario_summary_cards.export_count` is computed per `scenario_name` from `export_lineage` |
| 8 | The route is path-parameter-only; no `await request.form()` (different from `/scenarios/save`) |
| 9 | The route does NOT emit `HX-Trigger` or `HX-Redirect` (full workspace render) |
| 10 | The route is currently inline orchestration (no service pattern yet) |

## Recommended 51K-2 extraction boundary

**Option A (recommended):** Create a new module
`app/services/scenario_duplicate_service.py` with:

- `@dataclass class ScenarioDuplicateRouteOutcome`:
  - `template_name: str | None = None`
  - `context: dict = field(default_factory=dict)`
  - `payload: dict = field(default_factory=dict)` (for 404 JSON)
  - `status_code: int = 200`
  - `headers: dict = field(default_factory=dict)`
  - `is_redirect: bool = False`
  - `redirect_url: str | None = None`

- `@dataclass class ScenarioDuplicateRouteDeps` with 9 callables:
  - `get_scenario: Callable[..., Any]`
  - `duplicate_scenario: Callable[..., Any]`
  - `get_project_by_code: Callable[..., Any]`
  - `list_scenarios: Callable[..., Any]`
  - `get_scenario_history: Callable[..., Any]`
  - `list_exports: Callable[..., Any]`
  - `build_export_lineage: Callable[..., Any]`
  - `get_workspace_state: Callable[..., Any]`
  - `render_scenario_workspace: Callable[..., Any]`

- `async def execute_scenario_duplicate_route(*, request,
  scenario_id, user, deps) -> ScenarioDuplicateRouteOutcome`.
  - The function returns the rendered workspace on success or a
    JSONResponse-like payload on 404.

**Why a separate module (not extending existing services):**

- `scenario_state_service.py` is data-layer only (no Request, no
  user, no auth). Adding route orchestration would mix concerns.

- `scenario_state_route_service.py` handles workspace draft/discard
  mutations WITHOUT scenario row creation. Duplicate creates a new
  ScenarioRecord (via `duplicate_scenario`); this is a different
  concern.

- `scenarios_save_service.py` is for `/scenarios/save` (creates a
  new ScenarioRecord from form snapshot). Duplicate copies an
  existing ScenarioRecord; different concern.

A new module keeps the dependency surface clean and aligned with
the Phase 51B/51C-2/51D-2/51E-2/51G-2/51H-2/51J-2 canonical
pattern.

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS (no change) |
| Parity-core lock (4 SHA-256 files) | ✓ PASS (no change) |
| No-service-imports-main_web/main_api | ✓ PASS (no change; route is unchanged in this phase) |

## Tests run and results

| Test module | Tests | Pass |
|---|---|---|
| `test_phase51k1_scenario_duplicate_route_golden_characterization.py` | 80 | 80 |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 (unchanged) |
| Other phase51 tests | ~827 | pass (unchanged) |
| **Total phase51 (post-51K-1)** | **~928** | **~928** |

## Known failures

Pre-existing out-of-scope failures (UNCHANGED by this phase):

- `tests/test_persistence.py`: `ImportError: No module named 'persistence'`.
- `tests/test_repository.py`: `ImportError: No module named 'persistence'`.

## Recommended next phase

**Phase 51K-2** — extract `POST /scenarios/{scenario_id}/duplicate`
into `app/services/scenario_duplicate_service.py`. Follow the
Phase 51B/51C-2/51D-2/51E-2/51G-2/51H-2/51J-2 canonical pattern.

After 51K-2, the next inline route family is
`POST /scenarios/add` (62 non-blank, HIGH risk). Phase 51L-1 will
characterize `/scenarios/add`.

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51K-1.**
