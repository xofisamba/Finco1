"""financial_engine.tax.models — Immutable result types for Phase 2B tax.

All types are frozen dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxYearCalculationBasis:
    """Aggregated annual inputs used for the ATAD and taxable-income calculation.

    tax_year_index : 0-based year counter within the horizon
    h1_period_index : model period index of the H1 period for this year
    h2_period_index : model period index of the H2 period for this year (or None
        if only one period exists in the final year)
    annual_ebitda_keur : sum of EBITDA across both periods
    annual_gross_interest_keur : sum of gross interest across both periods
    annual_tax_depreciation_keur : sum of tax depreciation across both periods
    annual_other_fiscal_reintegration_keur : sum of addbacks
    """
    tax_year_index: int
    h1_period_index: int
    h2_period_index: int | None
    annual_ebitda_keur: float
    annual_gross_interest_keur: float
    annual_tax_depreciation_keur: float
    annual_other_fiscal_reintegration_keur: float


@dataclass(frozen=True)
class AtadPeriodResult:
    """ATAD result for one model period."""
    period_index: int
    gross_interest_keur: float
    deductible_interest_keur: float
    disallowed_addback_keur: float
    annual_limit_keur: float
    limit_type: str
    is_h1: bool


@dataclass(frozen=True)
class TaxLossVintage:
    """One loss vintage in the FIFO ledger."""
    amount_keur: float
    periods_remaining: int
    source_period_index: int | None
    source_label: str


@dataclass(frozen=True)
class TaxLossLedgerYear:
    """Loss ledger snapshot for one model period."""
    period_index: int
    opening_loss_keur: float
    loss_used_keur: float
    loss_generated_keur: float
    loss_expired_keur: float
    closing_loss_keur: float
    taxable_income_before_losses_keur: float
    taxable_profit_after_losses_keur: float


@dataclass(frozen=True)
class PeriodTaxResult:
    """Full tax result for one model period."""
    period_index: int
    is_operation: bool
    ebitda_keur: float
    tax_depreciation_keur: float
    gross_interest_keur: float
    deductible_interest_keur: float
    disallowed_addback_keur: float
    other_fiscal_reintegration_keur: float
    taxable_income_before_losses_keur: float
    loss_opening_keur: float
    loss_used_keur: float
    loss_generated_keur: float
    loss_expired_keur: float
    loss_closing_keur: float
    taxable_profit_after_losses_keur: float
    cit_accrual_keur: float
    cash_tax_keur: float


@dataclass(frozen=True)
class TaxSchedules:
    """Parallel arrays for all tax schedule fields, one value per model period."""
    period_indices: tuple[int, ...]
    taxable_profit_keur: tuple[float, ...]
    taxable_income_before_losses_keur: tuple[float, ...]
    taxable_profit_after_losses_keur: tuple[float, ...]
    tax_keur: tuple[float, ...]
    corporate_tax_cash_keur: tuple[float, ...]
    cit_accrual_keur: tuple[float, ...]
    tax_loss_opening_keur: tuple[float, ...]
    tax_loss_closing_keur: tuple[float, ...]
    tax_loss_used_keur: tuple[float, ...]
    fiscal_reintegration_keur: tuple[float, ...]
    tax_depreciation_audit_keur: tuple[float, ...]
    cf_after_tax_keur: tuple[float, ...]
    cash_tax_current_period_keur: tuple[float, ...]
    cash_tax_bridge_reconciliation_keur: tuple[float, ...]
