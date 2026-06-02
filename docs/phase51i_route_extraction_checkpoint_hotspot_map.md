# Phase 51I — Route extraction checkpoint and updated hotspot map

## Current baseline

| Field | Value |
|---|---|
| **Current main SHA** | `3300b5df2a0ee902b7307720ce8384240b46b29c` |
| **Latest merged phase** | Phase 51H-2 (PR #395) — /scenarios/state/* extraction into `scenario_state_route_service.py` |
| **rc1 frozen SHA** | `b425a0708719eaa5e1d922b1008e5609758e0ad4` (verified unchanged) |
| **Phase 51F guardrail status** | ✅ ALL GREEN — engine-output golden, parity-core lock, no-service-imports-main_web/main_api |
| **Known pre-existing issue** | `tests/test_persistence.py` and `tests/test_repository.py` may fail collection with `ImportError: No module named 'persistence'`. Pre-existing, out of scope. |
| **Branch** | `phase51i-route-extraction-checkpoint-hotspot-map` |
| **Base SHA** | `3300b5df2a0ee902b7307720ce8384240b46b29c` (origin/main @ PR #395 merge) |

## Completed route extractions

| # | Route | Service module | Char phase | Extr phase | Bugfix phase | Current route size (non-blank) | One-way import | Key side effects |
|---|---|---|---|---|---|---|---|---|
| 1 | POST /run | `app/services/run_service.py` | 51A | 51B | — | 67 (thin + service deps) | ✓ no main_web import | run_project + record_workspace_runtime + update_scenario_last_run_summary + record_export (for Excel download via run) |
| 2 | POST /compare | `app/services/compare_service.py` | 51C-1 | 51C-2 | — | 35 (thin + service deps) | ✓ no main_web import | compare_scenarios (read-only) |
| 3 | POST /validate | `app/services/validation_service.py` | 51D-1 | 51D-2 | — | 34 (thin + service deps) | ✓ no main_web import | _validate_form (read-only validation) |
| 4 | POST /download + GET /download | `app/services/download_service.py` | 51E-1 | 51E-2 | — | 48 / 49 (thin + service deps) | ✓ no main_web import | record_download_export + build export payloads |
| 5 | POST /save-run | `app/services/save_run_service.py` | 51G-1 | 51G-2 | **51G-3** (user_created latent bug fix) | 61 (thin + service deps) | ✓ no main_web import | save_run + save_project (1× each, save_run first; save_project.runtime_timestamp = run_record.created_at) |
| 6 | POST /scenarios/state/draft + POST /scenarios/state/discard | `app/services/scenario_state_route_service.py` | 51H-1 | 51H-2 | — | 36 / 36 (thin + service deps) | ✓ no main_web import | save_workspace_state (draft × 1, discard fallback × 0-1) + discard_workspace_draft (discard × 1) |

**Total: 6 route families fully extracted. 6 service modules (run, compare, validate, download, save_run, scenario_state_route) own orchestration. 1 data-layer module (scenario_state_service) remains untouched. 2 export-related modules (export_service, export_audit_service) are helpers, not route orchestration.**

## Service inventory

| Service file | Lines | Classification | Public API | Imports main_web? | Imports main_api? |
|---|---|---|---|---|---|
| `app/services/run_service.py` | 653 | **Route orchestration** | `RunRouteDeps`, `RunRouteOutcome`, `execute_run_route` | ❌ no | ❌ no |
| `app/services/compare_service.py` | 299 | **Route orchestration** | `CompareRouteDeps`, `CompareRouteOutcome`, `execute_compare_route` | ❌ no | ❌ no |
| `app/services/validation_service.py` | 281 | **Route orchestration** | `ValidateRouteDeps`, `ValidateRouteOutcome`, `execute_validate_route` | ❌ no | ❌ no |
| `app/services/download_service.py` | 569 | **Route orchestration** | `DownloadRouteDeps`, `DownloadRouteOutcome`, `execute_post_download_route`, `execute_get_download_route` | ❌ no | ❌ no |
| `app/services/save_run_service.py` | 438 | **Route orchestration** | `SaveRunRouteDeps`, `SaveRunRouteOutcome`, `execute_save_run_route` | ❌ no | ❌ no |
| `app/services/scenario_state_route_service.py` | 361 | **Route orchestration** | `ScenarioStateRouteDeps`, `ScenarioStateRouteOutcome`, `execute_draft_route`, `execute_discard_route` | ❌ no | ❌ no |
| `app/services/scenario_state_service.py` | 232 | **Data-layer helper** | `build_workspace_state_metadata`, `resolve_runtime_snapshot`, `check_runtime_allowed`, `scenario_provenance_for_record` (NO Request, NO form, NO auth) | ❌ no | ❌ no |
| `app/services/export_service.py` | 332 | **Export/audit helper** | `build_values_only_export_for_project`, `build_runtime_summary_csv_export`, `build_institutional_workbook_export`, `build_excel_export_for_post_request` | ❌ no | ❌ no |
| `app/services/export_audit_service.py` | 193 | **Export/audit helper** | `record_runtime_summary_export`, `record_institutional_workbook_export`, `record_download_export` | ❌ no | ❌ no |
| `app/services/__init__.py` | 45 | (package init) | — | ❌ no | ❌ no |
| **Total** | **3,403** | — | — | — | — |

**All 9 services verified clean (no main_web / main_api imports).**

## Updated main_web.py hotspot map

### Auth + UI routes (low-risk, auth/UI scope — NOT extraction targets)

| Method | Path | Function | Non-blank | Service-backed? | Inline orchestration? | Risk | Recommended phase |
|---|---|---|---|---|---|---|---|
| GET | /login | login_page | 12 | n/a | n/a | low | out of scope (auth) |
| POST | /login | login_endpoint | 50 | n/a | auth + session | low | out of scope (auth) |
| POST | /logout | logout_endpoint | 8 | n/a | n/a | low | out of scope (auth) |
| GET | /public-health | public_health | 8 | n/a | n/a | low | out of scope (ops) |
| GET | /readyz | readyz | 11 | n/a | n/a | low | out of scope (ops) |
| GET | /health | health | 8 | n/a | n/a | low | out of scope (ops) |
| GET | / | index | 66 | n/a | UI render | low | out of scope (UI) |
| GET | /projects/new | new_project_form | 15 | n/a | form render | low | out of scope (UI) |
| GET | /projects/browse | browse_projects | 26 | n/a | UI render | low | out of scope (UI) |
| GET | /scenarios | list_scenarios | 21 | n/a | UI render | low | out of scope (UI) |
| GET | /scenarios/history | scenario_history | 21 | n/a | UI refresh | low | out of scope (UI) |
| GET | /scenarios/compare | scenario_compare | 36 | n/a | UI render | low | out of scope (UI) |
| GET | /scenarios/{scenario_id}/load | load_scenario | 33 | n/a | scenario load UI | low | out of scope (UI) |
| GET | /run/{run_id} | run_detail | 30 | n/a | UI render | low | out of scope (UI) |
| GET | /runs | list_runs | 20 | n/a | UI render | low | out of scope (UI) |
| GET | /exports/runtime-summary.csv | runtime_summary_csv_export | 39 | n/a | export | medium | export audit, not route extraction |
| GET | /exports/institutional-workbook.xlsx | institutional_workbook_export | 40 | n/a | export | medium | export audit, not route extraction |

### Already service-backed (Phase 51A-51H-2)

| Method | Path | Service | Non-blank | Service-backed? | Risk | Recommended phase |
|---|---|---|---|---|---|---|
| POST | /validate | validation_service | 34 | ✓ (Phase 51D-2) | done | (done) |
| POST | /run | run_service | 67 | ✓ (Phase 51B) | done | (done) |
| POST | /compare | compare_service | 35 | ✓ (Phase 51C-2) | done | (done) |
| POST | /download | download_service | 48 | ✓ (Phase 51E-2) | done | (done) |
| GET | /download | download_service | 49 | ✓ (Phase 51E-2) | done | (done) |
| POST | /save-run | save_run_service | 61 | ✓ (Phase 51G-2 + 51G-3) | done | (done) |
| POST | /scenarios/state/draft | scenario_state_route_service | 36 | ✓ (Phase 51H-2) | done | (done) |
| POST | /scenarios/state/discard | scenario_state_route_service | 36 | ✓ (Phase 51H-2) | done | (done) |

### Remaining INLINE route families (future extraction targets)

| Method | Path | Function | Non-blank | Service-backed? | Risk | Recommended phase |
|---|---|---|---|---|---|---|
| POST | /scenarios/save | save_scenario_endpoint | **88** | ❌ inline | **high** (persistence-heavy: save_scenario + scenario state mutations) | **Phase 51J-1 + 51J-2** (next) |
| POST | /scenarios/{scenario_id}/duplicate | duplicate_scenario_endpoint | **67** | ❌ inline | **high** (persistence: save_scenario with new scenario_id) | **Phase 51K-1 + 51K-2** |
| POST | /scenarios/add | add_scenario_endpoint | **62** | ❌ inline | **high** (persistence: save_scenario with new record) | **Phase 51L-1 + 51L-2** |
| POST | /scenarios/{scenario_id}/rename | rename_scenario_endpoint | **51** | ❌ inline | medium (update_scenario; light persistence) | Phase 51O-1 + 51O-2 |
| POST | /scenarios/{scenario_id}/archive | archive_scenario_endpoint | **47** | ❌ inline | medium (update_scenario state) | Phase 51P-1 + 51P-2 |
| POST | /scenarios/{scenario_id}/update-overrides | update_scenario_overrides_endpoint | **25** | ❌ inline | medium (update_scenario) | Phase 51Q-1 + 51Q-2 |
| POST | /scenarios/{scenario_id}/select | select_scenario_endpoint | **21** | ❌ inline | medium (update_scenario active flag + workspace state) | Phase 51R-1 + 51R-2 |
| POST | /projects/create | create_project_endpoint | **117** | ❌ inline | **high** (persistence-heavy: create_project_record + save_workspace_state) | **Phase 51M-1 + 51M-2** |
| POST | /projects/{project_code}/save-as | save_as_project_endpoint | **49** | ❌ inline | **high** (persistence: create_project_record with new project_code) | **Phase 51N-1 + 51N-2** |

**Subtotal: 9 inline route families, 527 non-blank lines of orchestration, 4 high-risk + 5 medium-risk.**

## Remaining risk areas

### Risk 1: scenario save/duplicate/add (persistence-heavy)
- These routes call `save_scenario(...)` and `update_scenario(...)` repository
  functions and may also call `save_workspace_state(...)` to update the
  active scenario pointer.
- **Total inline orchestration: ~217 non-blank lines.**
- These are the next 3 highest-value extraction targets after /scenarios/state/*.

### Risk 2: project create / save-as (persistence-heavy)
- `/projects/create` is 117 non-blank lines, the largest remaining inline
  route. It calls `create_project_record(...)` (a heavy persistence call)
  plus `save_workspace_state(...)` to seed a fresh workspace.
- `/projects/{project_code}/save-as` is 49 non-blank lines. It calls
  `create_project_record(...)` with a derived project_code.
- **Total inline orchestration: 166 non-blank lines.**
- These are the 4th and 5th highest-value extraction targets.

### Risk 3: repository.py (god-module risk)
- `app/persistence/repository.py` is the central persistence layer.
- It exposes ~50+ functions: `save_run`, `save_project`, `save_scenario`,
  `save_workspace_state`, `discard_workspace_draft`, `select_scenario`,
  `update_scenario`, `list_scenarios`, `record_workspace_runtime`,
  `record_export`, `record_download_export`, etc.
- It is **not a service** — it is a repository module that the service
  modules call.
- Phase 52A (optional) could map the full repository surface, classify
  each function (read/write/audit/state mutation), and document which
  routes call which functions.
- This is a documentation/structural phase, NOT a refactor. It would
  precede more persistence-heavy route extractions to surface the
  underlying call graph.

### Risk 4: UI is not fully revamped
- The /scenarios, /scenarios/history, /scenarios/compare, /scenarios/{id}/load,
  /run/{run_id}, /runs, /projects/new, /projects/browse, / GET / routes
  are all UI render routes. They are out of scope for route extraction
  (they do not call persistence functions; they only render templates).
- A future "UI refactor" phase would extract UI render helpers into
  separate modules, but this is **not** part of the Phase 51 program.

### Risk 5: generic solar/wind remains exploratory
- The /run route has a `factory_template` branch that maps
  `template_source` to `Solar` or `Wind` runtime keys (after TUHO /
  Oborovo). This is a fallback for non-named-template projects.
- This is **NOT promoted to a production claim**; it is exploratory
  and unvalidated. Phase 50C-2 introduced the runtime snapshot
  resolver that supports this branch. No further work planned.

### Risk 6: no-go claims (pilot / lender / SaaS / bankability)
- **No bankability / lender-ready / audit / certification / SaaS-ready
  claims.**
- Controlled trusted pilot readiness only in **narrow TUHO / Oborovo
  scope**.
- Generic solar / wind are **exploratory and unvalidated**.
- G20 remains **BLOCKED**.
- R99 / R102 remain **NOT APPROVED**.
- `partial_pay_sweep` is **not promoted**.
- Flat / min DSCR sculpting is **not promoted**.

## Recommended next sequence (5–8 phases)

**Option A: Continue route extraction (recommended).**

| Phase | Scope | Why this order |
|---|---|---|
| **51J-1** | /scenarios/save golden characterization | Largest remaining inline route (88 non-blank); persistence-heavy; well-understood behavior |
| **51J-2** | /scenarios/save extraction into `app/services/scenarios_save_service.py` | 88 → ~36 non-blank route; 1:1 extraction with no factory changes |
| **51K-1** | /scenarios/{scenario_id}/duplicate characterization | 67 non-blank; persistence-heavy (save_scenario with new scenario_id) |
| **51K-2** | /scenarios/{scenario_id}/duplicate extraction | Same pattern as 51J-2 (or extend 51J's service with a duplicate entry point) |
| **51L-1** | /scenarios/add characterization | 62 non-blank; persistence-heavy |
| **51L-2** | /scenarios/add extraction | Same pattern |
| **51M-1** | /projects/create characterization | **117 non-blank** (largest remaining inline route); persistence-heavy (create_project_record + save_workspace_state) |
| **51M-2** | /projects/create extraction | Same pattern; the largest single-route reduction |

**Why Option A:** Each phase is self-contained (characterize → extract).
The patterns from 51B/51C-2/51D-2/51E-2/51G-2/51H-2 are now well-established.
The candidate service modules (`scenarios_save_service.py`,
`scenarios_duplicate_service.py`, `scenarios_add_service.py`,
`projects_create_service.py`) would each be small (200-400 lines) and
focused. Total orchestration extracted: 88 + 67 + 62 + 117 = 334 non-blank
lines. After Option A, the remaining inline route families would be
4 medium-risk: rename / archive / update-overrides / select
(21-51 non-blank each, easier to extract after the heavy ones).

**Option B: Repository mapping (alternative, only if needed).**

| Phase | Scope | Why this order |
|---|---|---|
| **52A** | Repository mapping and persistence boundary inventory | Map all 50+ repository functions; classify read/write/audit; document which routes call which functions |
| (then resume 51J-1 / 51J-2) | /scenarios/save characterization + extraction | As above |

**Why Option B might be preferred:** The scenario-state and /save-run
extractions touched only a small subset of repository functions
(`save_run`, `save_project`, `save_workspace_state`, `discard_workspace_draft`).
The remaining 6 inline route families would touch more functions
(`save_scenario`, `update_scenario`, `create_project_record`, etc.).
A repository mapping phase would surface the full call graph
before more extraction phases. This is a docs/reports-only phase;
no production code changes.

**Decision (Phase 51I recommendation): Option A.** The 4
characterization-then-extraction phases (51J, 51K, 51L, 51M) cover
the 4 highest-risk remaining routes. The repository mapping
(Option B / Phase 52A) can be done LATER, in parallel with
Agent B's docs work, if the scenario / project persistence calls
become unwieldy.

## Parallel Agent B file ownership

Agent B can continue docs/reports external review / pilot readiness
work in parallel with the Phase 51J-51M extraction series. Agent B's
allowed scope:

- **Allowed**:
  - `docs/external_review/*` (new or existing)
  - `reports/external_review/*` (new or existing)
  - `docs/phase*_*.md` (new phase docs, IF rebased on latest main)
  - `reports/phase*_*.json` (new phase reports, IF rebased on latest main)
  - pilot readiness summaries, risk registers, governance posture
    documents
- **NOT allowed** (Agent B must not touch):
  - `main_web.py` (production code)
  - `app/services/*` (route orchestration services)
  - `app/waterfall_core.py` (parity-core)
  - `app/project_factories.py` (parity-core)
  - `app/persistence/repository.py` (god-module; no refactor in 51J-51M)
  - `reports/phase7_tuho_senior_debt_sizing_extraction.csv` (parity-core)
  - `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` (parity-core)
  - any `static/js/*` (financial calculations)
  - any fixture CSV
  - any schema / migration file
- **Coordination rules**:
  - If Agent B opens a docs/report-only PR, it must rebase on the
    latest main and avoid changing the Phase 51 docs / reports
    unless explicitly necessary.
  - If Agent B needs to add a new doc that depends on a Phase 51
    route extraction (e.g. a doc that references /scenarios/save
    behavior), Agent B should wait for the relevant Phase 51J-51M
    PR to merge, then rebase.
  - Agent B can independently verify the Phase 51F guardrails
    (engine-output + parity-core + no-service-imports) by running
    `pytest tests/test_phase51f_parallel_work_guardrails.py`.

## No-go claims (repeat)

- **No bankability / lender-ready / audit / certification / SaaS-ready claims.**
- **Controlled trusted pilot readiness only in narrow TUHO / Oborovo scope.**
- **Generic solar / wind are exploratory and unvalidated.**
- **G20 remains BLOCKED.**
- **R99 / R102 remain NOT APPROVED.**
- **`partial_pay_sweep` is not promoted.**
- **Flat / min DSCR sculpting is not promoted.**

## Test evidence

| Command | Result |
|---|---|
| `pytest tests/test_phase51i_route_extraction_checkpoint_hotspot_map.py` | **63 passed**, 0 failed |
| `pytest tests/test_phase51f_parallel_work_guardrails.py` | (run separately — must remain green) |
| `pytest tests/test_phase51*.py` (full regression) | (run separately — must remain green) |

The 51I test suite covers 8 test classes (63 tests):
- TestCompletedExtractions (7 — parametrized over 6 service modules + 1 all-present check)
- TestNoServiceImportsMainWebOrMainApi (18 — 9 services × 2 import-direction checks)
- TestServiceClassification (8)
- TestMainWebRouteHotspotMap (4)
- TestPhase51FGuardrailsSmokeCheck (2)
- TestRecommendedNextSequenceMarkers (5)
- TestPhase51JPrerequisites (2)
- TestImportSmoke (3)

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
  intact (unchanged).
- No new app/services/* file is created in 51I.
- No new imports of main_web or main_api (all 9 services
  remain clean).
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

## Known failures

- `tests/test_persistence.py` + `tests/test_repository.py`:
  ImportError on `persistence` module. Pre-existing,
  reproduces on `origin/main` HEAD. Out of scope.

## Recommended next phase

**Phase 51J-1** (separate PR with explicit user sign-off) —
`/scenarios/save` golden characterization. The 88 non-blank
inline route is the highest-value remaining target. Follow
the Phase 51A/51C-1/51D-1/51E-1/51G-1/51H-1 characterization
pattern. 51I has already documented the extraction
prerequisites (`scenarios_save_service.py` does not yet
exist; the route has substantial orchestration; one-way
import direction is preserved; all 9 services are clean).

After 51J-1 + 51J-2: 51K-1 + 51K-2 (duplicate), 51L-1 + 51L-2 (add),
51M-1 + 51M-2 (project create). The 4 medium-risk routes
(rename / archive / update-overrides / select) can follow
in 51O-51R.
