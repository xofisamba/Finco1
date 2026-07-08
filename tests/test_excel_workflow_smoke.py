"""PR 854 Excel workflow acceptance lock.

This is a narrow route/render smoke for the current Excel-style workflow:
Inputs, CAPEX, OPEX, Revenue, Scenarios, Run, and post-run return. It avoids
financial assertions and only checks that the workbook surfaces render with the
backend-provided CAPEX/OPEX view models in protected and user-created projects.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.parse

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from main_web import app  # noqa: E402


EXCEPTION_MARKERS = (
    "UndefinedError",
    "NameError",
    "AttributeError",
    "Internal Server Error",
    "Traceback",
)


@pytest.fixture()
def client():
    tc = TestClient(app, raise_server_exceptions=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _assert_clean_html(response, label: str) -> str:
    assert response.status_code == 200, (
        f"{label} returned {response.status_code}: {response.text[:500]}"
    )
    body = response.text
    for marker in EXCEPTION_MARKERS:
        assert marker not in body, f"{label} rendered exception marker {marker!r}"
    return body


def _assert_workbook_flow_surfaces(body: str) -> None:
    for marker in (
        'id="panel-inputs"',
        'id="panel-revenue"',
        'id="panel-scenario"',
        'id="panel-opex"',
        'id="panel-capex"',
        'hx-post="/run"',
        "CAPEX Summary",
        "OPEX Summary",
        "cx-grid-wrapper",
        "ox-grid-wrapper",
        "cx-grid",
        "ox-grid",
        "cx-sticky-col",
        "ox-sticky-col",
        ">Y30<",
        "Total CAPEX",
        "Total OPEX",
    ):
        assert marker in body, f"Workbook surface marker missing: {marker}"


def _assert_no_vm_fallback(body: str) -> None:
    lowered = body.lower()
    assert "capex grid unavailable" not in lowered
    assert "opex grid unavailable" not in lowered
    assert "capex_vm unavailable" not in lowered
    assert "opex_vm unavailable" not in lowered


def _create_generic_wind_project(client: TestClient) -> str:
    response = client.post(
        "/projects/create",
        data={
            "project_name": "PR854 Excel Workflow Acceptance Wind",
            "project_type": "Wind",
            "template_source": "generic_wind",
            "country_market": "Croatia",
            "capacity_mw": "80",
            "cod_date": "2027-01-01",
            "construction_months": "12",
            "horizon_years": "30",
            "tariff_eur_mwh": "55",
            "ppa_term_years": "15",
            "p50_hours": "2800",
            "opex_y1_keur": "700",
            "total_capex_keur": "80000",
            "gearing_pct": "70",
            "interest_rate_pct": "4.5",
            "tenor_years": "15",
            "target_dscr": "1.25",
        },
        follow_redirects=False,
    )
    redirect = response.headers.get("hx-redirect")
    assert redirect, (
        "Expected HX-Redirect from /projects/create, got "
        f"{response.status_code}: {response.text[:300]}"
    )
    query = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    return query["project"][0]


def test_protected_reference_excel_workflow_survives_run_and_return(client):
    before_run = _assert_clean_html(
        client.get("/?project=tuho", follow_redirects=True),
        "GET /?project=tuho before run",
    )

    _assert_workbook_flow_surfaces(before_run)
    _assert_no_vm_fallback(before_run)
    assert "Protected original" in before_run
    assert "Read-only" in before_run
    assert 'class="cx-input"' not in before_run
    assert 'class="ox-input"' not in before_run

    run_response = client.post(
        "/run",
        data={"active_project": "tuho", "currency": "EUR"},
        headers={"HX-Request": "true"},
    )
    assert run_response.status_code != 500, run_response.text[:500]
    for marker in EXCEPTION_MARKERS:
        assert marker not in run_response.text

    after_run = _assert_clean_html(
        client.get("/?project=tuho", follow_redirects=True),
        "GET /?project=tuho after run",
    )
    _assert_workbook_flow_surfaces(after_run)
    _assert_no_vm_fallback(after_run)
    assert "Protected original" in after_run
    assert "cx-grid-wrapper" in after_run
    assert "ox-grid-wrapper" in after_run


def test_user_created_project_renders_editable_capex_and_opex_workbook(client):
    project_code = _create_generic_wind_project(client)

    body = _assert_clean_html(
        client.get(f"/?project={project_code}", follow_redirects=True),
        f"GET /?project={project_code}",
    )

    _assert_workbook_flow_surfaces(body)
    _assert_no_vm_fallback(body)
    assert "Protected original" not in body
    assert 'class="cx-input"' in body
    assert 'class="ox-input"' in body
    assert re.search(r'name="capex_[^"]+"', body), "Expected editable CAPEX inputs"
    assert re.search(r'name="opex_[^"]+"', body), "Expected editable OPEX inputs"
    assert "Total CAPEX" in body
    assert "Total OPEX" in body


def test_workspace_shell_includes_current_capex_and_opex_grid_partials():
    workspace_shell = os.path.join(
        REPO_ROOT, "app", "templates", "partials", "workspace_shell.html"
    )
    with open(workspace_shell, "r", encoding="utf-8") as f:
        src = f.read()

    assert 'include "partials/sheet_capex_grid.html"' in src
    assert 'include "partials/sheet_opex_grid.html"' in src


def test_inputs_section_uses_view_models_without_normal_fallback_copy():
    inputs_section = os.path.join(
        REPO_ROOT, "app", "templates", "partials", "inputs_section.html"
    )
    with open(inputs_section, "r", encoding="utf-8") as f:
        src = f.read()

    assert "{% if capex_vm %}" in src
    assert "{% if opex_vm %}" in src
    assert "Hard CAPEX" in src
    assert "Total OPEX Y1" in src
    assert "capex_vm unavailable" not in src
    assert "opex_vm unavailable" not in src
