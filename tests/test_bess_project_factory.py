"""Tests for BESS project factory in app/project_factories.py."""
import pytest
from app.project_factories import create_default_bess_project


class TestCreateDefaultBessProject:
    """Test suite for create_default_bess_project factory."""

    def test_returns_project_inputs(self):
        result = create_default_bess_project()
        assert result is not None

    def test_bess_enabled_flag(self):
        result = create_default_bess_project()
        assert result.technical.bess_enabled is True

    def test_capacity_mw_passed_through(self):
        result = create_default_bess_project(power_mw=25.0)
        assert result.technical.capacity_mw == 25.0

    def test_bess_degradation_set(self):
        result = create_default_bess_project()
        assert result.technical.bess_degradation == 0.02

    def test_ppa_base_tariff_zero_for_bess(self):
        result = create_default_bess_project()
        assert result.revenue.ppa_base_tariff == 0.0

    def test_ppa_term_zero(self):
        result = create_default_bess_project()
        assert result.revenue.ppa_term_years == 0

    def test_co2_disabled(self):
        result = create_default_bess_project()
        assert result.revenue.co2_enabled is False

    def test_operating_hours_zero(self):
        result = create_default_bess_project()
        assert result.technical.operating_hours_p50 == 0.0
        assert result.technical.operating_hours_p90_10y == 0.0

    def test_horizon_years_passed_through(self):
        result = create_default_bess_project(horizon_years=15)
        assert result.info.horizon_years == 15

    def test_construction_months_passed_through(self):
        result = create_default_bess_project(construction_months=18)
        assert result.info.construction_months == 18

    def test_period_frequency_is_semestrial(self):
        result = create_default_bess_project()
        assert result.info.period_frequency.value == "Semestrial"

    def test_capex_has_bess_asset_classes(self):
        result = create_default_bess_project()
        # The BESS cells should be in capex.epc_contract
        assert result.capex.epc_contract.asset_class.value == "bess_cells"
        assert result.capex.production_units.asset_class.value == "bess_pe"

    def test_name_contains_bess(self):
        result = create_default_bess_project()
        assert "BESS" in result.info.name

    def test_all_opex_items_have_valid_structure(self):
        result = create_default_bess_project()
        assert len(result.opex) > 0
        for item in result.opex:
            assert item.name is not None
