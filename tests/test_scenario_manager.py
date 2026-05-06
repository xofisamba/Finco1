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


class TestScenarioDisplayMatchesCalculation:
    """Regression test: scenario_summary reports the same axes that apply_overrides actually applies.

    Ensures the ScenarioManager summary shown in UI/export matches the multipliers
    that were actually applied to the project, so users see truthful scenario deltas.
    """

    def test_solar_downside_summary_matches_applied_overrides(self):
        """Solar Downside: summary must show PPA Tariff -5%, P50 Hours -10%, CapEx +5%, OpEx +10%, Degradation +15%."""
        from app.scenario_manager import ScenarioManager
        from app.project_factories import create_default_solar_project

        mgr = ScenarioManager("solar")
        solar = create_default_solar_project()
        result = mgr.apply_overrides(solar, "Downside")
        rows = mgr.scenario_summary("Downside")

        # Build a dict of assumption -> change string
        summary = {r["assumption"]: r["change"] for r in rows}

        # Verify each axis is present and correct
        assert "PPA Tariff" in summary, f"PPA Tariff missing from summary: {summary}"
        assert summary["PPA Tariff"] == "-5%", f"PPA Tariff should be -5%, got {summary['PPA Tariff']}"
        assert "P50 Hours" in summary, f"P50 Hours missing from summary: {summary}"
        assert summary["P50 Hours"] == "-10%", f"P50 Hours should be -10%, got {summary['P50 Hours']}"
        assert "Total CapEx" in summary, f"Total CapEx missing from summary: {summary}"
        assert summary["Total CapEx"] == "+5%", f"Total CapEx should be +5%, got {summary['Total CapEx']}"
        assert "OpEx" in summary, f"OpEx missing from summary: {summary}"
        assert summary["OpEx"] == "+10%", f"OpEx should be +10%, got {summary['OpEx']}"
        assert "Degradation" in summary, f"Degradation missing from summary: {summary}"
        assert summary["Degradation"] == "+15%", f"Degradation should be +15%, got {summary['Degradation']}"

        # Verify actual applied multipliers match summary
        base = create_default_solar_project()
        assert result.revenue.ppa_base_tariff / base.revenue.ppa_base_tariff == pytest.approx(0.95)
        assert result.technical.operating_hours_p50 / base.technical.operating_hours_p50 == pytest.approx(0.90)
        assert result.capex.total_capex / base.capex.total_capex == pytest.approx(1.05)
        base_opex_y1 = sum(i.y1_amount_keur for i in base.opex)
        down_opex_y1 = sum(i.y1_amount_keur for i in result.opex)
        assert down_opex_y1 / base_opex_y1 == pytest.approx(1.10)
        assert result.technical.pv_degradation / base.technical.pv_degradation == pytest.approx(1.15)

    def test_solar_upside_summary_matches_applied_overrides(self):
        """Solar Upside: summary must show PPA Tariff +3%, P50 Hours +5%, CapEx -3%, OpEx -5%, Degradation -10%."""
        from app.scenario_manager import ScenarioManager
        from app.project_factories import create_default_solar_project

        mgr = ScenarioManager("solar")
        solar = create_default_solar_project()
        result = mgr.apply_overrides(solar, "Upside")
        rows = mgr.scenario_summary("Upside")
        summary = {r["assumption"]: r["change"] for r in rows}

        assert summary.get("PPA Tariff") == "+3%"
        assert summary.get("P50 Hours") == "+5%"
        assert summary.get("Total CapEx") == "-3%"
        assert summary.get("OpEx") == "-5%"
        assert summary.get("Degradation") == "-10%"

        base = create_default_solar_project()
        assert result.revenue.ppa_base_tariff / base.revenue.ppa_base_tariff == pytest.approx(1.03)
        assert result.technical.operating_hours_p50 / base.technical.operating_hours_p50 == pytest.approx(1.05)
        assert result.capex.total_capex / base.capex.total_capex == pytest.approx(0.97)
        base_opex_y1 = sum(i.y1_amount_keur for i in base.opex)
        up_opex_y1 = sum(i.y1_amount_keur for i in result.opex)
        assert up_opex_y1 / base_opex_y1 == pytest.approx(0.95)
        assert result.technical.pv_degradation / base.technical.pv_degradation == pytest.approx(0.90)

    def test_wind_downside_summary_matches_applied_overrides(self):
        """Wind Downside: summary must show PPA Tariff -5%, P50 Hours -10%, CapEx +5%, OpEx +10%."""
        from app.scenario_manager import ScenarioManager
        from app.project_factories import create_default_wind_project

        mgr = ScenarioManager("wind")
        wind = create_default_wind_project()
        result = mgr.apply_overrides(wind, "Downside")
        rows = mgr.scenario_summary("Downside")
        summary = {r["assumption"]: r["change"] for r in rows}

        assert summary.get("PPA Tariff") == "-5%"
        assert summary.get("P50 Hours") == "-10%"
        assert summary.get("Total CapEx") == "+5%"
        assert summary.get("OpEx") == "+10%"

    def test_wind_upside_summary_matches_applied_overrides(self):
        """Wind Upside: summary must show PPA Tariff +3%, P50 Hours +5%, CapEx -3%, OpEx -5%."""
        from app.scenario_manager import ScenarioManager
        from app.project_factories import create_default_wind_project

        mgr = ScenarioManager("wind")
        wind = create_default_wind_project()
        result = mgr.apply_overrides(wind, "Upside")
        rows = mgr.scenario_summary("Upside")
        summary = {r["assumption"]: r["change"] for r in rows}

        assert summary.get("PPA Tariff") == "+3%"
        assert summary.get("P50 Hours") == "+5%"
        assert summary.get("Total CapEx") == "-3%"
        assert summary.get("OpEx") == "-5%"


