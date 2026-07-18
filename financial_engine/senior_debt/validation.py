"""financial_engine.senior_debt.validation — Input validation for Phase 2C."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    from financial_engine.senior_debt.policy import SeniorDebtPolicy


def validate_senior_debt_inputs(
    inputs: "SeniorDebtInputs",
    policy: "SeniorDebtPolicy",
    known_period_indices: frozenset[int],
) -> list[str]:
    """Return a list of error messages (empty = valid)."""
    from financial_engine.senior_debt.policy import SeniorDebtSizingMode

    errors: list[str] = []

    # --- Policy fields ---
    if policy.target_dscr <= 1.0:
        errors.append(
            f"target_dscr must be > 1.0, got {policy.target_dscr}"
        )
    if policy.maximum_gearing is not None:
        if not (0.0 < policy.maximum_gearing <= 1.0):
            errors.append(
                f"maximum_gearing must be in (0, 1], got {policy.maximum_gearing}"
            )
    if policy.maturity_period_index < policy.repayment_start_period_index:
        errors.append(
            f"maturity_period_index ({policy.maturity_period_index}) "
            f"must be >= repayment_start_period_index ({policy.repayment_start_period_index})"
        )
    if policy.convergence_tolerance_keur < 0:
        errors.append(f"convergence_tolerance_keur must be >= 0")
    if policy.maximum_iterations < 1:
        errors.append(f"maximum_iterations must be >= 1")
    if not (0.0 < policy.damping_alpha <= 1.0):
        errors.append(f"damping_alpha must be in (0, 1], got {policy.damping_alpha}")

    # --- Input fields ---
    if not math.isfinite(inputs.eligible_project_cost_keur):
        errors.append("eligible_project_cost_keur must be finite")
    if inputs.eligible_project_cost_keur < 0:
        errors.append("eligible_project_cost_keur must be >= 0")
    if not math.isfinite(inputs.initial_debt_guess_keur):
        errors.append("initial_debt_guess_keur must be finite")
    if inputs.initial_debt_guess_keur < 0:
        errors.append("initial_debt_guess_keur must be >= 0")

    # --- Period rates ---
    seen_rate_periods: set[int] = set()
    for pr in inputs.period_rates:
        if pr.period_index in seen_rate_periods:
            errors.append(f"Duplicate period_rate for period_index={pr.period_index}")
        seen_rate_periods.add(pr.period_index)
        if pr.period_index not in known_period_indices:
            errors.append(f"period_rate references unknown period_index={pr.period_index}")
        if not math.isfinite(pr.annual_rate):
            errors.append(f"Non-finite annual_rate for period_index={pr.period_index}")

    # Fixed rate required if no explicit rates cover all periods
    if not inputs.period_rates and policy.annual_fixed_rate is None:
        errors.append(
            "No period_rates provided and policy.annual_fixed_rate is None; "
            "at least one source of interest rates is required"
        )
    if policy.annual_fixed_rate is not None and not math.isfinite(policy.annual_fixed_rate):
        errors.append(f"Non-finite policy.annual_fixed_rate: {policy.annual_fixed_rate}")

    # --- GEARING_CAP / COMBINED_MINIMUM require maximum_gearing ---
    if policy.sizing_mode in (
        SeniorDebtSizingMode.GEARING_CAP, SeniorDebtSizingMode.COMBINED_MINIMUM
    ):
        if policy.maximum_gearing is None:
            errors.append(
                f"sizing_mode={policy.sizing_mode.value} requires maximum_gearing to be set"
            )

    # --- EXPLICIT_SCHEDULE requires principal schedule ---
    if policy.sizing_mode == SeniorDebtSizingMode.EXPLICIT_SCHEDULE:
        if inputs.explicit_principal_schedule is None:
            errors.append("EXPLICIT_SCHEDULE mode requires explicit_principal_schedule")
        else:
            seen_principal_periods: set[int] = set()
            for pp in inputs.explicit_principal_schedule:
                if pp.period_index in seen_principal_periods:
                    errors.append(
                        f"Duplicate explicit_principal for period_index={pp.period_index}"
                    )
                seen_principal_periods.add(pp.period_index)
                if pp.period_index not in known_period_indices:
                    errors.append(
                        f"explicit_principal references unknown period_index={pp.period_index}"
                    )
                if not math.isfinite(pp.principal_keur):
                    errors.append(
                        f"Non-finite principal_keur for period_index={pp.period_index}"
                    )
                if pp.principal_keur < 0:
                    errors.append(
                        f"Negative principal_keur for period_index={pp.period_index}"
                    )
        if inputs.opening_debt_balance_keur < 0:
            errors.append("opening_debt_balance_keur must be >= 0")
        if not math.isfinite(inputs.opening_debt_balance_keur):
            errors.append("opening_debt_balance_keur must be finite")

    return errors
