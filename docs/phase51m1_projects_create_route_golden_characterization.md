# Phase 51M-1 — POST /projects/create golden characterization

Phase 51M-1 is a characterization-only phase that pins the current
behavior of `POST /projects/create` (`create_project_route`) in
`main_web.py` BEFORE the future 51M-2 vertical extraction.

## Route location and size

- **Route:** `POST /projects/create`
- **Handler:** `create_project_route`
- **Location:** `main_web.py:1867-1992` (pre-extraction)
- **Total lines:** 126
- **Non-blank lines:** 117 (matches Phase 51I hotspot estimate)
- **Risk:** HIGH, largest remaining inline route

## Auth/session behavior

- Auth check via `get_current_user(request)` (route-owned).
- Unauthenticated → 302 redirect to `/login` (NOT 401 JSON, NOT
  200 + render, NOT HX-Redirect).
- The auth check happens FIRST in the route body, before any
  other logic.

## Form inputs

The route signature uses FastAPI `Form(...)` dependency injection
(NOT `await request.form()`):

- `project_name: str = Form(...)` (required)
- `project_type: str = Form(...)` (required)
- `template_source: str = Form("")` (default empty)
- `country_market: str = Form("Croatia")` (default)
- `capacity_mw: str = Form("")` (default empty)
- `cod_date: str = Form("")` (default empty)
- `construction_months: str = Form("")` (default empty)
- `horizon_years: str = Form("")` (default empty)
- `tariff_eur_mwh: str = Form("")` (default empty)
- `ppa_term_years: str = Form("")` (default empty)
- `p50_hours: str = Form("")` (default empty)
- `opex_y1_keur: str = Form("")` (default empty)
- `total_capex_keur: str = Form("")` (default empty)
- `gearing_pct: str = Form("")` (default empty)
- `interest_rate_pct: str = Form("")` (default empty)
- `tenor_years: str = Form("")` (default empty)
- `target_dscr: str = Form("1.20")` (default)

**18 form fields** total. (Quirk 1: FastAPI Form injection, NOT
`_collect_form_snapshot` or `await request.form()`.)

## user_id source

- `user_id` is derived from `user.user_id` (session-based).
- Never read from the form.
- All persistence calls take `user.user_id` as their user-scoping
  argument.

## Project creation behavior

The route orchestrates the project creation as follows:

1. **Initialize submitted dict** via
   `_submitted_new_project_defaults()` and override with the
   form values.
2. **Coerce text** via `_coerce_form_text(project_name)`.
3. **Canonicalize project type** via
   `_canonical_project_type(project_type)`.
4. **Normalize template source** via
   `_normalize_template_source(template_source, canonical_type)`.
5. **Validate payload** via
   `_validate_new_project_payload(submitted)`.
6. **Template validation:** if wind template but not Wind
   project type → validation error; if solar template but not
   Solar project type → validation error. (Quirk 6.)
7. **Slugify project code** via
   `_slugify_project_code(clean_name)`.
8. **Unique project code loop:** if `get_project_by_code` returns
   non-None, append `-2`, `-3`, ... until unique. (Quirk 4.)
9. **Build baseline snapshot** via
   `_project_baseline_snapshot(canonical_type, normalized_source)`.
10. **Apply required inputs** via
    `_apply_new_project_required_inputs(...)`.
11. **Create project record** via
    `create_project_record(...)` with:
    - `project_origin="user_created"` (Quirk 8)
    - `baseline_snapshot`
    - `governance_state=_governance_snapshot(project_code)`
    - `replay_metadata` with `export_type="project_record_created"`
12. **Save workspace state** via
    `save_workspace_state(...)` with:
    - `draft_snapshot=baseline_snapshot`
    - `saved_snapshot=baseline_snapshot`
    - `dirty=False` (no unsaved edits)
    - `governance_state=_governance_snapshot(project_code)`
    - `replay_metadata` with `export_type="workspace_project_created"`
13. **Return success response** via
    `templates.TemplateResponse(...)` with HX-Redirect header.

## Default scenario/workspace behavior

The route does NOT explicitly call `add_scenario(...)` or
`save_scenario(...)`. It only creates:
- `ProjectRecord` (via `create_project_record`)
- `WorkspaceState` (via `save_workspace_state` with
  `baseline_snapshot` for both `draft_snapshot` and
  `saved_snapshot`, and `dirty=False`)

The Base Case scenario is created later (via factory helpers
or on first `/scenarios/save`). (Quirk 9.)

