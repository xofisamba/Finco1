"""
Tests for the V2 Project Setup sheet — read-only projection (PR 6).

This PR renders a read-only view of the project_setup sheet.  No <input>
controls exist; editing deferred to a follow-up PR with save endpoint and
round-trip persistence tests.

Coverage:
1. _build_ps_fields — structure, ordering, field_type, binding_label, value source
2. Field-by-field proof — each project_setup field's value from pis.get(field_id)
3. Read-only contract — no <input> controls, no snapshot key names, binding badges
4. HTTP integration — project_setup sheet rendered in /v2/workbook response
5. FieldType metadata — field_type propagated from registry
6. Binding label contract — BOUND/PARTIAL/DISPLAY_ONLY/TEMPLATE_LOCKED mapping
7. Template structure — partial exists, no legacy snapshot key refs
8. Source guard — _build_ps_fields contains no hardcoded snapshot keys
"""
from __future__ import annotations

import inspect
import os
import sys
import unittest
import urllib.parse
from unittest.mock import patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-ps-tests")

from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.workbook.input_set import ProjectInputSet  # noqa: E402
from app.workbook.registry import WORKBOOK  # noqa: E402
from app.workbook.service import WorkbookService  # noqa: E402
from app.workbook.specs import BindingStatus  # noqa: E402
from app.v2.router import _build_ps_fields  # noqa: E402


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
            "project_name": f"PS Test {suffix}",
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


def _make_pis(snapshot: dict) -> ProjectInputSet:
    return ProjectInputSet.from_snapshot(snapshot, workbook=WORKBOOK)


# ---------------------------------------------------------------------------
# 1. _build_ps_fields structure
# ---------------------------------------------------------------------------

class TestBuildPsFieldsStructure(unittest.TestCase):

    def setUp(self):
        self.pis = _make_pis({
            "project_name": "Wind Farm A",
            "project_type": "wind_onshore",
            "country_market": "Poland",
            "currency": "EUR",
            "scenario": "Base",
            "capacity_mw": "150",
            "p50_hours": "2400",
            "cod_date": "2028-01-01",
            "construction_months": "20",
            "horizon_years": "25",
        })
        self.rows = _build_ps_fields(self.pis)

    def test_returns_list(self):
        self.assertIsInstance(self.rows, list)

    def test_all_rows_have_required_keys(self):
        required = {
            "field_id", "label", "unit", "field_type", "binding_label",
            "options", "section_id", "section_label", "value",
            # Validation metadata (PR 865)
            "required", "min_value", "max_value", "step", "help_text",
        }
        for row in self.rows:
            missing = required - set(row.keys())
            self.assertFalse(missing, f"missing keys in row for {row.get('field_id')}: {missing}")

    def test_no_editable_key(self):
        """Read-only PR: editable key must not exist (no inputs allowed yet)."""
        for row in self.rows:
            self.assertNotIn("editable", row,
                             f"'editable' key must not appear in read-only projection: {row['field_id']}")

    def test_no_display_only_key(self):
        """Replaced by binding_label; display_only must not appear."""
        for row in self.rows:
            self.assertNotIn("display_only", row)

    def test_covers_all_registry_fields(self):
        sheet = WORKBOOK.sheet("project_setup")
        registry_ids = {f.field_id for s in sheet.sections for f in s.fields}
        output_ids = {r["field_id"] for r in self.rows}
        self.assertEqual(output_ids, registry_ids)

    def test_identity_section_before_technical(self):
        sections_seen = []
        for r in self.rows:
            if not sections_seen or sections_seen[-1] != r["section_id"]:
                sections_seen.append(r["section_id"])
        self.assertEqual(sections_seen, ["identity", "technical"])

    def test_section_label_matches_registry(self):
        sheet = WORKBOOK.sheet("project_setup")
        section_labels = {s.section_id: s.label for s in sheet.sections}
        for row in self.rows:
            self.assertEqual(row["section_label"], section_labels[row["section_id"]])

    def test_field_id_strings_are_semantic(self):
        for row in self.rows:
            self.assertTrue(row["field_id"].startswith("project_setup."),
                            f"unexpected field_id: {row['field_id']}")

    def test_no_snapshot_key_in_field_id(self):
        legacy_keys = {
            "project_name", "project_type", "country_market", "currency",
            "scenario", "capacity_mw", "p50_hours", "capacity_factor",
            "cod_date", "construction_months", "horizon_years",
        }
        for row in self.rows:
            self.assertNotIn(row["field_id"], legacy_keys)


