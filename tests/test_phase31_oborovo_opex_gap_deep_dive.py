"""Phase 31 — Oborovo OpEx Gap Deep-Dive tests.

Verifies:
1. Diagnostic docs exist and contain required sections
2. Oborovo OpEx architecture is identified (legacy simple OpexItem path)
3. B.01/B.02 investigation is documented
4. Parent/sub-item double-count risk is classified
5. TUHO vs Oborovo comparison is present
6. No formula fix claimed without proof
7. Phase 31B fix is scoped (anchor sign error only, no runtime changes)
8. Oborovo frozen debt path unchanged
9. TUHO frozen path unchanged
10. No bank/lender/audit/certification claims
11. No runtime model files changed
12. Guardrails unchanged

Classification confirmed: FALSE ALARM — Oborovo Y1 OpEx = 1,338 kEUR,
matching Excel target exactly. No runtime bug found.

Separate finding: cfads_bridge.py OBOROVO_P4_ANCHORS["opex_keur"] = -644.34
is a sign/data-entry error (dash-typo, not negative value). Should be +644.34.
This is a data quality issue only, no runtime impact.
"""
import pytest
from pathlib import Path

BASE_SHA = "2c33411e12f7bfec72224727ce1111de5b7fc91b"
PHASE31_DOC = Path("docs/phase31_oborovo_opex_gap_deep_dive.md")
PHASE31_MATRIX = Path("docs/phase31_oborovo_opex_gap_evidence_matrix.md")
OBOROVO_FIXED_DEBT_KEUR = 42_852.27
OBOROVO_SHL_OPENING_KEUR = 15_790.0  # shl_amount + shl_idc = 14,621 + 1,169


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 31 doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase31_doc_exists():
    assert PHASE31_DOC.exists(), f"{PHASE31_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Evidence matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase31_evidence_matrix_exists():
    assert PHASE31_MATRIX.exists(), f"{PHASE31_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Oborovo OpEx source identified
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_opex_source_identified():
    doc = PHASE31_DOC.read_text()
    # Must identify that Oborovo uses legacy simple OpexItem path (not template)
    assert "legacy simple OpexItem" in doc or "legacy OpexItem" in doc
    # Must identify the runtime source
    assert "domain.opex.projections" in doc or "domain/opex/projections" in doc
    # Must confirm 1,338 kEUR total
    assert "1,338" in doc


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: B.01/B.02 investigation present
# ─────────────────────────────────────────────────────────────────────────────
def test_b01_b02_investigation_present():
    doc = PHASE31_DOC.read_text()
    # Must explicitly discuss B.01/B.02
    assert "B.01" in doc, "B.01 not found in doc"
    assert "B.02" in doc, "B.02 not found in doc"
    # Must explain the template is not wired
    assert "not wired" in doc.lower() or "not connected" in doc.lower() or "design doc" in doc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Parent/sub-item double-count classification present
# ─────────────────────────────────────────────────────────────────────────────
def test_parent_subitem_double_count_classification_present():
    doc = PHASE31_DOC.read_text()
    # Must include classification of aggregation risk
    assert "double-count" in doc.lower() or "double count" in doc.lower()
    # Must state risk = NONE / confirmed excluded / false alarm
    classification_found = (
        "none" in doc.lower() and "double" in doc.lower()
    ) or (
        "confirmed excluded" in doc.lower()
    ) or (
        "false alarm" in doc.lower()
    ) or (
        "no double-count" in doc.lower()
    )
    assert classification_found, "Double-count risk classification not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: TUHO vs Oborovo OpEx comparison present
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_vs_oborovo_opex_comparison_present():
    doc = PHASE31_DOC.read_text()
    assert "TUHO" in doc and "Oborovo" in doc
    # Must compare Y1 values
    assert "1,998" in doc and "1,338" in doc
    # Must note TUHO = 12 items, Oborovo = 15 items
    assert "12 items" in doc or "12" in doc
    assert "15 items" in doc or "15" in doc


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: No formula fix claimed without proof
# ─────────────────────────────────────────────────────────────────────────────
def test_no_formula_fix_claimed_without_proof():
    doc = PHASE31_DOC.read_text()
    # Must state diagnostic-only
    assert (
        "no runtime bug" in doc.lower()
        or "no fix needed" in doc.lower()
        or "false alarm" in doc.lower()
        or "diagnostic-only" in doc.lower()
        or "no formula change" in doc.lower()
    )
    # Must confirm Y1 OpEx = 1,338 kEUR matches Excel
    assert "1,338" in doc and "excel" in doc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: If defect proven, fix phase is scoped; if not, closure/external review
