"""PR-10 typed country-tax resolution and opening-loss authority tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest

from app.project_factories import create_default_solar_project, create_default_tuho_wind1
from finco_core.inputs import (
    OpeningTaxLossVintageParams,
    ShlInterestDeductibilityMode,
    TaxParams,
    project_inputs_from_dict,
    project_inputs_to_dict,
)
from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
from financial_engine.inputs import PeriodInterestInput, PeriodTaxAdjustmentInput
from financial_engine.tax.engine import calculate_tax
from tests.pr5_ebitda_guard import assert_only_approved_pr5_domain_diff


SOURCE_OPENING_LOSS_KEUR = 3568.6878026481627
SOURCE_POLICY_ID = "HR-approved-source-model-2026-v1"


def _project(*, rate_override: float | None = None, loss_years: int = 5):
    base = create_default_solar_project()
    tax = replace(
        base.tax,
        country_tax_policy_id=SOURCE_POLICY_ID,
        corporate_rate=0.18,
        corporate_rate_override=rate_override,
        loss_carryforward_years=loss_years,
    )
    return replace(base, info=replace(base.info, country_iso="HR"), tax=tax)


def _period(*, ebitda: float = 1000.0, depreciation: float = 100.0):
    return SimpleNamespace(
        period_index=0,
        period_start=date(2031, 1, 1),
        period_end=date(2032, 1, 1),
        is_operation=True,
        ebitda_keur=ebitda,
        tax_depreciation_keur=depreciation,
    )


def _calculate(project, *, interest=(), adjustments=()):
    contract = build_tax_contract_from_project_inputs(
        project,
        complete_financing_interest_will_be_injected=bool(interest),
    )
    contract = replace(
        contract,
        period_interest=tuple(interest),
        period_adjustments=tuple(adjustments),
    )
    return calculate_tax((_period(),), contract)


def test_explicit_country_policy_default_then_project_override():
    default_contract = build_tax_contract_from_project_inputs(_project())
    override_contract = build_tax_contract_from_project_inputs(
        _project(rate_override=0.21)
    )

    assert default_contract.policy.policy_id == SOURCE_POLICY_ID
    assert default_contract.policy.corporate_rate == pytest.approx(0.18)
    assert override_contract.policy.corporate_rate == pytest.approx(0.21)


def test_country_metadata_does_not_activate_illustrative_registry():
    base = create_default_solar_project()
    country_only = replace(base, info=replace(base.info, country_iso="HR"))

    contract = build_tax_contract_from_project_inputs(country_only)

    assert contract.policy.policy_id == "clean-project-tax-v1"
    assert contract.policy.corporate_rate == pytest.approx(0.25)


def test_policy_country_mismatch_and_legacy_rate_conflict_fail_closed():
    base = create_default_solar_project()
    mismatch = replace(
        base,
        tax=replace(base.tax, country_tax_policy_id=SOURCE_POLICY_ID),
    )
    with pytest.raises(ValueError, match="COUNTRY_TAX_POLICY_COUNTRY_MISMATCH"):
        build_tax_contract_from_project_inputs(mismatch)

    conflict = replace(_project(), tax=replace(_project().tax, corporate_rate=0.17))
    with pytest.raises(ValueError, match="COUNTRY_TAX_LEGACY_FIELD_CONFLICT"):
        build_tax_contract_from_project_inputs(conflict)


def test_opening_vintages_are_serialized_and_mapped_without_scalar_authority():
    vintage = OpeningTaxLossVintageParams(
        origin_tax_year=2029,
        opening_amount_keur=SOURCE_OPENING_LOSS_KEUR,
        source_label="TUHO P&L!G35 -> H36",
    )
    project = _project()
    project = replace(
        project,
        tax=replace(project.tax, opening_tax_loss_vintages=(vintage,)),
    )

    restored = project_inputs_from_dict(project_inputs_to_dict(project))
    contract = build_tax_contract_from_project_inputs(restored)

    assert restored.tax.opening_tax_loss_vintages == (vintage,)
    assert contract.opening_loss_vintages[0].origin_tax_year == 2029
    assert contract.opening_loss_vintages[0].amount_keur == pytest.approx(
        SOURCE_OPENING_LOSS_KEUR
    )


def test_nonzero_legacy_scalar_without_vintage_evidence_fails_closed():
    project = _project()
    project = replace(project, tax=replace(project.tax, prior_tax_loss_keur=5000.0))

    with pytest.raises(NotImplementedError, match="non-zero legacy"):
        build_tax_contract_from_project_inputs(project)


def test_vintage_expiry_changes_with_explicit_lcf_policy():
    vintage = OpeningTaxLossVintageParams(2025, 500.0, "synthetic opening loss")
    short = _project(loss_years=5)
    long = _project(loss_years=10)
    short = replace(short, tax=replace(short.tax, opening_tax_loss_vintages=(vintage,)))
    long = replace(long, tax=replace(long.tax, opening_tax_loss_vintages=(vintage,)))

    short_result = _calculate(short)
    long_result = _calculate(long)

    assert short_result.annual_results[0].loss_expired_keur == pytest.approx(500.0)
    assert long_result.annual_results[0].loss_used_keur == pytest.approx(500.0)
    assert long_result.annual_results[0].current_tax_liability_keur < (
        short_result.annual_results[0].current_tax_liability_keur
    )


def test_larger_opening_loss_reduces_early_cit_and_reconciles_closing_ledger():
    project = _project(loss_years=10)
    small = replace(
        project,
        tax=replace(
            project.tax,
            opening_tax_loss_vintages=(OpeningTaxLossVintageParams(2029, 100.0),),
        ),
    )
    large = replace(
        project,
        tax=replace(
            project.tax,
            opening_tax_loss_vintages=(OpeningTaxLossVintageParams(2029, 200.0),),
        ),
    )

    small_annual = _calculate(small).annual_results[0]
    large_annual = _calculate(large).annual_results[0]

    assert large_annual.current_tax_liability_keur < small_annual.current_tax_liability_keur
    ledger = large_annual.ledger_entry
    assert (
        ledger.opening_loss_pre_expiry_keur
        + ledger.loss_generated_keur
        - ledger.loss_used_keur
        - ledger.loss_expired_keur
    ) == pytest.approx(ledger.closing_loss_keur)


def test_different_typed_interest_limit_changes_deductible_interest():
    unrestricted = _project()
    limited = replace(
        unrestricted,
        tax=replace(
            unrestricted.tax,
            atad_enabled=True,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur=0.0,
        ),
    )
    interest = (PeriodInterestInput(0, senior_interest_keur=500.0),)

    unrestricted_annual = _calculate(unrestricted, interest=interest).annual_results[0]
    limited_annual = _calculate(limited, interest=interest).annual_results[0]

    assert unrestricted_annual.deductible_interest_keur == pytest.approx(500.0)
    assert limited_annual.deductible_interest_keur == pytest.approx(300.0)
    assert limited_annual.disallowed_interest_keur == pytest.approx(200.0)


def test_causal_rate_depreciation_interest_and_reintegration_grid():
    base = _calculate(_project())
    higher_rate = _calculate(_project(rate_override=0.19))
    higher_dep_contract = build_tax_contract_from_project_inputs(_project())
    higher_dep = calculate_tax(
        (_period(depreciation=200.0),), higher_dep_contract
    )
    deductible_interest = _calculate(
        _project(), interest=(PeriodInterestInput(0, senior_interest_keur=100.0),)
    )
    reintegrated = _calculate(
        _project(), adjustments=(PeriodTaxAdjustmentInput(0, 50.0),)
    )

    base_annual = base.annual_results[0]
    assert higher_rate.annual_results[0].current_tax_liability_keur > (
        base_annual.current_tax_liability_keur
    )
    assert higher_dep.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(
        base_annual.taxable_income_before_lcf_keur - 100.0
    )
    assert deductible_interest.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(
        base_annual.taxable_income_before_lcf_keur - 100.0
    )
    assert reintegrated.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(
        base_annual.taxable_income_before_lcf_keur + 50.0
    )


def test_fully_non_deductible_shl_does_not_reduce_taxable_income():
    project = _project()
    project = replace(
        project,
        tax=replace(
            project.tax,
            shl_interest_deductibility=(
                ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE
            ),
        ),
    )
    result = _calculate(
        project,
        interest=(PeriodInterestInput(0, shl_interest_keur=100.0),),
    )

    assert result.annual_results[0].deductible_interest_keur == pytest.approx(0.0)
    assert result.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(900.0)


def test_identity_change_with_same_typed_policy_has_zero_financial_effect():
    project = _project()
    renamed = replace(
        project,
        info=replace(project.info, name="Unrelated Name", code="UNRELATED-CODE"),
    )

    assert _calculate(project) == _calculate(renamed)


def test_tuho_source_variant_maps_exact_vintage_then_stops_at_g2c_boundary():
    tuho = create_default_tuho_wind1()
    assert tuho.tax.prior_tax_loss_keur == pytest.approx(25_000.0)

    source_variant = replace(
        tuho,
        tax=replace(
            tuho.tax,
            country_tax_policy_id=SOURCE_POLICY_ID,
            prior_tax_loss_keur=0.0,
            opening_tax_loss_vintages=(
                OpeningTaxLossVintageParams(
                    2029,
                    SOURCE_OPENING_LOSS_KEUR,
                    "20260330_TUHO_BP.xlsm P&L!G35 -> H36",
                ),
            ),
            clean_cash_tax_timing_enabled=True,
        ),
    )
    contract = build_tax_contract_from_project_inputs(
        source_variant,
        complete_financing_interest_will_be_injected=True,
    )

    assert contract.opening_loss_vintages[0].amount_keur == pytest.approx(
        SOURCE_OPENING_LOSS_KEUR
    )
    with pytest.raises(NotImplementedError, match="TUHO_SHL_TAX_POLICY_BLOCKED"):
        contract.policy.shl_tax_deductible_fraction()


def test_input_validation_rejects_competing_opening_loss_authorities():
    with pytest.raises(ValueError, match="conflicting authorities"):
        TaxParams(
            prior_tax_loss_keur=1.0,
            opening_tax_loss_vintages=(
                OpeningTaxLossVintageParams(2029, 1.0),
            ),
        )


def test_pr5_guard_scopes_formula_lock_to_pr5_sizing_files():
    unrelated_domain_facade = "\n".join(
        (
            "diff --git a/domain/inputs.py b/domain/inputs.py",
            "--- a/domain/inputs.py",
            "+++ b/domain/inputs.py",
            "+    OpeningTaxLossVintageParams,",
        )
    )
    assert_only_approved_pr5_domain_diff(unrelated_domain_facade)

    sizing_change = "\n".join(
        (
            "diff --git a/domain/senior_debt_sizing/engine.py "
            "b/domain/senior_debt_sizing/engine.py",
            "--- a/domain/senior_debt_sizing/engine.py",
            "+++ b/domain/senior_debt_sizing/engine.py",
            "+                capacity = cfads / dscr",
        )
    )
    with pytest.raises(AssertionError, match="beyond the source-approved"):
        assert_only_approved_pr5_domain_diff(sizing_change)
