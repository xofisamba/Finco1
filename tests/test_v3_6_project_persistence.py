"""V3-6: Full-fidelity ProjectInputs serialization round-trip tests.

Tests that project_inputs_to_dict / project_inputs_from_dict preserve every
field of every nested dataclass without loss. No financial calculations are
verified here — only structural identity (restored == original).
"""
import json
import pytest
from dataclasses import replace
from datetime import date

from finco_core.inputs import (
    project_inputs_to_dict,
    project_inputs_from_dict,
    ProjectInputs,
    ProjectInfo,
    TechnicalParams,
    CapexItem,
    CapexStructure,
    OpexItem,
    RevenueParams,
    RevenueAdjustmentSchedule,
    FinancingParams,
    TaxParams,
    BessParams,
    PeriodFrequency,
    AssetClass,
    DebtSizingMode,
    SeniorDebtInterestConfig,
    SeniorSculptingConfig,
    SeniorRateSchedule,
    SeniorHedgeConfig,
    SeniorRateMode,
    SeniorDayCountConvention,
    SeniorSculptingMode,
    SeniorFinalRepaymentPolicy,
    SeniorPrincipalCapPolicy,
    SeniorReserveTreatment,
)
from finco_core.tax.construction_pl import ConstructionPLStatement
from app.project_factories import create_default_solar_project, create_default_wind_project


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def solar_project():
    return create_default_solar_project()


@pytest.fixture
def wind_project():
    return create_default_wind_project()


# ── Basic round-trip tests ─────────────────────────────────────────────────────

