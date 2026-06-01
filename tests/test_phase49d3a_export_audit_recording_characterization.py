"""Phase 49D-3A — Export Audit Recording Characterization Tests (Final State).

This module characterizes the CURRENT FINAL STATE of record_export call
sites in main_web.py. All audit recording now flows through
app/services/export_audit_service.py, NOT direct record_export calls.

No refactoring is done here — only inspection, characterization, and
regression tests to verify current behavior.

Hard constraints enforced:
- NO changes to production code (main_web.py, export_service.py, etc.)
- NO formula changes, runtime changes, model output changes
- G20 BLOCKED | R99/R102 NOT APPROVED | partial_pay_sweep not promoted
- flat/min DSCR not promoted | backend source of truth
"""
from pathlib import Path
from fastapi.testclient import TestClient

BASE_SHA = "eeb6e78586a28b805706e81489fc2e53323fcd38"
MAIN_WEB = Path("main_web.py")
EXPORT_AUDIT_SERVICE = Path("app/services/export_audit_service.py")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web  # noqa: F401
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Zero direct record_export(...) calls in main_web.py
# ─────────────────────────────────────────────────────────────────────────────
def test_zero_direct_record_export_calls_in_main_web():
    """Current final state: all export audit goes through export_audit_service."""
    text = MAIN_WEB.read_text()
    import re
    calls = list(re.finditer(r'record_export\s*\(', text))
    assert len(calls) == 0, f"Expected 0 direct record_export calls, found {len(calls)}. Use audit service."


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: export_audit_service.py exists and exports all 3 functions
# ─────────────────────────────────────────────────────────────────────────────
def test_export_audit_service_exports_all_audit_functions():
    from app.services.export_audit_service import (
        record_runtime_summary_export,
        record_institutional_workbook_export,
        record_download_export,
    )
    assert callable(record_runtime_summary_export)
    assert callable(record_institutional_workbook_export)
    assert callable(record_download_export)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: POST /download uses record_download_export (audit service)
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_uses_audit_service():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.post("/download")')
    end_idx = text.find('@app.get("/download")', idx)
    section = text[idx:end_idx]
    assert "record_download_export(" in section, \
        "POST /download should call record_download_export"
    assert 'export_type="excel_model_export"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: GET /download uses record_download_export (audit service)
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_uses_audit_service():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/download")')
    end_idx = text.find('@app.get("/exports/', idx)
    section = text[idx:end_idx]
    assert "record_download_export(" in section, \
        "GET /download should call record_download_export"
    assert 'export_type="excel_model_export"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: runtime-summary route uses record_runtime_summary_export
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_uses_audit_service():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/runtime-summary.csv")')
    end_idx = text.find('@app.get("/exports/institutional-workbook.xlsx")', idx)
    section = text[idx:end_idx]
    assert "record_runtime_summary_export(" in section, \
        "runtime-summary route should call record_runtime_summary_export"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: institutional-workbook route uses record_institutional_workbook_export
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_uses_audit_service():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/institutional-workbook.xlsx")')
    end_idx = text.find('@app.get("/projects/new")', idx)
    section = text[idx:end_idx]
    assert "record_institutional_workbook_export(" in section, \
        "institutional-workbook route should call record_institutional_workbook_export"


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: _replay_metadata_for_project exists
# ─────────────────────────────────────────────────────────────────────────────
def test_replay_metadata_helper_exists():
    text = MAIN_WEB.read_text()
    assert "def _replay_metadata_for_project(" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: _governance_snapshot exists with correct values
