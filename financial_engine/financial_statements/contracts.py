"""financial_engine.financial_statements.contracts — Phase C3 typed contracts.

Clean Financial Statements & Output Completeness Authority.

STRICTLY DOWNSTREAM: assembly consumes already-authoritative clean-engine
outputs (operating / tax / Senior / SHL / G2C / DSRA / construction results)
and performs accounting roll-forwards and identity checks only. Statements
never feed back into tax, debt sizing, SHL, distributions, returns or
valuation. No second engine.

Authority vocabulary (per line):
  EXISTING_CLEAN_AUTHORITY        — direct clean runtime vector;
  DERIVED_ACCOUNTING_ROLL_FORWARD — causal accounting roll-forward of clean
                                    vectors (identities checked);
  GENERIC_FINCO_ACCOUNTING_POLICY — standard Finco accounting convention,
                                    explicitly NOT Excel parity;
  SOURCE_PROVEN_CONFIGURATION     — typed input provenance;
  UNRESOLVED                      — no authority; surfaced as unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class StatementStatus(str, Enum):
    """Overall / per-statement typed status."""

    OK = "OK"
    UPSTREAM_FINANCIAL_RESULT_UNAVAILABLE = "UPSTREAM_FINANCIAL_RESULT_UNAVAILABLE"
    STATEMENT_PERIOD_AXIS_MISMATCH = "STATEMENT_PERIOD_AXIS_MISMATCH"
    BOOK_CAPITALIZATION_BASIS_UNAVAILABLE = "BOOK_CAPITALIZATION_BASIS_UNAVAILABLE"
    OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE = (
        "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE"
    )
    UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE = "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE"
    TAX_PAYABLE_AUTHORITY_UNAVAILABLE = "TAX_PAYABLE_AUTHORITY_UNAVAILABLE"
    ACCOUNTING_TREATMENT_UNRESOLVED = "ACCOUNTING_TREATMENT_UNRESOLVED"
    BALANCE_SHEET_DOES_NOT_BALANCE = "BALANCE_SHEET_DOES_NOT_BALANCE"
    CASH_FLOW_DOES_NOT_RECONCILE = "CASH_FLOW_DOES_NOT_RECONCILE"
    NON_FINITE_RESULT = "NON_FINITE_RESULT"


class LineAuthority(str, Enum):
    """Per-line accounting authority label."""

    EXISTING_CLEAN_AUTHORITY = "EXISTING_CLEAN_AUTHORITY"
    DERIVED_ACCOUNTING_ROLL_FORWARD = "DERIVED_ACCOUNTING_ROLL_FORWARD"
    GENERIC_FINCO_ACCOUNTING_POLICY = "GENERIC_FINCO_ACCOUNTING_POLICY"
    SOURCE_PROVEN_CONFIGURATION = "SOURCE_PROVEN_CONFIGURATION"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class IncomeStatementPeriod:
    """One period of the clean Income Statement (P&L).

    Book depreciation authority: OperatingSchedules.book_depreciation_keur
    (NOT tax depreciation — the tax bridge carries tax depreciation).
    SHL interest expense = gross accrued interest (cash + PIK).
    CIT = canonical tax accrual (tax_keur) — never recomputed here.
    """

    period_index: int
    period_start: date | None
    period_end: date | None
    is_construction: bool

    revenue_keur: float
    opex_keur: float
    ebitda_keur: float
    book_depreciation_keur: float
    ebit_keur: float

    senior_interest_expense_keur: float
    shl_interest_expense_keur: float
    net_financial_result_keur: float

    earnings_before_tax_keur: float
    cit_accrual_keur: float
    net_income_keur: float

    authority: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TaxBridgePeriod:
    """Accrual vs cash tax bridge + loss carryforward audit (pass-through of
    canonical TaxAndCfadsSchedules audit vectors)."""

    period_index: int
    taxable_income_before_losses_keur: float | None
    taxable_profit_after_losses_keur: float | None
    fiscal_reintegration_keur: float | None
    tax_loss_opening_keur: float | None
    tax_loss_used_keur: float | None
    tax_loss_closing_keur: float | None
    tax_depreciation_keur: float | None
    cit_accrual_keur: float | None
    cash_tax_current_period_keur: float | None
    corporate_tax_cash_keur: float | None
    cash_tax_bridge_reconciliation_keur: float | None


@dataclass(frozen=True)
class PFCashWaterfallPeriod:
    """One period of the PF Cash Waterfall statement (Option A).

    This is the project-finance cash waterfall (clearly labelled as such —
    NOT an IFRS IAS 7 statutory cash flow). Every movement row reconciles
    exactly once to the clean G2C waterfall.
    """

    period_index: int
    cashflow_date: date | None
    is_construction: bool

    revenue_cash_keur: float
    opex_cash_keur: float
    ebitda_keur: float
    cash_tax_keur: float

    fcf_banks_keur: float                      # post-tax, pre-DS cash for banks
    senior_cash_interest_keur: float
    senior_principal_keur: float
    senior_debt_service_keur: float

    dsra_top_up_keur: float
    dsra_draw_keur: float
    dsra_release_keur: float

    distribution_account_inflow_keur: float
    distribution_account_release_keur: float
    distribution_account_closing_keur: float

    shl_cash_interest_keur: float
    shl_pik_keur: float                        # non-cash (memo)
    shl_principal_paid_keur: float
    shl_unpaid_principal_keur: float

    legal_equity_distribution_keur: float
    equity_contributions_keur: float
    senior_draw_keur: float | None             # construction financing draws


@dataclass(frozen=True)
class FixedAssetRollForwardPeriod:
    """Accumulated book depreciation roll-forward (causal).

    Gross/NFA basis requires a book-capitalization authority that does not
    exist on clean results yet — gross_fixed_assets_keur is intentionally
    None with BOOK_CAPITALIZATION_BASIS_UNAVAILABLE.
    """

    period_index: int
    period_end: date | None
    book_depreciation_keur: float
    accumulated_book_depreciation_keur: float
    gross_fixed_assets_keur: float | None
    accumulated_depreciation_on_disposals_keur: float
    net_fixed_assets_keur: float | None


@dataclass(frozen=True)
class RetainedEarningsPeriod:
    """Retained earnings roll-forward.

    closing = opening + net income - legal equity distributions
              - legal reserve allocation + explicit equity adjustments

    SHL is debt, NOT retained earnings — never deducted here. No balancing
    plug: opening retained earnings requires a construction-period equity
    accounting authority that clean inputs do not yet provide, so the
    opening is surfaced as unavailable rather than defaulted to zero.
    """

    period_index: int
    period_end: date | None
    opening_retained_earnings_keur: float | None   # None = opening authority unavailable
    net_income_keur: float
    legal_equity_distribution_keur: float
    legal_reserve_allocation_keur: float | None
    closing_retained_earnings_keur: float | None   # None while opening unavailable


@dataclass(frozen=True)
class BalanceSheetPeriod:
    """Balance-sheet presentation (PARTIAL / honest-unavailable by design).

    Senior, SHL, DA and DSRA balances are clean closing-balance authority.
    Unrestricted cash requires a causal unrestricted-cash roll-forward that
    the clean runtime does not yet provide — therefore the Balance Sheet is
    NOT claimed complete and no residual-cash plug is applied.
    """

    period_index: int
    period_end: date | None
    senior_debt_balance_keur: float | None
    shl_balance_keur: float | None
    shl_unpaid_principal_keur: float | None
    distribution_account_balance_keur: float | None
    dsra_balance_keur: float | None
    unrestricted_cash_keur: float | None          # None = authority unavailable
    gross_fixed_assets_keur: float | None
    accumulated_book_depreciation_keur: float | None
    share_capital_keur: float | None
    share_premium_keur: float | None
    retained_earnings_keur: float | None
    balance_check_keur: float | None              # None = not claimed


@dataclass(frozen=True)
class AccountingPolicies:
    """Typed accounting-policy labels for every derived rule."""

    pnl_depreciation: str = "BOOK_DEPRECIATION (OperatingSchedules.book_depreciation_keur)"
    pnl_shl_interest: str = "GROSS_ACCRUED (cash + PIK)"
    pnl_cit: str = "CANONICAL_TAX_ACCRUAL (TaxAndCfadsSchedules.tax_keur)"
    cash_statement: str = "PF_CASH_WATERFALL (project-finance convention, not IAS 7)"
    retained_earnings: str = "DERIVED_ROLL_FORWARD (NI - legal distributions; SHL is debt)"
    legal_reserve: str = "NOT_APPLICABLE (no generic legal-reserve authority)"
    fixed_asset_basis: str = "BOOK_CAPITALIZATION_BASIS_UNAVAILABLE"
    unrestricted_cash: str = "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE"
    opening_retained_earnings: str = "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE"
    provenance: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialStatementsResult:
    """Phase C3 decision-complete output (honest partial availability)."""

    status: StatementStatus
    project_inputs_summary: dict

    income_statement_status: StatementStatus
    income_statement_periods: tuple[IncomeStatementPeriod, ...]

    tax_bridge_status: StatementStatus
    tax_bridge_periods: tuple[TaxBridgePeriod, ...]
    terminal_unpaid_tax_keur: float | None

    cash_flow_status: StatementStatus
    pf_cash_waterfall_periods: tuple[PFCashWaterfallPeriod, ...]

    fixed_asset_status: StatementStatus
    fixed_asset_periods: tuple[FixedAssetRollForwardPeriod, ...]

    retained_earnings_status: StatementStatus
    retained_earnings_periods: tuple[RetainedEarningsPeriod, ...]

    balance_sheet_status: StatementStatus
    balance_sheet_periods: tuple[BalanceSheetPeriod, ...]

    accounting_policies: AccountingPolicies
    unavailable_reasons: dict = field(default_factory=dict)
    authority_labels: dict = field(default_factory=dict)
