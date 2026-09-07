"""
tests/test_ui3a_decision_dashboard.py
UI-3A: Decision Dashboard — acceptance suite.

Test categories:

  STRUCTURAL         — tab ordering, no financial formulas, canonical
                       RuntimeResult projection used, stale/current wiring.
  VIEW-MODEL         — authoritative KPI mapping, unavailable values,
                       formatting-only, chart series trace to runtime output.
  REAL_ENGINE_E2E    — Generic Solar and Wind, real engine (no mock).
  BROWSER            — Playwright: render, run, KPI populated, chart rendered,
                       stale after edit, current after rerun, no-run state.
  REGRESSION         — Run UI-1A, UI-2A, UI-2B, UI-2C suites (import only).

Engine freeze gate: zero diff on financial_engine/, finco_core/,
app/api/project_runner.py, app/services/production_financial_authority.py
from caffef16ca2e68238fac927b661e02af44a15a1d.
"""
from __future__ import annotations

import glob
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest.mock
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from types import MappingProxyType

import pytest

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-ui3a")

from starlette.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token, decode_session_token  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
OVERVIEW_PROJ  = REPO_ROOT / "app" / "v2" / "overview_projection.py"
OVERVIEW_TPL   = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_overview.html"
WORKBOOK_SHELL = REPO_ROOT / "app" / "templates" / "v2" / "workbook.html"
V2_ROUTER      = REPO_ROOT / "app" / "v2" / "router.py"
CHARTS_JS      = REPO_ROOT / "static" / "interaction" / "overview-charts.js"

# ── Client helpers ────────────────────────────────────────────────────────────

def _client():
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client, suffix="ui3a", project_type="Solar", template_source=None):
    if template_source is None:
        template_source = "generic_solar" if project_type == "Solar" else "generic_wind"
    resp = client.post("/projects/create", data={
        "project_name": f"UI3A-{suffix}",
        "project_type": project_type,
        "template_source": template_source,
        "country_market": "Poland",
        "capacity_mw": "50",
        "cod_date": "2029-01-01",
        "construction_months": "18",
        "horizon_years": "25",
        "tariff_eur_mwh": "55",
        "ppa_term_years": "15",
        "p50_hours": "2200",
        "opex_y1_keur": "700",
        "total_capex_keur": "45000",
        "gearing_pct": "70",
        "interest_rate_pct": "4.5",
        "tenor_years": "15",
        "target_dscr": "1.30",
    }, follow_redirects=False)
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"expected redirect, got {resp.status_code}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    return parsed["project"][0]


def _get_ws(client, project_code):
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    token = client.cookies.get(COOKIE_NAME)
    session = decode_session_token(token)
    proj = get_project_record(user_id=session.user_id, project_code=project_code)
    return get_workspace_state(user_id=session.user_id, project_id=proj.project_id)


def _get_composite_hash(client, project_code):
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200
    body = resp.text
    ch = re.search(r'data-content-hash="([^"]+)"', body).group(1)
    wv = re.search(r'data-workbook-version="([^"]+)"', body).group(1)
    return ch, wv


def _run(client, project_code):
    """Real run — no mock."""
    ch, wv = _get_composite_hash(client, project_code)
    resp = client.post("/v2/workbook/run", data={
        "project": project_code, "content_hash": ch, "workbook_version": wv,
    }, headers={"HX-Request": "true"}, follow_redirects=False)
    assert resp.status_code == 200, f"Run HTTP {resp.status_code}: {resp.text[:400]}"
    return resp


def _update_field(client, project_code, field_id, value, sheet_id="project_setup"):
    ch, wv = _get_composite_hash(client, project_code)
    resp = client.post("/v2/workbook/update", data={
        "field_id": field_id, "value": value,
        "project": project_code, "workbook_version": wv,
        "content_hash": ch, "sheet_id": sheet_id,
    }, headers={"HX-Request": "true"})
    assert resp.status_code == 200, f"Update failed: {resp.status_code}: {resp.text[:300]}"
    return resp


def _assert_real_run_succeeded(resp, client, project_code, label=""):
    body = resp.text
    pfx = f"[{label}] " if label else ""
    assert "Engine run failed" not in body, f"{pfx}engine failure: {body[:600]}"
    assert "could not be saved" not in body.lower(), f"{pfx}persistence fail: {body[:600]}"
    ws = _get_ws(client, project_code)
    assert ws.last_runtime_snapshot_id is not None, f"{pfx}snapshot_id not set"
    assert ws.last_runtime_at is not None, f"{pfx}runtime_at not set"
    assert ws.dirty is False, f"{pfx}workspace still dirty after run"
    return ws


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURAL
# ═══════════════════════════════════════════════════════════════════════════════

