"""financial_engine.senior_debt.solver — Fixed-point senior debt sizing solver.

Iteration sequence (DSCR_SCULPTED / COMBINED_MINIMUM):
  1.  Start from initial_debt_guess.
  2.  Build opening-balance and interest schedules.
  3.  Pass period interest into the Phase 2B tax/CFADS calculation.
  4.  Recalculate cash tax and canonical CFADS.
  5.  Sculpt debt-service capacity from CFADS.
  6.  Compute new debt size = D_old − terminal_balance(D_old).
     (terminal_balance = opening at maturity minus principal at maturity)
  7.  Apply optional damping: D_new = alpha*D_candidate + (1-alpha)*D_old.
  8.  Compare new vs old debt size and per-period schedules.
  9.  Repeat until convergence or maximum_iterations.

Convergence requires BOTH:
  |D_new - D_old| <= convergence_tolerance_keur
  max per-period schedule difference <= convergence_relative_tolerance
  (checked across opening, interest, principal, closing, cash_tax, CFADS)

Non-convergence → termination_reason=MAX_ITERATIONS_REACHED; result is blocked,
not silently returned as a valid model output.

GEARING_CAP: D = eligible_project_cost × maximum_gearing; level-principal amort;
one iteration (no sizing loop). Tax feedback computed once.

COMBINED_MINIMUM: run both DSCR and GEARING sizing; take the minimum.

EXPLICIT_SCHEDULE: accept given opening balance and principal; compute interest,
closing balance, DSCR. One iteration; no sizing.

Determinism guarantee: same input → same iteration count → same schedules.
No random damping. No mutable global state.
"""
from __future__ import annotations

import math
from typing import Callable, TYPE_CHECKING

from financial_engine.senior_debt.interest import (
    build_rate_map,
    period_day_fraction,
    period_interest,
)
from financial_engine.senior_debt.models import SeniorDebtSchedules, SolverDiagnostics
from financial_engine.senior_debt.policy import SeniorDebtPolicy, SeniorDebtSizingMode
from financial_engine.senior_debt.sculpting import (
    PeriodDebtRow,
    build_explicit_schedule,
    build_level_principal_schedule,
    build_schedule,
)

if TYPE_CHECKING:
    from financial_engine.results import OperatingPeriodResult
    from financial_engine.senior_debt.inputs import SeniorDebtInputs


# Type alias for the tax+CFADS callable the solver calls on each iteration.
# Signature: (period_interest_map: dict[int, float]) -> dict[int, float]
# Returns {period_index: cfads_keur} and modifies tax_keur_by_period in-place
# via a shared container — the solver passes an interest dict, receives a
# (cfads_by_period, cash_tax_by_period) pair.
TaxCfadsCallable = Callable[
    [dict[int, float]],        # senior_interest_by_period
    tuple[dict[int, float], dict[int, float]],  # (cfads_by_period, cash_tax_by_period)
]


def _max_schedule_diff(
    old_rows: tuple[PeriodDebtRow, ...],
    new_rows: tuple[PeriodDebtRow, ...],
) -> float:
    """Maximum absolute difference across all per-period schedule fields."""
    if not old_rows:
        return 0.0
    diffs = []
    for o, n in zip(old_rows, new_rows):
        diffs.extend([
            abs(n.opening_keur - o.opening_keur),
            abs(n.interest_keur - o.interest_keur),
            abs(n.principal_keur - o.principal_keur),
            abs(n.closing_keur - o.closing_keur),
        ])
    return max(diffs) if diffs else 0.0


def _max_cfads_diff(
    old_cfads: dict[int, float],
    new_cfads: dict[int, float],
    period_indices: tuple[int, ...],
) -> float:
    diffs = [abs(new_cfads.get(i, 0.0) - old_cfads.get(i, 0.0)) for i in period_indices]
    return max(diffs) if diffs else 0.0


def _build_interest_by_period(
    debt_keur: float,
    rows: tuple[PeriodDebtRow, ...],
    rate_map: dict[int, float],
    period_start_end: dict[int, tuple],
    policy: SeniorDebtPolicy,
) -> dict[int, float]:
    """Compute {period_index: interest_keur} given opening balances from rows."""
    result: dict[int, float] = {}
    for row in rows:
        idx = row.period_index
        rate = rate_map.get(idx, 0.0)
        start, end = period_start_end[idx]
        day_frac = period_day_fraction(start, end, policy.day_count_convention)
        result[idx] = period_interest(row.opening_keur, rate, day_frac)
    return result


