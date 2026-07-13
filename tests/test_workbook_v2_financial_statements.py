"""
Tests for the Workbook V2 Financial Statements worksheet (PR 3/6).

Coverage
--------
Template rendering — no runtime
  1.  GET /v2/workbook includes #v2-sheet-financial-statements
  2.  No-runtime state badge shows "Run Required"
  3.  No-runtime notice for Income Statement
  4.  No-runtime notice for PF Cash Waterfall
  5.  No-runtime notice for Balance Sheet

Template rendering — with runtime (mocked RuntimeResult)
  6.  Income Statement table renders when fs_pnl_periods is present
  7.  PF Cash Waterfall table renders when fs_pf_cf_periods is present
  8.  Balance Sheet table renders when fs_bs_periods is present
  9.  PARTIAL badge present on all three statement sections
  10. PARTIAL notices present on all three sections
  11. Income Statement rows map payload keys correctly
  12. PF Cash Waterfall rows map payload keys correctly
  13. Balance Sheet rows map payload keys correctly
  14. Share capital footnote present on Balance Sheet
  15. Dates rendered as YYYY-MM (first 7 chars of ISO date)
  16. None values render as dash (—)

_build_financial_statements_ctx unit tests
  17. Returns fs_available=False when ws has no runtime result
  18. Returns fs_available=True when ws has runtime result
  19. Returns None period lists when no runtime (not empty lists)
  20. Returns correct period lists from RuntimeResult payload
  21. All three classification keys are "PARTIAL"
  22. runtime_summary key is present

Runtime state badge variants
  23. State B (clean): "Outputs current" when has_runtime and not ws_dirty
  24. State C (dirty): "Previous run — stale" when has_runtime and ws_dirty

No arithmetic in context builder
  25. Period dicts passed verbatim — no values summed or transformed

Regression
  26. Tax sheet still present after financial_statements wiring
  27. Debt sheet still present after financial_statements wiring
"""
from __future__ import annotations

import os
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-fs-tests-v2")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

import main_web
from app.auth import COOKIE_NAME, create_session_token
from app.workbook.runtime_result import RuntimeResult


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
            "project_name": f"FS V2 Test {suffix}",
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


def _get_workbook(client: TestClient, project_code: str) -> BeautifulSoup:
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"workbook GET failed: {resp.status_code}"
    return BeautifulSoup(resp.text, "html.parser")


def _sample_pnl_period(n: int) -> dict:
    return {
        "period": n,
        "date": f"2029-{n:02d}-30",
        "year_index": 1,
        "period_in_year": n,
        "revenues_keur": 1000.0 + n,
        "operating_expenses_keur": 200.0 + n,
        "depreciation_keur": 100.0,
        "ebit_keur": 700.0 + n,
        "senior_interest_expense_keur": 50.0,
        "shl_interest_expense_keur": 10.0,
        "earnings_before_tax_keur": 640.0 + n,
        "cit_accrual_keur": 115.2 + n,
        "net_income_keur": 524.8 + n,
        "retained_earnings_keur": 524.8 + n,
        "net_dividends_keur": 400.0,
    }


def _sample_bs_period(n: int) -> dict:
    return {
        "period_index": n,
        "date": f"2029-{n:02d}-30",
        "net_fixed_assets_keur": 75000.0,
        "dsra_balance_keur": 500.0,
        "cash_keur": 200.0,
        "total_assets_keur": 75700.0,
        "share_capital_keur": 0.0,
        "retained_earnings_keur": 524.8,
        "shl_balance_keur": 10000.0,
        "senior_balance_keur": 40000.0,
        "total_liabilities_equity_keur": 75700.0,
        "balance_check_keur": 0.0,
    }


def _sample_pf_cf_period(n: int) -> dict:
    return {
        "period_index": n,
        "date": f"2029-{n:02d}-30",
        "revenue_cash_keur": 1000.0 + n,
        "opex_cash_keur": 200.0 + n,
        "ebitda_cash_keur": 800.0 + n,
        "cash_tax_keur": 115.2,
        "fcf_banks_keur": 684.8,
        "senior_total_ds_keur": 300.0,
        "dsra_funding_keur": 50.0,
        "dsra_release_keur": 0.0,
        "fcf_junior_keur": 334.8,
        "fcf_for_distribution_keur": 334.8,
        "net_dividends_keur": 300.0,
    }


