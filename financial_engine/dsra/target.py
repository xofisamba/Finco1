"""financial_engine.dsra.target — Dynamic DSRA required-balance schedule builder.

SOURCE AUTHORITY:
  Legacy workbook formula (finco_core/waterfall/dsra_engine.py, dsra_engine.py):
      target[t] = annual_DS[t] × (dsra_months / 12)
      where annual_DS[t] = current_period_DS × periods_per_year

  This is equivalent to a FORWARD-LOOKING TIME-COVERAGE algorithm:
      Cover the next `dsra_months` months of Senior debt service,
      pro-rating partial coverage of the last period within the window.

  For semiannual periods (6 months each):
      3m coverage  → fraction 3/6 = 0.5 of next payment
      6m coverage  → fraction 6/6 = 1.0 of next payment
      9m coverage  → 1 full + 0.5 of next → 1.5 × avg_payment
      12m coverage → 2 full payments → sum(next two)

  For 12m the sum-of-next-two is more accurate than 2 × current when
  payments amortise (the two amounts may differ slightly).

  WORKBOOK_EVIDENCE:
    finco_core/waterfall/dsra_engine.py compute_dsra_target():
        annual_ds = current_period_payment × periods_per_year
        dsra_target = annual_ds × (dsra_months / 12)

    finco_core/debt/sculpting_iterative.py dsra_rolling_target():
        periods_needed = max(1, dsra_months × periods_per_year // 12)
        return sum(future_payments[:periods_needed])
    [Note: integer-ceiling formula; time-coverage formula is the generic refinement
     that correctly handles 3m = 0.5 × 6m for semiannual periods.]

  Oborovo workbook: Inputs!I348 = 0 (dsra_months=0 → no DSRA for Oborovo).
  TUHO workbook: no DSRA in production configuration (requirement_keur=0).
  Both projects are NONE-mode; this module is tested synthetically and via
  cross-verification with the legacy formula.

POLICY ENUM:
  DsraTargetPolicy.FIXED_AMOUNT:
      required_balance = static scalar every operating period (existing PR-3 behavior).
      Used when requirement_keur is set explicitly and no dsra_months coverage is desired.

  DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS:
      required_balance[t] = time-coverage sum of future Senior DS.
      Used when dsra_months > 0 and a Senior debt schedule is available.

MEASUREMENT DATE:
  The DSRA target at period t represents the buffer needed going INTO period t+1.
  Coverage is computed over future periods STARTING FROM period t+1.
  The current period t's DS has already been paid; it is excluded from the window.

COD FUNDING:
  The first-operating-period target is the funded amount (Project Use at construction close).
  For FORWARD_DEBT_SERVICE_MONTHS, COD funding = target at first operating period.
  This preserves the COD_FUNDING_HANDSHAKE invariant.

UNRESOLVED_RELEASE_POLICY:
  This module computes required targets only.
  Release timing remains unresolved; see financial_engine/dsra/model.py.
"""
from __future__ import annotations

import math
from datetime import date
from enum import Enum


class DsraTargetPolicy(Enum):
    """DSRA required-balance target policy.

    FIXED_AMOUNT:
        Static scalar requirement_keur used every operating period.
        Preserves PR-3 behavior.

    FORWARD_DEBT_SERVICE_MONTHS:
        Per-period target = time-coverage sum of future Senior DS within
        coverage_months from the measurement date (end of period t,
        covering future periods t+1, t+2, ...).
    """
    FIXED_AMOUNT = "fixed_amount"
    FORWARD_DEBT_SERVICE_MONTHS = "forward_debt_service_months"


