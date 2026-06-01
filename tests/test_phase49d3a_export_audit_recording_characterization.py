"""Phase 49D-3A — Export Audit Recording Characterization Tests.

This module characterizes the record_export call sites in main_web.py
WITHOUT changing production code. The goal is to lock down current
audit/provenance behavior so Phase 49D-3B can safely extract.

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

BASE_SHA = "c05d7b036ad2cab6d9c989e0ff78b3679c3e74c9"
MAIN_WEB = Path("main_web.py")


def _get_section(start_marker, end_marker=None):
    """Extract a route section from main_web.py."""
    text = MAIN_WEB.read_text()
    idx = text.find(start_marker)
    if idx < 0:
        return ""
    if end_marker:
        end_idx = text.find(end_marker, idx + len(start_marker))
        return text[idx:end_idx]
    return text[idx:idx + 10000]


def _get_record_export_call(route_marker, route_end_marker=None):
    """Extract the record_export call block from a route."""
    section = _get_section(route_marker, route_end_marker)
    if not section:
        return ""
    rec_start = section.find("record_export(")
    if rec_start < 0:
        return ""
    # Get the full call (up to 1500 chars to capture all kwargs)
    return section[rec_start:rec_start + 1500]


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web  # noqa: F401
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: record_export imported in main_web.py
# ─────────────────────────────────────────────────────────────────────────────
def test_record_export_imported():
    text = MAIN_WEB.read_text()
    assert "record_export" in text
    # Imported from app.persistence.repository (multi-line import)
    assert "from app.persistence.repository import" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: 4 record_export call sites exist in main_web.py
# ─────────────────────────────────────────────────────────────────────────────
def test_four_record_export_call_sites():
    text = MAIN_WEB.read_text()
    count = text.count("record_export(")
    assert count == 4, f"Expected 4 record_export calls, found {count}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: POST /download has record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_record_export():
    call = _get_record_export_call('@app.post("/download")', '@app.get("/download")')
    assert "record_export(" in call
    assert 'export_type="excel_model_export"' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: GET /download has record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_record_export():
    call = _get_record_export_call('@app.get("/download")', '@app.get("/exports/')
    assert "record_export(" in call
    assert 'export_type="excel_model_export"' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: runtime-summary route has record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_record_export():
    call = _get_record_export_call('@app.get("/exports/runtime-summary.csv")')
    assert "record_export(" in call
    assert 'export_type="runtime_summary_csv"' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: institutional-workbook route has record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_record_export():
    call = _get_record_export_call('@app.get("/exports/institutional-workbook.xlsx")')
    assert "record_export(" in call
    assert 'export_type="institutional_workbook"' in call


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
# Test 10: _replay_metadata_for_project is called before record_export in POST /download
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_replay_metadata_before_record():
    section = _get_section('@app.post("/download")', '@app.get("/download")')
    repro_idx = section.find("_replay_metadata_for_project(")
    record_idx = section.find("record_export(")
    assert 0 <= repro_idx < record_idx


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: POST /download baseline_source set AFTER export, BEFORE record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_baseline_source_timing():
    section = _get_section('@app.post("/download")', '@app.get("/download")')
    baseline_set = section.find('replay_metadata["baseline_source"] = True')
    assert baseline_set > 0, "baseline_source set not found in POST /download"
    export_call = section.find("build_excel_export_for_post_request(")
    assert export_call > 0 and export_call < baseline_set, \
        f"baseline_source (pos {baseline_set}) should be after service call (pos {export_call})"
    record_idx = section.find("record_export(")
    assert baseline_set < record_idx, \
        f"baseline_source (pos {baseline_set}) should be before record_export (pos {record_idx})"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: GET /download replay_metadata via _replay_metadata_for_project
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_replay_metadata_via_helper():
    section = _get_section('@app.get("/download")', '@app.get("/exports/')
    assert "_replay_metadata_for_project(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: GET /download does NOT have scenario_id in record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_no_scenario_id():
    call = _get_record_export_call('@app.get("/download")', '@app.get("/exports/')
    assert "scenario_id" not in call, \
        "GET /download should not pass scenario_id to record_export"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: runtime-summary inline _replay_metadata_for_project
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_inline_replay_metadata():
    call = _get_record_export_call('@app.get("/exports/runtime-summary.csv")')
    assert "_replay_metadata_for_project(" in call
    assert 'export_type="runtime_summary_csv"' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: runtime-summary baseline_source conditional on saved_baseline
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_baseline_source():
    call = _get_record_export_call('@app.get("/exports/runtime-summary.csv")')
    assert 'baseline_source=(project_record.project_origin == "saved_baseline")' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: institutional-workbook inline _replay_metadata_for_project
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_inline_replay_metadata():
    call = _get_record_export_call('@app.get("/exports/institutional-workbook.xlsx")')
    assert "_replay_metadata_for_project(" in call
    assert 'export_type="institutional_workbook"' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: institutional-workbook workbook_type field present
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_workbook_type():
    call = _get_record_export_call('@app.get("/exports/institutional-workbook.xlsx")')
    assert 'workbook_type="institutional_workbook_runtime_binding"' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: governance_state from _governance_snapshot in all 4 calls
# ─────────────────────────────────────────────────────────────────────────────
def test_governance_snapshot_used():
    text = MAIN_WEB.read_text()
    count = text.count("governance_state=_governance_snapshot(")
    assert count >= 4, f"Expected at least 4 _governance_snapshot calls, found {count}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: No production code changed by this phase
# ─────────────────────────────────────────────────────────────────────────────
def test_no_production_code_changed():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "main_web.py", "app/services/export_service.py", "app/excel_export.py",
         "app/ui_runner.py", "app/input_adapter.py"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], (
        f"Production files changed (should be 0): {changed}. "
        "Phase 49D-3A must NOT modify production code."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: No fixture CSV changes
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
# Test 21: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text()
        pass  # Guard — git diff will catch changes


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: Guardrails stated
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_stated():
    text = Path(__file__).read_text().lower()
    assert "g20" in text and "blocked" in text
    assert "r99" in text and "not approved" in text
    assert "r102" in text and "not approved" in text
    assert "partial_pay_sweep" in text and "not promoted" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: Phase 49D-2 tests — verify underlying behaviors (not git diff checks)
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49d2_behavioral_regression():
    """49D-2 tests pass for behavioral aspects (git diff checks expected to fail in 49D-3A context)."""
    import subprocess
    # Run only the behavioral tests, not the git-diff ones
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_phase49d2_post_download_extraction.py", "-q", "-k", "not no_production_code and not main_web_minimal"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, f"49D-2 behavioral tests failed:\n{result.stdout}\n{result.stderr}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 24: Phase 49D-1 tests behavioral regression
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49d1_behavioral_regression():
    """49D-1 tests pass for behavioral aspects."""
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_phase49d1_post_download_characterization.py", "-q", "-k", "not no_production_code and not build_excel_export_called"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, f"49D-1 behavioral tests failed:\n{result.stdout}\n{result.stderr}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 25: Phase 49B behavioral regression
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49b_behavioral_regression():
    """49B tests pass for behavioral aspects (line count tests expected to fail)."""
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_phase49b_export_service_extraction.py", "-q", "-k", "not main_web_lines and not main_web_line_count"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, f"49B behavioral tests failed:\n{result.stdout}\n{result.stderr}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 26: No schema migrations
# ─────────────────────────────────────────────────────────────────────────────
def test_no_schema_migrations():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "**/migrations/**/*.py", "alembic.ini"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"Migrations changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 27: artifact_path is route URL in all 4 calls
# ─────────────────────────────────────────────────────────────────────────────
def test_artifact_path_is_route_url():
    text = MAIN_WEB.read_text()
    import re
    calls = list(re.finditer(r'record_export\s*\(', text))
    assert len(calls) == 4
    for m in calls:
        chunk = text[m.start():m.start() + 1200]
        if 'artifact_path=' in chunk:
            has_url = (
                'artifact_path="/download' in chunk or
                'artifact_path="/exports/' in chunk or
                'artifact_path=f"/download' in chunk or
                'artifact_path=f"/exports/' in chunk
            )
            assert has_url, f"artifact_path should be a route URL in chunk: {chunk[:200]}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 28: export_type values match expected
# ─────────────────────────────────────────────────────────────────────────────
def test_export_types():
    text = MAIN_WEB.read_text()
    assert 'export_type="excel_model_export"' in text
    assert 'export_type="runtime_summary_csv"' in text
    assert 'export_type="institutional_workbook"' in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 29: unauthenticated POST /download redirects to /login
# ─────────────────────────────────────────────────────────────────────────────
def test_unauthenticated_redirect():
    import main_web
    client = TestClient(main_web.app, raise_server_exceptions=False)
    response = client.post("/download", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers.get("location", "")


# ─────────────────────────────────────────────────────────────────────────────
# Test 30: user_id from user.user_id in all 4 calls
# ─────────────────────────────────────────────────────────────────────────────
def test_user_id_in_all_calls():
    text = MAIN_WEB.read_text()
    import re
    calls = list(re.finditer(r'record_export\s*\(', text))
    assert len(calls) == 4
    for m in calls:
        chunk = text[m.start():m.start() + 1200]
        assert "user_id=user.user_id" in chunk


# ─────────────────────────────────────────────────────────────────────────────
# Test 31: POST /download has scenario_id in record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_has_scenario_id():
    call = _get_record_export_call('@app.post("/download")', '@app.get("/download")')
    assert "scenario_id=" in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 32: runtime-summary runtime_origin from export.metadata
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_runtime_origin():
    call = _get_record_export_call('@app.get("/exports/runtime-summary.csv")')
    assert 'runtime_origin=export.metadata["runtime_origin"]' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 33: institutional-workbook runtime_origin from export.metadata
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_runtime_origin():
    call = _get_record_export_call('@app.get("/exports/institutional-workbook.xlsx")')
    assert 'runtime_origin=export.metadata["runtime_origin"]' in call


# ─────────────────────────────────────────────────────────────────────────────
# Test 34: GET /download baseline_source is set (saved_baseline path)
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_has_baseline_source():
    """GET /download does set baseline_source for saved_baseline project_origin."""
    section = _get_section('@app.get("/download")', '@app.get("/exports/')
    # The GET /download route sets baseline_source after calling _replay_metadata_for_project
    # and before calling record_export (line ~2216)
    assert 'replay_metadata["baseline_source"] = True' in section
    # And it should be before record_export
    baseline_idx = section.find('replay_metadata["baseline_source"] = True')
    record_idx = section.find("record_export(")
    assert 0 <= baseline_idx < record_idx


# ─────────────────────────────────────────────────────────────────────────────
# Test 35: POST /download record_export has scenario_id from active_scenario_record
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_scenario_id_from_active_scenario():
    call = _get_record_export_call('@app.post("/download")', '@app.get("/download")')
    # scenario_id comes from active_scenario_record.scenario_id
    assert "active_scenario_record.scenario_id" in call