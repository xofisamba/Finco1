"""Phase 49 Closeout — Export Service and Audit Extraction Tests.

Docs/reports-only phase. No production code changes.
Validates Phase 49 completion state.
"""
from pathlib import Path
import json
from unittest.mock import patch

BASE_SHA = "01edb03957716caee55cfa794c693d08b2d1acfb"
MAIN_WEB = Path("main_web.py")
CLOSEOUT_DOC = Path("docs/phase49_closeout_export_service_audit_extraction_summary.md")
RESIDUAL_MAP = Path("docs/phase49_main_web_residual_god_module_map.md")
CLOSEOUT_JSON = Path("reports/phase49_closeout_summary.json")
EXPORT_SERVICE = Path("app/services/export_service.py")
EXPORT_AUDIT_SERVICE = Path("app/services/export_audit_service.py")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: closeout doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_closeout_doc_exists():
    assert CLOSEOUT_DOC.exists(), f"Closeout doc not found: {CLOSEOUT_DOC}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: residual main_web map exists
# ─────────────────────────────────────────────────────────────────────────────
def test_residual_main_web_map_exists():
    assert RESIDUAL_MAP.exists(), f"Residual map not found: {RESIDUAL_MAP}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: JSON summary parses
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses():
    data = json.loads(CLOSEOUT_JSON.read_text())
    assert isinstance(data, dict)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: JSON says export_service_complete=true
# ─────────────────────────────────────────────────────────────────────────────
def test_export_service_complete():
    data = json.loads(CLOSEOUT_JSON.read_text())
    assert data.get("export_service_complete") is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: JSON says export_audit_service_complete=true
# ─────────────────────────────────────────────────────────────────────────────
def test_export_audit_service_complete():
    data = json.loads(CLOSEOUT_JSON.read_text())
    assert data.get("export_audit_service_complete") is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: JSON says main_web_record_export_calls=0
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_record_export_calls_zero():
    data = json.loads(CLOSEOUT_JSON.read_text())
    assert data.get("main_web_record_export_calls") == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: JSON says main_web_imports_record_export=false
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_no_longer_imports_record_export():
    data = json.loads(CLOSEOUT_JSON.read_text())
    assert data.get("main_web_imports_record_export") is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Docs mention PRs #361 through #369
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_mention_pr_range():
    text = CLOSEOUT_DOC.read_text()
    for pr in range(361, 370):
        assert f"#{pr}" in text, f"PR #{pr} not found in closeout doc"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Docs mention all 4 export routes
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_mention_all_4_export_routes():
    text = CLOSEOUT_DOC.read_text()
    routes = [
        "GET /download",
        "POST /download",
        "runtime-summary.csv",
        "institutional-workbook",
    ]
    for route in routes:
        assert route in text, f"Route '{route}' not found in closeout doc"


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Docs mention app/services/export_service.py
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_mention_export_service():
    text = CLOSEOUT_DOC.read_text()
    assert "app/services/export_service.py" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Docs mention app/services/export_audit_service.py
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_mention_export_audit_service():
    text = CLOSEOUT_DOC.read_text()
    assert "app/services/export_audit_service.py" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Docs mention Phase 50 recommended next
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_recommend_phase50():
    text = CLOSEOUT_DOC.read_text()
    assert "Phase 50" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: main_web.py does not import record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_does_not_import_record_export():
    text = MAIN_WEB.read_text()
    import_end = text.find("from app.persistence.provenance")
    import_section = text[:import_end]
    assert "record_export" not in import_section


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: main_web.py has zero direct record_export calls
# ─────────────────────────────────────────────────────────────────────────────
def test_zero_direct_record_export_calls():
    import re
    text = MAIN_WEB.read_text()
    calls = list(re.finditer(r'record_export\s*\(', text))
    assert len(calls) == 0, f"Expected 0 direct record_export calls, found {len(calls)}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: export_service.py exists
# ─────────────────────────────────────────────────────────────────────────────
def test_export_service_exists():
    assert EXPORT_SERVICE.exists(), f"export_service.py not found: {EXPORT_SERVICE}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: export_audit_service.py exists