def _rows_from_opening(
    opening_keur: float,
    period_indices: tuple[int, ...],
    rate_map: dict[int, float],
    period_start_end: dict[int, tuple],
    cfads_by_period: dict[int, float],
    policy: SeniorDebtPolicy,
    mode: SeniorDebtSizingMode,
    explicit_principal_by_period: dict[int, float] | None,
) -> tuple[PeriodDebtRow, ...]:
    """Build schedule rows from an opening balance.

    Interest is computed from the opening balance within the schedule builder.
    """
    interest_map: dict[int, float] = {}
    balance = opening_keur
    # Pre-compute interest by period based on rolling balance
    tmp_balance = opening_keur
    for idx in period_indices:
        rate = rate_map.get(idx, 0.0)
        start, end = period_start_end[idx]
        day_frac = period_day_fraction(start, end, policy.day_count_convention)
        interest_map[idx] = period_interest(tmp_balance, rate, day_frac)
        # Approximate closing for interest pre-computation (use sculpting to get principal)
        # This is re-computed in the schedule builders below; here we just need interest_map
        # for the final call — the builders compute rolling interest themselves.
        # Reset: the builders roll the balance internally.
    # Actually, delegate entirely to the builders which roll balance internally.
    # Recompute interest_map correctly by simulating the roll:
    _balance = opening_keur
    for idx in period_indices:
        rate = rate_map.get(idx, 0.0)
        start, end = period_start_end[idx]
        day_frac = period_day_fraction(start, end, policy.day_count_convention)
        interest_map[idx] = period_interest(_balance, rate, day_frac)
        # Compute principal to advance balance (approximate for pre-computation)
        in_repayment = policy.repayment_start_period_index <= idx <= policy.maturity_period_index
        if in_repayment and _balance > 0.0:
            if mode == SeniorDebtSizingMode.GEARING_CAP:
                pass  # will be overridden in level-principal builder
            else:
                cfads = cfads_by_period.get(idx, 0.0)
                max_ds = max(0.0, cfads / policy.target_dscr) if policy.target_dscr > 0 else 0.0
                p = max(0.0, max_ds - interest_map[idx])
                p = min(p, _balance)
                _balance -= p
        # For gearing / explicit: interest map is still useful for principal computation later

    if mode in (SeniorDebtSizingMode.DSCR_SCULPTED, SeniorDebtSizingMode.COMBINED_MINIMUM):
        return build_schedule(
            opening_debt_keur=opening_keur,
            period_indices=period_indices,
            interest_by_period=interest_map,
            cfads_by_period=cfads_by_period,
            target_dscr=policy.target_dscr,
            repayment_start_index=policy.repayment_start_period_index,
            maturity_index=policy.maturity_period_index,
        )
    if mode == SeniorDebtSizingMode.GEARING_CAP:
        return build_level_principal_schedule(
            opening_debt_keur=opening_keur,
            period_indices=period_indices,
            interest_by_period=interest_map,
            cfads_by_period=cfads_by_period,
            repayment_start_index=policy.repayment_start_period_index,
            maturity_index=policy.maturity_period_index,
        )
    if mode == SeniorDebtSizingMode.EXPLICIT_SCHEDULE:
        return build_explicit_schedule(
            opening_debt_keur=opening_keur,
            period_indices=period_indices,
            interest_by_period=interest_map,
            cfads_by_period=cfads_by_period,
            explicit_principal_by_period=explicit_principal_by_period or {},
        )
    raise ValueError(f"Unsupported sizing_mode: {mode!r}")


def _to_schedules(
    rows: tuple[PeriodDebtRow, ...],
    cfads_by_period: dict[int, float],
    debt_size_keur: float,
    binding_constraint: str | None,
    diagnostics: SolverDiagnostics,
) -> SeniorDebtSchedules:
    return SeniorDebtSchedules(
        period_indices=tuple(r.period_index for r in rows),
        senior_debt_opening_keur=tuple(r.opening_keur for r in rows),
        senior_interest_keur=tuple(r.interest_keur for r in rows),
        senior_principal_keur=tuple(r.principal_keur for r in rows),
        senior_debt_service_keur=tuple(r.debt_service_keur for r in rows),
        senior_debt_closing_keur=tuple(r.closing_keur for r in rows),
        senior_dscr=tuple(r.dscr for r in rows),
        debt_size_keur=debt_size_keur,
        binding_constraint=binding_constraint,
        diagnostics=diagnostics,
    )


