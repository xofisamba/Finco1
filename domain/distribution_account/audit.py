"""Audit row dataclass for DistributionAccount CSV export."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class DistributionAuditRow:
    """Single-period audit row for DistributionAccount.

    Suitable for CSV export.
    """
    period_index: int
    project_name: str
    operating_period_index: int
    period_date: date

    # Balance
    opening_balance_keur: float
    closing_balance_keur: float

    # Cash flows
    cash_available_for_distribution_keur: float
    equity_distribution_candidate_keur: float
    equity_distribution_paid_keur: float
    cash_swept_to_shl_keur: float
    cash_retained_keur: float
    dsra_top_up_keur: float

    # Gate results
    r99_gate_passed: bool
    r102_gate_passed: bool
    dscr_gate_passed: bool
    lockup_gate_passed: bool
    oborovo_guard_passed: bool

    # Status
    blocked_reason: str
    is_tuho: bool
    is_oborovo: bool

    def to_csv_row(self) -> dict:
        return {
            "period_index": self.period_index,
            "project_name": self.project_name,
            "operating_period_index": self.operating_period_index,
            "period_date": str(self.period_date),
            "opening_balance_keur": f"{self.opening_balance_keur:.2f}",
            "closing_balance_keur": f"{self.closing_balance_keur:.2f}",
            "cash_available_for_distribution_keur": f"{self.cash_available_for_distribution_keur:.2f}",
            "equity_distribution_candidate_keur": f"{self.equity_distribution_candidate_keur:.2f}",
            "equity_distribution_paid_keur": f"{self.equity_distribution_paid_keur:.2f}",
            "cash_swept_to_shl_keur": f"{self.cash_swept_to_shl_keur:.2f}",
            "cash_retained_keur": f"{self.cash_retained_keur:.2f}",
            "dsra_top_up_keur": f"{self.dsra_top_up_keur:.2f}",
            "r99_gate_passed": self.r99_gate_passed,
            "r102_gate_passed": self.r102_gate_passed,
            "dscr_gate_passed": self.dscr_gate_passed,
            "lockup_gate_passed": self.lockup_gate_passed,
            "oborovo_guard_passed": self.oborovo_guard_passed,
            "blocked_reason": self.blocked_reason,
            "is_tuho": self.is_tuho,
            "is_oborovo": self.is_oborovo,
        }