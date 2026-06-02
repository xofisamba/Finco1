# Phase 51E-2 — /download route family vertical extraction

## Base SHA

`a53d278263f1f9e134d500e1a7915e9bde615626` (origin/main @ PR #386 merge,
Phase 51E-1 /download golden characterization)

## Objective

Extract `POST /download` and `GET /download` orchestration from
`main_web.py` into a new service module
`app/services/download_service.py`. Follow the Phase 51B/51C-2/51D-2
canonical pattern:

- main_web.py keeps auth/session/request/form/StreamingResponse
  construction as the route boundary.
- service owns orchestration.
- dependency bundle injects helpers from main_web module scope.
- service does NOT import main_web.
- backend remains source of truth.

This is a behavior-preserving production refactor. All 12
documented behavior quirks from Phase 51E-1 are preserved EXACTLY.

## What moved

| Concern | Before | After |
|---|---|---|
| `DownloadRouteOutcome` dataclass | n/a | `app/services/download_service.py` |
| `DownloadRouteDeps` dataclass | n/a | `app/services/download_service.py` |
| `execute_post_download_route(...)` | n/a | `app/services/download_service.py` |
| `execute_get_download_route(...)` | n/a | `app/services/download_service.py` |
| Inline error HTML format (Phase 49) | inline in route | `_build_inline_error_outcome` helper in service |
| Form parsing (POST, 12 fields) | inline in route | inside `execute_post_download_route` |
| Schema build + override construction | inline in route | inside `execute_post_download_route` |
| Snapshot + project/workspace resolution (POST) | inline in route | inside `execute_post_download_route` |
| Runtime guard + user_created branch (POST) | inline in route | inside `execute_post_download_route` |
| Runtime origin mutation to "saved_state" (POST) | inline in route | inside `execute_post_download_route` |
| Runtime snapshot resolution (POST) | inline in route | inside `execute_post_download_route` |
| Project key resolution (TUHO/Oborovo/Solar/Wind) | inline in route | inside `execute_post_download_route` |
| Model execution `run_demo_project` (POST + GET) | inline in route | inside service |
| Hardcoded project_code mapping (GET, "oborovo"/"tuho") | inline in route | inside `execute_get_download_route` |
| Project record lookup (GET, `get_project_by_code`) | inline in route | inside `execute_get_download_route` |
| Replay metadata + scenario provenance (POST + GET) | inline in route | inside service |
| Baseline source flag | inline in route | inside service |
| Excel generation (`build_excel_export_for_post_request` / `build_values_only_export_for_project`) | inline in route | inside service |
| Export error check | inline in route | inside service |
| **Export audit (`record_download_export`)** | inline in route | **inside service** (INTENDED behavior from Phase 49, preserved) |
| StreamingResponse success path (hardcoded xlsx media_type, route-constructed filename for POST; `export.media_type` / `export.filename` for GET) | inline in route | inside service (return `DownloadRouteOutcome`) |
| Top-level `except Exception` broad catch (preserved) | inline in route | inside service (return `DownloadRouteOutcome` with `is_error=True`) |

## What did NOT move

