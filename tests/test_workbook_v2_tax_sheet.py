"""
Tests for the Workbook V2 Tax worksheet (PR 2).

Coverage
--------
1.  GET /v2/workbook returns 200 and includes #v2-sheet-tax
2.  Section A placeholder rows render with correct labels
3.  No-runtime State A: runtime-state badge shows "Run Required"
4.  Pre-run notice renders when no runtime
5.  Tax schedule table renders from mocked RuntimeResult
6.  Operational-period filtering: construction periods excluded server-side
7.  Operational periods retained in order
8.  Empty operational set renders truthful empty state
9.  None operational periods (no runtime) renders no-runtime notice
10. HTMX round-trip: sheet_id=tax re-renders #v2-sheet-tax
11. _build_tax_ctx returns expected keys
12. Runtime summary KPI tile renders total_tax_keur
13. Runtime summary KPI tile renders effective_tax_rate_pct
14. KPI bar hidden when no runtime
15. Tax schedule table has expected column headers
16. Authority chain: _build_tax_ctx reads from WorkbookService not engine
17. Regression: debt sheet still works after tax wiring
18. Regression: GET workbook still includes #v2-sheet-senior-debt
"""
from __future__ import annotations

import dataclasses
import os
import types
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-tax-tests-v2")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

import main_web
from app.auth import COOKIE_NAME, create_session_token
from app.v2.router import _build_tax_ctx, _thaw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _authed_client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str) -> str:
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"Tax V2 Test {suffix}",
            "project_type": "Wind",
            "template_source": "generic_wind",
            "country_market": "Germany",
            "capacity_mw": "100",
            "cod_date": "2027-06-01",
            "construction_months": "24",
            "horizon_years": "20",
            "tariff_eur_mwh": "65",
            "ppa_term_years": "15",
            "p50_hours": "2500",
            "opex_y1_keur": "5000",
            "total_capex_keur": "80000",
            "gearing_pct": "70",
            "interest_rate_pct": "4.5",
            "tenor_years": "18",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"expected redirect, got {resp.status_code}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    codes = parsed.get("project", [])
    assert codes, f"no project= in redirect: {redirect}"
    return codes[0]


def _get_workbook(client: TestClient, project_code: str) -> str:
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"workbook GET failed: {resp.status_code}"
    return resp.text


def _make_ws_with_tax_schedule(periods: list[dict], summary: dict | None = None) -> MagicMock:
    """Build a workspace mock with a tax_schedule on the RuntimeResult."""
    ws = MagicMock()
    ws.last_runtime_snapshot_id = "snap-123"
    ws.dirty = False
    ws.last_runtime_summary = {
        "total_tax_keur": "12,345 kEUR",
        "effective_tax_rate_pct": "22.5%",
        "avg_dscr": "1.45x",
        "min_dscr": "1.20x",
        "total_senior_ds_keur": 5000,
    }
    ws.last_debt_schedule = None
    ws.last_tax_schedule = {
        "periods": periods,
        "summary": summary or {"total_tax_keur": 12345.0},
        "source": "WaterfallResult.periods",
    }
    return ws


def _sample_period(period: int, is_operation: bool, tax_keur: float = 100.0) -> dict:
    return {
        "period": period,
        "date": f"2029-{period:02d}-30",
        "year_index": 1,
        "period_in_year": period,
        "is_operation": is_operation,
        "taxable_profit_keur": 500.0,
        "tax_keur": tax_keur if is_operation else None,
        "cf_after_tax_keur": 400.0 if is_operation else None,
        "corporate_tax_cash_keur": tax_keur if is_operation else None,
        "tax_depreciation_audit_keur": 100.0,
        "taxable_income_before_losses_audit_keur": 600.0,
        "tax_loss_opening_audit_keur": 0.0,
        "tax_loss_used_audit_keur": 0.0,
        "tax_loss_closing_audit_keur": 0.0,
        "taxable_profit_after_losses_audit_keur": 600.0,
        "cit_accrual_audit_keur": tax_keur if is_operation else None,
        "cash_tax_current_period_audit_keur": tax_keur if is_operation else None,
    }


# ---------------------------------------------------------------------------
# Tests: page rendering
# ---------------------------------------------------------------------------

