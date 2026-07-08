from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.auth import COOKIE_NAME, create_session_token
from app.ui.project_context import get_project_context
from main_web import app

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "app" / "templates" / "partials" / "sheet_revenue.html"


def _render_revenue(project_id: str, *, is_user_project: bool) -> str:
    env = Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "app" / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template("partials/sheet_revenue.html").render(
        project_ctx=get_project_context(project_id),
        is_user_project=is_user_project,
    )


@pytest.fixture()
def client() -> TestClient:
    tc = TestClient(app)
    token = create_session_token()
    tc.cookies.set(COOKIE_NAME, token)
    return tc


def _create_user_project(client: TestClient) -> str:
    resp = client.post(
        "/projects/create",
        data={
            "project_name": "PR855 Revenue Excel Cleanup",
            "project_type": "Solar",
            "template_source": "generic_solar",
            "country_market": "Croatia",
            "capacity_mw": "50",
            "cod_date": "2027-01-01",
            "construction_months": "12",
            "horizon_years": "25",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "1400",
            "opex_y1_keur": "1000",
            "total_capex_keur": "50000",
            "gearing_pct": "70",
            "interest_rate_pct": "5",
            "tenor_years": "15",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect")
    assert redirect, f"expected project create redirect, got {resp.status_code}: {resp.text[:200]}"

    import urllib.parse

    return urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)["project"][0]


def test_revenue_renders_for_protected_reference_projects() -> None:
    for project_id in ("tuho", "oborovo"):
        html = _render_revenue(project_id, is_user_project=False)
        assert "Production assumptions" in html
        assert "Price assumptions" in html
        assert "Revenue output" in html
        assert "Protected original" in html
        assert 'name="rev_' not in html


def test_revenue_user_project_route_renders_supported_editable_fields(client: TestClient) -> None:
    project_code = _create_user_project(client)
    resp = client.get(f"/?project={project_code}&sheet=revenue")
    assert resp.status_code == 200
    assert 'id="revenue-grid"' in resp.text

    html = _render_revenue("generic_solar", is_user_project=True)
    names = set(re.findall(r'name="(rev_[^"]+)"', html))
    assert names == {"rev_ppa_base_tariff"}
    assert "Editable supported assumption" in html


def test_revenue_visible_sheet_avoids_internal_code_and_technical_output_claims() -> None:
    html = _render_revenue("tuho", is_user_project=False)

    assert re.search(r"<th[^>]*>\s*Code\s*</th>", html) is None
    assert "period index" not in html
    assert "Revenue = Production" not in html
    assert "Production x Price" not in html
    assert "Runtime Summary after Run" in html
    assert "Backend runtime is authoritative; this sheet does not recompute revenue." in html


def test_revenue_calculated_output_rows_are_read_only() -> None:
    html = _render_revenue("tuho", is_user_project=False)

    for expected in (
        'data-fc-addr="revenue!summary.tariff_y1"',
        'data-fc-addr="revenue!summary.ppa_revenue_y1"',
        'data-fc-addr="revenue!summary.total_revenue_y1"',
    ):
        assert expected in html
    output_rows = html.split('id="revenue-grid-output"', 1)[1]
    assert 'data-fc-editable="true"' not in output_rows
    assert "Calculated after Run" in output_rows


def test_revenue_template_has_no_hidden_revenue_formula() -> None:
    src = TEMPLATE_PATH.read_text(encoding="utf-8")

    forbidden = (
        "ppa_y1",
        "co2_y1",
        "capacity_mw *",
        "operating_hours_p50 *",
        "Est. Total Y1 Revenue",
        "Indicative",
    )
    for token in forbidden:
        assert token not in src


def test_revenue_template_does_not_require_optional_revenue_view_model() -> None:
    src = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "revenue_vm" not in src
