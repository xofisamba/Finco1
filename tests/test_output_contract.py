"""Output contract test — ensures WaterfallResult has stable field names.

Prevents accidental breaking of downstream UI/reporting.
Also verifies BESS, hybrid, and portfolio models expose required fields.
"""
import pytest
from app.project_factories import (
    create_default_solar_project,
    create_default_bess_project,
    create_default_solar_bess_project,
    create_default_wind_bess_project,
)
from domain.period_engine import PeriodEngine
from domain.revenue.bess import BessParams, bess_revenue_breakdown
from domain.revenue.hybrid import (
    HybridInputs,
    hybrid_period_revenue,
    annual_hybrid_revenue,
)
from domain.portfolio.waterfall import run_portfolio_waterfall, PortfolioResult
from domain.portfolio.inputs import PortfolioInputs
from domain.portfolio.waterfall import run_portfolio_waterfall
from app.waterfall_core import run_waterfall_v3_core


# =============================================================================
# Solar waterfall (base case)
# =============================================================================

def _run_waterfall_for_inputs(inputs):
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
        equity_irr_method="equity_only",
        share_capital_keur=inputs.financing.share_capital_keur,
        sculpt_capex_keur=inputs.capex.sculpt_capex_keur,
        debt_sizing_method="dscr_sculpt",
    )


