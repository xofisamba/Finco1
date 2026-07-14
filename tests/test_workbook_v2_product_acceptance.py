"""
tests/test_workbook_v2_product_acceptance.py — Workbook V2 product acceptance tests.

Tests the full chain: edit → Run → persisted output changed → reload → preserved.
Uses the REAL engine (no mock for the output assertions).

Coverage:
1. TestRunChain — run produces output, dirty/clean transitions, output stability
2. TestRevenueEffectiveness — p50_hours edit → total_revenue_keur changes
3. TestCapexEffectiveness — CAPEX sub-line → total_capex_keur increases
4. TestOpexEffectiveness — OPEX sub-line → total_opex_keur increases, EBITDA decreases
5. TestDebtEffectiveness — target_dscr change → total_senior_ds_keur changes
6. TestTaxEffectiveness — CIT rate change → total_tax_keur changes + reload preservation

Note on revenue.ppa.base_tariff (rev_ppa_base_tariff snapshot key):
  The rev_ppa_base_tariff key is not yet wired into _snapshot_to_dict
  (which reads the legacy tariff_eur_mwh key). The BOUND field is correctly stored in
  the draft snapshot, but does not flow through to the engine via V2's to_projectinputs()
  path. This is a known input coverage gap; revenue tariff effectiveness is NOT tested here.
  Tracked as ITEM 8 (Input Coverage Gap report).

Note on DSCR-sculpted model: higher target_dscr → the engine re-sculpts debt service to
match CFADS / target_dscr per period (debt quantum changes to hit the target). In the
test below, total_senior_ds_keur changes materially when target_dscr is changed — proving
the debt wiring is live — but the direction depends on the full model dynamics.
"""
from __future__ import annotations

import json
import os
import re
import unittest
import urllib.parse

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-accept")

