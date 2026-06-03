# Phase 51O-2 — POST /projects/{project_code}/save-as route vertical extraction

> **Phase 51O-2** — vertical extraction of the
> `/projects/{project_code}/save-as` route family
> (single canonical POST route, handler
> `save_project_as_endpoint`) into a new dedicated service module.

## Summary

**New module:** `app/services/project_save_as_service.py`
(~11,700 bytes, 9 callables).

**Service API:**

```python
@dataclass
class ProjectSaveAsRouteOutcome:
    """Result of POST /projects/{project_code}/save-as orchestration.

    The route in main_web.py translates this into a FastAPI
    response via RedirectResponse(...) (success or auth) or
    JSONResponse(...) (404 / 400)."""
    template_name: str = ""
    context: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    is_redirect: bool = False
    redirect_url: Optional[str] = None

@dataclass
class ProjectSaveAsRouteDeps:  # 9 callables
    get_project_record
    save_project
    save_workspace_state
    now_utc
    project_record_creation_governance_state
    workspace_state_initialization_governance_state
    build_project_replay_metadata
    build_workspace_replay_metadata
    is_already_user_project

async def execute_project_save_as_route(
    *,
    request: Any,
    project_code: str,
    user: Any,
    deps: ProjectSaveAsRouteDeps,
) -> ProjectSaveAsRouteOutcome:
    ...
```

## Route thinned

| Metric | Pre-O-2 (M1) | Post-O-2 (51O-2) | Delta |
|---|---|---|---|
| `/projects/{code}/save-as` total lines | 51 | 67 | +16 (+31%) |
| `/projects/{code}/save-as` non-blank | 49 | 58 | +9 (+18%) |

> **Note:** The route did NOT shrink significantly because the
> extraction kept the inline helper functions in the route
> (`_project_record_creation_governance_state`,
> `_workspace_state_initialization_governance_state`,
> `_build_project_replay_metadata`,
> `_build_workspace_replay_metadata`, `_is_already_user_project`).
> The **orchestration body** (the actual `save_project(...)` and
> `save_workspace_state(...)` calls with their kwargs, plus the
> `new_code`/`new_name` computation, plus the gate check, plus the
> redirect_url construction) has moved to the service.
>
> The route is now 5 lines of orchestration glue (auth + service
> call + outcome translation), down from 49 lines of mixed
> orchestration.

## Behaviors preserved (16, from Phase 51O-1)

1. POST /projects/{project_code}/save-as exists.
2. Auth check via `get_current_user(request)`.
3. Unauthenticated → 302 redirect to `/login`.
4. Path parameter `project_code`: target project to duplicate.
5. Source project lookup: `get_project_record(user_id, project_code)`.
6. 404 if source not found.
7. 400 if source.project_origin == "user_created".
8. new_code = f"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}"
9. new_name = f"{source.project_name} (Copy)"
10. save_project creates new record with project_origin="user_created",
    is_readonly=False, last_run_summary={}.
11. save_workspace_state initializes workspace from
    source.baseline_snapshot, draft=saved=baseline, dirty=False.
12. Both calls inject governance_state dict with g20=BLOCKED,
    r99_r102=NOT_APPROVED, lender_ready=False.
13. replay_metadata.export_type: "project_duplicated" (save_project)
    and "workspace_duplicated" (save_workspace_state).
14. Response: 302 redirect to /?project={new_code}.
15. No HTMX-specific headers (no HX-Trigger, no HX-Redirect).
16. No model execution. No exports.

## Quirks preserved (10, from Phase 51O-1)

1. Local import `from app.persistence.repository import
   get_project_record as gpr` (now in the route; the route passes
   `gpr` to `deps.get_project_record`).
2. new_code = f"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}"
3. new_name = f"{source.project_name} (Copy)"
4. governance_state dict inlined twice (route has two helper
   functions; service receives the dicts via deps).
5. baseline_source is a computed boolean:
   source.project_origin == "saved_baseline" (in route helper).
6. last_run_summary={} (in service call).
7. draft_snapshot=saved_snapshot=source.baseline_snapshot
   (in service call).
8. 400 path returns JSONResponse (route translates outcome).
9. 404 path returns JSONResponse with formatted error.
10. Success returns 302 RedirectResponse (route translates outcome).

## Intended persistence side effects (preserved)

| Side effect | Count | Notes |
|---|---|---|
| `deps.get_project_record` | 1 | Source lookup |
| `deps.save_project` | 1 | New ProjectRecord creation |
| `deps.save_workspace_state` | 1 | New WorkspaceState init |

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
- `add_scenario` / `save_scenario` / `create_scenario`
- `_collect_form_snapshot` / `await request.form()` (this route
  uses path params only, no form)

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✓ PASS |
| Parity-core lock (4 SHA-256 files) | ✓ PASS |
| No-service-imports-main_web/main_api | ✓ PASS |

The new `project_save_as_service.py` module does NOT import
`main_web` or `main_api`. The 14-service inventory is clean.

## Tests

| Module | Tests | Pass | Notes |
|---|---|---|---|
| `test_phase51o2_project_save_as_route_vertical_extraction.py` (new) | 49 | 49 | All passed |
| `test_phase51o1_project_save_as_route_golden_characterization.py` (re-pointed) | 84 | 84 | All passed |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 | All passed |

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51O-2.**

## Why a separate service module

- `projects_create_service.py` handles `/projects/create` (new
  project from form snapshot, with template validation and 18
  form fields). Different concern.

- `scenario_state_service.py` is data-layer only (no Request, no
  form, no auth).

- `scenario_state_route_service.py` handles workspace
  draft/discard mutations. Different concern.

- `scenarios_save_service.py` is for `/scenarios/save`. Different
  concern.

- `scenario_duplicate_service.py` is for
  `/scenarios/{id}/duplicate`. Different concern.

- `scenarios_add_service.py` is for `/scenarios/add`. Different
  concern.

The new `project_save_as_service.py` is the right place for the
project-copy/save-as orchestration.

## Recommendation

**Ready for merge.** Behavior preserved exactly. No production
code changes outside the route + new service. No forbidden side
effects. All 10 quirks preserved. All 49+84+21=154 tests pass.
Phase 51F guardrails remain green.

Backend remains source of truth. rc1 remains frozen.
