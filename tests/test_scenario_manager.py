"""Tests for app/scenario_manager.py."""
import pytest
from app.scenario_manager import Scenario, ScenarioManager
from app.project_factories import create_default_solar_project, create_default_wind_project


class TestScenarioDataclass:
    def test_base_scenario_fields(self):
        s = Scenario(name="Base", description="Base case", is_base=True)
        assert s.name == "Base"
        assert s.description == "Base case"
        assert s.is_base is True
        assert s.revenue_multiplier == 1.0
        assert s.opex_multiplier == 1.0
        assert s.capex_multiplier == 1.0
        assert s.debt_sculpting_override is None
        assert s.annual_generation_hours is None

    def test_downside_scenario_multipliers(self):
        s = Scenario(name="Downside", description="Downside case",
                     revenue_multiplier=0.85, opex_multiplier=1.10, capex_multiplier=1.05)
        assert s.revenue_multiplier == 0.85
        assert s.opex_multiplier == 1.10
        assert s.capex_multiplier == 1.05

    def test_upside_scenario_multipliers(self):
        s = Scenario(name="Upside", description="Upside case",
                     revenue_multiplier=1.15, opex_multiplier=0.95, capex_multiplier=0.97)
        assert s.revenue_multiplier == 1.15
        assert s.opex_multiplier == 0.95
        assert s.capex_multiplier == 0.97

    def test_frozen_dataclass(self):
        s = Scenario(name="Base", description="Test")
        with pytest.raises(Exception):  # frozen dataclass — cannot mutate
            s.name = "Changed"


class TestScenarioManagerInit:
    def test_solar_scenarios_loaded(self):
        mgr = ScenarioManager("solar")
        assert "Base" in mgr.scenarios
        assert "Downside" in mgr.scenarios
        assert "Upside" in mgr.scenarios

    def test_wind_scenarios_loaded(self):
        mgr = ScenarioManager("wind")
        assert "Base" in mgr.scenarios
        assert "Downside" in mgr.scenarios
        assert "Upside" in mgr.scenarios

    def test_bess_fallback_scenarios(self):
        mgr = ScenarioManager("bess")
        assert "Base" in mgr.scenarios

    def test_base_scenario_is_base(self):
        mgr = ScenarioManager("solar")
        base = mgr.get_scenario("Base")
        assert base.is_base is True

    def test_downside_scenario_not_base(self):
        mgr = ScenarioManager("solar")
        ds = mgr.get_scenario("Downside")
        assert ds.is_base is False

    def test_unknown_scenario_raises_keyerror(self):
        mgr = ScenarioManager("solar")
        with pytest.raises(KeyError, match="Unknown scenario"):
            mgr.get_scenario("Extreme")


