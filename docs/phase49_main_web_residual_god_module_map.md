# Phase 49 — main_web.py Residual God Module Map

## Post-Phase 49 Status
- **Direct `record_export` calls in main_web.py: 0** ✅
- **`record_export` imported in main_web.py: No** ✅
- **Export routes fully delegated to services: Yes** ✅

## Route Inventory (33 routes)

| Route | Method | Auth | High-Risk Extraction Candidate |
|-------|--------|------|-------|
| `/login` | GET | No | — |
| `/login` | POST | No | — |
| `/logout` | POST | No | — |
| `/public-health` | GET | No | — |
| `/readyz` | GET | No | — |
| `/health` | GET | Yes | — |
| `/` | GET | Yes | — |
| `/validate` | POST | Yes | — |
| `/run` | POST | Yes | **HIGH** — runtime orchestration |
| `/compare` | POST | Yes | **HIGH** — runtime orchestration |
| `/download` | GET | Yes | ✅ Extracted |
| `/download` | POST | Yes | ✅ Extracted |
| `/exports/runtime-summary.csv` | GET | Yes | ✅ Extracted |
| `/exports/institutional-workbook.xlsx` | GET | Yes | ✅ Extracted |
| `/projects/new` | GET | Yes | — |
| `/projects/browse` | GET | Yes | — |
| `/projects/create` | POST | Yes | — |
| `/scenarios` | GET | Yes | — |
| `/scenarios/state/draft` | POST | Yes | — |
| `/scenarios/state/discard` | POST | Yes | — |
| `/scenarios/history` | GET | Yes | — |
| `/scenarios/compare` | GET | Yes | — |
| `/scenarios/save` | POST | Yes | — |
| `/scenarios/{scenario_id}/load` | GET | Yes | — |
| `/scenarios/{scenario_id}/duplicate` | POST | Yes | — |
| `/scenarios/add` | POST | Yes | — |
| `/scenarios/{scenario_id}/select` | POST | Yes | **MEDIUM** — scenario binding |
| `/scenarios/{scenario_id}/update-overrides` | POST | Yes | **MEDIUM** — scenario overrides |
| `/projects/{project_code}/save-as` | POST | Yes | — |
| `/scenarios/{scenario_id}/rename` | POST | Yes | — |
| `/scenarios/{scenario_id}/archive` | POST | Yes | — |
| `/runs` | GET | Yes | — |
| `/save-run` | POST | Yes | **HIGH** — workspace runtime persistence |
| `/run/{run_id}` | GET | Yes | — |

## Residual Responsibility Map

### 1. Auth/Session Layer
- `get_current_user()` — cookie decoding
- `verify_login()`, `create_session_token()`, `make_session_cookie()`, `clear_session_cookie()`
- CSRF token generation/validation
- Rate limiting (`_check_rate_limit`, `_record_failed_login`)
- `_get_client_ip()`

**Extraction candidate:** `app/services/auth_service.py` — medium risk, many callers

### 2. Scenario State Management
- `_resolve_runtime_snapshot_source()` — active scenario resolution with fallback chain
- `_scenario_provenance_for_record()` — scenario provenance building
- `resolve_active_scenario_runtime_snapshot()` — from repository
- `runtime_guard_for_snapshot()` — dirty guard logic

**Extraction candidate:** `app/services/scenario_state_service.py` — high value, complex

### 3. Project/Form Parsing
- `_project_workspace_from_snapshot()` — project+workspace resolution
- `_resolve_project_record()` — project record with factory template seeding
- `_collect_form_snapshot()` — form field collection
- `_build_schema_from_form()` — schema construction from form fields
- `_validate_form()`, `_validate_numeric_field()` — validation
- `_project_baseline_snapshot()` — baseline snapshot from template
- `_project_identity_from_template_source()` — project code/name from template

**Extraction candidate:** `app/services/project_form_service.py` — medium risk, many helpers

### 4. Model Run Orchestration (`/run` route)
- `run_project()` call with snapshot override
- `run_demo_project()` call for factory templates
- `build_projectinputs_from_snapshot()` — snapshot → inputs
- `record_workspace_runtime()` — runtime record persistence
- KPI formatting (`_format_kpis`)

