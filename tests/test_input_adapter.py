"""Tests for input_adapter.py."""
import pytest

from app.input_schema import ProjectInputsSchema
from app.input_adapter import build_projectinputs


class TestInputAdapter:
    def test_adapter_builds_without_error(self):
        schema = ProjectInputsSchema(project_type="Solar", scenario="Base")
        proj = build_projectinputs(schema)
        assert proj is not None

    def test_custom_capacity_set(self):
        schema = ProjectInputsSchema(project_type="Solar", capacity_mw=100)
        proj = build_projectinputs(schema)
        assert proj.technical.capacity_mw == 100.0

    def test_wind_capacity_set(self):
        schema = ProjectInputsSchema(project_type="Wind", capacity_mw=80)
        proj = build_projectinputs(schema)
        assert proj.technical.capacity_mw == 80.0

    def test_custom_tariff_set(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            revenue={"tariff_eur_mwh": 80.0},
        )
        proj = build_projectinputs(schema)
        assert proj.revenue.ppa_base_tariff == 80.0

    def test_custom_p50_hours(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            revenue={"p50_hours": 1400},
        )
        proj = build_projectinputs(schema)
        assert proj.technical.operating_hours_p50 == 1400.0

    def test_custom_degradation_converts_to_fraction(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            revenue={"degradation_pct": 0.5},  # 0.5%
        )
        proj = build_projectinputs(schema)
        assert proj.technical.pv_degradation == 0.005  # domain uses fraction

    def test_opex_y1_scaling(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            opex={"opex_y1_keur": 1000},
        )
        proj = build_projectinputs(schema)
        # All items scaled proportionally from base total (380 kEUR)
        total = sum(item.y1_amount_keur for item in proj.opex)
        assert abs(total - 1000.0) < 0.01

    def test_opex_inflation_set(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            opex={"inflation_pct": 3.0},
        )
        proj = build_projectinputs(schema)
        # All items should have 0.03 inflation
        for item in proj.opex:
            assert item.annual_inflation == 0.03

    def test_debt_gearing_converts_to_fraction(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            debt={"gearing_pct": 75},
        )
        proj = build_projectinputs(schema)
        assert proj.financing.gearing_ratio == 0.75

    def test_debt_interest_rate_converts(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            debt={"interest_rate_pct": 6.0},
        )
        proj = build_projectinputs(schema)
        # base_rate=0.03, all_in=0.06 -> margin_bps=300
        assert proj.financing.margin_bps == 300

    def test_debt_tenor_set(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            debt={"tenor_years": 12},
        )
        proj = build_projectinputs(schema)
        assert proj.financing.senior_tenor_years == 12

    def test_debt_target_dscr_set(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            debt={"target_dscr": 1.5},
        )
        proj = build_projectinputs(schema)
        assert proj.financing.target_dscr == 1.5

    def test_wind_defaults_preserved(self):
        """Ensure Wind factory defaults are not corrupted."""
        from app.project_factories import create_default_wind_project
        wind_defaults = create_default_wind_project()
        schema = ProjectInputsSchema(project_type="Wind", capacity_mw=60)
        proj = build_projectinputs(schema)
        # Only capacity changed; revenue tariff should be Wind default
        assert proj.revenue.ppa_base_tariff == wind_defaults.revenue.ppa_base_tariff

    def test_unspecified_fields_use_factory_defaults(self):
        """Fields not in schema should remain at factory defaults."""
        from app.project_factories import create_default_solar_project
        defaults = create_default_solar_project()
        schema = ProjectInputsSchema(project_type="Solar")
        proj = build_projectinputs(schema)
        assert proj.technical.capacity_mw == defaults.technical.capacity_mw
        assert proj.revenue.ppa_base_tariff == defaults.revenue.ppa_base_tariff
        assert proj.financing.target_dscr == defaults.financing.target_dscr

    def test_full_custom_schema_runs_through_ui_runner(self):
        """End-to-end: schema -> adapter -> run_demo_project."""
        from app.ui_runner import run_demo_project
        schema = ProjectInputsSchema(
            project_type="Solar",
            capacity_mw=75,
            scenario="Base",
            revenue={"tariff_eur_mwh": 70.0, "p50_hours": 1400},
            capex={"total_capex_keur": 50000},
            opex={"opex_y1_keur": 500, "inflation_pct": 2.5},
            debt={"gearing_pct": 70, "interest_rate_pct": 5.5,
                  "tenor_years": 15, "target_dscr": 1.3},
        )
        proj = build_projectinputs(schema)
        demo = run_demo_project("Solar", "Base",
                                project_inputs_override=proj)
        assert demo.result is not None
        assert demo.result.project_irr is not None


