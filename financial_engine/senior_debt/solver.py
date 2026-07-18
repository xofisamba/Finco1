"""financial_engine.senior_debt.solver — Fixed-point senior debt sizing solver.

Iteration sequence (DSCR_SCULPTED / COMBINED_MINIMUM):
  1.  Start from initial_debt_guess.
  2.  Forward-roll the schedule to get per-period interest (rolling balance).
  3.  Pass period interest into the Phase 2B tax/CFADS calculation.
  4.  Recalculate cash tax and canonical CFADS.
  5.  Backward-induct DSCR capacity from the updated CFADS.
  6.  Apply optional damping: D_new = alpha*D_candidate + (1-alpha)*D_old.
  7.  Compare |D_new - D_old| and per-period CFADS/tax diffs.
  8.  Repeat until convergence or maximum_iterations.

Convergence requires:
  max(|D_new - D_old|, max_cfads_diff, max_cash_tax_diff) <= convergence_tolerance_keur

Non-convergence → termination_reason=MAX_ITERATIONS_REACHED; result has
is_authoritative=False.

GEARING_CAP: D = eligible_project_cost × maximum_gearing; level-principal amort;
one iteration (no sizing loop). Tax feedback computed once.

COMBINED_MINIMUM: run DSCR sizing loop to convergence, then apply gearing cap and
take the minimum; forward roll with DSCR-sculpted repayment at that final D.

EXPLICIT_SCHEDULE: validate that explicit schedule sums to opening balance (within
tolerance); forward roll once with exact explicit principals; no sizing loop.

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
# Signature: (period_interest_map: dict[int, float]) -> (cfads_by_period, cash_tax_by_period)
TaxCfadsCallable = Callable[
    [dict[int, float]],        # senior_interest_by_period
    tuple[dict[int, float], dict[int, float]],  # (cfads_by_period, cash_tax_by_period)
]


# ---------------------------------------------------------------------------
# Helper: max absolute difference across two period-keyed dicts
# ---------------------------------------------------------------------------

def _max_dict_diff(
    a: dict[int, float],
    b: dict[int, float],
    period_indices: tuple[int, ...],
) -> float:
    diffs = [abs(a.get(i, 0.0) - b.get(i, 0.0)) for i in period_indices]
    return max(diffs) if diffs else 0.0


# ---------------------------------------------------------------------------
# Helper: repayment method string for a given policy / mode
# ---------------------------------------------------------------------------

def _repayment_method_for_mode(
    policy: SeniorDebtPolicy,
    mode: SeniorDebtSizingMode | None = None,
) -> str:
    effective_mode = mode if mode is not None else policy.sizing_mode
    if effective_mode == SeniorDebtSizingMode.GEARING_CAP:
        return "level_principal"
    if effective_mode == SeniorDebtSizingMode.EXPLICIT_SCHEDULE:
        return "explicit"
    # DSCR_SCULPTED and COMBINED_MINIMUM both use sculpted repayment
    return "dscr_sculpted"


# ---------------------------------------------------------------------------
# BLOCKER 1: Backward DSCR capacity via backward induction
# ---------------------------------------------------------------------------

def _backward_dscr_capacity(
    cfads_by: dict[int, float],
    rate_map: dict[int, float],
    period_start_end: dict[int, tuple],
    period_indices: tuple[int, ...],
    policy: SeniorDebtPolicy,
) -> float:
    """Compute maximum debt capacity via backward induction.

    Starting from closing_maturity = 0, work backwards:
      opening_t = (closing_t + ds_t) / (1 + f_t)
    where ds_t = max(0, cfads_t / target_dscr) and f_t = rate_t * day_frac_t.
    """
    repayment_ids = [
        idx for idx in period_indices
        if policy.repayment_start_period_index <= idx <= policy.maturity_period_index
    ]
    if not repayment_ids:
        return 0.0

    closing = 0.0
    for idx in reversed(repayment_ids):
        ds = max(0.0, cfads_by.get(idx, 0.0) / policy.target_dscr) if policy.target_dscr > 0 else 0.0
        rate = rate_map.get(idx, 0.0)
        start, end = period_start_end[idx]
        f = rate * period_day_fraction(start, end, policy.day_count_convention)
        denom = 1.0 + f
        opening = (closing + ds) / denom if denom > 1e-15 else closing + ds
        closing = max(0.0, opening)

    return closing


# ---------------------------------------------------------------------------
# BLOCKER 2: Authoritative forward roll (single pass, rolling balance)
# ---------------------------------------------------------------------------

def _forward_roll(
    opening_keur: float,
    period_indices: tuple[int, ...],
    rate_map: dict[int, float],
    period_start_end: dict[int, tuple],
    cfads_by: dict[int, float],
    policy: SeniorDebtPolicy,
    repayment_method_str: str,
    explicit_by: dict[int, float] | None = None,
) -> tuple[PeriodDebtRow, ...]:
    """Single-pass authoritative forward roll.

    Interest is computed from the rolling balance — the identity of this function.
    """
    rows: list[PeriodDebtRow] = []
    balance = opening_keur

    repayment_ids = [
        idx for idx in period_indices
        if policy.repayment_start_period_index <= idx <= policy.maturity_period_index
    ]
    n_repayment = len(repayment_ids)
    level_installment = opening_keur / n_repayment if n_repayment > 0 else 0.0

    for idx in period_indices:
        rate = rate_map.get(idx, 0.0)
        start, end = period_start_end[idx]
        day_frac = period_day_fraction(start, end, policy.day_count_convention)
        interest = balance * rate * day_frac  # ROLLING BALANCE — identity test

        in_repayment = (
            policy.repayment_start_period_index <= idx <= policy.maturity_period_index
        )

        if not in_repayment:
            principal = 0.0
        elif repayment_method_str == "dscr_sculpted":
            cfads = cfads_by.get(idx, 0.0)
            ds = max(0.0, cfads / policy.target_dscr) if policy.target_dscr > 0 else 0.0
            principal = max(0.0, ds - interest)
            principal = min(principal, balance)  # safety floor
        elif repayment_method_str == "level_principal":
            principal = min(level_installment, balance)
        elif repayment_method_str == "explicit":
            # NO CAPPING per Blocker 5 — exact explicit schedule
            principal = (explicit_by or {}).get(idx, 0.0)
        else:
            raise ValueError(f"Unknown repayment_method_str: {repayment_method_str!r}")

        debt_service = interest + principal
        closing = max(0.0, balance - principal)

        cfads_val = cfads_by.get(idx, 0.0)
        dscr_val = (
            cfads_val / debt_service
            if debt_service > 0.0 and math.isfinite(cfads_val)
            else None
        )

        rows.append(PeriodDebtRow(
            period_index=idx,
            opening_keur=balance,
            interest_keur=interest,
            principal_keur=principal,
            debt_service_keur=debt_service,
            closing_keur=closing,
            dscr=dscr_val,
        ))
        balance = closing

    return tuple(rows)


# ---------------------------------------------------------------------------
# Diagnostic factory
# ---------------------------------------------------------------------------

def _make_diag(
    *,
    converged: bool,
    iteration: int,
    initial_guess: float,
    final_d: float,
    max_abs_diff: float,
    binding: str | None,
    termination_reason: str,
) -> SolverDiagnostics:
    return SolverDiagnostics(
        converged=converged,
        iteration_count=iteration,
        initial_debt_guess_keur=initial_guess,
        final_debt_size_keur=final_d,
        maximum_absolute_difference_keur=max_abs_diff,
        maximum_relative_difference=max_abs_diff / max(abs(final_d), 1.0),
        binding_constraint=binding,
        termination_reason=termination_reason,
        is_authoritative=(termination_reason == "CONVERGED"),
    )


# ---------------------------------------------------------------------------
# Schedule → SeniorDebtSchedules
# ---------------------------------------------------------------------------

def _to_schedules(
    rows: tuple[PeriodDebtRow, ...],
    debt_size_keur: float,
    binding: str | None,
    diag: SolverDiagnostics,
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
        binding_constraint=binding,
        diagnostics=diag,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

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
    termination_reason=MAX_ITERATIONS_REACHED and is_authoritative=False.
    Callers must check diagnostics.is_authoritative.
    """
    from financial_engine.senior_debt.validation import validate_senior_debt_inputs

    # Operating periods only (exclude construction)
    op_periods = tuple(p for p in periods if p.is_operation)
    period_indices = tuple(p.period_index for p in op_periods)
    known_period_indices = frozenset(period_indices)
    period_start_end = {p.period_index: (p.period_start, p.period_end) for p in op_periods}

    errors = validate_senior_debt_inputs(inputs, policy, known_period_indices)
    if errors:
        diag = _make_diag(
            converged=False, iteration=0,
            initial_guess=inputs.initial_debt_guess_keur,
            final_d=0.0, max_abs_diff=float("inf"),
            binding=None, termination_reason="INVALID_INPUT",
        )
        zero_rows = tuple(
            PeriodDebtRow(
                period_index=idx,
                opening_keur=0.0, interest_keur=0.0, principal_keur=0.0,
                debt_service_keur=0.0, closing_keur=0.0, dscr=None,
            )
            for idx in period_indices
        )
        return _to_schedules(zero_rows, 0.0, None, diag)

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