## Project type/template behavior

The route validates that wind templates require Wind project
type, and solar templates require Solar project type:
- If `normalized_source in {"tuho", "generic_wind"}` AND
  `canonical_type != "Wind"`: validation error
  "Wind templates require project type Wind."
- If `normalized_source in {"oborovo", "generic_solar"}` AND
  `canonical_type != "Solar"`: validation error
  "Solar templates require project type Solar."

(Quirk 6.)

## replay_metadata behavior

The `replay_metadata` dict has different `export_type` values for
the two persistence calls:
- For `create_project_record`:
  `export_type="project_record_created"`.
- For `save_workspace_state`:
  `export_type="workspace_project_created"`.

(Quirk 5; different from `/scenarios/save` which uses
`export_type='saved_scenario_snapshot'`, and different from
`/scenarios/add` which uses `action="add_scenario"`.)

## governance_state behavior

The route passes `_governance_snapshot(project_code)` to both
`create_project_record` and `save_workspace_state` (called twice
per success).

## Response behavior

- Success: `templates.TemplateResponse(request=request,
  name="partials/new_project_result.html", context={
  "project_record": project_record, "template_source_label":
  _template_source_label(normalized_source)}, headers={
  "HX-Redirect": f"/?project={project_record.project_code}"})`.
- Validation error (400): `templates.TemplateResponse(
  request=request, name="partials/new_project_form.html",
  context=_new_project_validation_error_context(submitted,
  validation_errors), status_code=400)`.

## HTMX headers

- Success response emits `HX-Redirect:
  f"/?project={project_record.project_code}"` (Quirk 2;
  different from `/scenarios/save` which uses
  `HX-Trigger: scenarioAdded`).
- Validation error response does NOT emit `HX-Redirect` (it
  returns the form template with errors).

## Redirects/status codes

| Outcome | Status | Response |
|---|---|---|
| Unauth | 302 | Redirect to `/login` |
| Validation error | 400 | `partials/new_project_form.html` with errors |
| Success | 200 | `partials/new_project_result.html` with HX-Redirect |
| Other errors | (propagate) | FastAPI default 500 |

## Error/fallback behavior

- The route has 1 explicit error path: 400 validation error.
- The route does NOT wrap the body in a broad `except Exception:`.
- The 302 redirect for unauthenticated requests is the canonical
  HTMX-redirect auth pattern.

## Intended side effects

Per success:

| Side effect | Count | Notes |
|---|---|---|
| `_submitted_new_project_defaults` | 1 | baseline submitted dict |
| `_coerce_form_text` | 1 | text coercion |
| `_canonical_project_type` | 1 | type canonicalization |
| `_normalize_template_source` | 1 | template source normalization |
| `_validate_new_project_payload` | 1 | payload validation |
| `get_project_by_code` | 1+ | uniqueness loop (at least 1 call) |
| `_project_baseline_snapshot` | 1 | baseline build |
| `_apply_new_project_required_inputs` | 1 | apply required inputs |
| `create_project_record` | 1 | write, the project record |
| `save_workspace_state` | 1 | write, the workspace state |
| `_governance_snapshot` | 2 | read, save + workspace |
| `_replay_metadata_for_project` | 2 | read, save + workspace |
| `_template_source_label` | 1 | read, for render context |
| `templates.TemplateResponse` | 1 | response render |

Per 400 (validation error):
- `_submitted_new_project_defaults` × 1
- `_coerce_form_text` × 1
- `_canonical_project_type` × 1
- `_normalize_template_source` × 1
- `_validate_new_project_payload` × 1
- The route short-circuits with the 400 form template.

## Forbidden side effects

The following helpers are NOT called in the route:
- `record_export`
- `record_download_export`
- `record_runtime_summary_export`
- `record_institutional_workbook_export`
- `record_workspace_runtime`
- `update_scenario_last_run_summary`
- `save_run`
- `run_project` / model execution
- `build_institutional_workbook_export`
- `build_excel_export_for_post_request`
- `build_runtime_summary_csv_export`
- `build_values_only_export_for_project`
- `db.add` / `db.commit` / `db.flush`
- `session.add` / `session.commit`
- unrelated persistence writes

(Note: `save_workspace_state` IS called as an intended write to
initialize the workspace for the new project. This is NOT a
forbidden helper.)

## Behavior quirks (10 quirks to be preserved in 51M-2)

