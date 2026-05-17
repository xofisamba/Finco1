"""Croatia reporting template metadata for offline P&L assembly."""

from __future__ import annotations

from dataclasses import dataclass

from domain.financial_statements.inputs import FinancialStatementsConfig
from domain.tax.loss_carryforward import LossCarryforwardConfig


@dataclass(frozen=True)
class CroatiaFinancialStatementsTemplate:
    country_iso: str = "HR"
    cit_rate: float = 0.18
    period_frequency: str = "semiannual"
    cash_tax_timing: str = "annual_h2_diagnostic"
    loss_carryforward_years: int = 5
    loss_expiry_method: str = "fifo_per_vintage"


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


def build_croatia_loss_carryforward_config(periods_per_year: int) -> LossCarryforwardConfig:
    """Build Croatia tax-law loss window semantics for the selected frequency."""

    template = CroatiaFinancialStatementsTemplate()
    return LossCarryforwardConfig(
        duration_years=template.loss_carryforward_years,
        periods_per_year=periods_per_year,
        expiry_method=template.loss_expiry_method,
        country_template=template.country_iso.lower(),
    )
