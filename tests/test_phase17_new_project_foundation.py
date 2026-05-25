from __future__ import annotations

import os
import sys
import types
import uuid

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if "bcrypt" not in sys.modules:
    sys.modules["bcrypt"] = types.SimpleNamespace(
        gensalt=lambda rounds=12: b"salt",
        hashpw=lambda password, salt: b"stub-hash",
        checkpw=lambda password, hashed: True,
    )

from app.auth import create_session_token
from app.persistence.repository import (
    count_runs,
    create_project_record,
    get_project_by_code,
    get_workspace_state,
    list_project_records,
    list_scenarios,
)


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase17_project_{uuid.uuid4().hex[:8]}.db")
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


@pytest.fixture
def auth_client(test_db):
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient
    from main_web import app

    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("finco_session", create_session_token(user_id=f"u{uuid.uuid4().hex[:8]}", username="phase17"))
    return client


def _user_id(client) -> str:
    from app.auth import decode_session_token

    token = client.cookies.get("finco_session")
    session = decode_session_token(token)
    assert session is not None
    return session.user_id


def _valid_new_project_payload(**overrides):
    payload = {
        "project_name": "North Wind",
        "project_type": "Wind",
        "template_source": "generic_wind",
        "country_market": "Croatia",
        "capacity_mw": "50",
        "cod_date": "2030-06-30",
        "construction_months": "18",
        "horizon_years": "30",
        "tariff_eur_mwh": "85",
        "ppa_term_years": "12",
        "p50_hours": "3200",
        "opex_y1_keur": "2100",
        "total_capex_keur": "65000",
        "gearing_pct": "70",
        "interest_rate_pct": "6.5",
        "tenor_years": "15",
        "target_dscr": "1.20",
    }
    payload.update(overrides)
    return payload


