"""Canonical DistributionAccount module.

All outputs are AUDIT-ONLY. Do NOT route production cashflows.
R99/R102 remain BLOCKED per G1/G8 governance rules.

Phase 9 implementation: audit-first mode.
"""
from domain.distribution_account.engine import DistributionAccountEngine
from domain.distribution_account.inputs import (
    DistributionAccountInputs,
    DistributionAccountPeriodInput,
    R99R102GateInputs,
)
from domain.distribution_account.result import (
    DistributionAccountResult,
    DistributionAccountPeriodResult,
    DistributionGateResult,
    R99InputResult,
    BLOCKED_REASONS,
)
from domain.distribution_account.gates import (
    evaluate_r99_gate,
    evaluate_r102_gate,
    evaluate_dscr_gate,
    evaluate_lockup_gate,
    evaluate_oborovo_guard,
    evaluate_cash_gate,
)
from domain.distribution_account.audit import DistributionAuditRow

# Legacy TUHO audit function — do not modify
from domain.distribution_account.engine import compute_tuho_r99_input_period

__all__ = [
    # Engine
    "DistributionAccountEngine",
    # Inputs
    "DistributionAccountInputs",
    "DistributionAccountPeriodInput",
    "R99R102GateInputs",
    # Results
    "DistributionAccountResult",
    "DistributionAccountPeriodResult",
    "DistributionGateResult",
    "R99InputResult",
    "BLOCKED_REASONS",
    # Gates
    "evaluate_r99_gate",
    "evaluate_r102_gate",
    "evaluate_dscr_gate",
    "evaluate_lockup_gate",
    "evaluate_oborovo_guard",
    "evaluate_cash_gate",
    # Audit
    "DistributionAuditRow",
    # Legacy
    "compute_tuho_r99_input_period",
]