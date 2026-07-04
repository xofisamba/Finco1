"""
finco_core.debt — Senior debt engine.

Extraction target (V2-3): senior debt schedule, DSCR sculpting,
covenant engine, debt sizing, amortisation schedule.

Source: domain/financing/, domain/senior_debt_sizing/, domain/senior_sculpting.py

V2-3: Forward shims to domain financing/senior_debt_sizing modules.
"""
from domain.financing import (
    AmortizationResult,
    DebtServiceResult,
    senior_debt_amount,
    standard_amortization,
    annuity_payment,
    balance_after_n_periods,
    sculpted_amortization,
    iterative_sculpt_debt,
    IterativeSculptResult,
    dscr_at_period,
    average_dscr,
    min_dscr,
    dscr,
    llcr,
    plcr,
)
from domain.financing.sculpting_iterative import (
    closed_form_sculpt,
    dsra_rolling_target,
    dsra_update,
    cash_sweep,
)
from domain.senior_debt_sizing import (
    SeniorDebtSizingPolicy,
    SeniorDebtDSCRPolicy,
    SizingMode,
    SeniorDebtSizingEngine,
)

__all__ = [
    # Schedule
    "AmortizationResult",
    "DebtServiceResult",
    "senior_debt_amount",
    "standard_amortization",
    "annuity_payment",
    "balance_after_n_periods",
    "sculpted_amortization",
    # Sculpting
    "iterative_sculpt_debt",
    "IterativeSculptResult",
    "closed_form_sculpt",
    "dsra_rolling_target",
    "dsra_update",
    "cash_sweep",
    # DSCR utilities
    "dscr_at_period",
    "average_dscr",
    "min_dscr",
    # Covenants
    "dscr",
    "llcr",
    "plcr",
    # Senior debt sizing
    "SeniorDebtSizingPolicy",
    "SeniorDebtDSCRPolicy",
    "SizingMode",
    "SeniorDebtSizingEngine",
]