| Concern | Status |
|---|---|
| Auth redirect (`get_current_user` → `RedirectResponse("/login")`) | stays in `main_web.py` (route-owned) |
| `await request.form()` (POST) | stays in `main_web.py` |
| Query param parsing (GET, `project_type="Solar"`, `scenario="Base"`) | stays in `main_web.py` |
| `DownloadRouteDeps` construction with all 18 callables | stays in `main_web.py` (route wires deps) |
| `templates.TemplateResponse` rendering (not used by /download; uses `StreamingResponse` / `HTMLResponse`) | n/a (inline response in route, but content from service) |
| `StreamingResponse(...)` and `HTMLResponse(...)` construction | stays in `main_web.py` (service returns `DownloadRouteOutcome`; route translates to `Response`) |
| `/run` route from Phase 51B | untouched |
| `run_service.py` from Phase 51B | untouched |
| `/compare` route from Phase 51C-2 | untouched |
| `compare_service.py` from Phase 51C-2 | untouched |
| `/validate` route from Phase 51D-2 | untouched |
| `validation_service.py` from Phase 51D-2 | untouched |
| `export_service.py` (Phase 49) | untouched (NOT refactored in 51E-2) |
| `export_audit_service.py` (Phase 49) | untouched (NOT refactored in 51E-2) |
| `_collect_form_snapshot`, `_project_workspace_from_snapshot`, `_canonical_project_type`, `_normalize_template_source`, `_resolve_runtime_snapshot_source`, `_build_schema_from_form`, `_scenario_provenance_for_record`, `_replay_metadata_for_project`, `_governance_snapshot` | all stay in `main_web.py` (passed as deps) |
| `build_projectinputs`, `build_projectinputs_from_snapshot`, `run_demo_project`, `get_project_by_code`, `build_excel_export_for_post_request`, `build_values_only_export_for_project`, `record_download_export`, `utc_now_iso` | stay as module-scope imports in `main_web.py` (passed as deps) |
| Financial formulas / model / project factories / fixture CSVs / schema migrations | unchanged |
| JS financial calculations | unchanged (none added) |
| Export audit behavior (Phase 49 `record_download_export`) | preserved EXACTLY (INTENDED, not forbidden) |
| All 12 documented behavior quirks | preserved EXACTLY |

## Final route sizes

| Route | Pre-Phase-51E-2 (non-blank) | Post-Phase-51E-2 (non-blank) | Reduction |
|---|---|---|---|
| `POST /download` | 106 | 48 | -54.7% |
| `GET /download` | 65 | 49 | -24.6% |
| **Combined /download route family** | **171** | **97** | **-43.3%** |

## DownloadRouteOutcome / DownloadRouteDeps API

```python
@dataclass
class DownloadRouteOutcome:
    content: Union[bytes, str]
    media_type: str
    filename: Optional[str] = None
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    is_error: bool = False


@dataclass
class DownloadRouteDeps:
    # Form / snapshot helpers (used by POST)
    collect_form_snapshot: Callable[[Any], dict]
    project_workspace_from_snapshot: Callable[[Any, dict], tuple]

    # Project / template normalization (used by POST)
    canonical_project_type: Callable[[Any], str]
    normalize_template_source: Callable[..., str]

    # Runtime guard + resolution (used by POST)
    check_runtime_allowed: Callable[..., tuple]
    resolve_runtime_snapshot_source: Callable[..., tuple]

    # Schema / input adapters (used by POST)
    build_schema_from_form: Callable[..., Any]
    build_projectinputs: Callable[..., Any]
    build_projectinputs_from_snapshot: Callable[..., Any]

    # Replay / governance (used by both)
    scenario_provenance_for_record: Callable[..., Any]
    replay_metadata_for_project: Callable[..., Any]
    governance_snapshot: Callable[..., str, dict]

    # Model execution (used by both)
    run_demo_project: Callable[..., Any]

    # Project lookup (used by GET only)
    get_project_by_code: Callable[..., Any]

    # Export builders (POST uses _for_post_request, GET uses _for_project)
    build_excel_export_for_post_request: Callable[..., Any]
    build_values_only_export_for_project: Callable[..., Any]

    # Audit (intended export-audit, preserved from Phase 49)
    record_download_export: Callable[..., Any]

    # Utility
    utc_now_iso: Callable[[], str]


async def execute_post_download_route(
    *, request, form, user, deps: DownloadRouteDeps,
) -> DownloadRouteOutcome: ...

async def execute_get_download_route(
    *, request, user, project_type, scenario, deps: DownloadRouteDeps,
) -> DownloadRouteOutcome: ...
```

## Behavior quirks preserved (all 12)

