"""Phase 5D.1 distribution constraint result structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from domain.portfolio.distribution_constraints.inputs import DistributionBlockReason


@dataclass(frozen=True)
class DistributionConstraintPeriod:
    """Single period result for distribution constraint evaluation.

    Fields
    ------
    period : int
        Period index
    entity_code : str
        Entity identifier (SPV or HoldCo)
    cash_before_distribution_keur : float
        Cash available before distribution and constraint application.
    requested_distribution_keur : float
        Distribution requested by the waterfall (unchanged by this layer).
    allowed_distribution_keur : float
        Distribution allowed after constraint evaluation.
        Always <= requested_distribution_keur.
    retained_cash_keur : float
        Cash retained = cash_before - allowed_distribution.
        Always >= 0 when constraints are applied correctly.
    block_reasons : tuple[DistributionBlockReason, ...]
        Zero or more reasons for constraint application.
        Empty tuple means no constraint was applied.
    warnings : tuple[str, ...]
        Warning messages (e.g., negative cash detected).
    """
    period: int
    entity_code: str
    cash_before_distribution_keur: float
    requested_distribution_keur: float
    allowed_distribution_keur: float
    retained_cash_keur: float
    block_reasons: tuple[DistributionBlockReason, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self):
        if self.period < 0:
            raise ValueError(f"period must be >= 0, got {self.period}")
        if self.allowed_distribution_keur > self.requested_distribution_keur:
            raise ValueError(
                f"allowed_distribution_keur ({self.allowed_distribution_keur}) cannot exceed "
                f"requested_distribution_keur ({self.requested_distribution_keur})"
            )
        # Retained cash is the difference; may be negative if allow_negative_cash=True
        # and cash_before is negative. This is accepted at construction.


@dataclass(frozen=True)
class DistributionConstraintResult:
    """Per-entity distribution constraint evaluation result.

    Aggregates constraint evaluation across all periods for one entity.
    """
    entity_code: str
    periods: tuple[DistributionConstraintPeriod, ...] = field(default_factory=tuple)
    total_requested_distribution_keur: float = 0.0
    total_allowed_distribution_keur: float = 0.0
    total_retained_cash_keur: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # Aggregate totals from periods
        computed_requested = sum(p.requested_distribution_keur for p in self.periods)
        computed_allowed = sum(p.allowed_distribution_keur for p in self.periods)
        computed_retained = sum(p.retained_cash_keur for p in self.periods)

        # Only validate if explicitly zero (caller passed values); if periods exist,
        # trust the period-level constructor. Allow caller to pre-compute or pass 0.
        if self.periods and self.total_requested_distribution_keur == 0.0:
            object.__setattr__(self, 'total_requested_distribution_keur', computed_requested)
            object.__setattr__(self, 'total_allowed_distribution_keur', computed_allowed)
            object.__setattr__(self, 'total_retained_cash_keur', computed_retained)