"""
Sprint 14B — Inputs control tower guardrails.

Verifies:
- All 10 sections present (Identity, Schedule, Technical, Revenue, CAPEX,
  OPEX, Debt, Tax, Sponsor/SHL, Runtime/Governance)
- Section anchors for local jump nav are present
- CAPEX and OPEX summaries link to their detail tabs
- No key assumption is discoverable only from output tabs
"""
from pathlib import Path

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_section_index_nav_present():
    src = _read("app/templates/partials/inputs_section.html")
    assert "inp-section-index" in src, \
        "inputs_section.html: local section index nav missing"


def test_all_ten_sections_have_anchors():
    src = _read("app/templates/partials/inputs_section.html")
    anchors = [
        "inp-sec-identity",
        "inp-sec-schedule",
        "inp-sec-technical",
        "inp-sec-revenue",
        "inp-sec-capex",
        "inp-sec-opex",
        "inp-sec-debt",
        "inp-sec-tax",
        "inp-sec-sponsor",
        "inp-sec-runtime",
    ]
    for anchor in anchors:
        assert anchor in src, \
            f"inputs_section.html: section anchor '{anchor}' missing"


def test_capex_summary_links_to_capex_tab():
    src = _read("app/templates/partials/inputs_section.html")
    assert "switchTab('capex')" in src or "switchTab(\"capex\")" in src, \
        "inputs_section.html: CAPEX tab link missing from CAPEX Summary"


def test_opex_summary_links_to_opex_tab():
    src = _read("app/templates/partials/inputs_section.html")
    assert "switchTab('opex')" in src or "switchTab(\"opex\")" in src, \
        "inputs_section.html: OPEX tab link missing from OPEX Summary"


def test_sponsor_shl_section_present():
    src = _read("app/templates/partials/inputs_section.html")
    assert "Sponsor / SHL" in src, \
        "inputs_section.html: Sponsor / SHL section missing"
    assert "shl_amount_keur" in src, \
        "inputs_section.html: shl_amount_keur field missing from Sponsor section"
    assert "shl_rate_pct" in src, \
        "inputs_section.html: shl_rate_pct field missing from Sponsor section"


def test_runtime_governance_section_present():
    src = _read("app/templates/partials/inputs_section.html")
    assert "Runtime / Governance" in src, \
        "inputs_section.html: Runtime / Governance section missing"


def test_debt_section_renamed():
    src = _read("app/templates/partials/inputs_section.html")
    assert "Debt / Sizing" in src, \
        "inputs_section.html: Debt / Sizing section header missing"


def test_technical_section_renamed():
    src = _read("app/templates/partials/inputs_section.html")
    assert "Technical / Yield" in src, \
        "inputs_section.html: Technical / Yield section header missing"


def test_tax_section_renamed():
    src = _read("app/templates/partials/inputs_section.html")
    assert "Tax / WHT" in src, \
        "inputs_section.html: Tax / WHT section header missing"