def _make_mock_rr(num_periods: int = 2) -> RuntimeResult:
    """Build a mock RuntimeResult with plausible financial_statements payload."""
    pnl_periods = [_sample_pnl_period(i + 1) for i in range(num_periods)]
    bs_periods = [_sample_bs_period(i + 1) for i in range(num_periods)]
    pf_cf_periods = [_sample_pf_cf_period(i + 1) for i in range(num_periods)]
    fs_payload = {
        "pnl": {"periods": pnl_periods},
        "balance_sheet": {"periods": bs_periods},
        "pf_cash_waterfall": {"periods": pf_cf_periods},
    }
    mock_rr = MagicMock(spec=RuntimeResult)
    mock_rr.financial_statements = fs_payload
    mock_rr.runtime_summary = {
        "total_tax_keur": "230 kEUR",
        "effective_tax_rate_pct": "18.0%",
    }
    mock_rr.tax_schedule = None
    mock_rr.debt_schedule = None
    mock_rr.distribution_schedule = None
    mock_rr.sponsor_schedule = None
    return mock_rr


def _render_fs_template(ctx: dict) -> BeautifulSoup:
    from jinja2 import Environment, FileSystemLoader
    tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
    env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
    env.globals["range"] = range
    html = env.get_template("partials/sheet_financial_statements.html").render(ctx)
    return BeautifulSoup(html, "html.parser")


def _base_ctx(**overrides) -> dict:
    ctx = {
        "project_code": "TEST-FS",
        "workbook_version": "2.1.0",
        "content_hash": "abc123",
        "project_editable": True,
        "ws_dirty": False,
        "has_runtime": False,
        "field_error": "",
        "fs_available": False,
        "fs_pnl_periods": None,
        "fs_bs_periods": None,
        "fs_pf_cf_periods": None,
        "fs_pnl_classification": "PARTIAL",
        "fs_bs_classification": "PARTIAL",
        "fs_pf_cf_classification": "PARTIAL",
        "runtime_summary": None,
    }
    ctx.update(overrides)
    return ctx


# ---------------------------------------------------------------------------
# 1–5. No-runtime rendering
# ---------------------------------------------------------------------------

class TestFinancialStatementsNoRuntime(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "NoRuntime")
        self.soup = _get_workbook(self.client, self.project_code)

    def test_sheet_div_present(self):
        div = self.soup.find(id="v2-sheet-financial-statements")
        assert div is not None, "#v2-sheet-financial-statements not found in workbook"

    def test_runtime_state_a_badge(self):
        div = self.soup.find(id="v2-sheet-financial-statements")
        badge = div.find(attrs={"data-testid": "fs-runtime-state-a"})
        assert badge is not None, "Run Required badge not found"
        assert "Run Required" in badge.get_text()

    def test_pnl_no_runtime_notice(self):
        div = self.soup.find(id="v2-sheet-financial-statements")
        notice = div.find(attrs={"data-testid": "fs-pnl-no-runtime"})
        assert notice is not None, "PNL no-runtime notice not found"

    def test_pf_cf_no_runtime_notice(self):
        div = self.soup.find(id="v2-sheet-financial-statements")
        notice = div.find(attrs={"data-testid": "fs-pf-cf-no-runtime"})
        assert notice is not None, "PF CF no-runtime notice not found"

    def test_bs_no_runtime_notice(self):
        div = self.soup.find(id="v2-sheet-financial-statements")
        notice = div.find(attrs={"data-testid": "fs-bs-no-runtime"})
        assert notice is not None, "BS no-runtime notice not found"


# ---------------------------------------------------------------------------
# 6–16. Template rendering with mocked RuntimeResult
# ---------------------------------------------------------------------------

