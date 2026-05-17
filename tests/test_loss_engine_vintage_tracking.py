"""Offline vintage-tracked FIFO loss carry-forward tests."""

from __future__ import annotations

import pytest

from domain.tax.loss_carryforward import (
    LossCarryforwardBucket,
    LossCarryforwardConfig,
    LossCarryforwardPeriodInput,
    compute_loss_carryforward_period,
    compute_loss_carryforward_schedule,
)


def test_vintage_bucket_tracks_generation_remaining_and_expiry():
    result = compute_loss_carryforward_schedule(
        (-120.0,),
        config=LossCarryforwardConfig(duration_years=5, periods_per_year=2),
    )

    bucket = result.periods[0].closing_buckets[0]
    assert bucket.source_period_index == 0
    assert bucket.generated_loss_keur == pytest.approx(120.0)
    assert bucket.remaining_loss_keur == pytest.approx(120.0)
    assert bucket.amount_keur == pytest.approx(120.0)
    assert bucket.expiry_period_index == 10
    assert bucket.periods_remaining == 10


def test_fifo_consumes_oldest_valid_vintage_first():
    result = compute_loss_carryforward_period(
        LossCarryforwardPeriodInput(
            period_index=3,
            taxable_income_before_losses_keur=90.0,
            opening_buckets=(
                LossCarryforwardBucket(
                    amount_keur=50.0,
                    periods_remaining=3,
                    source_period_index=0,
                    source_label="old",
                    generated_loss_keur=50.0,
                    remaining_loss_keur=50.0,
                    expiry_period_index=5,
                ),
                LossCarryforwardBucket(
                    amount_keur=80.0,
                    periods_remaining=5,
                    source_period_index=2,
                    source_label="new",
                    generated_loss_keur=80.0,
                    remaining_loss_keur=80.0,
                    expiry_period_index=7,
                ),
            ),
        ),
        LossCarryforwardConfig(duration_years=5, periods_per_year=2, expire_before_use=True),
    )

    assert result.allocated_losses_keur == pytest.approx(90.0)
    assert result.taxable_profit_after_losses_keur == pytest.approx(0.0)
    assert len(result.closing_buckets) == 1
    assert result.closing_buckets[0].source_label == "new"
    assert result.closing_buckets[0].remaining_loss_keur == pytest.approx(40.0)


def test_expired_bucket_is_removed_before_use():
    result = compute_loss_carryforward_period(
        LossCarryforwardPeriodInput(
            period_index=5,
            taxable_income_before_losses_keur=75.0,
            opening_buckets=(
                LossCarryforwardBucket(
                    amount_keur=100.0,
                    periods_remaining=1,
                    source_period_index=0,
                    generated_loss_keur=100.0,
                    remaining_loss_keur=100.0,
                    expiry_period_index=5,
                ),
            ),
        ),
        LossCarryforwardConfig(duration_years=5, periods_per_year=2, expire_before_use=True),
    )

    assert result.expired_losses_keur == pytest.approx(100.0)
    assert result.allocated_losses_keur == pytest.approx(0.0)
    assert result.taxable_profit_after_losses_keur == pytest.approx(75.0)
    assert result.closing_buckets == ()


def test_current_period_generated_loss_cannot_be_used_in_same_period():
    result = compute_loss_carryforward_period(
        LossCarryforwardPeriodInput(
            period_index=4,
            taxable_income_before_losses_keur=-60.0,
            opening_buckets=(),
        ),
        LossCarryforwardConfig(duration_years=5, periods_per_year=2),
    )

    assert result.allocated_losses_keur == pytest.approx(0.0)
    assert result.taxable_profit_after_losses_keur == pytest.approx(0.0)
    assert result.losses_generated_keur == pytest.approx(60.0)
    assert result.closing_buckets[0].source_period_index == 4
    assert result.closing_buckets[0].expiry_period_index == 14


def test_window_modes_drive_vintage_expiry_without_hardcoded_periods():
    annual = LossCarryforwardConfig(duration_years=5, periods_per_year=1)
    semiannual = LossCarryforwardConfig(
        duration_years=5,
        periods_per_year=2,
        expire_before_use=True,
    )
    excel = LossCarryforwardConfig.excel_compatibility(override_periods=5)

    assert annual.duration_periods == 5
    assert semiannual.duration_periods == 10
    assert excel.duration_periods == 5

    annual_result = compute_loss_carryforward_schedule((-1.0,), annual)
    semiannual_result = compute_loss_carryforward_schedule((-1.0,), semiannual)
    excel_result = compute_loss_carryforward_schedule((-1.0,), excel)

    assert annual_result.periods[0].closing_buckets[0].expiry_period_index == 5
    assert semiannual_result.periods[0].closing_buckets[0].expiry_period_index == 10
    assert excel_result.periods[0].closing_buckets[0].expiry_period_index == 5


def test_no_single_pool_no_expiry_behavior_when_old_and_new_vintages_coexist():
    result = compute_loss_carryforward_schedule(
        (-100.0, 0.0, 0.0, -40.0, 0.0, 90.0),
        config=LossCarryforwardConfig.excel_compatibility(override_periods=5),
    )

    # The period-0 bucket expires before period 5 and cannot be pooled with
    # the period-3 bucket.
    assert result.periods[5].expired_losses_keur == pytest.approx(100.0)
    assert result.periods[5].allocated_losses_keur == pytest.approx(40.0)
    assert result.periods[5].taxable_profit_after_losses_keur == pytest.approx(50.0)
