"""
financial_engine.inputs — Immutable input contracts (Phase 2A + 2B).

All types are frozen dataclasses. No mutable state.
No imports from app, finco_core, fastapi, jinja2, requests, openpyxl, pandas.
No file I/O. No project-identity dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from financial_engine.policies.tax import TaxPolicy


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

    Both fields are required — no defaults.

    financial_cost_useful_life_years: amortization period for items with
        asset_class_code == "financial_costs". Mapped explicitly from
        financing.senior_tenor_years in the adapter.
    """
    capex_items_for_depreciation: tuple[CapexItemForDep, ...]
    financial_cost_useful_life_years: int


# ---------------------------------------------------------------------------
# Phase 2B tax input contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OpeningTaxLossVintageInput:
    """One pre-existing loss vintage carried into the model start.

    origin_tax_year : 0-based index of the tax year in which the loss was
        generated. Must be negative (losses generated before the model) or
        0 (first model tax year). Use negative integers for pre-model losses
        (e.g. -3 = three tax years before the model start).
    amount_keur : outstanding loss (must be non-negative and finite)
    source_label : optional human-readable label for audit trail
    """
    origin_tax_year: int
    amount_keur: float
    source_label: str = ""


@dataclass(frozen=True)
class PeriodInterestInput:
    """Exogenous interest expense for one model period.

    Phase 2B does not size debt — interest is provided externally.

    All three components are optional (default 0). At least one must be
    provided for the period to carry non-zero interest.
    """
    period_index: int
    senior_interest_keur: float = 0.0
    shl_interest_keur: float = 0.0
    other_interest_keur: float = 0.0

    @property
    def total_interest_keur(self) -> float:
        return self.senior_interest_keur + self.shl_interest_keur + self.other_interest_keur


@dataclass(frozen=True)
class PeriodTaxAdjustmentInput:
    """Additional fiscal adjustments for one model period.

    other_fiscal_reintegration_keur : addbacks not already captured by the
        ATAD interest-limitation mechanism. Positive = addback to taxable income.
    """
    period_index: int
    other_fiscal_reintegration_keur: float = 0.0


@dataclass(frozen=True)
class TaxCalculationInput:
    """All tax-specific inputs for a Phase 2B run.

    policy : the jurisdiction's TaxPolicy
    opening_loss_vintages : pre-model loss pool in vintage order (oldest first)
    period_interest : one entry per model period that carries interest; periods
        not listed default to zero interest
    period_adjustments : optional per-period fiscal adjustments
    """
    policy: "TaxPolicy"
    opening_loss_vintages: tuple[OpeningTaxLossVintageInput, ...]
    period_interest: tuple[PeriodInterestInput, ...]
    period_adjustments: tuple[PeriodTaxAdjustmentInput, ...] = ()


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


@dataclass(frozen=True)
class TaxCfadsModelInput:
    """Phase 2B input: operating core inputs + tax inputs.

    operating: the Phase 2A OperatingModelInput
    tax: tax policy and per-period interest / adjustment inputs
    """
    operating: OperatingModelInput
    tax: TaxCalculationInput
