"""TUHO loss-window dual semantics fixture.

The fixture isolates the confirmed Excel loss-window issue: the workbook uses
five semiannual columns, while tax-law-correct Croatia semantics use five years.
"""

from __future__ import annotations

import pytest

from domain.tax.loss_carryforward import (
    LossCarryforwardConfig,
    compute_loss_carryforward_schedule,
)


TAX_RATE = 0.18
EXCEL_COMPATIBILITY_CIT_TOTAL_KEUR = 38_240.9
TAX_LAW_CORRECT_CIT_TOTAL_KEUR = 37_580.2
EXPECTED_CIT_DELTA_KEUR = TAX_LAW_CORRECT_CIT_TOTAL_KEUR - EXCEL_COMPATIBILITY_CIT_TOTAL_KEUR
LOSS_WINDOW_EXPLAINED_TAX_BASE_KEUR = abs(EXPECTED_CIT_DELTA_KEUR) / TAX_RATE
BASELINE_TAXABLE_PROFIT_KEUR = TAX_LAW_CORRECT_CIT_TOTAL_KEUR / TAX_RATE


def _tuho_window_taxable_income_fixture() -> tuple[float, ...]:
    """Synthetic TUHO sensitivity fixture matching the discovered CIT impact."""

    return (
        -LOSS_WINDOW_EXPLAINED_TAX_BASE_KEUR,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        LOSS_WINDOW_EXPLAINED_TAX_BASE_KEUR,
        BASELINE_TAXABLE_PROFIT_KEUR,
    )


def _cit_total(result) -> float:
    return TAX_RATE * sum(
        period.taxable_profit_after_losses_keur for period in result.periods
    )


def test_excel_compatibility_fixture_reproduces_tuho_five_period_r36_r37_behavior():
    result = compute_loss_carryforward_schedule(
        _tuho_window_taxable_income_fixture(),
        config=LossCarryforwardConfig.excel_compatibility(
            override_periods=5,
            country_template="tuho_excel_compatibility",
        ),
    )

    assert result.config.duration_periods == 5
    assert result.periods[5].expired_losses_keur == pytest.approx(
        LOSS_WINDOW_EXPLAINED_TAX_BASE_KEUR,
        abs=0.01,
    )
    assert result.periods[6].losses_n_1_keur == pytest.approx(0.0)
    assert result.periods[6].allocated_losses_keur == pytest.approx(0.0)
    assert result.periods[6].taxable_profit_after_losses_keur == pytest.approx(
        LOSS_WINDOW_EXPLAINED_TAX_BASE_KEUR,
        abs=0.01,
    )
    assert _cit_total(result) == pytest.approx(EXCEL_COMPATIBILITY_CIT_TOTAL_KEUR, abs=0.1)


def test_tax_law_correct_fixture_uses_ten_semiannual_periods_and_differs_materially():
    result = compute_loss_carryforward_schedule(
        _tuho_window_taxable_income_fixture(),
        config=LossCarryforwardConfig(
            duration_years=5,
            periods_per_year=2,
            country_template="croatia",
        ),
    )

    assert result.config.duration_periods == 10
    assert result.periods[5].expired_losses_keur == pytest.approx(0.0)
    assert result.periods[5].losses_n_keur == pytest.approx(
        LOSS_WINDOW_EXPLAINED_TAX_BASE_KEUR,
        abs=0.01,
    )
    assert result.periods[6].losses_n_1_keur == pytest.approx(
        LOSS_WINDOW_EXPLAINED_TAX_BASE_KEUR,
        abs=0.01,
    )
    assert result.periods[6].allocated_losses_keur == pytest.approx(
        LOSS_WINDOW_EXPLAINED_TAX_BASE_KEUR,
        abs=0.01,
    )
    assert result.periods[6].taxable_profit_after_losses_keur == pytest.approx(0.0)
    assert _cit_total(result) == pytest.approx(TAX_LAW_CORRECT_CIT_TOTAL_KEUR, abs=0.1)


def test_tuho_dual_fixture_quantifies_cit_effect_and_remaining_residual():
    excel_compatibility = compute_loss_carryforward_schedule(
        _tuho_window_taxable_income_fixture(),
        config=LossCarryforwardConfig.excel_compatibility(override_periods=5),
    )
    tax_law_correct = compute_loss_carryforward_schedule(
        _tuho_window_taxable_income_fixture(),
        config=LossCarryforwardConfig(duration_years=5, periods_per_year=2),
    )

    excel_cit = _cit_total(excel_compatibility)
    tax_law_cit = _cit_total(tax_law_correct)
    cit_delta = tax_law_cit - excel_cit

    assert excel_cit == pytest.approx(38_240.9, abs=0.1)
    assert tax_law_cit == pytest.approx(37_580.2, abs=0.1)
    assert cit_delta == pytest.approx(-660.7, abs=0.1)

    current_python_residual_keur = 2_149.3
    unresolved_after_window_keur = current_python_residual_keur - abs(cit_delta)
    assert unresolved_after_window_keur == pytest.approx(1_488.6, abs=0.1)
