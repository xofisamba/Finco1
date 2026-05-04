"""Tests for WaterfallRunConfig.from_inputs()."""
import pytest
from app.project_factories import create_default_solar_project, create_default_wind_project
from domain.period_engine import PeriodEngine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


def make_engine(inputs):
    return PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )


class TestFromInputsMapsFields:
    def test_maps_tax_rate(self):
        solar = create_default_solar_project()
        engine = make_engine(solar)
        config = WaterfallRunConfig.from_inputs(solar, engine)
        assert config.tax_rate == solar.tax.corporate_rate

    def test_maps_target_dscr(self):
        solar = create_default_solar_project()
        engine = make_engine(solar)
        config = WaterfallRunConfig.from_inputs(solar, engine)
        assert config.target_dscr == solar.financing.target_dscr

    def test_maps_shl_fields(self):
        solar = create_default_solar_project()
        engine = make_engine(solar)
        config = WaterfallRunConfig.from_inputs(solar, engine)
        assert config.shl_amount_keur == solar.financing.shl_amount_keur
        assert config.shl_rate == solar.financing.shl_rate
        assert config.shl_idc_keur == solar.financing.shl_idc_keur
        assert config.shl_tenor_years == solar.financing.shl_tenor_years

    def test_maps_sculpt_capex(self):
        solar = create_default_solar_project()
        engine = make_engine(solar)
        config = WaterfallRunConfig.from_inputs(solar, engine)
        assert config.sculpt_capex_keur == solar.capex.sculpt_capex_keur

    def test_maps_share_capital(self):
        solar = create_default_solar_project()
        engine = make_engine(solar)
        config = WaterfallRunConfig.from_inputs(solar, engine)
        assert config.share_capital_keur == solar.financing.share_capital_keur

    def test_maps_debt_sizing_method(self):
        solar = create_default_solar_project()
        engine = make_engine(solar)
        config = WaterfallRunConfig.from_inputs(solar, engine)
        assert config.debt_sizing_method.value == solar.financing.debt_sizing_method

    def test_maps_equity_irr_method(self):
        solar = create_default_solar_project()
        engine = make_engine(solar)
        config = WaterfallRunConfig.from_inputs(solar, engine)
        assert config.equity_irr_method.value == solar.financing.equity_irr_method

    def test_maps_dsra_months(self):
        solar = create_default_solar_project()
        engine = make_engine(solar)
        config = WaterfallRunConfig.from_inputs(solar, engine)
        assert config.dsra_months == solar.financing.dsra_months

    def test_wind_project_also_works(self):
        wind = create_default_wind_project()
        engine = make_engine(wind)
        config = WaterfallRunConfig.from_inputs(wind, engine)
        assert config.tax_rate == wind.tax.corporate_rate
        assert config.shl_amount_keur == wind.financing.shl_amount_keur
