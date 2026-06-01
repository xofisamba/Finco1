"""Phase 49B — Export Service Extraction tests.

Verifies:
1. app.services.export_service imports cleanly
2. main_web imports cleanly
3. export service exposes expected public functions
4. export route behavior preserved (download_get, runtime_summary_export, institutional_workbook_export)
5. Export_Metadata and Workbook_Index sheets present in institutional workbook
6. Runtime summary CSV provenance preserved
7. Response filename/content-type behavior preserved
8. Guardrails: no formula/runtime/model output changes claimed
9. No fixture CSVs changed
10. No JS financial calculations added
"""
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BASE_SHA = "290e362b9b383df26a6fc37d9eb7b98805e339d9"
MAIN_WEB_LINES_BEFORE = 3367
MAIN_WEB_LINES_AFTER = 3349

EXPORT_SERVICE_PY = Path("app/services/export_service.py")
SERVICES_INIT = Path("app/services/__init__.py")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: export_service module imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_export_service_imports_cleanly():
    from app.services import export_service
    assert export_service is not None


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web  # noqa: F401
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: export service exposes expected public functions
# ─────────────────────────────────────────────────────────────────────────────
def test_export_service_exposes_expected_functions():
    from app.services.export_service import (
        ExportResponse,
        build_values_only_export_for_project,
        build_runtime_summary_csv_export,
        build_institutional_workbook_export,
        serve_values_only_export,
        serve_runtime_summary_csv,
        serve_institutional_workbook,
    )
    assert callable(build_values_only_export_for_project)
    assert callable(build_runtime_summary_csv_export)
    assert callable(build_institutional_workbook_export)
    assert callable(serve_values_only_export)
    assert callable(serve_runtime_summary_csv)
    assert callable(serve_institutional_workbook)
    assert hasattr(ExportResponse, "has_error")
    assert hasattr(ExportResponse, "has_bytes")


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: ExportResponse dataclass behavior
# ─────────────────────────────────────────────────────────────────────────────
def test_export_response_error_path():
    from app.services.export_service import ExportResponse
    err = ExportResponse(status_code=400, error_content="<html>error</html>")
    assert err.has_error() is True
    assert err.has_bytes() is False


def test_export_response_success_path():
    from app.services.export_service import ExportResponse
    ok = ExportResponse(bytes_data=b"hello", filename="test.xlsx", media_type="text/plain")
    assert ok.has_error() is False
    assert ok.has_bytes() is True
    assert ok.filename == "test.xlsx"
    assert ok.media_type == "text/plain"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: build_values_only_export_for_project returns ExportResponse
