# Phase 49D-3A — Export Audit Recording Matrix

**Branch:** `phase49d3a-characterize-export-audit-recording`
**Base SHA:** `c05d7b036ad2cab6d9c989e0ff78b3679c3e74c9`

---

## Matrix

| Route | export_type | artifact_name | artifact_path | project_code | project_id source | governance_state source | replay_metadata source | baseline_source | runtime_origin | record_export expected | extraction risk | test coverage |
|-------|-------------|---------------|---------------|--------------|-------------------|------------------------|------------------------|-----------------|-----------------|----------------------|----------------|---------------|
| POST /download | excel_model_export | fincogpt_{type}_{scenario}.xlsx | /download?project_type={type}&scenario={scenario} | project_code (from project_record) | project_record.project_id | _governance_snapshot(project_code) | Route-built (line ~2132) | YES — set post-service at line 2163 | factory_base_runtime or saved_state | YES | HIGH — multi-path replay_metadata, scenario_id conditional | Needs path-specific test |
| GET /download | excel_model_export | fincogpt_{type}_{scenario}.xlsx | /download?project_type={type}&scenario={scenario} | project_code | project_record.project_id | _governance_snapshot(project_code) | Route via _replay_metadata_for_project (line 2132) | NO | factory_base_runtime | YES | MEDIUM — user_created template_origin_override | Needs auth+form test |
| GET /exports/runtime-summary.csv | runtime_summary_csv | phase10_{safe_project}_runtime_summary.csv | /exports/runtime-summary.csv?project={safe_project} | safe_project | project_record.project_id if project_record else None | _governance_snapshot(safe_project) | Inline _replay_metadata_for_project call | YES conditional (saved_baseline) | export.metadata["runtime_origin"] | YES | LOW — inline pattern, simple call | Can test with mock |
| GET /exports/institutional-workbook.xlsx | institutional_workbook | phase10_{safe_project}_institutional_workbook_skeleton.xlsx | /exports/institutional-workbook.xlsx?project={safe_project} | safe_project | project_record.project_id if project_record else None | _governance_snapshot(safe_project) | Inline _replay_metadata_for_project call | YES conditional (saved_baseline) | export.metadata["runtime_origin"] | YES | LOW — same pattern as runtime-summary | Can test with mock |

---

## Key Observations

### record_export always called AFTER export construction
In all 4 routes, record_export is called AFTER the export bytes/data have been successfully generated and AFTER the export service has returned. This means:
- The export is recorded even if the client disconnects after receiving bytes
- record_export never blocks or affects export delivery
- record_export side effect is truly fire-and-forget from the route's perspective

### replay_metadata patterns vary by route type

| Pattern | Routes | Description |
|---------|--------|-------------|
| Pre-built + passed | POST /download, GET /download | Route builds replay_metadata first, passes to record_export |
| Inline build | runtime-summary, institutional-workbook | _replay_metadata_for_project called directly in record_export call |

### baseline_source handling

| Route | Timing | Condition |
|-------|--------|-----------|
| POST /download | Post-service (line 2163) | project_record.project_origin == "saved_baseline" |
| GET /download | None | Not handled |
| runtime-summary | Inline with _replay_metadata_for_project | same condition |
| institutional-workbook | Inline with _replay_metadata_for_project | same condition |

### scenario_id only in POST /download
Only POST /download passes scenario_id to record_export. All other routes omit it.

### artifact_path is always the route URL with query params
All 4 routes use the route URL + query params as artifact_path, not a file system path.

---

## Service Boundary Options

### Option A: Route-specific functions (recommended for 49D-3B)
```python
app/services/export_audit_service.py

def audit_download_export(user_id, project_code, export_type, artifact_name, artifact_path, project_id, scenario_id, governance_state, replay_metadata):
    record_export(user_id=user_id, project_code=project_code, export_type=export_type, artifact_name=artifact_name, artifact_path=artifact_path, project_id=project_id, scenario_id=scenario_id, governance_state=governance_state, replay_metadata=replay_metadata)

def audit_runtime_summary_export(user_id, safe_project, export, project_record, export_metadata):
    record_export(...)
```

### Option B: Single generic function with export_type discrimination
Not recommended — too many conditional branches.

---

## Extraction Readiness

| Criterion | Status | Notes |
|-----------|--------|-------|
| All 4 call sites documented | YES | |
| Helper functions signatures known | YES | _replay_metadata_for_project (20+ kwargs), _governance_snapshot |
| baseline_source timing mapped | YES | 3 patterns identified |
| scenario_id handling mapped | YES | Only POST /download uses it |
| replay_metadata patterns mapped | YES | 2 patterns (pre-built vs inline) |
| ready_for_extraction | PARTIAL | 49D-3B should start with runtime-summary + institutional-workbook (simpler) |
| recommended_first_extraction | runtime-summary + institutional-workbook | Inline pattern, no complex conditional logic |
