"""financial_engine.dsra.target — Dynamic DSRA required-balance schedule builder.

WORKBOOK SOURCE EVIDENCE:
  XLSM workbooks are not stored in this repository. The selector values,
  formulas and cached targets below were independently inspected from the
  read-only TUHO, Oborovo and KUPI source workbooks on 2026-08-20.

  TUHO (senior_ds_p1 = 2116.361394092063 kEUR,
                      senior_ds_p2 = 2151.439207253809 kEUR):
    Construction selector Inputs!I330 = 0.
    Operation selector Inputs!I331 = 0.
    Available DSRA coverage amounts (from Inputs tab 3m/6m/12m selectors):
      3m  = 1,058.1806970460316 kEUR = DS1 × 3/6
      6m  = 2,116.3613940920630 kEUR = DS1 × 6/6 = DS1
      12m = 4,267.8006013458730 kEUR = DS1 + DS2

  Oborovo (senior_ds_p1 = 2239.133412854356 kEUR,
                      senior_ds_p2 = 2202.625802862166 kEUR):
    Construction selector Inputs!I347 = 0.
    Operation selector Inputs!I348 = 0.
    Available DSRA coverage amounts (from Inputs tab 3m/6m/12m selectors):
      3m  = 1,119.566706427178 kEUR = DS1 × 3/6
      6m  = 2,239.133412854356 kEUR = DS1 × 6/6 = DS1
      12m = 4,441.759215716522 kEUR = DS1 + DS2

  KUPI:
    Construction selector Inputs!I330 = 0.
    Operation selector Inputs!I331 = 0 (Inputs!A331 = 6 is an option label).
    Available Operation targets: 3m = 3,688.3274356894 kEUR;
      6m = 7,376.6548713788 kEUR; 12m = 14,633.03819594164 kEUR.

  All three calibration projects have separate Construction and Operation
  selectors, both selected at 0 months. Their financial delta remains zero.

LEGACY IMPLEMENTATION CORROBORATION:
  finco_core/waterfall/dsra_engine.py compute_dsra_target():
      annual_ds = current_period_payment × periods_per_year
      dsra_target = annual_ds × (dsra_months / 12)
      → for 6m semi-annual: target = DS_current × 2 × 0.5 = DS_current ✓

  finco_core/debt/sculpting_iterative.py dsra_rolling_target():
      periods_needed = max(1, dsra_months × periods_per_year // 12)
      return sum(future_payments[:periods_needed])
      Note: integer-ceiling formula; time-coverage formula is the generic refinement
      that correctly handles 3m = 0.5 × 6m for semiannual periods.

MEASUREMENT DATE RULE (source-proven):
  The DSRA target at operating period t covers the current period t's DS plus
  upcoming DS within the coverage window.

  WORKBOOK PROOF: for semi-annual periods (6m each):
    DSRA_6m_target[op_0] = DS[op_0]  (current period's own DS)
    DSRA_3m_target[op_0] = 0.5 × DS[op_0]
    DSRA_12m_target[op_0] = DS[op_0] + DS[op_1]

  This proves j starts at i (INCLUDES current period), NOT at i+1.
  Interpretation: the target is set at the START of period i, covering DS
  to be paid DURING period i through the end of the coverage window.

  COVERAGE LOOP: for period i, j ∈ {i, i+1, i+2, ...}
    fraction_j = min(1.0, coverage_remaining / period_months_j)
    target += fraction_j × DS_j
    coverage_remaining -= fraction_j × period_months_j

  Semi-annual (6m period) examples:
    3m  → fraction at j=i = 3/6 = 0.5 → target = 0.5 × DS[i]
    6m  → fraction at j=i = 1.0 → target = DS[i]
    9m  → j=i full (6m→DS[i]) + j=i+1 partial (3m/6m=0.5→0.5×DS[i+1])
    12m → j=i full (6m→DS[i]) + j=i+1 full (6m→DS[i+1])

GENERIC ENGINE POLICY:
  Any positive integer coverage_months is supported by the time-coverage algorithm.
  Only 3m, 6m, 12m are source-proven from TUHO/Oborovo workbooks.
  9m and other values are ENGINE_GENERIC_CAPABILITY (not workbook-proven options).

POLICY ENUM:
  DsraTargetPolicy.FIXED_AMOUNT:
      required_balance = static scalar every operating period (PR-3 behavior).
      Used when requirement_keur is set explicitly and FORWARD policy is not elected.

  DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS:
      required_balance[t] = time-coverage sum of Senior DS from period t onwards.
      Used when dsra_months > 0, mode == CASH_DSRA, and dsra_target_policy explicitly set.

CONSTRUCTION / OPERATION AUTHORITY:
  Construction reserve funding is a separate workbook selector and bridge:
    TUHO/KUPI Macro!G24 = LOOKUP(Inputs!I330,Inputs!A329:A332,Inputs!D329:D332)
    Oborovo Macro!G24 = LOOKUP(Inputs!I347,Inputs!A346:A349,Inputs!D346:D349)
    DSRA_in = Macro!H24; Macro!E24 = ABS(H24-G24).
  CashDsraInput.requirement_keur carries that actual funded reserve cash.
  Operation selectors feed CF!B76 (TUHO/KUPI) or CF!B86 (Oborovo), and the
  dynamic schedule supplies operating targets only. Legacy dsra_months is an
  operation-only compatibility alias; it is not Construction funding authority.

SOURCE-PROVEN EXCESS RELEASE:
  The workbook CF Operation row includes an excess reduction when Beginning >=
  Target. This module computes targets only; financial_engine.dsra.model owns
  the cash/reserve roll-forward and release.
"""
from __future__ import annotations

