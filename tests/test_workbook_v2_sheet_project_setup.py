"""
Tests for the V2 Project Setup sheet migration (PR 6).

Coverage:
1. _build_ps_fields — structure, ordering, value source (pis.get not snapshot keys)
2. Field-by-field proof — each project_setup field's value comes from pis.get(field_id)
3. HTTP integration — project_setup sheet rendered in /v2/workbook response
4. Editability contract — BOUND fields get <input>, DISPLAY_ONLY get <span>
5. Template structure — partial file exists and contains no legacy snapshot key refs
6. WORKBOOK registry completeness — all project_setup fields covered
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
        required = {"field_id", "label", "unit", "editable", "display_only",
                    "section_id", "section_label", "value"}
        for row in self.rows:
            self.assertEqual(set(row.keys()) & required, required,
                             f"missing keys in row for {row.get('field_id')}")

    def test_covers_all_registry_fields(self):
        """Every FieldSpec in project_setup registry appears in output."""
        sheet = WORKBOOK.sheet("project_setup")
        registry_ids = {f.field_id for s in sheet.sections for f in s.fields}
        output_ids = {r["field_id"] for r in self.rows}
        self.assertEqual(output_ids, registry_ids)

    def test_identity_section_before_technical(self):
        """identity section fields appear before technical section fields."""
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
        """All field_ids use the project_setup.<section>.<name> convention."""
        for row in self.rows:
            self.assertTrue(row["field_id"].startswith("project_setup."),
                            f"unexpected field_id: {row['field_id']}")

    def test_no_snapshot_key_in_field_id(self):
        """field_ids are semantic, not legacy snapshot keys."""
        legacy_keys = {
            "project_name", "project_type", "country_market", "currency",
            "scenario", "capacity_mw", "p50_hours", "capacity_factor",
            "cod_date", "construction_months", "horizon_years",
        }
        for row in self.rows:
            self.assertNotIn(row["field_id"], legacy_keys,
                             f"legacy snapshot key used as field_id: {row['field_id']}")


# ---------------------------------------------------------------------------
# 2. Field-by-field value proof
# ---------------------------------------------------------------------------

class TestPsFieldValueSource(unittest.TestCase):
    """Prove each field's value comes from pis.get(field_id), not snapshot keys."""

    def _row(self, rows: list[dict], field_id: str) -> dict:
        for r in rows:
            if r["field_id"] == field_id:
                return r
        self.fail(f"field_id {field_id!r} not found in ps_fields")

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
        """DISPLAY_ONLY — value from pis (may be None if not stored in snapshot)."""
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
        """Proves value tracks pis, not a stale snapshot copy."""
        pis_a = _make_pis({"capacity_mw": "50"})
        pis_b = _make_pis({"capacity_mw": "200"})
        rows_a = _build_ps_fields(pis_a)
        rows_b = _build_ps_fields(pis_b)
        val_a = next(r["value"] for r in rows_a if r["field_id"] == "project_setup.technical.capacity_mw")
        val_b = next(r["value"] for r in rows_b if r["field_id"] == "project_setup.technical.capacity_mw")
        self.assertNotEqual(val_a, val_b)
        self.assertAlmostEqual(val_a, 50.0)
        self.assertAlmostEqual(val_b, 200.0)


# ---------------------------------------------------------------------------
# 3. Editability contract
# ---------------------------------------------------------------------------

class TestPsFieldEditability(unittest.TestCase):

    def setUp(self):
        pis = _make_pis({"project_name": "X", "project_type": "wind_onshore"})
        self.rows = _build_ps_fields(pis)

    def _row(self, field_id: str) -> dict:
        for r in self.rows:
            if r["field_id"] == field_id:
                return r
        self.fail(f"{field_id} not found")

    def test_project_name_is_editable(self):
        r = self._row("project_setup.identity.project_name")
        self.assertTrue(r["editable"])
        self.assertFalse(r["display_only"])

    def test_project_type_is_not_editable(self):
        """TEMPLATE_LOCKED — editable=False, display_only=False."""
        r = self._row("project_setup.identity.project_type")
        self.assertFalse(r["editable"])
        self.assertFalse(r["display_only"])

    def test_capacity_factor_is_display_only(self):
        r = self._row("project_setup.technical.capacity_factor")
        self.assertTrue(r["display_only"])
        self.assertFalse(r["editable"])

    def test_bound_fields_are_editable(self):
        bound_ids = {
            "project_setup.identity.project_name",
            "project_setup.technical.capacity_mw",
            "project_setup.technical.p50_hours",
            "project_setup.technical.cod_date",
            "project_setup.technical.construction_months",
            "project_setup.technical.horizon_years",
        }
        for row in self.rows:
            if row["field_id"] in bound_ids:
                self.assertTrue(row["editable"],
                                f"BOUND field {row['field_id']} should be editable")

    def test_display_only_fields_not_editable(self):
        for row in self.rows:
            if row["display_only"]:
                self.assertFalse(row["editable"],
                                 f"display_only field {row['field_id']} should not be editable")


# ---------------------------------------------------------------------------
# 4. HTTP integration — ps_fields in response
# ---------------------------------------------------------------------------

