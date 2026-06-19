"""U7-ERROR-WARNING-CLEANUP: remove internal-development terminology and
governance references from the external-facing UX.

Covers:
1. No forbidden terminology rendered in primary user paths.
2. Governance codes (G20 / R99 / R102) hidden from external-facing UI.
3. Validation wording remains intact (Validated Generic Model / Example
   Project / Experimental / Validation Status concepts).
4. "Example Project" wording appears where expected (project browser).
5. "Project Template" / template-naming wording appears where expected
   (new-project template selector).
6. Existing functionality unchanged (project create / browse / run /
   export / scenario compare still work).

Does not touch domain/*, app/waterfall_core.py, app/input_adapter.py,
app/project_factories.py, or any engine/validation/export calculation --
only user-facing wording and visibility in templates, main_web.py
context wiring, and app/validation_status.py labels.
"""
from __future__ import annotations

import os

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-u7")

import pytest
from fastapi.testclient import TestClient

from app.auth import create_session_token
from app.validation_status import get_validation_status
from main_web import app


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=True)


def _login(client, user_id):
    token = create_session_token(user_id=user_id, username=user_id)
    client.cookies.set("finco_session", token)
    return client


FORBIDDEN_TERMS = (
    "Factory Template",
    "Generic Factory",
    "Runtime Factory",
    "Saved Baseline",
    "Golden Fixture",
    "factory-bound",
    "Calibrated reference project",
)


# ---------------------------------------------------------------------------
# 1. No forbidden terminology rendered in primary user paths
# ---------------------------------------------------------------------------

def test_no_forbidden_terminology_on_project_browse(client):
    _login(client, "u7_browse")
    resp = client.get("/projects/browse")
    assert resp.status_code == 200
    for term in FORBIDDEN_TERMS:
        assert term not in resp.text, f"forbidden term leaked: {term!r}"


def test_no_forbidden_terminology_on_project_home(client):
    _login(client, "u7_home")
    resp = client.get("/?project=tuho")
    assert resp.status_code == 200
    for term in FORBIDDEN_TERMS:
        assert term not in resp.text, f"forbidden term leaked: {term!r}"


# ---------------------------------------------------------------------------
# 2. Governance codes hidden from external-facing UI
# ---------------------------------------------------------------------------

def test_governance_codes_hidden_from_project_home(client):
    _login(client, "u7_gov_home")
    resp = client.get("/?project=tuho")
    assert resp.status_code == 200
    assert "G20" not in resp.text
    assert "R99" not in resp.text
    assert "R102" not in resp.text


def test_governance_codes_hidden_from_multi_scenario_compare(client):
    from app.persistence.db import init_db
    from app.persistence.projects_repository import save_project, get_project_by_code
    from app.persistence.scenarios_repository import save_scenario

    init_db()
    user_id = "u7_gov_multi"
    _login(client, user_id)
    project_code = "u7-gov-multi-fixture"
    rec = get_project_by_code(user_id, project_code)
    if not rec:
        rec = save_project(
            user_id=user_id,
            project_code=project_code,
            project_name="U7 Gov Multi Fixture",
            project_type="Wind",
            project_origin="user_created",
            source_project_template="test",
            baseline_snapshot={"tariff_eur_mwh": "50"},
        )
    scenario_ids = []
    for i in range(2):
        sc = save_scenario(
            user_id=user_id,
            project_id=rec.project_id,
            project_code=project_code,
            source_project_template="test",
            scenario_name=f"U7 Scenario {i}",
            snapshot={"tariff_eur_mwh": str(50 + i * 5)},
        )
        scenario_ids.append(sc.scenario_id)

    resp = client.get(
        f"/scenarios/compare-multi?scenario_ids={','.join(scenario_ids)}"
    )
    assert resp.status_code == 200
    assert "g20_status" not in resp.text
    assert "r99_r102_status" not in resp.text
    assert "scm-multi-row--gov" not in resp.text


# ---------------------------------------------------------------------------
# 3. Validation wording remains intact
# ---------------------------------------------------------------------------

def test_validation_status_uses_g1d_terminology_not_calibration():
    status = get_validation_status("tuho")
    assert status.tier_label == "Validated reference project"
    assert "calibrat" not in status.tier_label.lower()
    assert "calibrat" not in status.tier_description.lower()

    generic = get_validation_status("generic_solar")
    assert generic.tier_label == "Validated model with caveats"

    experimental = get_validation_status("portfolio")
    assert experimental.tier_label == "Experimental, internal only"


def test_project_browser_validation_badge_uses_g1d_wording(client):
    _login(client, "u7_validation_badge")
    resp = client.get("/projects/browse")
    assert resp.status_code == 200
    assert "Validated reference project" in resp.text
    assert "Calibrated reference project" not in resp.text


# ---------------------------------------------------------------------------
# 4. "Example Project" wording appears where expected
# ---------------------------------------------------------------------------

def test_example_project_wording_in_browser(client):
    _login(client, "u7_example_wording")
    resp = client.get("/projects/browse")
    assert resp.status_code == 200
    assert "Example Projects" in resp.text


# ---------------------------------------------------------------------------
# 5. "Project Template" / template-naming wording appears where expected
# ---------------------------------------------------------------------------

def test_new_project_template_selector_does_not_say_factory(client):
    _login(client, "u7_template_wording")
    resp = client.get("/projects/new/prefill")
    assert resp.status_code == 200
    assert "Factory" not in resp.text


# ---------------------------------------------------------------------------
# 6. Existing functionality unchanged
# ---------------------------------------------------------------------------

def test_create_browse_run_export_unaffected(client):
    _login(client, "u7_e2e")
    create_resp = client.post(
        "/projects/create",
        data={
            "project_name": "U7 Functional Check",
            "project_type": "Solar",
            "template_source": "",
            "country_market": "Spain",
            "capacity_mw": "12",
        },
    )
    assert create_resp.status_code == 200

    browse = client.get("/projects/browse")
    assert browse.status_code == 200
    assert "U7 Functional Check" in browse.text

    run_resp = client.post("/run", data={"active_project": "u7-functional-check"})
    assert run_resp.status_code == 200

    export_resp = client.get(
        "/exports/runtime-summary.csv?project=u7-functional-check"
    )
    assert export_resp.status_code == 200
    assert export_resp.headers.get("content-type", "").startswith("text/csv")
