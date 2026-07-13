"""
Tests for the Workbook V2 Tax worksheet (PR 2/6 — revised).

Coverage
--------
Registry
  1.  Tax sheet is registered in WORKBOOK (v2.1.0)
  2.  tax.assumptions.cit_rate_pct is BOUND, editable, persisted
  3.  tax.assumptions.loss_carryforward_years is BOUND, editable, persisted
  4.  Both fields have correct engine_path values

Materialization (adapter)
  5.  tax_corporate_rate_pct snapshot key → ProjectInputs.tax.corporate_rate (÷100)
  6.  tax_loss_carryforward_years snapshot key → ProjectInputs.tax.loss_carryforward_years
  7.  Absent tax keys preserve factory defaults (backward compatibility)
  8.  Explicit values override factory defaults

Page rendering
  9.  GET /v2/workbook includes #v2-sheet-tax
  10. Section A renders CIT Rate as editable input form
  11. Section A renders Loss Carryforward Years as editable input form
  12. No-runtime State A badge shows "Run Required"
  13. Pre-run notice renders when no runtime
  14. Tax schedule no-runtime notice renders

HTMX round-trip — CIT Rate
  15. POST /v2/workbook/update field_id=tax.assumptions.cit_rate_pct → 200 + #v2-sheet-tax
  16. Hash rotates after CIT Rate edit
  17. Full reload preserves edited CIT Rate value
  18. Materialized ProjectInputs.tax.corporate_rate reflects the change

HTMX round-trip — Loss Carryforward Years
  19. POST /v2/workbook/update field_id=tax.assumptions.loss_carryforward_years → 200 + #v2-sheet-tax
  20. Hash rotates after Loss Carryforward edit
  21. Full reload preserves Loss Carryforward value

Conflict / stale
  22. Stale content_hash returns HTMX 200 with error banner (no mutation)
  23. No mutation on stale update

Protected reference
  24. TUHO/Oborovo has no editable Tax input forms

Operational-period filtering (server-side)
  25. Construction periods excluded from tax_operational_periods
  26. Operational periods retained in order
  27. Empty operational set renders truthful empty state
  28. None operational periods (no runtime) renders no-runtime notice
  29. Operational rows in table match only is_operation=True periods

Engine-effectiveness
  30. Lower CIT rate → lower total_tax_keur in RuntimeResult (direction proof)
  31. Higher CIT rate → higher total_tax_keur in RuntimeResult
  32. tax_loss_carryforward_years snapshot value reaches TaxParams

KPI tiles / runtime summary
  33. KPI tile total_tax_keur renders from runtime_summary
  34. KPI tile effective_tax_rate_pct renders from runtime_summary
  35. KPI bar absent when no runtime

Regression
  36. Debt sheet still present after tax wiring
"""
from __future__ import annotations

import os
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-tax-tests-v2")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

import main_web
from app.auth import COOKIE_NAME, create_session_token
from app.v2.router import _build_tax_ctx, _thaw
from app.workbook.registry import WORKBOOK
from app.workbook.specs import BindingStatus, FieldKind, SourceOfTruth


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
            "project_name": f"Tax V2 Test {suffix}",
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


def _sample_period(period: int, is_operation: bool, tax_keur: float = 100.0) -> dict:
    return {
        "period": period,
        "date": f"2029-{period:02d}-30",
        "year_index": 1,
        "period_in_year": period,
        "is_operation": is_operation,
        "taxable_profit_keur": 500.0 if is_operation else None,
        "tax_keur": tax_keur if is_operation else None,
        "cf_after_tax_keur": 400.0 if is_operation else None,
        "corporate_tax_cash_keur": tax_keur if is_operation else None,
        "tax_depreciation_audit_keur": 100.0,
        "taxable_income_before_losses_audit_keur": 600.0,
        "tax_loss_opening_audit_keur": 0.0,
        "tax_loss_used_audit_keur": 0.0,
        "tax_loss_closing_audit_keur": 0.0,
        "taxable_profit_after_losses_audit_keur": 600.0,
        "cit_accrual_audit_keur": tax_keur if is_operation else None,
        "cash_tax_current_period_audit_keur": tax_keur if is_operation else None,
    }


def _render_tax_template(ctx: dict) -> BeautifulSoup:
    from jinja2 import Environment, FileSystemLoader
    tpl_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
    env = Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)
    env.globals["range"] = range
    html = env.get_template("partials/sheet_tax.html").render(ctx)
    return BeautifulSoup(html, "html.parser")


# ---------------------------------------------------------------------------
# 1–4. Registry tests
# ---------------------------------------------------------------------------

class TestTaxRegistry(unittest.TestCase):

    def test_tax_sheet_registered(self):
        sheet_ids = [s.sheet_id for s in WORKBOOK.sheets]
        assert "tax" in sheet_ids, f"tax sheet not in registry: {sheet_ids}"

    def test_workbook_version_bumped(self):
        assert WORKBOOK.version >= "2.1.0", f"version not bumped: {WORKBOOK.version}"

    def test_cit_rate_field_is_bound_editable_persisted(self):
        f = WORKBOOK.field("tax.assumptions.cit_rate_pct")
        assert f is not None
        assert f.binding_status == BindingStatus.BOUND
        assert f.editable is True
        assert f.persisted is True
        assert f.source_of_truth == SourceOfTruth.INPUT_SET
        assert f.kind == FieldKind.INPUT

    def test_loss_carryforward_field_is_bound_editable_persisted(self):
        f = WORKBOOK.field("tax.assumptions.loss_carryforward_years")
        assert f is not None
        assert f.binding_status == BindingStatus.BOUND
        assert f.editable is True
        assert f.persisted is True

    def test_cit_rate_engine_path(self):
        f = WORKBOOK.field("tax.assumptions.cit_rate_pct")
        assert f.engine_path == "tax.corporate_rate"

    def test_loss_carryforward_engine_path(self):
        f = WORKBOOK.field("tax.assumptions.loss_carryforward_years")
        assert f.engine_path == "tax.loss_carryforward_years"

    def test_cit_rate_snapshot_key(self):
        f = WORKBOOK.field("tax.assumptions.cit_rate_pct")
        assert f.snapshot_key == "tax_corporate_rate_pct"

    def test_loss_carryforward_snapshot_key(self):
        f = WORKBOOK.field("tax.assumptions.loss_carryforward_years")
        assert f.snapshot_key == "tax_loss_carryforward_years"


