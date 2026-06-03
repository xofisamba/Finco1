# Phase 51M-2 — POST /projects/create route vertical extraction

> **Phase 51M-2** — vertical extraction of the `/projects/create`
> route family (single canonical POST route, handler
> `create_project_route`) into a new dedicated service module.

## Summary

**New module:** `app/services/projects_create_service.py` (392
lines, 16 callables).

**Service API:**

```python
@dataclass
class ProjectsCreateRouteOutcome:
    """Result of POST /projects/create orchestration.

    The route in main_web.py translates this into a FastAPI
    response via TemplateResponse(...) (success or validation
    error)."""
    template_name: str = "partials/new_project_result.html"
    context: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    is_redirect: bool = False
    redirect_url: Optional[str] = None

@dataclass
class ProjectsCreateRouteDeps:  # 16 callables
    submitted_new_project_defaults
    coerce_form_text
    canonical_project_type
    normalize_template_source
    validate_new_project_payload
    slugify_project_code
    get_project_by_code
    project_baseline_snapshot
    apply_new_project_required_inputs
    create_project_record
    save_workspace_state
    governance_snapshot
    replay_metadata_for_project
    new_project_validation_error_context
    template_source_label
    render_template_response

async def execute_projects_create_route(
    *,
    request: Any,
    submitted: dict,
    user: Any,
    deps: ProjectsCreateRouteDeps,
) -> ProjectsCreateRouteOutcome:
    ...
```

## Route thinned

| Metric | Pre-M2 | Post-M2 | Delta |
|---|---|---|---|
| `/projects/create` total lines | 126 | 98 | -28 (-22%) |
| `/projects/create` non-blank | 117 | 93 | -24 (-21%) |

The route in `main_web.py` is now a thin wrapper that:
1. Performs auth check (`get_current_user(request)`).
2. Receives 18 FastAPI `Form(...)` parameters.
3. Builds the `submitted` dict from `_submitted_new_project_defaults()`
   + form values.
4. Constructs a `ProjectsCreateRouteDeps` bundle (16 callables).
5. Calls `await execute_projects_create_route(...)`.
6. Translates the returned outcome into a `TemplateResponse`.

## Behaviors preserved (20, from Phase 51M-1)

1. POST /projects/create exists.
2. Auth check via `get_current_user(request)`.
3. Unauthenticated → 302 redirect to `/login`.
4. Form read via FastAPI `Form(...)` injection.
5. `submitted` dict built from `_submitted_new_project_defaults()` +
   form values.
6. `_coerce_form_text(submitted['project_name'])` coerces the
   project name.
7. `_canonical_project_type(submitted['project_type'])`
   canonicalizes the project type.
8. `_normalize_template_source(...)` normalizes the template
   source.
9. `_validate_new_project_payload(submitted)` validates the
   payload.
10. Template source validation: wind templates require Wind
    type; solar templates require Solar type.
11. `_slugify_project_code(clean_name)` slugifies the project
    code.
12. Project code uniqueness loop: if
    `deps.get_project_by_code(user.user_id, project_code)` returns
    non-None, append `-2`, `-3`, ... until unique.
13. `_project_baseline_snapshot(canonical_type,
    normalized_source)` builds the baseline snapshot.
14. `_apply_new_project_required_inputs(...)` applies required
    inputs.
15. `deps.create_project_record(...)` creates the ProjectRecord
    with `project_origin="user_created"`.
16. `deps.save_workspace_state(...)` initializes the workspace.
17. `deps.governance_snapshot(project_code)` is called twice
    (create + save).
18. `deps.replay_metadata_for_project(...)` is called twice with
    different `export_type` values.
19. Validation error (400): TemplateResponse with
    `partials/new_project_form.html`.
20. Success (200): TemplateResponse with
    `partials/new_project_result.html` and `HX-Redirect` header.

## Quirks preserved (10, from Phase 51M-1)

1. FastAPI `Form(...)` injection, NOT `await request.form()` or
   `_collect_form_snapshot`.
2. `HX-Redirect: f'/?project={project_record.project_code}'` on
   success.
3. Partial template render: `partials/new_project_result.html`,
   NOT full workspace render.
4. Project code uniqueness loop with `-2`, `-3`, ... suffixes.
5. `replay_metadata` uses `export_type` values:
   - `project_record_created` (for `create_project_record`)
   - `workspace_project_created` (for `save_workspace_state`)
6. Template source validation: wind templates require Wind type;
   solar templates require Solar type.
7. `save_workspace_state` with `draft=saved=baseline_snapshot`,
   `dirty=False`.
8. `project_origin="user_created"` only; no gate for non-
   user_created (no 403 path).
9. Does NOT explicitly call `add_scenario` or `save_scenario`;
   only creates ProjectRecord + WorkspaceState.
10. `target_dscr` defaults to `"1.20"`.

## Intended persistence side effects (preserved)

| Side effect | Count | Notes |
|---|---|---|
| `get_project_by_code` | 1+ | Uniqueness loop |
| `create_project_record` | 1 | ProjectRecord creation |
| `save_workspace_state` | 1 | WorkspaceState init |
| `governance_snapshot` | 2 | Once per write |
| `replay_metadata_for_project` | 2 | Different export_type |
| `template_source_label` | 1 | Render label |

## Forbidden side effects (absent)

- `record_export` / `record_download_export` /
  `record_runtime_summary_export` /
  `record_institutional_workbook_export` /
  `record_workspace_runtime`
- `update_scenario_last_run_summary`
- `save_run` / `run_project` (no model execution)
- `build_institutional_workbook_export` /
  `build_excel_export_for_post_request` /
  `build_runtime_summary_csv_export` /
  `build_values_only_export_for_project`
- Direct `db.add` / `db.commit` / `db.flush`
- Direct `session.add` / `session.commit`
- `add_scenario` / `save_scenario` / `create_scenario` (Quirk 9)
- `_collect_form_snapshot` / `await request.form()` (Quirk 1)

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS |
| Parity-core lock (4 SHA-256 files) | ✓ PASS |
| No-service-imports-main_web/main_api | ✓ PASS |

The new `projects_create_service.py` module does NOT import
`main_web` or `main_api`. The 12-service inventory is clean.

## Tests

| Module | Tests | Pass | Notes |
|---|---|---|---|
| `test_phase51m2_projects_create_route_vertical_extraction.py` (new) | 58 | 58 | All passed |
| `test_phase51m1_projects_create_route_golden_characterization.py` (re-pointed) | 92 | 92 | All passed |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 | All passed |

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51M-2.**

## Why a separate service module

- `scenario_state_service.py` is data-layer only.
- `scenario_state_route_service.py` is for workspace draft/discard
  mutations, NOT project creation.
- `scenarios_save_service.py` is for `/scenarios/save` (new
  scenario from form snapshot).
- `scenarios_add_service.py` is for `/scenarios/add` (new
  scenario with parent inheritance from base case).
- `scenario_duplicate_service.py` is for
  `/scenarios/{id}/duplicate` (copy existing scenario).
- None of the above handle ProjectRecord creation. The new
  `projects_create_service.py` is the right place for that.

## Recommendation

**Ready for merge.** Characterization-only constraints satisfied.
No production code outside the route + new service changed. No
forbidden side effects. All 10 quirks preserved. All 92/58 tests
pass. Phase 51F guardrails green.

Backend remains source of truth. rc1 remains frozen.
