"""Phase 12 persistence and saved-scenarios foundation tests."""

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
    archive_scenario,
    duplicate_scenario,
    get_project_by_code,
    get_scenario,
    list_exports,
    list_scenarios,
    record_export,
    rename_scenario,
    save_project,
    save_scenario,
)


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase12_test_{uuid.uuid4().hex[:8]}.db")
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


def test_project_and_scenario_persistence_structures_exist(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(
        user_id=user_id,
        project_code="tuho",
        project_name="TUHO Wind 1",
        source_project_template="tuho",
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
        last_run_summary={"project_irr": 0.094},
    )
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="TUHO Base Snapshot",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho", "scenario": "Base", "capacity_mw": "35"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
        last_run_summary={"equity_irr": 0.113},
    )

    assert project.project_id
    assert scenario.scenario_id
    assert scenario.snapshot["active_project"] == "tuho"
    assert scenario.governance_state["g20_status"] == "BLOCKED"


def test_save_load_duplicate_and_archive_workflow_exists(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "oborovo", "Oborovo Solar PV", "oborovo")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Oborovo Base",
        project_code="oborovo",
        source_project_template="oborovo",
        snapshot={"active_project": "oborovo", "scenario": "Base"},
    )

    duplicate = duplicate_scenario(user_id, scenario.scenario_id)
    assert duplicate is not None
    assert duplicate.copied_from_scenario_id == scenario.scenario_id

    assert archive_scenario(user_id, scenario.scenario_id) is True
    archived = get_scenario(scenario.scenario_id, user_id)
    assert archived is not None
    assert archived.archived is True

    visible = list_scenarios(user_id, project_id=project.project_id, include_archived=False)
    assert all(item.scenario_id != scenario.scenario_id for item in visible)


def test_rename_workflow_exists(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Old Name",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho", "scenario": "Base"},
    )

    assert rename_scenario(user_id, scenario.scenario_id, "New Name") is True
    renamed = get_scenario(scenario.scenario_id, user_id)
    assert renamed is not None
    assert renamed.scenario_name == "New Name"


def test_export_history_and_governance_snapshots_exist(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="TUHO Review Snapshot",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho", "scenario": "Base"},
    )

    export = record_export(
        user_id=user_id,
        project_code="tuho",
        export_type="institutional_workbook",
        artifact_name="phase10_tuho_institutional_workbook_skeleton.xlsx",
        project_id=project.project_id,
        scenario_id=scenario.scenario_id,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )

    history = list_exports(user_id, project_id=project.project_id)
    assert export.export_id
    assert history
    assert history[0].governance_state["g20_status"] == "BLOCKED"


def test_tuho_and_oborovo_template_integration_exists(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    save_project(user_id, "oborovo", "Oborovo Solar PV", "oborovo")

    assert get_project_by_code(user_id, "tuho") is not None
    assert get_project_by_code(user_id, "oborovo") is not None


def test_workspace_templates_and_routes_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_web_path = os.path.join(base, "main_web.py")
    base_template_path = os.path.join(base, "app", "templates", "base.html")
    index_template_path = os.path.join(base, "app", "templates", "index.html")
    scenario_workspace_path = os.path.join(base, "app", "templates", "partials", "scenario_workspace.html")
    load_partial_path = os.path.join(base, "app", "templates", "partials", "scenario_load_result.html")
    app_js_path = os.path.join(base, "static", "app.js")

    main_web = open(main_web_path, encoding="utf-8").read()
    base_template = open(base_template_path, encoding="utf-8").read()
    index_template = open(index_template_path, encoding="utf-8").read()
    scenario_workspace = open(scenario_workspace_path, encoding="utf-8").read()
    load_partial = open(load_partial_path, encoding="utf-8").read()
    app_js = open(app_js_path, encoding="utf-8").read()

    assert '/scenarios/save' in main_web
    assert '/scenarios/{scenario_id}/load' in main_web
    assert '/scenarios/{scenario_id}/duplicate' in main_web
    assert '/scenarios/{scenario_id}/rename' in main_web
    assert '/scenarios/{scenario_id}/archive' in main_web
    assert 'record_export(' in main_web

    assert 'Save Scenario' in base_template
    assert 'Refresh Saved' in base_template
    assert 'saved-scenario-panel' in base_template
    assert 'current_saved_scenario_id' in index_template

    assert 'Saved Scenarios' in scenario_workspace
    assert 'Scenario Cards' in scenario_workspace
    assert 'Export Lineage' in scenario_workspace
    assert 'Load' in scenario_workspace
    assert 'Duplicate' in scenario_workspace
    assert 'Archive' in scenario_workspace
    assert 'applyScenarioSnapshot' in load_partial
    assert 'window.applyScenarioSnapshot' in app_js


def test_runtime_summary_export_records_traceability(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="TUHO Runtime Snapshot",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho", "scenario": "Base"},
    )
    record_export(
        user_id=user_id,
        project_code="tuho",
        export_type="runtime_summary_csv",
        artifact_name="phase10_tuho_runtime_summary.csv",
        artifact_path="/exports/runtime-summary.csv?project=tuho",
        project_id=project.project_id,
        scenario_id=scenario.scenario_id,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )

    exports = list_exports(user_id)
    assert any(item.export_type == "runtime_summary_csv" for item in exports)


def test_phase12_reports_and_doc_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.exists(os.path.join(base, "docs", "phase12_persistence_and_saved_scenarios_foundation.md"))
    assert os.path.exists(os.path.join(base, "reports", "phase12_persistence_model_map.csv"))
    assert os.path.exists(os.path.join(base, "reports", "phase12_scenario_workflow_map.csv"))
    assert os.path.exists(os.path.join(base, "reports", "phase12_export_traceability_map.csv"))
