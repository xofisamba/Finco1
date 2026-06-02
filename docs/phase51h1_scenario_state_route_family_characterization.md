# Phase 51H-1 — Scenario state route family golden characterization

## Base SHA

`47faffbfadf22dcdcc3d0b2f3fab9454ab22a166` (origin/main @ PR #392
merge, Phase 51G-3 /save-run user_created branch latent bug fix)

## Objective

Characterize the scenario state route family BEFORE Phase 51H-2
extraction. Pin current behavior of the two routes in scope:

- `POST /scenarios/state/draft`
- `POST /scenarios/state/discard`

This is a **characterization-only phase**. **No production code
changes** are made in 51H-1. The extraction itself happens in
51H-2.

## In-scope routes

| Route | Method | Handler |
|---|---|---|
| `/scenarios/state/draft` | POST | `save_workspace_draft_endpoint` |
| `/scenarios/state/discard` | POST | `discard_workspace_draft_endpoint` |

These are the only routes under `/scenarios/state/` in main_web.py.
Adjacent routes (`/scenarios`, `/scenarios/save`, `/scenarios/{id}/*`,
`/scenarios/history`, `/scenarios/compare`, `/scenarios/add`) are
**NOT** in scope for 51H-1 — they are separate route families.

## Route sizes (current, pre-extraction)

| Route | Total lines | Non-blank lines |
|---|---|---|
| `/scenarios/state/draft` | 35 | **33** |
| `/scenarios/state/discard` | 33 | **31** |

## Route responsibilities

### POST /scenarios/state/draft

**Path:** main_web.py line 2018-2052

**Purpose:** Persist unsaved workspace edits without promoting them
to saved-scenario authority.

**Auth/session behavior:**
- Calls `get_current_user(request)`.
- If no user: returns `JSONResponse({"error": "Login required"}, status_code=401)`.
  (Quirk: 401 JSON, NOT 302 redirect to /login — these routes are
  JSON-only, not HTMX-partial-based.)
- user_id is derived from `user.user_id`, NEVER from form.

**Form inputs:**
- Reads `await request.form()`.
- Collects full form snapshot via `_collect_form_snapshot(form)`.

**Active project / scenario handling:**
- Resolves project via `_project_workspace_from_snapshot(user, snapshot)`.
- If no existing workspace_state, reads `current_saved_scenario_id`
  from form (`form.get("current_saved_scenario_id", "") or None`).
- If existing workspace_state, preserves
  `existing.active_scenario_id` and `existing.active_scenario_name`.

**Workspace state behavior:**
- If no existing workspace_state, the route
  `save_workspace_state(...)` is called with
  - `draft_snapshot=snapshot` (the new form snapshot)
  - `saved_snapshot=existing.saved_snapshot` (preserved from existing
    or seeded from baseline_snapshot / default)
  - `dirty=not snapshots_equal(snapshot, saved_snapshot)`
  - `replay_metadata.export_type="workspace_draft_state"`

**Response:**
- 200 + JSON payload built from
  `_workspace_state_meta(workspace_state) + {"message": "Workspace
  draft captured. Saved scenario authority is unchanged."}`.
- Required keys: `dirty`, `dirty_label`, `active_scenario_id`,
  `active_scenario_name`, `last_runtime_origin`,
  `last_runtime_origin_label`, `last_runtime_snapshot_id`, `message`.
- No `snapshot` key (unlike discard).
- No `HX-Trigger` header (unlike /save-run).
- No template render (returns JSON, not a Jinja template).

### POST /scenarios/state/discard

**Path:** main_web.py line 2054-2086

**Purpose:** Discard unsaved workspace edits and restore the last
saved scenario boundary.

**Auth/session behavior:**
- Same as draft: 401 JSON if no user.

**Form inputs:**
- Reads `await request.form()` and collects snapshot.

**Active project / scenario handling:**
- Resolves project via `_project_workspace_from_snapshot(user, snapshot)`.
- Then calls `discard_workspace_draft(user.user_id, project_record.project_id)`.

**Workspace state behavior:**
- If `discard_workspace_draft` returns a workspace_state, that's used
  (the saved_snapshot has been copied to draft_snapshot by the
  repository function, with dirty=False).
- If `discard_workspace_draft` returns None (no existing workspace),
  the route calls `save_workspace_state(...)` with
  - `draft_snapshot=baseline_snapshot` (project baseline or default)
  - `saved_snapshot=baseline_snapshot` (same as draft)
  - `dirty=False`
  - `replay_metadata.export_type="workspace_draft_state"`.

**Response:**
- 200 + JSON payload built from
  `_workspace_state_meta(workspace_state) + {"snapshot":
  workspace_state.draft_snapshot, "message": "Unsaved edits
  discarded. Workspace restored to the last saved runtime
  boundary."}`.
