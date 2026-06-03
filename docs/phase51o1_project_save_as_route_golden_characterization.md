# Phase 51O-1 — POST /projects/{project_code}/save-as route golden characterization

> **Phase 51O-1** — golden characterization (Agent A).
> Pins current behavior of `POST /projects/{project_code}/save-as`
> (`save_project_as_endpoint`) in `main_web.py` BEFORE the future
> 51O-2 vertical extraction.

## Summary

- **Path:** `POST /projects/{project_code}/save-as`
- **Handler:** `save_project_as_endpoint`
- **Location:** `main_web.py` (route body, 49 non-blank lines)
- **Risk:** **HIGH** (project copy/save-as semantics, dual-write,
  governance_state injection)

## Behavior summary (16 categories)

### 1. Route existence

- `POST /projects/{project_code}/save-as` exists in main_web.py.
- Handler `save_project_as_endpoint(request: Request, project_code: str)`.
- No form body (path param only).

### 2. Auth/session behavior

- Auth check via `get_current_user(request)`.
- Unauthenticated → 302 redirect to `/login`.

### 3. Path parameter behavior

- `project_code: str` is the path parameter.
- Used in source project lookup: `gpr(user_id=user.user_id, project_code=project_code)`.

### 4. Source project lookup

- Local import: `from app.persistence.repository import get_project_record as gpr`.
- Calls `gpr(user_id=user.user_id, project_code=project_code)`.
- If `source is None` → 404 JSONResponse with `f"Project '{project_code}' not found"`.

### 5. Already-user-project gate

- If `source.project_origin == "user_created"` → 400 JSONResponse `"Already a user project"`.

### 6. new_code / new_name behavior

- `new_code = f"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}"`
- `new_name = f"{source.project_name} (Copy)"`
- Uses `_now_utc()` for the timestamp.

### 7. save_project call (intended write #1)

- `save_project(user_id=..., project_code=new_code, project_name=new_name, project_type=source.project_type, project_origin="user_created", source_project_template=source.source_project_template, template_source=source.template_source, baseline_snapshot=source.baseline_snapshot, is_readonly=False, governance_state=..., last_run_summary={}, replay_metadata=...)`
- `project_origin="user_created"` (the new record is always user-editable).
- `is_readonly=False` (always editable).
- `last_run_summary={}` (empty dict, no run yet).
- `governance_state` inlined dict: `{"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False}`.

### 8. replay_metadata for save_project

- `export_type: "project_duplicated"`
- `source_project_code: project_code`
- `source_project_origin: source.project_origin`
- `baseline_source: source.project_origin == "saved_baseline"` (note: this is a computed boolean, not a static value)

### 9. save_workspace_state call (intended write #2)

- `save_workspace_state(user_id=..., project_id=new_record.project_id, project_code=new_record.project_code, draft_snapshot=source.baseline_snapshot, saved_snapshot=source.baseline_snapshot, dirty=False, governance_state=..., replay_metadata=...)`
- `draft_snapshot=saved_snapshot=source.baseline_snapshot` (new workspace starts clean).
- `dirty=False`.

### 10. replay_metadata for save_workspace_state

- `export_type: "workspace_duplicated"`
- `source_project_code: project_code`
- `baseline_source: source.project_origin == "saved_baseline"`

### 11. Response behavior

- Success → 302 `RedirectResponse(url=f"/?project={new_code}", status_code=302)`.
- 404 → `JSONResponse({"error": f"Project '{project_code}' not found"}, status_code=404)`.
- 400 → `JSONResponse({"error": "Already a user project"}, status_code=400)`.
- No `templates.TemplateResponse` used.

### 12. HTMX headers

- No `HX-Trigger`, no `HX-Redirect`. The 302 redirect is a regular RedirectResponse.

### 13. Forbidden side effects (all absent)

- `record_export` family (record_export, record_download_export, record_runtime_summary_export, record_institutional_workbook_export, record_workspace_runtime)
- `update_scenario_last_run_summary`
- `save_run`, `run_project`, model execution
- `build_institutional_workbook_export`, `build_excel_export_for_post_request`, `build_runtime_summary_csv_export`, `build_values_only_export_for_project`
- `add_scenario`, `save_scenario`, `create_scenario`
- Direct `db.add`, `db.commit`, `db.flush`, `session.add`, `session.commit`