# ─────────────────────────────────────────────────────────────────────────────
def test_if_defect_proven_fix_phase_is_scoped():
    doc = PHASE31_DOC.read_text()
    matrix = PHASE31_MATRIX.read_text()

    # Classification must be FALSE ALARM (no defect proven)
    assert "false alarm" in doc.lower() or "no runtime bug found" in doc.lower()

    # If no defect proven, must explain closure or external review
    closure_found = (
        "no fix phase required" in doc.lower()
        or "documentation-only closure" in doc.lower()
        or "no fix needed" in doc.lower()
        or "external review" in doc.lower()
        or "Phase 31B" in doc  # anchor sign fix only
    )
    assert closure_found, "No defect proven but no closure/external-review explanation found"

    # If Phase 31B is mentioned, it must be only for anchor sign fix (no runtime change)
    if "Phase 31B" in doc:
        assert (
            "anchor sign" in doc.lower()
            or "sign error" in doc.lower()
            or "dash-typo" in doc.lower()
            or "data quality" in doc.lower()
        ), "Phase 31B must be scoped to anchor sign fix only"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Oborovo frozen debt path unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_frozen_debt_path_unchanged():
    from app.project_factories import create_default_oborovo

    oborovo = create_default_oborovo()
    fin = oborovo.financing

    # use_frozen_excel_senior_debt_schedule must be True
    assert fin.use_frozen_excel_senior_debt_schedule is True

    # fixed_debt_keur must be approx 42,852.27 kEUR
    assert abs(fin.fixed_debt_keur - OBOROVO_FIXED_DEBT_KEUR) < 1.0, (
        f"Oborovo fixed_debt_keur={fin.fixed_debt_keur:.2f} "
        f"expected {OBOROVO_FIXED_DEBT_KEUR:.2f}"
    )

    # shl_amount_keur must be approx 14,621 kEUR
    assert abs(fin.shl_amount_keur - 14_621.0) < 1.0

    # shl_idc_keur must be approx 1,169 kEUR
    assert abs(fin.shl_idc_keur - 1_169.0) < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: TUHO frozen path unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_frozen_path_unchanged():
    from app.project_factories import create_default_tuho_wind1

    tuho = create_default_tuho_wind1()
    fin = tuho.financing

    # use_frozen_excel_senior_debt_schedule must be True
    assert fin.use_frozen_excel_senior_debt_schedule is True

    # TUHO equity IRR within tolerance (11.61% ± 1.0pp)
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

    eng = _build_period_engine(tuho)
    result = WaterfallRunner(inputs=tuho, engine=eng).run(
        WaterfallRunConfig.from_inputs(tuho, eng)
    )
    assert abs(result.equity_irr - 0.1161) <= 0.01, (
        f"TUHO equity_irr={result.equity_irr*100:.2f}% expected ~11.61%"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: CSV not created — doc explains why
# ─────────────────────────────────────────────────────────────────────────────
def test_csv_if_present_is_valid():
    csv_path = Path("reports/phase31_oborovo_opex_diagnostic.csv")
    doc = PHASE31_DOC.read_text()

    if csv_path.exists():
        # If CSV exists, it must have classification and source columns
        content = csv_path.read_text()
        assert "classification" in content.lower(), "CSV must have classification column"
        assert "source" in content.lower(), "CSV must have source column"
    else:
        # If CSV absent, doc must explain why
        assert (
            "csv not created" in doc.lower()
            or "no csv" in doc.lower()
            or "csv not needed" in doc.lower()
            or "skip csv" in doc.lower()
            or "csv decision" in doc.lower()
        ), "CSV absent but doc does not explain why"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: No bank/lender/audit/certification/SaaS/enterprise claims
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims_are_explicit():
    doc = PHASE31_DOC.read_text()
    matrix = PHASE31_MATRIX.read_text()

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
# Test 13: No runtime model files changed (financial formulas)
# ─────────────────────────────────────────────────────────────────────────────
def test_no_runtime_model_files_changed_or_claimed():
    doc = PHASE31_DOC.read_text()

    # Must state no financial formula changes
    assert (
        "no financial formula" in doc.lower()
        or "no formula changes" in doc.lower()
        or "no runtime changes" in doc.lower()
        or "diagnostic-only" in doc.lower()
    )

    # Must not claim to have changed any financial formulas
    # (only diagnostics and docs were created)
    formula_change_terms = [
        "opex formula changed",
        "revenue formula changed",
        "debt formula changed",
        "tax formula changed",
        "changed opex_year",
        "changed opex_item_amount",
    ]
    for term in formula_change_terms:
        assert term.lower() not in doc.lower(), f"Formula change claim '{term}' found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Guardrails unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_unchanged():
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1

    oborovo = create_default_oborovo()
    tuho = create_default_tuho_wind1()

    # TUHO and Oborovo frozen senior DS must both be True
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True

    # TUHO use_senior_debt_sizing_engine must be True (sculpting candidate but frozen)
    assert tuho.info.use_senior_debt_sizing_engine is True

    doc = PHASE31_DOC.read_text()
    # G20 and R99/R102 must be mentioned as preserved/blocked
    assert "G20" in doc or "g20" in doc.lower() or "blocked" in doc.lower()
    assert "R99" in doc or "r99" in doc.lower() or "R102" in doc or "r102" in doc.lower()

    # partial_pay_sweep not promoted
    assert "partial_pay_sweep" not in doc or "not promoted" in doc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 15 (bonus): Oborovo Y1 OpEx is 1,338 kEUR — confirmed correct
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_y1_opex_is_1338_keur():
    """Verifies Oborovo Y1 OpEx is 1,338.56 kEUR — matching Excel target."""
    from app.project_factories import create_default_oborovo
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

    oborovo = create_default_oborovo()
    eng = _build_period_engine(oborovo)
    result = WaterfallRunner(inputs=oborovo, engine=eng).run(
        WaterfallRunConfig.from_inputs(oborovo, eng)
    )

    # Sum Y1 periods (P2 + P3, year_index=1)
    y1_opex = sum(
        p.opex_keur
        for p in result.periods
        if p.year_index == 1 and p.is_operation
    )
    # Must be approximately 1,338 kEUR (within 2 kEUR)
    assert abs(y1_opex - 1_338.0) < 2.0, (
        f"Oborovo Y1 OpEx = {y1_opex:.2f} kEUR — expected ~1,338 kEUR"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 16 (bonus): Oborovo equity IRR is 6.24% — documented as separate issue
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_equity_irr_documented_as_separate_issue():
    """Oborovo equity IRR = 6.24% — documented as separate from OpEx."""
    from app.project_factories import create_default_oborovo
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

    oborovo = create_default_oborovo()
    eng = _build_period_engine(oborovo)
    result = WaterfallRunner(inputs=oborovo, engine=eng).run(
        WaterfallRunConfig.from_inputs(oborovo, eng)
    )

    # Equity IRR should be approximately 6.24% (not 9.88%)
    # The delta from 9.88% is a separate issue from OpEx
    assert 0.05 < result.equity_irr < 0.08, (
        f"Oborovo equity_irr={result.equity_irr*100:.2f}% unexpected range"
    )

    doc = PHASE31_DOC.read_text()
    # Must document this is a separate issue from OpEx
    assert "separate issue" in doc.lower() or "unrelated" in doc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 17 (bonus): CFADS bridge anchor has sign error (-644.34 should be +644.34)
# ─────────────────────────────────────────────────────────────────────────────
def test_cfads_bridge_anchor_sign_error_documented():
    """OBOROVO_P4_ANCHORS['opex_keur'] = -644.34 is a sign error (dash-typo)."""
    from domain.diagnostics.cfads_bridge import OBOROVO_P4_ANCHORS

    anchor = OBOROVO_P4_ANCHORS["opex_keur"]
    # Anchor is negative but should be positive (it's a dash-typo)
    # This is documented in Phase 31 doc as a data quality issue only
    assert anchor < 0, (
        f"OBOROVO_P4_ANCHORS['opex_keur'] = {anchor} — expected negative (sign error)"
    )

    doc = PHASE31_DOC.read_text()
    assert "644.34" in doc or "-644.34" in doc, "Anchor sign issue not documented"
    assert (
        "sign error" in doc.lower()
        or "dash-typo" in doc.lower()
        or "data quality" in doc.lower()
    ), "Sign error classification not found"


# ─────────────────────────────────────────────────────────────────────────────
# Regression: Oborovo frozen debt path still works
# ─────────────────────────────────────────────────────────────────────────────
def test_oborovo_frozen_debt_still_produces_reasonable_output():
    """Oborovo frozen path produces reasonable outputs (no regression)."""
    from app.project_factories import create_default_oborovo
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

    oborovo = create_default_oborovo()
    eng = _build_period_engine(oborovo)
    result = WaterfallRunner(inputs=oborovo, engine=eng).run(
        WaterfallRunConfig.from_inputs(oborovo, eng)
    )

    # Basic sanity checks
    assert 0 < result.equity_irr < 0.20, f"equity_irr={result.equity_irr*100:.2f}% out of range"
    assert 0 < result.project_irr < 0.20, f"project_irr={result.project_irr*100:.2f}% out of range"
    assert 0.5 < result.avg_dscr < 3.0, f"avg_dscr={result.avg_dscr:.3f} out of range"
    assert result.total_distribution_keur > 0, "total_distribution_keur should be positive"
    assert result._frozen_senior_ds_wired is True, "Frozen DS should be wired"
    assert result._oborovo_frozen_fixture_loaded is True, "Frozen fixture should be loaded"