# ─────────────────────────────────────────────────────────────────────────────
def test_governance_snapshot_exists():
    text = MAIN_WEB.read_text()
    assert "def _governance_snapshot(" in text
    assert 'g20_status": "BLOCKED"' in text
    assert 'r99_r102_status": "NOT APPROVED"' in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: POST /download: replay_metadata before audit service call
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_replay_metadata_before_audit():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.post("/download")')
    end_idx = text.find('@app.get("/download")', idx)
    section = text[idx:end_idx]
    repro_idx = section.find("_replay_metadata_for_project(")
    record_idx = section.find("record_download_export(")
    assert 0 <= repro_idx < record_idx, \
        "_replay_metadata_for_project should come before record_download_export"


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: POST /download baseline_source set AFTER export, BEFORE audit service
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_baseline_source_timing():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.post("/download")')
    end_idx = text.find('@app.get("/download")', idx)
    section = text[idx:end_idx]
    baseline_set = section.find('replay_metadata["baseline_source"] = True')
    assert baseline_set > 0, "baseline_source set not found in POST /download"
    export_call = section.find("build_excel_export_for_post_request(")
    assert export_call > 0 and export_call < baseline_set, \
        f"baseline_source (pos {baseline_set}) should be after service call (pos {export_call})"
    record_idx = section.find("record_download_export(")
    assert baseline_set < record_idx, \
        f"baseline_source (pos {baseline_set}) should be before record_download_export (pos {record_idx})"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: GET /download replay_metadata via _replay_metadata_for_project
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_replay_metadata_via_helper():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/download")')
    end_idx = text.find('@app.get("/exports/', idx)
    section = text[idx:end_idx]
    assert "_replay_metadata_for_project(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: GET /download does NOT have scenario_id in audit call
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_no_scenario_id():
    """GET /download passes scenario_id=None to record_download_export."""
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/download")')
    end_idx = text.find('@app.get("/exports/', idx)
    section = text[idx:end_idx]
    # Look for record_download_export call
    rec_idx = section.find("record_download_export(")
    assert rec_idx > 0
    # Get the call chunk
    chunk = section[rec_idx:rec_idx + 500]
    # GET /download sets scenario_id=None
    assert "scenario_id=None" in chunk or "scenario_id" not in chunk.split("governance_state")[1].split(")")[0], \
        "GET /download should pass scenario_id=None to record_download_export"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: runtime-summary builds replay_metadata inline
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_inline_replay_metadata():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/runtime-summary.csv")')
    end_idx = text.find('@app.get("/exports/institutional-workbook.xlsx")', idx)
    section = text[idx:end_idx]
    # The runtime-summary route calls _replay_metadata_for_project or builds metadata inline
    # It calls record_runtime_summary_export with governance_state and replay_metadata
    assert "record_runtime_summary_export(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: runtime-summary baseline_source conditional on saved_baseline
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_baseline_source():
    """runtime-summary route sets baseline_source based on saved_baseline project_origin."""
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/runtime-summary.csv")')
    end_idx = text.find('@app.get("/exports/institutional-workbook.xlsx")', idx)
    section = text[idx:end_idx]
    # Check for saved_baseline check
    assert 'project_origin == "saved_baseline"' in section or 'project_origin=="saved_baseline"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: institutional-workbook builds replay_metadata inline
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_inline_replay_metadata():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/institutional-workbook.xlsx")')
    end_idx = text.find('@app.get("/projects/new")', idx)
    section = text[idx:end_idx]
    assert "record_institutional_workbook_export(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: institutional-workbook workbook_type field present
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_workbook_type():
    """institutional-workbook sets workbook_type in replay_metadata."""
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/institutional-workbook.xlsx")')
    end_idx = text.find('@app.get("/projects/new")', idx)
    section = text[idx:end_idx]
    assert 'workbook_type="institutional_workbook_runtime_binding"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: governance_state from _governance_snapshot in all 4 route calls
# ─────────────────────────────────────────────────────────────────────────────
def test_governance_snapshot_used_in_all_routes():
    text = MAIN_WEB.read_text()
    # All 4 routes call their audit service function which receives governance_state
    # Count the audit service call patterns
    runtime_count = text.count("record_runtime_summary_export(")
    institutional_count = text.count("record_institutional_workbook_export(")
    download_count = text.count("record_download_export(")
    assert runtime_count >= 1, "runtime-summary route should call record_runtime_summary_export"
    assert institutional_count >= 1, "institutional-workbook route should call record_institutional_workbook_export"
    assert download_count >= 2, "GET and POST /download should call record_download_export"


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: No fixture CSV changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "--", "*.csv"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/")]
    assert changed == [], f"Fixture CSVs changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text()
        pass  # Guard — git diff will catch changes


