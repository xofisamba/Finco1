"""Phase 13B editable-grid UX tests."""

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
    get_workspace_state,
    record_workspace_runtime,
    runtime_guard_for_snapshot,
    save_project,
    save_scenario,
    save_workspace_state,
)


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase13_ux_{uuid.uuid4().hex[:8]}.db")
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


def test_runtime_blocking_and_saved_boundary_stay_separate(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Reviewed Base",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho", "tariff_eur_mwh": "72"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    state = bind_workspace_to_scenario(user_id, project.project_id, "tuho", scenario)
    edited_snapshot = dict(state.saved_snapshot)
    edited_snapshot["tariff_eur_mwh"] = "88"
    state = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="tuho",
        active_scenario_id=state.active_scenario_id,
        active_scenario_name=state.active_scenario_name,
        draft_snapshot=edited_snapshot,
        saved_snapshot=state.saved_snapshot,
        dirty=True,
        governance_state=state.governance_state,
    )

    allowed, runtime_origin, message = runtime_guard_for_snapshot(state, edited_snapshot)
    assert allowed is False
    assert runtime_origin == "preview_only"
    assert "Unsaved edits" in message
    assert state.saved_snapshot["tariff_eur_mwh"] == "72"
    assert state.draft_snapshot["tariff_eur_mwh"] == "88"


def test_runtime_snapshot_remains_authoritative_after_later_grid_edits(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "oborovo", "Oborovo Solar PV", "oborovo")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Oborovo Base",
        project_code="oborovo",
        source_project_template="oborovo",
        snapshot={"active_project": "oborovo", "scenario": "Base", "opex_y1_keur": "1250"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    state = bind_workspace_to_scenario(user_id, project.project_id, "oborovo", scenario)
    recorded = record_workspace_runtime(
        user_id=user_id,
        project_id=project.project_id,
        project_code="oborovo",
        runtime_snapshot=dict(state.saved_snapshot),
        runtime_summary={"project_irr": 0.099, "avg_dscr": 1.29},
        runtime_snapshot_id="ux-runtime-001",
        runtime_origin="saved_state",
        governance_state=state.governance_state,
        active_scenario_id=scenario.scenario_id,
        active_scenario_name=scenario.scenario_name,
    )

    later_draft = dict(recorded.saved_snapshot)
    later_draft["opex_y1_keur"] = "1390"
    save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="oborovo",
        active_scenario_id=recorded.active_scenario_id,
        active_scenario_name=recorded.active_scenario_name,
        draft_snapshot=later_draft,
        saved_snapshot=recorded.saved_snapshot,
        dirty=True,
        governance_state=recorded.governance_state,
        last_runtime_snapshot=recorded.last_runtime_snapshot,
        last_runtime_summary=recorded.last_runtime_summary,
        last_runtime_snapshot_id=recorded.last_runtime_snapshot_id,
        last_runtime_origin=recorded.last_runtime_origin,
        last_runtime_scenario_id=recorded.last_runtime_scenario_id,
        last_runtime_at=recorded.last_runtime_at,
    )

    reloaded = get_workspace_state(user_id, project.project_id)
    assert reloaded is not None
    assert reloaded.last_runtime_snapshot["opex_y1_keur"] == "1250"
    assert reloaded.draft_snapshot["opex_y1_keur"] == "1390"
    assert reloaded.last_runtime_origin == "saved_state"


def test_templates_docs_reports_and_js_preserve_runtime_authority():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_web = open(os.path.join(base, "main_web.py"), encoding="utf-8").read()
    repository_py = open(os.path.join(base, "app", "persistence", "repository.py"), encoding="utf-8").read()
    index_html = open(os.path.join(base, "app", "templates", "index.html"), encoding="utf-8").read()
    workspace_shell = open(os.path.join(base, "app", "templates", "partials", "workspace_shell.html"), encoding="utf-8").read()
    revenue_html = open(os.path.join(base, "app", "templates", "partials", "sheet_revenue.html"), encoding="utf-8").read()
    opex_html = open(os.path.join(base, "app", "templates", "partials", "sheet_opex.html"), encoding="utf-8").read()
    debt_html = open(os.path.join(base, "app", "templates", "partials", "sheet_senior_debt.html"), encoding="utf-8").read()
    app_js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read()
    docs = open(os.path.join(base, "docs", "phase13_editable_grid_ux.md"), encoding="utf-8").read()

    assert 'id="btn-run-model"' in index_html
    assert 'id="btn-compare-draft"' in index_html
    assert "Revert Draft" in index_html
    assert "workspace-unsaved-banner" in workspace_shell
    assert "workspace-strip-runtime-origin" in workspace_shell
    assert "Editable draft assumptions" in revenue_html
    assert "data-grid-source=\"tariff_eur_mwh\"" in revenue_html
    assert "data-grid-source=\"opex_y1_keur\"" in opex_html
    assert "data-grid-source=\"target_dscr\"" in debt_html
    assert "btn-run-model" in app_js
    assert "btn-compare-draft" in app_js
    assert "/scenarios/state/draft" in app_js
    assert "data-grid-source" in app_js
    assert "runtime_guard_for_snapshot" in main_web
    assert '"/save-run"' in main_web
    assert "Unsaved edits are active" in repository_py
    assert "browser does not calculate debt service".lower() in debt_html.lower()
    assert "move calculations into the browser" in docs
    assert "- `G20` remains `BLOCKED`" in docs
    assert "- `R99/R102` remain `NOT APPROVED`" in docs

    for report_name in (
        "phase13_editable_grid_surface_map.csv",
        "phase13_draft_vs_runtime_boundary.csv",
        "phase13_grid_state_transition_matrix.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))


def test_frontend_does_not_become_runtime_authority():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read().lower()
    forbidden_markers = [
        "xirr(",
        "project_irr =",
        "equity_irr =",
        "avg_dscr =",
        "min_dscr =",
        "senior_debt_keur =",
    ]
    for marker in forbidden_markers:
        assert marker not in app_js
