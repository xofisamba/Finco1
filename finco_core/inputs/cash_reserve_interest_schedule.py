"""Typed result contract and production builder for cash/reserve interest income.

Produced by the orchestrator after solver convergence when computing per-period
financing income from a CashReserveInterestPolicy. Carried through to
TaxCalculationInput as PeriodFinancingIncomeInput entries.

Balance convention (source-proven for TUHO and Oborovo):
    PRIOR_PERIOD_CLOSING == CURRENT_PERIOD_OPENING
    i.e. the balance used for interest accrual is the closing balance of the
    PRIOR period (= the opening balance of the current period).

Roll-forward identity (source-proven):
    TUHO:    CF!G135 = CF!F135 + CF!G122  (prior_cash + change_in_cash)
    Oborovo: CF!G144 = CF!F144 + CF!G132

Authority composition rule (H.4):
    final_authority = weakest(policy.authority, schedule.authority)
    SOURCE_PROVEN policy + UNRESOLVED schedule → UNRESOLVED result → 0.0 income.
    No authoritative cash increments → schedule is UNRESOLVED.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finco_core.inputs.cash_reserve_interest_policy import CashReserveInterestPolicy

_AUTHORITY_RANK = {"UNRESOLVED": 0, "GENERIC_FINCO_POLICY": 1, "SOURCE_PROVEN": 2}


def _weakest_authority(a: str, b: str) -> str:
    return a if _AUTHORITY_RANK.get(a, 0) <= _AUTHORITY_RANK.get(b, 0) else b


@dataclass(frozen=True)
class UnrestrictedCashPeriodBalance:
    """Per-period unrestricted cash balance (opening and closing) in kEUR.

    Roll-forward identity:
        closing_balance_keur = opening_balance_keur + period_cash_increment_keur
        opening_balance_keur[p] = closing_balance_keur[p-1]
    """
    period_index: int
    period_start: date
    period_end: date
    period_cash_increment_keur: float  # authoritative increment for this period
    opening_balance_keur: float        # = prior period closing (balance convention)
    closing_balance_keur: float        # = opening + increment
    is_eligible: bool                  # True when post-debt and in project life
    authority: str                     # "SOURCE_PROVEN" | "GENERIC_FINCO_POLICY" | "UNRESOLVED"


@dataclass(frozen=True)
class UnrestrictedCashSchedule:
    """Full-run unrestricted cash balance schedule across all operating periods.

    Economic identity (source-proven):
        TUHO:    CF!G135 = F135 + G122  (prior_cash + change_in_cash)
        Oborovo: CF!G144 = F144 + G132

    Authority:
        UNRESOLVED when no authoritative cash increments are provided.
        Authority is carried into build_cash_reserve_interest_schedules and
        composed with policy authority via the weakest-upstream rule.
    """
    period_balances: tuple[UnrestrictedCashPeriodBalance, ...]
    authority: str


@dataclass(frozen=True)
class CashReserveInterestPeriodResult:
    """Per-period result of cash/reserve interest income computation."""
    period_index: int
    period_start: date
    period_end: date
    eligible_unrestricted_cash_keur: float
    eligible_dsra_keur: float
    balance_convention: str          # "opening" | "closing" | "average"
    annual_rate: float               # deposit rate, e.g. 0.01 for 1%
    day_count_convention: str        # "actual_365" | "actual_360"
    day_fraction: float              # (period_end - period_start).days / denominator
    calculated_financing_income_keur: float
    authority: str                   # "UNRESOLVED" | "GENERIC_FINCO_POLICY" | "SOURCE_PROVEN"


@dataclass(frozen=True)
class CashReserveInterestSchedules:
    """Full-run result for cash/reserve interest income across all model periods."""
    period_results: tuple[CashReserveInterestPeriodResult, ...]
    authority: str                   # overall authority level (worst-case across periods)
    total_financing_income_keur: float


def build_unrestricted_cash_schedule(
    periods: tuple,
    authority: str,
    authoritative_period_cash_increments: dict[int, float] | None = None,
    senior_debt_outstanding_by_period: dict[int, float] | None = None,
    shl_outstanding_by_period: dict[int, float] | None = None,
) -> UnrestrictedCashSchedule:
    """Build per-period unrestricted cash balance from authoritative increments.

    When authoritative_period_cash_increments is None, the schedule authority
    is forced to UNRESOLVED regardless of the authority parameter — no
    authoritative balance can be established without increment data.

    Roll-forward identity:
        closing[p] = opening[p] + increment[p]
        opening[p] = closing[p-1]
        opening[0] = 0.0

    Eligibility rule:
        eligible = in_life AND senior_outstanding == 0
                   AND (shl_outstanding == 0 or shl not modeled)

    Parameters
    ----------
    periods:
        All model periods (OperatingPeriodResult or similar duck-typed).
    authority:
        Authority string from the CashReserveInterestPolicy. Overridden to
        UNRESOLVED when authoritative_period_cash_increments is None.
    authoritative_period_cash_increments:
        {period_index: cash_increment_keur} from the solver/waterfall.
        None → UNRESOLVED schedule authority; all balances = 0.0.
    senior_debt_outstanding_by_period:
        {period_index: outstanding_keur} from SeniorDebtSchedules.
        None means no senior debt schedule available → treat as post-debt.
    shl_outstanding_by_period:
        {period_index: outstanding_keur} from SHL schedules.
        None means no SHL → ignored for eligibility.
    """
    if authoritative_period_cash_increments is None:
        effective_authority = "UNRESOLVED"
    else:
        effective_authority = authority

    balances: list[UnrestrictedCashPeriodBalance] = []
    prior_closing = 0.0

    for p in periods:
        idx: int = p.period_index  # type: ignore[attr-defined]
        p_start: date = p.period_start  # type: ignore[attr-defined]
        p_end: date = p.period_end  # type: ignore[attr-defined]
        in_life: bool = getattr(p, "is_operation", False)

        senior_out = (senior_debt_outstanding_by_period or {}).get(idx, 0.0)
        shl_out = (
            (shl_outstanding_by_period or {}).get(idx, 0.0)
            if shl_outstanding_by_period is not None else 0.0
        )

        post_debt = (senior_out < 1e-6) and (shl_out < 1e-6)
        eligible = in_life and post_debt

        if effective_authority == "UNRESOLVED" or authoritative_period_cash_increments is None:
            increment = 0.0
            opening = 0.0
            closing = 0.0
        else:
            increment = (authoritative_period_cash_increments or {}).get(idx, 0.0)
            opening = prior_closing
            closing = opening + increment

        balances.append(UnrestrictedCashPeriodBalance(
            period_index=idx,
            period_start=p_start,
            period_end=p_end,
            period_cash_increment_keur=increment,
            opening_balance_keur=opening,
            closing_balance_keur=closing,
            is_eligible=eligible,
            authority=effective_authority,
        ))
        prior_closing = closing

    return UnrestrictedCashSchedule(
        period_balances=tuple(balances),
        authority=effective_authority,
    )


def build_cash_reserve_interest_schedules(
    periods: tuple,
    policy: "CashReserveInterestPolicy",
    unrestricted_cash_schedule: UnrestrictedCashSchedule,
    dsra_balance_by_period: dict[int, float] | None = None,
) -> CashReserveInterestSchedules:
    """Build per-period cash/reserve interest income from policy and cash schedule.

    Authority composition (H.4):
        result_authority = weakest(policy.authority, schedule.authority)
        SOURCE_PROVEN policy + UNRESOLVED schedule → UNRESOLVED → 0.0 income.

    Parameters
    ----------
    periods:
        All model periods (OperatingPeriodResult or similar duck-typed).
    policy:
        Source-proven or generic CashReserveInterestPolicy.
    unrestricted_cash_schedule:
        Built by build_unrestricted_cash_schedule().
    dsra_balance_by_period:
        {period_index: balance_keur} — DSRA opening balance per period.
        Source-proven: DSRA is zero for all periods (TUHO and Oborovo).
        None → uses 0.0 for all periods.

    Returns
    -------
    CashReserveInterestSchedules with financing income per period.
    """
    from finco_core.inputs.cash_reserve_interest_policy import (
        CashReserveInterestAuthority,
        EligibilityStatus,
    )

    # H.4: weakest upstream authority determines result authority.
    composed_authority = _weakest_authority(
        policy.authority.value,
        unrestricted_cash_schedule.authority,
    )

    cash_by_period = {b.period_index: b for b in unrestricted_cash_schedule.period_balances}

    results: list[CashReserveInterestPeriodResult] = []
    total = 0.0

    for p in periods:
        idx: int = p.period_index  # type: ignore[attr-defined]
        p_start: date = p.period_start  # type: ignore[attr-defined]
        p_end: date = p.period_end  # type: ignore[attr-defined]

        if composed_authority == "UNRESOLVED" or not policy.enabled:
            results.append(CashReserveInterestPeriodResult(
                period_index=idx,
                period_start=p_start,
                period_end=p_end,
                eligible_unrestricted_cash_keur=0.0,
                eligible_dsra_keur=0.0,
                balance_convention=policy.balance_convention.value,
                annual_rate=0.0,
                day_count_convention=policy.day_count_convention.value,
                day_fraction=0.0,
                calculated_financing_income_keur=0.0,
                authority=composed_authority,
            ))
            continue

        cash_bal_entry = cash_by_period.get(idx)
        cash_eligible = (
            cash_bal_entry.opening_balance_keur
            if (cash_bal_entry is not None
                and policy.eligible_unrestricted_cash == EligibilityStatus.ELIGIBLE)
            else 0.0
        )

        dsra_raw = (dsra_balance_by_period or {}).get(idx, 0.0)
        dsra_eligible = (
            dsra_raw
            if policy.eligible_dsra == EligibilityStatus.ELIGIBLE
            else 0.0
        )

        # Day fraction: actual/365 or actual/360
        period_days = (p_end - p_start).days
        denominator = 365.0 if policy.day_count_convention.value == "actual_365" else 360.0
        day_fraction = period_days / denominator

        income = policy.compute_period_income_keur(
            unrestricted_cash_balance_keur=cash_eligible,
            dsra_balance_keur=dsra_eligible,
            day_fraction=day_fraction,
        )
        total += income

        results.append(CashReserveInterestPeriodResult(
            period_index=idx,
            period_start=p_start,
            period_end=p_end,
            eligible_unrestricted_cash_keur=cash_eligible,
            eligible_dsra_keur=dsra_eligible,
            balance_convention=policy.balance_convention.value,
            annual_rate=policy.annual_rate,
            day_count_convention=policy.day_count_convention.value,
            day_fraction=day_fraction,
            calculated_financing_income_keur=income,
            authority=composed_authority,
        ))

    return CashReserveInterestSchedules(
        period_results=tuple(results),
        authority=composed_authority,
        total_financing_income_keur=total,
    )
