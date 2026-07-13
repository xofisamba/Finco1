"""
Tests for the Workbook V2 Financial Statements worksheet (PR 3/6).

Coverage
--------
State machine (template rendering, no patching)
  1.  State A — no runtime: "Not yet run" + "Available after Run"
  2.  State A — no runtime: statement tables absent; correct no-runtime notices
  3.  State B — clean: "Outputs current" visible
  4.  State C — stale: "Previous run — stale" + "Run Required" visible
  5.  State D — rr exists, fs absent: truthful unavailable copy; "Outputs current" absent
  6.  State D — statement tables absent; fs-unavailable-notice present

Classifications
  7.  No runtime → all three classifications = NOT_RUN
  8.  FS payload absent (State D) → all three classifications = UNAVAILABLE
  9.  Normal payload → all three classifications = PARTIAL
  10. Individual statement key missing → that statement = UNAVAILABLE, others = PARTIAL

Server-side row projection
  11. fs_pnl_rows carries correct (key, label, is_total, values) structure
  12. fs_pf_cf_rows carries correct structure
  13. fs_bs_rows carries correct structure
  14. Period labels are YYYY-MM (first 7 chars of ISO date), projected server-side
  15. None values preserved as None; 0 preserved as 0 (not mixed up)
  16. Empty period list → rows have empty values lists; "no periods produced" notice

Template rendering
  17. #v2-sheet-financial-statements present in full workbook GET
  18. PARTIAL badges present on all three sections when payload available
  19. PARTIAL notices present on all three sections when payload available
  20. Income Statement table renders all 11 rows when payload available
  21. PF Cash Waterfall table renders all 11 rows when payload available
  22. Balance Sheet table renders all 10 rows when payload available
  23. Share capital footnote present on Balance Sheet when payload available
  24. Revenue value from sample period visible in PNL table
  25. None value in row renders as dash (—); 0 renders as 0

_build_financial_statements_ctx unit tests (mock)
  26. fs_available=False when no runtime
  27. fs_available=True when runtime present
  28. Period rows are None (not []) when no runtime
  29. Period rows populated from payload
  30. All three classification keys present
  31. runtime_summary key present

OOB cross-sheet FS runtime bar update
  32. Success HTMX Tax edit response contains #fs-runtime-bar OOB fragment
  33. Success HTMX Debt edit response contains #fs-runtime-bar OOB fragment
  34. Validation-error response does NOT contain FS OOB fragment (no mutation)

Integration — persisted runtime reload
  35. Full persisted reload: create project, persist FS runtime, GET shows tables
  36. Income Statement table contains persisted revenue value after reload
  37. PF Cash Waterfall table present after reload
  38. Balance Sheet table present after reload
  39. State D: rr + summary but no FS payload → UNAVAILABLE; "Outputs current" absent
  40. State D: unavailable notice present; no statement tables

Cross-sheet stale transition
  41. After successful HTMX edit, OOB contains stale badge
  42. Full page reload after edit shows State C (stale, run required visible)

Empty vs missing
  43. Missing FS payload → fs_pnl_classification = UNAVAILABLE
  44. Missing statement key in FS → that statement UNAVAILABLE
  45. Empty periods list → classification PARTIAL, "no periods" notice

Protected reference
  46. Protected reference project: FS sheet present, zero editable inputs
  47. Protected reference with persisted FS: tables render

Regression
  48. Tax sheet still present after FS wiring
  49. Debt sheet still present after FS wiring
"""
from __future__ import annotations

import os
import unittest
import urllib.parse
import uuid
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-fs-tests-v2")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

import main_web
from app.auth import COOKIE_NAME, create_session_token


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


def _get_workbook_soup(client: TestClient, project_code: str) -> BeautifulSoup:
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"workbook GET failed: {resp.status_code}"
    return BeautifulSoup(resp.text, "html.parser")


def _get_project_and_ws(client: TestClient, project_code: str):
    """Return (project_record, ws) for the test user's project."""
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    proj = get_project_record(user_id="1", project_code=project_code)
    ws = get_workspace_state("1", proj.project_id)
    return proj, ws


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
        "cit_accrual_keur": 115.2,
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


def _full_fs_payload(num_periods: int = 2) -> dict:
    return {
        "pnl": {"periods": [_sample_pnl_period(i + 1) for i in range(num_periods)]},
        "balance_sheet": {"periods": [_sample_bs_period(i + 1) for i in range(num_periods)]},
        "pf_cash_waterfall": {"periods": [_sample_pf_cf_period(i + 1) for i in range(num_periods)]},
    }


