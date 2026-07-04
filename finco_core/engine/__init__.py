"""
finco_core.engine — Top-level financial engine orchestration.

Extraction target (V2-3): FinancialEngine entry point that accepts
RunConfiguration and returns a typed EngineResult. Orchestrates all
domain subpackages (waterfall, tax, debt, SHL, depreciation, sponsor).

Runtime contract:
    RunConfiguration → FinancialEngine → EngineResult

No post-engine mutation. No identity dispatch. One execution path.

V2-3: Forward shims to domain engine modules.
Authoritative definitions will be moved here in V2-4.
"""
from domain.period_engine import PeriodMeta, PeriodEngine, hash_engine_for_cache
from domain.distribution_account import (
    DistributionAccountEngine,
    DistributionAccountInputs,
    DistributionAccountPeriodInput,
    R99R102GateInputs,
    DistributionAccountResult,
    DistributionAccountPeriodResult,
    DistributionGateResult,
    R99InputResult,
    BLOCKED_REASONS,
    evaluate_r99_gate,
    evaluate_r102_gate,
    evaluate_dscr_gate,
    evaluate_lockup_gate,
    evaluate_oborovo_guard,
    evaluate_cash_gate,
    DistributionAuditRow,
    compute_tuho_r99_input_period,
)

__all__ = [
    # Period engine
    "PeriodMeta",
    "PeriodEngine",
    "hash_engine_for_cache",
    # Distribution account engine
    "DistributionAccountEngine",
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
    "compute_tuho_r99_input_period",
]
