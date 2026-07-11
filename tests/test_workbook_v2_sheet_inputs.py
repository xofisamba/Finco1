"""
Tests for the Workbook V2 Inputs Control Tower sheet (PR 866).

Coverage:
1. Registry-driven rendering — fields from all 5 registry sheets appear
2. No duplicated field_ids — each field_id appears at most once per sheet
3. Placeholder rows — "Not yet connected" / "Available after … migration"
4. Section links — CAPEX, OPEX, Debt, Revenue, Tax links present
5. Editable controls — BOUND fields render <input>/<select> for user projects
6. Protected reference — zero editable controls for TUHO/Oborovo originals
7. HTMX edit from inputs sheet — sheet_id="inputs", hx-target="#v2-sheet-inputs"
8. HTMX success response — returns #v2-sheet-inputs + OOB banner
9. _build_sheet_fields — structure, ordering, parity with _build_ps_fields for project_setup
10. _build_inputs_context — CAPEX/OPEX summaries derived without engine calls
11. Runtime section — workbook_version, content_hash, draft/runtime status
"""
from __future__ import annotations

import os
import sys
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-inputs-tests")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.workbook.registry import WORKBOOK  # noqa: E402
from app.workbook.specs import BindingStatus  # noqa: E402
from app.v2.router import (  # noqa: E402
    _build_inputs_context,
    _build_ps_fields,
    _build_sheet_fields,
)


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
            "project_name": f"Inputs Test {suffix}",
            "project_type": "Wind",
            "template_source": "generic_wind",
            "country_market": "Germany",
            "capacity_mw": "100",
            "cod_date": "2027-06-01",
            "construction_months": "24",
            "horizon_years": "20",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "2500",
            "opex_y1_keur": "1200",
            "total_capex_keur": "80000",
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


def _get_workbook_body(client, project_code: str) -> str:
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}"
    return resp.text


def _fake_pis(values: dict | None = None):
    """Minimal ProjectInputSet-like mock for unit tests."""
    m = MagicMock()
    m.workbook_version = "2.0.0"
    m.content_hash = "abc123deadbeef"
    m.template_source = "generic_wind"
    m.get = lambda fid: (values or {}).get(fid)
    return m


def _fake_ws(dirty: bool = False, has_runtime: bool = False):
    m = MagicMock()
    m.dirty = dirty
    m.last_runtime_snapshot_id = "snap-001" if has_runtime else None
    m.last_runtime_at = None
    return m


# ---------------------------------------------------------------------------
# 1. _build_sheet_fields — structure and ordering
# ---------------------------------------------------------------------------

class TestBuildSheetFields(unittest.TestCase):

    def test_project_setup_parity(self):
        """_build_sheet_fields('project_setup', pis) == _build_ps_fields(pis)."""
        pis = _fake_pis()
        result_generic = _build_sheet_fields("project_setup", pis)
        result_ps = _build_ps_fields(pis)
        self.assertEqual(
            [r["field_id"] for r in result_generic],
            [r["field_id"] for r in result_ps],
        )

    def test_all_registry_sheets_accessible(self):
        """_build_sheet_fields works for every declared registry sheet."""
        pis = _fake_pis()
        for sheet_id in ("project_setup", "capex", "opex", "revenue", "debt"):
            rows = _build_sheet_fields(sheet_id, pis)
            self.assertIsInstance(rows, list)
            self.assertGreater(len(rows), 0, f"sheet {sheet_id!r} returned no fields")

    def test_field_dict_keys_complete(self):
        """Every field dict carries all required keys."""
        pis = _fake_pis()
        required_keys = {
            "field_id", "label", "unit", "field_type", "binding_label",
            "options", "section_id", "section_label", "value",
            "required", "min_value", "max_value", "step", "help_text",
        }
        for sheet_id in ("project_setup", "capex", "opex", "revenue", "debt"):
            for row in _build_sheet_fields(sheet_id, pis):
                missing = required_keys - row.keys()
                self.assertFalse(
                    missing,
                    f"sheet {sheet_id!r} field {row.get('field_id')!r} missing keys: {missing}",
                )

    def test_no_duplicate_field_ids_per_sheet(self):
        """No field_id appears twice within a single registry sheet."""
        pis = _fake_pis()
        for sheet_id in ("project_setup", "capex", "opex", "revenue", "debt"):
            fids = [r["field_id"] for r in _build_sheet_fields(sheet_id, pis)]
            self.assertEqual(
                len(fids), len(set(fids)),
                f"sheet {sheet_id!r} has duplicate field_ids: "
                + str([f for f in fids if fids.count(f) > 1]),
            )

    def test_value_comes_from_pis(self):
        """Values are taken from pis.get(field_id), not hardcoded."""
        pis = _fake_pis({"project_setup.technical.capacity_mw": 123.45})
        rows = _build_sheet_fields("project_setup", pis)
        cap = next(r for r in rows if r["field_id"] == "project_setup.technical.capacity_mw")
        self.assertEqual(cap["value"], 123.45)

    def test_debt_senior_gearing_binding(self):
        """debt.senior.gearing_pct is BOUND (editable)."""
        pis = _fake_pis()
        rows = _build_sheet_fields("debt", pis)
        gearing = next(r for r in rows if r["field_id"] == "debt.senior.gearing_pct")
        self.assertEqual(gearing["binding_label"], "bound")

    def test_capex_summary_total_is_partial(self):
        """capex.summary.total is PARTIAL (engine-derived, not user-editable)."""
        pis = _fake_pis()
        rows = _build_sheet_fields("capex", pis)
        total = next(r for r in rows if r["field_id"] == "capex.summary.total")
        self.assertEqual(total["binding_label"], "partial")


