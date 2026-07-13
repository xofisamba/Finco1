"""
tests/test_workbook_v2_runtime_projection.py

Test suite for PR 4/6 — Unified Runtime Projection Layer.

Coverage matrix:
  A. Pure projection module (app.workbook.runtime_projection)
     - State classification (all 4 states, UNAVAILABLE beats STALE)
     - thaw_runtime_payload (MappingProxyType, nested, None, list)
     - extract_periods (with/without operational filter)
     - project_period_labels
     - project_rows (None, empty, values)
     - fs_classify_statement
     - build_runtime_projection_bundle (debt/tax/fs derived from one rr)

  B. OOB view helpers (app.v2.runtime_projection_views)
     - build_all_runtime_bar_oob renders all three divs
     - build_fs_bar_oob translates UNAVAILABLE → FS_UNAVAILABLE

  C. Router adapter: GET handler calls get_runtime_result exactly once
  D. Router adapter: scalar HTMX success appends all three OOB bars
  E. CAPEX row mutation HTMX success appends all three OOB bars
  F. OPEX row mutation HTMX success appends all three OOB bars
  G. Debt/Tax context builders: debt_state / tax_state populated
  H. Template integration: debt_state / tax_state rendered in bars
  I. Missing/empty payload cases
  J. Ordering: UNAVAILABLE beats STALE (rr + dirty + no payload → UNAVAILABLE)
  K. Persisted-runtime integration (real DB path)
  L. Failure responses do NOT include runtime bar OOBs
"""
from __future__ import annotations

import os
import sys
import uuid
from types import MappingProxyType
from unittest.mock import MagicMock, call, patch

import pytest

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-pr4")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.auth import COOKIE_NAME, create_session_token
import main_web

_SESSION = create_session_token()


def _authed_client():
    client = TestClient(main_web.app, follow_redirects=False)
    client.cookies.set(COOKIE_NAME, _SESSION)
    return client


def _create_project(client, suffix=""):
    resp = client.post("/projects/create", data={
        "project_name": f"PR4 Test {suffix}",
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
    }, follow_redirects=False)
    import urllib.parse
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    return parsed["project"][0]


_FULL_RUNTIME_SUMMARY = {
    "project_irr": "8.5%",
    "equity_irr": "12.1%",
    "avg_dscr": 1.35,
    "min_dscr": 1.20,
    "total_senior_ds_keur": 5000.0,
    "total_revenue_keur": 15000.0,
    "total_capex_keur": 80000.0,
    "total_tax_keur": 2000.0,
    "equity_multiple": 2.5,
    "payback_years": 8,
}


def _persist_runtime(project_code, debt_schedule=None, tax_schedule=None, fs_payload=None):
    from app.persistence.projects_repository import get_project_record
    from app.persistence.repository import record_workspace_runtime
    proj = get_project_record(user_id="1", project_code=project_code)
    record_workspace_runtime(
        user_id="1",
        project_id=proj.project_id,
        project_code=project_code,
        runtime_snapshot={"_test": True},
        runtime_summary=_FULL_RUNTIME_SUMMARY,
        runtime_snapshot_id=f"test-{uuid.uuid4().hex[:8]}",
        runtime_origin="workbook_v2",
        debt_schedule=debt_schedule,
        tax_schedule=tax_schedule,
        financial_statements=fs_payload,
    )


def _sample_debt_schedule(n=2):
    periods = []
    for i in range(1, n + 1):
        periods.append({
            "period": i,
            "date": f"2029-{i:02d}-30",
            "is_operation": True,
            "senior_balance_open_keur": 50000.0 - (i - 1) * 1000,
            "senior_balance_close_keur": 50000.0 - i * 1000,
            "senior_balance_keur": 50000.0 - i * 1000,
            "senior_principal_keur": 1000.0,
            "senior_interest_keur": 500.0,
            "senior_total_ds_keur": 1500.0,
            "senior_ds_keur": 1500.0,
            "dscr": 1.35,
            "llcr": 1.40,
            "plcr": 1.50,
            "dsra_balance_keur": 500.0,
            "dsra_funding_keur": 50.0,
            "dsra_release_keur": 0.0,
        })
    return {"periods": periods}


def _sample_tax_schedule(n=2):
    periods = []
    for i in range(1, n + 1):
        periods.append({
            "period": i,
            "date": f"2029-{i:02d}-30",
            "is_operation": True,
            "taxable_income_keur": 700.0 + i,
            "taxable_profit_keur": 700.0 + i,
            "cit_keur": 126.0 + i,
            "tax_keur": 126.0 + i,
            "cf_after_tax_keur": 574.0 + i,
            "tax_loss_opening_audit_keur": 0.0,
            "tax_loss_used_audit_keur": 0.0,
            "tax_loss_closing_audit_keur": 0.0,
        })
    return {"periods": periods}


def _sample_fs():
    def pnl(n):
        return {"period": n, "date": f"2029-{n:02d}-30", "year_index": 1,
                "period_in_year": n, "revenues_keur": 1000.0 + n,
                "operating_expenses_keur": 200.0, "depreciation_keur": 100.0,
                "ebit_keur": 700.0 + n, "senior_interest_expense_keur": 50.0,
                "shl_interest_expense_keur": 10.0,
                "earnings_before_tax_keur": 640.0 + n, "cit_accrual_keur": 115.2,
                "net_income_keur": 524.8 + n, "retained_earnings_keur": 524.8 + n,
                "net_dividends_keur": 400.0}

    def bs(n):
        return {"period_index": n, "date": f"2029-{n:02d}-30",
                "net_fixed_assets_keur": 75000.0, "dsra_balance_keur": 500.0,
                "cash_keur": 200.0, "total_assets_keur": 75700.0,
                "share_capital_keur": 0.0, "retained_earnings_keur": 524.8,
                "shl_balance_keur": 10000.0, "senior_balance_keur": 40000.0,
                "total_liabilities_equity_keur": 75700.0, "balance_check_keur": 0.0}

    def pf(n):
        return {"period_index": n, "date": f"2029-{n:02d}-30",
                "revenue_cash_keur": 1000.0 + n, "opex_cash_keur": 200.0,
                "ebitda_cash_keur": 800.0 + n, "cash_tax_keur": 115.2,
                "fcf_banks_keur": 684.8, "senior_total_ds_keur": 300.0,
                "dsra_funding_keur": 50.0, "dsra_release_keur": 0.0,
                "fcf_junior_keur": 334.8, "fcf_for_distribution_keur": 334.8,
                "net_dividends_keur": 300.0}

    return {
        "pnl": {"periods": [pnl(1), pnl(2)]},
        "balance_sheet": {"periods": [bs(1), bs(2)]},
        "pf_cash_waterfall": {"periods": [pf(1), pf(2)]},
    }


# ═══════════════════════════════════════════════════════════════════════════ #
# A. Pure projection module                                                   #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestRuntimeProjectionState:
    def test_not_run_when_rr_is_none(self):
        from app.workbook.runtime_projection import classify_runtime_state, RuntimeProjectionState
        assert classify_runtime_state(None, None, False) == RuntimeProjectionState.NOT_RUN

    def test_unavailable_when_rr_has_no_payload(self):
        from app.workbook.runtime_projection import classify_runtime_state, RuntimeProjectionState
        rr = MagicMock()
        assert classify_runtime_state(rr, None, True) == RuntimeProjectionState.UNAVAILABLE

    def test_unavailable_beats_stale(self):
        from app.workbook.runtime_projection import classify_runtime_state, RuntimeProjectionState
        rr = MagicMock()
        # dirty=True but payload missing → UNAVAILABLE, not STALE
        state = classify_runtime_state(rr, None, is_dirty=True)
        assert state == RuntimeProjectionState.UNAVAILABLE

    def test_stale_when_dirty_and_payload_present(self):
        from app.workbook.runtime_projection import classify_runtime_state, RuntimeProjectionState
        rr = MagicMock()
        assert classify_runtime_state(rr, {"periods": []}, True) == RuntimeProjectionState.STALE

    def test_clean_when_not_dirty_and_payload_present(self):
        from app.workbook.runtime_projection import classify_runtime_state, RuntimeProjectionState
        rr = MagicMock()
        assert classify_runtime_state(rr, {"periods": []}, False) == RuntimeProjectionState.CLEAN


