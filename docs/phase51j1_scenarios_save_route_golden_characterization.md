# Phase 51J-1 — POST /scenarios/save golden characterization

## Base SHA

`09481dc65c57e7bd318153a6816af80c4c0bbf7f` (origin/main @ PR #396
merge, Phase 51I route extraction checkpoint and updated hotspot
map)

## Objective

Characterize the current behavior of POST /scenarios/save in
`main_web.py` BEFORE Phase 51J-2 extraction into
`app/services/scenarios_save_service.py`. Pin all current
behavior with tests + docs only. This is a **characterization-
only phase** — no production code changes.

Phase 51I's hotspot map identified POST /scenarios/save as
the next recommended extraction target (88 non-blank,
persistence-heavy, high risk).

## In-scope route

| Route | Method | Handler | Non-blank | File |
|---|---|---|---|---|
| `/scenarios/save` | POST | `save_scenario_endpoint` | **88** | main_web.py:2163-2255 |

(Adjacent routes — `/scenarios/{scenario_id}/duplicate`,
`/scenarios/add`, `/scenarios/{scenario_id}/rename`,
`/scenarios/{scenario_id}/archive`,
`/scenarios/{scenario_id}/update-overrides`,
`/scenarios/{scenario_id}/select` — are NOT in 51J-1 scope;
they are separate route families targeted by 51K-51R.)

## Route responsibilities

POST /scenarios/save persists the current form snapshot as a
saved scenario. The route:

1. Authenticates the user (302 redirect to /login if no user).
2. Reads the form snapshot.
3. Resolves the project_record + existing_workspace_state
   from the snapshot.
4. **Soft-blocks** factory_template and saved_baseline projects
   by returning 200 + render with a "Save is not available" message
   (instead of calling save_scenario).
5. Computes a scenario_name from project_name + scenario +
   current datetime.
6. Calls `save_scenario(...)` with the snapshot, governance
   state, and replay_metadata (preserves last_run_summary if
   existing workspace state matches).
7. Calls `bind_workspace_to_scenario(...)` to bind the new
   scenario to the workspace.
8. Renders the scenario workspace with scenarios, history,
   exports, export_lineage, and scenario_summary_cards.

## Auth / session / input map

- All inputs read from `await request.form()` (POST form-encoded).
- `user_id` always derived from `user.user_id` (session). NEVER
  from form.
- Form is collected ONCE via `_collect_form_snapshot(form)`.
  The route treats the form as a generic snapshot dict (no
  per-field reads).
- The ONLY snapshot read is `snapshot.get('scenario', 'Base')`
  to derive the scenario name suffix.
- `project_id`, `project_code`, `project_name`, `template_source`,
  `source_project_template`, `project_origin` all come from
  the resolved `project_record` (not the form).

## Active project / scenario behavior

- The route resolves the project via
  `_project_workspace_from_snapshot(user, snapshot)`.
- The route reads `project_record.project_origin` to decide
  whether to block.
- The route blocks `factory_template` and `saved_baseline`
  projects with a soft-fail (200 + render with error message).
- The route allows `user_created` projects (and any other origin
  that is not factory_template or saved_baseline).
- The blocked message includes the project_origin (with
  underscores replaced by spaces) and the project_code, and
  suggests "Use 'Save As' to create a user project."
- The success message is "Saved scenario snapshot for
  {project_name}."

## Workspace / snapshot behavior

- The route unpacks `(project_record, existing_workspace_state)
  = _project_workspace_from_snapshot(user, snapshot)`.
- `last_run_summary` is preserved if and only if
  `existing_workspace_state` exists AND its `last_runtime_snapshot`
  equals the current snapshot. Otherwise it is reset to `{}`.
- After save_scenario, the route calls `bind_workspace_to_scenario(...)`
  to bind the new scenario to the workspace (active_scenario_id,
  active_scenario_name, draft_snapshot=saved_snapshot=record.snapshot,
  dirty=False).

## Dependency / helper map

