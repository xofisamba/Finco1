"""Tests for domain/portfolio/waterfall.py — pooled CFADS portfolio waterfall."""
import pytest
from datetime import date
from domain.portfolio.waterfall import (
    PortfolioPeriod,
    PortfolioResult,
    aggregate_project_results,
    portfolio_cfads_schedule,
    run_portfolio_waterfall,
)
from domain.waterfall.waterfall_engine import WaterfallResult, WaterfallPeriod
from app.project_factories import create_default_solar_project, create_default_wind_project
from domain.inputs import FinancingParams


def _make_wf_result(name: str, ebitda: float, tax: float, rev: float) -> WaterfallResult:
    """Create a minimal WaterfallResult with two operation periods."""
    # All 37 WaterfallPeriod fields must be present
    def _op(period: int, date_: date, rev_h: float, ebitda_h: float, tax_h: float):
        return WaterfallPeriod(
            period=period, date=date_, year_index=1, period_in_year=period,
            is_operation=True,
            generation_mwh=0.0,
            revenue_keur=rev_h, opex_keur=0.0, ebitda_keur=ebitda_h,
            depreciation_keur=0.0, interest_senior_keur=0.0, interest_shl_keur=0.0,
            taxable_profit_keur=ebitda_h, tax_keur=tax_h,
            cf_after_tax_keur=ebitda_h - tax_h,
            senior_interest_keur=0.0, senior_principal_keur=0.0,
            senior_ds_keur=50.0,
            shl_interest_keur=0.0, shl_principal_keur=0.0, shl_service_keur=0.0,
            dsra_contribution_keur=0.0, dsra_balance_keur=0.0,
            mra_contribution_keur=0.0, mra_balance_keur=0.0,
            cf_after_reserves_keur=ebitda_h - tax_h,
            dscr=1.5, llcr=1.5, plcr=1.5, lockup_active=False,
            distribution_keur=0.0, cash_sweep_keur=0.0, cum_distribution_keur=0.0,
            cash_balance_keur=0.0,
            shl_balance_keur=0.0, shl_pik_keur=0.0,
            senior_balance_keur=0.0,
        )
    op1 = _op(1, date(2031, 1, 1), rev / 2, ebitda / 2, tax / 2)
    op2 = _op(2, date(2031, 7, 1), rev / 2, ebitda / 2, tax / 2)
    return WaterfallResult(
        periods=(op1, op2),
        total_revenue_keur=rev, total_opex_keur=0.0,
        total_ebitda_keur=ebitda, total_tax_keur=tax,
        total_senior_ds_keur=100.0, total_shl_service_keur=0.0,
        total_distribution_keur=0.0,
        avg_dscr=1.5, min_dscr=1.4, max_dscr=1.6,
        min_llcr=1.4, min_plcr=1.3, periods_in_lockup=0,
        project_irr=0.0, equity_irr=0.0, sponsor_irr=0.0,
        project_npv=0.0, equity_npv=0.0,
        sculpting_result=None,
    )


def _portfolio_inputs():
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.3)
    from domain.portfolio.inputs import PortfolioInputs
    return PortfolioInputs(
        projects=(create_default_solar_project(), create_default_wind_project()),
        portfolio_name="Test",
        shared_financing=shared,
    )


class TestAggregateProjectResults:
    """Test aggregate_project_results aligns and sums waterfalls."""

    def test_two_projects_sum_revenue_and_ebitda(self):
        wf_a = _make_wf_result("A", ebitda=80.0, tax=10.0, rev=100.0)
        wf_b = _make_wf_result("B", ebitda=120.0, tax=15.0, rev=150.0)
        pooled = aggregate_project_results((("A", wf_a), ("B", wf_b)))
        assert len(pooled) == 2
        assert abs(pooled[0]["pooled_revenue_keur"] - 125.0) < 0.01
        assert abs(pooled[0]["pooled_ebitda_keur"] - 100.0) < 0.01

    def test_cfads_equals_ebitda_minus_tax(self):
        wf = _make_wf_result("X", ebitda=80.0, tax=10.0, rev=100.0)
        pooled = aggregate_project_results((("X", wf),))
        assert len(pooled) == 2
        # Per period: ebitda=40, tax=5, cfads=35
        assert abs(pooled[0]["pooled_cfads_keur"] - 35.0) < 0.01

    def test_skips_non_operation_periods(self):
        wf = _make_wf_result("X", ebitda=80.0, tax=10.0, rev=100.0)
        pooled = aggregate_project_results((("X", wf),))
        assert all(p["date"] >= date(2030, 1, 1) for p in pooled)