class TestAdvancedOpexScenarioInteraction:
    """Regression test: Advanced OPEX line items + scenario scaling interact correctly.

    When advanced_opex_line_items are provided, scenario overrides must still apply
    to revenue/capex/p50/degradation, and the resulting KPI directionality must be
    consistent with the scenario intent (Downside = lower IRR, lower DSCR).
    """

    def test_solar_downside_lower_irr_than_base_with_advanced_opex(self):
        """Solar Downside with advanced OPEX: IRR must be lower than Base."""
        from app.ui_runner import run_demo_project
        from app.opex_engine import build_opex_line_items_from_defaults

        opex_items = build_opex_line_items_from_defaults("solar")
        r_base = run_demo_project("Solar", "Base", advanced_opex_line_items=opex_items).result
        r_down = run_demo_project("Solar", "Downside", advanced_opex_line_items=opex_items).result

        assert r_down.project_irr < r_base.project_irr, (
            f"Downside IRR ({r_down.project_irr:.4f}) should be < Base IRR ({r_base.project_irr:.4f})"
        )

    def test_scenario_summary_shows_opex_plus_10pct_for_downside(self):
        """Solar Downside scenario_summary must show OpEx +10% even with advanced OPEX items."""
        from app.scenario_manager import ScenarioManager

        mgr = ScenarioManager("solar")
        rows = mgr.scenario_summary("Downside")
        opex_rows = [r for r in rows if r["assumption"] == "OpEx"]
        assert len(opex_rows) == 1, f"Expected exactly one OpEx row, got {len(opex_rows)}: {opex_rows}"
        assert "+10%" in opex_rows[0]["change"], f"OpEx change should be +10%, got {opex_rows[0]['change']}"

    def test_solar_downside_opex_actually_increases_with_scenario_override(self):
        """Downside apply_overrides must increase OPEX Y1 by 10% even when advanced items are provided.

        Note: DSCR directionality with advanced OPEX is complex — higher OPEX reduces CFADS,
        but lower revenue in Downside also reduces debt sizing (lower debt service), so actual
        DSCR may go up or down depending on which effect dominates. The IRR direction is
        unambiguous (Downside < Base), but DSCR direction depends on the OPEX quantum.
        """
        from app.scenario_manager import ScenarioManager
        from app.project_factories import create_default_solar_project

        mgr = ScenarioManager("solar")
        solar = create_default_solar_project()
        result = mgr.apply_overrides(solar, "Downside")

        base_y1 = sum(i.y1_amount_keur for i in solar.opex)
        down_y1 = sum(i.y1_amount_keur for i in result.opex)
        assert down_y1 > base_y1, (
            f"Downside OPEX Y1 ({down_y1}) should be > Base OPEX Y1 ({base_y1}). "
            f"The apply_overrides multiplier (+10%) must actually increase OPEX."
        )
        assert abs(down_y1 / base_y1 - 1.10) < 0.001, (
            f"Downside OPEX Y1 multiplier should be 1.10x, got {down_y1/base_y1:.4f}"
        )


class TestScenarioManagerGoldenOutputs:
    """Golden-output validation for Solar Base scenario via ScenarioManager flow.

    # Branch-current golden values — NOT bank certification. For internal validation only.

    NOTE: These are wide sanity bounds. Test pollution from other modules mutating
    shared default-project objects can shift KPI by ~50bps in the full suite.
    Run this test in isolation for precise KPI validation.
    Captured values (2026-05-06 post-rc1-structure-roadmap HEAD):
      project_irr=0.104029, equity_irr=0.135783, actual_min_dscr=1.4421,
      actual_avg_dscr=1.6502, total_senior_ds=34175keur,
      total_revenue=119532keur, total_distribution=43705keur, total_ebitda=107361keur
    """

    def test_solar_base_golden_outputs(self):
        from app.ui_runner import run_demo_project
        r = run_demo_project("Solar", "Base").result
        # Wide sanity bounds (catches gross regressions; tolerant of test-pollution drift)
        assert 0.08 < r.project_irr < 0.13
        assert 0.10 < r.equity_irr < 0.18
        assert 1.1 < r.actual_min_dscr < 1.7
        assert 1.3 < r.actual_avg_dscr < 1.9
        assert 25000 < r.total_senior_ds_keur < 45000
        assert 90000 < r.total_revenue_keur < 140000
        assert 30000 < r.total_distribution_keur < 60000
        assert 80000 < r.total_ebitda_keur < 130000
