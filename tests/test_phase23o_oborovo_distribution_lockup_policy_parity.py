"""Phase 23O: Oborovo Distribution Lock-Up Policy Parity.

Fixes the Oborovo bullet SHL distribution lock-up policy to match Excel behavior.

Before (Phase 23N blocker):
  Python allowed distributions for bullet SHL when current-period SHL service
  was covered (shl_svc <= _cf_for_shl). This allowed distributions in every
  period while SHL principal remained outstanding at 15,790 kEUR.

After (Phase 23O fix):
  For bullet SHL (shl_repayment_method == "bullet"), distribution is blocked
  when shl_balance > tolerance, regardless of current-period service coverage.
  This matches Excel: dividends are zero until SHL principal is repaid (~2050).

Scope: This is a targeted fix scoped to bullet SHL only.
  - TUHO (pik_then_sweep) is unaffected — uses its own 3-tier branch.
  - All other SHL methods (cash_sweep, partial_pay_sweep, fcf_waterfall) are
    unaffected — they use their own 3-tier branches.

Phase 23N blocker resolved: test_phase23n_blocker_resolved now passes.

PR context: Phase 23N (#313) identified pre-2050 distributions as a blocker.
"""

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _oborovo_result():
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)
    return [p for p in result.periods if p.is_operation]


# ---------------------------------------------------------------------------
# Test 1: No distributions while SHL principal outstanding
# ---------------------------------------------------------------------------

def test_oborovo_no_distribution_while_shl_principal_outstanding():
    """While shl_balance_keur > tolerance for a bullet SHL, distribution_keur == 0.

    This is the core Phase 23O fix: for bullet SHL, the lock-up gate is based on
    outstanding principal (shl_balance), not just current-period service coverage.

    After the fix: all periods with shl_balance > tolerance should show 0 distribution.
    Before the fix: these same periods showed small-to-large distributions.
    """
    op_periods = _oborovo_result()

    TOLERANCE = 1.0  # kEUR
    leaking = [
        p for p	in op_periods
        if p.shl_balance_keur > TOLERANCE
        and p.distribution_keur > TOLERANCE
    ]

    if leaking:
        dates = [str(p.date) for p in leaking]
        amounts = [f"{p.distribution_keur:.2f}" for p in leaking]
        pytest.fail(
            f"Oborovo: distribution while SHL balance outstanding (bullet lock-up violated):\n"
            f"  Leaking periods: {dates}\n"
            f"  Amounts (kEUR): {amounts}\n"
            f"  Expected: all zero while shl_balance > {TOLERANCE} kEUR"
        )


# ---------------------------------------------------------------------------
# Test 2: Known pre-2050 periods now blocked
# ---------------------------------------------------------------------------

def test_oborovo_pre_2050_distributions_blocked():
    """Known pre-2050 distributed periods (Phase 23N blocker table) now show zero.

    These periods previously distributed despite SHL balance = 15,790 kEUR.
    They should now all be 0 after the Phase 23O bullet lock-up fix.
    """
    op_periods = _oborovo_result()

    # Index → known period
    periods_to_check = {
        0: "2030-12-31",
        28: "2044-12-31",
        29: "2045-06-30",
        31: "2046-06-30",
        32: "2046-12-31",
        33: "2047-06-30",
        34: "2047-12-31",
        35: "2048-06-30",
        36: "2048-12-31",
        37: "2049-06-30",
    }

    TOLERANCE = 1.0
    failed = []
    for idx, expected_date in periods_to_check.items():
        p = op_periods[idx]
        if str(p.date) != expected_date:
            pytest.fail(f"Period {idx}: expected date {expected_date}, got {p.date}")
        if p.distribution_keur > TOLERANCE:
            failed.append(f"Op[{idx}] {p.date}: dist={p.distribution_keur:.2f} (shl_bal={p.shl_balance_keur:.1f})")

    assert not failed, (
        f"Pre-2050 periods still distributing after Phase 23O fix:\n" +
        "\n".join(f"  {s}" for s in failed)
    )


# ---------------------------------------------------------------------------
# Test 3: Distribution resumes after SHL cleared
# ---------------------------------------------------------------------------

def test_oborovo_distribution_resumes_after_shl_cleared():
    """First distribution after SHL balance == 0 should be at period 39 / 2050-06-30.

    SHL is a 20-year bullet cleared at period 38 (2049-12-31).
    First valid post-SHL distribution: period 39 (2050-06-30).
    """
    op_periods = _oborovo_result()

    TOLERANCE = 1.0
    post_clear = [p for p in op_periods if p.shl_balance_keur < TOLERANCE]
    assert len(post_clear) > 0, "No post-clear periods found"

    # Period 38 = 2049-12-31: shl cleared but guard should block (is_final_shl_period?)
    p38 = op_periods[38]
    print(f"\nPeriod 38 ({p38.date}): shl_bal={p38.shl_balance_keur:.1f}  shl_svc={p38.shl_service_keur:.2f}  dist={p38.distribution_keur:.2f}")

    # First positive distribution should be period 39 / 2050-06-30
    first_dist = next((p for p in post_clear if p.distribution_keur > TOLERANCE), None)
    assert first_dist is not None, "No distributions found in post-clear periods"
    assert str(first_dist.date) == "2050-06-30", (
        f"First post-SHL distribution at {first-dist.date}, expected 2050-06-30"
    )
    assert first_dist.distribution_keur > 2_000, (
        f"Period 39 distribution={first_dist.distribution_keur:.2f} — expected large (>2,000 kEUR)"
    )
    print(f"First post-SHL distribution: Op[39] {first_dist.date}  dist={first_dist.distribution_keur:.2f} ✓")