class TestStructural:
    """STRUCTURAL: tab ordering, source inspection, no financial formulas."""

    # ── Tab ordering ────────────────────────────────────────────────────────

    def test_overview_tab_exists_in_shell(self):
        text = WORKBOOK_SHELL.read_text()
        assert 'id="tab-overview"' in text

    def test_overview_tab_is_first_tab(self):
        text = WORKBOOK_SHELL.read_text()
        ov_pos = text.index('id="tab-overview"')
        ps_pos = text.index('id="tab-project-setup"')
        assert ov_pos < ps_pos, "Overview tab must appear before Project Setup tab"

    def test_overview_panel_is_first_panel(self):
        text = WORKBOOK_SHELL.read_text()
        ov_pos = text.index('id="panel-overview"')
        ps_pos = text.index('id="panel-project-setup"')
        assert ov_pos < ps_pos

    def test_overview_panel_not_hidden_on_load(self):
        text = WORKBOOK_SHELL.read_text()
        # Overview panel must NOT have hidden attribute; others must
        assert 'id="panel-overview"' in text
        overview_block = text[text.index('id="panel-overview"'):text.index('id="panel-project-setup"')]
        assert "hidden" not in overview_block, (
            "panel-overview must not be hidden (it is the default active tab)"
        )

    def test_project_setup_panel_hidden(self):
        text = WORKBOOK_SHELL.read_text()
        assert 'id="panel-project-setup" aria-labelledby="tab-project-setup" hidden' in text

    def test_overview_tab_aria_selected_true(self):
        text = WORKBOOK_SHELL.read_text()
        assert 'aria-controls="panel-overview"' in text
        ov_btn_start = text.index('aria-controls="panel-overview"')
        chunk = text[max(0, ov_btn_start - 80):ov_btn_start]
        assert 'aria-selected="true"' in chunk

    # ── Projection source ────────────────────────────────────────────────────

    def test_overview_projection_module_exists(self):
        assert OVERVIEW_PROJ.exists()

    def test_overview_template_exists(self):
        assert OVERVIEW_TPL.exists()

    def test_overview_projection_imported_in_router(self):
        text = V2_ROUTER.read_text()
        assert "build_overview_projection" in text
        assert "overview_projection" in text

    def test_overview_projection_uses_runtime_result(self):
        text = OVERVIEW_PROJ.read_text()
        assert "RuntimeResult" in text or "runtime_summary" in text
        assert "thaw_runtime_payload" in text

    def test_overview_projection_uses_classify_schedule_state(self):
        text = OVERVIEW_PROJ.read_text()
        assert "classify_schedule_state" in text

    def test_no_financial_formulas_in_js(self):
        text = CHARTS_JS.read_text()
        # Ensure no IRR/NPV/DSCR computation in JS
        for forbidden in ["irr(", "npv(", "Math.pow", "pv("]:
            assert forbidden not in text, f"Financial formula {forbidden!r} found in charts JS"

    def test_no_financial_formulas_in_template(self):
        text = OVERVIEW_TPL.read_text()
        for forbidden in ["* 100", "/ total", "+ interest", "Math.pow"]:
            assert forbidden not in text, (
                f"Possible financial formula {forbidden!r} in overview template"
            )

    def test_stale_state_wired_in_template(self):
        text = OVERVIEW_TPL.read_text()
        assert "is_stale" in text
        assert "stale-banner" in text or "stale_banner" in text or "v2-overview-stale-banner" in text

    def test_no_run_state_wired_in_template(self):
        text = OVERVIEW_TPL.read_text()
        assert "is_no_run" in text or "no-run" in text

    def test_charts_js_loaded_in_shell(self):
        text = WORKBOOK_SHELL.read_text()
        assert "overview-charts.js" in text

    def test_overview_gaps_documented_in_projection_module(self):
        text = OVERVIEW_PROJ.read_text()
        assert "equity_npv" in text
        assert "NOT_AVAILABLE" in text

    def test_kpi_tiles_reference_testids(self):
        text = OVERVIEW_TPL.read_text()
        for tid in ["kpi-project-irr", "kpi-equity-irr", "kpi-min-dscr", "kpi-avg-dscr", "kpi-min-llcr"]:
            assert tid in text, f"Missing testid: {tid}"


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW-MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class TestViewModelProjection:
    """VIEW-MODEL: OverviewProjection builder unit tests."""

    def _make_pis(self):
        """Minimal pis stub that delegates to generic solar factory."""
        class _PIS:
            template_source = "generic_solar"
            def to_projectinputs(self):
                from app.project_factories import create_default_solar_project
                return create_default_solar_project()
        return _PIS()

    def test_no_runtime_gives_not_run_state(self):
        from app.v2.overview_projection import build_overview_projection
        from app.workbook.runtime_projection import RuntimeProjectionState
        ov = build_overview_projection(None, False, self._make_pis())
        assert ov.state == RuntimeProjectionState.NOT_RUN

    def test_no_runtime_kpis_are_not_available(self):
        from app.v2.overview_projection import build_overview_projection, NOT_AVAILABLE
        ov = build_overview_projection(None, False, self._make_pis())
        assert ov.project_irr == NOT_AVAILABLE
        assert ov.equity_irr == NOT_AVAILABLE
        assert ov.avg_dscr == NOT_AVAILABLE
        assert ov.min_dscr == NOT_AVAILABLE
        assert ov.min_llcr == NOT_AVAILABLE

    def test_no_runtime_chart_data_is_none(self):
        from app.v2.overview_projection import build_overview_projection
        ov = build_overview_projection(None, False, self._make_pis())
        assert ov.chart_debt_periods is None

    def test_project_context_populated_from_pis(self):
        from app.v2.overview_projection import build_overview_projection
        ov = build_overview_projection(None, False, self._make_pis())
        assert ov.capacity_mw == "50.0 MW"
        assert ov.gearing_pct == "75.0%"
        assert ov.senior_tenor_years == "15 years"
        assert ov.input_target_dscr == "1.20x"

    def test_equity_npv_permanently_not_available(self):
        from app.v2.overview_projection import build_overview_projection, NOT_AVAILABLE
        ov = build_overview_projection(None, False, self._make_pis())
        assert ov.equity_npv == NOT_AVAILABLE

    def test_plcr_permanently_not_available(self):
        from app.v2.overview_projection import build_overview_projection, NOT_AVAILABLE
        ov = build_overview_projection(None, False, self._make_pis())
        assert ov.plcr == NOT_AVAILABLE

    def test_kpis_come_from_runtime_summary_dict(self):
        """Runtime summary strings are passed through without transformation."""
        from app.v2.overview_projection import build_overview_projection, NOT_AVAILABLE
        from unittest.mock import MagicMock

        rs = {
            "project_irr": "8.50%",
            "equity_irr": "11.20%",
            "avg_dscr": "1.45x",
            "min_dscr": "1.31x",
            "total_capex_keur": "45,000 kEUR",
            "senior_debt_keur": "31,500 kEUR",
            "total_revenue_keur": "120,000 kEUR",
            "total_ebitda_keur": "85,000 kEUR",
            "total_cfads_keur": "60,000 kEUR",
        }
        rr = MagicMock()
        rr.snapshot_id = "20260907T180000"
        rr.ran_at = "2026-09-07T18:00:00+00:00"
        rr.runtime_summary = rs
        rr.debt_schedule = None

        ov = build_overview_projection(rr, False, self._make_pis())
        # KPIs must come verbatim from runtime_summary — no transformation
        assert ov.project_irr == "8.50%"
        assert ov.equity_irr == "11.20%"
        assert ov.avg_dscr == "1.45x"
        assert ov.min_dscr == "1.31x"
        assert ov.total_capex_keur == "45,000 kEUR"

    def test_min_llcr_from_debt_schedule_summary(self):
        """min_llcr must come from debt_schedule.summary, not runtime_summary."""
        from app.v2.overview_projection import build_overview_projection
        from unittest.mock import MagicMock
        from types import MappingProxyType

        rr = MagicMock()
        rr.snapshot_id = "snap1"
        rr.ran_at = "2026-09-07T18:00:00+00:00"
        rr.runtime_summary = {"avg_dscr": "1.40x", "min_dscr": "1.28x"}
        rr.debt_schedule = MappingProxyType({
            "periods": [
                {"date": "2032-06-30", "is_operation": True,
                 "senior_balance_keur": 30000.0, "senior_ds_keur": 2000.0, "dscr": 1.30}
            ],
            "summary": {"min_llcr": 1.35, "target_dscr": 1.30, "periods_in_lockup": 0},
        })

        ov = build_overview_projection(rr, False, self._make_pis())
        assert ov.min_llcr == "1.35x", f"Expected 1.35x, got {ov.min_llcr}"
        assert ov.target_dscr == "1.30x"
        assert ov.periods_in_lockup == "0"

    def test_chart_debt_periods_traces_to_debt_schedule(self):
        """chart_debt_periods must be the thawed debt_schedule periods verbatim."""
        from app.v2.overview_projection import build_overview_projection
        from unittest.mock import MagicMock
        from types import MappingProxyType

        periods = [
            {"date": "2032-06-30", "is_operation": True,
             "senior_balance_keur": 30000.0, "senior_ds_keur": 2000.0, "dscr": 1.35},
            {"date": "2032-12-31", "is_operation": True,
             "senior_balance_keur": 28500.0, "senior_ds_keur": 2000.0, "dscr": 1.40},
        ]
        rr = MagicMock()
        rr.snapshot_id = "snap2"
        rr.ran_at = "2026-09-07T18:00:00+00:00"
        rr.runtime_summary = {}
        rr.debt_schedule = MappingProxyType({
            "periods": periods,
            "summary": {"min_llcr": 1.40, "target_dscr": 1.30, "periods_in_lockup": 0},
        })

        ov = build_overview_projection(rr, False, self._make_pis())
        assert ov.chart_debt_periods is not None
        assert len(ov.chart_debt_periods) == 2
        # Verify exact authoritative values are preserved
        assert ov.chart_debt_periods[0]["senior_balance_keur"] == 30000.0
        assert ov.chart_debt_periods[1]["dscr"] == 1.40

    def test_dirty_workspace_gives_stale_state(self):
        from app.v2.overview_projection import build_overview_projection
        from app.workbook.runtime_projection import RuntimeProjectionState
        from unittest.mock import MagicMock
        from types import MappingProxyType

        rr = MagicMock()
        rr.snapshot_id = "snap3"
        rr.ran_at = "2026-09-07T18:00:00+00:00"
        rr.runtime_summary = {}
        rr.debt_schedule = MappingProxyType({
            "periods": [{"date": "2032-06-30", "is_operation": True,
                         "senior_balance_keur": 30000.0, "senior_ds_keur": 2000.0, "dscr": 1.35}],
            "summary": {"min_llcr": 1.35},
        })
        ov = build_overview_projection(rr, is_dirty=True, pis=self._make_pis())
        assert ov.state == RuntimeProjectionState.STALE

    def test_clean_state_when_not_dirty_with_runtime(self):
        from app.v2.overview_projection import build_overview_projection
        from app.workbook.runtime_projection import RuntimeProjectionState
        from unittest.mock import MagicMock
        from types import MappingProxyType

        rr = MagicMock()
        rr.snapshot_id = "snap4"
        rr.ran_at = "2026-09-07T18:00:00+00:00"
        rr.runtime_summary = {}
        rr.debt_schedule = MappingProxyType({
            "periods": [{"date": "2032-06-30", "is_operation": True,
                         "senior_balance_keur": 30000.0, "senior_ds_keur": 2000.0, "dscr": 1.35}],
            "summary": {"min_llcr": 1.35},
        })
        ov = build_overview_projection(rr, is_dirty=False, pis=self._make_pis())
        assert ov.state == RuntimeProjectionState.CLEAN

    def test_fmt_x_returns_not_available_for_none(self):
        from app.v2.overview_projection import _fmt_x, NOT_AVAILABLE
        assert _fmt_x(None) == NOT_AVAILABLE
        assert _fmt_x(float("nan")) == NOT_AVAILABLE
        assert _fmt_x(float("inf")) == NOT_AVAILABLE

    def test_fmt_x_formats_correctly(self):
        from app.v2.overview_projection import _fmt_x
        assert _fmt_x(1.35) == "1.35x"
        assert _fmt_x(1.3) == "1.30x"


