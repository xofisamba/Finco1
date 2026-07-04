"""finco_core.shl — Shareholder loan engine.

V2-4: Authoritative. domain.shl.* are compatibility shims.

Covers: SHL engine, canonical wiring, interest accrual, repayment alignment,
audit trail. Capability-driven dispatch only — no identity guards.
"""
from finco_core.shl.inputs import ShlEngineInputs, ShlPeriodInput
from finco_core.shl.result import ShlEngineResult, ShlPeriodResult, ShlAuditRow
from finco_core.shl.engine import ShlEngine
from finco_core.shl.fcf_waterfall import (
    SHLFCFWaterfallPeriodResult,
    compute_shl_fcf_waterfall_period,
)

__all__ = [
    "ShlPeriodInput",
    "ShlEngineInputs",
    "ShlPeriodResult",
    "ShlEngineResult",
    "ShlAuditRow",
    "ShlEngine",
    "SHLFCFWaterfallPeriodResult",
    "compute_shl_fcf_waterfall_period",
]
