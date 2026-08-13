"""Generic project-finance input models for the runtime engine.

Authoritative location: finco_core.inputs._models (V2-2).
Legacy location finco_core.inputs re-exports from here.

The dataclasses in this module define immutable inputs for project,
portfolio, and scenario calculations. They intentionally contain schema and
validation only; project-specific defaults live outside the domain layer.

Runtime dependencies:
    finco_core.inputs.senior_rate_schedule  — SeniorDebtInterestConfig
    finco_core.inputs.senior_sculpting      — SeniorSculptingConfig

"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, TYPE_CHECKING

from finco_core.inputs.senior_rate_schedule import SeniorDebtInterestConfig
from finco_core.inputs.senior_sculpting import SeniorSculptingConfig

if TYPE_CHECKING:
    from finco_core.inputs.bess import BessParams
    from finco_core.opex._capability import HierarchicalOpexCapability


class PeriodFrequency(Enum):
    """Supported reporting and calculation period frequencies."""
    SEMESTRIAL = "Semestrial"
    ANNUAL = "Annual"
    QUARTERLY = "Quarterly"


class PeriodAxisConvention(str, Enum):
    """Project period-axis policy for construction and operating boundaries."""
    COD_ANCHOR_TWO_CONSTRUCTION_COLUMNS = "cod_anchor_two_construction_columns"
    OPERATING_BOUNDARY_SINGLE_CONSTRUCTION_COLUMN = "operating_boundary_single_construction_column"


class EquityIRRMethod(Enum):
    """Supported equity return cash-flow conventions."""
    EQUITY_ONLY = "equity_only"
    COMBINED = "combined"
    SHL_PLUS_DIVIDENDS = "shl_plus_dividends"


class DebtSizingMethod(Enum):
    """Supported senior-debt sizing approaches."""
    DSCR_SCULPT = "dscr_sculpt"
    GEARING_CAP = "gearing_cap"
    FIXED = "fixed"

class DebtSizingMode(Enum):
    """Senior debt sizing calibration modes.

    Mode C (FROZEN_EXCEL_SCHEDULE) is the default — it preserves current runtime
    behavior by treating the Excel-derived debt amount and per-period service
    schedule as frozen inputs. DSCR is an outcome.

    Mode B (FLAT_DSCR_SCULPTED) is supported via the clean senior-debt
    source-contract adapter for SEMESTRIAL projects (C3B3A).
    Mode A (MINIMUM_DSCR_SCULPTED) is not yet implemented.

    Attributes:
        FROZEN_EXCEL_SCHEDULE: Debt amount and/or per-period service schedule
            are treated as frozen inputs (from Excel calibration). DSCR is a
            backward-computed outcome. This is the default mode and preserves
            current runtime behavior.
        MINIMUM_DSCR_SCULPTED: TUHO-style solver that finds the debt amount
            so that the minimum DSCR across all periods meets a target
            (e.g. ~1.45). Per-period service uses the DSCR divisor schedule
            (1.20 during PPA, ~1.41 during merchant). NOT YET IMPLEMENTED.
        FLAT_DSCR_SCULPTED: Sculpted solver with a configurable target DSCR.
            Supported by the clean senior-debt source-contract adapter
            (build_senior_debt_contract_from_project_inputs). The clean solver
            supports a scalar policy.target_dscr fallback plus explicit
            per-period target_dscr_schedule overrides. Oborovo source truth
            uses 1.15x for periods P1–P24 and 1.35x for periods P25–P28.
            This does NOT imply legacy runtime promotion or support for every
            project or period frequency — the FROZEN_EXCEL_SCHEDULE runtime path
            remains unaffected.
    """

    FROZEN_EXCEL_SCHEDULE = "frozen_excel_schedule"
    MINIMUM_DSCR_SCULPTED = "minimum_dscr_sculpted"
    FLAT_DSCR_SCULPTED = "flat_dscr_sculpted"

    def validate_and_resolve(self) -> "DebtSizingMode":
        """Return resolved mode, raising for unimplemented future modes.

        Currently only FROZEN_EXCEL_SCHEDULE is fully implemented.
        Future modes are allowed as config values for documentation purposes
        but raise NotImplementedError at resolve time unless their
        corresponding implementation flag is set.
        """
        if self in (
            DebtSizingMode.FROZEN_EXCEL_SCHEDULE,
            DebtSizingMode.MINIMUM_DSCR_SCULPTED,
            DebtSizingMode.FLAT_DSCR_SCULPTED,
        ):
            return self
        raise ValueError(f"Unknown DebtSizingMode: {self}")



class SHLRepaymentMethod(Enum):
    """Supported shareholder-loan repayment conventions."""
    BULLET = "bullet"
    CASH_SWEEP = "cash_sweep"
    PIK = "pik"
    ACCRUED = "accrued"
    PIK_THEN_SWEEP = "pik_then_sweep"
    PARTIAL_PAY_SWEEP = "partial_pay_sweep"
    FCF_WATERFALL = "fcf_waterfall"


class YieldScenario(Enum):
    """Supported production-yield scenarios."""
    P50 = "P_50"
    P90_10Y = "P90-10y"
    P99_1Y = "P99-1y"


class AssetClass(Enum):
    """Asset class for depreciation and useful-life selection."""
    SOLAR_PANELS = "solar_panels"
    WIND_TURBINES = "wind_turbines"
    BESS_CELLS = "bess_cells"
    BESS_POWER_ELECTRONICS = "bess_pe"
    CIVIL_GRID = "civil_grid"
    SOFT_COSTS = "soft_costs"
    FINANCIAL_COSTS = "financial_costs"


ASSET_CLASS_USEFUL_LIFE: dict[AssetClass, int] = {
    AssetClass.SOLAR_PANELS: 25,
    AssetClass.WIND_TURBINES: 25,
    AssetClass.BESS_CELLS: 10,
    AssetClass.BESS_POWER_ELECTRONICS: 15,
    AssetClass.CIVIL_GRID: 30,
    AssetClass.SOFT_COSTS: 5,
    AssetClass.FINANCIAL_COSTS: 14,
}


@dataclass(frozen=True)
class ProjectInfo:
    """Basic project metadata and project timeline."""
    name: str
    company: str
    code: str
    country_iso: str
    financial_close: date
    construction_months: int
    cod_date: date
    horizon_years: int
    period_frequency: PeriodFrequency
    use_opex_line_item_engine: bool = False
    use_construction_schedule_engine: bool = False
    use_senior_rate_schedule_engine: bool = False
    use_senior_sculpting_basis_engine: bool = False
    use_shl_fcf_waterfall_engine: bool = False
    use_shl_canonical_engine: bool = False
    use_canonical_tax_depreciation_bridge: bool = False
    use_depreciation_canonical_engine: bool = False
    use_tax_bridge_engine: bool = False
    use_senior_debt_sizing_engine: bool = False
    use_shl_gross_accrued_for_pnl: bool = False
    use_book_depreciation_for_pnl: bool = False
    period_axis_convention: PeriodAxisConvention = (
        PeriodAxisConvention.COD_ANCHOR_TWO_CONSTRUCTION_COLUMNS
    )


@dataclass(frozen=True)
class CapexItem:
    """Single capital-expenditure line item with a spending profile."""
    name: str
    amount_keur: float
    y0_share: float = 0.0
    spending_profile: tuple[float, ...] = ()
    asset_class: AssetClass = AssetClass.CIVIL_GRID
    useful_life_override: Optional[int] = None
    # Asset-level depreciable flag driven by source asset/CAPEX treatment.
    # True (default) for all standard hard-CAPEX items in Oborovo.
    # Set False for land or explicitly non-depreciable items.
    # Filters book_depreciable_capex_items() when False.
    is_depreciable: bool = True

    @property
    def total_spending_shares(self) -> float:
        """Sum of all spending shares across construction periods."""
        return self.y0_share + sum(self.spending_profile)

    def __post_init__(self):
        """Validate that non-zero spending profiles sum to 100%."""
        total = self.total_spending_shares
        if total > 0 and abs(total - 1.0) > 0.001:
            raise ValueError(
                f'{self.name}: spending shares sum to {total:.4f}, expected 1.0. '
                f'Check spending_profile or y0_share values.'
            )

    def amount_in_period(self, period: int) -> float:
        """Return the capital-expenditure amount for a construction period.

        Args:
            period: 0 for the initial period, 1 for the first profile period,
                and so on.

        Returns:
            Amount in kEUR for the requested period.
        """
        if period == 0:
            return self.amount_keur * self.y0_share
        idx = period - 1
        if idx < len(self.spending_profile):
            return self.amount_keur * self.spending_profile[idx]
        return 0.0


@dataclass(frozen=True)
class CapexStructure:
    """Capital-expenditure structure used by the financial model.

    The named fields provide a stable schema for UI tables, imports, and
    existing callers. Generic factories may map individual technologies to
    these fields while preserving asset-class metadata on each CapexItem.
    """
    epc_contract: CapexItem
    production_units: CapexItem
    epc_other: CapexItem
    grid_connection: CapexItem
    ops_prep: CapexItem
    insurances: CapexItem
    lease_tax: CapexItem
    construction_mgmt_a: CapexItem
    commissioning: CapexItem
    audit_legal: CapexItem
    construction_mgmt_b: CapexItem
    contingencies: CapexItem
    taxes: CapexItem
    project_acquisition: CapexItem
    project_rights: CapexItem

    # SOURCE-DERIVED CALIBRATION VALUES — pending generic monthly Construction/IDC runtime.
    # These fields hold DERIVED OUTPUTS from the workbook construction financing model,
    # temporarily carried as calibration inputs. They are NOT permanent primary inputs and
    # MUST NOT be generalised as hardcoded engine constants for other projects.
    # Future: computed by generic ConstructionFinancingEngine → BookDepreciableAssetBasis.
    idc_keur: float = 0.0          # Senior Debt IDC (derived from debt draws × rate × day-count)
    commitment_fees_keur: float = 0.0  # Senior Debt commitment fees (derived from undrawn × rate)
    # Structuring / arrangement fees paid to lenders, capitalised into Gross Fixed Assets.
    # Derived from fee_rate × facility basis — NOT a universal fixed input.
    bank_fees_keur: float = 0.0
    other_financial_keur: float = 0.0
    # VAT-facility financing costs — explicitly decomposed sub-fields.
    # Semantic distinction (MANDATORY — do not conflate):
    #   vat_costs_keur              = TOTAL capitalised VAT-facility financing cost = idc + commitment
    #   vat_facility_idc_keur       = VAT Facility IDC (derived: VAT facility req × rate × day-count)
    #   vat_facility_commitment_fee_keur = VAT Facility commitment fee (derived: undrawn × rate)
    #   Construction VAT payable    ≈ 7,665 kEUR (a separate working-capital flow, NOT in GFA)
    # Oborovo source: vat_facility_idc_keur=208.448 + vat_facility_commitment_fee_keur=13.622 = 222.070.
    vat_costs_keur: float = 0.0  # total VAT-facility capitalised financing = idc + commitment
    vat_facility_idc_keur: float = 0.0        # derived sub-component
    vat_facility_commitment_fee_keur: float = 0.0  # derived sub-component
    reserve_accounts_keur: float = 0.0

    _CAPEX_ITEM_FIELDS = (
        "epc_contract", "production_units", "epc_other", "grid_connection",
        "ops_prep", "insurances", "lease_tax", "construction_mgmt_a",
        "commissioning", "audit_legal", "construction_mgmt_b", "contingencies",
        "taxes", "project_acquisition", "project_rights",
    )

    def capex_items(self) -> tuple[CapexItem, ...]:
        """Return all non-zero CapexItem entries."""
        return tuple(
            getattr(self, field) for field in self._CAPEX_ITEM_FIELDS
            if getattr(self, field).amount_keur != 0
        )

    def book_depreciable_capex_items(self) -> tuple[CapexItem, ...]:
        """Return items included in the BOOK depreciable basis.

        Contract: hard capex items (capex_items()) plus bank financing costs
        capitalised into the asset base:
          - idc_keur        : bank interest during construction, capitalised
          - commitment_fees_keur: bank commitment fees, capitalised
          - bank_fees_keur  : bank structuring / arrangement fees, capitalised
          - vat_costs_keur  : VAT on capital expenditure, capitalised

        These fields are on CapexStructure (not OpexStructure) because they
        represent capitalised costs forming part of the gross asset value.
        Their presence here is itself the evidence of capitalisation.

        Excel Dep-sheet evidence (Oborovo): dep_idc_keur, dep_commitment_fees_keur,
        dep_bank_fees_keur, dep_vat_keur are all non-zero across operating periods,
        confirming these costs enter the book depreciable basis.

        SHL IDC is excluded — it is on FinancingStructure, not CapexStructure,
        and its book/tax treatment is OPEN.

        Useful-life evidence (Oborovo Inputs sheet, MANUAL_WORKBOOK_SOURCE_EVIDENCE,
        confirmed 2026-07-22): IDC, commitment fees, bank fees → 12-year book life;
        VAT costs → 20-year book life. Each component is returned as a separate
        CapexItem with useful_life_override set to the proven per-component year count
        so canonical_wiring.py can apply distinct straight-line schedules.
        """
        items = [i for i in self.capex_items() if i.is_depreciable]
        # Each financing component has a distinct proven book useful life;
        # use_life_override carries the year count to canonical_wiring.
        if self.idc_keur > 0:
            items.append(CapexItem(
                name="IDC (Interest During Construction)",
                amount_keur=self.idc_keur,
                asset_class=AssetClass.FINANCIAL_COSTS,
                useful_life_override=12,
            ))
        if self.commitment_fees_keur > 0:
            items.append(CapexItem(
                name="Commitment Fees",
                amount_keur=self.commitment_fees_keur,
                asset_class=AssetClass.FINANCIAL_COSTS,
                useful_life_override=12,
            ))
        if self.bank_fees_keur > 0:
            items.append(CapexItem(
                name="Bank Fees",
                amount_keur=self.bank_fees_keur,
                asset_class=AssetClass.FINANCIAL_COSTS,
                useful_life_override=12,
            ))
        if self.vat_costs_keur > 0:
            items.append(CapexItem(
                name="VAT Costs",
                amount_keur=self.vat_costs_keur,
                asset_class=AssetClass.FINANCIAL_COSTS,
                useful_life_override=20,
            ))
        return tuple(items)

    def tax_depreciable_capex_items(self) -> tuple[CapexItem, ...]:
        """Return items included in the TAX depreciable basis.

        Currently returns hard capex only (same as capex_items()).

        Tax treatment of capitalised financing costs (IDC, commitment fees,
        bank fees, VAT) is OPEN — no authoritative per-project tax evidence
        has been validated. These items are excluded until explicit tax
        source evidence is confirmed for each item.
        """
        return self.capex_items()

    def depreciable_capex_items(self) -> tuple[CapexItem, ...]:
        """Backward-compat alias for book_depreciable_capex_items().

        Prefer book_depreciable_capex_items() for new callers.
        """
        return self.book_depreciable_capex_items()

    @property
    def hard_capex_keur(self) -> float:
        """Sum of all hard-capex items, excluding financing and reserve costs."""
        items = [
            self.epc_contract, self.production_units, self.epc_other,
            self.grid_connection, self.ops_prep, self.insurances,
            self.lease_tax, self.construction_mgmt_a, self.commissioning,
            self.audit_legal, self.construction_mgmt_b, self.contingencies,
            self.taxes, self.project_acquisition, self.project_rights,
        ]
        return sum(item.amount_keur for item in items)

    @property
    def hard_capex(self) -> float:
        """Backward-compatible alias for hard_capex_keur."""
        return self.hard_capex_keur

    @property
    def sculpt_capex_keur(self) -> float:
        """Capital cost base used for debt sizing.

        Reserve accounts are excluded because they are funded separately from
        the project's hard capital cost.
        """
        return (self.hard_capex_keur + self.idc_keur +
                self.bank_fees_keur + self.other_financial_keur + self.vat_costs_keur)

    @property
    def total_capex_before_idc(self) -> float:
        """Total capital cost before interest during construction."""
        return self.hard_capex_keur + self.commitment_fees_keur + \
               self.bank_fees_keur + self.other_financial_keur + \
               self.vat_costs_keur + self.reserve_accounts_keur

    @property
    def total_capex(self) -> float:
        """Total capital cost including interest during construction."""
        return self.total_capex_before_idc + self.idc_keur


@dataclass(frozen=True)
class OpexItem:
    """Single operating-cost line item with escalation and optional steps."""
    name: str
    y1_amount_keur: float
    annual_inflation: float = 0.02
    step_changes: tuple[tuple[int, float], ...] = field(default_factory=lambda: ())
    # If > 0, this item is a contingency calculated as a percentage of other OPEX.
    # percentage_of_opex = X means: amount = X * sum_of_other_fixed_opex_items (excl. self)
    # This is mutually exclusive with step_changes — do not use both on same item.
    percentage_of_opex: float = 0.0

    def amount_at_year(self, year: int) -> float:
        """Return operating cost for a 1-based operating year."""
        for step_year, amount in self.step_changes:
            if year == step_year:
                return amount
        result = self.y1_amount_keur * (1 + self.annual_inflation) ** (year - 1)
        return max(0.0, result)


@dataclass(frozen=True)
class TechnicalParams:
    """Technical production and availability assumptions."""
    capacity_mw: float
    yield_scenario: str
    operating_hours_p50: float = 0.0
    operating_hours_p90_1y: float | None = None
    operating_hours_p90_10y: float = 0.0
    operating_hours_p99_1y: float | None = None
    pv_degradation: float = 0.004
    bess_degradation: float = 0.003
    plant_availability: float = 0.99
    grid_availability: float = 0.99
    bess_enabled: bool = False
    bess: "BessParams | None" = None

    @property
    def combined_availability(self) -> float:
        """Combined plant and grid availability."""
        return self.plant_availability * self.grid_availability


@dataclass(frozen=True)
class RevenueAdjustmentSchedule:
    """Operating-period schedule for revenue adjustment inputs.

    The schedule is indexed by operating periods only: semiannual_values[0] is
    Y1-H1, semiannual_values[1] is Y1-H2, and construction/stub periods do not
    consume values.
    """
    constant_value: float = 0.0
    annual_values: tuple[float, ...] = ()
    semiannual_values: tuple[float, ...] = ()

    def value_for_period(
        self,
        *,
        operating_period_index: int,
        operating_year_index: int,
        period_in_year: int,
    ) -> float:
        """Return the EUR/MWh value for a given operating period."""
        if self.semiannual_values and operating_period_index < len(self.semiannual_values):
            return self.semiannual_values[operating_period_index]
        if self.annual_values:
            year_idx = operating_year_index - 1
            if year_idx < len(self.annual_values):
                return self.annual_values[year_idx]
        return self.constant_value


@dataclass(frozen=True)
class RevenueParams:
    """Revenue parameters for contracted and merchant sales."""
    ppa_base_tariff: float
    ppa_term_years: float
    ppa_index: float = 0.02
    ppa_production_share: float = 1.0
    market_scenario: str = "Central"
    market_prices_curve: tuple[float, ...] = ()
    market_inflation: float = 0.02
    balancing_cost_pv: float = 0.025
    balancing_cost_bess: float = 0.025
    balancing_cost_wind_eur_mwh: float = 0.0
    co2_enabled: bool = False
    co2_price_eur: float = 1.5
    # Phase 7: explicit certificate and balancing cost inputs (EUR/MWh)
    co2_certificate_price_eur_per_mwh: float = 0.0
    balancing_cost_eur_per_mwh: float = 0.0
    balancing_cost_schedule: RevenueAdjustmentSchedule | None = None
    co2_sales_schedule: RevenueAdjustmentSchedule | None = None
    first_merchant_operating_period_index: int | None = None
    # PPA indexation policy — string name of PpaIndexationStartPolicy enum, or None.
    # None = not yet explicitly migrated; orchestrator uses legacy tariff_at_year path.
    ppa_indexation_start_policy: str | None = None
    ppa_indexation_start_date: date | None = None
    # Pre-computed per-operating-period tariff schedule (indexed by operating_period_index).
    # When non-empty, tariff_at_operating_period() uses this instead of the analytic formula.
    ppa_tariff_by_operating_period: tuple[float, ...] = ()
    # Calendar-year merchant price schedule.  When supplied, market_price_for_period()
    # uses YEAR(period_end) as the lookup key, matching Excel CF row 30 semantics.
    # market_price_calendar_start_year must be set when this tuple is non-empty.
    # Values are already-nominal selected-scenario prices; market_inflation is NOT
    # re-applied to them.
    market_price_calendar_start_year: int | None = None
    market_prices_by_calendar_year_eur_mwh: tuple[float, ...] = ()

    def tariff_at_year(self, year: int) -> float:
        """Return indexed contract tariff for a 1-based operating year (legacy path).

        Prefer tariff_at_operating_period() when ppa_tariff_by_operating_period is set.
        """
        return self.ppa_base_tariff * (1 + self.ppa_index) ** (year - 1)

    def tariff_at_operating_period(self, operating_period_index: int) -> float | None:
        """Return indexed tariff for a given 0-based operating period index.

        Returns None when ppa_tariff_by_operating_period is empty (caller should fall
        back to tariff_at_year).
        """
        if self.ppa_tariff_by_operating_period and operating_period_index >= 0:
            if operating_period_index < len(self.ppa_tariff_by_operating_period):
                return self.ppa_tariff_by_operating_period[operating_period_index]
        return None

    def market_price_at_year(self, year: int) -> float:
        """Return merchant market price for a 1-based operating year (legacy path)."""
        idx = year - 1
        if idx < len(self.market_prices_curve):
            return self.market_prices_curve[idx]
        if self.market_prices_curve:
            base = self.market_prices_curve[-1]
            return base * (1 + self.market_inflation) ** (idx - len(self.market_prices_curve) + 1)
        return self.ppa_base_tariff

    def market_price_for_period(self, period_end_year: int, operating_year: int) -> float:
        """Return merchant market price for a period.

        When market_prices_by_calendar_year_eur_mwh is supplied, looks up the price
        for period_end_year (calendar year of the period end date), matching Excel
        CF row 30: INDEX(row106, MATCH(YEAR(period_end), row96)).

        Falls back to market_price_at_year(operating_year) when no calendar-year
        schedule is present, preserving existing behavior for all other projects.

        Raises ValueError on invalid combinations (curve without start year, or
        period_end_year outside the supplied range).
        """
        if self.market_prices_by_calendar_year_eur_mwh:
            if self.market_price_calendar_start_year is None:
                raise ValueError(
                    "market_prices_by_calendar_year_eur_mwh is set but "
                    "market_price_calendar_start_year is None"
                )
            idx = period_end_year - self.market_price_calendar_start_year
            n = len(self.market_prices_by_calendar_year_eur_mwh)
            if idx < 0:
                # Period falls before the merchant start year (e.g. PPA years).
                # Spot price is irrelevant here; caller is responsible for using
                # ppa_active to skip merchant revenue calculation.
                return 0.0
            if idx >= n:
                # Beyond the supplied calendar-year range: extrapolate from the
                # last entry using market_inflation, matching the documented
                # fallback behavior of market_price_at_year().
                base = self.market_prices_by_calendar_year_eur_mwh[-1]
                return base * (1 + self.market_inflation) ** (idx - n + 1)
            return self.market_prices_by_calendar_year_eur_mwh[idx]
        if self.market_price_calendar_start_year is not None and not self.market_prices_by_calendar_year_eur_mwh:
            raise ValueError(
                "market_price_calendar_start_year is set but "
                "market_prices_by_calendar_year_eur_mwh is empty"
            )
        return self.market_price_at_year(operating_year)


@dataclass(frozen=True)
class DebtSizingCaseConfig:
    """Project-owned bank/debt-sizing economic case assumptions.

    This canonical input config mirrors the clean runtime DebtSizingCaseInput
    without importing the financial_engine package into finco_core. It is
    intentionally explicit and project-identity-free: factories may set
    source-compatible values, while the engine consumes only these fields.
    """

    production_yield_scenario: YieldScenario = YieldScenario.P90_10Y
    merchant_price_calendar_start_year: int | None = None
    merchant_prices_by_calendar_year_eur_mwh: tuple[float, ...] = ()
    market_prices_curve_eur_mwh: tuple[float, ...] = ()
    source_label: str = ""

    def __post_init__(self) -> None:
        has_calendar = (
            self.merchant_price_calendar_start_year is not None
            or bool(self.merchant_prices_by_calendar_year_eur_mwh)
        )
        has_curve = bool(self.market_prices_curve_eur_mwh)
        if has_calendar and has_curve:
            raise ValueError(
                "DebtSizingCaseConfig: calendar-year merchant prices and "
                "market_prices_curve_eur_mwh are mutually exclusive."
            )
        if (
            self.merchant_price_calendar_start_year is not None
            and not self.merchant_prices_by_calendar_year_eur_mwh
        ):
            raise ValueError(
                "DebtSizingCaseConfig: merchant_price_calendar_start_year is set but "
                "merchant_prices_by_calendar_year_eur_mwh is empty."
            )
        if (
            self.merchant_prices_by_calendar_year_eur_mwh
            and self.merchant_price_calendar_start_year is None
        ):
            raise ValueError(
                "DebtSizingCaseConfig: merchant_prices_by_calendar_year_eur_mwh is "
                "supplied but merchant_price_calendar_start_year is None."
            )
        if self.merchant_price_calendar_start_year is not None:
            if isinstance(self.merchant_price_calendar_start_year, bool) or not isinstance(
                self.merchant_price_calendar_start_year, int
            ):
                raise ValueError(
                    "DebtSizingCaseConfig: merchant_price_calendar_start_year must be an integer year."
                )
            if self.merchant_price_calendar_start_year < 1:
                raise ValueError(
                    "DebtSizingCaseConfig: merchant_price_calendar_start_year must be >= 1."
                )
        for field_name, values in (
            ("merchant_prices_by_calendar_year_eur_mwh", self.merchant_prices_by_calendar_year_eur_mwh),
            ("market_prices_curve_eur_mwh", self.market_prices_curve_eur_mwh),
        ):
            for i, value in enumerate(values):
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(
                        f"DebtSizingCaseConfig: {field_name}[{i}] must be a finite numeric value, "
                        f"got {value!r}."
                    )
                if value != value or value in (float("inf"), float("-inf")):
                    raise ValueError(
                        f"DebtSizingCaseConfig: {field_name}[{i}] must be a finite numeric value, "
                        f"got {value!r}."
                    )


@dataclass(frozen=True)
class FinancingParams:
    """Debt, equity, reserve, and shareholder-loan assumptions."""
    share_capital_keur: float = 500.0
    share_premium_keur: float = 0.0
    shl_amount_keur: float = 13547.2
    shl_rate: float = 0.08

    gearing_ratio: float = 0.7524
    senior_debt_amount_keur: float = 0.0
    senior_tenor_years: int = 14
    base_rate: float = 0.03
    margin_bps: int = 265
    floating_share: float = 0.2
    fixed_share: float = 0.8
    hedge_coverage: float = 0.8

    commitment_fee: float = 0.0105
    arrangement_fee: float = 0.0
    structuring_fee: float = 0.01

    target_dscr: float = 1.15
    lockup_dscr: float = 1.10
    min_llcr: float = 1.15

    amortization_type: str = "sculpted"
    fixed_ds_keur: float = 0.0

    dsra_months: int = 6

    equity_irr_method: str = "equity_only"

    debt_sizing_method: str = "dscr_sculpt"
    debt_sizing_mode: "DebtSizingMode | None" = None
    target_min_dscr: float | None = None
    flat_dscr_target: float | None = None
    frozen_schedule_note: str | None = None
    use_frozen_excel_senior_debt_schedule: bool = False
    frozen_senior_ds_fixture_path: str | None = None
    fixed_debt_keur: float | None = None
    dscr_schedule: list[float] | None = None
    senior_debt_interest_config: SeniorDebtInterestConfig = field(default_factory=SeniorDebtInterestConfig)
    senior_sculpting_config: SeniorSculptingConfig = field(default_factory=SeniorSculptingConfig)
    debt_sizing_case: DebtSizingCaseConfig = field(default_factory=DebtSizingCaseConfig)

    shl_repayment_method: str = "bullet"
    shl_pik_switch_period: int = 0
    shl_tenor_years: int = 0
    shl_idc_keur: float = 0.0
    clean_shl_principal_keur: float | None = None
    clean_shl_repayment_method: str | None = None
    shl_day_count_convention: str | None = None
    shl_construction_day_count_fraction: float | None = None
    shl_principal_eligibility_start_period: int | None = None
    shl_maturity_period_index: int | None = None
    shl_fcf_waterfall_cash_schedule_keur: tuple[float, ...] = ()
    shl_fcf_waterfall_minimum_cash_retained_keur: float = 0.0

    use_senior_sweep_cash_cap_for_shl: bool = False
    use_tuho_r99_input_engine: bool = False
    use_tuho_shl_repayment_alignment: bool = False
    tuho_shl_principal_eligibility_start_period: int | None = None

    @property
    def all_in_rate(self) -> float:
        """All-in senior debt interest rate."""
        return self.base_rate + self.margin_bps / 10000

    @property
    def total_equity_shl_keur(self) -> float:
        """Total sponsor equity and shareholder-loan funding."""
        return self.share_capital_keur + self.share_premium_keur + self.shl_amount_keur + self.shl_idc_keur

    def resolved_debt_sizing_mode(self) -> "DebtSizingMode":
        """Resolve the effective debt sizing mode."""
        if self.debt_sizing_mode is not None:
            return self.debt_sizing_mode.validate_and_resolve()
        return DebtSizingMode.FROZEN_EXCEL_SCHEDULE

    @property
    def sizing_mode_description(self) -> str:
        """Return human-readable description of current sizing mode."""
        mode = self.resolved_debt_sizing_mode()
        if mode == DebtSizingMode.FROZEN_EXCEL_SCHEDULE:
            note = f" ({self.frozen_schedule_note})" if self.frozen_schedule_note else ""
            return f"FROZEN_EXCEL_SCHEDULE{note} — DSCR is computed from fixed service schedule"
        if mode == DebtSizingMode.FLAT_DSCR_SCULPTED:
            return f"FLAT_DSCR_SCULPTED — closed-form sculpting, uniform DSCR = {self.target_dscr}"
        if mode == DebtSizingMode.MINIMUM_DSCR_SCULPTED:
            return "MINIMUM_DSCR_SCULPTED — closed-form sculpting, per-period DSCR schedule"
        return f"{mode.value}"


class ShlInterestDeductibilityMode(str, Enum):
    """How SHL (Shareholder Loan) interest is treated for corporate income tax.

    This is a TAX POLICY enum — not a model/workbook convention.

    Deductible-only arithmetic (C3B3C):
        Only the deductible fraction of SHL interest enters the ATAD pool.
        The non-deductible fraction is simply never deducted — it is not
        added back to taxable income. shl_non_deductible_keur in TaxPeriodResult
        is an audit field only.

    FULLY_DEDUCTIBLE:
        SHL interest is treated identically to senior interest for CIT purposes.
        The full SHL gross amount enters the ATAD pool alongside senior interest.
        shl_interest_deductible_pct must be absent or 1.0.

    FULLY_NON_DEDUCTIBLE:
        SHL interest is entirely non-deductible. Zero SHL interest enters the ATAD
        pool. The gross SHL amount is never deducted — no fiscal addback is required.
        Oborovo source: C59=100%, D59=TRUE → zero SHL deduction for all periods
        (proved from C3B1 fixture). shl_interest_deductible_pct must be absent or 0.0.

    SUBJECT_TO_LIMITATIONS:
        SHL deductibility is subject to active interest limitation mechanisms
        (thin-cap, ATAD, or both). Deductible amount is determined by whichever
        enabled limitation engine fires. Requires at least one limitation enabled.
        thin_cap_enabled=True + unsupported formula → FAIL CLOSED (C3B3C).

        SOURCE_POLICY_CAPTURED_RUNTIME_NOT_PROMOTED: this mode stores source
        metadata only. It has no legacy-waterfall runtime implementation.
        The legacy engine preserves prior SHL-fully-deductible behavior until
        the thin-cap formula is proven and explicitly activated.

    CUSTOM_DEDUCTIBLE_PERCENTAGE:
        A fixed fraction of SHL interest is deductible. Only that fraction enters
        the ATAD pool; the non-deductible fraction is never deducted (no addback).
        shl_interest_deductible_pct is required (0.0 ≤ pct ≤ 1.0).
    """
    FULLY_DEDUCTIBLE = "fully_deductible"
    FULLY_NON_DEDUCTIBLE = "fully_non_deductible"
    SUBJECT_TO_LIMITATIONS = "subject_to_limitations"
    CUSTOM_DEDUCTIBLE_PERCENTAGE = "custom_deductible_percentage"

    @property
    def legacy_runtime_supported(self) -> bool:
        """Whether the legacy waterfall engine can execute this deductibility mode.

        SUBJECT_TO_LIMITATIONS has no legacy implementation (thin-cap formula not yet
        proven). Source metadata may be stored but must not be promoted to the legacy
        runtime. The legacy engine defaults to SHL-fully-deductible behavior instead.

        SOURCE_POLICY_CAPTURED_RUNTIME_NOT_PROMOTED applies to SUBJECT_TO_LIMITATIONS.
        """
        return self != ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS


class TaxLossUtilisationGate(str, Enum):
    """Gate condition that must be satisfied before tax losses can be utilised.

    This is a MODEL CONVENTION enum — not a universal tax law.

    TAXABLE_INCOME_POSITIVE:
        Canonical mode. Loss carryforward can be applied only when taxable
        income before losses is positive. This is the standard conceptual rule.
        Generic/default projects should use this mode unless source evidence
        proves otherwise.

    EBT_POSITIVE:
        Workbook convention observed in Oborovo and TUHO Excel models.
        Source workbook formula: IF(AND(losses_available<=0, EBT>0), ...).
        Loss carryforward can be applied only when EBT (Earnings Before Tax,
        i.e. EBIT minus all financing interest) is positive.

        This differs from TAXABLE_INCOME_POSITIVE: a project can have positive
        taxable income but negative EBT (e.g. due to non-deductible SHL interest
        that is excluded from the ATAD pool but also not an addback).
        For Oborovo, EBT stays negative during debt service due to SHL interest,
        so allocated_losses=0 always under EBT_POSITIVE gate.

        IMPORTANT: do not call this Croatian tax law. It is a workbook model
        convention. The clean engine fails closed on EBT_POSITIVE unless
        explicitly supported — see TaxParams.tax_loss_utilisation_gate.
    """
    TAXABLE_INCOME_POSITIVE = "taxable_income_positive"
    EBT_POSITIVE = "ebt_positive"


class TaxPeriodisationMode(str, Enum):
    """How CIT annual amounts are periodised in a semi-annual model.

    This is a MODEL CONVENTION enum.

    CALENDAR_TAX_YEAR:
        Clean engine convention. Annual CIT is aggregated on a calendar-year
        (Jan–Dec) basis and placed in the last semi-annual period of that year
        (TAX_YEAR_LAST_PERIOD). This is the supported production mode.

    WORKBOOK_MODEL_YEAR_PAIRING:
        Source workbook convention (Oborovo, TUHO). Each fiscal year is formed
        by pairing H2(year N) + H1(year N+1). CIT fires in the even period
        (H1 of the model year). This is structurally different from CALENDAR_TAX_YEAR
        and is the root cause of WORKBOOK_PERIODISATION_MISMATCH.

        UNSUPPORTED IN PRODUCTION — fail closed. May appear as source metadata
        or calibration annotation only. Do not expose as an editable runtime input.
    """
    CALENDAR_TAX_YEAR = "calendar_tax_year"
    WORKBOOK_MODEL_YEAR_PAIRING = "workbook_model_year_pairing"


class ShlAccountingTreatment(str, Enum):
    """How SHL (Shareholder Loan) construction-period interest is accounted for.

    Separates the ACCOUNTING question from the PAYMENT question.
    See also ShlPaymentMethod.

    EXPENSE_TO_PNL:
        SHL construction interest is recorded as an expense in the P&L
        (interest expense line). It is NOT capitalised into the depreciable
        asset basis (GFA). This is the treatment for Oborovo and TUHO:
        SHL construction interest flows through P&L, not into GFA.

    CAPITALIZE_TO_ASSET:
        SHL construction interest is capitalised into the qualifying asset
        (GFA / depreciable basis). This increases the asset cost and therefore
        depreciation. NOT applicable to Oborovo or TUHO as proven by source.
    """
    EXPENSE_TO_PNL = "expense_to_pnl"
    CAPITALIZE_TO_ASSET = "capitalize_to_asset"


class ShlPaymentMethod(str, Enum):
    """How SHL interest is settled (cash vs capitalisation into the liability).

    Separates the PAYMENT question from the ACCOUNTING question.
    See also ShlAccountingTreatment.

    PIK_TO_SHL_BALANCE:
        SHL interest is not paid in cash during the accrual period.
        It is added (PIK = Payment In Kind) to the SHL liability balance.
        Oborovo and TUHO: SHL construction interest accretes into the SHL
        balance (opening SHL + PIK → closing SHL). NOT the same as
        capitalisation into the asset (ShlAccountingTreatment.CAPITALIZE_TO_ASSET).

    CASH_PAID:
        SHL interest is settled in cash in the period it accrues.
    """
    PIK_TO_SHL_BALANCE = "pik_to_shl_balance"
    CASH_PAID = "cash_paid"


class TaxDepreciationMode(str, Enum):
    """Engine capability: how tax-deductible depreciation is derived for CIT.

    This is an ENGINE CAPABILITY enum — not a country tax policy.
    Which mode a project uses is determined by its selected Tax Policy
    (future: versioned country/jurisdiction policy library) plus any
    project-level overrides. See docs/tax_policy_library_future_contract.md.

    BOOK_BASED_PERCENTAGE: tax_dep = book_dep * tax_deductible_book_dep_pct.
        Used when the tax authority allows deduction based on accounting
        depreciation (possibly at a percentage). Oborovo source workbook shows
        100% deductibility with no add-back in the Fiscal Reintegration bridge.
    STATUTORY_TAX_SCHEDULE: independent tax-asset-group schedule, separate from
        book. Used when statutory lives/methods differ from IFRS book lives.
        NOT YET IMPLEMENTED — raises NotImplementedError.
    CUSTOM_SCHEDULE: externally supplied period-by-period tax depreciation.
        NOT YET IMPLEMENTED — raises NotImplementedError.
    """
    BOOK_BASED_PERCENTAGE = "book_based_percentage"
    STATUTORY_TAX_SCHEDULE = "statutory_tax_schedule"
    CUSTOM_SCHEDULE = "custom_schedule"


@dataclass(frozen=True)
class TaxParams:
    """Tax, withholding, and interest-deductibility assumptions."""
    corporate_rate: float = 0.10
    loss_carryforward_years: int = 5
    loss_carryforward_cap: float = 1.0
    prior_tax_loss_keur: float = 0.0
    legal_reserve_cap: float = 0.10

    construction_pl: Optional["ConstructionPLStatement"] = None

    thin_cap_enabled: bool = False
    thin_cap_de_ratio: float = 0.8

    # ATAD interest limitation (Article 4 ATAD). True = apply 30%/€3m cap.
    # INDEPENDENT of thin_cap_enabled — neither is derived from the other (C3B3D0).
    # Default False: generic/multi-jurisdiction projects must not silently activate
    # a jurisdiction-specific limitation. Old-payload backward compatibility is
    # handled by the deserialization fallback (→ thin_cap_enabled), not by this default.
    atad_enabled: bool = False

    atad_ebitda_limit: float = 0.30
    atad_min_interest_keur: float = 3000.0

    wht_sponsor_dividends: float = 0.05
    wht_sponsor_shl_interest: float = 0.0

    # DEPRECATED — preserved for backward compatibility with serialised payloads.
    # Use shl_interest_deductibility instead.
    # When shl_interest_deductibility is not set, shl_cap_applies=True was the
    # prior signal for "some SHL restriction applies" but was never wired to the engine.
    shl_cap_applies: bool = True

    # ── SHL Interest Deductibility Policy (C3B3C) ──────────────────────────────
    # Typed replacement for the ambiguous shl_cap_applies boolean.
    # Governs what fraction of gross SHL interest enters the ATAD pool.
    # Deductible-only method: only the deductible fraction is deducted from
    # taxable income; the non-deductible fraction is simply never deducted
    # (no addback required).
    #
    # DEFAULT FULLY_DEDUCTIBLE preserves backward-compatibility for projects
    # that have not been explicitly calibrated. It is NOT a global tax law.
    # Calibrated projects must receive the correct mode via their factory.
    #
    # Oborovo (C3B1-proved): FULLY_NON_DEDUCTIBLE
    #   C59=100%, D59=TRUE → zero SHL deduction for all periods.
    # TUHO: SUBJECT_TO_LIMITATIONS (source metadata only — thin-cap formula not
    #   yet proven; legacy runtime preserves SHL-fully-deductible behavior until
    #   the formula is explicitly activated — C3B3C_BLOCKED_TUHO_THIN_CAP_FORMULA).
    shl_interest_deductibility: ShlInterestDeductibilityMode = ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE

    # Fraction of SHL interest that is deductible (0.0–1.0).
    # Required when shl_interest_deductibility == CUSTOM_DEDUCTIBLE_PERCENTAGE.
    # Must be None or absent for FULLY_DEDUCTIBLE (pct=1.0) and FULLY_NON_DEDUCTIBLE (pct=0.0).
    shl_interest_deductible_pct: float | None = None

    # Whether the foreign-shareholder SHL interest cap (Oborovo D59=TRUE) applies.
    # Distinct from thin-cap. Provenance flag — must be consistent with shl_interest_deductibility.
    # When True, shl_interest_deductibility must be FULLY_NON_DEDUCTIBLE.
    # Oborovo: True. TUHO: False.
    foreign_shl_interest_cap_enabled: bool = False

    # Loss utilisation gate convention (C3B3C).
    # Controls when tax losses may be offset against taxable income.
    # Default TAXABLE_INCOME_POSITIVE is the canonical clean-engine mode.
    # EBT_POSITIVE matches workbook convention for Oborovo/TUHO but is NOT
    # supported in production execution unless explicitly implemented.
    # When EBT_POSITIVE is set, the engine raises NotImplementedError unless
    # the EBT gate execution path is proven and activated.
    tax_loss_utilisation_gate: TaxLossUtilisationGate = TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE

    # Tax periodisation mode (C3B3C).
    # CALENDAR_TAX_YEAR is the only supported production mode.
    # WORKBOOK_MODEL_YEAR_PAIRING must be UNSUPPORTED — fail closed.
    tax_periodisation_mode: TaxPeriodisationMode = TaxPeriodisationMode.CALENDAR_TAX_YEAR

    # SHL construction accounting and payment treatment (C3B3C).
    # Source-proved for Oborovo and TUHO: EXPENSE_TO_PNL + PIK_TO_SHL_BALANCE.
    # These are SEPARATE dimensions — PIK into liability ≠ capitalise into asset.
    shl_construction_accounting: ShlAccountingTreatment = ShlAccountingTreatment.EXPENSE_TO_PNL
    shl_construction_payment: ShlPaymentMethod = ShlPaymentMethod.PIK_TO_SHL_BALANCE

    cit_cash_tax_start_operating_index: int | None = None

    # Explicit tax-depreciation policy — governs how the waterfall derives the
    # depreciation deduction passed to compute_period_tax().
    #
    # COMPATIBILITY DEFAULT — NOT A GLOBAL COUNTRY TAX RULE:
    # The default BOOK_BASED_PERCENTAGE at 100% preserves legacy behaviour where
    # book dep and tax dep are numerically equal. This default does NOT mean that
    # all countries or all projects use 100% book-based tax depreciation. Future
    # projects must receive these assumptions through a selected versioned Tax
    # Policy plus project-level overrides (see docs/tax_policy_library_future_contract.md).
    # Oborovo explicitly sets BOOK_BASED_PERCENTAGE = 100% because the source
    # workbook calibration supports that project policy.
    tax_depreciation_mode: TaxDepreciationMode = TaxDepreciationMode.BOOK_BASED_PERCENTAGE
    # Fraction of book depreciation that is tax-deductible (1.0 = 100%).
    # COMPATIBILITY DEFAULT — NOT A GLOBAL COUNTRY TAX RULE.
    # Oborovo: source workbook P&L shows no depreciation add-back in Fiscal
    # Reintegration bridge → 100% of book dep is tax-deductible for this project.
    tax_deductible_book_dep_pct: float = 1.0

    # SOURCE-OWNERSHIP FLAG — explicit opt-in to book-depreciable-basis tax dep.
    # When True: the clean adapter uses book_depreciable_capex_items() (hard capex
    # + capitalised financial costs) as the tax depreciation asset list.
    # When False (default): uses tax_depreciable_capex_items() (hard capex only).
    # Must only be set True when source workbook evidence proves the book basis
    # applies to tax depreciation for this specific project. Set in factory data;
    # the financial engine must not inspect project identity to derive this value.
    # Oborovo: C3B1 fixture proves excel_tax_dep == excel_book_dep → True.
    # All other projects: retain legacy tax_depreciable_capex_items() path → False.
    tax_dep_basis_source_owned: bool = False

    # CLEAN ENGINE OPT-IN — explicit permission to use the currently supported
    # clean cash-tax timing convention (TAX_YEAR_LAST_PERIOD, lag=0).
    #
    # What is source-proven for Oborovo (C3B1 evidence):
    #   cash-tax payment lag relative to source CIT accrual = 0 periods.
    #
    # What is a CLEAN ENGINE CONVENTION (not source-proven):
    #   annual CIT is placed in the last period of the calendar year
    #   (TAX_YEAR_LAST_PERIOD). The workbook uses H2+H1 model-year pairing,
    #   which is a structurally different periodisation — the C3B3B
    #   WORKBOOK_PERIODISATION_MISMATCH directly measures this gap.
    #
    # These are SEPARATE facts. This flag gates only whether the project is
    # explicitly permitted to use the clean convention; it does NOT assert that
    # TAX_YEAR_LAST_PERIOD itself matches the workbook.
    #
    # When False (default): adapter raises NotImplementedError (fail-closed).
    # All projects without an explicit opt-in must not silently inherit this convention.
    clean_cash_tax_timing_enabled: bool = False

    def __post_init__(self) -> None:
        mode = self.shl_interest_deductibility
        pct = self.shl_interest_deductible_pct
        # ── numeric validation for shl_interest_deductible_pct ──────────────────
        if pct is not None:
            import math as _math
            if isinstance(pct, bool):
                raise ValueError("shl_interest_deductible_pct must be a float, not bool.")
            pct_f = float(pct)
            if _math.isnan(pct_f) or _math.isinf(pct_f):
                raise ValueError(f"shl_interest_deductible_pct must be finite, got {pct!r}")

        if mode == ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE:
            if pct is None:
                raise ValueError(
                    "shl_interest_deductible_pct is required when "
                    "shl_interest_deductibility == CUSTOM_DEDUCTIBLE_PERCENTAGE"
                )
            if not (0.0 <= pct <= 1.0):
                raise ValueError(
                    f"shl_interest_deductible_pct must be in [0, 1], got {pct}"
                )
        if mode == ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE and pct is not None:
            if abs(pct - 1.0) > 1e-9:
                raise ValueError(
                    f"shl_interest_deductible_pct must be absent or 1.0 for "
                    f"FULLY_DEDUCTIBLE, got {pct}"
                )
        if mode == ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE and pct is not None:
            if abs(pct) > 1e-9:
                raise ValueError(
                    f"shl_interest_deductible_pct must be absent or 0.0 for "
                    f"FULLY_NON_DEDUCTIBLE, got {pct}"
                )
        # ── SUBJECT_TO_LIMITATIONS requires a limitation mechanism ────────────
        if mode == ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS:
            if not self.thin_cap_enabled:
                raise ValueError(
                    "shl_interest_deductibility=SUBJECT_TO_LIMITATIONS requires at least "
                    "one explicit limitation mechanism (thin_cap_enabled=True)."
                )
        # ── foreign_shl_interest_cap_enabled consistency ──────────────────────
        if self.foreign_shl_interest_cap_enabled:
            if mode != ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE:
                raise ValueError(
                    "foreign_shl_interest_cap_enabled=True requires "
                    "shl_interest_deductibility=FULLY_NON_DEDUCTIBLE."
                )
        # ── WORKBOOK_MODEL_YEAR_PAIRING unconditionally blocked ───────────────
        if self.tax_periodisation_mode == TaxPeriodisationMode.WORKBOOK_MODEL_YEAR_PAIRING:
            raise ValueError(
                "WORKBOOK_MODEL_YEAR_PAIRING is unsupported in production. "
                "Only CALENDAR_TAX_YEAR is supported."
            )

    @property
    def shl_non_deductible_fraction(self) -> float:
        """Non-deductible fraction of gross SHL interest for this tax policy.

        Under the deductible-only method: only shl_deductible_fraction enters the
        ATAD pool; the non-deductible fraction is simply never deducted (no addback).
        This property is used only for audit reporting or rate-based analysis.

        Returns 0.0 for FULLY_DEDUCTIBLE (full gross amount is deductible).
        Returns 1.0 for FULLY_NON_DEDUCTIBLE (zero gross amount is deductible).
        Returns (1 - pct) for CUSTOM_DEDUCTIBLE_PERCENTAGE.
        Raises NotImplementedError for SUBJECT_TO_LIMITATIONS (limitation engine required).
        """
        mode = self.shl_interest_deductibility
        if mode == ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE:
            return 0.0
        if mode == ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE:
            return 1.0
        if mode == ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE:
            pct = self.shl_interest_deductible_pct
            return 1.0 - (pct if pct is not None else 0.0)
        raise NotImplementedError(
            "shl_non_deductible_fraction is not defined for SUBJECT_TO_LIMITATIONS; "
            "use the interest limitation engine to derive the addback."
        )

    @property
    def initial_tax_loss_keur(self) -> float:
        """Initial tax loss carryforward available at commercial operation."""
        if self.construction_pl is not None:
            return self.construction_pl.initial_tax_loss_keur
        return self.prior_tax_loss_keur

@dataclass(frozen=True)
class ProjectInputs:
    """Root immutable project input object."""
    info: ProjectInfo
    technical: TechnicalParams
    capex: CapexStructure
    opex: tuple[OpexItem, ...]
    revenue: RevenueParams
    financing: FinancingParams
    tax: TaxParams
    # Capability field: when set, opex_schedule_period() routes through the
    # generic hierarchical engine instead of the legacy flat-item path.
    # Presence (non-None) is the sole dispatch signal — never check project name.
    hierarchical_opex_capability: "HierarchicalOpexCapability | None" = None


def hash_inputs_for_cache(inputs: "ProjectInputs") -> tuple:
    """Build a deterministic cache key from stable input fields."""
    return (
        inputs.info.financial_close,
        inputs.technical.capacity_mw,
        inputs.technical.yield_scenario,
        inputs.technical.operating_hours_p50,
        inputs.technical.operating_hours_p90_10y,
        inputs.technical.operating_hours_p99_1y,
        inputs.technical.pv_degradation,
        inputs.technical.bess_degradation,
        inputs.financing.gearing_ratio,
        inputs.financing.all_in_rate,
        inputs.financing.senior_tenor_years,
        inputs.financing.target_dscr,
        inputs.financing.lockup_dscr,
        inputs.financing.dsra_months,
        inputs.financing.shl_amount_keur,
        inputs.financing.shl_rate,
        inputs.financing.commitment_fee,
        inputs.financing.arrangement_fee,
        inputs.financing.structuring_fee,
        inputs.revenue.ppa_base_tariff,
        inputs.revenue.ppa_term_years,
        inputs.revenue.ppa_index,
        inputs.revenue.ppa_production_share,
        inputs.revenue.market_prices_curve,
        inputs.revenue.market_inflation,
        inputs.revenue.balancing_cost_pv,
        inputs.capex.epc_contract.amount_keur,
        inputs.capex.production_units.amount_keur,
        inputs.capex.contingencies.amount_keur,
        tuple((o.y1_amount_keur, o.annual_inflation) for o in inputs.opex),
        inputs.capex.total_capex,
        inputs.capex.idc_keur,
        inputs.capex.bank_fees_keur,
        inputs.capex.commitment_fees_keur,
        inputs.tax.corporate_rate,
        inputs.tax.loss_carryforward_years,
        inputs.tax.atad_ebitda_limit,
        # Hierarchical OPEX capability — if present, include full model structure in cache key.
        # Sorted by category code, then subitem code within each category, for determinism.
        # Does NOT include senior_tenor_years — that lives in FinancingParams above.
        (
            tuple(
                (
                    cat.code,
                    cat.calculation_type.value,
                    cat.inflation_rate,
                    cat.escalation_convention.value,
                    cat.percentage_rate,
                    tuple(sorted(cat.percentage_base_codes)),
                    tuple(
                        (
                            si.code,
                            si.amount_basis.value,
                            si.base_amount_keur,
                            si.activation_mode.value,
                            (
                                tuple(si.activation_schedule.annual_flags)
                                if si.activation_schedule is not None else None
                            ),
                            (
                                tuple(
                                    (yr, half, flag)
                                    for (yr, half), flag in si.activation_schedule.period_overrides
                                )
                                if si.activation_schedule is not None
                                   and si.activation_schedule.period_overrides
                                else None
                            ),
                        )
                        for si in sorted(cat.subitems, key=lambda s: s.code)
                    ),
                )
                for cat in sorted(
                    inputs.hierarchical_opex_capability.opex_model.categories,
                    key=lambda c: c.code,
                )
            ) if inputs.hierarchical_opex_capability is not None else None
        ),
        (
            tuple(
                (code, tuple(vals))
                for code, vals in sorted(
                    inputs.hierarchical_opex_capability.external_annual_series,
                    key=lambda kv: kv[0],
                )
            )
            if inputs.hierarchical_opex_capability is not None else None
        ),
    )