# ---------------------------------------------------------------------------
# 2. Field-by-field value proof
# ---------------------------------------------------------------------------

class TestPsFieldValueSource(unittest.TestCase):

    def _row(self, rows, field_id):
        for r in rows:
            if r["field_id"] == field_id:
                return r
        self.fail(f"{field_id!r} not found")

    def test_project_name_from_pis(self):
        pis = _make_pis({"project_name": "My Wind Farm"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.identity.project_name")
        self.assertEqual(r["value"], pis.get("project_setup.identity.project_name"))
        self.assertEqual(r["value"], "My Wind Farm")

    def test_project_type_from_pis(self):
        pis = _make_pis({"project_type": "solar_pv"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.identity.project_type")
        self.assertEqual(r["value"], pis.get("project_setup.identity.project_type"))
        self.assertEqual(r["value"], "solar_pv")

    def test_country_market_from_pis(self):
        pis = _make_pis({"country_market": "Germany"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.identity.country_market")
        self.assertEqual(r["value"], pis.get("project_setup.identity.country_market"))
        self.assertEqual(r["value"], "Germany")

    def test_currency_from_pis(self):
        pis = _make_pis({"currency": "USD"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.identity.currency")
        self.assertEqual(r["value"], pis.get("project_setup.identity.currency"))
        self.assertEqual(r["value"], "USD")

    def test_scenario_from_pis(self):
        pis = _make_pis({"scenario": "Upside"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.identity.scenario")
        self.assertEqual(r["value"], pis.get("project_setup.identity.scenario"))
        self.assertEqual(r["value"], "Upside")

    def test_capacity_mw_from_pis(self):
        pis = _make_pis({"capacity_mw": "75.5"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.technical.capacity_mw")
        self.assertEqual(r["value"], pis.get("project_setup.technical.capacity_mw"))
        self.assertAlmostEqual(r["value"], 75.5)

    def test_p50_hours_from_pis(self):
        pis = _make_pis({"p50_hours": "2100"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.technical.p50_hours")
        self.assertEqual(r["value"], pis.get("project_setup.technical.p50_hours"))
        self.assertAlmostEqual(r["value"], 2100.0)

    def test_capacity_factor_from_pis(self):
        pis = _make_pis({"capacity_mw": "100", "p50_hours": "2000"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.technical.capacity_factor")
        self.assertEqual(r["value"], pis.get("project_setup.technical.capacity_factor"))

    def test_cod_date_from_pis(self):
        from datetime import date
        pis = _make_pis({"cod_date": "2026-07-01"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.technical.cod_date")
        self.assertEqual(r["value"], pis.get("project_setup.technical.cod_date"))
        self.assertEqual(r["value"], date(2026, 7, 1))

    def test_construction_months_from_pis(self):
        pis = _make_pis({"construction_months": "18"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.technical.construction_months")
        self.assertEqual(r["value"], pis.get("project_setup.technical.construction_months"))
        self.assertEqual(r["value"], 18)

    def test_horizon_years_from_pis(self):
        pis = _make_pis({"horizon_years": "30"})
        rows = _build_ps_fields(pis)
        r = self._row(rows, "project_setup.technical.horizon_years")
        self.assertEqual(r["value"], pis.get("project_setup.technical.horizon_years"))
        self.assertEqual(r["value"], 30)

    def test_value_changes_when_snapshot_changes(self):
        pis_a = _make_pis({"capacity_mw": "50"})
        pis_b = _make_pis({"capacity_mw": "200"})
        val_a = next(r["value"] for r in _build_ps_fields(pis_a)
                     if r["field_id"] == "project_setup.technical.capacity_mw")
        val_b = next(r["value"] for r in _build_ps_fields(pis_b)
                     if r["field_id"] == "project_setup.technical.capacity_mw")
        self.assertNotEqual(val_a, val_b)
        self.assertAlmostEqual(val_a, 50.0)
        self.assertAlmostEqual(val_b, 200.0)


# ---------------------------------------------------------------------------
# 3. Read-only contract
# ---------------------------------------------------------------------------

class TestReadOnlyContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "readonly")

    def _body(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        return resp.text

    def test_non_bound_fields_have_no_input(self):
        """PARTIAL, DISPLAY_ONLY, TEMPLATE_LOCKED field rows must not contain <input>."""
        from bs4 import BeautifulSoup
        body = self._body()
        soup = BeautifulSoup(body, "html.parser")
        for row in soup.select(".v2-field-readonly"):
            self.assertEqual(
                row.find("input"), None,
                f"Read-only row {row.get('data-field-id')} must not have <input>"
            )

    def test_bound_fields_have_input_elements(self):
        """BOUND field rows must contain an <input> or <select> for editing."""
        from bs4 import BeautifulSoup
        body = self._body()
        soup = BeautifulSoup(body, "html.parser")
        for row in soup.select(".v2-field-editable"):
            has_ctrl = row.find("input", {"name": "value"}) or row.find("select", {"name": "value"})
            self.assertIsNotNone(
                has_ctrl,
                f"Editable row {row.get('data-field-id')} must have an input/select"
            )

    def test_bound_fields_have_form_action(self):
        """BOUND fields render a form posting to /v2/workbook/update."""
        body = self._body()
        self.assertIn('action="/v2/workbook/update"', body)

    def test_no_legacy_snapshot_name_attrs(self):
        """No name="capacity_mw" or similar snapshot key attrs in the body."""
        body = self._body()
        legacy_names = [
            'name="capacity_mw"', 'name="project_name"', 'name="p50_hours"',
            'name="cod_date"', 'name="horizon_years"', 'name="construction_months"',
            'name="country_market"', 'name="currency"', 'name="scenario"',
        ]
        for pat in legacy_names:
            self.assertNotIn(pat, body, f"Legacy snapshot key name found: {pat!r}")

    def test_binding_badges_present(self):
        """binding_label badges render in the HTML."""
        body = self._body()
        self.assertIn("v2-binding-badge", body)

    def test_bound_rows_have_data_binding_bound(self):
        body = self._body()
        self.assertIn('data-binding="bound"', body)

    def test_read_only_class_on_rows(self):
        body = self._body()
        self.assertIn("v2-field-readonly", body)

    def test_data_field_id_on_value_spans(self):
        body = self._body()
        self.assertIn('data-field-id="project_setup.technical.capacity_mw"', body)

    def test_capacity_mw_value_displayed(self):
        """The capacity_mw value from project creation (100) appears as read-only text."""
        body = self._body()
        # Value renders as typed float (100.0) in a <span>
        self.assertIn("100.0", body)


# ---------------------------------------------------------------------------
# 4. FieldType metadata
# ---------------------------------------------------------------------------

class TestFieldTypeMetadata(unittest.TestCase):

    def setUp(self):
        self.pis = _make_pis({})
        self.rows = _build_ps_fields(self.pis)

    def _row(self, field_id):
        for r in self.rows:
            if r["field_id"] == field_id:
                return r
        self.fail(f"{field_id} not found")

    def test_project_name_is_text_type(self):
        self.assertEqual(self._row("project_setup.identity.project_name")["field_type"], "text")

    def test_project_type_is_select_type(self):
        self.assertEqual(self._row("project_setup.identity.project_type")["field_type"], "select")

    def test_capacity_mw_is_mw_type(self):
        self.assertEqual(self._row("project_setup.technical.capacity_mw")["field_type"], "mw")

    def test_p50_hours_is_mwh_type(self):
        self.assertEqual(self._row("project_setup.technical.p50_hours")["field_type"], "mwh")

    def test_cod_date_is_date_type(self):
        self.assertEqual(self._row("project_setup.technical.cod_date")["field_type"], "date")

    def test_construction_months_is_months_type(self):
        self.assertEqual(self._row("project_setup.technical.construction_months")["field_type"], "months")

    def test_horizon_years_is_years_type(self):
        self.assertEqual(self._row("project_setup.technical.horizon_years")["field_type"], "years")

    def test_project_type_options_from_registry(self):
        r = self._row("project_setup.identity.project_type")
        self.assertIn("wind_onshore", r["options"])
        self.assertIn("solar_pv", r["options"])

    def test_currency_options_from_registry(self):
        r = self._row("project_setup.identity.currency")
        self.assertIn("EUR", r["options"])

    def test_non_select_fields_have_empty_options(self):
        for row in self.rows:
            if row["field_type"] != "select":
                self.assertEqual(row["options"], [],
                                 f"{row['field_id']} is not SELECT but has options: {row['options']}")


# ---------------------------------------------------------------------------
# 5. Binding label contract
# ---------------------------------------------------------------------------

class TestBindingLabelContract(unittest.TestCase):

    def setUp(self):
        self.pis = _make_pis({})
        self.rows = {r["field_id"]: r for r in _build_ps_fields(self.pis)}

    def test_bound_fields(self):
        bound = {
            "project_setup.identity.project_name",
            "project_setup.technical.capacity_mw",
            "project_setup.technical.p50_hours",
            "project_setup.technical.cod_date",
            "project_setup.technical.construction_months",
            "project_setup.technical.horizon_years",
        }
        for fid in bound:
            self.assertEqual(self.rows[fid]["binding_label"], "bound",
                             f"{fid} should be 'bound'")

    def test_partial_fields(self):
        partial = {
            "project_setup.identity.country_market",
            "project_setup.identity.currency",
            "project_setup.identity.scenario",
        }
        for fid in partial:
            self.assertEqual(self.rows[fid]["binding_label"], "partial",
                             f"{fid} should be 'partial'")

    def test_display_only_fields(self):
        self.assertEqual(
            self.rows["project_setup.technical.capacity_factor"]["binding_label"],
            "display-only"
        )

    def test_template_locked_fields(self):
        self.assertEqual(
            self.rows["project_setup.identity.project_type"]["binding_label"],
            "template-locked"
        )

    def test_binding_labels_are_valid_values(self):
        valid = {"bound", "partial", "display-only", "template-locked"}
        for row in self.rows.values():
            self.assertIn(row["binding_label"], valid,
                          f"invalid binding_label: {row['binding_label']}")


# ---------------------------------------------------------------------------
# 6. HTTP integration
# ---------------------------------------------------------------------------

class TestV2WorkbookProjectSetupResponse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "psresponse")

    def _get(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        return resp.text

    def test_v2_project_setup_div_present(self):
        self.assertIn('id="v2-sheet-project-setup"', self._get())

    def test_identity_section_present(self):
        self.assertIn('data-section="identity"', self._get())

    def test_technical_section_present(self):
        self.assertIn('data-section="technical"', self._get())

    def test_field_id_attributes_use_semantic_ids(self):
        body = self._get()
        self.assertIn('data-field-id="project_setup.identity.project_name"', body)
        self.assertIn('data-field-id="project_setup.technical.capacity_mw"', body)

    def test_no_legacy_input_name_attrs(self):
        body = self._get()
        self.assertNotIn('name="capacity_mw"', body)
        self.assertNotIn('name="project_name"', body)
        self.assertNotIn('name="p50_hours"', body)

    def test_ps_fields_called_with_projectinputset(self):
        """Router calls _build_ps_fields with a ProjectInputSet instance."""
        sentinel = [{"field_id": "project_setup.identity.project_name",
                     "label": "Project Name", "unit": None, "field_type": "text",
                     "binding_label": "bound", "options": [],
                     "section_id": "identity", "section_label": "Project Identity",
                     "value": "SENTINEL"}]
        with patch("app.v2.router._build_ps_fields", return_value=sentinel) as mock:
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            self.assertEqual(resp.status_code, 200)
            mock.assert_called_once()
            pis_arg = mock.call_args[0][0]
            self.assertIsInstance(pis_arg, ProjectInputSet)


# ---------------------------------------------------------------------------
# 7. Template structure
# ---------------------------------------------------------------------------

class TestV2ProjectSetupTemplateStructure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.partial_path = os.path.join(
            base, "app", "templates", "v2", "partials", "sheet_project_setup.html"
        )

    def test_partial_file_exists(self):
        self.assertTrue(os.path.isfile(self.partial_path))

    def test_sheet_imports_field_editor(self):
        """sheet_project_setup.html must import the render_field macro."""
        with open(self.partial_path) as fh:
            src = fh.read()
        self.assertIn("field_editor.html", src)
        self.assertIn("render_field", src)

    def test_field_editor_partial_exists(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        editor_path = os.path.join(
            base, "app", "templates", "v2", "partials", "field_editor.html"
        )
        self.assertTrue(os.path.isfile(editor_path),
                        "partials/field_editor.html must exist")

    def test_no_legacy_snapshot_key_references(self):
        with open(self.partial_path) as fh:
            src = fh.read()
        for pat in ['name="capacity_mw"', 'name="project_name"', 'name="p50_hours"',
                    'name="cod_date"', 'name="horizon_years"']:
            self.assertNotIn(pat, src, f"Legacy key in template: {pat!r}")

    def test_uses_binding_label(self):
        with open(self.partial_path) as fh:
            src = fh.read()
        self.assertIn("binding_label", src)

    def test_uses_field_type_for_display(self):
        with open(self.partial_path) as fh:
            src = fh.read()
        self.assertIn("field_type", src)

    def test_workbook_html_includes_partial(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_tpl = os.path.join(base, "app", "templates", "v2", "workbook.html")
        with open(main_tpl) as fh:
            src = fh.read()
        self.assertIn("sheet_project_setup.html", src)


# ---------------------------------------------------------------------------
# 8. Field editor — live edit controls for BOUND fields
# ---------------------------------------------------------------------------

class TestFieldEditorControls(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "editor")

    def _body(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        return resp.text

    def test_hidden_content_hash_present(self):
        """BOUND field forms include a hidden content_hash input."""
        body = self._body()
        self.assertIn('name="content_hash"', body)

    def test_hidden_workbook_version_present(self):
        """BOUND field forms include a hidden workbook_version input."""
        body = self._body()
        self.assertIn('name="workbook_version"', body)

    def test_hidden_field_id_present(self):
        """BOUND field forms include a hidden field_id input (not a snapshot key)."""
        body = self._body()
        self.assertIn('name="field_id"', body)
        self.assertIn('value="project_setup.', body)

    def test_hidden_project_present(self):
        """BOUND field forms include a hidden project input."""
        body = self._body()
        self.assertIn('name="project"', body)

    def test_project_name_has_text_input(self):
        """project_name (TEXT, BOUND) renders as type=text input."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body(), "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.identity.project_name"})
        self.assertIsNotNone(row, "project_name row not found")
        inp = row.find("input", {"name": "value", "type": "text"})
        self.assertIsNotNone(inp, "project_name must have type=text input")

    def test_capacity_mw_has_number_input(self):
        """capacity_mw (MW, BOUND) renders as type=number input."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body(), "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.technical.capacity_mw"})
        self.assertIsNotNone(row, "capacity_mw row not found")
        inp = row.find("input", {"name": "value", "type": "number"})
        self.assertIsNotNone(inp, "capacity_mw must have type=number input")

    def test_cod_date_has_date_input(self):
        """cod_date (DATE, BOUND) renders as type=date input."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body(), "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.technical.cod_date"})
        self.assertIsNotNone(row, "cod_date row not found")
        inp = row.find("input", {"name": "value", "type": "date"})
        self.assertIsNotNone(inp, "cod_date must have type=date input")

    def test_non_bound_country_market_has_no_input(self):
        """country_market (PARTIAL) must not have an input — not user-editable."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body(), "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.identity.country_market"})
        self.assertIsNotNone(row, "country_market row not found")
        self.assertIsNone(row.find("input", {"name": "value"}),
                          "country_market must not have an editable input")

    def test_display_only_capacity_factor_has_no_input(self):
        """capacity_factor (DISPLAY_ONLY) must not have an input."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body(), "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.technical.capacity_factor"})
        self.assertIsNotNone(row, "capacity_factor row not found")
        self.assertIsNone(row.find("input", {"name": "value"}),
                          "capacity_factor must not have an editable input")

    def test_template_locked_project_type_has_no_input(self):
        """project_type (TEMPLATE_LOCKED) must not have an input."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body(), "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.identity.project_type"})
        self.assertIsNotNone(row, "project_type row not found")
        self.assertIsNone(row.find("input", {"name": "value"}),
                          "project_type must not have an editable input")

    def test_save_button_present_for_bound_fields(self):
        """A save button renders inside BOUND field forms."""
        body = self._body()
        self.assertIn('class="v2-field-save"', body)

    def test_no_legacy_name_attrs_for_snapshot_keys(self):
        """Inputs must not use snapshot key names (e.g. name='capacity_mw')."""
        body = self._body()
        for legacy in ['name="capacity_mw"', 'name="project_name"', 'name="p50_hours"',
                       'name="cod_date"', 'name="horizon_years"', 'name="construction_months"']:
            self.assertNotIn(legacy, body, f"Legacy snapshot key attr found: {legacy!r}")


# ---------------------------------------------------------------------------
# 9. Registry validation metadata propagated to field dicts
# ---------------------------------------------------------------------------

class TestRegistryValidationMetadata(unittest.TestCase):

    def setUp(self):
        self.rows = {r["field_id"]: r for r in _build_ps_fields(_make_pis({}))}

    def test_capacity_mw_has_min_from_registry(self):
        r = self.rows["project_setup.technical.capacity_mw"]
        self.assertIsNotNone(r["min_value"])
        self.assertAlmostEqual(r["min_value"], 0.1)

    def test_capacity_mw_step_from_decimals(self):
        r = self.rows["project_setup.technical.capacity_mw"]
        # decimals=2 → step="0.01"
        self.assertEqual(r["step"], "0.01")

    def test_p50_hours_step_from_decimals_zero(self):
        r = self.rows["project_setup.technical.p50_hours"]
        # decimals=0 → step="1"
        self.assertEqual(r["step"], "1")

    def test_p50_hours_has_min_from_registry(self):
        r = self.rows["project_setup.technical.p50_hours"]
        self.assertIsNotNone(r["min_value"])
        self.assertAlmostEqual(r["min_value"], 1.0)

    def test_construction_months_has_max_from_registry(self):
        r = self.rows["project_setup.technical.construction_months"]
        self.assertIsNotNone(r["max_value"])
        self.assertEqual(r["max_value"], 120)

    def test_construction_months_has_integer_step(self):
        r = self.rows["project_setup.technical.construction_months"]
        self.assertEqual(r["step"], "1")

    def test_horizon_years_has_max_from_registry(self):
        r = self.rows["project_setup.technical.horizon_years"]
        self.assertIsNotNone(r["max_value"])
        self.assertEqual(r["max_value"], 50)

    def test_horizon_years_has_integer_step(self):
        r = self.rows["project_setup.technical.horizon_years"]
        self.assertEqual(r["step"], "1")

    def test_project_name_is_required(self):
        r = self.rows["project_setup.identity.project_name"]
        self.assertTrue(r["required"])

    def test_select_options_come_from_registry_only(self):
        r = self.rows["project_setup.identity.project_type"]
        spec = WORKBOOK.field("project_setup.identity.project_type")
        self.assertEqual(r["options"], list(spec.options))

    def test_non_select_fields_have_empty_options(self):
        for fid, row in self.rows.items():
            if row["field_type"] != "select":
                self.assertEqual(row["options"], [],
                                 f"{fid} options must be empty for non-SELECT")

    def test_step_rendered_in_number_input(self):
        """step value from registry appears in the rendered input attr."""
        from bs4 import BeautifulSoup
        import os as _os
        client = _authed_client()
        project_code = _create_project(client, "regval")
        resp = client.get(f"/v2/workbook?project={project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.technical.capacity_mw"})
        inp = row.find("input", {"name": "value"}) if row else None
        self.assertIsNotNone(inp, "capacity_mw input not found")
        # step must be "0.01" (decimals=2), not "any"
        self.assertEqual(inp.get("step"), "0.01")

    def test_min_attr_rendered_in_number_input(self):
        """min_value from registry appears in the rendered input attr."""
        from bs4 import BeautifulSoup
        client = _authed_client()
        project_code = _create_project(client, "regval-min")
        resp = client.get(f"/v2/workbook?project={project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.technical.capacity_mw"})
        inp = row.find("input", {"name": "value"}) if row else None
        self.assertIsNotNone(inp)
        self.assertIsNotNone(inp.get("min"), "capacity_mw input must have min attr")

    def test_max_attr_rendered_in_number_input(self):
        """max_value from registry appears in construction_months input."""
        from bs4 import BeautifulSoup
        client = _authed_client()
        project_code = _create_project(client, "regval-max")
        resp = client.get(f"/v2/workbook?project={project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        row = soup.find(attrs={"data-field-id": "project_setup.technical.construction_months"})
        inp = row.find("input", {"name": "value"}) if row else None
        self.assertIsNotNone(inp)
        self.assertIsNotNone(inp.get("max"), "construction_months input must have max attr")


# ---------------------------------------------------------------------------
# 10. Protected reference display — no editable controls for TUHO/Oborovo
# ---------------------------------------------------------------------------

class TestProtectedReferenceDisplay(unittest.TestCase):
    """Protected reference projects (TUHO/Oborovo) must render fully
    read-only with a working-copy CTA, zero editable controls."""

    @classmethod
    def setUpClass(cls):
        from unittest.mock import patch as _patch
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "protected-ref")
        cls._patch = _patch

    def _body_as_protected(self):
        from unittest.mock import patch
        with patch("app.v2.router.is_protected_reference", return_value=True):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            self.assertEqual(resp.status_code, 200, resp.text[:200])
            return resp.text

    def test_no_editable_controls_for_protected_ref(self):
        """Protected reference → zero v2-field-editable rows (in DOM, not CSS)."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body_as_protected(), "html.parser")
        editable = soup.select(".v2-field-editable")
        self.assertEqual(len(editable), 0,
                         f"Protected ref must have no editable rows, found: "
                         f"{[e.get('data-field-id') for e in editable]}")

    def test_all_rows_read_only_for_protected_ref(self):
        """Every field row in a protected reference is read-only."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body_as_protected(), "html.parser")
        editable = soup.select(".v2-field-editable")
        self.assertEqual(len(editable), 0, "No editable rows for protected reference")

    def test_working_copy_cta_shown(self):
        """Protected reference shows 'create a working copy' notice."""
        body = self._body_as_protected()
        self.assertIn("working copy", body.lower())

    def test_working_copy_link_present(self):
        """Working copy link points to /projects/{code}/save-as."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body_as_protected(), "html.parser")
        link = soup.find("a", href=lambda h: h and "save-as" in h)
        self.assertIsNotNone(link, "working-copy link must be present")

    def test_no_form_elements_for_protected_ref(self):
        """No <form> elements should appear for protected reference."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._body_as_protected(), "html.parser")
        forms = soup.select("form.v2-field-form")
        self.assertEqual(len(forms), 0, "No v2-field-form for protected reference")

    def test_post_to_protected_ref_returns_409(self):
        """POST /v2/workbook/update to protected project → 409 (defense in depth)."""
        from unittest.mock import patch
        with patch("app.ui.protected_reference_service.is_protected_reference", return_value=True):
            resp = self.client.post(
                "/v2/workbook/update",
                data={
                    "field_id": "project_setup.identity.project_name",
                    "project": self.project_code,
                    "workbook_version": WORKBOOK.version,
                    "content_hash": "a" * 64,
                    "value": "Hacked",
                },
            )
        self.assertEqual(resp.status_code, 409)

    def test_user_project_has_six_editable_controls(self):
        """Normal (non-protected) user project has exactly 6 BOUND editable rows."""
        from bs4 import BeautifulSoup
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        editable = soup.select(".v2-field-editable")
        self.assertEqual(len(editable), 6,
                         f"Expected 6 editable rows, got {len(editable)}: "
                         f"{[e.get('data-field-id') for e in editable]}")


# ---------------------------------------------------------------------------
# 11. Draft status banner
# ---------------------------------------------------------------------------

class TestDraftStatusBanner(unittest.TestCase):
    """After a successful V2 edit the workspace is dirty and the page
    must display 'Draft changed — Run required'."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "dirty-banner")

    def _get_body(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)
        return resp.text

    def _current_hash(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._get_body(), "html.parser")
        inp = soup.find("input", {"name": "content_hash"})
        return inp["value"] if inp else None

    def test_clean_project_no_dirty_banner(self):
        """Fresh project has no dirty banner."""
        body = self._get_body()
        self.assertNotIn("Draft changed", body)

    def test_dirty_banner_after_edit(self):
        """After a V2 edit the page shows 'Draft changed — Run required'."""
        content_hash = self._current_hash()
        self.assertIsNotNone(content_hash)
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.identity.project_name",
                "project": self.project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": content_hash,
                "value": "Dirty Banner Test",
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 303)
        body = self._get_body()
        self.assertIn("Draft changed", body,
                      "Status banner must show 'Draft changed — Run required' after edit")

    def test_htmx_success_response_contains_dirty_banner(self):
        """HTMX success response includes the dirty status in OOB banner."""
        content_hash = self._current_hash()
        self.assertIsNotNone(content_hash)
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.identity.project_name",
                "project": self.project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": content_hash,
                "value": "HTMX Dirty Banner",
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Draft changed", resp.text,
                      "HTMX response must contain dirty banner")


# ---------------------------------------------------------------------------
# 12. HTMX field edit integration
# ---------------------------------------------------------------------------

class TestHtmxFieldEdit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "htmx-edit")

    def _current_hash(self):
        from bs4 import BeautifulSoup
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        inp = soup.find("input", {"name": "content_hash"})
        return inp["value"] if inp else None

    def test_htmx_success_returns_sheet_html(self):
        """HTMX success → 200 with updated #v2-sheet-project-setup."""
        content_hash = self._current_hash()
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.identity.project_name",
                "project": self.project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": content_hash,
                "value": "HTMX Update Name",
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-project-setup", resp.text)

    def test_htmx_success_contains_oob_status_banner(self):
        """HTMX success response includes the OOB status banner element."""
        content_hash = self._current_hash()
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.identity.project_name",
                "project": self.project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": content_hash,
                "value": "HTMX OOB Test",
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)
        self.assertIn("hx-swap-oob", resp.text)

    def test_htmx_success_new_content_hash_in_forms(self):
        """After HTMX edit, returned sheet contains a different content_hash."""
        from bs4 import BeautifulSoup
        old_hash = self._current_hash()
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.identity.project_name",
                "project": self.project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": old_hash,
                "value": "Hash Change Test",
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        new_hash_inp = soup.find("input", {"name": "content_hash"})
        self.assertIsNotNone(new_hash_inp, "New form must carry content_hash")
        self.assertNotEqual(new_hash_inp.get("value"), old_hash,
                            "content_hash must change after successful edit")

    def test_htmx_forms_carry_hx_attrs(self):
        """BOUND field forms include HTMX attributes."""
        from bs4 import BeautifulSoup
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", {"class": "v2-field-form"})
        self.assertIsNotNone(form, "v2-field-form must exist")
        self.assertEqual(form.get("hx-post"), "/v2/workbook/update")
        self.assertEqual(form.get("hx-target"), "#v2-sheet-project-setup")

    def test_flash_error_shown_after_non_htmx_redirect(self):
        """Non-HTMX validation error → v2_err param shown as flash in GET."""
        import urllib.parse
        content_hash = self._current_hash()
        # Submit invalid value (negative capacity)
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.technical.capacity_mw",
                "project": self.project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": content_hash,
                "value": "-999",
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 303)
        location = resp.headers["location"]
        self.assertIn("v2_err", location)
        # Follow the redirect and check the error is shown
        get_resp = self.client.get(location)
        self.assertEqual(get_resp.status_code, 200)
        err_param = urllib.parse.parse_qs(urllib.parse.urlparse(location).query).get("v2_err", [""])[0]
        decoded = urllib.parse.unquote_plus(err_param)
        self.assertIn(decoded[:30], get_resp.text,
                      "Flash error must appear in the workbook page")


# ---------------------------------------------------------------------------
# 13. Source guard — _build_ps_fields must not hard-code snapshot keys
# ---------------------------------------------------------------------------

class TestBuildPsFieldsSourceGuard(unittest.TestCase):

    def test_no_legacy_snapshot_keys_hardcoded(self):
        src = inspect.getsource(_build_ps_fields)
        for key in ['"project_name"', '"project_type"', '"country_market"',
                    '"currency"', '"scenario"', '"capacity_mw"', '"p50_hours"',
                    '"capacity_factor"', '"cod_date"', '"construction_months"',
                    '"horizon_years"']:
            self.assertNotIn(key, src, f"snapshot key hard-coded: {key}")

    def test_uses_pis_get(self):
        src = inspect.getsource(_build_ps_fields)
        self.assertIn("pis.get(", src)

    def test_uses_fspec_field_id(self):
        src = inspect.getsource(_build_ps_fields)
        self.assertIn("fspec.field_id", src)

    def test_uses_fspec_field_type(self):
        src = inspect.getsource(_build_ps_fields)
        self.assertIn("fspec.field_type", src)

    def test_no_direct_snapshot_access(self):
        src = inspect.getsource(_build_ps_fields)
        self.assertNotIn("snapshot_origin", src)
        self.assertNotIn("draft_snapshot", src)


if __name__ == "__main__":
    unittest.main()
