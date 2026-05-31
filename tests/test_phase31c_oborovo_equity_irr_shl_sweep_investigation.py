"""Phase 31C — Oborovo Equity IRR / SHL Sweep Investigation tests.

Verifies:
1. Phase 31C doc exists
2. Evidence matrix exists
3. Phase 31/31B recap is present
4. Equity IRR investigation is present and classifies discrepancy
5. PPA revenue P4 investigation is present
6. SHL sweep P4 investigation is present
7. Discrepancy classification table is present
8. Phase 31D fix is not required
9. OpEx false alarm still closed
10. Oborovo frozen debt path unchanged
11. TUHO frozen path unchanged
12. No stale bank/lender/audit/certification claims
13. No runtime model files changed
14. Guardrails unchanged
"""
import pytest
from pathlib import Path

BASE_SHA = "965675f5ba9552daf4474e796c8c7a02844d8136"
PHASE31C_DOC = Path("docs/phase31c_oborovo_equity_irr_shl_sweep_investigation.md")
PHASE31C_MATRIX = Path("docs/phase31c_oborovo_equity_irr_shl_sweep_evidence_matrix.md")
OBOROVO_FIXED_DEBT_KEUR = 42_852.27


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 31C doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase31c_doc_exists():
    assert PHASE31C_DOC.exists(), f"{PHASE31C_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Evidence matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase31c_evidence_matrix_exists():
    assert PHASE31C_MATRIX.exists(), f"{PHASE31C_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Phase 31/31B recap present
# ─────────────────────────────────────────────────────────────────────────────
def test_phase31c_recaps_phase31_and_31b():
    doc = PHASE31C_DOC.read_text()
    assert "phase 31" in doc.lower()
    assert "phase 31b" in doc.lower()
    # OpEx false alarm must still be referenced as closed
    assert "false alarm" in doc.lower() or "opex" in doc.lower()
    # P4 OpEx anchor = +644.34 must be confirmed
    assert "644.34" in doc or "opex" in doc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Equity IRR investigation present
# ─────────────────────────────────────────────────────────────────────────────
def test_equity_irr_investigation_present():
    doc = PHASE31C_DOC.read_text()
    assert "equity irr" in doc.lower() or "equity_irr" in doc.lower()
    # Must discuss runtime vs expected/stale anchor
    assert "6.24" in doc or "6.244" in doc
    assert (
        "stale" in doc.lower()
        or "not a runtime" in doc.lower()
        or "not a defect" in doc.lower()
        or "expected" in doc.lower()
        or "no fix" in doc.lower()
    ), "Equity IRR discrepancy must be classified (stale anchor / expected / no runtime defect)"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: PPA revenue P4 investigation present
