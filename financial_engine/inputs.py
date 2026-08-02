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

from financial_engine.ppa_indexation import PpaIndexationStartPolicy

if TYPE_CHECKING:
    from financial_engine.policies.tax import TaxPolicy
    from finco_core.opex.hierarchical._inputs import OpexModelInput


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
    # PPA indexation policy — explicit timing convention chosen for this project.
    # None = not yet explicitly migrated; the legacy tariff_at_year path is preserved.
    # None is a migration state, not a financial policy assumption.
    ppa_indexation_start_policy: PpaIndexationStartPolicy | None = None
    # Required only for CONTRACT_ANNIVERSARY; raises ValueError if None when that policy is used.
    ppa_indexation_start_date: date | None = None
    # Calendar-year merchant price schedule (matches Excel CF row 30 / Inputs row 106).
    # When supplied, the orchestrator passes these through to RevenueParams instead of
    # market_prices_curve_eur_mwh.  market_inflation is NOT re-applied.
    merchant_price_calendar_start_year: int | None = None
    merchant_prices_by_calendar_year_eur_mwh: tuple[float, ...] = ()


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
    # Hierarchical OPEX capability — present when the source project carries a
    # HierarchicalOpexCapability.  None = flat-item path (default, backward-compatible).
    # TYPE_CHECKING import only; no runtime finco_core dependency at import time.
    hierarchical_model: "OpexModelInput | None" = None
    hierarchical_external_annual_series: "tuple[tuple[str, tuple[float, ...]], ...]" = ()


@dataclass(frozen=True)
class CapexItemForDep:
    """Minimal capex item description for straight-line depreciation."""
    name: str
    amount_keur: float
    asset_class_code: str  # e.g. "civil_grid", "solar_panels", "financial_costs"
    useful_life_override: int | None = None


@dataclass(frozen=True)
class DepreciationInput:
    """CAPEX items for straight-line depreciation — book and tax treated separately.

    All fields are required — no defaults.

    book_capex_items_for_depreciation:
        Items entering the BOOK depreciable basis. Includes hard capex plus
        capitalised bank financing costs (IDC, commitment fees, bank fees, VAT)
        where Excel Dep-sheet evidence confirms these are depreciated.

    tax_capex_items_for_depreciation:
        Items entering the TAX depreciable basis. Currently hard capex only.
        Tax treatment of capitalised financing costs is OPEN — each item
        requires separate authoritative tax-source evidence before inclusion.

    financial_cost_useful_life_years:
        Amortization period for items with asset_class_code == "financial_costs".
        Mapped from financing.senior_tenor_years in the adapter.
        OPEN: Excel Dep-sheet formula for useful life is unverified from
        data_only extraction. Do not tune to eliminate delta.
    """
    book_capex_items_for_depreciation: tuple[CapexItemForDep, ...]
    tax_capex_items_for_depreciation: tuple[CapexItemForDep, ...]
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


# ---------------------------------------------------------------------------
# Phase 2C senior debt input contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SeniorDebtModelInput:
    """Phase 2C input: Phase 2B inputs + senior debt policy + senior debt inputs.

    operating: Phase 2A OperatingModelInput
    tax: Phase 2B TaxCalculationInput (interest from Phase 2C solver feeds back here)
    senior_debt_policy: SeniorDebtPolicy (sizing mode, DSCR target, rates, etc.)
    senior_debt_inputs: SeniorDebtInputs (cost base, initial guess, rate schedule, etc.)
    """
    operating: "OperatingModelInput"
    tax: "TaxCalculationInput"
    senior_debt_policy: object   # SeniorDebtPolicy (avoid circular imports)
    senior_debt_inputs: object   # SeniorDebtInputs


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