# ---------------------------------------------------------------------------
# BLOCKER 4: DSCR convergence loop (tracks debt, cfads, cash_tax)
# ---------------------------------------------------------------------------

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
    """Fixed-point iteration for DSCR_SCULPTED sizing using backward induction."""
    D = inputs.initial_debt_guess_keur
    alpha = policy.damping_alpha
    max_iter = policy.maximum_iterations
    tol = policy.convergence_tolerance_keur

    cfads_by: dict[int, float] = {idx: 0.0 for idx in period_indices}
    cash_tax_by: dict[int, float] = {idx: 0.0 for idx in period_indices}

    prev_D: float | None = None
    prev_cfads: dict[int, float] | None = None
    prev_cash_tax: dict[int, float] | None = None
    max_abs_diff = float("inf")

    for iteration in range(1, max_iter + 1):
        # Step 1: forward roll to get interest (using current cfads_by for DSCR sculpting)
        rows = _forward_roll(
            D, period_indices, rate_map, period_start_end,
            cfads_by, policy, "dscr_sculpted",
        )
        interest_by = {r.period_index: r.interest_keur for r in rows}

        # Step 2: tax feedback
        new_cfads, new_cash_tax = tax_cfads_fn(interest_by)

        # Step 3: backward capacity from updated CFADS
        dscr_capacity = _backward_dscr_capacity(
            new_cfads, rate_map, period_start_end, period_indices, policy,
        )

        # Zero capacity short-circuit
        if dscr_capacity == 0.0 and D > 0.0 and iteration == 1:
            diag = _make_diag(
                converged=False, iteration=iteration,
                initial_guess=inputs.initial_debt_guess_keur,
                final_d=0.0, max_abs_diff=D,
                binding=binding_constraint, termination_reason="NO_DEBT_CAPACITY",
            )
            zero_rows = _forward_roll(
                0.0, period_indices, rate_map, period_start_end,
                new_cfads, policy, "dscr_sculpted",
            )
            return _to_schedules(zero_rows, 0.0, binding_constraint, diag)

        # Step 4: damping
        new_D = alpha * dscr_capacity + (1.0 - alpha) * D
        new_D = max(0.0, new_D)

        # Step 5: convergence check (skip first iteration — no prev to compare)
        if prev_D is not None:
            debt_diff = abs(new_D - D)
            cfads_diff = _max_dict_diff(new_cfads, cfads_by, period_indices)
            cash_tax_diff = _max_dict_diff(new_cash_tax, cash_tax_by, period_indices)
            max_abs_diff = max(debt_diff, cfads_diff, cash_tax_diff)

            if max_abs_diff <= tol:
                # CONVERGED: final authoritative forward roll
                final_rows = _forward_roll(
                    new_D, period_indices, rate_map, period_start_end,
                    new_cfads, policy, "dscr_sculpted",
                )
                diag = _make_diag(
                    converged=True, iteration=iteration,
                    initial_guess=inputs.initial_debt_guess_keur,
                    final_d=new_D, max_abs_diff=max_abs_diff,
                    binding=binding_constraint, termination_reason="CONVERGED",
                )
                return _to_schedules(final_rows, new_D, binding_constraint, diag)

        prev_D = D
        prev_cfads = cfads_by
        prev_cash_tax = cash_tax_by
        D = new_D
        cfads_by = new_cfads
        cash_tax_by = new_cash_tax

    # Max iterations reached
    final_rows = _forward_roll(
        D, period_indices, rate_map, period_start_end,
        cfads_by, policy, "dscr_sculpted",
    )
    diag = _make_diag(
        converged=False, iteration=max_iter,
        initial_guess=inputs.initial_debt_guess_keur,
        final_d=D, max_abs_diff=max_abs_diff,
        binding=binding_constraint, termination_reason="MAX_ITERATIONS_REACHED",
    )
    return _to_schedules(final_rows, D, binding_constraint, diag)


