"""Depreciation schedule result dataclasses."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DepreciationScheduleEntry:
    """One period's depreciation output for a single asset category."""

    period_index: int
    book_depreciation_keur: float
    tax_depreciation_keur: float
    cumulative_book_keur: float
    cumulative_tax_keur: float
    remaining_book_basis_keur: float
    remaining_tax_basis_keur: float
    is_zero_after_life: bool = False

    def book_depreciation_if_active(self, end_period: Optional[int] = None) -> float:
        """Return book depreciation, or 0.0 if period is past useful life."""
        return self.book_depreciation_keur


@dataclass
class DepreciationScheduleResult:
    """Full schedule for one asset category."""

    category_id: str
    entries: list[DepreciationScheduleEntry]
    total_book_depreciation_keur: float
    total_tax_depreciation_keur: float
    frequency: str

    def book_entry(self, period_index: int) -> Optional[DepreciationScheduleEntry]:
        """Return the entry for a given period index, or None."""
        for e in self.entries:
            if e.period_index == period_index:
                return e
        return None