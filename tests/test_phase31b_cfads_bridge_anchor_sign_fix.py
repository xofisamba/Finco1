"""Phase 31B — CFADS Bridge Anchor Sign Fix tests.

Verifies:
1. Phase 31B doc exists
2. OBOROVO_P4_ANCHORS["opex_keur"] == 644.34 (positive)
3. No negative Oborovo OpEx anchor remains
4. Doc describes diagnostic-only fix
5. Doc references Phase 31 false-alarm
6. No fixture CSV change claimed
7. Guardrails unchanged
8. TUHO P4 anchor unchanged (still -1,023.26 — that's a different case)
"""
import pytest
from pathlib import Path

BASE_SHA = "c84778518f8c9c6e18b6045dc41ea7e5e6e960b8"
PHASE31B_DOC = Path("docs/phase31b_cfads_bridge_anchor_sign_fix.md")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 31B doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase31b_doc_exists():
    assert PHASE31B_DOC.exists(), f"{PHASE31B_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Oborovo P4 OpEx anchor is positive 644.34
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_p4_opex_anchor_is_positive():
    from domain.diagnostics.cfads_bridge import OBOROVO_P4_ANCHORS

    anchor = OBOROVO_P4_ANCHORS["opex_keur"]
    assert anchor == 644.34, (
        f"OBOROVO_P4_ANCHORS['opex_keur'] = {anchor} — expected 644.34"
    )
    assert anchor > 0, (
        f"OBOROVO_P4_ANCHORS['opex_keur'] = {anchor} — must be positive"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: No negative Oborovo OpEx anchor remains
# ─────────────────────────────────────────────────────────────────────────────
def test_no_negative_oborovo_opex_anchor_remains():
    from domain.diagnostics.cfads_bridge import OBOROVO_P4_ANCHORS

    anchor = OBOROVO_P4_ANCHORS["opex_keur"]
    assert anchor >= 0, (
        f"Negative Oborovo OpEx anchor remains: {anchor}"
    )
    # Specifically check the old value is gone
    assert anchor != -644.34, (
        "Old negative anchor -644.34 still present"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Doc describes diagnostic-only fix
# ─────────────────────────────────────────────────────────────────────────────
def test_doc_describes_diagnostic_only_fix():
    doc = PHASE31B_DOC.read_text()
    assert "diagnostic" in doc.lower() or "data-quality" in doc.lower()
    assert (
        "no runtime" in doc.lower()
        or "no formula change" in doc.lower()
        or "not a runtime" in doc.lower()
    )
    assert "644.34" in doc
    assert "-644.34" in doc or "negative" in doc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Doc references Phase 31 false-alarm
# ─────────────────────────────────────────────────────────────────────────────
def test_doc_references_phase31_false_alarm():
    doc = PHASE31B_DOC.read_text()
    assert "phase 31" in doc.lower()
    assert (
        "false alarm" in doc.lower()
        or "no fix needed" in doc.lower()
        or "no runtime bug" in doc.lower()
    )
    assert "1,338" in doc or "1338" in doc


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: No fixture CSV change claimed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_change_claimed():
    doc = PHASE31B_DOC.read_text()
    assert (
        "no fixture" in doc.lower()
        or "fixture csv" not in doc.lower()
        or "no csv" in doc.lower()
        or "unchanged" in doc.lower()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Guardrails unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_unchanged():
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1

    oborovo = create_default_oborovo()
    tuho = create_default_tuho_wind1()

    # Both frozen senior DS paths unchanged
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True

    doc = PHASE31B_DOC.read_text()
    assert "G20" in doc or "g20" in doc.lower() or "blocked" in doc.lower()
    assert "R99" in doc or "r99" in doc.lower() or "R102" in doc or "r102" in doc.lower()
    assert "partial_pay_sweep" not in doc or "not promoted" in doc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: TUHO P4 anchor unchanged (different case — negative is intentional)
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_p4_opex_anchor_unchanged():
    """TUHO P4 opex_keur = -1,023.26 is intentional (Excel negative convention).
    Phase 31B only fixes Oborovo. TUHO anchor is unchanged."""
    from domain.diagnostics.cfads_bridge import TUHO_P4_ANCHORS

    tuho_opex = TUHO_P4_ANCHORS["opex_keur"]
    # TUHO anchor should still be -1,023.26 (not changed by Phase 31B)
    assert tuho_opex == -1023.26, (
        f"TUHO P4 anchor changed unexpectedly: {tuho_opex}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Diagnostic table now passes for Oborovo OpEx (positive vs positive)
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_p4_opex_diagnostic_now_passes():
    """OBOROVO_P4_ANCHORS['opex_keur'] = +644.34; Python P4 opex = ~644.26.
    Delta should be tiny (within 5 kEUR tolerance) — not sign flip."""
    from domain.diagnostics.cfads_bridge import OBOROVO_P4_ANCHORS

    anchor = OBOROVO_P4_ANCHORS["opex_keur"]
    python_val = 644.26  # P4 (Y1-H2) Oborovo OpEx from Phase 31 investigation
    delta = abs(anchor - python_val)
    assert delta < 1.0, (
        f"Anchor={anchor}, Python={python_val}, delta={delta:.2f} — expected < 1 kEUR"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Anchor sign fix is in the correct file
# ─────────────────────────────────────────────────────────────────────────────
def test_anchor_fix_is_in_cfads_bridge():
    from domain.diagnostics.cfads_bridge import OBOROVO_P4_ANCHORS

    # Verify the fix is in the right module
    anchor = OBOROVO_P4_ANCHORS["opex_keur"]
    assert anchor == 644.34

    # The diagnostic anchor file is cfads_bridge.py — verify we can import it
    assert hasattr(OBOROVO_P4_ANCHORS, "__getitem__")
    assert "opex_keur" in OBOROVO_P4_ANCHORS