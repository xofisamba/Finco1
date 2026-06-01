# Phase 49B — Extract Export Service from main_web.py

**Branch:** `phase49b-extract-export-service-from-main-web`
**Base SHA:** `290e362b9b383df26a6fc37d9eb7b98805e339d9`
**Head SHA:** `569565971451823fcccdb50168044aaad71a7608`
**Phase:** 49B

---

## 1. Objective

Extract export/download orchestration from `main_web.py` into a dedicated service module (`app/services/export_service.py`) while preserving existing route behavior exactly.

This is the first production-code refactor following Phase 49A mapping. **No financial formulas, runtime calculations, or model outputs changed.**

---

## 2. Routes/Functions Inspected

| Route | Function | Status |
|-------|----------|--------|
| `GET /download` | `download_get` | ✅ Wrapped — delegates to `build_values_only_export_for_project` |
| `POST /download` | `download_post` | Not refactored (complex POST form handling) |
| `GET /exports/runtime-summary.csv` | `runtime_summary_export` | ✅ Wrapped — delegates to `build_runtime_summary_csv_export` |
| `GET /exports/institutional-workbook.xlsx` | `institutional_workbook_export` | ✅ Wrapped — delegates to `build_institutional_workbook_export` |

---

## 3. Functions Moved or Wrapped

### `build_values_only_export_for_project(result, project_inputs, project_type, scenario, *, replay_metadata=None) → ExportResponse`
- **Location:** `app/services/export_service.py`
- **Original caller:** `download_get` (main_web.py)
- **Behavior:** Calls `build_excel_export()` with the `replay_metadata` dict that the caller pre-computed — identical output bytes, provenance preserved
- **Note:** `run_demo_project()` stays in the route to allow provenance metadata to be computed before the service call

### `build_runtime_summary_csv_export(runtime_project_code, safe_project=None) → ExportResponse`
- **Location:** `app/services/export_service.py`
- **Original caller:** `runtime_summary_export` (main_web.py)
- **Behavior:** Calls `build_runtime_summary_rows()` internally; returns provenance timestamps via `ExportResponse.metadata` from `runtime_rows[0]`

### `build_institutional_workbook_export(runtime_project_code, safe_project=None) → ExportResponse`
- **Location:** `app/services/export_service.py`
- **Original caller:** `institutional_workbook_export` (main_web.py)
- **Behavior:** Calls `build_runtime_summary_rows()` internally; returns provenance timestamps via `ExportResponse.metadata` from `runtime_rows[0]`

---

## 4. Service API Summary

```python
@dataclass ExportResponse:
    bytes_data: bytes | None
    filename: str | None
    media_type: str | None
    status_code: int
    error_content: str | None
    metadata: dict[str, Any]  # populated from runtime_rows[0] for CSV/workbook exports

def build_values_only_export_for_project(
    result, project_inputs, project_type, scenario, *, replay_metadata=None
) -> ExportResponse
def build_runtime_summary_csv_export(runtime_project_code, *, safe_project=None) -> ExportResponse
def build_institutional_workbook_export(runtime_project_code, *, safe_project=None) -> ExportResponse

def serve_runtime_summary_csv(runtime_project_code, safe_project=None) -> StreamingResponse | HTMLResponse
def serve_institutional_workbook(runtime_project_code, safe_project=None) -> StreamingResponse | HTMLResponse
```

Note: `serve_values_only_export` was removed — it was not used by any route or test.

---

## 5. Provenance Preservation (Key Design Decision)

The service layer is designed so the route handler controls provenance:

1. **GET /download**: Route calls `run_demo_project()` first → computes `replay_metadata` → passes `(demo.result, demo.project_inputs, replay_metadata)` to service → Excel file and `record_export` share the same provenance dict.

2. **Runtime CSV + Institutional Workbook**: Service calls `build_runtime_summary_rows()` internally and populates `ExportResponse.metadata` with `runtime_rows[0]` fields. Route uses `export.metadata["export_generated_at"]`, `export.metadata["runtime_generated_at"]`, and `export.metadata["runtime_origin"]` in its `record_export` call — exactly what the runtime itself recorded.

---

## 6. Behavior Preservation Checklist

| Behavior | Preserved? |
|----------|------------|
| Route URLs | ✅ Unchanged |
| Response status codes | ✅ Identical |
| Content types | ✅ Identical |
| Filenames | ✅ Identical |
| Workbook generator calls | ✅ Identical |
| CSV layout | ✅ Identical |
| Export_Metadata sheet (first) | ✅ Preserved |
| Workbook_Index sheet (second) | ✅ Preserved |
| Provenance columns in CSV | ✅ Preserved |
| Error HTML pages | ✅ Identical |
| No financial formulas changed | ✅ Confirmed |
| No runtime calculations changed | ✅ Confirmed |
| No model outputs changed | ✅ Confirmed |

---

## 7. Tests Added

- `tests/test_phase49b_export_service_extraction.py` — **17 tests**
- Key assertions: import clean, ExportResponse.metadata populated, sheet order in workbooks, CSV provenance columns, media types, no unused params

---

## 8. main_web Shrink Summary

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| main_web.py lines | 3367 | 3362 | −5 |
| Export routes wrapped | — | 3 of 4 | — |

Note: Only 3 of 4 export routes wrapped — `download_post` has complex POST form handling. The service module is structured for straightforward follow-up extraction.

---

## 9. Guardrails Confirmed

| Gate | Status |
|------|--------|
| G20 | BLOCKED |
| R99 | NOT APPROVED |
| R102 | NOT APPROVED |
| partial_pay_sweep | Not promoted |
| flat/min DSCR sculpting | Not promoted |
| Backend source of truth | ✅ Confirmed |
| No JS financial calculations | ✅ Confirmed |
| No fixture CSVs changed | ✅ Confirmed |
| No schema migrations | ✅ Confirmed |

---

## 10. Production Files Changed (Narrow Scope)

| File | Change |
|------|--------|
| `main_web.py` | Added import; wrapped 3 export routes to delegate to service |
| `app/services/__init__.py` | New — service package init |
| `app/services/export_service.py` | New — ExportResponse + 3 build functions + 2 serve functions |

---

## 11. Recommended Next Phase

**Phase 49C — Extract Remaining Export Routes from main_web.py**
- Wrap `download_post` into export_service (complex POST form handling)
- Add remaining export routes (gap register, source map) as second extraction batch
- Add isolated export service tests, dependency injection tests, interface contract tests

---

## 12. Changed Files

| File | Description |
|------|-------------|
| `app/services/export_service.py` | New — export service module |
| `app/services/__init__.py` | New — service package init |
| `main_web.py` | Wrapped 3 export routes to delegate to service |
| `tests/test_phase49b_export_service_extraction.py` | 17 tests |
| `docs/phase49b_extract_export_service_from_main_web.md` | This document |
| `docs/phase49b_export_service_extraction_matrix.md` | Extraction matrix |
| `reports/phase49b_export_service_extraction_summary.json` | JSON summary |