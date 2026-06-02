# Phase 51E-1 — /download route golden characterization

## Base SHA

`c9144f2f4975a55a1428f79b8abae3ffaf8b8aa5` (origin/main @ PR #385 merge,
Phase 51 Closeout — route service extraction summary and residual
main_web hotspot map)

## Objective

Characterize the current `POST /download` and `GET /download` route
behavior before any extraction. This is characterization only. No
production code changes, no refactor, no extraction. The goal is to
pin the current contract (structural + behavioral) so that Phase
51E-2 can extract the orchestration into
`app/services/download_service.py` (or split into the existing
`app/services/export_service.py` /
`app/services/export_audit_service.py`) with confidence that
behavior is preserved.

This phase follows the same pattern as Phase 51A (`/run` golden),
Phase 51C-1 (`/compare` golden), and Phase 51D-1 (`/validate`
golden). `/run`, `/compare`, and `/validate` are now extracted and
serve as canonical templates. `/download` is the largest residual
main_web.py hotspot (~131 non-blank lines across POST + GET).

## Current route size

| Variant | Location | Total lines | Non-blank lines |
|---|---|---|---|
| `POST /download` | `main_web.py:1582` | 109 | 106 |
| `GET /download` | `main_web.py:1721` | 65 | 65 |
| **Combined `/download` route family** | `main_web.py:1582..1785` | **174** | **171** |

This is the largest route family in `main_web.py` (followed by
`POST /save-run` at ~125 non-blank and `POST /scenarios/save` at
~86 non-blank). `/download` is a "leaf-like" route — it has no model
execution, no scenario loop, and the heavy lifting is already
delegated to the export services.

## Route responsibilities

### `POST /download` (`main_web.py:1582`)

