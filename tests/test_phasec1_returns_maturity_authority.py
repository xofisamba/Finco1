"""Phase C1 decision-complete returns and maturity acceptance."""

from __future__ import annotations

import dataclasses
import inspect
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.project_factories import (
    create_default_oborovo,
    create_default_solar_project,
    create_default_tuho_wind1,
    create_default_wind_project,
)
from app.services.production_financial_authority import run_clean_production
from financial_engine.project_returns.contracts import (
    CashAccountTerminalStatus,
    DebtTerminalStatus,
    ProjectReturnStatus,
    ShlTerminalStatus,
)
from financial_engine.project_returns.model import (
    _project_return,
    _senior_terminal_state,
    _shl_terminal_state,
)
from financial_engine.sponsor_returns.contracts import ReturnMetricStatus


PROJECTS = {
    "Solar": create_default_solar_project,
    "Wind": create_default_wind_project,
    "Oborovo": create_default_oborovo,
    "TUHO": create_default_tuho_wind1,
}

EXPECTED_PROJECT_XIRR = {
    "Solar": 0.07593168077588568,
    "Wind": 0.11366132007429408,
    "Oborovo": 0.08512246818013307,
    "TUHO": 0.09477998283668464,
}


def _run(inputs, project_type="Solar"):
    return run_clean_production(inputs, project_type=project_type).g2c_result


@pytest.fixture(scope="module")
def supported_results():
    return {name: _run(factory(), name) for name, factory in PROJECTS.items()}


def _scale_capex(capex, factor):
    return replace(
        capex,
        **{
            field: replace(
                getattr(capex, field),
                amount_keur=getattr(capex, field).amount_keur * factor,
            )
            for field in capex._CAPEX_ITEM_FIELDS
        },
    )


def _scale_opex(opex, factor):
    return tuple(replace(item, y1_amount_keur=item.y1_amount_keur * factor) for item in opex)


@pytest.mark.parametrize("project_type", tuple(PROJECTS))
def test_c1_supported_projects_have_project_return_authority(
    supported_results, project_type
):
    result = supported_results[project_type]
    project = result.return_summary.project
    assert project.project_xirr_status is ProjectReturnStatus.OK
    assert project.project_xirr is not None
    assert project.project_xirr > 0.0
    assert project.project_xirr == pytest.approx(
        EXPECTED_PROJECT_XIRR[project_type], abs=1e-12
    )
    assert project.methodology_authority == (
        "C1_UNLEVERED_HARD_CAPEX_PLUS_EBITDA_MINUS_ZERO_FINANCING_INTEREST_CASH_TAX"
    )
    assert result.deductible_shl_covenant_feedback_status is None
    assert result.return_summary.deductible_shl_covenant_feedback_status is None
    assert project.terminal_unpaid_project_tax_keur == pytest.approx(0.0)
    assert project.other_explicit_project_uses_keur == pytest.approx(0.0)
    assert project.hard_capex_timing_authority in {
        "TYPED_CONSTRUCTION_FINANCING_HARD_CAPEX_VECTOR",
        "CANONICAL_HARD_CAPEX_ONLY_CONSTRUCTION_FUNDING_VECTOR",
    }


@pytest.mark.parametrize("project_type", tuple(PROJECTS))
def test_c1_project_cashflow_bridge_is_complete_and_date_unique(
    supported_results, project_type
):
    result = supported_results[project_type]
    project = result.return_summary.project
    dates = [row.cashflow_date for row in project.cashflows]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))
    assert project.total_hard_capex_investment_keur == pytest.approx(
        result.financing_result.project_uses.hard_project_capex_keur
    )
    for row in project.cashflows:
        assert row.net_unlevered_project_cashflow_keur == pytest.approx(
            row.project_operating_inflow_keur
            - row.project_tax_outflow_keur
            + row.terminal_component_keur
            - row.project_investment_outflow_keur
        )
    assert project.terminal_component_keur == 0.0


@pytest.mark.parametrize("project_type", ("Oborovo", "TUHO"))
def test_c1_financing_uses_are_explicitly_excluded_from_project_return(
    supported_results, project_type
):
    result = supported_results[project_type]
    project = result.return_summary.project
    uses = result.financing_result.project_uses
    assert uses.explicit_financing_cost_uses_keur > 0.0
    assert project.excluded_financing_cost_uses_keur == pytest.approx(
        uses.explicit_financing_cost_uses_keur
    )
    assert project.total_hard_capex_investment_keur < uses.total_project_uses_keur


