"""Typed result contract and production builder for cash/reserve interest income.

Produced by the orchestrator after solver convergence when computing per-period
financing income from a CashReserveInterestPolicy. Carried through to
TaxCalculationInput as PeriodFinancingIncomeInput entries.

Balance convention (source-proven for TUHO and Oborovo):
    PRIOR_PERIOD_CLOSING == CURRENT_PERIOD_OPENING
    i.e. the balance used for interest accrual is the closing balance of the
    PRIOR period (= the opening balance of the current period).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finco_core.inputs.cash_reserve_interest_policy import CashReserveInterestPolicy


@dataclass(frozen=True)
class UnrestrictedCashPeriodBalance:
    """Per-period unrestricted cash balance (opening and closing) in kEUR."""
    period_index: int
    period_start: date
    period_end: date
    opening_balance_keur: float   # = prior period closing (balance convention)
    closing_balance_keur: float
    is_eligible: bool             # True when post-debt and in project life
    authority: str                # "SOURCE_PROVEN" | "GENERIC_FINCO_POLICY" | "UNRESOLVED"


@dataclass(frozen=True)
class UnrestrictedCashSchedule:
    """Full-run unrestricted cash balance schedule across all operating periods.

    Built from:
    - min_unrestricted_cash_floor_keur: typed project input (e.g. 550 kEUR)
    - Senior debt outstanding status from SeniorDebtSchedules
    - SHL outstanding status (optional — post-debt means senior AND shl both zero)
    - in-life flag per period

    Economic identity (source-proven):
        TUHO:   CF!G135 = F135 + G122  (prior_cash + change_in_cash)
        Oborovo: CF!G144 = F144 + G132
    The clean engine approximation: eligible_cash = min_cash_floor when
    post-debt AND in-life, else 0.0 (all excess cash is assumed distributed).
    """
    period_balances: tuple[UnrestrictedCashPeriodBalance, ...]
    min_cash_floor_keur: float
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
    periods: tuple,                      # tuple[OperatingPeriodResult]
    min_cash_floor_keur: float,
    authority: str,
    senior_debt_outstanding_by_period: dict[int, float] | None = None,
    shl_outstanding_by_period: dict[int, float] | None = None,
) -> UnrestrictedCashSchedule:
    """Build per-period unrestricted cash balance from clean engine outputs.

    Eligibility rule (source-proven approximation):
        eligible = in_life AND senior_outstanding == 0 AND (shl_outstanding == 0 or shl not modeled)

    Balance convention: PRIOR_PERIOD_CLOSING == CURRENT_PERIOD_OPENING.
    Eligible periods use min_cash_floor_keur as both opening and closing balance
    (source-proven: 550 kEUR stable floor, all excess distributed).
    Ineligible periods use 0.0.

    Parameters
    ----------
    periods:
        All model periods (OperatingPeriodResult or similar duck-typed).
    min_cash_floor_keur:
        Typed project input — minimum maintained unrestricted cash (e.g. 550.0).
    authority:
        Authority string from the CashReserveInterestPolicy.
    senior_debt_outstanding_by_period:
        {period_index: outstanding_keur} from SeniorDebtSchedules.
        None means "no senior debt schedule available" → treat as post-debt.
    shl_outstanding_by_period:
        {period_index: outstanding_keur} from SHL schedules.
        None means "no SHL available" → ignored for eligibility.
    """
    balances: list[UnrestrictedCashPeriodBalance] = []

    for p in periods:
        idx: int = p.period_index  # type: ignore[attr-defined]
        p_start: date = p.period_start  # type: ignore[attr-defined]
        p_end: date = p.period_end  # type: ignore[attr-defined]
        in_life: bool = getattr(p, "is_operation", False)

        senior_out = (senior_debt_outstanding_by_period or {}).get(idx, 0.0)
        shl_out = (shl_outstanding_by_period or {}).get(idx, 0.0) if shl_outstanding_by_period is not None else 0.0

        post_debt = (senior_out < 1e-6) and (shl_out < 1e-6)
        eligible = in_life and post_debt

        balance = min_cash_floor_keur if eligible else 0.0
        balances.append(UnrestrictedCashPeriodBalance(
            period_index=idx,
            period_start=p_start,
            period_end=p_end,
            opening_balance_keur=balance,
            closing_balance_keur=balance,
            is_eligible=eligible,
            authority=authority,
        ))

    return UnrestrictedCashSchedule(
        period_balances=tuple(balances),
        min_cash_floor_keur=min_cash_floor_keur,
        authority=authority,
    )


def build_cash_reserve_interest_schedules(
    periods: tuple,
    policy: "CashReserveInterestPolicy",
    unrestricted_cash_schedule: UnrestrictedCashSchedule,
    dsra_balance_by_period: dict[int, float] | None = None,
) -> CashReserveInterestSchedules:
    """Build per-period cash/reserve interest income from policy and cash schedule.

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

    cash_by_period = {b.period_index: b for b in unrestricted_cash_schedule.period_balances}

    results: list[CashReserveInterestPeriodResult] = []
    total = 0.0

    for p in periods:
        idx: int = p.period_index  # type: ignore[attr-defined]
        p_start: date = p.period_start  # type: ignore[attr-defined]
        p_end: date = p.period_end  # type: ignore[attr-defined]

        if policy.authority == CashReserveInterestAuthority.UNRESOLVED or not policy.enabled:
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
                authority=policy.authority.value,
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
            authority=policy.authority.value,
        ))

    return CashReserveInterestSchedules(
        period_results=tuple(results),
        authority=policy.authority.value,
        total_financing_income_keur=total,
    )
