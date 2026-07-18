"""financial_engine.senior_debt.policy — Immutable senior debt policy contract."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeniorDebtRepaymentMethod(str, Enum):
    """Controls the amortisation profile applied by the solver.

    DSCR_SCULPTED   : principal repaid in each period is sized so that DSCR equals
                      the target (default for DSCR_SCULPTED and COMBINED_MINIMUM
                      sizing modes).
    LEVEL_PRINCIPAL : equal principal repayment in every period between
                      repayment_start_period_index and maturity_period_index
                      (default for GEARING_CAP sizing mode).
    EXPLICIT        : the repayment schedule is supplied directly via the explicit
                      schedule on the inputs object (default for EXPLICIT_SCHEDULE
                      sizing mode).

    Documented default combinations
    --------------------------------
    DSCR_SCULPTED sizing   → DSCR_SCULPTED repayment  (default)
    GEARING_CAP sizing     → LEVEL_PRINCIPAL repayment (default)
    COMBINED_MINIMUM sizing→ DSCR_SCULPTED repayment   (min of two capacities;
                             amortisation does NOT switch to level-principal merely
                             because the gearing constraint binds)
    EXPLICIT_SCHEDULE sizing→ EXPLICIT repayment       (default)
    """
    DSCR_SCULPTED = "dscr_sculpted"
    LEVEL_PRINCIPAL = "level_principal"
    EXPLICIT = "explicit"


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
    repayment_method        : amortisation profile; None = inferred from sizing_mode by
                              the solver (see SeniorDebtRepaymentMethod for defaults)
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
    repayment_method: SeniorDebtRepaymentMethod | None = None
