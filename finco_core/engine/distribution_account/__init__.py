"""finco_core.engine.distribution_account — Distribution account engine.

V2-4: Authoritative implementation. domain.distribution_account.* are compatibility shims.
"""
from finco_core.engine.distribution_account.engine import (
    DistributionAccountEngine,
    compute_tuho_r99_input_period,
)
from finco_core.engine.distribution_account.inputs import (
    DistributionAccountInputs,
    DistributionAccountPeriodInput,
    R99R102GateInputs,
)
from finco_core.engine.distribution_account.result import (
    DistributionAccountResult,
    DistributionAccountPeriodResult,
    DistributionGateResult,
    R99InputResult,
    BLOCKED_REASONS,
)
from finco_core.engine.distribution_account.gates import (
    evaluate_r99_gate,
    evaluate_r102_gate,
    evaluate_dscr_gate,
    evaluate_lockup_gate,
    evaluate_oborovo_guard,
    evaluate_cash_gate,
)
from finco_core.engine.distribution_account.audit import DistributionAuditRow

__all__ = [
    "DistributionAccountEngine",
    "compute_tuho_r99_input_period",
    "DistributionAccountInputs",
    "DistributionAccountPeriodInput",
    "R99R102GateInputs",
    "DistributionAccountResult",
    "DistributionAccountPeriodResult",
    "DistributionGateResult",
    "R99InputResult",
    "BLOCKED_REASONS",
    "evaluate_r99_gate",
    "evaluate_r102_gate",
    "evaluate_dscr_gate",
    "evaluate_lockup_gate",
    "evaluate_oborovo_guard",
    "evaluate_cash_gate",
    "DistributionAuditRow",
]
