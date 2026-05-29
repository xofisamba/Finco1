"""Phase 23N: Oborovo Post-Correction Parity Snapshot.

Diagnostic-only: captures current corrected Oborovo state after Phase 23H/23J/23K/23L/23M.
No runtime changes.

Corrected anchors (Phase 23L):
  shl_amount_keur = 14,621.0 kEUR (corrected from 13,547.2)
  shl_idc_keur = 1,169.0 kEUR (unchanged)
  opening SHL = 15,790.0 kEUR ≈ Excel 15,791 kEUR
  shl_tenor_years = 20 (corrected from 0, PR #306)

Key observations from snapshot:
  - Senior debt active periods 0-27, repaid at period 28 (2045-12-31)
  - DSCR ~1.26 during active period
  - SHL cleared at period 38 (2049-12-31) — bullet 16,426.8 kEUR
  - Distributions resume at period 39 (2050-06-30) — first after SHL clear

IMPORTANT — BLOCKER IDENTIFIED (Phase 23N correction):
  Python distributes pre-2050 (2046-2049) while SHL principal remains outstanding.
  Per manual Excel CF tab inspection, dividends are zero until 2050.
  Phase 23O must resolve distribution lock-up policy parity before frozen DS fixture work.

PR context:
  #304/23H: SHL/distribution guard (2-tier bug)
  #306/23J: shl_tenor_years 0→20
  #308/23K: diagnostic gap
  #309/23L: factory correction
  #310/23M: test/doc update
"""

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# ---------------------------------------------------------------------------
# Test 1: Corrected factory anchors
# ---------------------------------------------------------------------------

def test_oborovo_corrected_factory_anchors():
    """Assert corrected Oborovo factory anchors post-Phase 23L.

    shl_amount_keur = 14,621.0 (corrected from 13,547.2)
    shl_idc_keur = 1,169.0 (unchanged)
    shl_tenor_years = 20 (corrected from 0, PR #306)
    use_frozen_excel_senior_debt_schedule = False (TUHO only, Oborovo OFF)
    """
    oborovo = create_default_oborovo()
    fin = oborovo.financing
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    assert fin.shl_amount_keur == pytest.approx(14_621.0, abs=0.1), (
        f"shl_amount_keur = {fin.shl_amount_keur} — expected 14,621.0 (corrected in Phase 23L)"
    )
    assert fin.shl_idc_keur == pytest.approx(1_169.0, abs=1.0), (
        f"shl_idc_keur = {fin.shl_idc_keur} — expected 1,169.0 (unchanged)"
    )
    assert fin.shl_tenor_years == 20, (
        f"shl_tenor_years = {fin.shl_tenor_years} — expected 20 (corrected in Phase 23J)"
    )

    # Frozen schedule for Oborovo remains OFF
    assert config.use_frozen_excel_senior_debt_schedule is False, (
        "Oborovo frozen schedule must remain OFF — guardrail"
    )
    assert config.use_senior_debt_sizing_engine is False, (
        "Oborovo senior debt sizing engine must remain OFF — guardrail"
    )

    # Opening SHL = shl_amount + shl_idc
    opening = fin.shl_amount_keur + fin.shl_idc_keur
    assert opening == pytest.approx(15_790.0, abs=1.0), (
        f"Opening SHL = {opening:.1f} kEUR — expected 15,790.0 (≈ Excel 15,791)"
    )


# ---------------------------------------------------------------------------
# Test 2: Opening SHL balance anchor (waterfall result)
# ---------------------------------------------------------------------------

def test_oborovo_opening_shl_balance_anchor():
    """First operating period SHL closing balance ≈ 15,790 kEUR.

    The waterfall sets shl_balance = shl_amount + shl_idc at first period.
    Post Phase 23L correction: shl_balance = 14,621 + 1,169 = 15,790 kEUR.
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)

    op_periods = [p for p in result.periods if p.is_operation]
    first = op_periods[0]

    # First operating period: shl_balance = opening = shl_amount + shl_idc
    opening_expected = 14_621.0 + 1_169.0  # = 15,790
    assert first.shl_balance_keur == pytest.approx(opening_expected, abs=1.0), (
        f"First-period shl_balance = {first.shl_balance_keur:.2f} — "
        f"expected ~{opening_expected:.0f} kEUR (Phase 23L correction)"
    )


# ---------------------------------------------------------------------------
# Test 3: Distribution timing post-correction
# ---------------------------------------------------------------------------

def test_oborovo_distribution_timing_post_correction():
    """No distributions at SHL final period (period 38 = 2049-12-31).

    Post Phase 23L + 23J correction:
    - shl_tenor_years=20 → SHL bullet at op_counter=39 (period 39, 2050-06-30)
    - Period 38 (2049-12-31): is_final_shl_period, shl_svc = 16,426.8 kEUR
      (principal 15,790 + interest 637) >> fcf_for_shl (3,277 kEUR)
      → PR #304 guard blocks distribution correctly
    - Period 39 (2050-06-30): SHL cleared → large distributions begin
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)

    op_periods = [p for p in result.periods if p.is_operation]

    # Period 38 = 2049-12-31: SHL final period (bullet)
    p38 = op_periods[38]
    assert str(p38.date) == "2049-12-31", (
        f"Period 38 expected at 2049-12-31, got {p38.date}"
    )
    assert p38.distribution_keur == 0.0, (
        f"Period 38 (SHL final): distribution = {p38.distribution_keur:.2f} — "
        f"should be 0 via PR #304 guard"
    )
    assert p38.shl_principal_keur > 15_000, (
        f"Period 38 SHL principal = {p38.shl_principal_keur:.2f} — "
        f"should be ~15,790 (bullet)"
    )
    assert p38.shl_service_keur > 16_000, (
        f"Period 38 SHL service = {p38.shl_service_keur:.2f} — "
        f"should be ~16,427 (principal + interest)"
    )

    # Period 39 = 2050-06-30: first distribution after SHL cleared
    p39 = op_periods[39]
    assert str(p39.date) == "2050-06-30", (
        f"Period 39 expected at 2050-06-30, got {p39.date}"
    )
    assert p39.distribution_keur > 2_000, (
        f"Period 39 (first after SHL clear): distribution = {p39.distribution_keur:.2f} — "
        f"should be large (>2,000 kEUR)"
    )
    assert p39.shl_balance_keur == 0.0, "Period 39 SHL balance should be 0"

    print(f"\nDistribution timing confirmed:")
    print(f"  Period 38 (2049-12-31): dist={p38.distribution_keur:.2f} shl_svc={p38.shl_service_keur:.2f} (SHL final period) ✓")
    print(f"  Period 39 (2050-06-30): dist={p39.distribution_keur:.2f} shl_bal={p39.shl_balance_keur:.2f} (SHL cleared) ✓")


