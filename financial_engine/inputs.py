"""
financial_engine.inputs — Immutable Phase 2A input contract.

All types are frozen dataclasses. No mutable state.
No imports from app, finco_core, fastapi, jinja2, requests, openpyxl, pandas.
No file I/O. No project-identity dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class YieldScenario(str, Enum):
    P50 = "P_50"
    P90_10Y = "P90-10y"


@dataclass(frozen=True)
class CalendarInput:
    financial_close: date
    construction_months: int
    horizon_years: int
    ppa_years: float


@dataclass(frozen=True)
class TechnicalInput:
    capacity_mw: float
    yield_scenario: YieldScenario
    operating_hours_p50: float
    operating_hours_p90_10y: float
    pv_degradation: float
    plant_availability: float
    grid_availability: float


@dataclass(frozen=True)
class RevenueInput:
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
    co2_price_semiannual_eur_mwh: tuple[float, ...] = ()
    co2_price_eur_per_mwh_scalar: float = 0.0
    balancing_cost_eur_per_mwh: float = 0.0


@dataclass(frozen=True)
class OpexLineInput:
    name: str
    y1_amount_keur: float
    annual_inflation: float
    step_changes: tuple[tuple[int, float], ...]
    percentage_of_opex: float


@dataclass(frozen=True)
class OpexInput:
    items: tuple[OpexLineInput, ...]


@dataclass(frozen=True)
class CapexItemForDep:
    """Minimal capex item description for straight-line depreciation."""
    name: str
    amount_keur: float
    asset_class_code: str  # e.g. "civil_grid", "solar_panels", "financial_costs"
    useful_life_override: int | None = None


@dataclass(frozen=True)
class DepreciationInput:
    """CAPEX items for straight-line book/tax depreciation.

    financial_cost_useful_life_years: amortization period for items with
        asset_class_code == "financial_costs". Maps from financing.senior_tenor_years
        in the adapter; kept explicit here so the clean engine has no financing dependency.
    """
    capex_items_for_depreciation: tuple[CapexItemForDep, ...] = ()
    financial_cost_useful_life_years: int = 14


@dataclass(frozen=True)
class InputProvenance:
    source_id: str
    baseline_commit_sha: str


@dataclass(frozen=True)
class OperatingModelInput:
    calendar: CalendarInput
    technical: TechnicalInput
    revenue: RevenueInput
    opex: OpexInput
    depreciation: DepreciationInput
    source: InputProvenance
