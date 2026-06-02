# Phase 51L-1 — POST /scenarios/add golden characterization

Phase 51L-1 is a characterization-only phase that pins the current
behavior of `POST /scenarios/add` (`add_scenario_endpoint`) in
`main_web.py` BEFORE the future 51L-2 vertical extraction.

## Route location and size

- **Route:** `POST /scenarios/add`
- **Handler:** `add_scenario_endpoint`
- **Location:** `main_web.py:2326-2397` (pre-extraction)
- **Total lines:** 72
- **Non-blank lines:** 62 (matches Phase 51I hotspot estimate)
- **Risk:** HIGH, persistence-heavy

## Auth/session behavior

- Auth check via `get_current_user(request)` (route-owned).
- Unauthenticated → 302 redirect to `/login` (NOT 401 JSON, NOT
  200 + render, NOT HX-Redirect). This is the canonical HTMX-
  redirect auth pattern.
- The auth check happens FIRST in the route body, before any
  other logic.

## Form input behavior

- The route reads the form via `await request.form()`.
- The route reads TWO individual form fields (NOT via
  `_collect_form_snapshot`):
  - `project_code = form.get("project_code", "").strip()`
  - `scenario_name = form.get("scenario_name", "").strip()`
- This is a behavior DIFFERENCE from `/scenarios/save` (which
  uses `collect_form_snapshot`) and `/scenarios/{id}/duplicate`
  (which is path-parameter-only). (Quirk 1.)
- Validation:
  - If `project_code` is empty → 400 JSON `{"error": "project_code is required"}`
  - If `scenario_name` is empty → 400 JSON `{"error": "scenario_name is required"}`

## user_id source

- `user_id` is derived from `user.user_id` (session-based).
- Never read from the form.
- All persistence calls take `user.user_id` as their user-scoping
  argument.

## Active project behavior

- `project_record` is resolved via
  `get_project_record(user_id=user.user_id, project_code=project_code)`.
- If `project_record is None` → 404 JSON `{"error": "Project not found"}`.
- If `project_record.project_origin != "user_created"` → 403
  JSON `{"error": "Add Scenario is only available for user-created projects"}`.
  (Quirk 8: only `user_created` projects can add scenarios.)

## Scenario creation behavior

The route creates a new non-base scenario inheriting from the
project's Base Case:

1. **Find the base case:** the route lists scenarios via
   `list_scenarios(user.user_id, project_id=project_record.project_id,
   include_archived=False)` and iterates to find the scenario with
   `is_base_case=True`.

2. **Fallback if no base case:** if no base case is found but
   other scenarios exist, the route promotes the OLDEST scenario
   to base case via:
   - `oldest = _get_least_created_scenario_for_project(user.user_id, project_record.project_id)`
   - `base_case = promote_scenario_to_base_case(user.user_id, oldest.scenario_id)`

3. **Create the new scenario:** the route calls `add_scenario(...)`
   with the following kwargs:
   - `user_id=user.user_id`
   - `project_id=project_record.project_id`
   - `project_code=project_record.project_code`
   - `scenario_name=scenario_name` (from form)
   - `parent_scenario_id=base_case.scenario_id`
   - `base_input_set=base_case.snapshot or base_case.base_input_set or {}`
     (Quirk 9: fallback chain)
   - `overrides={}` (Quirk 7: empty dict, user adds later)
   - `governance_state={}` (Quirk 6: empty dict, repository is source of truth)
   - `replay_metadata={"action": "add_scenario", "parent_scenario_id": base_case.scenario_id, "project_code": project_code}`
     (Quirk 5: uses `action` instead of `export_type`)

4. **Failure handling:** if `new_scenario is None` → 500 JSON
   `{"error": "Failed to create scenario"}`.

## Workspace/snapshot behavior

- After `add_scenario`, the route re-reads the scenarios list
  (with `limit=12`) and the workspace state for the render
  context. (Quirk 10: re-read scenarios to ensure the new
  scenario appears in the rendered scenario tab.)
- The render context is built via
  `_build_scenario_tab_context(user, project_record, scenarios, ws)`.

## replay_metadata behavior

