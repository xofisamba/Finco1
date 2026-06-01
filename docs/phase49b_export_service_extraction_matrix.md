# Phase 49B — Export Service Extraction Matrix

**Branch:** `phase49b-extract-export-service-from-main-web`
**Base SHA:** `290e362b9b383df26a6fc37d9eb7b98805e339d9`

---

## Extraction Matrix

| Export route/function | Previous location | New service function | Response type | Filename behavior preserved? | Content-type preserved? | Workbook metadata preserved? | Tests |
|----------------------|------------------|---------------------|--------------|------------------------------|----------------------|---------------------------|-------|
| `GET /download` — `download_get` | main_web.py:2187 | `build_values_only_export_for_project()` | StreamingResponse | ✅ `fincogpt_{type}_{scenario}.xlsx` | ✅ `application/vnd.openxmlformats...sheet` | N/A (values-only Excel) | ✅ test_serve_values_only_export_media_type |
| `GET /exports/runtime-summary.csv` — `runtime_summary_export` | main_web.py:2241 | `build_runtime_summary_csv_export()` | StreamingResponse | ✅ `phase10_{proj}_runtime_summary.csv` | ✅ `text/csv` | N/A | ✅ test_serve_runtime_summary_csv_media_type |
| `GET /exports/institutional-workbook.xlsx` — `institutional_workbook_export` | main_web.py:2287 | `build_institutional_workbook_export()` | StreamingResponse | ✅ `phase10_{proj}_institutional_workbook_skeleton.xlsx` | ✅ `application/vnd.openxmlformats...sheet` | ✅ Export_Metadata first, Workbook_Index second | ✅ test_institutional_workbook_has_export_metadata_and_index_sheets |
| `POST /download` — `download_post` | main_web.py:2053 | Not extracted (complex POST form handling) | StreamingResponse | ✅ preserved | ✅ preserved | N/A | ⚠️ route tests cover it |

---

## Production Files Changed

| File | Change type | Lines delta |
|------|------------|-----------|
| `main_web.py` | Routes wrapped to delegate to service | −18 (3367→3349) |
| `app/services/__init__.py` | New | +18 |
| `app/services/export_service.py` | New | +224 |

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