| Helper | Where it lives | Used for |
|---|---|---|
| `get_current_user` | `app.auth` | Auth check |
| `await request.form()` | (FastAPI) | Read form |
| `_collect_form_snapshot(form)` | main_web.py | Generic form snapshot |
| `_project_workspace_from_snapshot(user, snapshot)` | main_web.py | Resolve project + workspace |
| `_governance_snapshot(project_code)` | main_web.py | Governance state |
| `_replay_metadata_for_project(...)` | main_web.py | Replay metadata |
| `dt.now().strftime('%Y-%m-%d %H:%M')` | stdlib | Scenario name timestamp |
| `save_scenario(...)` | app.persistence.repository | INSERT INTO scenarios |
| `bind_workspace_to_scenario(...)` | app.persistence.repository | UPDATE workspace_state |
| `list_scenarios(...)` | app.persistence.repository | Read scenarios list |
| `get_scenario_history(...)` | app.persistence.repository | Read history |
| `list_exports(...)` | app.persistence.repository | Read exports |
| `build_export_lineage(...)` | app.persistence.repository | Read export lineage |
| `_render_scenario_workspace(...)` | main_web.py | Render response |
| `snapshots_equal(...)` | app.persistence.repository | Snapshot diff check |

## Intended persistence side-effect map

| Side effect | Class | Pin |
|---|---|---|
| `save_scenario(...)` (success branch only) | **INTENDED** | 1 call per success |
| `bind_workspace_to_scenario(...)` (success branch only) | **INTENDED** | 1 call per success |
| `list_scenarios`, `get_scenario_history`, `list_exports`, `build_export_lineage` | read-only queries | 1× each per success |
| `save_workspace_state` (via bind_workspace_to_scenario) | indirect write | 1× per success |
| `dt.now()` | timestamp for scenario_name | 1× per success |
| `_governance_snapshot` | metadata assembly | 1-2× per success |
| `_replay_metadata_for_project` | metadata assembly | 2× per success (save + bind) |
| `save_workspace_state` direct | NOT called by route | 0 (via bind) |
| `save_run` | NOT called | 0 |
| `save_project` | NOT called | 0 |
| `record_export` family | NOT called | 0 |
| `record_workspace_runtime` | NOT called | 0 |
| `update_scenario_last_run_summary` | NOT called | 0 |
| `db.add` / `db.commit` / `db.flush` | NOT used | 0 |
| `session.add` / `session.commit` | NOT used | 0 |
| `run_project` (model exec) | NOT called | 0 |
| `build_institutional_workbook_export` | NOT called | 0 |
| `build_excel_export_for_post_request` | NOT called | 0 |
| `build_runtime_summary_csv_export` | NOT called | 0 |
| `build_values_only_export_for_project` | NOT called | 0 |

## Replay metadata export_type values

| Side effect | export_type |
|---|---|
| `save_scenario` | `"saved_scenario_snapshot"` |
| `bind_workspace_to_scenario` | `"workspace_saved_boundary"` (with non-ASCII char `\u03b5`/etc., or its escaped form) |

## Forbidden side-effect confirmation

Verified absent in code (after stripping docstrings, comments,
and string literals):

- `record_export`: 0
- `record_download_export`: 0
- `record_runtime_summary_export`: 0
- `record_institutional_workbook_export`: 0
- `record_workspace_runtime`: 0
- `update_scenario_last_run_summary`: 0
- `db.add` / `db.commit` / `db.flush`: 0
- `session.add` / `session.commit`: 0
- `save_run`: 0
- `save_project`: 0
- `run_project`: 0

The route is pure scenario persistence + workspace binding.
It does not touch export audit, runtime state, scenario run
history, project records, model execution, or Excel exports.

## Response / template / JSON / header behavior

| Behavior | Value |
|---|---|
| Status code (auth OK, block) | 200 |
| Status code (auth OK, success) | 200 |
| Status code (no auth) | **302** redirect to /login |
| Status code (4xx error) | NEVER (no HTTPException) |
| Status code (5xx error) | FastAPI default (no broad except) |
| Content-Type (auth OK) | text/html (HTMLResponse via _render_scenario_workspace) |
| Content-Type (no auth) | (redirect, no body) |
| Template name | (uses _render_scenario_workspace, not a single template) |
| HX-Trigger header | NO (Quirk 6) |
| HX-Redirect header | NO |
| Location header (unauth) | `/login` |
| Body (block) | workspace render with "Save is not available for {origin} '{code}'. Use 'Save As' to create a user project." |
| Body (success) | workspace render with "Saved scenario snapshot for {project_name}." + populated scenarios/history/exports/lineage/cards |