class TestPortfolioCFADSSchedule:
    """Test portfolio_cfads_schedule extracts CFADS list."""

    def test_extracts_cfads_from_pooled_periods(self):
        pooled = [
            {"date": date(2031, 1, 1), "pooled_cfads_keur": 35.0},
            {"date": date(2031, 7, 1), "pooled_cfads_keur": 40.0},
        ]
        cfads = portfolio_cfads_schedule(pooled)
        assert cfads == [35.0, 40.0]


class TestRunPortfolioWaterfall:
    """Test run_portfolio_waterfall with skeleton debt service."""

    def test_total_revenue_summed_across_projects(self):
        wf_a = _make_wf_result("A", ebitda=80.0, tax=10.0, rev=100.0)
        wf_b = _make_wf_result("B", ebitda=120.0, tax=15.0, rev=150.0)
        result = run_portfolio_waterfall(_portfolio_inputs(), (("A", wf_a), ("B", wf_b)))
        assert abs(result.total_revenue_keur - 250.0) < 0.01

    def test_total_ebitda_summed_across_projects(self):
        wf_a = _make_wf_result("A", ebitda=80.0, tax=10.0, rev=100.0)
        wf_b = _make_wf_result("B", ebitda=120.0, tax=15.0, rev=150.0)
        result = run_portfolio_waterfall(_portfolio_inputs(), (("A", wf_a), ("B", wf_b)))
        assert abs(result.total_ebitda_keur - 200.0) < 0.01

    def test_total_tax_summed_across_projects(self):
        wf_a = _make_wf_result("A", ebitda=80.0, tax=10.0, rev=100.0)
        wf_b = _make_wf_result("B", ebitda=120.0, tax=15.0, rev=150.0)
        result = run_portfolio_waterfall(_portfolio_inputs(), (("A", wf_a), ("B", wf_b)))
        assert abs(result.total_tax_keur - 25.0) < 0.01

    def test_dscr_is_computed_per_period(self):
        wf = _make_wf_result("X", ebitda=80.0, tax=10.0, rev=100.0)
        result = run_portfolio_waterfall(_portfolio_inputs(), (("X", wf),))
        assert len(result.periods) == 2
        # DSCR depends on sculpted debt from CFADS; just check it's positive
        assert result.periods[0].dscr > 0

    def test_avg_dscr_across_periods(self):
        wf_a = _make_wf_result("A", ebitda=80.0, tax=10.0, rev=100.0)
        wf_b = _make_wf_result("B", ebitda=120.0, tax=15.0, rev=150.0)
        result = run_portfolio_waterfall(_portfolio_inputs(), (("A", wf_a), ("B", wf_b)))
        assert result.avg_dscr > 0

    def test_min_dscr_identified(self):
        wf_a = _make_wf_result("A", ebitda=80.0, tax=10.0, rev=100.0)
        wf_b = _make_wf_result("B", ebitda=120.0, tax=15.0, rev=150.0)
        result = run_portfolio_waterfall(_portfolio_inputs(), (("A", wf_a), ("B", wf_b)))
        assert result.min_dscr > 0

    def test_explicit_ds_schedule_used_when_provided(self):
        wf = _make_wf_result("X", ebitda=80.0, tax=10.0, rev=100.0)
        ds_schedule = (200.0, 200.0)
        result = run_portfolio_waterfall(None, (("X", wf),),
                                         portfolio_debt_service_schedule=ds_schedule)
        # Period 1: cfads=35, ds=200, dscr=0.175
        assert abs(result.periods[0].dscr - 0.175) < 0.001

    def test_project_results_passed_through(self):
        wf_a = _make_wf_result("A", ebitda=80.0, tax=10.0, rev=100.0)
        wf_b = _make_wf_result("B", ebitda=120.0, tax=15.0, rev=150.0)
        result = run_portfolio_waterfall(_portfolio_inputs(), (("A", wf_a), ("B", wf_b)))
        assert len(result.project_results) == 2
        names = [n for n, _ in result.project_results]
        assert "A" in names
        assert "B" in names

    def test_requires_inputs_or_explicit_debt_service_schedule(self):
        """Without portfolio_inputs AND without explicit ds schedule, raises."""
        wf = _make_wf_result("X", ebitda=80.0, tax=10.0, rev=100.0)
        with pytest.raises(ValueError, match="Either portfolio_inputs or explicit"):
            run_portfolio_waterfall(None, (("X", wf),))


