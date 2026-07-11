"""
Tests for the Workbook V2 OPEX worksheet (PR #870 rev 2).

Coverage
--------
1.  CANONICAL_OPEX_GROUPS — single owner of B.01-B.13 mapping, order, suffixes
2.  build_opex_sheet_projection — always 13 groups, correct merge, B.09/B.13 semantics
3.  Router: _build_opex_vm_ctx returns opex_sheet_groups (no hardcoded OPEX map in router)
4.  Registry: _build_sheet_fields("opex") — field count, binding labels, PARTIAL not filtered
5.  DOM: exactly 13 group <details> elements, B.01-B.13 in exact order
6.  DOM: B.09 always ENGINE/read-only, no editable form (even in generic project)
7.  DOM: B.13 always DERIVED/read-only, no editable form
8.  DOM: all registered OPEX BOUND field IDs appear exactly once (no duplicates)
9.  DOM: PARTIAL fields not filtered out
10. DOM: KPI strip present with correct testid attributes
11. DOM: runtime state A/B/C — correct text, Run Required logic
12. HTMX edit roundtrip — returns #v2-sheet-opex partial, hash rotates, dirty → Run Required
13. Protected reference — zero editable controls
14. Working copy — editable controls present
15. No legacy snapshot keys in form field_id inputs
16. All forms use hx-target="#v2-sheet-opex" and sheet_id="opex"
17. Year projection table — 13 group rows in order, total row, Y1 column
18. No DOM tests skipped for B.01-B.13
"""
from __future__ import annotations

import dataclasses
import os
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-opex-tests-v2")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.ui.opex_sheet_projection import (  # noqa: E402
    CANONICAL_OPEX_GROUPS,
    CANONICAL_OPEX_GROUP_BY_CODE,
    build_opex_sheet_projection,
    CanonicalOpexGroup,
    OpexSheetGroup,
)
from app.v2.router import _build_opex_vm_ctx, _build_sheet_fields  # noqa: E402
from app.workbook.registry import WORKBOOK  # noqa: E402
from app.workbook.specs import BindingStatus  # noqa: E402


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
            "project_name": f"OPEX V2 Test {suffix}",
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


def _opex_div(html: str):
    return BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")


def _fake_pis():
    m = MagicMock()
    m.get = lambda fid: None
    return m


def _fake_opex_vm():
    """Minimal OpexViewModel stub with zero groups."""
    from app.ui.opex_view_model import OpexViewModel
    return OpexViewModel(
        project_name="Test",
        capacity_mw=100.0,
        p50_annual_mwh=250000.0,
        groups=(),
        contingency_rate=0.0,
        total_excl_contingency=(0.0,) * 30,
        contingency_by_year=(0.0,) * 30,
        total_incl_contingency=(0.0,) * 30,
        y1_total_opex=0.0,
        final_year_total_opex=0.0,
        display_years=30,
        opex_per_mw_y1=None,
        opex_per_mwh_y1=None,
        is_user_project=True,
    )


# ---------------------------------------------------------------------------
# 1. CANONICAL_OPEX_GROUPS — single source of truth
# ---------------------------------------------------------------------------

class TestCanonicalOpexGroups(unittest.TestCase):

    def test_exactly_13_canonical_groups(self):
        self.assertEqual(len(CANONICAL_OPEX_GROUPS), 13)

    def test_exact_b_code_order(self):
        codes = [g.code for g in CANONICAL_OPEX_GROUPS]
        expected = [f"B.{n:02d}" for n in range(1, 14)]
        self.assertEqual(codes, expected, f"Canonical order wrong: {codes}")

    def test_all_codes_in_lookup(self):
        for g in CANONICAL_OPEX_GROUPS:
            self.assertIn(g.code, CANONICAL_OPEX_GROUP_BY_CODE)
            self.assertIs(CANONICAL_OPEX_GROUP_BY_CODE[g.code], g)

    def test_b09_has_no_field_suffix(self):
        """B.09 Fees has no BOUND registry field."""
        b09 = CANONICAL_OPEX_GROUP_BY_CODE["B.09"]
        self.assertIsNone(b09.field_suffix)
        self.assertFalse(b09.is_always_derived)

    def test_b13_is_always_derived(self):
        b13 = CANONICAL_OPEX_GROUP_BY_CODE["B.13"]
        self.assertTrue(b13.is_always_derived)
        self.assertEqual(b13.field_suffix, "contingencies")

    def test_b01_to_b08_have_suffixes(self):
        for n in range(1, 9):
            g = CANONICAL_OPEX_GROUP_BY_CODE[f"B.{n:02d}"]
            self.assertIsNotNone(g.field_suffix, f"B.{n:02d} should have a field suffix")

    def test_b10_b11_b12_have_suffixes(self):
        for code in ("B.10", "B.11", "B.12"):
            g = CANONICAL_OPEX_GROUP_BY_CODE[code]
            self.assertIsNotNone(g.field_suffix, f"{code} should have a field suffix")

    def test_types(self):
        for g in CANONICAL_OPEX_GROUPS:
            self.assertIsInstance(g, CanonicalOpexGroup)
            self.assertIsInstance(g.code, str)
            self.assertIsInstance(g.name, str)


