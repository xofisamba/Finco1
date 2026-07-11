"""
Tests for the Workbook V2 CAPEX worksheet (PR 868).

Coverage
--------
1.  Registry coverage — _build_sheet_fields("capex") returns all fields
2.  _build_capex_vm_ctx — CapexViewModel built from canonical path
3.  Sheet structure — capex div present, totals bar, column header, groups
4.  C.01–C.18 group order preserved in DOM
5.  BOUND fields have editable controls via render_field()
6.  ENGINE badge on C.17 / C.18 groups
7.  DERIVED badge on C.13 (Contingencies)
8.  Protected reference — zero editable controls
9.  Totals from CapexViewModel only (no hardcoded formulas in template)
10. HTMX edit roundtrip (POST /v2/workbook/update, sheet_id="capex")
11. OOB status banner present in HTMX response
12. hx-target="#v2-sheet-capex" and sheet_id="capex" on all capex forms
13. No duplicate data-field-id in capex DOM region
14. Sub-line detail rows present when CapexViewModel has lines
15. Grand total row present
"""
from __future__ import annotations

import os
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-capex-tests")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

import main_web
from app.auth import COOKIE_NAME, create_session_token
from app.v2.router import _build_sheet_fields
from app.workbook.registry import WORKBOOK
from app.workbook.specs import BindingStatus


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
            "project_name": f"CAPEX V2 Test {suffix}",
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
    assert resp.status_code == 200
    return resp.text


def _capex_div(html: str):
    return BeautifulSoup(html, "html.parser").find(id="v2-sheet-capex")


def _fake_pis():
    m = MagicMock()
    m.get = lambda fid: None
    return m


# ---------------------------------------------------------------------------
# 1. Registry: _build_sheet_fields("capex") coverage
# ---------------------------------------------------------------------------