### 14. Intended persistence side effects

| Side effect | Count | Notes |
|---|---|---|
| `gpr` (alias for `get_project_record`) | 1 | Source lookup |
| `save_project` | 1 | New ProjectRecord creation |
| `save_workspace_state` | 1 | New WorkspaceState init |

### 15. Behavior quirks (10)

| # | Quirk | Description |
|---|---|---|
| 1 | Local import | `from app.persistence.repository import get_project_record as gpr` inside the function body (not at module top) |
| 2 | new_code pattern | `f"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}"` — uses `now` (not `now.isoformat()` or similar) |
| 3 | new_name pattern | `f"{source.project_name} (Copy)"` — exactly "(Copy)" suffix |
| 4 | governance_state inlined twice | Same dict literal appears for both `save_project` and `save_workspace_state` — not a helper function |
| 5 | baseline_source computed | `baseline_source: source.project_origin == "saved_baseline"` is a computed boolean, not a static value. Factory templates get `baseline_source=False` |
| 6 | last_run_summary={} | Empty dict, not None. The duplicated project has no prior run |
| 7 | draft_equals_saved | `draft_snapshot=saved_snapshot=source.baseline_snapshot` — new workspace is clean |
| 8 | 400 path uses JSONResponse | "Already a user project" returns JSONResponse, not a friendly UI |
| 9 | 404 path uses JSONResponse | "Project not found" returns JSONResponse with formatted error |
| 10 | Success uses 302 redirect | Not HX-Redirect. Different from /projects/create (which uses HX-Redirect) |

### 16. Recommended 51O-2 extraction boundary

**New module:** `app/services/project_save_as_service.py`

**Public dataclasses:**

- `@dataclass class ProjectSaveAsRouteOutcome`
  - `template_name: str = "partials/new_project_result.html"` (or similar; route still doesn't render)
  - `context: dict`
  - `payload: dict`
  - `status_code: int`
  - `headers: dict`
  - `is_redirect: bool` (True for the 302 success path)
  - `redirect_url: Optional[str]` (e.g., `f"/?project={new_code}"`)

- `@dataclass class ProjectSaveAsRouteDeps` (~9 callables)
  - `get_project_record` (was `gpr`)
  - `save_project`
  - `save_workspace_state`
  - `now_utc` (or `now_utc_factory` returning a callable)
  - `project_record_creation_governance_state` (returns the inlined dict)
  - `workspace_state_initialization_governance_state` (returns the inlined dict)
  - `build_project_replay_metadata` (computes the replay_metadata for save_project)
  - `build_workspace_replay_metadata` (computes the replay_metadata for save_workspace_state)
  - `is_already_user_project` (returns bool: source.project_origin == "user_created")

**Service entry point:**

```python
async def execute_project_save_as_route(
    *,
    request: Any,
    project_code: str,
    user: Any,
    deps: ProjectSaveAsRouteDeps,
) -> ProjectSaveAsRouteOutcome:
    ...
```

**Expected route thinned:** 49 → ~30 non-blank (~-40%).

## Phase 51F guardrail status

- Engine-output golden (TUHO + Oborovo): unchanged
- Parity-core lock (4 SHA-256 files): unchanged
- No-service-imports-main_web/main_api: N/A for 51O-1 (no service yet)

## Tests

- 84 tests in `tests/test_phase51o1_project_save_as_route_golden_characterization.py`
- All passed in 51O-1 development

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched in Phase 51O-1.**

## Recommendation

**Ready for 51O-2 extraction.** Characterization complete. No
ambiguous behavior, no latent bugs, no unclear persistence boundary.
The route is HIGH-risk because of the dual-write semantics
(`save_project` + `save_workspace_state` together) and the inlined
governance_state dict (replicated twice). 51O-2 must preserve both
calls and both governance_state dicts exactly.