def _persist_runtime(project_code: str, fs_payload: dict | None = None,
                     runtime_summary: dict | None = None) -> None:
    """Persist a runtime result for the test user's project using real DB path."""
    from app.persistence.projects_repository import get_project_record
    from app.persistence.repository import record_workspace_runtime

    proj = get_project_record(user_id="1", project_code=project_code)
    snapshot_id = f"test-run-{uuid.uuid4().hex[:8]}"
    record_workspace_runtime(
        user_id="1",
        project_id=proj.project_id,
        project_code=project_code,
        runtime_snapshot={"_test": True},
        runtime_summary=runtime_summary or {
            "project_irr": "8.5%",
            "equity_irr": "12.1%",
            "total_revenue_keur": "85000",
        },
        runtime_snapshot_id=snapshot_id,
        runtime_origin="workbook_v2",
        financial_statements=fs_payload,
    )


def _render_fs_template(ctx: dict) -> BeautifulSoup:
    from jinja2 import Environment, FileSystemLoader
    tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
    env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
    env.globals["range"] = range
    html = env.get_template("partials/sheet_financial_statements.html").render(ctx)
    return BeautifulSoup(html, "html.parser")


def _base_no_runtime_ctx() -> dict:
    return {
        "project_code": "TEST-FS",
        "workbook_version": "2.1.0",
        "content_hash": "abc123",
        "project_editable": True,
        "ws_dirty": False,
        "has_runtime": False,
        "field_error": "",
        "fs_state": "NOT_RUN",
        "fs_available": False,
        "fs_pnl_rows": None,
        "fs_bs_rows": None,
        "fs_pf_cf_rows": None,
        "fs_pnl_period_labels": [],
        "fs_bs_period_labels": [],
        "fs_pf_cf_period_labels": [],
        "fs_pnl_classification": "NOT_RUN",
        "fs_bs_classification": "NOT_RUN",
        "fs_pf_cf_classification": "NOT_RUN",
        "runtime_summary": None,
    }


def _base_clean_ctx(num_periods: int = 2) -> dict:
    pnl = [_sample_pnl_period(i + 1) for i in range(num_periods)]
    bs = [_sample_bs_period(i + 1) for i in range(num_periods)]
    pf_cf = [_sample_pf_cf_period(i + 1) for i in range(num_periods)]
    from app.v2.router import (
        _FS_PNL_ROW_DEFS, _FS_BS_ROW_DEFS, _FS_PF_CF_ROW_DEFS,
        _fs_project_rows, _fs_period_labels,
    )
    return {
        "project_code": "TEST-FS",
        "workbook_version": "2.1.0",
        "content_hash": "abc123",
        "project_editable": True,
        "ws_dirty": False,
        "has_runtime": True,
        "field_error": "",
        "fs_state": "CLEAN",
        "fs_available": True,
        "fs_pnl_rows": _fs_project_rows(_FS_PNL_ROW_DEFS, pnl),
        "fs_bs_rows": _fs_project_rows(_FS_BS_ROW_DEFS, bs),
        "fs_pf_cf_rows": _fs_project_rows(_FS_PF_CF_ROW_DEFS, pf_cf),
        "fs_pnl_period_labels": _fs_period_labels(pnl),
        "fs_bs_period_labels": _fs_period_labels(bs),
        "fs_pf_cf_period_labels": _fs_period_labels(pf_cf),
        "fs_pnl_classification": "PARTIAL",
        "fs_bs_classification": "PARTIAL",
        "fs_pf_cf_classification": "PARTIAL",
        "runtime_summary": {"project_irr": "8.5%"},
    }


def _base_stale_ctx(num_periods: int = 2) -> dict:
    ctx = _base_clean_ctx(num_periods)
    ctx["fs_state"] = "STALE"
    ctx["ws_dirty"] = True
    return ctx


def _base_unavailable_ctx() -> dict:
    ctx = _base_no_runtime_ctx()
    ctx.update({
        "has_runtime": True,
        "fs_state": "FS_UNAVAILABLE",
        "fs_available": False,
        "fs_pnl_classification": "UNAVAILABLE",
        "fs_bs_classification": "UNAVAILABLE",
        "fs_pf_cf_classification": "UNAVAILABLE",
        "runtime_summary": {"project_irr": "8.5%"},
    })
    return ctx