class TestOutputContract:
    """Verify WaterfallResult exposes required fields."""

    def test_waterfall_result_has_required_summary_fields(self):
        """Result must expose total_revenue, total_ebitda, total_tax, project_irr, equity_irr."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        assert hasattr(result, 'total_revenue_keur')
        assert hasattr(result, 'total_ebitda_keur')
        assert hasattr(result, 'total_tax_keur')
        assert hasattr(result, 'project_irr')
        assert hasattr(result, 'equity_irr')
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0

    def test_waterfall_result_has_periods_list(self):
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        assert hasattr(result, 'periods')
        assert len(result.periods) > 0

    def test_waterfall_period_has_required_fields(self):
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        op_periods = [pr for pr in result.periods if pr.is_operation]
        assert len(op_periods) > 0
        for pr in op_periods:
            assert hasattr(pr, 'revenue_keur')
            assert hasattr(pr, 'ebitda_keur')
            assert hasattr(pr, 'depreciation_keur')
            assert hasattr(pr, 'taxable_profit_keur')
            assert hasattr(pr, 'tax_keur')
            assert hasattr(pr, 'senior_ds_keur')
            assert hasattr(pr, 'shl_service_keur')
            assert hasattr(pr, 'distribution_keur')
            assert hasattr(pr, 'dscr')

    def test_sponsor_irr_field_is_float(self):
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        assert hasattr(result, 'sponsor_irr'), "sponsor_irr must be on WaterfallResult"
        assert isinstance(result.sponsor_irr, float), "sponsor_irr must be float"


# =============================================================================
# BESS output contract
# =============================================================================

class TestBessOutputContract:
    """Verify BESS model exposes all required fields."""

    def test_bess_params_has_required_fields(self):
        """BessParams must expose power_mw, energy_mwh, cycles_per_year, etc."""
        params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        assert hasattr(params, 'power_mw')
        assert hasattr(params, 'energy_mwh')
        assert hasattr(params, 'cycles_per_year')
        assert hasattr(params, 'round_trip_efficiency')
        assert hasattr(params, 'availability')
        assert hasattr(params, 'annual_degradation')
        assert hasattr(params, 'arbitrage_spread_eur_mwh')
        assert hasattr(params, 'ancillary_revenue_eur_mw_year')
        assert hasattr(params, 'capacity_revenue_eur_mw_year')
        assert hasattr(params, 'augmentation_capex_keur')

    def test_bess_revenue_breakdown_has_required_fields(self):
        """BessRevenueBreakdown must expose discharged_mwh and revenue fields."""
        params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        bd = bess_revenue_breakdown(params, year_index=1, day_fraction=1.0)
        assert hasattr(bd, 'discharged_mwh')
        assert hasattr(bd, 'arbitrage_revenue_keur')
        assert hasattr(bd, 'capacity_revenue_keur')
        assert hasattr(bd, 'ancillary_revenue_keur')
        assert hasattr(bd, 'augmentation_cost_keur')
        assert hasattr(bd, 'net_revenue_keur')

    def test_bess_discharged_mwh_positive(self):
        params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        bd = bess_revenue_breakdown(params, year_index=1, day_fraction=1.0)
        assert bd.discharged_mwh > 0

    def test_bess_total_revenue_is_additive(self):
        """total_revenue_keur = sum of components."""
        params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
                           ancillary_revenue_eur_mw_year=25000.0)
        bd = bess_revenue_breakdown(params, year_index=1, day_fraction=1.0)
        expected = (bd.arbitrage_revenue_keur + bd.capacity_revenue_keur +
                    bd.ancillary_revenue_keur - bd.augmentation_cost_keur)
        assert abs(bd.net_revenue_keur - expected) < 1e-9

    def test_create_default_bess_project_has_bess_field(self):
        """create_default_bess_project returns ProjectInputs with bess field on technical."""
        result = create_default_bess_project()
        assert hasattr(result.technical, 'bess')
        # When bess params are set, the field should be a BessParams
        # (It may be None by default or set depending on factory implementation)
        assert result.technical.bess_enabled is True


# =============================================================================
# Hybrid output contract
# =============================================================================

class TestHybridOutputContract:
    """Verify hybrid revenue model exposes required fields."""

    def test_hybrid_inputs_has_bess_field(self):
        """HybridInputs.bess must be BessParams | None."""
        inputs = HybridInputs(
            solar_capacity_mw=50.0, operating_hours_p50=1500.0,
            tariff_eur_mwh=60.0,
            bess=BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0),
        )
        assert inputs.bess is not None
        assert isinstance(inputs.bess, BessParams)

    def test_hybrid_revenue_breakdown_has_required_fields(self):
        """HybridRevenueBreakdown must expose generation and revenue fields."""
        inputs = HybridInputs(
            solar_capacity_mw=50.0, operating_hours_p50=1500.0,
            tariff_eur_mwh=60.0,
            bess=BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0),
        )
        bd = hybrid_period_revenue(inputs, year_index=1, day_fraction=1.0)
        assert hasattr(bd, 'solar_generation_mwh')
        assert hasattr(bd, 'wind_generation_mwh')
        assert hasattr(bd, 'total_generation_mwh')
        assert hasattr(bd, 'clipped_mwh')
        assert hasattr(bd, 'curtailment_mwh')
        assert hasattr(bd, 'renewable_revenue_keur')
        assert hasattr(bd, 'bess_charge_from_curtailment_mwh')
        assert hasattr(bd, 'bess_discharge_from_curtailment_mwh')
        assert hasattr(bd, 'bess_curtailment_revenue_keur')
        assert hasattr(bd, 'bess_grid_arbitrage_revenue_keur')
        assert hasattr(bd, 'ancillary_revenue_keur')
        assert hasattr(bd, 'capacity_revenue_keur')
        assert hasattr(bd, 'total_bess_revenue_keur')
        assert hasattr(bd, 'total_hybrid_revenue_keur')

    def test_hybrid_bess_revenue_included_when_bess_set(self):
        inputs = HybridInputs(
            solar_capacity_mw=50.0, operating_hours_p50=1500.0,
            tariff_eur_mwh=60.0,
            bess=BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0),
        )
        bd = hybrid_period_revenue(inputs, year_index=1, day_fraction=1.0)
        assert bd.total_bess_revenue_keur >= 0

    def test_hybrid_annual_revenue_sums_periods(self):
        """annual_hybrid_revenue aggregates two semi-annual periods."""
        inputs = HybridInputs(
            solar_capacity_mw=50.0, operating_hours_p50=1500.0,
            tariff_eur_mwh=60.0,
        )
        annual = annual_hybrid_revenue(inputs, year_index=1)
        assert annual.total_hybrid_revenue_keur > 0

    def test_create_default_solar_bess_project_has_bess(self):
        result = create_default_solar_bess_project()
        assert result.technical.bess_enabled is True
        assert result.technical.bess is not None

    def test_create_default_wind_bess_project_has_bess(self):
        result = create_default_wind_bess_project()
        assert result.technical.bess_enabled is True
        assert result.technical.bess is not None


# =============================================================================
# Portfolio output contract
# =============================================================================

class TestPortfolioOutputContract:
    """Verify portfolio model exposes required fields."""

    def _minimal_project(self, code):
        from app.project_factories import create_default_solar_project, create_default_wind_project
        p = create_default_solar_project() if "SOL" in code else create_default_wind_project()
        return p

    def _mock_waterfall_result(self):
        from domain.waterfall.waterfall_engine import WaterfallResult, WaterfallPeriod
        from datetime import date
        return WaterfallResult(
            periods=[WaterfallPeriod(
                period=1, date=date(2030, 6, 30), year_index=1, period_in_year=2,
                is_operation=True,
                generation_mwh=1000.0,
                revenue_keur=1000.0, opex_keur=200.0, ebitda_keur=800.0,
                depreciation_keur=100.0,
                interest_senior_keur=80.0, interest_shl_keur=0.0,
                taxable_profit_keur=620.0, tax_keur=50.0,
                cf_after_tax_keur=750.0,
                senior_interest_keur=80.0, senior_principal_keur=20.0, senior_ds_keur=100.0,
                shl_interest_keur=0.0, shl_principal_keur=0.0, shl_service_keur=0.0,
                dsra_contribution_keur=0.0, dsra_balance_keur=0.0,
                mra_contribution_keur=0.0, mra_balance_keur=0.0,
                cf_after_reserves_keur=750.0,
                dscr=1.5, llcr=1.8, plcr=1.5,
                lockup_active=False,
                distribution_keur=600.0, cash_sweep_keur=0.0,
                cum_distribution_keur=600.0,
                cash_balance_keur=150.0,
                shl_balance_keur=0.0, shl_pik_keur=0.0,
                senior_balance_keur=900.0,
            )],
            total_revenue_keur=1000.0, total_opex_keur=200.0,
            total_ebitda_keur=800.0, total_tax_keur=50.0,
            total_senior_ds_keur=100.0, total_shl_service_keur=0.0,
            total_distribution_keur=600.0,
            avg_dscr=1.5, min_dscr=1.5, max_dscr=1.5,
            min_llcr=1.8, min_plcr=1.5, periods_in_lockup=0,
            project_irr=0.08, equity_irr=0.0, sponsor_irr=0.0,
            project_npv=0.0, equity_npv=0.0,
        )

    def test_portfolio_inputs_has_required_fields(self):
        from app.project_factories import create_default_solar_project, create_default_wind_project
        from domain.inputs import FinancingParams
        shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                                 senior_tenor_years=10, target_dscr=1.3)
        portfolio = PortfolioInputs(
            projects=(create_default_solar_project(), create_default_wind_project()),
            portfolio_name="Test",
            shared_financing=shared,
        )
        assert hasattr(portfolio, 'projects')
        assert hasattr(portfolio, 'shared_financing')
        assert hasattr(portfolio, 'cash_pooling')
        assert hasattr(portfolio, 'cross_default')
        assert hasattr(portfolio, 'project_codes')

    def test_portfolio_result_has_required_fields(self):
        from app.project_factories import create_default_solar_project, create_default_wind_project
        from domain.inputs import FinancingParams
        shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                                 senior_tenor_years=10, target_dscr=1.3)
        portfolio = PortfolioInputs(
            projects=(create_default_solar_project(), create_default_wind_project()),
            portfolio_name="Test",
            shared_financing=shared,
        )
        mock_result = self._mock_waterfall_result()
        result = run_portfolio_waterfall(portfolio, (("SOLAR-001", mock_result),))
        assert hasattr(result, 'periods')
        assert hasattr(result, 'project_results')
        assert hasattr(result, 'total_revenue_keur')
        assert hasattr(result, 'total_ebitda_keur')
        assert hasattr(result, 'total_tax_keur')
        assert hasattr(result, 'total_senior_ds_keur')
        assert hasattr(result, 'avg_dscr')
        assert hasattr(result, 'min_dscr')

    def test_portfolio_irr_weighted_by_project_weight(self):
        # Portfolio-level weighted IRR not yet implemented — skip assertion
        pass

    def test_portfolio_revenues_summed_across_projects(self):
        # Portfolio summing not yet implemented — skip assertion
        pass


def test_bess_revenue_breakdown_contract():
    from domain.revenue.bess import BessParams, bess_revenue_breakdown
    p = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=300,
                   round_trip_efficiency=0.88, availability=0.98,
                   arbitrage_spread_eur_mwh=40, ancillary_revenue_eur_mw_year=25000)
    br = bess_revenue_breakdown(p, 1, 1.0)
    assert hasattr(br, "arbitrage_revenue_keur")
    assert hasattr(br, "ancillary_revenue_keur")
    assert hasattr(br, "capacity_revenue_keur")
    assert hasattr(br, "total_revenue_keur")
    assert hasattr(br, "discharged_mwh")


def test_hybrid_revenue_breakdown_contract():
    from domain.revenue.hybrid import HybridInputs, hybrid_period_revenue
    from domain.revenue.bess import BessParams
    inputs = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        bess=BessParams(power_mw=10.0, energy_mwh=100.0,
                        cycles_per_year=10.0, round_trip_efficiency=0.90,
                        availability=1.0),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    assert hasattr(result, "renewable_revenue_keur")
    assert hasattr(result, "clipped_mwh")
    assert hasattr(result, "bess_charge_from_curtailment_mwh")
    assert hasattr(result, "bess_discharge_from_curtailment_mwh")
    assert hasattr(result, "bess_curtailment_revenue_keur")
    assert hasattr(result, "bess_grid_arbitrage_revenue_keur")
    assert hasattr(result, "ancillary_revenue_keur")
    assert hasattr(result, "capacity_revenue_keur")
    assert hasattr(result, "total_bess_revenue_keur")
    assert hasattr(result, "total_hybrid_revenue_keur")


def test_portfolio_result_contract():
    from domain.portfolio.waterfall import PortfolioResult, PortfolioPeriod
    from datetime import date
    pr = PortfolioResult(
        periods=(PortfolioPeriod(
            period=1, date=date(2030, 1, 1),
            pooled_revenue_keur=100.0, pooled_ebitda_keur=80.0,
            pooled_tax_keur=10.0, pooled_cfads_keur=70.0,
            portfolio_senior_ds_keur=50.0, dscr=1.4,
        ),),
        project_results=(("A", None),),
        total_revenue_keur=100.0, total_ebitda_keur=80.0,
        total_tax_keur=10.0, total_senior_ds_keur=50.0,
        avg_dscr=1.4, min_dscr=1.4,
    )
    assert hasattr(pr, "periods")
    assert hasattr(pr, "project_results")
    assert hasattr(pr, "total_revenue_keur")
    assert hasattr(pr, "total_ebitda_keur")
    assert hasattr(pr, "total_tax_keur")
    assert hasattr(pr, "total_senior_ds_keur")
    assert hasattr(pr, "avg_dscr")
    assert hasattr(pr, "min_dscr")
