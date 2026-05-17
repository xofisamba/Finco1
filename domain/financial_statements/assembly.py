"""Top-level offline financial statement assembly."""

from __future__ import annotations

from domain.financial_statements.inputs import FinancialStatementsConfig
from domain.financial_statements.pnl import assemble_pnl
from domain.financial_statements.result import FinancialStatementsResult
from domain.financial_statements.tax_bridge import assemble_tax_bridge
from domain.waterfall.waterfall_engine import WaterfallResult


def assemble_financial_statements(
    waterfall_result: WaterfallResult,
    config: FinancialStatementsConfig | None = None,
) -> FinancialStatementsResult:
    """Assemble offline P&L and tax bridge outputs from an existing waterfall run."""

    effective_config = config or FinancialStatementsConfig()
    return FinancialStatementsResult(
        config=effective_config,
        pnl=assemble_pnl(waterfall_result),
        tax_bridge=assemble_tax_bridge(waterfall_result),
    )