class TestFinancialStatementsWithRuntime(unittest.TestCase):

    def setUp(self):
        self.pnl_periods = [_sample_pnl_period(1), _sample_pnl_period(2)]
        self.bs_periods = [_sample_bs_period(1), _sample_bs_period(2)]
        self.pf_cf_periods = [_sample_pf_cf_period(1), _sample_pf_cf_period(2)]
        ctx = _base_ctx(
            has_runtime=True,
            fs_available=True,
            fs_pnl_periods=self.pnl_periods,
            fs_bs_periods=self.bs_periods,
            fs_pf_cf_periods=self.pf_cf_periods,
        )
        self.soup = _render_fs_template(ctx)

    def test_pnl_table_renders(self):
        table = self.soup.find(attrs={"data-testid": "fs-pnl-table"})
        assert table is not None, "Income Statement table not found"

    def test_pf_cf_table_renders(self):
        table = self.soup.find(attrs={"data-testid": "fs-pf-cf-table"})
        assert table is not None, "PF Cash Waterfall table not found"

    def test_bs_table_renders(self):
        table = self.soup.find(attrs={"data-testid": "fs-bs-table"})
        assert table is not None, "Balance Sheet table not found"

    def test_partial_badge_pnl(self):
        div = self.soup.find(id="nav-fs-pnl")
        assert div is not None
        assert "PARTIAL" in div.get_text()

    def test_partial_badge_pf_cf(self):
        div = self.soup.find(id="nav-fs-pf-cf")
        assert div is not None
        assert "PARTIAL" in div.get_text()

    def test_partial_badge_bs(self):
        div = self.soup.find(id="nav-fs-bs")
        assert div is not None
        assert "PARTIAL" in div.get_text()

    def test_partial_notice_pnl(self):
        notice = self.soup.find(attrs={"data-testid": "fs-pnl-partial-notice"})
        assert notice is not None
        assert "PARTIAL" in notice.get_text()

    def test_partial_notice_pf_cf(self):
        notice = self.soup.find(attrs={"data-testid": "fs-pf-cf-partial-notice"})
        assert notice is not None
        assert "PARTIAL" in notice.get_text()

    def test_partial_notice_bs(self):
        notice = self.soup.find(attrs={"data-testid": "fs-bs-partial-notice"})
        assert notice is not None
        assert "PARTIAL" in notice.get_text()

    def test_pnl_revenue_row_present(self):
        row = self.soup.find(attrs={"data-testid": "fs-pnl-row-revenues_keur"})
        assert row is not None, "revenues_keur row missing from PNL table"
        # value from period 1: 1001.0 → rounded to 0 dp = "1001"
        assert "1001" in row.get_text()

    def test_pnl_net_income_row_present(self):
        row = self.soup.find(attrs={"data-testid": "fs-pnl-row-net_income_keur"})
        assert row is not None, "net_income_keur row missing from PNL table"

    def test_pf_cf_ebitda_row_present(self):
        row = self.soup.find(attrs={"data-testid": "fs-pf-cf-row-ebitda_cash_keur"})
        assert row is not None, "ebitda_cash_keur row missing from PF CF table"

    def test_pf_cf_fcf_for_distribution_row_present(self):
        row = self.soup.find(attrs={"data-testid": "fs-pf-cf-row-fcf_for_distribution_keur"})
        assert row is not None, "fcf_for_distribution_keur row missing from PF CF table"

    def test_bs_total_assets_row_present(self):
        row = self.soup.find(attrs={"data-testid": "fs-bs-row-total_assets_keur"})
        assert row is not None, "total_assets_keur row missing from BS table"

    def test_bs_balance_check_row_present(self):
        row = self.soup.find(attrs={"data-testid": "fs-bs-row-balance_check_keur"})
        assert row is not None, "balance_check_keur row missing"

    def test_bs_share_capital_footnote(self):
        footnote = self.soup.find(attrs={"data-testid": "fs-bs-share-capital-footnote"})
        assert footnote is not None
        assert "placeholder" in footnote.get_text().lower()

    def test_dates_rendered_as_yyyy_mm(self):
        # dates in sample periods are "2029-01-30" → header should show "2029-01"
        table = self.soup.find(attrs={"data-testid": "fs-pnl-table"})
        headers_text = table.find("thead").get_text()
        assert "2029-01" in headers_text
        assert "2029-01-30" not in headers_text

    def test_none_value_renders_as_dash(self):
        # Build with a None value in one field
        period_with_none = dict(_sample_pnl_period(1))
        period_with_none["revenues_keur"] = None
        ctx = _base_ctx(
            has_runtime=True,
            fs_available=True,
            fs_pnl_periods=[period_with_none],
            fs_bs_periods=[],
            fs_pf_cf_periods=[],
        )
        soup = _render_fs_template(ctx)
        row = soup.find(attrs={"data-testid": "fs-pnl-row-revenues_keur"})
        assert row is not None
        assert "—" in row.get_text()