# ---------------------------------------------------------------------------
# GEARING_CAP: single-pass level-principal
# ---------------------------------------------------------------------------

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

    # One pass: forward roll with zero CFADS to get interest, then tax feedback once
    rows = _forward_roll(
        D, period_indices, rate_map, period_start_end,
        {idx: 0.0 for idx in period_indices}, policy, "level_principal",
    )
    interest_by = {r.period_index: r.interest_keur for r in rows}
    cfads_by, _ = tax_cfads_fn(interest_by)

    # Final roll with updated CFADS (for DSCR reporting)
    final_rows = _forward_roll(
        D, period_indices, rate_map, period_start_end,
        cfads_by, policy, "level_principal",
    )

    diag = _make_diag(
        converged=True, iteration=1,
        initial_guess=D, final_d=D, max_abs_diff=0.0,
        binding="GEARING", termination_reason="CONVERGED",
    )
    return _to_schedules(final_rows, D, "GEARING", diag)


# ---------------------------------------------------------------------------
# COMBINED_MINIMUM (BLOCKER 7): DSCR loop → gearing cap → min → DSCR-sculpted roll
# ---------------------------------------------------------------------------

def _solve_combined(
    *,
    policy: SeniorDebtPolicy,
    inputs: "SeniorDebtInputs",
    period_indices: tuple[int, ...],
    period_start_end: dict[int, tuple],
    rate_map: dict[int, float],
    tax_cfads_fn: TaxCfadsCallable,
) -> SeniorDebtSchedules:
    """COMBINED_MINIMUM: run DSCR loop to get dscr_capacity, apply gearing cap, take min.

    Forward roll at final D always uses DSCR-sculpted repayment.
    """
    assert policy.maximum_gearing is not None
    gearing_cap = inputs.eligible_project_cost_keur * policy.maximum_gearing

    # Run DSCR loop to convergence
    dscr_result = _solve_dscr(
        policy=policy, inputs=inputs, period_indices=period_indices,
        period_start_end=period_start_end, rate_map=rate_map, tax_cfads_fn=tax_cfads_fn,
        binding_constraint="DSCR",
    )
    if not dscr_result.diagnostics.is_authoritative:
        # Propagate non-convergence / non-authoritative results unchanged
        return dscr_result

    dscr_capacity = dscr_result.debt_size_keur
    tol = policy.convergence_tolerance_keur

    # Determine binding constraint
    if abs(dscr_capacity - gearing_cap) <= tol:
        binding = "BOTH"
    elif dscr_capacity < gearing_cap:
        binding = "DSCR"
    else:
        binding = "GEARING"

    final_d = min(dscr_capacity, gearing_cap)

    # Final authoritative forward roll with DSCR-sculpted repayment at final_d
    # Re-use cfads from the converged DSCR run
    cfads_by = dict(zip(dscr_result.period_indices, [0.0] * len(dscr_result.period_indices)))
    # Recompute interest from final_d to get correct CFADS via tax feedback
    initial_rows = _forward_roll(
        final_d, period_indices, rate_map, period_start_end,
        cfads_by, policy, "dscr_sculpted",
    )
    interest_by = {r.period_index: r.interest_keur for r in initial_rows}
    new_cfads, _ = tax_cfads_fn(interest_by)

    final_rows = _forward_roll(
        final_d, period_indices, rate_map, period_start_end,
        new_cfads, policy, "dscr_sculpted",
    )

    diag = _make_diag(
        converged=True,
        iteration=dscr_result.diagnostics.iteration_count,
        initial_guess=inputs.initial_debt_guess_keur,
        final_d=final_d,
        max_abs_diff=dscr_result.diagnostics.maximum_absolute_difference_keur,
        binding=binding,
        termination_reason="CONVERGED",
    )
    return _to_schedules(final_rows, final_d, binding, diag)


