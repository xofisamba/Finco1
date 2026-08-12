"""C3B3D2B5 - generic SHL fixed-point vertical slice.

These tests validate the local Batch A slice without using source vectors as
runtime inputs. Source fixtures are used only in pure schedule parity tests.
"""
from __future__ import annotations

import dataclasses
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"
OBOROVO_SHL_DRAW = 14_620.773894815633
OBOROVO_SHL_RATE = 0.08


def _period(
    idx: int,
    start: date,
    end: date,
    *,
    construction: bool,
):
    from financial_engine.results import OperatingPeriodResult

    return OperatingPeriodResult(
        period_index=idx,
        period_start=start,
        period_end=end,
        year_index=0.0,
        period_in_year=0.0,
        is_construction=construction,
        is_operation=not construction,
        is_ppa_active=False,
        days_in_period=0,
        day_fraction=0.0,
        production_mwh=0.0,
        revenue_keur=0.0,
        opex_keur=0.0,
        ebitda_keur=0.0,
        book_depreciation_keur=0.0,
        tax_depreciation_keur=0.0,
        ebit_keur=0.0,
    )


def _parse_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _oborovo_source_periods_and_cash():
    d2a = json.loads((FIXTURES / "excel_oborovo_shl_operating_truth.json").read_text())
    cf = json.loads((FIXTURES / "excel_oborovo_financial_truth.json").read_text())
    periods = [
        _period(0, date(2030, 1, 1), date(2030, 6, 30), construction=True)
    ]
    for fp in d2a["periods"][1:41]:
        periods.append(
            _period(
                fp["ds_index"],
                _parse_date(fp["period_start_date"]),
                _parse_date(fp["period_end_date"]),
                construction=False,
            )
        )
    cash = (0.0,) + tuple(cf["cf"]["free_cash_flow_for_shl_keur"][1:41])
    return tuple(periods), cash, d2a


def _diag():
    from financial_engine.results import ShareholderLoanDiagnostics

    return ShareholderLoanDiagnostics(
        converged=False,
        is_authoritative=False,
        iteration_count=0,
        max_iterations=1,
        convergence_tolerance_keur=0.0,
        convergence_relative_tolerance=0.0,
        max_closing_delta_keur=0.0,
        max_interest_delta_keur=0.0,
        termination_reason="TEST",
    )


_SHL_UNCHANGED = object()


def _oborovo_shl_input(*, source_label: str = ""):
    from financial_engine.inputs import ShareholderLoanModelInput
    from financial_engine.shl.contracts import ShlDayCountConvention

    return ShareholderLoanModelInput(
        initial_principal_keur=OBOROVO_SHL_DRAW,
        annual_fixed_rate=OBOROVO_SHL_RATE,
        day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
        construction_day_count_fraction=1.0,
        repayment_start_period_index=25,
        maturity_period_index=40,
        convergence_tolerance_keur=1e-4,
        convergence_relative_tolerance=1e-9,
        maximum_iterations=20,
        source_label=source_label,
    )


def _oborovo_model(*, shl_input=_SHL_UNCHANGED, bank_yield=None):
    from dataclasses import replace

    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

    model = build_senior_debt_model_input_from_project_inputs(
        create_default_oborovo(),
        source_id="c3b3d2b5-oborovo",
    )
    if bank_yield is not None:
        model = replace(
            model,
            debt_sizing_case=DebtSizingCaseInput(
                production_yield_scenario=bank_yield,
                source_label="audit_label_not_financial_input",
            ),
        )
    if shl_input is not _SHL_UNCHANGED:
        model = replace(model, shareholder_loan=shl_input)
    return model


def _run_oborovo(*, shl_input=_SHL_UNCHANGED, bank_yield=None):
    from financial_engine.orchestrator import run_senior_debt_model

    return run_senior_debt_model(_oborovo_model(shl_input=shl_input, bank_yield=bank_yield))


