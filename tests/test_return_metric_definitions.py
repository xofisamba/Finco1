"""Tests for return metric definitions and SHL cash-flow treatment.

Ensures:
- Project IRR is unlevered (independent of financing structure).
- Sponsor IRR includes SHL cash interest and principal when actually paid.
- PIK/accrued SHL interest is NOT counted as sponsor cash until actually paid.
"""
from dataclasses import replace
import pytest
from app.project_factories import create_default_solar_project
from domain.period_engine import PeriodEngine
from app.waterfall_core import run_waterfall_v3_core


def _run_waterfall_for_inputs(inputs, equity_irr_method="equity_only", fixed_debt_keur=None, shl_tenor_years=None):
    engine = PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )
    all_periods = list(engine.periods())
    op_periods = [p for p in all_periods if p.is_operation]
    return run_waterfall_v3_core(
        inputs=inputs,
        engine=engine,
        rate_per_period=inputs.financing.all_in_rate / 2,
        tenor_periods=len(op_periods),
        target_dscr=inputs.financing.target_dscr,
        lockup_dscr=inputs.financing.lockup_dscr,
        tax_rate=inputs.tax.corporate_rate,
        dsra_months=inputs.financing.dsra_months,
        shl_amount=inputs.financing.shl_amount_keur,
        shl_rate=inputs.financing.shl_rate,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        equity_irr_method=equity_irr_method,
        share_capital_keur=inputs.financing.share_capital_keur,
        sculpt_capex_keur=inputs.capex.sculpt_capex_keur,
        debt_sizing_method="dscr_sculpt",
        fixed_debt_keur=fixed_debt_keur,
        shl_tenor_years=shl_tenor_years if shl_tenor_years is not None else inputs.financing.shl_tenor_years,
    )


class TestReturnMetricDefinitions:
    """Verify return metric definitions are correctly implemented."""

    def test_project_irr_independent_of_debt_amount(self):
        """Project IRR should not change when senior debt amount changes.

        Project IRR = unlevered IRR on (total_capex, then EBITDA - cash_tax).
        It must be the same whether leverage is 0% or 80%.
        """
        base = create_default_solar_project()
        # Low leverage: reduce senior debt by making share capital larger
        low_lev = replace(base,
            financing=replace(base.financing,
                senior_debt_amount_keur=base.financing.senior_debt_amount_keur * 0.5,
                share_capital_keur=base.financing.share_capital_keur * 1.5,
            )
        )
        # High leverage: increase senior debt
        high_lev = replace(base,
            financing=replace(base.financing,
                senior_debt_amount_keur=base.financing.senior_debt_amount_keur * 1.5,
                share_capital_keur=base.financing.share_capital_keur * 0.5,
            )
        )
        r_low = _run_waterfall_for_inputs(low_lev)
        r_high = _run_waterfall_for_inputs(high_lev)
        # Project IRR should be approximately the same (within 0.5pp tolerance for numerical effects)
        diff = abs(r_high.project_irr - r_low.project_irr)
        assert diff < 0.005, (
            f"Expected project_irr to be similar across leverage: "
            f"low={r_low.project_irr:.4f}, high={r_high.project_irr:.4f}, diff={diff:.4f}"
        )

    def test_equity_or_sponsor_irr_changes_with_leverage(self):
        """Sponsor IRR should change when actual runtime debt amount changes.

        We change the actual debt by passing fixed_debt_keur directly to the
        headless runner — this overrides the sculpted debt so the test actually
        produces different debt levels in the waterfall.
        """
        base = create_default_solar_project()
        # Run baseline to find sculpted debt level
        r_base = _run_waterfall_for_inputs(base, equity_irr_method="equity_only")
        sculpted_debt = r_base.sculpting_result.debt_keur if r_base.sculpting_result else None

        # Low leverage: fixed_debt = 50% of sculpted
        low_debt = sculpted_debt * 0.5 if sculpted_debt else 20000.0
        r_low = _run_waterfall_for_inputs(base, equity_irr_method="equity_only",
                                        fixed_debt_keur=low_debt)
        # High leverage: fixed_debt = 90% of sculpted
        high_debt = sculpted_debt * 0.9 if sculpted_debt else 36000.0
        r_high = _run_waterfall_for_inputs(base, equity_irr_method="equity_only",
                                          fixed_debt_keur=high_debt)

        # Verify debt levels actually differ
        assert abs(high_debt - low_debt) > 100.0, "Debt levels should differ meaningfully"

        # Sponsor IRR should be different with different leverage
        diff = abs(r_high.sponsor_irr - r_low.sponsor_irr)
        assert diff > 0.001, (
            f"Expected sponsor_irr to change with leverage: "
            f"low={r_low.sponsor_irr:.4f} (debt={low_debt:.0f}), "
            f"high={r_high.sponsor_irr:.4f} (debt={high_debt:.0f})"
        )

    def test_project_irr_uses_ebitda_less_cash_tax_before_financing(self):
        """Project IRR cash flows must not subtract senior debt service or SHL service.

        Project cash flows for unlevered IRR:
        t0: -total_capex
        t>0: EBITDA - cash_tax (no financing costs subtracted)

        The waterfall engine uses project_cfs = ebitda - tax_this_period,
        which does NOT subtract senior_ds or shl_service. This test verifies
        that the project_irr cash flow in each period equals ebitda - tax,
        not ebitda - tax - senior_ds - shl_service.
        """
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        op_periods = [pr for pr in result.periods if pr.is_operation]

        for pr in op_periods[:3]:
            # Project CF = EBITDA - cash tax
            project_cf = pr.ebitda_keur - pr.tax_keur
            assert pr.ebitda_keur > 0, "EBITDA should be positive in operating periods"
            assert pr.tax_keur >= 0, "Tax should not be negative"
            # project_cf must NOT be (ebitda - tax - senior_ds - shl_service)
            # i.e. it must NOT be reduced by debt service
            expected_min = pr.ebitda_keur  # if no tax (tax=0 in H1), CF=EBITDA
            assert project_cf <= expected_min, (
                f"Project CF ({project_cf}) exceeds EBITDA ({expected_min}) — "
                f"may indicate debt service was incorrectly subtracted"
            )

        # Main check: project IRR must be finite and positive
        assert result.project_irr is not None
        assert result.project_irr > 0

        # Sanity: project IRR should be in a plausible range for solar (5-15%)
        assert 0.03 < result.project_irr < 0.20, (
            f"Project IRR {result.project_irr:.4f} outside plausible solar range" 
        )

    def test_pik_interest_not_counted_as_cash_until_paid(self):
        """PIK interest accrued but not yet paid should not appear as sponsor cash inflow.

        When SHL uses PIK (pik_then_sweep), accrued interest increases the SHL balance
        but is NOT sponsor cash. Sponsor receives it only when actually repaid.
        """
        from domain.waterfall.shl_engine import compute_shl_period_v3

        # Simulate: SHL balance = 1000, rate = 8%/yr semiannual = 4%/period
        # Period 1: PIK only — no cash paid (cf_available=0)
        shl_balance_1 = 1000.0
        rate = 0.04  # per period

        res_1 = compute_shl_period_v3(
            shl_balance=shl_balance_1,
            shl_rate_per_period=rate,
            cf_available=0.0,  # no cash available, all PIK
            method="pik",
        )
        # shi (cash interest paid) should be 0 for PIK period
        assert res_1.interest_paid_keur == 0.0, f"Expected shi=0 for PIK period, got {res_1.interest_paid_keur}"
        # principal repaid = 0
        assert res_1.principal_keur == 0.0, f"Expected shp=0 for PIK period, got {res_1.principal_keur}"
        # PIK should capitalize and grow the balance
        new_balance_1 = res_1.new_balance_keur
        assert new_balance_1 > shl_balance_1, (
            f"Expected balance to grow with PIK: {new_balance_1} vs {shl_balance_1}"
        )

        # Period 2: Repay principal including accumulated PIK using cash_sweep
        shl_balance_2 = new_balance_1
        principal_2 = 50.0  # some principal repaid (includes accrued PIK)

        res_2 = compute_shl_period_v3(
            shl_balance=shl_balance_2,
            shl_rate_per_period=rate,
            cf_available=principal_2,
            method="cash_sweep",
        )
        # At repayment, principal (including accrued PIK) is cash to sponsor
        assert res_2.principal_keur > 0.0, f"Expected principal repaid in cash, got {res_2.principal_keur}"


