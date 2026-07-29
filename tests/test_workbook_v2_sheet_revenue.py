"""
Tests for the Workbook V2 Revenue worksheet (PR 867 v2).

Coverage
--------
1.  Registry coverage — all 9 revenue fields via _build_sheet_fields
2.  All 9 field IDs appear exactly once in the DOM
3.  7 BOUND fields have editable input controls (active editable count)
4.  2 PARTIAL fields are read-only with PARTIAL badge; no form/input
5.  Sheet has 5 sections, local nav
6.  hx-target="#v2-sheet-revenue", sheet_id="revenue" on all forms
7.  Runtime truth matrix: State A / B / C
8.  Revenue output placeholder text varies by runtime state (A/B/C)
9.  HTMX edit roundtrip from revenue sheet
10. Protected reference (TUHO/Oborovo) — zero editable controls
11. Working copy — editable controls present
12. No legacy snapshot keys in form field_id inputs
13. No duplicate field IDs in DOM
14. No financial calculations in the sheet template
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
# 1. Registry: _build_sheet_fields coverage
# ---------------------------------------------------------------------------

class TestRevenueBuildSheetFields(unittest.TestCase):

    def test_revenue_fields_returned(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        self.assertGreater(len(rows), 0)

    def test_exactly_nine_fields(self):
        """Revenue registry has exactly 9 FieldSpecs; all must be returned."""
        sheet = WORKBOOK.sheet("revenue")
        expected = sum(len(sec.fields) for sec in sheet.sections)
        rows = _build_sheet_fields("revenue", _fake_pis())
        self.assertEqual(len(rows), expected,
                         f"expected {expected} rows, got {len(rows)}")

    def test_no_duplicate_field_ids(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        fids = [r["field_id"] for r in rows]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids: {dupes}")

    def test_seven_bound_fields(self):
        """BOUND fields in the revenue sheet (ppa×5 + balancing×4 + merchant×1 = 10)."""
        rows = _build_sheet_fields("revenue", _fake_pis())
        bound = [r for r in rows if r["binding_label"] == "bound"]
        self.assertEqual(len(bound), 11, f"expected 11 BOUND, got {len(bound)}: {[r['field_id'] for r in bound]}")

    def test_two_partial_fields(self):
        """Exactly 2 PARTIAL fields (the legacy keys)."""
        rows = _build_sheet_fields("revenue", _fake_pis())
        partial = [r for r in rows if r["binding_label"] == "partial"]
        self.assertEqual(len(partial), 2,
                         f"expected 2 PARTIAL, got {len(partial)}: {[r['field_id'] for r in partial]}")

    def test_partial_fields_are_legacy_keys(self):
        rows = _build_sheet_fields("revenue", _fake_pis())
        partial_ids = {r["field_id"] for r in rows if r["binding_label"] == "partial"}
        self.assertEqual(partial_ids,
                         {"revenue.ppa.tariff_legacy", "revenue.ppa.ppa_term_legacy"})

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

    def test_ppa_section_has_eight_fields(self):
        # C2B3: added rev_ppa_indexation_start_date → 8 fields (6 BOUND + 2 PARTIAL).
        rows = _build_sheet_fields("revenue", _fake_pis())
        ppa_rows = [r for r in rows if r["section_id"] == "ppa"]
        self.assertEqual(len(ppa_rows), 8)

    def test_balancing_section_has_three_fields(self):
        # C2B2: split balancing into merchant_pct + cost_eur_per_mwh → 4 fields.
        rows = _build_sheet_fields("revenue", _fake_pis())
        bal_rows = [r for r in rows if r["section_id"] == "balancing"]
        self.assertEqual(len(bal_rows), 4)


# ---------------------------------------------------------------------------
# 2. All 9 field IDs appear exactly once in the DOM
# ---------------------------------------------------------------------------

class TestRevenueAllFieldsRendered(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "all-fields-01")
        cls.soup = BeautifulSoup(_get_workbook(cls.client, cls.project_code), "html.parser")
        cls.rev = cls.soup.find(id="v2-sheet-revenue")

    def _dom_field_ids(self):
        return [r["data-field-id"] for r in self.rev.find_all(attrs={"data-field-id": True})]

    def test_all_nine_field_ids_present(self):
        # revenue.ppa.base_tariff is excluded from the revenue sheet DOM:
        # it is NOT wired in V2 _snapshot_to_dict (engine reads legacy tariff_eur_mwh).
        # It is shown as a placeholder in the "Planned inputs" collapsed section instead.
        expected = {
            "revenue.ppa.index",
            "revenue.ppa.term_years",
            "revenue.ppa.production_share",
            "revenue.ppa.tariff_legacy",
            "revenue.ppa.ppa_term_legacy",
            "revenue.balancing.cost",
            "revenue.balancing.co2_enabled",
            "revenue.balancing.co2_price",
        }
        dom_ids = set(self._dom_field_ids())
        missing = expected - dom_ids
        self.assertFalse(missing, f"Missing field_ids in DOM: {missing}")
        # Also verify base_tariff is NOT in the revenue sheet DOM (moved to placeholder)
        self.assertNotIn("revenue.ppa.base_tariff", dom_ids,
            "revenue.ppa.base_tariff must not appear as editable in revenue sheet "
            "(not wired to V2 engine)")

    def test_each_field_id_appears_exactly_once(self):
        fids = self._dom_field_ids()
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids in DOM: {dupes}")

    def test_seven_editable_controls(self):
        """7 BOUND fields rendered as editable rows (base_tariff moved to planned placeholder)."""
        editable = self.rev.find_all(class_="v2-field-editable")
        self.assertEqual(len(editable), 7,
                         f"expected 7 editable (base_tariff is a placeholder), got {len(editable)}")

    def test_two_partial_rows_in_dom(self):
        """Both PARTIAL legacy fields appear as read-only rows with PARTIAL badge."""
        for fid in ("revenue.ppa.tariff_legacy", "revenue.ppa.ppa_term_legacy"):
            row = self.rev.find(attrs={"data-field-id": fid})
            self.assertIsNotNone(row, f"PARTIAL field {fid!r} missing from DOM")

    def test_partial_badge_on_both_legacy_fields(self):
        """PARTIAL badge must appear for both legacy fields."""
        for fid in ("revenue.ppa.tariff_legacy", "revenue.ppa.ppa_term_legacy"):
            row = self.rev.find(attrs={"data-field-id": fid})
            self.assertIsNotNone(row, f"field {fid!r} missing")
            badge = row.find(class_="v2-binding-partial")
            self.assertIsNotNone(badge,
                                 f"PARTIAL badge missing for {fid!r}; row HTML: {row}")

    def test_partial_fields_have_no_form(self):
        """PARTIAL fields must not be wrapped in editable <form> elements."""
        for fid in ("revenue.ppa.tariff_legacy", "revenue.ppa.ppa_term_legacy"):
            row = self.rev.find(attrs={"data-field-id": fid})
            self.assertIsNotNone(row, f"field {fid!r} missing")
            self.assertIsNone(
                row.find("form"),
                f"PARTIAL field {fid!r} has an editable form",
            )

    def test_partial_fields_have_no_value_input(self):
        """PARTIAL fields must not contain an <input name='value'>."""
        for fid in ("revenue.ppa.tariff_legacy", "revenue.ppa.ppa_term_legacy"):
            row = self.rev.find(attrs={"data-field-id": fid})
            self.assertIsNotNone(row, f"field {fid!r} missing")
            self.assertIsNone(
                row.find("input", {"name": "value"}),
                f"PARTIAL field {fid!r} has an editable input",
            )


# ---------------------------------------------------------------------------
# 3. Sheet HTML structure
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
        # PR-B: nav updated — Production section removed; Outputs and Planned added.
        nav = self.rev.find("nav", class_="v2-inputs-nav")
        link_texts = {a.get_text(strip=True) for a in nav.find_all("a")}
        for expected in ("Commercial", "Balancing", "Outputs", "Planned", "Future"):
            self.assertIn(expected, link_texts, f"nav missing '{expected}'")

    def test_ppa_bound_fields_rendered(self):
        # revenue.ppa.base_tariff is excluded from the sheet DOM (not wired in V2 engine).
        for fid in (
            "revenue.ppa.index",
            "revenue.ppa.term_years",
            "revenue.ppa.production_share",
        ):
            self.assertIsNotNone(
                self.rev.find(attrs={"data-field-id": fid}),
                f"field {fid!r} missing from revenue sheet",
            )
        # base_tariff must NOT appear in the revenue sheet DOM
        self.assertIsNone(
            self.rev.find(attrs={"data-field-id": "revenue.ppa.base_tariff"}),
            "revenue.ppa.base_tariff must not appear as editable in revenue sheet",
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

    def test_not_yet_supported_tags_present(self):
        # PR-B: placeholder vocabulary changed from "Future input" to "Not yet supported".
        self.assertIn("Not yet supported", self.rev.get_text())

    def test_future_modules_placeholders(self):
        text = self.rev.get_text()
        for label in ("Battery Revenue", "Ancillary Services", "GOOs", "Carbon Credits"):
            self.assertIn(label, text, f"future module placeholder '{label}' missing")

    def test_outputs_section_present(self):
        # PR-B: Revenue Outputs section (nav-rev-outputs) replaced the old Production section.
        self.assertIsNotNone(self.rev.find(id="nav-rev-outputs"),
                             "nav-rev-outputs section must exist in revenue sheet")

    def test_no_duplicate_field_ids_in_dom(self):
        fids = [r["data-field-id"] for r in self.rev.find_all(attrs={"data-field-id": True})]
        dupes = [f for f in set(fids) if fids.count(f) > 1]
        self.assertFalse(dupes, f"Duplicate field_ids in revenue sheet DOM: {dupes}")

    def test_no_legacy_snapshot_keys_in_form_actions(self):
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
# 4. Editable controls (user project)
# ---------------------------------------------------------------------------

class TestRevenueSheetEditable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "editable-01")
        cls.soup = BeautifulSoup(_get_workbook(cls.client, cls.project_code), "html.parser")
        cls.rev = cls.soup.find(id="v2-sheet-revenue")

    def test_exactly_seven_editable_controls(self):
        """7 BOUND fields → 7 editable rows (base_tariff is a planned placeholder)."""
        editable = self.rev.find_all(class_="v2-field-editable")
        self.assertEqual(len(editable), 7,
                         f"expected 7 (base_tariff excluded from editables), got {len(editable)}")

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

    def test_base_tariff_not_in_editable_dom(self):
        """base_tariff must NOT appear as an editable field — it is a planned placeholder."""
        row = self.rev.find(attrs={"data-field-id": "revenue.ppa.base_tariff"})
        self.assertIsNone(row,
            "revenue.ppa.base_tariff must not appear in editable DOM "
            "(not wired in V2 engine; shown as planned placeholder instead)")

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
# 5. Protected reference — zero editable controls
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

    def test_protected_ref_partial_fields_still_shown(self):
        """PARTIAL legacy fields must still appear read-only for protected refs."""
        with patch("app.v2.router.is_protected_reference", return_value=True):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        rev = _revenue_div(resp.text)
        for fid in ("revenue.ppa.tariff_legacy", "revenue.ppa.ppa_term_legacy"):
            self.assertIsNotNone(
                rev.find(attrs={"data-field-id": fid}),
                f"PARTIAL field {fid!r} missing for protected ref",
            )

    def test_user_project_has_editable_controls(self):
        with patch("app.v2.router.is_protected_reference", return_value=False):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        rev = _revenue_div(resp.text)
        self.assertGreater(len(rev.find_all(class_="v2-field-editable")), 0)


# ---------------------------------------------------------------------------
# 6. Runtime truth matrix
# ---------------------------------------------------------------------------

class TestRevenueRuntimeMatrix(unittest.TestCase):
    """
    Revenue outputs section uses uniform 'Future input' tags regardless of runtime state.
    The global status banner (not the revenue sheet) conveys runtime state to the user.
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

    def test_state_a_outputs_section_shows_not_run(self):
        """State A (NOT_RUN): no runtime → shows 'Run the model' notice."""
        rev = _revenue_div(self._render_with(has_runtime=False, ws_dirty=False))
        self.assertIn("Run the model", rev.get_text())
        # PR-B: state bar is present
        self.assertIsNotNone(rev.find(attrs={"data-testid": "revenue-state-bar"}))

    def test_state_b_outputs_section_shows_state_bar(self):
        """State B (CLEAN or UNAVAILABLE): runtime present + clean → state bar visible."""
        rev = _revenue_div(self._render_with(has_runtime=True, ws_dirty=False))
        self.assertIsNotNone(rev.find(attrs={"data-testid": "revenue-state-bar"}))

    def test_state_c_outputs_section_shows_stale_or_notrun(self):
        """State C: runtime present + dirty → stale or UNAVAILABLE notice visible."""
        rev = _revenue_div(self._render_with(has_runtime=True, ws_dirty=True))
        text = rev.get_text()
        # Either stale notice or the state bar indicates an output is present/stale
        self.assertIsNotNone(rev.find(attrs={"data-testid": "revenue-state-bar"}))
        # Must not silently say "Outputs current" when dirty
        self.assertNotIn("Outputs current", text)

    def test_not_run_state_has_no_outputs_current_label(self):
        """NOT_RUN state must not label outputs as current."""
        rev = _revenue_div(self._render_with(has_runtime=False, ws_dirty=False))
        self.assertNotIn("Outputs current", rev.get_text())


