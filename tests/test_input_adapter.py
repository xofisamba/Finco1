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


class TestFrozenScheduleCompatibility:
    """Tests for the frozen debt schedule compatibility rule in _resolve_user_inputs.

    Rule: if the user-supplied total_capex_keur differs from the factory
    base_capex by >= 0.01 kEUR (strict <), the frozen Excel senior debt
    schedule flag and all calibrated debt values must be zeroed out.
    If the diff is < 0.01 kEUR the frozen schedule is preserved unchanged.
    """

    # ------------------------------------------------------------------
    # A1: Exact unchanged Oborovo CAPEX → frozen preserved, calibrated
    #     debt field values are intact.
    # ------------------------------------------------------------------
    def test_oborovo_exact_capex_preserves_frozen_schedule(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _resolve_user_inputs

        obo = create_default_oborovo()
        base_capex = obo.capex.total_capex  # 57973.05265737862

        result = _resolve_user_inputs(
            project_type="Solar",
            total_capex_keur=base_capex,
            base_inputs=obo,
        )

        assert result.financing.use_frozen_excel_senior_debt_schedule is True
        assert abs(result.financing.fixed_debt_keur - 42852.26672602787) < 0.01
        assert abs(result.financing.shl_amount_keur - 13547.2) < 0.01
        assert abs(result.financing.shl_idc_keur - 1169.0) < 0.01

    # ------------------------------------------------------------------
    # A2: Significantly different CAPEX → frozen disabled, calibrated
    #     debt fields zeroed; gearing and DSCR are preserved.
    # ------------------------------------------------------------------
    def test_oborovo_different_capex_disables_frozen_schedule(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _resolve_user_inputs

        obo = create_default_oborovo()

        result = _resolve_user_inputs(
            project_type="Solar",
            total_capex_keur=40000.0,
            base_inputs=obo,
        )

        assert result.financing.use_frozen_excel_senior_debt_schedule is False
        assert result.financing.fixed_debt_keur == 0.0
        assert result.financing.shl_amount_keur == 0.0
        assert result.financing.shl_idc_keur == 0.0
        # Gearing and DSCR must be preserved from the factory
        assert abs(result.financing.gearing_ratio - obo.financing.gearing_ratio) < 1e-9
        assert abs(result.financing.target_dscr - obo.financing.target_dscr) < 1e-9

    # ------------------------------------------------------------------
    # A3: CAPEX within tolerance (diff = 0.005 kEUR < 0.01) → preserved.
    # ------------------------------------------------------------------
    def test_oborovo_capex_within_tolerance_preserves_frozen(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _resolve_user_inputs

        obo = create_default_oborovo()
        within_tolerance = obo.capex.total_capex + 0.005

        result = _resolve_user_inputs(
            project_type="Solar",
            total_capex_keur=within_tolerance,
            base_inputs=obo,
        )

        assert result.financing.use_frozen_excel_senior_debt_schedule is True

    # ------------------------------------------------------------------
    # A4: Boundary — diff exactly 0.01 kEUR → strict < means DISABLED.
    # ------------------------------------------------------------------
    def test_oborovo_capex_at_boundary_disables_frozen(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _resolve_user_inputs

        obo = create_default_oborovo()
        at_boundary = obo.capex.total_capex + 0.01

        result = _resolve_user_inputs(
            project_type="Solar",
            total_capex_keur=at_boundary,
            base_inputs=obo,
        )

        assert result.financing.use_frozen_excel_senior_debt_schedule is False
        assert result.financing.fixed_debt_keur == 0.0

    # ------------------------------------------------------------------
    # A5: Generic Solar / Wind with a capex override — these factories
    #     do NOT set use_frozen_excel_senior_debt_schedule=True, so the
    #     flag must remain False regardless (no invented values).
    # ------------------------------------------------------------------
    def test_generic_solar_capex_override_does_not_invent_frozen(self):
        from app.project_factories import create_default_solar_project
        from app.input_adapter import _resolve_user_inputs

        solar = create_default_solar_project()
        assert solar.financing.use_frozen_excel_senior_debt_schedule is False

        result = _resolve_user_inputs(
            project_type="Solar",
            total_capex_keur=solar.capex.total_capex + 5000.0,
            base_inputs=solar,
        )

        assert result.financing.use_frozen_excel_senior_debt_schedule is False
        assert not result.financing.fixed_debt_keur  # None or 0.0 — no invented calibrated value

    # ------------------------------------------------------------------
    # A6: TUHO unchanged CAPEX → financing mode (frozen=True) preserved.
    # ------------------------------------------------------------------
    def test_tuho_exact_capex_preserves_frozen_schedule(self):
        from app.project_factories import create_default_tuho_wind1
        from app.input_adapter import _resolve_user_inputs

        tuho = create_default_tuho_wind1()
        assert tuho.financing.use_frozen_excel_senior_debt_schedule is True
        base_capex = tuho.capex.total_capex

        result = _resolve_user_inputs(
            project_type="Wind",
            total_capex_keur=base_capex,
            base_inputs=tuho,
        )

        assert result.financing.use_frozen_excel_senior_debt_schedule is True