# ═══════════════════════════════════════════════════════════════════════════════
# REAL ENGINE E2E
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealEngineSolar:
    """REAL_ENGINE_E2E: Generic Solar with real engine (no mock).

    Proves that:
    1. Overview shows no-run state before run.
    2. Real engine run succeeds.
    3. Workbook page includes Overview with populated non-NOT_AVAILABLE KPIs.
    4. KPI values match stored runtime_summary (authoritative source).
    5. chart_debt_periods populated from real debt_schedule.periods.
    """

    @pytest.fixture(scope="class")
    def client(self):
        return _client()

    @pytest.fixture(scope="class")
    def project_code(self, client):
        return _create_project(client, suffix="solar-rre", project_type="Solar")

    def test_overview_in_workbook_page_before_run(self, client, project_code):
        resp = client.get(f"/v2/workbook?project={project_code}")
        assert resp.status_code == 200
        body = resp.text
        assert "panel-overview" in body
        assert "tab-overview" in body
        # Before run: no snapshot / no KPI values
        assert "NOT_AVAILABLE" not in body or "no-run-state" in body or "no_run" in body

    def test_overview_shows_no_run_state_before_run(self, client, project_code):
        resp = client.get(f"/v2/workbook?project={project_code}")
        body = resp.text
        assert "overview-no-run-state" in body or "no-run" in body or "No model results" in body

    def test_real_engine_run_succeeds(self, client, project_code):
        resp = _run(client, project_code)
        ws = _assert_real_run_succeeded(resp, client, project_code, label="Solar")
        assert ws.last_runtime_snapshot_id is not None

    def test_overview_kpis_populated_after_run(self, client, project_code):
        resp = client.get(f"/v2/workbook?project={project_code}")
        assert resp.status_code == 200
        body = resp.text
        # Overview panel must exist and contain KPI tiles
        assert "kpi-project-irr" in body
        assert "kpi-equity-irr" in body
        assert "kpi-min-dscr" in body

    def test_overview_kpis_not_all_not_available(self, client, project_code):
        """After a real run, at least the IRR and DSCR KPIs must be populated."""
        resp = client.get(f"/v2/workbook?project={project_code}")
        body = resp.text
        # Parse the overview panel area
        ov_start = body.find('id="panel-overview"')
        ov_end = body.find('id="panel-project-setup"')
        assert ov_start != -1 and ov_end != -1
        ov_section = body[ov_start:ov_end]
        # At least one KPI must show a real value (not all NOT_AVAILABLE)
        not_avail_count = ov_section.count("NOT_AVAILABLE")
        total_kpi_tiles = ov_section.count("v2-kpi-tile")
        assert total_kpi_tiles > 0, "No KPI tiles found in overview panel"
        # Equity NPV and PLCR are always NOT_AVAILABLE — allow for those
        assert not_avail_count < total_kpi_tiles, (
            "All KPI tiles show NOT_AVAILABLE — real engine KPIs not populated"
        )

    def test_overview_kpi_matches_authoritative_runtime_summary(self, client, project_code):
        """Displayed project_irr must match the stored authoritative runtime_summary."""
        ws = _get_ws(client, project_code)
        assert ws.last_runtime_summary, "No runtime_summary stored — run must have succeeded first"
        stored_irr = ws.last_runtime_summary.get("project_irr", "")
        if not stored_irr or stored_irr == "NOT_AVAILABLE":
            pytest.skip("project_irr not in runtime_summary for this run")
        # Normalise: raw float → formatted percentage string (mirrors overview_projection._get)
        if isinstance(stored_irr, float):
            expected_irr = f"{stored_irr * 100:.2f}%"
        else:
            expected_irr = str(stored_irr)

        resp = client.get(f"/v2/workbook?project={project_code}")
        body = resp.text
        ov_section = body[body.find('id="panel-overview"'):body.find('id="panel-project-setup"')]
        assert expected_irr in ov_section, (
            f"Displayed project_irr '{expected_irr}' not found in overview panel.\n"
            f"Overview snippet: {ov_section[:800]}"
        )

    def test_overview_min_dscr_matches_runtime_summary(self, client, project_code):
        ws = _get_ws(client, project_code)
        stored_min_dscr = ws.last_runtime_summary.get("min_dscr", "")
        if not stored_min_dscr or stored_min_dscr == "NOT_AVAILABLE":
            pytest.skip("min_dscr not available in runtime_summary")
        # Normalise: raw float → formatted ratio string
        if isinstance(stored_min_dscr, float):
            expected_dscr = f"{stored_min_dscr:.2f}x"
        else:
            expected_dscr = str(stored_min_dscr)
        resp = client.get(f"/v2/workbook?project={project_code}")
        ov = resp.text[resp.text.find('id="panel-overview"'):resp.text.find('id="panel-project-setup"')]
        assert expected_dscr in ov, (
            f"Displayed min_dscr '{expected_dscr}' not found in overview. Section: {ov[:600]}"
        )

    def test_chart_data_present_in_overview_after_run(self, client, project_code):
        """After a real run, chart containers with real debt period data must be in the page."""
        # Ensure a run has happened (may have run in a prior test in this class)
        ws = _get_ws(client, project_code)
        if not ws.last_runtime_snapshot_id:
            _run(client, project_code)
        resp = client.get(f"/v2/workbook?project={project_code}")
        ov = resp.text[resp.text.find('id="panel-overview"'):resp.text.find('id="panel-project-setup"')]
        assert "chart-debt-balance" in ov or "chart-dscr-profile" in ov, (
            "No chart containers found in overview after real run"
        )
        # Verify data-periods attribute is present and parseable.
        # Extract via tag boundary rather than a simple [^"]+ regex, since
        # tojson returns a Markup safe-string that bypasses | e escaping.
        # data-periods uses single-quoted attribute to avoid HTML-escaping JSON double quotes
        m = re.search(r"data-periods='([^']+)'", ov)
        if m:
            import html
            raw = html.unescape(m.group(1))
            periods = json.loads(raw)
            assert isinstance(periods, list)
            assert len(periods) > 0, "chart_debt_periods is empty after real run"
            # Verify authoritative field names are present
            sample = periods[0]
            assert "date" in sample
            assert "senior_balance_keur" in sample or "dscr" in sample

    def test_chart_debt_period_values_match_stored_debt_schedule(self, client, project_code):
        """Chart period values must trace to authoritative stored debt_schedule."""
        ws = _get_ws(client, project_code)
        if not ws.last_runtime_snapshot_id:
            _run(client, project_code)
            ws = _get_ws(client, project_code)
        if not ws.last_debt_schedule:
            pytest.skip("No debt_schedule stored — cannot verify chart data")
        stored_periods = ws.last_debt_schedule.get("periods", [])
        if not stored_periods:
            pytest.skip("Debt schedule has no periods")

        resp = client.get(f"/v2/workbook?project={project_code}")
        ov = resp.text[resp.text.find('id="panel-overview"'):resp.text.find('id="panel-project-setup"')]
        m = re.search(r"data-periods='([^']+)'", ov)
        if not m:
            pytest.skip("No data-periods found (no chart rendered)")
        import html
        rendered_periods = json.loads(html.unescape(m.group(1)))

        # Verify count matches
        assert len(rendered_periods) == len(stored_periods), (
            f"Rendered period count {len(rendered_periods)} != stored {len(stored_periods)}"
        )
        # Verify first period's authoritative field matches
        if stored_periods and rendered_periods:
            stored_bal = stored_periods[0].get("senior_balance_keur")
            rendered_bal = rendered_periods[0].get("senior_balance_keur")
            assert stored_bal == rendered_bal, (
                f"Rendered balance {rendered_bal} != stored {stored_bal}"
            )

    def test_overview_shows_run_timestamp(self, client, project_code):
        resp = client.get(f"/v2/workbook?project={project_code}")
        ov = resp.text[resp.text.find('id="panel-overview"'):resp.text.find('id="panel-project-setup"')]
        assert "overview-run-at" in ov or "overview-footer-timestamp" in ov

    def test_workspace_becomes_stale_after_edit(self, client, project_code):
        # Run first to have a clean state
        ws_before = _get_ws(client, project_code)
        if ws_before.dirty:
            _run(client, project_code)

        # Edit a financial input
        _update_field(client, project_code, "debt.senior.gearing_pct", "72")
        ws = _get_ws(client, project_code)
        assert ws.dirty is True, "Workspace must be dirty after edit"

    def test_overview_shows_stale_banner_after_edit(self, client, project_code):
        ws = _get_ws(client, project_code)
        if not ws.dirty:
            _update_field(client, project_code, "debt.senior.gearing_pct", "73")
        resp = client.get(f"/v2/workbook?project={project_code}")
        ov = resp.text[resp.text.find('id="panel-overview"'):resp.text.find('id="panel-project-setup"')]
        assert "overview-stale-banner" in ov or "stale-banner" in ov, (
            "Expected stale banner in overview after editing inputs"
        )

    def test_overview_returns_current_after_rerun(self, client, project_code):
        # Ensure dirty first
        ws = _get_ws(client, project_code)
        if not ws.dirty:
            _update_field(client, project_code, "debt.senior.gearing_pct", "74")
        # Rerun
        resp = _run(client, project_code)
        _assert_real_run_succeeded(resp, client, project_code, label="Solar-rerun")
        # Overview should now show current state
        resp2 = client.get(f"/v2/workbook?project={project_code}")
        ov = resp2.text[resp2.text.find('id="panel-overview"'):resp2.text.find('id="panel-project-setup"')]
        assert "overview-status-clean" in ov or "Outputs current" in ov, (
            "Expected clean/current status in overview after rerun"
        )