## Behavior quirks

| # | Quirk | Source |
|---|---|---|
| 1 | scenario_name is built as `f"{project_name} {snapshot.get('scenario', 'Base')} {dt.now().strftime('%Y-%m-%d %H:%M')}"` (timestamp IS the name suffix, no separate field) | `scenario_name = f"..."` in route |
| 2 | Blocked message replaces underscores with spaces: `project_origin.replace('_', ' ')` | blocked-branch message |
| 3 | Blocked message includes the suggestion: "Use 'Save As' to create a user project." | blocked-branch message |
| 4 | `last_run_summary` is preserved if and only if existing_workspace_state exists AND its last_runtime_snapshot equals the current snapshot. Otherwise reset to `{}`. | ternary in save_scenario kwargs |
| 5 | Blocked branch is a soft-fail (200 + render with message), NOT a hard 4xx error. save_scenario and bind_workspace_to_scenario are NEVER called in the blocked branch. | `if project_record.project_origin in (...): return _render_scenario_workspace(...)` |
| 6 | No HX-Trigger header (unlike /save-run which sets HX-Trigger: refreshHistory). Success response is a full workspace render, not an HTMX partial. | route does not set HX-Trigger |
| 7 | scenario_summary_cards include an 'export_count' field, computed by counting entries in export_lineage per scenario_name | `for entry in export_lineage: export_counts[entry['scenario_name']] = ...` |
| 8 | scenario_summary_cards include specific fields: scenario_id, scenario_name, project_code, updated_at, copied_from_scenario_id, project_irr, equity_irr, avg_dscr, export_count, governance_state | card dict literal in route |
| 9 | Two distinct export_type values: save_scenario uses "saved_scenario_snapshot"; bind_workspace_to_scenario uses "workspace_saved_boundary" (non-ASCII char may be escaped) | _replay_metadata_for_project call sites |
| 10 | Route does NOT call _validate_form. Accepts any form input as a snapshot. (Same as /scenarios/state/draft and /scenarios/state/discard.) | route does not import or call _validate_form |

## Extraction risks for Phase 51J-2

1. **Soft-block vs hard-error** — the blocked branch is a soft-fail
   (200 + render). 51J-2 must preserve this behavior. The block check
   should stay in the service, not the route.
2. **last_run_summary conditional** — the conditional
   `existing_workspace_state.last_runtime_summary if ... else {}`
   is subtle. 51J-2 must preserve it exactly.
3. **scenario_name timestamp format** — `'%Y-%m-%d %H:%M'` is a
   fixed format. 51J-2 must preserve it exactly.
4. **scenario_summary_cards shape** — the card dict has 10 fields
   including `export_count` (computed by counting export_lineage
   entries per scenario_name). 51J-2 must preserve the card shape
   exactly.
5. **Two distinct export_type values** — must be preserved
   (save_scenario uses "saved_scenario_snapshot", bind_workspace
   uses "workspace_saved_boundary").
