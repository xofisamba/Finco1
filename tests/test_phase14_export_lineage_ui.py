from __future__ import annotations

import os
import sys
import uuid

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.persistence.repository import build_export_lineage, record_export, save_project, save_scenario


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase14_export_lineage_{uuid.uuid4().hex[:8]}.db")
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


def test_export_lineage_panel_and_download_semantics_are_visible():
    workspace_shell = _read("app", "templates", "partials", "workspace_shell.html")
    scenario_workspace = _read("app", "templates", "partials", "scenario_workspace.html")
    index_html = _read("app", "templates", "index.html")

    assert "Export Lineage" in workspace_shell
    assert 'id="export-lineage-panel"' in workspace_shell
    assert "Reviewer-facing lineage only." in workspace_shell
    assert "Active project" in workspace_shell
    assert "Saved scenario boundary" in workspace_shell
    assert "Scenario revision" in workspace_shell
    assert "Last runtime snapshot" in workspace_shell
    assert "Runtime generated at" in workspace_shell
    assert "Governance posture" in workspace_shell
    assert "Values-only Excel Export (.xlsx)" in workspace_shell
    assert "Runtime Summary CSV" in workspace_shell
    assert "Institutional Workbook" in workspace_shell
    assert "Current draft is newer than the last clean runtime snapshot" in index_html
    assert "Values-only export uses submitted workbook values" in index_html

    assert "Export lineage is descriptive only." in scenario_workspace
    assert "Scenario ID" in scenario_workspace
    assert "Runtime snapshot" in scenario_workspace
    assert "Branch" in scenario_workspace
    assert "Template" in scenario_workspace


def test_export_lineage_ui_remains_descriptive_and_governance_safe():
    docs = _read("docs", "phase14_export_lineage_ui.md")
    app_js = _read("static", "app.js").lower()
    main_web_source = _read("main_web.py")

    assert "Export lineage UI is descriptive only." in docs
    assert "No runtime/model formulas were changed." in docs
    assert "No workbook calculations were changed." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs

    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "ebitda ="):
        assert marker not in app_js

    assert "_build_export_lineage_ui_context" in main_web_source
    assert "Descriptive only. This workbook is backend-authored and does not become the calculation engine." in main_web_source
    assert "Current draft is newer than the last runtime snapshot." in main_web_source


def test_export_lineage_repository_records_keep_scenario_and_replay_context(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Saved Case",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    record_export(
        user_id=user_id,
        project_code="tuho",
        export_type="runtime_summary_csv",
        artifact_name="runtime-summary.csv",
        project_id=project.project_id,
        scenario_id=scenario.scenario_id,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
        replay_metadata={
            "scenario_id": scenario.scenario_id,
            "scenario_revision": "2026-05-24 10:30",
            "runtime_snapshot_id": "runtime-1",
            "runtime_origin": "saved_state",
            "runtime_timestamp": "2026-05-24T10:00:00+00:00",
            "export_timestamp": "2026-05-24T10:45:00+00:00",
            "branch_name": "phase14-export-lineage-ui",
            "template_origin": "project_factory:tuho",
            "runtime_flag_count": 2,
        },
    )

    lineage = build_export_lineage(user_id, project.project_id)
    assert len(lineage) == 1
    item = lineage[0]
    assert item["scenario_name"] == "Saved Case"
    assert item["artifact_name"] == "runtime-summary.csv"
    assert item["replay_metadata"]["scenario_id"] == scenario.scenario_id
    assert item["replay_metadata"]["runtime_snapshot_id"] == "runtime-1"
    assert item["replay_metadata"]["runtime_origin"] == "saved_state"
    assert item["replay_metadata"]["branch_name"] == "phase14-export-lineage-ui"
    assert item["replay_metadata"]["template_origin"] == "project_factory:tuho"
    assert item["governance_state"]["g20_status"] == "BLOCKED"
    assert item["governance_state"]["r99_r102_status"] == "NOT APPROVED"


def test_reports_exist_and_capture_lineage_guardrails():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for report_name in (
        "phase14_export_lineage_ui_matrix.csv",
        "phase14_export_action_semantics.csv",
        "phase14_export_lineage_guardrail_matrix.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))

    matrix = _read("reports", "phase14_export_lineage_ui_matrix.csv")
    semantics = _read("reports", "phase14_export_action_semantics.csv")
    guardrails = _read("reports", "phase14_export_lineage_guardrail_matrix.csv")

    assert "workspace_shell export lineage panel" in matrix
    assert "scenario_workspace export lineage history" in matrix
    assert "values_only_excel_export" in semantics
    assert "runtime_summary_csv" in semantics
    assert "institutional_workbook" in semantics
    assert "no_runtime_model_formula_changes,confirmed" in guardrails
    assert "no_javascript_financial_calculations,confirmed" in guardrails
    assert "g20_blocked,confirmed" in guardrails
    assert "r99_r102_not_approved,confirmed" in guardrails