# ---------------------------------------------------------------------------
# Test 3b: Distribution lock-up mismatch detector
# ---------------------------------------------------------------------------

def test_oborovo_pre_2050_distribution_lockup_mismatch_detected():
    """Pre-2050 distributions with SHL outstanding: diagnostic detection test.

    PASSES by confirming the mismatch exists. After Phase 23O fixes the
    distribution lock-up policy, update this test to assert len(mismatch)==0.

    Currently Python distributes 2,000-2,600 kEUR per period throughout
    2046-2049 while SHL principal of 15,790 kEUR remains outstanding.
    Per Excel CF tab: dividends are zero until around 2050.

    Phase 23O must resolve this blocker before frozen senior DS fixture work.
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)

    op_periods = [p for p in result.periods if p.is_operation]

    # Collect all periods before 2050 where distribution occurs with SHL balance outstanding
    mismatch = [
        p for p in op_periods
        if str(p.date) < "2050-01-01"
        and p.distribution_keur > 1.0   # tolerance for noise
        and p.shl_balance_keur > 1.0    # tolerance for zero-balance
    ]

    print(f"\n[detected] Pre-2050 distributions with SHL balance outstanding: {len(mismatch)}")
    for p in mismatch:
        print(f"  {p.date}: dist={p.distribution_keur:8.2f}  shl_bal={p.shl_balance_keur:8.1f}  "
              f"shl_svc={p.shl_service_keur:.2f}")

    # PASS: this test proves the blocker exists
    assert len(mismatch) > 0, (
        "Pre-2050 distribution list must be non-empty — "
        "if empty, the distribution lock-up mismatch may have resolved unexpectedly"
    )
    # Confirm at least one period in the 2046-2049 range is in the list
    kpi_periods = [p for p in mismatch if str(p.date) >= "2046-01-01"]
    assert len(kpi_periods) > 0, (
        "At least one 2046-2049 period expected in the mismatch list; "
        "got none — check period indexing or date ranges"
    )


# ---------------------------------------------------------------------------
# Test 4: TUHO regression — flags and fixture unchanged
# ---------------------------------------------------------------------------

def test_tuho_regression_flags_and_fixture():
    """TUHO factory flags remain True (PR #303) after all Oborovo corrections."""
    tuho = create_default_tuho_wind1()
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)

    assert config.use_frozen_excel_senior_debt_schedule is True, (
        "TUHO should have use_frozen_excel_senior_debt_schedule=True (PR #303)"
    )
    assert config.use_senior_debt_sizing_engine is True, (
        "TUHO should have use_senior_debt_sizing_engine=True (PR #303)"
    )

    result = WaterfallRunner(tuho, engine).run(config)
    assert len(result.periods) > 0, "TUHO waterfall must produce periods"


# ---------------------------------------------------------------------------
# Test 5: Guardrails unchanged
# ---------------------------------------------------------------------------

def test_guardrails_unchanged():
    """Confirm all hard guardrails preserved."""
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    assert config.use_frozen_excel_senior_debt_schedule is False, (
        "G20 guardrail violated: Oborovo frozen schedule must remain OFF"
    )
    assert config.use_senior_debt_sizing_engine is False, (
        "G20 guardrail violated: Oborovo senior sizing engine must remain OFF"
    )

    method_val = config.shl_repayment_method
    method_str = method_val.value if hasattr(method_val, 'value') else str(method_val)
    assert method_str == "bullet", (
        f"Oborovo SHL method = {method_val} — expected 'bullet'"
    )

    print(f"\nGuardrails: Oborovo frozen={config.use_frozen_excel_senior_debt_schedule}, "
          f"sizing={config.use_senior_debt_sizing_engine}, method={method_str}")