class TestCustomInputDirectionality:
    """Smoke tests proving custom inputs actually affect financial outputs.

    These are API-level integration tests. They run the full waterfall via
    run_project() and verify that directional changes in inputs produce the
    expected directional change in KPIs.
    """

    def test_higher_tariff_increases_revenue(self):
        """API: higher tariff -> higher total revenue."""
        from app.api.project_runner import run_project
        from app.input_schema import ProjectInputsSchema
        from app.input_adapter import build_projectinputs
        import json

        r_base = run_project('Solar', 'Base')
        base_rev = r_base['kpis']['total_revenue_keur']

        with open('examples/custom_solar.json') as f:
            custom = json.load(f)
        custom['revenue']['tariff_eur_mwh'] = 150  # Very high tariff
        schema = ProjectInputsSchema(**custom)
        proj = build_projectinputs(schema)
        r_high = run_project('Solar', 'Base', project_inputs_override=proj)
        high_rev = r_high['kpis']['total_revenue_keur']

        delta = high_rev - base_rev
        assert delta > 10_000, (
            f"Tariff increase should add >10,000 kEUR revenue, got {delta:,.0f}"
        )
        print(f"TARIFF: +{delta:,.0f} kEUR revenue for higher tariff OK")

    def test_higher_capex_reduces_irr(self):
        """API: higher CAPEX -> lower project IRR."""
        from app.api.project_runner import run_project
        from app.input_schema import ProjectInputsSchema
        from app.input_adapter import build_projectinputs
        import json

        r_base = run_project('Solar', 'Base')
        base_irr = r_base['kpis']['project_irr']

        with open('examples/custom_solar.json') as f:
            custom = json.load(f)
        custom['capex']['total_capex_keur'] = 80_000  # Much higher CAPEX
        schema = ProjectInputsSchema(**custom)
        proj = build_projectinputs(schema)
        r_high = run_project('Solar', 'Base', project_inputs_override=proj)
        high_irr = r_high['kpis']['project_irr']

        assert high_irr < base_irr, (
            f"Higher CAPEX should reduce IRR: {high_irr:.4f} vs {base_irr:.4f}"
        )
        print(f"CAPEX: IRR {base_irr:.4f} -> {high_irr:.4f} with higher CAPEX OK")

    def test_higher_opex_reduces_ebitda(self):
        """API: higher OPEX -> lower EBITDA."""
        from app.api.project_runner import run_project
        from app.input_schema import ProjectInputsSchema
        from app.input_adapter import build_projectinputs
        import json

        r_base = run_project('Solar', 'Base')
        base_ebitda = r_base['kpis']['total_ebitda_keur']

        with open('examples/custom_solar.json') as f:
            custom = json.load(f)
        custom['opex']['opex_y1_keur'] = 5000  # Much higher OPEX
        schema = ProjectInputsSchema(**custom)
        proj = build_projectinputs(schema)
        r_high = run_project('Solar', 'Base', project_inputs_override=proj)
        high_ebitda = r_high['kpis']['total_ebitda_keur']

        assert high_ebitda < base_ebitda, (
            f"Higher OPEX should reduce EBITDA: {high_ebitda:,.0f} vs {base_ebitda:,.0f}"
        )
        print(f"OPEX: EBITDA {base_ebitda:,.0f} -> {high_ebitda:,.0f} with higher OPEX OK")

    def test_lower_degradation_increases_revenue(self):
        """API: lower degradation -> higher long-term revenue."""
        from app.api.project_runner import run_project
        from app.input_schema import ProjectInputsSchema
        from app.input_adapter import build_projectinputs
        import json

        with open('examples/custom_solar.json') as f:
            custom = json.load(f)

        # Very high degradation
        custom['revenue']['degradation_pct'] = 1.0
        schema = ProjectInputsSchema(**custom)
        proj = build_projectinputs(schema)
        r_high_deg = run_project('Solar', 'Base', project_inputs_override=proj)
        high_deg_rev = r_high_deg['kpis']['total_revenue_keur']

        # Very low degradation
        custom['revenue']['degradation_pct'] = 0.1
        schema2 = ProjectInputsSchema(**custom)
        proj2 = build_projectinputs(schema2)
        r_low_deg = run_project('Solar', 'Base', project_inputs_override=proj2)
        low_deg_rev = r_low_deg['kpis']['total_revenue_keur']

        assert low_deg_rev > high_deg_rev, (
            f"Lower degradation should increase revenue: "
            f"{low_deg_rev:,.0f} vs {high_deg_rev:,.0f}"
        )
        print(f"DEGRADATION: revenue {high_deg_rev:,.0f} (1%) -> {low_deg_rev:,.0f} (0.1%) OK")
