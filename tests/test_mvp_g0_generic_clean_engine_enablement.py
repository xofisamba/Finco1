"""MVP-G0 generic clean-engine enablement tests.

These tests prove that fictional Generic Solar and Generic Wind projects run the
clean senior-debt orchestration from ordinary canonical inputs. They assert
causal direction and contract invariants, not Excel parity or brittle goldens.
"""
from __future__ import annotations

import dataclasses
import math

import pytest


def _run(project):
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    model = build_senior_debt_model_input_from_project_inputs(
        project,
        source_id="mvp-g0-generic-clean-engine-test",
    )
    return run_senior_debt_model(model)


def _debt_service_dscr(result) -> list[float]:
    senior = result.senior_debt
    assert senior is not None
    return [
        value
        for value, service in zip(senior.base_dscr, senior.senior_debt_service_keur)
        if value is not None and service > 1e-9
    ]


def _assert_clean_chain_complete(result) -> None:
    assert result.tax_and_cfads is not None
    assert result.senior_debt is not None
    assert result.debt_sizing is not None
    assert result.post_senior_cash is not None
    assert result.shareholder_loan is not None

    n = len(result.periods)
    assert n > 0
    assert len(result.operating_schedules.period_indices) == n
    assert len(result.tax_and_cfads.period_indices) == n
    assert len(result.post_senior_cash.period_indices) == n
    assert len(result.shareholder_loan.period_indices) == n

    for values in (
        result.operating_schedules.production_mwh,
        result.operating_schedules.revenue_keur,
        result.operating_schedules.opex_keur,
        result.operating_schedules.ebitda_keur,
        result.operating_schedules.book_depreciation_keur,
        result.tax_and_cfads.corporate_tax_cash_keur,
        result.tax_and_cfads.cfads_keur,
        result.debt_sizing.bank_cfads_keur,
        result.post_senior_cash.cash_after_senior_before_reserves_keur,
    ):
        assert all(math.isfinite(v) for v in values)

    op_positions = [i for i, period in enumerate(result.periods) if period.is_operation]
    assert any(result.operating_schedules.production_mwh[i] > 0 for i in op_positions)
    assert all(result.operating_schedules.production_mwh[i] > 0 for i in op_positions)

    senior = result.senior_debt
    assert senior.debt_size_keur > 0.0
    assert abs(senior.senior_debt_closing_keur[-1]) < 1e-3
    assert all(math.isfinite(v) for v in senior.senior_interest_keur)
    assert all(math.isfinite(v) for v in senior.senior_principal_keur)
    assert all(math.isfinite(v) for v in senior.senior_debt_service_keur)
    assert all(math.isfinite(v) for v in _debt_service_dscr(result))

    shl = result.shareholder_loan
    construction_positions = [i for i, period in enumerate(result.periods) if period.is_construction]
    first_operating_position = next(i for i, period in enumerate(result.periods) if period.is_operation)
    assert [i for i, value in enumerate(shl.shl_drawdown_keur) if value > 0.0] == [
        construction_positions[-1]
    ]
    assert shl.shl_closing_keur[construction_positions[-1]] == pytest.approx(
        shl.shl_drawdown_keur[construction_positions[-1]]
    )
    assert shl.shl_opening_keur[first_operating_position] == pytest.approx(
        shl.shl_drawdown_keur[construction_positions[-1]]
    )
    assert all(value >= 0.0 for value in shl.shl_principal_keur)
    principal_positions = [i for i, value in enumerate(shl.shl_principal_keur) if value > 1e-9]
    assert principal_positions == [33]
    assert shl.shl_closing_keur[33] == pytest.approx(0.0, abs=1e-9)
    assert shl.diagnostics.is_authoritative is True
    assert shl.diagnostics.max_final_shl_interest_handshake_delta_keur < 1e-6
    assert shl.diagnostics.max_final_shl_closing_handshake_delta_keur < 1e-6


