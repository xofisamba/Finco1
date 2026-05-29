"""Phase 23H: Oborovo SHL distribution lock-up shortfall fix.

Fix for Python waterfall bug: non-sweep / 2-tier distribution branch was paying
equity distributions while SHL service obligations exceeded available cash.

Root cause: In waterfall_engine.py, the "else" branch for bullet/cash_sweep/pik/accrued
methods used `dist = max(0, cf_after_reserves)` with no guard for SHL cash shortfall.

Fix: Add cash-shortfall guard in the else branch:
    if shl_svc > _cf_for_shl + TOLERANCE:
        dist = 0.0
    else:
        dist = max(0, cf_after_reserves)

where shl_svc = shi + shp (SHL interest paid + principal paid) and
_cf_for_shl = cash available for SHL step (cf_after_tax for non-pik_then_sweep methods).

Manual Excel check (cofi19):
- Excel CF tab: 2046 cash flows go to Free Cash Flow for Shareholder Loan / Net SHL
- Free Cash Flow for dividends is blank/zero in 2046
- Dividends start ~2050 after SHL is cleared
- Classification: Python waterfall bug, NOT Excel calibration issue

Guardrails (HARD):
- G20 BLOCKED
- R99/R102 NOT APPROVED
- Do NOT enable Oborovo frozen schedule
- Do NOT change TUHO factory flags
- Do NOT change senior debt sizing
- partial_pay_sweep remains opt-in only
"""

import pytest

from app.project_factories import create_default_solar_project, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig

TOLERANCE = 0.01  # kEUR


def _run_oborovo():
    oborovo = create_default_solar_project()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    return WaterfallRunner(oborovo, engine).run(config)


def _run_tuho_factory():
    tuho = create_default_tuho_wind1()
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    return WaterfallRunner(tuho, engine).run(config)


# ---------------------------------------------------------------------------
# Test 1: Oborovo period 30 distribution blocked by SHL shortfall
# ---------------------------------------------------------------------------