def test_source_cash_oracle_reproduces_oborovo_shl_period_by_period():
    """SOURCE_EVIDENCE: source cash proves generic SHL formula, not runtime replay."""
    from financial_engine.shl.production import compute_shareholder_loan_schedules

    periods, cash, d2a = _oborovo_source_periods_and_cash()
    schedule = compute_shareholder_loan_schedules(
        periods,
        _oborovo_shl_input(),
        cash,
        diagnostics=_diag(),
    )
    source = d2a["periods"][1:41]
    max_deltas = {
        "MAX_SOURCE_ORACLE_SHL_GROSS_INTEREST_DELTA_KEUR": max(
            abs(actual - expected["gross_accrued_interest_keur"])
            for actual, expected in zip(schedule.shl_gross_interest_keur[1:], source)
        ),
        "MAX_SOURCE_ORACLE_SHL_CASH_INTEREST_DELTA_KEUR": max(
            abs(actual - expected["cash_interest_keur"])
            for actual, expected in zip(schedule.shl_cash_interest_keur[1:], source)
        ),
        "MAX_SOURCE_ORACLE_SHL_PIK_DELTA_KEUR": max(
            abs(actual - expected["pik_interest_keur"])
            for actual, expected in zip(schedule.shl_pik_interest_keur[1:], source)
        ),
        "MAX_SOURCE_ORACLE_SHL_PRINCIPAL_DELTA_KEUR": max(
            abs(actual - expected["principal_repaid_keur"])
            for actual, expected in zip(schedule.shl_principal_keur[1:], source)
        ),
        "MAX_SOURCE_ORACLE_SHL_CLOSING_DELTA_KEUR": max(
            abs(actual - expected["closing_balance_keur"])
            for actual, expected in zip(schedule.shl_closing_keur[1:], source)
        ),
    }

    assert schedule.shl_opening_keur[0] == pytest.approx(0.0)
    assert schedule.shl_drawdown_keur[0] == pytest.approx(OBOROVO_SHL_DRAW)
    assert schedule.shl_gross_interest_keur[0] == pytest.approx(1169.6619115852516)
    assert schedule.shl_closing_keur[0] == pytest.approx(15790.435806400885)
    assert (
        schedule.shl_opening_keur[0]
        + schedule.shl_drawdown_keur[0]
        + schedule.shl_pik_interest_keur[0]
        - schedule.shl_principal_keur[0]
    ) == pytest.approx(schedule.shl_closing_keur[0])
    assert schedule.shl_opening_keur[1] == pytest.approx(15790.435806400885)
    source_oracle_classification = (
        "SHL_FORMULA_SOURCE_ORACLE_PARITY"
        if max(max_deltas.values()) < 1e-9
        else "SHL_FORMULA_SOURCE_ORACLE_PARITY_FAILED"
    )
    assert source_oracle_classification == "SHL_FORMULA_SOURCE_ORACLE_PARITY"


def test_source_cash_oracle_proves_sweep_not_bullet_and_final_clearance():
    from financial_engine.shl.production import compute_shareholder_loan_schedules

    periods, cash, _ = _oborovo_source_periods_and_cash()
    schedule = compute_shareholder_loan_schedules(
        periods,
        _oborovo_shl_input(),
        cash,
        diagnostics=_diag(),
    )

    first_principal_period = next(
        idx
        for idx, principal in zip(schedule.period_indices, schedule.shl_principal_keur)
        if principal > 1e-6
    )
    assert first_principal_period == 25
    assert schedule.shl_principal_keur[-1] > 0.0
    assert schedule.shl_closing_keur[-1] == pytest.approx(0.0, abs=1e-9)
    assert sum(1 for principal in schedule.shl_principal_keur if principal > 1e-6) > 1


def test_pre_repayment_excess_cash_is_preserved_pre_reserve():
    from financial_engine.inputs import ShareholderLoanModelInput
    from financial_engine.shl.contracts import ShlDayCountConvention
    from financial_engine.shl.production import compute_shareholder_loan_schedules

    periods = (
        _period(0, date(2030, 1, 1), date(2030, 12, 31), construction=True),
        _period(1, date(2031, 1, 1), date(2031, 12, 31), construction=False),
        _period(2, date(2032, 1, 1), date(2032, 12, 30), construction=False),
    )
    raw_cash = (0.0, 1000.0, 1000.0)
    shl_input = ShareholderLoanModelInput(
        initial_principal_keur=10_000.0,
        annual_fixed_rate=0.06,
        day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
        construction_day_count_fraction=1.0,
        repayment_start_period_index=2,
        maturity_period_index=2,
        convergence_tolerance_keur=20_000.0,
        convergence_relative_tolerance=1e-9,
        maximum_iterations=20,
        source_label="pre_repayment_cash_preservation_test",
    )

    schedule = compute_shareholder_loan_schedules(
        periods,
        shl_input,
        raw_cash,
        diagnostics=_diag(),
    )
    pre_gross = schedule.shl_gross_interest_keur[1]
    post_gross = schedule.shl_gross_interest_keur[2]

    assert pre_gross == pytest.approx(636.0)
    assert schedule.cash_available_for_shl_before_reserves_keur[1] == pytest.approx(1000.0)
    assert schedule.shl_cash_interest_keur[1] == pytest.approx(pre_gross)
    assert schedule.shl_principal_keur[1] == pytest.approx(0.0)
    assert schedule.cash_remaining_after_shl_before_reserves_keur[1] == pytest.approx(
        1000.0 - pre_gross
    )

    assert schedule.cash_available_for_shl_before_reserves_keur[2] == pytest.approx(1000.0)
    assert schedule.shl_cash_interest_keur[2] == pytest.approx(post_gross)
    assert schedule.shl_principal_keur[2] > 0.0
    assert schedule.cash_remaining_after_shl_before_reserves_keur[2] == pytest.approx(
        1000.0 - schedule.shl_cash_interest_keur[2] - schedule.shl_principal_keur[2]
    )
    preservation_classification = (
        "PRE_REPAYMENT_EXCESS_CASH_IS_PRESERVED_PRE_RESERVE"
        if schedule.cash_remaining_after_shl_before_reserves_keur[1] > 0.0
        and schedule.shl_principal_keur[1] == pytest.approx(0.0)
        else "PRE_REPAYMENT_EXCESS_CASH_PRESERVATION_FAILED"
    )
    assert preservation_classification == "PRE_REPAYMENT_EXCESS_CASH_IS_PRESERVED_PRE_RESERVE"


