# Phase 51G-2 — /save-run route family vertical extraction

## Base SHA

`2e41b24f8c47ec544e1ef52e35084646df4d4d8f` (origin/main @ PR #389
merge, Phase 51G-1 /save-run golden characterization)

## Objective

Extract POST /save-run orchestration from `main_web.py` into a
new service module `app/services/save_run_service.py`. Follow
the Phase 51B/51C-2/51D-2/51E-2 canonical pattern:

- main_web.py keeps auth/session/request/form/deps construction
  + final templates.TemplateResponse rendering.
- service owns orchestration.
- dependency bundle injects helpers from main_web module scope.
- service does NOT import main_web or main_api.
- backend remains source of truth.

This is a **behavior-preserving production refactor**. All 15
documented behaviors from Phase 51G-1 are preserved EXACTLY. All
7 quirks are preserved EXACTLY.

**Critical decision (per user):** The pre-existing latent bug
`_clean_user_project_runtime_snapshot` (referenced in
/save-run's user_created branch but NOT defined) is **preserved
as-is in 51G-2** — NOT fixed. A separate Phase 51G-3 bugfix PR is
recommended with explicit user sign-off (rationale: keep refactor
PR and behavior change PR separate for cleaner audit trail).

## What moved to save_run_service.py

| Concern | Before | After |
|---|---|---|
| `SaveRunRouteOutcome` dataclass | n/a | `app/services/save_run_service.py` |
| `SaveRunRouteDeps` dataclass | n/a | `app/services/save_run_service.py` |
| `execute_save_run_route(...)` | n/a | `app/services/save_run_service.py` |
| Form parsing (9 fields) | inline in route | inside `execute_save_run_route` |
| Snapshot collection (via dep) | inline in route | route-owned, passed to service |
| Project / workspace resolution | inline in route | inside service (via deps) |
| Runtime guard + 3-tuple unpacking | inline in route | inside service |
| `user_id = user.user_id` derivation | inline in route | inside service |
| inputs dict construction | inline in route | inside service |
| `_validate_form` call | inline in route | inside service (via deps) |
| effective_project_type computation | inline in route | inside service |
| user_created / factory_template branch dispatch | inline in route | inside service |
| runtime key resolution (TUHO/Oborovo/Solar/Wind) | inline in route | inside service |
| `run_project(...)` call | inline in route | inside service (via deps) |
| `result["kpis"]` extraction | inline in route | inside service |
| Broad `except Exception` for model exec | inline in route | inside service |
| `save_run(...)` kwargs assembly + call | inline in route | inside service (via deps) |
| `save_project(...)` kwargs assembly + call | inline in route | inside service (via deps) |
| `_replay_metadata_for_project` calls (both variants) | inline in route | inside service (via deps) |
| `_governance_snapshot` call | inline in route | inside service (via deps) |
| `run_record.created_at.isoformat()` timestamp quirk | inline in route | inside service |
| `project_id=None` explicit None quirk | inline in route | inside service |
| save_result-ok / save_result-err context assembly | inline in route | inside service |
| Broad `except Exception` for persistence | inline in route | inside service |
| `HX-Trigger: refreshHistory` header | inline in route | service default (route forwards) |
| `partials/save_result.html` template name | inline in route | service default (route forwards) |

## What did NOT move (stays in main_web.py)

| Concern | Status |
|---|---|
| `get_current_user(request)` auth check | stays in main_web.py (route-owned) |
| `RedirectResponse(url="/login", status_code=302)` for no-user | stays in main_web.py (route-owned) |
| `await request.form()` form parsing | stays in main_web.py (route-owned) |
| `_collect_form_snapshot(form)` snapshot collection | stays in main_web.py (route-owned) |
| `SaveRunRouteDeps(...)` construction with 15 callables + 2 constants | stays in main_web.py (route wires deps) |
| `templates.TemplateResponse(...)` rendering | stays in main_web.py (route renders) |
| `name=outcome.template_name` template forwarding | stays in main_web.py |
| `headers=outcome.headers` headers forwarding | stays in main_web.py |
| `is_redirect` / `redirect_url` (for symmetry) | stays in main_web.py (route handles) |
| `/run`, `/compare`, `/validate`, `/download` routes | UNCHANGED |
| `run_service.py`, `compare_service.py`, `validation_service.py`, `download_service.py` | UNCHANGED |
| `export_service.py`, `export_audit_service.py`, `scenario_state_service.py` | UNCHANGED |
| All helper functions (`_collect_form_snapshot`, `_project_workspace_from_snapshot`, `_canonical_project_type`, `_build_schema_from_form`, `_normalize_template_source`, `_replay_metadata_for_project`, `_governance_snapshot`, `_validate_form`, `PROJECT_TYPES`, `SCENARIOS`) | stay as main_web module-scope (passed as deps) |
| Financial formulas / model / project factories / fixture CSVs / schema | UNCHANGED |
| JS financial calculations | UNCHANGED (none added) |
| Export audit behavior (Phase 49 record_download_export) | UNCHANGED |
| All 15 documented behaviors from Phase 51G-1 | UNCHANGED |
| All 7 quirks from Phase 51G-1 | UNCHANGED |

## Final POST /save-run route size

| Metric | Pre-51G-2 | Post-51G-2 | Reduction |
|---|---|---|---|
| Total lines | 137 | 68 | -50.4% |
| Non-blank lines | **127** | **58** | **-54.3%** |

## SaveRunRouteOutcome / SaveRunRouteDeps API

```python
@dataclass
class SaveRunRouteOutcome:
    """Result of POST /save-run orchestration.
    
    The route in main_web.py translates this into a FastAPI response
    via templates.TemplateResponse (default) or RedirectResponse
    (when is_redirect is True).
    """
    template_name: str = "partials/save_result.html"
    context: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(
        default_factory=lambda: {"HX-Trigger": "refreshHistory"}
    )
    is_redirect: bool = False
    redirect_url: Optional[str] = None


@dataclass
class SaveRunRouteDeps:
    """Dependencies that execute_save_run_route needs from the route.
    
    15 callables + 2 constants:
    - project_workspace_from_snapshot
    - check_runtime_allowed
    - validate_form
    - project_types (list)
    - scenarios (list)
    - canonical_project_type
    - build_projectinputs_from_snapshot
    - build_schema_from_form
    - build_projectinputs
    - normalize_template_source
    - run_project
    - save_run
    - save_project
    - replay_metadata_for_project
    - governance_snapshot
    - utc_now_iso
    """
    # ... (15 callables + 2 constants)


async def execute_save_run_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    snapshot: dict,
    deps: SaveRunRouteDeps,
) -> SaveRunRouteOutcome:
    """Execute the /save-run orchestration and return a
    SaveRunRouteOutcome.
    """
    # ... 8 numbered steps ...
```

## Intended runtime persistence side-effect preservation

| Side effect | Class | Pin |
|---|---|---|
| `save_run(...)` | **INTENDED** | 1 call per success → `RunRecord` row |
| `save_project(...)` | **INTENDED** | 1 call per success → `ProjectRecord.last_run_summary` update |
| `run_project(...)` | in-memory model exec | not persistence, just memory + KPIs |
| `_replay_metadata_for_project` export_type="saved_run_metadata" | audit metadata | on save_run only |
| `_replay_metadata_for_project` export_type="saved_run_project_state" | audit metadata | on save_project only |
| `utc_now_iso()` | timestamp | save_run.replay_metadata.runtime_timestamp |
| `run_record.created_at.isoformat()` | timestamp | save_project.replay_metadata.runtime_timestamp (must match run timestamp) |

## save_run/save_project ordering (preserved exactly)

```text
on success:
    run_record = deps.save_run(
        user_id=user.user_id,                  # session-derived
        project_type=effective_project_type,   # record.project_type or form
        scenario=scenario,                     # from form
        inputs=inputs,                         # 9 form fields
        kpis=kpis,                             # result["kpis"] from run_project
        replay_metadata={
            ...deps.replay_metadata_for_project(project_code,
                export_type="saved_run_metadata",
                runtime_timestamp=deps.utc_now_iso())...
        },
    )
    deps.save_project(
        user_id=user.user_id,
        project_code=project_code,             # from project_record
        project_name=project_name,             # from project_record
        source_project_template=project_code,  # SAME as project_code
        governance_state=deps.governance_snapshot(project_code),
        last_run_summary=kpis,                 # SAME kpis as save_run
        replay_metadata={
            ...deps.replay_metadata_for_project(project_code,
                project_id=None,               # explicit None
                export_type="saved_run_project_state",
                runtime_timestamp=run_record.created_at.isoformat())  # SAME timestamp as save_run
        },
    )
    return SaveRunRouteOutcome(
        context={"success": True, "run_id": run_record.run_id, ...},
    )
```

## 15 behavior preservation checklist (all ✅ preserved)

| # | Behavior | Preserved? |
|---|---|---|
| 1 | POST /save-run exists in main_web.py | ✅ |
| 2 | Unauthenticated → 302 to /login (route-owned) | ✅ |
| 3 | Auth + dirty/empty state → 200 + save_result-err + HX-Trigger | ✅ |
| 4 | Auth + factory_template + valid form → 200 + save_result-ok + HX-Trigger | ✅ |
| 5 | user_id derived from session, never from form | ✅ |
| 6 | Form fields exactly: capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur, opex_y1_keur, gearing_pct, target_dscr, interest_rate_pct, tenor_years | ✅ |
| 7 | Project code and name from project_record | ✅ |
| 8 | effective_project_type = project_record.project_type or form.project_type | ✅ |
| 9 | check_runtime_allowed unpacks 3-tuple: allow_run, runtime_origin, guard_message | ✅ |
| 10 | Two model-execution branches: user_created and factory_template | ✅ |
| 11 | factory_template branch maps template_source → runtime key | ✅ |
| 12 | Model execution wrapped in broad except Exception | ✅ |
| 13 | save_run called first, save_project second | ✅ |
| 14 | save_project.runtime_timestamp = run_record.created_at.isoformat() (NOT utc_now_iso) | ✅ |
| 15 | All 4 non-auth responses use partials/save_result.html + HX-Trigger: refreshHistory | ✅ |

## 7 quirks preservation checklist (all ✅ preserved)

| # | Quirk | Preserved? |
|---|---|---|
| 1 | user_created branch references `_clean_user_project_runtime_snapshot` (NOT DEFINED) — latent bug, NOT fixed in 51G-2 | ✅ (Phase 51G-3 recommended) |
| 2 | runtime_origin captured but not used to mutate state | ✅ |
| 3 | save_project.runtime_timestamp = run_record.created_at, not utc_now_iso | ✅ |
| 4 | save_project.replay_metadata.project_id explicitly None | ✅ |
| 5 | All 4 non-auth responses use same partial template | ✅ |
| 6 | _validate_form uses hardcoded PROJECT_TYPES / SCENARIOS | ✅ |
| 7 | save_run before save_project (ordering) | ✅ |

## Explicit confirmation: `_clean_user_project_runtime_snapshot` NOT fixed

The latent bug is **preserved exactly as characterized in Phase 51G-1**:

- The service still calls `_clean_user_project_runtime_snapshot(...)` in
  the user_created branch (line ~250 of save_run_service.py).
- The function is **NOT defined** anywhere in the codebase.
- The broad `except Exception` in the model-execution block catches
  the resulting `NameError` and returns a 200 + save_result-err with
  message `"Model error: name '_clean_user_project_runtime_snapshot'
  is not defined"`.
- The test `test_user_created_branch_has_latent_name_error` in
  `tests/test_phase51g1_save_run_route_golden_characterization.py`
  continues to pass, pinning this behavior.
- The service docstring explicitly documents this as a "preserved
  latent bug" — recommended for a separate Phase 51G-3 bugfix PR.

**Why we did NOT fix it in 51G-2:**

> User's recommendation (verbatim):
> "51G-2 je extraction PR. Ako u istoj fazi i preselimo /save-run
> i popravljamo latentni bug, miješamo refaktor + behavior change.
> Bolje je: 51G-2: extract /save-run 1:1, uključujući postojeći
> latentni bug kao documented/pinned behavior. 51G-3: zaseban mali
> bugfix PR za user_created branch, s jasnim testom i sign-offom.
> To je čišće, auditabilnije i manje rizično."

## Forbidden side effects (verified absent in save_run_service.py)

- `record_export` — NOT called
- `record_download_export` — NOT called
- `record_runtime_summary_export` — NOT called
- `record_institutional_workbook_export` — NOT called
- `record_workspace_runtime` — NOT called
- `update_scenario_last_run_summary` — NOT called
- `db.add / db.commit / db.flush / session.add / session.commit` — NOT used (service uses save_run/save_project repository functions)

## Phase 51F guardrail status (post-51G-2)

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✅ PASS — all 5+5 golden values still match |
| Parity-core lock (4 SHA-256 files) | ✅ PASS — all 4 files unchanged |
| No-service-imports-main_web/main_api | ✅ PASS — save_run_service does NOT import main_web or main_api |

## Test results

| Suite | Pass | Fail | xfail |
|---|---|---|---|
| Phase 51G-1 (golden, re-pointed) | 59 | 0 | 0 |
| Phase 51G-2 (extraction, new) | 55 | 0 | 0 |
| Phase 51F (guardrails) | 21 | 0 | 0 |
| Phase 51A-51E-2 (other) | 357 | 0 | 0 |
| **Total Phase 51** | **492** | **0** | **0** |

`import main_web, run_service, compare_service, validation_service,
download_service, save_run_service` all OK.

Structural guards all PASS:
- `run_service.py` does NOT import `main_web`
- `compare_service.py` does NOT import `main_web`
- `validation_service.py` does NOT import `main_web`
- `download_service.py` does NOT import `main_web`
- `save_run_service.py` does NOT import `main_web` ✅ (NEW)
- `save_run_service.py` does NOT import `main_api` ✅ (NEW)
- `main_web.py` has zero direct `record_export` calls
- `/run`, `/compare`, `/validate`, `/download` routes remain thin
- `/save-run` route is now thin (NEW, was 127 non-blank, now 58)

## Known pre-existing issues

- `tests/test_persistence.py` and `tests/test_repository.py` may
  fail collection with `ImportError: No module named 'persistence'`.
  This is pre-existing, NOT introduced by Phase 51G-2, and out of
  scope.
- `_clean_user_project_runtime_snapshot` is still NOT defined.
  Pre-existing latent bug. Pinned in
  `test_user_created_branch_has_latent_name_error`. NOT fixed in
  51G-2 (per user decision; separate Phase 51G-3 bugfix PR
  recommended).

## Guardrails preserved

- No financial formula / model / project factory / fixture CSV
  changes.
- No schema / migration changes.
- No new JavaScript financial calculations.
- /run route+service from Phase 51B remain thin and intact.
- /compare route+service from Phase 51C-2 remain thin and intact.
- /validate route+service from Phase 51D-2 remain thin and intact.
- /download route+service from Phase 51E-2 remain thin and intact.
- run_service.py, compare_service.py, validation_service.py,
  download_service.py, export_service.py, export_audit_service.py,
  scenario_state_service.py all remain intact (unchanged).
- /save-run is now service-backed (new); all 15 behaviors
  preserved.
- save_run_service.py does NOT import main_web or main_api
  (one-way import direction preserved).
- main_web.py has zero direct record_export calls.
- G20 remains BLOCKED.
- R99/R102 remain NOT APPROVED.
- partial_pay_sweep not promoted.
- flat / min DSCR sculpting not promoted.
- Generic solar / wind remain exploratory / unvalidated.
- No lender / bank / audit / certification / SaaS claims.
- Backend remains source of truth.
- rc1 remains frozen (not touched by any Phase 51 commit, including
  51G-2).
- PR #299 remains closed (no longer active guardrail).

## Recommended next phase

**Phase 51G-3** (optional, separate PR with explicit user
sign-off) — Bugfix for `_clean_user_project_runtime_snapshot`
latent bug. Inject a real implementation (or a stub) so the
user_created branch of /save-run can actually save. This is a
**behavior change** (the user_created branch currently returns a
"Model error" message; after the fix it will save the run). The
fix should be a small, focused PR with:

1. A clear description of what the function should do (the
   current call site passes `project_record, workspace_state,
   runtime_origin` and expects a `runtime_snapshot` dict back).
2. A test that exercises the user_created branch end-to-end
   (currently impossible because the function is undefined).
3. The 51G-1 latent-bug test
   (`test_user_created_branch_has_latent_name_error`) updated to
   pin the new expected behavior.
4. A 51G-1 docs update removing the "preserved latent bug"
   note.

After 51G-3 (or instead of it), the natural next route
extractions are:

1. **Phase 51H-1 + 51H-2** — Scenario state service family
   (`/scenarios/state/draft`, `/scenarios/state/discard`,
   `/scenarios/{scenario_id}/update-overrides`,
   `/scenarios/{scenario_id}/select`,
   `/scenarios/{scenario_id}/archive`,
   `/scenarios/{scenario_id}/rename`,
   `/scenarios/{scenario_id}/duplicate`,
   `/scenarios/add`,
   `/scenarios/save`).

2. **Phase 51I-1 + 51I-2** — Project save-as service
   (`/projects/{project_code}/save-as`,
   `/projects/create`).

3. **Phase 51J** — Optional: structural guardrail phase to add
   `export_service.py` / `export_audit_service.py` does NOT
   import `main_web` (per Phase 51E-1 / 51F recommendation).

`/run`, `/compare`, `/validate`, `/download` (Phases 51A-51E-2)
and `/save-run` (Phase 51G-2) now serve as the canonical
templates for vertical extraction. The pattern is:

- thin route (auth + form + snapshot + deps + service call +
  render)
- service owns orchestration
- deps bundle (callable injection)
- one-way import direction
- preserve all characterized behaviors and quirks
- preserve intended persistence side effects with exact ordering
