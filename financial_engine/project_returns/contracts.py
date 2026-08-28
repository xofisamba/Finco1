"""Canonical downstream return and terminal-state contracts for clean G2C."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from financial_engine.sponsor_returns.contracts import ReturnMetricStatus


class DebtTerminalStatus(str, Enum):
    REPAID = "REPAID"
    OUTSTANDING_AT_MATURITY = "OUTSTANDING_AT_MATURITY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ShlTerminalStatus(str, Enum):
    REPAID = "REPAID"
    UNPAID_AT_CONTRACTUAL_MATURITY = "UNPAID_AT_CONTRACTUAL_MATURITY"
    OUTSTANDING_WITHIN_CONTRACTUAL_TERM = "OUTSTANDING_WITHIN_CONTRACTUAL_TERM"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CashAccountTerminalStatus(str, Enum):
    RELEASED = "RELEASED"
    STRANDED_CASH = "STRANDED_CASH"
    CASH_SHORTFALL = "CASH_SHORTFALL"
    REMAINING_BALANCE = "REMAINING_BALANCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class ProjectReturnCashFlow:
    """One dated, financing-independent project-return cash flow."""

    cashflow_date: date
    project_investment_outflow_keur: float
    project_operating_inflow_keur: float
    project_tax_outflow_keur: float
    terminal_component_keur: float
    net_unlevered_project_cashflow_keur: float


@dataclass(frozen=True)
class ProjectReturnResult:
    """Canonical Project / Unlevered XIRR and its complete audit bridge."""

    cashflows: tuple[ProjectReturnCashFlow, ...]
    project_xirr: float | None
    project_xirr_status: ReturnMetricStatus
    total_hard_capex_investment_keur: float
    excluded_financing_cost_uses_keur: float
    excluded_reserve_funding_keur: float
    total_operating_inflow_keur: float
    total_project_tax_outflow_keur: float
    terminal_component_keur: float
    methodology_authority: str


@dataclass(frozen=True)
class ReturnMetricSummary:
    """Existing canonical Legal Equity or Total Sponsor return authority."""

    xirr: float | None
    xirr_status: ReturnMetricStatus
    moic: float | None
    moic_status: ReturnMetricStatus
    total_contributions_keur: float
    total_receipts_keur: float
    net_cashflow_keur: float


@dataclass(frozen=True)
class DebtTerminalState:
    contractual_maturity_period_index: int | None
    contractual_maturity_date: date | None
    terminal_balance_keur: float
    status: DebtTerminalStatus


@dataclass(frozen=True)
class ShlTerminalState:
    repayment_mode: str | None
    contractual_maturity_period_index: int | None
    contractual_maturity_date: date | None
    contractual_amount_due_at_maturity_keur: float
    amount_paid_at_maturity_keur: float
    unpaid_at_maturity_keur: float
    terminal_balance_keur: float
    status: ShlTerminalStatus


@dataclass(frozen=True)
class CashAccountTerminalState:
    terminal_closing_balance_keur: float
    status: CashAccountTerminalStatus


@dataclass(frozen=True)
class TerminalFinancialState:
    senior: DebtTerminalState
    shareholder_loan: ShlTerminalState
    distribution_account: CashAccountTerminalState
    senior_dsra: CashAccountTerminalState


@dataclass(frozen=True)
class DecisionCompleteReturnSummary:
    """Single downstream authority for project, sponsor, and terminal results."""

    project: ProjectReturnResult
    legal_equity: ReturnMetricSummary
    total_sponsor: ReturnMetricSummary
    terminal: TerminalFinancialState
    deductible_shl_covenant_feedback_status: str | None
