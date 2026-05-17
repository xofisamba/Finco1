"""TUHO vintage-tracked loss carry-forward scenario tests."""

from __future__ import annotations

import pytest

from domain.tax.loss_carryforward import (
    LossCarryforwardConfig,
    compute_loss_carryforward_schedule,
)


TAX_RATE = 0.18
EXCEL_COMPATIBILITY_CIT_TOTAL_KEUR = 38_240.9
TAX_LAW_CORRECT_CIT_TOTAL_KEUR = 37_580.2
WINDOW_CIT_DELTA_KEUR = TAX_LAW_CORRECT_CIT_TOTAL_KEUR - EXCEL_COMPATIBILITY_CIT_TOTAL_KEUR
WINDOW_LOSS_BASE_KEUR = abs(WINDOW_CIT_DELTA_KEUR) / TAX_RATE
BASELINE_TAXABLE_PROFIT_KEUR = TAX_LAW_CORRECT_CIT_TOTAL_KEUR / TAX_RATE


def _tuho_taxable_income_fixture() -> tuple[float, ...]:
    return (
        -WINDOW_LOSS_BASE_KEUR,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        WINDOW_LOSS_BASE_KEUR,
        BASELINE_TAXABLE_PROFIT_KEUR,
    )


def _cit_total(result) -> float:
    return TAX_RATE * sum(
        period.taxable_profit_after_losses_keur for period in result.periods
    )


def test_tuho_excel_compatibility_reproduces_five_period_vintage_expiry():
    result = compute_loss_carryforward_schedule(
        _tuho_taxable_income_fixture(),
        config=LossCarryforwardConfig.excel_compatibility(
            override_periods=5,
            country_template="tuho_excel_compatibility",
        ),
    )

    assert result.config.duration_periods == 5
    first_bucket = result.periods[0].closing_buckets[0]
    assert first_bucket.generated_loss_keur == pytest.approx(WINDOW_LOSS_BASE_KEUR, abs=0.01)
    assert first_bucket.expiry_period_index == 5
    assert result.total_losses_generated_keur == pytest.approx(WINDOW_LOSS_BASE_KEUR, abs=0.01)
    assert result.total_expired_losses_keur == pytest.approx(WINDOW_LOSS_BASE_KEUR, abs=0.01)
    assert result.total_losses_used_keur == pytest.approx(0.0)
    assert _cit_total(result) == pytest.approx(EXCEL_COMPATIBILITY_CIT_TOTAL_KEUR, abs=0.1)


def test_tuho_tax_law_correct_window_uses_ten_period_vintage_expiry():
    result = compute_loss_carryforward_schedule(
        _tuho_taxable_income_fixture(),
        config=LossCarryforwardConfig(
            duration_years=5,
            periods_per_year=2,
            country_template="croatia",
            expire_before_use=True,
        ),
    )

    assert result.config.duration_periods == 10
    first_bucket = result.periods[0].closing_buckets[0]
    assert first_bucket.expiry_period_index == 10
    assert result.total_losses_generated_keur == pytest.approx(WINDOW_LOSS_BASE_KEUR, abs=0.01)
    assert result.total_expired_losses_keur == pytest.approx(0.0)
    assert result.total_losses_used_keur == pytest.approx(WINDOW_LOSS_BASE_KEUR, abs=0.01)
    assert _cit_total(result) == pytest.approx(TAX_LAW_CORRECT_CIT_TOTAL_KEUR, abs=0.1)


def test_tuho_vintage_tracking_quantifies_window_delta():
    excel = compute_loss_carryforward_schedule(
        _tuho_taxable_income_fixture(),
        config=LossCarryforwardConfig.excel_compatibility(override_periods=5),
    )
    tax_law = compute_loss_carryforward_schedule(
        _tuho_taxable_income_fixture(),
        config=LossCarryforwardConfig(
            duration_years=5,
            periods_per_year=2,
            expire_before_use=True,
        ),
    )

    assert _cit_total(excel) == pytest.approx(38_240.9, abs=0.1)
    assert _cit_total(tax_law) == pytest.approx(37_580.2, abs=0.1)
    assert _cit_total(tax_law) - _cit_total(excel) == pytest.approx(-660.7, abs=0.1)
    assert tax_law.total_losses_used_keur - excel.total_losses_used_keur == pytest.approx(
        WINDOW_LOSS_BASE_KEUR,
        abs=0.01,
    )
