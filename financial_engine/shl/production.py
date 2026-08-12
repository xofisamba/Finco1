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
from typing import TYPE_CHECKING, Sequence

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

if TYPE_CHECKING:  # pragma: no cover
    from financial_engine.inputs import ShareholderLoanModelInput
    from financial_engine.results import OperatingPeriodResult, ShareholderLoanSchedules


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


def compute_shareholder_loan_schedules(
    periods: Sequence["OperatingPeriodResult"],
    shl_input: "ShareholderLoanModelInput",
    cash_available_for_shl_before_reserves_keur: Sequence[float],
    *,
    diagnostics: "object",
) -> "ShareholderLoanSchedules":
    """Build immutable SHL audit vectors from backend-authoritative cash.

    ONE_CANONICAL_SHL_CALCULATION_KERNEL: this adapter delegates construction
    arithmetic to ``compute_shl_period`` and operating sweep arithmetic to
    ``compute_shl_waterfall_period``. It does not duplicate the SHL formula.
    """
    from financial_engine.inputs import ShareholderLoanModelInput
    from financial_engine.results import ShareholderLoanSchedules

    if not isinstance(shl_input, ShareholderLoanModelInput):
        raise ValueError(
            "compute_shareholder_loan_schedules: shl_input must be ShareholderLoanModelInput"
        )
    if len(periods) != len(cash_available_for_shl_before_reserves_keur):
        raise ValueError(
            "compute_shareholder_loan_schedules: periods and cash availability "
            "vectors must have equal length"
        )
    if not periods:
        raise ValueError("compute_shareholder_loan_schedules: at least one period is required")
    _validate_shareholder_loan_input(shl_input)

    period_indices: list[int] = []
    opening_values: list[float] = []
    drawdown_values: list[float] = []
    gross_values: list[float] = []
    cash_interest_values: list[float] = []
    pik_values: list[float] = []
    principal_values: list[float] = []
    service_values: list[float] = []
    closing_values: list[float] = []
    cash_available_values: list[float] = []
    cash_remaining_values: list[float] = []

    draw_consumed = False
    construction_result: ShlPeriodResult | None = None
    operating_inputs: list[ShlOperatingPeriodInput] = []
    for p, raw_cash in zip(periods, cash_available_for_shl_before_reserves_keur):
        _check_finite("cash_available_for_shl_before_reserves_keur", raw_cash)
        if raw_cash < 0.0:
            raise ValueError(
                f"cash_available_for_shl_before_reserves_keur must be >= 0.0, "
                f"got {raw_cash!r} at period_index={p.period_index}"
            )

        period_indices.append(p.period_index)
        if p.is_construction and not draw_consumed:
            construction = ShlConstructionInput(
                draw_keur=shl_input.initial_principal_keur,
                annual_rate=shl_input.annual_fixed_rate,
                dcf=shl_input.construction_day_count_fraction,
                period_index=p.period_index,
            )
            policy = ShlWaterfallPolicy(
                annual_rate=shl_input.annual_fixed_rate,
                day_count_convention=shl_input.day_count_convention,
            )
            construction_result = compute_shl_schedule(
                construction=construction,
                operating_periods=(),
                policy=policy,
            ).construction
            draw_consumed = True
            opening = construction_result.opening_balance_keur
            drawdown = shl_input.initial_principal_keur
            gross = construction_result.gross_accrued_interest_keur
            cash_interest = construction_result.cash_interest_keur
            pik = construction_result.pik_interest_keur
            principal = construction_result.scheduled_principal_keur
            service = cash_interest + principal
            closing = construction_result.closing_balance_keur
            cash_available = 0.0
        else:
            if construction_result is None:
                raise ValueError(
                    "compute_shareholder_loan_schedules: construction period "
                    "must precede operating periods for current single-draw SHL"
                )
            cash_available = raw_cash
            if p.period_index < shl_input.repayment_start_period_index:
                preliminary = compute_shl_schedule(
                    construction=ShlConstructionInput(
                        draw_keur=shl_input.initial_principal_keur,
                        annual_rate=shl_input.annual_fixed_rate,
                        dcf=shl_input.construction_day_count_fraction,
                        period_index=periods[0].period_index,
                    ),
                    operating_periods=tuple(operating_inputs + [
                        ShlOperatingPeriodInput(
                            period_index=p.period_index,
                            period_start=p.period_start,
                            period_end=p.period_end,
                            cash_available_for_shl_keur=cash_available,
                        )
                    ]),
                    policy=ShlWaterfallPolicy(
                        annual_rate=shl_input.annual_fixed_rate,
                        day_count_convention=shl_input.day_count_convention,
                    ),
                ).operating[-1]
                cash_available = min(cash_available, preliminary.gross_accrued_interest_keur)

            op_input = ShlOperatingPeriodInput(
                period_index=p.period_index,
                period_start=p.period_start,
                period_end=p.period_end,
                cash_available_for_shl_keur=cash_available,
            )
            operating_inputs.append(op_input)
            schedule = compute_shl_schedule(
                construction=ShlConstructionInput(
                    draw_keur=shl_input.initial_principal_keur,
                    annual_rate=shl_input.annual_fixed_rate,
                    dcf=shl_input.construction_day_count_fraction,
                    period_index=periods[0].period_index,
                ),
                operating_periods=tuple(operating_inputs),
                policy=ShlWaterfallPolicy(
                    annual_rate=shl_input.annual_fixed_rate,
                    day_count_convention=shl_input.day_count_convention,
                ),
            )
            result = schedule.operating[-1]
            opening = result.opening_balance_keur
            drawdown = 0.0
            gross = result.gross_accrued_interest_keur
            cash_interest = result.cash_interest_keur
            pik = result.pik_interest_keur
            principal = result.principal_repaid_keur
            service = result.shl_service_keur
            closing = result.closing_balance_keur

        if p.period_index == shl_input.maturity_period_index and closing > (
            shl_input.convergence_tolerance_keur + 1e-9
        ):
            raise ValueError(
                "SHL_MATURITY_RESIDUAL_FAILS_CLOSED: "
                f"closing balance {closing:.12f} kEUR remains at maturity "
                f"period_index={p.period_index}"
            )

        opening_values.append(opening)
        drawdown_values.append(drawdown)
        gross_values.append(gross)
        cash_interest_values.append(cash_interest)
        pik_values.append(pik)
        principal_values.append(principal)
        service_values.append(service)
        closing_values.append(closing)
        cash_available_values.append(cash_available)
        cash_remaining_values.append(max(0.0, cash_available - service))

    return ShareholderLoanSchedules(
        period_indices=tuple(period_indices),
        shl_opening_keur=tuple(opening_values),
        shl_drawdown_keur=tuple(drawdown_values),
        shl_gross_interest_keur=tuple(gross_values),
        shl_cash_interest_keur=tuple(cash_interest_values),
        shl_pik_interest_keur=tuple(pik_values),
        shl_principal_keur=tuple(principal_values),
        shl_debt_service_keur=tuple(service_values),
        shl_closing_keur=tuple(closing_values),
        cash_available_for_shl_before_reserves_keur=tuple(cash_available_values),
        cash_remaining_after_shl_before_reserves_keur=tuple(cash_remaining_values),
        diagnostics=diagnostics,
    )