- Required keys: `dirty`, `dirty_label`, `active_scenario_id`,
  `active_scenario_name`, `last_runtime_origin`,
  `last_runtime_origin_label`, `last_runtime_snapshot_id`,
  `snapshot`, `message`.
- Quirks: response includes the full snapshot dict (so the client
  JS can restore form fields), AND a message string.

## Dependency / helper map

| Helper | Used by draft | Used by discard | Where it lives |
|---|---|---|---|
| `get_current_user` | yes | yes | `app.auth` |
| `_collect_form_snapshot` | yes | yes | `main_web.py:268` |
| `_project_workspace_from_snapshot` | yes | yes | `main_web.py:989` |
| `_default_workspace_snapshot` | yes (via existing) | yes (fallback) | `main_web.py:469` |
| `save_workspace_state` (repo) | yes (1×) | yes (1× fallback) | `app.persistence.repository:1501` |
| `discard_workspace_draft` (repo) | no | yes (1×) | `app.persistence.repository:1651` |
| `snapshots_equal` | yes | no | imported from persistence |
| `_governance_snapshot` | yes | yes (fallback) | `main_web.py:219` |
| `_replay_metadata_for_project` | yes | yes (fallback) | `main_web.py:858` |
| `_workspace_state_meta` | yes | yes | `main_web.py:686` (delegates to `scenario_state_service.build_workspace_state_metadata`) |

## Auth/session/input map

- All inputs are read from `await request.form()` (POST form-encoded,
  not JSON, not multipart).
- `user_id` is **always** derived from `user.user_id` (session). It is
  **NEVER** accepted from the form.
- `project_id` is derived from `project_record.project_id`, which is
  resolved from the form's `active_project` field (or defaults to
  one of the factory projects: `tuho`, `oborovo`, `generic_wind`,
  `generic_solar`, or creates a new project on the fly).

## Scenario/project/workspace-state behavior

- **Draft endpoint** persists the current form snapshot as
  `draft_snapshot` while keeping the existing `saved_snapshot`
  (or seeding from baseline). `dirty` is computed by comparing the
  two. The existing `last_runtime_*` fields are preserved by the
  repository function (the route does not pass them explicitly).

- **Discard endpoint** restores the `saved_snapshot` as the
  `draft_snapshot` (via the `discard_workspace_draft` repository
  function, which calls `save_workspace_state` internally with
  `draft_snapshot=record.saved_snapshot` and `dirty=False`).

- **No data export, no scenario row creation, no project mutation**
  happens in either route. They are pure workspace-state mutations.

## Intended side-effect map

| Route | Intended writes | Forbidden writes |
|---|---|---|
| `/scenarios/state/draft` | `save_workspace_state(...)` × 1 (always) | record_export, record_download_export, record_runtime_summary_export, record_institutional_workbook_export, record_workspace_runtime, update_scenario_last_run_summary, save_run, save_project, save_scenario, db.add / db.commit / db.flush, session.add / session.commit |
| `/scenarios/state/discard` | `discard_workspace_draft(...)` × 1 (always) + `save_workspace_state(...)` × 1 (only if discard returned None) | (same as draft) |

**Note:** `discard_workspace_draft` internally calls
`save_workspace_state(...)` to update the row (with
`draft_snapshot=record.saved_snapshot`). So in the happy path
(workspace_state existed), discard still results in a write — but
it's an UPDATE, not an INSERT.

## Forbidden side-effect confirmation

Verified absent in code (after stripping docstrings, comments, and
string literals):

- `record_export`: 0
- `record_download_export`: 0
- `record_runtime_summary_export`: 0
- `record_institutional_workbook_export`: 0
- `record_workspace_runtime`: 0
- `update_scenario_last_run_summary`: 0
- `db.add` / `db.commit` / `db.flush`: 0
- `session.add` / `session.commit`: 0

The scenario-state routes are pure workspace-state mutations.
They do not touch the export audit, the runtime state, the
scenario run history, or the project records.

## Response/template/header behavior

Both routes return JSON, not HTMX-rendered templates. Specifically:

| Behavior | /scenarios/state/draft | /scenarios/state/discard |
|---|---|---|
| Status code (auth OK) | 200 | 200 |
| Status code (no auth) | **401** (JSON, NOT 302) | **401** (JSON, NOT 302) |
| Content-Type | application/json | application/json |
| Template render | NO | NO |
| HX-Trigger header | NO | NO |
| HX-Redirect header | NO | NO |
| Location header | NO | NO |
| Body keys (required) | dirty, dirty_label, active_scenario_id, active_scenario_name, last_runtime_origin, last_runtime_origin_label, last_runtime_snapshot_id, message | dirty, dirty_label, active_scenario_id, active_scenario_name, last_runtime_origin, last_runtime_origin_label, last_runtime_snapshot_id, snapshot, message |
| Body keys (quirk) | (no `snapshot` key) | `snapshot` = workspace_state.draft_snapshot (full dict) |
| message | "Workspace draft captured. Saved scenario authority is unchanged." | "Unsaved edits discarded. Workspace restored to the last saved runtime boundary." |

