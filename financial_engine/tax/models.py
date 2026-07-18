"""financial_engine.tax.models — Immutable result types for Phase 2B tax.

All types are frozen dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxYearCalculationBasis:
    """Aggregated annual inputs for one tax year.

    tax_year : 0-based tax-year index (0 = first operating year)
    period_indices : actual model period indices belonging to this tax year
                     (ordered chronologically; typically two for semi-annual)
    ebitda_keur : sum of EBITDA across all periods in the year
    tax_depreciation_keur : sum of tax depreciation across all periods
    total_interest_keur : sum of gross interest across all periods
    other_fiscal_reintegration_keur : sum of other addbacks
    """
    tax_year: int
    period_indices: tuple[int, ...]
    ebitda_keur: float
    tax_depreciation_keur: float
    total_interest_keur: float
    other_fiscal_reintegration_keur: float


@dataclass(frozen=True)
class AtadAnnualResult:
    """ATAD result for one tax year, with per-period allocation."""
    tax_year: int
    total_interest_keur: float
    deduction_capacity_keur: float
    deductible_interest_keur: float
    disallowed_interest_keur: float
    binding_rule: str  # "ebitda_30pct" | "min_threshold" | "disabled"
    # Per-period allocation in chronological order (same length as basis.period_indices)
    period_deductible_keur: tuple[float, ...]
    period_disallowed_keur: tuple[float, ...]


@dataclass(frozen=True)
class TaxLossVintage:
    """One loss vintage in the annual FIFO ledger."""
    origin_tax_year: int
    last_usable_tax_year: int  # loss expires before use outside this year
    amount_keur: float
    source_label: str = ""


@dataclass(frozen=True)
class TaxAnnualLedgerEntry:
    """Loss ledger snapshot for one tax year."""
    tax_year: int
    opening_loss_keur: float
    loss_expired_keur: float
    loss_used_keur: float
    loss_generated_keur: float
    closing_loss_keur: float
    taxable_income_before_lcf_keur: float
    taxable_income_after_lcf_keur: float


@dataclass(frozen=True)
class TaxAnnualResult:
    """Full tax result for one tax year."""
    tax_year: int
    period_indices: tuple[int, ...]
    # ATAD
    total_interest_keur: float
    deduction_capacity_keur: float
    deductible_interest_keur: float
    disallowed_interest_keur: float
    atad_binding_rule: str
    # Taxable income
    ebitda_keur: float
    tax_depreciation_keur: float
    other_fiscal_reintegration_keur: float
    taxable_income_before_lcf_keur: float
    # LCF
    loss_opening_keur: float
    loss_expired_keur: float
    loss_used_keur: float
    loss_generated_keur: float
    loss_closing_keur: float
    taxable_income_after_lcf_keur: float
    # CIT
    current_tax_liability_keur: float
    # Per-period ATAD allocation (same length as period_indices)
    period_atad_deductible: tuple[float, ...]
    period_atad_disallowed: tuple[float, ...]


@dataclass(frozen=True)
class PeriodCashTaxResult:
    """Cash tax payment assignment for one model period."""
    period_index: int
    is_operation: bool
    ebitda_keur: float
    tax_year: int
    deductible_interest_keur: float
    disallowed_interest_keur: float
    other_fiscal_reintegration_keur: float
    # Taxable income shares (from the annual result, allocated to this period for audit)
    taxable_income_before_lcf_share_keur: float
    cit_accrual_share_keur: float
    cash_tax_keur: float  # actual cash payment in this period
    cfads_keur: float


@dataclass(frozen=True)
class TaxAndCfadsResult:
    """Complete Phase 2B tax and CFADS result."""
    annual_results: tuple[TaxAnnualResult, ...]
    period_results: tuple[PeriodCashTaxResult, ...]
    terminal_unpaid_tax_keur: float