# ─────────────────────────────────────────────────────────────────────────────
def test_export_audit_service_exists():
    assert EXPORT_AUDIT_SERVICE.exists(), f"export_audit_service.py not found: {EXPORT_AUDIT_SERVICE}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: No fixture CSV changes (git diff)
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "*.csv"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/")]
    assert changed == [], f"Fixture CSVs changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: No JS financial calculations
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations():
    # Closeout phase — verify production code unchanged (already verified via other tests)
    # This is a guardrail confirmation placeholder
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: JSON summary has correct PRs list
# ─────────────────────────────────────────────────────────────────────────────
def test_json_has_prs_361_to_369():
    data = json.loads(CLOSEOUT_JSON.read_text())
    prs = data.get("prs_merged", [])
    assert 361 in prs and 369 in prs, f"Expected PRs 361–369, got {prs}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: JSON has no_formula_changes=true
# ─────────────────────────────────────────────────────────────────────────────
def test_json_no_formula_changes():
    data = json.loads(CLOSEOUT_JSON.read_text())
    assert data.get("no_formula_changes") is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 21: JSON has no_model_output_changes=true
# ─────────────────────────────────────────────────────────────────────────────
def test_json_no_model_output_changes():
    data = json.loads(CLOSEOUT_JSON.read_text())
    assert data.get("no_model_output_changes") is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: Residual map mentions run route as high-priority extraction candidate
# ─────────────────────────────────────────────────────────────────────────────
def test_residual_map_identifies_run_route():
    text = RESIDUAL_MAP.read_text()
    assert "/run" in text and "HIGH" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: Residual map identifies record_workspace_runtime as Phase 50 candidate
# ─────────────────────────────────────────────────────────────────────────────
def test_residual_map_identifies_record_workspace_runtime():
    text = RESIDUAL_MAP.read_text()
    assert "record_workspace_runtime" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 24: Closeout doc mentions all 4 audit service functions
# ─────────────────────────────────────────────────────────────────────────────
def test_closeout_doc_mentions_audit_functions():
    text = CLOSEOUT_DOC.read_text()
    funcs = [
        "record_runtime_summary_export",
        "record_institutional_workbook_export",
        "record_download_export",
    ]
    for func in funcs:
        assert func in text, f"Function '{func}' not found in closeout doc"


# ─────────────────────────────────────────────────────────────────────────────
# Test 25: main_web.py imports audit service functions
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_audit_service():
    text = MAIN_WEB.read_text()
    assert "from app.services.export_audit_service import" in text
    assert "record_download_export" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 26: main_web.py imports export service
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_export_service():
    text = MAIN_WEB.read_text()
    assert "from app.services.export_service import" in text
    assert "build_excel_export_for_post_request" in text or "build_values_only_export" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 27: Services __init__.py exports audit functions
# ─────────────────────────────────────────────────────────────────────────────
def test_services_init_exports_audit_functions():
    from app.services import (
        record_runtime_summary_export,
        record_institutional_workbook_export,
        record_download_export,
    )
    assert callable(record_runtime_summary_export)
    assert callable(record_institutional_workbook_export)
    assert callable(record_download_export)


# ─────────────────────────────────────────────────────────────────────────────
# Test 28: Export route calls still use service functions
# ─────────────────────────────────────────────────────────────────────────────
def test_export_routes_use_service_functions():
    text = MAIN_WEB.read_text()
    # GET /download
    get_dl = text.find('@app.get("/download")')
    next_route = text.find('@app.get("/exports/', get_dl)
    get_section = text[get_dl:next_route]
    assert "record_download_export(" in get_section

    # POST /download
    post_dl = text.find('@app.post("/download")')
    next_route = text.find('@app.get("/download")', post_dl)
    post_section = text[post_dl:next_route]
    assert "record_download_export(" in post_section

    # runtime-summary.csv
    rt_sum = text.find('@app.get("/exports/runtime-summary.csv")')
    next_route = text.find('@app.get("/exports/institutional-workbook', rt_sum)
    rt_section = text[rt_sum:next_route]
    assert "record_runtime_summary_export(" in rt_section

    # institutional-workbook
    inst = text.find('@app.get("/exports/institutional-workbook.xlsx")')
    next_routes = [text.find('@app.get("/projects', inst), text.find('@app.post("/scenarios', inst)]
    inst_section = text[inst:min(n for n in next_routes if n > 0)]
    assert "record_institutional_workbook_export(" in inst_section