@pytest.mark.parametrize("project_type", tuple(PROJECTS))
def test_c1_existing_legal_equity_and_total_sponsor_authorities_are_reused(
    supported_results, project_type
):
    result = supported_results[project_type]
    legal = result.return_summary.legal_equity
    sponsor = result.return_summary.total_sponsor
    assert legal.xirr == result.pure_equity_xirr
    assert legal.xirr_status is result.pure_equity_xirr_status
    assert legal.moic == result.pure_equity_moic
    assert legal.moic_status is result.pure_equity_moic_status
    assert sponsor.xirr == result.total_sponsor_xirr
    assert sponsor.xirr_status is result.total_sponsor_xirr_status
    assert sponsor.moic == result.total_sponsor_moic
    assert sponsor.moic_status is result.total_sponsor_moic_status
    assert legal.net_cashflow_keur == pytest.approx(
        legal.total_receipts_keur - legal.total_contributions_keur
    )
    assert sponsor.net_cashflow_keur == pytest.approx(
        sponsor.total_receipts_keur - sponsor.total_contributions_keur
    )
    assert sum(p.pure_equity_net_cashflow_keur for p in result.waterfall_periods) == pytest.approx(
        legal.net_cashflow_keur
    )
    assert sum(p.total_sponsor_net_cashflow_keur for p in result.waterfall_periods) == pytest.approx(
        sponsor.net_cashflow_keur
    )


@pytest.mark.parametrize("project_type", tuple(PROJECTS))
def test_c1_terminal_state_reconciles_to_canonical_schedules(
    supported_results, project_type
):
    result = supported_results[project_type]
    terminal = result.return_summary.terminal
    model = result.financing_result.project_model_result
    assert terminal.senior.terminal_balance_keur == pytest.approx(
        model.senior_debt.senior_debt_closing_keur[-1]
    )
    assert terminal.senior.balance_at_contractual_maturity_keur == pytest.approx(
        model.senior_debt.senior_debt_closing_keur[-1]
    )
    assert terminal.senior.terminal_model_horizon_balance_keur == pytest.approx(
        model.senior_debt.senior_debt_closing_keur[-1]
    )
    assert terminal.senior.status is DebtTerminalStatus.REPAID
    assert terminal.shareholder_loan.terminal_balance_keur == pytest.approx(
        result.waterfall_periods[-1].shl_closing_balance_keur
    )
    assert (
        terminal.shareholder_loan.terminal_model_horizon_balance_keur
        == pytest.approx(result.waterfall_periods[-1].shl_closing_balance_keur)
    )
    assert terminal.distribution_account.terminal_closing_balance_keur == pytest.approx(
        result.waterfall_periods[-1].distribution_account_closing_keur
    )
    if model.cash_dsra is not None:
        assert terminal.senior_dsra.terminal_closing_balance_keur == pytest.approx(
            model.cash_dsra.final_closing_balance_keur
        )
    if model.cash_dsra is None or str(
        getattr(model.cash_dsra.mode, "value", model.cash_dsra.mode)
    ) != "CASH_DSRA":
        assert terminal.senior_dsra.status is CashAccountTerminalStatus.NOT_APPLICABLE


@pytest.mark.parametrize("project_type", ("Solar", "Wind"))
def test_c1_unpaid_bullet_is_visible_and_no_terminal_cash_is_invented(
    supported_results, project_type
):
    result = supported_results[project_type]
    shl = result.return_summary.terminal.shareholder_loan
    assert shl.repayment_mode == "BULLET"
    assert shl.status is ShlTerminalStatus.UNPAID_AT_CONTRACTUAL_MATURITY
    assert shl.contractual_amount_due_at_maturity_keur == pytest.approx(
        shl.amount_paid_at_maturity_keur + shl.unpaid_at_maturity_keur
    )
    assert shl.unpaid_at_maturity_keur == pytest.approx(shl.terminal_balance_keur)
    assert shl.contractual_outstanding_at_maturity_keur == pytest.approx(
        shl.amount_paid_at_maturity_keur + shl.unpaid_at_maturity_keur
    )
    assert shl.unpaid_at_maturity_keur > 0.0
    assert result.return_summary.legal_equity.xirr_status is (
        ReturnMetricStatus.UNPAID_SHL_AT_CONTRACTUAL_MATURITY
    )
    assert result.return_summary.total_sponsor.xirr_status is (
        ReturnMetricStatus.UNPAID_SHL_AT_CONTRACTUAL_MATURITY
    )
    maturity = shl.contractual_maturity_period_index
    assert not any(
        period.legal_equity_distribution_keur > 1e-9
        for period in result.waterfall_periods
        if not period.is_construction and period.period_index > maturity
    )