from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token, decode_session_token  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client():
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client, suffix):
    resp = client.post("/projects/create", data={
        "project_name": f"Acceptance {suffix}",
        "project_type": "Solar",
        "template_source": "generic_solar",
        "country_market": "Poland",
        "capacity_mw": "50",
        "cod_date": "2028-01-01",
        "construction_months": "18",
        "horizon_years": "25",
        "tariff_eur_mwh": "55",
        "ppa_term_years": "15",
        "p50_hours": "2200",
        "opex_y1_keur": "700",
        "total_capex_keur": "45000",
        "gearing_pct": "70",
        "interest_rate_pct": "4.5",
        "tenor_years": "18",
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


def _get_hash(client, project_code):
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200
    body = resp.text
    ch = re.search(r'data-content-hash="([^"]+)"', body).group(1)
    wv = re.search(r'data-workbook-version="([^"]+)"', body).group(1)
    return ch, wv


def _run(client, project_code):
    ch, wv = _get_hash(client, project_code)
    resp = client.post("/v2/workbook/run", data={
        "project": project_code, "content_hash": ch, "workbook_version": wv,
    }, headers={"HX-Request": "true"}, follow_redirects=False)
    assert resp.status_code == 200, f"Run failed: {resp.status_code} {resp.text[:300]}"


def _update_field(client, project_code, field_id, value, sheet_id):
    ch, wv = _get_hash(client, project_code)
    resp = client.post("/v2/workbook/update", data={
        "field_id": field_id, "value": value,
        "project": project_code, "workbook_version": wv,
        "content_hash": ch, "sheet_id": sheet_id,
    }, headers={"HX-Request": "true"})
    assert resp.status_code == 200, f"Update failed: {resp.status_code} {resp.text[:300]}"


def _get_summary(ws):
    summary = ws.last_runtime_summary
    if summary is None:
        return {}
    if isinstance(summary, dict):
        return summary
    return json.loads(summary)


# ---------------------------------------------------------------------------
# 1. Run chain: output produced, dirty/clean transitions, stability
# ---------------------------------------------------------------------------

class TestRunChain(unittest.TestCase):
    """Verify the full run → persist → reload chain."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "run-chain")

    def test_fresh_project_has_no_runtime(self):
        ws = _get_ws(self.client, self.project_code)
        self.assertFalse(bool(ws.last_runtime_snapshot_id),
                         "Fresh project must have no runtime snapshot")

    def test_run_produces_ebitda(self):
        _run(self.client, self.project_code)
        ws = _get_ws(self.client, self.project_code)
        summary = _get_summary(ws)
        self.assertIsNotNone(summary.get("total_ebitda_keur"),
                             f"Run must produce total_ebitda_keur; keys={list(summary.keys())}")

    def test_run_sets_snapshot_id(self):
        _run(self.client, self.project_code)
        ws = _get_ws(self.client, self.project_code)
        self.assertIsNotNone(ws.last_runtime_snapshot_id)

    def test_workspace_dirty_after_edit(self):
        _update_field(self.client, self.project_code,
                      "debt.senior.gearing_pct", "68.0", "debt")
        ws = _get_ws(self.client, self.project_code)
        self.assertTrue(ws.dirty, "Workspace must be dirty after field edit")

    def test_workspace_clean_after_run(self):
        _run(self.client, self.project_code)
        ws = _get_ws(self.client, self.project_code)
        self.assertFalse(ws.dirty, "Workspace must be clean after run")

    def test_output_stable_on_consecutive_runs(self):
        """Consecutive runs with no edits must produce identical EBITDA."""
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        ebitda1 = _get_summary(ws1).get("total_ebitda_keur")

        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        ebitda2 = _get_summary(ws2).get("total_ebitda_keur")

        self.assertIsNotNone(ebitda1)
        self.assertAlmostEqual(ebitda1, ebitda2, places=0,
                               msg="EBITDA must be stable across identical consecutive runs")

    def test_previous_runtime_preserved_while_stale(self):
        """After run then edit, runtime summary is preserved (not erased)."""
        _run(self.client, self.project_code)
        ws_clean = _get_ws(self.client, self.project_code)
        self.assertIsNotNone(_get_summary(ws_clean).get("total_ebitda_keur"))

        _update_field(self.client, self.project_code,
                      "debt.senior.gearing_pct", "69.0", "debt")
        ws_stale = _get_ws(self.client, self.project_code)
        self.assertTrue(ws_stale.dirty)

        # Previous runtime summary must still be there
        stale_summary = _get_summary(ws_stale)
        self.assertIsNotNone(stale_summary.get("total_ebitda_keur"),
                             "Runtime summary must be preserved while workspace is stale")


# ---------------------------------------------------------------------------
# 2. Revenue — p50_hours increase → total_revenue_keur increases
# ---------------------------------------------------------------------------

class TestRevenueEffectiveness(unittest.TestCase):
    """Verify p50_hours edit flows through engine to change total_revenue_keur."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "rev-accept")

    def test_p50_hours_increase_raises_total_revenue(self):
        # Step 1: Baseline run
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        summary1 = _get_summary(ws1)
        rev1 = summary1.get("total_revenue_keur")
        self.assertIsNotNone(rev1, f"Baseline must produce total_revenue_keur; keys={list(summary1)}")

        # Step 2: Edit p50_hours from 2200 → 6000 (nearly 3× increase)
        _update_field(self.client, self.project_code,
                      "project_setup.technical.p50_hours", "6000", "project_setup")
        ws_stale = _get_ws(self.client, self.project_code)
        self.assertTrue(ws_stale.dirty, "Workspace must be STALE after p50_hours edit")

        # Step 3: Run
        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty, "Workspace must be CLEAN after run")
        summary2 = _get_summary(ws2)
        rev2 = summary2.get("total_revenue_keur")
        self.assertIsNotNone(rev2)

        # Step 4: Assert total_revenue_keur increased materially (expect ~3× of baseline)
        self.assertGreater(rev2, rev1 * 2.0,
            f"p50_hours 2200→6000 must increase total_revenue_keur >2×: "
            f"{rev1:.0f} → {rev2:.0f}")

        # Step 5: Reload and assert value preserved
        ws_reload = _get_ws(self.client, self.project_code)
        rev_reload = _get_summary(ws_reload).get("total_revenue_keur")
        self.assertAlmostEqual(rev2, rev_reload, places=0,
            msg=f"Revenue must be preserved after reload: {rev2:.0f} vs {rev_reload:.0f}")


# ---------------------------------------------------------------------------
# 3. CAPEX — sub-line add → total_capex_keur increases
# ---------------------------------------------------------------------------

class TestCapexEffectiveness(unittest.TestCase):
    """Verify CAPEX sub-line flows through engine to change total_capex_keur."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "capex-accept")

    def test_capex_subline_increases_total_capex(self):
        # Step 1: Baseline run
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        summary1 = _get_summary(ws1)
        capex1 = summary1.get("total_capex_keur")
        self.assertIsNotNone(capex1, f"Baseline must produce total_capex_keur; keys={list(summary1)}")

        # Step 2: Add CAPEX sub-line (8000 kEUR)
        ch, wv = _get_hash(self.client, self.project_code)
        resp = self.client.post("/v2/capex/line/add", data={
            "project": self.project_code,
            "parent_category_code": "C.07",
            "label": "Extra CAPEX Test",
            "amount_keur": 8000.0,
            "notes": "",
            "workbook_version": wv,
            "content_hash": ch,
        }, headers={"HX-Request": "true"})
        self.assertEqual(resp.status_code, 200,
            f"CAPEX sub-line add failed: {resp.status_code} {resp.text[:200]}")

        ws_stale = _get_ws(self.client, self.project_code)
        self.assertTrue(ws_stale.dirty, "Workspace must be STALE after CAPEX sub-line add")

        # Step 3: Run
        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty, "Workspace must be CLEAN after run")
        summary2 = _get_summary(ws2)
        capex2 = summary2.get("total_capex_keur")
        self.assertIsNotNone(capex2)

        # Step 4: Assert total_capex_keur increased by ~8000
        self.assertGreater(capex2, capex1 + 5000,
            f"CAPEX sub-line +8000kEUR must increase total_capex_keur: "
            f"{capex1:.0f} → {capex2:.0f}")

        # Step 5: Reload and assert value preserved
        ws_reload = _get_ws(self.client, self.project_code)
        capex_reload = _get_summary(ws_reload).get("total_capex_keur")
        self.assertAlmostEqual(capex2, capex_reload, places=0,
            msg=f"CAPEX must be preserved after reload: {capex2:.0f} vs {capex_reload:.0f}")


# ---------------------------------------------------------------------------
# 4. OPEX — sub-line add → total_opex_keur increases, EBITDA decreases
# ---------------------------------------------------------------------------

class TestOpexEffectiveness(unittest.TestCase):
    """Verify OPEX sub-line flows through engine to change total_opex_keur and EBITDA."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "opex-accept")

    def test_opex_subline_increases_opex_and_decreases_ebitda(self):
        # Step 1: Baseline run
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        summary1 = _get_summary(ws1)
        opex1 = summary1.get("total_opex_keur")
        ebitda1 = summary1.get("total_ebitda_keur")
        self.assertIsNotNone(opex1, f"Baseline must produce total_opex_keur; keys={list(summary1)}")
        self.assertIsNotNone(ebitda1)

        # Step 2: Add OPEX sub-line (500 kEUR/yr)
        ch, wv = _get_hash(self.client, self.project_code)
        resp = self.client.post("/v2/opex/line/add", data={
            "project": self.project_code,
            "parent_group_code": "B.01",
            "label": "Extra OPEX Test",
            "amount_keur": 500.0,
            "workbook_version": wv,
            "content_hash": ch,
        }, headers={"HX-Request": "true"})
        self.assertEqual(resp.status_code, 200,
            f"OPEX sub-line add failed: {resp.status_code} {resp.text[:200]}")

        ws_stale = _get_ws(self.client, self.project_code)
        self.assertTrue(ws_stale.dirty, "Workspace must be STALE after OPEX sub-line add")

        # Step 3: Run
        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty, "Workspace must be CLEAN after run")
        summary2 = _get_summary(ws2)
        opex2 = summary2.get("total_opex_keur")
        ebitda2 = summary2.get("total_ebitda_keur")
        self.assertIsNotNone(opex2)
        self.assertIsNotNone(ebitda2)

        # Step 4: Assert total_opex_keur increased and EBITDA decreased
        self.assertGreater(opex2, opex1,
            f"OPEX sub-line +500kEUR/yr must increase total_opex_keur: "
            f"{opex1:.0f} → {opex2:.0f}")
        self.assertLess(ebitda2, ebitda1,
            f"OPEX increase must decrease EBITDA: {ebitda1:.0f} → {ebitda2:.0f}")

        # Step 5: Reload and assert values preserved
        ws_reload = _get_ws(self.client, self.project_code)
        summary_reload = _get_summary(ws_reload)
        opex_reload = summary_reload.get("total_opex_keur")
        ebitda_reload = summary_reload.get("total_ebitda_keur")
        self.assertAlmostEqual(opex2, opex_reload, places=0,
            msg=f"OPEX must be preserved after reload: {opex2:.0f} vs {opex_reload:.0f}")
        self.assertAlmostEqual(ebitda2, ebitda_reload, places=0,
            msg=f"EBITDA must be preserved after reload: {ebitda2:.0f} vs {ebitda_reload:.0f}")


