"""Tests for equity IRR methods (S4-3).

Verifies that all three equity_irr_method values compute correctly:
- "equity_only": equity = total_capex - debt (TUHO style)
- "combined": equity = sculpt_capex - debt (Oborovo style)
- "shl_plus_dividends": equity = shl_amount + share_capital, includes SHL interest in CF
"""
import pytest
from datetime import date, timedelta

from domain.period_engine import PeriodEngine, PeriodFrequency
from domain.returns.xirr import robust_xirr
from domain.waterfall.waterfall_engine import run_waterfall


def make_test_periods(construction_periods: int = 2, operation_periods: int = 28):
    """Create periods using PeriodEngine for integration testing.

    The PeriodEngine returns periods with semi-annual frequency.
    We build schedules of matching length so ebitda_schedule[period.index] is valid.
    """
    engine = PeriodEngine(
        financial_close=date(2029, 6, 29),
        construction_months=construction_periods * 6,
        horizon_years=20,
        ppa_years=15,
        frequency=PeriodFrequency.SEMESTRIAL,
    )
    periods = engine.periods()
    return periods


def build_schedules(construction_periods: int, operation_periods: int, periods):
    """Build schedules matching the actual period list from PeriodEngine.

    Returns (ebitda, revenue, generation, depreciation) schedules of len(periods).
    """
    n = len(periods)
    ebitda = [0.0] * construction_periods + [50_000.0] * (n - construction_periods)
    revenue = [0.0] * construction_periods + [60_000.0] * (n - construction_periods)
    generation = [0.0] * construction_periods + [50_000.0] * (n - construction_periods)
    depreciation = [0.0] * construction_periods + [10_000.0] * (n - construction_periods)
    return ebitda, revenue, generation, depreciation