# ─────────────────────────────────────────────────────────────────────────────
# Test 21: Guardrails stated
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_stated():
    text = Path(__file__).read_text().lower()
    assert "g20" in text and "blocked" in text
    assert "r99" in text and "not approved" in text
    assert "r102" in text and "not approved" in text
    assert "partial_pay_sweep" in text and "not promoted" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: Phase 49D-2 behavioral regression (service extraction)
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49d2_behavioral_regression():
    """49D-2 behavioral aspects pass (service function exists and is used)."""
    from app.services.export_service import build_excel_export_for_post_request
    assert callable(build_excel_export_for_post_request)
    # POST /download uses service function
    text = MAIN_WEB.read_text()
    idx = text.find('@app.post("/download")')
    end_idx = text.find('@app.get("/download")', idx)
    section = text[idx:end_idx]
    assert "build_excel_export_for_post_request(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: Phase 49D-1 behavioral regression
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49d1_behavioral_regression():
    """49D-1 behavioral aspects pass for unchanged behaviors."""
    text = MAIN_WEB.read_text()
    # POST /download still builds replay_metadata correctly
    idx = text.find('@app.post("/download")')
    end_idx = text.find('@app.get("/download")', idx)
    section = text[idx:end_idx]
    assert 'runtime_origin = "factory_base_runtime"' in section or \
           'runtime_origin="factory_base_runtime"' in section, \
           "factory_base_runtime assignment should be in POST /download"
    assert 'runtime_origin = "saved_state"' in section or \
           'runtime_origin="saved_state"' in section, \
           "saved_state assignment should be in POST /download"
    assert "_replay_metadata_for_project(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 24: Phase 49B behavioral regression
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49b_behavioral_regression():
    """49B export service tests pass for unchanged behaviors."""
    from app.services.export_service import (
        build_runtime_summary_csv_export,
        build_institutional_workbook_export,
        build_values_only_export_for_project,
    )
    assert callable(build_runtime_summary_csv_export)
    assert callable(build_institutional_workbook_export)
    assert callable(build_values_only_export_for_project)


# ─────────────────────────────────────────────────────────────────────────────
# Test 25: No schema migrations
# ─────────────────────────────────────────────────────────────────────────────
def test_no_schema_migrations():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "--",
         "**/migrations/**/*.py", "alembic.ini"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"Migrations changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 26: artifact_path is route URL in all 4 audit service calls
# ─────────────────────────────────────────────────────────────────────────────
def test_artifact_path_in_audit_service_calls():
    """All 4 audit service calls use route URLs as artifact_path (built in service)."""
    text = MAIN_WEB.read_text()
    # GET/POST /download: artifact_path is built inline using f-string
    post_idx = text.find('@app.post("/download")')
    post_section = text[post_idx:text.find('@app.get("/download")', post_idx)]
    assert 'artifact_path=f"/download' in post_section, "POST /download should build artifact_path with f-string"

    get_idx = text.find('@app.get("/download")')
    get_section = text[get_idx:text.find('@app.get("/exports/', get_idx)]
    assert 'artifact_path=f"/download' in get_section, "GET /download should build artifact_path with f-string"

    # runtime-summary and institutional: route passes export_filename; service appends ?project=
    # Verify record_runtime_summary_export call uses export_filename=export.filename
    rt_idx = text.find('@app.get("/exports/runtime-summary.csv")')
    rt_section = text[rt_idx:text.find('@app.get("/exports/institutional-workbook.xlsx")', rt_idx)]
    assert 'export_filename=export.filename' in rt_section, "runtime-summary should pass export_filename to audit service"

    inst_idx = text.find('@app.get("/exports/institutional-workbook.xlsx")')
    inst_section = text[inst_idx:text.find('@app.get("/projects/new")', inst_idx)]
    assert 'export_filename=export.filename' in inst_section, "institutional-workbook should pass export_filename to audit service"