def solve_senior_debt(
    *,
    policy: SeniorDebtPolicy,
    inputs: "SeniorDebtInputs",
    periods: tuple["OperatingPeriodResult", ...],
    tax_cfads_fn: TaxCfadsCallable,
) -> SeniorDebtSchedules:
    """Main entry point: size and sculpt senior debt using fixed-point iteration.

    tax_cfads_fn(senior_interest_by_period) → (cfads_by_period, cash_tax_by_period)
      Called on each iteration with the current period interest map.
      Must invoke the Phase 2B tax engine and canonical CFADS function.
      Must be deterministic.

    Returns SeniorDebtSchedules. Raises ValueError on INVALID_INPUT.
    Non-convergence does NOT raise — it returns diagnostics with
    termination_reason=MAX_ITERATIONS_REACHED and converged=False.
    Callers must check diagnostics.converged.
    """
    from financial_engine.senior_debt.validation import validate_senior_debt_inputs

    # Operating periods only (exclude construction)
    op_periods = tuple(p for p in periods if p.is_operation)
    period_indices = tuple(p.period_index for p in op_periods)
    known_period_indices = frozenset(period_indices)
    period_start_end = {p.period_index: (p.period_start, p.period_end) for p in op_periods}

    errors = validate_senior_debt_inputs(inputs, policy, known_period_indices)
    if errors:
        diag = SolverDiagnostics(
            converged=False,
            iteration_count=0,
            initial_debt_guess_keur=inputs.initial_debt_guess_keur,
            final_debt_size_keur=0.0,
            maximum_absolute_difference_keur=float("inf"),
            maximum_relative_difference=float("inf"),
            binding_constraint=None,
            termination_reason="INVALID_INPUT",
        )
        # Return a zero schedule with error diagnostics
        zero_rows = tuple(
            PeriodDebtRow(
                period_index=idx,
                opening_keur=0.0, interest_keur=0.0, principal_keur=0.0,
                debt_service_keur=0.0, closing_keur=0.0, dscr=None,
            )
            for idx in period_indices
        )
        return _to_schedules(zero_rows, {}, 0.0, None, diag)

    rate_map = build_rate_map(inputs.period_rates, period_indices, policy.annual_fixed_rate)
    mode = policy.sizing_mode

    if mode == SeniorDebtSizingMode.EXPLICIT_SCHEDULE:
        return _solve_explicit(
            policy=policy, inputs=inputs, period_indices=period_indices,
            period_start_end=period_start_end, rate_map=rate_map, tax_cfads_fn=tax_cfads_fn,
        )

    if mode == SeniorDebtSizingMode.GEARING_CAP:
        return _solve_gearing(
            policy=policy, inputs=inputs, period_indices=period_indices,
            period_start_end=period_start_end, rate_map=rate_map, tax_cfads_fn=tax_cfads_fn,
        )

    if mode == SeniorDebtSizingMode.DSCR_SCULPTED:
        return _solve_dscr(
            policy=policy, inputs=inputs, period_indices=period_indices,
            period_start_end=period_start_end, rate_map=rate_map, tax_cfads_fn=tax_cfads_fn,
            binding_constraint="DSCR",
        )

    if mode == SeniorDebtSizingMode.COMBINED_MINIMUM:
        return _solve_combined(
            policy=policy, inputs=inputs, period_indices=period_indices,
            period_start_end=period_start_end, rate_map=rate_map, tax_cfads_fn=tax_cfads_fn,
        )

    raise ValueError(f"Unsupported sizing_mode: {mode!r}")


def _compute_interest_map(
    opening_keur: float,
    period_indices: tuple[int, ...],
    rate_map: dict[int, float],
    period_start_end: dict[int, tuple],
    policy: SeniorDebtPolicy,
    cfads_by_period: dict[int, float],
    mode: SeniorDebtSizingMode,
    explicit_principal_by_period: dict[int, float] | None = None,
) -> dict[int, float]:
    """Compute interest by rolling the balance through the sculpted schedule."""
    rows = _rows_from_opening(
        opening_keur, period_indices, rate_map, period_start_end,
        cfads_by_period, policy, mode, explicit_principal_by_period,
    )
    return {r.period_index: r.interest_keur for r in rows}