def test_shl_fixed_point_result_exposes_immutable_audit_vectors():
    result = _run_oborovo(shl_input=_oborovo_shl_input())
    shl = result.shareholder_loan
    assert shl is not None
    assert dataclasses.is_dataclass(shl)
    assert shl.diagnostics.converged is True
    assert shl.diagnostics.is_authoritative is True
    assert shl.diagnostics.termination_reason == "CONVERGED_FINAL_RECOMPUTE"
    assert shl.diagnostics.max_final_shl_interest_handshake_delta_keur <= 1e-9
    assert shl.diagnostics.max_final_shl_closing_handshake_delta_keur <= 1e-9
    assert len(shl.period_indices) == len(result.periods)
    assert shl.shl_opening_keur[0] == pytest.approx(0.0)
    assert shl.shl_drawdown_keur[0] == pytest.approx(OBOROVO_SHL_DRAW)
    assert shl.shl_gross_interest_keur[0] == pytest.approx(1169.6619115852516)
    assert shl.shl_closing_keur[0] == pytest.approx(15790.435806400885)


def test_shl_service_never_exceeds_pre_reserve_cash_and_remaining_cash_identity():
    result = _run_oborovo(shl_input=_oborovo_shl_input())
    shl = result.shareholder_loan
    for idx, service, cash, remaining in zip(
        shl.period_indices,
        shl.shl_debt_service_keur,
        shl.cash_available_for_shl_before_reserves_keur,
        shl.cash_remaining_after_shl_before_reserves_keur,
    ):
        assert service <= cash + 1e-9, f"period {idx}"
        assert remaining == pytest.approx(max(0.0, cash - service))


def test_shl_gross_interest_enters_tax_and_oborovo_policy_reintegration_chain():
    result = _run_oborovo(shl_input=_oborovo_shl_input())
    shl = result.shareholder_loan
    tac = result.tax_and_cfads
    reint_by_idx = dict(zip(tac.period_indices, tac.fiscal_reintegration_audit_keur))
    for idx, gross in zip(shl.period_indices[:5], shl.shl_gross_interest_keur[:5]):
        assert gross > 0.0
        assert reint_by_idx[idx] == pytest.approx(gross)


def test_tax_policy_controls_deductible_shl_without_double_counting():
    from dataclasses import replace

    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.policies.tax import ShlInterestDeductibilityMode

    no_shl = _run_oborovo(shl_input=None)
    full_non_deductible = _run_oborovo(shl_input=_oborovo_shl_input())
    deductible_model = _oborovo_model(shl_input=_oborovo_shl_input())
    deductible_policy = replace(
        deductible_model.tax.policy,
        shl_interest_tax_treatment_enabled=True,
        shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
        shl_interest_deductible_pct=None,
    )
    deductible = run_senior_debt_model(
        replace(deductible_model, tax=replace(deductible_model.tax, policy=deductible_policy))
    )

    assert full_non_deductible.senior_debt.debt_size_keur == pytest.approx(
        no_shl.senior_debt.debt_size_keur
    )
    assert sum(full_non_deductible.tax_and_cfads.corporate_tax_cash_keur) == pytest.approx(
        sum(no_shl.tax_and_cfads.corporate_tax_cash_keur)
    )
    assert deductible.senior_debt.debt_size_keur != pytest.approx(
        full_non_deductible.senior_debt.debt_size_keur
    )
    assert sum(deductible.tax_and_cfads.corporate_tax_cash_keur) < sum(
        full_non_deductible.tax_and_cfads.corporate_tax_cash_keur
    )
    assert sum(full_non_deductible.tax_and_cfads.fiscal_reintegration_audit_keur) == pytest.approx(
        sum(full_non_deductible.shareholder_loan.shl_gross_interest_keur)
    )
    assert sum(deductible.tax_and_cfads.fiscal_reintegration_audit_keur) == pytest.approx(0.0)


def test_financing_tax_merge_preserves_unoverridden_interest_components():
    from financial_engine.inputs import (
        PeriodInterestInput,
        PeriodTaxAdjustmentInput,
        TaxCalculationInput,
    )
    from financial_engine.orchestrator import _merge_financing_tax_input
    from finco_parity.tax_reference_inputs import build_tax_policy

    base = TaxCalculationInput(
        policy=build_tax_policy("oborovo"),
        opening_loss_vintages=(),
        period_interest=(
            PeriodInterestInput(
                period_index=1,
                senior_interest_keur=10.0,
                shl_interest_keur=20.0,
                other_interest_keur=30.0,
            ),
            PeriodInterestInput(
                period_index=2,
                senior_interest_keur=40.0,
                shl_interest_keur=50.0,
                other_interest_keur=60.0,
            ),
        ),
        period_adjustments=(
            PeriodTaxAdjustmentInput(
                period_index=1,
                other_fiscal_reintegration_keur=70.0,
            ),
        ),
    )

    merged = _merge_financing_tax_input(
        base,
        senior_interest_by_period={1: 11.0},
        shl_interest_by_period={2: 55.0},
    )
    by_period = {pi.period_index: pi for pi in merged.period_interest}

    assert by_period[1].senior_interest_keur == pytest.approx(11.0)
    assert by_period[1].shl_interest_keur == pytest.approx(20.0)
    assert by_period[1].other_interest_keur == pytest.approx(30.0)
    assert by_period[2].senior_interest_keur == pytest.approx(40.0)
    assert by_period[2].shl_interest_keur == pytest.approx(55.0)
    assert by_period[2].other_interest_keur == pytest.approx(60.0)
    assert merged.period_adjustments == base.period_adjustments