class TestProjectInputsRoundTrip:

    def test_solar_round_trip_exact_equality(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored == solar_project

    def test_wind_round_trip_exact_equality(self, wind_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(wind_project))
        assert restored == wind_project

    def test_round_trip_returns_project_inputs_instance(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert isinstance(restored, ProjectInputs)

    def test_dict_is_json_serializable(self, solar_project):
        d = project_inputs_to_dict(solar_project)
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
        assert len(json_str) > 100

    def test_json_dumps_loads_round_trip(self, solar_project):
        d = project_inputs_to_dict(solar_project)
        restored = project_inputs_from_dict(json.loads(json.dumps(d)))
        assert restored == solar_project

    def test_schema_version_present(self, solar_project):
        d = project_inputs_to_dict(solar_project)
        assert "_schema_version" in d
        assert d["_schema_version"] == "v3-6"


# ── Sub-struct round-trip tests ────────────────────────────────────────────────

class TestProjectInfoRoundTrip:

    def test_dates_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.info.financial_close == solar_project.info.financial_close
        assert restored.info.cod_date == solar_project.info.cod_date
        assert isinstance(restored.info.financial_close, date)

    def test_period_frequency_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.info.period_frequency == solar_project.info.period_frequency
        assert isinstance(restored.info.period_frequency, PeriodFrequency)

    def test_feature_flags_preserved(self, solar_project):
        proj = replace(solar_project, info=replace(solar_project.info,
            use_shl_canonical_engine=True,
            use_senior_debt_sizing_engine=True,
        ))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.info.use_shl_canonical_engine is True
        assert restored.info.use_senior_debt_sizing_engine is True


class TestTechnicalParamsRoundTrip:

    def test_bess_none_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.technical.bess is None

    def test_bess_params_round_trip(self, solar_project):
        bess = BessParams(
            power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
            round_trip_efficiency=0.90, availability=0.97,
            annual_degradation=0.015, arbitrage_spread_eur_mwh=35.0,
            ancillary_revenue_eur_mw_year=22000.0,
            capacity_revenue_eur_mw_year=1000.0, augmentation_capex_keur=500.0,
        )
        proj = replace(solar_project, technical=replace(solar_project.technical,
            bess_enabled=True, bess=bess))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.technical.bess == bess
        assert restored.technical.bess_enabled is True

    def test_yield_scenario_string_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.technical.yield_scenario == solar_project.technical.yield_scenario


class TestCapexRoundTrip:

    def test_all_capex_item_fields_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        cap_orig = solar_project.capex
        cap_rest = restored.capex
        assert cap_orig == cap_rest

    def test_spending_profile_tuple_preserved(self, solar_project):
        item = replace(solar_project.capex.epc_contract,
                       spending_profile=(0.4, 0.4, 0.2))
        proj = replace(solar_project, capex=replace(solar_project.capex, epc_contract=item))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.capex.epc_contract.spending_profile == (0.4, 0.4, 0.2)

    def test_asset_class_enum_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.capex.epc_contract.asset_class == solar_project.capex.epc_contract.asset_class
        assert isinstance(restored.capex.epc_contract.asset_class, AssetClass)

    def test_useful_life_override_none_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.capex.epc_contract.useful_life_override == solar_project.capex.epc_contract.useful_life_override

    def test_useful_life_override_int_preserved(self, solar_project):
        item = replace(solar_project.capex.epc_contract, useful_life_override=20)
        proj = replace(solar_project, capex=replace(solar_project.capex, epc_contract=item))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.capex.epc_contract.useful_life_override == 20

    def test_financial_capex_floats_preserved(self, solar_project):
        proj = replace(solar_project, capex=replace(solar_project.capex,
            idc_keur=1234.5, bank_fees_keur=56.7, commitment_fees_keur=89.0))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.capex.idc_keur == pytest.approx(1234.5)
        assert restored.capex.bank_fees_keur == pytest.approx(56.7)


class TestOpexRoundTrip:

    def test_opex_tuple_length_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert len(restored.opex) == len(solar_project.opex)

    def test_opex_tuple_type_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert isinstance(restored.opex, tuple)

    def test_opex_step_changes_preserved(self, solar_project):
        item = OpexItem(name="StepItem", y1_amount_keur=100.0,
                        step_changes=((5, 90.0), (10, 80.0)))
        proj = replace(solar_project, opex=solar_project.opex + (item,))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        last = restored.opex[-1]
        assert last.step_changes == ((5, 90.0), (10, 80.0))

    def test_opex_step_changes_types_are_tuples(self, solar_project):
        item = OpexItem(name="StepItem2", y1_amount_keur=50.0,
                        step_changes=((3, 45.0),))
        proj = replace(solar_project, opex=(item,))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert isinstance(restored.opex[0].step_changes, tuple)
        assert isinstance(restored.opex[0].step_changes[0], tuple)


class TestRevenueRoundTrip:

    def test_market_prices_curve_tuple_preserved(self, solar_project):
        proj = replace(solar_project, revenue=replace(solar_project.revenue,
            market_prices_curve=(45.0, 47.0, 50.0, 52.0)))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.revenue.market_prices_curve == (45.0, 47.0, 50.0, 52.0)
        assert isinstance(restored.revenue.market_prices_curve, tuple)

    def test_revenue_adjustment_schedule_preserved(self, solar_project):
        sched = RevenueAdjustmentSchedule(
            constant_value=2.5,
            annual_values=(1.0, 2.0, 3.0),
            semiannual_values=(0.5, 1.0, 1.5, 2.0),
        )
        proj = replace(solar_project, revenue=replace(solar_project.revenue,
            balancing_cost_schedule=sched))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.revenue.balancing_cost_schedule == sched

    def test_revenue_adjustment_none_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.revenue.balancing_cost_schedule == solar_project.revenue.balancing_cost_schedule


class TestFinancingRoundTrip:

    def test_debt_sizing_mode_none_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.financing.debt_sizing_mode is None

    def test_debt_sizing_mode_enum_preserved(self, solar_project):
        proj = replace(solar_project, financing=replace(solar_project.financing,
            debt_sizing_mode=DebtSizingMode.FROZEN_EXCEL_SCHEDULE))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.financing.debt_sizing_mode == DebtSizingMode.FROZEN_EXCEL_SCHEDULE
        assert isinstance(restored.financing.debt_sizing_mode, DebtSizingMode)

    def test_shl_fcf_schedule_tuple_preserved(self, solar_project):
        proj = replace(solar_project, financing=replace(solar_project.financing,
            shl_fcf_waterfall_cash_schedule_keur=(500.0, 600.0, 700.0)))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.financing.shl_fcf_waterfall_cash_schedule_keur == (500.0, 600.0, 700.0)
        assert isinstance(restored.financing.shl_fcf_waterfall_cash_schedule_keur, tuple)

    def test_senior_interest_config_defaults_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        orig = solar_project.financing.senior_debt_interest_config
        rest = restored.financing.senior_debt_interest_config
        assert rest == orig
        assert isinstance(rest, SeniorDebtInterestConfig)

    def test_senior_interest_config_enabled_preserved(self, solar_project):
        config = SeniorDebtInterestConfig(
            enabled=True,
            rate_schedule=SeniorRateSchedule(
                mode=SeniorRateMode.FIXED_PLUS_MARGIN,
                flat_all_in_rate=0.055,
                fixed_base_rate=0.03,
                margin_rate=0.025,
            ),
            day_count=SeniorDayCountConvention.ACT_365,
            explicit_period_fractions=(0.5, 0.5, 0.5),
        )
        proj = replace(solar_project, financing=replace(solar_project.financing,
            senior_debt_interest_config=config))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.financing.senior_debt_interest_config == config

    def test_senior_interest_config_hedge_preserved(self, solar_project):
        hedge = SeniorHedgeConfig(hedge_pct=0.7, fixed_base_rate=0.03,
                                  floating_base_rate_curve=(0.025, 0.03, 0.035),
                                  floating_curve_buffer_pct=0.001)
        rate_sched = SeniorRateSchedule(mode=SeniorRateMode.HEDGE_BLEND,
                                        hedge=hedge, margin_rate=0.02)
        config = SeniorDebtInterestConfig(enabled=True, rate_schedule=rate_sched)
        proj = replace(solar_project, financing=replace(solar_project.financing,
            senior_debt_interest_config=config))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        rest_hedge = restored.financing.senior_debt_interest_config.rate_schedule.hedge
        assert rest_hedge == hedge
        assert rest_hedge.floating_base_rate_curve == (0.025, 0.03, 0.035)

    def test_senior_sculpting_config_preserved(self, solar_project):
        config = SeniorSculptingConfig(
            enabled=True,
            mode=SeniorSculptingMode.EXPLICIT_DEBT_SERVICE_SCHEDULE,
            explicit_debt_service_schedule=(1000.0, 1100.0, 1200.0),
            final_repayment_policy=SeniorFinalRepaymentPolicy.CAP_AT_EXPLICIT_SCHEDULE,
            principal_cap_policy=SeniorPrincipalCapPolicy.CAP_AT_EXPLICIT_AVAILABLE_CASH,
            reserve_treatment=SeniorReserveTreatment.INCLUDE_DSRA_MOVEMENTS,
        )
        proj = replace(solar_project, financing=replace(solar_project.financing,
            senior_sculpting_config=config))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.financing.senior_sculpting_config == config

    def test_dscr_schedule_list_preserved(self, solar_project):
        proj = replace(solar_project, financing=replace(solar_project.financing,
            dscr_schedule=[1.20, 1.20, 1.15, 1.15]))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.financing.dscr_schedule == [1.20, 1.20, 1.15, 1.15]


class TestTaxRoundTrip:

    def test_construction_pl_none_preserved(self, solar_project):
        restored = project_inputs_from_dict(project_inputs_to_dict(solar_project))
        assert restored.tax.construction_pl is None

    def test_construction_pl_preserved(self, solar_project):
        cpl = ConstructionPLStatement(
            idc_keur=1200.0, bank_fees_keur=300.0, commitment_fees_keur=150.0,
            pre_operational_opex_keur=50.0, construction_period_revenue_keur=0.0,
            other_book_tax_difference_keur=25.0,
        )
        proj = replace(solar_project, tax=replace(solar_project.tax, construction_pl=cpl))
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.tax.construction_pl == cpl
        assert isinstance(restored.tax.construction_pl, ConstructionPLStatement)

    def test_tax_params_all_fields_preserved(self, solar_project):
        tax = TaxParams(
            corporate_rate=0.18,
            loss_carryforward_years=7,
            loss_carryforward_cap=0.5,
            prior_tax_loss_keur=5000.0,
            legal_reserve_cap=0.05,
            thin_cap_enabled=True,
            thin_cap_de_ratio=0.75,
            atad_ebitda_limit=0.25,
            atad_min_interest_keur=2000.0,
            wht_sponsor_dividends=0.10,
            wht_sponsor_shl_interest=0.05,
            shl_cap_applies=False,
            cit_cash_tax_start_operating_index=3,
        )
        proj = replace(solar_project, tax=tax)
        restored = project_inputs_from_dict(project_inputs_to_dict(proj))
        assert restored.tax == tax


# ── Parity: TUHO and Oborovo from real waterfall fixtures ─────────────────────

class TestProjectInputsParity:
    """Round-trip on real TUHO and Oborovo project inputs."""

    @pytest.fixture(scope="class")
    def tuho_inputs(self):
        from app.ui_runner import run_demo_project
        demo = run_demo_project("TUHO")
        assert demo.project_inputs is not None
        return demo.project_inputs

    @pytest.fixture(scope="class")
    def oborovo_inputs(self):
        from app.ui_runner import run_demo_project
        demo = run_demo_project("Oborovo")
        assert demo.project_inputs is not None
        return demo.project_inputs

    def test_tuho_round_trip(self, tuho_inputs):
        restored = project_inputs_from_dict(project_inputs_to_dict(tuho_inputs))
        assert restored == tuho_inputs

    def test_oborovo_round_trip(self, oborovo_inputs):
        restored = project_inputs_from_dict(project_inputs_to_dict(oborovo_inputs))
        assert restored == oborovo_inputs

    def test_tuho_json_serializable(self, tuho_inputs):
        d = project_inputs_to_dict(tuho_inputs)
        restored = project_inputs_from_dict(json.loads(json.dumps(d)))
        assert restored == tuho_inputs

    def test_oborovo_json_serializable(self, oborovo_inputs):
        d = project_inputs_to_dict(oborovo_inputs)
        restored = project_inputs_from_dict(json.loads(json.dumps(d)))
        assert restored == oborovo_inputs