| # | Quirk | Preserved in 51E-2? |
|---|---|---|
| 1 | POST has TWO template branches for project_key resolution (user_created vs template-seeded) | ✅ exact (canonical_project_type + normalize_template_source both in service) |
| 2 | GET has HARDCODED project_code mapping ("oborovo" if solar else "tuho") | ✅ exact (regex test_quirk_2_get_hardcoded_project_code_mapping pins this) |
| 3 | POST mutates runtime_origin='saved_state' in non-user_created branch | ✅ exact (regex `runtime_origin = "saved_state"` in service) |
| 4 | POST uses `build_excel_export_for_post_request`; GET uses `build_values_only_export_for_project` | ✅ exact (both in service) |
| 5 | POST uses hardcoded xlsx media_type; GET uses `export.media_type` | ✅ exact (both in service) |
| 6 | POST constructs filename in service; GET uses `export.filename` | ✅ exact (both in service) |
| 7 | GET passes scenario_id=None to record_download_export | ✅ exact (regex `scenario_id = None` in service) |
| 8 | Inline error HTML format preserved; no Jinja template | ✅ exact ("Excel generation failed" + "href='/'>Back" in service) |
| 9 | Top-level `except Exception` broad catch preserved; 500 inline error page | ✅ exact (both in service) |
| 10 | artifact_path is a string describing the URL, not a filesystem path | ✅ exact (regex `f"/download?project_type=...` in service) |
| 11 | POST captures `effective_runtime_origin` but discards it (parity quirk) | ✅ exact (`_effective_runtime_origin` underscore-prefixed in service) |
| 12 | POST broad `except (ValueError, Exception)` on schema build preserved as-is | ✅ exact (regex `except (ValueError, Exception)` in service) |

## Export audit side-effect classification

`record_download_export` is the **only** persistence write on the
/download path. It is **INTENDED** Phase 49 export audit behavior —
NOT forbidden persistence.

| Side effect | POST | GET | Classified as |
|---|---|---|---|
| `record_download_export` call | yes (1 per success) | yes (1 per success) | **INTENDED export audit** (preserved from Phase 49) |
| `run_demo_project` (in-memory model run) | yes (with override) | yes (no override) | **read-only model exec** |
| `db.add` / `db.commit` / `db.flush` / `session.add` / `session.commit` | no | no | n/a (forbidden) |
| `record_workspace_runtime` | no | no | n/a (forbidden, only /run) |
| `update_scenario_last_run_summary` | no | no | n/a (forbidden, only /run) |
| `record_compare_run` | n/a (does not exist) | n/a | n/a |
| `record_export` (direct call) | no | no | 0 direct calls in main_web.py (Phase 49 guardrail) |

The export audit side effect is preserved with all arguments
identical to the legacy /download route:

- `user_id=user.user_id`
- `project_code=project_code` (from project_record in POST; from
  hardcoded mapping in GET)
- `export_type="excel_model_export"`
- `artifact_name=filename` (constructed in service for POST;
  `export.filename` for GET)
- `artifact_path=f"/download?project_type={project_type}&scenario={scenario}"`
  (string URL, not filesystem path)
- `project_id=project_record.project_id if project_record else None`
- `governance_state=_governance_snapshot(project_code)`
- `replay_metadata=replay_metadata`
- `scenario_id=active_scenario_record.scenario_id if active_scenario_record else None` (POST) or `None` (GET)

## Test results

| Suite | Pass | Fail | xfail |
|---|---|---|---|
| Phase 51A (/run golden) | 25 | 0 | 0 |
| Phase 51B (/run extraction) | 22 | 0 | 0 |
| Phase 51C-1 (/compare golden) | 37 | 0 | 0 |
| Phase 51C-2 (/compare extraction) | 49 | 0 | 0 |
| Phase 51D-1 (/validate golden) | 51 | 0 | 0 |
| Phase 51D-2 (/validate extraction) | 52 | 0 | 0 |
| Phase 51E-1 (/download golden, re-pointed) | 56 | 0 | 0 |
| Phase 51E-2 (/download extraction) | 65 | 0 | 0 |
| **Total Phase 51** | **357** | **0** | **0** |

`import main_web`, `from app.services import run_service`,
`from app.services import compare_service`, `from app.services import
validation_service`, `from app.services import download_service`
all OK.

Structural guards all PASS:
- `run_service.py` does NOT import `main_web` ✅
- `compare_service.py` does NOT import `main_web` ✅
- `validation_service.py` does NOT import `main_web` ✅
- `download_service.py` does NOT import `main_web` ✅
- `download_service.py` does NOT import `main_api` ✅
- `main_web.py` has zero direct `record_export` calls ✅
- `/run`, `/compare`, `/validate` routes remain thin ✅
- `run_service.py`, `compare_service.py`, `validation_service.py` remain intact ✅
- `export_service.py`, `export_audit_service.py` remain intact (NOT refactored in 51E-2) ✅