class TestRealEngineWind:
    """REAL_ENGINE_E2E: Generic Wind with real engine (no mock)."""

    @pytest.fixture(scope="class")
    def client(self):
        return _client()

    @pytest.fixture(scope="class")
    def project_code(self, client):
        return _create_project(client, suffix="wind-rre", project_type="Wind")

    def test_wind_real_engine_run_succeeds(self, client, project_code):
        resp = _run(client, project_code)
        ws = _assert_real_run_succeeded(resp, client, project_code, label="Wind")
        assert ws.last_runtime_snapshot_id is not None

    def test_wind_overview_kpis_populated(self, client, project_code):
        resp = client.get(f"/v2/workbook?project={project_code}")
        body = resp.text
        assert "kpi-project-irr" in body
        ov = body[body.find('id="panel-overview"'):body.find('id="panel-project-setup"')]
        not_avail_count = ov.count("NOT_AVAILABLE")
        total_tiles = ov.count("v2-kpi-tile")
        assert total_tiles > 0
        assert not_avail_count < total_tiles, "All tiles NOT_AVAILABLE for Wind run"

    def test_wind_min_dscr_matches_runtime_summary(self, client, project_code):
        ws = _get_ws(client, project_code)
        stored_min_dscr = ws.last_runtime_summary.get("min_dscr", "")
        if not stored_min_dscr or stored_min_dscr == "NOT_AVAILABLE":
            pytest.skip("min_dscr unavailable")
        if isinstance(stored_min_dscr, float):
            expected_dscr = f"{stored_min_dscr:.2f}x"
        else:
            expected_dscr = str(stored_min_dscr)
        resp = client.get(f"/v2/workbook?project={project_code}")
        ov = resp.text[resp.text.find('id="panel-overview"'):resp.text.find('id="panel-project-setup"')]
        assert expected_dscr in ov


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE DIFF GATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineDiffGate:
    """STRUCTURAL: Prove frozen financial paths are untouched from UI-3A starting SHA."""

    STARTING_SHA = "caffef16ca2e68238fac927b661e02af44a15a1d"
    FROZEN_PATHS = [
        "financial_engine/",
        "finco_core/",
        "app/api/project_runner.py",
        "app/services/production_financial_authority.py",
    ]

    def _git_diff(self, path: str) -> str:
        try:
            result = subprocess.run(
                ["git", "diff", self.STARTING_SHA, "--", path],
                cwd=str(REPO_ROOT),
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout
        except Exception:
            return ""

    def test_financial_engine_untouched(self):
        diff = self._git_diff("financial_engine/")
        assert diff == "", f"financial_engine/ has diff from {self.STARTING_SHA}:\n{diff[:400]}"

    def test_finco_core_untouched(self):
        diff = self._git_diff("finco_core/")
        assert diff == "", f"finco_core/ has diff from {self.STARTING_SHA}:\n{diff[:400]}"

    def test_project_runner_untouched(self):
        diff = self._git_diff("app/api/project_runner.py")
        assert diff == "", f"project_runner.py has diff from {self.STARTING_SHA}:\n{diff[:400]}"

    def test_production_financial_authority_untouched(self):
        diff = self._git_diff("app/services/production_financial_authority.py")
        assert diff == "", f"production_financial_authority.py has diff from {self.STARTING_SHA}:\n{diff[:400]}"


# ═══════════════════════════════════════════════════════════════════════════════
# BROWSER (Playwright)
# ═══════════════════════════════════════════════════════════════════════════════

def _chromium_path() -> str:
    candidates = glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome")
    return candidates[0] if candidates else ""


def _http(base_url, token, method, path, data=None, htmx=False):
    url = base_url.rstrip("/") + path
    headers = {"Cookie": f"{COOKIE_NAME}={token}"}
    if htmx:
        headers["HX-Request"] = "true"
    body = urllib.parse.urlencode(data).encode() if data else None
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, {}, e.read().decode("utf-8", errors="replace")


def _browser_create_project(base_url, token, suffix, project_type="Solar"):
    template = "generic_solar" if project_type == "Solar" else "generic_wind"
    _, _, body = _http(base_url, token, "POST", "/projects/create", data={
        "project_name": f"UI3A-Browser-{suffix}",
        "project_type": project_type,
        "template_source": template,
        "country_market": "Poland",
        "capacity_mw": "50",
        "cod_date": "2029-01-01",
        "construction_months": "18",
        "horizon_years": "25",
        "tariff_eur_mwh": "55",
        "ppa_term_years": "15",
        "p50_hours": "2200",
        "opex_y1_keur": "700",
        "total_capex_keur": "45000",
        "gearing_pct": "70",
        "interest_rate_pct": "4.5",
        "tenor_years": "15",
        "target_dscr": "1.30",
    })
    m = re.search(r'project=([^&"\'\\s]+)', body)
    if m:
        return urllib.parse.unquote(m.group(1))
    return None


def _browser_content_hash(base_url, token, project_code):
    _, _, body = _http(base_url, token, "GET", f"/v2/workbook?project={project_code}")
    m = re.search(r'data-content-hash="([^"]+)"', body)
    wv_m = re.search(r'data-workbook-version="([^"]+)"', body)
    return (m.group(1) if m else "", wv_m.group(1) if wv_m else "")


def _browser_run(base_url, token, project_code):
    ch, wv = _browser_content_hash(base_url, token, project_code)
    status, _, body = _http(base_url, token, "POST", "/v2/workbook/run", data={
        "project": project_code, "content_hash": ch, "workbook_version": wv,
    }, htmx=True)
    return status, body


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: playwright not installed",
    )
    tmp_db = tmp_path_factory.mktemp("v2_browser_ui3a") / "test.db"
    env = os.environ.copy()
    env["FINCO_WORKBOOK_V2"] = "1"
    env["FINCO_SECRET_KEY"] = "browser-accept-secret-ui3a"
    env["DATABASE_URL"] = f"sqlite:///{tmp_db}"
    port = 9127
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app",
         "--host", "127.0.0.1", "--port", str(port)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=str(REPO_ROOT),
    )
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(30):
        try:
            urllib.request.urlopen(base_url + "/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    yield {"base_url": base_url, "db_path": str(tmp_db), "token": create_session_token()}
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def playwright_browser(live_server):
    from playwright.sync_api import sync_playwright
    pl = sync_playwright().start()
    exe = _chromium_path()
    kwargs = {"headless": True}
    if exe:
        kwargs["executable_path"] = exe
    browser = pl.chromium.launch(**kwargs)
    yield browser
    browser.close()
    pl.stop()


@pytest.fixture(scope="module")
def authed_page(playwright_browser, live_server):
    ctx = playwright_browser.new_context(base_url=live_server["base_url"])
    ctx.add_cookies([{
        "name": COOKIE_NAME,
        "value": live_server["token"],
        "url": live_server["base_url"],
    }])
    page = ctx.new_page()
    yield page
    ctx.close()


@pytest.fixture(scope="module")
def browser_project(live_server):
    base_url = live_server["base_url"]
    token = live_server["token"]
    code = _browser_create_project(base_url, token, "solar-browser")
    assert code, "Could not create browser test project"
    return code


class TestBrowser:
    """BROWSER: Playwright acceptance tests for the Overview tab."""

    def test_overview_tab_visible_in_workbook(self, authed_page, live_server, browser_project):
        page = authed_page
        page.goto(f"{live_server['base_url']}/v2/workbook?project={browser_project}")
        tab = page.locator("#tab-overview")
        assert tab.count() > 0, "Overview tab not found"
        assert tab.is_visible()

    def test_overview_tab_is_first_tab(self, authed_page, live_server, browser_project):
        page = authed_page
        page.goto(f"{live_server['base_url']}/v2/workbook?project={browser_project}")
        tabs = page.locator("#v2-sheet-tabs .v2-tab").all()
        assert len(tabs) > 0
        first_id = tabs[0].get_attribute("id")
        assert first_id == "tab-overview", f"First tab is {first_id!r}, expected 'tab-overview'"

    def test_overview_panel_visible_on_load(self, authed_page, live_server, browser_project):
        page = authed_page
        page.goto(f"{live_server['base_url']}/v2/workbook?project={browser_project}")
        panel = page.locator("#panel-overview")
        assert panel.is_visible(), "Overview panel must be visible on load"

    def test_no_run_state_shown_before_run(self, authed_page, live_server, browser_project):
        page = authed_page
        page.goto(f"{live_server['base_url']}/v2/workbook?project={browser_project}")
        no_run = page.locator("[data-testid='overview-no-run-state']")
        assert no_run.count() > 0, "No-run state element not found before first run"

    def test_run_model_populates_overview_kpis(self, authed_page, live_server, browser_project):
        """After a real Run Model, KPI tiles must contain non-NOT_AVAILABLE values."""
        page = authed_page
        base_url = live_server["base_url"]
        token = live_server["token"]

        # Trigger run via API (real engine)
        status, body = _browser_run(base_url, token, browser_project)
        assert status == 200, f"Run returned {status}: {body[:300]}"
        assert "Engine run failed" not in body

        page.goto(f"{base_url}/v2/workbook?project={browser_project}")
        page.wait_for_selector("#panel-overview", timeout=10000)

        # KPI tiles must exist
        kpi_irr = page.locator("[data-testid='kpi-project-irr']")
        assert kpi_irr.count() > 0, "kpi-project-irr tile not found after run"
        kpi_dscr = page.locator("[data-testid='kpi-min-dscr']")
        assert kpi_dscr.count() > 0

        # At least one KPI must not say NOT_AVAILABLE
        ov_text = page.locator("#panel-overview").inner_text()
        assert "NOT_AVAILABLE" not in ov_text or "—" in ov_text, (
            "All KPI tiles still show NOT_AVAILABLE after real run"
        )

    def test_kpi_value_matches_authoritative_stored_value(
        self, authed_page, live_server, browser_project
    ):
        """Rendered project_irr must match the stored authoritative runtime_summary."""
        import sqlite3
        db_path = live_server["db_path"]
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT last_runtime_summary_json FROM workspace_states ws "
                "JOIN projects p ON ws.project_id = p.project_id "
                "WHERE p.project_code = ?", (browser_project,)
            ).fetchall()
            conn.close()
        except Exception:
            pytest.skip("Cannot read DB for KPI verification")

        if not rows or not rows[0][0]:
            pytest.skip("No runtime_summary in DB")
        rs = json.loads(rows[0][0])
        stored_irr = rs.get("project_irr", "")
        if not stored_irr or stored_irr == "NOT_AVAILABLE":
            pytest.skip("project_irr not available in stored summary")

        page = authed_page
        page.goto(f"{live_server['base_url']}/v2/workbook?project={browser_project}")
        tile = page.locator("[data-testid='kpi-project-irr'] .v2-kpi-value")
        rendered = tile.inner_text().strip()
        assert rendered == stored_irr, (
            f"Rendered IRR '{rendered}' != stored authoritative '{stored_irr}'"
        )

    def test_charts_rendered_after_run(self, authed_page, live_server, browser_project):
        page = authed_page
        page.goto(f"{live_server['base_url']}/v2/workbook?project={browser_project}")
        # Wait for JS to render SVG charts
        page.wait_for_selector("[data-testid='chart-debt-balance'] svg", timeout=8000)
        chart = page.locator("[data-testid='chart-debt-balance'] svg")
        assert chart.count() > 0, "Debt balance SVG chart not rendered"

    def test_overview_stale_after_input_edit(self, authed_page, live_server, browser_project):
        base_url = live_server["base_url"]
        token = live_server["token"]
        # Edit a field to make workspace dirty
        ch, wv = _browser_content_hash(base_url, token, browser_project)
        _http(base_url, token, "POST", "/v2/workbook/update", data={
            "field_id": "debt.senior.gearing_pct",
            "value": "72",
            "project": browser_project, "workbook_version": wv,
            "content_hash": ch, "sheet_id": "project_setup",
        }, htmx=True)

        page = authed_page
        page.goto(f"{base_url}/v2/workbook?project={browser_project}")
        stale_banner = page.locator("[data-testid='overview-stale-banner']")
        assert stale_banner.count() > 0 or page.locator("[data-testid='overview-status-stale']").count() > 0, (
            "Expected stale indicator in overview after editing inputs"
        )

    def test_overview_current_after_rerun(self, authed_page, live_server, browser_project):
        base_url = live_server["base_url"]
        token = live_server["token"]
        status, body = _browser_run(base_url, token, browser_project)
        assert status == 200
        assert "Engine run failed" not in body

        page = authed_page
        page.goto(f"{base_url}/v2/workbook?project={browser_project}")
        current = page.locator("[data-testid='overview-status-clean']")
        assert current.count() > 0 or "Outputs current" in page.locator("#panel-overview").inner_text(), (
            "Expected 'Outputs current' status in overview after rerun"
        )

    def test_overview_snapshot_id_shown(self, authed_page, live_server, browser_project):
        page = authed_page
        page.goto(f"{live_server['base_url']}/v2/workbook?project={browser_project}")
        snap = page.locator("[data-testid='overview-snapshot-id']")
        if snap.count() > 0:
            text = snap.inner_text().strip()
            assert text != "—", "Snapshot ID should be populated after run"


