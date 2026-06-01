# Phase 49B — Export Service Extraction Matrix

**Branch:** `phase49b-extract-export-service-from-main-web`
**Base SHA:** `290e362b9b383df26a6fc37d9eb7b98805e339d9`
**Head SHA:** `569565971451823fcccdb50168044aaad71a7608`

---

## Extraction Matrix

| Export route/function | Previous location | New service function | Response type | Filename preserved? | Content-type preserved? | Workbook metadata preserved? | Tests |
|----------------------|------------------|---------------------|--------------|------------------------------|----------------------|---------------------------|-------|
| `GET /download` — `download_get` | main_web.py:2187 | `build_values_only_export_for_project(result, project_inputs, project_type, scenario, replay_metadata=)` | StreamingResponse | ✅ `fincogpt_{type}_{scenario}.xlsx` | ✅ `application/vnd.openxmlformats...sheet` | N/A (values-only Excel) | ✅ test_values_only_export_passes_replay_metadata |
| `GET /exports/runtime-summary.csv` — `runtime_summary_export` | main_web.py:2241 | `build_runtime_summary_csv_export()` (populates ExportResponse.metadata) | StreamingResponse | ✅ `phase10_{proj}_runtime_summary.csv` | ✅ `text/csv` | N/A | ✅ test_runtime_summary_csv_export_metadata_populated |
| `GET /exports/institutional-workbook.xlsx` — `institutional_workbook_export` | main_web.py:2287 | `build_institutional_workbook_export()` (populates ExportResponse.metadata) | StreamingResponse | ✅ `phase10_{proj}_institutional_workbook_skeleton.xlsx` | ✅ `application/vnd.openxmlformats...sheet` | ✅ Export_Metadata first, Workbook_Index second | ✅ test_institutional_workbook_has_export_metadata_and_index_sheets |
| `POST /download` — `download_post` | main_web.py:2053 | Not extracted (complex POST form handling) | StreamingResponse | ✅ preserved | ✅ preserved | N/A | ⚠️ route tests cover it |

---

## Production Files Changed

| File | Change type | Lines delta |
|------|------------|-----------|
| `main_web.py` | Routes wrapped to delegate to service; provenance preserved | 3367 → 3362 (−5) |
| `app/services/__init__.py` | New service package init | +16 |
| `app/services/export_service.py` | New — ExportResponse + 3 build functions + 2 serve functions | +234 |

---

## Public API (export_service.py)

```python
@dataclass ExportResponse:
    bytes_data: bytes | None
    filename: str | None
    media_type: str | None
    status_code: int
    error_content: str | None
    metadata: dict[str, Any]

def build_values_only_export_for_project(
    result, project_inputs, project_type, scenario, *, replay_metadata=None
) -> ExportResponse

def build_runtime_summary_csv_export(
    runtime_project_code, *, safe_project=None
) -> ExportResponse  # metadata from runtime_rows[0]

def build_institutional_workbook_export(
    runtime_project_code, *, safe_project=None
) -> ExportResponse  # metadata from runtime_rows[0]

def serve_runtime_summary_csv(runtime_project_code, safe_project=None) -> StreamingResponse | HTMLResponse
def serve_institutional_workbook(runtime_project_code, safe_project=None) -> StreamingResponse | HTMLResponse
```

---

## Behavior Preservation Verification

| Behavior | Method | Result |
|----------|--------|--------|
| Same workbook bytes | `export_institutional_workbook_skeleton()` called unchanged | ✅ |
| Same CSV layout | `build_runtime_summary_csv()` called unchanged | ✅ |
| Same filenames | Hardcoded strings unchanged | ✅ |
| Same content-types | Media type strings unchanged | ✅ |
| Export_Metadata first sheet | Workbook generator unchanged | ✅ |
| Workbook_Index second sheet | Workbook generator unchanged | ✅ |
| CSV provenance columns | `build_runtime_summary_rows()` unchanged | ✅ |
| Error HTML pages | Error content strings unchanged | ✅ |

---

## Guardrails Status

| Guardrail | Status |
|-----------|--------|
| No formula changes | ✅ Confirmed |
| No runtime changes | ✅ Confirmed |
| No model output changes | ✅ Confirmed |
| G20 BLOCKED | ✅ Unchanged |
| R99 NOT APPROVED | ✅ Unchanged |
| R102 NOT APPROVED | ✅ Unchanged |
| partial_pay_sweep not promoted | ✅ Unchanged |
| flat/min DSCR sculpting not promoted | ✅ Unchanged |
| Backend source of truth | ✅ Confirmed |
| No JS financial calculations | ✅ Confirmed |
| No fixture CSVs changed | ✅ Confirmed |
| No schema migrations | ✅ Confirmed |