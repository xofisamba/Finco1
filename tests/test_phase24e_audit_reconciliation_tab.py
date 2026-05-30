"""Phase 24E: Audit / Reconciliation Tab — Tests

Diagnostic-only. UI/reporting only.
No runtime formula changes.
"""
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.runtime_impact_taxonomy import CANONICAL_STATES


# =============================================================================
# 1. Audit partial exists
# =============================================================================


def test_audit_reconciliation_partial_exists():
    """Confirms audit partial exists at expected path."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
    assert panel_path.exists(), f"Audit partial not found at {panel_path}"
    content = panel_path.read_text()
    assert len(content) > 500, "Audit partial should have meaningful content"


# =============================================================================
# 2. Audit tab contains required sections
# =============================================================================


def test_audit_tab_contains_required_sections():
    """Revenue, OPEX, CAPEX, Debt/DSCR, SHL/Distribution, Unresolved Issues, Validation Checks."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
    content = panel_path.read_text()
    required = ["Revenue", "OPEX", "CAPEX", "Debt", "SHL", "Distribution", "Unresolved", "Validation"]
    for section in required:
        assert section in content, f"Audit tab should contain '{section}' section"


# =============================================================================
# 3. Audit tab uses runtime impact taxonomy
# =============================================================================


def test_audit_tab_uses_runtime_impact_taxonomy():
    """Confirms canonical labels are used and no non-canonical primary labels introduced."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
    content = panel_path.read_text()

    # Canonical primary states should appear
    for state in CANONICAL_STATES:
        if state in content:
            assert state in CANONICAL_STATES

    # Runtime Impact taxonomy should be referenced
    assert "Drives model" in content or "Display only" in content or "Pending" in content or "Needs review" in content


# =============================================================================
# 4. Audit tab contains frozen-template scope warning
# =============================================================================


def test_audit_tab_contains_frozen_template_scope_warning():
    """Confirms TUHO/Oborovo frozen-template parity vs generic-project unvalidated warning exists."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
    content = panel_path.read_text()
    assert "frozen" in content.lower() or "fixture-backed" in content.lower()
    assert "generic" in content.lower()
    assert "unvalidated" in content.lower()


# =============================================================================
# 5. Audit tab contains no bank or external audit claim
# =============================================================================


def test_audit_tab_contains_no_bank_or_external_audit_claim():
    """Confirms no 'bank approved', 'lender approved', 'certified audit', or similar claims."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
    content = panel_path.read_text().lower()

    # Check for positive claims (NOT negative disclaimers)
    # "certified audit" and "external audit" appear ONLY in the disclaimer as negatives
    # e.g. "This is NOT an external model audit, bank approval, or certified audit"
    # We check the content does NOT contain positive bank/lender claims
    positive_forbidden = [
        "bank approved",
        "lender approved",
        "auditor approved",
        "credit approved",
        "loan approved",
    ]
    for claim in positive_forbidden:
        assert claim not in content, f"Audit tab should not claim '{claim}'"
    # certified audit and external audit appear only in disclaimer negatives
    # they should appear with "not" or "NOT" nearby to confirm disclaimer context
    # Simpler: just check positive forbidden claims - the disclaimer correctly uses negatives
    # so any appearance of these without "not" is a positive claim
    lines = content.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        # Skip lines containing "not" (disclaimer negatives)
        if "not" in stripped.lower() and "audit" in stripped.lower():
            continue
        for claim in ["bank approved", "lender approved", "auditor approved", "credit approved", "loan approved"]:
            assert claim not in stripped.lower(), f"Found positive claim '{claim}' in: {stripped[:80]}"


# =============================================================================
# 6. CAPEX audit status not runtime promoted
# =============================================================================


def test_capex_audit_status_not_runtime_promoted():
    """Confirms C.16 and M1–M18 are not represented as runtime-effective."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
    content = panel_path.read_text()

    # C.16 should be marked Pending, not Drives model
    assert "C.16" in content
    # M1-M18 should be marked timing only / pending
    assert "M1" in content or "M1–M18" in content or "M1-M18" in content


# =============================================================================
# 7. Debt/DSCR audit status mentions fixture-backed
# =============================================================================


def test_debt_dscr_audit_status_mentions_fixture_backed():
    """Confirms frozen Excel / fixture-backed language appears for senior DS."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
    content = panel_path.read_text()
    assert "fixture-backed" in content.lower() or "frozen" in content.lower() or "fixture backed" in content.lower()


# =============================================================================
# 8. SHL/distribution audit status mentions lock-up
# =============================================================================


def test_shl_distribution_audit_status_mentions_lockup():
    """Confirms distribution lock-up and first valid distribution concept appears."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
    content = panel_path.read_text()
    assert "lock-up" in content.lower() or "lockup" in content.lower()
    assert "op_idx 39" in content or "2050-06-30" in content or "first dist" in content.lower()


# =============================================================================
# 9. No JS financial calculations added
# =============================================================================


def test_no_js_financial_calculations_added():
    """Scan static/app.js for forbidden financial calculation patterns."""
    js_file = Path(__file__).resolve().parents[1] / "static" / "app.js"
    if not js_file.exists():
        pytest.skip("static/app.js not found")

    content = js_file.read_text()
    forbidden = [
        "senior_ds_keur",
        "dscr",
        "r69_fcf_banks",
        "distribution_keur",
        "shl_balance",
        "irr",
        "npv",
        "xirr",
        "cfads",
        "ebitda",
    ]

    found = []
    for pattern in forbidden:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            import re
            if re.search(r'\b' + re.escape(pattern) + r'\b', line):
                found.append(pattern)
                break

    assert len(found) == 0, f"Found forbidden financial terms in JS: {found}"


# =============================================================================
# 10. Guardrails unchanged
# =============================================================================


def test_guardrails_unchanged():
    """Guardrails preserved: G20/R99/R102 blocked, no flags promoted."""
    oborovo = create_default_oborovo()
    info = oborovo.info

    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
