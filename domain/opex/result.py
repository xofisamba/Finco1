"""OPEX result dataclasses — annual results for the OPEX engine.

These dataclasses expose per-year, per-group, per-item OPEX breakdown.
Used for audit, export, and UI display.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class OpexItemAnnualResult:
    """Annual result for a single OPEX item in a single year.

    Fields:
        year_index: 1-based operating year
        group_code: parent group code
        group_name: parent group name
        item_code: item code
        item_name: item name
        active: whether item was active this year
        basis: basis type string
        budget_keur: original budget amount in kEUR
        calculated_keur: computed amount before manual override (includes inflation)
        manual_override_keur: manual override value if present, else None
        inflation_rate: effective inflation rate used
        wth_rate: effective WTH rate used
        wth_keur: WTH amount (final + wth)
        total_keur: final amount (manual override or calculated + WTH)
        is_manual_override: True if manual override was used this year

    Note:
        calculated_keur is pre-override. If manual_override exists,
        total_keur = manual_override + wth_keur and is_manual_override = True.
        calculated_keur is still the inflation-adjusted computed value
        (useful for comparison).
    """
    year_index: int
    group_code: str
    group_name: str
    item_code: str
    item_name: str
    active: bool
    basis: str
    budget_keur: float
    calculated_keur: float
    manual_override_keur: Optional[float]
    inflation_rate: float
    wth_rate: float
    wth_keur: float
    total_keur: float
    is_manual_override: bool


@dataclass(frozen=True)
class OpexGroupAnnualResult:
    """Annual result for an OPEX group (aggregated across items)."""
    year_index: int
    group_code: str
    group_name: str
    item_results: tuple[OpexItemAnnualResult, ...]
    group_total_keur: float
    contingency_from_groups_keur: float = 0.0


@dataclass(frozen=True)
class OpexAnnualResult:
    """Full annual OPEX result across all groups and years."""
    years: tuple[int, ...]  # year indices included (e.g. (1, 2, ..., 30))
    group_results: tuple[OpexGroupAnnualResult, ...]
    total_by_year_keur: tuple[float, ...]  # indexed by position in years
    grand_total_keur: float

    def year_index_to_position(self, year_index: int) -> int:
        """Convert 1-based year_index to 0-based position in years tuple."""
        return self.years.index(year_index)

    def total_for_year(self, year_index: int) -> float:
        """Return total OPEX for a given year."""
        pos = self.year_index_to_position(year_index)
        return self.total_by_year_keur[pos]

    def group_result(self, year_index: int, group_code: str) -> Optional[OpexGroupAnnualResult]:
        """Find group result for a specific year and group."""
        for gr in self.group_results:
            if gr.year_index == year_index and gr.group_code == group_code:
                return gr
        return None

    def item_result(self, year_index: int, group_code: str, item_code: str) -> Optional[OpexItemAnnualResult]:
        """Find item result for a specific year, group, and item."""
        gr = self.group_result(year_index, group_code)
        if not gr:
            return None
        for ir in gr.item_results:
            if ir.item_code == item_code:
                return ir
        return None