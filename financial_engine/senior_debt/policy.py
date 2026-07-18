"""financial_engine.senior_debt.policy — Immutable senior debt policy contract."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeniorDebtSizingMode(str, Enum):
    DSCR_SCULPTED = "DSCR_SCULPTED"
    GEARING_CAP = "GEARING_CAP"
    COMBINED_MINIMUM = "COMBINED_MINIMUM"
    EXPLICIT_SCHEDULE = "EXPLICIT_SCHEDULE"


class DayCountConvention(str, Enum):
    ACT_365 = "ACT_365"
    ACT_360 = "ACT_360"


@dataclass(frozen=True)
class SeniorDebtPolicy:
    """Immutable senior debt policy.

    sizing_mode             : how debt is sized/sculpted
    target_dscr             : DSCR target used for sculpting (must be > 1.0)
    maximum_gearing         : fraction of eligible_project_cost; None = unconstrained
    annual_fixed_rate       : uniform annual interest rate; None = use period_rates on inputs
    periods_per_year        : model periods per year (2 = semi-annual)
    day_count_convention    : ACT_365 or ACT_360
    repayment_start_period_index : first period in which principal is repaid
    maturity_period_index   : last period in which principal can be repaid
    convergence_tolerance_keur   : absolute debt-size convergence threshold
    convergence_relative_tolerance : relative period-schedule convergence threshold
    maximum_iterations      : iteration cap; non-convergence → MAX_ITERATIONS_REACHED
    permit_terminal_balloon : if False, a non-zero closing balance at maturity is an error
    damping_alpha           : iteration damping factor in (0, 1]; 1.0 = no damping
    """
    policy_id: str
    policy_version: str
    sizing_mode: SeniorDebtSizingMode
    target_dscr: float
    maximum_gearing: float | None
    annual_fixed_rate: float | None
    periods_per_year: int
    day_count_convention: DayCountConvention
    repayment_start_period_index: int
    maturity_period_index: int
    convergence_tolerance_keur: float
    convergence_relative_tolerance: float
    maximum_iterations: int
    permit_terminal_balloon: bool
    damping_alpha: float = 1.0
