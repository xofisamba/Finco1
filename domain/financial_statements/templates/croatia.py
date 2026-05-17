"""Croatia reporting template metadata for offline P&L assembly."""

from __future__ import annotations

from dataclasses import dataclass

from domain.financial_statements.inputs import FinancialStatementsConfig


@dataclass(frozen=True)
class CroatiaFinancialStatementsTemplate:
    country_iso: str = "HR"
    cit_rate: float = 0.18
    period_frequency: str = "semiannual"
    cash_tax_timing: str = "annual_h2_diagnostic"
    loss_carryforward_years: int = 5


def build_croatia_financial_statements_config(project_code: str = "") -> FinancialStatementsConfig:
    template = CroatiaFinancialStatementsTemplate()
    return FinancialStatementsConfig(
        project_code=project_code,
        template_name="croatia",
        cit_rate=template.cit_rate,
        period_frequency=template.period_frequency,
        cash_tax_timing=template.cash_tax_timing,
        loss_carryforward_years=template.loss_carryforward_years,
    )