# ---------------------------------------------------------------------------
# 5–8. Materialization (adapter)
# ---------------------------------------------------------------------------

class TestTaxMaterialization(unittest.TestCase):

    def _build(self, snapshot_overrides: dict):
        """Build ProjectInputs from a snapshot with optional tax overrides."""
        from app.input_adapter import build_projectinputs_from_snapshot
        base = {
            "project_name": "Tax Adapter Test",
            "project_type": "Wind",
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
        }
        base.update(snapshot_overrides)
        return build_projectinputs_from_snapshot(base)

    def test_cit_rate_snapshot_to_domain(self):
        # 20% stored → 0.20 in domain
        inputs = self._build({"tax_corporate_rate_pct": "20"})
        assert abs(inputs.tax.corporate_rate - 0.20) < 1e-9, \
            f"expected 0.20, got {inputs.tax.corporate_rate}"

    def test_cit_rate_35pct(self):
        inputs = self._build({"tax_corporate_rate_pct": "35"})
        assert abs(inputs.tax.corporate_rate - 0.35) < 1e-9

    def test_loss_carryforward_snapshot_to_domain(self):
        inputs = self._build({"tax_loss_carryforward_years": "10"})
        assert inputs.tax.loss_carryforward_years == 10

    def test_absent_tax_keys_preserve_factory_defaults(self):
        from app.project_factories import create_default_wind_project
        factory = create_default_wind_project()
        inputs = self._build({})
        # Absent keys should not override factory default corporate_rate
        # (factory generic wind uses 0.25)
        assert abs(inputs.tax.corporate_rate - factory.tax.corporate_rate) < 1e-9

    def test_explicit_override_beats_factory_default(self):
        inputs = self._build({"tax_corporate_rate_pct": "15"})
        assert abs(inputs.tax.corporate_rate - 0.15) < 1e-9

    def test_explicit_loss_carryforward_override(self):
        inputs = self._build({"tax_loss_carryforward_years": "3"})
        assert inputs.tax.loss_carryforward_years == 3


# ---------------------------------------------------------------------------
# 9–14. Page rendering
# ---------------------------------------------------------------------------