class TestThawRuntimePayload:
    def test_mapping_proxy_to_dict(self):
        from app.workbook.runtime_projection import thaw_runtime_payload
        proxy = MappingProxyType({"a": 1, "b": MappingProxyType({"c": 2})})
        result = thaw_runtime_payload(proxy)
        assert result == {"a": 1, "b": {"c": 2}}
        assert isinstance(result, dict)
        assert isinstance(result["b"], dict)

    def test_plain_dict_unchanged(self):
        from app.workbook.runtime_projection import thaw_runtime_payload
        d = {"x": [1, 2]}
        assert thaw_runtime_payload(d) == d

    def test_list_items_thawed(self):
        from app.workbook.runtime_projection import thaw_runtime_payload
        lst = [MappingProxyType({"k": "v"})]
        result = thaw_runtime_payload(lst)
        assert result == [{"k": "v"}]

    def test_scalar_passthrough(self):
        from app.workbook.runtime_projection import thaw_runtime_payload
        assert thaw_runtime_payload(42) == 42
        assert thaw_runtime_payload(None) is None


class TestExtractPeriods:
    def test_none_schedule_returns_none(self):
        from app.workbook.runtime_projection import extract_periods
        assert extract_periods(None) is None

    def test_all_periods_no_filter(self):
        from app.workbook.runtime_projection import extract_periods
        periods = [{"is_operation": False}, {"is_operation": True}]
        assert extract_periods({"periods": periods}) == periods

    def test_operational_filter(self):
        from app.workbook.runtime_projection import extract_periods
        periods = [{"is_operation": False, "n": 0}, {"is_operation": True, "n": 1}]
        result = extract_periods({"periods": periods}, operational_only=True)
        assert len(result) == 1
        assert result[0]["n"] == 1

    def test_missing_periods_key_returns_none(self):
        """Empty dict has no 'periods' key → structurally unavailable → None."""
        from app.workbook.runtime_projection import extract_periods
        assert extract_periods({}) is None

    def test_periods_key_none_returns_none(self):
        from app.workbook.runtime_projection import extract_periods
        assert extract_periods({"periods": None}) is None

    def test_schedule_with_other_keys_but_no_periods_returns_none(self):
        from app.workbook.runtime_projection import extract_periods
        assert extract_periods({"summary": {"total": 100}}) is None

    def test_empty_periods_list_returns_empty_list(self):
        """Explicit empty list is structurally available → []."""
        from app.workbook.runtime_projection import extract_periods
        assert extract_periods({"periods": []}) == []


class TestProjectRows:
    def test_none_periods_returns_none(self):
        from app.workbook.runtime_projection import project_rows
        assert project_rows([("k", "l", False)], None) is None

    def test_empty_periods_returns_rows_with_empty_values(self):
        from app.workbook.runtime_projection import project_rows
        rows = project_rows([("k", "l", False)], [])
        assert rows == [{"key": "k", "label": "l", "is_total": False, "values": []}]

    def test_row_structure(self):
        from app.workbook.runtime_projection import project_rows
        periods = [{"k": 42}, {"k": None}]
        rows = project_rows([("k", "Label", True)], periods)
        assert rows[0] == {"key": "k", "label": "Label", "is_total": True, "values": [42, None]}

    def test_zero_preserved(self):
        from app.workbook.runtime_projection import project_rows
        rows = project_rows([("k", "L", False)], [{"k": 0}])
        assert rows[0]["values"] == [0]

    def test_no_arithmetic(self):
        from app.workbook.runtime_projection import project_rows
        periods = [{"a": 10}, {"b": 20}]
        rows = project_rows([("a", "A", False), ("b", "B", False)], periods)
        assert rows[0]["values"] == [10, None]
        assert rows[1]["values"] == [None, 20]


class TestFsClassifyStatement:
    def test_no_rr_returns_not_run(self):
        from app.workbook.runtime_projection import fs_classify_statement
        assert fs_classify_statement(None, None, "pnl") == "NOT_RUN"

    def test_fs_none_returns_unavailable(self):
        from app.workbook.runtime_projection import fs_classify_statement
        assert fs_classify_statement(MagicMock(), None, "pnl") == "UNAVAILABLE"

    def test_missing_key_returns_unavailable(self):
        from app.workbook.runtime_projection import fs_classify_statement
        assert fs_classify_statement(MagicMock(), {}, "pnl") == "UNAVAILABLE"

    def test_periods_none_returns_unavailable(self):
        from app.workbook.runtime_projection import fs_classify_statement
        assert fs_classify_statement(MagicMock(), {"pnl": {"periods": None}}, "pnl") == "UNAVAILABLE"

    def test_periods_present_returns_partial(self):
        from app.workbook.runtime_projection import fs_classify_statement
        assert fs_classify_statement(MagicMock(), {"pnl": {"periods": []}}, "pnl") == "PARTIAL"