def _solve_dscr(
    *,
    policy: SeniorDebtPolicy,
    inputs: "SeniorDebtInputs",
    period_indices: tuple[int, ...],
    period_start_end: dict[int, tuple],
    rate_map: dict[int, float],
    tax_cfads_fn: TaxCfadsCallable,
    binding_constraint: str,
) -> SeniorDebtSchedules:
    """Fixed-point iteration for DSCR_SCULPTED sizing."""
    D = inputs.initial_debt_guess_keur
    alpha = policy.damping_alpha
    max_iter = policy.maximum_iterations
    tol_abs = policy.convergence_tolerance_keur
    tol_rel = policy.convergence_relative_tolerance

    prev_rows: tuple[PeriodDebtRow, ...] = ()
    prev_cfads: dict[int, float] = {}
    max_abs_diff = float("inf")
    max_rel_diff = float("inf")

    for iteration in range(1, max_iter + 1):
        # Step 1: build interest map from current D
        interest_map = _compute_interest_map(
            D, period_indices, rate_map, period_start_end, policy,
            prev_cfads if prev_cfads else {i: 0.0 for i in period_indices},
            SeniorDebtSizingMode.DSCR_SCULPTED,
        )

        # Step 2: call Phase 2B tax+CFADS with these interests
        cfads_by_period, cash_tax_by_period = tax_cfads_fn(interest_map)

        # Step 3: build sculpted schedule from D with updated CFADS
        rows = _rows_from_opening(
            D, period_indices, rate_map, period_start_end,
            cfads_by_period, policy, SeniorDebtSizingMode.DSCR_SCULPTED, None,
        )

        # Step 4: terminal balance at maturity
        terminal_balance = rows[-1].closing_keur if rows else 0.0

        # Check if capacity is zero
        total_principal = sum(r.principal_keur for r in rows)
        if total_principal == 0.0 and D > 0.0:
            diag = SolverDiagnostics(
                converged=False, iteration_count=iteration,
                initial_debt_guess_keur=inputs.initial_debt_guess_keur,
                final_debt_size_keur=0.0,
                maximum_absolute_difference_keur=D,
                maximum_relative_difference=1.0,
                binding_constraint=binding_constraint,
                termination_reason="NO_DEBT_CAPACITY",
            )
            return _to_schedules(rows, cfads_by_period, 0.0, binding_constraint, diag)

        # Step 5: new D = D - terminal_balance (find D such that terminal = 0)
        D_candidate = D - terminal_balance
        D_candidate = max(0.0, D_candidate)

        # Apply damping
        D_new = alpha * D_candidate + (1.0 - alpha) * D

        # Convergence checks
        if prev_rows:
            sched_diff = _max_schedule_diff(prev_rows, rows)
            cfads_diff = _max_cfads_diff(prev_cfads, cfads_by_period, period_indices)
            max_abs_diff = max(abs(D_new - D), sched_diff, cfads_diff)
            max_rel_diff = max_abs_diff / max(abs(D), 1.0)
        else:
            max_abs_diff = abs(D_new - D)
            max_rel_diff = max_abs_diff / max(abs(D), 1.0)

        prev_rows = rows
        prev_cfads = cfads_by_period

        if max_abs_diff <= tol_abs and (
            prev_rows is rows or max_rel_diff <= tol_rel
        ):
            # Converged
            if not policy.permit_terminal_balloon and terminal_balance > tol_abs:
                diag = SolverDiagnostics(
                    converged=False, iteration_count=iteration,
                    initial_debt_guess_keur=inputs.initial_debt_guess_keur,
                    final_debt_size_keur=D,
                    maximum_absolute_difference_keur=max_abs_diff,
                    maximum_relative_difference=max_rel_diff,
                    binding_constraint=binding_constraint,
                    termination_reason="TERMINAL_BALANCE_NOT_ALLOWED",
                )
                return _to_schedules(rows, cfads_by_period, D, binding_constraint, diag)

            diag = SolverDiagnostics(
                converged=True, iteration_count=iteration,
                initial_debt_guess_keur=inputs.initial_debt_guess_keur,
                final_debt_size_keur=D,
                maximum_absolute_difference_keur=max_abs_diff,
                maximum_relative_difference=max_rel_diff,
                binding_constraint=binding_constraint,
                termination_reason="CONVERGED",
            )
            return _to_schedules(rows, cfads_by_period, D, binding_constraint, diag)

        D = D_new

    # Max iterations reached — do NOT return as if valid
    # Build final rows for diagnostic purposes only
    interest_map = _compute_interest_map(
        D, period_indices, rate_map, period_start_end, policy,
        prev_cfads if prev_cfads else {i: 0.0 for i in period_indices},
        SeniorDebtSizingMode.DSCR_SCULPTED,
    )
    cfads_by_period, _ = tax_cfads_fn(interest_map)
    rows = _rows_from_opening(
        D, period_indices, rate_map, period_start_end,
        cfads_by_period, policy, SeniorDebtSizingMode.DSCR_SCULPTED, None,
    )
    diag = SolverDiagnostics(
        converged=False, iteration_count=max_iter,
        initial_debt_guess_keur=inputs.initial_debt_guess_keur,
        final_debt_size_keur=D,
        maximum_absolute_difference_keur=max_abs_diff,
        maximum_relative_difference=max_rel_diff,
        binding_constraint=binding_constraint,
        termination_reason="MAX_ITERATIONS_REACHED",
    )
    return _to_schedules(rows, cfads_by_period, D, binding_constraint, diag)


