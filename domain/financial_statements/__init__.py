"""Offline financial statement assembly layer."""

from domain.financial_statements.assembly import assemble_financial_statements
from domain.financial_statements.inputs import FinancialStatementsConfig
from domain.financial_statements.result import (
    BalanceSheetPeriodResult,
    BalanceSheetResult,
    FinancialStatementsResult,
    PFCashWaterfallPeriodResult,
    PFCashWaterfallResult,
    PnLPeriodResult,
    PnLStatementResult,
    TaxBridgePeriodResult,
    TaxBridgeResult,
)

__all__ = [
    "FinancialStatementsConfig",
    "BalanceSheetPeriodResult",
    "BalanceSheetResult",
    "FinancialStatementsResult",
    "PFCashWaterfallPeriodResult",
    "PFCashWaterfallResult",
    "PnLPeriodResult",
    "PnLStatementResult",
    "TaxBridgePeriodResult",
    "TaxBridgeResult",
    "assemble_financial_statements",
]