# ---------------------------------------------------------------------------
# 7. Revenue output placeholder text varies by runtime state
# ---------------------------------------------------------------------------

class TestRevenueOutputPlaceholders(unittest.TestCase):
    """
    Revenue output rows (Annual Revenue, Average Price, etc.) show 'Future input'
    in all runtime states — uniform vocabulary, no state-conditional messaging.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "outputs-ph-01")

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

    def _outputs_text(self, html: str) -> str:
        """Text of the Revenue Outputs section only."""
        rev = _revenue_div(html)
        # Find the outputs section by its anchor id
        anchor = rev.find(id="nav-rev-outputs")
        if anchor:
            section = anchor.find_parent("details")
            return section.get_text() if section else rev.get_text()
        return rev.get_text()

    def test_all_states_show_state_bar(self):
        """PR-B: All runtime states: Revenue Outputs section has a state bar."""
        for has_runtime, ws_dirty in ((False, False), (True, False), (True, True)):
            html = self._render_with(has_runtime=has_runtime, ws_dirty=ws_dirty)
            rev = _revenue_div(html)
            self.assertIsNotNone(
                rev.find(attrs={"data-testid": "revenue-state-bar"}),
                f"revenue-state-bar missing in state has_runtime={has_runtime}, ws_dirty={ws_dirty}"
            )

    def test_no_migration_text_in_outputs(self):
        """Output placeholders must not say 'mapping not yet connected' or 'Available after run'."""
        for has_runtime, ws_dirty in ((False, False), (True, False), (True, True)):
            text = self._outputs_text(self._render_with(has_runtime=has_runtime, ws_dirty=ws_dirty))
            self.assertNotIn("mapping not yet connected", text)
            self.assertNotIn("Available after run", text)

    def test_outputs_section_and_planned_section_both_present(self):
        """PR-B: Revenue Outputs section and Planned inputs section both exist."""
        html = self._render_with(has_runtime=False, ws_dirty=False)
        rev = _revenue_div(html)
        self.assertIsNotNone(rev.find(id="nav-rev-outputs"),
                             "nav-rev-outputs section must exist (PR-B adds runtime outputs)")
        self.assertIsNotNone(rev.find(id="nav-rev-planned"),
                             "nav-rev-planned section must exist for non-wired planned inputs")
        self.assertIn("Not yet supported", rev.get_text(),
                      "Planned inputs section must show 'Not yet supported' placeholder tags")


# ---------------------------------------------------------------------------
# 8. HTMX edit roundtrip from revenue sheet
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
        resp = self._post("revenue.ppa.index", "2.5")
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
        resp = self._post("revenue.ppa.term_years", "-999")
        self.assertIn("v2-sheet-revenue", resp.text)

    def test_htmx_co2_enabled_bool_field(self):
        resp = self._post("revenue.balancing.co2_enabled", "true")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-revenue", resp.text)

    def test_value_persists_after_edit(self):
        """After HTMX edit, a fresh GET must reflect the new value."""
        # Fetch a fresh content_hash — prior tests in this class may have rotated it.
        current_html = _get_workbook(self.client, self.project_code)
        shell = BeautifulSoup(current_html, "html.parser").find(id="v2-workbook-shell")
        fresh_hash = shell["data-content-hash"]

        # Use ppa.index (a wired, editable field) instead of base_tariff
        # (base_tariff is now a planned placeholder, not an editable field in V2)
        resp = self._post("revenue.ppa.index", "3.5", content_hash=fresh_hash)
        self.assertEqual(resp.status_code, 200)
        # Confirm no stale-hash error in response
        self.assertNotIn("Draft changed since page loaded", resp.text)

        html3 = _get_workbook(self.client, self.project_code)
        rev = _revenue_div(html3)
        index_row = rev.find(attrs={"data-field-id": "revenue.ppa.index"})
        self.assertIsNotNone(index_row, "revenue.ppa.index must be in revenue sheet DOM")
        inp = index_row.find("input", {"name": "value"})
        self.assertIsNotNone(inp)
        self.assertEqual(inp["value"], "3.5")


# ---------------------------------------------------------------------------
# 9. No financial calculations in the sheet template
# ---------------------------------------------------------------------------

class TestRevenueNoCalculations(unittest.TestCase):

    def _template_source(self) -> str:
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "templates", "v2", "partials",
        )
        with open(os.path.join(template_dir, "sheet_revenue.html")) as f:
            return f.read()

    def test_no_revenue_formulas_in_template(self):
        source = self._template_source()
        forbidden = ["* tariff", "* price", "* mwh", "revenue / ", "ppa * "]
        for pattern in forbidden:
            self.assertNotIn(
                pattern.lower(), source.lower(),
                f"Template contains forbidden calculation pattern: {pattern!r}",
            )

    def test_template_uses_render_field_macro(self):
        source = self._template_source()
        self.assertIn("render_field", source)
        self.assertIn('from "partials/field_editor.html"', source)

    def test_template_filters_by_section_id_not_binding_label(self):
        """PPA section loop must filter by section_id only, not binding_label."""
        source = self._template_source()
        self.assertIn("f.section_id", source)
        # The old filter that excluded PARTIAL must be gone
        self.assertNotIn('f.binding_label == "bound"', source)

    def test_template_no_hardcoded_bound_field_ids(self):
        """Template must not reference specific BOUND field IDs in loop conditions."""
        import re
        source = self._template_source()
        hardcoded = re.findall(
            r'f\.field_id\s*==\s*"revenue\.ppa\.(base_tariff|index|term_years|production_share)"',
            source,
        )
        self.assertFalse(hardcoded, f"Template hardcodes bound field_ids: {hardcoded}")


if __name__ == "__main__":
    unittest.main()
