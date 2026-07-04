"""
finco_core.shl — Shareholder loan engine.

Extraction target (V2-3): SHL engine, canonical wiring, interest accrual,
repayment alignment, audit trail. Capability-driven dispatch only —
no identity guards (eliminated in Stack AC + Phase 0 Y3).

Source: domain/shl/, domain/shl_fcf_waterfall.py

V2-3: Forward shims to domain shl modules.
"""
from domain.shl import (
    ShlEngine,
    ShlEngineInputs,
    ShlPeriodInput,
    ShlPeriodResult,
    ShlEngineResult,
    ShlAuditRow,
    ShlTaxInterface,
)
from domain.shl_fcf_waterfall import (
    SHLFCFWaterfallPeriodResult,
    compute_shl_fcf_waterfall_period,
)

__all__ = [
    "ShlPeriodInput",
    "ShlEngineInputs",
    "ShlTaxInterface",
    "ShlPeriodResult",
    "ShlEngineResult",
    "ShlAuditRow",
    "ShlEngine",
    "SHLFCFWaterfallPeriodResult",
    "compute_shl_fcf_waterfall_period",
]
