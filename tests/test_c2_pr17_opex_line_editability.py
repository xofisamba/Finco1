"""C2-PR17: OPEX Line Editability Bridge — route-level backend tests.

Covers the required-behaviour points from the C2-PR17 task spec that
don't require a browser:

  1. OPEX line Budget/amount cells are editable only where intended:
     non-contingency rows on user (is_user_project=True) projects get
     `data-fc-editable="true"` plus a real `<input class="fc-input-native">`
     descendant; contingency rows, subtotal/total rows, and rows on
     protected/reference projects remain `data-fc-editable="false"`
     with the existing read-only `<span class="fc-cell-runtime">`.
  2. The new OPEX Budget `<input>` carries no `name` attribute, so it
     structurally cannot be submitted by any HTML form post — this is
     the concrete evidence behind the "preview-only, not yet
     persisted" decision documented in
     docs/C2_PR17_OPEX_LINE_EDITABILITY_BRIDGE.md.
  3. No financial engine call (waterfall_core.run_project) as a side
     effect of rendering the OPEX sheet or of /model/preview, mirroring
     the existing pattern in tests/test_c2_pr14_opex_preview.py.
  4. Editing-related rendering does not change any authoritative
     Run output: rendering the OPEX sheet twice for the same project
     produces byte-identical Budget cell values.

Uses fastapi.testclient.TestClient against the real `main_web.app`,
mirroring tests/test_c2_pr14_opex_preview.py's pattern.
"""
import os
import re
import urllib.parse

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token, COOKIE_NAME

client = TestClient(app)


def _auth_cookies():
    token = create_session_token()
    return {COOKIE_NAME: token}


def _create_user_project(name_suffix):
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"C2 PR17 OPEX Editability {name_suffix}",
            "project_type": "Solar",
            "template_source": "generic_solar",
            "country_market": "Croatia",
            "capacity_mw": "50",
            "cod_date": "2027-01-01",
            "construction_months": "12",
            "horizon_years": "25",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "1400",
            "opex_y1_keur": "1000",
            "total_capex_keur": "50000",
            "gearing_pct": "70",
            "interest_rate_pct": "5",
            "tenor_years": "15",
            "target_dscr": "1.30",
        },
        cookies=_auth_cookies(),
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect")
    assert redirect, f"expected HX-Redirect from /projects/create, got {resp.status_code} {resp.text[:200]}"
    project_code = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)["project"][0]
    return project_code


def _create_user_project_with_contingency():
    """Duplicate the oborovo factory project (which has a real B.13
    contingency OPEX category) into an editable user project via
    /projects/oborovo/save-as."""
    resp = client.post(
        "/projects/oborovo/save-as",
        data={"new_project_name": "C2 PR17 contingency check"},
        cookies=_auth_cookies(),
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303), f"expected redirect, got {resp.status_code}: {resp.text[:300]}"
    location = resp.headers.get("location")
    assert location, "expected Location header from /projects/oborovo/save-as"
    project_code = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)["project"][0]
    return project_code


def _get_opex_sheet_html(project_code):
    resp = client.get(f"/?project={project_code}", cookies=_auth_cookies())
    assert resp.status_code == 200
    return resp.text


class TestOpexBudgetCellEditability:
    def test_non_contingency_budget_cells_are_editable_on_user_project(self):
        project_code = _create_user_project("editable-check")
        html = _get_opex_sheet_html(project_code)

        budget_cells = re.findall(
            r'data-fc-addr="opex!([^"]*)\.budget"[^>]*data-fc-editable="(true|false)"',
            html,
        )
        assert budget_cells, "expected at least one OPEX budget cell in the rendered sheet"
        assert all(editable == "true" for _, editable in budget_cells), (
            f"expected all OPEX budget cells editable on a user project with no "
            f"contingency category, got {budget_cells}"
        )

    def test_budget_input_has_no_name_attribute(self):
        """Evidence for the preview-only decision: the new <input> must
        not be submittable by any HTML form post."""
        project_code = _create_user_project("no-name-attr")
        html = _get_opex_sheet_html(project_code)

        # Find the OPEX grid block and confirm any budget <input> there
        # carries no name= attribute.
        opex_grid_start = html.find('data-fc-grid="opex"')
        assert opex_grid_start != -1
        opex_grid_html = html[opex_grid_start: opex_grid_start + 200_000]

        inputs = re.findall(r"<input[^>]*class=\"fc-input-native\"[^>]*/?>", opex_grid_html)
        assert inputs, "expected at least one fc-input-native OPEX input"
        for input_tag in inputs:
            assert "name=" not in input_tag, (
                f"OPEX budget input must not carry a name= attribute "
                f"(preview-only, not submitted by Save): {input_tag!r}"
            )

    def test_contingency_budget_cells_remain_read_only(self):
        project_code = _create_user_project_with_contingency()
        html = _get_opex_sheet_html(project_code)

        budget_cells = re.findall(
            r'data-fc-addr="opex!([^"]*)\.budget"[^>]*data-fc-editable="(true|false)"',
            html,
        )
        assert budget_cells, "expected OPEX budget cells in the duplicated project's sheet"

        editable_map = dict(budget_cells)
        contingency_codes = [code for code in editable_map if code.startswith("B.13")]
        assert contingency_codes, "expected a contingency (B.13) line in oborovo's OPEX detail"
        for code in contingency_codes:
            assert editable_map[code] == "false", (
                f"contingency OPEX line {code} must remain read-only, got "
                f"{editable_map[code]!r}"
            )

        non_contingency_codes = [code for code in editable_map if not code.startswith("B.13")]
        assert non_contingency_codes, "expected non-contingency OPEX lines too"
        for code in non_contingency_codes:
            assert editable_map[code] == "true", (
                f"non-contingency OPEX line {code} must be editable, got "
                f"{editable_map[code]!r}"
            )

    def test_subtotal_and_total_rows_remain_read_only(self):
        project_code = _create_user_project("subtotal-readonly")
        html = _get_opex_sheet_html(project_code)

        subtotal_cells = re.findall(
            r'data-fc-addr="opex![^"]*\.subtotal"[^>]*data-fc-editable="(true|false)"',
            html,
        )
        assert subtotal_cells, "expected at least one OPEX category subtotal cell"
        assert all(v == "false" for v in subtotal_cells), (
            "OPEX category subtotal cells must always remain read-only"
        )

    def test_protected_reference_project_stays_fully_read_only(self):
        html = _get_opex_sheet_html("oborovo")

        budget_cells = re.findall(
            r'data-fc-addr="opex![^"]*\.budget"[^>]*data-fc-editable="(true|false)"',
            html,
        )
        assert budget_cells, "expected OPEX budget cells in the protected oborovo sheet"
        assert all(v == "false" for v in budget_cells), (
            "protected/reference project OPEX budget cells must remain read-only"
        )


