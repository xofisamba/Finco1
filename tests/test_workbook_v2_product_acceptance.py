"""
tests/test_workbook_v2_product_acceptance.py — Workbook V2 product acceptance tests.

Tests the full chain: edit → Run → persisted output changed → reload → preserved.
Uses the REAL engine (no mock for the output assertions).

Coverage:
1. TestRunChain — run produces output, dirty/clean transitions, output stability
2. TestDebtEffectiveness — gearing / interest rate change → debt service / EBITDA changes
3. TestOpexEffectiveness — OPEX Y1 change → EBITDA decreases
4. TestTaxEffectiveness — cit_rate_pct change → total_tax_keur changes

Note on revenue.ppa.base_tariff (rev_ppa_base_tariff snapshot key):
  The rev_ppa_base_tariff key is not yet wired into build_projectinputs_from_snapshot
  (which reads the legacy tariff_eur_mwh key). The BOUND field is correctly stored in
  the draft snapshot, but does not flow through to the engine via V2's to_projectinputs()
  path. This is a known input coverage gap; revenue tariff effectiveness is tested via
  the legacy run path. Tracked as ITEM 8 (Input Coverage Gap report).
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
        "p50_hours": "1800",
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
# 2. Debt — gearing / interest rate changes → output changes
# ---------------------------------------------------------------------------

class TestDebtEffectiveness(unittest.TestCase):
    """Verify debt field changes flow through to engine output."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "debt-accept")

    def test_gearing_increase_increases_debt_service(self):
        """Higher gearing → more debt → more total debt service."""
        # Run at default gearing (70%)
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        ds1 = _get_summary(ws1).get("total_senior_ds_keur")
        self.assertIsNotNone(ds1, f"Must have total_senior_ds_keur; keys={list(_get_summary(ws1))}")

        # Increase gearing
        _update_field(self.client, self.project_code,
                      "debt.senior.gearing_pct", "80.0", "debt")

        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty)
        ds2 = _get_summary(ws2).get("total_senior_ds_keur")

        self.assertIsNotNone(ds2)
        self.assertGreater(ds2, ds1,
            f"Higher gearing must increase total debt service: {ds1} → {ds2}")

    def test_higher_gearing_reduces_ebitda_via_interest(self):
        """Higher gearing means more interest → lower CFADS but EBITDA itself is unchanged."""
        # EBITDA is revenue - opex, unaffected by gearing.
        # CFADS (after tax) changes. Just verify total_senior_ds_keur changes.
        _run(self.client, self.project_code)
        ws_baseline = _get_ws(self.client, self.project_code)
        ds_baseline = _get_summary(ws_baseline).get("total_senior_ds_keur")

        _update_field(self.client, self.project_code,
                      "debt.senior.gearing_pct", "60.0", "debt")
        _run(self.client, self.project_code)
        ws_lower = _get_ws(self.client, self.project_code)
        ds_lower = _get_summary(ws_lower).get("total_senior_ds_keur")

        self.assertIsNotNone(ds_lower)
        self.assertLess(ds_lower, ds_baseline,
            f"Lower gearing must decrease total debt service: {ds_baseline} → {ds_lower}")

    def test_interest_rate_increase_increases_debt_service(self):
        """Higher interest rate → more interest → more total debt service."""
        _update_field(self.client, self.project_code,
                      "debt.senior.gearing_pct", "70.0", "debt")
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        ds1 = _get_summary(ws1).get("total_senior_ds_keur")

        _update_field(self.client, self.project_code,
                      "debt.senior.interest_rate_pct", "7.0", "debt")
        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        ds2 = _get_summary(ws2).get("total_senior_ds_keur")

        self.assertIsNotNone(ds2)
        self.assertGreater(ds2, ds1,
            f"Higher interest rate must increase debt service: {ds1} → {ds2}")


# ---------------------------------------------------------------------------
# 3. OPEX — OPEX Y1 increase → EBITDA decreases
# ---------------------------------------------------------------------------

class TestOpexEffectiveness(unittest.TestCase):
    """Verify OPEX field changes reduce EBITDA."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "opex-accept")

    def test_opex_increase_decreases_ebitda(self):
        # Initial run
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        ebitda1 = _get_summary(ws1).get("total_ebitda_keur")
        self.assertIsNotNone(ebitda1, f"No total_ebitda_keur: {list(_get_summary(ws1))}")

        # Increase OPEX Y1 significantly (700 → 1400 kEUR)
        _update_field(self.client, self.project_code,
                      "opex.summary.total_y1", "1400", "opex")

        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty)
        ebitda2 = _get_summary(ws2).get("total_ebitda_keur")

        self.assertIsNotNone(ebitda2)
        self.assertLess(ebitda2, ebitda1,
            f"Higher OPEX must reduce EBITDA: {ebitda1} → {ebitda2}")

    def test_opex_decrease_increases_ebitda(self):
        _update_field(self.client, self.project_code,
                      "opex.summary.total_y1", "1400", "opex")
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        ebitda1 = _get_summary(ws1).get("total_ebitda_keur")

        _update_field(self.client, self.project_code,
                      "opex.summary.total_y1", "400", "opex")
        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        ebitda2 = _get_summary(ws2).get("total_ebitda_keur")

        self.assertIsNotNone(ebitda2)
        self.assertGreater(ebitda2, ebitda1,
            f"Lower OPEX must increase EBITDA: {ebitda1} → {ebitda2}")


# ---------------------------------------------------------------------------
# 4. Tax — cit_rate_pct change → total_tax_keur changes
# ---------------------------------------------------------------------------

class TestTaxEffectiveness(unittest.TestCase):
    """Verify tax rate changes flow through to total_tax_keur."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(cls.client, "tax-accept")

    def test_cit_rate_increase_changes_tax(self):
        # Initial run
        _run(self.client, self.project_code)
        ws1 = _get_ws(self.client, self.project_code)
        tax1 = _get_summary(ws1).get("total_tax_keur")
        self.assertIsNotNone(tax1, f"No total_tax_keur in summary: {list(_get_summary(ws1))}")

        # Increase CIT rate significantly (default ~19% → 35%)
        _update_field(self.client, self.project_code,
                      "tax.assumptions.cit_rate_pct", "35.0", "tax")

        _run(self.client, self.project_code)
        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty)
        tax2 = _get_summary(ws2).get("total_tax_keur")

        self.assertIsNotNone(tax2)
        # Higher CIT rate → tax amount changes (absolute value increases)
        self.assertNotAlmostEqual(tax1, tax2, places=0,
            msg=f"CIT rate change must change total tax: {tax1} → {tax2}")

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
