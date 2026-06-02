# Phase 51H-2 — Scenario state route family vertical extraction

## Base SHA

`86d5a9041c9bbd183bdf48383a2028e59e3388f1` (origin/main @ PR #393
merge, Phase 51H-1 /scenarios/state/* golden characterization)

## Objective

Extract POST /scenarios/state/draft and POST /scenarios/state/discard
orchestration from `main_web.py` into a new service module
`app/services/scenario_state_route_service.py`. Follow the
canonical Phase 51B/51C-2/51D-2/51E-2/51G-2 pattern:

- main_web.py keeps auth/session/request/form/deps bundle
  construction + final JSONResponse rendering.
- service owns orchestration.
- dependency bundle injects helpers from main_web module scope.
- service does NOT import main_web or main_api.
- backend remains source of truth.

This is a **behavior-preserving production refactor**. All 15
documented behaviors (draft) + 15 documented behaviors (discard)
and 12 quirks from Phase 51H-1 are preserved EXACTLY.

The new module is intentionally separate from the existing
`app/services/scenario_state_service.py` (which is data-layer
only and remains unchanged).

## What moved to scenario_state_route_service.py

| Concern | Before | After |
|---|---|---|
| `ScenarioStateRouteOutcome` dataclass | n/a | new file |
| `ScenarioStateRouteDeps` dataclass | n/a | new file |
| `execute_draft_route(...)` | n/a | new file |
| `execute_discard_route(...)` | n/a | new file |
| Form parsing (full `_collect_form_snapshot(form)` call) | inline in route | inside service (via `deps.collect_form_snapshot(form)`) |
| Project / workspace resolution | inline in route | inside service (via `deps.project_workspace_from_snapshot(user, snapshot)`) |
| `active_scenario_id` resolution (existing vs form) | inline in route | inside service |
| `active_scenario_name` resolution (existing vs None) | inline in route | inside service |
| `saved_snapshot` resolution (existing vs baseline vs default) | inline in route | inside service |
| `save_workspace_state(...)` kwargs assembly + call | inline in route | inside service (via `deps.save_workspace_state(...)`) |
| `dirty=not snapshots_equal(snapshot, saved_snapshot)` | inline in route | inside service (via `deps.snapshots_equal(...)`) |
| `_replay_metadata_for_project(...)` assembly | inline in route | inside service (via `deps.replay_metadata_for_project(...)`) |
| `_governance_snapshot(...)` call | inline in route | inside service (via `deps.governance_snapshot(...)`) |
| `_workspace_state_meta(...)` payload assembly | inline in route | inside service (via `deps.workspace_state_meta(...)`) |
| Fixed message string assignment | inline in route | inside service |
| `discard_workspace_draft(...)` call | inline in route | inside service (via `deps.discard_workspace_draft(...)`) |
| Fallback `save_workspace_state(...)` for fresh projects | inline in route | inside service (inside `if workspace_state is None:` branch) |
| `baseline_snapshot` resolution (project vs default) | inline in route | inside service (via `deps.default_workspace_snapshot(...)`) |
| `payload["snapshot"] = workspace_state.draft_snapshot` | inline in route | inside service (discard only) |
| Response payload assembly | inline in route | inside service |
| Broad `except Exception` / status code decisions | inline in route | inside service (status_code=200 default) |

## What did NOT move (stays in main_web.py)

| Concern | Status |
|---|---|
| `get_current_user(request)` auth check | stays in main_web.py (route-owned) |
| `JSONResponse({"error": "Login required"}, status_code=401)` for no-user | stays in main_web.py (route-owned; quirk 9) |
| `await request.form()` form parsing | stays in main_web.py (route-owned) |
| `ScenarioStateRouteDeps(...)` construction with 9 callables | stays in main_web.py (route wires deps) |
| `execute_draft_route(...)` / `execute_discard_route(...)` call | stays in main_web.py (route invokes service) |
| `JSONResponse(...)` rendering with outcome.payload | stays in main_web.py (route renders) |
| `is_redirect` / `redirect_url` handling (currently unused) | stays in main_web.py (route handles, currently never triggers) |
| `/run`, `/compare`, `/validate`, `/download`, `/save-run` routes | UNCHANGED |
| `run_service.py`, `compare_service.py`, `validation_service.py`, `download_service.py`, `save_run_service.py` | UNCHANGED |
| `export_service.py`, `export_audit_service.py`, `scenario_state_service.py` | UNCHANGED |
| All helper functions (`_collect_form_snapshot`, `_project_workspace_from_snapshot`, `_default_workspace_snapshot`, `_governance_snapshot`, `_replay_metadata_for_project`, `_workspace_state_meta`) | stay as main_web module-scope (passed as deps) |
| Financial formulas / model / project factories / fixture CSVs / schema | UNCHANGED |
| JS financial calculations | UNCHANGED (none added) |
| All 15+15 characterized behaviors from Phase 51H-1 | UNCHANGED |
| All 12 quirks from Phase 51H-1 | UNCHANGED |

## Why existing scenario_state_service.py was NOT extended

`app/services/scenario_state_service.py` (Phase 50, 232 lines) is
intentionally a **data-layer module**. It exposes 4 pure helpers:

- `build_workspace_state_metadata(workspace_state) -> dict`
- `resolve_runtime_snapshot(*, user, project_record, workspace_state, runtime_origin) -> RuntimeSnapshotResolution`
- `check_runtime_allowed(workspace_state, snapshot) -> (allow, origin, message)`
- `scenario_provenance_for_record(project_record, scenario_record) -> dict | None`

None of these helpers depend on Request, form, or auth. They are
called by main_web and by other services (e.g. run_service.py).
They are pure data transformations and policy checks.

Adding route-orchestration to this module would mix:

- Data-layer concerns (no Request, no form, no auth, no
  JSONResponse) — current scope.
- Route-orchestration concerns (Request, form, auth, deps
  bundle, JSONResponse) — would be added.

Mixing these would:

1. Increase the module's surface area, making it harder to
   reason about.
2. Risk import cycles (route orchestration needs Request, form,
   auth; if scenario_state_service.py starts importing
   FastAPI/Starlette types, it could create cycles with the
   other services that import from it).
3. Make the data-layer helpers harder to use in non-route
   contexts (e.g. background jobs, scripts).
4. Break the Phase 50 design intent (scenario_state_service.py
   is a stable, pure helper module that other services can
   depend on without worrying about web framework dependencies).

The Phase 51H-1 characterization (in
`tests/test_phase51h1_scenario_state_route_family_characterization.py::TestExtractionBoundaryMarkers`)
explicitly recommended Option B (new file) over Option A (extend
existing module). Phase 51H-2 follows that recommendation.

## Final route sizes (post-extraction)

| Route | Pre-51H-2 non-blank | Post-51H-2 non-blank | Reduction |
|---|---|---|---|
| `/scenarios/state/draft` | 33 | **36** | +3 (deps + service call) |
| `/scenarios/state/discard` | 31 | **36** | +5 (deps + service call + is_redirect branch) |

Note: the route is now THIN (orchestration moved to the service),
but the line count is slightly higher because the route adds
the deps construction (9 callables) and the service call
boilerplate. The orchestration body (active_scenario_id
resolution, save_workspace_state kwargs assembly, replay
metadata assembly, response payload assembly) has all moved
to the service.

If we want a stricter "lines must decrease" invariant, we
could collapse the 9-line deps bundle into a builder function.
This was considered but rejected for 51H-2: the explicit deps
bundle is the canonical Phase 51 pattern (matches run_service,
compare_service, validation_service, download_service,
save_run_service) and the clarity benefit outweighs the +3
line cost.

## ScenarioStateRouteOutcome / ScenarioStateRouteDeps API

```python
@dataclass
class ScenarioStateRouteOutcome:
    """Result of a /scenarios/state/* route orchestration.

    The route in ``main_web.py`` translates this into a FastAPI
    response via ``JSONResponse(...)`` (the only path the current
    routes use). For symmetry with the broader Phase 51 family
    the outcome also carries ``is_redirect`` and ``redirect_url``
    in case future routes need to redirect; auth is currently
    route-owned, so the service does not produce redirects itself.
    """
    payload: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    is_redirect: bool = False
    redirect_url: Optional[str] = None


@dataclass
class ScenarioStateRouteDeps:
    """Dependencies that ``execute_draft_route`` and
    ``execute_discard_route`` need from the route.

    The route in ``main_web.py`` owns these helpers; passing them
    in as callables (rather than importing from ``main_web``) keeps
    the ``main_web`` -> ``scenario_state_route_service`` import
    direction clean and lets future test code inject test doubles.

    The bundle has 9 callables. No constants are needed because
    the scenario-state routes do not validate the form (quirk 11)
    — they accept any form input as a snapshot.
    """
    collect_form_snapshot: Callable[..., dict]
    project_workspace_from_snapshot: Callable[..., tuple]
    save_workspace_state: Callable[..., Any]
    discard_workspace_draft: Callable[..., Any]
    snapshots_equal: Callable[..., bool]
    default_workspace_snapshot: Callable[..., dict]
    governance_snapshot: Callable[..., dict]
    replay_metadata_for_project: Callable[..., dict]
    workspace_state_meta: Callable[..., dict]


async def execute_draft_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    deps: ScenarioStateRouteDeps,
) -> ScenarioStateRouteOutcome:
    """Execute the /scenarios/state/draft orchestration."""


async def execute_discard_route(
    *,
    request: Any,
    form: Any,
    user: Any,
    deps: ScenarioStateRouteDeps,
) -> ScenarioStateRouteOutcome:
    """Execute the /scenarios/state/discard orchestration."""
```

## 30 behavior preservation checklist (all ✅ preserved)

### POST /scenarios/state/draft (15 behaviors)

| # | Behavior | Preserved? |
|---|---|---|
| 1 | POST /scenarios/state/draft exists in main_web.py | ✅ |
| 2 | Unauthenticated -> 401 JSON `{"error": "Login required"}` (NOT 302) | ✅ |
| 3 | Authenticated + valid form -> 200 + JSON payload | ✅ |
| 4 | Authenticated + empty form -> 200 + JSON payload (no 400) | ✅ |
| 5 | Authenticated + unknown active_project -> 200 + JSON (falls back to factory) | ✅ |
| 6 | user_id derived from session, never from form | ✅ |
| 7 | draft_snapshot = current form snapshot | ✅ |
| 8 | saved_snapshot = existing.saved_snapshot OR project baseline OR default | ✅ |
| 9 | dirty = not snapshots_equal(snapshot, saved_snapshot) | ✅ |
| 10 | Two paths in main_web preserved (auth + form + deps + service call + JSONResponse) | ✅ |
| 11 | Active project/workspace resolution via deps.project_workspace_from_snapshot | ✅ |
| 12 | Active scenario resolved (existing vs form branch) | ✅ |
| 13 | save_workspace_state called exactly once | ✅ |
| 14 | replay_metadata.export_type = "workspace_draft_state" | ✅ |
| 15 | No snapshot key, no HX-Trigger, no template render | ✅ |

### POST /scenarios/state/discard (15 behaviors)

| # | Behavior | Preserved? |
|---|---|---|
| 1 | POST /scenarios/state/discard exists in main_web.py | ✅ |
| 2 | Unauthenticated -> 401 JSON (NOT 302) | ✅ |
| 3 | Authenticated + valid form -> 200 + JSON payload | ✅ |
| 4 | Authenticated + empty form -> 200 + JSON payload (no 400) | ✅ |
| 5 | Authenticated + unknown active_project -> 200 + JSON (falls back to factory) | ✅ |
| 6 | user_id derived from session, never from form | ✅ |
| 7 | discard_workspace_draft called exactly once | ✅ |
| 8 | If discard_workspace_draft returns None, save_workspace_state fallback called once | ✅ |
| 9 | Fallback uses baseline_snapshot (draft_snapshot=saved_snapshot=baseline_snapshot) | ✅ |
| 10 | Fallback uses dirty=False | ✅ |
| 11 | Fallback uses replay_metadata.export_type="workspace_draft_state" | ✅ |
| 12 | Response includes 'snapshot' key (= workspace_state.draft_snapshot) | ✅ |
| 13 | Response message is a fixed string | ✅ |
| 14 | last_runtime_* fields preserved (not modified) | ✅ |
| 15 | No HX-Trigger, no template render | ✅ |

## 12 quirks preservation checklist (all ✅ preserved)

| # | Quirk | Preserved? |
|---|---|---|
| 1 | Draft message is a fixed string | ✅ (in service) |
| 2 | Discard message is a fixed string | ✅ (in service) |
| 3 | Discard response includes 'snapshot' key; draft does NOT | ✅ (in service) |
| 4 | Draft reads 'current_saved_scenario_id' from form OR uses existing.active_scenario_id | ✅ (in service, multiline ternary) |
| 5 | Draft replay_metadata uses scenario_id=active_scenario_id when present | ✅ (in service) |
| 6 | Discard fallback creates a clean workspace when none exists | ✅ (in service, if workspace_state is None) |
| 7 | Draft does NOT modify last_runtime_* fields | ✅ (route does not pass these kwargs to save_workspace_state; repository preserves them) |
| 8 | Discard keeps last_runtime_* fields | ✅ (discard_workspace_draft preserves them) |
| 9 | Unauth returns 401 JSON, NOT 302 redirect | ✅ (route-owned; preserved verbatim) |
| 10 | No HX-Trigger header | ✅ (ScenarioStateRouteOutcome.headers is empty by default) |
| 11 | Routes do NOT validate form fields strictly | ✅ (ScenarioStateRouteDeps has no validate_form field; service accepts any form) |
| 12 | Routes do NOT check for HTMX-request header | ✅ (HTMX-agnostic; preserved) |

## Intended side effects preserved

| Side effect | Class | Pin |
|---|---|---|
| `deps.save_workspace_state(...)` (draft) | **INTENDED** | 1 call per success |
| `deps.discard_workspace_draft(...)` (discard) | **INTENDED** | 1 call per discard |
| `deps.save_workspace_state(...)` (discard fallback) | **INTENDED** | 0-1 call per discard (only if discard returns None) |
| `replay_metadata.export_type="workspace_draft_state"` (draft) | audit metadata | preserved |
| `replay_metadata.export_type="workspace_draft_state"` (discard fallback) | audit metadata | preserved |
| `replay_metadata.scenario_id=active_scenario_id` (draft) | audit metadata | preserved (only when active_scenario_id is not None) |
| `replay_metadata.project_id=project_record.project_id` | audit metadata | preserved |
| `governance_state=deps.governance_snapshot(project_code)` | audit metadata | preserved |
| `dirty=not deps.snapshots_equal(snapshot, saved_snapshot)` (draft) | state computation | preserved |
| `dirty=False` (discard fallback) | state computation | preserved |
| `draft_snapshot=baseline_snapshot` (discard fallback) | state computation | preserved |
| `saved_snapshot=baseline_snapshot` (discard fallback) | state computation | preserved |

## Forbidden side effects confirmed (verified absent)

After stripping docstrings, comments, and string literals:

- `record_export`: 0
- `record_download_export`: 0
- `record_runtime_summary_export`: 0
- `record_institutional_workbook_export`: 0
- `record_workspace_runtime`: 0
- `update_scenario_last_run_summary`: 0
- `db.add` / `db.commit` / `db.flush`: 0
- `session.add` / `session.commit`: 0
- `deps.save_run` / `deps.save_project` / `deps.save_scenario`: 0

The 51H-2 extraction only moves which deps the orchestration
calls. It does not add new persistence, audit, or recording
side effects.

## Phase 51F guardrail status

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✅ PASS — all 5+5 golden values still match (untouched) |
| Parity-core lock (4 SHA-256 files) | ✅ PASS — all 4 files unchanged (SHA verified) |
| No-service-imports-main_web/main_api | ✅ PASS — `scenario_state_route_service.py` does NOT import main_web or main_api; all 9 service files verified clean |

## Test evidence

| Suite | Result |
|---|---|
| `pytest tests/test_phase51h1_scenario_state_route_family_characterization.py` | **92 passed**, 0 failed (re-pointed: now uses `_route_or_service_body()` helper; structural tests look at service for orchestration) |
| `pytest tests/test_phase51h2_scenario_state_route_family_vertical_extraction.py` | **81 passed**, 0 failed (new) |
| `pytest tests/test_phase51f_parallel_work_guardrails.py` | **21 passed**, 0 failed |
| `pytest tests/test_phase51h1*` + `tests/test_phase51h2*` + `tests/test_phase51f*` | **194 passed**, 0 failed |
| `pytest tests/test_phase51a*` ... `tests/test_phase51g3*` (rest) | **532 passed**, 0 failed |
| `pytest tests/test_phase51*.py` (full regression, clean tree) | **726 passed**, 0 failed, 0 xfail |

The 51H-2 suite covers 14 test classes (81 tests):
- TestServiceModuleExists (5)
- TestServiceImportDirection (3)
- TestScenarioStateServiceUnchanged (3)
- TestRoutesAreThin (8)
- TestServiceOwnsOrchestration (10)
- TestIntendedSideEffectsPreserved (7)
- TestForbiddenSideEffectsAbsent (parametrized + standalone, 9)
- TestJSONResponseBehavior (8)
- TestOtherRoutesRemainServiceBacked (parametrized + standalone, 10)
- TestDepsBundle (4)
- TestOutcomeShape (2)
- TestIntegration (3)
- TestPhase51FGuardrailsSmokeCheck (3)
- TestImportSmoke (3)

## Confirmation: no model / parity-core changes

- `app/waterfall_core.py` — NOT MODIFIED (parity-core, SHA unchanged)
- `app/project_factories.py` — NOT MODIFIED (parity-core, SHA unchanged)
- `reports/phase7_tuho_senior_debt_sizing_extraction.csv` — NOT MODIFIED (parity-core, SHA unchanged)
- `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` — NOT MODIFIED (parity-core, SHA unchanged)
- No financial formula changes
- No model output changes
- No fixture CSV changes (other than parity-core)
- No schema / migration changes
- No JS changes
- No runtime flag changes
- No route family refactors (only 1 new module + 2 thin route replacements)
- factory_template behavior: UNCHANGED (different family, no touch)
- save_run / save_project ordering in /save-run: UNCHANGED
- replay_metadata export_type values: UNCHANGED
- save_project.runtime_timestamp behavior in /save-run: UNCHANGED

## Confirmation: rc1 untouched

```
b425a0708719eaa5e1d922b1008e5609758e0ad4	refs/heads/rc1
```

Verified unchanged on origin (pinned in
`TestPhase51FGuardrailsSmokeCheck::test_rc1_untouched` in
both 51H-1 and 51H-2 suites).

## Guardrails preserved

- No financial formula / model / project factory / fixture CSV
  changes.
- No schema / migration changes.
- No new JavaScript financial calculations.
- /run, /compare, /validate, /download, /save-run route+service
  from Phases 51A-51G-2 remain thin and intact.
- run_service.py, compare_service.py, validation_service.py,
  download_service.py, save_run_service.py, export_service.py,
  export_audit_service.py all remain intact (UNCHANGED).
- scenario_state_service.py is unchanged (still 4 data-layer
  helpers, 232 lines, no Request, no form, no auth).
- scenario_state_route_service.py does NOT import main_web or
  main_api (one-way import direction preserved).
- main_web.py has zero direct record_export calls.
- G20 remains BLOCKED.
- R99/R102 remain NOT APPROVED.
- partial_pay_sweep not promoted.
- flat / min DSCR sculpting not promoted.
- Generic solar / wind remain exploratory / unvalidated.
- No lender / bank / audit / certification / SaaS claims.
- Backend remains source of truth.
- rc1 remains frozen (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged).
- PR #299 remains closed (no longer active guardrail).
- All 15+15 Phase 51H-1 behaviors preserved EXACTLY.
- All 12 Phase 51H-1 quirks preserved EXACTLY.
- save_run / save_project ordering preserved (no touch).
- replay_metadata export_type values preserved.
- save_project.runtime_timestamp behavior preserved.

## Known failures

- `tests/test_persistence.py` + `tests/test_repository.py`:
  ImportError on `persistence` module. Pre-existing,
  reproduces on `origin/main` HEAD. Out of scope.

## Recommended next phase

After 51H-2, the natural next extractions are:

1. **Phase 51I-1 + 51I-2** — Project save-as service family
   (`/projects/{project_code}/save-as`, `/projects/create`).
2. **Phase 51J** — Optional: structural guardrail phase to add
   `export_service.py` / `export_audit_service.py` does NOT
   import `main_web` (per Phase 51E-1 / 51F recommendation).

`/run`, `/compare`, `/validate`, `/download`, `/save-run`
(Phases 51A-51G-2) and `/scenarios/state/*` (Phase 51H-2) now
serve as the canonical templates for vertical extraction, with
a known narrow bugfix phase pattern for any latent bugs
discovered along the way.

The pattern is:

- thin route (auth + form + deps + service call + render)
- service owns orchestration
- deps bundle (callable injection)
- one-way import direction
- preserve all characterized behaviors and quirks
- preserve intended persistence side effects with exact ordering
- for the scenario-state family specifically: data-layer
  helpers stay in `scenario_state_service.py`; route
  orchestration lives in a new `*_route_service.py` module.

JSON-only response quirk: unlike /run, /compare, /validate,
/download, /save-run (all of which return HTMX-rendered
templates), /scenarios/state/draft and /scenarios/state/discard
return JSON payloads (no HX-Trigger, no HX-Redirect, no
template render). The ScenarioStateRouteOutcome dataclass is
designed for this JSON-only pattern (payload + status_code +
headers).
