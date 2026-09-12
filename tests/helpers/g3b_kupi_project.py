"""G3B KUPI fixture — real out-of-sample validation.

KUPI: 144 MW Wind, Bosnia & Herzegovina.  Existing real project built on the
same TUHO template family but with materially different economics and financing.

This fixture is TEST / DIAGNOSTIC ONLY.  It is NOT registered in the application
UI, NOT callable from any production factory registry, and must NOT be committed
to any user-facing feature branch without explicit authorisation.

Workbook:   20260422_KUPI_BP_NEW.xlsm
SHA-256:    111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954
Authority:  KUPI_G3B_Source_Authority_Pack_2026-08-17.md
            KUPI_G3B_Authority_Map_2026-08-17.json

──────────────────────────────────────────────────────────────────────────────
SOURCE QUALITY REGISTER (pre-recorded before any Finco comparison)
──────────────────────────────────────────────────────────────────────────────
SQ-01 SOURCE_CIRCULARITY_RESIDUAL
  Inputs!G154 Total Uses    = 215,803.437976869 kEUR
  Inputs!D154 sources/cash  = 215,804.821023411 kEUR
  Inputs!H154 absolute gap  =       1.383046543 kEUR
  Rule: use Inputs!G154 as authority for Total Uses;
        use DS!D44/Inputs!D178 as authority for final Senior.
        Do NOT target the 1.383 kEUR overfund.

SQ-02 SOURCE_INPUT_INCONSISTENCY — CO2 toggle unused
  Inputs!D121 = FALSE (CO2 Certificates Sales)
  CF!H35 = 1,075.477 kEUR certificate revenue present in source CF.
  Run A (this fixture): co2_enabled=False (literal input).
  Run B: SOURCE_EFFECTIVE_UNUSED_TOGGLE_DIAGNOSTIC using exact 30-year CO2 price schedule.
  Source total CO2 revenue (sum CF!row35): 25,002.043309 kEUR.

SQ-03 SOURCE_INPUT_INCONSISTENCY — turbine label conflict
  Inputs!I53 = NORDEX N175
  Scenarios!I8 = V150-6.0MW-HH125m
  Financial logic must NOT dispatch on turbine string.  Non-financial metadata.

──────────────────────────────────────────────────────────────────────────────
PRE-CLASSIFIED CAPABILITY GAPS (do not implement fixes during G3B diagnostic)
──────────────────────────────────────────────────────────────────────────────
KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP  →  CURRENT_FINCO_CAPABILITY_GAP
  Source IDC!D51: source_SHL × ((1+8%)^2 − 1) = 11,340.658 kEUR   [compound]
  Source SHL principal (comparison anchor): 68,152.996 kEUR
  Source compound PIK:                68,153 × ((1.08)^2 − 1) = 11,340.658 kEUR
  Source simple counterfactual:       68,153 × 8% × 2          = 10,904.479 kEUR
  Pure method delta (source-SHL basis):                           +436.179 kEUR  ← capability gap
  Finco primitive: simple interest, dcf=2.0 (24 months / 12).
  Finco simple PIK: engine_SHL × 8% × 2.0 ≈ 79,596 × 0.16      = 12,735.337 kEUR
  Finco compound counterfactual: 79,596 × ((1.08)^2 − 1)        ≈ 13,244.750 kEUR
  Pure method delta (Finco-SHL basis):                            ≈+509.413 kEUR
  CROSS_BASIS_SHL_PIK_DIFFERENCE: 12,735.337 − 11,340.658 = +1,394.678 kEUR
    This is NOT the pure method delta — it mixes different SHL principals.
  Rule: do NOT set dcf≈2.08 to match.  Quantify downstream impact, stop.

GENERIC_DYNAMIC_REVENUE_RATIO_DSCR_FORMULA_NOT_IMPLEMENTED  →  CURRENT_FINCO_CAPABILITY_GAP
  Source DS!row13 = merchant_revenue / total_revenue (merchant_revenue_ratio).
  This ratio can EXCEED 100%: AF13≈1.030598, AH13≈1.031398.
  Do NOT call it "merchant_share" — it is not normalised.
  Source target_dscr[t] = PPA_DSCR + (Merchant_DSCR - PPA_DSCR) × merchant_revenue_ratio[t]
  This yields DS!row19: 24×1.50 then AF19≈1.757649, AG19≈1.757649, AH19≈1.757849, AI19≈1.757849.
  KUPI_PROJECT_DSCR_SCHEDULE_RESULT_REPRODUCED via explicit _KUPI_DSCR_SCHEDULE.
  This is a generic configurability gap — NOT a KUPI numeric schedule parity failure.

KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP  →  DEFINITION_OR_TIMING_DIFFERENCE
  Source Eq places full SHL (68,152.996 kEUR) + Share Capital (500 kEUR) at FC.
  Clean engine distributes contributions through construction via generic policy.
  Do not hardcode FC timing in production to match XIRR.

KUPI_TAX_WORKBOOK_COMPATIBILITY_GAP   →  CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY
  Source: 5 model-period LCF + EBT-positive gate + model-year CIT pairing.
  Clean: calendar tax year + taxable-income-positive gate.
  Total source cash CIT anchor: 95,291.964 kEUR (comparison only, not runtime target).

KUPI_SOURCE_BANK_REVENUE_BALANCING_OMISSION  →  SOURCE_WORKBOOK_ASYMMETRY_OR_INCONSISTENCY
  Finco revenue-stack principle: balancing cost is a REVENUE-SIDE PROJECT INPUT.
  The same revenue definition (gross energy + CO2 − balancing) is used for both
  Base and Bank cases. The Bank case may differ only in SCENARIO INPUTS (P90, price curve,
  DSCR target) — not in what constitutes project revenue.
  Source bank CFADS formula: DS Bank CFADS = P90_revenue − OPEX — balancing NOT deducted.
  No explicit lender evidence (term sheet, lender note, dedicated Bank balancing input)
  was found to prove the omission is deliberate policy.
  Finco is economically consistent. The no-balancing diagnostic variant explains WHY
  source Senior is higher — it is NOT a candidate production methodology change.
  Literal Finco Senior:      135,707.583 kEUR
  Source Senior:             147,150.442 kEUR
  Literal gap:               −11,442.860 kEUR
  No-bal diagnostic Senior:  147,649.261 kEUR   (bridge: +11,941.678 kEUR)
  Residual after bridge:        +498.819 kEUR   →  KUPI_SENIOR_GAP_RESIDUAL  OPEN_SMALL_RESIDUAL

G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED  →  (existing known boundary — not KUPI-specific)
  Sub-cause 1: CASH_DSRA draw/replenishment not fully causal.
  Sub-cause 2: J-DSRA not modelled.
  Sub-cause 3: within_senior_maturity period-index proxy unproven vs source.

──────────────────────────────────────────────────────────────────────────────
SOURCE AUTHORITY ANCHORS (comparison after blind run — NOT runtime inputs)
──────────────────────────────────────────────────────────────────────────────
  Final Senior             DS!D44 / Inputs!D178  =  147,150.442310339 kEUR
  Senior total principal   DS!D49                =  147,150.442310339 kEUR
  Senior total interest    DS!D50                =   78,848.801061344 kEUR
  Avg Base Senior DSCR     CF!D128               =        1.859035714x
  Min Base Senior DSCR     CF!D150               =           1.689000x
  Initial SHL              Inputs!D308/D311      =   68,152.995666529 kEUR  [comparison anchor]
  Construction SHL PIK     IDC!D51 / DS!D125     =   11,340.658478910 kEUR  [compound; comparison only]
  First op SHL opening     DS!D124 derived       =   79,493.654145440 kEUR  [source compound; comparison]
  Total SHL principal      DS!D124               =   79,493.654145440 kEUR
  Total SHL interest       DS!D122               =   48,681.151163696 kEUR
  Source total cash CIT    sum P&L!G44:DW44      =   95,291.964024174 kEUR
  Project IRR              CF!D125               =       11.732259393%
  Unlevered Project IRR    CF!D126               =       11.903558373%
  Equity IRR               Eq!D28                =       17.136128545%
  Gross Total Sponsor XIRR Eq!row84 recomputed   =       16.987158032%
  Net Total Sponsor XIRR   Eq!D85                =       16.771044135%
  Source total CO2 revenue sum CF!row35           =   25,002.043309 kEUR
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Optional

from finco_core.inputs._models import (
    AssetClass,
    CapexItem,
    CapexStructure,
    DebtServiceReserveSupportMode,
    DebtSizingCaseConfig,
    DebtSizingMode,
    FinancingParams,
    GearingBasisMode,
    OpexItem,
    PeriodFrequency,
    ProjectInfo,
    RevenueParams,
    SponsorFundingMode,
    TaxParams,
    TechnicalParams,
    YieldScenario,
)
from finco_core.inputs import ProjectInputs
from finco_core.inputs.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)
from finco_core.inputs.senior_sculpting import SeniorSculptingConfig
from finco_core.inputs._models import RevenueAdjustmentSchedule

# ─── Source-authority design assumptions (inputs, not fitted outputs) ─────────

_KUPI_TOTAL_CAPEX_KEUR: float = 205_932.22          # CapEx!C99 hard CAPEX
_KUPI_SENIOR_IDC_KEUR: float = 7_152.520038600      # IDC pasted/source-close
_KUPI_COMMITMENT_FEE_KEUR: float = 782.925875313    # commitment fee source-close
_KUPI_BANK_STRUCTURING_KEUR: float = 1_549.590939566
_KUPI_VAT_FINANCING_KEUR: float = 386.181123400     # VAT facility financing total
_KUPI_TOTAL_USES_KEUR: float = 215_803.437976869    # Inputs!G154 authority

_KUPI_SHARE_CAPITAL_KEUR: float = 500.0             # Inputs!D295
_KUPI_MAX_GEARING: float = 0.80                     # Inputs!D208
_KUPI_SENIOR_TENOR_YEARS: int = 14
_KUPI_ALL_IN_RATE: float = 0.061                    # 3.10% + 280bps + 20bps swap
_KUPI_SHL_RATE: float = 0.08                        # Inputs!F311

# ─── Source SHL comparison anchor (NOT used as a model input) ─────────────────
# DS!D121 / Inputs!D308 = 68,152.995666530 kEUR.
# This is a SOURCE OUTPUT: Uses_source − Senior_source − Capital.
# It is provided here for post-run comparison only.
# The fixture uses the ENGINE_DERIVED_SHL_ADAPTER_HANDSHAKE_DIAGNOSTIC to supply
# clean_shl_principal_keur derived from run_project_financing_model's G2A fixed-point.
_KUPI_SOURCE_SHL_PRINCIPAL_KEUR: float = 68_152.995666530  # comparison anchor only
_KUPI_SHL_PRINCIPAL_KEUR = _KUPI_SOURCE_SHL_PRINCIPAL_KEUR  # alias kept for test imports

# Period axis for 30yr semestrial:
_KUPI_SHL_MATURITY_PERIOD_IDX: int = 61   # last operating period (confirmed by period grid)
_KUPI_SHL_ELIGIBILITY_START: int = 2      # first operating period

# ─── DSCR target schedule — exact source DS!row19 values ─────────────────────
# Source DS!row19: 24 periods at 1.50 (PPA), then 4 periods at formula result.
# Formula: merchant_share × 1.75 + (1 − merchant_share) × 1.50
# For 100% merchant periods the formula yields ≈1.7576 (not exactly 1.75).
# Exact values extracted from DS!AF:AI:
#   AF: 1.757649388048956, AG: 1.757649388048956
#   AH: 1.7578495048083824, AI: 1.7578495048083824
# KUPI_DSCR_REVENUE_MIX_FORMULA_GAP: engine cannot derive from revenue mix dynamically.
# Explicit schedule supplied here matching source DS!row19 exactly.
_KUPI_DSCR_SCHEDULE: tuple[float, ...] = (
    1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50,   # periods 2..9   (PPA years 1..4)
    1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50,   # periods 10..17 (PPA years 5..8)
    1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50,   # periods 18..25 (PPA years 9..12)
    1.757649388048956, 1.757649388048956,               # periods 26..27 (merchant yr 1)
    1.7578495048083824, 1.7578495048083824,             # periods 28..29 (merchant yr 2)
)  # 28 periods total = 14yr × 2

# ─── Merchant price curves — exact source values ──────────────────────────────
# Extracted from workbook Inputs sheet (data_only=True):
#   Inputs!E106:AI106 = Central inflated prices (row 107 × row 111), 2030-2060 (31 years)
#   Inputs!E109:AI109 × Inputs!E111:AI111 = MidLow inflated prices, 2030-2060
# Exact annual values (calendar years 2030-2060, 31 values).
# Post-2060 not required: 30yr project from COD 2030 ends in 2060.
_KUPI_CENTRAL_PRICES: tuple[float, ...] = (
    99.572,    102.265,   107.985,   111.618,   110.789,   110.776,   114.824,
    114.554,   109.134,   107.448,   107.602,   113.847,   114.520,   114.972,
    115.340,   114.996,   115.213,   115.962,   117.552,   118.174,   118.736,
    119.238,   122.265,   124.584,   126.909,   129.958,   133.015,   134.984,
    137.856,   140.532,   132.645,
)  # Inputs!E106:AI106, years 2030-2060

_KUPI_MIDLOW_PRICES: tuple[float, ...] = (
    79.233,    81.360,    84.928,    87.224,    89.309,    91.805,    95.914,
    97.663,    95.718,    96.228,    95.542,    97.955,    98.210,    98.384,
    98.404,    97.828,    97.697,    98.637,   100.172,   101.028,   101.762,
    102.538,  104.738,   106.401,   107.970,   110.229,   112.388,   113.834,
    115.968,  117.992,   111.093,
)  # row109 × row111, years 2030-2060

# ─── CO2 certificate price schedule — exact source Inputs!E123:AH123 ─────────
# 30 annual values (years 1-30 from COD = 2030-2059 semi-annual pairs).
# Used for Run B (SOURCE_EFFECTIVE_UNUSED_TOGGLE_DIAGNOSTIC).
# Source total CO2 revenue (CF!row35): 25,002.043309 kEUR.
_KUPI_CO2_ANNUAL_PRICES: tuple[float, ...] = (
    4.191063311878815, 3.7830324552157393, 3.3750015985526645, 2.9669707418895896,
    2.45, 2.35, 2.2, 2.1, 2.05, 1.95, 1.8, 1.7, 1.6, 1.5, 1.4, 1.3,
    1.2, 1.15, 1.05, 1.0, 0.95, 0.9, 0.85, 0.8, 0.8, 0.8, 0.75, 0.75,
    0.7, 0.7,
)  # Inputs!E123:AH123 (30 years)

# ─── O&M exact step schedule — Scenarios!E79:E108 ────────────────────────────
# Annual values (30 years, Y1-Y30):
# Y1-Y2: 1320, Y3-Y4: 1488, Y5-Y9: 1752, Y10-Y14: 1824, Y15-Y19: 2040,
# Y20-Y22: 2328, Y23-Y30: 2616.
_OM_STEP_CHANGES: tuple[tuple[int, float], ...] = (
    (3, 1488.0),    # Y3: 1320 → 1488
    (5, 1752.0),    # Y5: 1488 → 1752
    (10, 1824.0),   # Y10: 1752 → 1824  (Scenarios!E88)
    (15, 2040.0),   # Y15: 1824 → 2040  (Scenarios!E93)
    (20, 2328.0),   # Y20: 2040 → 2328  (Scenarios!E98)
    (23, 2616.0),   # Y23: 2328 → 2616  (Scenarios!E101)
)


def _build_kupi_project_inputs(
    name: str,
    company: str,
    code: str,
    clean_shl_principal_keur: float,
) -> ProjectInputs:
    """Build KUPI ProjectInputs with a caller-supplied SHL principal.

    Called by create_kupi_project() after the ENGINE_DERIVED_SHL_ADAPTER_HANDSHAKE.
    The clean_shl_principal_keur argument MUST be the engine-derived G2A residual,
    not the source Senior output.
    """
    _z = CapexItem(name="Zero", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)

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
        idc_keur=_KUPI_SENIOR_IDC_KEUR + _KUPI_COMMITMENT_FEE_KEUR + _KUPI_VAT_FINANCING_KEUR,
        bank_fees_keur=_KUPI_BANK_STRUCTURING_KEUR,
    )

    info = ProjectInfo(
        name=name,
        company=company,
        code=code,
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

    opex = (
        OpexItem("Technical Management", y1_amount_keur=836.0, annual_inflation=0.02),

        # O&M Preventive & Corrective — exact Scenarios!E79:E108 step schedule
        OpexItem(
            "O&M Preventive & Corrective",
            y1_amount_keur=1_320.0,
            annual_inflation=0.0,
            step_changes=_OM_STEP_CHANGES,
        ),

        # Other Infrastructure Maintenance (Minor, HV, Regulatory, HSE, Met, Blade, Vehicle)
        # Sum: 72+70+36+10+8+144+10 = 350 kEUR; inflation matches parent B.02 = 2%
        OpexItem("Other Infrastructure Maintenance", y1_amount_keur=350.0, annual_inflation=0.02),

        OpexItem("Maintain Site", y1_amount_keur=55.0, annual_inflation=0.02),
        OpexItem("Clean Material", y1_amount_keur=5.0, annual_inflation=0.02),
        OpexItem("Security", y1_amount_keur=20.0, annual_inflation=0.02),
        OpexItem("Insurance", y1_amount_keur=1_500.0, annual_inflation=0.02),

        # Lease & Property Tax — OpEx!B07 inflation=0 (municipality/county % of income)
        OpexItem("Lease / Property Tax", y1_amount_keur=801.738, annual_inflation=0.0),

        # Power Expenses — OpEx!B08 = 96.94296, 2%
        OpexItem("Power Expenses", y1_amount_keur=96.943, annual_inflation=0.02),

        # Audit & Accounting & Legal — OpEx!B10 = 32 kEUR, 2%
        OpexItem("Audit / Accounting / Legal", y1_amount_keur=32.0, annual_inflation=0.02),

        OpexItem("Bank Fees", y1_amount_keur=20.0, annual_inflation=0.02),

        # Environmental & Social — OpEx!B12 = 200 kEUR (100 mitigation + 100 fauna/flora), 2%
        OpexItem("Environmental & Social", y1_amount_keur=200.0, annual_inflation=0.02),

        # Contingencies — OpEx!B13 = 6% of total OPEX base
        OpexItem("Contingencies", y1_amount_keur=0.0, percentage_of_opex=0.06),
    )

    # Run A: literal CO2-off (Inputs!D121=FALSE)
    revenue = RevenueParams(
        ppa_base_tariff=63.0,
        ppa_term_years=12.0,
        ppa_index=0.02,
        ppa_production_share=1.0,
        market_scenario="Central",
        market_prices_curve=_KUPI_CENTRAL_PRICES,
        market_inflation=0.0,               # exact annual prices supplied; no compounding
        balancing_cost_pv=0.0,
        balancing_cost_wind_eur_mwh=5.0,
        co2_enabled=False,                  # Inputs!D121=FALSE (Run A literal)
    )

    financing = FinancingParams(
        share_capital_keur=_KUPI_SHARE_CAPITAL_KEUR,
        shl_amount_keur=clean_shl_principal_keur,
        shl_rate=_KUPI_SHL_RATE,
        gearing_ratio=_KUPI_MAX_GEARING,
        senior_tenor_years=_KUPI_SENIOR_TENOR_YEARS,
        base_rate=0.031,
        margin_bps=280,
        hedge_coverage=1.0,
        target_dscr=1.50,
        lockup_dscr=1.10,
        min_llcr=1.50,
        dsra_months=6,
        dsra_support_mode=DebtServiceReserveSupportMode.NONE,
        equity_irr_method="equity_only",
        debt_sizing_method="dscr_sculpt",
        debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,
        sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
        senior_debt_interest_config=SeniorDebtInterestConfig(
            enabled=True,
            rate_schedule=SeniorRateSchedule(
                mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
                explicit_all_in_rates=(_KUPI_ALL_IN_RATE,) * (_KUPI_SENIOR_TENOR_YEARS * 2),
            ),
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        senior_sculpting_config=SeniorSculptingConfig(
            enabled=True,
            target_dscr_schedule=_KUPI_DSCR_SCHEDULE,
        ),
        debt_sizing_case=DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_prices_by_calendar_year_eur_mwh=_KUPI_MIDLOW_PRICES,
            merchant_price_calendar_start_year=2030,
        ),
        # ENGINE_DERIVED_SHL_ADAPTER_HANDSHAKE_DIAGNOSTIC:
        # clean_shl_principal_keur is set by create_kupi_project() after stage-1 run.
        # The engine's fixed-point in run_project_financing_model() overrides this value
        # via G2A convergence (candidate_shl starts at 0.0). Setting it to the
        # engine-derived residual ensures the configured value matches what the engine
        # independently computes, with no source Senior output as input.
        clean_shl_principal_keur=clean_shl_principal_keur,
        clean_shl_repayment_method="cash_sweep",
        shl_maturity_period_index=_KUPI_SHL_MATURITY_PERIOD_IDX,
        shl_principal_eligibility_start_period=_KUPI_SHL_ELIGIBILITY_START,
        shl_day_count_convention="PERIOD_AXIS_ACTUAL_YEAR",
        # Construction accrual: 24 months / 12 = 2.0 (simple interest, source 24-month build).
        # KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP: source uses compound ((1.08)^2−1);
        # engine uses simple (rate × dcf). Capability gap documented; not implemented here.
        shl_construction_day_count_fraction=2.0,
    )

    tax = TaxParams(
        corporate_rate=0.10,
        loss_carryforward_years=5,
        loss_carryforward_cap=1.0,
        clean_cash_tax_timing_enabled=True,
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


def create_kupi_project(
    name: str = "KUPI",
    company: str = "KUPI Energy",
    code: str = "KUP",
) -> ProjectInputs:
    """Return canonical ProjectInputs for KUPI G3B diagnostic.

    ENGINE_DERIVED_SHL_ADAPTER_HANDSHAKE_DIAGNOSTIC (two-stage):
      Stage 1: Run run_project_financing_model() with a seed SHL to get the
               engine's G2A-derived SHL residual.
      Stage 2: Build the definitive ProjectInputs with clean_shl_principal_keur
               set to the engine-derived value (not any source Senior output).

    Note: the engine's fixed-point in run_project_financing_model() always overrides
    clean_shl_principal_keur with the G2A convergence result (candidate_shl starts at
    0.0 regardless of the input value). The handshake makes the CONFIGURED value match
    what the engine derives independently, for governance documentation.

    Run A (this function): literal CO2-off (Inputs!D121=FALSE).
    Run B (create_kupi_project_source_effective_co2): SOURCE_EFFECTIVE_UNUSED_TOGGLE.
    """
    from financial_engine.financing import run_project_financing_model

    # Stage 1: seed run (any positive SHL value; engine overrides via fixed-point)
    seed_proj = _build_kupi_project_inputs(
        name=name, company=company, code=code,
        clean_shl_principal_keur=1.0,          # seed; overridden by fixed-point
    )
    fr_stage1 = run_project_financing_model(seed_proj)
    engine_derived_shl = fr_stage1.derived_shl_cash_principal_keur

    # Stage 2: definitive project with engine-derived SHL
    return _build_kupi_project_inputs(
        name=name, company=company, code=code,
        clean_shl_principal_keur=engine_derived_shl,
    )


def create_kupi_project_source_effective_co2() -> ProjectInputs:
    """Run B: SOURCE_EFFECTIVE_UNUSED_TOGGLE_DIAGNOSTIC (SQ-02).

    Inputs!D121 = FALSE but source CF includes CO2 certificate revenue.
    This variant supplies the exact 30-year CO2 price schedule from Inputs!E123:AH123.

    Source total CO2 revenue (sum CF!row35): 25,002.043309 kEUR.
    The Run B bridge (Rev_B − Rev_A) should reconcile to this amount subject only
    to already-documented production/calendar differences between Finco and source.
    """
    base = create_kupi_project()
    # Exact 30-year annual CO2 price schedule from Inputs!E123:AH123.
    # Each annual price applies to both semi-annual periods of that year.
    co2_semiannual = tuple(
        price
        for price in _KUPI_CO2_ANNUAL_PRICES
        for _ in range(2)           # each annual value applies to 2 semi-annual periods
    )  # 60 semi-annual values
    return replace(
        base,
        revenue=replace(
            base.revenue,
            co2_enabled=True,
            co2_sales_schedule=RevenueAdjustmentSchedule(
                semiannual_values=co2_semiannual,
            ),
        ),
    )