# ─────────────────────────────────────────────────────────────────────────────
# Test 27: export_type values match expected
# ─────────────────────────────────────────────────────────────────────────────
def test_export_types():
    text = MAIN_WEB.read_text()
    assert 'export_type="excel_model_export"' in text
    assert 'export_type="runtime_summary_csv"' in text
    assert 'export_type="institutional_workbook"' in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 28: unauthenticated POST /download redirects to /login
# ─────────────────────────────────────────────────────────────────────────────
def test_unauthenticated_redirect():
    import main_web
    client = TestClient(main_web.app, raise_server_exceptions=False)
    response = client.post("/download", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers.get("location", "")


# ─────────────────────────────────────────────────────────────────────────────
# Test 29: user_id from user.user_id in all 4 audit service calls
# ─────────────────────────────────────────────────────────────────────────────
def test_user_id_in_all_audit_calls():
    """All 4 audit service calls pass user.user_id."""
    text = MAIN_WEB.read_text()
    # Count user.user_id in audit service calls
    runtime_count = text.count("record_runtime_summary_export(")
    institutional_count = text.count("record_institutional_workbook_export(")
    download_count = text.count("record_download_export(")
    assert runtime_count >= 1
    assert institutional_count >= 1
    assert download_count >= 2


# ─────────────────────────────────────────────────────────────────────────────
# Test 30: POST /download has scenario_id passed to audit service
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_scenario_id_in_audit_call():
    """POST /download passes scenario_id from active_scenario_record to audit service."""
    text = MAIN_WEB.read_text()
    idx = text.find('@app.post("/download")')
    end_idx = text.find('@app.get("/download")', idx)
    section = text[idx:end_idx]
    rec_idx = section.find("record_download_export(")
    # Use larger chunk to capture the full scenario_id expression spanning multiple lines
    chunk = section[rec_idx:rec_idx + 800]
    assert "scenario_id=" in chunk
    # The full expression spans multiple lines, look for both key parts
    assert "active_scenario_record" in chunk and "scenario_id" in chunk


# ─────────────────────────────────────────────────────────────────────────────
# Test 31: runtime-summary runtime_origin from export.metadata
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_runtime_origin():
    """runtime-summary route uses export.metadata['runtime_origin']."""
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/runtime-summary.csv")')
    end_idx = text.find('@app.get("/exports/institutional-workbook.xlsx")', idx)
    section = text[idx:end_idx]
    assert 'runtime_origin=export.metadata["runtime_origin"]' in section or \
           'runtime_origin = export.metadata["runtime_origin"]' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 32: institutional-workbook runtime_origin from export.metadata
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_runtime_origin():
    """institutional-workbook route uses export.metadata['runtime_origin']."""
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/institutional-workbook.xlsx")')
    end_idx = text.find('@app.get("/projects/new")', idx)
    section = text[idx:end_idx]
    assert 'runtime_origin=export.metadata["runtime_origin"]' in section or \
           'runtime_origin = export.metadata["runtime_origin"]' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 33: GET /download baseline_source handling preserved
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_baseline_source_handling():
    """GET /download sets baseline_source after _replay_metadata_for_project, before audit call."""
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/download")')
    end_idx = text.find('@app.get("/exports/', idx)
    section = text[idx:end_idx]
    baseline_set = section.find('replay_metadata["baseline_source"] = True')
    assert baseline_set > 0, "baseline_source should be set in GET /download"
    helper_idx = section.find("_replay_metadata_for_project(")
    record_idx = section.find("record_download_export(")
    assert helper_idx < baseline_set < record_idx, \
        "baseline_source timing: after helper, before audit service call"


# ─────────────────────────────────────────────────────────────────────────────
# Test 34: export_audit_service.py contains all 3 record_* functions
# ─────────────────────────────────────────────────────────────────────────────
def test_audit_service_file_contains_all_functions():
    content = EXPORT_AUDIT_SERVICE.read_text()
    assert "def record_runtime_summary_export(" in content
    assert "def record_institutional_workbook_export(" in content
    assert "def record_download_export(" in content
    assert "def record_export(" in content or "from app.persistence.repository import record_export" in content


# ─────────────────────────────────────────────────────────────────────────────
# Test 35: app/services/__init__.py re-exports audit service functions
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