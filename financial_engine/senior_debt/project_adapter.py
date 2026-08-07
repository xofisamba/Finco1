"""financial_engine.senior_debt.project_adapter — Generic ProjectInputs → SeniorDebt contract.

Maps a canonical ProjectInputs (from finco_core) plus the operating-model period results
to (SeniorDebtPolicy, SeniorDebtInputs) using only generic field access.

No project-name dispatch, no project-code references, no factory invocations.
The factory may encode project-specific DATA; this module encodes only the generic
field-mapping CONTRACT.

Availability source ownership decision (C3B3A):
    DS!row9 ops_flag = 179/181 for the final debt period is NOT derivable from
    ``COD + relativedelta(years=senior_tenor_years)`` which always yields 1.0.
    The availability schedule is therefore classified EXPLICIT_INPUT and must be
    provided via SeniorSculptingConfig.debt_service_availability_schedule.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finco_core.inputs import ProjectInputs
    from financial_engine.results import OperatingPeriodResult

from finco_core.inputs._models import PeriodFrequency
from financial_engine.senior_debt.inputs import (
    PeriodDebtServiceAvailability,
    PeriodDscrTarget,
    PeriodRate,
    SeniorDebtInputs,
)
from financial_engine.senior_debt.policy import (
    DayCountConvention,
    SeniorDebtPolicy,
    SeniorDebtSizingMode,
)


def build_senior_debt_contract_from_project_inputs(
    project_inputs: "ProjectInputs",
    operating_periods: "tuple[OperatingPeriodResult, ...]",
) -> "tuple[SeniorDebtPolicy, SeniorDebtInputs]":
    """Map a canonical ProjectInputs + operating periods to a clean senior-debt contract.

    Parameters
    ----------
    project_inputs:
        Canonical project inputs (finco_core.inputs.ProjectInputs).
    operating_periods:
        All operating-period results from run_operating_model (includes construction).
        The function selects the first ``N`` operating periods where ``N`` equals
        the number of sculpting-schedule entries (or senior_tenor_years * periods_per_year).

    Returns
    -------
    (SeniorDebtPolicy, SeniorDebtInputs) — ready for solve_senior_debt().
    """
    from finco_core.inputs._models import DebtSizingMode
    from finco_core.inputs.senior_rate_schedule import SeniorRateMode

    fin = project_inputs.financing
    sculpting = fin.senior_sculpting_config
    rate_cfg = fin.senior_debt_interest_config

    # --- Sizing mode mapping ---
    raw_mode = fin.debt_sizing_mode
    if raw_mode == DebtSizingMode.FLAT_DSCR_SCULPTED:
        sizing_mode = SeniorDebtSizingMode.DSCR_SCULPTED
    else:
        raise ValueError(
            f"build_senior_debt_contract_from_project_inputs: unsupported "
            f"debt_sizing_mode={raw_mode!r}. "
            f"Only FLAT_DSCR_SCULPTED is supported via the clean solver path."
        )

    # --- Day-count convention ---
    from finco_core.inputs.senior_rate_schedule import SeniorDayCountConvention
    finco_dc = rate_cfg.day_count
    if finco_dc == SeniorDayCountConvention.ACT_360:
        day_count = DayCountConvention.ACT_360
    elif finco_dc == SeniorDayCountConvention.ACT_365:
        day_count = DayCountConvention.ACT_365
    else:
        raise ValueError(
            f"build_senior_debt_contract_from_project_inputs: unsupported day-count "
            f"convention {finco_dc!r}. Only ACT_360 and ACT_365 are supported. "
            f"FIXED_SEMIANNUAL and EXPLICIT_FRACTIONS are not yet supported."
        )

    # --- Period selection ---
    # Select operating-only periods; map to debt tenor (first N of those).
    op_only = [p for p in operating_periods if p.is_operation]
    frequency = project_inputs.info.period_frequency
    if frequency == PeriodFrequency.SEMESTRIAL:
        periods_per_year = 2
    else:
        raise ValueError(
            f"build_senior_debt_contract_from_project_inputs: unsupported period "
            f"frequency {frequency!r}. Only SEMESTRIAL (2 periods/year) is supported "
            f"by the clean senior-debt source contract. ANNUAL and QUARTERLY require "
            f"end-to-end operating-period proof before enablement."
        )
    tenor_periods = fin.senior_tenor_years * periods_per_year

    debt_periods = op_only[:tenor_periods]
    if len(debt_periods) < tenor_periods:
        raise ValueError(
            f"Not enough operating periods for tenor: need {tenor_periods}, "
            f"got {len(debt_periods)}"
        )

    first_idx = debt_periods[0].period_index
    last_idx = debt_periods[-1].period_index

    # --- Per-period rates ---
    if rate_cfg.rate_schedule.mode == SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE:
        explicit_rates = rate_cfg.rate_schedule.explicit_all_in_rates
        if len(explicit_rates) < tenor_periods:
            raise ValueError(
                f"explicit_all_in_rates has {len(explicit_rates)} entries, "
                f"need {tenor_periods}"
            )
        period_rates = tuple(
            PeriodRate(period_index=p.period_index, annual_rate=explicit_rates[i])
            for i, p in enumerate(debt_periods)
        )
    else:
        raise ValueError(
            f"build_senior_debt_contract_from_project_inputs: unsupported "
            f"rate mode {rate_cfg.rate_schedule.mode!r}. "
            f"Only EXPLICIT_ALL_IN_SCHEDULE is supported."
        )

    # --- DSCR targets ---
    dscr_targets: tuple[PeriodDscrTarget, ...] = ()
    if sculpting.target_dscr_schedule:
        if len(sculpting.target_dscr_schedule) < tenor_periods:
            raise ValueError(
                f"target_dscr_schedule has {len(sculpting.target_dscr_schedule)} entries, "
                f"need {tenor_periods}"
            )
        dscr_targets = tuple(
            PeriodDscrTarget(
                period_index=p.period_index,
                target_dscr=sculpting.target_dscr_schedule[i],
            )
            for i, p in enumerate(debt_periods)
        )

    # --- Debt-service availability ---
    avail: tuple[PeriodDebtServiceAvailability, ...] = ()
    if sculpting.debt_service_availability_schedule:
        if len(sculpting.debt_service_availability_schedule) < tenor_periods:
            raise ValueError(
                f"debt_service_availability_schedule has "
                f"{len(sculpting.debt_service_availability_schedule)} entries, "
                f"need {tenor_periods}"
            )
        avail = tuple(
            PeriodDebtServiceAvailability(
                period_index=p.period_index,
                availability_fraction=sculpting.debt_service_availability_schedule[i],
            )
            for i, p in enumerate(debt_periods)
        )

    policy = SeniorDebtPolicy(
        policy_id="clean-project-senior-debt-v1",
        policy_version="1.0.0",
        sizing_mode=sizing_mode,
        target_dscr=fin.target_dscr,
        maximum_gearing=None,
        annual_fixed_rate=None,
        periods_per_year=periods_per_year,
        day_count_convention=day_count,
        repayment_start_period_index=first_idx,
        maturity_period_index=last_idx,
        convergence_tolerance_keur=1e-4,
        convergence_relative_tolerance=1e-9,
        maximum_iterations=200,
        permit_terminal_balloon=True,
        damping_alpha=1.0,
    )

    inputs = SeniorDebtInputs(
        eligible_project_cost_keur=0.0,
        initial_debt_guess_keur=fin.gearing_ratio * sum(
            item.amount_keur for item in project_inputs.capex.capex_items()
        ),
        period_rates=period_rates,
        explicit_principal_schedule=None,
        period_dscr_targets=dscr_targets,
        period_debt_service_availability=avail,
    )

    return policy, inputs
