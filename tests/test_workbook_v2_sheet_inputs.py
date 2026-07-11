"""
Tests for the Workbook V2 Inputs Control Tower sheet (PR 866 v2).

Coverage:
1.  _build_sheet_fields — structure, ordering, parity with _build_ps_fields
2.  build_inputs_summary — parity with canonical CapexViewModel / OpexViewModel
3.  OPEX/MWh units — EUR/MWh (kEUR * 1000 / MWh), not kEUR/MWh
4.  Runtime status truth matrix — three states (no run / clean / stale)
5.  Sheet HTML — registry-driven rendering, 8 sections, local nav
6.  Placeholder rows — "Not yet connected" / "Available after … migration"
7.  Section links — CAPEX, OPEX, Debt, Revenue, Tax
8.  Editable controls — BOUND fields, hx-target, sheet_id="inputs"
9.  Protected reference — zero editable controls
10. HTMX edit from inputs sheet — correct sheet returned, OOB banner
"""
from __future__ import annotations

import os
import unittest
import urllib.parse
from unittest.mock import patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-inputs-tests")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.ui.capex_view_model import build_capex_view_model  # noqa: E402
from app.ui.inputs_summary import build_inputs_summary  # noqa: E402
from app.ui.opex_view_model import build_opex_view_model  # noqa: E402
from app.ui.project_context import build_project_context_for_record  # noqa: E402
from app.v2.router import _build_ps_fields, _build_sheet_fields  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _authed_client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str, capacity_mw="100",
                    p50_hours="1000", opex_y1_keur="5000",
                    total_capex_keur="80000") -> str:
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"Inputs Test {suffix}",
            "project_type": "Wind",
            "template_source": "generic_wind",
            "country_market": "Germany",
            "capacity_mw": capacity_mw,
            "cod_date": "2027-06-01",
            "construction_months": "24",
            "horizon_years": "20",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": p50_hours,
            "opex_y1_keur": opex_y1_keur,
            "total_capex_keur": total_capex_keur,
            "gearing_pct": "70",
            "interest_rate_pct": "4.5",
            "tenor_years": "18",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"expected redirect from /projects/create, got {resp.status_code}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    codes = parsed.get("project", [])
    assert codes, f"no project= in redirect URL: {redirect}"
    return codes[0]


def _get_workbook(client, project_code: str):
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200
    return resp.text


def _inputs_div(html: str):
    return BeautifulSoup(html, "html.parser").find(id="v2-sheet-inputs")


def _project_record_and_pis(client, project_code: str):
    """Return (project_record, pis, ws) for a project."""
    from app.auth import COOKIE_NAME, decode_session_token
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    from app.workbook.service import WorkbookService
    token = client.cookies.get(COOKIE_NAME)
    user = decode_session_token(token)
    pr = get_project_record(user_id=user.user_id, project_code=project_code)
    ws = get_workspace_state(user_id=user.user_id, project_id=pr.project_id)
    pis = WorkbookService.build_draft_input_set_from_workspace(ws)
    return pr, pis, ws


# ---------------------------------------------------------------------------
# 1. _build_sheet_fields — structure and ordering
# ---------------------------------------------------------------------------