def test_c1_project_economics_sensitivities_are_causal():
    base_inputs = create_default_solar_project()
    base = _run(base_inputs).return_summary.project.project_xirr
    higher_revenue = _run(replace(
        base_inputs,
        revenue=replace(
            base_inputs.revenue,
            ppa_base_tariff=base_inputs.revenue.ppa_base_tariff * 1.10,
        ),
    )).return_summary.project.project_xirr
    higher_capex = _run(replace(
        base_inputs,
        capex=_scale_capex(base_inputs.capex, 1.10),
    )).return_summary.project.project_xirr
    higher_opex = _run(replace(
        base_inputs,
        opex=_scale_opex(base_inputs.opex, 1.10),
    )).return_summary.project.project_xirr
    higher_tax = _run(replace(
        base_inputs,
        tax=replace(
            base_inputs.tax,
            corporate_rate=base_inputs.tax.corporate_rate + 0.10,
        ),
    )).return_summary.project.project_xirr
    assert higher_revenue > base
    assert higher_capex < base
    assert higher_opex < base
    assert higher_tax < base


@pytest.mark.parametrize(
    "project_type,factory,financing_change",
    (
        ("Solar", create_default_solar_project, {"gearing_ratio": 0.60}),
        ("Solar", create_default_solar_project, {"margin_bps": 450}),
        ("Solar", create_default_solar_project, {"shl_rate": 0.06}),
        ("Oborovo", create_default_oborovo, {"margin_bps": 550}),
        ("Oborovo", create_default_oborovo, {"shl_rate": 0.045}),
        ("TUHO", create_default_tuho_wind1, {"gearing_ratio": 0.68}),
        ("TUHO", create_default_tuho_wind1, {"margin_bps": 450}),
        ("TUHO", create_default_tuho_wind1, {"shl_rate": 0.045}),
    ),
)
def test_c1_project_xirr_and_tax_are_financing_invariant(
    project_type, factory, financing_change
):
    base_inputs = factory()
    changed_inputs = replace(
        base_inputs,
        financing=replace(base_inputs.financing, **financing_change),
    )
    base = _run(base_inputs, project_type).return_summary.project
    changed = _run(changed_inputs, project_type).return_summary.project
    assert changed.project_xirr == pytest.approx(base.project_xirr, abs=1e-12)
    assert changed.total_project_tax_outflow_keur == pytest.approx(
        base.total_project_tax_outflow_keur, abs=1e-9
    )


def test_c1_tax_adapter_uses_truthful_zero_financing_interest_context():
    from financial_engine.adapters.tax_inputs import (
        FinancingInterestContext,
        build_tax_contract_from_project_inputs,
    )

    contract = build_tax_contract_from_project_inputs(
        create_default_solar_project(),
        financing_interest_context=(
            FinancingInterestContext.UNLEVERED_ZERO_FINANCING_INTEREST
        ),
    )
    assert contract.period_interest == ()
    assert not contract.policy.shl_interest_tax_treatment_enabled
    source = inspect.getsource(_project_return)
    helper_source = inspect.getsource(
        __import__(
            "financial_engine.project_returns.model", fromlist=["_unlevered_cash_tax_by_period"]
        )._unlevered_cash_tax_by_period
    )
    assert "complete_financing_interest_will_be_injected=True" not in helper_source
    assert "UNLEVERED_ZERO_FINANCING_INTEREST" in helper_source
    assert "calculate_tax" not in source


def test_c1_unlevered_atad_has_no_interest_deduction_from_zero_interest():
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.adapters.tax_inputs import (
        FinancingInterestContext,
        build_tax_contract_from_project_inputs,
    )
    from financial_engine.orchestrator import run_operating_model
    from financial_engine.tax.engine import calculate_tax

    base = create_default_solar_project()
    inputs = replace(
        base,
        tax=replace(base.tax, atad_enabled=True, thin_cap_enabled=False),
    )
    contract = build_tax_contract_from_project_inputs(
        inputs,
        financing_interest_context=(
            FinancingInterestContext.UNLEVERED_ZERO_FINANCING_INTEREST
        ),
    )
    periods = run_operating_model(from_project_inputs(inputs)).periods
    result = calculate_tax(periods, contract)
    assert contract.period_interest == ()
    assert all(
        period.deductible_interest_keur == pytest.approx(0.0)
        and period.disallowed_interest_keur == pytest.approx(0.0)
        for period in result.period_results
    )


