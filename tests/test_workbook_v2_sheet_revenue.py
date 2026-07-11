"""
Tests for the Workbook V2 Revenue worksheet (PR 867).

Coverage
--------
1.  Registry coverage — every revenue field accessible via _build_sheet_fields
2.  BOUND fields have editable input controls
3.  PARTIAL fields (legacy keys) are never editable
4.  Sheet has 5 sections, local nav
5.  hx-target="#v2-sheet-revenue", sheet_id="revenue" on all forms
6.  Runtime truth matrix: State A / B / C
7.  HTMX edit roundtrip from revenue sheet
8.  Protected reference (TUHO/Oborovo) — zero editable controls
9.  Working copy — editable controls present
10. No legacy snapshot keys in form action targets
11. No duplicate field IDs in DOM
12. Placeholder text for unmigrated sections
"""
from __future__ import annotations

import os
import unittest
import urllib.parse
from unittest.mock import patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-revenue-tests")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.v2.router import _build_sheet_fields  # noqa: E402
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
            "project_name": f"Revenue V2 Test {suffix}",
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


def _revenue_div(html: str):
    return BeautifulSoup(html, "html.parser").find(id="v2-sheet-revenue")


def _fake_pis():
    from unittest.mock import MagicMock
    m = MagicMock()
    m.get = lambda fid: None
    return m


# ---------------------------------------------------------------------------
# 1. Registry coverage
# ---------------------------------------------------------------------------

