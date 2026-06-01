# Phase 49D-3D — POST /download Audit Service Wiring

## Objective
Wire `record_download_export()` into `POST /download` route and remove the final direct `record_export` import/call from `main_web.py`.

## Base SHA
`1321fadc9997793401de2838950b84934336d4f2` (after PR #368 merge)

## Completion SHA
`1321fadc` (same — this is the branch head before PR)

## Affected Route
`POST /download`

## What Moved
- The `record_export(...)` call in `POST /download` route → now calls `record_download_export(...)` from `app.services.export_audit_service`
- The `record_export` import line removed from `main_web.py`

## What Did NOT Move
All other production code remains in `main_web.py`:
- `_replay_metadata_for_project` construction (including `baseline_source` timing)
- `_governance_snapshot` construction
- `active_scenario_record` resolution and `scenario_id` extraction
- `build_excel_export_for_post_request` call
- `StreamingResponse` construction
- Error handling (HTMLResponse on error)

## scenario_id Handling
- **POST /download**: passes `active_scenario_record.scenario_id if active_scenario_record else None` to `record_download_export`
- **GET /download**: passes `scenario_id=None` to `record_download_export`
- Service conditionally passes `scenario_id` to `record_export` only when not None (preserving exact original behavior)

## artifact_path Preservation
Both GET and POST use: `f"/download?project_type={project_type}&scenario={scenario}"` — exact match to original.

## replay_metadata Preservation
Routes continue to own `replay_metadata` construction, including:
- `_replay_metadata_for_project()` call
- `active_scenario_id` injection
- `baseline_source = True` set AFTER export call and BEFORE record call (POST /download)
- All provenance fields injected by route

## governance_state Preservation
Routes continue to own `_governance_snapshot(project_code)` call; pre-built dict passed to service.

## baseline_source Timing
Preserved exactly:
```
build_excel_export_for_post_request(...)
↓
replay_metadata["baseline_source"] = True    ← post-export, pre-record
↓
record_download_export(...)
```
Timing: after bytes computed, before audit recorded. POST /download only (GET /download does not set baseline_source).

## Exception Behavior
`record_download_export` propagates exceptions from `record_export` unchanged — does NOT swallow them.

## record_export Import Removal
After this phase, `main_web.py` no longer imports `record_export` from `app.persistence.repository`.

## Zero Direct record_export Calls
After this phase, `main_web.py` has **0** direct `record_export(...)` calls. All 4 routes now delegate to the audit service:
- `GET /exports/runtime-summary.csv` → `record_runtime_summary_export()` (49D-3B)
- `GET /exports/institutional-workbook.xlsx` → `record_institutional_workbook_export()` (49D-3B)
- `GET /download` → `record_download_export()` (49D-3C)
- `POST /download` → `record_download_export()` (49D-3D)

## Tests
- **26 tests** in `test_phase49d3d_post_download_audit_service_wiring.py` — all pass
- Phase 49D-3C GET /download behavioral tests — still pass
- Phase 49D-3B runtime/institutional tests — still pass

## Guardrails
- NO changes to financial formulas
- NO changes to runtime calculations
- NO changes to model outputs
- NO fixture CSV changes
- NO schema migrations
- NO JS financial calculations
- G20 BLOCKED | R99/R102 NOT APPROVED
- partial_pay_sweep not promoted | flat/min DSCR not promoted
- Backend remains source of truth

## Recommended Next Phase
**Phase 50**: Extract remaining god module routes (`/run`, `/compare`, scenario management) to service layer.