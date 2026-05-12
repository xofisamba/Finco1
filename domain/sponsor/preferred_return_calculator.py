"""Phase 7C-2 — Preferred return calculator.

Deterministic preferred return accrual engine.
Pure function: no mutation, no side effects, no I/O.

Compounding conventions (from SponsorWaterfallTier):
  - ANNUAL   : accrual = opening_invested * hurdle_rate  (compounded once/year)
  - SIMPLE   : accrual = opening_invested * hurdle_rate * accrual_periods (no compounding)
  - SEMIANNUAL: accrual = opening_invested * ((1 + hurdle_rate)^0.5 - 1) per half-year

Hurdle satisfaction: once cumulative_accrued_pref >= cumulative_invested * hurdle_rate,
  hurdle_satisfied = True and stays True for all remaining periods.

No forward-looking projections. No distribution allocation. No promote logic.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from domain.sponsor.sponsor_waterfall_tier import (
    SponsorWaterfallTier,
    TierType,
    CompoundingConvention,
)
from domain.sponsor.preferred_return_result import (
    PreferredReturnAccrualEntry,
    PreferredReturnResult,
)

__all__ = [
    "PreferredReturnCalculatorInputs",
    "calculate_preferred_return",
]


# ── Input type ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PreferredReturnCalculatorInputs:
    """Inputs for preferred return accrual calculation.

    Attributes
    ----------
    tier : SponsorWaterfallTier
        PREFERRED_RETURN tier from Phase 7C-1 schema.
        Must have tier_type == TierType.PREFERRED_RETURN.
    cumulative_invested_by_period : list[float]
        Cumulative equity invested by sponsor at end of each period (kEUR).
        Index p = value at end of period p.
        Must be non-negative. Length = num_periods.
    distributions_by_period : list[float]
        Per-period distributions applied to preferred return balance at end of
        each period (kEUR). NOT cumulative — this is the delta distributed in
        each period. Length = num_periods.
        Must be non-negative.
    num_periods : int
        Number of semiannual periods to compute.

    Notes
    -----
    - cumulative_invested_by_period[p] - cumulative_invested_by_period[p-1]
      = equity injected in period p (>= 0 by construction)
    - distributions_by_period is cumulative; delta = distribution in that period
    - Both lists must have length == num_periods
    """
    tier: SponsorWaterfallTier
    cumulative_invested_by_period: tuple[float, ...]
    distributions_by_period: tuple[float, ...]
    num_periods: int

    def __post_init__(self):
        if not isinstance(self.tier, SponsorWaterfallTier):
            raise TypeError("tier must be SponsorWaterfallTier")
        if self.tier.tier_type != TierType.PREFERRED_RETURN:
            raise ValueError(
                f"tier.tier_type must be PREFERRED_RETURN, got {self.tier.tier_type.value}"
            )
        if not isinstance(self.cumulative_invested_by_period, (list, tuple)):
            raise TypeError("cumulative_invested_by_period must be list or tuple")
        if not isinstance(self.distributions_by_period, (list, tuple)):
            raise TypeError("distributions_by_period must be list or tuple")
        if len(self.cumulative_invested_by_period) != self.num_periods:
            raise ValueError(
                f"cumulative_invested_by_period length ({len(self.cumulative_invested_by_period)}) "
                f"must equal num_periods ({self.num_periods})"
            )
        if len(self.distributions_by_period) != self.num_periods:
            raise ValueError(
                f"distributions_by_period length ({len(self.distributions_by_period)}) "
                f"must equal num_periods ({self.num_periods})"
            )
        for i, val in enumerate(self.cumulative_invested_by_period):
            if not isinstance(val, (int, float)):
                raise TypeError(f"cumulative_invested_by_period[{i}] must be float")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"cumulative_invested_by_period[{i}] must be finite, got {val}")
        for i, val in enumerate(self.distributions_by_period):
            if not isinstance(val, (int, float)):
                raise TypeError(f"distributions_by_period[{i}] must be float")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"distributions_by_period[{i}] must be finite, got {val}")
        if not isinstance(self.num_periods, int) or self.num_periods <= 0:
            raise ValueError(f"num_periods must be positive int, got {self.num_periods}")


# ── Core accrual calculation ───────────────────────────────────────────────────

def _accrue_pref_simple(opening_invested: float, hurdle_rate: float, accrual_periods: float) -> float:
    """Simple interest accrual: no compounding."""
    return opening_invested * hurdle_rate * accrual_periods


def _accrue_pref_annual(opening_invested: float, hurdle_rate: float, accrual_periods: float) -> float:
    """Annual compounding accrual.

    Accrues for 1 full year = hurdle_rate on opening_invested.
    accrual_periods is ignored (always 1.0 for the annual period).
    """
    if accrual_periods < 0.5:
        return opening_invested * ((1 + hurdle_rate) ** accrual_periods - 1)
    return opening_invested * hurdle_rate


def _accrue_pref_semiannual(opening_invested: float, hurdle_rate: float, accrual_periods: float) -> float:
    """Semiannual compounding accrual.

    Per 6-month period: opening_invested * ((1 + hurdle_rate)^0.5 - 1)
    accrual_periods is the year-fraction for this period.
    """
    if accrual_periods <= 0.0:
        return 0.0
    periodic_rate = (1 + hurdle_rate) ** accrual_periods - 1
    return opening_invested * periodic_rate


def _accrue_pref(
    opening_invested: float,
    hurdle_rate: float,
    convention: CompoundingConvention,
    accrual_periods: float,
) -> float:
    """Dispatch accrual by compounding convention."""
    if convention == CompoundingConvention.SIMPLE:
        return _accrue_pref_simple(opening_invested, hurdle_rate, accrual_periods)
    elif convention == CompoundingConvention.ANNUAL:
        return _accrue_pref_annual(opening_invested, hurdle_rate, accrual_periods)
    elif convention == CompoundingConvention.SEMIANNUAL:
        return _accrue_pref_semiannual(opening_invested, hurdle_rate, accrual_periods)
    else:
        raise ValueError(f"Unknown compounding convention: {convention}")


# ── Main calculation function ─────────────────────────────────────────────────

def calculate_preferred_return(
    inputs: PreferredReturnCalculatorInputs,
) -> PreferredReturnResult:
    """Calculate per-period preferred return accrual.

    Pure function. Deterministic. No mutation.

    Parameters
    ----------
    inputs : PreferredReturnCalculatorInputs
        Tier + capital data for accrual calculation.

    Returns
    -------
    PreferredReturnResult
        Frozen result with per-period accrual entries and summary stats.

    Hurdle satisfaction logic
    -------------------------
    hurdle_satisfied = True when cumulative_accrued_pref_keur >=
        cumulative_invested * hurdle_rate_pa. Once True, stays True
        for all remaining periods (once hurdle is met it is never "unmet").

    Accrual base
    ------------
    opening_invested_capital_keur = max(0, cumulative_invested_by_period[p-1]) at period p.
    First period (p=0): opening_invested = cumulative_invested_by_period[0] (all injected at p=0).

    Accrual formula (per convention)
    -------------------------------
    SIMPLE    : opening_invested * hurdle_rate * accrual_periods
    ANNUAL    : opening_invested * hurdle_rate  (ignores accrual_periods, 1/year)
    SEMIANNUAL: opening_invested * ((1 + hurdle_rate)^accrual_periods - 1)
    """
    tier = inputs.tier
    hurdle_rate = tier.hurdle_rate_pa
    convention = tier.compounding_convention
    sponsor_code = tier.sponsor_shares[0].sponsor_code  # single sponsor for now

    entries: list[PreferredReturnAccrualEntry] = []
    cumulative_accrued_pref = 0.0
    cumulative_dist = 0.0
    hurdle_satisfied = False

    # Semiannual accrual period (6 months = 0.5 year)
    accrual_periods = 0.5

    for p in range(inputs.num_periods):
        # Opening invested capital at start of period p
        if p == 0:
            opening_invested = max(0.0, inputs.cumulative_invested_by_period[0])
        else:
            opening_invested = max(0.0, inputs.cumulative_invested_by_period[p - 1])

        # Equity injected during period p
        if p == 0:
            invested_delta = inputs.cumulative_invested_by_period[0]
        else:
            invested_delta = (
                inputs.cumulative_invested_by_period[p]
                - inputs.cumulative_invested_by_period[p - 1]
            )

        # Accrue preferred return for this period
        accrued = _accrue_pref(opening_invested, hurdle_rate, convention, accrual_periods)
        cumulative_accrued_pref += accrued

        # Cumulative invested through this period
        cumulative_invested = inputs.cumulative_invested_by_period[p]

        # Check hurdle satisfaction: cumulative_pref >= cumulative_invested * hurdle
        hurdle_threshold = cumulative_invested * hurdle_rate
        if not hurdle_satisfied and cumulative_accrued_pref >= hurdle_threshold - 1e-9:
            hurdle_satisfied = True

        # Per-period distribution (delta) applied at end of this period
        dist_this_period = inputs.distributions_by_period[p]
        cumulative_dist += dist_this_period

        # Unpaid preferred return balance = cumulative accrued - cumulative dist
        unpaid_pref = cumulative_accrued_pref - cumulative_dist

        entry = PreferredReturnAccrualEntry(
            period_index=p,
            opening_invested_capital_keur=opening_invested,
            invested_capital_delta_keur=invested_delta,
            hurdle_rate_pa=hurdle_rate,
            compounding_convention=convention.value,
            accrual_periods=accrual_periods,
            accrued_pref_keur=accrued,
            cumulative_accrued_pref_keur=cumulative_accrued_pref,
            cumulative_distributions_keur=cumulative_dist,
            unpaid_pref_balance_keur=unpaid_pref,
            hurdle_satisfied=hurdle_satisfied,
        )
        entries.append(entry)

    final_entry = entries[-1]
    return PreferredReturnResult(
        sponsor_code=sponsor_code,
        hurdle_rate_pa=hurdle_rate,
        compounding_convention=convention.value,
        entries=tuple(entries),
        total_accrued_pref_keur=cumulative_accrued_pref,
        total_unpaid_pref_keur=final_entry.unpaid_pref_balance_keur,
        all_periods_hurdle_satisfied=final_entry.hurdle_satisfied,
    )
