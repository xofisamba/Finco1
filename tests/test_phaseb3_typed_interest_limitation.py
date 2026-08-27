from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
from pathlib import Path

import pytest

from financial_engine.policies.tax import (
    CapitalisationGatePolicy,
    InterestLimitationCarryforwardMode,
    InterestLimitationCombinationMode,
    InterestLimitationPolicy,
)
from financial_engine.tax.interest_limitation import (
    CapitalisationState,
    EquityStatePeriodInput,
    InterestLimitationPeriodInput,
    calculate_capitalisation_gate,
    calculate_interest_limitation_period,
    roll_forward_equity_state,
)


def _policy(**changes: object) -> InterestLimitationPolicy:
    policy = InterestLimitationPolicy(
        enabled=True,
        absolute_interest_limit_keur=3_000.0,
        ebitda_interest_limit_pct=0.30,
        capitalisation_gate_policy=CapitalisationGatePolicy(
            enabled=True,
            threshold=0.80,
            subtotal_is_reincluded_in_denominator=True,
        ),
        combination_mode=InterestLimitationCombinationMode.MAX_DISALLOWED,
        carryforward_mode=InterestLimitationCarryforwardMode.NONE,
        source_model_convention="NO_RESTRICTED_INTEREST_CARRYFORWARD_IN_SOURCE_MODEL",
    )
    return replace(policy, **changes)


def _state(*, shl: float, retained: float = 0.0, capital: float = 500.0) -> CapitalisationState:
    return CapitalisationState(
        share_capital_keur=capital,
        legal_reserve_keur=0.0,
        retained_earnings_keur=retained,
        shl_closing_keur=shl,
    )


def test_literal_capitalisation_gate_below_equal_and_above_threshold():
    policy = _policy()

    below = calculate_capitalisation_gate(_state(shl=1_500.0), policy)
    at_threshold = calculate_capitalisation_gate(
        _state(shl=800.0, retained=-800.0), policy
    )
    above = calculate_capitalisation_gate(
        _state(shl=700.0, retained=-800.0), policy
    )

    assert below.ratio == pytest.approx(0.375)
    assert below.active is False
    assert at_threshold.ratio == pytest.approx(0.8)
    assert at_threshold.active is True
    assert above.ratio > 0.8
    assert above.active is True


def test_shl_equity_and_retained_earnings_mutations_move_literal_ratio():
    policy = _policy()
    base = calculate_capitalisation_gate(_state(shl=1_500.0), policy)
    higher_shl = calculate_capitalisation_gate(_state(shl=2_000.0), policy)
    higher_equity = calculate_capitalisation_gate(
        _state(shl=1_500.0, capital=1_000.0), policy
    )
    higher_retained = calculate_capitalisation_gate(
        _state(shl=1_500.0, retained=500.0), policy
    )

    assert higher_shl.ratio > base.ratio
    assert higher_equity.ratio < base.ratio
    assert higher_retained.ratio < base.ratio


def test_max_combination_and_deductible_only_identity():
    result = calculate_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=7,
            gross_shl_interest_keur=4_000.0,
            ebitda_basis_keur=5_000.0,
            capitalisation_state=_state(shl=700.0, retained=-800.0),
        ),
        _policy(),
    )

    assert result.absolute_limit_component_keur == pytest.approx(1_000.0)
    assert result.ebitda_limit_component_keur == pytest.approx(2_500.0)
    assert result.disallowed_shl_interest_keur == pytest.approx(2_500.0)
    assert result.deductible_shl_interest_keur == pytest.approx(1_500.0)
    assert (
        result.deductible_shl_interest_keur
        + result.disallowed_shl_interest_keur
    ) == pytest.approx(result.gross_shl_interest_keur, abs=1e-12)
    assert result.restricted_interest_carryforward_created_keur == 0.0


def test_sum_combination_additional_component_and_gross_cap():
    result = calculate_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=1,
            gross_shl_interest_keur=4_000.0,
            ebitda_basis_keur=5_000.0,
            capitalisation_state=_state(shl=700.0, retained=-800.0),
        ),
        _policy(
            combination_mode=InterestLimitationCombinationMode.SUM_DISALLOWED,
            additional_non_deductible_share=0.25,
        ),
    )

    assert result.additional_non_deductible_component_keur == pytest.approx(1_000.0)
    assert result.disallowed_shl_interest_keur == pytest.approx(4_000.0)
    assert result.deductible_shl_interest_keur == 0.0


