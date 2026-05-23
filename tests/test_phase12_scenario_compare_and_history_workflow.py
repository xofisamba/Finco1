"""Phase 12 scenario compare and history workflow tests."""

import os
import sys
import uuid
import types

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if "bcrypt" not in sys.modules:
    fake_bcrypt = types.SimpleNamespace(
        gensalt=lambda rounds=12: b"salt",
        hashpw=lambda password, salt: b"stub-hash",
        checkpw=lambda password, hashed: True,
    )
    sys.modules["bcrypt"] = fake_bcrypt

from app.persistence.repository import (
    build_export_lineage,
    compare_scenarios,
    get_scenario_history,
    record_export,
    save_project,
    save_scenario,
)


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase12_compare_{uuid.uuid4().hex[:8]}.db")
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


def test_scenario_compare_workflow_exists(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    left = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Base Snapshot",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"total_capex_keur": "100000", "opex_y1_keur": "2500"},
        last_run_summary={"total_revenue_keur": 120000.0, "project_irr": 0.094, "equity_irr": 0.113, "avg_dscr": 1.32},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    right = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Downside Snapshot",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"total_capex_keur": "104000", "opex_y1_keur": "2800"},
        last_run_summary={"total_revenue_keur": 115000.0, "project_irr": 0.089, "equity_irr": 0.106, "avg_dscr": 1.24},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )

    result = compare_scenarios(user_id, left.scenario_id, right.scenario_id)
    assert result is not None
    assert result["left"].scenario_name == "Base Snapshot"
    assert result["right"].scenario_name == "Downside Snapshot"
    metrics = {row["metric"] for row in result["metrics"]}
    assert {"Revenue", "OPEX", "EBITDA", "Senior Debt", "SHL", "DSCR", "Project IRR", "Equity IRR", "CAPEX", "Distributions"} <= metrics


def test_scenario_history_and_lineage_exist(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "oborovo", "Oborovo Solar PV", "oborovo")
    original = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Original",
        project_code="oborovo",
        source_project_template="oborovo",
        snapshot={"active_project": "oborovo"},
    )
    copy = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Copy",
        project_code="oborovo",
        source_project_template="oborovo",
        snapshot={"active_project": "oborovo"},
        copied_from_scenario_id=original.scenario_id,
    )

    history = get_scenario_history(user_id, project.project_id)
    assert len(history) >= 2
    assert any(item.copied_from_scenario_id == original.scenario_id for item in history)
    assert any(item.scenario_name == "Original" for item in history)
    assert any(item.scenario_name == "Copy" for item in history)


def test_export_lineage_exists(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Reviewed Case",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    record_export(
        user_id=user_id,
        project_code="tuho",
        export_type="institutional_workbook",
        artifact_name="review-pack.xlsx",
        project_id=project.project_id,
        scenario_id=scenario.scenario_id,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )

    lineage = build_export_lineage(user_id, project.project_id)
    assert lineage
    assert lineage[0]["scenario_name"] == "Reviewed Case"
    assert lineage[0]["governance_state"]["g20_status"] == "BLOCKED"


def test_compare_templates_routes_and_reports_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_web_path = os.path.join(base, "main_web.py")
    base_template_path = os.path.join(base, "app", "templates", "base.html")
    workspace_path = os.path.join(base, "app", "templates", "partials", "scenario_workspace.html")
    compare_partial_path = os.path.join(base, "app", "templates", "partials", "scenario_compare.html")
    docs_path = os.path.join(base, "docs", "phase12_scenario_compare_and_history_workflow.md")
    report_one = os.path.join(base, "reports", "phase12_scenario_compare_matrix.csv")
    report_two = os.path.join(base, "reports", "phase12_scenario_history_map.csv")
    report_three = os.path.join(base, "reports", "phase12_export_lineage_map.csv")

    main_web = open(main_web_path, encoding="utf-8").read()
    base_template = open(base_template_path, encoding="utf-8").read()
    workspace = open(workspace_path, encoding="utf-8").read()
    compare_partial = open(compare_partial_path, encoding="utf-8").read()
    docs = open(docs_path, encoding="utf-8").read()

    assert '/scenarios/history' in main_web
    assert '/scenarios/compare' in main_web
    assert 'compare_scenarios(' in main_web
    assert 'build_export_lineage(' in main_web
    assert 'Compare Scenarios' in base_template
    assert 'Scenario Cards' in workspace
    assert 'Scenario History' in workspace
    assert 'Export Lineage' in workspace
    assert 'Compare Scenarios' in workspace
    assert 'governance posture' in compare_partial.lower()
    assert 'G20 remains `BLOCKED`' in docs
    assert 'R99/R102 remains `NOT APPROVED`' in docs
    assert os.path.exists(report_one)
    assert os.path.exists(report_two)
    assert os.path.exists(report_three)