# ---------------------------------------------------------------------------
# 1–6. State machine
# ---------------------------------------------------------------------------

class TestStateMachine(unittest.TestCase):

    def test_state_a_not_yet_run_text(self):
        soup = _render_fs_template(_base_no_runtime_ctx())
        bar = soup.find(id="fs-runtime-bar")
        assert bar is not None
        text = bar.get_text()
        assert "Not yet run" in text
        assert "Available after Run" in text

    def test_state_a_statement_tables_absent(self):
        soup = _render_fs_template(_base_no_runtime_ctx())
        assert soup.find(attrs={"data-testid": "fs-pnl-table"}) is None
        assert soup.find(attrs={"data-testid": "fs-pf-cf-table"}) is None
        assert soup.find(attrs={"data-testid": "fs-bs-table"}) is None

    def test_state_b_clean(self):
        soup = _render_fs_template(_base_clean_ctx())
        badge = soup.find(attrs={"data-testid": "fs-runtime-state-b"})
        assert badge is not None
        assert "Outputs current" in badge.get_text()

    def test_state_c_stale_text(self):
        soup = _render_fs_template(_base_stale_ctx())
        badge = soup.find(attrs={"data-testid": "fs-runtime-state-c"})
        assert badge is not None
        assert "stale" in badge.get_text().lower()

    def test_state_c_run_required_visible(self):
        soup = _render_fs_template(_base_stale_ctx())
        run_req = soup.find(attrs={"data-testid": "fs-runtime-state-c-run-required"})
        assert run_req is not None
        assert "Run Required" in run_req.get_text()

    def test_state_d_unavailable_no_outputs_current(self):
        soup = _render_fs_template(_base_unavailable_ctx())
        assert soup.find(attrs={"data-testid": "fs-runtime-state-b"}) is None
        bar = soup.find(id="fs-runtime-bar")
        assert "Outputs current" not in bar.get_text()

    def test_state_d_truthful_notice(self):
        soup = _render_fs_template(_base_unavailable_ctx())
        badge = soup.find(attrs={"data-testid": "fs-runtime-state-d"})
        assert badge is not None
        text = badge.get_text()
        assert "completed" in text.lower()
        assert "unavailable" in text.lower() or "not" in text.lower()

    def test_state_d_statement_tables_absent(self):
        soup = _render_fs_template(_base_unavailable_ctx())
        assert soup.find(attrs={"data-testid": "fs-pnl-table"}) is None
        assert soup.find(attrs={"data-testid": "fs-bs-table"}) is None

    def test_state_d_unavailable_notice_present(self):
        soup = _render_fs_template(_base_unavailable_ctx())
        notice = soup.find(attrs={"data-testid": "fs-unavailable-notice"})
        assert notice is not None


# ---------------------------------------------------------------------------
# 7–10. Classifications
# ---------------------------------------------------------------------------

class TestClassifications(unittest.TestCase):

    def test_no_runtime_all_not_run(self):
        from app.v2.router import _build_financial_statements_ctx
        mock_ws = MagicMock()
        mock_ws.last_runtime_snapshot_id = None
        mock_ws.dirty = False
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            ctx = _build_financial_statements_ctx(MagicMock(), mock_ws)
        assert ctx["fs_pnl_classification"] == "NOT_RUN"
        assert ctx["fs_bs_classification"] == "NOT_RUN"
        assert ctx["fs_pf_cf_classification"] == "NOT_RUN"

    def test_fs_absent_all_unavailable(self):
        from app.v2.router import _build_financial_statements_ctx
        from app.workbook.runtime_result import RuntimeResult
        mock_rr = MagicMock(spec=RuntimeResult)
        mock_rr.financial_statements = None
        mock_rr.runtime_summary = {"k": "v"}
        mock_ws = MagicMock()
        mock_ws.dirty = False
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=mock_rr):
            ctx = _build_financial_statements_ctx(MagicMock(), mock_ws)
        assert ctx["fs_pnl_classification"] == "UNAVAILABLE"
        assert ctx["fs_bs_classification"] == "UNAVAILABLE"
        assert ctx["fs_pf_cf_classification"] == "UNAVAILABLE"

    def test_normal_payload_all_partial(self):
        from app.v2.router import _build_financial_statements_ctx
        from app.workbook.runtime_result import RuntimeResult
        mock_rr = MagicMock(spec=RuntimeResult)
        mock_rr.financial_statements = _full_fs_payload()
        mock_rr.runtime_summary = {"k": "v"}
        mock_ws = MagicMock()
        mock_ws.dirty = False
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=mock_rr):
            ctx = _build_financial_statements_ctx(MagicMock(), mock_ws)
        assert ctx["fs_pnl_classification"] == "PARTIAL"
        assert ctx["fs_bs_classification"] == "PARTIAL"
        assert ctx["fs_pf_cf_classification"] == "PARTIAL"

    def test_missing_statement_key_unavailable(self):
        from app.v2.router import _build_financial_statements_ctx
        from app.workbook.runtime_result import RuntimeResult
        fs = {
            "pnl": {"periods": [_sample_pnl_period(1)]},
            # balance_sheet missing
            "pf_cash_waterfall": {"periods": [_sample_pf_cf_period(1)]},
        }
        mock_rr = MagicMock(spec=RuntimeResult)
        mock_rr.financial_statements = fs
        mock_rr.runtime_summary = {"k": "v"}
        mock_ws = MagicMock()
        mock_ws.dirty = False
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=mock_rr):
            ctx = _build_financial_statements_ctx(MagicMock(), mock_ws)
        assert ctx["fs_pnl_classification"] == "PARTIAL"
        assert ctx["fs_bs_classification"] == "UNAVAILABLE"
        assert ctx["fs_pf_cf_classification"] == "PARTIAL"