def months_between(start: date, end: date) -> float:
    """Compute fractional months between two dates.

    Uses exact calendar month difference with day-fraction for partial months.
    For standard model periods (exact month boundaries), returns exact integers.
    """
    if end <= start:
        return 0.0
    full_months = (end.year - start.year) * 12 + (end.month - start.month)
    # Day adjustment: if end.day < start.day, the last month is partial
    if end.day < start.day:
        full_months -= 1
        # Fractional part of the remaining partial month
        import calendar
        days_in_end_month = calendar.monthrange(end.year, end.month)[1]
        frac = (end.day - 1) / days_in_end_month  # days since month start
        # Days in the partial start month
        days_in_partial = calendar.monthrange(
            (start.replace(day=1) if start.day > 1 else start).year,
            start.month,
        )[1]
        # Remaining days in start month after start.day
        remaining_start = days_in_partial - start.day
        return full_months + remaining_start / days_in_partial + frac
    elif end.day > start.day:
        import calendar
        days_in_start_month = calendar.monthrange(start.year, start.month)[1]
        frac = (end.day - start.day) / days_in_start_month
        return full_months + frac
    else:
        return float(full_months)


def build_dsra_required_balance_schedule(
    *,
    period_indices: tuple[int, ...],
    period_start_dates: tuple[date, ...],
    period_end_dates: tuple[date, ...],
    is_construction: tuple[bool, ...],
    senior_debt_service_keur: tuple[float, ...],
    coverage_months: int,
    policy: DsraTargetPolicy = DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS,
    fixed_amount_keur: float = 0.0,
) -> tuple[float, ...]:
    """Build DSRA required-balance schedule for all model periods.

    Parameters
    ----------
    period_indices:
        Period identifiers in chronological order (no gaps, no duplicates).
    period_start_dates:
        Start date of each period. Must be strictly ascending.
    period_end_dates:
        End date of each period. Must be strictly ascending. end > start for each period.
    is_construction:
        True for construction periods. Target is 0 for construction.
    senior_debt_service_keur:
        Senior debt service per period. Must be same length as period_indices.
        Typically ≥ 0; for construction periods the value is ignored in the target.
    coverage_months:
        Number of months of future Senior DS to cover.
        Must be > 0 for FORWARD_DEBT_SERVICE_MONTHS policy.
    policy:
        DsraTargetPolicy.FIXED_AMOUNT → fixed_amount_keur every operating period.
        DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS → dynamic time-coverage sum.
    fixed_amount_keur:
        Required when policy=FIXED_AMOUNT. Must be finite and >= 0.

    Returns
    -------
    Tuple of required balances, one per period (same length as period_indices).
    Construction periods always have required_balance = 0.

    Raises
    ------
    ValueError on:
        - Length mismatch
        - coverage_months <= 0 for FORWARD policy
        - Non-finite or negative fixed_amount
        - Non-ascending dates
        - end_date <= start_date for any period
        - Duplicate period indices

    MEASUREMENT DATE RULE:
        For operating period t (index i in sorted order), coverage is computed
        over all future operating periods t+1, t+2, ... (i+1, i+2, ...).
        The current period's DS (period t) is excluded from the target window
        because it has already been paid by the end of period t.
    """
    n = len(period_indices)
    if n == 0:
        return ()
    if len(period_start_dates) != n:
        raise ValueError(
            f"DSRA_TARGET_LENGTH_MISMATCH: period_start_dates length {len(period_start_dates)} "
            f"!= period_indices length {n}."
        )
    if len(period_end_dates) != n:
        raise ValueError(
            f"DSRA_TARGET_LENGTH_MISMATCH: period_end_dates length {len(period_end_dates)} "
            f"!= period_indices length {n}."
        )
    if len(is_construction) != n:
        raise ValueError(
            f"DSRA_TARGET_LENGTH_MISMATCH: is_construction length {len(is_construction)} "
            f"!= period_indices length {n}."
        )
    if len(senior_debt_service_keur) != n:
        raise ValueError(
            f"DSRA_TARGET_LENGTH_MISMATCH: senior_debt_service_keur length "
            f"{len(senior_debt_service_keur)} != period_indices length {n}."
        )

    # Validate no duplicate indices
    if len(set(period_indices)) != n:
        raise ValueError("DSRA_TARGET_DUPLICATE_PERIOD_INDICES: period_indices contains duplicates.")

    # Validate dates
    for i, (s, e) in enumerate(zip(period_start_dates, period_end_dates)):
        if e <= s:
            raise ValueError(
                f"DSRA_TARGET_INVALID_DATES: period_end_dates[{i}] ({e}) "
                f"<= period_start_dates[{i}] ({s}). End must be strictly after start."
            )

    if policy == DsraTargetPolicy.FIXED_AMOUNT:
        if not isinstance(fixed_amount_keur, (int, float)) or isinstance(fixed_amount_keur, bool):
            raise ValueError(
                f"DSRA_TARGET_INVALID_FIXED_AMOUNT: {fixed_amount_keur!r} must be numeric."
            )
        if not math.isfinite(fixed_amount_keur):
            raise ValueError(
                f"DSRA_TARGET_INVALID_FIXED_AMOUNT: {fixed_amount_keur!r} must be finite."
            )
        if fixed_amount_keur < 0.0:
            raise ValueError(
                f"DSRA_TARGET_INVALID_FIXED_AMOUNT: {fixed_amount_keur!r} must be >= 0."
            )
        return tuple(
            0.0 if is_constr else fixed_amount_keur
            for is_constr in is_construction
        )

    # FORWARD_DEBT_SERVICE_MONTHS policy
    if not isinstance(coverage_months, int) or isinstance(coverage_months, bool):
        raise ValueError(
            f"DSRA_TARGET_INVALID_COVERAGE_MONTHS: {coverage_months!r} must be an integer."
        )
    if coverage_months <= 0:
        raise ValueError(
            f"DSRA_TARGET_INVALID_COVERAGE_MONTHS: {coverage_months!r} must be > 0 "
            "for FORWARD_DEBT_SERVICE_MONTHS policy."
        )

    # Pre-compute period lengths in months (for pro-rata coverage)
    period_month_lengths: list[float] = []
    for s, e in zip(period_start_dates, period_end_dates):
        ml = months_between(s, e)
        if ml <= 0.0:
            raise ValueError(
                f"DSRA_TARGET_ZERO_PERIOD_LENGTH: period from {s} to {e} has "
                f"computed length {ml:.4f} months. All periods must have positive length."
            )
        period_month_lengths.append(ml)

    targets: list[float] = []

    for i in range(n):
        if is_construction[i]:
            targets.append(0.0)
            continue

        # Measurement date: end of period i. Coverage window: periods i+1, i+2, ...
        coverage_remaining = float(coverage_months)
        target = 0.0

        for j in range(i + 1, n):
            if is_construction[j]:
                # Construction periods after operating ones are not expected, but
                # skip them gracefully — don't count construction DS.
                continue
            ds_j = senior_debt_service_keur[j]
            if ds_j < 0.0:
                # Negative DS (e.g. refinancing receipts) — exclude from target.
                continue
            period_len_j = period_month_lengths[j]
            fraction = min(1.0, coverage_remaining / period_len_j)
            target += fraction * ds_j
            coverage_remaining -= fraction * period_len_j
            if coverage_remaining <= 1e-9:
                break

        targets.append(target)

    return tuple(targets)


def compute_cod_dsra_funding_keur(
    required_balance_schedule: tuple[float, ...],
    is_construction: tuple[bool, ...],
) -> float:
    """Compute the COD reserve funding requirement from the dynamic target schedule.

    Returns the required_balance at the first operating period. This is the amount
    that must be funded at construction close (as a Project Use) to satisfy the
    COD_FUNDING_HANDSHAKE invariant.

    If all periods are construction (no operating periods), returns 0.0.
    """
    if len(required_balance_schedule) != len(is_construction):
        raise ValueError(
            f"DSRA_COD_FUNDING_LENGTH_MISMATCH: schedule length "
            f"{len(required_balance_schedule)} != is_construction length {len(is_construction)}."
        )
    for i, is_constr in enumerate(is_construction):
        if not is_constr:
            return required_balance_schedule[i]
    return 0.0