@pytest.mark.parametrize(
    ("label", "factory_name"),
    (
        ("Generic Solar", "create_default_solar_project"),
        ("Generic Wind", "create_default_wind_project"),
    ),
)
def test_generic_solar_and_wind_run_clean_chain_end_to_end(label, factory_name):
    from app import project_factories
    from finco_core.inputs import DebtSizingMode, TaxLossUtilisationGate, TaxPeriodisationMode
    from finco_core.inputs.senior_rate_schedule import SeniorDayCountConvention, SeniorRateMode

    project = getattr(project_factories, factory_name)()

    assert project.tax.clean_cash_tax_timing_enabled is True
    assert project.tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE
    assert project.tax.tax_periodisation_mode == TaxPeriodisationMode.CALENDAR_TAX_YEAR
    assert project.financing.debt_sizing_mode == DebtSizingMode.FLAT_DSCR_SCULPTED
    assert project.financing.resolved_debt_sizing_mode() == DebtSizingMode.FLAT_DSCR_SCULPTED
    assert project.financing.senior_debt_interest_config.day_count == SeniorDayCountConvention.ACT_360
    assert project.financing.senior_debt_interest_config.rate_schedule.mode == (
        SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE
    )
    assert project.financing.clean_shl_principal_keur == project.financing.shl_amount_keur
    from finco_core.inputs import SHLRepaymentMethod

    assert project.financing.clean_shl_repayment_method is SHLRepaymentMethod.BULLET
    assert project.financing.shl_tenor_years == 0
    assert project.financing.shl_day_count_convention == "PERIOD_AXIS_ACTUAL_YEAR"
    assert project.financing.shl_construction_day_count_fraction == 0.0

    first = _run(project)
    second = _run(project)

    _assert_clean_chain_complete(first)
    assert first.senior_debt.debt_size_keur == pytest.approx(second.senior_debt.debt_size_keur)
    assert first.debt_sizing.bank_cfads_keur == pytest.approx(second.debt_sizing.bank_cfads_keur)
    assert first.tax_and_cfads.cfads_keur == pytest.approx(second.tax_and_cfads.cfads_keur)
    assert first.shareholder_loan.shl_closing_keur == pytest.approx(
        second.shareholder_loan.shl_closing_keur
    )


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_generic_bank_case_uses_p90_while_base_remains_p50(factory_name):
    from app import project_factories

    project = getattr(project_factories, factory_name)()
    result = _run(project)

    assert max(result.debt_sizing.bank_production_mwh) < max(
        result.operating_schedules.production_mwh
    )
    assert sum(result.debt_sizing.bank_production_mwh) < sum(
        result.operating_schedules.production_mwh
    )


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_generic_shl_contract_is_causal_and_independent_of_bank_case(factory_name):
    from app import project_factories
    from finco_core.inputs import DebtSizingCaseConfig, YieldScenario

    project = getattr(project_factories, factory_name)()
    base = _run(project)
    larger_principal = _run(
        dataclasses.replace(
            project,
            financing=dataclasses.replace(
                project.financing,
                clean_shl_principal_keur=project.financing.clean_shl_principal_keur * 1.10,
            ),
        )
    )
    higher_rate = _run(
        dataclasses.replace(
            project,
            financing=dataclasses.replace(
                project.financing,
                shl_rate=project.financing.shl_rate + 0.01,
            ),
        )
    )
    p50_bank = _run(
        dataclasses.replace(
            project,
            financing=dataclasses.replace(
                project.financing,
                debt_sizing_case=DebtSizingCaseConfig(
                    production_yield_scenario=YieldScenario.P50,
                    source_label="generic-p50-bank-mutation",
                ),
            ),
        )
    )

    assert max(larger_principal.shareholder_loan.shl_drawdown_keur) == pytest.approx(
        max(base.shareholder_loan.shl_drawdown_keur) * 1.10
    )
    assert sum(larger_principal.shareholder_loan.shl_gross_interest_keur) > sum(
        base.shareholder_loan.shl_gross_interest_keur
    )
    assert sum(higher_rate.shareholder_loan.shl_gross_interest_keur) > sum(
        base.shareholder_loan.shl_gross_interest_keur
    )
    for changed in (larger_principal, higher_rate):
        assert sum(changed.debt_sizing.bank_cash_tax_keur) < sum(
            base.debt_sizing.bank_cash_tax_keur
        )
        assert sum(changed.debt_sizing.bank_cfads_keur) > sum(
            base.debt_sizing.bank_cfads_keur
        )
        # SHL causality operates through DSCR capacity; the final Senior may be
        # gearing-capped at the same level even when DSCR capacity increases.
        assert changed.senior_debt.diagnostics["dscr_debt_capacity_keur"] > base.senior_debt.diagnostics["dscr_debt_capacity_keur"]
    # P50 bank case gives higher DSCR capacity; final Senior may remain gearing-capped.
    assert p50_bank.senior_debt.diagnostics["dscr_debt_capacity_keur"] != pytest.approx(base.senior_debt.diagnostics["dscr_debt_capacity_keur"])
    assert max(p50_bank.shareholder_loan.shl_drawdown_keur) == pytest.approx(
        max(base.shareholder_loan.shl_drawdown_keur)
    )
    assert [i for i, value in enumerate(p50_bank.shareholder_loan.shl_principal_keur) if value > 1e-9] == [33]


