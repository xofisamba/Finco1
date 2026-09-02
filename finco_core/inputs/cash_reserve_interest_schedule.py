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

Source interest formula (workbook):
    TUHO P&L!H20:    =(CF!G135>0)*$B19*CF!G135*H$5*H$6
    Oborovo P&L!G20: =(CF!F144>0)*$B19*CF!F144*G$5*G$6
    Components:
        (balance>0)  — structural guard (not an eligibility criterion)
        $B19         — deposit rate (1%, source-proven)
        CF!prior_col — prior-period closing cash (opening convention)
        H$5 / G$5    — project-life flag (boolean)
        H$6 / G$6    — period day fraction (actual/365)

Authority composition rule (H.4/I.9):
    final_authority = weakest(policy, unrestricted_cash_schedule, dsra_component)
    SOURCE_PROVEN policy + UNRESOLVED schedule → UNRESOLVED result → 0.0 income.

Debt-state gate (I.4):
    The source formula does NOT gate interest on senior/SHL outstanding.
    Account eligibility is a POLICY property.
    Balance being zero while debt is outstanding is a WATERFALL OUTCOME.
    build_unrestricted_cash_schedule does not accept senior/SHL parameters.

DSRA authority (I.6):
    dsra_balance_by_period = None means UNKNOWN balance — not zero.
    For ELIGIBLE DSRA: unknown balance → DSRA component authority UNRESOLVED.
    A known authoritative zero explicitly passed as {period: 0.0} is valid.
    When ELIGIBLE + non-UNRESOLVED authority is claimed, exact period-axis
    coverage is required; missing periods or invalid values → UNRESOLVED.

Opening cash (I.7 / K.4):
    opening_cash_keur: float | None — must be explicitly provided.
    None with authoritative increments → UNRESOLVED schedule authority.
    null ≠ zero: workbook CF!F135 = null (blank cell, NOT an explicit zero).
    Caller must pass 0.0 only after proving the project starts with zero cash;
    a workbook null is UNKNOWN, not source-proven zero.
    Bool, NaN, Inf → UNRESOLVED regardless of claimed authority.

Fixed-point boundary (K.10):
    This builder is a pure function of policy, authoritative_period_cash_increments,
    and opening_cash_keur. It does NOT model the causal feedback loop where interest
    income increases CFADS/FCF, which changes the cash increment, which changes next
    period's interest. Fixed-point iteration is the caller's responsibility.
    The distributable-profit accounting cap (CF113 Max formula) is also NOT
    implemented here — CASH_RESERVE_INTEREST_DISTRIBUTABLE_PROFIT_CAP_AUTHORITY_BLOCKED.

Day fraction (I.8):
    Uses canonical period.day_fraction when available on the period object.
    Falls back to (period_end - period_start).days / denominator when absent.

Authority validation (I.9):
    Only recognised authority strings are accepted.
    Unknown value → ValueError (caller must pass a valid authority).

Period-axis validation (J.7 / K.5):
    Duplicate period indices → UNRESOLVED (set() alone loses duplicates).
    Period axis of unrestricted_cash_schedule must exactly match the
    periods tuple passed to build_cash_reserve_interest_schedules in BOTH
    element identity AND ordering (ordered tuple comparison, not set equality).
    A SOURCE_PROVEN schedule with a missing, extra, or differently-ordered
    period axis must not silently produce zero interest income.

DSRA construction gate (K.6):
    Source formula P&L!H19 has (H$3>0) guard — Year > 0 means post-construction only.
    Construction periods (is_operation=False) must not accrue DSRA interest.
    The per-period loop gates DSRA accrual on period.is_operation.

Balance convention (K.7):
    Only OPENING balance convention is source-proven (prior-period closing).
    CLOSING and AVERAGE are not implemented. build_cash_reserve_interest_schedules
    fails closed (forces UNRESOLVED) when policy.balance_convention != OPENING.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finco_core.inputs.cash_reserve_interest_policy import CashReserveInterestPolicy

_VALID_AUTHORITIES = {"UNRESOLVED", "GENERIC_FINCO_POLICY", "SOURCE_PROVEN"}
_AUTHORITY_RANK = {"UNRESOLVED": 0, "GENERIC_FINCO_POLICY": 1, "SOURCE_PROVEN": 2}


def _validate_authority(authority: str) -> str:
    if authority not in _VALID_AUTHORITIES:
        raise ValueError(
            f"Unknown authority string {authority!r}. "
            f"Must be one of {sorted(_VALID_AUTHORITIES)}."
        )
    return authority