- The `replay_metadata` dict has 3 fields:
  - `action="add_scenario"`
  - `parent_scenario_id=base_case.scenario_id`
  - `project_code=project_code`
- This is a behavior DIFFERENCE from `/scenarios/save` (which
  uses `export_type='saved_scenario_snapshot'`). (Quirk 5.)

## governance_state behavior

- The route passes `governance_state={}` (empty dict).
- The repository function `add_scenario` is the single source of
  truth for the new scenario's governance state. (Quirk 6.)

## Response behavior

- Success: `templates.TemplateResponse(request=request,
  name="partials/scenario_tab.html",
  context=_build_scenario_tab_context(user, project_record,
  scenarios, ws), headers={"HX-Trigger": "scenarioAdded"})`.
- 400 (missing project_code or scenario_name): JSON
  `{"error": "..."}` with status_code=400.
- 404 (project not found): JSON `{"error": "Project not found"}`
  with status_code=404.
- 403 (non-user_created project): JSON
  `{"error": "Add Scenario is only available for user-created projects"}`
  with status_code=403.
- 500 (add_scenario failure): JSON
  `{"error": "Failed to create scenario"}` with status_code=500.

## HTMX headers

- The success response emits `HX-Trigger: scenarioAdded`.
  (Quirk 2; different from `/scenarios/save` which emits no
  HX-Trigger, and `/save-run` which emits
  `HX-Trigger: refreshHistory`.)
- The 400/403/404/500 error responses are JSON and do NOT set
  HX-Trigger.

## Redirects/status codes

| Outcome | Status | Response |
|---|---|---|
| Unauth | 302 | Redirect to `/login` |
| Missing `project_code` | 400 | JSON `{"error": "project_code is required"}` |
| Missing `scenario_name` | 400 | JSON `{"error": "scenario_name is required"}` |
| Project not found | 404 | JSON `{"error": "Project not found"}` |
| Non-`user_created` project | 403 | JSON `{"error": "Add Scenario is only available for user-created projects"}` |
| `add_scenario` failure | 500 | JSON `{"error": "Failed to create scenario"}` |
| Success | 200 | TemplateResponse (`partials/scenario_tab.html`) with `HX-Trigger: scenarioAdded` |
| Other errors | (propagate) | FastAPI default 500 |

## Error/fallback behavior

- The route has 5 explicit error paths:
  - 400 (missing `project_code`)
  - 400 (missing `scenario_name`)
  - 404 (project not found)
  - 403 (non-`user_created` project)
  - 500 (`add_scenario` failure)
- The route does NOT wrap the body in a broad `except Exception:`.
  Other errors propagate to FastAPI's default 500 handling.
- The 302 redirect for unauthenticated requests is the canonical
  HTMX-redirect auth pattern.

## Intended side effects

Per success:

| Side effect | Count | Notes |
|---|---|---|
| `get_project_record(user_id=user.user_id, project_code=project_code)` | 1 | read |
| `list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False)` | 1 | read, for base case lookup |
| `_get_least_created_scenario_for_project(user.user_id, project_record.project_id)` | 0 or 1 | read, only if no base case |
| `promote_scenario_to_base_case(user.user_id, oldest.scenario_id)` | 0 or 1 | write, only if no base case |
| `add_scenario(...)` | 1 | write, the new scenario |
| `list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)` | 1 | read, for render context |
| `get_workspace_state(user.user_id, project_record.project_id)` | 1 | read |
| `templates.TemplateResponse(...)` | 1 | response render |

Per 400 (missing field), 403 (non-user_created), or 404 (project
not found): NONE of the persistence calls happen. The route
short-circuits with the JSON error.

Per 500 (add_scenario failure): `get_project_record` × 1,
`list_scenarios` × 1 (for base case lookup), `add_scenario` × 1,
then the route short-circuits with the 500 JSON.

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

## Behavior quirks (10 quirks to be preserved in 51L-2)