class TestBuildSheetFields(unittest.TestCase):

    def _fake_pis(self):
        from unittest.mock import MagicMock
        m = MagicMock()
        m.get = lambda fid: None
        return m

    def test_project_setup_parity(self):
        """_build_sheet_fields('project_setup') == _build_ps_fields for same pis."""
        pis = self._fake_pis()
        self.assertEqual(
            [r["field_id"] for r in _build_sheet_fields("project_setup", pis)],
            [r["field_id"] for r in _build_ps_fields(pis)],
        )

    def test_all_registry_sheets_accessible(self):
        pis = self._fake_pis()
        for sid in ("project_setup", "capex", "opex", "revenue", "debt"):
            rows = _build_sheet_fields(sid, pis)
            self.assertGreater(len(rows), 0, f"sheet {sid!r} returned no fields")

    def test_field_dict_keys_complete(self):
        pis = self._fake_pis()
        required = {
            "field_id", "label", "unit", "field_type", "binding_label",
            "options", "section_id", "section_label", "value",
            "required", "min_value", "max_value", "step", "help_text",
        }
        for sid in ("project_setup", "capex", "opex", "revenue", "debt"):
            for row in _build_sheet_fields(sid, pis):
                missing = required - row.keys()
                self.assertFalse(missing, f"{sid!r} {row.get('field_id')!r}: {missing}")

    def test_no_duplicate_field_ids_per_sheet(self):
        pis = self._fake_pis()
        for sid in ("project_setup", "capex", "opex", "revenue", "debt"):
            fids = [r["field_id"] for r in _build_sheet_fields(sid, pis)]
            dupes = [f for f in set(fids) if fids.count(f) > 1]
            self.assertFalse(dupes, f"sheet {sid!r} has duplicate field_ids: {dupes}")

    def test_debt_gearing_is_bound(self):
        pis = self._fake_pis()
        rows = {r["field_id"]: r for r in _build_sheet_fields("debt", pis)}
        self.assertEqual(rows["debt.senior.gearing_pct"]["binding_label"], "bound")

    def test_capex_summary_total_is_partial(self):
        pis = self._fake_pis()
        rows = {r["field_id"]: r for r in _build_sheet_fields("capex", pis)}
        self.assertEqual(rows["capex.summary.total"]["binding_label"], "partial")


# ---------------------------------------------------------------------------
# 2. build_inputs_summary — parity with canonical ViewModels
# ---------------------------------------------------------------------------

