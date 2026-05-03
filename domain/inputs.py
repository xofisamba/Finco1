"""Project finance input models - immutable dataclasses matching Excel structure.

All classes use @dataclass(frozen=True) for immutability.
Each field documents the corresponding Excel cell reference.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class PeriodFrequency(Enum):
    """Period frequency matching Excel Inputs!D18."""
    SEMESTRIAL = "Semestrial"
    ANNUAL = "Annual"
    QUARTERLY = "Quarterly"


class EquityIRRMethod(Enum):
    EQUITY_ONLY = "equity_only"
    COMBINED = "combined"
    SHL_PLUS_DIVIDENDS = "shl_plus_dividends"


class DebtSizingMethod(Enum):
    DSCR_SCULPT = "dscr_sculpt"
    GEARING_CAP = "gearing_cap"
    FIXED = "fixed"


class SHLRepaymentMethod(Enum):
    BULLET = "bullet"
    CASH_SWEEP = "cash_sweep"
    PIK = "pik"
    ACCRUED = "accrued"
    PIK_THEN_SWEEP = "pik_then_sweep"


class YieldScenario(Enum):
    """Yield scenario selection matching Excel Inputs!D52."""
    P50 = "P_50"
    P90_10Y = "P90-10y"
    P99_1Y = "P99-1y"


class AssetClass(Enum):
    """Asset class for depreciation — determines useful life.

    Industry standard useful lives:
    - Solar panels: 25 years
    - Wind turbines: 25 years
    - BESS cells: 10 years
    - BESS power electronics: 15 years
    - Civil/grid: 30 years
    - Soft costs: 5 years
    - Financial costs: amortized over senior debt tenor
    """
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
    AssetClass.FINANCIAL_COSTS: 14,  # default: senior tenor
}


@dataclass(frozen=True)
class ProjectInfo:
    """Basic project metadata. Corresponds to Excel Inputs sheet rows 2-18."""
    name: str                       # Inputs!D2 - Project name
    company: str                   # Inputs!D3 - Company name
    code: str                      # Inputs!D4 - Project code
    country_iso: str                # Inputs!D5 - Country code (e.g., "HR")
    financial_close: date           # Inputs!D9 - Financial close date
    construction_months: int       # Inputs!D10 - Construction duration in months
    cod_date: date                  # Inputs!D11 - Commercial operation date
    horizon_years: int             # Inputs!D14 - Investment horizon in years
    period_frequency: PeriodFrequency  # Inputs!D18 - "Semestrial", "Annual", etc.


@dataclass(frozen=True)
class CapexItem:
    """Single CAPEX line item with spending profile.

    Corresponds to Excel Inputs rows 23-44.
    Each item has an amount and spending profile across periods.

    Example:
        EPC Contract: 26,430 k€ → Y0:0%, Y1:8.3%, Y2:8.3% ... (12 month linear)
        Project Rights: 3,024.5 k€ → Y0:100%, rest: 0%
    """
    name: str                      # Item description
    amount_keur: float             # Total amount in kEUR
    y0_share: float = 0.0          # % paid in Y0 (construction year 0)
    spending_profile: tuple[float, ...] = ()  # Shares for Y1, Y2, Y3, Y4
    asset_class: AssetClass = AssetClass.CIVIL_GRID  # For depreciation useful life
    useful_life_override: Optional[int] = None  # Override default useful life

    @property
    def total_spending_shares(self) -> float:
        """Sum of all spending shares (y0 + profile). Should equal 1.0."""
        return self.y0_share + sum(self.spending_profile)

    def __post_init__(self):
        """Validate spending shares sum to approximately 1.0."""
        total = self.total_spending_shares
        if total > 0 and abs(total - 1.0) > 0.001:
            raise ValueError(
                f'{self.name}: spending shares sum to {total:.4f}, expected 1.0. '
                f'Check spending_profile or y0_share values.'
            )

    def amount_in_period(self, period: int) -> float:
        """Return CAPEX amount for a given period.

        Args:
            period: 0=Y0, 1=Y1, 2=Y2, 3=Y3, 4=Y4+

        Returns:
            Amount in kEUR for that period
        """
        if period == 0:
            return self.amount_keur * self.y0_share
        idx = period - 1
        if idx < len(self.spending_profile):
            return self.amount_keur * self.spending_profile[idx]
        return 0.0


@dataclass(frozen=True)
class CapexStructure:
    """Complete CAPEX structure with 22 items from Oborovo Excel.

    Corresponds to Excel Inputs rows 23-44 (22 CAPEX categories).

    Items marked as "dynamic" are computed iteratively:
    - IDC: Solved via fixed-point iteration (circular with debt)
    - Commitment Fees: Based on undrawn debt during construction
    - Reserve Accounts: DSRA, J-DSRA, MRA funded at financial close
    """
    # === Hard CAPEX items ===
    epc_contract: CapexItem        # Inputs!C23 - EPC Contract (26,430 k€)
    production_units: CapexItem    # Inputs!C24 - Production Units (10,912.7 k€)
    epc_other: CapexItem           # Inputs!C25 - Other EPC (3,200 k€)
    grid_connection: CapexItem     # Inputs!C26 - Grid Connection (1,800 k€)
    ops_prep: CapexItem            # Inputs!C27 - Operations Preparation (500 k€)
    insurances: CapexItem          # Inputs!C28 - Insurances (400 k€)
    lease_tax: CapexItem           # Inputs!C29 - Lease & Property Tax (200 k€)
    construction_mgmt_a: CapexItem  # Inputs!C30 - Construction Management A
    commissioning: CapexItem       # Inputs!C31 - Commissioning (300 k€)
    audit_legal: CapexItem         # Inputs!C32 - Audit & Legal (200 k€)
    construction_mgmt_b: CapexItem  # Inputs!C33 - Construction Management B
    contingencies: CapexItem       # Inputs!C34 - Contingencies (1,986.4 k€)
    taxes: CapexItem               # Inputs!C35 - Taxes & Duties (150 k€)
    project_acquisition: CapexItem  # Inputs!C36 - Project Acquisition (1,000 k€)
    project_rights: CapexItem      # Inputs!C37 - Project Rights (3,024.5 k€)
    # === Dynamic items (computed, not direct input) ===
    idc_keur: float = 0.0          # Interest During Construction (computed)
    commitment_fees_keur: float = 0.0  # Commitment fees on undrawn debt
    bank_fees_keur: float = 0.0   # Bank fees (upfront)
    other_financial_keur: float = 0.0  # Other financial costs
    vat_costs_keur: float = 0.0    # VAT costs spread over Y0-Y3
    reserve_accounts_keur: float = 0.0  # Initial reserve account funding

    # === Explicit CapexItem accessor ===
    _CAPEX_ITEM_FIELDS = (
        "epc_contract", "production_units", "epc_other", "grid_connection",
        "ops_prep", "insurances", "lease_tax", "construction_mgmt_a",
        "commissioning", "audit_legal", "construction_mgmt_b", "contingencies",
        "taxes", "project_acquisition", "project_rights",
    )

    def capex_items(self) -> tuple[CapexItem, ...]:
        """Return all CapexItem entries that have non-zero amounts.

        Excludes scalar float fields (idc_keur, bank_fees_keur, etc.).
        """
        return tuple(
            getattr(self, field) for field in self._CAPEX_ITEM_FIELDS
            if getattr(self, field).amount_keur != 0
        )

    @property
    def hard_capex_keur(self) -> float:
        """Sum of all hard CAPEX items (excluding dynamic items)."""
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
        """Alias for hard_capex_keur for backward compatibility."""
        return self.hard_capex_keur

    @property
    def sculpt_capex_keur(self) -> float:
        """CAPEX used for debt sizing / gearing cap computation.

        Excludes reserve accounts (DSRA, MRA, J-DSRA) which are funded separately
        and not part of the project's capital cost for debt sizing purposes.
        Corresponds to Excel 'Total CAPEX' for sculpting: hard_capex + idc + bank_fees + vat_costs.
        """
        return (self.hard_capex_keur + self.idc_keur +
                self.bank_fees_keur + self.other_financial_keur + self.vat_costs_keur)

    @property
    def total_capex_before_idc(self) -> float:
        """Total CAPEX excluding IDC."""
        return self.hard_capex_keur + self.commitment_fees_keur + \
               self.bank_fees_keur + self.other_financial_keur + \
               self.vat_costs_keur + self.reserve_accounts_keur

    @property
    def total_capex(self) -> float:
        """Total CAPEX including IDC."""
        return self.total_capex_before_idc + self.idc_keur


@dataclass(frozen=True)
class OpexItem:
    """Single OPEX line item with individual escalation.

    Corresponds to Excel Inputs rows 146-161 (15 OPEX categories).
    Each item has Y1 amount and annual escalation rate.

    Example:
        Technical Management: 198 k€ Y1, 2% annual index
        Power Expenses: 126.86 k€ Y1, 0% index (flat)
    """
    name: str                      # Item description
    y1_amount_keur: float         # Amount in kEUR for Year 1
    annual_inflation: float = 0.02  # Annual escalation rate (0.02 = 2%)
    step_changes: tuple[tuple[int, float], ...] = field(default_factory=lambda: ())
    # e.g. ((3, 185.64),) means Y3 OPEX is hardcoded to 185.64 k€

    def amount_at_year(self, year: int) -> float:
        """Return OPEX amount for a given year with escalation.

        Args:
            year: 1-based year index (1=Y1, 2=Y2, etc.)

        Returns:
            Amount in kEUR for that year
        """
        # Check for step change
        for step_year, amount in self.step_changes:
            if year == step_year:
                return amount
        # Apply escalation from Y1
        result = self.y1_amount_keur * (1 + self.annual_inflation) ** (year - 1)
        return max(0.0, result)  # Guard against negative OPEX from negative inflation


@dataclass(frozen=True)
class TechnicalParams:
    """Technical parameters for the project.

    Corresponds to Excel Inputs rows 51-68.
    """
    capacity_mw: float             # Inputs!D51 - Installed capacity (75.26 MW)
    yield_scenario: str            # Inputs!D52 - "P_50", "P90-10y", etc.
    operating_hours_p50: float = 0.0    # Inputs!D64 - P50 yield hours (1,494)
    operating_hours_p90_1y: float | None = None  # P90-1y hours (single year exceedance)
    operating_hours_p90_10y: float = 0.0  # Inputs!D68 - P90-10y hours (1,410)
    operating_hours_p99_1y: float | None = None  # P99-1y hours (scenario engine)
    pv_degradation: float = 0.004  # Inputs!D56 - Annual degradation (0.4%)
    bess_degradation: float = 0.003  # Inputs!D57 - BESS degradation (0.3%)
    plant_availability: float = 0.99  # Inputs!D58 - Plant availability (99%)
    grid_availability: float = 0.99   # Inputs!D59 - Grid availability (99%)
    bess_enabled: bool = False     # Inputs!D140 - BESS enabled flag

    @property
    def combined_availability(self) -> float:
        """Combined plant × grid availability (98% for Oborovo)."""
        return self.plant_availability * self.grid_availability


@dataclass(frozen=True)
class RevenueParams:
    """Revenue parameters including PPA and market pricing.

    Corresponds to Excel Inputs rows 78-141.
    """
    ppa_base_tariff: float         # Inputs!D78 - Base PPA tariff (57 €/MWh)
    ppa_term_years: float       # Inputs!D81 - PPA term in years (supports 12.5 for mid-year expiry)
    ppa_index: float = 0.02        # Inputs!D83 - PPA annual index (2%)
    ppa_production_share: float = 1.0  # Inputs!D80 - Share of production in PPA
    market_scenario: str = "Central"  # Inputs!B103 - Market scenario name
    market_prices_curve: tuple[float, ...] = ()  # Inputs row 107 - Market price curve
    market_inflation: float = 0.02  # Inputs!B129 - Market price inflation (2%)
    balancing_cost_pv: float = 0.025  # Inputs!D114 - Balancing cost % (2.5%)
    balancing_cost_bess: float = 0.025  # Inputs!D115 - BESS balancing cost
    balancing_cost_wind_eur_mwh: float = 0.0  # Wind balancing cost (EUR/MWh), e.g. 8.0 for TUHO
    co2_enabled: bool = False      # Inputs!D139 - CO2 certificates enabled
    co2_price_eur: float = 1.5     # Inputs!E141 - CO2 price (1.5 €/ton)

    def tariff_at_year(self, year: int) -> float:
        """Return PPA tariff in year with escalation.

        Args:
            year: 1-based year index (1=Y1, 2=Y2, etc.)

        Returns:
            Tariff in €/MWh
        """
        return self.ppa_base_tariff * (1 + self.ppa_index) ** (year - 1)

    def market_price_at_year(self, year: int) -> float:
        """Return market price in year.

        Args:
            year: 1-based year index

        Returns:
            Market price in €/MWh
        """
        idx = year - 1
        if idx < len(self.market_prices_curve):
            return self.market_prices_curve[idx]
        # Extrapolate with market inflation
        if self.market_prices_curve:
            base = self.market_prices_curve[-1]
            return base * (1 + self.market_inflation) ** (idx - len(self.market_prices_curve) + 1)
        return self.ppa_base_tariff  # Fallback


@dataclass(frozen=True)
class FinancingParams:
    """Financing parameters including debt and equity structure.

    Corresponds to Excel Inputs rows 168-349.
    """
    # Equity structure
    share_capital_keur: float = 500.0   # Inputs!D312 - Share capital (500 k€)
    share_premium_keur: float = 0.0     # Inputs!D313 - Share premium
    shl_amount_keur: float = 13547.2     # Inputs!D325 - Shareholder loan (13,547.2 k€)
    shl_rate: float = 0.08              # Inputs!F328 - SHL interest rate (8%)

    # Debt structure
    gearing_ratio: float = 0.7524       # Inputs!D168 - Gearing ratio (75.24%)
    senior_debt_amount_keur: float = 0.0  # Inputs!D192 - Senior debt (computed)
    senior_tenor_years: int = 14        # Inputs!D196 - Senior debt tenor (14 years)
    base_rate: float = 0.03             # Inputs!D202 - Base rate (3%)
    margin_bps: int = 265               # Inputs!D203 - Margin in basis points (265)
    floating_share: float = 0.2         # Inputs!B39 - Floating rate share (20%)
    fixed_share: float = 0.8            # Inputs!B40 - Fixed rate share (80%)
    hedge_coverage: float = 0.8         # Inputs!D230 - Hedge coverage (80%)

    # Fees
    commitment_fee: float = 0.0105      # Inputs!D214 - Commitment fee (1.05%)
    arrangement_fee: float = 0.0        # Inputs!D218 - Arrangement fee
    structuring_fee: float = 0.01       # Inputs!D217 - Structuring fee (1%)

    # Covenants
    target_dscr: float = 1.15           # Inputs!D221 - Target DSCR (1.15x)
    lockup_dscr: float = 1.10           # Inputs!D223 - Lockup DSCR threshold (1.10x)
    min_llcr: float = 1.15             # Inputs!D224 - Minimum LLCR (1.15x)

    # Amortization type: "sculpted" (DSCR-based, OBOROVO) or "fixed_ds" (fixed debt service, TUHO)
    amortization_type: str = "sculpted"  # "sculpted" | "fixed_ds"
    fixed_ds_keur: float = 0.0           # Fixed debt service per period (kEUR) — for fixed_ds type

    # Reserve accounts
    dsra_months: int = 6               # Inputs!D348 - DSRA funding months (6)

    # Equity IRR calculation method:
    # "equity_only" → IRR base = capex - debt - SHL (TUHO style)
    # "combined" → IRR base = share_capital + SHL, cash flows include SHL interest + principal (Oborovo style)
    equity_irr_method: str = "equity_only"

    # Debt sizing method:
    # "dscr_sculpt" → debt = min(DSCR-constrained, gearing_cap) — default
    # "gearing_cap" → debt = max(DSCR-constrained, gearing_cap) — gearing wins (Oborovo style)
    # "fixed" → debt = fixed_debt_keur (override)
    debt_sizing_method: str = "dscr_sculpt"
    fixed_debt_keur: float | None = None  # Override sculpted debt with fixed amount
    # Per-period DSCR targets for dual-DSCR sculpting (PPA vs merchant)
    # e.g., [1.20] * 24 + [1.45] * 40 for TUHO: 24 PPA periods at 1.20x, then merchant at 1.45x
    dscr_schedule: list[float] | None = None

    # SHL repayment method:
    # "bullet" — sav principal na kraju tenora, kamate cash
    # "cash_sweep" — principal iz FCF nakon senior DS (po prioritetu)
    # "pik" — kamate i principal se kapitaliziraju uvijek
    # "accrued" — ništa se ne plaća, sve do exit/refinanciranja
    # "pik_then_sweep" — PIK dok nema FCF, sweep kad ima (TUHO)
    shl_repayment_method: str = "bullet"
    shl_pik_switch_period: int = 0  # 0 = auto (kad senior_balance = 0)
    shl_tenor_years: int = 0  # 0 = bullet at end of senior tenor; >0 = bullet in specific year
    shl_idc_keur: float = 0.0  # SHL IDC — added to opening balance

    @property
    def all_in_rate(self) -> float:
        """All-in interest rate (base + margin)."""
        return self.base_rate + self.margin_bps / 10000

    @property
    def total_equity_shl_keur(self) -> float:
        """Total equity + shareholder loan."""
        return self.share_capital_keur + self.share_premium_keur + self.shl_amount_keur + self.shl_idc_keur


@dataclass(frozen=True)
class TaxParams:
    """Tax parameters including corporate tax and loss carryforward.

    Corresponds to Excel Inputs rows 403-426.
    """
    corporate_rate: float = 0.10       # Inputs!D403 - Corporate tax rate (10%)
    loss_carryforward_years: int = 5   # Inputs!D407 - Loss carryforward years (5)
    loss_carryforward_cap: float = 1.0  # Inputs!D408 - Cap as % of profit (100%)
    prior_tax_loss_keur: float = 0.0   # Deprecated: use construction_pl instead
    legal_reserve_cap: float = 0.10    # Inputs!D410 - Legal reserve cap (% of capital)

    # Construction P&L — deterministically computed tax loss
    construction_pl: Optional["ConstructionPLStatement"] = None

    # Thin cap / ATAD
    thin_cap_enabled: bool = False     # Inputs!D414 - Thin cap enabled
    thin_cap_de_ratio: float = 0.8     # Inputs!D415 - DE/equity ratio threshold
    atad_ebitda_limit: float = 0.30    # ATAD EBITDA interest limit (30%)
    atad_min_interest_keur: float = 3000.0  # ATAD minimum interest threshold

    # Withholding taxes
    wht_sponsor_dividends: float = 0.05  # Inputs!D426 - WHT on dividends (5%)
    wht_sponsor_shl_interest: float = 0.0  # Inputs!D423 - WHT on SHL interest (0%)

    # SHL interest cap (for foreign sovereign)
    shl_cap_applies: bool = True       # Inputs!D412 - SHL interest cap applies

    @property
    def initial_tax_loss_keur(self) -> float:
        """Initial tax loss carryforward from construction period.

        Uses construction_pl if set (deterministic), otherwise falls back
        to prior_tax_loss_keur (for backward compatibility).
        """
        if self.construction_pl is not None:
            return self.construction_pl.initial_tax_loss_keur
        return self.prior_tax_loss_keur

    @classmethod
    def from_generic_config(cls, cfg: "GenericTaxConfig") -> "TaxParams":
        """Create TaxParams from a GenericTaxConfig.

        Provides backward compatibility: GenericTaxConfig fields map to TaxParams.
        """
        # Import here to avoid circular import
        from core.tax.generic_tax import GenericTaxConfig

        if not isinstance(cfg, GenericTaxConfig):
            raise TypeError(f"Expected GenericTaxConfig, got {type(cfg).__name__}")

        return cls(
            corporate_rate=cfg.cit_rate,
            loss_carryforward_years=cfg.loss_carryforward_years,
            loss_carryforward_cap=cfg.loss_carryforward_cap_pct,
            legal_reserve_cap=0.10,  # Default legal reserve
            thin_cap_enabled=cfg.interest_cap_enabled,
            thin_cap_de_ratio=0.80,  # Default DE ratio
            atad_ebitda_limit=cfg.interest_cap_ebitda_ratio,
            atad_min_interest_keur=cfg.interest_cap_min_keur,
            wht_sponsor_dividends=cfg.wht_dividends,
            wht_sponsor_shl_interest=cfg.wht_interest_shl,
            shl_cap_applies=True,
        )


@dataclass(frozen=True)
class ProjectInputs:
    """Complete project inputs combining all parameter classes.

    This is the root input structure for the entire model.
    All values are frozen after construction (immutable).
    """
    info: ProjectInfo
    technical: TechnicalParams
    capex: CapexStructure
    opex: tuple[OpexItem, ...]  # 15 OPEX items
    revenue: RevenueParams
    financing: FinancingParams
    tax: TaxParams

# =============================================================================
# Hash function for cache key generation (used by app/cache.py)

    # -------------------------------------------------------------------------
    # Compatibility shims — project factories moved to app/project_factories.py
    # These exist only for backward compatibility with existing tests/examples.
    # Do not add new project-specific logic here.
    # -------------------------------------------------------------------------
    @classmethod
    def create_default_oborovo(cls) -> "ProjectInputs":
        """Deprecated: use app.project_factories.create_default_oborovo() directly."""
        import warnings
        warnings.warn("ProjectInputs.create_default_oborovo is deprecated; "
                      "use app.project_factories.create_default_oborovo()",
                      DeprecationWarning, stacklevel=2)
        from app.project_factories import create_default_oborovo as factory
        return factory()

    @classmethod
    def create_default_tuho_wind1(cls) -> "ProjectInputs":
        """Deprecated: use app.project_factories.create_default_tuho_wind1() directly."""
        import warnings
        warnings.warn("ProjectInputs.create_default_tuho_wind1 is deprecated; "
                      "use app.project_factories.create_default_tuho_wind1()",
                      DeprecationWarning, stacklevel=2)
        from app.project_factories import create_default_tuho_wind1 as factory
        return factory()


def hash_inputs_for_cache(inputs: "ProjectInputs") -> tuple:
    """Deterministic hash for frozen ProjectInputs (cache key).

    Args:
        inputs: ProjectInputs instance (must be frozen)

    Returns:
        Tuple of values for hashing
    """
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
    )