def test_generic_explicit_shl_maturity_mutation_moves_bullet_without_changing_terms():
    from app.project_factories import create_default_wind_project

    project = create_default_wind_project()
    later = _run(
        dataclasses.replace(
            project,
            financing=dataclasses.replace(
                project.financing,
                shl_maturity_period_index=35,
            ),
        )
    )

    shl = later.shareholder_loan
    assert [i for i, value in enumerate(shl.shl_principal_keur) if value > 1e-9] == [35]
    assert max(shl.shl_drawdown_keur) == pytest.approx(project.financing.shl_amount_keur)
    assert shl.shl_closing_keur[35] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_generic_senior_rate_schedule_has_no_total_period_count_80_binding(factory_name):
    from app import project_factories
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )

    project = getattr(project_factories, factory_name)()
    config = project.financing.senior_debt_interest_config
    model = build_senior_debt_model_input_from_project_inputs(project)

    assert not hasattr(config, "total_period_count")
    assert len(config.rate_schedule.explicit_all_in_rates) == 30
    assert len(model.senior_debt_inputs.period_rates) == 30
    assert model.senior_debt_policy.maturity_period_index == 31
    assert max(rate.period_index for rate in model.senior_debt_inputs.period_rates) == 31


def test_generic_bank_case_mutation_changes_sizing_without_mutating_base_case():
    from app.project_factories import create_default_solar_project
    from finco_core.inputs import DebtSizingCaseConfig, YieldScenario

    project = create_default_solar_project()
    base = _run(project)
    p50_bank_project = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            debt_sizing_case=DebtSizingCaseConfig(production_yield_scenario=YieldScenario.P50),
        ),
    )
    p50_bank = _run(p50_bank_project)

    assert sum(p50_bank.debt_sizing.bank_production_mwh) > sum(
        base.debt_sizing.bank_production_mwh
    )
    assert sum(p50_bank.debt_sizing.bank_cfads_keur) > sum(base.debt_sizing.bank_cfads_keur)
    # When gearing binds, the final Senior is capped at the gearing level regardless of DSCR.
    # The DSCR capacity diagnostic captures the increase.
    assert p50_bank.senior_debt.diagnostics["dscr_debt_capacity_keur"] > base.senior_debt.diagnostics["dscr_debt_capacity_keur"]
    assert p50_bank.operating_schedules.production_mwh == pytest.approx(
        base.operating_schedules.production_mwh
    )
    assert p50_bank.operating_schedules.revenue_keur == pytest.approx(
        base.operating_schedules.revenue_keur
    )
    assert p50_bank.operating_schedules.ebitda_keur == pytest.approx(
        base.operating_schedules.ebitda_keur
    )


def test_generic_price_downside_reduces_revenue_ebitda_bank_cfads_and_debt():
    from app.project_factories import create_default_solar_project

    project = create_default_solar_project()
    base = _run(project)
    price_downside = dataclasses.replace(
        project,
        revenue=dataclasses.replace(
            project.revenue,
            ppa_base_tariff=project.revenue.ppa_base_tariff * 0.90,
            market_prices_curve=tuple(v * 0.90 for v in project.revenue.market_prices_curve),
        ),
    )
    downside = _run(price_downside)

    assert sum(downside.operating_schedules.revenue_keur) < sum(base.operating_schedules.revenue_keur)
    assert sum(downside.operating_schedules.ebitda_keur) < sum(base.operating_schedules.ebitda_keur)
    assert sum(downside.debt_sizing.bank_cfads_keur) < sum(base.debt_sizing.bank_cfads_keur)
    # When gearing binds, verify the price shock reduces DSCR capacity (not just final Senior).
    assert downside.senior_debt.diagnostics["dscr_debt_capacity_keur"] < base.senior_debt.diagnostics["dscr_debt_capacity_keur"]


