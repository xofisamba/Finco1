# Phase 49 Closeout — Export Service and Audit Extraction Summary

## Base SHA
`01edb03957716caee55cfa794c693d08b2d1acfb` (after PR #369 merge)

## Objective
Summarize the completed export service/audit extraction work and map residual main_web.py god-module responsibilities before Phase 50.

## Phase 49 PRs (#361–#369)

| PR | Phase | Description | Status |
|----|-------|-------------|--------|
| #361 | 49A | God module mapping and safe extraction plan | ✅ Merged |
| #362 | 49B | Extract export service from main_web.py (3 routes) | ✅ Merged |
| #363 | 49C | Inspect remaining leaf export routes | ✅ Merged |
| #364 | 49D-1 | Characterize POST /download before extraction | ✅ Merged |
| #365 | 49D-2 | Extract POST /download Excel construction | ✅ Merged |
| #366 | 49D-3A | Characterize export audit recording (4 routes) | ✅ Merged |
| #367 | 49D-3B | Extract runtime/institutional audit service | ✅ Merged |
| #368 | 49D-3C | Wire GET /download audit service | ✅ Merged |
| #369 | 49D-3D | Wire POST /download audit service — **FINAL** | ✅ Merged |

## Final Export Route Map

All 4 export routes now delegate to `app/services/export_service.py`:

| Route | Method | Service Function | Bytes Construction |
|-------|--------|-----------------|--------------------|
| `/download` | GET | `record_download_export()` | `build_values_only_export_for_project()` |
| `/download` | POST | `record_download_export()` | `build_excel_export_for_post_request()` |
| `/exports/runtime-summary.csv` | GET | `record_runtime_summary_export()` | `build_runtime_summary_csv_export()` |
| `/exports/institutional-workbook.xlsx` | GET | `record_institutional_workbook_export()` | `build_institutional_workbook_export()` |

## Final Service Map

### app/services/export_service.py
Owns: **export bytes/workbook construction** for all 4 routes.

Functions:
- `build_values_only_export_for_project()` — GET /download
- `build_excel_export_for_post_request()` — POST /download
- `build_runtime_summary_csv_export()` — runtime-summary.csv
- `build_institutional_workbook_export()` — institutional-workbook.xlsx

### app/services/export_audit_service.py
Owns: **export audit recording** (record_export side-effects) for all 4 routes.

Functions:
- `record_runtime_summary_export()` — runtime-summary.csv route
- `record_institutional_workbook_export()` — institutional-workbook.xlsx route
- `record_download_export()` — GET + POST /download routes

## Before/After Responsibility Split

### Before (main_web.py as god module)
- All export bytes construction inline in routes
- All record_export calls inline in routes
- 31,000+ line monolithic route file

### After (service layers extracted)
| Concern | Owner |
|---------|-------|
| Export bytes/workbook construction | `app/services/export_service.py` |
| Export audit recording (record_export) | `app/services/export_audit_service.py` |
| Route orchestration (auth, form parsing, response) | `main_web.py` |
| Provenance dicts (replay_metadata, governance_state) | `main_web.py` builds, services receive |
| `baseline_source` timing | `main_web.py` (route sets post-export, pre-record) |
| Scenario resolution | `main_web.py` |
| StreamingResponse | `main_web.py` |

## Behavior Preservation

- ✅ All 4 export routes respond identically
- ✅ Provenance metadata (replay_metadata) built in routes, passed unchanged to services
- ✅ `baseline_source` timing preserved (set after export bytes, before audit record)
- ✅ Exception behavior preserved (services do not swallow exceptions)
- ✅ Auth checks unchanged
- ✅ artifact_path strings preserved exactly

## Provenance Preservation

- `replay_metadata` built by routes via `_replay_metadata_for_project()`
- `governance_state` built by routes via `_governance_snapshot()`
- Both passed to services unchanged — services do not modify them
- Services add audit-specific fields (export_id, export_timestamp) after receiving

## Test Coverage

| Phase | Tests | Status |
|-------|-------|--------|
| 49D-1 | 40 | ✅ Passed |
| 49D-2 | 42 | ✅ Passed |
| 49D-3A | 35 | ✅ Passed |
| 49D-3B | 28 | ✅ Passed |
| 49D-3C | 20 | ✅ Passed |
| 49D-3D | 26 | ✅ Passed |
| **Total** | **191** | ✅ All pass |

## Known Limitations

- Export routes still use inline form parsing and schema construction — not yet extracted
- Provenance helpers (`_replay_metadata_for_project`, `_governance_snapshot`) remain in main_web.py
- `record_workspace_runtime` not yet extracted (Phase 50 candidate)
- `scenario_id` for exports still resolved in routes (passed to service)

## Residual main_web.py Responsibilities

After Phase 49, main_web.py is the **orchestration layer**. Key residual responsibilities:

1. **Route definitions** (33 routes total)
2. **Auth/session** — `get_current_user`, `decode_session_token`, login/logout
3. **Scenario state** — resolution, snapshots, active scenario binding
4. **Project selection/creation** — `_resolve_project_record`, `_project_workspace_from_snapshot`
5. **Form parsing** — `_collect_form_snapshot`, `_build_schema_from_form`
6. **Model run orchestration** — `run_project`, `run_demo_project`
7. **Provenance building** — `_replay_metadata_for_project`, `_governance_snapshot`
8. **KPI formatting** — `_format_kpis`
9. **Template rendering** — Jinja2 templates
10. **Compare logic** — comparison metrics computation
11. **Persistence calls** — direct calls to repository layer functions
12. **Operational endpoints** — health, readyz, public-health

## Recommended Phase 50 Direction

1. **Scenario state characterization** — map active_scenario_record resolution and workspace binding
2. **Scenario state service extraction** — extract scenario snapshot management
3. **Run route characterization** — map `/run` route runtime orchestration
4. **Run orchestration service extraction** — extract `record_workspace_runtime` and related calls
5. **Compare route extraction** — if applicable
6. **Context/template builder extraction** — `_build_*_ui_context` helpers
7. **persistence/repository.py mapping** — later phase mapping of direct DB calls

## Guardrails Confirmed (All Phases)

- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No model output changes
- ✅ No fixture CSV changes
- ✅ No schema migrations
- ✅ No JS financial calculations
- ✅ G20 BLOCKED | R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted | flat/min DSCR not promoted
- ✅ Backend remains source of truth