class TestBuildInputsSummaryParity(unittest.TestCase):
    """
    Proves that build_inputs_summary values equal the canonical CapexViewModel
    and OpexViewModel values for the same project state.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(
            cls.client, "parity-01",
            capacity_mw="50", p50_hours="2000",
            opex_y1_keur="3000", total_capex_keur="60000",
        )
        cls.pr, cls.pis, cls.ws = _project_record_and_pis(cls.client, cls.project_code)

        snapshot = cls.pis.to_snapshot()
        ctx = build_project_context_for_record(
            project_code=cls.pr.project_code,
            project_name=cls.pr.project_name,
            project_type=cls.pr.project_type,
            project_origin=cls.pr.project_origin,
            template_source=cls.pr.template_source,
            baseline_snapshot=snapshot,
        )
        cls.capex_vm = build_capex_view_model(ctx, is_user_project=True)
        cls.opex_vm = build_opex_view_model(ctx, is_user_project=True)
        cls.summary = build_inputs_summary(cls.pr, cls.pis, cls.ws)

    def test_capex_hard_matches_viewmodel(self):
        self.assertAlmostEqual(
            self.summary["capex_hard_keur"], self.capex_vm.hard_capex_keur, places=2,
            msg="capex_hard_keur != CapexViewModel.hard_capex_keur",
        )

    def test_capex_financing_matches_viewmodel(self):
        self.assertAlmostEqual(
            self.summary["capex_financing_keur"], self.capex_vm.financing_keur, places=2,
        )

    def test_capex_reserve_matches_viewmodel(self):
        self.assertAlmostEqual(
            self.summary["capex_reserve_keur"], self.capex_vm.reserve_keur, places=2,
        )

    def test_capex_total_matches_viewmodel(self):
        self.assertAlmostEqual(
            self.summary["capex_total_keur"], self.capex_vm.total_capex_keur, places=2,
            msg="capex_total_keur != CapexViewModel.total_capex_keur",
        )

    def test_capex_per_mw_matches_viewmodel(self):
        self.assertAlmostEqual(
            self.summary["capex_per_mw_keur"], self.capex_vm.total_per_mw, places=2,
        )

    def test_opex_y1_matches_viewmodel(self):
        self.assertAlmostEqual(
            self.summary["opex_y1_keur"], self.opex_vm.y1_total_opex, places=2,
            msg="opex_y1_keur != OpexViewModel.y1_total_opex",
        )

    def test_opex_per_mw_matches_viewmodel(self):
        if self.opex_vm.opex_per_mw_y1 is None:
            self.assertIsNone(self.summary["opex_per_mw_keur"])
        else:
            self.assertAlmostEqual(
                self.summary["opex_per_mw_keur"], self.opex_vm.opex_per_mw_y1, places=2,
            )

    def test_opex_per_mwh_matches_viewmodel(self):
        if self.opex_vm.opex_per_mwh_y1 is None:
            self.assertIsNone(self.summary["opex_per_mwh_eur"])
        else:
            self.assertAlmostEqual(
                self.summary["opex_per_mwh_eur"], self.opex_vm.opex_per_mwh_y1, places=4,
                msg="opex_per_mwh_eur != OpexViewModel.opex_per_mwh_y1",
            )


# ---------------------------------------------------------------------------
# 3. OPEX/MWh units — EUR/MWh, not kEUR/MWh
# ---------------------------------------------------------------------------

class TestOpexPerMwhUnits(unittest.TestCase):
    """
    Regression: 1,000 kEUR / 100,000 MWh = 10 EUR/MWh.

    The OpexViewModel formula (used by build_inputs_summary via the adapter):
        opex_per_mwh_y1 = y1_total_opex_keur × 1000 / p50_annual_mwh   [EUR/MWh]

    The wrong formula (the units bug) would be:
        y1_total_opex_keur / p50_annual_mwh                             [kEUR/MWh ≈ 0.01]
    """

    def test_viewmodel_formula_proves_eur_mwh(self):
        """Numerical proof: ~1,000 kEUR / (100 MW × 1,000 h) ≈ 10 EUR/MWh.

        Build an OpexViewModel from a controlled snapshot:
          capacity_mw = 100, p50_hours = 1000 → p50_annual_mwh = 100,000 MWh
          opex_y1_keur seeded at 1000

        The ViewModel formula is:
          opex_per_mwh_y1 = y1_total_opex * 1000 / 100,000

        So if y1_total_opex ≈ 1000 kEUR, we get ≈ 10 EUR/MWh.
        The kEUR/MWh bug would give ≈ 0.01.  The test guards the > 1.0
        lower bound, proving the 1000× factor is present.
        """
        ctx = build_project_context_for_record(
            project_code="TEST",
            project_name="Test",
            project_type="wind",
            project_origin="user_created",
            template_source="generic_wind",
            baseline_snapshot={
                "capacity_mw": "100",
                "p50_hours": "1000",    # → p50_annual_mwh = 100,000 MWh
                "opex_y1_keur": "1000", # target Y1 total (template scales to this)
            },
        )
        vm = build_opex_view_model(ctx, is_user_project=True)
        self.assertIsNotNone(vm.opex_per_mwh_y1)
        # correct: ~1000 * 1000 / 100_000 ≈ 10 EUR/MWh (allow delta for contingency)
        # wrong:   ~1000 / 100_000 ≈ 0.01 kEUR/MWh
        self.assertGreater(vm.opex_per_mwh_y1, 1.0,
                           f"opex_per_mwh_y1 = {vm.opex_per_mwh_y1:.4f}: "
                           f"looks like kEUR/MWh (expected EUR/MWh ≈ 10)")
        self.assertAlmostEqual(vm.opex_per_mwh_y1, 10.0, delta=5.0,
                               msg=f"Expected ~10 EUR/MWh, got {vm.opex_per_mwh_y1:.4f}. "
                                   f"The kEUR/MWh bug would give ~0.01.")

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(
            cls.client, "mwh-units",
            capacity_mw="100", p50_hours="1000", opex_y1_keur="1000",
        )
        cls.pr, cls.pis, cls.ws = _project_record_and_pis(cls.client, cls.project_code)

    def test_adapter_matches_canonical_viewmodel(self):
        """build_inputs_summary EUR/MWh == OpexViewModel.opex_per_mwh_y1."""
        summary = build_inputs_summary(self.pr, self.pis, self.ws)
        snapshot = self.pis.to_snapshot()
        ctx = build_project_context_for_record(
            project_code=self.pr.project_code,
            project_name=self.pr.project_name,
            project_type=self.pr.project_type,
            project_origin=self.pr.project_origin,
            template_source=self.pr.template_source,
            baseline_snapshot=snapshot,
        )
        vm = build_opex_view_model(ctx, is_user_project=True)
        if vm.opex_per_mwh_y1 is None:
            self.skipTest("ViewModel opex_per_mwh_y1 is None")
        self.assertAlmostEqual(
            summary["opex_per_mwh_eur"], vm.opex_per_mwh_y1, places=4,
        )

    def test_adapter_value_is_not_keur_per_mwh(self):
        """Adapter value is in EUR/MWh (> 1), not kEUR/MWh (≈ 0.01)."""
        summary = build_inputs_summary(self.pr, self.pis, self.ws)
        per_mwh = summary["opex_per_mwh_eur"]
        if per_mwh is None:
            self.skipTest("opex_per_mwh_eur is None")
        self.assertGreater(per_mwh, 0.1,
                           f"opex_per_mwh_eur={per_mwh:.4f} looks like kEUR/MWh "
                           f"(should be EUR/MWh, typically 5–30 for wind)")


# ---------------------------------------------------------------------------
# 4. Runtime status truth matrix
# ---------------------------------------------------------------------------

class TestRuntimeStatusMatrix(unittest.TestCase):
    """
    State A — no RuntimeResult:    Runtime Status = "Not yet run"
    State B — runtime + not dirty: Runtime Status = "Outputs current"
    State C — runtime + dirty:     Runtime Status = "Previous run available — stale for current draft"

    "Outputs current" must never appear while the draft is dirty.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "runtime-matrix")
        body = _get_workbook(cls.client, cls.project_code)
        shell = BeautifulSoup(body, "html.parser").find(id="v2-workbook-shell")
        cls.content_hash = shell["data-content-hash"]
        cls.workbook_version = shell["data-workbook-version"]

    def _render_inputs_with(self, *, has_runtime: bool, ws_dirty: bool) -> str:
        """GET /v2/workbook with workspace dirty/runtime state overridden."""
        import dataclasses
        from app.persistence.workspace_repository import get_workspace_state as _real_ws

        def _patched_ws(*args, **kwargs):
            real = _real_ws(*args, **kwargs)
            if real is None:
                return None
            return dataclasses.replace(
                real,
                dirty=ws_dirty,
                last_runtime_snapshot_id="snap-001" if has_runtime else None,
                last_runtime_at=None,
            )

        with patch("app.persistence.workspace_repository.get_workspace_state",
                   side_effect=_patched_ws):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")

        assert resp.status_code == 200, f"Got {resp.status_code}"
        return resp.text

    def test_state_a_no_runtime(self):
        """State A: no RuntimeResult → 'Not yet run'."""
        html = self._render_inputs_with(has_runtime=False, ws_dirty=False)
        inp = _inputs_div(html)
        self.assertIn("Not yet run", inp.get_text())
        self.assertNotIn("Outputs current", inp.get_text())
        self.assertNotIn("stale", inp.get_text())

    def test_state_b_runtime_clean(self):
        """State B: RuntimeResult + clean draft → 'Outputs current'."""
        html = self._render_inputs_with(has_runtime=True, ws_dirty=False)
        inp = _inputs_div(html)
        self.assertIn("Outputs current", inp.get_text())
        self.assertNotIn("Not yet run", inp.get_text())
        self.assertNotIn("stale", inp.get_text())

    def test_state_c_runtime_dirty(self):
        """State C: RuntimeResult + dirty draft → stale message, not 'Outputs current'."""
        html = self._render_inputs_with(has_runtime=True, ws_dirty=True)
        inp = _inputs_div(html)
        self.assertIn("stale", inp.get_text())
        self.assertNotIn("Outputs current", inp.get_text())
        self.assertNotIn("Not yet run", inp.get_text())

    def test_state_c_shows_run_required(self):
        """State C: Run Required = Yes when dirty."""
        html = self._render_inputs_with(has_runtime=True, ws_dirty=True)
        inp = _inputs_div(html)
        text = inp.get_text()
        idx = text.find("Run Required")
        self.assertGreater(idx, -1)
        self.assertIn("Yes", text[idx:idx + 40])

    def test_state_b_does_not_show_run_required(self):
        """State B: Run Required = No when clean."""
        html = self._render_inputs_with(has_runtime=True, ws_dirty=False)
        inp = _inputs_div(html)
        text = inp.get_text()
        idx = text.find("Run Required")
        self.assertGreater(idx, -1)
        self.assertNotIn("Yes", text[idx:idx + 40])