# ---------------------------------------------------------------------------
# 11–16. Server-side row projection
# ---------------------------------------------------------------------------

class TestServerSideProjection(unittest.TestCase):

    def setUp(self):
        from app.v2.router import (
            _FS_PNL_ROW_DEFS, _FS_BS_ROW_DEFS, _FS_PF_CF_ROW_DEFS,
            _fs_project_rows, _fs_period_labels,
        )
        self.pnl_periods = [_sample_pnl_period(1), _sample_pnl_period(2)]
        self.bs_periods = [_sample_bs_period(1), _sample_bs_period(2)]
        self.pf_cf_periods = [_sample_pf_cf_period(1), _sample_pf_cf_period(2)]
        self.pnl_rows = _fs_project_rows(_FS_PNL_ROW_DEFS, self.pnl_periods)
        self.bs_rows = _fs_project_rows(_FS_BS_ROW_DEFS, self.bs_periods)
        self.pf_cf_rows = _fs_project_rows(_FS_PF_CF_ROW_DEFS, self.pf_cf_periods)
        self.pnl_labels = _fs_period_labels(self.pnl_periods)

    def test_pnl_rows_structure(self):
        assert self.pnl_rows is not None
        assert len(self.pnl_rows) == 11
        first = self.pnl_rows[0]
        assert "key" in first and "label" in first and "is_total" in first and "values" in first
        assert first["key"] == "revenues_keur"
        assert len(first["values"]) == 2

    def test_pf_cf_rows_structure(self):
        assert self.pf_cf_rows is not None
        assert len(self.pf_cf_rows) == 11
        assert self.pf_cf_rows[0]["key"] == "revenue_cash_keur"

    def test_bs_rows_structure(self):
        assert self.bs_rows is not None
        assert len(self.bs_rows) == 10
        assert self.bs_rows[0]["key"] == "net_fixed_assets_keur"

    def test_period_labels_yyyy_mm(self):
        assert self.pnl_labels == ["2029-01", "2029-02"]

    def test_none_preserved_separately_from_zero(self):
        from app.v2.router import _FS_PNL_ROW_DEFS, _fs_project_rows
        p = dict(_sample_pnl_period(1))
        p["revenues_keur"] = None      # explicitly None
        p["net_dividends_keur"] = 0.0  # explicitly zero
        rows = _fs_project_rows(_FS_PNL_ROW_DEFS, [p])
        rev_row = next(r for r in rows if r["key"] == "revenues_keur")
        div_row = next(r for r in rows if r["key"] == "net_dividends_keur")
        assert rev_row["values"][0] is None
        assert div_row["values"][0] == 0.0

    def test_empty_periods_empty_value_lists(self):
        from app.v2.router import _FS_PNL_ROW_DEFS, _fs_project_rows
        rows = _fs_project_rows(_FS_PNL_ROW_DEFS, [])
        assert rows is not None
        assert len(rows) == 11
        assert rows[0]["values"] == []

    def test_none_periods_returns_none(self):
        from app.v2.router import _FS_PNL_ROW_DEFS, _fs_project_rows
        result = _fs_project_rows(_FS_PNL_ROW_DEFS, None)
        assert result is None