**Extraction candidate:** `app/services/runtime_orchestration_service.py` — high value, complex, many persistence calls

### 5. Compare Route
- `/compare` — multi-scenario runtime execution
- `_build_compare_ui_context()` — comparison data preparation

**Extraction candidate:** `app/services/compare_service.py` — medium risk

### 6. Provenance Helpers
- `_replay_metadata_for_project()` — builds full provenance dict
- `_governance_snapshot()` — governance state builder
- `build_replay_metadata()` — from `app.persistence.provenance`

**Consider keeping in main_web.py** — these are route-owned concerns; services receive pre-built dicts

### 7. Template/Context Building
- `_project_record_to_context()` — build project context for template
- `_build_export_lineage_ui_context()` — export lineage for UI
- `_workspace_state_meta()` — workspace state metadata
- `_build_schema_from_form()` — already listed above
- `_format_ui_timestamp()` — timestamp formatting

**Extraction candidate:** `app/services/ui_context_service.py` — medium risk

### 8. Persistence Calls (Repository Layer)
Direct calls to `app.persistence.repository` functions:
- `list_project_records()`, `get_project_record()`, `save_project()`
- `list_scenarios()`, `get_scenario()`, `save_scenario()`, `select_scenario()`
- `get_workspace_state()`, `save_workspace_state()`
- `list_exports()`, `list_runs()`, `get_run()`, `save_run()`
- `record_workspace_runtime()` — **pending extraction (Phase 50)**
- `record_export()` — **extracted (Phase 49)** ✅

**Note:** Repository calls are the DB layer. Extracting them to a service creates a new abstraction. Recommend mapping repository first, then extracting callers.

### 9. Operational Endpoints
- `/public-health`, `/readyz`, `/health` — monitoring
- Keep in main_web.py (very low risk, no business logic)

## High-Risk Extraction Candidates (Recommended Order)

### Priority 1: Scenario State Service (Phase 50A)
**Why:** Complex, used by both `/run` and `/download` routes, has fallback chain logic.
**What:** Extract `_resolve_runtime_snapshot_source`, `_scenario_provenance_for_record`, `runtime_guard_for_snapshot`.
**Impact:** Removes ~150 lines, centralizes scenario binding logic.

### Priority 2: Run Orchestration Service (Phase 50B)
**Why:** Largest remaining god-path, has `record_workspace_runtime`, used by `/run` route.
**What:** Extract `record_workspace_runtime`, `update_scenario_last_run_summary`, `run_project` orchestration.
**Impact:** Removes ~200 lines from `/run` route.

### Priority 3: Compare Service (Phase 50C)
**Why:** Self-contained comparison logic with template rendering.
**What:** Extract multi-scenario execution and `_build_compare_ui_context`.
**Impact:** Removes ~80 lines from `/compare` route.

### Priority 4: Project/Form Service (Phase 50D)
**Why:** Many small helpers used across routes.
**What:** Extract form parsing, validation, project resolution helpers.
**Impact:** Removes ~120 lines of helpers.

## Remaining Routes in main_web.py (Post-Phase 49)

**Orchestration only (thin routes):**
- `/`, `/validate` — rendering routes
- `/projects/*`, `/scenarios/*` — CRUD routes with direct persistence calls
- `/runs`, `/save-run`, `/run/{run_id}` — run management

**Service-extracted:**
- 4 export routes → `export_service.py` + `export_audit_service.py` ✅

**Not yet extracted:**
- `/run` — runtime orchestration (HIGH priority)
- `/compare` — comparison execution (MEDIUM priority)
- Scenario binding calls (MEDIUM priority)

## Phase 49 Statistics

| Metric | Value |
|--------|-------|
| Lines of production code changed | 0 (closeout phase) |
| New service files | 2 (`export_service.py`, `export_audit_service.py`) |
| Routes extracted | 4 / 33 |
| Direct `record_export` calls in main_web.py | 0 |
| Tests added | 191 (all passing) |
| PRs merged | 9 (#361–#369) |