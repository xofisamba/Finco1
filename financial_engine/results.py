"""
financial_engine.results — Immutable result types (Phase 2A + 2B).

All types are frozen dataclasses. No setattr, no post-construction mutation,
no mutable period lists.

Phase 2A provides: period_grid, operating_schedules.
Phase 2B adds: tax_and_cfads (annual tax, period cash tax, canonical CFADS).
Unimplemented: financing, financial_statements, returns.
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
    ebit_keur: float


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
    ebit_keur: tuple[float, ...]


@dataclass(frozen=True)
class TaxAndCfadsSchedules:
    """Parallel-array tax and CFADS schedules for all model periods.

    Field names match the Phase 1 baseline snapshot schema for tax_and_cfads.

    Phase 2B populates all fields that the clean engine computes.
    Unimplemented waterfall rows (fcf_for_shl, r69, r84, r99, r102) are NOT
    included here — they belong to Phase 2C+ and are declared unavailable in
    the candidate snapshot's unavailable_fields map.

    terminal_unpaid_tax_keur : annual CIT liabilities whose cash-tax payment
        falls outside the model horizon due to the payment lag.
    """
    period_indices: tuple[int, ...]
    # Taxable income trail
    taxable_profit_keur: tuple[float, ...]
    taxable_income_before_losses_audit_keur: tuple[float, ...]
    taxable_profit_after_losses_audit_keur: tuple[float, ...]
    # Tax (accrual and cash)
    tax_keur: tuple[float, ...]                          # CIT accrual share per period
    corporate_tax_cash_keur: tuple[float, ...]           # actual cash payment per period
    cit_accrual_audit_keur: tuple[float, ...]
    cash_tax_bridge_reconciliation_keur: tuple[float, ...]
    cash_tax_current_period_audit_keur: tuple[float, ...]
    # LCF audit trail
    tax_loss_opening_audit_keur: tuple[float, ...]
    tax_loss_closing_audit_keur: tuple[float, ...]
    tax_loss_used_audit_keur: tuple[float, ...]
    # Supplementary audit fields
    fiscal_reintegration_audit_keur: tuple[float, ...]
    tax_depreciation_audit_keur: tuple[float, ...]
    cf_after_tax_keur: tuple[float, ...]  # EBITDA - cash_tax per period (matches legacy definition)
    # Canonical CFADS (primary deliverable)
    cfads_keur: tuple[float, ...]
    # Terminal unpaid tax (annual liabilities not yet paid within the model horizon)
    terminal_unpaid_tax_keur: float


@dataclass(frozen=True)
class SeniorDebtSchedules:
    """Phase 2C per-period senior debt schedules.

    senior_dscr: None where debt service is zero (avoids division by zero).
    debt_size_keur: final sized/solved opening debt balance at COD.
    binding_constraint: "DSCR", "GEARING", "BOTH", or None.
    diagnostics: solver convergence metadata (dict for JSON serialisability).
    """
    period_indices: tuple[int, ...]
    senior_debt_opening_keur: tuple[float, ...]
    senior_interest_keur: tuple[float, ...]
    senior_principal_keur: tuple[float, ...]
    senior_debt_service_keur: tuple[float, ...]
    senior_debt_closing_keur: tuple[float, ...]
    senior_dscr: tuple[float | None, ...]
    debt_size_keur: float
    binding_constraint: str | None
    diagnostics: dict  # SolverDiagnostics serialised to dict
    # Bank-sizing CFADS audit (one entry per debt period, aligned to period_indices).
    # None when no bank_sizing_scenario was provided (base = bank, current behaviour).
    bank_sizing_cfads_keur: tuple[float, ...] | None = None
    # Bank-sizing DSCR: bank_sizing_cfads[p] / senior_debt_service[p].
    # Populated only when bank_sizing_scenario is active.  None entries where DS = 0.
    # Semantics: this is the SIZING/bank DSCR, not the actual/economic project DSCR.
    bank_sizing_dscr: tuple[float | None, ...] | None = None


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
    senior_debt: "SeniorDebtSchedules | None" = None