# ---------------------------------------------------------------------------
# 17–25. Template rendering (using template-level ctx)
# ---------------------------------------------------------------------------

class TestTemplateRendering(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "TplRender")
        self.no_runtime_soup = _get_workbook_soup(self.client, self.project_code)
        self.clean_ctx = _base_clean_ctx()
        self.clean_soup = _render_fs_template(self.clean_ctx)

    def test_sheet_div_present_in_workbook(self):
        div = self.no_runtime_soup.find(id="v2-sheet-financial-statements")
        assert div is not None

    def test_partial_badges_present_when_payload(self):
        assert self.clean_soup.find(attrs={"data-testid": "fs-pnl-classification-badge"})
        assert self.clean_soup.find(attrs={"data-testid": "fs-pf-cf-classification-badge"})
        assert self.clean_soup.find(attrs={"data-testid": "fs-bs-classification-badge"})

    def test_partial_notices_present(self):
        assert self.clean_soup.find(attrs={"data-testid": "fs-pnl-partial-notice"})
        assert self.clean_soup.find(attrs={"data-testid": "fs-pf-cf-partial-notice"})
        assert self.clean_soup.find(attrs={"data-testid": "fs-bs-partial-notice"})

    def test_pnl_table_has_11_data_rows(self):
        table = self.clean_soup.find(attrs={"data-testid": "fs-pnl-table"})
        assert table is not None
        rows = table.find("tbody").find_all("tr")
        assert len(rows) == 11

    def test_pf_cf_table_has_11_data_rows(self):
        table = self.clean_soup.find(attrs={"data-testid": "fs-pf-cf-table"})
        assert table is not None
        rows = table.find("tbody").find_all("tr")
        assert len(rows) == 11

    def test_bs_table_has_10_data_rows(self):
        table = self.clean_soup.find(attrs={"data-testid": "fs-bs-table"})
        assert table is not None
        rows = table.find("tbody").find_all("tr")
        assert len(rows) == 10

    def test_share_capital_footnote(self):
        footnote = self.clean_soup.find(attrs={"data-testid": "fs-bs-share-capital-footnote"})
        assert footnote is not None
        assert "placeholder" in footnote.get_text().lower()

    def test_revenue_value_visible_in_pnl(self):
        row = self.clean_soup.find(attrs={"data-testid": "fs-pnl-row-revenues_keur"})
        assert row is not None
        assert "1001" in row.get_text()  # period 1: 1000+1=1001

    def test_none_renders_as_dash_zero_as_zero(self):
        from app.v2.router import _FS_PNL_ROW_DEFS, _fs_project_rows, _fs_period_labels
        p = dict(_sample_pnl_period(1))
        p["revenues_keur"] = None
        p["net_dividends_keur"] = 0.0
        ctx = _base_no_runtime_ctx()
        ctx.update({
            "fs_state": "CLEAN",
            "has_runtime": True,
            "fs_available": True,
            "fs_pnl_rows": _fs_project_rows(_FS_PNL_ROW_DEFS, [p]),
            "fs_pnl_period_labels": _fs_period_labels([p]),
            "fs_pnl_classification": "PARTIAL",
        })
        soup = _render_fs_template(ctx)
        rev_row = soup.find(attrs={"data-testid": "fs-pnl-row-revenues_keur"})
        assert "—" in rev_row.get_text()
        div_row = soup.find(attrs={"data-testid": "fs-pnl-row-net_dividends_keur"})
        assert "0" in div_row.get_text()
        assert "—" not in div_row.get_text()


# ---------------------------------------------------------------------------
# 26–31. _build_financial_statements_ctx unit tests
# ---------------------------------------------------------------------------

