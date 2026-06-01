# Phase 49D-3B — Export Audit Service Extraction Matrix

**Branch:** `phase49d3b-extract-runtime-institutional-export-audit-service`
**Base SHA:** `aa92ef6a4fe181da6900cbaae9a2f31b720423c1`

---

## Extraction Matrix

| Route | record_export moved? | New service function | audit_service wired? | GET/POST /download |
|-------|---------------------|---------------------|---------------------|-------------------|
| `GET /exports/runtime-summary.csv` | ✅ YES | `record_runtime_summary_export` | ✅ YES | unchanged |
| `GET /exports/institutional-workbook.xlsx` | ✅ YES | `record_institutional_workbook_export` | ✅ YES | unchanged |
| `GET /download` | ❌ NO | `record_download_export` (ready) | ❌ NO | unchanged |
| `POST /download` | ❌ NO | `record_download_export` (ready) | ❌ NO | unchanged |

---

## Service Function Signature Comparison

### Original record_export call (runtime-summary.csv)

```python
record_export(
    user_id=user.user_id,
    project_code=safe_project,
    export_type="runtime_summary_csv",
    artifact_name=export.filename,
    artifact_path=f"/exports/runtime-summary.csv?project={safe_project}",
    project_id=project_record.project_id if project_record else None,
    governance_state=_governance_snapshot(safe_project),
    replay_metadata=_replay_metadata_for_project(
        safe_project,
        export_type="runtime_summary_csv",
        export_timestamp=export.metadata["export_generated_at"],
        runtime_timestamp=export.metadata["runtime_generated_at"],
        project_id=project_record.project_id if project_record else None,
        runtime_origin=export.metadata["runtime_origin"],
        artifact_name=export.filename,
        baseline_source=(project_record.project_origin == "saved_baseline") if project_record else None,
    ),
)
```

### New record_runtime_summary_export call (runtime-summary.csv)

```python
record_runtime_summary_export(
    user_id=user.user_id,
    project_code=safe_project,
    artifact_name=export.filename,
    project_id=project_record.project_id if project_record else None,
    governance_state=_governance_snapshot(safe_project),
    replay_metadata=_replay_metadata_for_project(
        safe_project,
        export_type="runtime_summary_csv",
        export_timestamp=export.metadata["export_generated_at"],
        runtime_timestamp=export.metadata["runtime_generated_at"],
        project_id=project_record.project_id if project_record else None,
        runtime_origin=export.metadata["runtime_origin"],
        artifact_name=export.filename,
        baseline_source=(project_record.project_origin == "saved_baseline") if project_record else None,
    ),
)
```

**Delta:** `artifact_path` constructed inside service (not duplicated in route); `export_type` hardcoded in service.

---

## Field Mapping

| Field | Route passes to service | Service passes to record_export | Delta |
|-------|------------------------|--------------------------------|-------|
| `user_id` | ✅ user.user_id | ✅ user_id | Same |
| `project_code` | ✅ safe_project | ✅ project_code | Same (renamed) |
| `artifact_name` | ✅ export.filename | ✅ artifact_name | Same (renamed) |
| `project_id` | ✅ project_record.project_id or None | ✅ project_id | Same (renamed) |
| `governance_state` | ✅ _governance_snapshot(...) | ✅ governance_state | Same |
| `replay_metadata` | ✅ _replay_metadata_for_project(...) | ✅ replay_metadata | Same |
| `export_type` | ❌ (hardcoded in service) | ✅ "runtime_summary_csv" | In service |
| `artifact_path` | ❌ (constructed in service) | ✅ f"/exports/runtime-summary.csv?project={project_code}" | In service |

---

## Production Code Changes Summary

| File | Lines changed | Type |
|------|-------------|------|
| `main_web.py` | +1 import line, +2 service calls (route lines unchanged count) | Extraction |
| `app/services/export_audit_service.py` | NEW (~220 lines) | New module |
| `app/services/__init__.py` | +5 lines | Export update |
| `tests/test_phase49d3b_export_audit_service_extraction.py` | NEW (~600 lines) | Tests |
| `docs/phase49d3b_export_audit_service_extraction.md` | NEW | Docs |
| `docs/phase49d3b_export_audit_service_matrix.md` | NEW | Matrix |

---

## Tests

| Test | Status |
|------|--------|
| `test_export_audit_service_imports_cleanly` | ✅ |
| `test_main_web_imports_cleanly` | ✅ |
| `test_service_exposes_record_runtime_summary_export` | ✅ |
| `test_service_exposes_record_institutional_workbook_export` | ✅ |
| `test_record_runtime_summary_export_calls_record_export_with_type` | ✅ |
| `test_record_runtime_summary_export_preserves_artifact_path` | ✅ |
| `test_record_runtime_summary_export_forwards_all_fields` | ✅ |
| `test_record_institutional_workbook_export_calls_record_export_with_type` | ✅ |
| `test_record_institutional_workbook_export_preserves_artifact_path` | ✅ |
| `test_record_institutional_workbook_export_forwards_all_fields` | ✅ |
| `test_runtime_summary_route_uses_audit_service` | ✅ |
| `test_institutional_workbook_route_uses_audit_service` | ✅ |
| `test_get_download_record_export_remains_in_main_web` | ✅ |
| `test_post_download_record_export_remains_in_main_web` | ✅ |
| `test_replay_metadata_helper_remains_in_main_web` | ✅ |
| `test_governance_snapshot_remains_in_main_web` | ✅ |
| `test_phase49d3a_assumptions_hold` | ✅ |
| `test_no_unexpected_production_code_changes` | ✅ |
| `test_no_fixture_csv_changes` | ✅ |
| `test_no_schema_migrations` | ✅ |
| `test_guardrails_stated` | ✅ |
| `test_audit_service_is_new_file` | ✅ |
| `test_init_exports_audit_service` | ✅ |
| `test_service_calls_record_export_with_correct_export_types` | ✅ |
| `test_service_does_not_swallow_exceptions` | ✅ |
| `test_exports_require_auth` | ✅ |
| `test_no_js_financial_calculations_added` | ✅ |
| `test_phase49d3a_regression` | ✅ |

**28 passed** ✅