def test_project_record_table_and_crud_exist(test_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    record = create_project_record(
        user_id=user_id,
        project_code="north-wind",
        project_name="North Wind",
        project_type="Wind",
        project_origin="user_created",
        template_source="generic_wind",
        baseline_snapshot={"active_project": "north-wind", "project_type": "Wind", "scenario": "Base"},
    )

    assert record.project_id
    assert record.project_origin == "user_created"
    assert record.project_type == "Wind"
    assert record.template_source == "generic_wind"
    assert record.baseline_snapshot["active_project"] == "north-wind"

    projects = list_project_records(user_id=user_id)
    assert any(item.project_code == "north-wind" for item in projects)


def test_new_project_route_validates_required_fields(auth_client):
    # Empty project_name triggers FastAPI Form validation → 422 + JSON error
    blank = auth_client.post(
        "/projects/create",
        data=_valid_new_project_payload(project_name=""),
    )
    assert blank.status_code == 422
    assert "Field required" in blank.text or "project_name" in blank.text

    # Whitespace-only name triggers application validation → 400 + rendered form
    blank_ws = auth_client.post(
        "/projects/create",
        data=_valid_new_project_payload(project_name="   "),
    )
    assert blank_ws.status_code == 400
    assert "Project name is required." in blank_ws.text

    invalid = auth_client.post(
        "/projects/create",
        data=_valid_new_project_payload(project_name="Bad Project", project_type="Hydro"),
    )
    assert invalid.status_code == 400
    assert "Project type must be one of" in invalid.text


def test_new_project_route_creates_user_project_and_selector_entry(auth_client):
    user_id = _user_id(auth_client)
    response = auth_client.post(
        "/projects/create",
        data=_valid_new_project_payload(),
    )
    assert response.status_code == 200
    assert "Created project" in response.text
    assert "North Wind" in response.text

    project = get_project_by_code(user_id, "north-wind")
    assert project is not None
    assert project.project_origin == "user_created"
    assert project.project_type == "Wind"
    assert project.baseline_snapshot
    assert project.baseline_snapshot["country_market"] == "Croatia"
    assert project.baseline_snapshot["capacity_mw"] == "50"
    assert project.baseline_snapshot["tariff_eur_mwh"] == "85"
    assert project.baseline_snapshot["target_dscr"] == "1.20"

    index = auth_client.get("/?project=north-wind")
    assert index.status_code == 200
    assert "User-Created Projects" in index.text
    assert "North Wind" in index.text
    assert "Factory Templates" in index.text
    assert "TUHO Wind 1" in index.text
    assert "Oborovo Solar PV" in index.text
    assert 'value="north-wind"' in index.text
    assert 'name="country_market"' in index.text
    assert 'value="Croatia"' in index.text
    assert 'value="85"' in index.text
    assert 'value="50"' in index.text
    assert "template-seeded defaults until Phase 17C" in index.text


def test_selecting_user_project_binds_workspace_and_preserves_save_run_boundaries(auth_client):
    user_id = _user_id(auth_client)
    auth_client.post(
        "/projects/create",
        data=_valid_new_project_payload(
            project_name="South Solar",
            project_type="Solar",
            template_source="generic_solar",
            capacity_mw="65",
            tariff_eur_mwh="92",
            p50_hours="1750",
            opex_y1_keur="2400",
            total_capex_keur="72000",
            gearing_pct="68",
            interest_rate_pct="5.9",
            tenor_years="17",
            target_dscr="1.25",
        ),
    )
    project = get_project_by_code(user_id, "south-solar")
    assert project is not None

    page = auth_client.get("/?project=south-solar")
    assert page.status_code == 200
    assert "South Solar" in page.text
    assert 'value="65"' in page.text
    assert 'value="92"' in page.text
    assert 'value="Croatia"' in page.text

    workspace = get_workspace_state(user_id, project.project_id)
    assert workspace is not None
    assert workspace.project_code == "south-solar"
    assert workspace.draft_snapshot["active_project"] == "south-solar"
    assert workspace.draft_snapshot["project_type"] == "Solar"
    assert workspace.draft_snapshot["capacity_mw"] == "65"
    assert workspace.draft_snapshot["tariff_eur_mwh"] == "92"
    assert workspace.draft_snapshot["country_market"] == "Croatia"

    save_response = auth_client.post(
        "/scenarios/save",
        data={
            "active_project": "south-solar",
            "project_type": "Solar",
            "scenario": "Base",
            "capacity_mw": "50",
        },
    )
    assert save_response.status_code == 200
    assert count_runs(user_id) == 0

    saved_scenarios = list_scenarios(user_id, project_id=project.project_id)
    assert len(saved_scenarios) == 1
    workspace_after_save = get_workspace_state(user_id, project.project_id)
    assert workspace_after_save is not None
    assert workspace_after_save.last_runtime_snapshot_id in (None, "")

    run_response = auth_client.post(
        "/run",
        data={
            "active_project": "south-solar",
            "project_type": "Solar",
            "scenario": "Base",
            "capacity_mw": "50",
            "tariff_eur_mwh": "55",
        },
    )
    assert run_response.status_code == 200
    assert len(list_scenarios(user_id, project_id=project.project_id)) == 1


def test_docs_and_reports_capture_phase17a_scope_and_guardrails():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = open(os.path.join(base, "docs", "phase17_new_project_foundation.md"), encoding="utf-8").read()
    schema = open(os.path.join(base, "reports", "phase17_project_record_schema.csv"), encoding="utf-8").read()
    workflow = open(os.path.join(base, "reports", "phase17_new_project_workflow_matrix.csv"), encoding="utf-8").read()
    gaps = open(os.path.join(base, "reports", "phase17_new_project_remaining_gaps.csv"), encoding="utf-8").read()
    js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read().lower()

    assert "Phase 17A creates project records and selector workflow" in docs
    assert "does not yet implement full from-scratch runtime" in docs
    assert "Phase 17B adds required 13-field form" in docs
    assert "Phase 17C adds build_projectinputs_from_scratch" in docs
    assert "TUHO/Oborovo remain templates" in docs
    assert "G20 remains BLOCKED" in docs
    assert "R99/R102 remains NOT APPROVED" in docs

    assert "project_origin" in schema
    assert "baseline_snapshot" in schema
    assert "user_created_project_visible_in_selector" in workflow
    assert "template_seeded_runtime_disclosure" in workflow
    assert "phase17c_from_scratch_runtime_path" in gaps

    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "debt service ="):
        assert marker not in js
