"""MVP G1 current-authority and governance signal locks."""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from finco_recon.governance_identity import find_identity_dispatch, scan_identity_dispatch


ENGINE_ROOT = Path("financial_engine")


def test_real_project_identity_dispatch_is_rejected():
    source = 'if project.code == "OBOROVO":\n    debt = 42_852.0\n'
    assert find_identity_dispatch(source, filename="example.py")


def test_benign_project_terminology_is_not_dispatch():
    source = '"""Oborovo source evidence."""\nlabel = "TUHO compatibility"\n'
    assert find_identity_dispatch(source, filename="example.py") == []


def test_clean_financial_engine_has_no_identity_execution_dispatch():
    assert scan_identity_dispatch(sorted(ENGINE_ROOT.rglob("*.py"))) == []


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_current_generic_authority_is_calculation_driven(factory_name):
    from app import project_factories
    from domain.inputs import DebtSizingMode

    project = getattr(project_factories, factory_name)()
    assert project.financing.resolved_debt_sizing_mode() == DebtSizingMode.FLAT_DSCR_SCULPTED
    assert project.financing.fixed_debt_keur is None
    assert project.financing.use_frozen_excel_senior_debt_schedule is False
    assert project.financing.frozen_senior_ds_fixture_path is None


def test_bank_target_dscr_and_base_dscr_remain_separate_authorities():
    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    project = create_default_solar_project()
    # Strip gearing so DSCR sculpting is unconstrained; when gearing binds the
    # scaled-down debt profile inflates solver_bank_dscr above target.
    unconstrained = dataclasses.replace(
        project,
        financing=dataclasses.replace(project.financing, gearing_basis_mode=None),
    )
    result = run_senior_debt_model(
        build_senior_debt_model_input_from_project_inputs(unconstrained)
    )
    service = result.senior_debt.senior_debt_service_keur
    bank = dict(zip(result.debt_sizing.period_indices, result.debt_sizing.solver_bank_dscr))
    base = dict(zip(result.tax_and_cfads.period_indices, result.tax_and_cfads.cfads_keur))
    observed_base_dscr = []
    for period, debt_service in zip(result.senior_debt.period_indices, service):
        if debt_service <= 1e-9:
            continue
        assert bank[period] == pytest.approx(unconstrained.financing.target_dscr, abs=1e-10)
        observed_base_dscr.append(base[period] / debt_service)
    assert any(
        value != pytest.approx(unconstrained.financing.target_dscr, abs=1e-8)
        for value in observed_base_dscr
    )


@pytest.mark.parametrize(
    "factory_name",
    ("create_default_solar_project", "create_default_wind_project"),
)
def test_shl_affects_senior_only_through_tax_and_bank_cfads(factory_name):
    from app import project_factories
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.policies.tax import ShlInterestDeductibilityMode

    model = build_senior_debt_model_input_from_project_inputs(
        getattr(project_factories, factory_name)()
    )
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
    assert non_deductible.debt_sizing.bank_cfads_keur == pytest.approx(
        without_shl.debt_sizing.bank_cfads_keur, abs=1e-8
    )
    assert non_deductible.senior_debt.debt_size_keur == pytest.approx(
        without_shl.senior_debt.debt_size_keur, abs=1e-8
    )


def test_generic_contract_has_no_source_vector_or_target_fitting_inputs():
    from app.project_factories import create_default_solar_project, create_default_wind_project

    forbidden = (
        "approved_delta",
        "expected_delta",
        "balancing_plug",
        "terminal_top_up",
    )
    for project in (create_default_solar_project(), create_default_wind_project()):
        assert project.financing.fixed_debt_keur is None
        assert project.financing.frozen_senior_ds_fixture_path is None
        assert not project.financing.senior_sculpting_config.explicit_principal_schedule
        assert not project.financing.senior_sculpting_config.explicit_debt_service_schedule
        assert all(not hasattr(project.financing, name) for name in forbidden)


def test_runtime_contracts_contain_no_calibration_execution_markers():
    runtime_files = (
        Path("financial_engine/orchestrator.py"),
        Path("financial_engine/adapters/project_inputs.py"),
        Path("financial_engine/senior_debt/solver.py"),
        Path("financial_engine/shl/production.py"),
    )
    forbidden = (
        "approved_delta",
        "expected_delta",
        "balancing_plug",
        "target fitting",
        "source output vector runtime input",
        "terminal_top_up",
    )
    for path in runtime_files:
        source = path.read_text(encoding="utf-8").lower()
        assert not [term for term in forbidden if term in source], path