class TestRevenueBuildSheetFields(unittest.TestCase):

    def test_revenue_fields_returned(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        self.assertGreater(len(rows), 0)

    def test_all_registry_fields_present(self):
        """_build_sheet_fields returns one row per FieldSpec in the revenue sheet."""
        sheet = WORKBOOK.sheet("revenue")
        expected = sum(len(sec.fields) for sec in sheet.sections)
        rows = _build_sheet_fields("revenue", _fake_pis())
        self.assertEqual(len(rows), expected)

    def test_no_duplicate_field_ids(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        fids = [r["field_id"] for r in rows]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids: {dupes}")

    def test_bound_fields_have_correct_binding_label(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        bound_ids = {
            f.field_id
            for sec in WORKBOOK.sheet("revenue").sections
            for f in sec.fields
            if f.binding_status == BindingStatus.BOUND
        }
        for row in rows:
            if row["field_id"] in bound_ids:
                self.assertEqual(row["binding_label"], "bound",
                                 f"{row['field_id']} should be 'bound'")

    def test_partial_legacy_fields_have_partial_binding_label(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        partial_ids = {"revenue.ppa.tariff_legacy", "revenue.ppa.ppa_term_legacy"}
        for row in rows:
            if row["field_id"] in partial_ids:
                self.assertEqual(row["binding_label"], "partial",
                                 f"{row['field_id']} should be 'partial'")

    def test_required_dict_keys_present(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        required_keys = {
            "field_id", "label", "unit", "field_type", "binding_label",
            "options", "section_id", "value", "required",
            "min_value", "max_value", "step", "help_text",
        }
        for row in rows:
            missing = required_keys - row.keys()
            self.assertFalse(missing, f"Row {row['field_id']} missing keys: {missing}")

    def test_ppa_section_fields_accessible(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        ppa_rows = [r for r in rows if r["section_id"] == "ppa"]
        self.assertGreater(len(ppa_rows), 0)

    def test_balancing_section_fields_accessible(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        bal_rows = [r for r in rows if r["section_id"] == "balancing"]
        self.assertGreater(len(bal_rows), 0)


# ---------------------------------------------------------------------------
# 2. Sheet HTML structure
# ---------------------------------------------------------------------------

class TestRevenueSheetHtml(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "html-01")
        cls.soup = BeautifulSoup(_get_workbook(cls.client, cls.project_code), "html.parser")
        cls.rev = cls.soup.find(id="v2-sheet-revenue")

    def test_revenue_sheet_container_present(self):
        self.assertIsNotNone(self.rev)

    def test_five_collapsible_sections(self):
        sections = self.rev.find_all("details", class_="v2-inputs-section")
        self.assertEqual(len(sections), 5, f"expected 5, got {len(sections)}")

    def test_local_nav_present(self):
        nav = self.rev.find("nav", class_="v2-inputs-nav")
        self.assertIsNotNone(nav)

    def test_local_nav_links(self):
        nav = self.rev.find("nav", class_="v2-inputs-nav")
        link_texts = {a.get_text(strip=True) for a in nav.find_all("a")}
        for expected in ("Commercial", "Balancing", "Production", "Outputs", "Future"):
            self.assertIn(expected, link_texts, f"nav missing '{expected}'")

    def test_ppa_bound_fields_rendered(self):
        """base_tariff, index, term_years, production_share must all appear."""
        for fid in (
            "revenue.ppa.base_tariff",
            "revenue.ppa.index",
            "revenue.ppa.term_years",
            "revenue.ppa.production_share",
        ):
            self.assertIsNotNone(
                self.rev.find(attrs={"data-field-id": fid}),
                f"field {fid!r} missing from revenue sheet",
            )

    def test_legacy_partial_fields_not_editable(self):
        """tariff_legacy and ppa_term_legacy must NOT appear as editable input forms."""
        for fid in ("revenue.ppa.tariff_legacy", "revenue.ppa.ppa_term_legacy"):
            row = self.rev.find(attrs={"data-field-id": fid})
            if row is not None:
                # Field may render read-only; it must not have an editable input
                self.assertIsNone(
                    row.find("input", {"name": "value"}),
                    f"legacy field {fid!r} rendered editable",
                )

    def test_balancing_fields_rendered(self):
        for fid in (
            "revenue.balancing.cost",
            "revenue.balancing.co2_enabled",
            "revenue.balancing.co2_price",
        ):
            self.assertIsNotNone(
                self.rev.find(attrs={"data-field-id": fid}),
                f"field {fid!r} missing from revenue sheet",
            )

    def test_planned_future_migration_placeholder(self):
        self.assertIn("Planned in future migration", self.rev.get_text())

    def test_future_modules_placeholders(self):
        text = self.rev.get_text()
        for label in ("Battery Revenue", "Ancillary Services", "GOOs", "Carbon Credits"):
            self.assertIn(label, text, f"future module placeholder '{label}' missing")

    def test_production_section_placeholders(self):
        text = self.rev.get_text()
        for label in ("Annual Generation", "Net Production", "Curtailment"):
            self.assertIn(label, text)

    def test_no_duplicate_field_ids_in_dom(self):
        fids = [r["data-field-id"] for r in self.rev.find_all(attrs={"data-field-id": True})]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids in revenue sheet DOM: {dupes}")

    def test_no_legacy_snapshot_keys_in_form_actions(self):
        """Form hidden inputs must not expose raw snapshot keys (e.g. tariff_eur_mwh)."""
        legacy_snapshot_keys = {"tariff_eur_mwh", "ppa_term_years"}
        for form in self.rev.find_all("form", class_="v2-field-form"):
            fid_input = form.find("input", {"name": "field_id"})
            if fid_input:
                self.assertNotIn(
                    fid_input.get("value", ""),
                    legacy_snapshot_keys,
                    f"Form exposes legacy snapshot key: {fid_input['value']!r}",
                )


# ---------------------------------------------------------------------------
# 3. Editable controls (user project)
# ---------------------------------------------------------------------------

class TestRevenueSheetEditable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "editable-01")
        cls.soup = BeautifulSoup(_get_workbook(cls.client, cls.project_code), "html.parser")
        cls.rev = cls.soup.find(id="v2-sheet-revenue")

    def test_bound_fields_have_editable_controls(self):
        editable = self.rev.find_all(class_="v2-field-editable")
        self.assertGreater(len(editable), 0)

    def test_forms_target_revenue_sheet(self):
        forms = self.rev.find_all("form", class_="v2-field-form")
        self.assertGreater(len(forms), 0)
        for form in forms:
            self.assertEqual(
                form.get("hx-target"), "#v2-sheet-revenue",
                f"wrong hx-target on form: {form.get('hx-target')!r}",
            )

    def test_forms_carry_sheet_id_revenue(self):
        for form in self.rev.find_all("form", class_="v2-field-form"):
            sid = form.find("input", {"name": "sheet_id"})
            self.assertIsNotNone(sid, "form missing sheet_id hidden input")
            self.assertEqual(sid["value"], "revenue")

    def test_base_tariff_has_float_input(self):
        row = self.rev.find(attrs={"data-field-id": "revenue.ppa.base_tariff"})
        self.assertIsNotNone(row)
        self.assertIsNotNone(row.find("input", {"name": "value"}))

    def test_base_tariff_step_from_registry(self):
        """base_tariff has decimals=2 → step="0.01"."""
        row = self.rev.find(attrs={"data-field-id": "revenue.ppa.base_tariff"})
        inp = row.find("input", {"name": "value"})
        self.assertIsNotNone(inp)
        self.assertEqual(inp.get("step"), "0.01")

    def test_term_years_step_is_1(self):
        """term_years is YEARS type → step="1"."""
        row = self.rev.find(attrs={"data-field-id": "revenue.ppa.term_years"})
        inp = row.find("input", {"name": "value"})
        self.assertIsNotNone(inp)
        self.assertEqual(inp.get("step"), "1")

    def test_co2_enabled_is_select(self):
        """co2_enabled is BOOL type → rendered as <select>."""
        row = self.rev.find(attrs={"data-field-id": "revenue.balancing.co2_enabled"})
        self.assertIsNotNone(row)
        self.assertIsNotNone(row.find("select"))


# ---------------------------------------------------------------------------
# 4. Protected reference — zero editable controls
# ---------------------------------------------------------------------------

class TestRevenueSheetProtectedRef(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "prot-01")

    def test_protected_ref_zero_editable(self):
        with patch("app.v2.router.is_protected_reference", return_value=True):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        rev = _revenue_div(resp.text)
        self.assertIsNotNone(rev)
        self.assertEqual(len(rev.find_all(class_="v2-field-editable")), 0)

    def test_protected_ref_shows_copy_cta(self):
        with patch("app.v2.router.is_protected_reference", return_value=True):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        rev = _revenue_div(resp.text)
        self.assertIsNotNone(rev.find(class_="v2-protected-notice"))

    def test_user_project_has_editable_controls(self):
        with patch("app.v2.router.is_protected_reference", return_value=False):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        rev = _revenue_div(resp.text)
        self.assertGreater(len(rev.find_all(class_="v2-field-editable")), 0)


# ---------------------------------------------------------------------------
# 5. Runtime truth matrix
# ---------------------------------------------------------------------------

class TestRevenueRuntimeMatrix(unittest.TestCase):
    """
    State A — no RuntimeResult:          "Not yet run"
    State B — RuntimeResult + clean:     "Outputs current"
    State C — RuntimeResult + dirty:     "Previous run available — stale for current draft"

    "Outputs current" must never appear while the draft is dirty.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "runtime-rev-01")

    def _render_with(self, *, has_runtime: bool, ws_dirty: bool) -> str:
        import dataclasses
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

    def test_state_a_not_yet_run(self):
        """State A: no RuntimeResult → 'Not yet run'."""
        rev = _revenue_div(self._render_with(has_runtime=False, ws_dirty=False))
        self.assertIn("Not yet run", rev.get_text())
        self.assertNotIn("Outputs current", rev.get_text())
        self.assertNotIn("stale", rev.get_text())

    def test_state_b_outputs_current(self):
        """State B: RuntimeResult + clean draft → 'Outputs current'."""
        rev = _revenue_div(self._render_with(has_runtime=True, ws_dirty=False))
        self.assertIn("Outputs current", rev.get_text())
        self.assertNotIn("Not yet run", rev.get_text())
        self.assertNotIn("stale", rev.get_text())

    def test_state_c_stale(self):
        """State C: RuntimeResult + dirty → stale message, never 'Outputs current'."""
        rev = _revenue_div(self._render_with(has_runtime=True, ws_dirty=True))
        self.assertIn("stale", rev.get_text())
        self.assertNotIn("Outputs current", rev.get_text())
        self.assertNotIn("Not yet run", rev.get_text())

    def test_state_c_run_required_yes(self):
        """State C: Run Required = Yes when dirty."""
        rev = _revenue_div(self._render_with(has_runtime=True, ws_dirty=True))
        text = rev.get_text()
        idx = text.find("Run Required")
        self.assertGreater(idx, -1)
        self.assertIn("Yes", text[idx:idx + 40])

    def test_state_b_run_required_no(self):
        """State B: Run Required = No when clean."""
        rev = _revenue_div(self._render_with(has_runtime=True, ws_dirty=False))
        text = rev.get_text()
        idx = text.find("Run Required")
        self.assertGreater(idx, -1)
        self.assertNotIn("Yes", text[idx:idx + 40])

    def test_outputs_current_never_when_dirty(self):
        """Regression: dirty draft must never show 'Outputs current'."""
        for has_runtime in (True, False):
            rev = _revenue_div(self._render_with(has_runtime=has_runtime, ws_dirty=True))
            self.assertNotIn(
                "Outputs current", rev.get_text(),
                f"'Outputs current' shown with has_runtime={has_runtime}, ws_dirty=True",
            )


# ---------------------------------------------------------------------------
# 6. HTMX edit roundtrip from revenue sheet
# ---------------------------------------------------------------------------

class TestRevenueHtmxEdit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "htmx-rev-01")
        html = _get_workbook(cls.client, cls.project_code)
        shell = BeautifulSoup(html, "html.parser").find(id="v2-workbook-shell")
        cls.content_hash = shell["data-content-hash"]
        cls.workbook_version = shell["data-workbook-version"]

    def _post(self, field_id, value, sheet_id="revenue", content_hash=None):
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

    def test_htmx_success_returns_revenue_sheet(self):
        resp = self._post("revenue.ppa.base_tariff", "70.0")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-revenue", resp.text)

    def test_htmx_success_returns_oob_banner(self):
        resp = self._post("revenue.ppa.index", "2.0")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('hx-swap-oob="true"', resp.text)
        self.assertIn("v2-status-banner", resp.text)

    def test_htmx_revenue_edit_not_project_setup_sheet(self):
        resp = self._post("revenue.ppa.term_years", "12")
        self.assertNotIn("v2-sheet-project-setup", resp.text)

    def test_htmx_revenue_edit_not_inputs_sheet(self):
        resp = self._post("revenue.ppa.production_share", "90.0")
        self.assertNotIn("v2-sheet-inputs", resp.text)

    def test_htmx_project_setup_still_works(self):
        resp = self._post("project_setup.technical.horizon_years", "25",
                          sheet_id="project_setup")
        self.assertIn("v2-sheet-project-setup", resp.text)

    def test_htmx_inputs_sheet_still_works(self):
        resp = self._post("revenue.balancing.cost", "3.0", sheet_id="inputs")
        self.assertIn("v2-sheet-inputs", resp.text)

    def test_htmx_new_content_hash_after_edit(self):
        resp = self._post("revenue.balancing.co2_price", "55.0")
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        hashes = {i["value"] for i in soup.find_all("input", {"name": "content_hash"})}
        self.assertEqual(len(hashes), 1)
        self.assertNotEqual(next(iter(hashes)), self.content_hash)

    def test_htmx_validation_error_returns_revenue_sheet(self):
        """Min-value violation on base_tariff returns revenue sheet with error."""
        resp = self._post("revenue.ppa.base_tariff", "-999")
        self.assertIn("v2-sheet-revenue", resp.text)

    def test_htmx_co2_enabled_bool_field(self):
        resp = self._post("revenue.balancing.co2_enabled", "true")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-revenue", resp.text)


# ---------------------------------------------------------------------------
# 7. No financial calculations in the sheet template
# ---------------------------------------------------------------------------

class TestRevenueNoCalculations(unittest.TestCase):

    def test_no_revenue_formulas_in_template(self):
        """Template must not contain multiplication/division operators on revenue data."""
        import inspect
        from jinja2 import Environment, FileSystemLoader
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "templates", "v2", "partials",
        )
        with open(os.path.join(template_dir, "sheet_revenue.html")) as f:
            source = f.read()
        # No inline arithmetic on financial variables
        forbidden = ["* tariff", "* price", "* mwh", "revenue / ", "ppa * "]
        for pattern in forbidden:
            self.assertNotIn(
                pattern.lower(), source.lower(),
                f"Template contains forbidden calculation pattern: {pattern!r}",
            )

    def test_template_uses_render_field_macro(self):
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "templates", "v2", "partials",
        )
        with open(os.path.join(template_dir, "sheet_revenue.html")) as f:
            source = f.read()
        self.assertIn("render_field", source)
        self.assertIn('from "partials/field_editor.html"', source)

    def test_template_uses_section_id_not_field_id_filter(self):
        """Template must filter by section_id (registry metadata), not hardcoded field_ids."""
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "templates", "v2", "partials",
        )
        with open(os.path.join(template_dir, "sheet_revenue.html")) as f:
            source = f.read()
        self.assertIn("f.section_id", source)
        # binding_label filter is acceptable (registry-derived)
        # but no hardcoded semantic field ID literals beyond the excluded legacy pair
        import re
        # Must not reference specific BOUND field_ids by ID in template logic
        bound_hardcoded = re.findall(r'f\.field_id\s*==\s*"revenue\.ppa\.(base_tariff|index|term_years|production_share)"', source)
        self.assertFalse(bound_hardcoded, f"Template hardcodes bound field_ids: {bound_hardcoded}")


if __name__ == "__main__":
    unittest.main()