# ---------------------------------------------------------------------------
# EXPLICIT_SCHEDULE (BLOCKER 5): upfront validation then exact forward roll
# ---------------------------------------------------------------------------

def _solve_explicit(
    *,
    policy: SeniorDebtPolicy,
    inputs: "SeniorDebtInputs",
    period_indices: tuple[int, ...],
    period_start_end: dict[int, tuple],
    rate_map: dict[int, float],
    tax_cfads_fn: TaxCfadsCallable,
) -> SeniorDebtSchedules:
    """EXPLICIT_SCHEDULE: validate principal schedule then forward roll once."""
    opening = inputs.opening_debt_balance_keur
    explicit_map = {
        pp.period_index: pp.principal_keur
        for pp in (inputs.explicit_principal_schedule or ())
    }
    explicit_total = sum(pp.principal_keur for pp in (inputs.explicit_principal_schedule or ()))
    tol = policy.convergence_tolerance_keur

    # BLOCKER 5 validation
    if explicit_total > opening + tol:
        diag = _make_diag(
            converged=False, iteration=0,
            initial_guess=opening, final_d=opening,
            max_abs_diff=explicit_total - opening,
            binding=None, termination_reason="INVALID_INPUT",
        )
        zero_rows = tuple(
            PeriodDebtRow(
                period_index=idx,
                opening_keur=0.0, interest_keur=0.0, principal_keur=0.0,
                debt_service_keur=0.0, closing_keur=0.0, dscr=None,
            )
            for idx in period_indices
        )
        return _to_schedules(zero_rows, opening, None, diag)

    if not policy.permit_terminal_balloon and explicit_total < opening - tol:
        diag = _make_diag(
            converged=False, iteration=0,
            initial_guess=opening, final_d=opening,
            max_abs_diff=opening - explicit_total,
            binding=None, termination_reason="TERMINAL_BALANCE_NOT_ALLOWED",
        )
        zero_rows = tuple(
            PeriodDebtRow(
                period_index=idx,
                opening_keur=0.0, interest_keur=0.0, principal_keur=0.0,
                debt_service_keur=0.0, closing_keur=0.0, dscr=None,
            )
            for idx in period_indices
        )
        return _to_schedules(zero_rows, opening, None, diag)

    # One pass: exact explicit schedule (NO min(p, balance))
    # Get interest first with zero CFADS, then tax feedback, then final roll
    cfads_by: dict[int, float] = {idx: 0.0 for idx in period_indices}
    rows = _forward_roll(
        opening, period_indices, rate_map, period_start_end,
        cfads_by, policy, "explicit", explicit_by=explicit_map,
    )
    interest_by = {r.period_index: r.interest_keur for r in rows}
    cfads_by, _ = tax_cfads_fn(interest_by)

    # Final roll for DSCR reporting with updated CFADS
    final_rows = _forward_roll(
        opening, period_indices, rate_map, period_start_end,
        cfads_by, policy, "explicit", explicit_by=explicit_map,
    )

    diag = _make_diag(
        converged=True, iteration=1,
        initial_guess=opening, final_d=opening, max_abs_diff=0.0,
        binding=None, termination_reason="CONVERGED",
    )
    return _to_schedules(final_rows, opening, None, diag)
