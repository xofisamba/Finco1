"""SHL waterfall diagnostic helpers — Phase 20R."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ShlWaterfallDiagnosticRow:
    """Single-period SHL waterfall diagnostic."""
    # Project/period identity
    project_code: str
    period_index: int
    excel_sheet: str = ""
    excel_column: str = ""

    # Cash inputs
    cash_before_shl_keur: float = 0.0
    excel_available_cash: float = 0.0

    # SHL balance
    opening_shl_balance_keur: float = 0.0
    excel_opening_balance: float = 0.0

    # Interest
    shl_interest_due_gross_keur: float = 0.0
    shl_interest_due_net_keur: float = 0.0
    wht_on_shl_interest_keur: float = 0.0
    interest_paid_cash_keur: float = 0.0
    unpaid_interest_keur: float = 0.0
    pik_interest_keur: float = 0.0
    accrued_unpaid_interest_keur: float = 0.0

    # Principal and balance
    cash_after_interest_keur: float = 0.0
    principal_sweep_keur: float = 0.0
    excel_principal_sweep_keur: float = 0.0
    closing_shl_balance_keur: float = 0.0
    excel_closing_balance: float = 0.0

    # Distribution
    net_shl_cashflow_keur: float = 0.0
    fcf_for_dividends_keur: float = 0.0
    distribution_keur: float = 0.0
    excel_distribution_keur: float = 0.0

    # Trigger
    pik_switch_triggered: bool = False
    trigger_used_explanation: str = ""
    likely_cause: str = ""

    @property
    def status(self) -> str:
        sweep_gap = abs(self.principal_sweep_keur - self.excel_principal_sweep_keur)
        dist_gap = abs(self.distribution_keur - self.excel_distribution_keur)
        if sweep_gap > 1.0 or dist_gap > 1.0:
            return "FAIL"
        return "PASS"


@dataclass
class ShlWaterfallDiagnosticReport:
    """Full-period SHL waterfall diagnostic report."""
    project_code: str
    rows: list[ShlWaterfallDiagnosticRow] = field(default_factory=list)

    def period_row(self, p: int) -> Optional[ShlWaterfallDiagnosticRow]:
        for r in self.rows:
            if r.period_index == p:
                return r
        return None

    def failed_rows(self) -> list[ShlWaterfallDiagnosticRow]:
        return [r for r in self.rows if r.status == "FAIL"]


def build_shl_diagnostic_row(
    project_code: str,
    period_index: int,
    opening_balance: float,
    period_rate: float,
    cf_for_shl: float,
    wht_rate: float,
    shl_interest_keur: float,
    shl_principal_keur: float,
    distribution_keur: float,
    pik_switch_triggered: bool,
    annual_shl_rate: float,
    excel_principal_sweep_keur: float = 0.0,
    excel_distribution_keur: float = 0.0,
    excel_available_cash: float = 0.0,
) -> ShlWaterfallDiagnosticRow:
    """Build a SHL waterfall diagnostic row for a given period."""
    gross_int = opening_balance * period_rate
    net_int = gross_int * (1.0 - wht_rate)
    interest_paid = min(net_int, cf_for_shl)
    unpaid_int = max(0.0, net_int - interest_paid)
    pik = gross_int - interest_paid  # correct: gross - cash paid
    cash_after_int = cf_for_shl - interest_paid
    annual_threshold = opening_balance * annual_shl_rate

    return ShlWaterfallDiagnosticRow(
        project_code=project_code,
        period_index=period_index,
        cash_before_shl_keur=cf_for_shl,
        opening_shl_balance_keur=opening_balance,
        excel_opening_balance=0.0,
        shl_interest_due_gross_keur=gross_int,
        shl_interest_due_net_keur=net_int,
        wht_on_shl_interest_keur=max(0.0, net_int - interest_paid) * (wht_rate / (1.0 - wht_rate)) if wht_rate > 0 and interest_paid > 0 else 0.0,
        interest_paid_cash_keur=interest_paid,
        unpaid_interest_keur=unpaid_int,
        pik_interest_keur=pik,
        cash_after_interest_keur=cash_after_int,
        principal_sweep_keur=shl_principal_keur,
        excel_principal_sweep_keur=excel_principal_sweep_keur,
        closing_shl_balance_keur=opening_balance + pik - shl_principal_keur,
        distribution_keur=distribution_keur,
        excel_distribution_keur=excel_distribution_keur,
        excel_available_cash=excel_available_cash,
        pik_switch_triggered=pik_switch_triggered,
        trigger_used_explanation=(
            f"pik_switch = (cf_for_shl {cf_for_shl:.2f} > "
            f"annual_threshold {annual_threshold:.2f} = balance*rate): "
            f"{cf_for_shl:.2f} > {annual_threshold:.2f} = {pik_switch_triggered}"
        ),
        likely_cause=(
            "Excel computes principal sweep using SWEEP-phase logic when either "
            "(a) available CF > period interest, or (b) a proportional/pari-passu rule applies. "
            "Python uses an annual-interest threshold trigger that stays False in early periods "
            "when CF < annual interest even if CF > period interest."
        ),
    )
