"""Phase 6C.1 — HoldCo / intercompany tax result models.

Schema only — no active calculation, no waterfall wiring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


__all__ = [
    "HoldCoTaxPeriodResult",
    "HoldCoTaxResult",
]


# ── HoldCoTaxPeriodResult ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class HoldCoTaxPeriodResult:
    """Audit-ready per-period result for HoldCo tax.

    Stores all income components and WHT fields — no active CIT calculation.

    Attributes
    ----------
    period_index : int
        Period index (0-based).
    taxable_dividend_income_keur : float
        Dividend income subject to CIT (gross, before WHT).
    taxable_interest_income_keur : float
        SHL interest income subject to CIT.
    non_taxable_principal_keur : float
        SHL principal — tracked as non-taxable recovery of investment.
        Not deducted from taxable income — simply excluded.
    deductible_opex_keur : float
        Deductible operating expenses for the period.
    taxable_income_before_limitations_keur : float
        Pre-thin-cap/EBITDA-limit taxable income.
    withholding_tax_dividends_keur : float
        WHT withheld on dividends at applicable rate. Stored, not paid.
    withholding_tax_interest_keur : float
        WHT withheld on interest at applicable rate. Stored, not paid.
    interest_limited_keur : float
        Excess interest over EBITDA limitation (ATAD). Stored, not applied.
    notes : tuple[str, ...]
        Audit notes (e.g., "SHL principal excluded from taxable income").
    warnings : tuple[str, ...]
        Warnings for review (e.g., "thin-cap exceeded in period 3").
    """
    period_index: int
    taxable_dividend_income_keur: float
    taxable_interest_income_keur: float
    non_taxable_principal_keur: float
    deductible_opex_keur: float
    taxable_income_before_limitations_keur: float
    withholding_tax_dividends_keur: float
    withholding_tax_interest_keur: float
    interest_limited_keur: float
    notes: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


# ── HoldCoTaxResult ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HoldCoTaxResult:
    """Complete HoldCo tax result across all periods.

    Schema only — no active CIT calculation.

    Attributes
    ----------
    entity_code : str
        HoldCo entity identifier.
    country_code : str
        HoldCo tax jurisdiction.
    tax_year : int
        Tax year.
    period_results : tuple[HoldCoTaxPeriodResult, ...]
        Per-period breakdown.
    total_taxable_dividend_keur : float
        Sum of all taxable dividend income.
    total_taxable_interest_keur : float
        Sum of all taxable interest income.
    total_non_taxable_principal_keur : float
        Sum of all SHL principal (non-taxable).
    total_withholding_tax_dividends_keur : float
        Total WHT on dividends (stored, not paid).
    total_withholding_tax_interest_keur : float
        Total WHT on interest (stored, not paid).
    metadata : dict
        Arbitrary metadata (e.g., input snapshot, template used).
    notes : tuple[str, ...]
        Top-level audit notes.
    """
    entity_code: str
    country_code: str
    tax_year: int
    period_results: tuple[HoldCoTaxPeriodResult, ...]
    total_taxable_dividend_keur: float
    total_taxable_interest_keur: float
    total_non_taxable_principal_keur: float
    total_withholding_tax_dividends_keur: float
    total_withholding_tax_interest_keur: float
    metadata: dict = field(default_factory=dict)
    notes: tuple[str, ...] = field(default_factory=tuple)