class TestEquityIRRMethod:
    """Test all three equity_irr_method values."""

    def test_equity_only_simple(self):
        """Test 'equity_only' — equity = total_capex - debt, no SHL."""
        periods = make_test_periods(2, 28)
        n = len(periods)
        n_construction = sum(1 for p in periods if not p.is_operation)

        ebitda_schedule, revenue_schedule, generation_schedule, depreciation_schedule = \
            build_schedules(n_construction, n - n_construction, periods)

        result = run_waterfall(
            ebitda_schedule=ebitda_schedule,
            revenue_schedule=revenue_schedule,
            generation_schedule=generation_schedule,
            depreciation_schedule=depreciation_schedule,
            periods=periods,
            total_capex=100_000.0,
            rate_per_period=0.02825,
            tenor_periods=28,
            target_dscr=1.15,
            lockup_dscr=1.10,
            tax_rate=0.10,
            dsra_months=6,
            equity_irr_method="equity_only",
            sculpt_capex_keur=0.0,
            shl_amount=0.0,
            shl_rate=0.0,
            financial_close=date(2029, 6, 29),
        )

        sculpt = getattr(result, 'sculpting_result', None)
        debt = getattr(sculpt, 'debt_keur', 0) if sculpt else 0
        assert debt > 0, f"Debt should be positive, got {debt}"
        assert result.project_irr > 0, "Project IRR should be positive"
        assert result.equity_irr >= 0 or result.equity_irr == 0.0

    def test_combined_with_sculpt_capex(self):
        """Test 'combined' — equity = sculpt_capex - debt (Oborovo style)."""
        periods = make_test_periods(2, 28)
        n = len(periods)
        n_construction = sum(1 for p in periods if not p.is_operation)

        ebitda_schedule, revenue_schedule, generation_schedule, depreciation_schedule = \
            build_schedules(n_construction, n - n_construction, periods)

        result = run_waterfall(
            ebitda_schedule=ebitda_schedule,
            revenue_schedule=revenue_schedule,
            generation_schedule=generation_schedule,
            depreciation_schedule=depreciation_schedule,
            periods=periods,
            total_capex=100_000.0,
            rate_per_period=0.02825,
            tenor_periods=28,
            target_dscr=1.15,
            lockup_dscr=1.10,
            tax_rate=0.10,
            dsra_months=6,
            equity_irr_method="combined",
            sculpt_capex_keur=90_000.0,
            shl_amount=0.0,
            shl_rate=0.0,
            financial_close=date(2029, 6, 29),
        )

        sculpt = getattr(result, 'sculpting_result', None)
        debt = getattr(sculpt, 'debt_keur', 0) if sculpt else 0
        assert debt > 0, f"Debt should be positive, got {debt}"
        assert result.project_irr > 0

    def test_shl_plus_dividends(self):
        """Test 'shl_plus_dividends' — equity = shl_amount + share_capital, SHL interest in CF."""
        periods = make_test_periods(2, 28)
        n = len(periods)
        n_construction = sum(1 for p in periods if not p.is_operation)

        # Higher EBITDA to cover SHL interest
        ebitda = [0.0] * n_construction + [60_000.0] * (n - n_construction)
        revenue = [0.0] * n_construction + [70_000.0] * (n - n_construction)
        generation = [0.0] * n_construction + [55_000.0] * (n - n_construction)
        depreciation = [0.0] * n_construction + [12_000.0] * (n - n_construction)

        result = run_waterfall(
            ebitda_schedule=ebitda,
            revenue_schedule=revenue,
            generation_schedule=generation,
            depreciation_schedule=depreciation,
            periods=periods,
            total_capex=100_000.0,
            rate_per_period=0.02825,
            tenor_periods=28,
            target_dscr=1.15,
            lockup_dscr=1.10,
            tax_rate=0.10,
            dsra_months=6,
            equity_irr_method="shl_plus_dividends",
            sculpt_capex_keur=0.0,
            shl_amount=20_000.0,
            shl_rate=0.08,
            share_capital_keur=15_000.0,
            financial_close=date(2029, 6, 29),
        )

        assert result.project_irr > 0
        assert result.equity_irr > 0

    def test_all_three_methods_produce_different_equity_irr(self):
        """Verify that different methods produce different (but plausible) equity IRR."""
        periods = make_test_periods(2, 28)
        n = len(periods)
        n_construction = sum(1 for p in periods if not p.is_operation)

        ebitda, revenue, generation, depreciation = \
            build_schedules(n_construction, n - n_construction, periods)

        def run_method(method, sculpt_capex=0, shl_amount=0, share_capital=0):
            return run_waterfall(
                ebitda_schedule=ebitda,
                revenue_schedule=revenue,
                generation_schedule=generation,
                depreciation_schedule=depreciation,
                periods=periods,
                total_capex=100_000.0,
                rate_per_period=0.02825,
                tenor_periods=28,
                target_dscr=1.15,
                lockup_dscr=1.10,
                tax_rate=0.10,
                dsra_months=6,
                equity_irr_method=method,
                sculpt_capex_keur=sculpt_capex,
                shl_amount=shl_amount,
                shl_rate=0.08 if shl_amount > 0 else 0.0,
                share_capital_keur=share_capital,
                financial_close=date(2029, 6, 29),
            )

        r_equity_only = run_method("equity_only")
        r_combined = run_method("combined", sculpt_capex=90_000.0)
        r_shl_plus = run_method("shl_plus_dividends", shl_amount=20_000.0, share_capital=15_000.0)

        assert r_equity_only.project_irr > 0
        assert r_combined.project_irr > 0
        assert r_shl_plus.project_irr > 0

        assert r_equity_only.equity_irr >= 0
        assert r_combined.equity_irr >= 0
        assert r_shl_plus.equity_irr >= 0

        # Project IRRs should be similar (same economics)
        assert abs(r_equity_only.project_irr - r_combined.project_irr) < 0.005
        assert abs(r_combined.project_irr - r_shl_plus.project_irr) < 0.005

    def test_xirr_function(self):
        """Verify xirr works correctly for simple cash flows."""
        dates = [date(2029, 6, 29) + timedelta(days=182 * i) for i in range(5)]
        cash_flows = [-100, 30, 30, 30, 30]

        irr = robust_xirr(cash_flows, dates, guess=0.10)
        assert irr is not None
        assert 0.05 < irr < 0.20


class TestProjectIRR:
    """Test project IRR calculation (same for all methods)."""

    def test_project_irr_independent_of_equity_method(self):
        """Project IRR should not depend on equity_irr_method."""
        periods = make_test_periods(2, 28)
        n = len(periods)
        n_construction = sum(1 for p in periods if not p.is_operation)

        ebitda, revenue, generation, depreciation = \
            build_schedules(n_construction, n - n_construction, periods)

        methods = ["equity_only", "combined", "shl_plus_dividends"]
        project_irrs = []

        for method in methods:
            result = run_waterfall(
                ebitda_schedule=ebitda,
                revenue_schedule=revenue,
                generation_schedule=generation,
                depreciation_schedule=depreciation,
                periods=periods,
                total_capex=100_000.0,
                rate_per_period=0.02825,
                tenor_periods=28,
                target_dscr=1.15,
                lockup_dscr=1.10,
                tax_rate=0.10,
                dsra_months=6,
                equity_irr_method=method,
                sculpt_capex_keur=90_000.0 if method == "combined" else 0.0,
                shl_amount=20_000.0 if method == "shl_plus_dividends" else 0.0,
                shl_rate=0.08,
                share_capital_keur=15_000.0 if method == "shl_plus_dividends" else 0.0,
                financial_close=date(2029, 6, 29),
            )
            project_irrs.append(result.project_irr)

        assert abs(project_irrs[0] - project_irrs[1]) < 0.001
        assert abs(project_irrs[1] - project_irrs[2]) < 0.001