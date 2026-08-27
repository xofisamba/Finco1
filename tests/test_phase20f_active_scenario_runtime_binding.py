import os
import sys
import uuid

import pytest
try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    TestClient = None

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
from app.auth import COOKIE_NAME, create_session_token
from app.input_adapter import build_projectinputs_from_snapshot
from app.persistence.repository import (
    add_scenario,
    bind_workspace_to_scenario,
    create_project_record,
    get_workspace_state,
    list_exports,
    resolve_active_scenario_runtime_snapshot,
    save_workspace_state,
    seed_scenarios_if_needed,
    select_scenario,
)


@pytest.fixture
def isolated_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase20f_{uuid.uuid4().hex[:8]}.db")
    os.environ["FINCO_DB_PATH"] = db_file
    db_mod.DB_PATH = db_file
    db_mod._connection = None

    yield db_file

    db_mod._connection = None
    if old_path:
        os.environ["FINCO_DB_PATH"] = old_path
        db_mod.DB_PATH = old_path
    else:
        os.environ.pop("FINCO_DB_PATH", None)


@pytest.fixture
def client(isolated_db):
    if TestClient is None:
        pytest.skip("FastAPI/TestClient not installed in this environment")
    import main_web

    tc = TestClient(main_web.app)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _snapshot(**overrides):
    data = {
        "active_project": "pilot-wind",
        "project_name": "Pilot Wind",
        "project_type": "Wind",
        "project_origin": "user_created",
        "template_source": "generic_wind",
        "country_market": "Croatia",
        "scenario": "Base",
        "capacity_mw": "50",
        "cod_date": "2027-01-01",
        "construction_months": "12",
        "horizon_years": "25",
        "tariff_eur_mwh": "60",
        "ppa_term_years": "15",
        "p50_hours": "1200",
        "opex_y1_keur": "1000",
        "total_capex_keur": "50000",
        "gearing_pct": "70",
        "interest_rate_pct": "5",
        "tenor_years": "15",
        "target_dscr": "1.30",
        "capacity_factor": "",
    }
    data.update(overrides)
    return data


def _setup_project_with_scenarios(user_id: str):
    governance = {"g20_status": "BLOCKED", "r99_r102_status": "NOT_APPROVED", "lender_ready": False}
    baseline = _snapshot()
    project = create_project_record(
        user_id=user_id,
        project_code="pilot-wind",
        project_name="Pilot Wind",
        project_type="Wind",
        project_origin="user_created",
        template_source="generic_wind",
        baseline_snapshot=baseline,
        governance_state=governance,
    )
    base_case = seed_scenarios_if_needed(
        user_id=user_id,
        project_id=project.project_id,
        project_code=project.project_code,
        project_type=project.project_type,
        source_project_template=project.template_source,
        baseline_snapshot=baseline,
        governance_state=governance,
        template_origin="generic_wind",
    )
    high_tariff = add_scenario(
        user_id=user_id,
        project_id=project.project_id,
        project_code=project.project_code,
        scenario_name="High Tariff",
        parent_scenario_id=base_case.scenario_id,
        base_input_set=base_case.base_input_set,
        overrides={"tariff_eur_mwh": "85"},
        governance_state=governance,
        replay_metadata={"phase": "20f"},
    )
    return project, base_case, high_tariff, baseline


def _run_revenue(snapshot):
    result = run_project(
        "Wind",
        snapshot.get("scenario", "Base"),
        project_inputs_override=build_projectinputs_from_snapshot(snapshot),
    )
    return result["kpis"]["total_revenue_keur"]


def test_resolve_active_scenario_runtime_snapshot_handles_base_and_overrides(isolated_db):
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    project, base_case, high_tariff, baseline = _setup_project_with_scenarios(user_id)

    base_record, base_snapshot, base_warning = resolve_active_scenario_runtime_snapshot(
        user_id,
        project.project_id,
        base_case.scenario_id,
    )
    high_record, high_snapshot, high_warning = resolve_active_scenario_runtime_snapshot(
        user_id,
        project.project_id,
        high_tariff.scenario_id,
    )

    assert base_record.scenario_id == base_case.scenario_id
    assert base_snapshot["tariff_eur_mwh"] == baseline["tariff_eur_mwh"]
    assert base_warning is None

    assert high_record.scenario_id == high_tariff.scenario_id
    assert high_snapshot["tariff_eur_mwh"] == "85"
    assert high_snapshot["capacity_mw"] == baseline["capacity_mw"]
    assert high_warning is None
    assert _run_revenue(high_snapshot) > _run_revenue(base_snapshot)