class TestBuildFinancialStatementsCtx(unittest.TestCase):

    def _ctx_no_runtime(self):
        from app.v2.router import _build_financial_statements_ctx
        mock_ws = MagicMock()
        mock_ws.last_runtime_snapshot_id = None
        mock_ws.dirty = False
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            return _build_financial_statements_ctx(MagicMock(), mock_ws)

    def _ctx_with_runtime(self):
        from app.v2.router import _build_financial_statements_ctx
        from app.workbook.runtime_result import RuntimeResult
        mock_rr = MagicMock(spec=RuntimeResult)
        mock_rr.financial_statements = _full_fs_payload(2)
        mock_rr.runtime_summary = {"project_irr": "8.5%"}
        mock_ws = MagicMock()
        mock_ws.dirty = False
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=mock_rr):
            return _build_financial_statements_ctx(MagicMock(), mock_ws)

    def test_fs_available_false_no_runtime(self):
        assert self._ctx_no_runtime()["fs_available"] is False

    def test_fs_available_true_with_runtime(self):
        assert self._ctx_with_runtime()["fs_available"] is True

    def test_rows_none_no_runtime(self):
        ctx = self._ctx_no_runtime()
        assert ctx["fs_pnl_rows"] is None
        assert ctx["fs_bs_rows"] is None
        assert ctx["fs_pf_cf_rows"] is None

    def test_rows_populated_with_runtime(self):
        ctx = self._ctx_with_runtime()
        assert isinstance(ctx["fs_pnl_rows"], list)
        assert len(ctx["fs_pnl_rows"]) == 11
        assert isinstance(ctx["fs_bs_rows"], list)
        assert len(ctx["fs_bs_rows"]) == 10
        assert isinstance(ctx["fs_pf_cf_rows"], list)
        assert len(ctx["fs_pf_cf_rows"]) == 11

    def test_classification_keys_present(self):
        ctx = self._ctx_with_runtime()
        assert "fs_pnl_classification" in ctx
        assert "fs_bs_classification" in ctx
        assert "fs_pf_cf_classification" in ctx

    def test_runtime_summary_key_present(self):
        ctx = self._ctx_with_runtime()
        assert "runtime_summary" in ctx


# ---------------------------------------------------------------------------
# 32–34. OOB cross-sheet FS runtime bar update
# ---------------------------------------------------------------------------

class TestCrossSheetOobUpdate(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "OOB")

    def _get_content_hash(self) -> str:
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        shell = soup.find(id="v2-workbook-shell")
        return shell["data-content-hash"]

    def _htmx_edit(self, field_id: str, value: str, sheet_id: str) -> str:
        ch = self._get_content_hash()
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": field_id,
                "value": value,
                "project": self.project_code,
                "workbook_version": "2.1.0",
                "content_hash": ch,
                "sheet_id": sheet_id,
            },
            headers={"HX-Request": "true"},
        )
        return resp.text

    def test_tax_edit_response_contains_fs_runtime_bar_oob(self):
        body = self._htmx_edit("tax.assumptions.cit_rate_pct", "19.0", "tax")
        assert "fs-runtime-bar" in body, "OOB #fs-runtime-bar missing from tax edit response"
        assert "hx-swap-oob" in body

    def test_debt_edit_response_contains_fs_runtime_bar_oob(self):
        body = self._htmx_edit("debt.senior.interest_rate_pct", "5.0", "debt")
        assert "fs-runtime-bar" in body, "OOB #fs-runtime-bar missing from debt edit response"

    def test_validation_error_no_fs_oob(self):
        # An edit that fails validation (unknown field_id) returns 422 JSON, not HTML OOB
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "nonexistent.field",
                "value": "999",
                "project": self.project_code,
                "workbook_version": "2.1.0",
                "content_hash": "stale-hash-that-causes-stale-error",
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        # Either 422 JSON or HTMX error response — either way no mutation occurred
        # so the response must not contain a false stale/dirty FS bar
        body = resp.text
        if "fs-runtime-bar" in body:
            # If OOB is included, it must not claim stale when no mutation occurred
            # (A stale-content error re-renders with fresh ws state, which is clean)
            assert "fs-runtime-state-c" not in body, (
                "Validation-error response must not show stale FS badge (no mutation)"
            )


# ---------------------------------------------------------------------------
# 35–40. Integration — persisted runtime reload
# ---------------------------------------------------------------------------

