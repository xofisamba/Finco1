"""U2-NEW-PROJECT-SIMPLIFICATION: minimal New Project flow correctness.

Covers the two bugs found and fixed while implementing U2:

1. The minimal create form (``app/templates/partials/new_project_minimal.html``)
   previously submitted a hardcoded ``template_source=generic_solar`` hidden
   field regardless of the Technology selector. Picking "Wind" therefore
   always failed server-side validation ("Solar templates require project
   type Solar."). Fixed by leaving the hidden field blank so
   ``main_web._normalize_template_source`` derives the correct generic
   template from the selected Technology.

2. ``main_web._apply_new_project_required_inputs`` unconditionally
   overwrote every detailed assumption (tariff, PPA term, P50 hours, OPEX,
   CAPEX, gearing, interest rate, tenor, target DSCR, COD, construction
   months, horizon years) with the submitted form value -- including a
   blank string when the minimal form (which only submits project_name,
   project_type, country_market, capacity_mw) didn't send that field at
   all. This silently wiped out the factory defaults that
   ``_project_baseline_snapshot`` had just populated from
   ``create_default_solar_project`` / ``create_default_wind_project``.
   Fixed so a blank submitted value keeps the existing baseline default
   instead of overwriting it with "".

This module does not touch domain/waterfall/*, app/waterfall_core.py, any
financial engine, app/project_factories.py, or the TUHO/Oborovo factories --
only the New Project creation route/template wiring in main_web.py and
app/templates/partials/new_project_minimal.html.
"""
from __future__ import annotations

import os

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-u2")

import pytest
from fastapi.testclient import TestClient

from app.auth import create_session_token
from app.persistence.projects_repository import get_project_by_code
from main_web import app


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=True)


def _login(client, user_id):
    token = create_session_token(user_id=user_id, username=user_id)
    client.cookies.set("finco_session", token)
    return client


def _create_minimal(client, *, user_id, name, technology, country, capacity_mw):
    _login(client, user_id)
    resp = client.post(
        "/projects/create",
        data={
            "project_name": name,
            "project_type": technology,
            "template_source": "",
            "country_market": country,
            "capacity_mw": str(capacity_mw),
        },
    )
    return resp


