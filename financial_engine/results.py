"""
financial_engine.results — Immutable result types for Phase 2A operating core.

All types are frozen dataclasses. No setattr, no post-construction mutation,
no mutable period lists.

Phase 2A provides: period_grid, operating_schedules.
Unimplemented sections: tax_and_cfads, financing, financial_statements, returns.
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
class ProjectModelResult:
    """Top-level immutable result for one Phase 2A run.

    Phase 2A populates: period_grid, operating_schedules.
    Sections declared unavailable: tax_and_cfads, financing,
    financial_statements, returns (out of Phase 2A scope).
    """
    provenance: "EngineProvenance"
    periods: tuple[OperatingPeriodResult, ...]
    operating_schedules: OperatingSchedules
    unavailable_sections: tuple[str, ...]
    validation_issues: tuple["ValidationIssue", ...]
    warnings: tuple[str, ...]
