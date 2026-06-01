# Phase 49D-3C — GET /download Audit Service Wiring Matrix

**Branch:** `phase49d3c-wire-get-download-export-audit-service`
**Base SHA:** `bed4b7e554c473225d6c306ad479f07d3e6d3152`

---

## Wiring Matrix

| Route | Extraction phase | Service function | Wired? |
|-------|-----------------|-------------------|--------|
| `GET /exports/runtime-summary.csv` | 49D-3B | `record_runtime_summary_export` | ✅ YES |
| `GET /exports/institutional-workbook.xlsx` | 49D-3B | `record_institutional_workbook_export` | ✅ YES |
| `GET /download` | 49D-3C | `record_download_export` | ✅ YES (this phase) |
| `POST /download` | 49D-3D | `record_download_export` | ❌ NO (next phase) |

---

## GET /download — Before vs After

### Before (direct record_export)

```python
record_export(
    user_id=user.user_id,
    project_code=project_code,
    export_type="excel_model_export",
    artifact_name=filename,
    artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
    project_id=project_record.project_id if project_record else None,
    governance_state=_governance_snapshot(project_code),
    replay_metadata=replay_metadata,
)
```

### After (via service)

```python
record_download_export(
    user_id=user.user_id,
    project_code=project_code,
    export_type="excel_model_export",
    artifact_name=filename,
    artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
    project_id=project_record.project_id if project_record else None,
    governance_state=_governance_snapshot(project_code),
    replay_metadata=replay_metadata,
    scenario_id=None,
)
```

---

## Field Mapping — GET /download

| Field | Route → Service | Service → record_export | Delta |
|-------|-----------------|------------------------|-------|
| `user_id` | ✅ user.user_id | ✅ user_id | Same |
| `project_code` | ✅ project_code | ✅ project_code | Same |
| `export_type` | ✅ "excel_model_export" | ✅ "excel_model_export" | Same |
| `artifact_name` | ✅ filename | ✅ artifact_name | Same |
| `artifact_path` | ✅ f"/download?project_type=..." | ✅ artifact_path | Same |
| `project_id` | ✅ project_record.project_id or None | ✅ project_id | Same |
| `governance_state` | ✅ _governance_snapshot(...) | ✅ governance_state | Same |
| `replay_metadata` | ✅ pre-built dict | ✅ replay_metadata | Same |
| `scenario_id` | ❌ not in original | ✅ None added | Service default |

---

## POST /download — Unchanged (for 49D-3D)

```python
# Still direct record_export in main_web.py
record_export(
    user_id=user.user_id,
    project_code=project_code,
    export_type="excel_model_export",
    artifact_name=filename,
    artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
    project_id=project_record.project_id if project_record else None,
    scenario_id=active_scenario_record.scenario_id if active_scenario_record else None,
    governance_state=_governance_snapshot(project_code),
    replay_metadata=replay_metadata,
)
```

The 49D-3D phase will convert this to:
```python
record_download_export(
    ...,
    scenario_id=active_scenario_record.scenario_id if active_scenario_record else None,
)
```

---

## Production Code Changes Summary

| File | Lines | Change |
|------|-------|--------|
| `main_web.py` | +1 import, +1 line (scenario_id=None) | Wiring only |

No new modules. No new service functions. No test files (test file is new documentation/validation).

---

## Tests

| Test file | Result |
|----------|--------|
| `tests/test_phase49d3c_get_download_audit_service_wiring.py` | 20 passed ✅ |
| `tests/test_phase49d3b_export_audit_service_extraction.py` | 28 passed ✅ (regression) |
| `tests/test_phase49d3a_export_audit_recording_characterization.py` | behavioral regression ✅ |