# Phase 49D-3D — Audit Service Wiring Matrix

## Route: POST /download

| Item | Before (49D-3C) | After (49D-3D) | Preserved? |
|------|----------------|----------------|------------|
| Route decorator | `@app.post("/download")` | `@app.post("/download")` | ✅ |
| Auth check | `get_current_user()` | `get_current_user()` | ✅ |
| Scenario resolution | `active_scenario_record` | `active_scenario_record` | ✅ |
| `scenario_id` extraction | `active_scenario_record.scenario_id if active_scenario_record else None` | Same (passed to service) | ✅ |
| `replay_metadata` construction | `_replay_metadata_for_project(...)` | Same (route builds pre-call) | ✅ |
| `baseline_source` timing | Set post-export, pre-record | Same timing | ✅ |
| Excel generation | `build_excel_export_for_post_request(...)` | Same | ✅ |
| Audit recording | `record_export(...)` direct | `record_download_export(...)` | ⚡ Moved |
| Governance state | `_governance_snapshot(project_code)` | Same (route builds pre-call) | ✅ |
| artifact_path | `f"/download?project_type={project_type}&scenario={scenario}"` | Same | ✅ |
| Export type | `"excel_model_export"` | Same | ✅ |
| StreamingResponse | Same | Same | ✅ |
| Error handling | `HTMLResponse` | Same | ✅ |
| `record_export` import | Present | Removed | ✅ |

## record_export → Audit Service Call Map (Final State)

| Route | Phase | Service Function | record_export in main_web.py |
|-------|-------|-----------------|------------------------------|
| `GET /exports/runtime-summary.csv` | 49D-3B | `record_runtime_summary_export()` | 0 |
| `GET /exports/institutional-workbook.xlsx` | 49D-3B | `record_institutional_workbook_export()` | 0 |
| `GET /download` | 49D-3C | `record_download_export()` | 0 |
| `POST /download` | 49D-3D | `record_download_export()` | 0 |

**Total direct `record_export` calls in main_web.py: 0** ✅

## What Stays in main_web.py (POST /download)
- Route handler + auth
- Project/scenario lookup
- `active_scenario_record` resolution
- `replay_metadata` construction (`_replay_metadata_for_project`)
- `baseline_source` timing (set after export, before record)
- `governance_state` construction (`_governance_snapshot`)
- `build_excel_export_for_post_request` call
- `StreamingResponse` construction
- Error handling

## What Moved to export_audit_service.py
- `record_export()` call with all parameters
- Type-safe wrapper with explicit signature
- `scenario_id=None` conditional (only passed if not None)

## Service Function Signatures
```python
def record_runtime_summary_export(user_id, project_code, artifact_name, project_id, governance_state, replay_metadata) -> None
def record_institutional_workbook_export(user_id, project_code, artifact_name, project_id, governance_state, replay_metadata) -> None
def record_download_export(*, user_id, project_code, export_type, artifact_name, artifact_path, project_id, governance_state, replay_metadata, scenario_id=None) -> None
```

## Guardrails Confirmed
- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No model output changes
- ✅ No fixture CSV changes
- ✅ No schema migrations
- ✅ No JS financial calculations
- ✅ G20 BLOCKED | R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted | flat/min DSCR not promoted
- ✅ Backend remains source of truth