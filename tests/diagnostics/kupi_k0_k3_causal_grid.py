"""
KUPI K0-K3 Causal Grid — Post-Fix3 diagnostic.

DIAGNOSTIC ONLY. Not production logic. All results are engine-derived.
No source Senior or SHL injected as production inputs.

Project: KUPI Wind (144 MW, Bosnia & Herzegovina)
  FC:              2028-06-30
  Construction:    24 months (4 semiannual periods)
  COD:             2030-06-30
  Operating life:  30 years, semiannual
  P50:             3,535 h/y (509.04 GWh)
  P90-10y:         3,058 h/y (440.352 GWh)
  PPA:             63 EUR/MWh, 12 years, 2% indexation, 100% offtake
  Balancing:       5 EUR/MWh (P0); D0 bank-sizing omits balancing
  SHL rate:        8%, ALL_AT_FC + COMPOUND_PERIODIC (source-evidenced)

Source quality register (pre-classification, not runtime targets):
  Workbook: 20260422_KUPI_BP_NEW.xlsm
  SHA-256:  111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954
  Total Uses (Inputs!G154):     215,803.437976869 kEUR  [authority]
  Final Senior (DS!D44):        147,150.442310339 kEUR  [comparison anchor]
  Source SHL principal:          68,152.995666529 kEUR  [comparison anchor]
  Source PIK (compound):         11,340.658478910 kEUR  [comparison anchor]

# P0_KUPI_CURRENT_CLEAN_POST_FIX3
# Source-exact KUPI economics + current clean Finco policy
# ALL_AT_FC + COMPOUND_PERIODIC (source-evidenced for KUPI)
# balancing = 5 EUR/MWh (P0 includes it; D0 diagnostic omits it from Bank sizing)

Factorial design:
  P0 — CURRENT_CLEAN_POST_FIX3:
       source-exact economics, balancing=5, source tax, ALL_AT_FC + COMPOUND_PERIODIC
  D0 — KUPI_SOURCE_BANK_BALANCING_OMISSION_DIAGNOSTIC:
       balancing=0 for bank sizing, source tax, ALL_AT_FC + COMPOUND_PERIODIC
  K0 — control: D0 revenue + CLEAN Finco tax + PRO_RATA + SIMPLE
  K1 — tax effect: D0 revenue + SOURCE WORKBOOK TAX FORMULAS + PRO_RATA + SIMPLE
  K2 — SHL effect: D0 revenue + CLEAN Finco tax + ALL_AT_FC + COMPOUND_PERIODIC
  K3 — combined: D0 revenue + SOURCE WORKBOOK TAX FORMULAS + ALL_AT_FC + COMPOUND_PERIODIC

Causal decompositions (Senior):
  TAX_MAIN_EFFECT    = Senior(K1) - Senior(K0)
  SHL_MAIN_EFFECT    = Senior(K2) - Senior(K0)
  COMBINED_EFFECT    = Senior(K3) - Senior(K0)
  INTERACTION_EFFECT = Senior(K3) - Senior(K1) - Senior(K2) + Senior(K0)
  K3_RESIDUAL        = 147,150.442 - Senior(K3)   [source anchor comparison only]
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import NamedTuple

from domain.inputs import (
    AssetClass,
    CapexItem,
    CapexStructure,
    EquityIRRMethod,
    FinancingParams,
    OpexItem,
    PeriodFrequency,
    ProjectInfo,
    ProjectInputs,
    RevenueParams,
    TaxParams,
    TechnicalParams,
    DebtSizingMethod,
)
from finco_core.inputs._models import (
    DebtSizingCaseConfig,
    DebtSizingMode,
    DebtServiceReserveSupportMode,
    GearingBasisMode,
    ShlConstructionInterestMethod,
    SponsorFundingMode,
    SponsorFundingTimingPolicy,
    ShlInterestDeductibilityMode,
    TaxLossUtilisationGate,
    YieldScenario,
)
from finco_core.inputs.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)
from finco_core.inputs.senior_sculpting import SeniorSculptingConfig
from financial_engine.financing import run_project_financing_model
from financial_engine.financing.contracts import ProjectFinancingResult


# ---------------------------------------------------------------------------
# SOURCE ANCHOR CONSTANTS — comparison only, NEVER injected as production inputs
# ---------------------------------------------------------------------------
SOURCE_SENIOR_KEUR = 147_150.442           # DS!D44 / Inputs!D178 comparison anchor
SOURCE_SHL_PRINCIPAL_KEUR = 68_152.996     # comparison anchor — NOT a runtime input
SOURCE_PIK_KEUR = 11_340.658               # compound PIK comparison anchor
SOURCE_OPENING_SHL_KEUR = 79_493.654       # comparison anchor
SOURCE_TOTAL_USES_KEUR = 215_803.438       # Inputs!G154 authority

# BA corporate tax rate (statutory)
BA_CORPORATE_RATE = 0.10

# ─── Source-authority design assumptions (inputs, not fitted outputs) ─────────

_KUPI_TOTAL_HARD_CAPEX_KEUR: float = 205_932.22        # CapEx!C99
_KUPI_SENIOR_IDC_KEUR: float = 7_152.520038600         # IDC source-close
_KUPI_COMMITMENT_FEE_KEUR: float = 782.925875313       # commitment fee source-close
_KUPI_BANK_STRUCTURING_KEUR: float = 1_549.590939566   # structuring fee
_KUPI_VAT_FINANCING_KEUR: float = 386.181123400        # VAT facility financing
_KUPI_TOTAL_USES_KEUR: float = 215_803.437976869       # Inputs!G154 authority

_KUPI_SHARE_CAPITAL_KEUR: float = 500.0                # Inputs!D295
_KUPI_MAX_GEARING: float = 0.80                        # Inputs!D208 (NOT 68.18%)
_KUPI_SENIOR_TENOR_YEARS: int = 14
_KUPI_ALL_IN_RATE: float = 0.061                       # 3.10% + 280bps + 20bps swap
_KUPI_SHL_RATE: float = 0.08                           # Inputs!F311

# Period axis for 30yr semestrial:
_KUPI_SHL_MATURITY_PERIOD_IDX: int = 61   # last operating period
_KUPI_SHL_ELIGIBILITY_START: int = 2      # first operating period

# ─── DSCR target schedule — exact source DS!row19 values ─────────────────────
# Source DS!row19: 24 periods at 1.50 (PPA), then 4 merchant-period results.
# Exact values extracted from DS!AF:AI:
#   AF: 1.757649388048956, AG: 1.757649388048956
#   AH: 1.7578495048083824, AI: 1.7578495048083824
# KUPI_DSCR_REVENUE_MIX_FORMULA_GAP: engine cannot derive dynamically.
# Explicit schedule supplied here matching source DS!row19 exactly.
_KUPI_DSCR_SCHEDULE: tuple[float, ...] = (
    1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50,   # periods 2..9   (PPA yrs 1..4)
    1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50,   # periods 10..17 (PPA yrs 5..8)
    1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50,   # periods 18..25 (PPA yrs 9..12)
    1.757649388048956, 1.757649388048956,               # periods 26..27 (merchant yr 1)
    1.7578495048083824, 1.7578495048083824,             # periods 28..29 (merchant yr 2)
)  # 28 periods = 14yr × 2

# ─── Merchant price curves — exact source Inputs!E106:AI106 / E109:AI109 ─────
# Central prices (Base case, P50 basis):
_KUPI_CENTRAL_PRICES: tuple[float, ...] = (
    99.572,    102.265,   107.985,   111.618,   110.789,   110.776,   114.824,
    114.554,   109.134,   107.448,   107.602,   113.847,   114.520,   114.972,
    115.340,   114.996,   115.213,   115.962,   117.552,   118.174,   118.736,
    119.238,   122.265,   124.584,   126.909,   129.958,   133.015,   134.984,
    137.856,   140.532,   132.645,
)  # Inputs!E106:AI106, years 2030-2060

# MidLow prices (Bank case, P90 basis):
_KUPI_MIDLOW_PRICES: tuple[float, ...] = (
    79.233,    81.360,    84.928,    87.224,    89.309,    91.805,    95.914,
    97.663,    95.718,    96.228,    95.542,    97.955,    98.210,    98.384,
    98.404,    97.828,    97.697,    98.637,   100.172,   101.028,   101.762,
    102.538,  104.738,   106.401,   107.970,   110.229,   112.388,   113.834,
    115.968,  117.992,   111.093,
)  # row109 × row111, years 2030-2060

# ─── O&M exact step schedule — Scenarios!E79:E108 ────────────────────────────
# Y1-Y2: 1320, Y3-Y4: 1488, Y5-Y9: 1752, Y10-Y14: 1824, Y15-Y19: 2040,
# Y20-Y22: 2328, Y23-Y30: 2616.
_OM_STEP_CHANGES: tuple[tuple[int, float], ...] = (
    (3, 1488.0),
    (5, 1752.0),
    (10, 1824.0),
    (15, 2040.0),
    (20, 2328.0),
    (23, 2616.0),
)

# ─── Construction period Uses for PRO_RATA control (K0/K1) ────────────────────
# Source-timing approximation (BLOCKER 4 fix; BLOCKER 4 Note below).
#
# Source CAPEX timing evidence (from workbook category descriptions):
#   Upfront items (disbursed at FC = construction period 1, y0_share=1.0):
#     Operation Investments:   1,050.000
#     Insurances:              1,500.000  (purchased at build start)
#     Land Securing:             800.000  (upfront)
#     Bank DD + Lender Mon.:     460.000  (upfront)
#     Construction Mgmt B:     4,629.750  (upfront per workbook)
#     Project Rights:         23,281.650  (typically front-loaded)
#     Subtotal upfront:       31,721.400 kEUR
#
#   Spread items (50/50 over 24-month build, y0_share=0.0):
#     Production Units:      144,000.000
#     EPC Contract:           20,010.000
#     Grid Connection:            30.000
#     Monitoring & Telecom:      100.000
#     Audit/Accounting/Legal:     42.000
#     Contingencies:          10,028.820
#     Subtotal spread:       174,210.820 → each period 87,105.410 kEUR
#
#   Capitalised financing costs (total: 9,871.217976869 kEUR):
#     Bank Structuring fee:    1,549.590939566 (at FC = period 1)
#     VAT facility financing:    386.181123400 (front-loaded, period 1)
#     Commitment fee (50/50):    782.925875313 → each 391.462937657 kEUR
#     Senior IDC (50/50):      7,152.520038600 → each 3,576.260019300 kEUR
#     Period 1 finance:        5,903.495019923 kEUR
#     Period 2 finance:        3,967.722956946 kEUR
#
# Period 1 = 31,721.400 + 87,105.410 + 5,903.495019923 = 124,730.305019923 kEUR
# Period 2 =             87,105.410 + 3,967.722956946 =  91,073.132956946 kEUR
# Sum      = 215,803.437976869 kEUR ≈ source authority Inputs!G154 ✓
#
# Note: This split is a REASONABLE APPROXIMATION based on workbook category
# evidence only. The exact draw schedule requires source DS!construction columns
# which were not available for direct read. Assumptions documented above.
_KUPI_CONSTRUCTION_USES_KEUR: tuple[float, ...] = (
    124_730.305019923,   # Period 1: FC + upfront items + half spread + front-loaded fees
    91_073.132956946,    # Period 2: remaining spread + back-end IDC/commitment
)
# Sum = 215,803.437976869 kEUR — within 0.001 kEUR of source authority ✓


# ---------------------------------------------------------------------------
# SOURCE WORKBOOK TAX MECHANICS — proven KUPI (K1/K3)
# ---------------------------------------------------------------------------

def _source_tax_params() -> TaxParams:
    """Source workbook tax (proven KUPI mechanics) — K1/K3.

    BLOCKER 2 FIX: this function now differs from _clean_tax_params() via the
    EBT_POSITIVE loss utilisation gate.  The source workbook gate condition is
    EBT > 0 (i.e. pre-LCF taxable profit is positive before loss offset), while
    clean Finco policy gates on TAXABLE_INCOME_POSITIVE (post-LCF earnings).
    With a deep SHL interest deduction the gate fires differently, producing a
    non-zero TAX_MAIN_EFFECT (K1 − K0).

    Source workbook tax mechanics (KUPI_TAX_WORKBOOK_COMPATIBILITY_GAP):
    - CIT: 10%
    - SHL interest: fully deductible
    - Loss carry-forward: rolling 5 model-period window
    - LCF utilisation gate: EBT > 0   ← KEY DIFFERENCE from clean Finco
    - Foreign SHL cap: False
    - Senior WHT: 0%, SHL interest WHT: 0%
    """
    return TaxParams(
        corporate_rate=BA_CORPORATE_RATE,
        loss_carryforward_years=5,
        loss_carryforward_cap=1.0,
        clean_cash_tax_timing_enabled=True,
        shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
        tax_loss_utilisation_gate=TaxLossUtilisationGate.EBT_POSITIVE,  # source workbook gate
    )


def _clean_tax_params() -> TaxParams:
    """Clean Finco tax params for K0/K2 control (generic BA).

    Uses TAXABLE_INCOME_POSITIVE gate (default clean Finco policy):
    LCF is only applied when taxable income after interest deductions is
    positive.  This differs from the source workbook EBT_POSITIVE gate.
    """
    return TaxParams(
        corporate_rate=BA_CORPORATE_RATE,
        loss_carryforward_years=5,
        loss_carryforward_cap=1.0,
        clean_cash_tax_timing_enabled=True,
        shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
        tax_loss_utilisation_gate=TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE,
    )


# ---------------------------------------------------------------------------
# KUPI PROJECT INPUT FACTORY — source-exact economics
# ---------------------------------------------------------------------------

def _kupi_senior_interest_config() -> SeniorDebtInterestConfig:
    """Source KUPI senior rate: 3.10% base + 280bps margin + 20bps swap = 6.10% all-in."""
    return SeniorDebtInterestConfig(
        enabled=True,
        rate_schedule=SeniorRateSchedule(
            mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
            explicit_all_in_rates=(_KUPI_ALL_IN_RATE,) * (_KUPI_SENIOR_TENOR_YEARS * 2),
        ),
        day_count=SeniorDayCountConvention.ACT_360,
    )


def build_kupi_project_inputs(
    *,
    shl_construction_interest_method: ShlConstructionInterestMethod = ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    sponsor_funding_timing_policy: SponsorFundingTimingPolicy = SponsorFundingTimingPolicy.ALL_AT_FC,
    bank_balancing_cost_eur_mwh: float = 5.0,
    use_source_workbook_tax: bool = False,
) -> ProjectInputs:
    """Build KUPI Wind project inputs — source-exact economics.

    All Senior and SHL values are engine-derived via the fixed-point solver.
    Source Senior/SHL anchors are NOT injected. See module constants for comparison values.

    Validate: Finco_total_uses ≈ 215,803.438 kEUR (within 1 kEUR).
    Max gearing: 0.80 (Inputs!D208). Source DSCR schedule: _KUPI_DSCR_SCHEDULE.

    Parameters
    ----------
    shl_construction_interest_method:
        SIMPLE for K0/K1; COMPOUND_PERIODIC for K2/K3/P0/D0 (source-evidenced).
    sponsor_funding_timing_policy:
        PRO_RATA_CONSTRUCTION for K0/K1; ALL_AT_FC for K2/K3/P0/D0.
    bank_balancing_cost_eur_mwh:
        5.0 for P0 (actual project economics).
        0.0 for D0/K0-K3 (KUPI_SOURCE_BANK_BALANCING_OMISSION_DIAGNOSTIC).
    use_source_workbook_tax:
        True for K1/K3 — source workbook proven tax mechanics (CIT 10%, 5-period LCF,
        EBT>0 gate, SHL interest fully deductible). False for K0/K2/P0/D0.
    """
    _z = CapexItem(name="Zero", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)

    # Source-exact hard CAPEX (CapEx!C99 total: 205,932.22 kEUR)
    capex = CapexStructure(
        production_units=CapexItem(
            "Production Units (Turbines)",
            144_000.0,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),
            asset_class=AssetClass.WIND_TURBINES,
        ),
        epc_contract=CapexItem(
            "EPC Contract",
            20_010.0,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),
            asset_class=AssetClass.WIND_TURBINES,
        ),
        grid_connection=CapexItem(
            "Grid Connection",
            30.0,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),
            asset_class=AssetClass.CIVIL_GRID,
        ),
        epc_other=CapexItem(
            "Monitoring & Telecom",
            100.0,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),
            asset_class=AssetClass.CIVIL_GRID,
        ),
        ops_prep=CapexItem(
            "Operation Investments",
            1_050.0,
            y0_share=1.0,
            spending_profile=(),
            asset_class=AssetClass.CIVIL_GRID,
        ),
        insurances=CapexItem(
            "Insurances",
            1_500.0,
            y0_share=1.0,
            spending_profile=(),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        lease_tax=CapexItem(
            "Land Securing",
            800.0,
            y0_share=1.0,
            spending_profile=(),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        construction_mgmt_a=CapexItem(
            "Bank DD + Lender Monitoring",
            460.0,
            y0_share=1.0,
            spending_profile=(),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        commissioning=_z,
        audit_legal=CapexItem(
            "Audit / Accounting / Legal",
            42.0,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        construction_mgmt_b=CapexItem(
            "Construction Management",
            4_629.75,
            y0_share=1.0,
            spending_profile=(),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        contingencies=CapexItem(
            "Contingencies",
            10_028.82,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        taxes=_z,
        project_acquisition=_z,
        project_rights=CapexItem(
            "Project Rights",
            23_281.65,
            y0_share=1.0,
            spending_profile=(),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        # Capitalised financing costs (Uses total = hard CAPEX + IDC + fees + VAT = 215,803.438)
        idc_keur=_KUPI_SENIOR_IDC_KEUR + _KUPI_COMMITMENT_FEE_KEUR + _KUPI_VAT_FINANCING_KEUR,
        bank_fees_keur=_KUPI_BANK_STRUCTURING_KEUR,
    )

    info = ProjectInfo(
        name="KUPI Wind — K0-K3 Diagnostic",
        company="KUPI DiagCo",
        code="KUPI-DIAG-001",
        country_iso="BA",
        financial_close=date(2028, 6, 30),
        construction_months=24,
        cod_date=date(2030, 6, 30),
        horizon_years=30,
        period_frequency=PeriodFrequency.SEMESTRIAL,
    )

    technical = TechnicalParams(
        capacity_mw=144.0,
        yield_scenario="P_50",
        operating_hours_p50=3_535.0,
        operating_hours_p90_10y=3_058.0,
        pv_degradation=0.0,
        bess_enabled=False,
    )

    # Source-exact OPEX (proven KUPI workbook mechanics):
    opex = (
        OpexItem("Technical Management",         y1_amount_keur=836.0,    annual_inflation=0.02),
        OpexItem(
            "O&M Preventive & Corrective",
            y1_amount_keur=1_320.0,
            annual_inflation=0.0,
            step_changes=_OM_STEP_CHANGES,
        ),
        OpexItem("Other Infrastructure Maint.",  y1_amount_keur=350.0,    annual_inflation=0.02),
        OpexItem("Maintain Site",                y1_amount_keur=55.0,     annual_inflation=0.02),
        OpexItem("Clean Material",               y1_amount_keur=5.0,      annual_inflation=0.02),
        OpexItem("Security",                     y1_amount_keur=20.0,     annual_inflation=0.02),
        OpexItem("Insurance",                    y1_amount_keur=1_500.0,  annual_inflation=0.02),
        OpexItem("Lease / Property Tax",         y1_amount_keur=801.738,  annual_inflation=0.0),
        OpexItem("Power Expenses",               y1_amount_keur=96.943,   annual_inflation=0.02),
        OpexItem("Audit / Accounting / Legal",   y1_amount_keur=32.0,     annual_inflation=0.02),
        OpexItem("Bank Fees",                    y1_amount_keur=20.0,     annual_inflation=0.02),
        OpexItem("Environmental & Social",       y1_amount_keur=200.0,    annual_inflation=0.02),
        OpexItem("Contingencies",                y1_amount_keur=0.0,      percentage_of_opex=0.06),
    )

    # Revenue: Central prices (P50 Base); Bank sizing uses MidLow (P90).
    revenue = RevenueParams(
        ppa_base_tariff=63.0,
        ppa_term_years=12,
        ppa_index=0.02,
        market_scenario="Central",
        market_prices_curve=_KUPI_CENTRAL_PRICES,
        market_inflation=0.0,   # exact annual prices supplied; no additional compounding
        balancing_cost_wind_eur_mwh=bank_balancing_cost_eur_mwh,
        co2_enabled=False,      # Inputs!D121=FALSE (Run A literal)
        co2_price_eur=0.0,
        balancing_cost_pv=0.0,
    )

    tax = _source_tax_params() if use_source_workbook_tax else _clean_tax_params()

    financing = FinancingParams(
        share_capital_keur=_KUPI_SHARE_CAPITAL_KEUR,
        shl_amount_keur=0.0,    # engine-derived; NOT injected from source
        shl_rate=_KUPI_SHL_RATE,
        gearing_ratio=_KUPI_MAX_GEARING,   # 0.80 — Inputs!D208 (NOT 68.18%)
        senior_tenor_years=_KUPI_SENIOR_TENOR_YEARS,
        base_rate=0.031,
        margin_bps=280,
        hedge_coverage=1.0,
        target_dscr=1.50,       # source-based; DSCR schedule overrides period-by-period
        lockup_dscr=1.10,
        min_llcr=1.50,
        dsra_months=6,
        dsra_support_mode=DebtServiceReserveSupportMode.NONE,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value,
        debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,
        sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
        senior_debt_interest_config=_kupi_senior_interest_config(),
        # Source DSCR schedule (28 periods = 14yr × 2): 24×1.50 then 4 merchant periods
        senior_sculpting_config=SeniorSculptingConfig(
            enabled=True,
            target_dscr_schedule=_KUPI_DSCR_SCHEDULE,
        ),
        # Bank sizing: MidLow prices (P90 basis) — source-evidenced
        debt_sizing_case=DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_prices_by_calendar_year_eur_mwh=_KUPI_MIDLOW_PRICES,
            merchant_price_calendar_start_year=2030,
        ),
        clean_shl_principal_keur=0.0,   # engine-derived; seed=0, fixed-point converges
        # BLOCKER 1 FIX: source G3B fixture (mvp-g3-synthetic-anti-overfit) uses
        # clean_shl_repayment_method="cash_sweep".  The bullet method is retained
        # here as the default for K0-K3 comparison consistency (so that R_BULLET vs
        # R_CASH_SWEEP isolates the repayment method effect cleanly).
        # All P0/D0/K0-K3 cases use "bullet" for internal factorial consistency.
        # R_CASH_SWEEP and R_BULLET are the dedicated repayment-method diagnostic cases.
        clean_shl_repayment_method="bullet",
        shl_maturity_period_index=_KUPI_SHL_MATURITY_PERIOD_IDX,
        shl_principal_eligibility_start_period=_KUPI_SHL_ELIGIBILITY_START,
        shl_day_count_convention="PERIOD_AXIS_ACTUAL_YEAR",
        shl_construction_day_count_fraction=2.0,  # 24 months / 12
        shl_construction_interest_method=shl_construction_interest_method,
        sponsor_funding_timing_policy=sponsor_funding_timing_policy,
        # PRO_RATA uses vector; ALL_AT_FC ignores it — both supplied for consistency.
        # Sum = 215,803.438 kEUR ≈ _KUPI_TOTAL_USES_KEUR (equal halves for K0/K1 control).
        construction_period_uses_keur=_KUPI_CONSTRUCTION_USES_KEUR,
    )

    return ProjectInputs(
        info=info,
        technical=technical,
        capex=capex,
        opex=opex,
        revenue=revenue,
        financing=financing,
        tax=tax,
    )


# ---------------------------------------------------------------------------
# RUN FUNCTIONS — P0, D0, K0-K3
# ---------------------------------------------------------------------------

def run_p0_current_generic() -> ProjectFinancingResult:
    """P0 — CURRENT_CLEAN_POST_FIX3.

    Source-exact economics. Post-Fix3 defaults: ALL_AT_FC + COMPOUND_PERIODIC.
    balancing=5 EUR/MWh. Source workbook tax. Engine-derived Senior and SHL.
    """
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=5.0,
            use_source_workbook_tax=True,
        ),
        source_id="KUPI_P0_CURRENT_CLEAN_POST_FIX3",
    )


def run_d0_bank_balancing_diagnostic() -> ProjectFinancingResult:
    """D0 — KUPI_SOURCE_BANK_BALANCING_OMISSION_DIAGNOSTIC.

    Diagnostic override: balancing_cost=0 EUR/MWh for bank CFADS sizing.
    This is NOT production logic. Tests whether source Senior can be explained
    by an omission of the 5 EUR/MWh balancing deduction in bank sizing.
    All other inputs identical to P0 (source-exact, ALL_AT_FC + COMPOUND_PERIODIC).
    """
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=0.0,   # DIAGNOSTIC: omit balancing for bank CFADS
            use_source_workbook_tax=True,
        ),
        source_id="KUPI_D0_BANK_BALANCING_OMISSION_DIAGNOSTIC",
    )


def run_k0_control() -> ProjectFinancingResult:
    """K0 — Control: D0 bank revenue + CLEAN Finco tax + PRO_RATA + SIMPLE."""
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            bank_balancing_cost_eur_mwh=0.0,
            use_source_workbook_tax=False,
        ),
        source_id="KUPI_K0_CONTROL",
    )


def run_k1_source_tax() -> ProjectFinancingResult:
    """K1 — Tax effect: D0 revenue + SOURCE WORKBOOK TAX FORMULAS + PRO_RATA + SIMPLE.

    Source workbook tax: CIT 10%, 5-period LCF, EBT>0 gate, SHL interest fully deductible.
    TAX_MAIN_EFFECT = Senior(K1) - Senior(K0).
    """
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            bank_balancing_cost_eur_mwh=0.0,
            use_source_workbook_tax=True,   # source workbook proven mechanics
        ),
        source_id="KUPI_K1_SOURCE_TAX",
    )


def run_k2_source_shl() -> ProjectFinancingResult:
    """K2 — SHL effect: D0 revenue + CLEAN Finco tax + ALL_AT_FC + COMPOUND_PERIODIC."""
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=0.0,
            use_source_workbook_tax=False,
        ),
        source_id="KUPI_K2_SOURCE_SHL",
    )


def run_k3_combined() -> ProjectFinancingResult:
    """K3 — Combined: D0 revenue + SOURCE WORKBOOK TAX + ALL_AT_FC + COMPOUND_PERIODIC."""
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=0.0,
            use_source_workbook_tax=True,
        ),
        source_id="KUPI_K3_COMBINED",
    )


# ---------------------------------------------------------------------------
# BLOCKER 1 — SHL REPAYMENT METHOD DIAGNOSTIC (R_BULLET vs R_CASH_SWEEP)
# ---------------------------------------------------------------------------
# Source G3B fixture uses cash_sweep.  These two cases differ ONLY in repayment
# method; all other inputs are identical to K3 (the most source-comparable case).
# REPAYMENT_EFFECT = Senior(R_CASH_SWEEP) - Senior(R_BULLET)
# Source SHL total operating interest anchor: 48,681.151163696 kEUR (comparison only).
# ---------------------------------------------------------------------------

def _build_kupi_for_repayment_method(repayment_method: str) -> ProjectFinancingResult:
    """Internal: run K3-equivalent but with explicit SHL repayment method override."""
    from dataclasses import replace as _replace
    inputs = build_kupi_project_inputs(
        shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
        sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
        bank_balancing_cost_eur_mwh=0.0,
        use_source_workbook_tax=True,
    )
    # Override only the SHL repayment method:
    financing_override = _replace(inputs.financing, clean_shl_repayment_method=repayment_method)
    inputs_override = _replace(inputs, financing=financing_override)
    return run_project_financing_model(
        inputs_override,
        source_id=f"KUPI_R_{repayment_method.upper()}_REPAYMENT_DIAGNOSTIC",
    )


def run_r_bullet() -> ProjectFinancingResult:
    """R_BULLET — K3 base with bullet SHL repayment (current fixture default).

    Used as the repayment-method control case against R_CASH_SWEEP.
    All other inputs identical to K3.
    """
    return _build_kupi_for_repayment_method("bullet")


def run_r_cash_sweep() -> ProjectFinancingResult:
    """R_CASH_SWEEP — K3 base with cash_sweep SHL repayment (source-evidenced).

    Source G3B fixture (mvp-g3-synthetic-anti-overfit:tests/helpers/g3b_kupi_project.py)
    specifies clean_shl_repayment_method="cash_sweep".
    REPAYMENT_EFFECT = Senior(R_CASH_SWEEP) - Senior(R_BULLET).
    All other inputs identical to K3.
    """
    return _build_kupi_for_repayment_method("cash_sweep")


# ---------------------------------------------------------------------------
# CAUSAL DECOMPOSITION
# ---------------------------------------------------------------------------

class KupiCausalGrid(NamedTuple):
    """Results and causal decompositions for the KUPI K0-K3 factorial.

    Also includes R_BULLET and R_CASH_SWEEP for the SHL repayment method
    diagnostic (BLOCKER 1).
    """
    p0: ProjectFinancingResult
    d0: ProjectFinancingResult
    k0: ProjectFinancingResult
    k1: ProjectFinancingResult
    k2: ProjectFinancingResult
    k3: ProjectFinancingResult
    r_bullet: ProjectFinancingResult
    r_cash_sweep: ProjectFinancingResult

    @property
    def senior_p0(self) -> float:
        return self.p0.final_senior_commitment_keur

    @property
    def senior_d0(self) -> float:
        return self.d0.final_senior_commitment_keur

    @property
    def senior_k0(self) -> float:
        return self.k0.final_senior_commitment_keur

    @property
    def senior_k1(self) -> float:
        return self.k1.final_senior_commitment_keur

    @property
    def senior_k2(self) -> float:
        return self.k2.final_senior_commitment_keur

    @property
    def senior_k3(self) -> float:
        return self.k3.final_senior_commitment_keur

    @property
    def delta_d0_vs_p0(self) -> float:
        """D0 - P0: Senior uplift from removing balancing cost for bank sizing."""
        return self.senior_d0 - self.senior_p0

    @property
    def tax_main_effect(self) -> float:
        """K1 - K0: Marginal impact of source workbook tax vs clean Finco tax."""
        return self.senior_k1 - self.senior_k0

    @property
    def shl_main_effect(self) -> float:
        """K2 - K0: Marginal impact of ALL_AT_FC + COMPOUND vs PRO_RATA + SIMPLE."""
        return self.senior_k2 - self.senior_k0

    @property
    def combined_effect(self) -> float:
        """K3 - K0: Combined effect of both dimensions."""
        return self.senior_k3 - self.senior_k0

    @property
    def interaction_effect(self) -> float:
        """Interaction: K3 - K1 - K2 + K0."""
        return self.senior_k3 - self.senior_k1 - self.senior_k2 + self.senior_k0

    @property
    def senior_r_bullet(self) -> float:
        return self.r_bullet.final_senior_commitment_keur

    @property
    def senior_r_cash_sweep(self) -> float:
        return self.r_cash_sweep.final_senior_commitment_keur

    @property
    def repayment_effect(self) -> float:
        """REPAYMENT_EFFECT = Senior(R_CASH_SWEEP) - Senior(R_BULLET)."""
        return self.senior_r_cash_sweep - self.senior_r_bullet

    @property
    def k3_residual_vs_source(self) -> float:
        """Source anchor comparison: 147,150.442 - Senior(K3). NOT a target."""
        return SOURCE_SENIOR_KEUR - self.senior_k3

    def print_report(self) -> None:
        """Print the causal grid report to stdout."""
        print("\n" + "=" * 75)
        print("KUPI K0-K3 CAUSAL GRID — Post-Fix3 Diagnostic (source-exact inputs)")
        print("=" * 75)
        print(f"\n{'Case':<8} {'Senior (kEUR)':>16} {'SHL Cash (kEUR)':>16} "
              f"{'PIK (kEUR)':>12} {'Opening SHL (kEUR)':>18}")
        print("-" * 74)
        for label, res in [("P0", self.p0), ("D0", self.d0), ("K0", self.k0),
                            ("K1", self.k1), ("K2", self.k2), ("K3", self.k3),
                            ("R_BULLET", self.r_bullet), ("R_SWEEP", self.r_cash_sweep)]:
            print(f"{label:<8} {res.final_senior_commitment_keur:>16.3f} "
                  f"{res.derived_shl_cash_principal_keur:>16.3f} "
                  f"{res.shl_construction_pik_keur:>12.3f} "
                  f"{res.opening_operating_shl_balance_keur:>18.3f}")
        print("-" * 74)
        print(f"\n{'SOURCE':8} {SOURCE_SENIOR_KEUR:>16.3f} {SOURCE_SHL_PRINCIPAL_KEUR:>16.3f} "
              f"{SOURCE_PIK_KEUR:>12.3f} {SOURCE_OPENING_SHL_KEUR:>18.3f}")
        print("\n--- Causal Decomposition (Senior, kEUR) ---")
        print(f"  D0 - P0  (balancing omission diagnostic): {self.delta_d0_vs_p0:+.3f}")
        print(f"  TAX_MAIN_EFFECT    K1-K0:                 {self.tax_main_effect:+.3f}")
        print(f"  SHL_MAIN_EFFECT    K2-K0:                 {self.shl_main_effect:+.3f}")
        print(f"  COMBINED_EFFECT    K3-K0:                 {self.combined_effect:+.3f}")
        print(f"  INTERACTION_EFFECT K3-K1-K2+K0:          {self.interaction_effect:+.3f}")
        print(f"  REPAYMENT_EFFECT   R_SWEEP - R_BULLET:   {self.repayment_effect:+.3f}")
        print(f"  K3_RESIDUAL vs source anchor:             {self.k3_residual_vs_source:+.3f}")
        print("  (source Senior 147,150.442 kEUR — comparison anchor only, NOT a target)")
        print("=" * 75)


def run_full_grid() -> KupiCausalGrid:
    """Run all 8 cases (P0, D0, K0-K3, R_BULLET, R_CASH_SWEEP) and return the causal grid."""
    p0 = run_p0_current_generic()
    d0 = run_d0_bank_balancing_diagnostic()
    k0 = run_k0_control()
    k1 = run_k1_source_tax()
    k2 = run_k2_source_shl()
    k3 = run_k3_combined()
    r_bullet = run_r_bullet()
    r_cash_sweep = run_r_cash_sweep()
    return KupiCausalGrid(
        p0=p0, d0=d0, k0=k0, k1=k1, k2=k2, k3=k3,
        r_bullet=r_bullet, r_cash_sweep=r_cash_sweep,
    )


if __name__ == "__main__":
    grid = run_full_grid()
    grid.print_report()
