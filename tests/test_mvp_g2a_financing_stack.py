from __future__ import annotations

import dataclasses

import pytest

from finco_core.inputs import GearingBasisMode, SponsorFundingMode
from financial_engine.financing import run_project_financing_model
from financial_engine.financing.stack import reconcile_financing_stack


@pytest.mark.parametrize(
    ("factory_name", "uses", "dscr_capacity", "gearing_capacity", "derived_shl"),
    (
        ("create_default_solar_project", 33_000.0, 28_458.117382991935, 24_750.0, 7_750.0),
        ("create_default_wind_project", 43_000.0, 45_842.05065359109, 32_250.0, 10_250.0),
    ),
)
def test_generic_shl_mode_derives_complete_funding_stack(
    factory_name, uses, dscr_capacity, gearing_capacity, derived_shl
):
    from app import project_factories

    project = getattr(project_factories, factory_name)()
    result = run_project_financing_model(project)

    assert result.project_uses.total_project_uses_keur == pytest.approx(uses)
    assert result.dscr_debt_capacity_keur == pytest.approx(dscr_capacity, abs=1e-8)
    assert result.gearing_basis_keur == pytest.approx(uses)
    assert result.gearing_ratio == pytest.approx(0.75)
    assert result.gearing_debt_capacity_keur == pytest.approx(gearing_capacity)
    assert result.final_senior_commitment_keur == pytest.approx(gearing_capacity)
    assert result.binding_senior_constraint == "GEARING"
    assert result.share_capital_keur == pytest.approx(500.0)
    assert result.additional_equity_keur == pytest.approx(0.0)
    assert result.derived_shl_cash_principal_keur == pytest.approx(derived_shl)
    assert result.shl_construction_pik_keur == pytest.approx(0.0)
    assert result.opening_operating_shl_balance_keur == pytest.approx(derived_shl)
    assert result.fixed_point_iteration_count >= 2

    schedules = result.project_model_result
    assert schedules.senior_debt.debt_size_keur == pytest.approx(gearing_capacity)
    assert schedules.senior_debt.diagnostics["gearing_debt_capacity_keur"] == pytest.approx(
        gearing_capacity
    )
    assert schedules.shareholder_loan is not None
    assert sum(schedules.shareholder_loan.shl_drawdown_keur) == pytest.approx(derived_shl)
    bank_dscr = [x for x in schedules.debt_sizing.solver_bank_dscr if x is not None]
    assert min(bank_dscr) >= project.financing.target_dscr - 1e-12


@pytest.mark.parametrize(
    ("factory_name", "no_shl_capacity", "final_senior", "additional_equity"),
    (
        ("create_default_solar_project", 27_349.340096443833, 24_750.0, 7_750.0),
        ("create_default_wind_project", 44_095.0171410797, 32_250.0, 10_250.0),
    ),
)
def test_equity_only_mode_preserves_gearing_and_funds_residual_as_equity(
    factory_name, no_shl_capacity, final_senior, additional_equity
):
    from app import project_factories

    project = getattr(project_factories, factory_name)()
    project = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            sponsor_funding_mode=SponsorFundingMode.EQUITY_ONLY,
        ),
    )
    result = run_project_financing_model(project)

    assert result.dscr_debt_capacity_keur == pytest.approx(no_shl_capacity, abs=1e-8)
    assert result.final_senior_commitment_keur == pytest.approx(final_senior)
    assert result.derived_shl_cash_principal_keur == 0.0
    assert result.additional_equity_keur == pytest.approx(additional_equity)
    assert result.project_model_result.shareholder_loan is None


@pytest.mark.parametrize(
    "factory_name", ("create_default_solar_project", "create_default_wind_project")
)
def test_construction_sources_and_uses_reconcile_every_period_and_cumulatively(factory_name):
    from app import project_factories

    result = run_project_financing_model(getattr(project_factories, factory_name)())
    funding = result.construction_funding

    assert funding.policy == "GENERIC_MVP_SPONSOR_FIRST_LINEAR_USES"
    assert funding.maximum_period_difference_keur <= 1e-9
    assert funding.maximum_cumulative_difference_keur <= 1e-8
    for row in funding.periods:
        assert row.total_sources_keur == pytest.approx(row.project_cash_uses_keur, abs=1e-9)
        assert row.cumulative_total_sources_keur == pytest.approx(
            row.cumulative_project_cash_uses_keur, abs=1e-8
        )
    last = funding.periods[-1]
    assert last.cumulative_senior_draw_keur == pytest.approx(
        result.final_senior_commitment_keur
    )
    assert last.cumulative_shl_cash_draw_keur == pytest.approx(
        result.derived_shl_cash_principal_keur
    )