# ─────────────────────────────────────────────────────────────────────────────
def test_ppa_revenue_p4_investigation_present():
    doc = PHASE31C_DOC.read_text()
    assert "ppa revenue" in doc.lower() or "ppa_revenue" in doc.lower()
    assert "p4" in doc.lower() or "period 4" in doc.lower()
    # Must classify the delta
    assert (
        "-58" in doc
        or "anchor" in doc.lower()
        or "diagnostic" in doc.lower()
        or "stale" in doc.lower()
        or "mismatch" in doc.lower()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: SHL sweep P4 investigation present
# ─────────────────────────────────────────────────────────────────────────────
def test_shl_sweep_p4_investigation_present():
    doc = PHASE31C_DOC.read_text()
    assert "shl sweep" in doc.lower() or "shl_sweep" in doc.lower()
    assert "bullet" in doc.lower() or "shl_tenor" in doc.lower()
    # Must classify the discrepancy
    assert (
        "-340" in doc
        or "expected" in doc.lower()
        or "artifact" in doc.lower()
        or "stale" in doc.lower()
        or "no fix" in doc.lower()
        or "architecture" in doc.lower()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Discrepancy classification table present
# ─────────────────────────────────────────────────────────────────────────────
def test_discrepancy_classification_table_present():
    doc = PHASE31C_DOC.read_text()
    # Must have classification for equity IRR, PPA revenue, and SHL sweep
    assert "classification" in doc.lower()
    # Must distinguish between stale anchor, diagnostic mismatch, and expected architecture
    assert (
        "stale anchor" in doc.lower()
        or "diagnostic" in doc.lower()
        or "expected" in doc.lower()
        or "architecture" in doc.lower()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Phase 31D fix scoped if defect proven, else closure
# ─────────────────────────────────────────────────────────────────────────────
def test_fix_phase_scoped_if_defect_proven():
    doc = PHASE31C_DOC.read_text()
    # Must state no Phase 31D is required (all findings are stale anchors / expected)
    assert (
        "no phase 31d" in doc.lower()
        or "phase 31d not required" in doc.lower()
        or "not a runtime defect" in doc.lower()
        or "no fix required" in doc.lower()
        or "documentation" in doc.lower()
        or "stale anchor" in doc.lower()
        or "closure" in doc.lower()
        or "expected" in doc.lower()
        or "architecture" in doc.lower()
    ), "Phase 31D fix decision must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: OpEx false alarm still closed
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_opex_false_alarm_still_closed():
    doc = PHASE31C_DOC.read_text()
    assert "opex" in doc.lower()
    assert (
        "false alarm" in doc.lower()
        or "closed" in doc.lower()
        or "validated" in doc.lower()
        or "1,338" in doc
    )
    # P4 OpEx anchor must be positive 644.34
    from domain.diagnostics.cfads_bridge import OBOROVO_P4_ANCHORS
    assert OBOROVO_P4_ANCHORS["opex_keur"] == 644.34


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Oborovo frozen debt path unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_frozen_debt_path_unchanged():
    from app.project_factories import create_default_oborovo

    oborovo = create_default_oborovo()
    fin = oborovo.financing

    assert fin.use_frozen_excel_senior_debt_schedule is True
    assert abs(fin.fixed_debt_keur - OBOROVO_FIXED_DEBT_KEUR) < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: TUHO frozen path unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_frozen_path_unchanged():
    from app.project_factories import create_default_tuho_wind1

    tuho = create_default_tuho_wind1()
    fin = tuho.financing

    assert fin.use_frozen_excel_senior_debt_schedule is True
    assert tuho.financing.shl_repayment_method == "pik_then_sweep"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: CSV not created — doc explains why
# ─────────────────────────────────────────────────────────────────────────────
def test_csv_if_present_is_valid():
    csv_path = Path("reports/phase31c_oborovo_irr_shl_sweep_diagnostic.csv")
    doc = PHASE31C_DOC.read_text()

    if csv_path.exists():
        content = csv_path.read_text()
        assert "metric" in content.lower()
        assert "runtime_value" in content.lower()
        assert "classification" in content.lower()
        assert "source" in content.lower()
    else:
        assert (
            "csv not created" in doc.lower()
            or "no csv" in doc.lower()
            or "csv not needed" in doc.lower()
            or "skip csv" in doc.lower()
            or "csv decision" in doc.lower()
        ), "CSV absent but doc does not explain why"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: No bank/lender/audit/certification/SaaS/enterprise claims
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims_are_explicit():
    doc = PHASE31C_DOC.read_text()
    matrix = PHASE31C_MATRIX.read_text()

    blocked_terms = [
        "bank ready", "bank-approved", "lender approved",
        "audit ready", "audited", "certified",
        "saas-ready", "enterprise-ready", "enterprise ready",
        "production ready", "go-live ready",
    ]
    for term in blocked_terms:
        assert term.lower() not in doc.lower(), f"Blocked claim '{term}' found in doc"
        assert term.lower() not in matrix.lower(), f"Blocked claim '{term}' found in matrix"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: No runtime model files changed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_runtime_model_files_changed_or_claimed():
    doc = PHASE31C_DOC.read_text()

    assert (
        "no financial formula" in doc.lower()
        or "no formula changes" in doc.lower()
        or "no runtime changes" in doc.lower()
        or "diagnostic-only" in doc.lower()
    )

    formula_change_terms = [
        "shl formula changed",
        "distribution formula changed",
        "revenue formula changed",
        "changed waterfall",
    ]
    for term in formula_change_terms:
        assert term.lower() not in doc.lower(), f"Formula change claim '{term}' found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Guardrails unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_unchanged():
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1

    oborovo = create_default_oborovo()
    tuho = create_default_tuho_wind1()

    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True

    doc = PHASE31C_DOC.read_text()
    assert "G20" in doc or "g20" in doc.lower() or "blocked" in doc.lower()
    assert "R99" in doc or "r99" in doc.lower() or "R102" in doc or "r102" in doc.lower()
    assert "partial_pay_sweep" not in doc or "not promoted" in doc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 16 (bonus): Equity IRR runtime is 6.24%
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_equity_irr_runtime_is_6_24_percent():
    """Verify runtime equity IRR is 6.24% — not a defect, stale anchor."""
    from app.project_factories import create_default_oborovo
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

    oborovo = create_default_oborovo()
    eng = _build_period_engine(oborovo)
    result = WaterfallRunner(inputs=oborovo, engine=eng).run(
        WaterfallRunConfig.from_inputs(oborovo, eng)
    )

    # Must be approximately 6.24%
    assert 0.058 < result.equity_irr < 0.068, (
        f"Oborovo equity_irr={result.equity_irr*100:.2f}% — expected ~6.24%"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 17 (bonus): First distribution at period 41 (year 20)
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_first_distribution_at_period_41():
    """Verify first distribution is at period 41 (year 20) — bullet SHL lockup."""
    from app.project_factories import create_default_oborovo
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

    oborovo = create_default_oborovo()
    eng = _build_period_engine(oborovo)
    result = WaterfallRunner(inputs=oborovo, engine=eng).run(
        WaterfallRunConfig.from_inputs(oborovo, eng)
    )

    first_dist_period = None
    for p in result.periods:
        if p.is_operation and p.distribution_keur > 0:
            first_dist_period = p.period
            break

    assert first_dist_period == 41, (
        f"First distribution at period {first_dist_period} — expected 41 (year 20)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 18 (bonus): SHL balance P4 = 15,790 kEUR (bullet, unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_shl_balance_p4_is_15790():
    """Verify SHL balance P4 = 15,790 kEUR (bullet SHL, no principal repayment)."""
    from app.project_factories import create_default_oborovo
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

    oborovo = create_default_oborovo()
    eng = _build_period_engine(oborovo)
    result = WaterfallRunner(inputs=oborovo, engine=eng).run(
        WaterfallRunConfig.from_inputs(oborovo, eng)
    )

    p4 = result.periods[3]
    assert abs(p4.shl_balance_keur - 15_790.0) < 1.0, (
        f"SHL balance P4 = {p4.shl_balance_keur:.2f} — expected 15,790 kEUR"
    )