def _slug(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


# ---------------------------------------------------------------------------
# 1. Solar project creation with minimal fields
# ---------------------------------------------------------------------------

def test_solar_minimal_creation_succeeds_and_uses_solar_defaults(client):
    name = "U2 Solar Minimal"
    resp = _create_minimal(
        client, user_id="u2_solar", name=name, technology="Solar",
        country="Spain", capacity_mw=30,
    )
    assert resp.status_code == 200

    record = get_project_by_code("u2_solar", _slug(name))
    assert record is not None
    snap = record.baseline_snapshot
    assert snap["template_source"] == "generic_solar"
    assert snap["project_type"] == "Solar"
    # User-supplied fields are respected.
    assert snap["country_market"] == "Spain"
    assert snap["capacity_mw"] == "30"
    # Every other assumption falls back to the Generic Solar factory
    # defaults (app.project_factories.create_default_solar_project),
    # not a blank string.
    assert snap["tariff_eur_mwh"] == "55.0"
    assert snap["ppa_term_years"] == "10"
    assert snap["p50_hours"] == "1500.0"
    assert snap["opex_y1_keur"] == "380.0"
    assert snap["total_capex_keur"] == "33000.0"
    assert snap["tenor_years"] == "15"
    assert snap["cod_date"]
    assert snap["construction_months"]
    assert snap["horizon_years"]


# ---------------------------------------------------------------------------
# 2. Wind project creation with minimal fields
# ---------------------------------------------------------------------------

def test_wind_minimal_creation_succeeds_and_uses_wind_defaults(client):
    name = "U2 Wind Minimal"
    resp = _create_minimal(
        client, user_id="u2_wind", name=name, technology="Wind",
        country="Croatia", capacity_mw=40,
    )
    # Regression guard for the hidden-template_source bug: this used to
    # be a 400 ("Solar templates require project type Solar.") because
    # the hidden field was hardcoded to generic_solar.
    assert resp.status_code == 200

    record = get_project_by_code("u2_wind", _slug(name))
    assert record is not None
    snap = record.baseline_snapshot
    assert snap["template_source"] == "generic_wind"
    assert snap["project_type"] == "Wind"
    assert snap["country_market"] == "Croatia"
    assert snap["capacity_mw"] == "40"
    # Generic Wind factory defaults, not blank.
    assert snap["tariff_eur_mwh"] == "60.0"
    assert snap["ppa_term_years"] == "12"
    assert snap["p50_hours"] == "3000.0"
    assert snap["opex_y1_keur"] == "550.0"
    assert snap["total_capex_keur"] == "43000.0"
    assert snap["tenor_years"] == "15"


def test_solar_and_wind_minimal_creation_produce_distinct_defaults(client):
    """The same minimal-form code path must branch on Technology, not
    silently reuse one hardcoded template for both."""
    solar_resp = _create_minimal(
        client, user_id="u2_branch", name="Branch Solar", technology="Solar",
        country="Spain", capacity_mw=30,
    )
    wind_resp = _create_minimal(
        client, user_id="u2_branch", name="Branch Wind", technology="Wind",
        country="Croatia", capacity_mw=40,
    )
    assert solar_resp.status_code == 200
    assert wind_resp.status_code == 200

    solar = get_project_by_code("u2_branch", _slug("Branch Solar")).baseline_snapshot
    wind = get_project_by_code("u2_branch", _slug("Branch Wind")).baseline_snapshot
    assert solar["template_source"] == "generic_solar"
    assert wind["template_source"] == "generic_wind"
    assert solar["tariff_eur_mwh"] != wind["tariff_eur_mwh"]
    assert solar["total_capex_keur"] != wind["total_capex_keur"]


# ---------------------------------------------------------------------------
# 3. Save / reopen flow
# ---------------------------------------------------------------------------

def test_minimal_project_can_be_reopened_after_creation(client):
    name = "U2 Reopen Test"
    resp = _create_minimal(
        client, user_id="u2_reopen", name=name, technology="Wind",
        country="Croatia", capacity_mw=40,
    )
    assert resp.status_code == 200
    code = _slug(name)

    reopened = client.get(f"/?project={code}")
    assert reopened.status_code == 200
    assert name in reopened.text


# ---------------------------------------------------------------------------
# 4. Run after creation
# ---------------------------------------------------------------------------

def test_minimal_project_can_be_run_after_creation(client):
    name = "U2 Run Test"
    resp = _create_minimal(
        client, user_id="u2_run", name=name, technology="Wind",
        country="Croatia", capacity_mw=40,
    )
    assert resp.status_code == 200
    code = _slug(name)
    client.get(f"/?project={code}")

    run_resp = client.post("/run", data={"active_project": code})
    assert run_resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. Export after creation
# ---------------------------------------------------------------------------

def test_minimal_project_can_be_exported_after_creation(client):
    name = "U2 Export Test"
    resp = _create_minimal(
        client, user_id="u2_export", name=name, technology="Solar",
        country="Spain", capacity_mw=30,
    )
    assert resp.status_code == 200
    code = _slug(name)
    client.get(f"/?project={code}")
    client.post("/run", data={"active_project": code})

    export_resp = client.get(f"/exports/runtime-summary.csv?project={code}")
    assert export_resp.status_code == 200
    assert export_resp.headers.get("content-type", "").startswith("text/csv")
    assert len(export_resp.content) > 0


# ---------------------------------------------------------------------------
# 6. Scenario creation after creation
# ---------------------------------------------------------------------------

def test_scenario_can_be_added_to_minimal_project(client):
    name = "U2 Scenario Test"
    resp = _create_minimal(
        client, user_id="u2_scenario", name=name, technology="Wind",
        country="Croatia", capacity_mw=40,
    )
    assert resp.status_code == 200
    code = _slug(name)

    add_resp = client.post(
        "/scenarios/add",
        data={"project_code": code, "scenario_name": "Downside"},
    )
    assert add_resp.status_code == 200


# ---------------------------------------------------------------------------
# 7. TUHO and Oborovo still accessible through their non-primary path
# ---------------------------------------------------------------------------

def test_tuho_and_oborovo_not_offered_in_primary_new_project_form(client):
    _login(client, "u2_tuho_check")
    resp = client.get("/projects/new")
    assert resp.status_code == 200
    assert "tuho" not in resp.text.lower()
    assert "oborovo" not in resp.text.lower()


def test_tuho_and_oborovo_still_reachable_via_project_browser(client):
    _login(client, "u2_tuho_check2")
    resp = client.get("/projects/browse")
    assert resp.status_code == 200
    assert "tuho" in resp.text.lower()
    assert "oborovo" in resp.text.lower()
