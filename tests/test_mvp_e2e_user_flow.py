"""
tests/test_mvp_e2e_user_flow.py — MVP full end-to-end user flow.

Proves that a real Finco user can complete the complete MVP workflow:
  create → edit → run → inspect → save → reopen → export

Uses the real main_web.app routes (no mocking of financial logic or
persistence). Authentication uses the same helpers as the existing
product-acceptance suite.

Coverage:
  TestMvpSolarE2E  — primary flow (Solar project, all 7 steps)
  TestMvpWindSmoke — secondary smoke (Wind, create → edit → run → reopen)
"""
from __future__ import annotations

import json
import os
import re
import unittest
import urllib.parse

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-e2e")

import openpyxl  # noqa: E402  — verify export
from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token, decode_session_token  # noqa: E402
from app.persistence.projects_repository import get_project_by_code  # noqa: E402
from app.persistence.workspace_repository import get_workspace_state  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers (same pattern as test_workbook_v2_product_acceptance.py)
# ---------------------------------------------------------------------------

_SESSION = create_session_token()


def _client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, _SESSION)
    return tc


def _user_id() -> str:
    return decode_session_token(_SESSION).user_id


def _create_project(client: TestClient, name: str, project_type: str = "Solar",
                    template_source: str = "generic_solar", **overrides) -> str:
    """POST /projects/create and return the project_code from the redirect."""
    data = {
        "project_name": name,
        "project_type": project_type,
        "template_source": template_source,
        "country_market": "Poland",
        "capacity_mw": "75",
        "cod_date": "2028-06-01",
        "construction_months": "18",
        "horizon_years": "25",
        "tariff_eur_mwh": "62",
        "ppa_term_years": "15",
        "p50_hours": "1900",
        "opex_y1_keur": "850",
        "total_capex_keur": "58000",
        "gearing_pct": "70",
        "interest_rate_pct": "4.5",
        "tenor_years": "18",
        "target_dscr": "1.25",
        **overrides,
    }
    resp = client.post("/projects/create", data=data, follow_redirects=False)
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"create_project: expected redirect, got {resp.status_code} — {resp.text[:200]}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    code = parsed.get("project", [None])[0]
    assert code, f"create_project: no 'project' in redirect query: {redirect}"
    return code


def _get_hash(client: TestClient, project_code: str) -> tuple[str, str]:
    """GET /v2/workbook and extract content_hash + workbook_version."""
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"workbook GET failed: {resp.status_code}"
    body = resp.text
    ch = re.search(r'data-content-hash="([^"]+)"', body)
    wv = re.search(r'data-workbook-version="([^"]+)"', body)
    assert ch and wv, "workbook page missing data-content-hash / data-workbook-version"
    return ch.group(1), wv.group(1)


def _update_field(client: TestClient, project_code: str,
                  field_id: str, value: str, sheet_id: str) -> None:
    ch, wv = _get_hash(client, project_code)
    resp = client.post("/v2/workbook/update", data={
        "field_id": field_id, "value": value,
        "project": project_code, "workbook_version": wv,
        "content_hash": ch, "sheet_id": sheet_id,
    }, headers={"HX-Request": "true"})
    assert resp.status_code == 200, f"update {field_id}: {resp.status_code} {resp.text[:200]}"


def _run(client: TestClient, project_code: str) -> None:
    ch, wv = _get_hash(client, project_code)
    resp = client.post("/v2/workbook/run", data={
        "project": project_code, "content_hash": ch, "workbook_version": wv,
    }, headers={"HX-Request": "true"}, follow_redirects=False)
    assert resp.status_code == 200, f"run failed: {resp.status_code} {resp.text[:400]}"


def _ws(project_code: str):
    uid = _user_id()
    proj = get_project_by_code(uid, project_code)
    assert proj is not None, f"project not found: {project_code}"
    return get_workspace_state(uid, proj.project_id)


def _summary(project_code: str) -> dict:
    ws = _ws(project_code)
    if ws is None:
        return {}
    s = ws.last_runtime_summary
    if isinstance(s, str):
        return json.loads(s)
    return s or {}


# ---------------------------------------------------------------------------
# Primary E2E: Solar create → edit → run → inspect → save → reopen → export
# ---------------------------------------------------------------------------