def test_gate_off_suppresses_source_gate_components_but_not_independent_additional_component():
    result = calculate_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=0,
            gross_shl_interest_keur=1_000.0,
            ebitda_basis_keur=1_000.0,
            capitalisation_state=_state(shl=100.0),
        ),
        _policy(additional_non_deductible_share=0.10),
    )

    assert result.capitalisation_gate.active is False
    assert result.absolute_limit_component_keur == 0.0
    assert result.ebitda_limit_component_keur == 0.0
    assert result.disallowed_shl_interest_keur == pytest.approx(100.0)


def test_carryforward_mode_fails_closed_until_a_ledger_exists():
    with pytest.raises(
        NotImplementedError,
        match="INTEREST_LIMITATION_CARRY_FORWARD_NOT_IMPLEMENTED",
    ):
        _policy(carryforward_mode=InterestLimitationCarryforwardMode.CARRY_FORWARD)


def test_source_legal_reserve_and_retained_earnings_roll_forward_is_causal():
    results = roll_forward_equity_state(
        (
            EquityStatePeriodInput(period_index=0, net_income_keur=-100.0),
            EquityStatePeriodInput(period_index=1, net_income_keur=30.0),
            EquityStatePeriodInput(period_index=2, net_income_keur=50.0),
            EquityStatePeriodInput(
                period_index=3,
                net_income_keur=20.0,
                gross_dividends_keur=5.0,
            ),
        ),
        share_capital_keur=500.0,
        legal_reserve_cap_fraction=0.10,
    )

    assert [r.legal_reserve_transfer_keur for r in results] == pytest.approx(
        [0.0, 30.0, 20.0, 0.0]
    )
    assert [r.closing_legal_reserve_keur for r in results] == pytest.approx(
        [0.0, 30.0, 50.0, 50.0]
    )
    assert [r.closing_retained_earnings_keur for r in results] == pytest.approx(
        [-100.0, -100.0, -70.0, -55.0]
    )
    assert max(abs(r.residual_keur) for r in results) == 0.0


def test_tuho_source_periods_recompute_from_balance_sheet_components_without_gate_replay():
    fixture_dir = Path("tests/fixtures/interest_limitation")
    limitation = json.loads(
        (fixture_dir / "tuho_interest_limitation_fixture.json").read_text(
            encoding="utf-8"
        )
    )
    balance_sheet = json.loads(
        (fixture_dir / "tuho_capitalisation_gate_fixture.json").read_text(
            encoding="utf-8"
        )
    )
    policy = _policy()
    source_by_period = {p["period_index"]: p for p in limitation["periods"]}

    max_ratio_delta = 0.0
    max_component_delta = 0.0
    max_r54_delta = 0.0
    gate_mismatches: list[int] = []
    calculated_total = 0.0
    for row in balance_sheet["periods"]:
        source = source_by_period[row["period_index"]]
        result = calculate_interest_limitation_period(
            InterestLimitationPeriodInput(
                period_index=row["period_index"],
                gross_shl_interest_keur=source["gross_shl_interest_r27"],
                ebitda_basis_keur=source["ebitda"],
                capitalisation_state=CapitalisationState(
                    share_capital_keur=row["share_capital_keur"],
                    legal_reserve_keur=row["legal_reserve_keur"],
                    retained_earnings_keur=row["retained_earnings_keur"],
                    shl_closing_keur=row["shl_closing_keur"],
                ),
            ),
            policy,
        )
        max_ratio_delta = max(
            max_ratio_delta,
            abs(result.capitalisation_gate.ratio - row["capitalisation_ratio"]),
        )
        if result.capitalisation_gate.active is not row["gate_active"]:
            gate_mismatches.append(row["period_index"])
        max_component_delta = max(
            max_component_delta,
            abs(
                result.absolute_limit_component_keur
                - source["r57_absolute_cap_excess"]
            ),
            abs(
                result.ebitda_limit_component_keur
                - source["r58_ebitda_cap_excess"]
            ),
            abs(
                result.additional_non_deductible_component_keur
                - source["r59_ratio_adjustment"]
            ),
        )
        max_r54_delta = max(
            max_r54_delta,
            abs(result.disallowed_shl_interest_keur - source["r54_helper"]),
        )
        calculated_total += result.disallowed_shl_interest_keur

    assert max_ratio_delta < 1e-12
    assert gate_mismatches == []
    assert max_component_delta < 1e-12
    assert max_r54_delta < 1e-12
    assert calculated_total == pytest.approx(9_242.742070978198, abs=1e-9)
    assert next(p["period_index"] for p in balance_sheet["periods"] if p["gate_active"]) == 7


