"""C2-PR21: Operating Preview Panel — route-level backend tests.

Covers the required-behaviour points from the C2-PR21 task spec:

  1. The Operating Preview Panel renders on the Overview tab with the
     exact heading text "Operating preview (unsaved)" and the exact
     explanatory copy "These values are live previews only. Save/Run
     and exports use the saved model."
  2. All five preview value element IDs
     (#capex-total-preview-value, #revenue-total-preview-value,
     #opex-total-preview-value, #ebitda-preview-value,
     #operating-cf-preview-value) still exist, unchanged, inside the
     panel (regression — these IDs are load-bearing for
     static/modelling/runtime-renderer.js).
  3. No internal jargon ("C1", "C2", "PR10".."PR23", "preview
     pipeline", "dependency graph", etc.) appears in the new panel's
     own heading/copy text.
  4. Accessibility attributes (role="status", aria-live, aria-busy,
     sr-only label spans) remain present on all five indicators.
  5. The panel lives inside panel-overview (not duplicated elsewhere)
     and does not appear inside the CAPEX/Revenue/OPEX tab panels.

Uses fastapi.testclient.TestClient against the real main_web.app,
mirroring tests/test_c2_pr18_opex_preview_only_governance.py's pattern
(including its `_extract_panel` helper).
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

PANEL_HEADING = "Operating preview (unsaved)"
PANEL_COPY = "These values are live previews only. Save/Run and exports use the saved model."

FIVE_VALUE_IDS = [
    "capex-total-preview-value",
    "revenue-total-preview-value",
    "opex-total-preview-value",
    "ebitda-preview-value",
    "operating-cf-preview-value",
]

FIVE_REGION_IDS = [
    "capex-total-preview",
    "revenue-total-preview",
    "opex-total-preview",
    "ebitda-preview",
    "operating-cf-preview",
]

FIVE_SR_IDS = [
    "capex-total-preview-sr",
    "revenue-total-preview-sr",
    "opex-total-preview-sr",
    "ebitda-preview-sr",
    "operating-cf-preview-sr",
]

JARGON_TERMS = [
    "C1", "C2",
    "PR10", "PR11", "PR12", "PR13", "PR14", "PR15", "PR16", "PR17",
    "PR18", "PR19", "PR20", "PR21", "PR22", "PR23",
    "preview pipeline", "dependency graph",
]


def _auth_cookies():
    token = create_session_token()
    return {COOKIE_NAME: token}


def _create_user_project(name_suffix):
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"C2 PR21 Operating Preview Panel {name_suffix}",
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


_PROJECT_CODE = None


def _get_full_page_html(project_code=None):
    global _PROJECT_CODE
    if project_code is None:
        if _PROJECT_CODE is None:
            _PROJECT_CODE = _create_user_project("shared")
        project_code = _PROJECT_CODE
    resp = client.get(f"/?project={project_code}", cookies=_auth_cookies())
    assert resp.status_code == 200
    return resp.text


def _extract_panel(html, panel_id):
    """Extract the HTML for a single tab-panel div by id, using the
    next sibling tab-panel's opening tag as the boundary. Mirrors
    tests/test_c2_pr18_opex_preview_only_governance.py's helper
    exactly."""
    start_marker = f'id="{panel_id}"'
    start = html.find(start_marker)
    assert start != -1, f"expected to find panel {panel_id!r} in rendered page"
    div_start = html.rfind("<div", 0, start)
    next_panel = html.find('class="tab-panel"', start + len(start_marker))
    if next_panel == -1:
        return html[div_start:]
    next_div_start = html.rfind("<div", 0, next_panel)
    return html[div_start:next_div_start]


def _visible_text(html_fragment):
    text = re.sub(r"<!--.*?-->", " ", html_fragment, flags=re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]*>", " ", text)
    return text


class TestOperatingPreviewPanelHeadingAndCopy:
    def test_exact_heading_text_present(self):
        html = _get_full_page_html()
        overview_panel = _extract_panel(html, "panel-overview")
        assert PANEL_HEADING in overview_panel

    def test_exact_explanatory_copy_present(self):
        html = _get_full_page_html()
        overview_panel = _extract_panel(html, "panel-overview")
        assert PANEL_COPY in overview_panel

    def test_panel_wrapper_element_present(self):
        html = _get_full_page_html()
        assert 'id="operating-preview-panel"' in html
        assert 'class="operating-preview-panel"' in html


class TestFivePreviewValueIdsStillPresent:
    """Regression: the five element IDs static/modelling/runtime-renderer.js
    targets must still exist, unrenamed, unremoved."""

    def test_all_five_value_ids_present(self):
        html = _get_full_page_html()
        for value_id in FIVE_VALUE_IDS:
            assert f'id="{value_id}"' in html, f"missing element id={value_id!r}"

    def test_all_five_region_ids_present(self):
        html = _get_full_page_html()
        for region_id in FIVE_REGION_IDS:
            assert f'id="{region_id}"' in html, f"missing element id={region_id!r}"

    def test_all_five_sr_only_label_ids_present(self):
        html = _get_full_page_html()
        for sr_id in FIVE_SR_IDS:
            assert f'id="{sr_id}"' in html, f"missing element id={sr_id!r}"

    def test_all_five_value_ids_are_inside_the_panel(self):
        html = _get_full_page_html()
        panel_start = html.find('id="operating-preview-panel"')
        assert panel_start != -1
        # The panel div's closing boundary is the next "Runtime summary
        # HTMX swap target" marker comment that has always immediately
        # followed these five indicators.
        panel_end = html.find('id="model-output-area"', panel_start)
        assert panel_end != -1
        panel_html = html[panel_start:panel_end]
        for value_id in FIVE_VALUE_IDS:
            assert f'id="{value_id}"' in panel_html, (
                f"expected {value_id!r} inside the operating preview panel"
            )


class TestAccessibilityAttributesPreserved:
    def test_role_status_and_aria_live_preserved_on_all_five(self):
        html = _get_full_page_html()
        for region_id in FIVE_REGION_IDS:
            marker = f'id="{region_id}"'
            idx = html.find(marker)
            assert idx != -1
            # Look at the opening tag containing this id.
            tag_start = html.rfind("<div", 0, idx)
            tag_end = html.find(">", idx)
            tag = html[tag_start:tag_end + 1]
            assert 'role="status"' in tag, f"{region_id} missing role=status"
            assert 'aria-live="polite"' in tag, f"{region_id} missing aria-live"
            assert "aria-busy=" in tag, f"{region_id} missing aria-busy"
            assert "aria-label=" in tag, f"{region_id} missing aria-label"


class TestNoInternalJargonInPanelCopy:
    def test_no_jargon_terms_in_new_panel_heading_and_copy(self):
        html = _get_full_page_html()
        panel_start = html.find('id="operating-preview-panel"')
        header_end = html.find("operating-preview-panel__desc")
        header_end = html.find("</div>", header_end)
        header_fragment = html[panel_start:header_end]
        visible = _visible_text(header_fragment)
        for term in JARGON_TERMS:
            assert term not in visible, (
                f"found internal jargon term {term!r} in the new panel's heading/copy"
            )
        # Sanity: the exact heading/copy text must still be there after
        # stripping markup (proves the fragment boundary is correct).
        assert PANEL_HEADING in visible
        assert PANEL_COPY in visible


class TestPanelNotDuplicatedOutsideOverview:
    def test_panel_heading_absent_from_capex_panel(self):
        html = _get_full_page_html()
        capex_panel = _extract_panel(html, "panel-capex")
        assert PANEL_HEADING not in capex_panel
        assert 'id="operating-preview-panel"' not in capex_panel

    def test_panel_heading_absent_from_revenue_panel(self):
        html = _get_full_page_html()
        revenue_panel = _extract_panel(html, "panel-revenue")
        assert PANEL_HEADING not in revenue_panel
        assert 'id="operating-preview-panel"' not in revenue_panel

    def test_panel_heading_absent_from_opex_panel(self):
        html = _get_full_page_html()
        opex_panel = _extract_panel(html, "panel-opex")
        assert PANEL_HEADING not in opex_panel
        assert 'id="operating-preview-panel"' not in opex_panel
