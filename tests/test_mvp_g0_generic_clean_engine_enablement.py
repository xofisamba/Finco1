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
    assert result.shareholder_loan is None

    n = len(result.periods)
    assert n > 0
    assert len(result.operating_schedules.period_indices) == n
    assert len(result.tax_and_cfads.period_indices) == n
    assert len(result.post_senior_cash.period_indices) == n

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

    first = _run(project)
    second = _run(project)

    _assert_clean_chain_complete(first)
    assert first.senior_debt.debt_size_keur == pytest.approx(second.senior_debt.debt_size_keur)
    assert first.debt_sizing.bank_cfads_keur == pytest.approx(second.debt_sizing.bank_cfads_keur)
    assert first.tax_and_cfads.cfads_keur == pytest.approx(second.tax_and_cfads.cfads_keur)


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
    assert p50_bank.senior_debt.debt_size_keur > base.senior_debt.debt_size_keur
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
    assert downside.senior_debt.debt_size_keur < base.senior_debt.debt_size_keur


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
    assert downside.senior_debt.debt_size_keur < base.senior_debt.debt_size_keur


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

    assert stricter.senior_debt.debt_size_keur < base.senior_debt.debt_size_keur


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