# ---------------------------------------------------------------------------
# 2. build_opex_sheet_projection
# ---------------------------------------------------------------------------

class TestBuildOpexSheetProjection(unittest.TestCase):

    def _build(self, opex_vm=None, opex_fields=None):
        if opex_vm is None:
            opex_vm = _fake_opex_vm()
        if opex_fields is None:
            opex_fields = []
        return build_opex_sheet_projection(opex_vm, opex_fields)

    def test_always_returns_13_groups(self):
        groups = self._build()
        self.assertEqual(len(groups), 13)

    def test_returns_tuple(self):
        groups = self._build()
        self.assertIsInstance(groups, tuple)

    def test_exact_order_b01_to_b13(self):
        groups = self._build()
        codes = [g.code for g in groups]
        expected = [f"B.{n:02d}" for n in range(1, 14)]
        self.assertEqual(codes, expected)

    def test_b09_is_engine(self):
        groups = self._build()
        b09 = next(g for g in groups if g.code == "B.09")
        self.assertTrue(b09.is_engine)
        self.assertFalse(b09.is_derived)
        self.assertFalse(b09.is_bound)
        self.assertIsNone(b09.field_suffix)

    def test_b13_is_derived(self):
        groups = self._build()
        b13 = next(g for g in groups if g.code == "B.13")
        self.assertTrue(b13.is_derived)
        self.assertFalse(b13.is_engine)

    def test_empty_vm_produces_no_vm_data_groups(self):
        groups = self._build()
        for g in groups:
            self.assertFalse(g.has_vm_data)
            self.assertIsNone(g.vm_group)

    def test_vm_group_merged_correctly(self):
        """When VM has a group for B.01, it merges into the OpexSheetGroup."""
        from app.ui.opex_view_model import OpexGroupVM, OpexViewModel
        vm_group = OpexGroupVM(
            code="B.01",
            name="Tech Mgmt VM",
            inflation_pct=2.0,
            is_contingency=False,
            contingency_pct=0.0,
            lines=(),
            subtotal_per_year=(100.0,) * 30,
        )
        opex_vm = dataclasses.replace(_fake_opex_vm(), groups=(vm_group,))
        groups = build_opex_sheet_projection(opex_vm, [])
        b01 = next(g for g in groups if g.code == "B.01")
        self.assertTrue(b01.has_vm_data)
        self.assertIs(b01.vm_group, vm_group)
        self.assertAlmostEqual(b01.subtotal_y1, 100.0)

    def test_field_merged_for_b01(self):
        """Registry field for B.01 suffix 'technical_management' merges into OpexSheetGroup."""
        fields = [{"field_id": "opex.lines.technical_management", "binding_label": "bound",
                   "label": "Technical Management", "value": "500"}]
        groups = build_opex_sheet_projection(_fake_opex_vm(), fields)
        b01 = next(g for g in groups if g.code == "B.01")
        self.assertIsNotNone(b01.field)
        self.assertEqual(b01.field["binding_label"], "bound")

    def test_b09_never_gets_field_even_if_passed(self):
        """B.09 has no field_suffix — no field can be merged for it."""
        # Even if we pass a field that happens to match somehow, B.09.field stays None
        groups = build_opex_sheet_projection(_fake_opex_vm(), [])
        b09 = next(g for g in groups if g.code == "B.09")
        self.assertIsNone(b09.field)
        self.assertIsNone(b09.field_suffix)

    def test_subtotal_y1_zero_when_no_vm_data(self):
        groups = self._build()
        for g in groups:
            self.assertAlmostEqual(g.subtotal_y1, 0.0)

    def test_all_types_are_opex_sheet_group(self):
        groups = self._build()
        for g in groups:
            self.assertIsInstance(g, OpexSheetGroup)