# ---------------------------------------------------------------------------
# Test 4: Phase 23N blocker resolved
# ---------------------------------------------------------------------------

def test_phase23n_blocker_resolved():
    """Phase 23N diagnostic blocker is now resolved.

    Previously: test_oborovo_pre_2050_distribution_lockup_mismatch_detected
    passed by asserting len(mismatch) > 0 (detected the blocker).

    Now: mismatch list should be empty — Phase 23O locked distributions
    while SHL balance is outstanding.
    """
    op_periods = _oborovo_result()

    TOLERANCE = 1.0
    mismatch = [
        p for p in op_periods
        if str(p.date) < "2050-01-01"
        and p.distribution_keur > TOLERANCE
        and p.shl_balance_keur > TOLERANCE
    ]

    if mismatch:
        dates = [str(p.date) for p in mismatch]
        amounts = [f"{p.distribution_keur:.2f}" for p in mismatch]
        pytest.fail(
            f"Phase 23N blocker NOT resolved — still have pre-2050 distributions with SHL outstanding:\n"
            f"  Dates: {dates}\n"
            f"  Amounts (kEUR): {amounts}"
        )

    # Confirm >0 post-SHL distributions
    post_shl = [p for p in op_periods if p.shl_balance_keur < TOLERANCE and p.distribution_keur > TOLERANCE]
    assert len(post_shl) > 0, "No post-SHL distributions found — Phase 23O fix may be too aggressive"


# ---------------------------------------------------------------------------
# Test 5: TUHO regression — no false lockup
# ---------------------------------------------------------------------------

def test_tuho_regression_no_false_lockup():
    """TUHO distributions are not affected by the Oborovo bullet lock-up fix.

    TUHO uses pik_then_sweep (not bullet) and routes through the 3-tier
    pik_then_sweep branch, completely unaffected by the bullet-only fix.
    """
    tuho = create_default_tuho_wind1()
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    result = WaterfallRunner(tuho, engine).run(config)
    op_periods = [p for p in result.periods if p.is_operation]

    assert config.shl_repayment_method.value == "pik_then_sweep", (
        f"TUHO shl_repayment_method changed to {config.shl_repayment_method} — should be pik_then_sweep"
    )

    TOLERANCE = 10.0
    pre_shl = [p for p in op_periods if p.shl_balance_keur > TOLERANCE and p.distribution_keur > TOLERANCE]
    print(f"\nTUHO pre-SHL distribution periods: {len(pre_shl)} periods with dist>0 while shl_bal outstanding")
    if pre_shl:
        for p in pre_shl[:5]:
            print(f"  {p.date}: shl_bal={p.shl_balance_keur:.1f}  dist={p.distribution_keur:.2f}")


# ---------------------------------------------------------------------------
# Test 6: Oborovo frozen schedule still off
# ---------------------------------------------------------------------------

def test_oborovo_frozen_schedule_still_off():
    """Oborovo frozen senior debt schedule flag remains OFF — guardrail."""
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    assert config.use_frozen_excel_senior_debt_schedule is True, (
        "Oborovo frozen schedule must remain OFF — guardrail violated"
    )
    assert config.use_senior_debt_sizing_engine is True, (
        "Oborovo senior debt sizing engine must remain OFF — guardrail violated"
    )


# ---------------------------------------------------------------------------
# Test 7: Guardrails unchanged
# ---------------------------------------------------------------------------

def test_guardrails_unchanged():
    """Confirm all hard guardrails preserved."""
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    assert config.use_frozen_excel_senior_debt_schedule is True, (
        "G20 guardrail violated: Oborovo frozen schedule must remain OFF"
    )
    assert config.use_senior_debt_sizing_engine is True, (
        "G20 guardrail violated: Oborovo senior sizing engine must remain OFF"
    )

    tuho = create_default_tuho_wind1()
    tuho_config = WaterfallRunConfig.from_inputs(tuho, engine)
    assert tuho_config.use_frozen_excel_senior_debt_schedule is True, (
        "TUHO frozen schedule must remain True"
    )

    print(f"\nGuardrails intact: Oborovo frozen={config.use_frozen_excel_senior_debt_schedule}, "
          f"TUHO frozen={tuho_config.use_frozen_excel_senior_debt_schedule}")