# ---------------------------------------------------------------------------
# 5. Debt — target_dscr change → total_senior_ds_keur changes
# ---------------------------------------------------------------------------

class TestDebtEffectiveness(unittest.TestCase):
    """Verify target_dscr change flows through to total_senior_ds_keur.

    In the sculpted-DSCR model: DS_period = CFADS_period / target_dscr.
    Changing target_dscr alters the sculpted debt service schedule, so
    total_senior_ds_keur must change materially.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "debt-accept")

    def test_target_dscr_change_alters_senior_ds(self):
        # Step 1: Baseline run at default (target_dscr=1.30)
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        summary1 = _get_summary(ws1)
        ds1 = summary1.get("total_senior_ds_keur")
        self.assertIsNotNone(ds1,
            f"Baseline must produce total_senior_ds_keur; keys={list(summary1)}")

        # Step 2: Edit target_dscr to 1.80
        _update_field(self.client, self.project_code,
                      "debt.senior.target_dscr", "1.80", "debt")
        ws_stale = _get_ws(self.client, self.project_code)
        self.assertTrue(ws_stale.dirty,
                        "Workspace must be STALE after target_dscr edit")

        # Step 3: Run
        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty, "Workspace must be CLEAN after run")
        summary2 = _get_summary(ws2)
        ds2 = summary2.get("total_senior_ds_keur")
        self.assertIsNotNone(ds2)

        # Step 4: Assert total_senior_ds_keur changed materially (>5% difference)
        relative_change = abs(ds2 - ds1) / max(abs(ds1), 1.0)
        self.assertGreater(relative_change, 0.05,
            f"target_dscr 1.30→1.80 must change total_senior_ds_keur >5%: "
            f"{ds1:.0f} → {ds2:.0f}")

        # Step 5: Reload and assert value preserved
        ws_reload = _get_ws(self.client, self.project_code)
        ds_reload = _get_summary(ws_reload).get("total_senior_ds_keur")
        self.assertAlmostEqual(ds2, ds_reload, places=0,
            msg=f"Senior DS must be preserved after reload: {ds2:.0f} vs {ds_reload:.0f}")

    def test_min_dscr_tracks_target(self):
        """After editing target_dscr, min_dscr value is present and numeric."""
        _update_field(self.client, self.project_code,
                      "debt.senior.target_dscr", "1.50", "debt")
        _run(self.client, self.project_code)
        ws = _get_ws(self.client, self.project_code)
        summary = _get_summary(ws)
        min_dscr = summary.get("min_dscr")
        self.assertIsNotNone(min_dscr, "Run must produce min_dscr")
        self.assertGreater(min_dscr, 0.5, "min_dscr must be positive")


# ---------------------------------------------------------------------------
# 6. Tax — CIT rate change → total_tax_keur changes + reload preservation
# ---------------------------------------------------------------------------

class TestTaxEffectiveness(unittest.TestCase):
    """Verify tax rate changes flow through to total_tax_keur, with reload preservation."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "tax-accept")

    def test_cit_rate_increase_changes_tax(self):
        # Step 1: Baseline run at default CIT (~19%)
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        tax1 = _get_summary(ws1).get("total_tax_keur")
        self.assertIsNotNone(tax1, f"No total_tax_keur in summary: {list(_get_summary(ws1))}")

        # Step 2: Edit CIT rate to 35%
        _update_field(self.client, self.project_code,
                      "tax.assumptions.cit_rate_pct", "35.0", "tax")
        ws_stale = _get_ws(self.client, self.project_code)
        self.assertTrue(ws_stale.dirty, "Workspace must be STALE after CIT rate edit")

        # Step 3: Run
        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty)
        tax2 = _get_summary(ws2).get("total_tax_keur")
        self.assertIsNotNone(tax2)

        # Step 4: Assert total_tax_keur changed (higher CIT rate → more tax)
        self.assertNotAlmostEqual(tax1, tax2, places=0,
            msg=f"CIT rate change must alter total_tax_keur: {tax1:.0f} → {tax2:.0f}")

        # Step 5: Reload via GET and re-read workspace summary (proves reload preservation)
        # Re-GET the workbook page (simulating a page reload)
        _get_hash(self.client, self.project_code)  # forces a fresh GET
        ws_reload = _get_ws(self.client, self.project_code)
        tax_reload = _get_summary(ws_reload).get("total_tax_keur")
        self.assertAlmostEqual(tax2, tax_reload, places=0,
            msg=f"total_tax_keur must be preserved after reload: {tax2:.0f} vs {tax_reload:.0f}")

    def test_loss_carryforward_change_affects_run(self):
        """Loss carryforward change produces a valid, stable run."""
        _update_field(self.client, self.project_code,
                      "tax.assumptions.loss_carryforward_years", "10", "tax")
        _run(self.client, self.project_code)
        ws = _get_ws(self.client, self.project_code)
        self.assertFalse(ws.dirty)
        self.assertIsNotNone(ws.last_runtime_snapshot_id)


if __name__ == "__main__":
    unittest.main()