class TestNoFinancialEngineCallFromOpexSheetRendering:
    def test_no_financial_engine_call_when_rendering_opex_sheet(self, monkeypatch):
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError(
                "waterfall_core.run_project must never be called by rendering "
                "the OPEX detail sheet"
            )

        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)

        project_code = _create_user_project("no-engine-call")
        html = _get_opex_sheet_html(project_code)
        assert 'data-fc-grid="opex"' in html


class TestNoAuthoritativeRunOutputChangeFromOpexRenderAlone:
    def test_rendering_opex_sheet_twice_is_byte_identical_for_budget_values(self):
        """Rendering (which is all "editing + previewing without
        explicitly running" can ever do server-side, since the new
        input has no name= and is never submitted) must never mutate
        the authoritative budget values backing the sheet."""
        project_code = _create_user_project("render-idempotent")
        html_1 = _get_opex_sheet_html(project_code)
        html_2 = _get_opex_sheet_html(project_code)

        budgets_1 = re.findall(r'data-fc-addr="opex![^"]*\.budget"[^>]*data-fc-raw="([^"]*)"', html_1)
        budgets_2 = re.findall(r'data-fc-addr="opex![^"]*\.budget"[^>]*data-fc-raw="([^"]*)"', html_2)
        assert budgets_1 == budgets_2
        assert budgets_1, "expected at least one OPEX budget value"


class TestSaveDoesNotPersistOpexLineEdits:
    def test_save_run_form_snapshot_has_no_per_line_opex_field(self):
        """Direct proof of the preview-only decision: the form-snapshot
        field list that /save-run reads (`_collect_form_snapshot`) has
        no per-child-code OPEX field (no `opex_{code}_keur` analogous
        to CAPEX's `capex_{code}_keur`), so even if a client crafted a
        raw POST with such a field, the save route would never read
        it. Combined with the fact that the new <input> has no name=
        attribute at all (test_budget_input_has_no_name_attribute
        above), this proves an OPEX budget edit cannot reach
        persistence via the existing Save action."""
        import inspect
        import main_web as main_web_module

        source = inspect.getsource(main_web_module._collect_form_snapshot)
        # The per-line CAPEX convention IS present (capex_<code>_keur).
        assert "capex_epc_contract_keur" in source
        # No per-child-code OPEX equivalent (e.g. a field built from
        # child.code, like "opex_OM-01_keur") exists in the snapshot
        # field list.
        assert "opex_OM" not in source
        assert re.search(r'"opex_[A-Za-z0-9_]+_keur"', source.replace("_y1_keur", "_YEARONE_KEUR_PLACEHOLDER")) is None, (
            "found an unexpected per-line OPEX keur field in "
            "_collect_form_snapshot's field list; if a real per-line "
            "OPEX save binding now exists, update "
            "docs/C2_PR17_OPEX_LINE_EDITABILITY_BRIDGE.md and this "
            "test to reflect the new persistence behaviour instead "
            "of asserting its absence"
        )

    def test_opex_budget_input_not_named_means_not_form_submitted(self):
        """End-to-end structural proof: simulate what a real browser
        form submission would contain by parsing the rendered OPEX
        input tag and confirming it has no name=, so
        request.form()/_collect_form_snapshot can never see an OPEX
        per-line edit regardless of which fields the snapshot reads."""
        project_code = _create_user_project("save-noop-check")
        html = _get_opex_sheet_html(project_code)

        opex_grid_start = html.find('data-fc-grid="opex"')
        opex_grid_html = html[opex_grid_start: opex_grid_start + 200_000]
        inputs = re.findall(r"<input[^>]*class=\"fc-input-native\"[^>]*/?>", opex_grid_html)
        assert inputs
        for input_tag in inputs:
            name_match = re.search(r'name="([^"]*)"', input_tag)
            assert name_match is None, (
                f"unexpected name= attribute on OPEX budget input: {input_tag!r}; "
                f"an HTML form submission WOULD include this field, contradicting "
                f"the preview-only persistence decision"
            )