def test_project_inputs_wires_oborovo_shl_without_manual_replace():
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )

    project = create_default_oborovo()
    model = build_senior_debt_model_input_from_project_inputs(
        project,
        source_id="production-wiring-check",
    )

    assert model.shareholder_loan is not None
    assert model.shareholder_loan.initial_principal_keur == pytest.approx(
        OBOROVO_SHL_DRAW
    )
    assert project.financing.shl_amount_keur != pytest.approx(OBOROVO_SHL_DRAW)
    assert model.shareholder_loan.annual_fixed_rate == pytest.approx(
        project.financing.shl_rate
    )
    assert model.shareholder_loan.construction_day_count_fraction == pytest.approx(1.0)
    assert model.shareholder_loan.repayment_start_period_index == 25
    assert model.shareholder_loan.maturity_period_index == 40
    assert model.shareholder_loan.source_label == "project_inputs.financing"
    clean_contract_classifications = {
        "principal": "OBOROVO_CLEAN_SHL_PRINCIPAL_AUTHORITY_IS_SOURCE_CORRECT",
        "source_params": "OBOROVO_SHL_CONTRACT_SOURCE_PARAMETERS_PRODUCTION_WIRED",
    }
    assert clean_contract_classifications["principal"].endswith("SOURCE_CORRECT")
    assert clean_contract_classifications["source_params"].endswith("PRODUCTION_WIRED")


def test_clean_shl_adapter_fails_closed_on_unsupported_repayment_method():
    from dataclasses import replace

    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import (
        _build_shareholder_loan_model_input_from_project_inputs,
    )

    periods, _, _ = _oborovo_source_periods_and_cash()
    project = create_default_solar_project()
    project = replace(
        project,
        financing=replace(
            project.financing,
            clean_shl_principal_keur=1000.0,
            clean_shl_repayment_method=None,
            shl_repayment_method="bullet",
            shl_rate=0.08,
            shl_day_count_convention="ACT_365_FIXED",
            shl_construction_day_count_fraction=1.0,
            shl_principal_eligibility_start_period=1,
            shl_maturity_period_index=10,
        ),
    )

    with pytest.raises(ValueError, match="UNSUPPORTED_SHL_REPAYMENT_MODE_FAILS_CLOSED"):
        _build_shareholder_loan_model_input_from_project_inputs(project, periods)


def test_clean_shl_adapter_requires_explicit_construction_dcf_not_idc_backsolve():
    from dataclasses import replace

    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import (
        _build_shareholder_loan_model_input_from_project_inputs,
    )

    periods, _, _ = _oborovo_source_periods_and_cash()
    project = create_default_solar_project()
    project = replace(
        project,
        financing=replace(
            project.financing,
            clean_shl_principal_keur=1000.0,
            clean_shl_repayment_method="partial_pay_sweep",
            shl_rate=0.08,
            shl_idc_keur=80.0,
            shl_day_count_convention="ACT_365_FIXED",
            shl_construction_day_count_fraction=None,
            shl_principal_eligibility_start_period=1,
            shl_maturity_period_index=10,
        ),
    )

    with pytest.raises(
        ValueError,
        match="SHL_CONSTRUCTION_DCF_IS_EXPLICIT_INPUT_NOT_BACKSOLVED_FROM_IDC",
    ):
        _build_shareholder_loan_model_input_from_project_inputs(project, periods)


def test_clean_shl_adapter_fails_closed_when_repayment_start_not_on_period_grid():
    from dataclasses import replace

    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import (
        _build_shareholder_loan_model_input_from_project_inputs,
    )

    periods, _, _ = _oborovo_source_periods_and_cash()
    project = create_default_solar_project()
    project = replace(
        project,
        financing=replace(
            project.financing,
            clean_shl_principal_keur=1000.0,
            clean_shl_repayment_method="partial_pay_sweep",
            shl_rate=0.08,
            shl_day_count_convention="ACT_365_FIXED",
            shl_construction_day_count_fraction=1.0,
            shl_principal_eligibility_start_period=80,
            shl_maturity_period_index=40,
        ),
    )

    with pytest.raises(
        ValueError,
        match="SHL_REPAYMENT_START_NOT_ON_PERIOD_GRID_FAILS_CLOSED",
    ):
        _build_shareholder_loan_model_input_from_project_inputs(project, periods)