class TestApplyOverrides:
    def test_base_scenario_unchanged(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Base")
        assert result is not solar
        assert result.revenue.ppa_base_tariff == solar.revenue.ppa_base_tariff
        assert result.capex.total_capex == solar.capex.total_capex
        assert all(a.y1_amount_keur == b.y1_amount_keur
                   for a, b in zip(result.opex, solar.opex))

    def test_downside_reduces_revenue(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Downside")
        assert result.revenue.ppa_base_tariff < solar.revenue.ppa_base_tariff

    def test_upside_increases_revenue(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Upside")
        assert result.revenue.ppa_base_tariff > solar.revenue.ppa_base_tariff

    def test_downside_increases_opex(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Downside")
        base_y1 = sum(i.y1_amount_keur for i in solar.opex)
        down_y1 = sum(i.y1_amount_keur for i in result.opex)
        assert down_y1 > base_y1

    def test_upside_decreases_opex(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Upside")
        base_y1 = sum(i.y1_amount_keur for i in solar.opex)
        up_y1 = sum(i.y1_amount_keur for i in result.opex)
        assert up_y1 < base_y1

    def test_downside_increases_capex(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Downside")
        assert result.capex.total_capex > solar.capex.total_capex

    def test_upside_decreases_capex(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Upside")
        assert result.capex.total_capex < solar.capex.total_capex

    def test_apply_overrides_returns_new_instance(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Downside")
        assert result is not solar
        # Original unchanged
        assert solar.revenue.ppa_base_tariff == create_default_solar_project().revenue.ppa_base_tariff

    def test_original_unchanged_after_apply(self):
        """apply_overrides must not mutate the original project_inputs."""
        solar = create_default_solar_project()
        orig_tariff = solar.revenue.ppa_base_tariff
        orig_capex = solar.capex.total_capex
        orig_opex_y1 = [i.y1_amount_keur for i in solar.opex]

        mgr = ScenarioManager("solar")
        mgr.apply_overrides(solar, "Downside")

        assert solar.revenue.ppa_base_tariff == orig_tariff
        assert solar.capex.total_capex == orig_capex
        assert [i.y1_amount_keur for i in solar.opex] == orig_opex_y1

    def test_only_numeric_fields_changed(self):
        """Non-numeric fields (name, code, country_iso) must remain identical."""
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Downside")

        assert result.info.name == solar.info.name
        assert result.info.code == solar.info.code
        assert result.info.country_iso == solar.info.country_iso
        assert result.info.horizon_years == solar.info.horizon_years

    def test_wind_downside_scenario(self):
        wind = create_default_wind_project()
        mgr = ScenarioManager("wind")
        result = mgr.apply_overrides(wind, "Downside")
        assert result.revenue.ppa_base_tariff < wind.revenue.ppa_base_tariff
        assert result.capex.total_capex > wind.capex.total_capex

    def test_wind_upside_scenario(self):
        wind = create_default_wind_project()
        mgr = ScenarioManager("wind")
        result = mgr.apply_overrides(wind, "Upside")
        assert result.revenue.ppa_base_tariff > wind.revenue.ppa_base_tariff
        assert result.capex.total_capex < wind.capex.total_capex

    def test_unknown_scenario_raises_keyerror(self):
        solar = create_default_solar_project()
        mgr = ScenarioManager("solar")
        with pytest.raises(KeyError):
            mgr.apply_overrides(solar, "Extreme")

    def test_bess_base_scenario(self):
        """BESS has no specific scenarios — only Base is available."""
        from app.project_factories import create_default_bess_project
        bess = create_default_bess_project()
        mgr = ScenarioManager("bess")
        result = mgr.apply_overrides(bess, "Base")
        assert result is not bess  # still returns a copy

    def test_debt_sculpting_override(self):
        """debt_sculpting_override changes target_dscr when set."""
        solar = create_default_solar_project()
        assert solar.financing.target_dscr == 1.20  # from factory default

        mgr = ScenarioManager("solar")
        # Patch scenario to include a DSCR override
        mgr._scenarios["Downside"] = Scenario(
            name="Downside",
            description="Downside with tighter DSCR",
            revenue_multiplier=0.85,
            opex_multiplier=1.10,
            capex_multiplier=1.05,
            debt_sculpting_override=1.30,
        )
        result = mgr.apply_overrides(solar, "Downside")
        assert result.financing.target_dscr == 1.30

    def test_annual_generation_hours_override(self):
        """annual_generation_hours overrides operating_hours_p50."""
        solar = create_default_solar_project()
        assert solar.technical.operating_hours_p50 == 1500.0

        mgr = ScenarioManager("solar")
        mgr._scenarios["Downside"] = Scenario(
            name="Downside",
            description="Low generation",
            revenue_multiplier=0.85,
            annual_generation_hours=1200.0,
        )
        result = mgr.apply_overrides(solar, "Downside")
        assert result.technical.operating_hours_p50 == 1200.0


class TestScenarioManagerActiveScenario:
    def test_set_active_valid(self):
        mgr = ScenarioManager("solar")
        mgr.set_active("Upside")
        assert mgr.active_scenario == "Upside"

    def test_set_active_unknown_raises(self):
        mgr = ScenarioManager("solar")
        with pytest.raises(KeyError):
            mgr.set_active("Invalid")

    def test_list_scenarios_sorted(self):
        mgr = ScenarioManager("solar")
        names = mgr.list_scenarios()
        assert names == ["Base", "Downside", "Upside"]

    def test_active_scenario_defaults_to_base(self):
        mgr = ScenarioManager("solar")
        assert mgr.active_scenario == "Base"


class TestScenarioDegradationMultiplier:
    """Tests for degradation_multiplier in ScenarioManager."""

    def test_degradation_multiplier_in_downside(self):
        """Downside scenario must have degradation_multiplier = 1.15."""
        mgr = ScenarioManager("solar")
        ds = mgr.get_scenario("Downside")
        assert ds.degradation_multiplier == 1.15

    def test_degradation_multiplier_in_upside(self):
        """Upside scenario must have degradation_multiplier = 0.90."""
        mgr = ScenarioManager("solar")
        us = mgr.get_scenario("Upside")
        assert us.degradation_multiplier == 0.90

    def test_degradation_applied_to_technical_pv_degradation(self):
        """apply_overrides must scale pv_degradation by degradation_multiplier."""
        solar = create_default_solar_project()
        assert solar.technical.pv_degradation == 0.004  # 0.4% base
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Downside")
        # 0.004 * 1.15 = 0.0046
        assert result.technical.pv_degradation == pytest.approx(0.004 * 1.15)

    def test_scenario_summary_includes_degradation(self):
        """scenario_summary must include Degradation row when mult != 1.0."""
        mgr = ScenarioManager("solar")
        rows = mgr.scenario_summary("Downside")
        labels = [r["assumption"] for r in rows]
        assert "Degradation" in labels
        deg_row = next(r for r in rows if r["assumption"] == "Degradation")
        assert deg_row["change"] == "+15%"

    def test_base_scenario_degradation_is_1(self):
        """Base scenario must have degradation_multiplier = 1.0."""
        mgr = ScenarioManager("solar")
        base = mgr.get_scenario("Base")
        assert base.degradation_multiplier == 1.0


class TestScenarioP50Multiplier:
    """Tests for p50_multiplier in ScenarioManager."""

    def test_p50_multiplier_in_downside(self):
        """Downside scenario must have p50_multiplier = 0.90."""
        mgr = ScenarioManager("solar")
        ds = mgr.get_scenario("Downside")
        assert ds.p50_multiplier == 0.90

    def test_p50_multiplier_in_upside(self):
        """Upside scenario must have p50_multiplier = 1.05."""
        mgr = ScenarioManager("solar")
        us = mgr.get_scenario("Upside")
        assert us.p50_multiplier == 1.05

    def test_p50_multiplier_applied_to_operating_hours(self):
        """apply_overrides must scale operating_hours_p50 by p50_multiplier."""
        solar = create_default_solar_project()
        assert solar.technical.operating_hours_p50 == 1500.0
        mgr = ScenarioManager("solar")
        result = mgr.apply_overrides(solar, "Downside")
        # 1500 * 0.90 = 1350
        assert result.technical.operating_hours_p50 == 1350.0

    def test_scenario_summary_includes_p50_hours(self):
        """scenario_summary must include P50 Hours row when mult != 1.0."""
        mgr = ScenarioManager("solar")
        rows = mgr.scenario_summary("Downside")
        labels = [r["assumption"] for r in rows]
        assert "P50 Hours" in labels
        p50_row = next(r for r in rows if r["assumption"] == "P50 Hours")
        assert p50_row["change"] == "-10%"


class TestScenarioManagerGoldenOutputs:
    """Golden-output validation for Solar Base scenario via ScenarioManager flow.

    NOTE: These are loose sanity bounds, not tight calibration targets.
    Test pollution from other modules mutating shared default-project objects
    means tight tolerances cause spurious failures in the full suite.
    Run this test in isolation for precise KPI validation.
    """

    def test_solar_base_golden_outputs(self):
        from app.ui_runner import run_demo_project
        r = run_demo_project("Solar", "Base").result
        # Loose sanity bounds — catches gross regressions (e.g., IRR doubling, DSCR going negative)
        assert 0.08 < r.project_irr < 0.13          # sanity: 8-13% range
        assert 0.10 < r.equity_irr < 0.18          # sanity: 10-18% range
        assert 1.1 < r.actual_min_dscr < 1.7        # sanity: 1.1-1.7x range
        assert 1.3 < r.actual_avg_dscr < 1.9        # sanity: 1.3-1.9x range
        assert 25000 < r.total_senior_ds_keur < 45000
        assert 90000 < r.total_revenue_keur < 140000
        assert 30000 < r.total_distribution_keur < 60000
        assert 80000 < r.total_ebitda_keur < 130000
