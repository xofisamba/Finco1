"""Loss carry-forward window semantics tests.

These tests are offline-only. They protect the distinction between tax-law
duration semantics and explicit Excel workbook compatibility windows.
"""

from __future__ import annotations

import pytest

from domain.financial_statements.templates.croatia import (
    build_croatia_loss_carryforward_config,
)
from domain.tax.loss_carryforward import (
    LossCarryforwardConfig,
    compute_loss_carryforward_schedule,
)


def test_tax_law_duration_periods_derive_from_years_and_frequency():
    assert LossCarryforwardConfig(duration_years=5, periods_per_year=1).duration_periods == 5
    assert LossCarryforwardConfig(duration_years=5, periods_per_year=2).duration_periods == 10
    assert LossCarryforwardConfig(duration_years=5, periods_per_year=4).duration_periods == 20


def test_explicit_override_periods_create_excel_compatibility_window():
    config = LossCarryforwardConfig.excel_compatibility(
        override_periods=5,
        duration_years=5,
        periods_per_year=2,
    )

    assert config.duration_periods == 5
    assert config.max_carryforward_periods == 5
    assert config.max_carryforward_years == 5
    assert config.explicit_override_periods == 5
    assert config.country_template == "excel_compatibility"


def test_croatia_template_is_tax_law_correct_and_frequency_driven():
    annual = build_croatia_loss_carryforward_config(periods_per_year=1)
    semiannual = build_croatia_loss_carryforward_config(periods_per_year=2)
    quarterly = build_croatia_loss_carryforward_config(periods_per_year=4)

    assert annual.duration_periods == 5
    assert semiannual.duration_periods == 10
    assert quarterly.duration_periods == 20
    assert semiannual.explicit_override_periods is None
    assert semiannual.expiry_method == "fifo_per_vintage"


def test_excel_compatibility_fixture_reproduces_five_period_expiry():
    taxable_income = (-100.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    result = compute_loss_carryforward_schedule(
        taxable_income,
        config=LossCarryforwardConfig.excel_compatibility(override_periods=5),
    )

    assert result.periods[0].losses_n_keur == pytest.approx(100.0)
    assert result.periods[4].losses_n_keur == pytest.approx(100.0)
    assert result.periods[5].expired_losses_keur == pytest.approx(100.0)
    assert result.periods[5].losses_n_keur == pytest.approx(0.0)


def test_tax_law_fixture_preserves_larger_surviving_loss_pool():
    taxable_income = (-100.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    result = compute_loss_carryforward_schedule(
        taxable_income,
        config=LossCarryforwardConfig(duration_years=5, periods_per_year=2),
    )

    assert result.config.duration_periods == 10
    assert result.periods[5].expired_losses_keur == pytest.approx(0.0)
    assert result.periods[5].losses_n_keur == pytest.approx(100.0)


def test_invalid_window_config_is_rejected():
    with pytest.raises(ValueError, match="duration_years"):
        LossCarryforwardConfig(duration_years=0)

    with pytest.raises(ValueError, match="explicit_override_periods"):
        LossCarryforwardConfig(explicit_override_periods=0)

    with pytest.raises(ValueError, match="fifo_per_vintage"):
        LossCarryforwardConfig(expiry_method="spreadsheet_columns")