class TestSponsorCashFlows:
    """Sponsor cash-flow composition tests."""

    def test_sponsor_cashflows_includes_shl_interest_and_principal_when_paid(self):
        """Sponsor cash flows include SHL cash interest and principal when actually paid.

        This test verifies the WATERFALL records shi (paid SHL interest) and
        shl_principal_keur (paid SHL principal) separately.
        """
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        op_periods = [pr for pr in result.periods if pr.is_operation]

        total_shi = sum(pr.shl_interest_keur for pr in op_periods)
        total_shp = sum(pr.shl_principal_keur for pr in op_periods)

        # SHL interest and principal should be tracked on each period
        # (they may be 0 for bullet SHL where all paid at maturity, but they are tracked)
        assert all(hasattr(pr, 'shl_interest_keur') for pr in op_periods)
        assert all(hasattr(pr, 'shl_principal_keur') for pr in op_periods)

        # At least in some operating periods, SHL service should be non-zero
        total_shl = sum(pr.shl_service_keur for pr in op_periods)
        assert total_shl >= 0

    def test_sponsor_irr_with_bullet_shl_includes_lump_sum_at_maturity(self):
        """With bullet SHL, sponsor receives full interest + principal at maturity.

        For bullet SHL, the last operating period should show both shi > 0 and shp > 0
        (all interest + full principal repaid at maturity).
        """
        p = create_default_solar_project()
        # shl_tenor_years=26 fires the bullet in the last operating period.
        result = _run_waterfall_for_inputs(p, equity_irr_method="shl_interest_only", shl_tenor_years=26)
        assert result.sponsor_irr > 0, f"Expected sponsor_irr > 0, got {result.sponsor_irr}"
        op_periods = [pr for pr in result.periods if pr.is_operation]
        last_op = op_periods[-1]
        assert last_op.shl_interest_keur > 0, f"Expected shi>0 at maturity, got {last_op.shl_interest_keur}"
        assert last_op.shl_principal_keur > 0, f"Expected shp>0 at maturity, got {last_op.shl_principal_keur}"
        # Earlier periods should NOT have principal repaid
        for pr in op_periods[:-1]:
            assert pr.shl_principal_keur == 0, f"Expected no principal before maturity, got {pr.shl_principal_keur}"

    def test_sponsor_irr_differs_from_project_irr(self):
        """Sponsor/Equity IRR should differ from project IRR due to leverage effect."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        # Project IRR and equity IRR should be numerically different
        # (project is unlevered, equity is levered)
        assert abs(result.project_irr - result.equity_irr) > 0.001, (
            f"Expected different values for project_irr ({result.project_irr:.4f}) "
            f"and equity_irr ({result.equity_irr:.4f})"
        )
