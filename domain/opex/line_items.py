"""OPEX line-item schema — groups and items for the OPEX engine.

This module defines the data model for OPEX groups and items.
All OPEX calculations use this schema.

Basis types:
  fixed_annual_keur  — budget is annual cost in kEUR, constant year-over-year
  fixed_period_keur  — budget is per-period cost in kEUR (same as fixed_annual for annual engine)
  eur_per_mw_year    — budget is EUR/MW/year (× capacity_mw gives EUR, /1000 = kEUR)
  eur_per_mwh        — budget is EUR/MWh (× generation_mwh / 1000 = kEUR)
  pct_of_revenue     — budget is decimal percentage (e.g. 0.02 = 2%) × revenue
  pct_of_group       — budget is decimal percentage × named group's total cost
  pct_of_selected_groups — contingency: budget is % × sum of selected groups' totals
  explicit_schedule  — budget is a list of annual values; no inflation applied
  inactive           — always returns 0 regardless of other settings

Schedule indexing (explicit_schedule):
  semiannual_values[0] = first operating year (Y1)
  semiannual_values[1] = Y2
  ...
  Length must match the `years` parameter passed to compute_annual_opex().
  No construction offset — purely user-facing operating-year indexing.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OpexBasis(Enum):
    """OPEX item basis type — how budget_keur is interpreted."""
    FIXED_ANNUAL_KEUR = "fixed_annual_keur"
    FIXED_PERIOD_KEUR = "fixed_period_keur"
    EUR_PER_MW_YEAR = "eur_per_mw_year"
    EUR_PER_MWH = "eur_per_mwh"
    PCT_OF_REVENUE = "pct_of_revenue"
    PCT_OF_GROUP = "pct_of_group"
    PCT_OF_SELECTED_GROUPS = "pct_of_selected_groups"
    EXPLICIT_SCHEDULE = "explicit_schedule"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class OpexItemStep:
    """Step change: at a given year, item base budget changes to a new value.

    The new budget takes effect at step_year and inflation then compounds
    from that year (not from Y1).

    Args:
        year_index: 1-based operating year when step takes effect
        new_budget_keur: new annual base amount in kEUR
        description: human-readable reason for the step change
    """
    year_index: int
    new_budget_keur: float
    description: str = ""


@dataclass(frozen=True)
class ManualOverride:
    """Manual period-level override for an OPEX item.

    Override takes precedence over calculated value (except inactive flag).

    Override values are NOT inflated — they are used as-is as the final amount.

    Args:
        year_index: 1-based operating year
        value_keur: override value in kEUR (used as-is, not inflated)
        source: origin of override ("manual", "import", "reset", etc.)
    """
    year_index: int
    value_keur: float
    source: str = "manual"


@dataclass(frozen=True)
class OpexItem:
    """Single OPEX line item.

    Args:
        code: item code e.g. "B.01.1" or "" for unclassified
        name: item display name
        budget_keur: base amount (interpretation depends on basis)
        basis: how budget_keur is interpreted
        group_code: parent group code e.g. "B.01"
        inflation_rate: annual inflation rate (decimal, e.g. 0.02 = 2%).
            None = inherit from group.
        wth_rate: withholding tax rate (decimal, e.g. 0.1 = 10%).
            0.0 = no WTH. WTH is treated as added cost, not deducted from base.
        active_flags: list of bools per operating year (1=active, 0=inactive).
            If None or shorter than years, missing years default to True (active).
        explicit_schedule_keur: explicit annual values for explicit_schedule basis.
            Length should match the number of operating years. No inflation applied.
        manual_overrides: ManualOverride entries per year. Year with no override
            uses calculated value. Manual override is NOT inflated.
        step_changes: OpexItemStep entries. Step becomes new base at step year,
            then inflation compounds from step year (not from Y1).
        selected_group_codes: for pct_of_group or pct_of_selected_groups basis.
            List of group codes whose totals are used in the percentage calculation.
        notes: free-text notes

    Basis-specific notes:
      fixed_annual_keur: base = budget_keur × (1 + inflation)^(year-1)
      fixed_period_keur: same as fixed_annual for annual engine
      eur_per_mw_year: base = budget_keur (EUR/MW/year) × capacity_mw / 1000
      eur_per_mwh: base = budget_keur (EUR/MWh) × production_mwh / 1000
      pct_of_revenue: base = revenue_keur × budget_keur (budget = decimal fraction)
      pct_of_group: base = group_total_keur × budget_keur (budget = decimal fraction)
      pct_of_selected_groups: base = sum(selected groups' totals) × budget_keur
      explicit_schedule: base = explicit_schedule_keur[year_index-1]; no inflation
      inactive: base = 0 regardless of other settings
    """
    code: str = ""
    name: str = ""
    budget_keur: float = 0.0
    basis: OpexBasis = OpexBasis.FIXED_ANNUAL_KEUR
    group_code: str = ""
    inflation_rate: Optional[float] = None
    wth_rate: float = 0.0
    active_flags: tuple[bool, ...] = field(default_factory=tuple)
    explicit_schedule_keur: tuple[float, ...] = field(default_factory=tuple)
    manual_overrides: tuple[ManualOverride, ...] = field(default_factory=tuple)
    step_changes: tuple[OpexItemStep, ...] = field(default_factory=tuple)
    selected_group_codes: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def is_active(self, year_index: int) -> bool:
        """Return whether item is active in the given year (1-based)."""
        idx = year_index - 1
        if self.active_flags and idx < len(self.active_flags):
            return bool(self.active_flags[idx])
        return True  # default: always active

    def override_for(self, year_index: int) -> Optional[ManualOverride]:
        """Return ManualOverride for year_index, or None."""
        for mo in self.manual_overrides:
            if mo.year_index == year_index:
                return mo
        return None

    def step_at_or_before(self, year_index: int) -> Optional[OpexItemStep]:
        """Return the most recent step at or before year_index, or None."""
        applicable = [s for s in self.step_changes if s.year_index <= year_index]
        if not applicable:
            return None
        return max(applicable, key=lambda s: s.year_index)

    def effective_budget(self, year_index: int) -> float:
        """Return the base budget after applying step changes at year_index.

        Inflation is NOT applied here — this returns the pre-inflation base.
        """
        step = self.step_at_or_before(year_index)
        if step:
            return step.new_budget_keur
        return self.budget_keur

    def inflation(self) -> Optional[float]:
        """Return inflation rate (item rate or None for group-level)."""
        return self.inflation_rate


@dataclass(frozen=True)
class OpexGroup:
    """OPEX group containing related items.

    Args:
        code: group code e.g. "B.01"
        name: group display name e.g. "Technical Management"
        inflation_rate: group-level inflation rate (decimal).
            Items with inflation_rate=None inherit this rate.
            Items with explicit inflation_rate use their own rate.
        wth_rate: group-level WTH rate. Items with wth_rate=0 inherit this.
        items: child OpexItem instances
        order: sort order for display
        editable: whether group is user-editable
        contingency_pct: if > 0, this group is a contingency group computed as
            pct × sum of selected groups' totals. The group's items must use
            pct_of_selected_groups basis.
    """
    code: str = ""
    name: str = ""
    inflation_rate: float = 0.0
    wth_rate: float = 0.0
    items: tuple[OpexItem, ...] = field(default_factory=tuple)
    order: int = 0
    editable: bool = True
    contingency_pct: float = 0.0  # 0 = not a contingency group

    def item_by_code(self, code: str) -> Optional[OpexItem]:
        """Find item by code within this group."""
        for item in self.items:
            if item.code == code:
                return item
        return None