def test_c1_tax_interest_context_preserves_legacy_complete_injection_selector():
    from financial_engine.adapters.tax_inputs import (
        FinancingInterestContext,
        build_tax_contract_from_project_inputs,
    )

    inputs = create_default_solar_project()
    legacy = build_tax_contract_from_project_inputs(
        inputs, complete_financing_interest_will_be_injected=True
    )
    typed = build_tax_contract_from_project_inputs(
        inputs,
        financing_interest_context=(
            FinancingInterestContext.COMPLETE_FINANCING_INTEREST_WILL_BE_INJECTED
        ),
    )
    assert legacy == typed
    assert legacy.policy.shl_interest_tax_treatment_enabled
    with pytest.raises(ValueError, match="FINANCING_INTEREST_CONTEXT_CONFLICT"):
        build_tax_contract_from_project_inputs(
            inputs,
            complete_financing_interest_will_be_injected=True,
            financing_interest_context=(
                FinancingInterestContext.UNLEVERED_ZERO_FINANCING_INTEREST
            ),
        )


def test_c1_senior_status_uses_contractual_maturity_not_model_end():
    result = _run(create_default_solar_project()).return_summary
    periods = _run(create_default_solar_project()).waterfall_periods
    operation_indices = [p.period_index for p in periods if not p.is_construction]
    maturity = operation_indices[1]
    horizon = operation_indices[2]
    senior = SimpleNamespace(
        debt_size_keur=1_000.0,
        period_indices=(operation_indices[0], maturity, horizon),
        senior_debt_closing_keur=(800.0, 100.0, 0.0),
    )
    model = SimpleNamespace(
        senior_debt=senior,
        axis_contract=SimpleNamespace(
            senior_axis=(operation_indices[0], maturity)
        ),
    )

    state = _senior_terminal_state(model, periods)
    assert result.project.project_xirr_status is ProjectReturnStatus.OK
    assert state.balance_at_contractual_maturity_keur == pytest.approx(100.0)
    assert state.terminal_model_horizon_balance_keur == pytest.approx(0.0)
    assert state.status is DebtTerminalStatus.OUTSTANDING_AT_MATURITY


def test_c1_underfunded_cash_sweep_maturity_is_truthful_without_top_up(
    supported_results,
):
    source = supported_results["Solar"]
    operation_rows = [p for p in source.waterfall_periods if not p.is_construction]
    maturity_source = operation_rows[2]
    maturity = replace(
        maturity_source,
        shl_opening_balance_keur=1_000.0,
        shl_pik_keur=50.0,
        contractual_shl_principal_due_keur=100.0,
        actual_shl_principal_paid_keur=100.0,
        unpaid_shl_principal_keur=0.0,
        actual_shl_closing_balance_keur=950.0,
        shl_principal_receipt_keur=100.0,
        shl_closing_balance_keur=950.0,
        legal_equity_distribution_keur=0.0,
    )
    horizon = replace(
        operation_rows[3],
        shl_opening_balance_keur=950.0,
        shl_gross_interest_keur=0.0,
        shl_cash_interest_receipt_keur=0.0,
        shl_pik_keur=0.0,
        contractual_shl_principal_due_keur=0.0,
        actual_shl_principal_paid_keur=0.0,
        unpaid_shl_principal_keur=0.0,
        actual_shl_closing_balance_keur=950.0,
        shl_principal_receipt_keur=0.0,
        shl_closing_balance_keur=950.0,
        legal_equity_distribution_keur=0.0,
    )
    state = _shl_terminal_state(
        SimpleNamespace(initial_principal_keur=1_000.0),
        (maturity, horizon),
        shl_repayment_mode="CASH_SWEEP",
        shl_maturity_period_index=maturity.period_index,
    )
    assert state.contractual_outstanding_at_maturity_keur == pytest.approx(1_050.0)
    assert state.contractual_amount_due_at_maturity_keur == pytest.approx(1_050.0)
    assert state.amount_paid_at_maturity_keur == pytest.approx(100.0)
    assert state.unpaid_at_maturity_keur == pytest.approx(950.0)
    assert state.contractual_amount_due_at_maturity_keur == pytest.approx(
        state.amount_paid_at_maturity_keur + state.unpaid_at_maturity_keur
    )
    assert state.balance_at_contractual_maturity_keur == pytest.approx(950.0)
    assert state.terminal_model_horizon_balance_keur == pytest.approx(950.0)
    assert state.status is ShlTerminalStatus.UNPAID_AT_CONTRACTUAL_MATURITY
    assert maturity.legal_equity_distribution_keur == 0.0
    assert horizon.shl_gross_interest_keur == 0.0
    assert horizon.actual_shl_principal_paid_keur == 0.0
    assert horizon.legal_equity_distribution_keur == 0.0


