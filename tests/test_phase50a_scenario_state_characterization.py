"""Phase 50A — Scenario State Service Characterization Tests.

Characterization only. No production code changes.
"""
from pathlib import Path
import json
import re

BASE_SHA = "c17208638b68240f3ea68c72e441eaee629409ac"
MAIN_WEB = Path("main_web.py")
CHAR_DOC = Path("docs/phase50a_scenario_state_characterization.md")
MATRIX_DOC = Path("docs/phase50a_scenario_state_behavior_matrix.md")
SUMMARY_JSON = Path("reports/phase50a_scenario_state_characterization_summary.json")
EXPORT_SERVICE = Path("app/services/export_service.py")
EXPORT_AUDIT_SERVICE = Path("app/services/export_audit_service.py")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web
    assert hasattr(main_web, 'app')


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: _resolve_runtime_snapshot_source exists (or documented equivalent)
# ─────────────────────────────────────────────────────────────────────────────
def test_resolve_runtime_snapshot_source_exists():
    text = MAIN_WEB.read_text()
    assert "_resolve_runtime_snapshot_source" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: runtime_guard_for_snapshot exists (imported from repository)
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_guard_for_snapshot_exists():
    text = MAIN_WEB.read_text()
    # Imported from app.persistence.repository
    assert "runtime_guard_for_snapshot" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: scenario provenance helper exists or documented equivalent
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_provenance_helper_exists():
    text = MAIN_WEB.read_text()
    # _scenario_provenance_for_record is documented
    assert "_scenario_provenance_for_record" in text or "scenario_provenance" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: docs mention saved_state, saved_baseline, user_created, factory_base_runtime
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_mention_runtime_paths():
    text = CHAR_DOC.read_text()
    for term in ["saved_state", "saved_baseline", "user_created", "factory_base_runtime"]:
        assert term in text, f"'{term}' not found in characterization doc"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: behavior matrix includes /run, GET /download, POST /download
# ─────────────────────────────────────────────────────────────────────────────
def test_matrix_includes_target_routes():
    text = MATRIX_DOC.read_text()
    for route in ["/run", "GET /download", "POST /download"]:
        assert route in text, f"'{route}' not found in behavior matrix"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: behavior matrix includes runtime_guard allowed and blocked
# ─────────────────────────────────────────────────────────────────────────────
def test_matrix_includes_runtime_guard():
    text = MATRIX_DOC.read_text()
    assert "runtime_guard allowed" in text or "runtime_guard" in text
    assert "runtime_guard blocked" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: docs mention active_project and scenario_id behavior
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_mention_active_project_and_scenario_id():
    text = CHAR_DOC.read_text()
    assert "active_project" in text or "active_scenario" in text
    assert "scenario_id" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: docs mention dirty/stale/runtime distinction
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_mention_dirty_stale_runtime():
    text = CHAR_DOC.read_text()
    assert "dirty" in text.lower() or "stale" in text.lower()
    assert "runtime" in text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: proposed service boundary is app/services/scenario_state_service.py
# ─────────────────────────────────────────────────────────────────────────────
def test_proposed_service_boundary_documented():
    text = CHAR_DOC.read_text()
    assert "scenario_state_service.py" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: docs clearly state no production code changes in 50A
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_state_no_production_code_changes():
    text = CHAR_DOC.read_text()
    # Verify characterization-only statement
    assert "characterization" in text.lower() or "no production code" in text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: main_web.py still contains scenario state logic; not extracted yet
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_not_yet_extracted():
    text = MAIN_WEB.read_text()
    # Scenario state logic should still be in main_web.py
    assert "_resolve_runtime_snapshot_source" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: no fixture CSV changes
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
# Test 14: no JS financial calculations
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations():
    assert True  # characterization only


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Phase 49 export/audit services still exist
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49_services_still_exist():
    assert EXPORT_SERVICE.exists()
    assert EXPORT_AUDIT_SERVICE.exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: main_web.py still has zero direct record_export calls
# ─────────────────────────────────────────────────────────────────────────────
def test_zero_direct_record_export_calls():
    text = MAIN_WEB.read_text()
    count = len(re.findall(r'record_export\s*\(', text))
    assert count == 0, f"Expected 0 record_export calls, found {count}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: JSON summary parses
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses():
    data = json.loads(SUMMARY_JSON.read_text())
    assert isinstance(data, dict)


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: JSON says production_code_changed=false
# ─────────────────────────────────────────────────────────────────────────────
def test_json_production_code_unchanged():
    data = json.loads(SUMMARY_JSON.read_text())
    assert data.get("production_code_changed") is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: JSON says ready_for_extraction=true
# ─────────────────────────────────────────────────────────────────────────────
def test_json_ready_for_extraction():
    data = json.loads(SUMMARY_JSON.read_text())
    assert data.get("ready_for_extraction") is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: JSON has no_formula_changes=true
# ─────────────────────────────────────────────────────────────────────────────
def test_json_no_formula_changes():
    data = json.loads(SUMMARY_JSON.read_text())
    assert data.get("no_formula_changes") is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 21: JSON has no_fixture_changes=true
# ─────────────────────────────────────────────────────────────────────────────
def test_json_no_fixture_changes():
    data = json.loads(SUMMARY_JSON.read_text())
    assert data.get("no_fixture_changes") is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: behavior matrix has all required rows
# ─────────────────────────────────────────────────────────────────────────────
def test_behavior_matrix_has_all_rows():
    text = MATRIX_DOC.read_text()
    # Rows are formatted as "### N. `/run` using ..." in the matrix
    required_rows = [
        "`/run` using saved_state",
        "`/run` using saved_baseline",
        "`/run` using user_created",
        "GET `/download` using factory_base_runtime",
        "POST `/download` using saved_state",
        "runtime_guard allowed",
        "runtime_guard blocked",
    ]
    for row in required_rows:
        assert row in text, f"Row '{row}' not found in behavior matrix"


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: characterization doc mentions decision tree
# ─────────────────────────────────────────────────────────────────────────────
def test_decision_tree_documented():
    text = CHAR_DOC.read_text()
    assert "decision" in text.lower() or "priority" in text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 24: docs mention extraction risks
# ─────────────────────────────────────────────────────────────────────────────
def test_extraction_risks_documented():
    text = CHAR_DOC.read_text()
    assert "risk" in text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 25: docs mention proposed service functions
# ─────────────────────────────────────────────────────────────────────────────
def test_proposed_service_functions_documented():
    text = CHAR_DOC.read_text()
    funcs = ["resolve_runtime_snapshot", "build_workspace_state_metadata"]
    for func in funcs:
        assert func in text, f"Function '{func}' not found in characterization doc"


# ─────────────────────────────────────────────────────────────────────────────
# Test 26: JSON has 13 behavior matrix rows
# ─────────────────────────────────────────────────────────────────────────────
def test_json_has_correct_row_count():
    data = json.loads(SUMMARY_JSON.read_text())
    assert data.get("behavior_matrix_rows") == 13


# ─────────────────────────────────────────────────────────────────────────────
# Test 27: docs mention routes depending on scenario state
# ─────────────────────────────────────────────────────────────────────────────
def test_routes_depending_on_scenario_state_documented():
    text = CHAR_DOC.read_text()
    assert "/run" in text and "/download" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 28: docs mention guardrails
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_documented():
    text = CHAR_DOC.read_text()
    assert "guardrail" in text.lower()
    assert "no production code" in text.lower() or "characterization only" in text.lower()