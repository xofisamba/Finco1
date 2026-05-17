"""Offline financial statement assembly layer."""

from domain.financial_statements.assembly import assemble_financial_statements
from domain.financial_statements.inputs import FinancialStatementsConfig
from domain.financial_statements.result import (
    FinancialStatementsResult,
    PnLPeriodResult,
    PnLStatementResult,
    TaxBridgePeriodResult,
    TaxBridgeResult,
)

__all__ = [
    "FinancialStatementsConfig",
    "FinancialStatementsResult",
    "PnLPeriodResult",
    "PnLStatementResult",
    "TaxBridgePeriodResult",
    "TaxBridgeResult",
    "assemble_financial_statements",
]
