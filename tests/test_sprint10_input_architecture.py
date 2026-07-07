"""
Sprint 10 — Model Input Architecture guardrails (PR-1, PR-2, PR-3).

PR-1: Schedule & Duration inputs use type="number" with unit suffixes
PR-2: Technical section restructured (no misleading P50/P90/P10 row, template badges)
PR-3: Revenue sheet has contract-based offtake structure
"""

from pathlib import Path

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# PR-1: Numeric inputs with unit suffixes
# ---------------------------------------------------------------------------

def test_inputs_section_has_input_group_css_class():
    src = _read("app/templates/partials/inputs_section.html")
    assert "inp-input-group" in src, \
        "inputs_section.html: .inp-input-group wrapper not found — numeric inputs not wrapped"


def test_inputs_section_has_unit_suffix_class():
    src = _read("app/templates/partials/inputs_section.html")
    assert "inp-unit" in src, \
        "inputs_section.html: .inp-unit span not found — unit suffix not rendered"


def test_inputs_section_field_row_supports_number_type():
    src = _read("app/templates/partials/inputs_section.html")
    assert 'input_type="number"' in src or "input_type" in src, \
        "inputs_section.html: field_row macro does not support input_type parameter"


def test_styles_has_input_group_rule():
    src = _read("static/styles.css")
    assert ".inp-input-group" in src, \
        "styles.css: .inp-input-group CSS rule missing — numeric inputs won't lay out correctly"


def test_styles_has_unit_rule():
    src = _read("static/styles.css")
    assert ".inp-unit" in src, \
        "styles.css: .inp-unit CSS rule missing"


def test_inputs_section_project_life_is_numeric():
    src = _read("app/templates/partials/inputs_section.html")
    # Project Life / Construction / Operation fields must use type="number"
    assert 'input_type="number"' in src, \
        "inputs_section.html: no number-type field_row calls found"


def test_inputs_section_no_prose_years_field():
    """Prose 'years' fields like '18 months' must be replaced with numeric inputs."""
    src = _read("app/templates/partials/inputs_section.html")
    # The old 'type="text"' for schedule fields must be gone — they're now type="number"
    # Check that unit suffixes are embedded, not left as freeform text inside the value
    assert "inp-unit" in src, \
        "inputs_section.html: unit suffix span missing — schedule fields may still be prose"


# ---------------------------------------------------------------------------
# PR-2: Technical section restructured
# ---------------------------------------------------------------------------

def test_inputs_section_no_p90_p10_misleading_row():
    src = _read("app/templates/partials/inputs_section.html")
    # The old row "P90 / P10 Hours = P50 * factor" was misleading — must be gone
    assert "P90 / P10 Hours" not in src, \
        "inputs_section.html: misleading 'P90 / P10 Hours' row still present"


def test_inputs_section_has_p50_annual_yield():
    src = _read("app/templates/partials/inputs_section.html")
    assert "P50 Annual Yield" in src or "p50_annual_yield" in src or "annual_yield" in src.lower(), \
        "inputs_section.html: P50 Annual Yield derived row not present"


def test_inputs_section_has_template_badge_for_availability():
    src = _read("app/templates/partials/inputs_section.html")
    assert "Template" in src, \
        "inputs_section.html: 'Template' badge missing — availability/degradation defaults not labelled"


def test_inputs_section_has_annual_degradation():
    src = _read("app/templates/partials/inputs_section.html")
    assert "Degradation" in src or "degradation" in src, \
        "inputs_section.html: Annual Degradation row missing from Technical section"


# ---------------------------------------------------------------------------
# PR-3: Revenue — contract-based offtake structure
# ---------------------------------------------------------------------------

def test_revenue_sheet_has_production_section():
    src = _read("app/templates/partials/sheet_revenue.html")
    assert "Production" in src, \
        "sheet_revenue.html: Production section missing"


def test_revenue_sheet_has_offtake_contracts_section():
    src = _read("app/templates/partials/sheet_revenue.html")
    assert "Offtake Contracts" in src, \
        "sheet_revenue.html: Offtake Contracts section missing"


def test_revenue_sheet_has_contract1_block():
    src = _read("app/templates/partials/sheet_revenue.html")
    assert "Contract 1" in src, \
        "sheet_revenue.html: Contract 1 block missing"


def test_revenue_sheet_has_contract2_disabled():
    src = _read("app/templates/partials/sheet_revenue.html")
    assert "Contract 2" in src, \
        "sheet_revenue.html: Contract 2 placeholder missing"
    assert "Not configured" in src or "disabled" in src.lower(), \
        "sheet_revenue.html: Contract 2 not shown as disabled/not configured"


def test_revenue_sheet_no_internal_group_column():
    src = _read("app/templates/partials/sheet_revenue.html")
    # The old flat table had a 'Group' column header — new design uses sections
    assert "<th" not in src or "Group" not in src, \
        "sheet_revenue.html: old 'Group' column header still present — section-based layout not applied"


def test_revenue_sheet_has_co2_section():
    src = _read("app/templates/partials/sheet_revenue.html")
    assert "CO" in src and "Certificates" in src or "co2" in src.lower(), \
        "sheet_revenue.html: CO₂ / Certificates section missing"


def test_revenue_sheet_has_revenue_summary():
    src = _read("app/templates/partials/sheet_revenue.html")
    assert "Revenue Summary" in src, \
        "sheet_revenue.html: Revenue Summary section missing"


def test_revenue_sheet_offtake_badge_logic():
    src = _read("app/templates/partials/sheet_revenue.html")
    assert "Indexed PPA" in src or "ppa_index_pct" in src, \
        "sheet_revenue.html: Indexed PPA / Fixed PPA badge logic missing"
    assert "Fixed PPA" in src, \
        "sheet_revenue.html: Fixed PPA badge missing"


def test_revenue_sheet_contract2_honest_notice():
    src = _read("app/templates/partials/sheet_revenue.html")
    # Must acknowledge this is a limitation, not just blank
    assert "second" in src.lower() or "future" in src.lower(), \
        "sheet_revenue.html: Contract 2 notice doesn't acknowledge the limitation honestly"
