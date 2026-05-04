"""Tests for app/scenarios.py — uses real project factories."""
import pytest
from app.scenarios import (
    apply_scenario,
    get_scenario_rules,
    scenario_summary,
    SCENARIO_RULES,
    scale_capex_items,
)
from app.project_factories import create_default_solar_project, create_default_wind_project
from app.ui_runner import run_demo_project


class TestGetScenarioRules:
    def test_base_rules(self):
        rules = get_scenario_rules("base")
        assert rules["p50_multiplier"] == 1.0
        assert rules["capex_multiplier"] == 1.0
        assert rules["tariff_multiplier"] == 1.0

    def test_downside_rules(self):
        rules = get_scenario_rules("downside")
        assert rules["p50_multiplier"] == 0.90
        assert rules["capex_multiplier"] == 1.05
        assert rules["tariff_multiplier"] == 0.95

    def test_upside_rules(self):
        rules = get_scenario_rules("upside")
        assert rules["p50_multiplier"] == 1.05
        assert rules["capex_multiplier"] == 0.97
        assert rules["tariff_multiplier"] == 1.03

    def test_unknown_scenario_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            get_scenario_rules("invalid")


class TestScenarioSummary:
    def test_base_summary_no_changes(self):
        rows = scenario_summary("base")
        assert len(rows) == 1
        assert rows[0]["change"] == "0%"

    def test_downside_includes_p50_capex_tariff_rows(self):
        rows = scenario_summary("downside")
        assumptions = [r["assumption"] for r in rows]
        assert "P50 Hours" in assumptions
        assert "Total CapEx" in assumptions
        assert "PPA Tariff" in assumptions

    def test_downside_changes_are_negative(self):
        """P50 and tariff decrease; capex increases in downside."""
        rows = scenario_summary("downside")
        found = {r["assumption"]: r["change"] for r in rows}
        assert found["P50 Hours"].startswith("-"), f"P50 should decrease: {found["P50 Hours"]}"
        assert found["PPA Tariff"].startswith("-"), f"Tariff should decrease: {found["PPA Tariff"]}"
        assert found["Total CapEx"].startswith("+"), f"CapEx should increase: {found["Total CapEx"]}"

    def test_upside_changes_are_positive(self):
        """P50 and tariff increase; capex decreases in upside."""
        rows = scenario_summary("upside")
        found = {r["assumption"]: r["change"] for r in rows}
        assert found["P50 Hours"].startswith("+"), f"P50 should increase: {found["P50 Hours"]}"
        assert found["PPA Tariff"].startswith("+"), f"Tariff should increase: {found["PPA Tariff"]}"
        assert found["Total CapEx"].startswith("-"), f"CapEx should decrease: {found["Total CapEx"]}"


class TestApplyScenario:
    def test_base_scenario_no_change(self):
        solar = create_default_solar_project()
        result = apply_scenario(solar, "base")
        assert result.technical.operating_hours_p50 == solar.technical.operating_hours_p50
        assert result.revenue.ppa_base_tariff == solar.revenue.ppa_base_tariff

    def test_downside_reduces_p50(self):
        solar = create_default_solar_project()
        result = apply_scenario(solar, "downside")
        assert result.technical.operating_hours_p50 < solar.technical.operating_hours_p50

    def test_downside_increases_capex(self):
        solar = create_default_solar_project()
        original = solar.capex.total_capex
        result = apply_scenario(solar, "downside")
        assert result.capex.total_capex > original

    def test_upside_decreases_capex(self):
        solar = create_default_solar_project()
        original = solar.capex.total_capex
        result = apply_scenario(solar, "upside")
        assert result.capex.total_capex < original

    def test_downside_reduces_tariff(self):
        solar = create_default_solar_project()
        result = apply_scenario(solar, "downside")
        assert result.revenue.ppa_base_tariff < solar.revenue.ppa_base_tariff

    def test_upside_increases_tariff(self):
        solar = create_default_solar_project()
        result = apply_scenario(solar, "upside")
        assert result.revenue.ppa_base_tariff > solar.revenue.ppa_base_tariff

    def test_case_insensitive_scenario_names(self):
        solar = create_default_solar_project()
        r1 = apply_scenario(solar, "DOWNSIDE")
        r2 = apply_scenario(solar, "downside")
        assert r1.technical.operating_hours_p50 == r2.technical.operating_hours_p50

    def test_unknown_scenario_raises_valueerror(self):
        solar = create_default_solar_project()
        with pytest.raises(ValueError, match="Unknown scenario"):
            apply_scenario(solar, "extreme")

    def test_returns_new_instance_not_mutated_original(self):
        solar = create_default_solar_project()
        result = apply_scenario(solar, "downside")
        assert result is not solar
        assert solar.technical.operating_hours_p50 == create_default_solar_project().technical.operating_hours_p50

    def test_wind_project_scenario(self):
        wind = create_default_wind_project()
        result = apply_scenario(wind, "upside")
        assert result.technical.operating_hours_p50 > wind.technical.operating_hours_p50
        assert result.revenue.ppa_base_tariff > wind.revenue.ppa_base_tariff


class TestScenarioIntegration:
    def test_downside_changes_solar_model_result(self):
        """Downside scenario must change model result."""
        base = run_demo_project("Solar")
        assert base.result is not None
        solar = create_default_solar_project()
        downside_solar = apply_scenario(solar, "downside")
        mod = run_demo_project("Solar", project_inputs_override=downside_solar)
        assert mod.result is not None
        # At least one metric should differ (tariff/generation down)
        assert base.result.project_irr != mod.result.project_irr or                base.result.equity_irr != mod.result.equity_irr

    def test_upside_changes_wind_model_result(self):
        """Upside scenario must change model result."""
        base = run_demo_project("Wind")
        assert base.result is not None
        wind = create_default_wind_project()
        upside_wind = apply_scenario(wind, "upside")
        mod = run_demo_project("Wind", project_inputs_override=upside_wind)
        assert mod.result is not None
        # At least one metric should differ (tariff/generation up)
        assert base.result.project_irr != mod.result.project_irr or                base.result.equity_irr != mod.result.equity_irr
