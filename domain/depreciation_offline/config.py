"""Depreciation configuration dataclasses and template defaults."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AssetCategoryRule:
    """Per-category depreciation rule.

    Parameters
    ----------
    category_id : str
        Unique identifier for the asset category (e.g. "turbines", "idc").
    category_name : str
        Human-readable label.
    capex_amount_keur : float
        Gross asset basis for this category in kEUR.
    useful_life_years : int
        Depreciation period in years.
    depreciation_method : str
        Depreciation method. Currently supported: "straight_line".
    start_period : int
        Period index (0-based) when depreciation begins.
    end_period : Optional[int]
        If provided, explicitly caps the schedule at this period.
        Otherwise inferred from useful_life_years.
    residual_value_keur : float, default 0.0
        Scrap/residual value at end of useful life.
    is_financing_cost : bool, default False
        True for IDC/commitment fees/bank fees.
    source_reference : str, default ""
        Reference to source data (e.g. "Excel Inputs!D358").
    frequency : str, default "semiannual"
        "semiannual" or "annual".
    """

    category_id: str
    category_name: str
    capex_amount_keur: float
    useful_life_years: int
    depreciation_method: str = "straight_line"
    start_period: int = 0
    end_period: Optional[int] = None
    residual_value_keur: float = 0.0
    is_financing_cost: bool = False
    source_reference: str = ""
    frequency: str = "semiannual"

    def useful_life_periods(self) -> int:
        """Convert useful life from years to number of periods."""
        if self.frequency == "semiannual":
            return self.useful_life_years * 2
        return self.useful_life_years

    def depreciable_basis_keur(self) -> float:
        """Return capex minus residual value."""
        return self.capex_amount_keur - self.residual_value_keur


@dataclass
class DepreciationConfig:
    """Top-level configuration for a depreciation run."""

    asset_categories: list[AssetCategoryRule] = field(default_factory=list)
    period_count: int = 60
    period_frequency: str = "semiannual"
    country_template: str = "croatia"
    fallback_warning_enabled: bool = True


@dataclass
class DepreciationTemplate:
    """Country / template-level defaults for useful life by asset category."""

    template_id: str
    template_name: str
    defaults: dict[str, int] = field(default_factory=dict)
    notes: str = ""