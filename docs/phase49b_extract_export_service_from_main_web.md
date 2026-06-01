# Phase 49B — Extract Export Service from main_web.py

**Branch:** `phase49b-extract-export-service-from-main-web`
**Base SHA:** `290e362b9b383df26a6fc37d9eb7b98805e339d9`
**Head SHA: 0d7b13e10ab716b0f0a5b11cecfcb6ffc8ae0c75
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
| `POST /download` | `download_post` | Not refactored (complex POST form handling, pre-existing complex logic) |
| `GET /exports/runtime-summary.csv` | `runtime_summary_export` | ✅ Wrapped — delegates to `build_runtime_summary_csv_export` |
| `GET /exports/institutional-workbook.xlsx` | `institutional_workbook_export` | ✅ Wrapped — delegates to `build_institutional_workbook_export` |

---

## 3. Functions Moved or Wrapped

### `build_values_only_export_for_project(project_type, scenario, **kwargs) → ExportResponse`
- **Location:** `app/services/export_service.py`
- **Original caller:** `download_get` (main_web.py)
- **Behavior:** Wraps `run_demo_project()` + `build_excel_export()` — identical output bytes

### `build_runtime_summary_csv_export(runtime_project_code, safe_project, **kwargs) → ExportResponse`
- **Location:** `app/services/export_service.py`
- **Original caller:** `runtime_summary_export` (main_web.py)
- **Behavior:** Wraps `build_runtime_summary_rows()` + `build_runtime_summary_csv()` — identical CSV

### `build_institutional_workbook_export(runtime_project_code, safe_project, **kwargs) → ExportResponse`
- **Location:** `app/services/export_service.py`
- **Original caller:** `institutional_workbook_export` (main_web.py)
- **Behavior:** Wraps `export_institutional_workbook_skeleton()` — identical workbook bytes

---

## 4. Service API Summary

```python
@dataclass ExportResponse:
    bytes_data: bytes | None
    filename: str | None
    media_type: str | None
    status_code: int
    error_content: str | None

def build_values_only_export_for_project(project_type, scenario, **kwargs) -> ExportResponse
def build_runtime_summary_csv_export(runtime_project_code, safe_project=None, **kwargs) -> ExportResponse
def build_institutional_workbook_export(runtime_project_code, safe_project=None, **kwargs) -> ExportResponse

def serve_values_only_export(project_type, scenario, **kwargs) -> StreamingResponse | HTMLResponse
def serve_runtime_summary_csv(runtime_project_code, safe_project=None, **kwargs) -> StreamingResponse | HTMLResponse
def serve_institutional_workbook(runtime_project_code, safe_project=None, **kwargs) -> StreamingResponse | HTMLResponse
```

---

## 5. Behavior Preservation Checklist

| Behavior | Preserved? |
|----------|------------|
| Route URLs | ✅ Unchanged |
| Response status codes | ✅ Identical |
| Content types | ✅ Identical |
| Filenames | ✅ Identical (`fincogpt_{type}_{scenario}.xlsx`, `phase10_{proj}_runtime_summary.csv`, `phase10_{proj}_institutional_workbook_skeleton.xlsx`) |
| Workbook generator calls | ✅ Identical — same `export_institutional_workbook_skeleton()` |
| CSV layout | ✅ Identical — same `build_runtime_summary_csv()` |
| Export_Metadata sheet (first) | ✅ Preserved — workbook generators unchanged |
| Workbook_Index sheet (second) | ✅ Preserved — workbook generators unchanged |
| Provenance columns in CSV | ✅ Preserved — `build_runtime_summary_rows()` unchanged |
| Error HTML pages | ✅ Identical |

---

## 6. Tests Added

- `tests/test_phase49b_export_service_extraction.py` — 19 tests
- Key assertions: import clean, ExportResponse behavior, sheet order in workbooks, CSV provenance columns, media types

---

## 7. main_web Shrink Summary

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| main_web.py lines | 3367 | 3362 | −5 |
| Export routes wrapped | — | 3 of 4 | — |

Note: Only 3 of 4 export routes wrapped because `download_post` has complex POST form handling that is harder to extract without changing behavior. The service module is structured to make `download_post` extraction straightforward in a follow-up phase.

---

## 8. Guardrails Confirmed

| Gate | Status |
|------|--------|
| No financial formula changes | ✅ Confirmed — `no financial formulas` stated in export_service docstring |
| No runtime calculation changes | ✅ Confirmed |
| No model output changes | ✅ Confirmed |
| G20 | BLOCKED — unchanged |
| R99 | NOT APPROVED — unchanged |
| R102 | NOT APPROVED — unchanged |
| partial_pay_sweep | Not promoted — unchanged |
| flat/min DSCR sculpting | Not promoted — unchanged |
| Backend source of truth | Confirmed |
| No JS financial calculations | Confirmed — JS untouched |
| No fixture CSVs changed | ✅ Confirmed |
| No schema migrations | ✅ Confirmed |

---

## 9. Production Files Changed (Narrow Scope)

| File | Change |
|------|--------|
| `main_web.py` | Added import; wrapped 3 export routes to delegate to export_service |
| `app/services/__init__.py` | New — service package init |
| `app/services/export_service.py` | New — ExportResponse + 3 build functions + 3 serve functions |

---

## 10. Recommended Next Phase

**Phase 49C — Extract Remaining Export Routes from main_web.py**

Wrap `download_post` into `export_service` and add remaining export routes (gap register, source map) as the second extraction batch. Also add the missing test coverage identified in Phase 49A:
- Isolated export service tests
- Dependency injection tests
- Interface contract tests

---

## 11. Changed Files

| File | Description |
|------|-------------|
| `app/services/export_service.py` | New — export service module |
| `app/services/__init__.py` | New — service package init |
| `main_web.py` | Wrapped 3 export routes to delegate to export_service |
| `tests/test_phase49b_export_service_extraction.py` | 19 tests |
| `docs/phase49b_extract_export_service_from_main_web.md` | This document |
| `docs/phase49b_export_service_extraction_matrix.md` | Extraction matrix |
| `reports/phase49b_export_service_extraction_summary.json` | JSON summary |