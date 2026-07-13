"""
Tests for the Workbook V2 Senior Debt worksheet (PR 1).

Coverage
--------
1.  GET /v2/workbook returns 200 with #v2-sheet-senior-debt
2.  All 4 BOUND registry fields appear in the page
3.  HTMX edit round-trip: POST /v2/workbook/update with sheet_id=debt returns
    200 and re-renders #v2-sheet-senior-debt
4.  Pre-run empty state: no runtime → empty-state notice
5.  Debt schedule rendered from mocked RuntimeResult with debt_schedule data
"""
from __future__ import annotations

import dataclasses
import os
import types
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-debt-tests-v2")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.v2.router import _build_sheet_fields  # noqa: E402


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
            "project_name": f"Debt V2 Test {suffix}",
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


def _debt_div(html: str):
    return BeautifulSoup(html, "html.parser").find(id="v2-sheet-senior-debt")


def _fake_pis():
    m = MagicMock()
    m.get = lambda fid: None
    return m


# ---------------------------------------------------------------------------
# 1. GET /v2/workbook returns 200 with #v2-sheet-senior-debt
# ---------------------------------------------------------------------------

class TestDebtSheetRendersInWorkbookPage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "get-01")

    def test_workbook_returns_200(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)

    def test_debt_sheet_container_present(self):
        html = _get_workbook(self.client, self.project_code)
        div = _debt_div(html)
        self.assertIsNotNone(div, "id='v2-sheet-senior-debt' not found in workbook page")

    def test_data_sheet_attribute(self):
        html = _get_workbook(self.client, self.project_code)
        div = _debt_div(html)
        self.assertEqual(div.get("data-sheet"), "debt")


# ---------------------------------------------------------------------------
# 2. All 4 BOUND registry fields appear in the page
# ---------------------------------------------------------------------------

class TestDebtFieldsRendered(unittest.TestCase):

    EXPECTED_FIELD_IDS = [
        "debt.senior.gearing_pct",
        "debt.senior.target_dscr",
        "debt.senior.interest_rate_pct",
        "debt.senior.tenor_years",
    ]

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "fields-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.div = _debt_div(html)

    def test_all_bound_field_ids_present_in_dom(self):
        fids_in_dom = [el["data-field-id"]
                       for el in self.div.find_all(attrs={"data-field-id": True})]
        for fid in self.EXPECTED_FIELD_IDS:
            self.assertIn(fid, fids_in_dom, f"Field {fid!r} missing from debt sheet DOM")

    def test_no_duplicate_field_ids(self):
        fids = [el["data-field-id"]
                for el in self.div.find_all(attrs={"data-field-id": True})]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids in debt sheet DOM: {dupes}")

    def test_bound_fields_are_editable(self):
        editable = self.div.find_all(class_="v2-field-editable")
        self.assertGreater(len(editable), 0, "Expected editable fields in debt sheet")

    def test_forms_use_debt_sheet_id(self):
        for form in self.div.find_all("form", class_="v2-field-form"):
            sid = form.find("input", {"name": "sheet_id"})
            self.assertIsNotNone(sid, "form missing sheet_id input")
            self.assertEqual(sid.get("value"), "debt",
                             f"form has wrong sheet_id: {sid.get('value')!r}")

    def test_forms_target_debt_sheet(self):
        for form in self.div.find_all("form", class_="v2-field-form"):
            self.assertEqual(form.get("hx-target"), "#v2-sheet-senior-debt",
                             f"form hx-target wrong: {form.get('hx-target')!r}")

    def test_placeholder_rows_present(self):
        text = self.div.get_text()
        for label in ("Base Rate", "Grace Period", "Repayment Profile", "DSRA (months)"):
            self.assertIn(label, text, f"Placeholder row '{label}' missing")

    def test_build_sheet_fields_returns_4_debt_fields(self):
        rows = _build_sheet_fields("debt", _fake_pis())
        bound = [r for r in rows if r["binding_label"] == "bound"]
        self.assertEqual(len(bound), 4, f"Expected 4 BOUND debt fields, got {len(bound)}")

    def test_no_legacy_snapshot_keys_in_forms(self):
        legacy = {"gearing_pct", "target_dscr", "interest_rate_pct", "tenor_years"}
        for form in self.div.find_all("form", class_="v2-field-form"):
            fid_input = form.find("input", {"name": "field_id"})
            if fid_input:
                val = fid_input.get("value", "")
                self.assertNotIn(val, legacy,
                                 f"Legacy snapshot key {val!r} used as field_id in form")