def test_tuho_source_retained_earnings_and_legal_reserve_are_recomputed_causally():
    fixture = json.loads(
        Path(
            "tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json"
        ).read_text(encoding="utf-8")
    )
    source_rows = (fixture["construction"], *fixture["periods"])
    results = roll_forward_equity_state(
        tuple(
            EquityStatePeriodInput(
                period_index=index - 1,
                net_income_keur=row["net_income_keur"],
                gross_dividends_keur=row["gross_dividends_keur"],
            )
            for index, row in enumerate(source_rows)
        ),
        share_capital_keur=500.0,
        legal_reserve_cap_fraction=0.10,
    )

    assert max(
        abs(result.closing_legal_reserve_keur - source["legal_reserve_keur"])
        for result, source in zip(results, source_rows)
    ) < 1e-9
    assert max(
        abs(result.legal_reserve_transfer_keur - source["legal_reserve_transfer_keur"])
        for result, source in zip(results, source_rows)
    ) < 1e-9
    assert max(
        abs(result.closing_retained_earnings_keur - source["retained_earnings_keur"])
        for result, source in zip(results, source_rows)
    ) < 1e-9


def test_tax_engine_consumes_deductible_shl_once_without_reintegration_addback():
    from financial_engine.inputs import PeriodInterestInput, TaxCalculationInput
    from financial_engine.policies.tax import (
        CashTaxTiming,
        ShlInterestDeductibilityMode,
        TaxPolicy,
    )
    from financial_engine.results import OperatingPeriodResult
    from financial_engine.tax.engine import calculate_tax

    period = OperatingPeriodResult(
        period_index=0,
        period_start=date(2030, 1, 1),
        period_end=date(2031, 1, 1),
        year_index=1.0,
        period_in_year=1.0,
        is_construction=False,
        is_operation=True,
        is_ppa_active=True,
        days_in_period=365,
        day_fraction=1.0,
        production_mwh=0.0,
        revenue_keur=0.0,
        opex_keur=0.0,
        ebitda_keur=5_000.0,
        book_depreciation_keur=0.0,
        tax_depreciation_keur=0.0,
        ebit_keur=5_000.0,
    )
    policy = TaxPolicy(
        policy_id="synthetic",
        policy_version="1",
        corporate_rate=0.18,
        periods_per_tax_year=1,
        loss_carryforward_years=5,
        atad_enabled=False,
        atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3_000.0,
        cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
        shl_interest_tax_treatment_enabled=True,
        shl_interest_deductibility=(
            ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS
        ),
        interest_limitation_policy=_policy(),
    )
    result = calculate_tax(
        (period,),
        TaxCalculationInput(
            policy=policy,
            opening_loss_vintages=(),
            period_interest=(
                PeriodInterestInput(
                    period_index=0,
                    senior_interest_keur=100.0,
                    shl_interest_keur=4_000.0,
                    shl_deductible_interest_keur=1_500.0,
                    capitalisation_ratio=0.9,
                    capitalisation_gate_active=True,
                    absolute_limit_component_keur=1_000.0,
                    ebitda_limit_component_keur=2_500.0,
                ),
            ),
        ),
    )

    annual = result.annual_results[0]
    period_tax = result.period_results[0]
    assert annual.total_interest_keur == pytest.approx(1_600.0)
    assert annual.taxable_income_before_lcf_keur == pytest.approx(3_400.0)
    assert annual.current_tax_liability_keur == pytest.approx(612.0)
    assert period_tax.shl_tax_eligible_interest_keur == pytest.approx(1_500.0)
    assert period_tax.shl_non_deductible_interest_keur == pytest.approx(2_500.0)
    assert period_tax.other_fiscal_reintegration_keur == 0.0
    assert period_tax.capitalisation_ratio == pytest.approx(0.9)
    assert period_tax.capitalisation_gate_active is True