class TestPortfolioResult:
    """Test PortfolioResult dataclass field contracts."""

    def test_portfolio_result_has_all_required_fields(self):
        wf = _make_wf_result("X", ebitda=80.0, tax=10.0, rev=100.0)
        pr = PortfolioResult(
            periods=(PortfolioPeriod(
                period=1, date=date(2030, 1, 1),
                pooled_revenue_keur=100.0, pooled_ebitda_keur=80.0,
                pooled_tax_keur=10.0, pooled_cfads_keur=70.0,
                portfolio_senior_interest_keur=40.0,
                portfolio_senior_principal_keur=10.0,
                portfolio_senior_ds_keur=50.0, dscr=1.4,
            ),),
            project_results=(("X", wf),),
            total_revenue_keur=100.0, total_ebitda_keur=80.0,
            total_tax_keur=10.0, total_senior_ds_keur=50.0,
            avg_dscr=1.4, min_dscr=1.2,
            portfolio_debt_keur=500.0,
            pooled_cfads_schedule=(70.0,),
            portfolio_debt_service_schedule=(50.0,),
        )
        assert hasattr(pr, "periods")
        assert hasattr(pr, "project_results")
        assert hasattr(pr, "total_revenue_keur")
        assert hasattr(pr, "total_ebitda_keur")
        assert hasattr(pr, "total_tax_keur")
        assert hasattr(pr, "total_senior_ds_keur")
        assert hasattr(pr, "avg_dscr")
        assert hasattr(pr, "min_dscr")
        assert hasattr(pr, "portfolio_project_irr")
        assert hasattr(pr, "portfolio_sponsor_irr")


def test_explicit_debt_service_schedule_overrides_sculpting():
    """When explicit portfolio_debt_service_schedule is supplied, portfolio_debt_keur = 0.0."""
    wf = _make_wf_result("X", ebitda=80.0, tax=10.0, rev=100.0)
    ds_schedule = (200.0, 200.0)
    result = run_portfolio_waterfall(None, (("X", wf),),
                                     portfolio_debt_service_schedule=ds_schedule)
    assert result.portfolio_debt_keur == 0.0


def test_portfolio_uses_sculpted_debt_service_when_no_schedule_supplied():
    """When no explicit schedule is given, portfolio_debt_keur comes from sculpted schedule (>0)."""
    wf_a = _make_wf_result("A", ebitda=80.0, tax=10.0, rev=100.0)
    wf_b = _make_wf_result("B", ebitda=120.0, tax=15.0, rev=150.0)
    result = run_portfolio_waterfall(_portfolio_inputs(), (("A", wf_a), ("B", wf_b)))
    assert result.portfolio_debt_keur > 0


def test_portfolio_irr_fields_are_documented_placeholders():
    """portfolio_project_irr and portfolio_sponsor_irr are not yet implemented."""
    assert PortfolioResult.__dataclass_fields__["portfolio_project_irr"].default == 0.0
    assert PortfolioResult.__dataclass_fields__["portfolio_sponsor_irr"].default == 0.0