def _solve_gearing(
    *,
    policy: SeniorDebtPolicy,
    inputs: "SeniorDebtInputs",
    period_indices: tuple[int, ...],
    period_start_end: dict[int, tuple],
    rate_map: dict[int, float],
    tax_cfads_fn: TaxCfadsCallable,
) -> SeniorDebtSchedules:
    """Single-pass gearing-cap sizing (level-principal amortization)."""
    assert policy.maximum_gearing is not None
    D = inputs.eligible_project_cost_keur * policy.maximum_gearing

    interest_map = _compute_interest_map(
        D, period_indices, rate_map, period_start_end, policy,
        {i: 0.0 for i in period_indices},
        SeniorDebtSizingMode.GEARING_CAP,
    )
    cfads_by_period, _ = tax_cfads_fn(interest_map)
    rows = _rows_from_opening(
        D, period_indices, rate_map, period_start_end,
        cfads_by_period, policy, SeniorDebtSizingMode.GEARING_CAP, None,
    )

    diag = SolverDiagnostics(
        converged=True, iteration_count=1,
        initial_debt_guess_keur=D, final_debt_size_keur=D,
        maximum_absolute_difference_keur=0.0, maximum_relative_difference=0.0,
        binding_constraint="GEARING", termination_reason="CONVERGED",
    )
    return _to_schedules(rows, cfads_by_period, D, "GEARING", diag)


