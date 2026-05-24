from __future__ import annotations

import os
import sys
import uuid

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.persistence.repository import compare_scenarios, save_project, save_scenario


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase14_compare_honesty_{uuid.uuid4().hex[:8]}.db")
    os.environ["FINCO_DB_PATH"] = db_file
    db_mod.DB_PATH = db_file

    yield db_file

    if os.path.exists(db_file):
        os.remove(db_file)
    if old_path:
        os.environ["FINCO_DB_PATH"] = old_path
        db_mod.DB_PATH = old_path
    else:
        os.environ.pop("FINCO_DB_PATH", None)


def test_compare_ui_includes_source_clarity_and_timestamps():
    compare_partial = _read("app", "templates", "partials", "scenario_compare.html")
    scenario_workspace = _read("app", "templates", "partials", "scenario_workspace.html")
    main_web = _read("main_web.py")

    assert "Scenario compare is descriptive only." in compare_partial
    assert "saved scenario snapshots and saved runtime summaries" in compare_partial
    assert "Compare generated at" in compare_partial
    assert "Saved snapshot timestamp:" in compare_partial
    assert "Runtime timestamp:" in compare_partial
    assert "Runtime snapshot ID:" in compare_partial
    assert "Runtime origin:" in compare_partial
    assert "Compare does not auto-save and does not auto-run." in compare_partial

    assert "Unsaved browser draft edits are not part of the comparison unless you save them first." in scenario_workspace
    assert "_build_compare_ui_context" in main_web
    assert "pending / unavailable" in main_web
    assert "not_applicable" in main_web


def test_compare_honesty_guardrails_and_governance_statements_exist():
    docs = _read("docs", "phase14_scenario_compare_honesty.md")
    styles = _read("static", "styles.css")
    main_web_source = _read("main_web.py")

    assert "Scenario compare is descriptive only." in docs
    assert "Compare does not auto-save and does not auto-run." in docs
    assert "Pending, unavailable, and `not_applicable` markers are intentional" in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs

    assert ".ps-compare-banner" in styles
    assert ".ps-compare-context-grid" in styles
    assert "compare_scenarios(user.user_id, left_scenario_id, right_scenario_id)" in main_web_source


def test_compare_repository_keeps_zero_distinct_from_missing_and_source_markers(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    left = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Base Snapshot",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"total_capex_keur": "100000", "opex_y1_keur": "0"},
        last_run_summary={"total_revenue_keur": 0.0, "project_irr": 0.094, "equity_irr": 0.113, "avg_dscr": "NOT_AVAILABLE"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    right = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Downside Snapshot",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"total_capex_keur": "104000", "opex_y1_keur": "2800"},
        last_run_summary={"total_revenue_keur": None, "project_irr": 0.089, "equity_irr": 0.106, "avg_dscr": 1.24},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )

    result = compare_scenarios(user_id, left.scenario_id, right.scenario_id)
    assert result is not None
    metrics = {row["metric"]: row for row in result["metrics"]}
    assert metrics["Revenue"]["left_value"] == 0.0
    assert metrics["Revenue"]["right_value"] is None
    assert metrics["Revenue"]["delta"] is None
    assert metrics["DSCR"]["left_value"] == "NOT_AVAILABLE"
    assert metrics["DSCR"]["right_value"] == 1.24
    assert metrics["DSCR"]["delta"] is None

    compare_partial = _read("app", "templates", "partials", "scenario_compare.html")
    main_web_source = _read("main_web.py")
    assert "Runtime snapshot ID:" in compare_partial
    assert "Runtime origin:" in compare_partial
    assert "pending values for zero" in compare_partial
    assert 'if value in (None, "", "NOT_AVAILABLE")' in main_web_source
    assert 'return "pending / unavailable"' in main_web_source
    assert 'if value is None:' in main_web_source
    assert 'return "not_applicable"' in main_web_source


def test_reports_exist_and_capture_compare_honesty_rules():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for report_name in (
        "phase14_scenario_compare_source_matrix.csv",
        "phase14_scenario_compare_missing_metric_matrix.csv",
        "phase14_scenario_compare_guardrail_matrix.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))

    source_matrix = _read("reports", "phase14_scenario_compare_source_matrix.csv")
    missing_matrix = _read("reports", "phase14_scenario_compare_missing_metric_matrix.csv")
    guardrails = _read("reports", "phase14_scenario_compare_guardrail_matrix.csv")

    assert "saved scenario snapshots and saved runtime summaries only" in source_matrix
    assert "missing_metric,\"pending / unavailable\"" in missing_matrix
    assert "missing_delta,\"not_applicable\"" in missing_matrix
    assert "compare_does_not_auto_save,confirmed" in guardrails
    assert "compare_does_not_auto_run,confirmed" in guardrails
    assert "missing_values_not_shown_as_zero,confirmed" in guardrails
    assert "g20_blocked,confirmed" in guardrails
    assert "r99_r102_not_approved,confirmed" in guardrails