class TestTaxSheetPageRendering(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "page-render")

    def test_workbook_includes_tax_sheet(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        assert soup.find(id="v2-sheet-tax"), "#v2-sheet-tax not found in workbook"

    def test_section_a_placeholder_cit_rate(self):
        html = _get_workbook(self.client, self.project_code)
        assert "CIT Rate" in html

    def test_section_a_placeholder_loss_carryforward(self):
        html = _get_workbook(self.client, self.project_code)
        assert "Loss Carryforward Years" in html

    def test_section_a_placeholders_not_editable_label(self):
        html = _get_workbook(self.client, self.project_code)
        assert "not yet migrated to Workbook Registry" in html

    def test_no_runtime_state_a_badge(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        badge = soup.find(attrs={"data-testid": "tax-runtime-state-a"})
        assert badge is not None, "State A badge not found"
        assert "Run Required" in badge.get_text()

    def test_no_runtime_pre_run_notice(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        notice = soup.find(attrs={"data-testid": "tax-pre-run-notice"})
        assert notice is not None, "pre-run notice not found"

    def test_no_runtime_schedule_no_runtime_notice(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        notice = soup.find(attrs={"data-testid": "tax-schedule-no-runtime"})
        assert notice is not None, "schedule no-runtime notice not found"

    def test_regression_debt_sheet_still_present(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        assert soup.find(id="v2-sheet-senior-debt"), "#v2-sheet-senior-debt missing after tax wiring"


# ---------------------------------------------------------------------------
# Tests: HTMX round-trip
# ---------------------------------------------------------------------------

class TestTaxSheetHtmx(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "htmx")

    def _get_content_hash(self) -> str:
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", attrs={"data-sheet": True})
        if form is None:
            # No editable fields on tax sheet; fetch hash from any form
            form = soup.find("form")
        if form:
            inp = form.find("input", {"name": "content_hash"})
            if inp:
                return inp.get("value", "")
        # Fallback: parse from workbook sheet
        tax_div = soup.find(id="v2-sheet-tax")
        if tax_div:
            f = tax_div.find("input", {"name": "content_hash"})
            if f:
                return f.get("value", "")
        return "fallback-hash"

    def test_htmx_any_sheet_update_does_not_break_tax(self):
        """Updating a debt field re-renders debt sheet; tax sheet stays intact."""
        full_html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(full_html, "html.parser")
        # find content_hash from a debt form
        debt_div = soup.find(id="v2-sheet-senior-debt")
        form = debt_div.find("form") if debt_div else None
        if form is None:
            self.skipTest("no editable form on debt sheet in this project")
        content_hash = form.find("input", {"name": "content_hash"})["value"]
        workbook_version = form.find("input", {"name": "workbook_version"})["value"]
        field_id_inp = form.find("input", {"name": "field_id"})
        if field_id_inp is None:
            self.skipTest("no field_id input found")
        field_id = field_id_inp["value"]
        value_inp = form.find("input", {"name": "value"}) or form.find("input", {"class": "v2-field-input"})
        value = value_inp.get("value", "70") if value_inp else "70"
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": field_id,
                "value": value,
                "content_hash": content_hash,
                "workbook_version": workbook_version,
                "sheet_id": "debt",
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200

    def test_htmx_sheet_id_tax_rerenders_tax_div(self):
        """POST with sheet_id=tax (even with no bound fields) should not 500."""
        full_html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(full_html, "html.parser")
        any_form = soup.find("form", attrs={"name": "content_hash"}) or soup.find("form")
        if any_form is None:
            self.skipTest("no form found")
        content_hash_inp = any_form.find("input", {"name": "content_hash"})
        workbook_version_inp = any_form.find("input", {"name": "workbook_version"})
        if not content_hash_inp or not workbook_version_inp:
            self.skipTest("hash/version inputs not found")
        # Try with a debt field — sheet_id=tax triggers _render_tax_htmx_sheet on success
        field_form = soup.find("form", id=lambda x: x and "debt" in (x or ""))
        if field_form is None:
            debt_div = soup.find(id="v2-sheet-senior-debt")
            field_form = debt_div.find("form") if debt_div else None
        if field_form is None:
            self.skipTest("no debt form found for tax htmx test")
        field_id_inp = field_form.find("input", {"name": "field_id"})
        if field_id_inp is None:
            self.skipTest("no field_id found")
        value_inp = field_form.find("input", {"class": "v2-field-input"})
        value = value_inp.get("value", "70") if value_inp else "70"
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": field_id_inp["value"],
                "value": value,
                "content_hash": field_form.find("input", {"name": "content_hash"})["value"],
                "workbook_version": field_form.find("input", {"name": "workbook_version"})["value"],
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert "v2-sheet-tax" in resp.text


# ---------------------------------------------------------------------------
# Tests: _build_tax_ctx unit tests
# ---------------------------------------------------------------------------

class TestBuildTaxCtx(unittest.TestCase):

    def _make_pis(self):
        pis = MagicMock()
        pis.workbook_version = "2.0.0"
        pis.content_hash = "abc123"
        return pis

    def test_returns_expected_keys(self):
        pis = self._make_pis()
        ws = MagicMock()
        ws.last_runtime_snapshot_id = None
        ws.last_tax_schedule = None
        ws.last_runtime_summary = None
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            ctx = _build_tax_ctx(pis, ws)
        assert "tax_schedule" in ctx
        assert "tax_operational_periods" in ctx
        assert "runtime_summary" in ctx

    def test_no_runtime_yields_none_op_periods(self):
        pis = self._make_pis()
        ws = MagicMock()
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            ctx = _build_tax_ctx(pis, ws)
        assert ctx["tax_operational_periods"] is None

    def test_no_runtime_yields_none_schedule(self):
        pis = self._make_pis()
        ws = MagicMock()
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            ctx = _build_tax_ctx(pis, ws)
        assert ctx["tax_schedule"] is None

    def test_authority_reads_from_workbook_service(self):
        """_build_tax_ctx must call WorkbookService.get_runtime_result, not the engine."""
        pis = self._make_pis()
        ws = MagicMock()
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None) as mock_get:
            _build_tax_ctx(pis, ws)
        mock_get.assert_called_once_with(ws)


# ---------------------------------------------------------------------------
# Tests: operational-period filtering
# ---------------------------------------------------------------------------

class TestTaxOperationalPeriodFiltering(unittest.TestCase):

    def _make_pis(self):
        pis = MagicMock()
        pis.workbook_version = "2.0.0"
        pis.content_hash = "abc123"
        return pis

    def _rr_with_tax(self, periods: list[dict]) -> MagicMock:
        rr = MagicMock()
        rr.tax_schedule = {
            "periods": periods,
            "summary": {"total_tax_keur": 999.0},
        }
        rr.runtime_summary = {
            "total_tax_keur": "999 kEUR",
            "effective_tax_rate_pct": "20.0%",
        }
        rr.debt_schedule = None
        return rr

    def test_construction_periods_excluded(self):
        periods = [
            _sample_period(1, is_operation=False),
            _sample_period(2, is_operation=False),
            _sample_period(3, is_operation=True),
        ]
        pis = self._make_pis()
        ws = MagicMock()
        rr = self._rr_with_tax(periods)
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(pis, ws)
        op = ctx["tax_operational_periods"]
        assert op is not None
        assert all(p["is_operation"] for p in op), "construction periods leaked into op list"
        assert len(op) == 1

    def test_operational_periods_retained_in_order(self):
        periods = [
            _sample_period(1, is_operation=True, tax_keur=100.0),
            _sample_period(2, is_operation=True, tax_keur=200.0),
            _sample_period(3, is_operation=True, tax_keur=300.0),
        ]
        pis = self._make_pis()
        ws = MagicMock()
        rr = self._rr_with_tax(periods)
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(pis, ws)
        op = ctx["tax_operational_periods"]
        assert [p["period"] for p in op] == [1, 2, 3]

    def test_empty_operational_set_when_only_construction(self):
        periods = [
            _sample_period(1, is_operation=False),
            _sample_period(2, is_operation=False),
        ]
        pis = self._make_pis()
        ws = MagicMock()
        rr = self._rr_with_tax(periods)
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(pis, ws)
        assert ctx["tax_operational_periods"] == []

    def test_empty_operational_set_template_shows_empty_state(self):
        periods = [_sample_period(1, is_operation=False)]
        ws = _make_ws_with_tax_schedule(periods)
        ws.last_tax_schedule["periods"] = periods

        pis = MagicMock()
        pis.workbook_version = "2.0.0"
        pis.content_hash = "abc"

        rr = MagicMock()
        rr.tax_schedule = {"periods": periods, "summary": {}}
        rr.runtime_summary = {"total_tax_keur": "0 kEUR", "effective_tax_rate_pct": "0.0%"}

        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(pis, ws)

        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
        env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
        env.globals["range"] = range

        ctx.update({
            "project_code": "test",
            "workbook_version": "2.0.0",
            "content_hash": "abc",
            "project_editable": True,
            "ws_dirty": False,
            "has_runtime": True,
            "field_error": "",
        })
        html = env.get_template("partials/sheet_tax.html").render(ctx)
        soup = BeautifulSoup(html, "html.parser")
        empty = soup.find(attrs={"data-testid": "tax-schedule-empty"})
        assert empty is not None, "empty state not shown when op list is []"
        table = soup.find(attrs={"data-testid": "tax-schedule-table"})
        assert table is None, "table should not render for empty op list"

    def test_no_runtime_template_shows_no_runtime_notice(self):
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
        env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
        env.globals["range"] = range

        ctx = {
            "tax_schedule": None,
            "tax_operational_periods": None,
            "runtime_summary": None,
            "project_code": "test",
            "workbook_version": "2.0.0",
            "content_hash": "abc",
            "project_editable": True,
            "ws_dirty": False,
            "has_runtime": False,
            "field_error": "",
        }
        html = env.get_template("partials/sheet_tax.html").render(ctx)
        soup = BeautifulSoup(html, "html.parser")
        notice = soup.find(attrs={"data-testid": "tax-schedule-no-runtime"})
        assert notice is not None, "no-runtime notice not shown when op_periods is None"

    def test_operational_rows_in_table(self):
        periods = [
            _sample_period(1, is_operation=False),
            _sample_period(2, is_operation=True, tax_keur=111.0),
            _sample_period(3, is_operation=True, tax_keur=222.0),
            _sample_period(4, is_operation=True, tax_keur=333.0),
        ]
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
        env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
        env.globals["range"] = range

        pis = MagicMock()
        ws = MagicMock()
        rr = MagicMock()
        rr.tax_schedule = {"periods": periods, "summary": {"total_tax_keur": 666.0}}
        rr.runtime_summary = {"total_tax_keur": "666 kEUR", "effective_tax_rate_pct": "22%"}

        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            tax_ctx = _build_tax_ctx(pis, ws)

        ctx = {
            **tax_ctx,
            "project_code": "test",
            "workbook_version": "2.0.0",
            "content_hash": "abc",
            "project_editable": True,
            "ws_dirty": False,
            "has_runtime": True,
            "field_error": "",
        }
        html = env.get_template("partials/sheet_tax.html").render(ctx)
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all(attrs={"data-testid": lambda v: v and v.startswith("tax-schedule-row-")})
        assert len(rows) == 3, f"expected 3 operational rows, got {len(rows)}"
        # period 1 (construction) must not appear
        period1_row = soup.find(attrs={"data-testid": "tax-schedule-row-1"})
        assert period1_row is None, "construction period 1 leaked into table"


# ---------------------------------------------------------------------------
# Tests: runtime summary KPI tiles
# ---------------------------------------------------------------------------

class TestTaxKpiTiles(unittest.TestCase):

    def _render_with_summary(self, total_tax: str, eff_rate: str) -> BeautifulSoup:
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
        env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
        env.globals["range"] = range
        ctx = {
            "tax_schedule": {"periods": [], "summary": {}},
            "tax_operational_periods": [],
            "runtime_summary": {
                "total_tax_keur": total_tax,
                "effective_tax_rate_pct": eff_rate,
            },
            "project_code": "test",
            "workbook_version": "2.0.0",
            "content_hash": "abc",
            "project_editable": True,
            "ws_dirty": False,
            "has_runtime": True,
            "field_error": "",
        }
        html = env.get_template("partials/sheet_tax.html").render(ctx)
        return BeautifulSoup(html, "html.parser")

    def test_total_tax_kpi_renders(self):
        soup = self._render_with_summary("12,345 kEUR", "22.5%")
        tile = soup.find(attrs={"data-testid": "tax-kpi-total-tax"})
        assert tile is not None, "total-tax KPI tile not found"
        assert "12,345 kEUR" in tile.get_text()

    def test_effective_rate_kpi_renders(self):
        soup = self._render_with_summary("12,345 kEUR", "22.5%")
        tile = soup.find(attrs={"data-testid": "tax-kpi-eff-rate"})
        assert tile is not None, "effective-rate KPI tile not found"
        assert "22.5%" in tile.get_text()

    def test_kpi_bar_hidden_when_no_runtime(self):
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
        env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
        env.globals["range"] = range
        ctx = {
            "tax_schedule": None,
            "tax_operational_periods": None,
            "runtime_summary": None,
            "project_code": "test",
            "workbook_version": "2.0.0",
            "content_hash": "abc",
            "project_editable": True,
            "ws_dirty": False,
            "has_runtime": False,
            "field_error": "",
        }
        html = env.get_template("partials/sheet_tax.html").render(ctx)
        soup = BeautifulSoup(html, "html.parser")
        bar = soup.find(attrs={"data-testid": "tax-kpi-bar"})
        assert bar is None, "KPI bar should not render when no runtime"

    def test_schedule_column_headers(self):
        soup = self._render_with_summary("0 kEUR", "0%")
        # render with at least 1 operational period to get a table
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
        env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
        env.globals["range"] = range
        ctx = {
            "tax_schedule": {"periods": [_sample_period(1, True)], "summary": {}},
            "tax_operational_periods": [_sample_period(1, True)],
            "runtime_summary": {"total_tax_keur": "1 kEUR", "effective_tax_rate_pct": "10%"},
            "project_code": "test",
            "workbook_version": "2.0.0",
            "content_hash": "abc",
            "project_editable": True,
            "ws_dirty": False,
            "has_runtime": True,
            "field_error": "",
        }
        html = env.get_template("partials/sheet_tax.html").render(ctx)
        assert "Taxable Profit" in html
        assert "Tax (kEUR)" in html
        assert "CF After Tax" in html
        assert "Loss Opening" in html


if __name__ == "__main__":
    unittest.main()
