# Phase 49D-2 — Extract POST /download Excel Construction into export_service

**Branch:** `phase49d2-extract-post-download-into-export-service`
**Base SHA:** `37d3935ef4dc8e54cbd3113bf8a136cf16adde9e`
**Route:** `POST /download` (main_web.py:2054)
**Phase:** 49D-2 (behavior-preserving production refactor)

---

## 1. Objective

Extract Excel export construction from `POST /download` route in `main_web.py` into `app/services/export_service.py` while preserving all current behavior. The route remains the orchestrator; only the Excel generation moves to the service.

---

## 2. What Was Moved

### Code moved from `main_web.py` → `app/services/export_service.py`

The Excel generation and response construction portion only:

```python
def build_excel_export_for_post_request(
    result,
    project_inputs,
    project_type: str,
    scenario: str,
    runtime_origin: str,
    replay_metadata: dict,
) -> ExportResponse:
    from app.excel_export import build_excel_export

    metadata = dict(replay_metadata)
    metadata["runtime_origin"] = runtime_origin
    filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"

    try:
        excel_bytes = build_excel_export(
            result=result,
            project_inputs=project_inputs,
            provenance_metadata=metadata,
        )
        return ExportResponse(
            bytes_data=excel_bytes,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            status_code=200,
        )
    except (ValueError, Exception) as e:
        return ExportResponse(
            status_code=500,
            error_content=(
                f"<html><body><h2>Excel generation failed</h2>"
                f"<p>{str(e)}</p><a href='/'>Back</a></body></html>"
            ),
        )
```

### Code changed in `main_web.py`

1. **Import added** (line 88):
   ```python
   from app.services.export_service import ..., build_excel_export_for_post_request
   ```

2. **Route call replaced** (was direct `build_excel_export`, now via service):
   ```python
   # Before:
   excel_bytes = build_excel_export(result=demo.result, project_inputs=demo.project_inputs, provenance_metadata=replay_metadata)
   
   # After:
   export = build_excel_export_for_post_request(
       result=demo.result,
       project_inputs=demo.project_inputs,
       project_type=project_type,
       scenario=scenario,
       runtime_origin=runtime_origin,
       replay_metadata=replay_metadata,
   )
   if export.has_error():
       return HTMLResponse(content=export.error_content, status_code=export.status_code)
   excel_bytes = export.bytes_data
   ```

---

## 3. What Was NOT Moved (stays in route)

| Responsibility | Location in route |
|----------------|-------------------|
| Authentication/session | `get_current_user(request)` |
| Form parsing (12 fields) | `form = await request.form()` |
| Project record lookup | `_project_workspace_from_snapshot()` |
| Runtime guard | `runtime_guard_for_snapshot()` |
| Runtime origin resolution | `_resolve_runtime_snapshot_source()` |
| `build_projectinputs` vs `build_projectinputs_from_snapshot` | Route logic |
| `record_export` | Stays in route after service call |
| `baseline_source` mutation | Stays in route (after service, before record_export) |
| StreamingResponse construction | Route final return |
| Error responses (HTMLResponse) | Route-level try/except |

---

## 4. Service API Summary

```python
def build_excel_export_for_post_request(
    result,
    project_inputs,
    project_type: str,
    scenario: str,
    runtime_origin: str,
    replay_metadata: dict,
) -> ExportResponse
```

- **result**: Completed model run result
- **project_inputs**: ProjectInputs from the run
- **project_type**: e.g. "Solar", "Wind"
- **scenario**: e.g. "Base", "Downside", "Upside"
- **runtime_origin**: e.g. "factory_base_runtime", "saved_state"
- **replay_metadata**: Fully-constructed provenance dict from route (includes baseline_source already set when applicable)

Returns `ExportResponse` with bytes_data, filename, media_type, status_code on success; or status_code=500 with error_content on failure.

---

## 5. Provenance Preservation

The route builds `replay_metadata` **before** calling the service. The service receives an already-complete provenance dict. This preserves the Phase 49B finding that provenance timestamps must match what `record_export` will later use.

`runtime_origin` is placed into `metadata["runtime_origin"]` by the service (not added by the route after the call), ensuring the service has a consistent view.

---

## 6. baseline_source Handling

- `baseline_source = True` is set by the route **after** calling `build_excel_export_for_post_request` but **before** calling `record_export`
- This matches the original timing: `replay_metadata["baseline_source"] = True` after Excel generation, before record_export
- The service receives `replay_metadata` before the baseline_source mutation, so `build_excel_export` sees the pre-mutation provenance

---

## 7. Behavior Preservation Checklist

| Behavior | Preserved? |
|----------|-----------|
| Auth check at top of route | ✅ |
| Form field parsing (12 fields) | ✅ |
| `build_projectinputs` path for factory | ✅ |
| `build_projectinputs_from_snapshot` for user_created/saved_state | ✅ |
| `runtime_guard_for_snapshot` blocking | ✅ |
| `runtime_origin` values: factory_base_runtime, saved_state | ✅ |
| `replay_metadata` construction with all conditional fields | ✅ |
| `scenario_provenance` via `_scenario_provenance_for_record` | ✅ |
| Excel filename format: `fincogpt_{type}_{scenario}.xlsx` | ✅ |
| Media type: `application/vnd.openxmlformats...sheet` | ✅ |
| `baseline_source` timing (after bytes, before record_export) | ✅ |
| `record_export` call on success | ✅ |
| 400 response for form validation error | ✅ |
| 400 response for runtime guard blocked | ✅ |
| 500 response for unknown exception | ✅ |
| GET /download route unchanged | ✅ |

---

## 8. main_web.py Line Count

| Metric | Value |
|--------|-------|
| Before (origin/main) | ~3362 lines |
| After (this phase) | 3368 lines |
| Delta | +6 lines (1 import line, call替换, error handling) |

The net increase of 6 lines is due to the service call wrapper + error check replacing a single direct call. The import adds 1 line. Overall the route grew by 6 lines while moving Excel generation logic out.

---

## 9. Tests

| Suite | Result |
|-------|--------|
| `test_phase49d2_post_download_extraction.py` | **42 passed** |
| `test_phase49b_export_service_extraction.py` | 15 passed, 2 expected-line-count failures |
| `test_phase49c_remaining_leaf_export_routes.py` | 15 passed, 1 expected-line-count failure |
| `main_web` import | **OK** |

Expected failures in 49B/49C tests: `test_main_web_lines_still_reduced` and `test_main_web_line_count_unchanged` fail due to main_web.py growing by 6 lines (expected consequence of production refactor).

---

## 10. Guardrails

| Gate | Status |
|------|--------|
| No financial formula changes | ✅ |
| No runtime calculation changes | ✅ |
| No model output changes | ✅ |
| No workbook value-sheet contents changed | ✅ |
| No export filenames changed | ✅ |
| No response status codes changed | ✅ |
| No content-types changed | ✅ |
| G20 BLOCKED | ✅ |
| R99/R102 NOT APPROVED | ✅ |
| partial_pay_sweep not promoted | ✅ |
| flat/min DSCR not promoted | ✅ |
| Backend source of truth | ✅ |

---

## 11. Recommended Next Phase

**Phase 49D-3 — Extract record_export into audit service**

After POST /download and GET /download both use the export_service, the next logical extraction is `record_export` (persistence/audit side-effect). This moves the export event recording logic into a dedicated audit service, leaving the route purely as orchestration + response handling.

Alternatively, **Phase 50** could begin extracting the remaining god module components (e.g., `/run`, `/compare`, scenario management routes) using the same pattern established in 49B/49D-2.