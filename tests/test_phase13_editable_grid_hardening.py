"""Phase 13C editable-grid hardening tests."""

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
)


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase13_hardening_{uuid.uuid4().hex[:8]}.db")
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


def test_repeated_draft_edits_and_revert_remain_deterministic(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "tuho", "TUHO Wind 1", "tuho")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="TUHO Base",
        project_code="tuho",
        source_project_template="tuho",
        snapshot={"active_project": "tuho", "scenario": "Base", "tariff_eur_mwh": "72", "opex_y1_keur": "1100"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    state = bind_workspace_to_scenario(user_id, project.project_id, "tuho", scenario)

    first_edit = dict(state.saved_snapshot)
    first_edit["tariff_eur_mwh"] = "81"
    state = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="tuho",
        active_scenario_id=state.active_scenario_id,
        active_scenario_name=state.active_scenario_name,
        draft_snapshot=first_edit,
        saved_snapshot=state.saved_snapshot,
        dirty=True,
        governance_state=state.governance_state,
    )
    second_edit = dict(first_edit)
    second_edit["opex_y1_keur"] = "1290"
    state = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="tuho",
        active_scenario_id=state.active_scenario_id,
        active_scenario_name=state.active_scenario_name,
        draft_snapshot=second_edit,
        saved_snapshot=state.saved_snapshot,
        dirty=True,
        governance_state=state.governance_state,
    )

    assert state.dirty is True
    reverted = discard_workspace_draft(user_id, project.project_id)
    assert reverted is not None
    assert reverted.dirty is False
    assert reverted.draft_snapshot == reverted.saved_snapshot
    assert reverted.saved_snapshot["tariff_eur_mwh"] == "72"
    assert reverted.saved_snapshot["opex_y1_keur"] == "1100"


def test_runtime_guard_and_last_runtime_boundary_survive_later_drafts(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    project = save_project(user_id, "oborovo", "Oborovo Solar PV", "oborovo")
    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Oborovo Saved",
        project_code="oborovo",
        source_project_template="oborovo",
        snapshot={"active_project": "oborovo", "scenario": "Base", "gearing_pct": "70"},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )
    state = bind_workspace_to_scenario(user_id, project.project_id, "oborovo", scenario)
    state = record_workspace_runtime(
        user_id=user_id,
        project_id=project.project_id,
        project_code="oborovo",
        runtime_snapshot=dict(state.saved_snapshot),
        runtime_summary={"avg_dscr": 1.27},
        runtime_snapshot_id="hardening-runtime-001",
        runtime_origin="saved_state",
        governance_state=state.governance_state,
        active_scenario_id=scenario.scenario_id,
        active_scenario_name=scenario.scenario_name,
    )
    later_draft = dict(state.saved_snapshot)
    later_draft["gearing_pct"] = "74"
    state = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code="oborovo",
        active_scenario_id=state.active_scenario_id,
        active_scenario_name=state.active_scenario_name,
        draft_snapshot=later_draft,
        saved_snapshot=state.saved_snapshot,
        dirty=True,
        governance_state=state.governance_state,
        last_runtime_snapshot=state.last_runtime_snapshot,
        last_runtime_summary=state.last_runtime_summary,
        last_runtime_snapshot_id=state.last_runtime_snapshot_id,
        last_runtime_origin=state.last_runtime_origin,
        last_runtime_scenario_id=state.last_runtime_scenario_id,
        last_runtime_at=state.last_runtime_at,
    )

    allowed, runtime_origin, message = runtime_guard_for_snapshot(state, later_draft)
    assert allowed is False
    assert runtime_origin == "preview_only"
    assert "Unsaved edits" in message
    assert state.last_runtime_snapshot["gearing_pct"] == "70"
    assert state.draft_snapshot["gearing_pct"] == "74"


def test_htmx_rebinding_and_runtime_action_disable_hooks_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read()
    index_html = open(os.path.join(base, "app", "templates", "index.html"), encoding="utf-8").read()
    shell_html = open(os.path.join(base, "app", "templates", "partials", "workspace_shell.html"), encoding="utf-8").read()
    scenario_workspace = open(os.path.join(base, "app", "templates", "partials", "scenario_workspace.html"), encoding="utf-8").read()
    main_web = open(os.path.join(base, "main_web.py"), encoding="utf-8").read()

    assert "bindDraftPersistenceFields" in app_js
    assert "bindEditableGridInputs" in app_js
    assert "htmx:afterSwap" in app_js
    assert "setButtonDisabledState" in app_js
    assert "btn-save-run" in app_js
    assert 'id="btn-save-run"' in index_html
    assert 'role="status"' in shell_html
    assert 'aria-live="polite"' in shell_html
    assert "last clean snapshot" in shell_html.lower()
    assert "most recent clean snapshot" in scenario_workspace.lower()
    assert "older than current draft" in main_web


def test_no_new_runtime_surfaces_or_frontend_financial_calculations():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read().lower()
    tax_html = open(os.path.join(base, "app", "templates", "partials", "sheet_tax.html"), encoding="utf-8").read()
    shl_html = open(os.path.join(base, "app", "templates", "partials", "sheet_shl.html"), encoding="utf-8").read()

    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "min_dscr =", "ebitda ="):
        assert marker not in app_js
    assert "editable-grid-shell" not in tax_html
    assert "editable-grid-shell" not in shl_html


def test_docs_reports_and_governance_posture_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = open(os.path.join(base, "docs", "phase13_editable_grid_hardening.md"), encoding="utf-8").read()
    assert "Phase 13C" in docs
    assert "`G20` remains `BLOCKED`" in docs
    assert "`R99/R102` remain `NOT APPROVED`" in docs

    for report_name in (
        "phase13_editable_grid_hardening_matrix.csv",
        "phase13_htmx_refresh_state_matrix.csv",
        "phase13_runtime_snapshot_guard_matrix.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))
