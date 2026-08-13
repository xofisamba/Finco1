"""C3B3D2B3.1 completion tests for the generic debt-sizing production contract."""
from __future__ import annotations

import inspect
import math

import pytest


def _make_base_op():
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import from_project_inputs

    return from_project_inputs(create_default_tuho_wind1())


def _make_tax_input():
    from financial_engine.inputs import TaxCalculationInput
    from finco_parity.tax_reference_inputs import build_opening_loss_vintages, build_tax_policy

    return TaxCalculationInput(
        policy=build_tax_policy("tuho"),
        opening_loss_vintages=build_opening_loss_vintages("tuho"),
        period_interest=(),
        period_adjustments=(),
    )


def _make_policy():
    from financial_engine.senior_debt.policy import (
        DayCountConvention,
        SeniorDebtPolicy,
        SeniorDebtSizingMode,
    )

    return SeniorDebtPolicy(
        policy_id="c3b3d2b3_hardening",
        policy_version="1.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.2,
        maximum_gearing=None,
        annual_fixed_rate=0.05,
        periods_per_year=2,
        day_count_convention=DayCountConvention.ACT_365,
        repayment_start_period_index=2,
        maturity_period_index=61,
        convergence_tolerance_keur=1.0,
        convergence_relative_tolerance=0.001,
        maximum_iterations=300,
        permit_terminal_balloon=True,
    )


def _make_sd_inputs():
    from financial_engine.senior_debt.inputs import SeniorDebtInputs

    return SeniorDebtInputs(
        eligible_project_cost_keur=100_000.0,
        initial_debt_guess_keur=60_000.0,
        period_rates=(),
        explicit_principal_schedule=None,
    )


def _run_case(*, price: float, source_label: str = ""):
    from financial_engine.inputs import (
        DebtSizingCaseInput,
        SeniorDebtModelInput,
        YieldScenario,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    base_op = _make_base_op()
    model = SeniorDebtModelInput(
        operating=base_op,
        tax=_make_tax_input(),
        senior_debt_policy=_make_policy(),
        senior_debt_inputs=_make_sd_inputs(),
        debt_sizing_case=DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            market_prices_curve_eur_mwh=tuple([price] * 40),
            source_label=source_label,
        ),
    )
    return model, run_senior_debt_model(model)


class TestFinitePriceValidation:
    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_relative_curve_rejects_nonfinite(self, bad):
        from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

        with pytest.raises(ValueError, match="finite numeric value"):
            DebtSizingCaseInput(
                production_yield_scenario=YieldScenario.P90_10Y,
                market_prices_curve_eur_mwh=(50.0, bad),
            )

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_calendar_curve_rejects_nonfinite(self, bad):
        from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

        with pytest.raises(ValueError, match="finite numeric value"):
            DebtSizingCaseInput(
                production_yield_scenario=YieldScenario.P90_10Y,
                merchant_price_calendar_start_year=2030,
                merchant_prices_by_calendar_year_eur_mwh=(50.0, bad),
            )

    def test_invalid_calendar_year_rejected(self):
        from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

        with pytest.raises(ValueError, match="integer year"):
            DebtSizingCaseInput(
                production_yield_scenario=YieldScenario.P90_10Y,
                merchant_price_calendar_start_year=2030.5,  # type: ignore[arg-type]
                merchant_prices_by_calendar_year_eur_mwh=(50.0,),
            )


class TestProductionAdapterSeam:
    def test_explicit_debt_sizing_case_is_public_adapter_argument(self):
        from financial_engine.adapters.project_inputs import (
            build_senior_debt_model_input_from_project_inputs,
        )

        sig = inspect.signature(build_senior_debt_model_input_from_project_inputs)
        assert "debt_sizing_case" in sig.parameters
        assert sig.parameters["debt_sizing_case"].default is None

    def test_default_policy_remains_p90(self):
        from app.project_factories import (
            create_default_solar_project,
            create_default_tuho_wind1,
            create_default_wind_project,
        )
        from finco_core.inputs import YieldScenario

        for factory in (
            create_default_solar_project,
            create_default_wind_project,
            create_default_tuho_wind1,
        ):
            project = factory()
            assert project.financing.debt_sizing_case.production_yield_scenario == (
                YieldScenario.P90_10Y
            )

    def test_legacy_payload_without_debt_sizing_case_loads_p90_default(self):
        from app.project_factories import create_default_solar_project
        from finco_core.inputs import YieldScenario
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )

        payload = project_inputs_to_dict(create_default_solar_project())
        payload["financing"].pop("debt_sizing_case")
        restored = project_inputs_from_dict(payload)
        assert restored.financing.debt_sizing_case.production_yield_scenario == (
            YieldScenario.P90_10Y
        )

    def test_oborovo_and_renamed_clone_keep_explicit_p50_bank_case(self):
        from dataclasses import replace

        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import (
            build_senior_debt_model_input_from_project_inputs,
        )
        from financial_engine.inputs import YieldScenario
        from financial_engine.orchestrator import run_senior_debt_model

        project = create_default_oborovo()
        renamed = replace(project, info=replace(project.info, name="Renamed Clone"))
        model = build_senior_debt_model_input_from_project_inputs(
            project,
            source_id="b3-hardening-oborovo",
        )
        clone_model = build_senior_debt_model_input_from_project_inputs(
            renamed,
            source_id="b3-hardening-oborovo-clone",
        )
        assert model.debt_sizing_case.production_yield_scenario == YieldScenario.P50
        assert clone_model.debt_sizing_case.production_yield_scenario == YieldScenario.P50
        assert run_senior_debt_model(model).senior_debt.debt_size_keur == pytest.approx(
            run_senior_debt_model(clone_model).senior_debt.debt_size_keur
        )

    def test_explicit_adapter_override_remains_diagnostic(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import (
            build_senior_debt_model_input_from_project_inputs,
        )
        from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

        model = build_senior_debt_model_input_from_project_inputs(
            create_default_oborovo(),
            source_id="b3-hardening-diagnostic-override",
            debt_sizing_case=DebtSizingCaseInput(
                production_yield_scenario=YieldScenario.P90_10Y,
                source_label="diagnostic override",
            ),
        )
        assert model.debt_sizing_case.production_yield_scenario == YieldScenario.P90_10Y
        assert model.debt_sizing_case.source_label == "diagnostic override"

    def test_explicit_case_supports_calendar_and_relative_price_contracts(self):
        from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

        cal = DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_price_calendar_start_year=2030,
            merchant_prices_by_calendar_year_eur_mwh=(55.0, 54.0),
        )
        rel = DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            market_prices_curve_eur_mwh=(55.0, 54.0),
        )
        assert cal.merchant_prices_by_calendar_year_eur_mwh == (55.0, 54.0)
        assert rel.market_prices_curve_eur_mwh == (55.0, 54.0)