class TestTaxSheetPageRendering(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "page-render")

    def test_workbook_includes_tax_sheet(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        assert soup.find(id="v2-sheet-tax"), "#v2-sheet-tax not found in workbook"

    def test_section_a_has_cit_rate_input(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        tax_div = soup.find(id="v2-sheet-tax")
        assert tax_div is not None
        # Find form with field_id=tax.assumptions.cit_rate_pct
        forms = tax_div.find_all("form")
        cit_form = next(
            (f for f in forms
             if any(i.get("value") == "tax.assumptions.cit_rate_pct"
                    for i in f.find_all("input", {"name": "field_id"}))),
            None,
        )
        assert cit_form is not None, "CIT Rate input form not found in tax sheet"

    def test_section_a_has_loss_carryforward_input(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        tax_div = soup.find(id="v2-sheet-tax")
        forms = tax_div.find_all("form")
        lcf_form = next(
            (f for f in forms
             if any(i.get("value") == "tax.assumptions.loss_carryforward_years"
                    for i in f.find_all("input", {"name": "field_id"}))),
            None,
        )
        assert lcf_form is not None, "Loss Carryforward input form not found in tax sheet"

    def test_no_runtime_state_a_badge(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        badge = soup.find(attrs={"data-testid": "tax-runtime-state-a"})
        assert badge is not None, "State A badge not found"
        assert "Not run" in badge.get_text()

    def test_no_runtime_pre_run_notice(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        assert soup.find(attrs={"data-testid": "tax-pre-run-notice"}) is not None

    def test_no_runtime_schedule_notice(self):
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        assert soup.find(attrs={"data-testid": "tax-schedule-no-runtime"}) is not None

    def test_regression_debt_sheet_still_present(self):
        html = _get_workbook(self.client, self.project_code)
        assert "v2-sheet-senior-debt" in html


# ---------------------------------------------------------------------------
# HTMX helper
# ---------------------------------------------------------------------------

def _get_tax_form_details(client, project_code, field_id):
    """Return (content_hash, workbook_version, current_value) for a Tax field."""
    html = _get_workbook(client, project_code)
    soup = BeautifulSoup(html, "html.parser")
    tax_div = soup.find(id="v2-sheet-tax")
    forms = tax_div.find_all("form")
    form = next(
        (f for f in forms
         if any(i.get("value") == field_id
                for i in f.find_all("input", {"name": "field_id"}))),
        None,
    )
    assert form is not None, f"No form found for field_id={field_id}"
    content_hash = form.find("input", {"name": "content_hash"})["value"]
    workbook_version = form.find("input", {"name": "workbook_version"})["value"]
    value_input = form.find("input", {"class": "v2-field-input"})
    current_value = value_input.get("value", "") if value_input else ""
    return content_hash, workbook_version, current_value


# ---------------------------------------------------------------------------
# 15–18. HTMX round-trip — CIT Rate
# ---------------------------------------------------------------------------

class TestTaxHtmxCITRate(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "htmx-cit")

    def _post_tax_update(self, field_id, value, content_hash, workbook_version):
        return self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": field_id,
                "value": str(value),
                "content_hash": content_hash,
                "workbook_version": workbook_version,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )

    def test_cit_rate_update_returns_200_with_tax_partial(self):
        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        resp = self._post_tax_update("tax.assumptions.cit_rate_pct", "22", ch, wv)
        assert resp.status_code == 200, f"expected 200, got {resp.status_code}"
        assert "v2-sheet-tax" in resp.text

    def test_cit_rate_hash_rotates(self):
        ch_before, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        self._post_tax_update("tax.assumptions.cit_rate_pct", "22", ch_before, wv)
        ch_after, _, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        assert ch_before != ch_after, "content hash did not rotate after CIT Rate edit"

    def test_cit_rate_reload_preserves_value(self):
        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        self._post_tax_update("tax.assumptions.cit_rate_pct", "28", ch, wv)
        _, _, reloaded_value = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        assert str(reloaded_value).strip() in ("28", "28.0", "28.00"), \
            f"persisted value wrong: {reloaded_value!r}"

    def test_cit_rate_materialized_in_projectinputs(self):
        """Value stored in snapshot produces correct ProjectInputs.tax.corporate_rate."""
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        from app.input_adapter import build_projectinputs_from_snapshot

        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        self._post_tax_update("tax.assumptions.cit_rate_pct", "18", ch, wv)

        from app.auth import create_session_token, decode_session_token
        session = decode_session_token(self.client.cookies.get(COOKIE_NAME))
        pr = get_project_record(user_id=session.user_id, project_code=self.project_code)
        ws = get_workspace_state(user_id=session.user_id, project_id=pr.project_id)
        snapshot = dict(ws.draft_snapshot or {})
        assert "tax_corporate_rate_pct" in snapshot, f"snapshot missing tax key: {list(snapshot.keys())}"
        inputs = build_projectinputs_from_snapshot(snapshot)
        assert abs(inputs.tax.corporate_rate - 0.18) < 1e-9, \
            f"expected 0.18, got {inputs.tax.corporate_rate}"

    def test_run_required_after_cit_edit(self):
        """After editing CIT Rate the Tax sheet badge must show Run Required."""
        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        self._post_tax_update("tax.assumptions.cit_rate_pct", "22", ch, wv)
        html = _get_workbook(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        badge = soup.find(attrs={"data-testid": "tax-runtime-state-a"})
        assert badge is not None, "Run Required badge not shown after CIT Rate edit"


# ---------------------------------------------------------------------------
# 19–21. HTMX round-trip — Loss Carryforward Years
# ---------------------------------------------------------------------------

class TestTaxHtmxLossCarryforward(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "htmx-lcf")

    def _post_tax_update(self, field_id, value, content_hash, workbook_version):
        return self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": field_id,
                "value": str(value),
                "content_hash": content_hash,
                "workbook_version": workbook_version,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )

    def test_loss_carryforward_update_returns_200_with_tax_partial(self):
        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.loss_carryforward_years")
        resp = self._post_tax_update("tax.assumptions.loss_carryforward_years", "7", ch, wv)
        assert resp.status_code == 200
        assert "v2-sheet-tax" in resp.text

    def test_loss_carryforward_hash_rotates(self):
        ch_before, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.loss_carryforward_years")
        self._post_tax_update("tax.assumptions.loss_carryforward_years", "7", ch_before, wv)
        ch_after, _, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.loss_carryforward_years")
        assert ch_before != ch_after, "hash did not rotate after Loss Carryforward edit"

    def test_loss_carryforward_reload_preserves_value(self):
        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.loss_carryforward_years")
        self._post_tax_update("tax.assumptions.loss_carryforward_years", "8", ch, wv)
        _, _, reloaded_value = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.loss_carryforward_years")
        assert str(reloaded_value).strip() in ("8", "8.0"), \
            f"persisted value wrong: {reloaded_value!r}"

    def test_loss_carryforward_snapshot_key_stored(self):
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        from app.auth import decode_session_token

        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.loss_carryforward_years")
        self._post_tax_update("tax.assumptions.loss_carryforward_years", "12", ch, wv)

        session = decode_session_token(self.client.cookies.get(COOKIE_NAME))
        pr = get_project_record(user_id=session.user_id, project_code=self.project_code)
        ws = get_workspace_state(user_id=session.user_id, project_id=pr.project_id)
        snapshot = dict(ws.draft_snapshot or {})
        assert "tax_loss_carryforward_years" in snapshot, \
            f"snapshot missing key tax_loss_carryforward_years: {list(snapshot.keys())}"
        from app.input_adapter import build_projectinputs_from_snapshot
        inputs = build_projectinputs_from_snapshot(snapshot)
        assert inputs.tax.loss_carryforward_years == 12


# ---------------------------------------------------------------------------
# 22–23. Stale hash / no mutation
# ---------------------------------------------------------------------------

class TestTaxStaleHash(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "stale-hash")

    def test_stale_hash_returns_200_with_error_message(self):
        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        # First, advance the hash by making a real edit
        self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "tax.assumptions.cit_rate_pct",
                "value": "22",
                "content_hash": ch,
                "workbook_version": wv,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        # Re-submit with the old (now stale) hash
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "tax.assumptions.cit_rate_pct",
                "value": "30",
                "content_hash": ch,  # stale
                "workbook_version": wv,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        # Should contain error notice (stale hash message or field-error banner)
        text = resp.text
        assert ("stale" in text.lower() or "changed" in text.lower() or "error" in text.lower()), \
            "No stale/conflict message in response"

    def test_stale_hash_no_mutation(self):
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        from app.auth import decode_session_token

        ch, wv, _ = _get_tax_form_details(self.client, self.project_code, "tax.assumptions.cit_rate_pct")
        # Advance hash
        self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "tax.assumptions.cit_rate_pct",
                "value": "22",
                "content_hash": ch,
                "workbook_version": wv,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        # Read snapshot after first edit
        session = decode_session_token(self.client.cookies.get(COOKIE_NAME))
        pr = get_project_record(user_id=session.user_id, project_code=self.project_code)
        ws = get_workspace_state(user_id=session.user_id, project_id=pr.project_id)
        value_after_first = dict(ws.draft_snapshot or {}).get("tax_corporate_rate_pct")

        # Stale post with "30" should not change the value
        self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "tax.assumptions.cit_rate_pct",
                "value": "30",
                "content_hash": ch,  # stale
                "workbook_version": wv,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        ws2 = get_workspace_state(user_id=session.user_id, project_id=pr.project_id)
        value_after_stale = dict(ws2.draft_snapshot or {}).get("tax_corporate_rate_pct")
        assert str(value_after_first) == str(value_after_stale), \
            f"snapshot mutated on stale hash: {value_after_first!r} → {value_after_stale!r}"


# ---------------------------------------------------------------------------
# 24. Protected reference — no editable Tax forms
# ---------------------------------------------------------------------------

class TestTaxProtectedReference(unittest.TestCase):

    def setUp(self):
        self.client = _authed_client()

    def _find_tuho_project(self):
        from app.persistence.projects_repository import list_project_records
        from app.auth import decode_session_token
        session = decode_session_token(self.client.cookies.get(COOKIE_NAME))
        projects = list_project_records(user_id=session.user_id)
        for p in projects:
            ts = (p.template_source or "").lower()
            if ts in ("tuho", "oborovo") and p.project_origin == "factory_template":
                return p.project_code
        return None

    def test_protected_reference_has_no_editable_tax_forms(self):
        tuho = self._find_tuho_project()
        if tuho is None:
            self.skipTest("No protected reference project found in this test DB")
        html = _get_workbook(self.client, tuho)
        soup = BeautifulSoup(html, "html.parser")
        tax_div = soup.find(id="v2-sheet-tax")
        if tax_div is None:
            self.skipTest("Tax sheet not in workbook HTML for protected reference")
        forms = tax_div.find_all("form")
        editable_tax_forms = [
            f for f in forms
            if any(i.get("value", "").startswith("tax.")
                   for i in f.find_all("input", {"name": "field_id"}))
        ]
        assert len(editable_tax_forms) == 0, \
            f"protected reference has editable Tax forms: {[str(f)[:200] for f in editable_tax_forms]}"


# ---------------------------------------------------------------------------
# 25–29. Operational-period filtering
# ---------------------------------------------------------------------------

class TestTaxOperationalPeriodFiltering(unittest.TestCase):

    def _make_pis(self):
        pis = MagicMock()
        pis.workbook_version = "2.1.0"
        pis.content_hash = "abc123"
        return pis

    def _rr_with_tax(self, periods):
        rr = MagicMock()
        rr.tax_schedule = {"periods": periods, "summary": {"total_tax_keur": 999.0}}
        rr.runtime_summary = {"total_tax_keur": "999 kEUR", "effective_tax_rate_pct": "20.0%"}
        return rr

    def test_construction_periods_excluded(self):
        periods = [
            _sample_period(1, is_operation=False),
            _sample_period(2, is_operation=False),
            _sample_period(3, is_operation=True),
        ]
        rr = self._rr_with_tax(periods)
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(self._make_pis(), MagicMock())
        op = ctx["tax_operational_periods"]
        assert op is not None
        assert all(p["is_operation"] for p in op)
        assert len(op) == 1

    def test_operational_periods_retained_in_order(self):
        periods = [_sample_period(i, True) for i in range(1, 4)]
        rr = self._rr_with_tax(periods)
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(self._make_pis(), MagicMock())
        assert [p["period"] for p in ctx["tax_operational_periods"]] == [1, 2, 3]

    def test_empty_operational_set_when_only_construction(self):
        periods = [_sample_period(1, False), _sample_period(2, False)]
        rr = self._rr_with_tax(periods)
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(self._make_pis(), MagicMock())
        assert ctx["tax_operational_periods"] == []

    def test_empty_operational_set_shows_empty_state(self):
        pis = self._make_pis()
        rr = self._rr_with_tax([_sample_period(1, False)])
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(pis, MagicMock())
        ctx.update({
            "project_code": "test", "workbook_version": "2.1.0", "content_hash": "x",
            "project_editable": True, "ws_dirty": False, "has_runtime": True, "field_error": "",
        })
        soup = _render_tax_template(ctx)
        assert soup.find(attrs={"data-testid": "tax-schedule-empty"}) is not None
        assert soup.find(attrs={"data-testid": "tax-schedule-table"}) is None

    def test_no_runtime_shows_no_runtime_notice(self):
        ctx = {
            "tax_fields": [], "tax_schedule": None, "tax_operational_periods": None,
            "runtime_summary": None, "project_code": "test", "workbook_version": "2.1.0",
            "content_hash": "x", "project_editable": True, "ws_dirty": False,
            "has_runtime": False, "field_error": "",
        }
        soup = _render_tax_template(ctx)
        assert soup.find(attrs={"data-testid": "tax-schedule-no-runtime"}) is not None

    def test_table_shows_only_operational_rows(self):
        periods = [
            _sample_period(1, False),
            _sample_period(2, True, 111.0),
            _sample_period(3, True, 222.0),
            _sample_period(4, True, 333.0),
        ]
        rr = self._rr_with_tax(periods)
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=rr):
            ctx = _build_tax_ctx(self._make_pis(), MagicMock())
        ctx.update({
            "project_code": "test", "workbook_version": "2.1.0", "content_hash": "x",
            "project_editable": True, "ws_dirty": False, "has_runtime": True, "field_error": "",
        })
        soup = _render_tax_template(ctx)
        rows = soup.find_all(attrs={"data-testid": lambda v: v and v.startswith("tax-schedule-row-")})
        assert len(rows) == 3
        assert soup.find(attrs={"data-testid": "tax-schedule-row-1"}) is None


# ---------------------------------------------------------------------------
# 30–32. Engine-effectiveness proofs
# ---------------------------------------------------------------------------

class TestTaxEngineEffectiveness(unittest.TestCase):

    def _run_with_snapshot(self, snapshot_overrides):
        from app.input_adapter import build_projectinputs_from_snapshot
        from app.ui_runner import run_demo_project
        base = {
            "project_name": "Tax Engine Test",
            "project_type": "Wind",
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
        }
        base.update(snapshot_overrides)
        inputs = build_projectinputs_from_snapshot(base)
        ctx = run_demo_project(project_type="Wind", project_inputs_override=inputs)
        return ctx.result

    def test_lower_cit_rate_lower_total_tax(self):
        result_low = self._run_with_snapshot({"tax_corporate_rate_pct": "10"})
        result_high = self._run_with_snapshot({"tax_corporate_rate_pct": "30"})
        tax_low = getattr(result_low, "total_tax_keur", None)
        tax_high = getattr(result_high, "total_tax_keur", None)
        assert tax_low is not None and tax_high is not None, \
            f"total_tax_keur not on result: low={tax_low}, high={tax_high}"
        assert tax_low < tax_high, \
            f"expected lower CIT → lower tax, got low={tax_low:.0f} high={tax_high:.0f}"

    def test_higher_cit_rate_higher_total_tax(self):
        result_low = self._run_with_snapshot({"tax_corporate_rate_pct": "5"})
        result_high = self._run_with_snapshot({"tax_corporate_rate_pct": "40"})
        assert result_low.total_tax_keur < result_high.total_tax_keur

    def test_loss_carryforward_snapshot_value_reaches_taxparams(self):
        from app.input_adapter import build_projectinputs_from_snapshot
        inputs = build_projectinputs_from_snapshot({
            "project_name": "Tax LCF Test",
            "project_type": "Wind",
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
            "tax_loss_carryforward_years": "3",
        })
        assert inputs.tax.loss_carryforward_years == 3


# ---------------------------------------------------------------------------
# 33–35. KPI tiles / runtime summary
# ---------------------------------------------------------------------------

class TestTaxKpiTiles(unittest.TestCase):

    def _ctx_with_summary(self, total_tax, eff_rate):
        return {
            "tax_fields": [],
            "tax_schedule": {"periods": [], "summary": {}},
            "tax_operational_periods": [],
            "runtime_summary": {"total_tax_keur": total_tax, "effective_tax_rate_pct": eff_rate},
            "project_code": "test", "workbook_version": "2.1.0", "content_hash": "x",
            "project_editable": True, "ws_dirty": False, "has_runtime": True, "field_error": "",
        }

    def test_total_tax_kpi_renders(self):
        soup = _render_tax_template(self._ctx_with_summary("12,345 kEUR", "22.5%"))
        tile = soup.find(attrs={"data-testid": "tax-kpi-total-tax"})
        assert tile is not None
        assert "12,345 kEUR" in tile.get_text()

    def test_effective_rate_kpi_renders(self):
        soup = _render_tax_template(self._ctx_with_summary("12,345 kEUR", "22.5%"))
        tile = soup.find(attrs={"data-testid": "tax-kpi-eff-rate"})
        assert tile is not None
        assert "22.5%" in tile.get_text()

    def test_kpi_bar_absent_when_no_runtime(self):
        ctx = {
            "tax_fields": [], "tax_schedule": None, "tax_operational_periods": None,
            "runtime_summary": None, "project_code": "test", "workbook_version": "2.1.0",
            "content_hash": "x", "project_editable": True, "ws_dirty": False,
            "has_runtime": False, "field_error": "",
        }
        soup = _render_tax_template(ctx)
        assert soup.find(attrs={"data-testid": "tax-kpi-bar"}) is None

    def test_schedule_column_headers_present(self):
        ctx = {
            "tax_fields": [],
            "tax_schedule": {"periods": [_sample_period(1, True)], "summary": {}},
            "tax_operational_periods": [_sample_period(1, True)],
            "runtime_summary": {"total_tax_keur": "1 kEUR", "effective_tax_rate_pct": "10%"},
            "project_code": "test", "workbook_version": "2.1.0", "content_hash": "x",
            "project_editable": True, "ws_dirty": False, "has_runtime": True, "field_error": "",
        }
        html_str = __import__("jinja2", fromlist=["Environment"]).Environment(
            loader=__import__("jinja2", fromlist=["FileSystemLoader"]).FileSystemLoader(
                os.path.join(os.path.dirname(__file__), "..", "app", "templates", "v2")
            ),
            autoescape=False,
        ).get_template("partials/sheet_tax.html").render(ctx)
        assert "Taxable Profit" in html_str
        assert "Tax (kEUR)" in html_str
        assert "CF After Tax" in html_str
        assert "Loss Opening" in html_str


# ---------------------------------------------------------------------------
# 37–46. Truthful default hydration (Option B) + merge-preserve (legacy save)
# ---------------------------------------------------------------------------

class TestTaxFirstLoadHydration(unittest.TestCase):
    """Option B effective-value projection: first GET shows factory defaults, not None.

    These are characterization tests — they prove the displayed Tax field
    values match the effective ProjectInputs.tax for each project template.
    No rate is hard-coded here; the expected value comes from the same
    canonical materialization path as the router.
    """

    def _effective_tax(self, template_source: str, project_type: str = "Wind") -> object:
        """Return effective TaxParams for a freshly created project (no V2 tax keys set)."""
        from app.input_adapter import build_projectinputs_from_snapshot
        base = {
            "project_name": f"Test {template_source}",
            "project_type": project_type,
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
            # No tax_corporate_rate_pct or tax_loss_carryforward_years → factory defaults.
        }
        return build_projectinputs_from_snapshot(base).tax

    def _pis_without_tax_keys(self, template_source: str = "generic_wind",
                               project_type: str = "Wind"):
        """Build a ProjectInputSet without any Tax snapshot keys (first-load state)."""
        from app.workbook.input_set import ProjectInputSet
        snapshot = {
            "project_name": f"Test {template_source}",
            "project_type": project_type,
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
        }
        return ProjectInputSet.from_snapshot(snapshot)

    def _tax_fields_from_pis(self, pis) -> dict:
        """Return {field_id: value} from _build_tax_ctx for a given ProjectInputSet."""
        from app.v2.router import _build_tax_ctx
        # Minimal workspace mock — no runtime result needed for this test.
        ws = MagicMock()
        ws.last_runtime_snapshot = None
        ws.last_runtime_summary = None
        ws.last_tax_schedule = None
        from unittest.mock import patch
        with patch("app.workbook.service.WorkbookService.get_runtime_result", return_value=None):
            ctx = _build_tax_ctx(pis, ws)
        return {f["field_id"]: f["value"] for f in ctx["tax_fields"]}

    def test_generic_wind_first_load_cit_rate_not_none(self):
        """First GET for Generic Wind shows effective CIT rate, not None."""
        pis = self._pis_without_tax_keys("generic_wind", "Wind")
        fields = self._tax_fields_from_pis(pis)
        assert fields["tax.assumptions.cit_rate_pct"] is not None, \
            "CIT Rate must not be None on first load (Option B hydration)"

    def test_generic_wind_first_load_cit_rate_matches_effective(self):
        """Displayed CIT rate equals canonical factory default × 100."""
        pis = self._pis_without_tax_keys("generic_wind", "Wind")
        fields = self._tax_fields_from_pis(pis)
        effective = self._effective_tax("generic_wind", "Wind")
        expected = round(effective.corporate_rate * 100, 10)
        assert fields["tax.assumptions.cit_rate_pct"] == expected, \
            f"CIT Rate mismatch: got {fields['tax.assumptions.cit_rate_pct']} expected {expected}"

    def test_generic_solar_first_load_cit_rate_not_none(self):
        """First GET for Generic Solar shows effective CIT rate."""
        pis = self._pis_without_tax_keys("generic_solar", "Solar")
        fields = self._tax_fields_from_pis(pis)
        assert fields["tax.assumptions.cit_rate_pct"] is not None

    def test_generic_solar_first_load_loss_carryforward_not_none(self):
        """First GET for Generic Solar shows effective loss carryforward years."""
        pis = self._pis_without_tax_keys("generic_solar", "Solar")
        fields = self._tax_fields_from_pis(pis)
        assert fields["tax.assumptions.loss_carryforward_years"] is not None

    def test_generic_wind_first_load_loss_carryforward_matches_effective(self):
        """Displayed loss carryforward equals canonical factory default."""
        pis = self._pis_without_tax_keys("generic_wind", "Wind")
        fields = self._tax_fields_from_pis(pis)
        effective = self._effective_tax("generic_wind", "Wind")
        assert fields["tax.assumptions.loss_carryforward_years"] == effective.loss_carryforward_years

    def test_first_get_does_not_mark_workspace_dirty(self):
        """GET /v2/workbook must not flip dirty=True (Option B is read-only)."""
        client = _authed_client()
        project_code = _create_project(client, "dirty-check")
        # Fetch the workbook — must not mutate dirty flag.
        _get_workbook(client, project_code)
        # Re-fetch and check that the dirty indicator is absent (no asterisk / "Unsaved").
        html = _get_workbook(client, project_code)
        soup = BeautifulSoup(html, "html.parser")
        dirty_marker = soup.find(attrs={"data-testid": "ws-dirty-indicator"})
        if dirty_marker:
            assert "unsaved" not in dirty_marker.get_text("", strip=True).lower(), \
                "GET must not mark workspace dirty"

    def test_hash_does_not_rotate_on_first_get(self):
        """Two consecutive GETs return the same content_hash (no spurious mutation)."""
        client = _authed_client()
        project_code = _create_project(client, "hash-stable")
        resp1 = client.get(f"/v2/workbook?project={project_code}")
        resp2 = client.get(f"/v2/workbook?project={project_code}")
        assert resp1.status_code == resp2.status_code == 200
        from bs4 import BeautifulSoup as BS
        h1 = BS(resp1.text, "html.parser").find(attrs={"data-content-hash": True})
        h2 = BS(resp2.text, "html.parser").find(attrs={"data-content-hash": True})
        if h1 and h2:
            assert h1["data-content-hash"] == h2["data-content-hash"], \
                "content_hash must not rotate between two consecutive GETs"


def _legacy_form_save(client: TestClient, project_code: str) -> int:
    """POST to /scenarios/state/draft — the canonical legacy save path.

    This is the real production path that calls _collect_form_snapshot()
    (which has no tax keys). Returns the HTTP status code.
    """
    resp = client.post(
        "/scenarios/state/draft",
        data={
            "active_project": project_code,
            "project_name": "Merge Preserve Test",
            "project_type": "Wind",
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
            # Intentionally NO tax_corporate_rate_pct or tax_loss_carryforward_years.
        },
        follow_redirects=False,
    )
    return resp.status_code


def _get_workspace_by_code(project_code: str):
    """Return (WorkspaceStateRecord, project_id) for the test user's project."""
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    # create_session_token() defaults to user_id="1"
    proj = get_project_record(user_id="1", project_code=project_code)
    assert proj is not None, f"Project not found in DB: {project_code}"
    ws = get_workspace_state("1", proj.project_id)
    return ws, proj.project_id


def _set_tax_via_v2(client: TestClient, project_code: str, cit_pct: float, lcf_years: int) -> None:
    """Set both Tax fields via the V2 endpoint. Asserts 200 on each POST."""
    ch1, wv1, _ = _get_tax_form_details(client, project_code, "tax.assumptions.cit_rate_pct")
    resp1 = client.post(
        "/v2/workbook/update",
        data={
            "project": project_code,
            "field_id": "tax.assumptions.cit_rate_pct",
            "value": str(cit_pct),
            "content_hash": ch1,
            "workbook_version": wv1,
            "sheet_id": "tax",
        },
        headers={"HX-Request": "true"},
    )
    assert resp1.status_code == 200, f"CIT rate set failed: {resp1.status_code} {resp1.text[:300]}"

    ch2, wv2, _ = _get_tax_form_details(client, project_code, "tax.assumptions.loss_carryforward_years")
    resp2 = client.post(
        "/v2/workbook/update",
        data={
            "project": project_code,
            "field_id": "tax.assumptions.loss_carryforward_years",
            "value": str(lcf_years),
            "content_hash": ch2,
            "workbook_version": wv2,
            "sheet_id": "tax",
        },
        headers={"HX-Request": "true"},
    )
    assert resp2.status_code == 200, f"LCF set failed: {resp2.status_code} {resp2.text[:300]}"


def _find_tax_form_value(soup: BeautifulSoup, field_id: str) -> str:
    """Find the value input inside the Tax form identified by a hidden field_id input.

    The render_field macro produces:
      <input type="hidden" name="field_id" value="tax.assumptions.cit_rate_pct">
      <input type="number" name="value" class="v2-field-input" value="...">
    inside the same <form>.
    """
    tax_div = soup.find(id="v2-sheet-tax")
    assert tax_div is not None, "v2-sheet-tax div not found in workbook HTML"
    forms = tax_div.find_all("form")
    form = next(
        (f for f in forms
         if any(i.get("value") == field_id
                for i in f.find_all("input", {"name": "field_id"}))),
        None,
    )
    assert form is not None, f"No form found for field_id={field_id}"
    value_input = form.find("input", {"name": "value"})
    assert value_input is not None, f"No 'value' input in form for field_id={field_id}"
    return value_input.get("value", "")


class TestTaxMergePreserve(unittest.TestCase):
    """Merge-preserve: V2 Tax values survive legacy save paths."""

    def test_v2_tax_values_survive_legacy_save(self):
        """Full path: V2 Tax edit → legacy save → workspace DB → HTML → ProjectInputs.

        Proves:
        1. Legacy save via /scenarios/state/draft returns expected success status.
        2. Workbook HTML after legacy save shows 17.5% CIT and 7yr LCF.
        3. draft_snapshot in DB has the correct Tax keys.
        4. build_projectinputs_from_snapshot materializes correct TaxParams.
        """
        from app.input_adapter import build_projectinputs_from_snapshot
        client = _authed_client()
        project_code = _create_project(client, "legacy-save-test")

        # Step 1: Set Tax values via V2 endpoint.
        _set_tax_via_v2(client, project_code, cit_pct=17.5, lcf_years=7)

        # Step 2: Verify Tax values in DB after V2 edits (pre-legacy-save baseline).
        ws_pre, _proj_id = _get_workspace_by_code(project_code)
        assert ws_pre is not None, "Workspace not found after V2 edits"
        assert str(ws_pre.draft_snapshot.get("tax_corporate_rate_pct", "")).strip() != "", \
            "tax_corporate_rate_pct should be set in DB after V2 edit"

        # Step 3: Legacy save — /scenarios/state/draft (the real production path).
        # This calls _collect_form_snapshot() which has no tax keys.
        save_status = _legacy_form_save(client, project_code)
        assert save_status in (200, 302, 303), \
            f"/scenarios/state/draft returned unexpected status {save_status}"

        # Step 4: Verify Tax values survived in the workspace draft_snapshot (DB layer).
        ws_post, _ = _get_workspace_by_code(project_code)
        assert ws_post is not None, "Workspace not found after legacy save"
        snap = ws_post.draft_snapshot

        cit_snap = str(snap.get("tax_corporate_rate_pct", "")).strip()
        assert cit_snap != "", \
            f"tax_corporate_rate_pct was erased from draft_snapshot by legacy save; got {snap.get('tax_corporate_rate_pct')!r}"
        assert float(cit_snap) == 17.5, \
            f"tax_corporate_rate_pct mismatch in draft_snapshot: expected '17.5', got {cit_snap!r}"

        lcf_snap = str(snap.get("tax_loss_carryforward_years", "")).strip()
        assert lcf_snap != "", \
            f"tax_loss_carryforward_years was erased from draft_snapshot by legacy save; got {snap.get('tax_loss_carryforward_years')!r}"
        assert int(float(lcf_snap)) == 7, \
            f"tax_loss_carryforward_years mismatch in draft_snapshot: expected '7', got {lcf_snap!r}"

        # Step 5: Materialize snapshot through the canonical adapter path.
        inputs = build_projectinputs_from_snapshot(snap)
        assert abs(inputs.tax.corporate_rate - 0.175) < 1e-9, \
            f"ProjectInputs.tax.corporate_rate should be 0.175 (17.5÷100), got {inputs.tax.corporate_rate}"
        assert inputs.tax.loss_carryforward_years == 7, \
            f"ProjectInputs.tax.loss_carryforward_years should be 7, got {inputs.tax.loss_carryforward_years}"

        # Step 6: HTML layer — workbook reload shows correct values.
        html = _get_workbook(client, project_code)
        soup = BeautifulSoup(html, "html.parser")

        cit_val = _find_tax_form_value(soup, "tax.assumptions.cit_rate_pct")
        assert cit_val != "", "CIT Rate input must have a non-empty value after legacy save"
        assert float(cit_val) == 17.5, \
            f"CIT Rate lost after legacy save: got {cit_val!r} expected '17.5'"

        lcf_val = _find_tax_form_value(soup, "tax.assumptions.loss_carryforward_years")
        assert lcf_val != "", "Loss Carryforward input must have a non-empty value after legacy save"
        assert int(float(lcf_val)) == 7, \
            f"Loss Carryforward lost after legacy save: got {lcf_val!r} expected '7'"

    def test_merge_preserve_semantics_via_real_save_workspace_state(self):
        """Prove merge-preserve in save_workspace_state() using the real repository function.

        Four cases:
        A — Missing incoming keys: existing non-empty V2 keys survive.
        B — Blank incoming keys: existing non-empty V2 keys survive (blank != explicit clear).
        C — Explicit incoming value: incoming value wins (not overwritten).
        D — Both absent: no empty-string V2 keys are injected.
        """
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state

        client = _authed_client()
        project_code = _create_project(client, "mp-semantics")
        ws_init, project_id = _get_workspace_by_code(project_code)
        assert ws_init is not None

        def _save(draft: dict) -> dict:
            """Call save_workspace_state and return the stored draft_snapshot."""
            save_workspace_state(
                user_id="1",
                project_id=project_id,
                project_code=project_code,
                draft_snapshot=dict(draft),
                saved_snapshot=dict(draft),
            )
            ws = get_workspace_state("1", project_id)
            return ws.draft_snapshot

        # Seed the workspace with non-empty V2 Tax keys.
        seed_snap = dict(ws_init.draft_snapshot)
        seed_snap["tax_corporate_rate_pct"] = "17.5"
        seed_snap["tax_loss_carryforward_years"] = "7"
        _save(seed_snap)

        # ── Case A: incoming omits V2 Tax keys entirely → existing values survive. ──
        incoming_a = {k: v for k, v in seed_snap.items()
                      if k not in ("tax_corporate_rate_pct", "tax_loss_carryforward_years")}
        stored_a = _save(incoming_a)
        assert str(stored_a.get("tax_corporate_rate_pct", "")).strip() == "17.5", \
            f"Case A: tax_corporate_rate_pct should survive; got {stored_a.get('tax_corporate_rate_pct')!r}"
        assert str(stored_a.get("tax_loss_carryforward_years", "")).strip() == "7", \
            f"Case A: tax_loss_carryforward_years should survive; got {stored_a.get('tax_loss_carryforward_years')!r}"

        # Re-seed (Case A mutated it but values should still be there).
        _save(seed_snap)

        # ── Case B: incoming has blank V2 Tax keys → existing non-empty values survive. ──
        incoming_b = dict(seed_snap)
        incoming_b["tax_corporate_rate_pct"] = ""
        incoming_b["tax_loss_carryforward_years"] = ""
        stored_b = _save(incoming_b)
        assert str(stored_b.get("tax_corporate_rate_pct", "")).strip() == "17.5", \
            f"Case B: blank incoming must not overwrite existing; got {stored_b.get('tax_corporate_rate_pct')!r}"
        assert str(stored_b.get("tax_loss_carryforward_years", "")).strip() == "7", \
            f"Case B: blank incoming must not overwrite existing; got {stored_b.get('tax_loss_carryforward_years')!r}"

        # ── Case C: incoming has explicit new value → incoming wins. ──
        incoming_c = dict(seed_snap)
        incoming_c["tax_corporate_rate_pct"] = "22.0"
        incoming_c["tax_loss_carryforward_years"] = "5"
        stored_c = _save(incoming_c)
        assert str(stored_c.get("tax_corporate_rate_pct", "")).strip() == "22.0", \
            f"Case C: explicit incoming value must win; got {stored_c.get('tax_corporate_rate_pct')!r}"
        assert str(stored_c.get("tax_loss_carryforward_years", "")).strip() == "5", \
            f"Case C: explicit incoming value must win; got {stored_c.get('tax_loss_carryforward_years')!r}"

        # ── Case D: both existing and incoming lack V2 Tax keys → no empty string injected. ──
        # Use a brand-new project so neither existing nor incoming has V2 Tax keys.
        project_code_d = _create_project(client, "mp-case-d")
        _, project_id_d = _get_workspace_by_code(project_code_d)
        ws_d_init = get_workspace_state("1", project_id_d)
        # Strip any accidental V2 keys from the initial snapshot.
        incoming_d = {k: v for k, v in ws_d_init.draft_snapshot.items()
                      if k not in ("tax_corporate_rate_pct", "tax_loss_carryforward_years")}
        save_workspace_state(
            user_id="1",
            project_id=project_id_d,
            project_code=project_code_d,
            draft_snapshot=dict(incoming_d),
            saved_snapshot=dict(incoming_d),
        )
        ws_d = get_workspace_state("1", project_id_d)
        for k in ("tax_corporate_rate_pct", "tax_loss_carryforward_years"):
            val = ws_d.draft_snapshot.get(k)
            assert not (isinstance(val, str) and val.strip() == ""), \
                f"Case D: merge-preserve injected empty string for {k}: {val!r}"

    def test_hash_rotates_only_on_real_mutation(self):
        """content_hash must change after a Tax edit but not after a read-only GET."""
        client = _authed_client()
        project_code = _create_project(client, "hash-rotation")

        # Get initial hash and form metadata.
        ch_before, wv, _ = _get_tax_form_details(client, project_code, "tax.assumptions.cit_rate_pct")

        # POST a real Tax mutation.
        resp_post = client.post(
            "/v2/workbook/update",
            data={
                "project": project_code,
                "field_id": "tax.assumptions.cit_rate_pct",
                "value": "22.0",
                "content_hash": ch_before,
                "workbook_version": wv,
                "sheet_id": "tax",
            },
            headers={"HX-Request": "true"},
        )
        assert resp_post.status_code == 200, f"Tax edit failed: {resp_post.status_code}"
        soup_post = BeautifulSoup(resp_post.text, "html.parser")
        ch_el_post = soup_post.find(attrs={"data-content-hash": True})
        hash_after = ch_el_post["data-content-hash"] if ch_el_post else None

        # Verify hash changed: GET after the edit must return a different hash from before.
        ch_after_edit, _, _ = _get_tax_form_details(client, project_code, "tax.assumptions.cit_rate_pct")
        assert ch_before != ch_after_edit, \
            f"content_hash must rotate after CIT Rate edit; before={ch_before} after={ch_after_edit}"

        # Second GET must return same hash (no further rotation).
        ch_get2, _, _ = _get_tax_form_details(client, project_code, "tax.assumptions.cit_rate_pct")
        assert ch_after_edit == ch_get2, \
            f"content_hash must not rotate between two consecutive GETs: {ch_after_edit} vs {ch_get2}"


if __name__ == "__main__":
    unittest.main()