def test_clean_shl_adapter_fails_closed_when_maturity_not_on_period_grid():
    from dataclasses import replace

    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import (
        _build_shareholder_loan_model_input_from_project_inputs,
    )

    periods, _, _ = _oborovo_source_periods_and_cash()
    project = create_default_solar_project()
    project = replace(
        project,
        financing=replace(
            project.financing,
            clean_shl_principal_keur=1000.0,
            clean_shl_repayment_method="partial_pay_sweep",
            shl_rate=0.08,
            shl_day_count_convention="ACT_365_FIXED",
            shl_construction_day_count_fraction=1.0,
            shl_principal_eligibility_start_period=25,
            shl_maturity_period_index=80,
        ),
    )

    with pytest.raises(ValueError, match="SHL_MATURITY_NOT_ON_PERIOD_GRID_FAILS_CLOSED"):
        _build_shareholder_loan_model_input_from_project_inputs(project, periods)


def test_clean_shl_adapter_fails_closed_when_maturity_precedes_repayment_start():
    from dataclasses import replace

    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import (
        _build_shareholder_loan_model_input_from_project_inputs,
    )

    periods, _, _ = _oborovo_source_periods_and_cash()
    project = create_default_solar_project()
    project = replace(
        project,
        financing=replace(
            project.financing,
            clean_shl_principal_keur=1000.0,
            clean_shl_repayment_method="partial_pay_sweep",
            shl_rate=0.08,
            shl_day_count_convention="ACT_365_FIXED",
            shl_construction_day_count_fraction=1.0,
            shl_principal_eligibility_start_period=25,
            shl_maturity_period_index=24,
        ),
    )

    with pytest.raises(ValueError, match="maturity_period_index must be >= repayment_start_period_index"):
        _build_shareholder_loan_model_input_from_project_inputs(project, periods)


def test_manual_shl_input_fails_closed_when_boundaries_not_on_period_grid():
    from dataclasses import replace

    from financial_engine.shl.production import compute_shareholder_loan_schedules

    periods, cash, _ = _oborovo_source_periods_and_cash()

    with pytest.raises(ValueError, match="SHL_MATURITY_NOT_ON_PERIOD_GRID_FAILS_CLOSED"):
        compute_shareholder_loan_schedules(
            periods,
            replace(_oborovo_shl_input(), maturity_period_index=80),
            cash,
            diagnostics=_diag(),
        )

    with pytest.raises(
        ValueError,
        match="SHL_REPAYMENT_START_NOT_ON_PERIOD_GRID_FAILS_CLOSED",
    ):
        compute_shareholder_loan_schedules(
            periods,
            replace(_oborovo_shl_input(), repayment_start_period_index=80, maturity_period_index=80),
            cash,
            diagnostics=_diag(),
        )


def test_clean_shl_contract_serialization_roundtrip_and_legacy_defaults():
    from app.project_factories import create_default_oborovo
    from finco_core.inputs.serialization import (
        project_inputs_from_dict,
        project_inputs_to_dict,
    )

    project = create_default_oborovo()
    payload = project_inputs_to_dict(project)
    restored = project_inputs_from_dict(payload)

    fields = (
        "clean_shl_principal_keur",
        "clean_shl_repayment_method",
        "shl_day_count_convention",
        "shl_construction_day_count_fraction",
        "shl_principal_eligibility_start_period",
        "shl_maturity_period_index",
    )
    for field_name in fields:
        assert getattr(restored.financing, field_name) == getattr(project.financing, field_name)

    legacy_payload = project_inputs_to_dict(project)
    for field_name in fields:
        legacy_payload["financing"].pop(field_name)
    legacy_restored = project_inputs_from_dict(legacy_payload)
    for field_name in fields:
        assert getattr(legacy_restored.financing, field_name) is None
    serialization_classification = (
        "CLEAN_SHL_CONTRACT_SERIALIZATION_ROUNDTRIP_PROVEN"
        if all(
            getattr(restored.financing, field_name) == getattr(project.financing, field_name)
            and getattr(legacy_restored.financing, field_name) is None
            for field_name in fields
        )
        else "CLEAN_SHL_CONTRACT_SERIALIZATION_ROUNDTRIP_FAILED"
    )
    assert serialization_classification == "CLEAN_SHL_CONTRACT_SERIALIZATION_ROUNDTRIP_PROVEN"