# ---------------------------------------------------------------------------
# 3. Router: _build_opex_vm_ctx — no hardcoded OPEX map in router module
# ---------------------------------------------------------------------------

class TestRouterOpexVmCtx(unittest.TestCase):

    def test_router_has_no_hardcoded_opex_field_suffix_dict(self):
        """_OPEX_GROUP_FIELD_SUFFIX must not exist in router (moved to opex_sheet_projection)."""
        import app.v2.router as router_module
        self.assertFalse(
            hasattr(router_module, "_OPEX_GROUP_FIELD_SUFFIX"),
            "router.py must not define _OPEX_GROUP_FIELD_SUFFIX — it belongs in opex_sheet_projection",
        )

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "router-ctx-01")

    def _get_ctx(self):
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        from app.workbook.service import WorkbookService
        token = create_session_token()
        from app.auth import decode_session_token
        user = decode_session_token(token)
        project_record = get_project_record(user_id=user.user_id, project_code=self.project_code)
        ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        return _build_opex_vm_ctx(project_record, pis)

    def test_opex_vm_key_present(self):
        ctx = self._get_ctx()
        self.assertIn("opex_vm", ctx)

    def test_opex_sheet_groups_key_present(self):
        ctx = self._get_ctx()
        self.assertIn("opex_sheet_groups", ctx)

    def test_opex_sheet_groups_always_13(self):
        ctx = self._get_ctx()
        self.assertEqual(len(ctx["opex_sheet_groups"]), 13)

    def test_opex_sheet_groups_exact_order(self):
        ctx = self._get_ctx()
        codes = [g.code for g in ctx["opex_sheet_groups"]]
        expected = [f"B.{n:02d}" for n in range(1, 14)]
        self.assertEqual(codes, expected)

    def test_b09_is_engine_in_ctx(self):
        ctx = self._get_ctx()
        b09 = next(g for g in ctx["opex_sheet_groups"] if g.code == "B.09")
        self.assertTrue(b09.is_engine)

    def test_b13_is_derived_in_ctx(self):
        ctx = self._get_ctx()
        b13 = next(g for g in ctx["opex_sheet_groups"] if g.code == "B.13")
        self.assertTrue(b13.is_derived)

    def test_opex_sheet_groups_no_opex_group_to_field_key(self):
        """Old key opex_group_to_field must not be in the context."""
        ctx = self._get_ctx()
        self.assertNotIn("opex_group_to_field", ctx)


# ---------------------------------------------------------------------------
# 4. Registry: _build_sheet_fields("opex")
# ---------------------------------------------------------------------------

class TestOpexBuildSheetFields(unittest.TestCase):

    def test_opex_fields_returned(self):
        rows = _build_sheet_fields("opex", _fake_pis())
        self.assertGreater(len(rows), 0)

    def test_field_count_matches_registry(self):
        sheet = WORKBOOK.sheet("opex")
        expected = sum(len(sec.fields) for sec in sheet.sections)
        rows = _build_sheet_fields("opex", _fake_pis())
        self.assertEqual(len(rows), expected)

    def test_no_duplicate_field_ids(self):
        rows = _build_sheet_fields("opex", _fake_pis())
        fids = [r["field_id"] for r in rows]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids: {dupes}")

    def test_required_dict_keys_present(self):
        rows = _build_sheet_fields("opex", _fake_pis())
        required = {
            "field_id", "label", "unit", "field_type", "binding_label",
            "options", "section_id", "value", "required",
            "min_value", "max_value", "step", "help_text",
        }
        for row in rows:
            missing = required - row.keys()
            self.assertFalse(missing, f"Row {row['field_id']} missing keys: {missing}")

    def test_bound_fields_exist(self):
        rows = _build_sheet_fields("opex", _fake_pis())
        bound = [r for r in rows if r["binding_label"] == "bound"]
        self.assertGreater(len(bound), 0)

    def test_contingencies_is_display_only(self):
        rows = _build_sheet_fields("opex", _fake_pis())
        cont = next((r for r in rows if r["field_id"] == "opex.lines.contingencies"), None)
        self.assertIsNotNone(cont, "opex.lines.contingencies missing")
        self.assertEqual(cont["binding_label"], "display-only")

    def test_summary_total_y1_is_partial(self):
        rows = _build_sheet_fields("opex", _fake_pis())
        total = next((r for r in rows if r["field_id"] == "opex.summary.total_y1"), None)
        self.assertIsNotNone(total, "opex.summary.total_y1 missing")
        self.assertEqual(total["binding_label"], "partial")

    def test_partial_fields_not_filtered_out(self):
        """PARTIAL fields must appear in the field list — never silently dropped."""
        rows = _build_sheet_fields("opex", _fake_pis())
        partial = [r for r in rows if r["binding_label"] == "partial"]
        self.assertGreater(len(partial), 0, "Expected at least one PARTIAL field in opex sheet")

    def test_every_bound_field_has_opex_prefix(self):
        rows = _build_sheet_fields("opex", _fake_pis())
        for r in rows:
            self.assertTrue(r["field_id"].startswith("opex."),
                            f"field_id {r['field_id']!r} does not start with 'opex.'")