def test_c1_missing_authoritative_hard_capex_timing_fails_closed():
    inputs = create_default_solar_project()
    financing = _run(inputs).financing_result
    funding = financing.construction_funding
    periods = list(funding.periods)
    periods[0] = replace(
        periods[0], project_cash_uses_keur=periods[0].project_cash_uses_keur + 1.0
    )
    invalid = replace(
        financing,
        construction_financing=None,
        construction_funding=replace(funding, periods=tuple(periods)),
    )
    project = _project_return(inputs, invalid)
    assert project.project_xirr is None
    assert project.project_xirr_status is ProjectReturnStatus.HARD_CAPEX_TIMING_UNAVAILABLE
    assert project.cashflows == ()
    assert project.hard_capex_timing_authority is None


def test_c1_terminal_unpaid_project_tax_fails_closed(monkeypatch):
    from financial_engine.project_returns import model

    inputs = create_default_solar_project()
    financing = _run(inputs).financing_result
    monkeypatch.setattr(
        model,
        "_unlevered_cash_tax_by_period",
        lambda *_args: ({}, 123.45),
    )
    project = model._project_return(inputs, financing)
    assert project.project_xirr is None
    assert project.project_xirr_status is (
        ProjectReturnStatus.TERMINAL_PROJECT_TAX_OUTSIDE_HORIZON
    )
    assert project.terminal_unpaid_project_tax_keur == pytest.approx(123.45)
    assert project.terminal_component_keur == 0.0


def test_c1_unclassified_other_project_use_fails_closed():
    inputs = create_default_solar_project()
    financing = _run(inputs).financing_result
    uses = financing.project_uses
    invalid = replace(
        financing,
        project_uses=replace(
            uses,
            other_explicit_project_uses_keur=1.0,
            total_project_uses_keur=uses.total_project_uses_keur + 1.0,
        ),
    )
    project = _project_return(inputs, invalid)
    assert project.project_xirr is None
    assert project.project_xirr_status is ProjectReturnStatus.UNCLASSIFIED_OTHER_PROJECT_USE
    assert project.other_explicit_project_uses_keur == pytest.approx(1.0)
    assert project.cashflows == ()


def test_c1_project_identity_is_financially_invariant():
    base_inputs = create_default_solar_project()
    renamed = replace(
        base_inputs,
        info=replace(base_inputs.info, name="Renamed", company="Other", code="X-1"),
    )
    assert _run(renamed).return_summary == _run(base_inputs).return_summary


def test_c1_production_serialization_is_json_safe_and_pass_through_only():
    from app.api.project_runner import run_project
    from app.services import clean_presentation_adapter as adapter

    payload = run_project("Oborovo", "Base")
    summary = payload["runtime_authority"]["return_summary"]
    assert payload["kpis"]["project_irr"] == summary["project"]["project_xirr"]
    assert summary["project"]["project_xirr_status"] == "OK"
    assert summary["terminal"]["senior"]["status"] == "REPAID"
    json.dumps(payload["runtime_authority"])
    source = inspect.getsource(adapter)
    assert "robust_xirr(" not in source
    assert "calculate_tax(" not in source


def test_c1_status_contract_is_typed_and_complete():
    required = {
        "OK",
        "NO_NEGATIVE_CASHFLOW",
        "NO_POSITIVE_CASHFLOW",
        "ZERO_CONTRIBUTION",
        "NON_CONVERGENT",
        "UNDEFINED",
        "UNPAID_SHL_AT_CONTRACTUAL_MATURITY",
        "UPSTREAM_FINANCIAL_FEEDBACK_NOT_CLOSED",
    }
    assert required <= {status.value for status in ReturnMetricStatus}
    assert {
        "OK",
        "PROJECT_RETURN_HARD_CAPEX_TIMING_UNAVAILABLE",
        "TERMINAL_PROJECT_TAX_PAYMENT_OUTSIDE_MODEL_HORIZON",
        "UNCLASSIFIED_OTHER_PROJECT_USE",
    } <= {status.value for status in ProjectReturnStatus}


def test_c1_governance_has_no_replay_fitting_plug_or_identity_dispatch():
    from financial_engine.project_returns import model

    source = inspect.getsource(model).lower()
    forbidden = (
        "approved_delta",
        "expected_delta",
        "target fitting",
        "workbook output vector",
        "terminal top-up",
        "project.name",
        "project.code",
        "baseline_id",
    )
    assert not [token for token in forbidden if token in source]
    assert "terminal_component_keur=0.0" in source