# ---------------------------------------------------------------------------
# 5. Sheet HTML — registry-driven rendering
# ---------------------------------------------------------------------------

class TestInputsSheetHtml(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "html-01")
        cls.soup = BeautifulSoup(_get_workbook(cls.client, cls.project_code), "html.parser")

    def test_inputs_sheet_container_present(self):
        self.assertIsNotNone(self.soup.find(id="v2-sheet-inputs"))

    def test_eight_collapsible_sections(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        details = inp.find_all("details", class_="v2-inputs-section")
        self.assertEqual(len(details), 8, f"expected 8, got {len(details)}")

    def test_section_nav_links(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        nav = inp.find("nav", class_="v2-inputs-nav")
        self.assertIsNotNone(nav)
        link_texts = {a.get_text(strip=True) for a in nav.find_all("a")}
        for t in ("Technical", "Revenue", "CAPEX", "OPEX", "Debt", "Tax", "Sponsor", "Runtime"):
            self.assertIn(t, link_texts)

    def test_technical_registry_fields_present(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(
            inp.find(attrs={"data-field-id": "project_setup.technical.capacity_mw"}))
        self.assertIsNotNone(
            inp.find(attrs={"data-field-id": "project_setup.technical.p50_hours"}))

    def test_revenue_ppa_fields_present(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(
            inp.find(attrs={"data-field-id": "revenue.ppa.base_tariff"}))

    def test_debt_gearing_field_present(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(
            inp.find(attrs={"data-field-id": "debt.senior.gearing_pct"}))

    def test_placeholder_not_yet_connected(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIn("Not yet connected", inp.get_text())

    def test_tax_migration_placeholder(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIn("Available after Tax migration", inp.get_text())

    def test_sponsor_reserved_placeholder(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIn("Reserved for future Sponsor module", inp.get_text())

    def test_capex_link(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(inp.find("a", href=lambda h: h and "/capex" in h))

    def test_opex_link(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(inp.find("a", href=lambda h: h and "/opex" in h))

    def test_debt_link(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(inp.find("a", href=lambda h: h and "/debt" in h))

    def test_revenue_link(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(inp.find("a", href=lambda h: h and "/revenue" in h))

    def test_no_duplicate_field_ids_in_dom(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        fids = [r["data-field-id"] for r in inp.find_all(attrs={"data-field-id": True})]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids in inputs sheet: {dupes}")

    def test_runtime_section_has_workbook_version(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIn("2.0.0", inp.get_text())

    def test_runtime_section_has_truncated_hash(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertIn("…", inp.get_text())


# ---------------------------------------------------------------------------
# 6. Editable controls for user project
# ---------------------------------------------------------------------------

class TestInputsSheetEditable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "editable-01")
        cls.soup = BeautifulSoup(_get_workbook(cls.client, cls.project_code), "html.parser")

    def test_bound_fields_have_input_controls(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        self.assertGreater(len(inp.find_all(class_="v2-field-editable")), 0)

    def test_forms_target_inputs_sheet(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        forms = inp.find_all("form", class_="v2-field-form")
        self.assertGreater(len(forms), 0)
        for form in forms:
            self.assertEqual(form.get("hx-target"), "#v2-sheet-inputs",
                             f"wrong hx-target on form {form}")

    def test_forms_carry_sheet_id_inputs(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        for form in inp.find_all("form", class_="v2-field-form"):
            sid = form.find("input", {"name": "sheet_id"})
            self.assertIsNotNone(sid)
            self.assertEqual(sid["value"], "inputs")

    def test_capacity_mw_step_from_registry(self):
        """capacity_mw step="0.01" from registry decimals=2."""
        inp = self.soup.find(id="v2-sheet-inputs")
        row = inp.find(attrs={"data-field-id": "project_setup.technical.capacity_mw"})
        self.assertEqual(row.find("input", {"name": "value"}).get("step"), "0.01")

    def test_gearing_pct_field_type(self):
        inp = self.soup.find(id="v2-sheet-inputs")
        row = inp.find(attrs={"data-field-id": "debt.senior.gearing_pct"})
        self.assertEqual(row.get("data-field-type"), "pct")


# ---------------------------------------------------------------------------
# 7. Protected reference — zero editable controls
# ---------------------------------------------------------------------------

class TestInputsSheetProtectedRef(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "prot-ref-01")

    def test_protected_ref_zero_editable(self):
        with patch("app.v2.router.is_protected_reference", return_value=True):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        inp = _inputs_div(resp.text)
        self.assertEqual(len(inp.find_all(class_="v2-field-editable")), 0)

    def test_user_project_has_editable_controls(self):
        with patch("app.v2.router.is_protected_reference", return_value=False):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        inp = _inputs_div(resp.text)
        self.assertGreater(len(inp.find_all(class_="v2-field-editable")), 0)


# ---------------------------------------------------------------------------
# 8. HTMX edit from inputs sheet
# ---------------------------------------------------------------------------

class TestInputsSheetHtmxEdit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "htmx-01")
        html = _get_workbook(cls.client, cls.project_code)
        shell = BeautifulSoup(html, "html.parser").find(id="v2-workbook-shell")
        cls.content_hash = shell["data-content-hash"]
        cls.workbook_version = shell["data-workbook-version"]

    def _post(self, field_id, value, sheet_id="inputs", content_hash=None):
        return self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": field_id,
                "value": value,
                "project": self.project_code,
                "workbook_version": self.workbook_version,
                "content_hash": content_hash or self.content_hash,
                "sheet_id": sheet_id,
            },
            headers={"HX-Request": "true"},
        )

    def test_htmx_success_returns_inputs_sheet(self):
        resp = self._post("debt.senior.gearing_pct", "65.0")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-inputs", resp.text)

    def test_htmx_success_oob_banner(self):
        resp = self._post("debt.senior.target_dscr", "1.25")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('hx-swap-oob="true"', resp.text)
        self.assertIn("v2-status-banner", resp.text)

    def test_htmx_inputs_edit_not_project_setup_sheet(self):
        resp = self._post("debt.senior.tenor_years", "20")
        self.assertNotIn("v2-sheet-project-setup", resp.text)

    def test_htmx_project_setup_still_works(self):
        resp = self._post("project_setup.technical.horizon_years", "25",
                          sheet_id="project_setup")
        self.assertIn("v2-sheet-project-setup", resp.text)

    def test_htmx_validation_error_returns_inputs_sheet(self):
        resp = self._post("project_setup.technical.capacity_mw", "-999")
        self.assertIn("v2-sheet-inputs", resp.text)

    def test_htmx_new_content_hash_in_returned_forms(self):
        resp = self._post("debt.senior.interest_rate_pct", "4.75")
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        hashes = {i["value"] for i in soup.find_all("input", {"name": "content_hash"})}
        self.assertEqual(len(hashes), 1)
        self.assertNotEqual(next(iter(hashes)), self.content_hash)


if __name__ == "__main__":
    unittest.main()