def test_real_oborovo_production_runtime_shl_acceptance_reports_causal_divergence():
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    project = create_default_oborovo()
    model = build_senior_debt_model_input_from_project_inputs(project)
    result = run_senior_debt_model(model)
    shl = result.shareholder_loan
    assert shl is not None
    source_truth = json.loads((FIXTURES / "excel_oborovo_shl_operating_truth.json").read_text())
    source_periods = source_truth["periods"][:41]

    vectors = {
        "MAX_RUNTIME_SHL_OPENING_DELTA_KEUR": (
            shl.shl_opening_keur,
            "opening_balance_keur",
        ),
        "MAX_RUNTIME_SHL_DRAWDOWN_DELTA_KEUR": (
            shl.shl_drawdown_keur,
            "drawdown_keur",
        ),
        "MAX_RUNTIME_SHL_GROSS_INTEREST_DELTA_KEUR": (
            shl.shl_gross_interest_keur,
            "gross_accrued_interest_keur",
        ),
        "MAX_RUNTIME_SHL_CASH_INTEREST_DELTA_KEUR": (
            shl.shl_cash_interest_keur,
            "cash_interest_keur",
        ),
        "MAX_RUNTIME_SHL_PIK_DELTA_KEUR": (
            shl.shl_pik_interest_keur,
            "pik_interest_keur",
        ),
        "MAX_RUNTIME_SHL_PRINCIPAL_DELTA_KEUR": (
            shl.shl_principal_keur,
            "principal_repaid_keur",
        ),
        "MAX_RUNTIME_SHL_CLOSING_DELTA_KEUR": (
            shl.shl_closing_keur,
            "closing_balance_keur",
        ),
    }
    max_deltas = {
        label: max(
            abs(actual - expected[source_key])
            for actual, expected in zip(actual_values[:41], source_periods)
        )
        for label, (actual_values, source_key) in vectors.items()
    }

    source_cash = json.loads(
        (FIXTURES / "excel_oborovo_financial_truth.json").read_text()
    )["cf"]["free_cash_flow_for_shl_keur"][:41]
    first_cash_divergence = next(
        (
            (idx, actual, expected)
            for idx, (actual, expected) in enumerate(
                zip(shl.cash_available_for_shl_before_reserves_keur[:41], source_cash)
            )
            if abs(actual - expected) > 1e-6
        ),
        None,
    )

    assert model.shareholder_loan.initial_principal_keur == pytest.approx(OBOROVO_SHL_DRAW)
    assert model.shareholder_loan.construction_day_count_fraction == pytest.approx(1.0)
    assert shl.shl_drawdown_keur[0] == pytest.approx(OBOROVO_SHL_DRAW)
    assert shl.shl_gross_interest_keur[0] == pytest.approx(1169.6619115852516)
    assert shl.shl_closing_keur[0] == pytest.approx(15790.435806400885)
    assert shl.diagnostics.max_final_shl_interest_handshake_delta_keur <= 1e-9
    assert shl.diagnostics.max_final_shl_closing_handshake_delta_keur <= 1e-9
    assert max_deltas["MAX_RUNTIME_SHL_DRAWDOWN_DELTA_KEUR"] == pytest.approx(0.0)
    assert max_deltas["MAX_RUNTIME_SHL_OPENING_DELTA_KEUR"] > 1.0
    assert max_deltas["MAX_RUNTIME_SHL_CLOSING_DELTA_KEUR"] > 1.0
    assert first_cash_divergence is not None
    period, runtime_cash, source_cash_value = first_cash_divergence
    assert period == 1
    assert runtime_cash == pytest.approx(0.0)
    assert source_cash_value == pytest.approx(335.8700119281534)
    production_runtime_classification = (
        "SHL_PRODUCTION_RUNTIME_PARITY"
        if max(max_deltas.values()) < 1e-6
        else "SHL_PRODUCTION_RUNTIME_BLOCKED_BY_UPSTREAM_POST_SENIOR_CASH"
    )
    first_divergence = {
        "FIRST_RUNTIME_SHL_CAUSAL_DIVERGENCE_PERIOD": period,
        "FIRST_RUNTIME_SHL_CAUSAL_DIVERGENCE_LINE": (
            "post_senior_cash.cash_available_for_shl_before_reserves_keur"
        ),
        "FIRST_RUNTIME_SHL_CAUSAL_DIVERGENCE_CAUSE": (
            "UPSTREAM_BASE_POST_SENIOR_CASH_DIFFERS_FROM_SOURCE_FREE_CASH_FLOW_FOR_SHL"
        ),
    }
    assert (
        production_runtime_classification
        == "SHL_PRODUCTION_RUNTIME_BLOCKED_BY_UPSTREAM_POST_SENIOR_CASH"
    )
    assert first_divergence["FIRST_RUNTIME_SHL_CAUSAL_DIVERGENCE_PERIOD"] == 1
    assert (
        first_divergence["FIRST_RUNTIME_SHL_CAUSAL_DIVERGENCE_LINE"]
        == "post_senior_cash.cash_available_for_shl_before_reserves_keur"
    )


def test_atad_adapter_plain_path_fails_but_b5_complete_interest_path_builds():
    from dataclasses import replace

    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs

    project = create_default_oborovo()
    atad_project = replace(project, tax=replace(project.tax, atad_enabled=True))

    with pytest.raises(NotImplementedError, match="atad_enabled=True requires complete"):
        build_tax_contract_from_project_inputs(atad_project)

    tax_input = build_tax_contract_from_project_inputs(
        atad_project,
        complete_financing_interest_will_be_injected=True,
    )

    assert tax_input.policy.atad_enabled is True
    assert tax_input.policy.shl_interest_tax_treatment_enabled is True
    assert tax_input.period_interest == ()