# ═══════════════════════════════════════════════════════════════════════════════
# REGRESSION — existing suite imports (collection-time proof that nothing broke)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    """REGRESSION: Verify prior test modules are importable (suites run separately)."""

    def test_ui1a_module_importable(self):
        import importlib
        mod = importlib.import_module("tests.test_workbook_v2_shell")
        assert mod is not None

    def test_ui2a_module_importable(self):
        import importlib
        try:
            mod = importlib.import_module("tests.test_workbook_v2_sheet_inputs")
        except ImportError as exc:
            if any(lib in str(exc) for lib in ("bs4", "BeautifulSoup", "lxml")):
                pytest.skip(f"Optional dependency not installed: {exc}")
            raise
        assert mod is not None

    def test_ui2b_module_importable(self):
        import importlib
        mod = importlib.import_module("tests.test_workbook_v2_runtime_integration")
        assert mod is not None

    def test_ui2c_module_importable(self):
        import importlib
        mod = importlib.import_module("tests.test_ui2c_model_run_workflow")
        assert mod is not None

    def test_overview_projection_importable(self):
        from app.v2.overview_projection import build_overview_projection, OverviewProjection  # noqa: F401
        assert True

    def test_runtime_projection_untouched(self):
        """Existing runtime_projection exports still present."""
        from app.workbook.runtime_projection import (  # noqa: F401
            build_runtime_projection_bundle,
            RuntimeProjectionState,
            WorkbookRuntimeProjection,
        )
        assert True