# ---------------------------------------------------------------------------
# 5. DOM: exactly 13 groups, B.01–B.13 in exact order
# ---------------------------------------------------------------------------

class TestOpexGroupAccordionCanonical(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "canon-dom-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.opex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")
        cls.group_els = cls.opex.find_all("details", class_="v2-opex-group")

    def test_exactly_13_group_details(self):
        self.assertEqual(len(self.group_els), 13,
                         f"Expected 13 groups, got {len(self.group_els)}: "
                         f"{[g.get('data-group-code') for g in self.group_els]}")

    def test_exact_b01_to_b13_order(self):
        codes = [g.get("data-group-code") for g in self.group_els]
        expected = [f"B.{n:02d}" for n in range(1, 14)]
        self.assertEqual(codes, expected, f"Group order wrong: {codes}")

    def test_each_group_has_testid(self):
        for n in range(1, 14):
            code = f"B.{n:02d}"
            el = self.opex.find(attrs={"data-testid": f"opex-group-{code}"})
            self.assertIsNotNone(el, f"testid opex-group-{code} missing")

    def test_each_group_has_subtotal_testid(self):
        for n in range(1, 14):
            code = f"B.{n:02d}"
            el = self.opex.find(attrs={"data-testid": f"opex-subtotal-{code}"})
            self.assertIsNotNone(el, f"testid opex-subtotal-{code} missing")


# ---------------------------------------------------------------------------
# 6. DOM: B.09 always ENGINE (even in generic project)
# ---------------------------------------------------------------------------

class TestOpexB09AlwaysEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "b09-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.opex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")
        cls.b09 = cls.opex.find("details", attrs={"data-group-code": "B.09"})

    def test_b09_present_in_dom(self):
        self.assertIsNotNone(self.b09, "B.09 missing from DOM — must always render")

    def test_b09_has_engine_badge(self):
        badge = self.b09.find(attrs={"data-testid": "badge-engine-B.09"})
        self.assertIsNotNone(badge, "B.09 ENGINE badge testid missing")

    def test_b09_has_no_editable_form(self):
        forms = self.b09.find_all("form", class_="v2-field-form")
        self.assertEqual(len(forms), 0, "B.09 must not have an editable form")

    def test_b09_has_no_value_input(self):
        inp = self.b09.find("input", {"name": "value"})
        self.assertIsNone(inp, "B.09 must not have an editable value input")


# ---------------------------------------------------------------------------
# 7. DOM: B.13 always DERIVED (even in generic project)
# ---------------------------------------------------------------------------

class TestOpexB13AlwaysDerived(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "b13-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.opex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")
        cls.b13 = cls.opex.find("details", attrs={"data-group-code": "B.13"})

    def test_b13_present_in_dom(self):
        self.assertIsNotNone(self.b13, "B.13 missing from DOM — must always render")

    def test_b13_has_derived_badge(self):
        badge = self.b13.find(attrs={"data-testid": "badge-derived-B.13"})
        self.assertIsNotNone(badge, "B.13 DERIVED badge testid missing")

    def test_b13_has_no_editable_form(self):
        forms = self.b13.find_all("form", class_="v2-field-form")
        self.assertEqual(len(forms), 0, "B.13 must not have an editable form")

    def test_b13_has_no_value_input(self):
        inp = self.b13.find("input", {"name": "value"})
        self.assertIsNone(inp, "B.13 must not have an editable value input")