## Behavior quirks

| # | Quirk | Source |
|---|---|---|
| 1 | Draft message is a fixed string | `payload["message"] = "Workspace draft captured..."` |
| 2 | Discard message is a fixed string | `payload["message"] = "Unsaved edits discarded..."` |
| 3 | Discard response includes `snapshot` key (full draft dict); draft does NOT | Discard route: `payload["snapshot"] = workspace_state.draft_snapshot` |
| 4 | Draft reads `current_saved_scenario_id` from form (when no existing workspace) OR uses `existing.active_scenario_id` (when existing) | Two-branch ternary in the draft route |
| 5 | Draft replay_metadata uses `scenario_id=active_scenario_id` when present | Replay metadata for project call site |
| 6 | Discard fallback creates a clean workspace when no existing one | `if workspace_state is None: ... save_workspace_state(...)` |
| 7 | Draft does NOT modify `last_runtime_*` fields (preserved by repository) | Route does not pass these kwargs |
| 8 | Discard keeps `last_runtime_*` fields (preserved by `discard_workspace_draft`) | Repository function uses existing record's fields |
| 9 | Unauth returns 401 JSON (not 302 redirect to /login) | `JSONResponse({"error": "Login required"}, status_code=401)` |
| 10 | No HX-Trigger header (unlike /save-run) | Plain JSONResponse, not template render |
| 11 | Routes do not validate form fields strictly (no `_validate_form`) | They accept any form input and treat it as a snapshot |
| 12 | Routes do not check for HTMX-request header | They respond the same way for both HTMX and non-HTMX callers |

## Adjacent / closely-coupled routes (NOT in 51H-1 scope)

These routes are related but should NOT be extracted in 51H-2:

| Route | Reason for exclusion |
|---|---|
| `/scenarios` (GET) | Read-only list, no state mutation |
| `/scenarios/save` (POST) | Creates a new saved scenario — different concern |
| `/scenarios/{id}/select` (POST) | Selects an existing saved scenario — different concern |
| `/scenarios/{id}/update-overrides` (POST) | Updates scenario overrides — different concern |
| `/scenarios/{id}/rename` (POST) | Renames a scenario — different concern |
| `/scenarios/{id}/archive` (POST) | Archives a scenario — different concern |
| `/scenarios/{id}/duplicate` (POST) | Duplicates a scenario — different concern |
| `/scenarios/{id}/load` (GET) | Loads a scenario — read-only |
| `/scenarios/add` (POST) | Adds a scenario — different concern |
| `/scenarios/history` (GET) | Refreshes history — read-only |
| `/scenarios/compare` (GET) | Renders comparison — read-only |

These are all separate route families and would need their own
characterization + extraction phases (51I-1 / 51I-2, etc.).

## Existing scenario_state_service.py (Phase 50 pre-existing)

`app/services/scenario_state_service.py` (232 lines) already exists
from Phase 50. It exposes **4 data-layer helpers**:

1. `build_workspace_state_metadata(workspace_state) -> dict`
2. `resolve_runtime_snapshot(*, user, project_record, workspace_state, runtime_origin) -> RuntimeSnapshotResolution`
3. `check_runtime_allowed(workspace_state, snapshot) -> (allow, origin, message)`
4. `scenario_provenance_for_record(project_record, scenario_record) -> dict | None`

It does NOT contain route orchestration. No `execute_*_route()`,
no `ScenarioStateRouteOutcome` dataclass.

**`build_workspace_state_metadata` is what `_workspace_state_meta`
in main_web.py delegates to** (Phase 50B). So the draft and discard
routes already use a small slice of scenario_state_service
indirectly.

## Recommended extraction boundary for 51H-2

Two options, with the trade-offs:

### Option A — Extend `app/services/scenario_state_service.py`

**Pros:**
- Single module for all scenario-state concerns.
- Helpers already in place (build_workspace_state_metadata, etc.)
  can be co-located with route orchestration.

**Cons:**
- Mixes data-layer helpers (pure, no Request, no form, no auth)
  with route orchestration (impure, requires Request, form, auth).
- Adds route-orchestration concerns to a module currently scoped
  to data-layer concerns. The four existing helpers do not import
  anything from main_web; adding route orchestration would pull in
  request/form/auth dependencies, increasing the module's surface
  area and increasing the risk of import cycles.

### Option B — Create `app/services/scenario_state_route_service.py`

**Pros:**
- Clean separation of concerns. scenario_state_service.py stays
  data-layer only; the new module is route-orchestration only.
- Follows the Phase 51B/51C-2/51D-2/51E-2/51G-2 canonical pattern
  (one service per route family).