def test_shl_production_adapter_reuses_canonical_kernel():
    import inspect

    import financial_engine.shl.production as production

    source = inspect.getsource(production.compute_shareholder_loan_schedules)

    assert "compute_shl_schedule(" in source
    assert "gross = opening" not in source
    assert "opening * shl_input.annual_fixed_rate" not in source
    assert "principal = min(" not in source
    assert "ONE_CANONICAL_SHL_CALCULATION_KERNEL" in source


def test_shl_maturity_residual_fails_closed_without_terminal_top_up():
    from dataclasses import replace

    from financial_engine.senior_debt.models import SeniorDebtNonConvergenceError

    model = _oborovo_model(
        shl_input=replace(
            _oborovo_shl_input(),
            initial_principal_keur=OBOROVO_SHL_DRAW + 1_000.0,
        )
    )
    with pytest.raises(
        (ValueError, SeniorDebtNonConvergenceError),
        match="SHL_MATURITY_RESIDUAL_FAILS_CLOSED",
    ):
        from financial_engine.orchestrator import run_senior_debt_model

        run_senior_debt_model(model)


def test_shl_rate_mutation_changes_gross_interest():
    low = _run_oborovo(
        shl_input=dataclasses.replace(_oborovo_shl_input(), annual_fixed_rate=0.04)
    )
    high = _run_oborovo(
        shl_input=dataclasses.replace(_oborovo_shl_input(), annual_fixed_rate=0.08)
    )
    assert high.shareholder_loan.shl_gross_interest_keur[0] > low.shareholder_loan.shl_gross_interest_keur[0]


def test_shl_principal_mutation_changes_drawdown_and_interest():
    base = _run_oborovo(shl_input=_oborovo_shl_input())
    lower = _run_oborovo(
        shl_input=dataclasses.replace(
            _oborovo_shl_input(),
            initial_principal_keur=OBOROVO_SHL_DRAW - 1000.0,
        )
    )
    assert lower.shareholder_loan.shl_drawdown_keur[0] < base.shareholder_loan.shl_drawdown_keur[0]
    assert lower.shareholder_loan.shl_gross_interest_keur[0] < base.shareholder_loan.shl_gross_interest_keur[0]


def test_available_cash_mutation_changes_principal_sweep_without_formula_patch():
    from financial_engine.shl.production import compute_shareholder_loan_schedules

    periods, cash, _ = _oborovo_source_periods_and_cash()
    base = compute_shareholder_loan_schedules(
        periods,
        _oborovo_shl_input(),
        cash,
        diagnostics=_diag(),
    )
    richer_cash = tuple(c + (500.0 if i == 25 else 0.0) for i, c in enumerate(cash))
    richer = compute_shareholder_loan_schedules(
        periods,
        _oborovo_shl_input(),
        richer_cash,
        diagnostics=_diag(),
    )
    assert richer.shl_principal_keur[25] > base.shl_principal_keur[25]
    assert richer.shl_closing_keur[25] < base.shl_closing_keur[25]


def test_bank_yield_mutation_changes_bank_cfads_and_senior_debt_with_shl_enabled():
    from financial_engine.inputs import YieldScenario

    shl_input = dataclasses.replace(_oborovo_shl_input(), maturity_period_index=61)
    p50 = _run_oborovo(shl_input=shl_input, bank_yield=YieldScenario.P50)
    p90 = _run_oborovo(shl_input=shl_input, bank_yield=YieldScenario.P90_10Y)
    assert p50.debt_sizing.bank_cfads_keur != p90.debt_sizing.bank_cfads_keur
    assert p50.senior_debt.debt_size_keur != pytest.approx(p90.senior_debt.debt_size_keur)


def test_source_label_invariance_for_fingerprint_and_financial_outputs():
    a = _run_oborovo(shl_input=_oborovo_shl_input(source_label="label-a"))
    b = _run_oborovo(shl_input=_oborovo_shl_input(source_label="label-b"))
    assert a.provenance.input_fingerprint == b.provenance.input_fingerprint
    assert a.senior_debt.debt_size_keur == pytest.approx(b.senior_debt.debt_size_keur)
    assert a.shareholder_loan.shl_gross_interest_keur == pytest.approx(
        b.shareholder_loan.shl_gross_interest_keur
    )


def test_tuho_subject_to_limitations_fails_closed_in_clean_fixed_point_path():
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import (
        _build_shareholder_loan_model_input_from_project_inputs,
    )

    periods, _, _ = _oborovo_source_periods_and_cash()
    project = create_default_tuho_wind1()

    with pytest.raises(ValueError, match="CLEAN_SHL_CONTRACT_AUTHORITY_REQUIRED"):
        _build_shareholder_loan_model_input_from_project_inputs(project, periods)

    tuho_adapter_classification = (
        "TUHO_CLEAN_SHL_MAPPING_FAILS_CLOSED_BECAUSE_GENERIC_CONTRACT_FIELDS_ARE_NOT_AUTHORITY"
    )
    assert project.tax.shl_interest_deductibility.value == "subject_to_limitations"
    assert project.financing.shl_amount_keur != pytest.approx(OBOROVO_SHL_DRAW)
    assert tuho_adapter_classification.endswith("NOT_AUTHORITY")