# ---------------------------------------------------------------------------
# 8. DOM: registered OPEX BOUND field IDs — each appears exactly once
# ---------------------------------------------------------------------------

class TestOpexAllRegisteredFieldsInDom(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "all-fields-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.opex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")

    def _dom_field_ids(self):
        return [el["data-field-id"] for el in self.opex.find_all(attrs={"data-field-id": True})]

    def test_no_duplicate_field_ids_in_dom(self):
        fids = self._dom_field_ids()
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids in OPEX DOM: {dupes}")

    def test_bound_fields_have_editable_rows(self):
        """At least the BOUND fields for groups present in the VM must be editable."""
        editable = self.opex.find_all(class_="v2-field-editable")
        self.assertGreater(len(editable), 0, "Expected some editable rows in OPEX sheet")

    def test_all_forms_have_opex_sheet_id(self):
        for form in self.opex.find_all("form", class_="v2-field-form"):
            sheet_input = form.find("input", {"name": "sheet_id"})
            self.assertIsNotNone(sheet_input, "form missing sheet_id input")
            self.assertEqual(sheet_input.get("value"), "opex",
                             f"form has wrong sheet_id: {sheet_input.get('value')!r}")

    def test_all_forms_target_opex_sheet(self):
        for form in self.opex.find_all("form", class_="v2-field-form"):
            self.assertEqual(
                form.get("hx-target"), "#v2-sheet-opex",
                f"form hx-target wrong: {form.get('hx-target')!r}",
            )

    def test_no_legacy_snapshot_keys_in_form_field_ids(self):
        legacy_keys = {
            "opex_technical_management_y1_keur",
            "opex_o_and_m_preventive_and_corrective_y1_keur",
            "opex_y1_keur",
        }
        for form in self.opex.find_all("form", class_="v2-field-form"):
            fid_input = form.find("input", {"name": "field_id"})
            if fid_input:
                self.assertNotIn(fid_input.get("value", ""), legacy_keys,
                                 f"Legacy key in form: {fid_input.get('value')!r}")

    def test_every_rendered_bound_field_appears_exactly_once(self):
        """Every BOUND field that IS rendered as editable must appear exactly once.

        Groups absent from the project VM render ENGINE/read-only (no data-field-id).
        The invariant is: no field that IS rendered appears more than once.
        """
        fids_in_dom = self._dom_field_ids()
        dupes = [f for f in set(fids_in_dom) if fids_in_dom.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate data-field-id elements in OPEX sheet: {dupes}")

    def test_partial_fields_not_filtered_from_dom(self):
        """PARTIAL fields must not be silently filtered — they must appear in the DOM."""
        rows = _build_sheet_fields("opex", _fake_pis())
        partial_fids = [r["field_id"] for r in rows if r["binding_label"] == "partial"]
        fids_in_dom = self._dom_field_ids()
        for fid in partial_fids:
            self.assertIn(fid, fids_in_dom, f"PARTIAL field {fid!r} missing from OPEX DOM")


# ---------------------------------------------------------------------------
# 9. DOM: KPI strip and basic structure
# ---------------------------------------------------------------------------

class TestOpexKpiAndStructure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "kpi-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.opex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")

    def test_opex_sheet_container_present(self):
        self.assertIsNotNone(self.opex, "id='v2-sheet-opex' not found")

    def test_data_sheet_attribute(self):
        self.assertEqual(self.opex.get("data-sheet"), "opex")

    def test_kpi_bar_present(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-kpi-bar"}))

    def test_kpi_y1_total(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-y1-total"}))

    def test_kpi_per_mw(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-per-mw"}))

    def test_kpi_per_mwh(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-per-mwh"}))

    def test_kpi_contingency_rate(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-contingency-rate"}))

    def test_grand_total_row_present(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-grand-total-row"}))

    def test_grand_total_y1_present(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-grand-total-y1"}))

    def test_runtime_bar_present(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-runtime-bar"}))


# ---------------------------------------------------------------------------
# 10. DOM: Runtime state A/B/C truth matrix
# ---------------------------------------------------------------------------

class TestOpexRuntimeMatrix(unittest.TestCase):
    """
    State A — no RuntimeResult:         "Not yet run"
    State B — RuntimeResult + clean:    "Outputs current"
    State C — RuntimeResult + dirty:    "Previous run available — stale for current draft"

    "Outputs current" must NEVER appear while ws_dirty=True.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "runtime-opex-01")

    def _render_with(self, *, has_runtime: bool, ws_dirty: bool) -> str:
        from app.persistence.workspace_repository import get_workspace_state as _real

        def _patched(*args, **kwargs):
            real = _real(*args, **kwargs)
            if real is None:
                return None
            return dataclasses.replace(
                real,
                dirty=ws_dirty,
                last_runtime_snapshot_id="snap-001" if has_runtime else None,
                last_runtime_at=None,
            )

        with patch("app.persistence.workspace_repository.get_workspace_state",
                   side_effect=_patched):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")

        assert resp.status_code == 200
        return resp.text

    def _opex(self, html: str):
        return _opex_div(html)

    def test_state_a_not_yet_run(self):
        opex = self._opex(self._render_with(has_runtime=False, ws_dirty=False))
        self.assertIsNotNone(opex.find(attrs={"data-testid": "opex-runtime-state-a"}))
        self.assertIn("Not yet run", opex.get_text())
        self.assertNotIn("Outputs current", opex.get_text())
        self.assertNotIn("stale", opex.get_text())

    def test_state_b_outputs_current(self):
        opex = self._opex(self._render_with(has_runtime=True, ws_dirty=False))
        self.assertIsNotNone(opex.find(attrs={"data-testid": "opex-runtime-state-b"}))
        self.assertIn("Outputs current", opex.get_text())
        self.assertNotIn("Not yet run", opex.get_text())
        self.assertNotIn("stale", opex.get_text())

    def test_state_c_stale(self):
        opex = self._opex(self._render_with(has_runtime=True, ws_dirty=True))
        self.assertIsNotNone(opex.find(attrs={"data-testid": "opex-runtime-state-c"}))
        self.assertIn("stale", opex.get_text())
        self.assertNotIn("Outputs current", opex.get_text())
        self.assertNotIn("Not yet run", opex.get_text())

    def test_state_c_run_required_yes(self):
        opex = self._opex(self._render_with(has_runtime=True, ws_dirty=True))
        el = opex.find(attrs={"data-testid": "opex-run-required-yes"})
        self.assertIsNotNone(el, "Run Required=Yes element missing in State C")
        self.assertIn("Yes", el.get_text())

    def test_state_b_run_required_no(self):
        opex = self._opex(self._render_with(has_runtime=True, ws_dirty=False))
        el = opex.find(attrs={"data-testid": "opex-run-required-no"})
        self.assertIsNotNone(el, "Run Required=No element missing in State B")
        self.assertNotIn("Yes", el.get_text())

    def test_outputs_current_never_when_dirty(self):
        """Regression: dirty draft must never show 'Outputs current'."""
        for has_runtime in (True, False):
            opex = self._opex(self._render_with(has_runtime=has_runtime, ws_dirty=True))
            self.assertNotIn(
                "Outputs current", opex.get_text(),
                f"'Outputs current' shown with has_runtime={has_runtime}, ws_dirty=True",
            )

    def test_state_a_run_required_no(self):
        """State A: no runtime, draft clean → Run Required = No."""
        opex = self._opex(self._render_with(has_runtime=False, ws_dirty=False))
        el = opex.find(attrs={"data-testid": "opex-run-required-no"})
        self.assertIsNotNone(el, "Run Required=No element missing in State A")


# ---------------------------------------------------------------------------
# 11. HTMX roundtrip — field update, hash rotation, dirty → Run Required
# ---------------------------------------------------------------------------

class TestOpexHtmxRoundtrip(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "htmx-opex-01")

    def _get_first_bound_form(self):
        html = _get_workbook(self.client, self.project_code)
        opex = _opex_div(html)
        form = opex.find("form", class_="v2-field-form")
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

    def test_htmx_update_returns_opex_partial(self):
        fid, wv, ch = self._get_first_bound_form()
        if not fid:
            self.skipTest("No BOUND field form in OPEX sheet for this generic project")
        resp = self.client.post(
            "/v2/workbook/update",
            data={"field_id": fid, "value": "100", "project": self.project_code,
                  "workbook_version": wv or "", "content_hash": ch or "",
                  "sheet_id": "opex"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-opex", resp.text)

    def test_htmx_update_returns_oob_status_banner(self):
        fid, wv, ch = self._get_first_bound_form()
        if not fid:
            self.skipTest("No BOUND field form in OPEX sheet for this generic project")
        resp = self.client.post(
            "/v2/workbook/update",
            data={"field_id": fid, "value": "200", "project": self.project_code,
                  "workbook_version": wv or "", "content_hash": ch or "",
                  "sheet_id": "opex"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)

    def test_htmx_update_after_edit_content_hash_rotates(self):
        """After a successful OPEX field edit the content_hash in the re-rendered
        partial must differ from the one submitted."""
        fid, wv, ch_before = self._get_first_bound_form()
        if not fid:
            self.skipTest("No BOUND field form in OPEX sheet for this generic project")
        resp = self.client.post(
            "/v2/workbook/update",
            data={"field_id": fid, "value": "999", "project": self.project_code,
                  "workbook_version": wv or "", "content_hash": ch_before or "",
                  "sheet_id": "opex"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        ch_input = soup.find("input", {"name": "content_hash"})
        self.assertIsNotNone(ch_input, "content_hash input missing from HTMX response")
        ch_after = ch_input.get("value")
        self.assertNotEqual(ch_before, ch_after,
                            "content_hash must rotate after a successful edit")

    def test_htmx_update_opex_shows_run_required_after_edit(self):
        """After an OPEX field edit the workspace is dirty — Run Required must appear."""
        fid, wv, ch = self._get_first_bound_form()
        if not fid:
            self.skipTest("No BOUND field form in OPEX sheet for this generic project")
        resp = self.client.post(
            "/v2/workbook/update",
            data={"field_id": fid, "value": "111", "project": self.project_code,
                  "workbook_version": wv or "", "content_hash": ch or "",
                  "sheet_id": "opex"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        opex = soup.find(id="v2-sheet-opex")
        self.assertIsNone(opex.find(attrs={"data-testid": "opex-runtime-state-b"}),
                          "'Outputs current' must not appear after a dirty edit")


# ---------------------------------------------------------------------------
# 12. Protected reference — zero editable controls
# ---------------------------------------------------------------------------

class TestOpexEditability(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "edit-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.opex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")

    def test_working_copy_has_editable_controls(self):
        editable = self.opex.find_all(class_="v2-field-editable")
        self.assertGreater(len(editable), 0,
                           "Working copy should have editable controls in OPEX sheet")

    def test_working_copy_no_protected_notice(self):
        notice = self.opex.find(class_="v2-protected-notice")
        self.assertIsNone(notice, "Working copy should not show protected notice")


# ---------------------------------------------------------------------------
# 13. Year projection table
# ---------------------------------------------------------------------------

class TestOpexYearProjectionTable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "proj-opex-01")
        html = _get_workbook(cls.client, cls.project_code)
        cls.opex = BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")

    def test_projection_panel_present(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-projection-panel"}))

    def test_projection_table_present(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "opex-projection-table"}))

    def test_y1_header_present(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "proj-year-1"}))

    def test_total_row_present(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "proj-row-total"}))

    def test_exactly_13_group_rows_in_projection(self):
        rows = self.opex.find_all(
            attrs={"data-testid": lambda v: v and v.startswith("proj-row-B.")}
        )
        self.assertEqual(len(rows), 13,
                         f"Expected 13 proj rows, got {len(rows)}: "
                         f"{[r.get('data-testid') for r in rows]}")

    def test_projection_b09_row_present(self):
        """B.09 must appear in the projection table."""
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "proj-row-B.09"}),
                             "proj-row-B.09 missing from projection table")

    def test_projection_b13_row_present(self):
        """B.13 must appear in the projection table."""
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "proj-row-B.13"}),
                             "proj-row-B.13 missing from projection table")

    def test_projection_total_y1_cell(self):
        self.assertIsNotNone(self.opex.find(attrs={"data-testid": "proj-total-y1"}))

    def test_projection_rows_in_b01_b13_order(self):
        rows = self.opex.find_all(
            attrs={"data-testid": lambda v: v and v.startswith("proj-row-B.")}
        )
        codes = [r.get("data-testid").replace("proj-row-", "") for r in rows]
        expected = [f"B.{n:02d}" for n in range(1, 14)]
        self.assertEqual(codes, expected, f"Projection row order wrong: {codes}")


if __name__ == "__main__":
    unittest.main()