6. **No HTMX headers / no template render / no JSON** — the
   success response is a full workspace render. 51J-2 should use
   the JSON response pattern (similar to /scenarios/state/*) for
   the route outcome, but the rendered HTML is the success path.
   The ScenarioSaveRouteOutcome would carry the populated
   scenarios/history/exports/etc. and the route would pass them
   to _render_scenario_workspace.
7. **bind_workspace_to_scenario always called after save_scenario**
   — if save_scenario raises, bind_workspace is not called. 51J-2
   must preserve this ordering.
8. **Block check before save_scenario** — the block check is
   structural (early return). 51J-2 should keep this in the
   service, not the route.

## Recommended extraction boundary for 51J-2

**Option B (recommended):** Create new
`app/services/scenarios_save_service.py` with:

- `ScenarioSaveRouteOutcome` dataclass (payload, status_code,
  headers, is_redirect, redirect_url, plus a
  `render_context: dict` field for the response render data)
- `ScenarioSaveRouteDeps` dataclass (~13-15 callables + 0 constants
  — the route does NOT validate the form, so no validate_form field
  is needed)
- `execute_scenarios_save_route(*, request, form, user, deps) ->
  ScenarioSaveRouteOutcome` — a single entry point that handles
  both the block check and the success path

**Why not extend scenario_state_service.py:** scenario_state_service.py
is a data-layer module (no Request, no form, no auth). Adding route
orchestration to it would mix data-layer and route-layer concerns.

**Why not reuse scenario_state_route_service.py:** That service
handles a different family (/scenarios/state/draft and /discard —
workspace mutations without scenario row creation). /scenarios/save
creates a new ScenarioRecord and binds it to the workspace, which
is a different concern.

**Candidate deps bundle (~13-15 callables):**
- `collect_form_snapshot`
- `project_workspace_from_snapshot`
- `governance_snapshot`
- `replay_metadata_for_project`
- `save_scenario`
- `bind_workspace_to_scenario`
- `list_scenarios`
- `get_scenario_history`
- `list_exports`
- `build_export_lineage`
- `snapshots_equal`
- `render_scenario_workspace` (for the response render)
- (potentially) `dt_provider` (a callable returning datetime, to
  allow test injection; alternatively just use `dt.now` directly)
- (potentially) `is_blocked_project_origin` (a callable that
  returns True for factory_template / saved_baseline; alternatively
  just check inline)

## Test results

| Suite | Result |
|---|---|
| `pytest tests/test_phase51j1_scenarios_save_route_golden_characterization.py` | **85 passed**, 0 failed, 0 xfail |
| `pytest tests/test_phase51f_parallel_work_guardrails.py` | (regression — must remain green) |
| `pytest tests/test_phase51*.py` (full regression) | (must remain green) |

The 51J-1 suite covers 13 test classes (85 tests):
- TestRouteExistence (4)
- TestAuthenticationBehavior (5)
- TestFormInputBehavior (6)
- TestActiveProjectScenarioBehavior (7)
- TestWorkspaceSnapshotBehavior (5)
- TestPersistenceSideEffects (13)
- TestResponseBehavior (6)
- TestErrorFallbackBehavior (3)
- TestForbiddenSideEffectsAbsent (6)
- TestArchitectureGuardrails (parametrized + 1, 17 total)
- TestPhase51FGuardrailsSmokeCheck (2)
- TestImportSmoke (2)
- TestBehaviorQuirks (10)

## Guardrails preserved

- No financial formula / model / project factory / fixture CSV
  changes.
- No schema / migration changes.
- No new JavaScript financial calculations.
- /run, /compare, /validate, /download, /save-run,
  /scenarios/state/* route+service from Phases 51A-51H-2
  remain thin and intact.
- run_service.py, compare_service.py, validation_service.py,
  download_service.py, save_run_service.py,
  scenario_state_route_service.py, scenario_state_service.py,
  export_service.py, export_audit_service.py all remain
  intact (UNCHANGED).
- No new app/services/* file is created in 51J-1.
- No new imports of main_web or main_api.
- main_web.py has zero direct record_export calls (no
  production code changes).
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
- All 30 Phase 51H-2 behaviors preserved.
- All 12 Phase 51H-2 quirks preserved.
- Phase 51G-3 user_created branch fix preserved (no regression).
- All 6 canonical route extractions remain intact.

## Known failures

- `tests/test_persistence.py` + `tests/test_repository.py`:
  ImportError on `persistence` module. Pre-existing,
  reproduces on `origin/main` HEAD. Out of scope.

## Recommended next phase

**Phase 51J-2** (separate PR with explicit user sign-off) —
Vertical extraction of POST /scenarios/save into
`app/services/scenarios_save_service.py`. Follow the
Phase 51B/51C-2/51D-2/51E-2/51G-2/51H-2 canonical pattern:

- main_web.py route becomes thin (auth + form + deps + service
  call + render).
- Service owns orchestration.
- Deps bundle (callable injection).
- One-way import direction.
- Preserve all 10 quirks.
- Preserve all intended side effects.
- Preserve soft-block behavior (200 + render with error message).
- Preserve scenario_name timestamp format.
- Preserve scenario_summary_cards shape.

After 51J-2: Phase 51K-1 + 51K-2 (`/scenarios/{scenario_id}/duplicate`,
67 non-blank, high risk), 51L-1 + 51L-2 (`/scenarios/add`, 62
non-blank, high risk), 51M-1 + 51M-2 (`/projects/create`, 117
non-blank, high risk). The 4 medium-risk routes
(rename / archive / update-overrides / select) can follow in
51O-51R.