| # | Quirk |
|---|---|
| 1 | Uses FastAPI `Form(...)` parameters, NOT `await request.form()` or `_collect_form_snapshot` |
| 2 | `HX-Redirect: f"/?project={project_record.project_code}"` on success (Quirk 2) |
| 3 | Partial template render (`partials/new_project_result.html`), NOT full workspace render |
| 4 | Project code uniqueness loop with `-2`, `-3`, ... suffixes |
| 5 | `replay_metadata` uses `export_type` values: `project_record_created` and `workspace_project_created` |
| 6 | Template source validation: wind templates require Wind type, solar templates require Solar type |
| 7 | `save_workspace_state` with `draft = saved = baseline_snapshot`, `dirty=False` |
| 8 | `project_origin="user_created"` only; no gate for non-user_created |
| 9 | Does NOT explicitly call `add_scenario` or `save_scenario`; only creates ProjectRecord + WorkspaceState |
| 10 | `target_dscr` defaults to `"1.20"` |

## Recommended future 51M-2 extraction boundary

**Option A (recommended):** Create a new module
`app/services/projects_create_service.py` with:

- `@dataclass class ProjectsCreateRouteOutcome`:
  - `template_name: str | None = None`
  - `context: dict = field(default_factory=dict)`
  - `payload: dict = field(default_factory=dict)`
  - `status_code: int = 200`
  - `headers: dict = field(default_factory=dict)` (e.g.
    `{"HX-Redirect": f"/?project=..."}` on success)
  - `is_redirect: bool = False`
  - `redirect_url: str | None = None`

- `@dataclass class ProjectsCreateRouteDeps` with ~15 callables:
  - `get_project_by_code`
  - `create_project_record`
  - `save_workspace_state`
  - `_submitted_new_project_defaults` (or expose as a free
    function)
  - `_coerce_form_text`
  - `_canonical_project_type`
  - `_normalize_template_source`
  - `_validate_new_project_payload`
  - `_slugify_project_code`
  - `_project_baseline_snapshot`
  - `_apply_new_project_required_inputs`
  - `_governance_snapshot`
  - `_replay_metadata_for_project`
  - `_new_project_validation_error_context`
  - `_template_source_label`
  - `render_template_response`

- `async def execute_projects_create_route(*, request,
  submitted, user, deps) -> ProjectsCreateRouteOutcome`.

**Why a separate module** (not extending existing services):
- `scenario_state_service.py`: data-layer only.
- `scenarios_add_service.py`: for `/scenarios/add` (creates a
  new ScenarioRecord from form + base case). Project creation
  is a different concern (creates ProjectRecord + workspace
  state, no base case inheritance).
- `save_run_service.py`, `run_service.py`, etc.: unrelated.

A new module keeps the dependency surface clean.

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS (no change) |
| Parity-core lock (4 SHA-256 files) | ✓ PASS (no change) |
| No-service-imports-main_web/main_api | ✓ PASS (12 services clean, route is unchanged in this phase) |

## Tests run and results

| Test module | Tests | Pass |
|---|---|---|
| `test_phase51m1_projects_create_route_golden_characterization.py` | 92 | 92 |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 (unchanged) |
| Other phase51 tests | unchanged | pass |

## Known failures

Pre-existing out-of-scope failures (UNCHANGED by this phase):
- `tests/test_persistence.py`: `ImportError: No module named 'persistence'`.
- `tests/test_repository.py`: `ImportError: No module named 'persistence'`.

## Recommended next phase

**Phase 51M-2** (separate PR, NOT started by this batch) —
extract `POST /projects/create` into
`app/services/projects_create_service.py`. After 51M-2, the
remaining inline route families are:

- `/projects/{project_code}/save-as` (49 non-blank, HIGH risk)
- `/scenarios/{scenario_id}/rename` (51 non-blank, MEDIUM)
- `/scenarios/{scenario_id}/archive` (47 non-blank, MEDIUM)
- `/scenarios/{scenario_id}/update-overrides` (25 non-blank, MEDIUM)
- `/scenarios/{scenario_id}/select` (21 non-blank, MEDIUM)

## Stack note

This PR is **stacked on Phase 51L-2 head** (`88acb5a`). The
recommended merge order is:

1. **PR #405 (51L-2)** → merge into main first
2. **PR (this, 51M-1)** → merge into main second (re-target to
   main after #405 lands)
3. **PR (51M-2)** → merge into main last

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51M-1.**
