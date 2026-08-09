"""financial_engine.shl — Canonical SHL accrual/balance schedule (C3B3D1).

Pure, identity-blind, immutable. No imports from app, finco_core waterfall,
fastapi, jinja2, requests, openpyxl, or pandas.

Not wired into orchestrator.py, waterfall_engine.py, or any production runtime.
Production wiring is deferred to C3B3D2.
"""
from financial_engine.shl.contracts import (
    ShlInterestRateMode,
    ShlInterestPaymentMode,
    ShlRepaymentMode,
    ShlSchedulePolicy,
    ShlPeriodInput,
    ShlPeriodResult,
    ShlScheduleResult,
)
from financial_engine.shl.engine import compute_shl_period
from financial_engine.shl.schedule import run_shl_schedule

__all__ = [
    "ShlInterestRateMode",
    "ShlInterestPaymentMode",
    "ShlRepaymentMode",
    "ShlSchedulePolicy",
    "ShlPeriodInput",
    "ShlPeriodResult",
    "ShlScheduleResult",
    "compute_shl_period",
    "run_shl_schedule",
]
