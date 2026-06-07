"""Phase A1 - DSCR / CFADS derivation popovers.

Read-only transparency UX:
- no model calculation changes
- no persistence changes
- no JS financial calculations
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jinja2 import Environment, DictLoader

from app.api.project_runner import run_project
from app.ui.runtime_summary import runtime_summary_to_dict
from app.ui_runner import run_demo_project
from tests.test_auth_lite import COOKIE_NAME, TestClient, app, create_session_token


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SUMMARY_PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "runtime_summary.html"


def _render_runtime_summary_partial(context: dict) -> str:
    env = Environment(
        loader=DictLoader({"runtime_summary": RUNTIME_SUMMARY_PARTIAL.read_text(encoding="utf-8")}),
        autoescape=False,
    )
    template = env.get_template("runtime_summary")
    return template.render(**context)


def _extract_runtime_summary_json(html: str) -> dict:
    match = re.search(
        r'sessionStorage\.setItem\("lastRuntimeSummary",\s*({.*?})\);',
        html,
        re.DOTALL,
    )
    assert match, "Could not extract runtime_summary JSON from the /run response"
    return json.loads(match.group(1))


def _build_run_form_data(client: TestClient, project: str) -> dict[str, str]:
    response = client.get(f"/?project={project}", follow_redirects=True)
    assert response.status_code == 200

    form_data: dict[str, str] = {}
    for name, value in re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', response.text):
        if name not in form_data or (not form_data[name] and value):
            form_data[name] = value
    return form_data


def _active_dscr_periods(result) -> list:
    return [
        period
        for period in result.periods
        if getattr(period, "is_operation", False) and float(getattr(period, "senior_ds_keur", 0.0) or 0.0) > 0.0
    ]


@pytest.fixture
def authenticated_client():
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(COOKIE_NAME, create_session_token())
    return client


class TestRuntimeSummaryContextContract:
    def test_runtime_summary_includes_dscr_and_cfads_derivation_keys(self):
        result = run_project("TUHO", "Base")
        summary = runtime_summary_to_dict(result, "tuho", "TUHO Wind 1")

        assert "dscr_derivation" in summary
        assert "cfads_derivation" in summary
        assert summary["dscr_derivation"]["display_value"] != "NOT_AVAILABLE"
        assert summary["cfads_derivation"]["display_value_keur"] != "NOT_AVAILABLE"

    def test_derivation_values_match_backend_waterfall_result(self):
        demo = run_demo_project("TUHO", "Base")
        api_result = run_project("TUHO", "Base")
        summary = runtime_summary_to_dict(api_result, "tuho", "TUHO Wind 1")
        periods = _active_dscr_periods(demo.result)
        sample = periods[0]

        assert summary["dscr_derivation"]["period_count"] == len(periods)
        assert summary["dscr_derivation"]["sample_period_label"] == f"Y{sample.year_index}-H{sample.period_in_year}"
        assert summary["dscr_derivation"]["sample_cfads_keur"] == f"{sample.cf_after_tax_keur:,.0f} kEUR"
        assert summary["dscr_derivation"]["sample_senior_debt_service_keur"] == f"{sample.senior_ds_keur:,.0f} kEUR"
        assert summary["cfads_derivation"]["sample_ebitda_keur"] == f"{sample.ebitda_keur:,.0f} kEUR"
        assert summary["cfads_derivation"]["sample_tax_keur"] == f"{sample.tax_keur:,.0f} kEUR"
        assert summary["cfads_derivation"]["sample_cfads_keur"] == f"{sample.cf_after_tax_keur:,.0f} kEUR"


class TestRuntimeSummaryPartialRendering:
    def test_dscr_derivation_renders_from_backend_values(self):
        result = run_project("TUHO", "Base")
        summary = runtime_summary_to_dict(result, "tuho", "TUHO Wind 1")
        html = _render_runtime_summary_partial({"runtime_summary": summary, "messages": []})

        assert 'id="kpi-avg-dscr-derivation"' in html
        assert "How is this calculated?" in html
        assert summary["avg_dscr"] in html
        assert summary["dscr_derivation"]["display_value"] in html
        assert summary["dscr_derivation"]["total_cfads_keur"] in html
        assert summary["dscr_derivation"]["total_senior_debt_service_keur"] in html

    def test_cfads_derivation_renders_from_backend_values(self):
        result = run_project("TUHO", "Base")
        summary = runtime_summary_to_dict(result, "tuho", "TUHO Wind 1")
        html = _render_runtime_summary_partial({"runtime_summary": summary, "messages": []})

        assert 'id="kpi-cfads-derivation"' in html
        assert "CFADS (Total)" in html
        assert summary["total_cfads_keur"] in html
        assert summary["cfads_derivation"]["sample_ebitda_keur"] in html
        assert summary["cfads_derivation"]["sample_tax_keur"] in html
        assert summary["cfads_derivation"]["sample_cfads_keur"] in html

    def test_partial_contains_no_javascript_financial_calculation(self):
        text = RUNTIME_SUMMARY_PARTIAL.read_text(encoding="utf-8")
        assert "<script" not in text.lower()
        assert "Math." not in text
        assert "xirr(" not in text
        assert "function(" not in text
        assert "sessionStorage" not in text


class TestRunRouteRendering:
    def test_run_route_renders_dscr_derivation_popover(self, authenticated_client):
        form_data = _build_run_form_data(authenticated_client, "tuho")
        response = authenticated_client.post(
            "/run",
            data=form_data,
        )
        assert response.status_code == 200
        html = response.text
        runtime_summary = _extract_runtime_summary_json(html)

        assert 'id="kpi-avg-dscr-derivation"' in html
        assert runtime_summary["dscr_derivation"]["display_value"] in html
        assert runtime_summary["dscr_derivation"]["total_cfads_keur"] in html
        assert runtime_summary["dscr_derivation"]["total_senior_debt_service_keur"] in html

    def test_run_route_renders_cfads_derivation_popover(self, authenticated_client):
        form_data = _build_run_form_data(authenticated_client, "oborovo")
        response = authenticated_client.post(
            "/run",
            data=form_data,
        )
        assert response.status_code == 200
        html = response.text
        runtime_summary = _extract_runtime_summary_json(html)

        assert 'id="kpi-cfads-derivation"' in html
        assert runtime_summary["cfads_derivation"]["display_value_keur"] in html
        assert runtime_summary["cfads_derivation"]["sample_cfads_keur"] in html
        assert runtime_summary["cfads_derivation"]["audit_source"] in html
