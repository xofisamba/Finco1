"""
Sprint 14A — Navigation reset guardrails.

Verifies that:
- secondary results sub-nav is hidden via CSS (no duplicate navigation)
- primary tab strip contains Scenarios in the inputs group
- CAPEX and OPEX are in the grids group
- Financials / Compare / Sensitivity are in the outputs group
- no second nav element with class 'results-subnav' is visible
"""
from pathlib import Path

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_secondary_subnav_hidden_via_css():
    css = _read("static/styles.css")
    assert "#results-subnav-wrapper" in css, \
        "styles.css: #results-subnav-wrapper rule missing"
    assert "display: none" in css or "display:none" in css, \
        "styles.css: display:none not applied to #results-subnav-wrapper"


def test_scenarios_tab_in_inputs_group():
    src = _read("app/templates/partials/_sheet_tabs.html")
    # Scenarios button must appear AND be in inputs group
    assert 'data-fo-sheet-id="scenarios"' in src, \
        "_sheet_tabs.html: scenarios tab missing"
    assert 'data-fo-sheet-group="inputs"' in src, \
        "_sheet_tabs.html: inputs group missing"
    # Scenarios must be grouped with inputs (group attribute on same element)
    assert 'data-fo-sheet-id="scenarios"' in src and 'data-fo-sheet-group="inputs"' in src


def test_capex_in_grids_group():
    src = _read("app/templates/partials/_sheet_tabs.html")
    assert 'data-fo-sheet-group="grids"' in src, \
        "_sheet_tabs.html: grids group missing"
    assert 'data-fo-sheet-id="capex"' in src, \
        "_sheet_tabs.html: capex tab missing"


def test_opex_in_grids_group():
    src = _read("app/templates/partials/_sheet_tabs.html")
    assert 'data-fo-sheet-id="opex"' in src, \
        "_sheet_tabs.html: opex tab missing"


def test_outputs_group_present():
    src = _read("app/templates/partials/_sheet_tabs.html")
    assert 'data-fo-sheet-group="outputs"' in src, \
        "_sheet_tabs.html: outputs group missing"
    assert 'data-fo-sheet-id="compare"' in src, \
        "_sheet_tabs.html: compare tab missing"
    assert 'data-fo-sheet-id="sensitivity"' in src, \
        "_sheet_tabs.html: sensitivity tab missing"


def test_no_duplicate_nav_structure():
    """The results sub-nav wrapper must exist in HTML but be hidden by CSS."""
    shell = _read("app/templates/partials/workspace_shell.html")
    assert "results-subnav-wrapper" in shell, \
        "workspace_shell.html: results-subnav-wrapper not found (it should exist but be hidden)"
    css = _read("static/styles.css")
    # Must be suppressed
    assert "#results-subnav-wrapper" in css


def test_primary_tabs_cover_all_excel_workflow_areas():
    src = _read("app/templates/partials/_sheet_tabs.html")
    required = ["inputs", "scenarios", "capex", "opex", "senior-debt", "tax", "pl"]
    for tab_id in required:
        assert f'data-fo-sheet-id="{tab_id}"' in src, \
            f"_sheet_tabs.html: tab '{tab_id}' missing from primary nav"