def test_tuho_mechanical_shl_source_fixture_matches_canonical_kernel():
    from financial_engine.inputs import ShareholderLoanModelInput
    from financial_engine.shl.contracts import ShlDayCountConvention
    from financial_engine.shl.production import compute_shareholder_loan_schedules

    data = json.loads((FIXTURES / "excel_tuho_full_model_extract.json").read_text())
    rows = data["shl"]
    construction_draw = -rows[0][4]
    annual_rate = 0.08
    construction_dcf = rows[0][3] / (construction_draw * annual_rate)
    first_zero_closing_index = next(
        i for i, row in enumerate(rows) if i > 0 and abs(row[2]) < 1e-9
    )

    periods = [
        _period(
            0,
            date(2029, 1, 1),
            _parse_date(rows[0][0]),
            construction=True,
        )
    ]
    previous_end = _parse_date(rows[0][0])
    for idx, row in enumerate(rows[1:], start=1):
        period_end = _parse_date(row[0])
        periods.append(
            _period(
                idx,
                previous_end + timedelta(days=1),
                period_end,
                construction=False,
            )
        )
        previous_end = period_end

    cash_available = (0.0,) + tuple(
        row[5] + max(0.0, row[4])
        for row in rows[1:]
    )
    schedule = compute_shareholder_loan_schedules(
        tuple(periods),
        ShareholderLoanModelInput(
            initial_principal_keur=construction_draw,
            annual_fixed_rate=annual_rate,
            day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
            construction_day_count_fraction=construction_dcf,
            repayment_start_period_index=1,
            maturity_period_index=first_zero_closing_index,
            convergence_tolerance_keur=1e-4,
            convergence_relative_tolerance=1e-9,
            maximum_iterations=20,
            source_label="tuho_source_fixture_mechanical_validation",
        ),
        cash_available,
        diagnostics=_diag(),
    )

    expected_principal = tuple(
        0.0 if i == 0 else max(0.0, row[4])
        for i, row in enumerate(rows)
    )
    vectors = {
        "opening": (schedule.shl_opening_keur, tuple(row[1] for row in rows)),
        "closing": (schedule.shl_closing_keur, tuple(row[2] for row in rows)),
        "gross": (schedule.shl_gross_interest_keur, tuple(row[3] for row in rows)),
        "principal": (schedule.shl_principal_keur, expected_principal),
        "cash_interest": (schedule.shl_cash_interest_keur, tuple(row[5] for row in rows)),
        "pik": (schedule.shl_pik_interest_keur, tuple(row[6] for row in rows)),
    }

    assert schedule.shl_drawdown_keur[0] == pytest.approx(construction_draw)
    assert all(draw == pytest.approx(0.0) for draw in schedule.shl_drawdown_keur[1:])
    for actual, expected in vectors.values():
        assert max(abs(a - e) for a, e in zip(actual, expected)) < 1e-9


def test_shl_fixed_point_fails_closed_on_non_convergence():
    from dataclasses import replace
    from financial_engine.senior_debt.models import SeniorDebtNonConvergenceError

    model = _oborovo_model(
        shl_input=replace(_oborovo_shl_input(), maximum_iterations=1)
    )
    with pytest.raises(SeniorDebtNonConvergenceError, match="MAX_ITERATIONS_REACHED"):
        from financial_engine.orchestrator import run_senior_debt_model

        run_senior_debt_model(model)


def test_governance_no_identity_dispatch_or_calibration_terms_in_b5_runtime_files():
    files = [
        "financial_engine/orchestrator.py",
        "financial_engine/shl/production.py",
        "financial_engine/inputs.py",
        "financial_engine/results.py",
    ]
    forbidden = (
        "approved_delta",
        "expected_delta",
        "balancing plug",
        "target-derived runtime inputs",
        "output-profile replay",
        "project.name",
        "project.code",
        "baseline_id",
    )
    root = Path(__file__).parent.parent
    for rel_path in files:
        source = (root / rel_path).read_text().lower()
        for token in forbidden:
            assert token not in source


def test_clean_shl_governance_rejects_backsolved_dcf_identity_dispatch_and_plugs():
    import inspect

    from financial_engine.adapters import project_inputs

    adapter_source = inspect.getsource(
        project_inputs._build_shareholder_loan_model_input_from_project_inputs
    )
    all_source = "\n".join(
        (Path(__file__).parent.parent / rel).read_text(encoding="utf-8").lower()
        for rel in (
            "financial_engine/adapters/project_inputs.py",
            "financial_engine/orchestrator.py",
            "financial_engine/shl/production.py",
        )
    )

    assert "shl_idc_keur" not in adapter_source
    assert "tuho_shl_principal_eligibility_start_period" not in adapter_source
    assert "maturity_period_index=last_period" not in adapter_source
    for token in (
        "approved_delta",
        "expected_delta",
        "balancing plug",
        "target fitting",
        "source schedule replay",
        "terminal top-up",
        "forced principal",
        "project.name",
        "project.code",
    ):
        assert token not in all_source
