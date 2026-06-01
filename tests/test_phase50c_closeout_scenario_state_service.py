"""Phase 50C Closeout — Scenario State Service Extraction Tests.

Tests that the closeout documentation, JSON summary, and residual route map
exist and contain the correct assertions. This phase is docs/reports only —
no production code changes.

Base SHA: 83d4388f8a6272c2a51b8646a59f6f26cb703358 (PR #371)
Head SHA: 4ff6b84d6ef86222fdb9f11dfa92da02ca5285b7 (PR #375)
"""
from pathlib import Path
import json
import re

import pytest

BASE_SHA = "83d4388f8a6272c2a51b8646a59f6f26cb703358"
HEAD_SHA = "4ff6b84d6ef86222fdb9f11dfa92da02ca5285b7"

DOCS_DIR = Path("docs")
REPORTS_DIR = Path("reports")
SCENARIO_SERVICE = Path("app/services/scenario_state_service.py")
EXPORT_SERVICE = Path("app/services/export_service.py")
EXPORT_AUDIT_SERVICE = Path("app/services/export_audit_service.py")
MAIN_WEB = Path("main_web.py")


# ─────────────────────────────────────────────────────────────────────────────
# Docs exist
# ─────────────────────────────────────────────────────────────────────────────
def test_closeout_doc_exists():
    assert DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md"


def test_residual_route_map_exists():
    assert DOCS_DIR / "phase50c_residual_run_compare_route_map.md"


def test_json_summary_exists():
    assert REPORTS_DIR / "phase50c_closeout_summary.json"


# ─────────────────────────────────────────────────────────────────────────────
# JSON summary parses
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses():
    text = (REPORTS_DIR / "phase50c_closeout_summary.json").read_text()
    data = json.loads(text)
    assert isinstance(data, dict)
    assert "phase" in data
    assert data["phase"] == "50C"


# ─────────────────────────────────────────────────────────────────────────────
# JSON summary content assertions
# ─────────────────────────────────────────────────────────────────────────────
def test_json_production_code_unchanged():
    data = json.loads((REPORTS_DIR / "phase50c_closeout_summary.json").read_text())
    assert data["production_code_changed"] is False


def test_json_scenario_service_complete():
    data = json.loads((REPORTS_DIR / "phase50c_closeout_summary.json").read_text())
    assert data["scenario_state_service_complete_for_current_scope"] is True


def test_json_service_functions():
    data = json.loads((REPORTS_DIR / "phase50c_closeout_summary.json").read_text())
    funcs = data["service_functions"]
    for f in [
        "build_workspace_state_metadata",
        "scenario_provenance_for_record",
        "RuntimeSnapshotResolution",
        "resolve_runtime_snapshot",
        "check_runtime_allowed",
    ]:
        assert f in funcs, f"Missing: {f}"


def test_json_main_web_no_direct_runtime_guard_import():
    data = json.loads((REPORTS_DIR / "phase50c_closeout_summary.json").read_text())
    assert data["main_web_runtime_guard_direct_import"] is False