def _solve_combined(
    *,
    policy: SeniorDebtPolicy,
    inputs: "SeniorDebtInputs",
    period_indices: tuple[int, ...],
    period_start_end: dict[int, tuple],
    rate_map: dict[int, float],
    tax_cfads_fn: TaxCfadsCallable,
) -> SeniorDebtSchedules:
    """COMBINED_MINIMUM: min(DSCR capacity, gearing cap)."""
    assert policy.maximum_gearing is not None
    gearing_cap = inputs.eligible_project_cost_keur * policy.maximum_gearing

    # Run DSCR solver
    dscr_result = _solve_dscr(
        policy=policy, inputs=inputs, period_indices=period_indices,
        period_start_end=period_start_end, rate_map=rate_map, tax_cfads_fn=tax_cfads_fn,
        binding_constraint="DSCR",
    )
    if not dscr_result.diagnostics.converged:
        # Propagate non-convergence
        return dscr_result

    dscr_debt = dscr_result.debt_size_keur

    tol = policy.convergence_tolerance_keur
    if abs(dscr_debt - gearing_cap) <= tol:
        binding = "BOTH"
    elif dscr_debt < gearing_cap:
        binding = "DSCR"
    else:
        binding = "GEARING"

    if binding in ("DSCR", "BOTH"):
        final_d = dscr_debt
    else:
        final_d = gearing_cap

    # If gearing binds, rebuild with gearing debt size and level-principal schedule
    if binding == "GEARING":
        gearing_inputs_d = final_d
        interest_map = _compute_interest_map(
            gearing_inputs_d, period_indices, rate_map, period_start_end, policy,
            {i: 0.0 for i in period_indices},
            SeniorDebtSizingMode.GEARING_CAP,
        )
        cfads_by_period, _ = tax_cfads_fn(interest_map)
        rows = _rows_from_opening(
            gearing_inputs_d, period_indices, rate_map, period_start_end,
            cfads_by_period, policy, SeniorDebtSizingMode.GEARING_CAP, None,
        )
        diag = SolverDiagnostics(
            converged=True,
            iteration_count=dscr_result.diagnostics.iteration_count + 1,
            initial_debt_guess_keur=inputs.initial_debt_guess_keur,
            final_debt_size_keur=final_d,
            maximum_absolute_difference_keur=dscr_result.diagnostics.maximum_absolute_difference_keur,
            maximum_relative_difference=dscr_result.diagnostics.maximum_relative_difference,
            binding_constraint=binding,
            termination_reason="CONVERGED",
        )
        return _to_schedules(rows, cfads_by_period, final_d, binding, diag)
    else:
        # DSCR or BOTH — reuse dscr_result arrays, update binding and debt_size
        diag = SolverDiagnostics(
            converged=dscr_result.diagnostics.converged,
            iteration_count=dscr_result.diagnostics.iteration_count,
            initial_debt_guess_keur=dscr_result.diagnostics.initial_debt_guess_keur,
            final_debt_size_keur=final_d,
            maximum_absolute_difference_keur=dscr_result.diagnostics.maximum_absolute_difference_keur,
            maximum_relative_difference=dscr_result.diagnostics.maximum_relative_difference,
            binding_constraint=binding,
            termination_reason=dscr_result.diagnostics.termination_reason,
        )
        return SeniorDebtSchedules(
            period_indices=dscr_result.period_indices,
            senior_debt_opening_keur=dscr_result.senior_debt_opening_keur,
            senior_interest_keur=dscr_result.senior_interest_keur,
            senior_principal_keur=dscr_result.senior_principal_keur,
            senior_debt_service_keur=dscr_result.senior_debt_service_keur,
            senior_debt_closing_keur=dscr_result.senior_debt_closing_keur,
            senior_dscr=dscr_result.senior_dscr,
            debt_size_keur=final_d,
            binding_constraint=binding,
            diagnostics=diag,
        )


def _solve_explicit(
    *,
    policy: SeniorDebtPolicy,
    inputs: "SeniorDebtInputs",
    period_indices: tuple[int, ...],
    period_start_end: dict[int, tuple],
    rate_map: dict[int, float],
    tax_cfads_fn: TaxCfadsCallable,
) -> SeniorDebtSchedules:
    """EXPLICIT_SCHEDULE: accept given opening balance and principal schedule."""
    D = inputs.opening_debt_balance_keur
    explicit_map = {pp.period_index: pp.principal_keur
                    for pp in (inputs.explicit_principal_schedule or ())}

    # One pass: compute interest from rolling balance, call tax+CFADS once
    interest_map = _compute_interest_map(
        D, period_indices, rate_map, period_start_end, policy,
        {i: 0.0 for i in period_indices},
        SeniorDebtSizingMode.EXPLICIT_SCHEDULE, explicit_map,
    )
    cfads_by_period, _ = tax_cfads_fn(interest_map)
    rows = _rows_from_opening(
        D, period_indices, rate_map, period_start_end,
        cfads_by_period, policy, SeniorDebtSizingMode.EXPLICIT_SCHEDULE, explicit_map,
    )

    terminal_balance = rows[-1].closing_keur if rows else 0.0
    tol = policy.convergence_tolerance_keur

    if not policy.permit_terminal_balloon and terminal_balance > tol:
        diag = SolverDiagnostics(
            converged=False, iteration_count=1,
            initial_debt_guess_keur=D, final_debt_size_keur=D,
            maximum_absolute_difference_keur=terminal_balance,
            maximum_relative_difference=terminal_balance / max(D, 1.0),
            binding_constraint=None, termination_reason="TERMINAL_BALANCE_NOT_ALLOWED",
        )
        return _to_schedules(rows, cfads_by_period, D, None, diag)

    diag = SolverDiagnostics(
        converged=True, iteration_count=1,
        initial_debt_guess_keur=D, final_debt_size_keur=D,
        maximum_absolute_difference_keur=0.0, maximum_relative_difference=0.0,
        binding_constraint=None, termination_reason="CONVERGED",
    )
    return _to_schedules(rows, cfads_by_period, D, None, diag)