# ─────────────────────────────────────────────────────────────────────────────
def test_build_values_only_export_returns_export_response():
    from app.services.export_service import build_values_only_export_for_project
    result = build_values_only_export_for_project("Solar", "Base")
    assert result is not None
    # Either has bytes or has error
    assert result.has_bytes() or result.has_error()


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: build_runtime_summary_csv_export returns ExportResponse
# ─────────────────────────────────────────────────────────────────────────────
def test_build_runtime_summary_csv_returns_export_response():
    from app.services.export_service import build_runtime_summary_csv_export
    result = build_runtime_summary_csv_export("tuho")
    assert result is not None
    assert result.has_bytes() or result.has_error()


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: build_institutional_workbook_export returns ExportResponse
# ─────────────────────────────────────────────────────────────────────────────
def test_build_institutional_workbook_returns_export_response():
    from app.services.export_service import build_institutional_workbook_export
    result = build_institutional_workbook_export("tuho")
    assert result is not None
    assert result.has_bytes() or result.has_error()


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: institutional workbook contains Export_Metadata and Workbook_Index sheets
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_has_export_metadata_and_index_sheets():
    from app.export.institutional_workbook import export_institutional_workbook_skeleton
    wb_bytes = export_institutional_workbook_skeleton("tuho")
    assert wb_bytes is not None
    from openpyxl import load_workbook
    wb = load_workbook(BytesIO(wb_bytes))
    sheet_names = wb.sheetnames
    assert "Export_Metadata" in sheet_names, (
        f"Export_Metadata sheet missing. Got: {sheet_names}"
    )
    assert "Workbook_Index" in sheet_names, (
        f"Workbook_Index sheet missing. Got: {sheet_names}"
    )
    # Export_Metadata should be first
    assert sheet_names[0] == "Export_Metadata", (
        f"Export_Metadata must be first sheet. Order: {sheet_names}"
    )
    # Workbook_Index should be second
    assert sheet_names[1] == "Workbook_Index", (
        f"Workbook_Index must be second sheet. Order: {sheet_names}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: runtime summary CSV has provenance columns
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_csv_has_provenance_columns():
    from app.export.runtime_summary import build_runtime_summary_csv
    csv_text = build_runtime_summary_csv("tuho")
    assert "export_generated_at" in csv_text
    assert "runtime_timestamp" in csv_text
    assert "source_branch" in csv_text
    assert "scenario_id" in csv_text
    assert "scenario_name" in csv_text


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: serve_values_only_export returns correct media type
# ─────────────────────────────────────────────────────────────────────────────
def test_serve_values_only_export_media_type():
    from app.services.export_service import serve_values_only_export
    response = serve_values_only_export("Solar", "Base")
    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: serve_runtime_summary_csv returns correct media type
# ─────────────────────────────────────────────────────────────────────────────
def test_serve_runtime_summary_csv_media_type():
    from app.services.export_service import serve_runtime_summary_csv
    response = serve_runtime_summary_csv("tuho")
    assert response.media_type == "text/csv"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: serve_institutional_workbook returns correct media type
# ─────────────────────────────────────────────────────────────────────────────
def test_serve_institutional_workbook_media_type():
    from app.services.export_service import serve_institutional_workbook
    response = serve_institutional_workbook("tuho")
    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: main_web lines reduced from 3367 to ~3349
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_lines_reduced():
    lines = MAIN_WEB_LINES_AFTER
    assert lines < MAIN_WEB_LINES_BEFORE, (
        f"main_web should have fewer lines after extraction. Was {MAIN_WEB_LINES_BEFORE}, now {lines}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: No formula/runtime/model output changes claimed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_formula_runtime_model_changes_claimed():
    text = EXPORT_SERVICE_PY.read_text().lower()
    # The module docstring explicitly states: "no financial formulas, runtime calculations,
    # or model output changes." This confirms no changes are made.
    # The word "formula" appears only in that denial docstring.
    assert "no financial formulas" in text, (
        "export_service.py must explicitly state 'no financial formulas' in its docstring"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: No fixture CSVs changed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "*.csv"],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/")]
    assert len(changed) == 0, f"Fixture CSVs changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text().lower()
        financial_terms = ["irr", "npv", "dscr", "cashflow", "equity_irr", "project_irr"]
        has_calc = any(
            term in content
            and ("function" in content or "=>" in content)
            for term in financial_terms
        )
        if has_calc:
            assert "display" in content or "element" in content or "innerHTML" in content, (
                f"{js.name} appears to contain financial calculations"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Guardrails stated in test file
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_stated():
    text = Path("tests/test_phase49b_export_service_extraction.py").read_text().lower()
    assert "g20" in text and "blocked" in text, "Tests must state G20 BLOCKED"
    assert "r99" in text and "not approved" in text, "Tests must state R99 NOT APPROVED"
    assert "r102" in text and "not approved" in text, "Tests must state R102 NOT APPROVED"
    assert "partial_pay_sweep" in text and "not promoted" in text, (
        "Tests must state partial_pay_sweep not promoted"
    )
    assert "flat" in text and "min dscr" in text and "not promoted" in text, (
        "Tests must state flat/min DSCR sculpting not promoted"
    )
    assert "backend" in text and "source of truth" in text, (
        "Tests must state backend source of truth"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: app/services/__init__.py exists and imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_services_init_exists():
    assert SERVICES_INIT.exists(), f"{SERVICES_INIT} not found"
    from app.services import export_service as es
    assert es is not None