- Smaller blast radius: 51H-2 only adds ONE new file; Option A
  modifies an existing file.
- Easier to test in isolation.

**Cons:**
- One more file in `app/services/`.
- Future "scenario-state" extensions (Phase 50, 51) might want to
  live in a unified module. We can address that when those phases
  come up.

### Recommendation: **Option B (scenario_state_route_service.py)**

This matches the canonical Phase 51B-51G-2 pattern. The new module
will contain:

- `ScenarioStateRouteOutcome` dataclass (template_name, context,
  status_code, headers, is_redirect, redirect_url) — actually,
  since these routes return JSON, the outcome should carry a
  `payload: dict` and `status_code: int` instead of template_name.
- `ScenarioStateRouteDeps` dataclass (15-20 callables + a few
  constants) — passed by main_web.
- `execute_draft_route(*, request, form, user, deps) -> ScenarioStateRouteOutcome`
- `execute_discard_route(*, request, form, user, deps) -> ScenarioStateRouteOutcome`

Or a single `execute_scenario_state_route(*, request, form, user,
action: Literal["draft", "discard"], deps) -> ScenarioStateRouteOutcome`
that dispatches.

The 51H-1 test suite (92 tests) already pins all current behavior,
so 51H-2 can refactor freely and use the same test suite as a
regression net.

## Test results

| Suite | Result |
|---|---|
| `pytest tests/test_phase51h1_scenario_state_route_family_characterization.py` | **92 passed**, 0 failed, 0 xfail |
| `pytest tests/test_phase51f_parallel_work_guardrails.py` | (run separately — must remain green) |
| `pytest tests/test_phase51*.py` (full regression) | (run separately — must remain green) |

The 51H-1 suite covers 13 test classes:
- TestRouteExistence (5 tests)
- TestAuthenticationBehavior (8 tests)
- TestDraftStateBehavior (10 tests)
- TestDiscardStateBehavior (9 tests)
- TestScenarioProjectPersistence (4 tests)
- TestSideEffectClassification (parametrized, 9 tests)
- TestResponseBehavior (6 tests)
- TestArchitectureGuardrails (parametrized + 6 standalone)
- TestPhase51FGuardrailsSmokeCheck (2 tests)
- TestExistingScenarioStateServiceHelpers (6 tests)
- TestBehaviorQuirks (8 tests)
- TestExtractionBoundaryMarkers (4 tests)
- TestImportSmoke (3 tests)

## Guardrails preserved

- No financial formula / model / project factory / fixture CSV
  changes.
- No schema / migration changes.
- No new JavaScript financial calculations.
- /run, /compare, /validate, /download, /save-run route+service
  from Phases 51A-51G-2 remain thin and intact.
- run_service.py, compare_service.py, validation_service.py,
  download_service.py, save_run_service.py,
  export_service.py, export_audit_service.py all remain
  intact (unchanged).
- scenario_state_service.py is unchanged (still 4 data-layer
  helpers).
- No new app/services/* file is created in 51H-1.
- No new imports of main_web or main_api.
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
- All 15 Phase 51G-1 /save-run behaviors preserved (no regression).
- All 6 Phase 51G-1 quirks preserved (no regression).
- Phase 51G-3 user_created branch fix preserved (no regression).

## Known failures

- `tests/test_persistence.py` + `tests/test_repository.py`:
  ImportError on `persistence` module. Pre-existing, reproduces
  on `origin/main` HEAD. Out of scope.

## Recommended next phase

**Phase 51H-2** (separate PR with explicit user sign-off) —
Vertical extraction of `/scenarios/state/draft` and
`/scenarios/state/discard` into
`app/services/scenario_state_route_service.py`. Follow the
Phase 51B/51C-2/51D-2/51E-2/51G-2 canonical pattern:

- main_web.py routes become thin (auth + form + deps + service
  call + JSONResponse).
- Service owns orchestration.
- Deps bundle (callable injection).
- One-way import direction (service does NOT import main_web or
  main_api).
- Preserve all 12 behavior quirks (including the
 401 JSON unauth quirk, the no-HX-Trigger quirk, the
 discard-snapshot quirk, the message constant strings, etc.).
- Preserve all intended side effects
 (`save_workspace_state` / `discard_workspace_draft`).
- Forbidden side effects remain absent.

After 51H-2 (or instead of it):
- Phase 51I-1 + 51I-2: project save-as service family
  (`/projects/{project_code}/save-as`, `/projects/create`).
- Phase 51J: optional structural guardrail phase
  (`export_service.py` / `export_audit_service.py` does NOT
  import `main_web`).

`/run`, `/compare`, `/validate`, `/download`, `/save-run`
(Phases 51A-51G-2) and `/scenarios/state/*` (Phase 51H-2)
now serve as the canonical templates for vertical extraction.