# ---------------------------------------------------------------------------
# 3. HTMX edit round-trip
# ---------------------------------------------------------------------------

class TestDebtFieldEditHtmxRoundTrip(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "htmx-debt-01")

    def _get_first_bound_form_data(self):
        html = _get_workbook(self.client, self.project_code)
        div = _debt_div(html)
        form = div.find("form", class_="v2-field-form")
        if not form:
            return None, None, None
        fid = form.find("input", {"name": "field_id"})
        wv = form.find("input", {"name": "workbook_version"})
        ch = form.find("input", {"name": "content_hash"})
        return (
            fid.get("value") if fid else None,
            wv.get("value") if wv else None,
            ch.get("value") if ch else None,
        )

    def test_htmx_update_returns_200(self):
        fid, wv, ch = self._get_first_bound_form_data()
        self.assertIsNotNone(fid, "No BOUND field form found in debt sheet")
        resp = self.client.post(
            "/v2/workbook/update",
            data={"field_id": fid, "value": "65", "project": self.project_code,
                  "workbook_version": wv or "", "content_hash": ch or "",
                  "sheet_id": "debt"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)

    def test_htmx_update_rerenders_debt_sheet(self):
        fid, wv, ch = self._get_first_bound_form_data()
        if not fid:
            self.skipTest("No BOUND field form in debt sheet")
        resp = self.client.post(
            "/v2/workbook/update",
            data={"field_id": fid, "value": "68", "project": self.project_code,
                  "workbook_version": wv or "", "content_hash": ch or "",
                  "sheet_id": "debt"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-senior-debt", resp.text)

    def test_htmx_update_includes_oob_status_banner(self):
        fid, wv, ch = self._get_first_bound_form_data()
        if not fid:
            self.skipTest("No BOUND field form in debt sheet")
        resp = self.client.post(
            "/v2/workbook/update",
            data={"field_id": fid, "value": "72", "project": self.project_code,
                  "workbook_version": wv or "", "content_hash": ch or "",
                  "sheet_id": "debt"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)

    def test_htmx_content_hash_rotates_after_edit(self):
        fid, wv, ch_before = self._get_first_bound_form_data()
        if not fid:
            self.skipTest("No BOUND field form in debt sheet")
        resp = self.client.post(
            "/v2/workbook/update",
            data={"field_id": fid, "value": "60", "project": self.project_code,
                  "workbook_version": wv or "", "content_hash": ch_before or "",
                  "sheet_id": "debt"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        ch_input = soup.find("input", {"name": "content_hash"})
        self.assertIsNotNone(ch_input, "content_hash input missing from HTMX response")
        self.assertNotEqual(ch_before, ch_input.get("value"),
                            "content_hash must rotate after a successful edit")


# ---------------------------------------------------------------------------
# 4. Pre-run empty state
# ---------------------------------------------------------------------------

class TestDebtPreRunEmptyState(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "prerun-debt-01")

    def _get_with_no_runtime(self) -> str:
        from app.persistence.workspace_repository import get_workspace_state as _real

        def _patched(*args, **kwargs):
            real = _real(*args, **kwargs)
            if real is None:
                return None
            return dataclasses.replace(
                real,
                last_runtime_snapshot_id=None,
                last_runtime_at=None,
            )

        with patch("app.persistence.workspace_repository.get_workspace_state",
                   side_effect=_patched):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        assert resp.status_code == 200
        return resp.text

    def test_pre_run_notice_present(self):
        html = self._get_with_no_runtime()
        div = _debt_div(html)
        self.assertIsNotNone(div, "Debt sheet not found")
        # Should show the empty state notice
        text = div.get_text()
        self.assertIn("Run the model", text)

    def test_no_kpi_tiles_without_runtime(self):
        html = self._get_with_no_runtime()
        div = _debt_div(html)
        kpi = div.find(attrs={"data-testid": "debt-kpi-bar"})
        self.assertIsNone(kpi, "KPI bar should not be present without runtime")

    def test_runtime_state_a_badge(self):
        html = self._get_with_no_runtime()
        div = _debt_div(html)
        badge = div.find(attrs={"data-testid": "debt-runtime-state-a"})
        self.assertIsNotNone(badge, "State A badge missing when no runtime")


# ---------------------------------------------------------------------------
# 5. Debt schedule rendered from mocked RuntimeResult
# ---------------------------------------------------------------------------

class TestDebtScheduleRenderedFromRuntime(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "sched-debt-01")

    def _make_fake_rr(self):
        """Build a minimal fake RuntimeResult with debt_schedule data."""
        rr = MagicMock()
        rr.debt_schedule = {
            "periods": [
                {
                    "period": 1,
                    "date": "2029-06-30",
                    "year_index": 1,
                    "period_in_year": 1,
                    "is_operation": True,
                    "senior_balance_keur": 50000.0,
                    "senior_principal_keur": 1500.0,
                    "senior_interest_keur": 2250.0,
                    "senior_ds_keur": 3750.0,
                    "dscr": 1.45,
                    "dsra_balance_keur": 3750.0,
                    "dsra_contribution_keur": 0.0,
                },
                {
                    "period": 2,
                    "date": "2029-12-31",
                    "year_index": 1,
                    "period_in_year": 2,
                    "is_operation": True,
                    "senior_balance_keur": 48500.0,
                    "senior_principal_keur": 1500.0,
                    "senior_interest_keur": 2182.5,
                    "senior_ds_keur": 3682.5,
                    "dscr": 1.48,
                    "dsra_balance_keur": 3682.5,
                    "dsra_contribution_keur": 0.0,
                },
            ],
            "summary": {
                "total_senior_ds_keur": 75000.0,
                "actual_min_dscr": 1.30,
                "actual_avg_dscr": 1.42,
                "target_dscr": 1.30,
                "min_llcr": 1.55,
                "periods_in_lockup": 0,
            },
        }
        rr.runtime_summary = {
            "project_irr": 0.08,
            "equity_irr": 0.12,
            "total_senior_ds_keur": 75000.0,
            "min_dscr": 1.30,
            "avg_dscr": 1.42,
            "target_dscr": 1.30,
        }
        return rr

    def test_debt_schedule_table_present_with_runtime(self):
        fake_rr = self._make_fake_rr()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=fake_rr):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")

        self.assertEqual(resp.status_code, 200)
        div = _debt_div(resp.text)
        self.assertIsNotNone(div, "Debt sheet not found")
        table = div.find(attrs={"data-testid": "debt-schedule-table"})
        self.assertIsNotNone(table, "Debt schedule table missing with runtime data")

    def test_debt_kpi_bar_present_with_runtime(self):
        fake_rr = self._make_fake_rr()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=fake_rr):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")

        self.assertEqual(resp.status_code, 200)
        div = _debt_div(resp.text)
        kpi = div.find(attrs={"data-testid": "debt-kpi-bar"})
        self.assertIsNotNone(kpi, "KPI bar missing with runtime data")

    def test_debt_schedule_rows_rendered(self):
        fake_rr = self._make_fake_rr()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=fake_rr):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")

        self.assertEqual(resp.status_code, 200)
        div = _debt_div(resp.text)
        rows = div.find_all(attrs={"data-testid": lambda v: v and v.startswith("debt-schedule-row-")})
        self.assertEqual(len(rows), 2, f"Expected 2 schedule rows, got {len(rows)}")

    def test_kpi_avg_dscr_value_rendered(self):
        fake_rr = self._make_fake_rr()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=fake_rr):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")

        self.assertEqual(resp.status_code, 200)
        div = _debt_div(resp.text)
        tile = div.find(attrs={"data-testid": "debt-kpi-avg-dscr"})
        self.assertIsNotNone(tile, "Avg DSCR tile missing")
        self.assertIn("1.42", tile.get_text())

    def test_runtime_state_b_with_clean_runtime(self):
        fake_rr = self._make_fake_rr()
        from app.persistence.workspace_repository import get_workspace_state as _real

        def _patched(*args, **kwargs):
            real = _real(*args, **kwargs)
            if real is None:
                return None
            return dataclasses.replace(
                real,
                dirty=False,
                last_runtime_snapshot_id="snap-001",
            )

        with patch("app.persistence.workspace_repository.get_workspace_state",
                   side_effect=_patched):
            with patch("app.workbook.service.WorkbookService.get_runtime_result",
                       return_value=fake_rr):
                resp = self.client.get(f"/v2/workbook?project={self.project_code}")

        self.assertEqual(resp.status_code, 200)
        div = _debt_div(resp.text)
        badge = div.find(attrs={"data-testid": "debt-runtime-state-b"})
        self.assertIsNotNone(badge, "State B badge missing with clean runtime")


# ---------------------------------------------------------------------------
# 6. Server-side operational-period filtering
# ---------------------------------------------------------------------------

class TestDebtOperationalPeriodFiltering(unittest.TestCase):
    """_build_debt_ctx must filter construction periods before the template sees them."""

    def _make_ws(self, has_runtime=True):
        ws = MagicMock()
        ws.last_runtime_snapshot_id = "snap-001" if has_runtime else None
        ws.dirty = False
        return ws

    def _make_rr_with_mixed_periods(self):
        """RuntimeResult with 2 construction periods and 3 operational periods."""
        rr = MagicMock()
        rr.debt_schedule = {
            "periods": [
                # construction draw-downs — must be excluded
                {"period": -2, "date": "2025-06-30", "is_operation": False,
                 "senior_balance_keur": 0.0, "senior_principal_keur": 0.0,
                 "senior_interest_keur": 500.0, "senior_ds_keur": 500.0,
                 "dscr": None, "dsra_balance_keur": 0.0},
                {"period": -1, "date": "2026-12-31", "is_operation": False,
                 "senior_balance_keur": 55000.0, "senior_principal_keur": 0.0,
                 "senior_interest_keur": 1000.0, "senior_ds_keur": 1000.0,
                 "dscr": None, "dsra_balance_keur": 0.0},
                # operational periods — must be retained in order
                {"period": 1, "date": "2027-06-30", "is_operation": True,
                 "senior_balance_keur": 54000.0, "senior_principal_keur": 1000.0,
                 "senior_interest_keur": 2475.0, "senior_ds_keur": 3475.0,
                 "dscr": 1.40, "dsra_balance_keur": 3475.0},
                {"period": 2, "date": "2027-12-31", "is_operation": True,
                 "senior_balance_keur": 53000.0, "senior_principal_keur": 1000.0,
                 "senior_interest_keur": 2430.0, "senior_ds_keur": 3430.0,
                 "dscr": 1.42, "dsra_balance_keur": 3430.0},
                {"period": 3, "date": "2028-06-30", "is_operation": True,
                 "senior_balance_keur": 52000.0, "senior_principal_keur": 1000.0,
                 "senior_interest_keur": 2385.0, "senior_ds_keur": 3385.0,
                 "dscr": 1.44, "dsra_balance_keur": 3385.0},
            ],
            "summary": {
                "total_senior_ds_keur": 100000.0, "actual_min_dscr": 1.40,
                "actual_avg_dscr": 1.42, "target_dscr": 1.30,
                "min_llcr": 1.55, "periods_in_lockup": 0,
            },
        }
        rr.runtime_summary = {
            "total_senior_ds_keur": 100000.0, "min_dscr": 1.40,
            "avg_dscr": 1.42, "target_dscr": 1.30,
        }
        return rr

    def test_construction_periods_excluded(self):
        """_build_debt_ctx must not include is_operation=False periods."""
        from app.v2.router import _build_debt_ctx
        fake_rr = self._make_rr_with_mixed_periods()
        fake_pis = _fake_pis()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=fake_rr):
            ctx = _build_debt_ctx(fake_pis, self._make_ws())

        op = ctx["debt_operational_periods"]
        self.assertIsNotNone(op, "debt_operational_periods should not be None with runtime")
        for p in op:
            self.assertTrue(p["is_operation"],
                            f"Period {p['period']} is not operational but appears in output")
        # Both construction periods (period -2 and -1) must be absent
        periods_in_output = {p["period"] for p in op}
        self.assertNotIn(-2, periods_in_output, "Construction period -2 leaked into output")
        self.assertNotIn(-1, periods_in_output, "Construction period -1 leaked into output")

    def test_operational_periods_retained_in_order(self):
        """Operational periods must appear in original schedule order."""
        from app.v2.router import _build_debt_ctx
        fake_rr = self._make_rr_with_mixed_periods()
        fake_pis = _fake_pis()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=fake_rr):
            ctx = _build_debt_ctx(fake_pis, self._make_ws())

        op = ctx["debt_operational_periods"]
        self.assertEqual([p["period"] for p in op], [1, 2, 3],
                         "Operational periods not in original order")

    def test_empty_operational_set_renders_truthful_empty_state(self):
        """When schedule has only construction periods, table shows empty-state notice."""
        from app.v2.router import _build_debt_ctx
        rr = MagicMock()
        rr.debt_schedule = {
            "periods": [
                {"period": -1, "date": "2026-12-31", "is_operation": False,
                 "senior_balance_keur": 55000.0, "senior_principal_keur": 0.0,
                 "senior_interest_keur": 1000.0, "senior_ds_keur": 1000.0,
                 "dscr": None, "dsra_balance_keur": 0.0},
            ],
            "summary": {},
        }
        rr.runtime_summary = {}
        fake_pis = _fake_pis()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=rr):
            ctx = _build_debt_ctx(fake_pis, self._make_ws())

        op = ctx["debt_operational_periods"]
        self.assertIsNotNone(op, "debt_operational_periods should not be None when schedule exists")
        self.assertEqual(op, [], "Expected empty list when all periods are construction")

    def test_empty_operational_set_template_shows_empty_state(self):
        """When debt_operational_periods is [], the template shows the empty-state row."""
        client = _authed_client()
        project_code = _create_project(client, "op-empty-01")

        rr = MagicMock()
        rr.debt_schedule = {
            "periods": [
                {"period": -1, "date": "2026-12-31", "is_operation": False,
                 "senior_balance_keur": 55000.0, "senior_principal_keur": 0.0,
                 "senior_interest_keur": 1000.0, "senior_ds_keur": 1000.0,
                 "dscr": None, "dsra_balance_keur": 0.0},
            ],
            "summary": {"total_senior_ds_keur": 1000.0, "actual_min_dscr": None,
                        "actual_avg_dscr": None, "target_dscr": 1.30,
                        "min_llcr": None, "periods_in_lockup": 0},
        }
        rr.runtime_summary = {"total_senior_ds_keur": 1000.0, "min_dscr": None, "avg_dscr": None}

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=rr):
            resp = client.get(f"/v2/workbook?project={project_code}")

        self.assertEqual(resp.status_code, 200)
        div = _debt_div(resp.text)
        # Empty-state element should be present; table should NOT be present
        empty = div.find(attrs={"data-testid": "debt-schedule-empty"})
        self.assertIsNotNone(empty, "Empty-state notice missing when only construction periods")
        table = div.find(attrs={"data-testid": "debt-schedule-table"})
        self.assertIsNone(table, "Schedule table must not render when operational set is empty")

    def test_no_runtime_yields_none_operational_periods(self):
        """When no runtime result exists, debt_operational_periods must be None."""
        from app.v2.router import _build_debt_ctx
        fake_pis = _fake_pis()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=None):
            ctx = _build_debt_ctx(fake_pis, self._make_ws(has_runtime=False))

        self.assertIsNone(ctx["debt_operational_periods"],
                          "debt_operational_periods must be None when no RuntimeResult")

    def test_construction_excluded_and_table_shows_only_operational_rows(self):
        """Template must render exactly the operational rows, none of the construction ones."""
        client = _authed_client()
        project_code = _create_project(client, "op-filter-01")
        fake_rr = self._make_rr_with_mixed_periods()

        with patch("app.workbook.service.WorkbookService.get_runtime_result",
                   return_value=fake_rr):
            resp = client.get(f"/v2/workbook?project={project_code}")

        self.assertEqual(resp.status_code, 200)
        div = _debt_div(resp.text)
        rows = div.find_all(attrs={"data-testid": lambda v: v and v.startswith("debt-schedule-row-")})
        row_ids = [r["data-testid"] for r in rows]
        # Must see exactly the 3 operational rows
        self.assertEqual(len(rows), 3, f"Expected 3 operational rows, got {len(rows)}: {row_ids}")
        # Construction period numbers (-2, -1) must not appear as row testids
        self.assertNotIn("debt-schedule-row--2", row_ids, "Construction period -2 rendered")
        self.assertNotIn("debt-schedule-row--1", row_ids, "Construction period -1 rendered")


if __name__ == "__main__":
    unittest.main()
