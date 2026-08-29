"""Phase C2 Project NPV and lender-coverage authority acceptance."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
import inspect
from types import SimpleNamespace

import pytest

from app.project_factories import (
    _generic_clean_senior_interest_config,
    create_default_oborovo,
    create_default_solar_project,
    create_default_tuho_wind1,
    create_default_wind_project,
)
from app.services.production_financial_authority import run_clean_production
from finco_core.inputs import (
    hash_inputs_for_cache,
    project_inputs_from_dict,
    project_inputs_to_dict,
)
from finco_core.inputs.valuation import (
    CoverageCalculationDatePolicy,
    CoverageCfadsCase,
    DebtCoverageValuationPolicy,
    DiscountConvention,
    ProjectValuationPolicy,
    ValuationDatePolicy,
    ValuationPolicies,
)
from financial_engine.project_returns.contracts import (
    ProjectReturnCashFlow,
    ProjectReturnResult,
    ProjectReturnStatus,
)
from financial_engine.results import (
    DebtSizingSchedules,
    OperatingPeriodResult,
    SeniorDebtSchedules,
    TaxAndCfadsSchedules,
)
from financial_engine.valuation.contracts import (
    CoverageStatus,
    LlcrThresholdStatus,
    ProjectNpvStatus,
)
from financial_engine.valuation.model import (
    calculate_lender_coverage,
    calculate_project_npv,
)


def _project_return(amounts=(-100.0, 60.0, 70.0), *, status=ProjectReturnStatus.OK):
    rows = tuple(
        ProjectReturnCashFlow(
            cashflow_date=date(2030 + index, 1, 1),
            project_investment_outflow_keur=max(0.0, -amount),
            project_operating_inflow_keur=max(0.0, amount),
            project_tax_outflow_keur=0.0,
            terminal_component_keur=0.0,
            net_unlevered_project_cashflow_keur=amount,
        )
        for index, amount in enumerate(amounts)
    )
    return ProjectReturnResult(
        cashflows=rows,
        project_xirr=0.1 if status is ProjectReturnStatus.OK else None,
        project_xirr_status=status,
        total_hard_capex_investment_keur=100.0,
        excluded_financing_cost_uses_keur=0.0,
        excluded_reserve_funding_keur=0.0,
        other_explicit_project_uses_keur=0.0,
        total_operating_inflow_keur=130.0,
        total_project_tax_outflow_keur=0.0,
        terminal_unpaid_project_tax_keur=0.0,
        terminal_component_keur=0.0,
        hard_capex_timing_authority="TEST_TYPED_CAPEX",
        methodology_authority="C1_TEST_AUTHORITY",
    )


def _project_policy(rate=0.08, *, explicit_date=None):
    return ProjectValuationPolicy(
        annual_discount_rate=rate,
        valuation_date_policy=(
            ValuationDatePolicy.EXPLICIT_DATE
            if explicit_date is not None
            else ValuationDatePolicy.FIRST_PROJECT_CASHFLOW_DATE
        ),
        explicit_valuation_date=explicit_date,
        discount_convention=DiscountConvention.ACT_365_FIXED,
        authority_label="TEST_EXPLICIT_PROJECT_RATE",
    )


def _period(index):
    return OperatingPeriodResult(
        period_index=index,
        period_start=date(2030 + index - 1, 1, 1),
        period_end=date(2030 + index, 1, 1),
        year_index=float(index),
        period_in_year=1.0,
        is_construction=False,
        is_operation=True,
        is_ppa_active=True,
        days_in_period=365,
        day_fraction=1.0,
        production_mwh=0.0,
        revenue_keur=0.0,
        opex_keur=0.0,
        ebitda_keur=0.0,
        book_depreciation_keur=0.0,
        tax_depreciation_keur=0.0,
        ebit_keur=0.0,
    )


def _tax_cfads(values):
    zeros = tuple(0.0 for _ in values)
    return TaxAndCfadsSchedules(
        period_indices=(1, 2, 3, 4),
        taxable_profit_keur=zeros,
        taxable_income_before_losses_audit_keur=zeros,
        taxable_profit_after_losses_audit_keur=zeros,
        tax_keur=zeros,
        corporate_tax_cash_keur=zeros,
        cit_accrual_audit_keur=zeros,
        cash_tax_bridge_reconciliation_keur=zeros,
        cash_tax_current_period_audit_keur=zeros,
        tax_loss_opening_audit_keur=zeros,
        tax_loss_closing_audit_keur=zeros,
        tax_loss_used_audit_keur=zeros,
        fiscal_reintegration_audit_keur=zeros,
        tax_depreciation_audit_keur=zeros,
        cf_after_tax_keur=tuple(values),
        cfads_keur=tuple(values),
        terminal_unpaid_tax_keur=0.0,
    )


def _coverage_model(base=(100.0, 100.0, 100.0, 100.0), bank=(80.0, 80.0, 80.0, 80.0)):
    senior = SeniorDebtSchedules(
        period_indices=(1, 2),
        senior_debt_opening_keur=(150.0, 75.0),
        senior_interest_keur=(0.0, 0.0),
        senior_principal_keur=(75.0, 75.0),
        senior_debt_service_keur=(75.0, 75.0),
        senior_debt_closing_keur=(75.0, 0.0),
        base_dscr=(None, None),
        debt_size_keur=150.0,
        binding_constraint="DSCR",
        diagnostics={},
    )
    bank_schedule = DebtSizingSchedules(
        period_indices=(1, 2, 3, 4),
        bank_production_mwh=(0.0,) * 4,
        bank_revenue_keur=(0.0,) * 4,
        bank_opex_keur=(0.0,) * 4,
        bank_ebitda_keur=tuple(bank),
        bank_cash_tax_keur=(0.0,) * 4,
        bank_cfads_keur=tuple(bank),
        bank_sizing_dscr=(None,) * 4,
        solver_bank_dscr=(None,) * 4,
    )
    return SimpleNamespace(
        periods=tuple(_period(index) for index in range(1, 5)),
        senior_debt=senior,
        tax_and_cfads=_tax_cfads(base),
        debt_sizing=bank_schedule,
    )


def _coverage_policy(case=CoverageCfadsCase.BASE, rate=0.05):
    return DebtCoverageValuationPolicy(
        annual_discount_rate=rate,
        cfads_case=case,
        calculation_date_policy=(
            CoverageCalculationDatePolicy.FIRST_SENIOR_PERIOD_OPENING
        ),
        discount_convention=DiscountConvention.ACT_365_FIXED,
        authority_label="TEST_EXPLICIT_COVERAGE_RATE_AND_CASE",
    )


def _terminal(maturity=2):
    return SimpleNamespace(contractual_maturity_period_index=maturity)


def test_project_npv_uses_exact_c1_cashflow_vector_and_full_pv_audit():
    project = _project_return()
    result = calculate_project_npv(project, _project_policy())
    assert result.status is ProjectNpvStatus.OK
    assert tuple(row.undiscounted_cashflow_keur for row in result.periods) == tuple(
        row.net_unlevered_project_cashflow_keur for row in project.cashflows
    )
    assert result.npv_keur == pytest.approx(
        sum(row.discounted_cashflow_keur for row in result.periods), abs=1e-12
    )
    assert result.cashflow_identity_authority == "C1_PROJECT_RETURN_RESULT_CASHFLOWS_EXACT"


def test_project_npv_rate_and_economics_sensitivities_are_causal():
    base = calculate_project_npv(_project_return(), _project_policy(0.05)).npv_keur
    high_rate = calculate_project_npv(_project_return(), _project_policy(0.15)).npv_keur
    high_revenue = calculate_project_npv(
        _project_return((-100.0, 70.0, 80.0)), _project_policy(0.05)
    ).npv_keur
    high_capex = calculate_project_npv(
        _project_return((-120.0, 60.0, 70.0)), _project_policy(0.05)
    ).npv_keur
    high_opex_or_tax = calculate_project_npv(
        _project_return((-100.0, 50.0, 60.0)), _project_policy(0.05)
    ).npv_keur
    assert high_rate < base
    assert high_revenue > base
    assert high_capex < base
    assert high_opex_or_tax < base


def test_project_npv_fails_closed_for_missing_invalid_and_upstream_inputs():
    assert calculate_project_npv(_project_return(), None).status is ProjectNpvStatus.NOT_CONFIGURED
    assert calculate_project_npv(
        _project_return(), _project_policy(float("nan"))
    ).status is ProjectNpvStatus.INVALID_DISCOUNT_RATE
    assert calculate_project_npv(
        _project_return(), _project_policy(True)
    ).status is ProjectNpvStatus.INVALID_DISCOUNT_RATE
    assert calculate_project_npv(
        _project_return(), _project_policy(10.01)
    ).status is ProjectNpvStatus.INVALID_DISCOUNT_RATE
    assert calculate_project_npv(
        _project_return(), _project_policy(0.05, explicit_date=date(2031, 1, 1))
    ).status is ProjectNpvStatus.CASHFLOW_BEFORE_UNSUPPORTED_VALUATION_DATE
    upstream = calculate_project_npv(
        _project_return(status=ProjectReturnStatus.HARD_CAPEX_TIMING_UNAVAILABLE),
        _project_policy(),
    )
    assert upstream.status is ProjectNpvStatus.UPSTREAM_PROJECT_RETURN_UNAVAILABLE
    assert upstream.upstream_project_return_status == (
        ProjectReturnStatus.HARD_CAPEX_TIMING_UNAVAILABLE.value
    )


def test_coverage_base_bank_case_isolation_and_horizon_separation():
    model = _coverage_model()
    base = calculate_lender_coverage(
        model=model,
        senior_terminal=_terminal(),
        policy=_coverage_policy(CoverageCfadsCase.BASE),
        minimum_llcr=1.15,
    )
    bank = calculate_lender_coverage(
        model=model,
        senior_terminal=_terminal(),
        policy=_coverage_policy(CoverageCfadsCase.BANK),
        minimum_llcr=1.15,
    )
    assert base.llcr.ratio > bank.llcr.ratio
    assert base.plcr.ratio > bank.plcr.ratio
    assert [row.period_index for row in base.llcr.periods if row.included] == [1, 2]
    assert [row.period_index for row in base.plcr.periods if row.included] == [1, 2, 3, 4]
    assert all(
        row.exclusion_reason == "AFTER_SENIOR_CONTRACTUAL_MATURITY"
        for row in base.llcr.periods[2:]
    )

    changed_base = calculate_lender_coverage(
        model=_coverage_model(base=(200.0,) * 4, bank=(80.0,) * 4),
        senior_terminal=_terminal(),
        policy=_coverage_policy(CoverageCfadsCase.BANK),
        minimum_llcr=1.15,
    )
    changed_bank = calculate_lender_coverage(
        model=_coverage_model(base=(100.0,) * 4, bank=(40.0,) * 4),
        senior_terminal=_terminal(),
        policy=_coverage_policy(CoverageCfadsCase.BASE),
        minimum_llcr=1.15,
    )
    assert changed_base.llcr.ratio == pytest.approx(bank.llcr.ratio, abs=1e-12)
    assert changed_bank.llcr.ratio == pytest.approx(base.llcr.ratio, abs=1e-12)


def test_coverage_causal_sensitivities_and_llcr_threshold_are_separate():
    base = calculate_lender_coverage(
        model=_coverage_model(),
        senior_terminal=_terminal(),
        policy=_coverage_policy(rate=0.05),
        minimum_llcr=1.15,
    )
    high_cfads = calculate_lender_coverage(
        model=_coverage_model(base=(120.0,) * 4),
        senior_terminal=_terminal(),
        policy=_coverage_policy(rate=0.05),
        minimum_llcr=1.15,
    )
    high_rate = calculate_lender_coverage(
        model=_coverage_model(),
        senior_terminal=_terminal(),
        policy=_coverage_policy(rate=0.15),
        minimum_llcr=1.15,
    )
    high_debt_model = _coverage_model()
    high_debt_model.senior_debt = replace(
        high_debt_model.senior_debt,
        senior_debt_opening_keur=(300.0, 150.0),
        debt_size_keur=300.0,
    )
    high_debt = calculate_lender_coverage(
        model=high_debt_model,
        senior_terminal=_terminal(),
        policy=_coverage_policy(rate=0.05),
        minimum_llcr=1.15,
    )
    assert high_cfads.llcr.ratio > base.llcr.ratio
    assert high_rate.llcr.ratio < base.llcr.ratio
    assert high_debt.llcr.ratio < base.llcr.ratio
    assert base.llcr_headroom == pytest.approx(base.llcr.ratio - 1.15)
    assert base.llcr_threshold_status in {LlcrThresholdStatus.PASS, LlcrThresholdStatus.FAIL}


def test_coverage_fails_closed_without_case_rate_maturity_or_valid_axis():
    model = _coverage_model()
    absent = calculate_lender_coverage(
        model=model, senior_terminal=_terminal(), policy=None, minimum_llcr=1.15
    )
    assert absent.llcr.status is CoverageStatus.COVERAGE_CFADS_CASE_NOT_CONFIGURED
    no_rate = replace(_coverage_policy(), annual_discount_rate=None)
    assert calculate_lender_coverage(
        model=model, senior_terminal=_terminal(), policy=no_rate, minimum_llcr=1.15
    ).llcr.status is CoverageStatus.COVERAGE_DISCOUNT_RATE_NOT_CONFIGURED
    assert calculate_lender_coverage(
        model=model, senior_terminal=_terminal(None), policy=_coverage_policy(), minimum_llcr=1.15
    ).llcr.status is CoverageStatus.SENIOR_MATURITY_UNAVAILABLE
    bad_axis = _coverage_model()
    bad_axis.tax_and_cfads = replace(bad_axis.tax_and_cfads, period_indices=(1, 2, 3, 5))
    assert calculate_lender_coverage(
        model=bad_axis, senior_terminal=_terminal(), policy=_coverage_policy(), minimum_llcr=1.15
    ).llcr.status is CoverageStatus.PERIOD_AXIS_MISMATCH
    zero_balance = _coverage_model()
    zero_balance.senior_debt = replace(
        zero_balance.senior_debt,
        senior_debt_opening_keur=(0.0, 0.0),
    )
    assert calculate_lender_coverage(
        model=zero_balance,
        senior_terminal=_terminal(),
        policy=_coverage_policy(),
        minimum_llcr=1.15,
    ).llcr.status is CoverageStatus.DEBT_BALANCE_ZERO
    no_senior = _coverage_model()
    no_senior.senior_debt = None
    assert calculate_lender_coverage(
        model=no_senior,
        senior_terminal=_terminal(),
        policy=_coverage_policy(),
        minimum_llcr=1.15,
    ).llcr.status is CoverageStatus.NOT_APPLICABLE_NO_SENIOR


def test_typed_valuation_policy_serialization_round_trip():
    inputs = create_default_solar_project()
    configured = replace(
        inputs,
        valuation=ValuationPolicies(
            project=_project_policy(), coverage=_coverage_policy()
        ),
    )
    restored = project_inputs_from_dict(project_inputs_to_dict(configured))
    assert restored.valuation == configured.valuation
    assert hash_inputs_for_cache(restored) != hash_inputs_for_cache(inputs)


@pytest.mark.parametrize(
    ("name", "factory", "npv_status"),
    (
        ("Solar", create_default_solar_project, ProjectNpvStatus.NOT_CONFIGURED),
        ("Wind", create_default_wind_project, ProjectNpvStatus.NOT_CONFIGURED),
        ("Oborovo", create_default_oborovo, ProjectNpvStatus.NOT_CONFIGURED),
        ("TUHO", create_default_tuho_wind1, ProjectNpvStatus.OK),
    ),
)
def test_current_project_configuration_is_source_honest(name, factory, npv_status):
    result = run_clean_production(factory(), project_type=name).g2c_result
    valuation = result.valuation_summary
    assert valuation.project_npv.status is npv_status
    assert valuation.lender_coverage.llcr.status is (
        CoverageStatus.COVERAGE_CFADS_CASE_NOT_CONFIGURED
    )
    assert valuation.lender_coverage.plcr.status is (
        CoverageStatus.COVERAGE_CFADS_CASE_NOT_CONFIGURED
    )
    if name == "TUHO":
        assert valuation.project_npv.annual_discount_rate == pytest.approx(0.066)
        assert valuation.project_npv.npv_keur is not None
        assert valuation.project_npv.periods


def test_project_identity_does_not_dispatch_c2_policy_or_results():
    inputs = create_default_tuho_wind1()
    renamed = replace(
        inputs,
        info=replace(inputs.info, name="Renamed", company="Other", code="X-1"),
    )
    base = run_clean_production(inputs, project_type="TUHO").g2c_result.valuation_summary
    changed = run_clean_production(renamed, project_type="TUHO").g2c_result.valuation_summary
    assert changed == base


def test_project_npv_is_invariant_to_financing_mutation_with_fixed_rate():
    inputs = create_default_solar_project()
    configured = replace(
        inputs,
        valuation=ValuationPolicies(project=_project_policy(0.08)),
    )
    financing_changed = replace(
        configured,
        financing=replace(
            configured.financing,
            gearing_ratio=0.65,
            margin_bps=300,
            senior_tenor_years=12,
            shl_rate=0.09,
            senior_debt_interest_config=_generic_clean_senior_interest_config(
                annual_all_in_rate=0.06,
                tenor_years=12,
            ),
        ),
    )
    base = run_clean_production(configured, project_type="Solar").g2c_result
    changed = run_clean_production(
        financing_changed, project_type="Solar"
    ).g2c_result
    assert changed.return_summary.project.cashflows == base.return_summary.project.cashflows
    assert changed.valuation_summary.project_npv.npv_keur == pytest.approx(
        base.valuation_summary.project_npv.npv_keur, abs=1e-12
    )


def test_clean_presentation_serializes_c2_as_pass_through_only():
    from app.services import clean_presentation_adapter as adapter

    clean_run = run_clean_production(create_default_tuho_wind1(), project_type="TUHO")
    view = adapter.build_clean_waterfall_view(clean_run)
    payload = view._authority_metadata["valuation_summary"]
    source = clean_run.g2c_result.valuation_summary.project_npv
    assert view.project_npv == source.npv_keur
    assert payload["project_npv"]["npv_keur"] == source.npv_keur
    assert payload["project_npv"]["periods"][0]["undiscounted_cashflow_keur"] == (
        source.periods[0].undiscounted_cashflow_keur
    )
    adapter_source = inspect.getsource(adapter)
    assert "discount_dated_cashflows(" not in adapter_source
    assert "calculate_project_npv(" not in adapter_source
    assert "calculate_lender_coverage(" not in adapter_source