# ---------------------------------------------------------------------------
# 2. _build_inputs_context — computed summaries
# ---------------------------------------------------------------------------

class TestBuildInputsContext(unittest.TestCase):

    def _pis_with_capex(self):
        values = {
            "capex.C.epc_contract": 10000,
            "capex.C.grid_connection": 5000,
            "capex.D.audit_legal": 500,
            "capex.F.idc": 2000,
            "capex.R.reserve_accounts": 1000,
            "capex.summary.total": 18500,
            "project_setup.technical.capacity_mw": 100.0,
            "project_setup.technical.p50_hours": 2500.0,
            "opex.summary.total_y1": 1200,
        }
        return _fake_pis(values)

    def test_hard_capex_sum(self):
        ctx = _build_inputs_context(self._pis_with_capex(), _fake_ws())
        # 10000 + 5000 (C) + 500 (D) = 15500
        self.assertEqual(ctx["capex_hard_keur"], 15500.0)

    def test_financing_sum(self):
        ctx = _build_inputs_context(self._pis_with_capex(), _fake_ws())
        self.assertEqual(ctx["capex_financing_keur"], 2000.0)

    def test_reserve_passthrough(self):
        ctx = _build_inputs_context(self._pis_with_capex(), _fake_ws())
        self.assertEqual(ctx["capex_reserve_keur"], 1000.0)

    def test_capex_total_from_summary_field(self):
        ctx = _build_inputs_context(self._pis_with_capex(), _fake_ws())
        self.assertEqual(ctx["capex_total_keur"], 18500.0)

    def test_capex_per_mw(self):
        ctx = _build_inputs_context(self._pis_with_capex(), _fake_ws())
        self.assertAlmostEqual(ctx["capex_per_mw_keur"], 185.0, places=0)

    def test_opex_y1_passthrough(self):
        ctx = _build_inputs_context(self._pis_with_capex(), _fake_ws())
        self.assertEqual(ctx["opex_y1_keur"], 1200.0)

    def test_opex_per_mw(self):
        ctx = _build_inputs_context(self._pis_with_capex(), _fake_ws())
        self.assertAlmostEqual(ctx["opex_per_mw_keur"], 12.0, places=0)

    def test_opex_per_mwh(self):
        ctx = _build_inputs_context(self._pis_with_capex(), _fake_ws())
        # 1200 / (100 * 2500) = 0.0048
        self.assertAlmostEqual(ctx["opex_per_mwh_eur"], 0.0048, places=4)

    def test_none_when_capacity_missing(self):
        pis = _fake_pis({"capex.summary.total": 50000})
        ctx = _build_inputs_context(pis, _fake_ws())
        self.assertIsNone(ctx["capex_per_mw_keur"])

    def test_none_when_no_capex_values(self):
        ctx = _build_inputs_context(_fake_pis(), _fake_ws())
        self.assertIsNone(ctx["capex_hard_keur"])
        self.assertIsNone(ctx["capex_total_keur"])

    def test_runtime_fields_from_ws(self):
        ws = _fake_ws(dirty=True, has_runtime=True)
        ctx = _build_inputs_context(_fake_pis(), ws)
        self.assertEqual(ctx["runtime_snapshot_id"], "snap-001")


# ---------------------------------------------------------------------------
# 3. Sheet HTML — registry-driven rendering
# ---------------------------------------------------------------------------