def test_canonical_interest_limitation_policy_round_trips_serialization():
    from app.project_factories import create_default_solar_project
    from finco_core.inputs import (
        CapitalisationGatePolicyParams,
        InterestLimitationCarryforwardMode as InputCarryforwardMode,
        InterestLimitationCombinationMode as InputCombinationMode,
        InterestLimitationPolicyParams,
        project_inputs_from_dict,
        project_inputs_to_dict,
    )

    project = create_default_solar_project()
    source_policy = InterestLimitationPolicyParams(
        enabled=True,
        absolute_interest_limit_keur=3_000.0,
        ebitda_interest_limit_pct=0.30,
        capitalisation_gate_policy=CapitalisationGatePolicyParams(
            enabled=True,
            threshold=0.8,
            subtotal_is_reincluded_in_denominator=True,
        ),
        combination_mode=InputCombinationMode.MAX_DISALLOWED,
        carryforward_mode=InputCarryforwardMode.NONE,
        source_model_convention="SOURCE_WORKBOOK_MECHANIC",
    )
    project = replace(
        project,
        tax=replace(project.tax, interest_limitation_policy=source_policy),
    )

    restored = project_inputs_from_dict(project_inputs_to_dict(project))
    assert restored.tax.interest_limitation_policy == source_policy


def test_dynamic_interest_limitation_closes_inside_existing_fixed_point_from_two_seeds():
    from app.project_factories import create_default_oborovo_legacy_calibration
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.inputs import CapitalisationGateEquityInput
    from financial_engine.orchestrator import _run_senior_debt_model_with_shl
    from financial_engine.policies.tax import ShlInterestDeductibilityMode

    model = build_senior_debt_model_input_from_project_inputs(
        create_default_oborovo_legacy_calibration(),
        source_id="generic-dynamic-interest-limitation-test",
    )
    dynamic_policy = replace(
        _policy(),
        capitalisation_gate_policy=CapitalisationGatePolicy(
            enabled=True,
            threshold=0.40,
            subtotal_is_reincluded_in_denominator=True,
        ),
    )
    tax_policy = replace(
        model.tax.policy,
        atad_enabled=False,
        thin_cap_enabled=False,
        shl_interest_deductibility=(
            ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS
        ),
        interest_limitation_policy=dynamic_policy,
    )
    model = replace(
        model,
        tax=replace(model.tax, policy=tax_policy),
        capitalisation_gate_equity=CapitalisationGateEquityInput(
            share_capital_keur=500.0,
            legal_reserve_cap_fraction=0.10,
        ),
    )

    zero_seed = _run_senior_debt_model_with_shl(model)
    high_seed = _run_senior_debt_model_with_shl(
        model,
        _test_only_initial_shl_interest_guess={idx: 2_000.0 for idx in range(41)},
    )

    assert zero_seed.senior_debt.debt_size_keur == pytest.approx(
        high_seed.senior_debt.debt_size_keur, abs=1e-7
    )
    assert zero_seed.tax_and_cfads.corporate_tax_cash_keur == pytest.approx(
        high_seed.tax_and_cfads.corporate_tax_cash_keur, abs=1e-7
    )
    assert zero_seed.shareholder_loan.shl_closing_keur == pytest.approx(
        high_seed.shareholder_loan.shl_closing_keur, abs=1e-7
    )
    assert zero_seed.tax_and_cfads.capitalisation_ratio_audit == pytest.approx(
        high_seed.tax_and_cfads.capitalisation_ratio_audit, abs=1e-9
    )
    diagnostics = zero_seed.shareholder_loan.diagnostics
    assert diagnostics.converged is True
    assert diagnostics.capitalisation_gate_mismatch_count == 0
    assert diagnostics.max_retained_earnings_delta_keur < 1e-4
    assert diagnostics.max_capitalisation_ratio_delta < 1e-9
    for gross, deductible, disallowed in zip(
        zero_seed.tax_and_cfads.shl_gross_interest_audit_keur,
        zero_seed.tax_and_cfads.shl_deductible_interest_audit_keur,
        zero_seed.tax_and_cfads.shl_disallowed_interest_audit_keur,
    ):
        assert deductible + disallowed == pytest.approx(gross, abs=1e-10)
