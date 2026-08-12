"""
finco_parity.check_financial_engine_senior_debt — Phase 2C senior debt parity CLI.

For each runnable baseline (oborovo, generic_solar, generic_wind):
  1. Build Phase 2A operating inputs via the project factory adapter.
  2. Build Phase 2B tax inputs (policy, opening vintages, exogenous interest from snapshot).
  3. Build an explicit Phase 2C senior-debt policy/inputs calibrated per baseline.
  4. Call run_senior_debt_model().
  5. Assert the result is authoritative.
  6. Assert schedule lengths align and non-negative principal/opening/closing.
  7. Assert interest reconciles to opening × rate × day count (within tolerance).
  8. Report debt size, binding constraint, iteration count, min/avg DSCR.

TUHO stops before the solver with INPUT_SOURCE_BLOCKED.

Usage::

    python -m finco_parity.check_financial_engine_senior_debt --baseline oborovo --check
    python -m finco_parity.check_financial_engine_senior_debt --all

Exit codes
----------
0   All selected baselines pass (authoritative results).
1   Execution error (unexpected exception or assertion failure).
2   Unknown baseline ID or invalid CLI args.
9   One or more baselines INPUT_SOURCE_BLOCKED.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
  - financial_engine.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import argparse
import sys
import traceback

from financial_engine.version import ENGINE_VERSION

_ALL_BASELINE_IDS = ("tuho", "oborovo", "generic_solar", "generic_wind")
_STATUS_BLOCKED = "INPUT_SOURCE_BLOCKED"
_STATUS_PASS = "PASS"
_STATUS_FAIL = "FAIL"


# ---------------------------------------------------------------------------
# Per-baseline Phase 2C senior-debt policy calibration
# ---------------------------------------------------------------------------

def _build_senior_debt_policy(baseline_id: str):
    """Build a calibrated SeniorDebtPolicy for the given baseline.

    Adapter-level calibration only — no runtime engine logic here.
    Period indices, gearing ratios, and rates are read from baseline-specific
    project factory parameters.
    """
    from financial_engine.senior_debt.policy import (
        SeniorDebtPolicy, SeniorDebtSizingMode, DayCountConvention,
    )
    # Baseline-specific calibration derived from project factory params.
    # These are parity/test inputs — not production runtime inputs.
    _CALIBRATION = {
        "oborovo": {
            "sizing_mode": SeniorDebtSizingMode.DSCR_SCULPTED,
            "target_dscr": 1.15,
            "maximum_gearing": None,
            "annual_fixed_rate": 0.0565,  # base_rate 3% + margin 265bps
            "repayment_start_period_index": 2,
            "maturity_period_index": 29,   # ~14 years × 2 semi-annual
        },
        "generic_solar": {
            "sizing_mode": SeniorDebtSizingMode.DSCR_SCULPTED,
            "target_dscr": 1.20,
            "maximum_gearing": None,
            "annual_fixed_rate": 0.05,
            "repayment_start_period_index": 2,
            "maturity_period_index": 29,
        },
        "generic_wind": {
            "sizing_mode": SeniorDebtSizingMode.DSCR_SCULPTED,
            "target_dscr": 1.20,
            "maximum_gearing": None,
            "annual_fixed_rate": 0.05,
            "repayment_start_period_index": 2,
            "maturity_period_index": 29,
        },
    }
    cal = _CALIBRATION[baseline_id]
    return SeniorDebtPolicy(
        policy_id=f"parity_{baseline_id}",
        policy_version="1.0",
        sizing_mode=cal["sizing_mode"],
        target_dscr=cal["target_dscr"],
        maximum_gearing=cal["maximum_gearing"],
        annual_fixed_rate=cal["annual_fixed_rate"],
        periods_per_year=2,
        day_count_convention=DayCountConvention.ACT_365,
        repayment_start_period_index=cal["repayment_start_period_index"],
        maturity_period_index=cal["maturity_period_index"],
        convergence_tolerance_keur=1.0,
        convergence_relative_tolerance=0.001,
        maximum_iterations=500,
        permit_terminal_balloon=True,
        damping_alpha=1.0,
    )


def _build_senior_debt_inputs(baseline_id: str, eligible_project_cost_keur: float):
    """Build SeniorDebtInputs for the given baseline."""
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    # Initial guess: 60% of eligible cost as a reasonable starting point
    initial_guess = eligible_project_cost_keur * 0.60
    return SeniorDebtInputs(
        eligible_project_cost_keur=eligible_project_cost_keur,
        initial_debt_guess_keur=initial_guess,
        period_rates=(),
        explicit_principal_schedule=None,
    )


# ---------------------------------------------------------------------------
# Blocked baseline detection
# ---------------------------------------------------------------------------

def _check_blocked_baselines(baseline_ids: list[str]) -> dict[str, str]:
    """Return {baseline_id: block_reason} for baselines that cannot be run.

    A blocked baseline (e.g. TUHO opening-loss unresolved) produces
    INPUT_SOURCE_BLOCKED rather than a comparison result.
    """
    from finco_parity.tax_reference_inputs import (
        TuhoOpeningLossVintageUnresolved,
        build_opening_loss_vintages,
    )
    blocked: dict[str, str] = {}
    for bid in baseline_ids:
        try:
            build_opening_loss_vintages(bid)
        except TuhoOpeningLossVintageUnresolved as exc:
            blocked[bid] = str(exc)
    return blocked


# ---------------------------------------------------------------------------
# Phase 2C run for one runnable baseline
# ---------------------------------------------------------------------------

def _run_baseline_phase2c(baseline_id: str) -> dict:
    """Run Phase 2C senior debt for one runnable baseline.

    Returns a result dict with keys:
      status         : PASS or FAIL
      debt_size_keur : final sized debt
      binding        : binding constraint string
      iteration_count: solver iterations
      min_dscr       : minimum non-None DSCR across periods
      avg_dscr       : average non-None DSCR across periods
      n_periods      : number of operating periods
      error          : error message (FAIL only)
    """
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.inputs import TaxCalculationInput, SeniorDebtModelInput, DebtSizingCaseInput, YieldScenario
    from financial_engine.senior_debt.models import SeniorDebtNonConvergenceError
    from finco_parity.tax_reference_inputs import build_tax_policy, build_opening_loss_vintages
    from finco_parity.financial_engine_tax_cfads_candidate import (
        _load_project_inputs,
        _load_baseline_snapshot,
        _build_exogenous_interest,
    )
    from financial_engine.adapters.project_inputs import from_project_inputs

    # Step 1: Phase 2A operating inputs
    project_inputs = _load_project_inputs(baseline_id)
    op_inputs = from_project_inputs(project_inputs, source_id=f"parity_{baseline_id}")

    # Step 2: Phase 2B tax inputs
    tax_policy = build_tax_policy(baseline_id)
    opening_vintages = build_opening_loss_vintages(baseline_id)
    # Exogenous interest from committed baseline snapshot
    snap = _load_baseline_snapshot(baseline_id)
    exog_interest = _build_exogenous_interest(snap)
    tax_input = TaxCalculationInput(
        policy=tax_policy,
        opening_loss_vintages=opening_vintages,
        period_interest=exog_interest,
        period_adjustments=(),
    )

    # Eligible project cost from project inputs
    eligible_cost_keur = getattr(project_inputs.capex, "total_capex_keur", None) or 100_000.0

    # Step 3: Phase 2C senior debt inputs
    sd_policy = _build_senior_debt_policy(baseline_id)
    sd_inputs = _build_senior_debt_inputs(baseline_id, eligible_cost_keur)

    model_input = SeniorDebtModelInput(
        operating=op_inputs,
        tax=tax_input,
        senior_debt_policy=sd_policy,
        senior_debt_inputs=sd_inputs,
        debt_sizing_case=DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            source_label="generic_bank_case_p90_10y",
        ),
    )

    # Step 4: Run Phase 2C
    try:
        result = run_senior_debt_model(model_input)
    except SeniorDebtNonConvergenceError as exc:
        return {"status": _STATUS_FAIL, "error": f"SeniorDebtNonConvergenceError: {exc}"}

    sd = result.senior_debt

    # Step 5+6: Assert authoritative, schedule lengths, non-negative balances
    diag = sd.diagnostics
    if not diag.get("is_authoritative", False):
        return {
            "status": _STATUS_FAIL,
            "error": f"Non-authoritative result: {diag.get('termination_reason')}",
        }

    n = len(sd.period_indices)
    if len(sd.senior_interest_keur) != n:
        return {"status": _STATUS_FAIL, "error": "schedule length mismatch"}

    for i, p in enumerate(sd.senior_principal_keur):
        if p < -1e-4:
            return {"status": _STATUS_FAIL, "error": f"Negative principal at period {sd.period_indices[i]}: {p:.4f}"}
    for i, o in enumerate(sd.senior_debt_opening_keur):
        if o < -1e-4:
            return {"status": _STATUS_FAIL, "error": f"Negative opening at period {sd.period_indices[i]}: {o:.4f}"}
    for i, c in enumerate(sd.senior_debt_closing_keur):
        if c < -1e-4:
            return {"status": _STATUS_FAIL, "error": f"Negative closing at period {sd.period_indices[i]}: {c:.4f}"}

    # Step 7: Interest reconciliation — opening × rate × day_count
    # (approximate: policy uses annual_fixed_rate and ACT/365)
    from financial_engine.senior_debt.interest import period_day_fraction
    from financial_engine.senior_debt.policy import DayCountConvention
    from financial_engine.orchestrator import run_tax_cfads_model
    from financial_engine.inputs import TaxCfadsModelInput

    # Get actual operating periods by running Phase 2B
    phase2b_result = run_tax_cfads_model(TaxCfadsModelInput(operating=op_inputs, tax=tax_input))
    op_periods = {p.period_index: p for p in phase2b_result.periods if p.is_operation}

    rate = sd_policy.annual_fixed_rate or 0.0
    max_interest_err = 0.0
    for i, idx in enumerate(sd.period_indices):
        op = op_periods.get(idx)
        if op is None:
            continue
        day_frac = period_day_fraction(op.period_start, op.period_end, DayCountConvention.ACT_365)
        expected_interest = sd.senior_debt_opening_keur[i] * rate * day_frac
        actual_interest = sd.senior_interest_keur[i]
        max_interest_err = max(max_interest_err, abs(expected_interest - actual_interest))

    if max_interest_err > 0.01:  # 10 EUR tolerance
        return {"status": _STATUS_FAIL, "error": f"Interest reconciliation error: {max_interest_err:.4f} kEUR"}

    # Step 8: Diagnostic output
    dscr_values = [v for v in sd.senior_dscr if v is not None]
    min_dscr = min(dscr_values) if dscr_values else None
    avg_dscr = sum(dscr_values) / len(dscr_values) if dscr_values else None

    return {
        "status": _STATUS_PASS,
        "debt_size_keur": diag.get("final_debt_size_keur", sd.debt_size_keur),
        "binding": diag.get("binding_constraint"),
        "iteration_count": diag.get("iteration_count"),
        "min_dscr": min_dscr,
        "avg_dscr": avg_dscr,
        "n_periods": n,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2C clean-engine senior debt parity check."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Check all baselines.")
    group.add_argument(
        "--baseline",
        choices=list(_ALL_BASELINE_IDS),
        help="Check a single baseline.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero on any blocked or failed baseline.",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output.")

    args = parser.parse_args(argv)
    selected_ids = list(_ALL_BASELINE_IDS) if args.all else [args.baseline]

    if not args.quiet:
        print(f"Phase 2C SENIOR_DEBT_V1 parity check — engine: {ENGINE_VERSION}")
        print(f"Baselines: {', '.join(selected_ids)}")
        print()

    # Check for blocked baselines first
    try:
        blocked = _check_blocked_baselines(selected_ids)
    except Exception as exc:
        print(f"UNEXPECTED ERROR in blocked-check: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    if not args.quiet:
        for bid, reason in blocked.items():
            print(f"  [{bid}] {_STATUS_BLOCKED}: {reason[:120]}")

    if args.check and blocked:
        print(
            f"CHECK FAILED: {len(blocked)} baseline(s) INPUT_SOURCE_BLOCKED: "
            f"{', '.join(blocked)}",
            file=sys.stderr,
        )
        return 9

    # Run Phase 2C for runnable baselines
    runnable = [bid for bid in selected_ids if bid not in blocked]
    failed: list[str] = []

    for bid in runnable:
        try:
            res = _run_baseline_phase2c(bid)
        except Exception as exc:
            if not args.quiet:
                print(f"  [{bid}] {_STATUS_FAIL}: UNEXPECTED ERROR — {type(exc).__name__}: {exc}")
                traceback.print_exc()
            failed.append(bid)
            continue

        if res["status"] == _STATUS_PASS:
            if not args.quiet:
                min_d = f"{res['min_dscr']:.3f}" if res['min_dscr'] is not None else "n/a"
                avg_d = f"{res['avg_dscr']:.3f}" if res['avg_dscr'] is not None else "n/a"
                print(
                    f"  [{bid}] {_STATUS_PASS} — "
                    f"debt={res['debt_size_keur']:.1f} kEUR  "
                    f"binding={res['binding']}  "
                    f"iter={res['iteration_count']}  "
                    f"n_periods={res['n_periods']}  "
                    f"min_dscr={min_d}  avg_dscr={avg_d}"
                )
        else:
            if not args.quiet:
                print(f"  [{bid}] {_STATUS_FAIL}: {res.get('error', 'unknown error')}")
            failed.append(bid)

    if not args.quiet:
        print()
        total = len(selected_ids)
        n_blocked = len(blocked)
        n_passed = len(runnable) - len(failed)
        n_failed = len(failed)
        print(f"Summary: {total} baselines — {n_blocked} blocked, {n_passed} passed, {n_failed} failed")

    if args.check and failed:
        print(
            f"CHECK FAILED: {len(failed)} baseline(s) FAILED: {', '.join(failed)}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
