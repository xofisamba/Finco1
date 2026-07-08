"""
Sprint 14C — Scenarios matrix guardrails.

Verifies:
- Scenario tab has section groups (Technical, Revenue, CAPEX, OPEX, Debt)
- Preset scenario buttons present (Downside, Upside, Bank Case, Custom)
- Matrix header is labeled as "Scenario Input Matrix"
- Base Case column rendered
- Matrix is not a blank/report-like page
"""
from pathlib import Path

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_scenario_matrix_header():
    src = _read("app/templates/partials/scenario_tab.html")
    assert "Scenario Input Matrix" in src, \
        "scenario_tab.html: 'Scenario Input Matrix' heading missing"


def test_preset_scenario_buttons_present():
    src = _read("app/templates/partials/scenario_tab.html")
    for preset in ["Downside", "Upside", "Bank Case", "Custom"]:
        assert preset in src, \
            f"scenario_tab.html: preset scenario button '{preset}' missing"


def test_scenario_matrix_table_present():
    src = _read("app/templates/partials/scenario_tab.html")
    assert "sc-matrix" in src, \
        "scenario_tab.html: .sc-matrix table missing"


def test_scenario_section_groups_in_editable_fields():
    """SCENARIO_EDITABLE_FIELDS in main_web.py must contain key groups."""
    src = _read("main_web.py")
    for group in ["Technical", "Revenue", "CAPEX", "OPEX", "Financing"]:
        assert f'("{group}' in src or f"('{group}" in src, \
            f"main_web.py: SCENARIO_EDITABLE_FIELDS missing '{group}' group"


def test_scenario_tab_has_base_case_column():
    src = _read("app/templates/partials/scenario_tab.html")
    assert "base_case_record" in src, \
        "scenario_tab.html: Base Case column logic missing"
    assert "sc-th--base" in src, \
        "scenario_tab.html: sc-th--base column header class missing"


def test_scenario_tab_is_not_blank():
    src = _read("app/templates/partials/scenario_tab.html")
    # Must have actual content (table + controls), not just a placeholder
    assert "<table" in src, "scenario_tab.html: no table element"
    assert "sc-add-form" in src, "scenario_tab.html: add scenario form missing"


def test_preset_css_present():
    css = _read("static/styles.css")
    assert "sc-preset-row" in css, \
        "styles.css: .sc-preset-row CSS missing for preset buttons"
