"""Offline rolling tax loss carry-forward engine.

The engine is intentionally standalone: it does not change the legacy tax
engine and callers must explicitly feed signed taxable income before losses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class LossCarryforwardConfig:
    """Configuration for a rolling loss carry-forward schedule."""

    max_carryforward_years: int = 5
    periods_per_year: int = 2
    loss_usage_order: str = "fifo"

    @property
    def max_carryforward_periods(self) -> int:
        return self.max_carryforward_years * self.periods_per_year

    def __post_init__(self) -> None:
        if self.max_carryforward_years <= 0:
            raise ValueError("max_carryforward_years must be positive")
        if self.periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")
        if self.loss_usage_order != "fifo":
            raise ValueError("Only FIFO loss usage is implemented")


@dataclass(frozen=True)
class LossCarryforwardBucket:
    """One remaining loss bucket, tracked by periods until expiry."""

    amount_keur: float
    periods_remaining: int
    source_period_index: int | None = None

    def __post_init__(self) -> None:
        if self.amount_keur < 0:
            raise ValueError("Loss bucket amount must be non-negative")
        if self.periods_remaining < 0:
            raise ValueError("Loss bucket periods_remaining must be non-negative")


@dataclass(frozen=True)
class LossCarryforwardPeriodInput:
    """Single-period signed taxable income input before loss usage."""

    period_index: int
    taxable_income_before_losses_keur: float
    opening_buckets: tuple[LossCarryforwardBucket, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LossCarryforwardPeriodResult:
    """Audit result matching Excel loss carry-forward rows R36-R41."""

    period_index: int
    taxable_income_before_losses_keur: float
    losses_n_1_keur: float
    allocated_losses_keur: float
    losses_n_keur: float
    carriable_losses_keur: float
    losses_generated_keur: float
    expired_losses_keur: float
    taxable_profit_after_losses_keur: float
    opening_buckets: tuple[LossCarryforwardBucket, ...]
    closing_buckets: tuple[LossCarryforwardBucket, ...]


@dataclass(frozen=True)
class LossCarryforwardResult:
    """Full rolling loss carry-forward result."""

    periods: tuple[LossCarryforwardPeriodResult, ...]
    config: LossCarryforwardConfig

    @property
    def total_losses_used_keur(self) -> float:
        return sum(period.allocated_losses_keur for period in self.periods)

    @property
    def total_losses_generated_keur(self) -> float:
        return sum(period.losses_generated_keur for period in self.periods)

    @property
    def total_expired_losses_keur(self) -> float:
        return sum(period.expired_losses_keur for period in self.periods)


def compute_loss_carryforward_period(
    period_input: LossCarryforwardPeriodInput,
    config: LossCarryforwardConfig,
) -> LossCarryforwardPeriodResult:
    """Compute one FIFO rolling loss carry-forward period."""

    opening_buckets = tuple(
        bucket for bucket in period_input.opening_buckets if bucket.amount_keur > 0
    )
    opening_loss = sum(bucket.amount_keur for bucket in opening_buckets)
    taxable_before = period_input.taxable_income_before_losses_keur

    losses_used = 0.0
    taxable_profit = 0.0
    retained_buckets: list[LossCarryforwardBucket] = []

    if taxable_before > 0:
        remaining_income = taxable_before
        for bucket in opening_buckets:
            use_amount = min(bucket.amount_keur, remaining_income)
            losses_used += use_amount
            remaining_income -= use_amount
            residual = bucket.amount_keur - use_amount
            if residual > 0:
                retained_buckets.append(
                    LossCarryforwardBucket(
                        amount_keur=residual,
                        periods_remaining=bucket.periods_remaining,
                        source_period_index=bucket.source_period_index,
                    )
                )
        taxable_profit = max(0.0, remaining_income)
        generated_loss = 0.0
    else:
        retained_buckets.extend(opening_buckets)
        taxable_profit = 0.0
        generated_loss = -taxable_before

    expired_losses = 0.0
    aged_buckets: list[LossCarryforwardBucket] = []
    for bucket in retained_buckets:
        remaining = bucket.periods_remaining - 1
        if remaining <= 0:
            expired_losses += bucket.amount_keur
        else:
            aged_buckets.append(
                LossCarryforwardBucket(
                    amount_keur=bucket.amount_keur,
                    periods_remaining=remaining,
                    source_period_index=bucket.source_period_index,
                )
            )

    if generated_loss > 0:
        aged_buckets.append(
            LossCarryforwardBucket(
                amount_keur=generated_loss,
                periods_remaining=config.max_carryforward_periods,
                source_period_index=period_input.period_index,
            )
        )

    closing_loss = sum(bucket.amount_keur for bucket in aged_buckets)

    return LossCarryforwardPeriodResult(
        period_index=period_input.period_index,
        taxable_income_before_losses_keur=taxable_before,
        losses_n_1_keur=opening_loss,
        allocated_losses_keur=losses_used,
        losses_n_keur=closing_loss,
        carriable_losses_keur=closing_loss,
        losses_generated_keur=generated_loss,
        expired_losses_keur=expired_losses,
        taxable_profit_after_losses_keur=taxable_profit,
        opening_buckets=opening_buckets,
        closing_buckets=tuple(aged_buckets),
    )


def compute_loss_carryforward_schedule(
    taxable_income_before_losses_keur: Sequence[float],
    config: LossCarryforwardConfig | None = None,
    opening_loss_keur: float = 0.0,
) -> LossCarryforwardResult:
    """Compute a rolling FIFO loss carry-forward schedule."""

    cfg = config or LossCarryforwardConfig()
    if opening_loss_keur < 0:
        raise ValueError("opening_loss_keur must be non-negative")

    buckets: tuple[LossCarryforwardBucket, ...] = ()
    if opening_loss_keur > 0:
        buckets = (
            LossCarryforwardBucket(
                amount_keur=opening_loss_keur,
                periods_remaining=cfg.max_carryforward_periods,
                source_period_index=None,
            ),
        )

    results: list[LossCarryforwardPeriodResult] = []
    for period_index, taxable_before in enumerate(taxable_income_before_losses_keur):
        period_result = compute_loss_carryforward_period(
            LossCarryforwardPeriodInput(
                period_index=period_index,
                taxable_income_before_losses_keur=float(taxable_before),
                opening_buckets=buckets,
            ),
            cfg,
        )
        results.append(period_result)
        buckets = period_result.closing_buckets

    return LossCarryforwardResult(periods=tuple(results), config=cfg)


__all__ = [
    "LossCarryforwardConfig",
    "LossCarryforwardBucket",
    "LossCarryforwardPeriodInput",
    "LossCarryforwardPeriodResult",
    "LossCarryforwardResult",
    "compute_loss_carryforward_period",
    "compute_loss_carryforward_schedule",
]