def _validate_shareholder_loan_input(shl_input: "ShareholderLoanModelInput") -> None:
    _check_finite("initial_principal_keur", shl_input.initial_principal_keur)
    _check_finite("annual_fixed_rate", shl_input.annual_fixed_rate)
    _check_finite(
        "construction_day_count_fraction",
        shl_input.construction_day_count_fraction,
    )
    if shl_input.initial_principal_keur <= 0.0:
        raise ValueError("initial_principal_keur must be > 0.0")
    if shl_input.annual_fixed_rate < 0.0:
        raise ValueError("annual_fixed_rate must be >= 0.0")
    if shl_input.construction_day_count_fraction <= 0.0:
        raise ValueError("construction_day_count_fraction must be > 0.0")
    if shl_input.maximum_iterations <= 0:
        raise ValueError("maximum_iterations must be > 0")
    if shl_input.convergence_tolerance_keur < 0.0:
        raise ValueError("convergence_tolerance_keur must be >= 0.0")
    if shl_input.convergence_relative_tolerance < 0.0:
        raise ValueError("convergence_relative_tolerance must be >= 0.0")
    if shl_input.repayment_start_period_index < 0:
        raise ValueError("repayment_start_period_index must be >= 0")
    if shl_input.maturity_period_index < shl_input.repayment_start_period_index:
        raise ValueError("maturity_period_index must be >= repayment_start_period_index")