def _weakest_authority(*authorities: str) -> str:
    """Return the weakest (lowest rank) authority from the provided values."""
    return min(authorities, key=lambda a: _AUTHORITY_RANK[_validate_authority(a)])


@dataclass(frozen=True)
class UnrestrictedCashPeriodBalance:
    """Per-period unrestricted cash balance (opening and closing) in kEUR.

    Roll-forward identity:
        closing_balance_keur = opening_balance_keur + period_cash_increment_keur
        opening_balance_keur[p] = closing_balance_keur[p-1]

    is_eligible:
        True when the period is within project life AND the account is eligible
        per policy. Does NOT reflect debt-outstanding state — that is a waterfall
        outcome that determines the BALANCE, not the account eligibility.
    """
    period_index: int
    period_start: date
    period_end: date
    period_cash_increment_keur: float   # authoritative increment for this period
    opening_balance_keur: float         # = prior period closing (balance convention)
    closing_balance_keur: float         # = opening + increment
    is_eligible: bool                   # in project life AND account eligible per policy
    authority: str                      # "SOURCE_PROVEN" | "GENERIC_FINCO_POLICY" | "UNRESOLVED"


@dataclass(frozen=True)
class UnrestrictedCashSchedule:
    """Full-run unrestricted cash balance schedule across all operating periods.

    Economic identity (source-proven):
        TUHO:    CF!G135 = F135 + G122  (prior_cash + change_in_cash)
        Oborovo: CF!G144 = F144 + G132

    Authority:
        UNRESOLVED when no authoritative cash increments are provided, when
        the increment map has incomplete coverage, or when opening_cash is
        unknown.
    """
    period_balances: tuple[UnrestrictedCashPeriodBalance, ...]
    authority: str
    opening_cash_keur: float   # authoritative opening balance (period 0)


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
    day_fraction: float              # authoritative period day fraction
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
    opening_cash_keur: float | None = None,
) -> UnrestrictedCashSchedule:
    """Build per-period unrestricted cash balance from authoritative increments.

    Authority rules (I.5, I.7):
        - authoritative_period_cash_increments is None → UNRESOLVED
        - increment map is missing any required period index → UNRESOLVED
        - increment map has unexpected period indices → UNRESOLVED
        - any increment value is non-finite or a bool → UNRESOLVED
        - opening_cash_keur is None → UNRESOLVED
        - any of the above → schedule authority forced to UNRESOLVED

    Debt-state gate (I.4):
        Senior/SHL outstanding are NOT accepted as parameters. They do not
        determine account eligibility; they are waterfall inputs that determine
        the cash balance through the normal FCF/distribution chain.

    is_eligible:
        True when the period is within project life (is_operation=True).
        Account-level eligibility (ELIGIBLE/INELIGIBLE) is stored on the policy,
        not per-period on the balance schedule.

    Parameters
    ----------
    periods:
        All model periods (must have period_index, period_start, period_end,
        is_operation attributes). Ordering must match the period axis.
    authority:
        Claimed authority string. Must be one of VALID_AUTHORITIES.
        Overridden to UNRESOLVED whenever any validation check fails.
    authoritative_period_cash_increments:
        {period_index: cash_increment_keur} from the solver/waterfall.
        None → UNRESOLVED. Must cover exactly the set of period indices in
        `periods`. Missing or extra indices → UNRESOLVED.
    opening_cash_keur:
        Authoritative opening cash balance at period 0. Must be explicitly
        provided. None → UNRESOLVED. Source-proven zero is valid (pass 0.0).
    """
    import math as _math

    _validate_authority(authority)

    # J.7: detect duplicate period indices (set() alone hides duplicates).
    all_indices = [p.period_index for p in periods]  # type: ignore[attr-defined]
    required_indices = set(all_indices)
    effective_authority = authority

    # --- Validate all inputs; any failure forces UNRESOLVED ---
    if len(all_indices) != len(required_indices):
        # Duplicate period indices in the periods tuple.
        effective_authority = "UNRESOLVED"
    elif authoritative_period_cash_increments is None:
        effective_authority = "UNRESOLVED"
    elif opening_cash_keur is None:
        effective_authority = "UNRESOLVED"
    elif (
        isinstance(opening_cash_keur, bool)
        or not isinstance(opening_cash_keur, (int, float))
        or not _math.isfinite(float(opening_cash_keur))
    ):
        # J.7: opening cash must be a real finite number, not bool/NaN/Inf.
        effective_authority = "UNRESOLVED"
    else:
        provided_indices = set(authoritative_period_cash_increments.keys())
        if provided_indices != required_indices:
            effective_authority = "UNRESOLVED"
        else:
            for idx, v in authoritative_period_cash_increments.items():
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not _math.isfinite(v):
                    effective_authority = "UNRESOLVED"
                    break

    balances: list[UnrestrictedCashPeriodBalance] = []
    prior_closing = float(opening_cash_keur) if effective_authority != "UNRESOLVED" else 0.0

    for p in periods:
        idx: int = p.period_index  # type: ignore[attr-defined]
        p_start: date = p.period_start  # type: ignore[attr-defined]
        p_end: date = p.period_end  # type: ignore[attr-defined]
        in_life: bool = getattr(p, "is_operation", False)

        if effective_authority == "UNRESOLVED":
            increment = 0.0
            opening = 0.0
            closing = 0.0
        else:
            increment = authoritative_period_cash_increments[idx]  # type: ignore[index]
            opening = prior_closing
            closing = opening + increment

        balances.append(UnrestrictedCashPeriodBalance(
            period_index=idx,
            period_start=p_start,
            period_end=p_end,
            period_cash_increment_keur=increment,
            opening_balance_keur=opening,
            closing_balance_keur=closing,
            is_eligible=in_life,
            authority=effective_authority,
        ))
        prior_closing = closing

    return UnrestrictedCashSchedule(
        period_balances=tuple(balances),
        authority=effective_authority,
        opening_cash_keur=opening_cash_keur if opening_cash_keur is not None else 0.0,
    )


