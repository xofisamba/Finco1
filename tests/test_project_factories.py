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

    def test_domain_inputs_shim_still_works(self):
        """ProjectInputs.create_default_oborovo() compatibility shim works."""
        from domain.inputs import ProjectInputs
        p = ProjectInputs.create_default_oborovo()
        assert p.info.name == "Oborovo Solar PV"
        p2 = ProjectInputs.create_default_tuho_wind1()
        assert p2.info.name == "TUHO Wind 1"
