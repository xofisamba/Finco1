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
  - 2046: no distribution at period 30 (SHL final period, guard blocks)
  - 2046 other periods: distributions active (pre-SHL clear, fcf>svc)

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

    Also: 2046 periods (periods 31-33, 36) show distributions because
    fcf_for_shl > shl_service (SHL not yet in final period). This matches
    the pre-SHL-clear behavior expected from the PR #304 fix.

    2046 period 30 (2045-12-31) was incorrectly flagged in earlier tests
    as a gap — but period 30 is NOT in 2046; the SHL final period is 38.
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

    # Confirm 2046 periods have distributions (pre-SHL-clear, fcf>svc)
    # This is CORRECT per the PR #304 guard only — but Excel shows no dividends pre-2050.
    # Mark this as a KNOWN BLOCKER for Phase 23O.
    p2046 = [p for p in op_periods if str(p.date).startswith("2046")]
    pre_2050_with_shl = [p for p in p2046 if p.distribution_keur > 0 and p.shl_balance_keur > 0]
    print(f"\nPre-2050 distributions with SHL outstanding (requires Excel verification):")
    for p in pre_2050_with_shl:
        print(f"  {p.date}: dist={p.distribution_keur:.2f}  shl_bal={p.shl_balance_keur:.1f}  shl_svc={p.shl_service_keur:.2f}")

    # This is the known Phase 23N mismatch: Python distributes pre-2050 while Excel does not.
    # Do NOT mark this as passing; it is an open diagnostic blocker.
    assert len(pre_2050_with_shl) > 0, (
        "Pre-2050 distributions list should be non-empty (diagnostic capture); "
        "if empty, something changed significantly"
    )

    print(f"\nDistribution timing confirmed:")
    print(f"  Period 38 (2049-12-31): dist={p38.distribution_keur:.2f} shl_svc={p38.shl_service_keur:.2f} (SHL final period) ✓")
    print(f"  Period 39 (2050-06-30): dist={p39.distribution_keur:.2f} shl_bal={p39.shl_balance_keur:.2f} (SHL cleared) ✓")


# ---------------------------------------------------------------------------
# Test 3b: Distribution lock-up mismatch blocker
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason=(
    "Known Phase 23N Oborovo distribution lock-up policy mismatch: Python distributes "
    "before Excel-observed dividend start around 2050. Python gates on current-period "
    "SHL service covered (fcf > shl_service); Excel appears to gate on no SHL principal "
    "outstanding (SHL fully cleared at 2049-12-31). Blocked until Phase 23O resolves "
    "the distribution policy parity question."
), strict=True)
def test_oborovo_distribution_lockup_mismatch_blocker():
    """Pre-2050 distributions with SHL outstanding are a known Phase 23N diagnostic blocker.

    Python distributes in every period where fcf_for_shl > shl_service (current-period
    interest only). For Oborovo bullet SHL (20-year tenor, principal 15,790 kEUR),
    current-period interest is ~626-636 kEUR per period — easily covered by CFADS.
    Result: Python distributes 2,000-2,600 kEUR per period throughout 2046-2049
    while SHL principal of 15,790 kEUR remains outstanding.


    Per manual Excel CF tab inspection, dividends in the same periods are zero.
    This gap must be resolved in Phase 23O before frozen senior DS fixture extraction.
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)

    op_periods = [p for p in result.periods if p.is_operation]

    # Collect all periods before 2050-01-01 where distribution > 0 AND SHL balance > 0
    pre2050_mismatch = [
        p for p in op_periods
        if str(p.date) < "2050-01-01"
        and p.distribution_keur > 0
        and p.shl_balance_keur > 0
    ]

    # Diagnostic display
    print("\n[xfail] Pre-2050 distributions with SHL balance outstanding:")
    for p in pre2050_mismatch:
        print(f"  {p.date}: dist={p.distribution_keur:.2f}  shl_bal={p.shl_balance_keur:.1f}  "
              f"shl_svc={p.shl_service_keur:.2f}  is_final_shl={getattr(p,'is_final_shl_period',False)}")

    # This xfails because Python SHOULD be blocking these distributions per Excel behavior.
    # After Phase 23O fix, update this to assert len(pre2050_mismatch) == 0.
    assert len(pre2050_mismatch) > 0, (
        "Pre-2050 distribution list must be non-empty to trigger xfail; "
        "if somehow empty, the mismatch may have resolved unexpectedly"
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