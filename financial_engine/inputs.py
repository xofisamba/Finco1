"""
financial_engine.inputs — Immutable Phase 2A input contract.

All types are frozen dataclasses. Lists are replaced with tuples; dicts with
read-only mappings. No optional field silently activates a project-specific
default. No project-code dispatch.

Fields are limited to what is required to calculate the Phase 2A operating
core: period grid, production, revenue, OPEX, EBITDA, book depreciation,
tax depreciation.

Financing, tax calculations, SHL, returns, and financial statements are out of
scope. Their parameters are not present here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class YieldScenario(str, Enum):
    P50 = "P_50"
    P90_10Y = "P90-10y"


@dataclass(frozen=True)
class CalendarInput:
    """Temporal axis for the model."""
    financial_close: date
    construction_months: int
    horizon_years: int
    ppa_years: float


@dataclass(frozen=True)
class TechnicalInput:
    """Production and availability assumptions."""
    capacity_mw: float
    yield_scenario: YieldScenario
    operating_hours_p50: float
    operating_hours_p90_10y: float
    pv_degradation: float
    plant_availability: float
    grid_availability: float


@dataclass(frozen=True)
class RevenueInput:
    """Revenue assumptions for PPA and merchant periods."""
    ppa_base_tariff_eur_mwh: float
    ppa_term_years: float
    ppa_index: float
    ppa_production_share: float
    market_prices_curve_eur_mwh: tuple[float, ...]
    market_inflation: float
    balancing_cost_pv_fraction: float
    balancing_cost_wind_eur_mwh: float
    co2_enabled: bool
    co2_price_eur_mwh: float
    first_merchant_operating_period_index: int | None = None
    # Rich schedule overrides (semiannual operating-period indexed tuples).
    # When non-empty, these take precedence over the scalar fields above.
    co2_price_semiannual_eur_mwh: tuple[float, ...] = ()
    co2_price_eur_per_mwh_scalar: float = 0.0
    balancing_cost_eur_per_mwh: float = 0.0


@dataclass(frozen=True)
class OpexLineInput:
    """One OPEX line item."""
    name: str
    y1_amount_keur: float
    annual_inflation: float
    step_changes: tuple[tuple[int, float], ...]
    percentage_of_opex: float


@dataclass(frozen=True)
class OpexInput:
    """Operating cost assumptions."""
    items: tuple[OpexLineInput, ...]


@dataclass(frozen=True)
class AssetInput:
    """One CAPEX asset class for depreciation (used by validation tests)."""
    asset_class: str
    gross_asset_basis_keur: float
    book_depreciable_basis_keur: float
    tax_depreciable_basis_keur: float
    placed_in_service_period: int
    book_useful_life_years: int
    tax_useful_life_years: int


@dataclass(frozen=True)
class CapexItemForDep:
    """Minimal capex item for straight-line depreciation via build_depreciation_schedule."""
    name: str
    amount_keur: float
    asset_class_code: str  # e.g. "civil_grid", "solar_panels", "financial_costs"
    useful_life_override: int | None = None


@dataclass(frozen=True)
class DepreciationInput:
    """CAPEX items and parameters for straight-line book/tax depreciation."""
    capex_items_for_depreciation: tuple[CapexItemForDep, ...] = ()
    senior_tenor_years: int = 14
    # Legacy fields kept for validation-test backward compat (not used by orchestrator).
    assets: tuple[AssetInput, ...] = ()
    period_count: int = 0
    cod_period: int = 0


@dataclass(frozen=True)
class InputProvenance:
    """Origin metadata for the clean input contract."""
    source_id: str
    baseline_commit_sha: str


@dataclass(frozen=True)
class OperatingModelInput:
    """Root immutable Phase 2A input contract."""
    calendar: CalendarInput
    technical: TechnicalInput
    revenue: RevenueInput
    opex: OpexInput
    depreciation: DepreciationInput
    source: InputProvenance