## Known pre-existing issue

`tests/test_persistence.py` and `tests/test_repository.py` fail to
collect with `ImportError: No module named 'persistence'`. This is
a pre-existing environment / refactor residue, NOT a regression
introduced by Phase 51E-2. Confirmed reproducible on `origin/main`
HEAD. Out of scope.

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
✅ `run_service.py`, `compare_service.py`, `validation_service.py` remain intact.
✅ `export_service.py`, `export_audit_service.py` remain intact (NOT refactored in 51E-2).
✅ `download_service.py` does NOT import `main_web` (one-way import).
✅ `download_service.py` does NOT import `main_api` (service is web-layer).
✅ `main_web.py` has zero direct `record_export` calls.
✅ `/download` route + service have zero forbidden persistence / `db.*` / `session.*` calls.
✅ All 12 behavior quirks preserved EXACTLY (each pinned with a
   dedicated test in `test_phase51e2_download_route_vertical_extraction.py`).
✅ `rc1` remains frozen (not touched by any Phase 51 commit).
✅ PR #299 remains closed (no longer active guardrail).
✅ Export audit (`record_download_export`) preserved as INTENDED
   Phase 49 behavior — not classified as forbidden persistence.

## Remaining risks

1. **Broad `except (ValueError, Exception)` and `except Exception`**
   patterns preserved from legacy /download route. This is
   overly-broad but matches the current behavior. Not addressed in
   51E-2 (out of scope; future cleanup phase).

2. **Two-template-branches project_key resolution** is preserved as
   documented quirk 1. The condition + canonical selection is more
   complex than a single if/else; preserved exactly.

3. **POST `runtime_origin` mutation** in the non-user_created
   branch is preserved as documented quirk 3. Could be cleaned up
   in a future phase (e.g. compute `effective_runtime_origin`
   upfront and avoid mutation).

4. **Inline error HTML format** is preserved as documented quirk 8.
   No Jinja template is introduced. A future phase could
   consolidate the error pages across `/download`, `/run`,
   `/compare`, and `/validate`.

5. **Stream `iter([outcome.content])`** in the route wrapper
   preserves the `StreamingResponse` body-as-iterator pattern from
   the legacy route. No `bytes_data` size assumption is hard-coded
   anywhere; `Content-Length` is set from `len(excel_bytes)`.

## Recommended next phase

**Phase 51E-3** — Characterize `POST /save-run` (~125 non-blank
lines, the second-largest residual main_web.py hotspot). The
`/save-run` route is similar in shape to `/download` but adds
runtime persistence via `record_workspace_runtime` and
`update_scenario_last_run_summary`. It is therefore more
sensitive than `/download` (which is read-then-write with INTENDED
audit only). Care must be taken to preserve the runtime persistence
contract.

After `/save-run`:

1. **Phase 51F-1 + 51F-2** — Scenario state service family
   (`/scenarios/state/draft`, `/scenarios/state/discard`,
   `/scenarios/{scenario_id}/update-overrides`,
   `/scenarios/{scenario_id}/select`,
   `/scenarios/{scenario_id}/archive`,
   `/scenarios/{scenario_id}/rename`,
   `/scenarios/{scenario_id}/duplicate`,
   `/scenarios/add`,
   `/scenarios/save`).

2. **Phase 51G-1 + 51G-2** — Project save-as service
   (`/projects/{project_code}/save-as`,
   `/projects/create`).

3. **Phase 51H-1 + 51H-2** — Optional: structural guardrail phase to
   add `export_service.py` does NOT import `main_web` and
   `export_audit_service.py` does NOT import `main_web` (per the
   Phase 51E-1 recommendation).

`/run`, `/compare`, `/validate`, and `/download` (post-51E-2) now
serve as the canonical templates. The pattern is:
- thin route (auth + form/query + deps + service call + render
  StreamingResponse or HTMLResponse),
- service owns orchestration,
- deps bundle injects helpers from main_web module scope,
- one-way import direction.
