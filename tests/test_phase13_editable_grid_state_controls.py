"""Phase 13A editable-grid state control foundation tests."""

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
    bind_workspace_to_scenario,
    discard_workspace_draft,
    get_workspace_state,
    record_workspace_runtime,
    runtime_guard_for_snapshot,
    save_project,
    save_scenario,
    save_workspace_state,
    snapshots_equal,
)


def _default_workspace_snapshot(project_code: str) -> dict[str, str]:
    code = (project_code or "tuho").strip().lower()
    return {
        "active_project": code,
        "project_type": "Solar" if code == "oborovo" else "Wind",
        "scenario": "Base",
        "capacity_mw": "",
        "tariff_eur_mwh": "",
        "p50_hours": "",
        "total_capex_keur": "",
        "opex_y1_keur": "",
        "gearing_pct": "",
        "target_dscr": "",
        "interest_rate_pct": "",
        "tenor_years": "",
        "cod_date": "",
        "construction_months": "",
        "horizon_years": "",
        "capacity_factor": "",
        "ppa_term_years": "",
    }


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase13_state_{uuid.uuid4().hex[:8]}.db")
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


def test_dirty_state_lifecycle_and_discard_flow(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    base_snapshot = _default_workspace_snapshot("tuho")
    state = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="tuho",
        draft_snapshot=base_snapshot,
        saved_snapshot=base_snapshot,
        dirty=False,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )

    edited_snapshot = dict(base_snapshot)
    edited_snapshot["capacity_mw"] = "42"
    state = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="tuho",
        draft_snapshot=edited_snapshot,
        saved_snapshot=base_snapshot,
        dirty=not snapshots_equal(edited_snapshot, base_snapshot),
        governance_state=state.governance_state,
    )

    assert state.dirty is True
    discarded = discard_workspace_draft(user_id, project.project_id)
    assert discarded is not None
    assert discarded.dirty is False
    assert discarded.draft_snapshot == base_snapshot


def test_runtime_guard_blocks_stale_unsaved_edits(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "oborovo", "Oborovo Solar PV", "oborovo")
    base_snapshot = _default_workspace_snapshot("oborovo")
    edited_snapshot = dict(base_snapshot)
    edited_snapshot["tariff_eur_mwh"] = "92"
    state = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="oborovo",
        draft_snapshot=edited_snapshot,
        saved_snapshot=base_snapshot,
        dirty=True,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )

    allowed, runtime_origin, message = runtime_guard_for_snapshot(state, edited_snapshot)
    assert allowed is False
    assert runtime_origin == "preview_only"
    assert "Unsaved edits" in message


def test_runtime_snapshot_boundary_is_immutable(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Saved Boundary",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho", "scenario": "Base", "capacity_mw": "35"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    state = bind_workspace_to_scenario(user_id, project.project_id, "tuho", scenario)
    runtime_snapshot = dict(state.saved_snapshot)

    recorded = record_workspace_runtime(
        user_id=user_id,
        project_id=project.project_id,
        project_code="tuho",
        runtime_snapshot=runtime_snapshot,
        runtime_summary={"project_irr": 0.101, "avg_dscr": 1.31},
        runtime_snapshot_id="runtime-snap-001",
        runtime_origin="saved_state",
        governance_state=state.governance_state,
        active_scenario_id=scenario.scenario_id,
        active_scenario_name=scenario.scenario_name,
    )
    later_edit = dict(runtime_snapshot)
    later_edit["capacity_mw"] = "40"
    updated = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="tuho",
        active_scenario_id=scenario.scenario_id,
        active_scenario_name=scenario.scenario_name,
        draft_snapshot=later_edit,
        saved_snapshot=runtime_snapshot,
        dirty=True,
        governance_state=recorded.governance_state,
    )

    assert updated.last_runtime_snapshot == runtime_snapshot
    assert updated.last_runtime_snapshot != later_edit
    assert updated.last_runtime_origin == "saved_state"


def test_active_scenario_binding_and_persistence_consistency(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "oborovo", "Oborovo Solar PV", "oborovo")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Active Reviewed Case",
        project_code="oborovo",
        source_project_template="oborovo",
        snapshot={"active_project": "oborovo", "scenario": "Base"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    bind_workspace_to_scenario(user_id, project.project_id, "oborovo", scenario)

    state = get_workspace_state(user_id, project.project_id)
    assert state is not None
    assert state.active_scenario_id == scenario.scenario_id
    assert state.active_scenario_name == "Active Reviewed Case"
    assert state.dirty is False


def test_routes_docs_reports_and_governance_guards_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_web_path = os.path.join(base, "main_web.py")
    app_js_path = os.path.join(base, "static", "app.js")
    index_path = os.path.join(base, "app", "templates", "index.html")
    workspace_path = os.path.join(base, "app", "templates", "partials", "scenario_workspace.html")
    docs_path = os.path.join(base, "docs", "phase13_editable_grid_state_controls.md")
    report_one = os.path.join(base, "reports", "phase13_state_transition_matrix.csv")
    report_two = os.path.join(base, "reports", "phase13_stale_state_prevention_matrix.csv")
    report_three = os.path.join(base, "reports", "phase13_runtime_binding_semantics.csv")

    main_web = open(main_web_path, encoding="utf-8").read()
    app_js = open(app_js_path, encoding="utf-8").read()
    index_html = open(index_path, encoding="utf-8").read()
    workspace_html = open(workspace_path, encoding="utf-8").read()
    docs = open(docs_path, encoding="utf-8").read()

    assert "/scenarios/state/draft" in main_web
    assert "/scenarios/state/discard" in main_web
    assert "Unsaved edits" in main_web
    assert "record_workspace_runtime" in main_web
    assert "btn-discard-edits" in index_html
    assert "workspace_dirty_state" in index_html
    assert "Editable State" in workspace_html
    assert "Unsaved draft edits remain preview-only" in workspace_html
    assert "dirty-state" in docs.lower()
    assert "G20 remains `BLOCKED`" in docs
    assert "R99/R102 remain `NOT APPROVED`" in docs
    assert os.path.exists(report_one)
    assert os.path.exists(report_two)
    assert os.path.exists(report_three)
