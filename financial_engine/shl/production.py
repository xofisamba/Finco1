"""financial_engine.shl.production — Production SHL schedule chaining (C3B3D2B1).

Chains the C3B3D1 construction primitive and the C3B3D2B0 operating waterfall
into a single schedule function.

Construction period
-------------------
Uses financial_engine.shl.engine.compute_shl_period with:
    opening_balance_keur = 0.0         (no balance before draw)
    drawdown_keur        = draw        (full SHL funding at construction close)
    day_count_fraction   = 1.0         (ARITHMETIC_SOURCE_IMPLIED;
                                        CALENDAR_CONVENTION_UNRESOLVED — see below)
    annual_rate          = policy.annual_rate
    payment_mode         = ShlInterestPaymentMode.PIK
    scheduled_principal  = 0.0

Construction DCF = 1.0 is arithmetic-implied: gross / (draw × rate) = 1.0.
The exact calendar interval between construction open and close is unresolved
(potential 2-day gap at the construction/operating seam; C3B3D2B0 §6).
Do NOT infer ACT_365 or ACT_360 for construction from the operating convention.

Operating periods
-----------------
Uses financial_engine.shl.waterfall.compute_shl_waterfall_period with:
    opening_balance_keur      = prior closing balance (recursive roll-forward)
    annual_rate               = policy.annual_rate
    day_count_fraction        = compute_shl_dcf(start, end, policy.day_count_convention)
    cash_available_for_shl_keur = from caller (seam adapter, not from fixture)

The natural waterfall formula handles all modes arithmetically (no dispatch):
    cash_interest = min(cash_available, gross)
    capitalised   = gross - cash_interest
    principal     = max(0, min(remaining_cash, opening + capitalised))
    closing       = opening + capitalised - principal

Cash available lineage
----------------------
The caller is responsible for providing cash_available_for_shl_keur per period.
In production this comes from financial_engine.adapters.shl_cash_seam:

    candidate_cash[p] = CFADS[p] - senior_debt_service[p]

where CFADS = EBITDA - cash_tax (Phase 2B) and senior_debt_service is from
Phase 2C.  The Phase 2C-derived figure is candidate cash before unresolved
reserve adjustments.  The ordering of DSRA relative to SHL is not source-proven
in C3B3D2B1 (DSRA_ORDERING_UNRESOLVED).

Fixed-point boundary
--------------------
SHL gross interest SHOULD reduce taxable income (via PeriodInterestInput.shl_interest_keur).
In C3B3D2B1, SHL interest is NOT fed back into the Phase 2C fixed-point loop.
This introduces a small approximation (SHL_OUTSIDE_FIXED_POINT).
The SHL→tax→CFADS→senior_debt→cash_for_shl→SHL circular dependency is
documented but deferred to C3B3D2B2.

No project-name/code dispatch.  No DS25/DS40 hardcoding.  No source fixture reads.
No imports from app, finco_core waterfall, or any production runtime.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from financial_engine.shl.contracts import (
    ShlDayCountConvention,
    ShlInterestPaymentMode,
    ShlPeriodResult,
    ShlWaterfallPolicy,
)
from financial_engine.shl.day_count import compute_shl_dcf
from financial_engine.shl.engine import compute_shl_period
from financial_engine.shl.waterfall import (
    ShlWaterfallPeriodResult,
    compute_shl_waterfall_period,
)


@dataclass(frozen=True)
class ShlConstructionInput:
    """Inputs for the SHL construction period.

    Fields
    ------
    draw_keur : float
        Full SHL funding drawn at construction close. Must be > 0.
        Oborovo source value: 14,620.773894815633 kEUR (Inputs!D325).
    annual_rate : float
        Annual simple interest rate. Must be >= 0 and finite.
        Oborovo source value: 0.08 (Inputs!F328).
    dcf : float
        Day-count fraction for the construction period.
        Default 1.0: ARITHMETIC_SOURCE_IMPLIED; CALENDAR_CONVENTION_UNRESOLVED.
        gross = draw × annual_rate × dcf = draw × 0.08 × 1.0 (for Oborovo).
        Do not override without calendar-date proof.
    period_index : int
        0-based period index for this construction period. Default 0.
    """
    draw_keur: float
    annual_rate: float
    dcf: float = 1.0
    period_index: int = 0

    def __post_init__(self) -> None:
        _check_finite("draw_keur", self.draw_keur)
        _check_finite("annual_rate", self.annual_rate)
        _check_finite("dcf", self.dcf)
        if self.draw_keur <= 0:
            raise ValueError(
                f"draw_keur must be > 0, got {self.draw_keur!r}"
            )
        if self.annual_rate < 0:
            raise ValueError(
                f"annual_rate must be >= 0, got {self.annual_rate!r}"
            )
        if self.dcf <= 0:
            raise ValueError(
                f"dcf must be > 0, got {self.dcf!r}"
            )
        if not isinstance(self.period_index, int) or isinstance(self.period_index, bool):
            raise ValueError(
                f"period_index must be int, got {self.period_index!r}"
            )
        if self.period_index < 0:
            raise ValueError(
                f"period_index must be >= 0, got {self.period_index!r}"
            )


@dataclass(frozen=True)
class ShlOperatingPeriodInput:
    """Input for one operating period in the production SHL schedule.

    Fields
    ------
    period_index : int
        0-based period index. Must be > 0 for operating (construction is 0).
    period_start : date
        First calendar day of the period (inclusive).
    period_end : date
        Last calendar day of the period (inclusive).
        SHL uses inclusive end-date convention throughout (proven C3B3D2B0).
    cash_available_for_shl_keur : float
        Cash available for SHL service this period (from the FCF waterfall above
        SHL: CFADS - senior_debt_service).  In production this comes from
        financial_engine.adapters.shl_cash_seam.compute_shl_cash_from_phase2c.
        For PIK/full-capitalisation periods: 0.0.
        Must be >= 0 and finite.
    drawdown_keur : float
        Additional SHL funding drawn in this operating period. Normally 0.0
        (no post-construction draws).  Must be >= 0.
    """
    period_index: int
    period_start: date
    period_end: date
    cash_available_for_shl_keur: float
    drawdown_keur: float = 0.0


@dataclass(frozen=True)
class ShlFullScheduleResult:
    """Result of compute_shl_schedule: construction + all operating periods.

    Fields
    ------
    construction : ShlPeriodResult
        Result for the construction period (C3B3D1 engine: opening=0, draw).
    operating : tuple[ShlWaterfallPeriodResult, ...]
        Results for all operating periods (C3B3D2B0 waterfall, natural formula).
        Indexed in the same order as the operating_periods input sequence.

    Balance continuity:
        operating[0].opening_balance_keur == construction.closing_balance_keur
        operating[n].opening_balance_keur == operating[n-1].closing_balance_keur
    """
    construction: ShlPeriodResult
    operating: tuple[ShlWaterfallPeriodResult, ...]


def compute_shl_schedule(
    construction: ShlConstructionInput,
    operating_periods: Sequence[ShlOperatingPeriodInput],
    policy: ShlWaterfallPolicy,
) -> ShlFullScheduleResult:
    """Compute the full SHL schedule from construction through all operating periods.

    The function chains two SHL computation primitives:

    1. Construction (C3B3D1 engine):
         compute_shl_period(opening=0, draw, dcf=1.0, PIK, principal=0)
         → ShlPeriodResult with closing_balance = draw + PIK interest

    2. Operating (C3B3D2B0 waterfall):
         For each period p in operating_periods:
           dcf = compute_shl_dcf(p.start, p.end, policy.day_count_convention)
           compute_shl_waterfall_period(
               opening = prior_closing,
               annual_rate = policy.annual_rate,
               day_count_fraction = dcf,
               cash_available = p.cash_available_for_shl_keur,
           )

    Parameters
    ----------
    construction : ShlConstructionInput
        Construction period inputs (draw, rate, DCF=1.0).
    operating_periods : Sequence[ShlOperatingPeriodInput]
        Operating period inputs in chronological order.  The function does
        NOT require contiguous period_index values — it chains on closing
        balance, not on period_index.
    policy : ShlWaterfallPolicy
        Annual rate and day-count convention for operating periods.

    Returns
    -------
    ShlFullScheduleResult

    Raises
    ------
    ValueError
        Any input validation failure from construction inputs, operating period
        inputs, or the underlying period computation functions.
    """
    if not isinstance(policy, ShlWaterfallPolicy):
        raise ValueError(
            f"policy must be ShlWaterfallPolicy, got {type(policy).__name__}"
        )

    # Rate consistency: construction and operating must use the same annual rate.
    # For FIXED rate mode, a silently diverging rate introduces unauditable errors.
    if construction.annual_rate != policy.annual_rate:
        raise ValueError(
            f"compute_shl_schedule: construction.annual_rate "
            f"({construction.annual_rate!r}) != policy.annual_rate "
            f"({policy.annual_rate!r}). For FIXED SHL rate mode both must "
            f"be identical. Correct the caller; do not introduce a patch rate."
        )

    # Step 1: Construction period via C3B3D1 engine.
    # opening=0, drawdown=draw, DCF=construction.dcf, PIK, principal=0
    constr_result = compute_shl_period(
        opening_balance_keur=0.0,
        drawdown_keur=construction.draw_keur,
        day_count_fraction=construction.dcf,
        annual_rate=construction.annual_rate,
        payment_mode=ShlInterestPaymentMode.PIK,
        scheduled_principal_keur=0.0,
        period_index=construction.period_index,
    )

    # Step 2: Operating periods via C3B3D2B0 waterfall (natural formula).
    operating_results: list[ShlWaterfallPeriodResult] = []
    opening = constr_result.closing_balance_keur

    for op in operating_periods:
        # Validate operating period inputs
        _check_finite("cash_available_for_shl_keur", op.cash_available_for_shl_keur)
        _check_finite("drawdown_keur", op.drawdown_keur)  # type check before value check below
        if op.cash_available_for_shl_keur < 0:
            raise ValueError(
                f"cash_available_for_shl_keur must be >= 0, got "
                f"{op.cash_available_for_shl_keur!r} (period_index={op.period_index})"
            )
        # Fail closed on non-zero operating draws: post-construction SHL draws
        # require an auditable roll-forward proof not yet implemented.
        # Oborovo: drawdown_keur = 0 for all 40 operating periods (proven).
        if op.drawdown_keur != 0.0:
            raise ValueError(
                f"compute_shl_schedule: operating period drawdown_keur must be "
                f"0.0 (post-construction SHL draws are not yet supported). "
                f"Got {op.drawdown_keur!r} at period_index={op.period_index}. "
                f"Support for operating draws is deferred to a future stage."
            )

        effective_opening = opening

        # Compute day-count fraction from calendar dates via typed convention.
        dcf = compute_shl_dcf(op.period_start, op.period_end, policy.day_count_convention)

        result = compute_shl_waterfall_period(
            opening_balance_keur=effective_opening,
            annual_rate=policy.annual_rate,
            day_count_fraction=dcf,
            cash_available_for_shl_keur=op.cash_available_for_shl_keur,
            period_index=op.period_index,
        )
        operating_results.append(result)
        opening = result.closing_balance_keur

    return ShlFullScheduleResult(
        construction=constr_result,
        operating=tuple(operating_results),
    )


def _check_finite(name: str, value: object) -> None:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a float, not bool: {value!r}")
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric, got {type(value).__name__}")
    if not math.isfinite(value):  # type: ignore[arg-type]
        raise ValueError(f"{name} must be finite, got {value!r}")
