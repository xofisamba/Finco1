"""domain/shl/ — Canonical SHL / Junior Debt Engine.

This module provides the canonical SHL (subordinated hybrid loan) engine
for the Finco1 financial model.

Default TUHO behavior:
    cash_sweep_after_senior = True
    maintain_minimum_cash_reserve = False
    minimum_cash_reserve_keur = 0.0
    pik_allowed = True
    day_count_fraction = 0.5 (semiannual)

This module is behind a default-off runtime flag (use_shl_canonical_engine=False).
Existing runtime behavior in app/waterfall_core.py is unchanged by default.

R99/R102: BLOCKED — this module does not compute distribution account logic.
"""

from domain.shl.inputs import ShlPeriodInput, ShlEngineInputs, ShlTaxInterface
from domain.shl.result import (
    ShlPeriodResult,
    ShlEngineResult,
    ShlAuditRow,
)
from domain.shl.engine import ShlEngine
from domain.shl.audit import to_audit_dataframe, to_csv, to_model_summary

__all__ = [
    "ShlEngine",
    "ShlEngineInputs",
    "ShlPeriodInput",
    "ShlPeriodResult",
    "ShlEngineResult",
    "ShlAuditRow",
    "ShlTaxInterface",
    "to_audit_dataframe",
    "to_csv",
    "to_model_summary",
]