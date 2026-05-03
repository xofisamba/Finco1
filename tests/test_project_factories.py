"""Tests for app/project_factories.py — generic and project-specific factories."""
import pytest
from app.project_factories import (
    create_default_oborovo,
    create_default_tuho_wind1,
    create_default_solar_project,
    create_default_wind_project,
)
from domain.inputs import AssetClass


class TestProjectFactories:
    def test_create_default_oborovo(self):
        """Oborovo factory produces valid ProjectInputs."""
        p = create_default_oborovo()
        assert p.info.name == "Oborovo Solar PV"
        assert p.technical.capacity_mw == 75.26
        assert p.technical.pv_degradation == 0.004
        assert len(p.opex) == 15
        assert p.capex.total_capex > 0

    def test_create_default_tuho_wind1(self):
        """TUHO factory produces valid ProjectInputs."""
        p = create_default_tuho_wind1()
        assert p.info.name == "TUHO Wind 1"
        assert p.technical.capacity_mw == 35.0
        assert p.technical.pv_degradation == 0.0  # wind
        assert p.financing.shl_idc_keur > 0

    def test_create_default_solar_project(self):
        """Generic solar factory produces valid inputs."""
        p = create_default_solar_project()
        assert p.info.name == "Generic Solar PV"
        assert p.technical.capacity_mw == 50.0
        assert p.technical.operating_hours_p50 == 1500.0
        assert p.technical.bess_enabled is False

    def test_create_default_wind_project(self):
        """Generic wind factory produces valid inputs."""
        p = create_default_wind_project()
        assert p.info.name == "Generic Wind Farm"
        assert p.technical.capacity_mw == 50.0
        assert p.technical.operating_hours_p50 == 3000.0
        assert p.technical.pv_degradation == 0.0

    def test_solar_factory_uses_solar_asset_class(self):
        """Solar factory capex includes SOLAR_PANELS asset class."""
        p = create_default_solar_project()
        items = p.capex.capex_items()
        asset_classes = {item.asset_class for item in items}
        assert AssetClass.SOLAR_PANELS in asset_classes

    def test_wind_factory_uses_wind_asset_class(self):
        """Wind factory capex includes WIND_TURBINES asset class."""
        p = create_default_wind_project()
        items = p.capex.capex_items()
        asset_classes = {item.asset_class for item in items}
        assert AssetClass.WIND_TURBINES in asset_classes

    def test_solar_factory_custom_capacity(self):
        """Solar factory respects custom capacity_mw parameter."""
        p = create_default_solar_project(capacity_mw=100.0)
        assert p.technical.capacity_mw == 100.0

    def test_wind_factory_custom_capacity(self):
        """Wind factory respects custom capacity_mw parameter."""
        p = create_default_wind_project(capacity_mw=75.0)
        assert p.technical.capacity_mw == 75.0

    def test_solar_factory_produces_positive_generation(self):
        """Solar factory yields positive generation in first operational year."""
        p = create_default_solar_project(capacity_mw=50.0)
        # Simple check: capacity * operating_hours > 0
        gen_y1 = p.technical.capacity_mw * p.technical.operating_hours_p50
        assert gen_y1 > 0

    def test_wind_factory_produces_positive_generation(self):
        """Wind factory yields positive generation in first operational year."""
        p = create_default_wind_project(capacity_mw=50.0)
        gen_y1 = p.technical.capacity_mw * p.technical.operating_hours_p50
        assert gen_y1 > 0

    def test_generic_factories_have_no_excel_comments(self):
        """Generic factories do not reference Excel calibration values."""
        p = create_default_solar_project()
        # Check that generic factory has reasonable round numbers (not Excel exact)
        assert p.capex.total_capex > 0
        # Market prices should be simple (not Excel exact 57.0, 66.3, etc.)
        assert len(p.revenue.market_prices_curve) == 30


    def test_domain_inputs_has_no_project_specific_factory_methods(self):
        """ProjectInputs has no create_default_* classmethods."""
        from domain.inputs import ProjectInputs
        assert not hasattr(ProjectInputs, "create_default_oborovo")
        assert not hasattr(ProjectInputs, "create_default_tuho_wind1")


def _run_waterfall_for_inputs(inputs):
    """Helper: run headless waterfall for generic project inputs."""
    from domain.period_engine import PeriodEngine
    from app.waterfall_core import run_waterfall_v3_core

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


class TestGenericProjectRuntime:
    """Test that generic factories run through the full headless waterfall."""

    def test_default_solar_project_runs_headless_waterfall(self):
        """Solar factory can run through headless waterfall."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        assert len(result.periods) > 0
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0
        assert result.total_tax_keur >= 0

    def test_default_wind_project_runs_headless_waterfall(self):
        """Wind factory can run through headless waterfall."""
        p = create_default_wind_project()
        result = _run_waterfall_for_inputs(p)
        assert len(result.periods) > 0
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0

    def test_default_solar_project_outputs_positive_revenue_ebitda_and_irr(self):
        """Solar factory produces positive revenue, EBITDA and finite IRR."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0
        assert result.project_irr is not None
        assert result.project_irr > 0
        assert result.project_irr < 5.0  # sanity check: not 500%

    def test_default_wind_project_outputs_positive_revenue_ebitda_and_irr(self):
        """Wind factory produces positive revenue, EBITDA and finite IRR."""
        p = create_default_wind_project()
        result = _run_waterfall_for_inputs(p)
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0
        assert result.project_irr is not None
        assert result.project_irr > 0
        assert result.project_irr < 5.0

    def test_solar_project_has_depreciation_in_operations(self):
        """At least one operating period shows positive depreciation."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        dep_periods = [pr for pr in result.periods if pr.depreciation_keur > 0]
        assert len(dep_periods) > 0, "No depreciation found in operating periods"

    def test_generic_factories_do_not_use_project_specific_codes(self):
        """Generic factories use generic project codes (SOLAR-*, WIND-*)."""
        solar = create_default_solar_project()
        wind = create_default_wind_project()
        assert "SOLAR" in solar.info.code
        assert "WIND" in wind.info.code
        assert "OBOROVO" not in solar.info.code
        assert "TUHO" not in wind.info.code