# ---------------------------------------------------------------------------
# 17–22. _build_financial_statements_ctx unit tests
# ---------------------------------------------------------------------------

class TestBuildFinancialStatementsCtx(unittest.TestCase):

    def _ctx_no_runtime(self):
        from app.v2.router import _build_financial_statements_ctx
        mock_ws = MagicMock()
        mock_ws.last_financial_statements = None
        mock_ws.last_runtime_snapshot_id = None
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            return _build_financial_statements_ctx(MagicMock(), mock_ws)

    def _ctx_with_runtime(self, num_periods=2):
        from app.v2.router import _build_financial_statements_ctx
        mock_rr = _make_mock_rr(num_periods)
        mock_ws = MagicMock()
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=mock_rr):
            return _build_financial_statements_ctx(MagicMock(), mock_ws)

    def test_fs_available_false_without_runtime(self):
        ctx = self._ctx_no_runtime()
        assert ctx["fs_available"] is False

    def test_fs_available_true_with_runtime(self):
        ctx = self._ctx_with_runtime()
        assert ctx["fs_available"] is True

    def test_period_lists_are_none_without_runtime(self):
        ctx = self._ctx_no_runtime()
        assert ctx["fs_pnl_periods"] is None, "expected None, not []"
        assert ctx["fs_bs_periods"] is None, "expected None, not []"
        assert ctx["fs_pf_cf_periods"] is None, "expected None, not []"

    def test_period_lists_populated_with_runtime(self):
        ctx = self._ctx_with_runtime(num_periods=3)
        assert isinstance(ctx["fs_pnl_periods"], list)
        assert len(ctx["fs_pnl_periods"]) == 3
        assert isinstance(ctx["fs_bs_periods"], list)
        assert len(ctx["fs_bs_periods"]) == 3
        assert isinstance(ctx["fs_pf_cf_periods"], list)
        assert len(ctx["fs_pf_cf_periods"]) == 3

    def test_all_classifications_are_partial(self):
        ctx = self._ctx_with_runtime()
        assert ctx["fs_pnl_classification"] == "PARTIAL"
        assert ctx["fs_bs_classification"] == "PARTIAL"
        assert ctx["fs_pf_cf_classification"] == "PARTIAL"

    def test_runtime_summary_key_present(self):
        ctx = self._ctx_with_runtime()
        assert "runtime_summary" in ctx

    def test_period_dicts_passed_verbatim(self):
        """Values must not be summed, transformed, or substituted in the context builder."""
        ctx = self._ctx_with_runtime(num_periods=2)
        first_pnl = ctx["fs_pnl_periods"][0]
        # revenues_keur for period 1 = 1001.0 (from _sample_pnl_period(1))
        assert first_pnl["revenues_keur"] == 1001.0
        first_bs = ctx["fs_bs_periods"][0]
        assert first_bs["total_assets_keur"] == 75700.0


# ---------------------------------------------------------------------------
# 23–24. Runtime state badge variants
# ---------------------------------------------------------------------------

class TestRuntimeStateBadge(unittest.TestCase):

    def test_state_b_clean(self):
        ctx = _base_ctx(has_runtime=True, ws_dirty=False)
        soup = _render_fs_template(ctx)
        badge = soup.find(attrs={"data-testid": "fs-runtime-state-b"})
        assert badge is not None, "State B badge missing"
        assert "current" in badge.get_text().lower()

    def test_state_c_dirty(self):
        ctx = _base_ctx(has_runtime=True, ws_dirty=True)
        soup = _render_fs_template(ctx)
        badge = soup.find(attrs={"data-testid": "fs-runtime-state-c"})
        assert badge is not None, "State C badge missing"
        assert "stale" in badge.get_text().lower()


# ---------------------------------------------------------------------------
# 26–27. Regression — other sheets still present
# ---------------------------------------------------------------------------

class TestRegressionOtherSheets(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "Regression")
        self.soup = _get_workbook(self.client, self.project_code)

    def test_tax_sheet_still_present(self):
        assert self.soup.find(id="v2-sheet-tax") is not None

    def test_debt_sheet_still_present(self):
        assert self.soup.find(id="v2-sheet-senior-debt") is not None