| # | Quirk |
|---|---|
| 1 | Form input: individual `form.get(...)` calls, NOT `_collect_form_snapshot` |
| 2 | `HX-Trigger: scenarioAdded` on success |
| 3 | Partial template render (`partials/scenario_tab.html`), NOT full workspace render |
| 4 | Fallback: promote oldest scenario to base case if none exists |
| 5 | `replay_metadata` uses `action="add_scenario"`, NOT `export_type` |
| 6 | `governance_state={}` (empty dict); repository is source of truth |
| 7 | `overrides={}` (empty dict); user adds later |
| 8 | Only `user_created` projects can add scenarios (403 otherwise) |
| 9 | `base_input_set` fallback chain: snapshot → base_input_set → `{}` |
| 10 | Re-read scenarios list after add (with `limit=12`) for render context |

## Recommended future 51L-2 extraction boundary

**Option A (recommended):** Create a new module
`app/services/scenarios_add_service.py` with:

- `@dataclass class ScenariosAddRouteOutcome`:
  - `template_name: str | None = None`
  - `context: dict = field(default_factory=dict)`
  - `payload: dict = field(default_factory=dict)` (for JSON errors)
  - `status_code: int = 200`
  - `headers: dict = field(default_factory=dict)` (e.g. `HX-Trigger: scenarioAdded`)
  - `is_redirect: bool = False`
  - `redirect_url: str | None = None`

- `@dataclass class ScenariosAddRouteDeps` with ~10 callables:
  - `get_project_record`
  - `list_scenarios`
  - `_get_least_created_scenario_for_project`
  - `promote_scenario_to_base_case`
  - `add_scenario`
  - `get_workspace_state`
  - `build_scenario_tab_context`
  - `render_template_response` (wraps `templates.TemplateResponse`)

- `async def execute_scenarios_add_route(*, request, form, user,
  deps) -> ScenariosAddRouteOutcome`.

**Why a separate module (not extending existing services):**

- `scenario_state_service.py` is data-layer only (no Request, no
  user, no auth).
- `scenario_state_route_service.py` handles workspace draft/discard
  mutations WITHOUT scenario row creation.
- `scenarios_save_service.py` is for `/scenarios/save` (creates
  from form snapshot).
- `scenario_duplicate_service.py` is for `/scenarios/{id}/duplicate`
  (copies existing ScenarioRecord).

`/scenarios/add` creates a new non-base scenario with parent
inheritance from the base case (a different concern). A new
module keeps the dependency surface clean.

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS (no change) |
| Parity-core lock (4 SHA-256 files) | ✓ PASS (no change) |
| No-service-imports-main_web/main_api | ✓ PASS (no change; route is unchanged in this phase) |

## Tests run and results

| Test module | Tests | Pass |
|---|---|---|
| `test_phase51l1_scenario_add_route_golden_characterization.py` | 86 | 86 |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 (unchanged) |
| Other phase51 tests | unchanged | pass |

## Known failures

Pre-existing out-of-scope failures (UNCHANGED by this phase):

- `tests/test_persistence.py`: `ImportError: No module named 'persistence'`.
- `tests/test_repository.py`: `ImportError: No module named 'persistence'`.

## Recommended next phase

**Phase 51L-2** (separate PR, NOT started by this batch) —
extract `POST /scenarios/add` into
`app/services/scenarios_add_service.py`. After 51L-2, the
remaining inline route families are:

- `/projects/create` (117 non-blank, HIGH risk, largest)
- `/projects/{project_code}/save-as` (49 non-blank, HIGH risk)
- `/scenarios/{scenario_id}/rename` (51 non-blank, MEDIUM)
- `/scenarios/{scenario_id}/archive` (47 non-blank, MEDIUM)
- `/scenarios/{scenario_id}/update-overrides` (25 non-blank, MEDIUM)
- `/scenarios/{scenario_id}/select` (21 non-blank, MEDIUM)

## Stack note

This PR is **stacked on Phase 51K-2 head** (`a00697b`), which
is in turn stacked on Phase 51K-1 head (`a24fdc8`). The
recommended merge order is:

1. **PR #400 (51K-1)** → merge into main first
2. **PR #401 (51K-2)** → merge into main second (re-target to
   main after #400 lands, or merge via K1 head)
3. **PR (this, 51L-1)** → merge into main last

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51L-1.**