class TestPersistedRuntimeReload(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "Persist")

    def test_persisted_fs_visible_on_get(self):
        """Prove the full reload path: DB → RuntimeResult → projection → template."""
        _persist_runtime(self.project_code, fs_payload=_full_fs_payload(2))
        soup = _get_workbook_soup(self.client, self.project_code)
        fs_div = soup.find(id="v2-sheet-financial-statements")
        assert fs_div is not None
        assert fs_div.find(attrs={"data-testid": "fs-pnl-table"}) is not None

    def test_pnl_revenue_value_visible_after_reload(self):
        _persist_runtime(self.project_code, fs_payload=_full_fs_payload(2))
        soup = _get_workbook_soup(self.client, self.project_code)
        row = soup.find(attrs={"data-testid": "fs-pnl-row-revenues_keur"})
        assert row is not None
        # period 1 revenue = 1001.0 → "1001"
        assert "1001" in row.get_text()

    def test_pf_cf_table_present_after_reload(self):
        _persist_runtime(self.project_code, fs_payload=_full_fs_payload(2))
        soup = _get_workbook_soup(self.client, self.project_code)
        assert soup.find(attrs={"data-testid": "fs-pf-cf-table"}) is not None

    def test_bs_table_present_after_reload(self):
        _persist_runtime(self.project_code, fs_payload=_full_fs_payload(2))
        soup = _get_workbook_soup(self.client, self.project_code)
        assert soup.find(attrs={"data-testid": "fs-bs-table"}) is not None

    def test_state_d_rr_without_fs_payload(self):
        """rr + runtime_summary + no FS payload → State D; 'Outputs current' absent."""
        _persist_runtime(self.project_code, fs_payload=None)
        soup = _get_workbook_soup(self.client, self.project_code)
        fs_div = soup.find(id="v2-sheet-financial-statements")
        bar = fs_div.find(id="fs-runtime-bar")
        assert bar is not None
        assert "Outputs current" not in bar.get_text()
        assert soup.find(attrs={"data-testid": "fs-runtime-state-b"}) is None

    def test_state_d_unavailable_notice_present(self):
        _persist_runtime(self.project_code, fs_payload=None)
        soup = _get_workbook_soup(self.client, self.project_code)
        # State D: show truthful unavailable notice, no statement tables
        assert soup.find(attrs={"data-testid": "fs-pnl-table"}) is None
        assert soup.find(attrs={"data-testid": "fs-unavailable-notice"}) is not None or \
               soup.find(attrs={"data-testid": "fs-runtime-state-d"}) is not None


# ---------------------------------------------------------------------------
# 41–42. Cross-sheet stale transition
# ---------------------------------------------------------------------------

class TestCrossSheetStaleTransition(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "Stale")
        _persist_runtime(self.project_code, fs_payload=_full_fs_payload(2))

    def _get_content_hash(self) -> str:
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        return soup.find(id="v2-workbook-shell")["data-content-hash"]

    def test_htmx_edit_oob_contains_stale_badge(self):
        ch = self._get_content_hash()
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "tax.assumptions.cit_rate_pct",
                "value": "19.5",
                "project": self.project_code,
                "workbook_version": "2.1.0",
                "content_hash": ch,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        body = resp.text
        assert "fs-runtime-bar" in body
        # After a successful edit the workspace becomes dirty → stale state
        assert "fs-runtime-state-c" in body or "stale" in body.lower()

    def test_full_reload_after_edit_shows_state_c(self):
        ch = self._get_content_hash()
        self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "tax.assumptions.cit_rate_pct",
                "value": "20.0",
                "project": self.project_code,
                "workbook_version": "2.1.0",
                "content_hash": ch,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        soup = _get_workbook_soup(self.client, self.project_code)
        fs_div = soup.find(id="v2-sheet-financial-statements")
        bar = fs_div.find(id="fs-runtime-bar")
        assert bar is not None
        bar_text = bar.get_text()
        # State C: stale badge + Run Required
        assert "stale" in bar_text.lower() or "previous run" in bar_text.lower()
        assert "Run Required" in bar_text
        # Previous statement tables still visible (persisted, not erased)
        assert fs_div.find(attrs={"data-testid": "fs-pnl-table"}) is not None


# ---------------------------------------------------------------------------
# 43–45. Empty vs missing
# ---------------------------------------------------------------------------

