"""C2-PR18: Preview-Only OPEX Governance — route-level backend tests.

Covers the required-behaviour points from the C2-PR18 task spec:

  1. The plain-language "preview-only" note is visible on the rendered
     OPEX sheet.
  2. The note does NOT appear on the rendered CAPEX, Revenue, or
     Overview sheet panels.
  3. No internal jargon ("C1", "C2", "PR17", "PR18", etc.) appears in
     the rendered OPEX sheet panel's visible text.
  4. The OPEX Budget <input> cells still have no name= attribute
     (regression check, mirrors tests/test_c2_pr17_opex_line_editability.py).
  5. Save still does not persist OPEX line edits (regression check —
     already covered thoroughly by
     tests/test_c2_pr17_opex_line_editability.py::TestSaveDoesNotPersistOpexLineEdits;
     this file adds one more direct confirmation that the relevant
     PR17 tests still hold under this PR's template change).

Uses fastapi.testclient.TestClient against the real main_web.app,
mirroring tests/test_c2_pr17_opex_line_editability.py's pattern.
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

NOTE_TEXT_FRAGMENT = "preview-only for now"

JARGON_TERMS = ["C1", "C2", "PR17", "PR18", "PR19", "PR20", "preview pipeline", "dependency graph"]


def _auth_cookies():
    token = create_session_token()
    return {COOKIE_NAME: token}


def _create_user_project(name_suffix):
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"C2 PR18 OPEX Governance {name_suffix}",
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


def _get_full_page_html(project_code):
    resp = client.get(f"/?project={project_code}", cookies=_auth_cookies())
    assert resp.status_code == 200
    return resp.text


def _extract_panel(html, panel_id):
    """Extract the HTML for a single tab-panel div by id, using the
    next sibling tab-panel's opening tag as the boundary. This is a
    simple, good-enough scoping mechanism given the page's flat
    sequence of <div class="tab-panel" id="panel-..."> blocks."""
    start_marker = f'id="{panel_id}"'
    start = html.find(start_marker)
    assert start != -1, f"expected to find panel {panel_id!r} in rendered page"
    # Back up to the start of this div's opening tag.
    div_start = html.rfind("<div", 0, start)
    # Find the next tab-panel div after this one as the end boundary.
    next_panel = html.find('class="tab-panel"', start + len(start_marker))
    if next_panel == -1:
        return html[div_start:]
    next_div_start = html.rfind("<div", 0, next_panel)
    return html[div_start:next_div_start]


class TestPreviewOnlyNoteVisibleOnOpexSheet:
    def test_note_appears_on_opex_sheet(self):
        project_code = _create_user_project("note-visible")
        html = _get_full_page_html(project_code)
        opex_panel = _extract_panel(html, "panel-opex")
        assert NOTE_TEXT_FRAGMENT in opex_panel, (
            "expected the preview-only governance note inside the OPEX panel"
        )
        assert "not saved yet" in opex_panel
        assert "Run uses the saved model inputs" in opex_panel


class TestPreviewOnlyNoteAbsentElsewhere:
    def test_note_absent_from_capex_panel(self):
        project_code = _create_user_project("note-absent-capex")
        html = _get_full_page_html(project_code)
        capex_panel = _extract_panel(html, "panel-capex")
        assert NOTE_TEXT_FRAGMENT not in capex_panel
        assert "opex-preview-only-note" not in capex_panel

    def test_note_absent_from_revenue_panel(self):
        project_code = _create_user_project("note-absent-revenue")
        html = _get_full_page_html(project_code)
        revenue_panel = _extract_panel(html, "panel-revenue")
        assert NOTE_TEXT_FRAGMENT not in revenue_panel
        assert "opex-preview-only-note" not in revenue_panel

    def test_note_absent_from_overview_panel(self):
        project_code = _create_user_project("note-absent-overview")
        html = _get_full_page_html(project_code)
        overview_panel = _extract_panel(html, "panel-overview")
        assert NOTE_TEXT_FRAGMENT not in overview_panel
        assert "opex-preview-only-note" not in overview_panel


class TestNoInternalJargonInOpexVisibleText:
    def test_no_jargon_terms_in_opex_panel_visible_text(self):
        project_code = _create_user_project("no-jargon")
        html = _get_full_page_html(project_code)
        opex_panel = _extract_panel(html, "panel-opex")

        # Strip HTML tags/attributes to approximate "visible text only"
        # — comments and any data-* attribute values that happen to
        # contain a jargon-like substring (there are none currently)
        # would not affect this check either way, since we strip all
        # markup before searching.
        visible_text = re.sub(r"<!--.*?-->", " ", opex_panel, flags=re.S)
        # Strip <style>/<script> blocks entirely first: their contents
        # (CSS rules, JS code/comments) are never user-visible text,
        # even though they're not HTML comments either.
        visible_text = re.sub(r"<style[^>]*>.*?</style>", " ", visible_text, flags=re.S | re.I)
        visible_text = re.sub(r"<script[^>]*>.*?</script>", " ", visible_text, flags=re.S | re.I)
        visible_text = re.sub(r"<[^>]*>", " ", visible_text)

        for term in JARGON_TERMS:
            assert term not in visible_text, (
                f"found internal jargon term {term!r} in OPEX sheet visible text"
            )


class TestRegressionOpexBudgetInputHasNoNameAttribute:
    def test_budget_input_has_no_name_attribute(self):
        """Regression mirror of
        tests/test_c2_pr17_opex_line_editability.py::test_budget_input_has_no_name_attribute,
        confirming PR18's template addition did not disturb PR17's
        editability/no-name-attribute behaviour."""
        project_code = _create_user_project("no-name-attr-regression")
        html = _get_full_page_html(project_code)

        opex_grid_start = html.find('data-fc-grid="opex"')
        assert opex_grid_start != -1
        opex_grid_html = html[opex_grid_start: opex_grid_start + 200_000]

        inputs = re.findall(r"<input[^>]*class=\"fc-input-native\"[^>]*/?>", opex_grid_html)
        assert inputs, "expected at least one fc-input-native OPEX input"
        for input_tag in inputs:
            assert "name=" not in input_tag, (
                f"OPEX budget input must not carry a name= attribute: {input_tag!r}"
            )


class TestRegressionSaveDoesNotPersistOpexEdits:
    def test_save_run_form_snapshot_still_has_no_per_line_opex_field(self):
        """Regression mirror confirming PR17's persistence boundary
        (no per-child-code opex_{code}_keur field in
        _collect_form_snapshot) still holds after PR18's purely
        template/UX-copy change."""
        import inspect
        import main_web as main_web_module

        source = inspect.getsource(main_web_module._collect_form_snapshot)
        assert "capex_epc_contract_keur" in source
        assert "opex_OM" not in source
