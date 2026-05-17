"""Standalone rolling loss carry-forward engine tests."""

from __future__ import annotations

import pytest

from domain.tax.loss_carryforward import (
    LossCarryforwardBucket,
    LossCarryforwardConfig,
    LossCarryforwardPeriodInput,
    compute_loss_carryforward_period,
    compute_loss_carryforward_schedule,
)


def test_fifo_usage_allocates_oldest_losses_first():
    config = LossCarryforwardConfig(max_carryforward_years=2, periods_per_year=1)
    result = compute_loss_carryforward_period(
        LossCarryforwardPeriodInput(
            period_index=2,
            taxable_income_before_losses_keur=120.0,
            opening_buckets=(
                LossCarryforwardBucket(75.0, periods_remaining=2, source_period_index=0),
                LossCarryforwardBucket(80.0, periods_remaining=2, source_period_index=1),
            ),
        ),
        config,
    )

    assert result.losses_n_1_keur == pytest.approx(155.0)
    assert result.allocated_losses_keur == pytest.approx(120.0)
    assert result.taxable_profit_after_losses_keur == pytest.approx(0.0)
    assert result.losses_n_keur == pytest.approx(35.0)
    assert result.closing_buckets[0].amount_keur == pytest.approx(35.0)
    assert result.closing_buckets[0].source_period_index == 1


def test_current_period_tax_loss_is_added_as_new_bucket():
    result = compute_loss_carryforward_period(
        LossCarryforwardPeriodInput(
            period_index=3,
            taxable_income_before_losses_keur=-42.5,
            opening_buckets=(),
        ),
        LossCarryforwardConfig(),
    )

    assert result.losses_generated_keur == pytest.approx(42.5)
    assert result.losses_n_keur == pytest.approx(42.5)
    assert result.taxable_profit_after_losses_keur == pytest.approx(0.0)
    assert result.closing_buckets[0].periods_remaining == 10


def test_expired_losses_are_removed_after_carryforward_window():
    config = LossCarryforwardConfig(max_carryforward_years=1, periods_per_year=1)
    result = compute_loss_carryforward_period(
        LossCarryforwardPeriodInput(
            period_index=1,
            taxable_income_before_losses_keur=0.0,
            opening_buckets=(LossCarryforwardBucket(100.0, periods_remaining=1),),
        ),
        config,
    )

    assert result.expired_losses_keur == pytest.approx(100.0)
    assert result.losses_n_keur == pytest.approx(0.0)
    assert result.closing_buckets == ()


def test_schedule_reproduces_excel_row_semantics_r36_to_r41():
    result = compute_loss_carryforward_schedule(
        taxable_income_before_losses_keur=(-100.0, 40.0, 90.0),
        config=LossCarryforwardConfig(max_carryforward_years=5, periods_per_year=2),
        opening_loss_keur=50.0,
    )

    first, second, third = result.periods
    assert first.losses_n_1_keur == pytest.approx(50.0)  # R36
    assert first.allocated_losses_keur == pytest.approx(0.0)  # R37
    assert first.losses_n_keur == pytest.approx(150.0)  # R38
    assert first.carriable_losses_keur == pytest.approx(150.0)  # R39
    assert first.taxable_profit_after_losses_keur == pytest.approx(0.0)  # R41

    assert second.allocated_losses_keur == pytest.approx(40.0)
    assert second.losses_n_keur == pytest.approx(110.0)
    assert third.allocated_losses_keur == pytest.approx(90.0)
    assert third.losses_n_keur == pytest.approx(20.0)
    assert result.total_losses_used_keur == pytest.approx(130.0)


def test_invalid_config_and_opening_loss_are_rejected():
    with pytest.raises(ValueError, match="max_carryforward_years"):
        LossCarryforwardConfig(max_carryforward_years=0)

    with pytest.raises(ValueError, match="opening_loss_keur"):
        compute_loss_carryforward_schedule((1.0,), opening_loss_keur=-1.0)