def test_run_route_uses_selected_saved_active_scenario_not_workspace_saved_snapshot(client):
    user_id = "1"
    project, base_case, high_tariff, baseline = _setup_project_with_scenarios(user_id)

    bind_workspace_to_scenario(
        user_id,
        project.project_id,
        project.project_code,
        base_case,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT_APPROVED"},
    )
    assert select_scenario(user_id, project.project_id, high_tariff.scenario_id) is True

    response = client.post("/run", data=baseline)
    assert response.status_code == 200

    workspace = get_workspace_state(user_id, project.project_id)
    assert workspace is not None
    assert workspace.saved_snapshot["tariff_eur_mwh"] == "60"
    assert workspace.last_runtime_scenario_id == high_tariff.scenario_id
    assert workspace.last_runtime_summary["total_revenue_keur"] > _run_revenue(baseline)


def test_run_route_blocks_dirty_draft_and_never_promotes_browser_state(client):
    user_id = "1"
    project, base_case, _, baseline = _setup_project_with_scenarios(user_id)

    dirty_snapshot = dict(baseline)
    dirty_snapshot["tariff_eur_mwh"] = "999"
    save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code=project.project_code,
        active_scenario_id=base_case.scenario_id,
        active_scenario_name=base_case.scenario_name,
        draft_snapshot=dirty_snapshot,
        saved_snapshot=baseline,
        dirty=True,
    )

    response = client.post("/run", data=dirty_snapshot)
    assert response.status_code == 200
    assert "Unsaved edits are active" in response.text


def test_invalid_active_scenario_id_falls_back_cleanly_with_warning(client):
    user_id = "1"
    project, base_case, _, baseline = _setup_project_with_scenarios(user_id)

    save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code=project.project_code,
        active_scenario_id="missing-scenario",
        active_scenario_name="Missing Scenario",
        draft_snapshot=baseline,
        saved_snapshot=baseline,
        dirty=False,
    )

    response = client.post("/run", data=baseline)
    assert response.status_code == 200
    assert "Selected saved scenario was unavailable" in response.text

    workspace = get_workspace_state(user_id, project.project_id)
    assert workspace.last_runtime_scenario_id is None
    assert workspace.last_runtime_summary["total_revenue_keur"] == _run_revenue(baseline)


def test_export_provenance_records_active_scenario_fields(client, monkeypatch):
    import main_web

    user_id = "1"
    project, base_case, high_tariff, baseline = _setup_project_with_scenarios(user_id)

    bind_workspace_to_scenario(
        user_id,
        project.project_id,
        project.project_code,
        base_case,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT_APPROVED"},
    )
    select_scenario(user_id, project.project_id, high_tariff.scenario_id)
    monkeypatch.setattr(main_web, "build_excel_export", lambda **kwargs: b"phase20f-xlsx")

    response = client.post("/download", data=baseline)
    assert response.status_code == 200
    exports = list_exports(user_id, project_id=project.project_id, limit=5)
    assert exports
    replay = exports[0].replay_metadata

    assert replay["active_scenario_id"] == high_tariff.scenario_id
    assert replay["active_scenario_name"] == "High Tariff"
    assert replay["scenario_id"] == high_tariff.scenario_id
    assert replay["scenario_name"] == "High Tariff"
    assert replay["is_base_case"] is False
    assert replay["parent_scenario_id"] == base_case.scenario_id
    assert replay["override_field_list"] == ["tariff_eur_mwh"]
    assert replay["baseline_source"] is False
    assert replay["template_origin"] == "project_factory:generic_wind"


def test_base_case_provenance_has_empty_override_field_list(client, monkeypatch):
    import main_web

    user_id = "1"
    project, base_case, _, baseline = _setup_project_with_scenarios(user_id)
    bind_workspace_to_scenario(
        user_id,
        project.project_id,
        project.project_code,
        base_case,
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT_APPROVED"},
    )
    monkeypatch.setattr(main_web, "build_excel_export", lambda **kwargs: b"phase20f-xlsx")

    response = client.post("/download", data=baseline)
    assert response.status_code == 200
    replay = list_exports(user_id, project_id=project.project_id, limit=1)[0].replay_metadata
    assert replay["active_scenario_id"] == base_case.scenario_id
    assert replay["is_base_case"] is True
    assert replay["override_field_list"] == []


def test_phase20f_docs_and_ui_copy_keep_guardrails():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tab_html = open(os.path.join(base_dir, "app", "templates", "partials", "scenario_tab.html"), encoding="utf-8").read()

    assert "Run Model will use" in tab_html
    assert "Unsaved draft edits do not affect Run until saved" in tab_html