class TestCapexBuildSheetFields(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = _build_sheet_fields("capex", _fake_pis())
        cls.sheet = WORKBOOK.sheet("capex")

    def test_returns_all_registry_fields(self):
        expected = sum(len(sec.fields) for sec in self.sheet.sections)
        self.assertEqual(len(self.rows), expected,
                         f"expected {expected} capex fields, got {len(self.rows)}")

    def test_no_duplicate_field_ids(self):
        fids = [r["field_id"] for r in self.rows]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids: {dupes}")

    def test_bound_fields_exist(self):
        bound = [r for r in self.rows if r["binding_label"] == "bound"]
        self.assertGreater(len(bound), 0, "Expected at least one BOUND capex field")

    def test_display_only_fields_exist(self):
        do_fields = [r for r in self.rows if r["binding_label"] == "display-only"]
        self.assertGreater(len(do_fields), 0, "Expected DISPLAY_ONLY capex fields")

    def test_template_locked_fields_exist(self):
        tl = [r for r in self.rows if r["binding_label"] == "template-locked"]
        self.assertGreater(len(tl), 0, "Expected TEMPLATE_LOCKED capex fields (C.17)")

    def test_required_dict_keys_present(self):
        required = {
            "field_id", "label", "unit", "field_type", "binding_label",
            "options", "section_id", "value", "required",
            "min_value", "max_value", "step", "help_text",
        }
        for row in self.rows:
            missing = required - row.keys()
            self.assertFalse(missing, f"Row {row['field_id']} missing keys: {missing}")

    def test_section_C_fields_present(self):
        c_fields = [r for r in self.rows if r["section_id"] == "C"]
        self.assertGreater(len(c_fields), 0, "No section C fields found")

    def test_section_F_fields_present(self):
        f_fields = [r for r in self.rows if r["section_id"] == "F"]
        self.assertGreater(len(f_fields), 0, "No section F (Financing) fields found")

    def test_section_R_fields_present(self):
        r_fields = [r for r in self.rows if r["section_id"] == "R"]
        self.assertGreater(len(r_fields), 0, "No section R (Reserve) fields found")

    def test_summary_section_present(self):
        s_fields = [r for r in self.rows if r["section_id"] == "summary"]
        self.assertGreater(len(s_fields), 0, "No summary section field found")


# ---------------------------------------------------------------------------
# 2. _build_capex_vm_ctx builds CapexViewModel via canonical path
# ---------------------------------------------------------------------------

class TestCapexVmCtxBuilder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app.v2.router import _build_capex_vm_ctx as _b
        cls._build_fn = staticmethod(_b)

    def setUp(self):
        # Patch sub-line loading so MagicMock project_ids don't hit SQLite.
        patcher = patch(
            "app.persistence.capex_sub_lines.get_active_sub_lines_for_project",
            return_value=[],
        )
        self._sub_lines_patcher = patcher
        patcher.start()

    def tearDown(self):
        self._sub_lines_patcher.stop()

    def _make_project_record(self, origin="user", template_source="generic_wind"):
        r = MagicMock()
        r.project_code = "TEST01"
        r.project_name = "Test Project"
        r.project_type = "Wind"
        r.project_origin = origin
        r.template_source = template_source
        return r

    def test_returns_capex_vm(self):
        from app.ui.capex_view_model import CapexViewModel
        pis = _fake_pis()
        pis.to_snapshot = lambda: {}
        project_record = self._make_project_record()
        ctx = self._build_fn(project_record, pis)
        self.assertIn("capex_vm", ctx)
        self.assertIsInstance(ctx["capex_vm"], CapexViewModel)

    def test_returns_capex_group_to_field(self):
        pis = _fake_pis()
        pis.to_snapshot = lambda: {}
        project_record = self._make_project_record()
        ctx = self._build_fn(project_record, pis)
        self.assertIn("capex_group_to_field", ctx)
        self.assertIsInstance(ctx["capex_group_to_field"], dict)

    def test_group_to_field_maps_c01(self):
        pis = _fake_pis()
        pis.to_snapshot = lambda: {}
        project_record = self._make_project_record()
        ctx = self._build_fn(project_record, pis)
        gf = ctx["capex_group_to_field"]
        self.assertIn("C.01", gf, "C.01 must map to a registry field")

    def test_returns_capex_section_fields(self):
        pis = _fake_pis()
        pis.to_snapshot = lambda: {}
        project_record = self._make_project_record()
        ctx = self._build_fn(project_record, pis)
        self.assertIn("capex_section_fields", ctx)
        sf = ctx["capex_section_fields"]
        self.assertIn("F", sf, "Section F (Financing) must be in capex_section_fields")
        self.assertIn("R", sf, "Section R (Reserve) must be in capex_section_fields")

    def test_no_capex_totals_computed_in_ctx(self):
        """The ctx dict must NOT contain direct financial aggregation keys."""
        pis = _fake_pis()
        pis.to_snapshot = lambda: {}
        project_record = self._make_project_record()
        ctx = self._build_fn(project_record, pis)
        forbidden = {"hard_capex_keur", "total_capex_keur", "financing_keur", "reserve_keur"}
        in_ctx = forbidden & ctx.keys()
        self.assertFalse(in_ctx, f"Router context must not contain raw total keys: {in_ctx}")

    def test_capex_alias_groups_in_ctx(self):
        """capex_alias_groups must be present and contain C.11 (shared with C.08)."""
        pis = _fake_pis()
        pis.to_snapshot = lambda: {}
        project_record = self._make_project_record()
        ctx = self._build_fn(project_record, pis)
        self.assertIn("capex_alias_groups", ctx,
                      "capex_alias_groups must be in context")
        alias = ctx["capex_alias_groups"]
        self.assertIsInstance(alias, dict)
        # C.11 shares capex.D.audit_legal with C.08
        self.assertIn("C.11", alias,
                      "C.11 must be in capex_alias_groups (shares audit_legal with C.08)")

    def test_c11_alias_points_to_c08_as_owner(self):
        """C.11 alias must name C.08 as the owning group."""
        pis = _fake_pis()
        pis.to_snapshot = lambda: {}
        project_record = self._make_project_record()
        ctx = self._build_fn(project_record, pis)
        alias = ctx["capex_alias_groups"]
        if "C.11" not in alias:
            self.skipTest("C.11 not in alias groups")
        self.assertEqual(alias["C.11"]["owner"], "C.08",
                         "C.11 alias owner must be C.08")

    def test_c08_is_not_an_alias(self):
        """C.08 must be the owning group (has editable form), not an alias."""
        pis = _fake_pis()
        pis.to_snapshot = lambda: {}
        project_record = self._make_project_record()
        ctx = self._build_fn(project_record, pis)
        alias = ctx["capex_alias_groups"]
        self.assertNotIn("C.08", alias,
                         "C.08 is the owner; it must NOT appear in capex_alias_groups")


# ---------------------------------------------------------------------------
# 3. Sheet structure — DOM presence
# ---------------------------------------------------------------------------

class TestCapexSheetStructure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "structure-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.soup = BeautifulSoup(html, "html.parser")
        cls.capex = cls.soup.find(id="v2-sheet-capex")

    def test_capex_div_present(self):
        self.assertIsNotNone(self.capex, "#v2-sheet-capex not found in workbook HTML")

    def test_data_sheet_attribute(self):
        self.assertEqual(self.capex.get("data-sheet"), "capex")

    def test_totals_bar_present(self):
        bar = self.capex.find(attrs={"data-testid": "capex-totals-bar"})
        self.assertIsNotNone(bar, "Totals bar (data-testid=capex-totals-bar) not found")

    def test_hard_capex_total_present(self):
        el = self.capex.find(attrs={"data-testid": "hard-capex-keur"})
        self.assertIsNotNone(el)

    def test_financing_total_present(self):
        el = self.capex.find(attrs={"data-testid": "financing-keur"})
        self.assertIsNotNone(el)

    def test_total_capex_present(self):
        el = self.capex.find(attrs={"data-testid": "total-capex-keur"})
        self.assertIsNotNone(el)

    def test_total_permw_present(self):
        el = self.capex.find(attrs={"data-testid": "total-capex-permw"})
        self.assertIsNotNone(el)

    def test_column_header_present(self):
        header = self.capex.find(class_="v2-capex-col-header")
        self.assertIsNotNone(header, ".v2-capex-col-header not found")

    def test_grand_total_row_present(self):
        row = self.capex.find(attrs={"data-testid": "grand-total-row"})
        self.assertIsNotNone(row, "Grand total row not found")

    def test_grand_total_keur_present(self):
        el = self.capex.find(attrs={"data-testid": "grand-total-keur"})
        self.assertIsNotNone(el)

    def test_at_least_one_group_present(self):
        groups = self.capex.find_all(attrs={"data-group-code": True})
        self.assertGreater(len(groups), 0, "No CAPEX group rows found")


# ---------------------------------------------------------------------------
# 4. C.01–C.18 group order preserved
# ---------------------------------------------------------------------------

class TestCapexGroupOrder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "groups-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.capex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-capex")

    def _group_codes(self):
        return [el["data-group-code"]
                for el in self.capex.find_all(attrs={"data-group-code": True})]

    def test_group_codes_start_with_c01(self):
        codes = self._group_codes()
        self.assertTrue(any(c.startswith("C.") for c in codes),
                        f"No C.NN groups found: {codes}")

    def test_c01_before_c02(self):
        codes = self._group_codes()
        if "C.01" in codes and "C.02" in codes:
            self.assertLess(codes.index("C.01"), codes.index("C.02"),
                            "C.01 must appear before C.02")

    def test_c16_before_c17(self):
        codes = self._group_codes()
        if "C.16" in codes and "C.17" in codes:
            self.assertLess(codes.index("C.16"), codes.index("C.17"),
                            "C.16 must appear before C.17 (hard capex before financing)")

    def test_c17_before_c18(self):
        codes = self._group_codes()
        if "C.17" in codes and "C.18" in codes:
            self.assertLess(codes.index("C.17"), codes.index("C.18"),
                            "C.17 (financing) must appear before C.18 (reserve)")


