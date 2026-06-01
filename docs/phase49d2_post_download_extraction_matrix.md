# Phase 49D-2 — POST /download Extraction Matrix

**Branch:** `phase49d2-extract-post-download-into-export-service`
**Base SHA:** `37d3935ef4dc8e54cbd3113bf8a136cf16adde9e`

---

## Extraction Matrix

| Component | Before (main_web.py) | After (export_service.py) | Route Change |
|-----------|---------------------|---------------------------|--------------|
| **Excel generation** | `build_excel_export(result, project_inputs, provenance_metadata)` | `build_excel_export_for_post_request(result, project_inputs, project_type, scenario, runtime_origin, replay_metadata)` | ✅ Moved to service |
| **Filename construction** | Inline in route | `f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"` in service | ✅ Moved to service |
| **ExportResponse construction** | Manual StreamingResponse | `ExportResponse(bytes_data, filename, media_type, status_code)` | ✅ Moved to service |
| **Error response** | Inline try/except in route | `ExportResponse(status_code=500, error_content=...)` | ✅ Moved to service |

| Component | Before (main_web.py) | After (main_web.py) | Change |
|-----------|---------------------|---------------------|--------|
| **Import** | `build_values_only_export_for_project`, etc. | + `build_excel_export_for_post_request` | ✅ Added |
| **Service call** | N/A | `build_excel_export_for_post_request(...)` | ✅ New |
| **Error handling** | N/A | `if export.has_error(): return HTMLResponse(...)` | ✅ Added |
| **excel_bytes extraction** | N/A | `excel_bytes = export.bytes_data` | ✅ Added |

---

## What Was NOT Changed (stays in main_web.py)

| Component | Location | Reason not moved |
|-----------|----------|-----------------|
| Authentication | `get_current_user()` | Auth/session is route-level |
| Form parsing | `form = await request.form()` | Form handling stays in route |
| Project record lookup | `_project_workspace_from_snapshot()` | Persistence concern |
| Runtime guard | `runtime_guard_for_snapshot()` | Authorization concern |
| Runtime origin resolution | `_resolve_runtime_snapshot_source()` | Snapshot management |
| `build_projectinputs` vs `build_projectinputs_from_snapshot` | Route conditional | Route-level input selection |
| `run_demo_project` | Route calls | Runtime orchestration |
| `replay_metadata` construction | `_replay_metadata_for_project()` | Route-level provenance construction |
| `baseline_source` mutation | Post-service route code | Route-level provenance mutation |
| `record_export` | Post-service route call | Persistence/audit concern |
| StreamingResponse construction | Route return | Route-level response construction |

---

## Route vs Service Responsibility Split

```
Route (main_web.py):
  ✅ auth check
  ✅ form parsing (12 fields)
  ✅ project record lookup
  ✅ runtime guard + guard blocked response
  ✅ runtime origin resolution
  ✅ build_projectinputs vs build_projectinputs_from_snapshot selection
  ✅ run_demo_project call
  ✅ replay_metadata construction (with all conditional fields)
  ✅ baseline_source mutation (post-service, pre-record_export)
  ✅ record_export call
  ✅ StreamingResponse return (with Content-Disposition, Content-Length)
  ✅ HTMLResponse error returns (400 validation, 400 guard, 500 generic)

Service (export_service.py):
  ✅ filename construction (fincogpt_{type}_{scenario}.xlsx)
  ✅ build_excel_export call with provenance_metadata
  ✅ ExportResponse with bytes_data, filename, media_type, status_code
  ✅ Error ExportResponse (500 with HTML error_content)
```

---

## Phase 49 Series Extraction Status

| Phase | Extracted | Status |
|-------|-----------|--------|
| 49B: GET /exports/runtime-summary.csv | `build_runtime_summary_csv_export` | ✅ Merged |
| 49B: GET /exports/institutional-workbook.xlsx | `build_institutional_workbook_export` | ✅ Merged |
| 49B: GET /download | `build_values_only_export_for_project` | ✅ Merged |
| 49D-2: POST /download | `build_excel_export_for_post_request` | ✅ Done (PR pending) |

**All export routes are now in export_service.py.**
**main_web.py remains the orchestration layer.**

---

## Guardrails Verification

| Guardrail | Before | After | Verified |
|-----------|--------|-------|---------|
| Financial formulas | Unchanged | Unchanged | ✅ |
| Runtime calculations | Unchanged | Unchanged | ✅ |
| Model outputs | Unchanged | Unchanged | ✅ |
| Workbook contents | Unchanged | Unchanged | ✅ |
| Export filenames | `fincogpt_{type}_{scenario}.xlsx` | `fincogpt_{type}_{scenario}.xlsx` | ✅ |
| Status codes | 200/400/500 | 200/400/500 | ✅ |
| Content-types | `application/vnd...sheet` | `application/vnd...sheet` | ✅ |
| Provenance timing | `replay_metadata` built before Excel generation | Same (route builds before calling service) | ✅ |
| baseline_source timing | After Excel bytes, before record_export | After service call, before record_export | ✅ |
| record_export location | After Excel generation | After service call | ✅ |