`POST /download` generates an Excel export using **current form
values** (the user has filled in the form and clicks "Download
Excel"). It uses the project workspace resolution to determine the
runtime origin (factory_base_runtime / saved_state / user_created)
and selects the appropriate project_key (TUHO / Oborovo / Solar /
Wind) for model execution via `run_demo_project(...)`.

1. **Auth redirect** — `get_current_user(request)` →
   `RedirectResponse("/login", 302)` if unauthenticated.
2. **Form parsing** — reads 12 form fields (project_type, scenario,
   capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur,
   opex_y1_keur, gearing_pct, target_dscr, interest_rate_pct,
   tenor_years).
3. **Schema build + override construction** — calls
   `_build_schema_from_form(...)` and `build_projectinputs(schema)`
   for the form-driven path. On `ValueError` (or broad `Exception`),
   returns `HTMLResponse(..., status_code=400)` with an inline error
   page.
4. **Snapshot + project/workspace resolution** — calls
   `_collect_form_snapshot(form)` and
   `_project_workspace_from_snapshot(user, snapshot)`.
5. **Runtime origin branching** — for `user_created` projects:
   - calls `check_runtime_allowed(workspace_state, snapshot)`. If
     guard blocks, returns `HTMLResponse(..., status_code=400)`.
   - calls `_resolve_runtime_snapshot_source(...)` to get the
     resolved snapshot, scenario record, warning, and effective
     runtime origin.
   - rebuilds `override = build_projectinputs_from_snapshot(runtime_snapshot)`.
   - sets `runtime_project_key = "Solar" if canonical == "Solar"
     else "Wind"`.
   For non-user_created projects:
   - if `runtime_origin == "saved_state" and
     workspace_state.active_scenario_id`, also calls
     `_resolve_runtime_snapshot_source(...)` and rebuilds
     override.
   - else, normalizes template source
     (`_normalize_template_source(...)`) and selects
     `runtime_project_key ∈ {"TUHO", "Oborovo", "Solar", "Wind"}`.
6. **Model execution** — `demo = run_demo_project(runtime_project_key, scenario, project_inputs_override=override)`.
7. **Provenance + replay metadata** — builds
   `scenario_provenance = _scenario_provenance_for_record(...)` and
   `replay_metadata = _replay_metadata_for_project(...)` with
   `export_type="excel_model_export"`,
   `workbook_type="values_only_excel_export"`, current timestamps,
   `runtime_origin`, scenario info, and the runtime snapshot /
   template_origin_override.
8. **Baseline source flag** — if
   `project_record.project_origin == "saved_baseline"`, sets
   `replay_metadata["baseline_source"] = True`.
9. **Excel generation** — `export = build_excel_export_for_post_request(result=demo.result, project_inputs=demo.project_inputs, project_type=project_type, scenario=scenario, runtime_origin=runtime_origin, replay_metadata=replay_metadata)`.
10. **Export error check** — if `export.has_error()`, returns
    `HTMLResponse(content=export.error_content, status_code=export.status_code)`.
11. **Audit recording** — calls `record_download_export(user_id, project_code, export_type="excel_model_export", artifact_name=filename, artifact_path=f"/download?project_type={project_type}&scenario={scenario}", project_id=..., governance_state=_governance_snapshot(project_code), replay_metadata=replay_metadata, scenario_id=active_scenario_record.scenario_id if active_scenario_record else None)`.
12. **Streaming response** — returns `StreamingResponse(iter([excel_bytes]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Length": str(len(excel_bytes))})`.
13. **Top-level error catch** — wraps steps 3-12 in a `try/except
    Exception`; on exception, returns
    `HTMLResponse(content=f"<html><body><h2>Excel generation failed</h2><p>{str(e)}</p><a href='/'>Back</a></body></html>", status_code=500)`.

### `GET /download` (`main_web.py:1721`)

`GET /download` generates an Excel export using **factory defaults**
(ignores form state). It always uses `project_type` and `scenario`
query parameters (default `"Solar"` / `"Base"`).

1. **Auth redirect** — same as POST.
2. **Defaults** — `project_type` and `scenario` are query params with
   defaults `"Solar"` / `"Base"` (with empty-string fallbacks to
   defaults inside the route).
3. **Model execution** — `demo = run_demo_project(project_type, scenario)` (no
   `project_inputs_override`).
4. **Project code resolution** — `project_code = "oborovo" if
   project_type.lower() == "solar" else "tuho"` (string mapping,
   not from the user's project list).
5. **Project record lookup** — `project_record =
   get_project_by_code(user.user_id, project_code)`. May be `None`
   if no project exists with that code.
6. **Filename** — `filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"`.
7. **Replay metadata** — `_replay_metadata_for_project(project_code, export_type="excel_model_export", workbook_type="values_only_excel_export", export_timestamp=utc_now_iso(), runtime_timestamp=utc_now_iso(), project_id=project_record.project_id if project_record else None, scenario_name=scenario, runtime_origin="factory_base_runtime", artifact_name=filename)`.
8. **Baseline source flag** — same as POST.
9. **Excel generation** — `export = build_values_only_export_for_project(demo.result, demo.project_inputs, project_type, scenario, replay_metadata=replay_metadata)`.
10. **Export error check** — same as POST.
11. **Audit recording** — same as POST, but `scenario_id=None`
    (no active scenario record in the GET path).
12. **Streaming response** — `StreamingResponse(iter([export.bytes_data]), media_type=export.media_type, headers={"Content-Disposition": f'attachment; filename="{export.filename}"', "Content-Length": str(len(export.bytes_data))})`.
13. **Top-level error catch** — same as POST.

## Dependency / helper map

| Helper | Used in POST | Used in GET | Source |
|---|---|---|---|
| `get_current_user` | yes | yes | `main_web.py:199` (route-owned) |
| `RedirectResponse` | yes | yes | `fastapi.responses` |
| `_collect_form_snapshot` | yes | no | `main_web.py:265` |
| `_project_workspace_from_snapshot` | yes | no | `main_web.py:986` |
| `check_runtime_allowed` | yes (user_created branch) | no | `app.services.scenario_state_service` (imported) |
| `_resolve_runtime_snapshot_source` | yes (user_created + saved_state branches) | no | `main_web.py:1005` |
| `_canonical_project_type` | yes (project_key resolution) | no | `main_web.py:232` |
| `_normalize_template_source` | yes (non-user_created branch) | no | `main_web.py:236` |
| `_build_schema_from_form` | yes (step 3) | no | `main_web.py:1117` |
| `_scenario_provenance_for_record` | yes (step 7) | no | `main_web.py:1002` |
| `_replay_metadata_for_project` | yes (step 7) | yes (step 7) | `main_web.py:857` |
| `_governance_snapshot` | yes (audit step 11) | yes (audit step 11) | `main_web.py:218` |
| `build_projectinputs` | yes (step 3) | no | `app.input_adapter` (imported) |
| `build_projectinputs_from_snapshot` | yes (runtime_snapshot paths) | no | `app.input_adapter` (imported) |
| `run_demo_project` | yes (step 6) | yes (step 3) | `app.ui_runner.run_demo_project` (imported) |
| `get_project_by_code` | no (POST uses snapshot path) | yes | `app.persistence.repository` (imported) |
| `build_excel_export_for_post_request` | yes (step 9) | no | `app.services.export_service` (imported) |
| `build_values_only_export_for_project` | no | yes (step 9) | `app.services.export_service` (imported) |
| `record_download_export` | yes (step 11) | yes (step 11) | `app.services.export_audit_service` (imported) |
| `utc_now_iso` | yes (step 7) | yes (step 7) | `app.persistence.provenance.utc_now_iso` (imported) |
| `HTMLResponse` | yes (error paths) | yes (error paths) | `fastapi.responses` |
| `StreamingResponse` | yes (step 12) | yes (step 12) | `fastapi.responses` |

## Response / header / file behavior

### `POST /download`

* **Success**: `StreamingResponse` with:
  - `media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`
  - `Content-Disposition: attachment; filename="fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"`
  - `Content-Length: {len(excel_bytes)}`
  - body: `iter([excel_bytes])` (1-element iterator)
* **Validation error (step 3)**: `HTMLResponse(content="<html><body><h2>Excel generation failed</h2><p>Invalid input: {e}</p><a href='/'>Back</a></body></html>", status_code=400)`.
* **Runtime guard block (user_created)**: `HTMLResponse(content="<html><body><h2>Excel generation failed</h2><p>{guard_message}</p><a href='/'>Back</a></body></html>", status_code=400)`.
* **Export has error**: `HTMLResponse(content=export.error_content, status_code=export.status_code)`.
* **Top-level exception**: `HTMLResponse(content="<html><body><h2>Excel generation failed</h2><p>{e}</p><a href='/'>Back</a></body></html>", status_code=500)`.

### `GET /download`

* **Success**: `StreamingResponse` with:
  - `media_type=export.media_type` (from the export object, may differ from POST's hardcoded string)
  - `Content-Disposition: attachment; filename="{export.filename}"` (filename from export object, not constructed in the route)
  - `Content-Length: {len(export.bytes_data)}`
  - body: `iter([export.bytes_data])`
* **Export has error**: same as POST.
* **Top-level exception**: same as POST.

## Audit / provenance behavior

`/download` has **intended export audit side effects** (this is
**NOT** forbidden persistence; it is the Phase 49 export audit /
provenance behavior). On every successful download, the route calls
`record_download_export(...)` with:

- `user_id=user.user_id`
- `project_code=project_code` (from project_record in POST; from
  string mapping in GET)
- `export_type="excel_model_export"`
- `artifact_name=filename` (constructed in route, e.g.
  `"fincogpt_solar_base.xlsx"`)
- `artifact_path=f"/download?project_type={project_type}&scenario={scenario}"`
  (a string describing the URL, NOT an actual filesystem path)
- `project_id=project_record.project_id if project_record else None`
- `governance_state=_governance_snapshot(project_code)`
- `replay_metadata=replay_metadata`
- `scenario_id=active_scenario_record.scenario_id if active_scenario_record else None` (POST) or `None` (GET)

`record_download_export` is the **only** persistence write on the
`/download` path. There are NO calls to:

- `record_workspace_runtime` (only `/run`)
- `record_compare_run` (does not exist)
- `record_export` (does not exist as a direct call — see below)
- `update_scenario_last_run_summary` (only `/run`)
- `db.add` / `db.commit` / `db.flush` / `session.add` /
  `session.commit`

`record_export(...)` does NOT appear as a function call in
`main_web.py` (verified by structural inspection: `grep -c
"record_export(" main_web.py` returns 0). The "record export"
operations are split into three purpose-specific helpers in
`app.services.export_audit_service`:

- `record_runtime_summary_export` (used by `/run` / `partials/runtime_summary.html`)
- `record_institutional_workbook_export` (used by institutional workbook route)
- `record_download_export` (used by `/download`)

This naming is intentional and preserved from Phase 49. The Phase
49 guardrail `main_web.has_zero_direct_record_export_calls` in
`tests/test_phase51*.py` already pins this.

## Read / write side effects

| Side effect | POST | GET | Classified as |
|---|---|---|---|
| `record_download_export` call | yes (1 per success) | yes (1 per success) | **intended export audit** (preserved) |
| `run_demo_project` (in-memory model run) | yes (project_inputs_override=override) | yes (no override) | **read-only model exec** |
| `db.add` / `db.commit` / etc. | no | no | n/a |
| `record_workspace_runtime` | no | no | n/a |
| `record_compare_run` | n/a (does not exist) | n/a | n/a |
| `update_scenario_last_run_summary` | no | no | n/a |

`/download` is **read-then-write** in a narrow sense: the model
runs in memory (no side effect) and the export audit is recorded
(intended). The route does NOT mutate the workspace state, scenario
state, or runtime snapshot.

## Runtime / project / scenario state dependencies

### `POST /download` runtime origin branches

The route explicitly branches on `runtime_origin` to determine the
project_key and override construction:

```
project_record.project_origin == "user_created":
    allow_run, runtime_origin, guard_message = check_runtime_allowed(...)
    if not allow_run: return HTMLResponse 400
    runtime_snapshot, _, _, effective_runtime_origin = _resolve_runtime_snapshot_source(...)
    override = build_projectinputs_from_snapshot(runtime_snapshot)
    runtime_project_key = "Solar" if canonical == "Solar" else "Wind"
else:
    if runtime_origin == "saved_state" and workspace_state.active_scenario_id:
        runtime_origin = "saved_state"
        runtime_snapshot, _, _, effective_runtime_origin = _resolve_runtime_snapshot_source(...)
        override = build_projectinputs_from_snapshot(runtime_snapshot)
    runtime_seed = _normalize_template_source(...)
    if runtime_seed == "tuho": runtime_project_key = "TUHO"
    elif runtime_seed == "oborovo": runtime_project_key = "Oborovo"
    else: runtime_project_key = "Solar" if canonical == "Solar" else "Wind"
```

The `runtime_origin` variable is **mutated inside the non-user_created
branch** (`runtime_origin = "saved_state"` if the active scenario
exists). The `effective_runtime_origin` returned by
`_resolve_runtime_snapshot_source` is captured but **not used** in
the POST path. (This is similar to the Phase 51D-1 /validate
runtime-snapshot parity quirk — though the value IS passed to
`build_excel_export_for_post_request` as `runtime_origin=runtime_origin`.)

### `GET /download` runtime origin

The GET path **always uses** `runtime_origin="factory_base_runtime"`
in the replay metadata. There is no branching; the path always
uses factory defaults.

## Error / fallback behavior

| Trigger | Response | Status |
|---|---|---|
| Unauthenticated | `RedirectResponse("/login")` | 302 |
| Schema build failure (POST) | `HTMLResponse("...Invalid input: {e}...")` | 400 |
| Runtime guard block (POST, user_created) | `HTMLResponse("...{guard_message}...")` | 400 |
| Export has error (both) | `HTMLResponse(content=export.error_content, status_code=export.status_code)` | per export |
| Top-level exception (both) | `HTMLResponse("...Excel generation failed...")` | 500 |

The error HTML is **inline** in the route (a simple `<html><body>`
with an "Excel generation failed" heading and a "Back" link). There
is **no template** for download errors.

## Behavior quirks to preserve

1. **POST has TWO template branches for project_key resolution**:
   - user_created: `"Solar"` or `"Wind"` based on
     `_canonical_project_type(...)`.
   - template-seeded: `"TUHO"`, `"Oborovo"`, or fallback
     `"Solar"`/`"Wind"` based on `_normalize_template_source(...)`
     then `_canonical_project_type(...)`.

2. **GET has HARDCODED project_code mapping**:
   `project_code = "oborovo" if project_type.lower() == "solar" else
   "tuho"`. This is a quirk — the GET path does not use
   `_project_workspace_from_snapshot` and does not consult the
   user's actual project list. (It is what it is; preserve.)

3. **POST mutates `runtime_origin`** in the non-user_created
   branch when active_scenario_id is set. The original
   `runtime_origin` from `check_runtime_allowed` is overwritten with
   `"saved_state"`. The mutated value is passed to
   `build_excel_export_for_post_request` as `runtime_origin`.

4. **GET uses different export service**:
   - POST: `build_excel_export_for_post_request(...)`
   - GET: `build_values_only_export_for_project(...)`

5. **POST uses hardcoded `media_type`** for the StreamingResponse:
   `"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`.
   **GET uses `export.media_type`** from the export object (which
   may differ — pinned by the export service).

6. **POST constructs filename in the route**:
   `f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"`. **GET
   uses `export.filename`** from the export object.

7. **GET always passes `scenario_id=None`** to
   `record_download_export`. POST passes the active scenario's id
   (or `None` if no active scenario).

8. **Inline error HTML** in both routes (no Jinja template for
   download errors). The error HTML uses `<html><body><h2>Excel
   generation failed</h2><p>{e}</p><a href='/'>Back</a></body></html>`.

9. **Top-level `except Exception`** is broad; on any uncaught
   exception, returns 500 with the inline error page. The POST
   version uses a slightly different prefix ("Invalid input:") in
   the schema-build catch (step 3), but the outer try uses the
   generic "Excel generation failed" string.

10. **`artifact_path` is a string describing the URL** (e.g.
    `"/download?project_type=Solar&scenario=Base"`), not a
    filesystem path. This is used by `record_download_export` for
    audit trail purposes only.

11. **POST `runtime_origin` from `check_runtime_allowed` is
    partially captured and partially ignored**. The returned
    `runtime_origin` is used in `runtime_origin` for the
    `runtime_origin == "saved_state" and
    workspace_state.active_scenario_id` check and as the
    `runtime_origin` arg to `build_excel_export_for_post_request`,
    but the **fourth element** of the
    `_resolve_runtime_snapshot_source` return tuple
    (`effective_runtime_origin`) is discarded. This is a similar
    pattern to the Phase 51D-1 /validate runtime-snapshot parity
    quirk. **Document and preserve.**

12. **The broad `except (ValueError, Exception) as e:`** on the
    schema-build step is preserved as-is (this is the same
    overly-broad except as in /compare). It's not great, but it is
    what the route does today.

## Recommended extraction boundary for Phase 51E-2

Two options are considered; the choice depends on whether
extraction should be a NEW service module or a split into existing
service modules.

### Option A: New `app/services/download_service.py`

A new service module that owns the entire `/download` orchestration
body for both POST and GET. Mirror the Phase 51B/51C-2/51D-2
pattern:

```python
@dataclass
class DownloadRouteOutcome:
    # Either a StreamingResponse payload or an HTMLResponse payload
    response: Response
    # OR:
    streaming_payload: Optional[bytes] = None
    media_type: Optional[str] = None
    headers: Optional[dict] = None
    error_html: Optional[str] = None
    error_status: int = 200
    is_html_error: bool = False
```

This is slightly awkward because the route returns either a
`StreamingResponse` (success) or an `HTMLResponse` (error). Two
approaches:

- A1 (response-style): pass a `Response` object across the service
  boundary (couples service to FastAPI).
- A2 (dataclass-style): pass a structured payload (`bytes_data`,
  `media_type`, `headers`, OR `error_html` + `error_status`); the
  route translates to a FastAPI `Response`.

A2 is the Phase 51 canonical pattern. Recommended.

### Option B: Split into existing `export_service.py` and `export_audit_service.py`

This is more invasive but more architecturally clean. The orchestration
body in `/download` could be partially absorbed into:

- `export_service.py` (already owns `build_excel_export_for_post_request`
  and `build_values_only_export_for_project`) — could add a
  `build_download_response_for_post_request` or similar that takes
  the model result + project_inputs + form + workspace context and
  returns a `DownloadResponse` (with bytes, media_type, filename,
  error_html).
- `export_audit_service.py` (already owns `record_download_export`)
  — could add a `record_download_for_post_request` or similar that
  takes the post-context and records the audit.

This is cleaner but requires more refactoring of the existing
export services. **Not recommended for Phase 51E-2** because it
expands the scope of the change beyond "extract the route body into
a service". A future phase could consolidate the export services.

### Recommendation

**Option A (new `app/services/download_service.py`) is recommended
for Phase 51E-2.** It mirrors the established Phase 51B/51C-2/51D-2
pattern and minimizes the scope of the change. Option B can be
considered as a future consolidation phase (e.g. Phase 51K or
later) once the route-level pattern is fully proven.

The recommended `DownloadRouteDeps` bundle:

```python
@dataclass
class DownloadRouteDeps:
    # Form / snapshot helpers
    collect_form_snapshot: Callable
    project_workspace_from_snapshot: Callable
    canonical_project_type: Callable
    normalize_template_source: Callable
    check_runtime_allowed: Callable
    resolve_runtime_snapshot_source: Callable
    build_schema_from_form: Callable
    scenario_provenance_for_record: Callable
    replay_metadata_for_project: Callable
    governance_snapshot: Callable

    # Schema / input adapters
    build_projectinputs: Callable
    build_projectinputs_from_snapshot: Callable

    # Persistence
    record_download_export: Callable
    utc_now_iso: Callable

    # Model execution
    run_demo_project: Callable
    get_project_by_code: Callable

    # Export builders
    build_excel_export_for_post_request: Callable
    build_values_only_export_for_project: Callable
```

## Risks for extraction

| Risk | Severity | Mitigation |
|---|---|---|
| Inline error HTML format drift | low | Pin error HTML strings in test (the route is the only place they are constructed) |
| `runtime_origin` mutation in non-user_created branch | medium | Pin in test that `runtime_origin` is mutated to `"saved_state"` when active_scenario_id is set |
| Hardcoded `media_type` vs `export.media_type` divergence POST vs GET | low | Pin: POST uses hardcoded `application/vnd.openxmlformats...`; GET uses `export.media_type` |
| Filename construction POST vs GET | low | Pin: POST constructs `f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"`; GET uses `export.filename` |
| `artifact_path` string format drift | low | Pin: `f"/download?project_type={project_type}&scenario={scenario}"` |
| `record_download_export` call argument shape | low | Pin all kwargs in test (export_type, artifact_name, artifact_path, project_id, governance_state, replay_metadata, scenario_id) |
| GET hardcoded `project_code` mapping ("oborovo"/"tuho") | low | Pin: the quirk is preserved; GET always uses these two strings |
| POST broad `except (ValueError, Exception)` | low | Preserve as-is; this is the same broad-except pattern as in /compare |
| `effective_runtime_origin` discarded (parity quirk) | low | Pin with comment: "captured but unused" |
| New `DownloadRouteDeps` bundle may grow large (15+ callables) | medium | Use the same shape as `RunRouteDeps` (which has 21 callables) — it's manageable |
| Service touches `export_audit_service` directly (side effect) | low | Pass `record_download_export` as dep (not import); service stays framework-agnostic |
| `StreamingResponse` construction in service vs route | low | Service returns structured payload; route constructs the `StreamingResponse` from payload |

## Test results

| Suite | Pass | Fail | xfail |
|---|---|---|---|
| Phase 51A (/run golden) | 25 | 0 | 0 |
| Phase 51B (/run extraction) | 22 | 0 | 0 |
| Phase 51C-1 (/compare golden) | 37 | 0 | 0 |
| Phase 51C-2 (/compare extraction) | 49 | 0 | 0 |
| Phase 51D-1 (/validate golden) | 51 | 0 | 0 |
| Phase 51D-2 (/validate extraction) | 52 | 0 | 0 |
| Phase 51E-1 (/download golden) | TBD | TBD | TBD |
| **Total Phase 51 (pre-51E-1)** | **236** | **0** | **0** |

`import main_web`, `from app.services import run_service`,
`from app.services import compare_service`, `from app.services
import validation_service` all OK.

Structural guards all pass:

- `run_service.py` does NOT import `main_web` ✅
- `compare_service.py` does NOT import `main_web` ✅
- `validation_service.py` does NOT import `main_web` ✅
- `main_web.py` has zero direct `record_export(...)` calls ✅

## Known pre-existing issue

`tests/test_persistence.py` and `tests/test_repository.py` fail to
collect with `ImportError: No module named 'persistence'`. This is
a pre-existing environment / refactor residue, NOT a regression
introduced by Phase 51. Out of scope.

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
✅ `/run` route from Phase 51B remains thin.
✅ `/compare` route from Phase 51C-2 remains thin.
✅ `/validate` route from Phase 51D-2 remains thin.
✅ `run_service.py`, `compare_service.py`, `validation_service.py`
   remain intact.
✅ `rc1` remains frozen (not touched by Phase 51).
✅ PR #299 remains closed (no longer active guardrail).
✅ Export audit (`record_download_export`) is preserved as the
   INTENDED export audit behavior from Phase 49 — not classified as
   forbidden persistence.

## Structural guardrail recommendation

The existing Phase 51 suite already has structural guards for
`run_service.py`, `compare_service.py`, and `validation_service.py`
("does NOT import main_web"). For Phase 51E-1, we recommend adding
the same kind of guard for the existing export services:

- `app/services/export_service.py` does NOT import main_web.
- `app/services/export_audit_service.py` does NOT import main_web.

This is a 5-line addition to a future Phase 51F guardrail suite, NOT
a 51E-1 test. **Documented here for 51F follow-up; not in scope for
51E-1 to avoid scope creep.**

## Recommended next phase

**Phase 51E-2** — Extract `/download` route family (POST + GET) into
`app/services/download_service.py` using Option A (new service
module) and the dataclass-style outcome (similar to
`CompareRouteOutcome` / `ValidateRouteOutcome`).

The proposed `DownloadRouteOutcome` shape (subject to 51E-2 design):

```python
@dataclass
class DownloadRouteOutcome:
    # One of three paths:
    # 1. success -> streaming payload
    bytes_data: Optional[bytes] = None
    media_type: Optional[str] = None
    headers: Optional[dict] = None
    # 2. inline HTML error from export
    error_html: Optional[str] = None
    error_status: int = 200
    # 3. inline HTML error from route (e.g. top-level exception, schema
    #    build failure, runtime guard block) — handled by the route
    #    itself OR also returned via error_html/error_status
```

Alternatively, the service could return a `Response`-like object
directly, but the Phase 51 pattern strongly prefers structured
dataclass outcomes for testability.

`/download` and `/save-run` are the two largest residual
main_web.py hotspots. After `/download` is extracted
(Phase 51E-1 → 51E-2), the next focus is `/save-run`
(Phase 51E-3 → 51E-4).