def test_generic_opex_downside_reduces_ebitda_cfads_and_debt():
    from app.project_factories import create_default_wind_project

    project = create_default_wind_project()
    base = _run(project)
    opex_downside = dataclasses.replace(
        project,
        opex=tuple(
            dataclasses.replace(item, y1_amount_keur=item.y1_amount_keur * 1.10)
            for item in project.opex
        ),
    )
    downside = _run(opex_downside)

    assert sum(downside.operating_schedules.ebitda_keur) < sum(base.operating_schedules.ebitda_keur)
    assert sum(downside.tax_and_cfads.cfads_keur) < sum(base.tax_and_cfads.cfads_keur)
    assert sum(downside.debt_sizing.bank_cfads_keur) < sum(base.debt_sizing.bank_cfads_keur)
    # When gearing binds, verify the opex shock reduces DSCR capacity (not just final Senior).
    assert downside.senior_debt.diagnostics["dscr_debt_capacity_keur"] < base.senior_debt.diagnostics["dscr_debt_capacity_keur"]


def test_generic_target_dscr_increase_reduces_debt_capacity():
    from app.project_factories import create_default_solar_project

    project = create_default_solar_project()
    base = _run(project)
    stricter = _run(
        dataclasses.replace(
            project,
            financing=dataclasses.replace(
                project.financing,
                target_dscr=project.financing.target_dscr + 0.15,
            ),
        )
    )

    # When gearing binds, verify stricter DSCR reduces DSCR capacity (not just final Senior).
    assert stricter.senior_debt.diagnostics["dscr_debt_capacity_keur"] < base.senior_debt.diagnostics["dscr_debt_capacity_keur"]


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_generic_bank_sizing_dscr_is_the_target_authority(factory_name):
    from app import project_factories

    project = getattr(project_factories, factory_name)()
    # Strip gearing constraint so DSCR sculpting is unconstrained: this tests the
    # DSCR authority mechanism in isolation, not the combined-minimum cap.
    unconstrained = dataclasses.replace(
        project,
        financing=dataclasses.replace(project.financing, gearing_basis_mode=None),
    )
    result = _run(unconstrained)
    senior = result.senior_debt
    sizing = result.debt_sizing
    assert senior is not None
    assert sizing is not None

    bank_cfads_by_period = dict(zip(sizing.period_indices, sizing.bank_cfads_keur))
    solver_bank_dscr_by_period = dict(
        zip(sizing.period_indices, sizing.solver_bank_dscr)
    )
    for period_index, debt_service in zip(
        senior.period_indices,
        senior.senior_debt_service_keur,
    ):
        if debt_service <= 1e-9:
            continue
        bank_cfads = bank_cfads_by_period[period_index]
        assert debt_service == pytest.approx(
            bank_cfads / unconstrained.financing.target_dscr,
            abs=1e-8,
        )
        assert solver_bank_dscr_by_period[period_index] == pytest.approx(
            unconstrained.financing.target_dscr,
            abs=1e-10,
        )


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_generic_base_dscr_is_independent_of_bank_sizing_case(factory_name):
    from app import project_factories

    project = getattr(project_factories, factory_name)()
    # Strip gearing constraint so DSCR-sculpted debt service is the authority.
    # When gearing binds, the sculpted profile is scaled down and base DSCR may
    # never fall below target; this test is about the base/bank CFADS split.
    unconstrained = dataclasses.replace(
        project,
        financing=dataclasses.replace(project.financing, gearing_basis_mode=None),
    )
    result = _run(unconstrained)
    senior = result.senior_debt
    sizing = result.debt_sizing
    tax_and_cfads = result.tax_and_cfads
    assert senior is not None
    assert sizing is not None
    assert tax_and_cfads is not None

    base_cfads_by_period = dict(zip(tax_and_cfads.period_indices, tax_and_cfads.cfads_keur))
    bank_cfads_by_period = dict(zip(sizing.period_indices, sizing.bank_cfads_keur))
    below_target = []
    for period_index, debt_service, base_dscr in zip(
        senior.period_indices,
        senior.senior_debt_service_keur,
        senior.base_dscr,
    ):
        if debt_service <= 1e-9:
            continue
        assert base_dscr == pytest.approx(
            base_cfads_by_period[period_index] / debt_service,
            abs=1e-10,
        )
        if base_dscr < unconstrained.financing.target_dscr:
            below_target.append(period_index)

    assert below_target
    first = below_target[0]
    assert base_cfads_by_period[first] != pytest.approx(bank_cfads_by_period[first])


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_generic_shl_changes_senior_capacity_only_through_tax_cfads(factory_name):
    from app import project_factories
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.policies.tax import ShlInterestDeductibilityMode

    project = getattr(project_factories, factory_name)()
    model = build_senior_debt_model_input_from_project_inputs(project)
    with_shl = run_senior_debt_model(model)
    without_shl = run_senior_debt_model(dataclasses.replace(model, shareholder_loan=None))
    non_deductible = run_senior_debt_model(
        dataclasses.replace(
            model,
            tax=dataclasses.replace(
                model.tax,
                policy=dataclasses.replace(
                    model.tax.policy,
                    shl_interest_deductibility=(
                        ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE
                    ),
                    shl_interest_deductible_pct=None,
                ),
            ),
        )
    )

    assert with_shl.shareholder_loan is not None
    assert sum(with_shl.shareholder_loan.shl_gross_interest_keur) > 0.0
    assert sum(with_shl.debt_sizing.bank_cash_tax_keur) < sum(
        without_shl.debt_sizing.bank_cash_tax_keur
    )
    assert sum(with_shl.debt_sizing.bank_cfads_keur) > sum(
        without_shl.debt_sizing.bank_cfads_keur
    )
    # SHL causality operates via DSCR capacity; final Senior may be gearing-capped.
    assert with_shl.senior_debt.diagnostics["dscr_debt_capacity_keur"] > without_shl.senior_debt.diagnostics["dscr_debt_capacity_keur"]

    # Keeping the SHL schedule but removing its tax deduction removes the entire
    # Senior-capacity effect: there is no direct SHL-to-debt or terminal top-up path.
    assert non_deductible.senior_debt.diagnostics["dscr_debt_capacity_keur"] == pytest.approx(
        without_shl.senior_debt.diagnostics["dscr_debt_capacity_keur"],
        abs=1e-8,
    )
    assert non_deductible.debt_sizing.bank_cfads_keur == pytest.approx(
        without_shl.debt_sizing.bank_cfads_keur,
        abs=1e-8,
    )


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_generic_outputs_are_project_identity_invariant(factory_name):
    from app import project_factories

    project = getattr(project_factories, factory_name)()
    renamed = dataclasses.replace(
        project,
        info=dataclasses.replace(
            project.info,
            name=f"Renamed {project.info.name}",
            code=f"RENAMED-{project.info.code}",
        ),
    )

    base = _run(project)
    clone = _run(renamed)

    assert clone.senior_debt.debt_size_keur == pytest.approx(base.senior_debt.debt_size_keur)
    assert clone.operating_schedules.production_mwh == pytest.approx(
        base.operating_schedules.production_mwh
    )
    assert clone.tax_and_cfads.cfads_keur == pytest.approx(base.tax_and_cfads.cfads_keur)
    assert clone.debt_sizing.bank_cfads_keur == pytest.approx(base.debt_sizing.bank_cfads_keur)


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_generic_clean_tax_timing_survives_roundtrip_and_old_payloads_fail_closed(factory_name):
    from app import project_factories
    from finco_core.inputs.serialization import project_inputs_from_dict, project_inputs_to_dict

    project = getattr(project_factories, factory_name)()
    payload = project_inputs_to_dict(project)
    restored = project_inputs_from_dict(payload)

    assert restored.tax.clean_cash_tax_timing_enabled is True
    assert restored.financing.debt_sizing_mode == project.financing.debt_sizing_mode
    assert restored.financing.senior_debt_interest_config == (
        project.financing.senior_debt_interest_config
    )
    _assert_clean_chain_complete(_run(restored))

    legacy_payload = project_inputs_to_dict(project)
    legacy_payload["tax"].pop("clean_cash_tax_timing_enabled", None)
    legacy_restored = project_inputs_from_dict(legacy_payload)
    assert legacy_restored.tax.clean_cash_tax_timing_enabled is False
    with pytest.raises(NotImplementedError, match="clean_cash_tax_timing_enabled=False"):
        _run(legacy_restored)


def test_generic_clean_path_contains_no_source_fixture_or_frozen_vector_runtime_inputs():
    from app.project_factories import create_default_solar_project, create_default_wind_project

    for project in (create_default_solar_project(), create_default_wind_project()):
        assert project.financing.fixed_debt_keur is None
        assert project.financing.frozen_senior_ds_fixture_path is None
        assert project.financing.use_frozen_excel_senior_debt_schedule is False
        assert not project.financing.senior_sculpting_config.explicit_principal_schedule
        assert not project.financing.senior_sculpting_config.explicit_debt_service_schedule
        assert not project.financing.senior_sculpting_config.available_senior_cfads_schedule