# ---------------------------------------------------------------------------
# 5. BOUND fields have editable controls (render_field)
# ---------------------------------------------------------------------------

class TestCapexEditable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "editable-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.capex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-capex")

    def test_at_least_one_editable_input_in_capex(self):
        inputs = self.capex.find_all("input", class_="v2-field-input")
        self.assertGreater(len(inputs), 0, "Expected editable inputs in CAPEX sheet")

    def test_capex_forms_target_capex_div(self):
        forms = self.capex.find_all("form")
        for form in forms:
            target = form.get("hx-target") or form.get("data-hx-target", "")
            self.assertIn("#v2-sheet-capex", target,
                          f"Form hx-target should be #v2-sheet-capex, got: {target!r}")

    def test_capex_forms_have_sheet_id_capex(self):
        # Only the workbook/update scalar-edit forms require sheet_id=capex.
        # Custom-row command forms (add/update/deactivate/reorder) post to
        # /v2/capex/line/* and do not carry sheet_id.
        forms = [
            f for f in self.capex.find_all("form")
            if (f.get("hx-post") or "").endswith("/v2/workbook/update")
        ]
        for form in forms:
            sheet_input = form.find("input", attrs={"name": "sheet_id"})
            self.assertIsNotNone(sheet_input,
                                 "workbook/update form must have a sheet_id hidden input")
            self.assertEqual(sheet_input.get("value", ""), "capex",
                             f"sheet_id value should be 'capex', got: {sheet_input.get('value')!r}")

    def test_no_duplicate_data_field_id_in_capex(self):
        fids = [el["data-field-id"]
                for el in self.capex.find_all(attrs={"data-field-id": True})]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate data-field-id in CAPEX DOM: {dupes}")