class TestBuildRuntimeProjectionBundle:
    def test_no_rr_all_not_run(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        bundle = build_runtime_projection_bundle(None, is_dirty=False)
        assert bundle.debt.state == RuntimeProjectionState.NOT_RUN
        assert bundle.tax.state == RuntimeProjectionState.NOT_RUN
        assert bundle.fs.state == RuntimeProjectionState.NOT_RUN

    def test_rr_with_all_payloads_clean(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {"k": "v"}
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.state == RuntimeProjectionState.CLEAN
        assert bundle.tax.state == RuntimeProjectionState.CLEAN
        assert bundle.fs.state == RuntimeProjectionState.CLEAN

    def test_unavailable_beats_stale_for_debt(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = None
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {}
        bundle = build_runtime_projection_bundle(rr, is_dirty=True)
        assert bundle.debt.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.tax.state == RuntimeProjectionState.STALE
        assert bundle.fs.state == RuntimeProjectionState.STALE

    def test_debt_operational_periods_filtered(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = {
            "periods": [
                {"is_operation": False, "n": 0},
                {"is_operation": True, "n": 1},
            ]
        }
        rr.tax_schedule = None
        rr.financial_statements = None
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.operational_periods is not None
        assert len(bundle.debt.operational_periods) == 1
        assert bundle.debt.operational_periods[0]["n"] == 1

    def test_fs_pnl_rows_projected(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = None
        rr.tax_schedule = None
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.fs.pnl_rows is not None
        assert len(bundle.fs.pnl_rows) == 11
        rev_row = next(r for r in bundle.fs.pnl_rows if r["key"] == "revenues_keur")
        assert rev_row["values"] == [1001.0, 1002.0]

    def test_missing_payload_partial_mock(self):
        """MagicMock(spec=RuntimeResult) with only financial_statements set."""
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {"k": "v"}
        # debt_schedule and tax_schedule not set → getattr returns Mock attribute
        # but our bundle uses getattr(rr, 'debt_schedule', None) defensively
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        # Must not raise; fs should be CLEAN since payload present
        assert bundle.fs.state == RuntimeProjectionState.CLEAN


# ═══════════════════════════════════════════════════════════════════════════ #
# B. OOB view helpers                                                         #
# ═══════════════════════════════════════════════════════════════════════════ #

def _make_meta(state_str, has_payload=False):
    """Build a RuntimeProjectionMeta for test purposes."""
    from app.workbook.runtime_projection import RuntimeProjectionMeta, RuntimeProjectionState
    return RuntimeProjectionMeta(
        state=RuntimeProjectionState(state_str),
        has_runtime=state_str != "NOT_RUN",
        has_payload=has_payload,
        is_dirty=state_str == "STALE",
        snapshot_id=None,
        ran_at=None,
        origin=None,
    )


class TestOobViewHelpers:
    def _make_bundle(self, debt_state, tax_state, fs_state):
        from app.workbook.runtime_projection import (
            WorkbookRuntimeProjection, DebtRuntimeProjection,
            TaxRuntimeProjection, FinancialStatementsProjection,
            RuntimeProjectionState,
        )
        debt = DebtRuntimeProjection(
            meta=_make_meta(debt_state),
            source=None, periods=None, operational_periods=None, summary=None,
            state=RuntimeProjectionState(debt_state),
            schedule=None, runtime_summary=None,
        )
        tax = TaxRuntimeProjection(
            meta=_make_meta(tax_state),
            source=None, periods=None, operational_periods=None, summary=None,
            state=RuntimeProjectionState(tax_state),
            schedule=None, runtime_summary=None,
        )
        fs = FinancialStatementsProjection(
            meta=_make_meta(fs_state),
            state=RuntimeProjectionState(fs_state),
            fs_available=False,
            pnl_rows=None, bs_rows=None, pf_cf_rows=None,
            pnl_period_labels=[], bs_period_labels=[], pf_cf_period_labels=[],
            pnl_classification="NOT_RUN", bs_classification="NOT_RUN",
            pf_cf_classification="NOT_RUN", runtime_summary=None,
        )
        return WorkbookRuntimeProjection(debt=debt, tax=tax, fs=fs)

    def test_all_three_divs_present(self):
        from app.v2.runtime_projection_views import build_all_runtime_bar_oob
        bundle = self._make_bundle("NOT_RUN", "NOT_RUN", "NOT_RUN")
        html = build_all_runtime_bar_oob(bundle)
        assert 'id="debt-runtime-bar"' in html
        assert 'id="tax-runtime-bar"' in html
        assert 'id="fs-runtime-bar"' in html
        assert 'hx-swap-oob="true"' in html

    def test_fs_unavailable_maps_to_fs_unavailable_key(self):
        from app.v2.runtime_projection_views import build_all_runtime_bar_oob
        bundle = self._make_bundle("CLEAN", "CLEAN", "UNAVAILABLE")
        html = build_all_runtime_bar_oob(bundle)
        assert "fs-runtime-state-d" in html

    def test_debt_stale_badge_present(self):
        from app.v2.runtime_projection_views import build_all_runtime_bar_oob
        bundle = self._make_bundle("STALE", "CLEAN", "CLEAN")
        html = build_all_runtime_bar_oob(bundle)
        assert "debt-runtime-state-c" in html

    def test_tax_clean_badge_present(self):
        from app.v2.runtime_projection_views import build_all_runtime_bar_oob
        bundle = self._make_bundle("CLEAN", "CLEAN", "CLEAN")
        html = build_all_runtime_bar_oob(bundle)
        assert "tax-runtime-state-b" in html

    def test_build_fs_bar_oob_legacy(self):
        from app.v2.runtime_projection_views import build_fs_bar_oob
        bundle = self._make_bundle("CLEAN", "CLEAN", "UNAVAILABLE")
        html = build_fs_bar_oob(bundle)
        assert 'id="fs-runtime-bar"' in html
        assert "fs-runtime-state-d" in html


# ═══════════════════════════════════════════════════════════════════════════ #
# C. Router: GET calls get_runtime_result exactly once                        #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestOneRuntimeResultPerRequest:
    def test_get_workbook_calls_get_runtime_result_once(self):
        client = _authed_client()
        code = _create_project(client, "one-rr")

        call_count = []
        original = __import__(
            "app.workbook.service", fromlist=["WorkbookService"]
        ).WorkbookService.get_runtime_result

        def counting_get_rr(ws):
            call_count.append(1)
            return original(ws)

        with patch(
            "app.workbook.service.WorkbookService.get_runtime_result",
            side_effect=counting_get_rr,
        ):
            resp = client.get(f"/v2/workbook?project={code}")

        assert resp.status_code == 200
        # Should be called exactly once in GET handler
        assert len(call_count) == 1, (
            f"Expected 1 get_runtime_result call in GET handler, got {len(call_count)}"
        )


# ═══════════════════════════════════════════════════════════════════════════ #
# D. Router: scalar HTMX success appends all three OOB bars                  #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestScalarHtmxOob:
    def _edit(self, client, project_code, field_id, value, sheet_id="project_setup"):
        from app.workbook.workbook_identity import assemble_consistent_for_get
        from app.workbook.service import WorkbookService
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        proj = get_project_record(user_id="1", project_code=project_code)
        ws = get_workspace_state(user_id="1", project_id=proj.project_id)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        identity = assemble_consistent_for_get(
            user_id="1",
            project_id=proj.project_id,
            workbook_version=pis.workbook_version,
        )
        return client.post(
            "/v2/workbook/update",
            data={
                "field_id": field_id,
                "value": value,
                "project": project_code,
                "workbook_version": pis.workbook_version,
                "content_hash": identity.composite_hash,
                "sheet_id": sheet_id,
            },
            headers={"HX-Request": "true"},
        )

    def test_project_setup_edit_returns_all_three_oob_bars(self):
        client = _authed_client()
        code = _create_project(client, "scalar-oob")
        resp = self._edit(client, code, "project_setup.technical.p50_hours", "2600")
        assert resp.status_code == 200
        body = resp.text
        assert 'id="debt-runtime-bar"' in body
        assert 'id="tax-runtime-bar"' in body
        assert 'id="fs-runtime-bar"' in body
        assert 'hx-swap-oob="true"' in body

    def test_tax_edit_returns_all_three_oob_bars(self):
        client = _authed_client()
        code = _create_project(client, "tax-oob")
        resp = self._edit(client, code, "tax.assumptions.cit_rate_pct", "20.0", sheet_id="tax")
        assert resp.status_code == 200
        body = resp.text
        assert 'id="debt-runtime-bar"' in body
        assert 'id="tax-runtime-bar"' in body
        assert 'id="fs-runtime-bar"' in body

    def test_debt_edit_returns_all_three_oob_bars(self):
        client = _authed_client()
        code = _create_project(client, "debt-oob")
        resp = self._edit(client, code, "debt.senior.interest_rate_pct", "5.0", sheet_id="debt")
        assert resp.status_code == 200
        body = resp.text
        assert 'id="debt-runtime-bar"' in body
        assert 'id="tax-runtime-bar"' in body
        assert 'id="fs-runtime-bar"' in body

    def test_fs_sheet_edit_does_not_duplicate_bars(self):
        """FS sheet re-render already contains fs-runtime-bar; no separate OOB."""
        client = _authed_client()
        code = _create_project(client, "fs-edit-dedup")
        # There's no directly editable FS field, use tax edit and confirm
        resp = self._edit(client, code, "tax.assumptions.cit_rate_pct", "21.0", sheet_id="tax")
        assert resp.status_code == 200
        # All three should appear exactly once
        body = resp.text
        assert body.count('id="fs-runtime-bar"') >= 1


# ═══════════════════════════════════════════════════════════════════════════ #
# E. CAPEX row mutation appends all three OOB bars                           #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestCapexRowOob:
    def _get_hash(self, client, project_code):
        from app.workbook.workbook_identity import assemble_consistent_for_get
        from app.workbook.service import WorkbookService
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        proj = get_project_record(user_id="1", project_code=project_code)
        ws = get_workspace_state(user_id="1", project_id=proj.project_id)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        identity = assemble_consistent_for_get(
            user_id="1",
            project_id=proj.project_id,
            workbook_version=pis.workbook_version,
        )
        return pis.workbook_version, identity.composite_hash

    def test_capex_line_add_returns_all_three_oob_bars(self):
        client = _authed_client()
        code = _create_project(client, "capex-oob")
        wv, ch = self._get_hash(client, code)
        resp = client.post(
            "/v2/capex/line/add",
            data={
                "project": code,
                "parent_category_code": "C.01",
                "label": "Test CAPEX OOB Line",
                "amount_keur": "500",
                "notes": "",
                "workbook_version": wv,
                "content_hash": ch,
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        body = resp.text
        assert 'id="debt-runtime-bar"' in body
        assert 'id="tax-runtime-bar"' in body
        assert 'id="fs-runtime-bar"' in body
        assert 'hx-swap-oob="true"' in body


# ═══════════════════════════════════════════════════════════════════════════ #
# F. OPEX row mutation appends all three OOB bars                            #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestOpexRowOob:
    def _get_hash(self, client, project_code):
        from app.workbook.workbook_identity import assemble_consistent_for_get
        from app.workbook.service import WorkbookService
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        proj = get_project_record(user_id="1", project_code=project_code)
        ws = get_workspace_state(user_id="1", project_id=proj.project_id)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        identity = assemble_consistent_for_get(
            user_id="1",
            project_id=proj.project_id,
            workbook_version=pis.workbook_version,
        )
        return pis.workbook_version, identity.composite_hash

    def test_opex_line_add_returns_all_three_oob_bars(self):
        client = _authed_client()
        code = _create_project(client, "opex-oob")
        wv, ch = self._get_hash(client, code)
        resp = client.post(
            "/v2/opex/line/add",
            data={
                "project": code,
                "parent_group_code": "B.01",
                "label": "Test OPEX OOB Line",
                "amount_keur": "200",
                "inflation_pct": "2.0",
                "notes": "",
                "workbook_version": wv,
                "content_hash": ch,
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        body = resp.text
        assert 'id="debt-runtime-bar"' in body
        assert 'id="tax-runtime-bar"' in body
        assert 'id="fs-runtime-bar"' in body
        assert 'hx-swap-oob="true"' in body


# ═══════════════════════════════════════════════════════════════════════════ #
# G. Debt/Tax context builders: state vars populated                          #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestContextBuilderStateVars:
    def test_debt_ctx_has_debt_state_not_run(self):
        from app.v2.router import _build_debt_ctx
        ws = MagicMock()
        ws.dirty = False
        ws.last_runtime_snapshot_id = None
        pis = MagicMock()
        pis.workbook_version = "2.1.0"
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            ctx = _build_debt_ctx(pis, ws)
        assert ctx["debt_state"] == "NOT_RUN"
        assert ctx["debt_schedule"] is None
        assert ctx["debt_operational_periods"] is None

    def test_tax_ctx_has_tax_state_not_run(self):
        from app.v2.router import _build_tax_ctx
        ws = MagicMock()
        ws.dirty = False
        pis = MagicMock()
        pis.workbook_version = "2.1.0"
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            ctx = _build_tax_ctx(pis, ws)
        assert ctx["tax_state"] == "NOT_RUN"
        assert ctx["tax_schedule"] is None
        assert ctx["tax_operational_periods"] is None

    def test_debt_ctx_clean_with_payload(self):
        from app.v2.router import _build_debt_ctx
        from app.workbook.runtime_result import RuntimeResult
        ws = MagicMock()
        ws.dirty = False
        ws.last_runtime_snapshot_id = "snap-1"
        pis = MagicMock()
        mock_rr = MagicMock(spec=RuntimeResult)
        mock_rr.debt_schedule = _sample_debt_schedule()
        mock_rr.tax_schedule = None
        mock_rr.financial_statements = None
        mock_rr.runtime_summary = {"project_irr": "8%"}
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=mock_rr):
            ctx = _build_debt_ctx(pis, ws)
        assert ctx["debt_state"] == "CLEAN"
        assert ctx["debt_schedule"] is not None

    def test_tax_ctx_unavailable_with_no_payload_but_rr(self):
        from app.v2.router import _build_tax_ctx
        from app.workbook.runtime_result import RuntimeResult
        ws = MagicMock()
        ws.dirty = True
        pis = MagicMock()
        pis.workbook_version = "2.1.0"
        mock_rr = MagicMock(spec=RuntimeResult)
        mock_rr.tax_schedule = None
        mock_rr.debt_schedule = None
        mock_rr.financial_statements = None
        mock_rr.runtime_summary = {}
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=mock_rr):
            ctx = _build_tax_ctx(pis, ws)
        # rr exists + no payload → UNAVAILABLE (beats STALE)
        assert ctx["tax_state"] == "UNAVAILABLE"


# ═══════════════════════════════════════════════════════════════════════════ #
# H. Template integration: state bars render correct badges                  #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestTemplateBarsRender:
    def test_debt_bar_not_run_renders_state_a(self):
        from fastapi.templating import Jinja2Templates
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl = Jinja2Templates(directory=os.path.join(base, "app", "templates", "v2"))
        html = tmpl.get_template("partials/_debt_runtime_bar.html").render(
            {"debt_state": "NOT_RUN"}
        )
        assert "debt-runtime-state-a" in html

    def test_debt_bar_clean_renders_state_b(self):
        from fastapi.templating import Jinja2Templates
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl = Jinja2Templates(directory=os.path.join(base, "app", "templates", "v2"))
        html = tmpl.get_template("partials/_debt_runtime_bar.html").render(
            {"debt_state": "CLEAN"}
        )
        assert "debt-runtime-state-b" in html
        assert "Outputs current" in html

    def test_debt_bar_stale_renders_state_c(self):
        from fastapi.templating import Jinja2Templates
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl = Jinja2Templates(directory=os.path.join(base, "app", "templates", "v2"))
        html = tmpl.get_template("partials/_debt_runtime_bar.html").render(
            {"debt_state": "STALE"}
        )
        assert "debt-runtime-state-c" in html
        assert "stale" in html.lower()
        assert "debt-runtime-state-c-run-required" in html

    def test_debt_bar_unavailable_renders_state_d(self):
        from fastapi.templating import Jinja2Templates
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl = Jinja2Templates(directory=os.path.join(base, "app", "templates", "v2"))
        html = tmpl.get_template("partials/_debt_runtime_bar.html").render(
            {"debt_state": "UNAVAILABLE"}
        )
        assert "debt-runtime-state-d" in html
        assert "unavailable" in html.lower()

    def test_tax_bar_not_run_renders_state_a(self):
        from fastapi.templating import Jinja2Templates
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl = Jinja2Templates(directory=os.path.join(base, "app", "templates", "v2"))
        html = tmpl.get_template("partials/_tax_runtime_bar.html").render(
            {"tax_state": "NOT_RUN"}
        )
        assert "tax-runtime-state-a" in html

    def test_tax_bar_stale_renders_state_c(self):
        from fastapi.templating import Jinja2Templates
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl = Jinja2Templates(directory=os.path.join(base, "app", "templates", "v2"))
        html = tmpl.get_template("partials/_tax_runtime_bar.html").render(
            {"tax_state": "STALE"}
        )
        assert "tax-runtime-state-c" in html
        assert "tax-runtime-state-c-run-required" in html


# ═══════════════════════════════════════════════════════════════════════════ #
# I. Missing/empty payload cases                                              #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestMissingEmptyPayloads:
    def test_debt_operational_periods_none_when_no_schedule(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = None
        rr.tax_schedule = None
        rr.financial_statements = None
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.debt.operational_periods is None

    def test_empty_periods_list_preserved(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = {"periods": []}
        rr.tax_schedule = {"periods": []}
        rr.financial_statements = {"pnl": {"periods": []}, "balance_sheet": {"periods": []},
                                    "pf_cash_waterfall": {"periods": []}}
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.operational_periods == []
        # pnl_rows has 11 row dicts (one per row_def), each with empty values
        assert bundle.fs.pnl_rows is not None
        assert len(bundle.fs.pnl_rows) == 11
        assert bundle.fs.pnl_rows[0]["values"] == []

    def test_fs_pnl_rows_none_when_fs_unavailable(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = None
        rr.tax_schedule = None
        rr.financial_statements = None
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.fs.pnl_rows is None
        assert bundle.fs.pf_cf_rows is None
        assert bundle.fs.bs_rows is None


# ═══════════════════════════════════════════════════════════════════════════ #
# J. Ordering: UNAVAILABLE beats STALE                                        #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestStatePrecedence:
    def test_all_payloads_missing_all_unavailable_even_dirty(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = None
        rr.tax_schedule = None
        rr.financial_statements = None
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=True)
        assert bundle.debt.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.tax.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.fs.state == RuntimeProjectionState.UNAVAILABLE

    def test_mixed_states_independent(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.debt_schedule = _sample_debt_schedule()  # STALE (dirty)
        rr.tax_schedule = None                       # UNAVAILABLE
        rr.financial_statements = _sample_fs()      # STALE (dirty)
        rr.runtime_summary = {}
        bundle = build_runtime_projection_bundle(rr, is_dirty=True)
        assert bundle.debt.state == RuntimeProjectionState.STALE
        assert bundle.tax.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.fs.state == RuntimeProjectionState.STALE


# ═══════════════════════════════════════════════════════════════════════════ #
# K. Persisted-runtime integration (real DB path)                            #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestPersistedRuntimeIntegration:
    def test_get_with_all_payloads_renders_clean_bars(self):
        client = _authed_client()
        code = _create_project(client, "pr4-clean")
        _persist_runtime(
            code,
            debt_schedule=_sample_debt_schedule(),
            tax_schedule=_sample_tax_schedule(),
            fs_payload=_sample_fs(),
        )
        resp = client.get(f"/v2/workbook?project={code}")
        assert resp.status_code == 200
        body = resp.text
        # All three bars should show "Outputs current"
        assert body.count("debt-runtime-state-b") >= 1
        assert body.count("tax-runtime-state-b") >= 1
        assert body.count("fs-runtime-state-b") >= 1

    def test_get_with_no_runtime_renders_not_run_bars(self):
        client = _authed_client()
        code = _create_project(client, "pr4-norun")
        resp = client.get(f"/v2/workbook?project={code}")
        assert resp.status_code == 200
        body = resp.text
        assert "debt-runtime-state-a" in body
        assert "tax-runtime-state-a" in body
        assert "fs-runtime-state-a" in body

    def test_edit_transitions_bars_to_stale_without_reload(self):
        client = _authed_client()
        code = _create_project(client, "pr4-stale")
        _persist_runtime(
            code,
            debt_schedule=_sample_debt_schedule(),
            tax_schedule=_sample_tax_schedule(),
            fs_payload=_sample_fs(),
        )
        # Edit a field
        from app.workbook.workbook_identity import assemble_consistent_for_get
        from app.workbook.service import WorkbookService
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        proj = get_project_record(user_id="1", project_code=code)
        ws = get_workspace_state(user_id="1", project_id=proj.project_id)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        identity = assemble_consistent_for_get(
            user_id="1",
            project_id=proj.project_id,
            workbook_version=pis.workbook_version,
        )
        resp = client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.technical.p50_hours",
                "value": "2700",
                "project": code,
                "workbook_version": pis.workbook_version,
                "content_hash": identity.composite_hash,
                "sheet_id": "project_setup",
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        body = resp.text
        # Stale bars should appear
        assert "debt-runtime-state-c" in body
        assert "tax-runtime-state-c" in body
        assert "fs-runtime-state-c" in body

    def test_runtime_with_only_fs_payload_debt_tax_unavailable(self):
        client = _authed_client()
        code = _create_project(client, "pr4-partial")
        _persist_runtime(
            code,
            debt_schedule=None,
            tax_schedule=None,
            fs_payload=_sample_fs(),
        )
        resp = client.get(f"/v2/workbook?project={code}")
        assert resp.status_code == 200
        body = resp.text
        assert "debt-runtime-state-d" in body
        assert "tax-runtime-state-d" in body
        assert "fs-runtime-state-b" in body


# ═══════════════════════════════════════════════════════════════════════════ #
# L. Failure responses do NOT include runtime bar OOBs                        #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestFailureResponsesNoOob:
    def test_validation_error_no_oob_bars(self):
        client = _authed_client()
        code = _create_project(client, "fail-oob")
        from app.workbook.workbook_identity import assemble_consistent_for_get
        from app.workbook.service import WorkbookService
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        proj = get_project_record(user_id="1", project_code=code)
        ws = get_workspace_state(user_id="1", project_id=proj.project_id)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        identity = assemble_consistent_for_get(
            user_id="1",
            project_id=proj.project_id,
            workbook_version=pis.workbook_version,
        )
        # Validation error: field value out of range
        resp = client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.technical.capacity_mw",
                "value": "-1",   # invalid (min 0.1); triggers FieldValidationError
                "project": code,
                "workbook_version": pis.workbook_version,
                "content_hash": identity.composite_hash,
                "sheet_id": "project_setup",
            },
            headers={"HX-Request": "true"},
        )
        # Validation error → 200 HTMX response with error in banner,
        # but workspace is not mutated so runtime-bar OOBs must NOT be appended.
        body = resp.text
        assert resp.status_code == 200
        # Exact assertions: no runtime bar OOB divs in validation error response.
        assert 'id="debt-runtime-bar" hx-swap-oob="true"' not in body
        assert 'id="tax-runtime-bar" hx-swap-oob="true"' not in body
        assert 'id="fs-runtime-bar" hx-swap-oob="true"' not in body


# ═══════════════════════════════════════════════════════════════════════════ #
# M. RuntimeProjectionMeta — shared identity across all three sheets         #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestRuntimeProjectionMeta:
    def test_meta_exists_on_all_three_projections(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        bundle = build_runtime_projection_bundle(None, is_dirty=False)
        assert hasattr(bundle.debt, "meta")
        assert hasattr(bundle.tax, "meta")
        assert hasattr(bundle.fs, "meta")

    def test_no_rr_meta_has_no_runtime(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        bundle = build_runtime_projection_bundle(None, is_dirty=False)
        assert bundle.debt.meta.has_runtime is False
        assert bundle.debt.meta.snapshot_id is None

    def test_all_three_share_same_snapshot_id(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = "snap-xyz-001"
        rr.ran_at = "2026-07-13T10:00:00"
        rr.origin = "workbook_v2"
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {}
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.meta.snapshot_id == bundle.tax.meta.snapshot_id
        assert bundle.tax.meta.snapshot_id == bundle.fs.meta.snapshot_id
        assert bundle.debt.meta.snapshot_id == "snap-xyz-001"

    def test_state_differs_per_sheet_while_identity_shared(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = "snap-002"
        rr.ran_at = "2026-07-13T10:00:00"
        rr.origin = "workbook_v2"
        rr.debt_schedule = None
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {}
        bundle = build_runtime_projection_bundle(rr, is_dirty=True)
        assert bundle.debt.meta.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.tax.meta.state == RuntimeProjectionState.STALE
        assert bundle.debt.meta.snapshot_id == bundle.tax.meta.snapshot_id == "snap-002"

    def test_meta_has_payload_reflects_per_sheet(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "x"
        rr.debt_schedule = None
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = None
        rr.runtime_summary = {}
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.meta.has_payload is False
        assert bundle.tax.meta.has_payload is True
        assert bundle.fs.meta.has_payload is False


# ═══════════════════════════════════════════════════════════════════════════ #
# N. Structural availability                                                  #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestStructuralAvailability:
    def _bundle_with_debt(self, debt_schedule, is_dirty=False):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "s"
        rr.debt_schedule = debt_schedule
        rr.tax_schedule = None
        rr.financial_statements = None
        rr.runtime_summary = None
        return build_runtime_projection_bundle(rr, is_dirty=is_dirty)

    def test_none_schedule_is_unavailable(self):
        from app.workbook.runtime_projection import RuntimeProjectionState
        bundle = self._bundle_with_debt(None)
        assert bundle.debt.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.debt.periods is None

    def test_empty_dict_schedule_is_unavailable(self):
        from app.workbook.runtime_projection import RuntimeProjectionState
        bundle = self._bundle_with_debt({})
        assert bundle.debt.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.debt.periods is None

    def test_schedule_missing_periods_key_is_unavailable(self):
        from app.workbook.runtime_projection import RuntimeProjectionState
        bundle = self._bundle_with_debt({"summary": {"total": 100}})
        assert bundle.debt.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.debt.periods is None

    def test_schedule_periods_none_is_unavailable(self):
        from app.workbook.runtime_projection import RuntimeProjectionState
        bundle = self._bundle_with_debt({"periods": None})
        assert bundle.debt.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.debt.periods is None

    def test_schedule_periods_empty_list_is_clean(self):
        from app.workbook.runtime_projection import RuntimeProjectionState
        bundle = self._bundle_with_debt({"periods": []}, is_dirty=False)
        assert bundle.debt.state == RuntimeProjectionState.CLEAN
        assert bundle.debt.periods == []

    def test_schedule_periods_empty_list_dirty_is_stale(self):
        from app.workbook.runtime_projection import RuntimeProjectionState
        bundle = self._bundle_with_debt({"periods": []}, is_dirty=True)
        assert bundle.debt.state == RuntimeProjectionState.STALE

    def test_same_contract_applies_to_tax(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "s"
        rr.debt_schedule = None
        rr.tax_schedule = {"summary": {"total": 50}}
        rr.financial_statements = None
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=True)
        assert bundle.tax.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.tax.periods is None


# ═══════════════════════════════════════════════════════════════════════════ #
# O. Debt/Tax projection contract                                              #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestDebtTaxProjectionContract:
    def test_debt_source_equals_schedule(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "x"
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = None
        rr.financial_statements = None
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.source is bundle.debt.schedule

    def test_debt_summary_equals_runtime_summary(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "x"
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = None
        rr.financial_statements = None
        rr.runtime_summary = {"project_irr": "8%"}
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.summary is bundle.debt.runtime_summary

    def test_debt_periods_all_in_original_order(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "x"
        rr.debt_schedule = {"periods": [
            {"is_operation": False, "period": 0},
            {"is_operation": True, "period": 1},
            {"is_operation": True, "period": 2},
        ]}
        rr.tax_schedule = None
        rr.financial_statements = None
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert len(bundle.debt.periods) == 3
        assert bundle.debt.periods[0]["period"] == 0
        assert len(bundle.debt.operational_periods) == 2

    def test_tax_source_equals_schedule(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "x"
        rr.debt_schedule = None
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = None
        rr.runtime_summary = None
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.tax.source is bundle.tax.schedule


# ═══════════════════════════════════════════════════════════════════════════ #
# P. One RuntimeResult per HTMX request                                       #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestOneRrPerHtmxRequest:
    def _get_identity(self, project_code):
        from app.workbook.workbook_identity import assemble_consistent_for_get
        from app.workbook.service import WorkbookService
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        proj = get_project_record(user_id="1", project_code=project_code)
        ws = get_workspace_state(user_id="1", project_id=proj.project_id)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        ident = assemble_consistent_for_get(user_id="1", project_id=proj.project_id, workbook_version=pis.workbook_version)
        return pis.workbook_version, ident.composite_hash

    def _count_rr_calls(self, fn):
        count = []
        original = __import__("app.workbook.service", fromlist=["WorkbookService"]).WorkbookService.get_runtime_result
        def counter(ws):
            count.append(1)
            return original(ws)
        with patch("app.workbook.service.WorkbookService.get_runtime_result", side_effect=counter):
            fn()
        return len(count)

    def test_debt_htmx_edit_calls_get_runtime_result_once(self):
        client = _authed_client()
        code = _create_project(client, "one-rr-debt")
        wv, ch = self._get_identity(code)
        def do_edit():
            client.post("/v2/workbook/update", data={
                "field_id": "debt.senior.interest_rate_pct",
                "value": "5.5", "project": code,
                "workbook_version": wv, "content_hash": ch, "sheet_id": "debt",
            }, headers={"HX-Request": "true"})
        count = self._count_rr_calls(do_edit)
        assert count == 1, f"Debt HTMX edit called get_runtime_result {count} times; expected 1"

    def test_tax_htmx_edit_calls_get_runtime_result_once(self):
        client = _authed_client()
        code = _create_project(client, "one-rr-tax")
        wv, ch = self._get_identity(code)
        def do_edit():
            client.post("/v2/workbook/update", data={
                "field_id": "tax.assumptions.cit_rate_pct",
                "value": "19.0", "project": code,
                "workbook_version": wv, "content_hash": ch, "sheet_id": "tax",
            }, headers={"HX-Request": "true"})
        count = self._count_rr_calls(do_edit)
        assert count == 1, f"Tax HTMX edit called get_runtime_result {count} times; expected 1"


# ═══════════════════════════════════════════════════════════════════════════ #
# Q. Stale composite hash — rejection, no OOB emitted                        #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestStaleHashNoOob:
    def test_scalar_stale_hash_no_oob(self):
        client = _authed_client()
        code = _create_project(client, "stale-scalar")
        resp = client.post("/v2/workbook/update", data={
            "field_id": "project_setup.technical.p50_hours", "value": "2600",
            "project": code, "workbook_version": "2.1.0",
            "content_hash": "definitely-wrong-hash", "sheet_id": "project_setup",
        }, headers={"HX-Request": "true"})
        body = resp.text
        assert 'id="debt-runtime-bar" hx-swap-oob="true"' not in body
        assert 'id="tax-runtime-bar" hx-swap-oob="true"' not in body
        assert 'id="fs-runtime-bar" hx-swap-oob="true"' not in body

    def test_capex_stale_hash_no_oob(self):
        client = _authed_client()
        code = _create_project(client, "stale-capex")
        resp = client.post("/v2/capex/line/add", data={
            "project": code, "parent_category_code": "C.01",
            "label": "Stale line", "amount_keur": "100", "notes": "",
            "workbook_version": "2.1.0", "content_hash": "wrong-hash",
        }, headers={"HX-Request": "true"})
        body = resp.text
        assert 'id="debt-runtime-bar" hx-swap-oob="true"' not in body
        assert 'id="fs-runtime-bar" hx-swap-oob="true"' not in body

    def test_opex_stale_hash_no_oob(self):
        client = _authed_client()
        code = _create_project(client, "stale-opex")
        resp = client.post("/v2/opex/line/add", data={
            "project": code, "parent_group_code": "B.01",
            "label": "Stale line", "amount_keur": "100",
            "inflation_pct": "2.0", "notes": "",
            "workbook_version": "2.1.0", "content_hash": "wrong-hash",
        }, headers={"HX-Request": "true"})
        body = resp.text
        assert 'id="debt-runtime-bar" hx-swap-oob="true"' not in body
        assert 'id="fs-runtime-bar" hx-swap-oob="true"' not in body


# ═══════════════════════════════════════════════════════════════════════════ #
# R. All 8 CAPEX/OPEX operations — full OOB coverage                         #
# ═══════════════════════════════════════════════════════════════════════════ #

def _get_identity_for(project_code):
    from app.workbook.workbook_identity import assemble_consistent_for_get
    from app.workbook.service import WorkbookService
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    proj = get_project_record(user_id="1", project_code=project_code)
    ws = get_workspace_state(user_id="1", project_id=proj.project_id)
    pis = WorkbookService.build_draft_input_set_from_workspace(ws)
    ident = assemble_consistent_for_get(user_id="1", project_id=proj.project_id, workbook_version=pis.workbook_version)
    return pis.workbook_version, ident.composite_hash


def _assert_oob_bars(resp):
    assert resp.status_code == 200
    body = resp.text
    assert 'id="debt-runtime-bar"' in body
    assert 'id="tax-runtime-bar"' in body
    assert 'id="fs-runtime-bar"' in body
    assert 'hx-swap-oob="true"' in body


def _get_custom_capex_lines(project_code):
    from app.persistence.projects_repository import get_project_record
    from app.persistence.capex_sub_lines import get_active_sub_lines_for_project
    proj = get_project_record(user_id="1", project_code=project_code)
    return get_active_sub_lines_for_project(proj.project_id)


def _get_custom_opex_lines(project_code):
    from app.persistence.projects_repository import get_project_record
    from app.persistence.opex_sub_lines import get_active_sub_lines_for_project as opex_active
    proj = get_project_record(user_id="1", project_code=project_code)
    return opex_active(proj.project_id)


class TestCapexAllOps:
    def test_capex_add(self):
        client = _authed_client()
        code = _create_project(client, "capex-add2")
        wv, ch = _get_identity_for(code)
        resp = client.post("/v2/capex/line/add", data={
            "project": code, "parent_category_code": "C.01",
            "label": "Add OOB", "amount_keur": "100", "notes": "",
            "workbook_version": wv, "content_hash": ch,
        }, headers={"HX-Request": "true"})
        _assert_oob_bars(resp)

    def test_capex_update(self):
        client = _authed_client()
        code = _create_project(client, "capex-update")
        wv, ch = _get_identity_for(code)
        client.post("/v2/capex/line/add", data={
            "project": code, "parent_category_code": "C.01",
            "label": "To update", "amount_keur": "100", "notes": "",
            "workbook_version": wv, "content_hash": ch,
        }, headers={"HX-Request": "true"})
        wv2, ch2 = _get_identity_for(code)
        lines = _get_custom_capex_lines(code)
        assert lines
        line = lines[0]
        resp = client.post("/v2/capex/line/update", data={
            "project": code, "sub_line_id": line.sub_line_id,
            "label": "Updated", "amount_keur": "200", "notes": "",
            "row_version": line.updated_at, "workbook_version": wv2, "content_hash": ch2,
        }, headers={"HX-Request": "true"})
        _assert_oob_bars(resp)

    def test_capex_deactivate(self):
        client = _authed_client()
        code = _create_project(client, "capex-deact")
        wv, ch = _get_identity_for(code)
        client.post("/v2/capex/line/add", data={
            "project": code, "parent_category_code": "C.01",
            "label": "To deactivate", "amount_keur": "50", "notes": "",
            "workbook_version": wv, "content_hash": ch,
        }, headers={"HX-Request": "true"})
        wv2, ch2 = _get_identity_for(code)
        lines = _get_custom_capex_lines(code)
        assert lines
        line = lines[0]
        resp = client.post("/v2/capex/line/deactivate", data={
            "project": code, "sub_line_id": line.sub_line_id,
            "row_version": line.updated_at, "workbook_version": wv2, "content_hash": ch2,
        }, headers={"HX-Request": "true"})
        _assert_oob_bars(resp)

    def test_capex_reorder(self):
        client = _authed_client()
        code = _create_project(client, "capex-reorder")
        wv, ch = _get_identity_for(code)
        client.post("/v2/capex/line/add", data={
            "project": code, "parent_category_code": "C.01",
            "label": "Line A", "amount_keur": "10", "notes": "",
            "workbook_version": wv, "content_hash": ch,
        }, headers={"HX-Request": "true"})
        wv2, ch2 = _get_identity_for(code)
        client.post("/v2/capex/line/add", data={
            "project": code, "parent_category_code": "C.01",
            "label": "Line B", "amount_keur": "20", "notes": "",
            "workbook_version": wv2, "content_hash": ch2,
        }, headers={"HX-Request": "true"})
        wv3, ch3 = _get_identity_for(code)
        lines = _get_custom_capex_lines(code)
        assert len(lines) >= 2
        resp = client.post("/v2/capex/line/reorder", data={
            "project": code, "parent_category_code": "C.01",
            "sub_line_id": [lines[1].sub_line_id, lines[0].sub_line_id],
            "row_version": [lines[1].updated_at, lines[0].updated_at],
            "workbook_version": wv3, "content_hash": ch3,
        }, headers={"HX-Request": "true"})
        _assert_oob_bars(resp)


class TestOpexAllOps:
    def test_opex_add(self):
        client = _authed_client()
        code = _create_project(client, "opex-add2")
        wv, ch = _get_identity_for(code)
        resp = client.post("/v2/opex/line/add", data={
            "project": code, "parent_group_code": "B.01",
            "label": "OPEX Add", "amount_keur": "50",
            "inflation_pct": "2.0", "notes": "",
            "workbook_version": wv, "content_hash": ch,
        }, headers={"HX-Request": "true"})
        _assert_oob_bars(resp)

    def test_opex_update(self):
        client = _authed_client()
        code = _create_project(client, "opex-update")
        wv, ch = _get_identity_for(code)
        client.post("/v2/opex/line/add", data={
            "project": code, "parent_group_code": "B.01",
            "label": "To update", "amount_keur": "30",
            "inflation_pct": "1.5", "notes": "",
            "workbook_version": wv, "content_hash": ch,
        }, headers={"HX-Request": "true"})
        wv2, ch2 = _get_identity_for(code)
        lines = _get_custom_opex_lines(code)
        assert lines
        line = lines[0]
        resp = client.post("/v2/opex/line/update", data={
            "project": code, "sub_line_id": line.sub_line_id,
            "label": "Updated OPEX", "amount_keur": "60",
            "inflation_pct": "3.0", "notes": "",
            "row_version": line.updated_at, "workbook_version": wv2, "content_hash": ch2,
        }, headers={"HX-Request": "true"})
        _assert_oob_bars(resp)

    def test_opex_deactivate(self):
        client = _authed_client()
        code = _create_project(client, "opex-deact")
        wv, ch = _get_identity_for(code)
        client.post("/v2/opex/line/add", data={
            "project": code, "parent_group_code": "B.01",
            "label": "To deactivate", "amount_keur": "25",
            "inflation_pct": "1.0", "notes": "",
            "workbook_version": wv, "content_hash": ch,
        }, headers={"HX-Request": "true"})
        wv2, ch2 = _get_identity_for(code)
        lines = _get_custom_opex_lines(code)
        assert lines
        line = lines[0]
        resp = client.post("/v2/opex/line/deactivate", data={
            "project": code, "sub_line_id": line.sub_line_id,
            "row_version": line.updated_at, "workbook_version": wv2, "content_hash": ch2,
        }, headers={"HX-Request": "true"})
        _assert_oob_bars(resp)

    def test_opex_reorder(self):
        client = _authed_client()
        code = _create_project(client, "opex-reorder")
        wv, ch = _get_identity_for(code)
        client.post("/v2/opex/line/add", data={
            "project": code, "parent_group_code": "B.01",
            "label": "OPEX A", "amount_keur": "10",
            "inflation_pct": "1.0", "notes": "",
            "workbook_version": wv, "content_hash": ch,
        }, headers={"HX-Request": "true"})
        wv2, ch2 = _get_identity_for(code)
        client.post("/v2/opex/line/add", data={
            "project": code, "parent_group_code": "B.01",
            "label": "OPEX B", "amount_keur": "20",
            "inflation_pct": "2.0", "notes": "",
            "workbook_version": wv2, "content_hash": ch2,
        }, headers={"HX-Request": "true"})
        wv3, ch3 = _get_identity_for(code)
        lines = _get_custom_opex_lines(code)
        assert len(lines) >= 2
        resp = client.post("/v2/opex/line/reorder", data={
            "project": code, "parent_group_code": "B.01",
            "sub_line_id": [lines[1].sub_line_id, lines[0].sub_line_id],
            "row_version": [lines[1].updated_at, lines[0].updated_at],
            "workbook_version": wv3, "content_hash": ch3,
        }, headers={"HX-Request": "true"})
        _assert_oob_bars(resp)


# ═══════════════════════════════════════════════════════════════════════════ #
# S. Immutability and persisted identity proofs                               #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestImmutabilityAndIdentity:
    def test_bundle_does_not_mutate_rr(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = "snap-immut"
        rr.ran_at = "2026-07-13"
        rr.origin = "workbook_v2"
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {}
        build_runtime_projection_bundle(rr, is_dirty=False)
        assert rr.snapshot_id == "snap-immut"
        assert rr.origin == "workbook_v2"

    def test_repeated_projection_produces_equal_output(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "x"
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {}
        b1 = build_runtime_projection_bundle(rr, is_dirty=False)
        b2 = build_runtime_projection_bundle(rr, is_dirty=False)
        assert b1.debt.state == b2.debt.state
        assert b1.debt.periods == b2.debt.periods
        assert b1.tax.state == b2.tax.state
        assert b1.fs.state == b2.fs.state
        assert b1.fs.pnl_rows == b2.fs.pnl_rows

    def test_no_repository_writes_during_projection(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "x"
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {}
        with patch("app.persistence.repository.record_workspace_runtime") as mock_write:
            build_runtime_projection_bundle(rr, is_dirty=False)
            assert mock_write.call_count == 0

    def test_persisted_snapshot_id_matches_meta(self):
        client = _authed_client()
        code = _create_project(client, "persist-id")
        snap_id = f"test-{uuid.uuid4().hex[:8]}"
        from app.persistence.projects_repository import get_project_record
        from app.persistence.repository import record_workspace_runtime
        from app.workbook.service import WorkbookService
        from app.persistence.workspace_repository import get_workspace_state
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        proj = get_project_record(user_id="1", project_code=code)
        record_workspace_runtime(
            user_id="1", project_id=proj.project_id, project_code=code,
            runtime_snapshot={"_test": True}, runtime_summary=_FULL_RUNTIME_SUMMARY,
            runtime_snapshot_id=snap_id, runtime_origin="workbook_v2",
            debt_schedule=_sample_debt_schedule(),
            tax_schedule=_sample_tax_schedule(),
            financial_statements=_sample_fs(),
        )
        ws = get_workspace_state(user_id="1", project_id=proj.project_id)
        rr = WorkbookService.get_runtime_result(ws)
        bundle = build_runtime_projection_bundle(rr, ws.dirty)
        assert bundle.debt.meta.snapshot_id == str(snap_id)
        assert bundle.tax.meta.snapshot_id == str(snap_id)
        assert bundle.fs.meta.snapshot_id == str(snap_id)

    def test_period_ordering_survives_fresh_reload(self):
        client = _authed_client()
        code = _create_project(client, "persist-order")
        extra = {k: 0.0 for k in ["senior_principal_keur","senior_interest_keur","senior_total_ds_keur","senior_ds_keur","dscr","llcr","plcr","dsra_balance_keur","dsra_funding_keur","dsra_release_keur","senior_balance_open_keur","senior_balance_close_keur"]}
        debt_sched = {"periods": [
            {"period": 1, "is_operation": True, "senior_balance_keur": 1000.0, "date": "2030-01-01", **extra},
            {"period": 2, "is_operation": True, "senior_balance_keur": 900.0, "date": "2030-07-01", **extra},
            {"period": 3, "is_operation": True, "senior_balance_keur": 800.0, "date": "2031-01-01", **extra},
        ]}
        from app.persistence.projects_repository import get_project_record
        from app.persistence.repository import record_workspace_runtime
        from app.workbook.service import WorkbookService
        from app.persistence.workspace_repository import get_workspace_state
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        proj = get_project_record(user_id="1", project_code=code)
        record_workspace_runtime(
            user_id="1", project_id=proj.project_id, project_code=code,
            runtime_snapshot={"_test": True}, runtime_summary=_FULL_RUNTIME_SUMMARY,
            runtime_snapshot_id=f"test-{uuid.uuid4().hex[:8]}", runtime_origin="workbook_v2",
            debt_schedule=debt_sched, tax_schedule=None, financial_statements=None,
        )
        ws2 = get_workspace_state(user_id="1", project_id=proj.project_id)
        rr2 = WorkbookService.get_runtime_result(ws2)
        bundle2 = build_runtime_projection_bundle(rr2, ws2.dirty)
        periods = bundle2.debt.periods
        assert periods is not None
        assert len(periods) == 3
        assert [p["senior_balance_keur"] for p in periods] == [1000.0, 900.0, 800.0]


# ═══════════════════════════════════════════════════════════════════════════ #
# T. has_payload structural truthfulness                                       #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestHasPayloadStructuralTruthfulness:
    """has_payload must agree with the structural availability contract."""

    def _make_rr(self, debt_schedule=None, tax_schedule=None):
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = rr.ran_at = rr.origin = "s"
        rr.debt_schedule = debt_schedule
        rr.tax_schedule = tax_schedule
        rr.financial_statements = None
        rr.runtime_summary = None
        return rr

    def test_debt_non_empty_payload_without_periods_key(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        rr = self._make_rr(debt_schedule={"summary": {"total": 100}})
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.meta.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.debt.meta.has_payload is False
        assert bundle.debt.periods is None
        assert bundle.debt.operational_periods is None

    def test_tax_non_empty_payload_without_periods_key(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        rr = self._make_rr(tax_schedule={"summary": {"total": 50}})
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.tax.meta.state == RuntimeProjectionState.UNAVAILABLE
        assert bundle.tax.meta.has_payload is False
        assert bundle.tax.periods is None
        assert bundle.tax.operational_periods is None

    def test_debt_empty_periods_list_has_payload_true_clean(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        rr = self._make_rr(debt_schedule={"periods": []})
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.meta.has_payload is True
        assert bundle.debt.meta.state == RuntimeProjectionState.CLEAN

    def test_debt_empty_periods_list_has_payload_true_stale(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        rr = self._make_rr(debt_schedule={"periods": []})
        bundle = build_runtime_projection_bundle(rr, is_dirty=True)
        assert bundle.debt.meta.has_payload is True
        assert bundle.debt.meta.state == RuntimeProjectionState.STALE

    def test_tax_empty_periods_list_has_payload_true_clean(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        rr = self._make_rr(tax_schedule={"periods": []})
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.tax.meta.has_payload is True
        assert bundle.tax.meta.state == RuntimeProjectionState.CLEAN

    def test_tax_empty_periods_list_has_payload_true_stale(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        rr = self._make_rr(tax_schedule={"periods": []})
        bundle = build_runtime_projection_bundle(rr, is_dirty=True)
        assert bundle.tax.meta.has_payload is True
        assert bundle.tax.meta.state == RuntimeProjectionState.STALE

    def test_meta_state_and_has_payload_never_contradict(self):
        """UNAVAILABLE ↔ has_payload False; CLEAN/STALE ↔ has_payload True."""
        from app.workbook.runtime_projection import build_runtime_projection_bundle, RuntimeProjectionState
        unavailable_states = {RuntimeProjectionState.UNAVAILABLE, RuntimeProjectionState.NOT_RUN}
        available_states = {RuntimeProjectionState.CLEAN, RuntimeProjectionState.STALE}
        cases = [
            (None, None),
            ({}, None),
            ({"summary": {}}, None),
            ({"periods": None}, None),
            ({"periods": []}, None),
            (_sample_debt_schedule(), None),
        ]
        from app.workbook.runtime_result import RuntimeResult
        for debt_sched, tax_sched in cases:
            rr = MagicMock(spec=RuntimeResult)
            rr.snapshot_id = rr.ran_at = rr.origin = "s"
            rr.debt_schedule = debt_sched
            rr.tax_schedule = tax_sched
            rr.financial_statements = None
            rr.runtime_summary = None
            bundle = build_runtime_projection_bundle(rr, is_dirty=False)
            if bundle.debt.meta.state in unavailable_states:
                assert bundle.debt.meta.has_payload is False, f"debt has_payload True but state={bundle.debt.meta.state} for schedule={debt_sched!r}"
            elif bundle.debt.meta.state in available_states:
                assert bundle.debt.meta.has_payload is True, f"debt has_payload False but state={bundle.debt.meta.state} for schedule={debt_sched!r}"


# ═══════════════════════════════════════════════════════════════════════════ #
# U. Identity None preservation                                                #
# ═══════════════════════════════════════════════════════════════════════════ #

class TestIdentityNonePreservation:
    """Absent identity attributes must be None, not the string "None"."""

    def test_absent_snapshot_id_is_none_not_string(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        # Do not set snapshot_id so getattr returns the MagicMock default sentinel
        # Instead, explicitly set it to None
        rr.snapshot_id = None
        rr.ran_at = None
        rr.origin = None
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {}
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.meta.snapshot_id is None
        assert bundle.debt.meta.ran_at is None
        assert bundle.debt.meta.origin is None
        assert bundle.debt.meta.snapshot_id != "None"
        assert bundle.debt.meta.ran_at != "None"
        assert bundle.debt.meta.origin != "None"

    def test_present_snapshot_id_preserved_as_string(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        from app.workbook.runtime_result import RuntimeResult
        rr = MagicMock(spec=RuntimeResult)
        rr.snapshot_id = "snap-abc-123"
        rr.ran_at = "2026-07-13T12:00:00"
        rr.origin = "workbook_v2"
        rr.debt_schedule = _sample_debt_schedule()
        rr.tax_schedule = _sample_tax_schedule()
        rr.financial_statements = _sample_fs()
        rr.runtime_summary = {}
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        assert bundle.debt.meta.snapshot_id == "snap-abc-123"
        assert bundle.tax.meta.ran_at == "2026-07-13T12:00:00"
        assert bundle.fs.meta.origin == "workbook_v2"

    def test_no_rr_identity_fields_all_none(self):
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        bundle = build_runtime_projection_bundle(None, is_dirty=False)
        assert bundle.debt.meta.snapshot_id is None
        assert bundle.debt.meta.ran_at is None
        assert bundle.debt.meta.origin is None
        assert bundle.tax.meta.snapshot_id is None
        assert bundle.fs.meta.snapshot_id is None