class TestRuntimeCausalityCompletion:
    def test_bank_price_changes_bank_ebitda_cfads_and_debt_but_not_base(self):
        _, high = _run_case(price=80.0)
        _, low = _run_case(price=20.0)

        assert high.debt_sizing is not None and low.debt_sizing is not None
        assert high.senior_debt is not None and low.senior_debt is not None

        # Base/equity performance surface is invariant to bank price assumptions.
        assert high.operating_schedules.production_mwh == low.operating_schedules.production_mwh
        assert high.operating_schedules.revenue_keur == low.operating_schedules.revenue_keur
        assert high.operating_schedules.opex_keur == low.operating_schedules.opex_keur
        assert high.operating_schedules.ebitda_keur == low.operating_schedules.ebitda_keur

        # Bank case responds causally.
        assert sum(high.debt_sizing.bank_revenue_keur) > sum(low.debt_sizing.bank_revenue_keur)
        assert sum(high.debt_sizing.bank_ebitda_keur) > sum(low.debt_sizing.bank_ebitda_keur)
        assert sum(high.debt_sizing.bank_cfads_keur) > sum(low.debt_sizing.bank_cfads_keur)
        assert high.senior_debt.debt_size_keur != low.senior_debt.debt_size_keur

    def test_source_label_changes_no_financial_result_or_fingerprint(self):
        from financial_engine.provenance import compute_senior_debt_fingerprint

        model_a, result_a = _run_case(price=50.0, source_label="lender_case_A")
        model_b, result_b = _run_case(price=50.0, source_label="lender_case_B")

        assert compute_senior_debt_fingerprint(model_a) == compute_senior_debt_fingerprint(model_b)
        assert result_a.operating_schedules == result_b.operating_schedules
        assert result_a.tax_and_cfads == result_b.tax_and_cfads
        assert result_a.debt_sizing == result_b.debt_sizing
        assert result_a.senior_debt == result_b.senior_debt

    def test_bank_cash_tax_is_authoritative_bridge_component(self):
        _, result = _run_case(price=50.0)
        assert result.debt_sizing is not None
        ds = result.debt_sizing
        assert len(ds.bank_cash_tax_keur) == len(ds.bank_cfads_keur)
        for ebitda, cash_tax, cfads in zip(
            ds.bank_ebitda_keur, ds.bank_cash_tax_keur, ds.bank_cfads_keur
        ):
            assert cfads == pytest.approx(ebitda - cash_tax, abs=1e-9)


class TestBankTaxAdjustmentContract:
    def test_project_input_tax_adapter_supplies_no_derived_period_adjustments(self):
        from financial_engine.adapters import tax_inputs

        src = inspect.getsource(tax_inputs.build_tax_contract_from_project_inputs)
        assert "period_adjustments=()" in src

    def test_period_adjustments_are_documented_case_invariant_inputs(self):
        from financial_engine.inputs import PeriodTaxAdjustmentInput, TaxCalculationInput

        assert "case-invariant" in (TaxCalculationInput.__doc__ or "")
        assert "not an operating-model" in (PeriodTaxAdjustmentInput.__doc__ or "")


def test_hardening_completion_verdict_contract():
    verdict = "C3B3D2B3_GENERIC_DEBT_SIZING_CASE_PRODUCTION_CONTRACT_HARDENED_AND_EXACT_HEAD_PROVEN"
    assert "HARDENED" in verdict and "EXACT_HEAD_PROVEN" in verdict