# ---------------------------------------------------------------------------
# 5b. C.08/C.11 shared-field alias row
# ---------------------------------------------------------------------------

class TestCapexSharedFieldAlias(unittest.TestCase):
    """
    C.08 and C.11 both map to capex.D.audit_legal (legacy quirk).
    C.08 gets the editable render_field form (the owner).
    C.11 gets a read-only SHARED FIELD alias row — visible, clearly labelled,
    no form/input, pointing back to C.08.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "alias-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.capex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-capex")

    def _group_el(self, code):
        return self.capex.find(attrs={"data-group-code": code})

    def test_c08_group_present(self):
        el = self._group_el("C.08")
        self.assertIsNotNone(el, "C.08 group must be present in CAPEX DOM")

    def test_c11_group_present(self):
        el = self._group_el("C.11")
        self.assertIsNotNone(el, "C.11 group must be present in CAPEX DOM (alias, not hidden)")

    def test_c08_has_editable_input(self):
        el = self._group_el("C.08")
        if el is None:
            self.skipTest("C.08 not present")
        inputs = el.find_all("input", class_="v2-field-input")
        self.assertGreater(len(inputs), 0,
                           "C.08 (owner of audit_legal) must have an editable input")

    def test_c11_has_no_editable_input(self):
        el = self._group_el("C.11")
        if el is None:
            self.skipTest("C.11 not present")
        inputs = el.find_all("input", class_="v2-field-input")
        self.assertEqual(len(inputs), 0,
                         "C.11 (alias of audit_legal) must have no editable input")

    def test_c11_has_no_form(self):
        el = self._group_el("C.11")
        if el is None:
            self.skipTest("C.11 not present")
        forms = el.find_all("form")
        self.assertEqual(len(forms), 0,
                         "C.11 (alias) must not contain a form element")

    def test_c11_has_shared_field_badge(self):
        el = self._group_el("C.11")
        if el is None:
            self.skipTest("C.11 not present")
        badge = el.find(class_="v2-capex-badge-shared")
        self.assertIsNotNone(badge,
                             "C.11 must have a SHARED FIELD badge (.v2-capex-badge-shared)")

    def test_c11_alias_row_references_owner_group(self):
        """The alias row must identify C.08 as the owning group."""
        el = self._group_el("C.11")
        if el is None:
            self.skipTest("C.11 not present")
        alias_row = el.find(attrs={"data-shared-field": "true"})
        self.assertIsNotNone(alias_row, "C.11 must contain a data-shared-field row")
        owner = alias_row.get("data-owner-group", "")
        self.assertEqual(owner, "C.08",
                         f"Alias row data-owner-group must be 'C.08', got {owner!r}")

    def test_c11_has_group_alias_class(self):
        el = self._group_el("C.11")
        if el is None:
            self.skipTest("C.11 not present")
        self.assertIn("v2-capex-group-alias", el.get("class", []),
                      "C.11 group element must have v2-capex-group-alias CSS class")

    def test_audit_legal_field_id_appears_only_once_as_editable(self):
        """capex.D.audit_legal must appear as editable (data-field-id) exactly once."""
        editable_fids = [
            el["data-field-id"]
            for el in self.capex.find_all(attrs={"data-field-id": True})
        ]
        count = editable_fids.count("capex.D.audit_legal")
        self.assertEqual(count, 1,
                         f"capex.D.audit_legal must appear exactly once as editable; found {count}")

    def test_no_duplicate_editable_field_ids(self):
        """No data-field-id should appear more than once as an editable control."""
        fids = [el["data-field-id"]
                for el in self.capex.find_all(attrs={"data-field-id": True})]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate editable data-field-id in CAPEX DOM: {dupes}")


# ---------------------------------------------------------------------------
# 6. ENGINE badge on C.17 / C.18 groups
# ---------------------------------------------------------------------------

class TestCapexEngineBadge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "engine-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.capex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-capex")

    def _group_element(self, code: str):
        return self.capex.find(attrs={"data-group-code": code})

    def test_c17_has_engine_badge(self):
        el = self._group_element("C.17")
        if el is None:
            self.skipTest("C.17 not present in this project's CAPEX data")
        badge = el.find(class_="v2-capex-badge-engine")
        self.assertIsNotNone(badge,
                             "C.17 group should have .v2-capex-badge-engine badge")

    def test_c18_has_engine_badge(self):
        el = self._group_element("C.18")
        if el is None:
            self.skipTest("C.18 not present in this project's CAPEX data")
        badge = el.find(class_="v2-capex-badge-engine")
        self.assertIsNotNone(badge,
                             "C.18 group should have .v2-capex-badge-engine badge")

    def test_c17_no_editable_inputs(self):
        el = self._group_element("C.17")
        if el is None:
            self.skipTest("C.17 not present")
        inputs = el.find_all("input", class_="v2-field-input")
        self.assertEqual(len(inputs), 0,
                         "C.17 (engine group) must have no editable inputs")

    def test_c18_no_editable_inputs(self):
        el = self._group_element("C.18")
        if el is None:
            self.skipTest("C.18 not present")
        inputs = el.find_all("input", class_="v2-field-input")
        self.assertEqual(len(inputs), 0,
                         "C.18 (engine group) must have no editable inputs")


# ---------------------------------------------------------------------------
# 7. DERIVED badge on C.13 (Contingencies)
# ---------------------------------------------------------------------------

class TestCapexDerivedBadge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "derived-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.capex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-capex")

    def test_c13_no_editable_input(self):
        el = self.capex.find(attrs={"data-group-code": "C.13"})
        if el is None:
            self.skipTest("C.13 not present in this project's CAPEX data")
        inputs = el.find_all("input", class_="v2-field-input")
        self.assertEqual(len(inputs), 0,
                         "C.13 (contingencies, derived) must have no editable inputs")

    def test_c13_has_derived_badge_or_engine_row(self):
        el = self.capex.find(attrs={"data-group-code": "C.13"})
        if el is None:
            self.skipTest("C.13 not present")
        derived_badge = el.find(class_="v2-capex-badge-derived")
        engine_row = el.find(class_="v2-capex-engine-row")
        self.assertTrue(
            derived_badge or engine_row,
            "C.13 group should have a DERIVED badge or engine-row class",
        )


# ---------------------------------------------------------------------------
# 8. Protected reference — zero editable controls
# ---------------------------------------------------------------------------

class TestCapexProtectedRef(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "protected-01")
        cls.html = _get_workbook(cls.client, cls.project_code)

    def _capex_div_with_mock_protected(self):
        from app.ui.protected_reference_service import is_protected_reference
        from app.persistence.projects_repository import get_project_record

        with patch("app.v2.router.is_protected_reference", return_value=True):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            assert resp.status_code == 200
            return BeautifulSoup(resp.text, "html.parser").find(id="v2-sheet-capex")

    def test_protected_ref_shows_zero_editable_inputs(self):
        capex = self._capex_div_with_mock_protected()
        inputs = capex.find_all("input", class_="v2-field-input")
        self.assertEqual(len(inputs), 0,
                         "Protected reference project must have no editable inputs in CAPEX")

    def test_protected_ref_shows_protected_notice(self):
        capex = self._capex_div_with_mock_protected()
        notice = capex.find(class_="v2-protected-notice")
        self.assertIsNotNone(notice, "Protected reference must show v2-protected-notice")

    def test_user_project_has_editable_inputs(self):
        capex = BeautifulSoup(self.html, "html.parser").find(id="v2-sheet-capex")
        inputs = capex.find_all("input", class_="v2-field-input")
        self.assertGreater(len(inputs), 0,
                           "User project must have at least one editable CAPEX input")


# ---------------------------------------------------------------------------
# 9. Totals come from CapexViewModel; no hardcoded formulas in template
# ---------------------------------------------------------------------------

class TestCapexTotals(unittest.TestCase):

    def test_template_has_no_arithmetic_formulas(self):
        """The CAPEX template must not contain Jinja arithmetic."""
        import re
        from pathlib import Path
        tmpl = Path("app/templates/v2/partials/sheet_capex.html").read_text()
        # Detect simple arithmetic: number OP number (e.g. 1000 + 2000)
        arith = re.findall(r"\d+\s*[+\-\*\/]\s*\d+", tmpl)
        self.assertFalse(arith, f"Template contains arithmetic: {arith}")

    def test_template_uses_capex_vm_for_totals(self):
        from pathlib import Path
        tmpl = Path("app/templates/v2/partials/sheet_capex.html").read_text()
        self.assertIn("capex_vm.total_capex_keur", tmpl,
                      "Template must read total from capex_vm, not compute it")
        self.assertIn("capex_vm.hard_capex_keur", tmpl)

    def test_template_uses_capex_vm_for_group_subtotals(self):
        from pathlib import Path
        tmpl = Path("app/templates/v2/partials/sheet_capex.html").read_text()
        self.assertIn("group.subtotal_keur", tmpl,
                      "Template must read group subtotal from CapexGroupVM")

    def test_template_uses_render_field_for_bound(self):
        from pathlib import Path
        tmpl = Path("app/templates/v2/partials/sheet_capex.html").read_text()
        self.assertIn("render_field", tmpl,
                      "Template must import and call render_field for BOUND fields")

    def test_template_no_direct_capex_field_id_hardcoded(self):
        """Template must not hardcode registry field IDs like 'capex.C.epc_contract'."""
        from pathlib import Path
        tmpl = Path("app/templates/v2/partials/sheet_capex.html").read_text()
        # These registry field IDs must never appear hardcoded in the template
        forbidden_ids = [
            "capex.C.epc_contract",
            "capex.C.production_units",
            "capex.C.grid_connection",
        ]
        for fid in forbidden_ids:
            self.assertNotIn(fid, tmpl,
                             f"Template must not hardcode registry field_id: {fid!r}")


# ---------------------------------------------------------------------------
# 10. HTMX edit roundtrip — capex field edit
# ---------------------------------------------------------------------------

class TestCapexHtmxEdit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "htmx-01")
        # Fetch initial workbook to get content_hash and a BOUND capex field_id
        resp = cls.client.get(f"/v2/workbook?project={cls.project_code}")
        assert resp.status_code == 200
        soup = BeautifulSoup(resp.text, "html.parser")
        capex = soup.find(id="v2-sheet-capex")
        # Find first editable capex form
        form = capex.find("form") if capex else None
        if form:
            cls.field_id = (form.find("input", attrs={"name": "field_id"}) or {}).get("value", "")
            cls.content_hash = (form.find("input", attrs={"name": "content_hash"}) or {}).get("value", "")
            cls.workbook_version = (form.find("input", attrs={"name": "workbook_version"}) or {}).get("value", "")
        else:
            cls.field_id = ""
            cls.content_hash = ""
            cls.workbook_version = ""

    def _htmx_post(self, field_id, value, content_hash, workbook_version=None):
        return self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": field_id,
                "value": value,
                "project": self.project_code,
                "workbook_version": workbook_version or self.workbook_version,
                "content_hash": content_hash,
                "sheet_id": "capex",
            },
            headers={"HX-Request": "true"},
        )

    def test_htmx_success_returns_200(self):
        if not self.field_id:
            self.skipTest("No editable CAPEX field found in DOM")
        resp = self._htmx_post(self.field_id, "5000", self.content_hash)
        self.assertEqual(resp.status_code, 200)

    def test_htmx_response_contains_capex_div(self):
        if not self.field_id:
            self.skipTest("No editable CAPEX field found in DOM")
        resp = self._htmx_post(self.field_id, "5000", self.content_hash)
        self.assertIn("v2-sheet-capex", resp.text)

    def test_htmx_response_contains_oob_banner(self):
        if not self.field_id:
            self.skipTest("No editable CAPEX field found in DOM")
        resp = self._htmx_post(self.field_id, "5000", self.content_hash)
        self.assertIn("v2-status-banner", resp.text)
        self.assertIn("hx-swap-oob", resp.text)

    def test_htmx_stale_hash_returns_200_with_error(self):
        if not self.field_id:
            self.skipTest("No editable CAPEX field found in DOM")
        resp = self._htmx_post(self.field_id, "5000", "stale-hash-000")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-capex", resp.text)

    def test_htmx_unknown_field_returns_422(self):
        resp = self._htmx_post("capex.unknown.field_xyz", "999", self.content_hash)
        self.assertEqual(resp.status_code, 422)

    def test_htmx_response_has_updated_content_hash(self):
        if not self.field_id:
            self.skipTest("No editable CAPEX field found in DOM")
        resp = self._htmx_post(self.field_id, "6000", self.content_hash)
        self.assertEqual(resp.status_code, 200)
        new_soup = BeautifulSoup(resp.text, "html.parser")
        # The new content_hash should appear in a hidden form input
        hash_inputs = new_soup.find_all("input", attrs={"name": "content_hash"})
        self.assertGreater(len(hash_inputs), 0, "No content_hash hidden input in response")

    def test_capex_sheet_id_routing(self):
        """Ensure sheet_id='capex' routes to the CAPEX partial, not project_setup."""
        if not self.field_id:
            self.skipTest("No editable CAPEX field found in DOM")
        resp = self._htmx_post(self.field_id, "7000", self.content_hash)
        # Should return CAPEX sheet, NOT project_setup sheet
        self.assertIn("v2-sheet-capex", resp.text)
        self.assertNotIn("v2-sheet-project-setup", resp.text)


# ---------------------------------------------------------------------------
# 11. OOB status banner — present and correct
# ---------------------------------------------------------------------------

class TestCapexOobBanner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "oob-01")
        resp = cls.client.get(f"/v2/workbook?project={cls.project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        capex = soup.find(id="v2-sheet-capex")
        form = capex.find("form") if capex else None
        if form:
            cls.field_id = (form.find("input", attrs={"name": "field_id"}) or {}).get("value", "")
            cls.content_hash = (form.find("input", attrs={"name": "content_hash"}) or {}).get("value", "")
            cls.workbook_version = (form.find("input", attrs={"name": "workbook_version"}) or {}).get("value", "")
        else:
            cls.field_id = ""
            cls.content_hash = ""
            cls.workbook_version = ""

    def test_oob_banner_div_in_htmx_response(self):
        if not self.field_id:
            self.skipTest("No editable CAPEX field found")
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": self.field_id,
                "value": "8000",
                "project": self.project_code,
                "workbook_version": self.workbook_version,
                "content_hash": self.content_hash,
                "sheet_id": "capex",
            },
            headers={"HX-Request": "true"},
        )
        self.assertIn('id="v2-status-banner"', resp.text)
        self.assertIn('hx-swap-oob="true"', resp.text)


# ---------------------------------------------------------------------------
# 12. No legacy snapshot keys appear in capex form field_id inputs
# ---------------------------------------------------------------------------

class TestCapexNoLegacyKeys(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "legacy-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.capex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-capex")

    def test_no_legacy_snapshot_keys_in_forms(self):
        legacy_prefixes = (
            "capex_", "opex_", "tariff_", "ppa_term", "capacity_", "cod_",
            "horizon_", "p50_", "gearing_", "interest_",
        )
        forms = self.capex.find_all("form") if self.capex else []
        for form in forms:
            fid_input = form.find("input", attrs={"name": "field_id"})
            if not fid_input:
                continue
            fid = fid_input.get("value", "")
            for prefix in legacy_prefixes:
                self.assertFalse(
                    fid.startswith(prefix),
                    f"Legacy snapshot key found in CAPEX form: {fid!r}",
                )


# ---------------------------------------------------------------------------
# 13. Template structural invariants
# ---------------------------------------------------------------------------

class TestCapexTemplateInvariants(unittest.TestCase):

    def _read_template(self):
        from pathlib import Path
        return Path("app/templates/v2/partials/sheet_capex.html").read_text()

    def test_template_imports_render_field_macro(self):
        tmpl = self._read_template()
        self.assertIn("from \"partials/field_editor.html\" import render_field", tmpl)

    def test_template_iterates_capex_vm_groups(self):
        tmpl = self._read_template()
        self.assertIn("capex_vm.groups", tmpl,
                      "Template must iterate capex_vm.groups for C.01-C.18 structure")

    def test_template_iterates_group_lines(self):
        tmpl = self._read_template()
        self.assertIn("group.lines", tmpl,
                      "Template must iterate group.lines for sub-line detail rows")

    def test_template_uses_capex_group_to_field(self):
        tmpl = self._read_template()
        self.assertIn("capex_group_to_field", tmpl,
                      "Template must use capex_group_to_field for registry field lookup")

    def test_template_handles_engine_groups(self):
        tmpl = self._read_template()
        self.assertIn("group.is_financing", tmpl,
                      "Template must check group.is_financing for ENGINE/C.17 handling")
        self.assertIn("group.is_reserve", tmpl,
                      "Template must check group.is_reserve for ENGINE/C.18 handling")

    def test_template_handles_contingency(self):
        tmpl = self._read_template()
        self.assertIn("group.is_contingency", tmpl,
                      "Template must check group.is_contingency for C.13 DERIVED handling")