def test_oborovo_period30_distribution_blocked_by_shl_shortfall():
    """Oborovo period 30: shl_svc > available cash → distribution_keur == 0.

    Before fix: distribution_keur ≈ 2,058 kEUR while SHL principal (5,000)
    and accrued interest (198) were unpaid — a pure Python waterfall bug.

    After fix: distribution_keur == 0 because shl_svc (5,198.36) > _cf_for_shl (2,256.38).
    """
    result = _run_oborovo()
    op_periods = [p for p in result.periods if p.is_operation]

    # Period 30 = 2046-06-30
    p30 = op_periods[30]
    assert str(p30.date) == "2046-06-30", f"Expected period 30 at 2046-06-30, got {p30.date}"

    shl_svc = p30.shl_service_keur
    cf_for_shl = p30.fcf_for_shl_keur  # _cf_for_shl is the same value in output
    shortfall = shl_svc - cf_for_shl

    assert p30.distribution_keur == 0.0, (
        f"Oborovo period 30 distribution must be 0; got {p30.distribution_keur:.4f}. "
        f"shl_svc={shl_svc:.4f} > cf_for_shl={cf_for_shl:.4f} (shortfall={shortfall:.4f})"
    )
    assert shl_svc > cf_for_shl + TOLERANCE, (
        f"Period 30 shortfall condition not triggered: shl_svc={shl_svc:.4f} <= cf_for_shl={cf_for_shl:.4f}"
    )
    assert p30.senior_ds_keur == 0.0, (
        f"Period 30 senior debt should be fully repaid; got senior_ds={p30.senior_ds_keur:.4f}"
    )
    assert p30.shl_principal_keur == 5000.0, (
        f"Period 30 SHL principal should be 5000; got {p30.shl_principal_keur:.4f}"
    )
    assert p30.shl_gross_accrued_interest_keur > TOLERANCE, (
        f"Period 30 accrued interest should be > 0; got {p30.shl_gross_accrued_interest_keur:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 2: Oborovo no distribution while SHL shortfall exists
# ---------------------------------------------------------------------------

def test_oborovo_no_distribution_while_shl_shortfall():
    """Every operating period: if shl_svc > available cash, distribution == 0."""
    result = _run_oborovo()
    op_periods = [p for p in result.periods if p.is_operation]

    breaches = []
    for i, p in enumerate(op_periods):
        shl_svc = p.shl_service_keur
        cf_for_shl = p.fcf_for_shl_keur
        has_shortfall = shl_svc > cf_for_shl + TOLERANCE
        dist_active = p.distribution_keur > TOLERANCE

        if dist_active and has_shortfall:
            breaches.append(
                f"op_idx={i+1} (period={p.period}, {p.date}): "
                f"distribution={p.distribution_keur:.4f} while "
                f"shl_svc={shl_svc:.4f} > cf_for_shl={cf_for_shl:.4f} (shortfall={shl_svc - cf_for_shl:.4f})"
            )

    assert not breaches, "Distribution while SHL cash shortfall:\n" + "\n".join(breaches)


# ---------------------------------------------------------------------------
# Test 3: Oborovo dividends allowed after SHL cleared (~2050)
# ---------------------------------------------------------------------------

def test_oborovo_dividends_allowed_after_shl_cleared():
    """Later periods (around 2050+) can and should distribute once SHL is cleared.

    The fix must NOT globally disable dividends — only block them when a cash
    shortfall exists. After SHL obligations are cleared, distributions resume.
    """
    result = _run_oborovo()
    op_periods = [p for p in result.periods if p.is_operation]

    # Collect post-SHL periods (shl_service_keur == 0 and shl_balance_keur == 0)
    post_shl = [
        p for p in op_periods
        if p.shl_service_keur < TOLERANCE and p.shl_balance_keur < TOLERANCE
    ]

    # Dividends must be allowed in at least some post-SHL periods
    dividend_periods = [p for p in post_shl if p.distribution_keur > TOLERANCE]
    assert len(dividend_periods) > 0, (
        f"No dividend periods found after SHL cleared. "
        f"post_shl periods: {len(post_shl)}, with dividends: {len(dividend_periods)}"
    )

    # Confirm dividends start around 2050 (period 38 = 2050-06-30, idx 38)
    period_38 = op_periods[38]
    assert str(period_38.date) == "2050-06-30", f"Expected period 38 = 2050-06-30, got {period_38.date}"
    assert period_38.distribution_keur > TOLERANCE, (
        f"Period 38 (2050-06-30) should have a dividend; got {period_38.distribution_keur:.4f}. "
        "Dividends must resume after SHL is cleared (~2050)."
    )
    assert period_38.shl_balance_keur < TOLERANCE
    assert period_38.shl_service_keur < TOLERANCE


# ---------------------------------------------------------------------------
# Test 4: TUHO regression — no false distribution block
# ---------------------------------------------------------------------------

def test_tuho_regression_no_false_distribution_block():
    """TUHO factory run must not be falsely blocked by the Oborovo shortfall guard.

    TUHO uses pik_then_sweep which has its own 3-tier distribution branch (already
    guarded). The fix only touches the non-sweep/2-tier branch (bullet, cash_sweep,
    pik, accrued). TUHO distributions must remain valid.
    """
    result = _run_tuho_factory()
    op_periods = [p for p in result.periods if p.is_operation]

    # TUHO should distribute in at least one period (fixture-backed frozen DS)
    dividend_periods = [p for p in op_periods if p.distribution_keur > TOLERANCE]
    assert len(dividend_periods) > 0, (
        "TUHO factory run should produce at least one dividend period. "
        "Check that the fix did not inadvertently block TUHO distributions."
    )

    # Specific check: TUHO first distribution (expected around idx=35, 2047-12-31)
    first_div = dividend_periods[0]
    assert first_div.distribution_keur > 0
    # shl_gross_accrued_interest_keur being > 0 in a TUHO period must NOT
    # by itself block distributions (it accrues every period even when paid)
    assert first_div.shl_gross_accrued_interest_keur >= 0  # always non-negative


# ---------------------------------------------------------------------------
# Test 5: Factory flags unchanged
# ---------------------------------------------------------------------------

def test_factory_flags_unchanged():
    """Confirm factory flag state: TUHO True, Oborovo False."""
    tuho = create_default_tuho_wind1()
    oborovo = create_default_solar_project()

    # TUHO
    assert getattr(tuho.info, "use_senior_debt_sizing_engine", False) is True, (
        "TUHO use_senior_debt_sizing_engine must remain True"
    )
    # Oborovo
    assert getattr(oborovo.info, "use_senior_debt_sizing_engine", False) is False, (
        "Oborovo use_senior_debt_sizing_engine must remain False"
    )


# ---------------------------------------------------------------------------
# Test 6: Revenue/OPEX unchanged
# ---------------------------------------------------------------------------

def test_revenue_opex_unchanged():
    """Revenue and OPEX are unchanged by the distribution branch fix.

    The fix only touches the distribution calculation (dist = 0 vs dist = max(0, cf...)).
    Revenue, OpEx, CAPEX, Tax, and senior debt sizing are unaffected.
    """
    result = _run_oborovo()
    op_periods = [p for p in result.periods if p.is_operation]

    # Spot check: period 0 (first operating period)
    p0 = op_periods[0]
    assert 1800 < p0.revenue_keur < 2200, f"Period 0 revenue {p0.revenue_keur:.2f} out of expected range"
    assert 150 < p0.opex_keur < 250, f"Period 0 OpEx {p0.opex_keur:.2f} out of expected range"

    # Spot check: period 15 (mid-model)
    p15 = op_periods[15]
    assert 1900 < p15.revenue_keur < 2500, f"Period 15 revenue {p15.revenue_keur:.2f} out of expected range"
    assert 180 < p15.opex_keur < 270, f"Period 15 OpEx {p15.opex_keur:.2f} out of expected range"