def test_financing_stack_exposes_dscr_and_gearing_binding_cases():
    from app.project_factories import create_default_solar_project

    gearing_bound = run_project_financing_model(create_default_solar_project())
    dscr_project = create_default_solar_project()
    dscr_project = dataclasses.replace(
        dscr_project,
        financing=dataclasses.replace(dscr_project.financing, gearing_ratio=1.0),
    )
    dscr_bound = run_project_financing_model(dscr_project)

    assert gearing_bound.binding_senior_constraint == "GEARING"
    assert dscr_bound.binding_senior_constraint == "DSCR"
    assert dscr_bound.final_senior_commitment_keur == pytest.approx(
        dscr_bound.dscr_debt_capacity_keur
    )
    assert dscr_bound.final_senior_commitment_keur < dscr_bound.gearing_debt_capacity_keur


def test_legacy_generic_shl_amount_is_not_g2a_runtime_authority():
    from app.project_factories import create_default_solar_project

    project = create_default_solar_project()
    changed = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            clean_shl_principal_keur=123.0,
            shl_amount_keur=456.0,
        ),
    )

    base = run_project_financing_model(project)
    mutated = run_project_financing_model(changed)
    assert mutated.derived_shl_cash_principal_keur == pytest.approx(7_750.0)
    assert mutated.dscr_debt_capacity_keur == pytest.approx(base.dscr_debt_capacity_keur)
    assert mutated.final_senior_commitment_keur == pytest.approx(
        base.final_senior_commitment_keur
    )


def test_sponsor_mode_does_not_change_upstream_operating_outputs():
    from app.project_factories import create_default_wind_project

    shl_project = create_default_wind_project()
    equity_project = dataclasses.replace(
        shl_project,
        financing=dataclasses.replace(
            shl_project.financing,
            sponsor_funding_mode=SponsorFundingMode.EQUITY_ONLY,
        ),
    )
    shl = run_project_financing_model(shl_project).project_model_result
    equity = run_project_financing_model(equity_project).project_model_result

    assert equity.operating_schedules.production_mwh == pytest.approx(
        shl.operating_schedules.production_mwh
    )
    assert equity.operating_schedules.revenue_keur == pytest.approx(
        shl.operating_schedules.revenue_keur
    )
    assert equity.operating_schedules.opex_keur == pytest.approx(
        shl.operating_schedules.opex_keur
    )
    assert equity.operating_schedules.ebitda_keur == pytest.approx(
        shl.operating_schedules.ebitda_keur
    )


def test_g2a_modes_roundtrip_and_old_payloads_remain_unpromoted():
    from app.project_factories import create_default_solar_project
    from finco_core.inputs.serialization import project_inputs_from_dict, project_inputs_to_dict

    project = create_default_solar_project()
    payload = project_inputs_to_dict(project)
    restored = project_inputs_from_dict(payload)
    assert restored.financing.sponsor_funding_mode == SponsorFundingMode.SHARE_CAPITAL_THEN_SHL
    assert restored.financing.gearing_basis_mode == GearingBasisMode.TOTAL_PROJECT_USES

    payload["financing"].pop("sponsor_funding_mode")
    payload["financing"].pop("gearing_basis_mode")
    legacy = project_inputs_from_dict(payload)
    assert legacy.financing.sponsor_funding_mode is None
    assert legacy.financing.gearing_basis_mode is None
    with pytest.raises(ValueError, match="SPONSOR_FUNDING_MODE"):
        run_project_financing_model(legacy)


def test_g0_capacity_result_exposes_dscr_capacity_without_applying_gearing():
    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    result = run_senior_debt_model(
        build_senior_debt_model_input_from_project_inputs(create_default_solar_project())
    )
    assert result.senior_debt.debt_size_keur == pytest.approx(28_458.117382991935)
    assert result.senior_debt.diagnostics["dscr_debt_capacity_keur"] == pytest.approx(
        result.senior_debt.debt_size_keur
    )
    assert result.senior_debt.diagnostics["gearing_debt_capacity_keur"] is None


def test_fixed_sources_exceeding_uses_fail_instead_of_hiding_negative_residual():
    with pytest.raises(ValueError, match="FIXED_SOURCES_EXCEED_TOTAL_PROJECT_USES"):
        reconcile_financing_stack(
            total_project_uses_keur=100.0,
            final_senior_commitment_keur=80.0,
            junior_or_other_main_project_funding_keur=20.0,
            share_capital_keur=1.0,
            other_equity_funding_before_shl_keur=0.0,
            sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        )


def test_g2a_contract_contains_no_sponsor_returns_or_balancing_fields():
    from financial_engine.financing.contracts import ProjectFinancingResult

    names = {field.name for field in dataclasses.fields(ProjectFinancingResult)}
    assert not names & {"irr", "moic", "distributions", "balancing_account", "plug"}