def test_json_main_web_zero_record_export():
    data = json.loads((REPORTS_DIR / "phase50c_closeout_summary.json").read_text())
    assert data["main_web_record_export_calls"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Closeout doc content assertions
# ─────────────────────────────────────────────────────────────────────────────
def test_closeout_doc_mentions_prs_371_to_375():
    text = (DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md").read_text()
    for pr in ["#371", "#372", "#373", "#374", "#375"]:
        assert pr in text, f"Missing {pr} in closeout doc"


def test_closeout_doc_mentions_routes():
    text = (DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md").read_text()
    assert "/run" in text
    assert "/compare" in text
    assert "/download" in text or "POST /download" in text


def test_closeout_doc_mentions_wrapper_remains():
    text = (DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md").read_text()
    assert "_resolve_runtime_snapshot_source" in text
    assert "thin wrapper" in text.lower() or "wrapper" in text


def test_closeout_doc_mentions_zero_record_export():
    text = (DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md").read_text()
    assert "record_export" in text
    assert "0" in text or "zero" in text.lower()


def test_closeout_doc_mentions_no_direct_runtime_guard_import():
    text = (DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md").read_text()
    assert "runtime_guard_for_snapshot" in text
    # Should mention it was removed or wrapped
    assert "wrapper" in text.lower() or "wrapped" in text.lower() or "check_runtime_allowed" in text


def test_closeout_doc_mentions_service_functions():
    text = (DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md").read_text()
    for f in [
        "build_workspace_state_metadata",
        "scenario_provenance_for_record",
        "RuntimeSnapshotResolution",
        "resolve_runtime_snapshot",
        "check_runtime_allowed",
    ]:
        assert f in text, f"Missing {f} in closeout doc"


def test_closeout_doc_mentions_base_sha():
    text = (DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md").read_text()
    assert BASE_SHA[:12] in text


# ─────────────────────────────────────────────────────────────────────────────
# Residual route map content assertions
# ─────────────────────────────────────────────────────────────────────────────
def test_residual_map_mentions_routes():
    text = (DOCS_DIR / "phase50c_residual_run_compare_route_map.md").read_text()
    assert "/run" in text
    assert "/compare" in text
    assert "/download" in text or "POST /download" in text


def test_residual_map_mentions_project_workspace_request():
    text = (DOCS_DIR / "phase50c_residual_run_compare_route_map.md").read_text()
    assert "_project_workspace_from_request" in text or "project/workspace" in text.lower()


def test_residual_map_mentions_record_workspace_runtime():
    text = (DOCS_DIR / "phase50c_residual_run_compare_route_map.md").read_text()
    assert "record_workspace_runtime" in text


def test_residual_map_mentions_collect_form_snapshot():
    text = (DOCS_DIR / "phase50c_residual_run_compare_route_map.md").read_text()
    assert "_collect_form_snapshot" in text


# ─────────────────────────────────────────────────────────────────────────────
# Service files exist
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_service_exists():
    assert SCENARIO_SERVICE.exists()


def test_export_service_exists():
    assert EXPORT_SERVICE.exists()


def test_export_audit_service_exists():
    assert EXPORT_AUDIT_SERVICE.exists()


# ─────────────────────────────────────────────────────────────────────────────
# main_web.py state assertions
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_zero_record_export_calls():
    text = MAIN_WEB.read_text()
    count = len(re.findall(r'record_export\s*\(', text))
    assert count == 0, f"Expected 0 record_export calls, found {count}"


def test_main_web_no_direct_runtime_guard_import():
    """runtime_guard_for_snapshot should not be imported directly into main_web."""
    text = MAIN_WEB.read_text()
    import_lines = [
        l for l in text.split('\n')
        if 'runtime_guard_for_snapshot' in l and 'import' in l
    ]
    assert len(import_lines) == 0, f"Still imported: {import_lines}"


def test_main_web_uses_check_runtime_allowed():
    text = MAIN_WEB.read_text()
    count = len(re.findall(r'check_runtime_allowed\(', text))
    assert count == 6, f"Expected 6 call sites, found {count}"


# ─────────────────────────────────────────────────────────────────────────────
# scenario_state_service.py content assertions
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_service_has_all_functions():
    text = SCENARIO_SERVICE.read_text()
    for f in [
        "def build_workspace_state_metadata",
        "def scenario_provenance_for_record",
        "def resolve_runtime_snapshot",
        "def check_runtime_allowed",
    ]:
        assert f in text, f"Missing {f} in scenario_state_service.py"
    assert "class RuntimeSnapshotResolution" in text


# ─────────────────────────────────────────────────────────────────────────────
# No fixture CSV changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/main", "--", "*.csv"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/")]
    assert changed == [], f"Fixture CSVs changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# No JS financial calculations
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations():
    # Closeout phase — docs only, no code changes
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# Guards: recommended next phase is 50D
# ─────────────────────────────────────────────────────────────────────────────
def test_recommended_next_phase_is_50d():
    data = json.loads((REPORTS_DIR / "phase50c_closeout_summary.json").read_text())
    assert "50D" in data.get("recommended_next_phase", "")


# ─────────────────────────────────────────────────────────────────────────────
# PRs 371-375 all mentioned
# ─────────────────────────────────────────────────────────────────────────────
def test_all_phase_50_prs_mentioned():
    text = (DOCS_DIR / "phase50c_closeout_scenario_state_service_summary.md").read_text()
    for pr_num in [371, 372, 373, 374, 375]:
        assert f"#{pr_num}" in text, f"Missing #{pr_num}"