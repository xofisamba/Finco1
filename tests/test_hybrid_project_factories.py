"""Tests for hybrid project factories in app/project_factories.py."""
import pytest
from app.project_factories import (
    create_default_solar_bess_project,
    create_default_wind_bess_project,
)


class TestCreateDefaultSolarBessProject:
    """Test suite for create_default_solar_bess_project factory."""

    def test_returns_project_inputs(self):
        result = create_default_solar_bess_project()
        assert result is not None

    def test_bess_enabled_flag(self):
        result = create_default_solar_bess_project()
        assert result.technical.bess_enabled is True

    def test_solar_capacity_passed_through(self):
        result = create_default_solar_bess_project(solar_capacity_mw=75.0)
        assert result.technical.capacity_mw == 75.0

    def test_bess_degradation_set(self):
        result = create_default_solar_bess_project()
        assert result.technical.bess_degradation > 0

    def test_ppa_tariff_positive_for_solar_bess(self):
        result = create_default_solar_bess_project()
        assert result.revenue.ppa_base_tariff > 0

    def test_co2_enabled_for_solar_bess(self):
        result = create_default_solar_bess_project()
        assert result.revenue.co2_enabled is True

    def test_operating_hours_p50_positive(self):
        result = create_default_solar_bess_project()
        assert result.technical.operating_hours_p50 > 0

    def test_horizon_years_passed_through(self):
        result = create_default_solar_bess_project(horizon_years=20)
        assert result.info.horizon_years == 20

    def test_name_contains_solar_and_bess(self):
        result = create_default_solar_bess_project()
        assert "Solar" in result.info.name or "BESS" in result.info.name


class TestCreateDefaultWindBessProject:
    """Test suite for create_default_wind_bess_project factory."""

    def test_returns_project_inputs(self):
        result = create_default_wind_bess_project()
        assert result is not None

    def test_bess_enabled_flag(self):
        result = create_default_wind_bess_project()
        assert result.technical.bess_enabled is True

    def test_wind_capacity_passed_through(self):
        result = create_default_wind_bess_project(wind_capacity_mw=100.0)
        assert result.technical.capacity_mw == 100.0

    def test_ppa_tariff_positive_for_wind_bess(self):
        result = create_default_wind_bess_project()
        assert result.revenue.ppa_base_tariff > 0

    def test_operating_hours_p50_for_wind(self):
        result = create_default_wind_bess_project()
        assert result.technical.operating_hours_p50 > 2000

    def test_balancing_cost_wind_positive(self):
        result = create_default_wind_bess_project()
        assert result.revenue.balancing_cost_wind_eur_mwh > 0

    def test_name_contains_wind(self):
        result = create_default_wind_bess_project()
        assert "Wind" in result.info.name

    def test_horizon_years_passed_through(self):
        result = create_default_wind_bess_project(horizon_years=25)
        assert result.info.horizon_years == 25

    def test_pv_degradation_zero_for_wind(self):
        result = create_default_wind_bess_project()
        assert result.technical.pv_degradation == 0.0
