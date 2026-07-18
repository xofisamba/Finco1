"""
financial_engine.results — Immutable result types (Phase 2A + 2B).

All types are frozen dataclasses. No setattr, no post-construction mutation,
no mutable period lists.

Phase 2A provides: period_grid, operating_schedules.
Phase 2B adds: tax_and_cfads.
Unimplemented sections: financing, financial_statements, returns.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from financial_engine.provenance import EngineProvenance
    from financial_engine.validation import ValidationIssue


@dataclass(frozen=True)
class OperatingPeriodResult:
    """Immutable result for one period in the operating core."""
    period_index: int
    period_start: date
    period_end: date
    year_index: float
    period_in_year: float
    is_construction: bool
    is_operation: bool
    is_ppa_active: bool
    days_in_period: int
    day_fraction: float

    production_mwh: float
    revenue_keur: float
    opex_keur: float
    ebitda_keur: float
    book_depreciation_keur: float
    tax_depreciation_keur: float


@dataclass(frozen=True)
class OperatingSchedules:
    """Period-indexed operating schedule arrays."""
    period_indices: tuple[int, ...]
    production_mwh: tuple[float, ...]
    revenue_keur: tuple[float, ...]
    opex_keur: tuple[float, ...]
    ebitda_keur: tuple[float, ...]
    book_depreciation_keur: tuple[float, ...]
    tax_depreciation_keur: tuple[float, ...]


@dataclass(frozen=True)
class TaxAndCfadsSchedules:
    """Parallel-array tax and CFADS schedules for all model periods.

    Fields match the Phase 1 baseline snapshot schema for tax_and_cfads.
    Waterfall-specific fields (fcf_for_shl, r69, r84, r99, r102) are
    populated with zeros in Phase 2B (out of scope).
    """
    period_indices: tuple[int, ...]
    taxable_profit_keur: tuple[float, ...]
    taxable_income_before_losses_audit_keur: tuple[float, ...]
    taxable_profit_after_losses_audit_keur: tuple[float, ...]
    tax_keur: tuple[float, ...]
    corporate_tax_cash_keur: tuple[float, ...]
    cit_accrual_audit_keur: tuple[float, ...]
    tax_loss_opening_audit_keur: tuple[float, ...]
    tax_loss_closing_audit_keur: tuple[float, ...]
    tax_loss_used_audit_keur: tuple[float, ...]
    fiscal_reintegration_audit_keur: tuple[float, ...]
    tax_depreciation_audit_keur: tuple[float, ...]
    cf_after_tax_keur: tuple[float, ...]
    cash_tax_current_period_audit_keur: tuple[float, ...]
    cash_tax_bridge_reconciliation_keur: tuple[float, ...]
    cfads_keur: tuple[float, ...]
    # Out-of-scope waterfall rows — always 0.0 in Phase 2B
    fcf_for_shl_keur: tuple[float, ...]
    r69_fcf_banks_keur: tuple[float, ...]
    r84_fcf_junior_keur: tuple[float, ...]
    r99_fcf_for_distribution_keur: tuple[float, ...]
    r102_fcf_for_shl_keur: tuple[float, ...]


@dataclass(frozen=True)
class ProjectModelResult:
    """Top-level immutable result for a clean engine run.

    Phase 2A populates: period_grid, operating_schedules.
    Phase 2B additionally populates: tax_and_cfads.
    Sections declared unavailable: financing, financial_statements, returns.
    """
    provenance: "EngineProvenance"
    periods: tuple[OperatingPeriodResult, ...]
    operating_schedules: OperatingSchedules
    unavailable_sections: tuple[str, ...]
    validation_issues: tuple["ValidationIssue", ...]
    warnings: tuple[str, ...]
    tax_and_cfads: TaxAndCfadsSchedules | None = None