import math
from datetime import date
from enum import Enum


class DsraTargetPolicy(Enum):
    """DSRA required-balance target policy.

    FIXED_AMOUNT:
        Static scalar requirement_keur used every operating period.
        Preserves PR-3 behavior. Backward-compatible default.

    FORWARD_DEBT_SERVICE_MONTHS:
        Per-period target = time-coverage sum of Senior DS from the start of
        period t, covering coverage_months months of debt service.
        Source-proven from TUHO and Oborovo workbook Inputs tab (3m/6m/12m options).
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
        result = full_months + remaining_start / days_in_partial + frac
        if result <= 0.0:
            # Edge case: start is last day of month, end is first day of next
            # (e.g. Dec 31 → Jan 1). Fall back to day-count approximation.
            days_elapsed = (end - start).days
            return days_elapsed / days_in_partial
        return result
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
        Expected positive-magnitude convention (unsigned cash outflow).
        Negative values are excluded from the coverage window (see sign-convention note).
    coverage_months:
        Number of months of Senior DS to cover starting from the current period.
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

    SIGN CONVENTION NOTE:
        senior_debt_service_keur must be in UNSIGNED POSITIVE magnitude
        (positive = cash outflow to service debt; 0 = no payment due).
        Negative values are rejected with DSRA_TARGET_NEGATIVE_SENIOR_DS.
        Refinancing is out of scope. Normalise sign at the adapter boundary.

    MEASUREMENT DATE RULE (source-proven from TUHO/Oborovo workbooks):
        For operating period t (index i), coverage STARTS AT period i (inclusive).
        The current period's DS (period t) IS included in the window.
        Target = sum over j ∈ {i, i+1, i+2, ...} of (fraction_j × DS_j)
        where fraction_j = min(1.0, coverage_remaining / period_months_j).
        This matches the workbook source evidence:
            6m target at first operating period = DS[first_op] (not DS[second_op]).
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

    # Validate Senior DS sign: all values must be >= 0 (unsigned positive magnitude).
    for i, ds in enumerate(senior_debt_service_keur):
        if not isinstance(ds, (int, float)) or isinstance(ds, bool):
            raise ValueError(
                f"DSRA_TARGET_INVALID_SENIOR_DS: senior_debt_service_keur[{i}]={ds!r} must be numeric."
            )
        if not math.isfinite(ds):
            raise ValueError(
                f"DSRA_TARGET_INVALID_SENIOR_DS: senior_debt_service_keur[{i}]={ds!r} must be finite."
            )
        if ds < 0.0:
            raise ValueError(
                f"DSRA_TARGET_NEGATIVE_SENIOR_DS: senior_debt_service_keur[{i}]={ds!r} is negative. "
                "DS must be unsigned positive magnitude (cash outflow). "
                "Refinancing is out of scope. Normalise sign at the adapter boundary."
            )

    # Validate dates: each period end > start; start dates strictly ascending.
    for i, (s, e) in enumerate(zip(period_start_dates, period_end_dates)):
        if e <= s:
            raise ValueError(
                f"DSRA_TARGET_INVALID_DATES: period_end_dates[{i}] ({e}) "
                f"<= period_start_dates[{i}] ({s}). End must be strictly after start."
            )
    for i in range(1, n):
        if period_start_dates[i] <= period_start_dates[i - 1]:
            raise ValueError(
                f"DSRA_TARGET_NON_CHRONOLOGICAL_PERIODS: period_start_dates[{i}] "
                f"({period_start_dates[i]}) <= period_start_dates[{i-1}] "
                f"({period_start_dates[i-1]}). Periods must be in strictly ascending order."
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

    # Pre-compute period lengths in months (for pro-rata coverage).
    # Construction periods are skipped in the inner loop; guard only operating periods.
    period_month_lengths: list[float] = []
    for idx_chk, (s, e, is_constr) in enumerate(zip(period_start_dates, period_end_dates, is_construction)):
        ml = months_between(s, e)
        if not is_constr and ml <= 0.0:
            raise ValueError(
                f"DSRA_TARGET_ZERO_PERIOD_LENGTH: operating period {idx_chk} "
                f"from {s} to {e} has computed length {ml:.4f} months. "
                "All operating periods must have positive length."
            )
        period_month_lengths.append(ml if ml > 0.0 else 1.0)  # 1.0 placeholder for construction

    targets: list[float] = []

    for i in range(n):
        if is_construction[i]:
            targets.append(0.0)
            continue

        # MEASUREMENT DATE RULE (source-proven):
        # Coverage window starts at period i (CURRENT period) and extends
        # forward until coverage_months is exhausted.
        # This matches TUHO/Oborovo workbook: 6m target[op_0] = DS[op_0].
        coverage_remaining = float(coverage_months)
        target = 0.0

        for j in range(i, n):
            if is_construction[j]:
                # Construction periods after operating ones are not expected, but
                # skip gracefully — construction has no DS to cover.
                continue
            ds_j = senior_debt_service_keur[j]
            period_len_j = period_month_lengths[j]
            fraction = min(1.0, coverage_remaining / period_len_j)
            target += fraction * ds_j
            coverage_remaining -= fraction * period_len_j
            if coverage_remaining <= 1e-9:
                break

        targets.append(target)

    return tuple(targets)