class TestInputsSheetHtml(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "html-01")
        body = _get_workbook_body(cls.client, cls.project_code)
        cls.soup = BeautifulSoup(body, "html.parser")

    def test_inputs_sheet_container_present(self):
        div = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(div, "#v2-sheet-inputs not found in workbook response")

    def test_eight_collapsible_sections(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        details = inputs_div.find_all("details", class_="v2-inputs-section")
        self.assertEqual(len(details), 8, f"expected 8 sections, got {len(details)}")

    def test_section_nav_present(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        nav = inputs_div.find("nav", class_="v2-inputs-nav")
        self.assertIsNotNone(nav, "section nav not found")
        links = nav.find_all("a")
        link_texts = {a.get_text(strip=True) for a in links}
        for expected in ("Technical", "Revenue", "CAPEX", "OPEX", "Debt", "Tax", "Sponsor", "Runtime"):
            self.assertIn(expected, link_texts, f"nav link '{expected}' missing")

    def test_technical_section_has_registry_fields(self):
        """Technical section renders capacity_mw and p50_hours from registry."""
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(
            inputs_div.find(attrs={"data-field-id": "project_setup.technical.capacity_mw"}),
            "capacity_mw field-row not found in inputs sheet",
        )
        self.assertIsNotNone(
            inputs_div.find(attrs={"data-field-id": "project_setup.technical.p50_hours"}),
        )

    def test_revenue_section_has_ppa_fields(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(
            inputs_div.find(attrs={"data-field-id": "revenue.ppa.base_tariff"}),
            "revenue.ppa.base_tariff not found in inputs sheet",
        )

    def test_debt_section_has_gearing_field(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(
            inputs_div.find(attrs={"data-field-id": "debt.senior.gearing_pct"}),
        )

    def test_placeholder_rows_present(self):
        """'Not yet connected' placeholders appear for missing technical fields."""
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        text = inputs_div.get_text()
        self.assertIn("Not yet connected", text)

    def test_tax_migration_placeholder(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        self.assertIn("Available after Tax migration", inputs_div.get_text())

    def test_sponsor_reserved_placeholder(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        self.assertIn("Reserved for future Sponsor module", inputs_div.get_text())

    def test_capex_sheet_link(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        capex_link = inputs_div.find("a", href=lambda h: h and "/capex" in h)
        self.assertIsNotNone(capex_link, "CAPEX link not found in inputs sheet")

    def test_opex_sheet_link(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        opex_link = inputs_div.find("a", href=lambda h: h and "/opex" in h)
        self.assertIsNotNone(opex_link, "OPEX link not found in inputs sheet")

    def test_debt_sheet_link(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        debt_link = inputs_div.find("a", href=lambda h: h and "/debt" in h)
        self.assertIsNotNone(debt_link, "Debt link not found in inputs sheet")

    def test_revenue_sheet_link(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        rev_link = inputs_div.find("a", href=lambda h: h and "/revenue" in h)
        self.assertIsNotNone(rev_link, "Revenue link not found in inputs sheet")

    def test_no_duplicate_field_ids_in_rendered_html(self):
        """No field_id data-attribute appears twice in the inputs sheet DOM."""
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        rows = inputs_div.find_all(attrs={"data-field-id": True})
        fids = [r["data-field-id"] for r in rows]
        self.assertEqual(
            len(fids), len(set(fids)),
            "Duplicate field_ids in rendered inputs sheet: "
            + str([f for f in fids if fids.count(f) > 1]),
        )

    def test_runtime_section_has_workbook_version(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        text = inputs_div.get_text()
        self.assertIn("2.0.0", text, "workbook_version not found in runtime section")

    def test_runtime_section_has_content_hash(self):
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        text = inputs_div.get_text()
        # Content hash is truncated to 12 chars + ellipsis in the template
        self.assertIn("…", text, "truncated content_hash not found in runtime section")


# ---------------------------------------------------------------------------
# 4. Editable controls for user project
# ---------------------------------------------------------------------------

class TestInputsSheetEditable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "editable-01")
        body = _get_workbook_body(cls.client, cls.project_code)
        cls.soup = BeautifulSoup(body, "html.parser")

    def test_bound_fields_have_input_controls(self):
        """BOUND fields in the inputs sheet render <input> or <select>."""
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        editable_rows = inputs_div.find_all(class_="v2-field-editable")
        self.assertGreater(len(editable_rows), 0, "no editable rows found in inputs sheet")

    def test_forms_target_inputs_sheet(self):
        """All forms in the inputs sheet target #v2-sheet-inputs."""
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        forms = inputs_div.find_all("form", class_="v2-field-form")
        self.assertGreater(len(forms), 0, "no forms found in inputs sheet")
        for form in forms:
            target = form.get("hx-target")
            self.assertEqual(
                target, "#v2-sheet-inputs",
                f"form for {form.find('input', {'name': 'field_id'}) and form.find('input', {'name': 'field_id'}).get('value')!r} "
                f"has wrong hx-target: {target!r}",
            )

    def test_forms_carry_sheet_id_inputs(self):
        """All forms in the inputs sheet send sheet_id=inputs."""
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        forms = inputs_div.find_all("form", class_="v2-field-form")
        for form in forms:
            sheet_input = form.find("input", {"name": "sheet_id"})
            self.assertIsNotNone(sheet_input, "sheet_id hidden input missing in form")
            self.assertEqual(sheet_input["value"], "inputs")

    def test_capacity_mw_has_step_attr(self):
        """capacity_mw input carries step derived from registry decimals=2."""
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        row = inputs_div.find(attrs={"data-field-id": "project_setup.technical.capacity_mw"})
        inp = row.find("input", {"name": "value"})
        self.assertIsNotNone(inp, "capacity_mw input not found")
        self.assertEqual(inp.get("step"), "0.01")

    def test_gearing_pct_has_pct_field_type(self):
        """gearing_pct field has field_type=pct in the rendered row."""
        inputs_div = self.soup.find(id="v2-sheet-inputs")
        row = inputs_div.find(attrs={"data-field-id": "debt.senior.gearing_pct"})
        self.assertIsNotNone(row)
        self.assertEqual(row.get("data-field-type"), "pct")


# ---------------------------------------------------------------------------
# 5. Protected reference — zero editable controls
# ---------------------------------------------------------------------------

class TestInputsSheetProtectedRef(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "prot-ref-01")

    def test_protected_ref_zero_editable_inputs_controls(self):
        """When project_editable=False, inputs sheet has zero editable rows."""
        with patch("app.v2.router.is_protected_reference", return_value=True):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        inputs_div = soup.find(id="v2-sheet-inputs")
        self.assertIsNotNone(inputs_div)
        editable = inputs_div.find_all(class_="v2-field-editable")
        self.assertEqual(
            len(editable), 0,
            f"expected 0 editable rows for protected ref, got {len(editable)}",
        )

    def test_user_project_has_editable_inputs_controls(self):
        """Normal user project has editable controls in inputs sheet."""
        with patch("app.v2.router.is_protected_reference", return_value=False):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        inputs_div = soup.find(id="v2-sheet-inputs")
        editable = inputs_div.find_all(class_="v2-field-editable")
        self.assertGreater(len(editable), 0)


# ---------------------------------------------------------------------------
# 6. HTMX edit from inputs sheet
# ---------------------------------------------------------------------------

class TestInputsSheetHtmxEdit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "htmx-01")
        # Get initial content_hash
        body = _get_workbook_body(cls.client, cls.project_code)
        soup = BeautifulSoup(body, "html.parser")
        shell = soup.find(id="v2-workbook-shell")
        cls.content_hash = shell["data-content-hash"]
        cls.workbook_version = shell["data-workbook-version"]

    def _post_htmx(self, field_id, value, content_hash=None, sheet_id="inputs"):
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
        """HTMX edit with sheet_id=inputs returns #v2-sheet-inputs."""
        resp = self._post_htmx("debt.senior.gearing_pct", "65.0")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-inputs", resp.text)

    def test_htmx_success_returns_oob_banner(self):
        """HTMX success includes OOB status banner."""
        resp = self._post_htmx("debt.senior.target_dscr", "1.25")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('hx-swap-oob="true"', resp.text)
        self.assertIn("v2-status-banner", resp.text)

    def test_htmx_success_does_not_return_project_setup_sheet(self):
        """HTMX inputs edit does NOT return the project_setup sheet container."""
        resp = self._post_htmx("debt.senior.tenor_years", "20")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("v2-sheet-project-setup", resp.text)

    def test_htmx_project_setup_edit_returns_project_setup_sheet(self):
        """HTMX edit with sheet_id=project_setup still returns project_setup sheet."""
        resp = self._post_htmx(
            "project_setup.technical.horizon_years", "25",
            sheet_id="project_setup",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-project-setup", resp.text)

    def test_htmx_validation_error_returns_inputs_sheet(self):
        """HTMX validation error for inputs-sheet field returns inputs sheet with error."""
        resp = self._post_htmx("project_setup.technical.capacity_mw", "-999")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-inputs", resp.text)

    def test_htmx_new_content_hash_in_forms(self):
        """After a successful inputs-sheet edit, new content_hash appears in returned forms."""
        resp = self._post_htmx("debt.senior.interest_rate_pct", "4.75")
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        hashes = {
            inp["value"]
            for inp in soup.find_all("input", {"name": "content_hash"})
        }
        self.assertEqual(len(hashes), 1, f"inconsistent content_hash values: {hashes}")
        new_hash = next(iter(hashes))
        self.assertNotEqual(
            new_hash, self.content_hash,
            "content_hash did not change after successful edit",
        )


if __name__ == "__main__":
    unittest.main()