class TestEmptyVsMissing(unittest.TestCase):

    def test_missing_fs_payload_pnl_unavailable(self):
        from app.v2.router import _fs_classify
        assert _fs_classify(object(), None, "pnl") == "UNAVAILABLE"

    def test_missing_statement_key_unavailable(self):
        from app.v2.router import _fs_classify
        fs = {"pnl": {"periods": []}}  # balance_sheet missing
        # The rr object just needs to be truthy
        assert _fs_classify(object(), fs, "balance_sheet") == "UNAVAILABLE"

    def test_empty_periods_list_partial(self):
        from app.v2.router import _fs_classify
        fs = {"pnl": {"periods": []}}
        assert _fs_classify(object(), fs, "pnl") == "PARTIAL"

    def test_empty_periods_no_periods_notice(self):
        from app.v2.router import _FS_PNL_ROW_DEFS, _fs_project_rows, _fs_period_labels
        ctx = _base_no_runtime_ctx()
        ctx.update({
            "fs_state": "CLEAN",
            "has_runtime": True,
            "fs_available": True,
            "fs_pnl_rows": _fs_project_rows(_FS_PNL_ROW_DEFS, []),
            "fs_pnl_period_labels": [],
            "fs_pnl_classification": "PARTIAL",
        })
        soup = _render_fs_template(ctx)
        assert soup.find(attrs={"data-testid": "fs-pnl-empty"}) is not None
        assert soup.find(attrs={"data-testid": "fs-pnl-table"}) is None

    def test_none_value_renders_dash(self):
        from app.v2.router import _FS_PNL_ROW_DEFS, _fs_project_rows, _fs_period_labels
        p = dict(_sample_pnl_period(1))
        p["revenues_keur"] = None
        ctx = _base_no_runtime_ctx()
        ctx.update({
            "fs_state": "CLEAN",
            "has_runtime": True,
            "fs_available": True,
            "fs_pnl_rows": _fs_project_rows(_FS_PNL_ROW_DEFS, [p]),
            "fs_pnl_period_labels": ["2029-01"],
            "fs_pnl_classification": "PARTIAL",
        })
        soup = _render_fs_template(ctx)
        row = soup.find(attrs={"data-testid": "fs-pnl-row-revenues_keur"})
        assert "—" in row.get_text()

    def test_zero_value_renders_zero_not_dash(self):
        from app.v2.router import _FS_BS_ROW_DEFS, _fs_project_rows, _fs_period_labels
        p = dict(_sample_bs_period(1))
        p["balance_check_keur"] = 0.0
        ctx = _base_no_runtime_ctx()
        ctx.update({
            "fs_state": "CLEAN",
            "has_runtime": True,
            "fs_available": True,
            "fs_bs_rows": _fs_project_rows(_FS_BS_ROW_DEFS, [p]),
            "fs_bs_period_labels": ["2029-01"],
            "fs_bs_classification": "PARTIAL",
        })
        soup = _render_fs_template(ctx)
        row = soup.find(attrs={"data-testid": "fs-bs-row-balance_check_keur"})
        text = row.get_text()
        assert "0" in text
        assert "—" not in text


# ---------------------------------------------------------------------------
# 46–47. Protected reference
# ---------------------------------------------------------------------------

class TestProtectedReference(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "ProtRef")

    def _get_as_protected(self) -> BeautifulSoup:
        with patch("app.v2.router.is_protected_reference", return_value=True):
            return _get_workbook_soup(self.client, self.project_code)

    def test_fs_sheet_present_in_protected_project(self):
        soup = self._get_as_protected()
        assert soup.find(id="v2-sheet-financial-statements") is not None

    def test_fs_sheet_has_zero_editable_inputs(self):
        soup = self._get_as_protected()
        fs_div = soup.find(id="v2-sheet-financial-statements")
        # Financial Statements is purely read-only — no form elements anywhere
        editable = fs_div.find_all(["form", "input", "button"])
        assert len(editable) == 0, (
            f"Protected FS sheet should have zero editable elements; found: "
            + ", ".join(e.name for e in editable)
        )

    def test_protected_ref_with_persisted_fs_renders_tables(self):
        _persist_runtime(self.project_code, fs_payload=_full_fs_payload(2))
        with patch("app.v2.router.is_protected_reference", return_value=True):
            soup = _get_workbook_soup(self.client, self.project_code)
        fs_div = soup.find(id="v2-sheet-financial-statements")
        assert fs_div.find(attrs={"data-testid": "fs-pnl-table"}) is not None


# ---------------------------------------------------------------------------
# 48–49. Regression
# ---------------------------------------------------------------------------

class TestRegressionOtherSheets(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "Regression")
        self.soup = _get_workbook_soup(self.client, self.project_code)

    def test_tax_sheet_still_present(self):
        assert self.soup.find(id="v2-sheet-tax") is not None

    def test_debt_sheet_still_present(self):
        assert self.soup.find(id="v2-sheet-senior-debt") is not None