def build_cash_reserve_interest_schedules(
    periods: tuple,
    policy: "CashReserveInterestPolicy",
    unrestricted_cash_schedule: UnrestrictedCashSchedule,
    dsra_balance_by_period: dict[int, float] | None = None,
    dsra_balance_authority: str | None = None,
) -> CashReserveInterestSchedules:
    """Build per-period cash/reserve interest income from policy and cash schedule.

    Authority composition (H.4, I.9):
        composed_authority = weakest(policy.authority, schedule.authority,
                                     dsra_component_authority)

    DSRA balance authority (I.6):
        dsra_balance_by_period = None means UNKNOWN balance.
        For ELIGIBLE DSRA: unknown balance → dsra_component_authority = UNRESOLVED.
        dsra_balance_authority must be explicitly provided when eligible_dsra == ELIGIBLE
        and dsra_balance_by_period is not None.

    Day fraction (I.8):
        Uses canonical period.day_fraction when available.
        Falls back to (period_end - period_start).days / denominator.

    Parameters
    ----------
    periods:
        All model periods.
    policy:
        Source-proven or generic CashReserveInterestPolicy.
    unrestricted_cash_schedule:
        Built by build_unrestricted_cash_schedule().
    dsra_balance_by_period:
        {period_index: balance_keur} — DSRA opening balance per period.
        None = unknown (not the same as zero).
    dsra_balance_authority:
        Authority string for the DSRA balance data. Required when eligible_dsra
        == ELIGIBLE and dsra_balance_by_period is not None.
        None → UNRESOLVED for DSRA component when DSRA is ELIGIBLE.
    """
    import math as _math

    from finco_core.inputs.cash_reserve_interest_policy import (
        CashReserveInterestAuthority,
        EligibilityStatus,
    )

    # J.7: detect duplicate period indices in the interest-calculation periods tuple.
    all_interest_indices = [p.period_index for p in periods]  # type: ignore[attr-defined]
    interest_period_set = set(all_interest_indices)
    if len(all_interest_indices) != len(interest_period_set):
        # Duplicate period indices → fail closed.
        composed_authority = "UNRESOLVED"
        return CashReserveInterestSchedules(
            period_results=tuple(
                CashReserveInterestPeriodResult(
                    period_index=p.period_index,  # type: ignore[attr-defined]
                    period_start=p.period_start,  # type: ignore[attr-defined]
                    period_end=p.period_end,  # type: ignore[attr-defined]
                    eligible_unrestricted_cash_keur=0.0,
                    eligible_dsra_keur=0.0,
                    balance_convention=policy.balance_convention.value,
                    annual_rate=0.0,
                    day_count_convention=policy.day_count_convention.value,
                    day_fraction=0.0,
                    calculated_financing_income_keur=0.0,
                    authority="UNRESOLVED",
                )
                for p in periods
            ),
            authority="UNRESOLVED",
            total_financing_income_keur=0.0,
        )

    # K.5: cash schedule period axis must match in both elements AND ordering.
    # Set equality is insufficient — [0,2,1] vs [0,1,2] share the same set.
    schedule_index_tuple = tuple(b.period_index for b in unrestricted_cash_schedule.period_balances)
    interest_period_tuple = tuple(p.period_index for p in periods)  # type: ignore[attr-defined]
    cash_axis_mismatch = schedule_index_tuple != interest_period_tuple

    # K.7: Only OPENING balance convention is source-proven. Fail closed on others.
    if policy.balance_convention.value != "opening":
        return CashReserveInterestSchedules(
            period_results=tuple(
                CashReserveInterestPeriodResult(
                    period_index=p.period_index,  # type: ignore[attr-defined]
                    period_start=p.period_start,  # type: ignore[attr-defined]
                    period_end=p.period_end,  # type: ignore[attr-defined]
                    eligible_unrestricted_cash_keur=0.0,
                    eligible_dsra_keur=0.0,
                    balance_convention=policy.balance_convention.value,
                    annual_rate=0.0,
                    day_count_convention=policy.day_count_convention.value,
                    day_fraction=0.0,
                    calculated_financing_income_keur=0.0,
                    authority="UNRESOLVED",
                )
                for p in periods
            ),
            authority="UNRESOLVED",
            total_financing_income_keur=0.0,
        )

    # H.4 / I.9: weakest upstream authority.
    dsra_eligible = policy.eligible_dsra == EligibilityStatus.ELIGIBLE

    # DSRA component authority (J.7 hardening: exact-axis validation).
    if dsra_eligible:
        if dsra_balance_by_period is None:
            # Unknown balance for an eligible account → UNRESOLVED
            dsra_component_authority = "UNRESOLVED"
        elif dsra_balance_authority is None:
            # Balance provided but no authority stated → UNRESOLVED
            dsra_component_authority = "UNRESOLVED"
        else:
            _validate_authority(dsra_balance_authority)
            # Exact period-axis coverage required for authoritative DSRA data.
            dsra_indices = set(dsra_balance_by_period.keys())
            dsra_axis_ok = dsra_indices == interest_period_set
            dsra_values_ok = all(
                not isinstance(v, bool)
                and isinstance(v, (int, float))
                and _math.isfinite(v)
                for v in dsra_balance_by_period.values()
            )
            if dsra_axis_ok and dsra_values_ok:
                dsra_component_authority = dsra_balance_authority
            else:
                dsra_component_authority = "UNRESOLVED"
    else:
        # INELIGIBLE DSRA — balance is ignored, no authority constraint from DSRA
        dsra_component_authority = policy.authority.value

    # Apply cash-axis mismatch to composed authority.
    schedule_auth = "UNRESOLVED" if cash_axis_mismatch else unrestricted_cash_schedule.authority

    composed_authority = _weakest_authority(
        policy.authority.value,
        schedule_auth,
        dsra_component_authority,
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
                and policy.eligible_unrestricted_cash == EligibilityStatus.ELIGIBLE
                and cash_bal_entry.is_eligible)
            else 0.0
        )

        # J.7 / K.6: DSRA eligible and axis-validated; gate on is_operation (K.6).
        # Source: P&L!H19 has (H$3>0) guard — construction periods must not accrue.
        if policy.eligible_dsra == EligibilityStatus.ELIGIBLE and dsra_balance_by_period is not None:
            p_is_operation: bool = getattr(p, "is_operation", False)
            # KeyError would be a bug (axis validated above); construction → 0.0 per source gate
            dsra_raw = dsra_balance_by_period[idx] if p_is_operation else 0.0
        else:
            dsra_raw = 0.0
        dsra_eligible_keur = dsra_raw if policy.eligible_dsra == EligibilityStatus.ELIGIBLE else 0.0

        # I.8: Use canonical period day_fraction when available.
        canonical_day_frac = getattr(p, "day_fraction", None)
        if canonical_day_frac is not None and isinstance(canonical_day_frac, float):
            day_fraction = canonical_day_frac
        else:
            denominator = 365.0 if policy.day_count_convention.value == "actual_365" else 360.0
            day_fraction = (p_end - p_start).days / denominator

        income = policy.compute_period_income_keur(
            unrestricted_cash_balance_keur=cash_eligible,
            dsra_balance_keur=dsra_eligible_keur,
            day_fraction=day_fraction,
        )
        total += income

        results.append(CashReserveInterestPeriodResult(
            period_index=idx,
            period_start=p_start,
            period_end=p_end,
            eligible_unrestricted_cash_keur=cash_eligible,
            eligible_dsra_keur=dsra_eligible_keur,
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