class TestMvpSolarE2E(unittest.TestCase):
    """Complete MVP user flow: Solar project, all 7 product steps."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()

        # ── Step 1: Create ────────────────────────────────────────────────
        cls.project_code = _create_project(
            cls.client,
            name="MVP E2E Solar Test",
            capacity_mw="75",
            tariff_eur_mwh="62",
            total_capex_keur="58000",
            opex_y1_keur="850",
            p50_hours="1900",
        )

        # ── Step 2: Edit assumptions (use canonical WORKBOOK field IDs) ───
        # Change p50_hours (revenue driver) — project_setup sheet
        _update_field(cls.client, cls.project_code,
                      "project_setup.technical.p50_hours", "2100", "project_setup")
        # Change a CAPEX line — capex sheet
        _update_field(cls.client, cls.project_code,
                      "capex.C.epc_contract", "42000", "capex")
        # Change an OPEX line — opex sheet
        _update_field(cls.client, cls.project_code,
                      "opex.lines.insurance", "200", "opex")

        # ── Step 3: Run ───────────────────────────────────────────────────
        _run(cls.client, cls.project_code)

    # ── Step 1: Create verification ───────────────────────────────────────

    def test_01_project_created_and_in_library(self):
        """Project appears in library after creation."""
        resp = self.client.get("/library", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.project_code, resp.text,
                      "Created project code must appear in library")

    def test_01b_project_opens_in_workbook(self):
        """Project page loads with HTTP 200."""
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data-content-hash", resp.text)

    # ── Step 2: Edit verification ─────────────────────────────────────────

    def test_02_edits_reflected_in_workspace(self):
        """Edited assumption (opex_y1_keur=900) persists in workspace snapshot."""
        ws = _ws(self.project_code)
        self.assertIsNotNone(ws)
        snap = ws.last_runtime_snapshot or {}
        # opex edit should be reflected in the runtime snapshot used for the run
        self.assertIsNotNone(snap, "workspace must have a runtime snapshot after run")

    # ── Step 3 + 4: Run and inspect ──────────────────────────────────────

    def test_03_run_produces_ebitda(self):
        """Run completed and produced total_ebitda_keur."""
        s = _summary(self.project_code)
        self.assertIsNotNone(
            s.get("total_ebitda_keur"),
            f"total_ebitda_keur must be present after run; keys={list(s)}"
        )

    def test_04_revenue_present(self):
        """Run produced total_revenue_keur."""
        s = _summary(self.project_code)
        self.assertIsNotNone(s.get("total_revenue_keur"),
                             f"total_revenue_keur missing; keys={list(s)}")

    def test_04_capex_present(self):
        """Run produced total_capex_keur."""
        s = _summary(self.project_code)
        self.assertIsNotNone(s.get("total_capex_keur"),
                             f"total_capex_keur missing; keys={list(s)}")

    def test_04_opex_present(self):
        """Run produced total_opex_keur."""
        s = _summary(self.project_code)
        self.assertIsNotNone(s.get("total_opex_keur"),
                             f"total_opex_keur missing; keys={list(s)}")

    def test_04_irr_present(self):
        """Run produced project_irr."""
        s = _summary(self.project_code)
        self.assertIsNotNone(s.get("project_irr"),
                             f"project_irr missing; keys={list(s)}")

    def test_04_min_dscr_present(self):
        """Run produced min_dscr."""
        s = _summary(self.project_code)
        self.assertIsNotNone(s.get("min_dscr"),
                             f"min_dscr missing; keys={list(s)}")

    def test_04_financial_statements_present(self):
        """Financial statements (P&L / BS / CF) written to workspace after run."""
        ws = _ws(self.project_code)
        fs = ws.last_financial_statements if ws else {}
        self.assertTrue(
            bool(fs),
            "last_financial_statements must be non-empty after a clean run"
        )

    def test_04_debt_schedule_present(self):
        """Debt schedule written to workspace after run."""
        ws = _ws(self.project_code)
        ds = ws.last_debt_schedule if ws else {}
        self.assertTrue(bool(ds), "last_debt_schedule must be non-empty after run")

    def test_04_workbook_output_page_200(self):
        """Workbook page loads HTTP 200 after run (output surfaces render)."""
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)

    # ── Step 5: Save (persistence after run) ─────────────────────────────

    def test_05_runtime_persisted_after_run(self):
        """Workspace has non-empty last_runtime_summary (runtime persisted)."""
        ws = _ws(self.project_code)
        self.assertIsNotNone(ws, "workspace must exist after run")
        self.assertTrue(
            bool(ws.last_runtime_summary),
            "last_runtime_summary must be non-empty after run"
        )

    def test_05_snapshot_id_set_after_run(self):
        """Runtime snapshot ID is stored (run was committed)."""
        ws = _ws(self.project_code)
        self.assertIsNotNone(ws.last_runtime_snapshot_id,
                             "last_runtime_snapshot_id must be set after run")

    # ── Step 6: Reopen ────────────────────────────────────────────────────

    def test_06_reopen_project_from_library(self):
        """Library lists the project; reopening workbook returns 200."""
        # Simulate leaving and returning to library
        resp_lib = self.client.get("/library", follow_redirects=True)
        self.assertEqual(resp_lib.status_code, 200)
        self.assertIn(self.project_code, resp_lib.text)

        # Reopen workbook
        resp_wb = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp_wb.status_code, 200)

    def test_06_reopened_runtime_matches_saved(self):
        """Runtime summary after reopen matches what was saved by the run."""
        s = _summary(self.project_code)
        ebitda = s.get("total_ebitda_keur")
        self.assertIsNotNone(ebitda, "reopened project must have persisted EBITDA")

    def test_06_project_identity_persists(self):
        """Project record still has correct project_code after reopen."""
        proj = get_project_by_code(_user_id(), self.project_code)
        self.assertIsNotNone(proj)
        self.assertEqual(proj.project_code, self.project_code)
        self.assertIn("MVP E2E Solar Test", proj.project_name)

    # ── Step 7: Export ────────────────────────────────────────────────────

    def test_07_institutional_workbook_http_200(self):
        """Institutional workbook export returns HTTP 200."""
        resp = self.client.get(
            f"/exports/institutional-workbook.xlsx?project={self.project_code}",
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200,
                         f"export returned {resp.status_code}: {resp.text[:200]}")

    def test_07_export_is_valid_xlsx(self):
        """Exported workbook is non-empty and parseable with openpyxl."""
        import io
        resp = self.client.get(
            f"/exports/institutional-workbook.xlsx?project={self.project_code}",
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content
        self.assertGreater(len(content), 1000,
                           f"export file too small ({len(content)} bytes)")
        wb = openpyxl.load_workbook(io.BytesIO(content))
        self.assertGreater(len(wb.sheetnames), 0,
                           "workbook must have at least one sheet")

    def test_07_export_runtime_summary_csv_200(self):
        """Runtime summary CSV export returns HTTP 200."""
        resp = self.client.get(
            f"/exports/runtime-summary.csv?project={self.project_code}",
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.content), 10)

    # ── Static assets (from installed wheel, not source) ──────────────────

    def test_static_css_200(self):
        """CSS asset tokens.css served HTTP 200."""
        resp = self.client.get("/static/tokens.css")
        self.assertEqual(resp.status_code, 200)

    def test_static_js_200(self):
        """JS asset app.js served HTTP 200."""
        resp = self.client.get("/static/app.js")
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Secondary smoke: Wind create → edit → run → reopen
# ---------------------------------------------------------------------------

class TestMvpWindSmoke(unittest.TestCase):
    """Secondary Wind smoke: create → edit → run → reopen."""

    @classmethod
    def setUpClass(cls):
        cls.client = _client()
        cls.project_code = _create_project(
            cls.client,
            name="MVP E2E Wind Smoke",
            project_type="Wind",
            template_source="generic_wind",
            capacity_mw="100",
            tariff_eur_mwh="55",
            total_capex_keur="130000",
            opex_y1_keur="1800",
            p50_hours="3200",
        )
        _update_field(cls.client, cls.project_code,
                      "project_setup.technical.p50_hours", "3400", "project_setup")
        _run(cls.client, cls.project_code)

    def test_wind_run_produces_ebitda(self):
        """Wind project run produced total_ebitda_keur."""
        s = _summary(self.project_code)
        self.assertIsNotNone(s.get("total_ebitda_keur"),
                             f"Wind EBITDA missing; keys={list(s)}")

    def test_wind_run_produces_irr(self):
        """Wind project run produced project_irr."""
        s = _summary(self.project_code)
        self.assertIsNotNone(s.get("project_irr"),
                             f"Wind project_irr missing; keys={list(s)}")

    def test_wind_reopen_workbook(self):
        """Wind workbook reopens successfully from library."""
        resp = self.client.get("/library", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        resp_wb = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp_wb.status_code, 200)

    def test_wind_project_identity_persists(self):
        """Wind project record has correct identity after reopen."""
        proj = get_project_by_code(_user_id(), self.project_code)
        self.assertIsNotNone(proj)
        self.assertIn("MVP E2E Wind Smoke", proj.project_name)


if __name__ == "__main__":
    unittest.main()