class TestV2WorkbookProjectSetupResponse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "psresponse")

    def _get(self) -> str:
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        return resp.text

    def test_v2_project_setup_div_present(self):
        body = self._get()
        self.assertIn('id="v2-sheet-project-setup"', body)

    def test_identity_section_present(self):
        body = self._get()
        self.assertIn('data-section="identity"', body)

    def test_technical_section_present(self):
        body = self._get()
        self.assertIn('data-section="technical"', body)

    def test_project_name_field_rendered(self):
        body = self._get()
        self.assertIn('data-field-id="project_setup.identity.project_name"', body)

    def test_capacity_mw_field_rendered(self):
        body = self._get()
        self.assertIn('data-field-id="project_setup.technical.capacity_mw"', body)

    def test_capacity_mw_value_in_response(self):
        """The capacity_mw value (100 MW from project creation) appears in the body."""
        body = self._get()
        # The value is rendered in the input's value attribute
        self.assertIn("100", body)

    def test_no_snapshot_keys_as_html_names(self):
        """<input name=> attributes must use semantic field_ids, not legacy snapshot keys."""
        body = self._get()
        # Legacy snapshot key 'capacity_mw' must NOT appear as name="capacity_mw"
        self.assertNotIn('name="capacity_mw"', body)
        self.assertNotIn('name="project_name"', body)
        self.assertNotIn('name="p50_hours"', body)
        # V2 semantic names must appear instead
        self.assertIn('name="project_setup.technical.capacity_mw"', body)
        self.assertIn('name="project_setup.identity.project_name"', body)

    def test_capacity_factor_rendered_as_span_not_input(self):
        """DISPLAY_ONLY field must render as <span>, not <input>."""
        body = self._get()
        # A <input ... data-field-id="project_setup.technical.capacity_factor"> must NOT appear
        self.assertNotIn(
            'name="project_setup.technical.capacity_factor"', body,
            "DISPLAY_ONLY capacity_factor must not render as <input>"
        )

    def test_ps_fields_values_from_pis(self):
        """Patch _build_ps_fields to confirm router calls it with pis, not raw snapshot."""
        sentinel = [{"field_id": "project_setup.identity.project_name",
                     "label": "Project Name", "unit": None, "editable": True,
                     "display_only": False, "section_id": "identity",
                     "section_label": "Project Identity", "value": "SENTINEL_VALUE"}]
        with patch("app.v2.router._build_ps_fields", return_value=sentinel) as mock:
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            self.assertEqual(resp.status_code, 200)
            mock.assert_called_once()
            # The first (and only) arg is a ProjectInputSet
            pis_arg = mock.call_args[0][0]
            self.assertIsInstance(pis_arg, ProjectInputSet)


# ---------------------------------------------------------------------------
# 5. Template structure
# ---------------------------------------------------------------------------

class TestV2ProjectSetupTemplateStructure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import os as _os
        base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        cls.partial_path = _os.path.join(
            base, "app", "templates", "v2", "partials", "sheet_project_setup.html"
        )

    def test_partial_file_exists(self):
        self.assertTrue(
            os.path.isfile(self.partial_path),
            f"partial not found: {self.partial_path}"
        )

    def test_no_legacy_snapshot_key_references(self):
        """Template must not reference snapshot key strings as form names."""
        with open(self.partial_path) as fh:
            src = fh.read()
        legacy_patterns = [
            'name="capacity_mw"', 'name="project_name"', 'name="p50_hours"',
            'name="cod_date"', 'name="horizon_years"', 'name="construction_months"',
            'name="country_market"', 'name="currency"', 'name="scenario"',
            'name="project_type"',
        ]
        for pat in legacy_patterns:
            self.assertNotIn(pat, src,
                             f"Legacy snapshot key reference found in template: {pat!r}")

    def test_uses_field_id_for_names(self):
        with open(self.partial_path) as fh:
            src = fh.read()
        # Template should use f.field_id as the name attribute
        self.assertIn("f.field_id", src,
                      "Template must use f.field_id as the form name attribute")

    def test_data_section_attribute_present(self):
        with open(self.partial_path) as fh:
            src = fh.read()
        self.assertIn("data-section=", src)

    def test_data_field_id_attribute_present(self):
        with open(self.partial_path) as fh:
            src = fh.read()
        self.assertIn("data-field-id=", src)

    def test_workbook_include_in_main_template(self):
        import os as _os
        base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        main_tpl = _os.path.join(base, "app", "templates", "v2", "workbook.html")
        with open(main_tpl) as fh:
            src = fh.read()
        self.assertIn("sheet_project_setup.html", src,
                      "workbook.html must include sheet_project_setup partial")


# ---------------------------------------------------------------------------
# 6. Router source guard — no snapshot key references in _build_ps_fields
# ---------------------------------------------------------------------------

class TestBuildPsFieldsSourceGuard(unittest.TestCase):

    def test_no_legacy_snapshot_keys_in_function_source(self):
        """_build_ps_fields must not hard-code any legacy snapshot key strings."""
        src = inspect.getsource(_build_ps_fields)
        legacy_snapshot_keys = [
            '"project_name"', '"project_type"', '"country_market"', '"currency"',
            '"scenario"', '"capacity_mw"', '"p50_hours"', '"capacity_factor"',
            '"cod_date"', '"construction_months"', '"horizon_years"',
        ]
        for key in legacy_snapshot_keys:
            self.assertNotIn(key, src,
                             f"_build_ps_fields hard-codes legacy snapshot key: {key}")

    def test_uses_pis_get(self):
        """_build_ps_fields must call pis.get() to retrieve values."""
        src = inspect.getsource(_build_ps_fields)
        self.assertIn("pis.get(", src,
                      "_build_ps_fields must retrieve values via pis.get(field_id)")

    def test_uses_fspec_field_id(self):
        src = inspect.getsource(_build_ps_fields)
        self.assertIn("fspec.field_id", src)

    def test_no_direct_snapshot_access(self):
        """_build_ps_fields must not access pis.snapshot_origin or ws.draft_snapshot."""
        src = inspect.getsource(_build_ps_fields)
        self.assertNotIn("snapshot_origin", src)
        self.assertNotIn("draft_snapshot", src)


if __name__ == "__main__":
    unittest.main()
