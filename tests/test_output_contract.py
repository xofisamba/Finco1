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
from domain.portfolio.inputs import PortfolioInputs, ProjectWeight
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
            ppa_base_tariff_eur_mwh=60.0,
            bess=BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0),
        )
        assert inputs.bess is not None
        assert isinstance(inputs.bess, BessParams)

    def test_hybrid_revenue_breakdown_has_required_fields(self):
        """HybridRevenueBreakdown must expose generation and revenue fields."""
        inputs = HybridInputs(
            solar_capacity_mw=50.0, operating_hours_p50=1500.0,
            ppa_base_tariff_eur_mwh=60.0,
            bess=BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0),
        )
        bd = hybrid_period_revenue(inputs, year_index=1, day_fraction=1.0)
        assert hasattr(bd, 'solar_generation_mwh')
        assert hasattr(bd, 'wind_generation_mwh')
        assert hasattr(bd, 'total_generation_mwh')
        assert hasattr(bd, 'clipped_generation_mwh')
        assert hasattr(bd, 'curtailment_mwh')
        assert hasattr(bd, 'ppa_revenue_keur')
        assert hasattr(bd, 'merchant_revenue_keur')
        assert hasattr(bd, 'co2_revenue_keur')
        assert hasattr(bd, 'bess_breakdown')
        assert hasattr(bd, 'bess_revenue_keur')
        assert hasattr(bd, 'gross_revenue_keur')
        assert hasattr(bd, 'net_revenue_keur')

    def test_hybrid_bess_revenue_included_when_bess_set(self):
        inputs = HybridInputs(
            solar_capacity_mw=50.0, operating_hours_p50=1500.0,
            ppa_base_tariff_eur_mwh=60.0,
            bess=BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0),
        )
        bd = hybrid_period_revenue(inputs, year_index=1, day_fraction=1.0)
        assert bd.bess_breakdown is not None
        assert bd.bess_revenue_keur > 0

    def test_hybrid_annual_revenue_sums_periods(self):
        """annual_hybrid_revenue aggregates two semi-annual periods."""
        inputs = HybridInputs(
            solar_capacity_mw=50.0, operating_hours_p50=1500.0,
            ppa_base_tariff_eur_mwh=60.0,
        )
        annual = annual_hybrid_revenue(inputs, year_index=1)
        assert annual.net_revenue_keur > 0

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

    def test_portfolio_inputs_has_required_fields(self):
        portfolio = PortfolioInputs(
            name="Test",
            projects=(ProjectWeight(name="A", weight=1.0, capacity_mw=50.0),),
        )
        assert hasattr(portfolio, 'name')
        assert hasattr(portfolio, 'projects')
        assert hasattr(portfolio, 'aggregation_method')
        assert hasattr(portfolio, 'num_projects')
        assert hasattr(portfolio, 'project_names')

    def test_portfolio_result_has_required_fields(self):
        portfolio = PortfolioInputs(
            name="Test",
            projects=(ProjectWeight(name="A", weight=1.0, capacity_mw=50.0),),
        )
        result = run_portfolio_waterfall(portfolio, {
            "A": {"revenue_keur": 1000, "ebitda_keur": 800, "tax_keur": 50,
                  "project_irr": 0.08, "equity_irr": 0.0, "sponsor_irr": 0.0, "project_npv": 0},
        })
        assert hasattr(result, 'project_revenues_keur')
        assert hasattr(result, 'project_ebitdas_keur')
        assert hasattr(result, 'project_irr')
        assert hasattr(result, 'project_npv')
        assert hasattr(result, 'total_revenue_keur')
        assert hasattr(result, 'total_ebitda_keur')
        assert hasattr(result, 'total_tax_keur')
        assert hasattr(result, 'avg_project_irr')
        assert hasattr(result, 'min_project_irr')
        assert hasattr(result, 'max_project_irr')
        assert hasattr(result, 'equity_irr')
        assert hasattr(result, 'sponsor_irr')
        assert hasattr(result, 'capacity_weighted_irr')

    def test_portfolio_irr_weighted_by_project_weight(self):
        portfolio = PortfolioInputs(
            name="Test",
            projects=(
                ProjectWeight(name="A", weight=0.6, capacity_mw=50.0),
                ProjectWeight(name="B", weight=0.4, capacity_mw=80.0),
            ),
        )
        result = run_portfolio_waterfall(portfolio, {
            "A": {"revenue_keur": 1000, "ebitda_keur": 800, "tax_keur": 50,
                  "project_irr": 0.08, "equity_irr": 0.0, "sponsor_irr": 0.0, "project_npv": 0},
            "B": {"revenue_keur": 1500, "ebitda_keur": 1200, "tax_keur": 80,
                  "project_irr": 0.10, "equity_irr": 0.0, "sponsor_irr": 0.0, "project_npv": 0},
        })
        # 0.6*0.08 + 0.4*0.10 = 0.088
        assert abs(result.avg_project_irr - 0.088) < 1e-9
        assert abs(result.capacity_weighted_irr - 0.088) < 1e-9

    def test_portfolio_revenues_summed_across_projects(self):
        portfolio = PortfolioInputs(
            name="Test",
            projects=(
                ProjectWeight(name="A", weight=0.5, capacity_mw=50.0),
                ProjectWeight(name="B", weight=0.5, capacity_mw=80.0),
            ),
        )
        result = run_portfolio_waterfall(portfolio, {
            "A": {"revenue_keur": 2000, "ebitda_keur": 1600, "tax_keur": 100,
                  "project_irr": 0.08, "equity_irr": 0.0, "sponsor_irr": 0.0, "project_npv": 0},
            "B": {"revenue_keur": 3000, "ebitda_keur": 2400, "tax_keur": 150,
                  "project_irr": 0.10, "equity_irr": 0.0, "sponsor_irr": 0.0, "project_npv": 0},
        })
        assert result.total_revenue_keur == 5000.0
        assert result.total_ebitda_keur == 4000.0
        assert result.total_tax_keur == 250.0
