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
from app.persistence.repository import get_project_by_code


@pytest.fixture
def test_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase17_required_{uuid.uuid4().hex[:8]}.db")
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
    client.cookies.set("finco_session", create_session_token(user_id=f"u{uuid.uuid4().hex[:8]}", username="phase17b"))
    return client


def _user_id(client) -> str:
    from app.auth import decode_session_token

    token = client.cookies.get("finco_session")
    session = decode_session_token(token)
    assert session is not None
    return session.user_id


def _payload(**overrides):
    payload = {
        "project_name": "Adriatic Wind",
        "project_type": "Wind",
        "template_source": "generic_wind",
        "country_market": "Croatia",
        "capacity_mw": "50",
        "cod_date": "2030-06-30",
        "construction_months": "18",
        "horizon_years": "30",
        "tariff_eur_mwh": "100",
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


def test_new_project_form_contains_all_required_fields(auth_client):
    response = auth_client.get("/projects/new")
    assert response.status_code == 200

    for field_name in (
        "project_name",
        "project_type",
        "template_source",
        "country_market",
        "capacity_mw",
        "cod_date",
        "construction_months",
        "horizon_years",
        "tariff_eur_mwh",
        "ppa_term_years",
        "p50_hours",
        "opex_y1_keur",
        "total_capex_keur",
        "gearing_pct",
        "interest_rate_pct",
        "tenor_years",
        "target_dscr",
    ):
        assert f'name="{field_name}"' in response.text


@pytest.mark.parametrize(
    ("override", "expected_error"),
    [
        ({"project_type": "Hydro"}, "Project type must be one of"),
        ({"project_name": ""}, "Project name is required."),
        ({"capacity_mw": "0"}, "Capacity (MW) must be > 0."),
        ({"tariff_eur_mwh": ""}, "Tariff (EUR/MWh) is required."),
        ({"tariff_eur_mwh": "abc"}, "Tariff (EUR/MWh) must be a number."),
        ({"p50_hours": "0"}, "P50 hours must be > 0."),
        ({"opex_y1_keur": ""}, "OPEX Y1 (kEUR) is required."),
        ({"opex_y1_keur": "-1"}, "OPEX Y1 (kEUR) must be >= 0."),
        ({"total_capex_keur": "0"}, "Total CAPEX (kEUR) must be > 0."),
        ({"gearing_pct": "110"}, "Gearing (%) must be <= 100."),
        ({"interest_rate_pct": "-1"}, "Interest rate (%) must be >= 0."),
        ({"tenor_years": "0"}, "Tenor (years) must be > 0."),
        ({"ppa_term_years": "0"}, "PPA term years must be > 0."),
        ({"horizon_years": "0"}, "Horizon years must be > 0."),
    ],
)
def test_new_project_route_validation_errors_are_visible(auth_client, override, expected_error):
    response = auth_client.post("/projects/create", data=_payload(**override))
    assert response.status_code == 400
    assert expected_error in response.text


def test_valid_new_project_post_creates_project_with_required_baseline_snapshot(auth_client):
    user_id = _user_id(auth_client)
    response = auth_client.post("/projects/create", data=_payload())
    assert response.status_code == 200
    assert "Created project" in response.text
    assert "Runtime is built from saved project assumptions" in response.text

    record = get_project_by_code(user_id, "adriatic-wind")
    assert record is not None
    assert record.project_origin == "user_created"
    assert record.template_source == "generic_wind"

    for key in (
        "active_project",
        "project_name",
        "project_type",
        "project_origin",
        "template_source",
        "country_market",
        "capacity_mw",
        "cod_date",
        "construction_months",
        "horizon_years",
        "tariff_eur_mwh",
        "ppa_term_years",
        "p50_hours",
        "opex_y1_keur",
        "total_capex_keur",
        "gearing_pct",
        "interest_rate_pct",
        "tenor_years",
        "target_dscr",
    ):
        assert key in record.baseline_snapshot

    assert record.baseline_snapshot["capacity_mw"] == "50"
    assert record.baseline_snapshot["tariff_eur_mwh"] == "100"
    assert record.baseline_snapshot["country_market"] == "Croatia"
    assert record.baseline_snapshot["project_origin"] == "user_created"


def test_created_project_appears_in_selector_and_loads_saved_values(auth_client):
    response = auth_client.post(
        "/projects/create",
        data=_payload(project_name="Baltic Solar", project_type="Solar", template_source="generic_solar", capacity_mw="75", tariff_eur_mwh="120"),
    )
    assert response.status_code == 200

    page = auth_client.get("/?project=baltic-solar")
    assert page.status_code == 200
    assert "User-Created Projects" in page.text
    assert "Baltic Solar" in page.text
    assert "Factory Templates" in page.text
    assert "TUHO Wind 1" in page.text
    assert "Oborovo Solar PV" in page.text
    assert 'value="75"' in page.text
    assert 'value="120"' in page.text
    assert 'value="Croatia"' in page.text
    assert "Runtime built from saved project assumptions" in page.text


def test_docs_reports_and_guardrails_capture_phase17b_scope():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = open(os.path.join(base, "docs", "phase17_required_field_input_form.md"), encoding="utf-8").read()
    schema = open(os.path.join(base, "reports", "phase17_required_field_schema.csv"), encoding="utf-8").read()
    validation = open(os.path.join(base, "reports", "phase17_required_field_validation_matrix.csv"), encoding="utf-8").read()
    runtime_binding = open(os.path.join(base, "reports", "phase17_required_field_runtime_binding_matrix.csv"), encoding="utf-8").read()
    gaps = open(os.path.join(base, "reports", "phase17_required_field_remaining_gaps.csv"), encoding="utf-8").read()
    js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read().lower()

    assert "Phase 17B adds required input capture and validation" in docs
    assert "Phase 17B persists user assumptions in baseline_snapshot" in docs
    assert "Phase 17B still uses template-seeded runtime" in docs
    assert "Phase 17C will add true build_projectinputs_from_scratch" in docs
    assert "G20 remains BLOCKED" in docs
    assert "R99/R102 remain NOT APPROVED" in docs

    for marker in (
        "country_market",
        "capacity_mw",
        "cod_date",
        "construction_months",
        "horizon_years",
        "tariff_eur_mwh",
        "ppa_term_years",
        "p50_hours",
        "opex_y1_keur",
        "total_capex_keur",
        "gearing_pct",
        "interest_rate_pct",
        "tenor_years",
        "target_dscr",
    ):
        assert marker in schema

    assert "project_name,required" in validation
    assert "capacity_mw,required_positive" in validation
    assert "target_dscr" in runtime_binding
    assert "template-seeded runtime remains in place" in gaps

    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "debt service ="):
        assert marker not in js
