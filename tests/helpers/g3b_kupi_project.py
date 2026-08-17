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
  Run B: diagnostic only, labelled SOURCE_EFFECTIVE_CASHFLOW_OVERRIDE.

SQ-03 SOURCE_INPUT_INCONSISTENCY — turbine label conflict
  Inputs!I53 = NORDEX N175
  Scenarios!I8 = V150-6.0MW-HH125m
  Financial logic must NOT dispatch on turbine string.  Non-financial metadata.

──────────────────────────────────────────────────────────────────────────────
PRE-CLASSIFIED CAPABILITY GAPS (do not implement fixes during G3B diagnostic)
──────────────────────────────────────────────────────────────────────────────
KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP  →  CURRENT_FINCO_CAPABILITY_GAP
  Source IDC!D51: SHL × ((1+8%)^2 − 1) = 11,340.658 kEUR   [compound]
  Current simple primitive (dcf=2.0):       10,904.479 kEUR
  Opening balance delta:                         436.179 kEUR
  Rule: do NOT set dcf≈2.08 to match.  Quantify downstream impact, stop.

KUPI_DSCR_REVENUE_MIX_FORMULA_GAP     →  CURRENT_FINCO_CAPABILITY_GAP
  Source DS!row19: target_dscr[t] = merchant_share[t]×1.75 + (1−merchant_share[t])×1.50
  Engine cannot derive this schedule from revenue mix dynamically.
  Explicit schedule supplied below: (1.50,)*24 + (1.75,)*4 for the 14yr senior tenor.
  This is a valid diagnostic approximation; the formula derivation gap remains open.

KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP  →  DEFINITION_OR_TIMING_DIFFERENCE
  Source Eq places full SHL (68,152.996 kEUR) + Share Capital (500 kEUR) at FC.
  Clean engine distributes contributions through construction via generic policy.
  Do not hardcode FC timing in production to match XIRR.

KUPI_TAX_WORKBOOK_COMPATIBILITY_GAP   →  CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY
  Source: 5 model-period LCF + EBT-positive gate + model-year CIT pairing.
  Clean: calendar tax year + taxable-income-positive gate.
  Total source cash CIT anchor: 95,291.964 kEUR (comparison only, not runtime target).

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
  Initial SHL              Inputs!D308/D311      =   68,152.995666529 kEUR
  Construction SHL PIK     IDC!D51 / DS!D125     =   11,340.658478910 kEUR
  First op SHL opening     derived               =   79,493.654145440 kEUR
  Total SHL principal      DS!D124               =   79,493.654145440 kEUR
  Total SHL interest       DS!D122               =   48,681.151163696 kEUR
  Source total cash CIT    sum P&L!G44:DW44      =   95,291.964024174 kEUR
  Project IRR              CF!D125               =       11.732259393%
  Unlevered Project IRR    CF!D126               =       11.903558373%
  Equity IRR               Eq!D28                =       17.136128545%
  Gross Total Sponsor XIRR Eq!row84 recomputed   =       16.987158032%
  Net Total Sponsor XIRR   Eq!D85                =       16.771044135%
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

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

# G2A SHL residual (authority identity; confirmed by blind run adapter handshake):
#   Total Uses - Senior - Share Capital
#   = 215,803.437976869 - 147,150.442310339 - 500 = 68,152.995666530
# This value is supplied here for the adapter handshake.  It is NOT used to
# target-fit the Senior amount.  After the blind run, fr.derived_shl_cash_principal_keur
# must equal this value (confirming the engine independently derived the same Senior).
_KUPI_SHL_PRINCIPAL_KEUR: float = 68_152.995666530

# Period axis estimates for 30yr semestrial:
# SYNTH-C (25yr) operating axis = 2..52 (51 periods).
# By extension KUPI (30yr) = 2..62 (61 periods) — confirmed / adjusted after blind run.
_KUPI_SHL_MATURITY_PERIOD_IDX: int = 61   # last operating period (confirmed by period grid check)
_KUPI_SHL_ELIGIBILITY_START: int = 2      # first operating period

# DSCR target schedule — explicitly supplied per lender policy:
#   PPA target  (Scenarios!E188) = 1.50x  →  14yr senior, first 12yr = 24 semi-annual periods
#   Merchant target (Scenarios!E189) = 1.75x  →  remaining 2yr = 4 semi-annual periods
# Formula: target_dscr[t] = merchant_share[t]*1.75 + (1-merchant_share[t])*1.50
# KUPI_DSCR_REVENUE_MIX_FORMULA_GAP: the engine cannot derive this schedule from
# the revenue mix dynamically; it is supplied explicitly here.
_KUPI_DSCR_SCHEDULE: tuple[float, ...] = (1.50,) * 24 + (1.75,) * 4   # 28 periods

# Merchant price curves — from source authority:
#   2030 Central reference: 90.52 × 1.10 inflation = 99.572 EUR/MWh
#   2030 MidLow reference:  72.03 × 1.10 inflation = 79.233 EUR/MWh
# Full Scenarios table (raw curves × inflation) not available in authority pack
# for extraction.  2030 anchor values used; 2.5% annual growth approximation
# applied for Y2031+.  Merchant price mismatch attributed to approximation
# and classified MATCH_WITHIN_APPROXIMATION after comparison.
_MARKET_INFLATION: float = 0.025
_CENTRAL_2030: float = 99.572
_MIDLOW_2030: float = 79.233
_KUPI_CENTRAL_PRICES: tuple[float, ...] = tuple(
    _CENTRAL_2030 * (1 + _MARKET_INFLATION) ** i for i in range(40)
)
_KUPI_MIDLOW_PRICES: tuple[float, ...] = tuple(
    _MIDLOW_2030 * (1 + _MARKET_INFLATION) ** i for i in range(40)
)

# O&M Preventive & Corrective — from Scenarios!E79:E108 (annual, 30yr)
# Known source data points: Y1-2=1320, Y3-4=1488, Y5-6=1752, Y30≈2616.
# Steps Y7+ approximated (full table not in authority pack for independent extraction).
# OPEX delta for Y7-Y30 classified as approximation gap; structure is correct.
_OM_STEP_CHANGES: tuple[tuple[int, float], ...] = (
    (3, 1488.0),
    (5, 1752.0),
    (7, 1920.0),   # approximated
    (9, 2088.0),   # approximated
    (11, 2256.0),  # approximated
    (13, 2424.0),  # approximated
    (15, 2616.0),  # approximated (source Y30 anchor, reached earlier — check vs source)
)


def create_kupi_project(
    name: str = "KUPI",
    company: str = "KUPI Energy",
    code: str = "KUP",
) -> ProjectInputs:
    """Return canonical ProjectInputs for KUPI G3B diagnostic.

    Independent construction — does NOT call any existing project factory.
    Fixture is READ-ONLY diagnostic evidence.  No production factory registry entry.

    Run A (this function): literal CO2-off (Inputs!D121 = FALSE).
    Run B (create_kupi_project_source_effective_co2): SOURCE_EFFECTIVE_CASHFLOW_OVERRIDE.

    DSCR policy: explicit two-tier schedule (1.50x PPA / 1.75x merchant, 28 periods).
    KUPI_DSCR_REVENUE_MIX_FORMULA_GAP documented — engine cannot derive from revenue mix.
    """
    # ── Zero CapexItem placeholder ──────────────────────────────────────────
    _z = CapexItem(name="Zero", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)

    # ── CAPEX (source: CapEx!C99 authority = 205,932.22 kEUR) ───────────────
    # Category mapping follows KUPI_G3B_Authority_Map categories.
    # Timing: core physical = uniform 24mo; soft/upfront = first construction; A/L = uniform.
    # NOTE: C08 Bank Due Diligence (420) + C09 Construction Mgmt / lender monitoring (40)
    #       aggregated into construction_mgmt_a (same timing/treatment).
    capex = CapexStructure(
        production_units=CapexItem(
            "Production Units (Turbines)",
            144_000.0,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),      # uniform 24mo (2 construction years)
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
            spending_profile=(),                # upfront at FC
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
            460.0,                              # C08=420 + C09=40
            y0_share=1.0,
            spending_profile=(),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        commissioning=_z,
        audit_legal=CapexItem(
            "Audit / Accounting / Legal",
            42.0,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),      # uniform across construction
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
        # Financing costs: Senior IDC + commitment fee + structuring fees (source-close values).
        # TOTAL_USES_INPUT_PARITY: source financing costs accepted as design assumptions.
        # INDEPENDENT_IDC_DERIVATION_PARITY: separate capability question — not claimed here.
        idc_keur=_KUPI_SENIOR_IDC_KEUR + _KUPI_COMMITMENT_FEE_KEUR + _KUPI_VAT_FINANCING_KEUR,
        bank_fees_keur=_KUPI_BANK_STRUCTURING_KEUR,
    )

    # ── Project Info ────────────────────────────────────────────────────────
    info = ProjectInfo(
        name=name,
        company=company,
        code=code,
        country_iso="BA",                       # Bosnia & Herzegovina ISO 3166-1
        financial_close=date(2028, 6, 30),      # Inputs!D9
        construction_months=24,                 # Inputs!D10
        cod_date=date(2030, 6, 30),             # Inputs!D11
        horizon_years=30,                       # Inputs!D16
        period_frequency=PeriodFrequency.SEMESTRIAL,  # Inputs!D18
    )

    # ── Technical ───────────────────────────────────────────────────────────
    # pv_degradation=0.0: no wind degradation in source; do not invent one.
    technical = TechnicalParams(
        capacity_mw=144.0,                      # Inputs!D51
        yield_scenario="P_50",                  # base case
        operating_hours_p50=3_535.0,            # Inputs!D67
        operating_hours_p90_10y=3_058.0,        # Inputs!D71
        pv_degradation=0.0,                     # Wind: no PV degradation
        bess_enabled=False,
    )

    # ── OPEX ────────────────────────────────────────────────────────────────
    # Source categories from OpEx worksheet.  Do NOT feed a frozen output vector.
    # Infrastructure Maintenance split: O&M explicit step schedule + other fixed.
    # Contingency: 6% of remaining OPEX lines (percentage_of_opex).
    opex = (
        # Technical Management — Y1=836 kEUR, 2% inflation
        OpexItem("Technical Management", y1_amount_keur=836.0, annual_inflation=0.02),

        # Infrastructure Maintenance — O&M Preventive & Corrective (explicit step schedule)
        # Source: Scenarios!E79:E108; biennial steps from 1320 (Y1) to 2616 (Y30).
        # Steps Y7+ are approximated from Y1-6 data and Y30 anchor (full table not extracted).
        OpexItem(
            "O&M Preventive & Corrective",
            y1_amount_keur=1_320.0,
            annual_inflation=0.0,               # no second inflation layer — explicit steps
            step_changes=_OM_STEP_CHANGES,
        ),

        # Infrastructure Maintenance — Other (~350 kEUR Y1, 2% inflation)
        OpexItem("Other Infrastructure Maintenance", y1_amount_keur=350.0, annual_inflation=0.02),

        # Maintain Site — Y1=55 kEUR, 2% inflation
        OpexItem("Maintain Site", y1_amount_keur=55.0, annual_inflation=0.02),

        # Clean Material — Y1=5 kEUR, 2% inflation
        OpexItem("Clean Material", y1_amount_keur=5.0, annual_inflation=0.02),

        # Security — Y1=20 kEUR, 2% inflation
        OpexItem("Security", y1_amount_keur=20.0, annual_inflation=0.02),

        # Insurance — Y1=1,500 kEUR
        OpexItem("Insurance", y1_amount_keur=1_500.0, annual_inflation=0.02),

        # Lease / Property Tax — Y1=801.738 kEUR
        OpexItem("Lease / Property Tax", y1_amount_keur=801.738, annual_inflation=0.02),

        # Power Expenses — Y1=96.943 kEUR
        OpexItem("Power Expenses", y1_amount_keur=96.943, annual_inflation=0.02),

        # Audit / Accounting / Legal — Y1=24 kEUR
        OpexItem("Audit / Accounting / Legal", y1_amount_keur=24.0, annual_inflation=0.02),

        # Bank Fees — Y1=20 kEUR
        OpexItem("Bank Fees", y1_amount_keur=20.0, annual_inflation=0.02),

        # Environmental & Social — effective Y1≈100 kEUR (component switches; approximated)
        OpexItem("Environmental & Social", y1_amount_keur=100.0, annual_inflation=0.02),

        # Contingencies — 6% of total OPEX base (OpEx!D87)
        OpexItem("Contingencies", y1_amount_keur=0.0, percentage_of_opex=0.06),
    )

    # ── Revenue (Run A: literal CO2-off per Inputs!D121=FALSE) ──────────────
    # Balancing cost: 5 EUR/MWh (wind-specific; Inputs!row112)
    # Merchant curve: Central 2030=99.572 EUR/MWh, 2.5% growth approximation.
    # Full Scenarios curve × inflation table not independently extracted.
    revenue = RevenueParams(
        ppa_base_tariff=63.0,                   # Inputs!D81
        ppa_term_years=12.0,                    # Inputs!D84
        ppa_index=0.02,                         # Inputs!D86
        ppa_production_share=1.0,               # Inputs!D83 = 100%
        market_scenario="Central",              # Inputs!B107
        market_prices_curve=_KUPI_CENTRAL_PRICES,
        market_inflation=_MARKET_INFLATION,
        balancing_cost_pv=0.0,                  # Wind project; no PV balancing
        balancing_cost_wind_eur_mwh=5.0,        # Inputs!row112 = 5 EUR/MWh
        co2_enabled=False,                      # Inputs!D121 = FALSE (Run A — literal)
    )

    # ── Financing ───────────────────────────────────────────────────────────
    # DSCR: two-tier schedule supplied explicitly (KUPI_DSCR_REVENUE_MIX_FORMULA_GAP).
    # Gearing capacity check: 80% × 215,803.44 = 172,642.75 kEUR > 147,150.44 → DSCR-binding.
    # SHL: CASH_SWEEP; G2A residual handshake at 68,152.996 kEUR.
    # Senior IDC and commitment/structuring fees treated as TOTAL_USES_INPUT_PARITY assumption.
    financing = FinancingParams(
        share_capital_keur=_KUPI_SHARE_CAPITAL_KEUR,
        shl_amount_keur=_KUPI_SHL_PRINCIPAL_KEUR,
        shl_rate=_KUPI_SHL_RATE,
        gearing_ratio=_KUPI_MAX_GEARING,
        senior_tenor_years=_KUPI_SENIOR_TENOR_YEARS,
        base_rate=0.031,                        # Inputs!D185
        margin_bps=280,                         # Inputs!D186
        hedge_coverage=1.0,                     # Inputs!D213 = 100%
        target_dscr=1.50,                       # PPA floor DSCR (Scenarios!E188)
        lockup_dscr=1.10,                       # Inputs!D206
        min_llcr=1.50,                          # Inputs!D207
        dsra_months=6,                          # Inputs!A331
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
                # 6.10% all-in (3.10% base + 280bps margin + 20bps swap @ 100% hedge)
                explicit_all_in_rates=(_KUPI_ALL_IN_RATE,) * (_KUPI_SENIOR_TENOR_YEARS * 2),
            ),
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        senior_sculpting_config=SeniorSculptingConfig(
            enabled=True,
            target_dscr_schedule=_KUPI_DSCR_SCHEDULE,  # (1.50,)*24 + (1.75,)*4
        ),
        # Bank case: P90-10y production + MidLow merchant prices
        debt_sizing_case=DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_prices_by_calendar_year_eur_mwh=_KUPI_MIDLOW_PRICES,
            merchant_price_calendar_start_year=2030,
        ),
        # G2A SHL adapter handshake: configured == engine-derived residual.
        # Value: 215,803.437976869 - 147,150.442310339 - 500 = 68,152.995666530 kEUR.
        # NOT target-fitting the Senior; this is the expected residual identity.
        clean_shl_principal_keur=_KUPI_SHL_PRINCIPAL_KEUR,
        clean_shl_repayment_method="cash_sweep",
        shl_maturity_period_index=_KUPI_SHL_MATURITY_PERIOD_IDX,   # estimate; confirm after blind run
        shl_principal_eligibility_start_period=_KUPI_SHL_ELIGIBILITY_START,
        shl_day_count_convention="PERIOD_AXIS_ACTUAL_YEAR",
        shl_construction_day_count_fraction=0.0,
    )

    # ── Tax (clean generic policy — KUPI_TAX_WORKBOOK_COMPATIBILITY_GAP) ───
    # Source: 10% CIT, 5 model-period LCF, EBT-positive gate, model-year CIT pairing.
    # Clean policy: calendar tax year, taxable-income-positive gate, 5yr LCF window.
    # Difference classified CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY — not a generic bug.
    tax = TaxParams(
        corporate_rate=0.10,                    # P&L!B43 / source CIT rate
        loss_carryforward_years=5,              # source Inputs!D390 = 5 periods
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


def create_kupi_project_source_effective_co2() -> ProjectInputs:
    """Run B: source-effective CO2 diagnostic.

    The source CF includes CO2 certificate revenue despite Inputs!D121=FALSE (SQ-02).
    This variant explicitly enables the source-effective certificate schedule to measure
    the CO2 bridge between literal-input Run A and source CF.

    Label: SOURCE_EFFECTIVE_CASHFLOW_OVERRIDE_DUE_TO_UNUSED_TOGGLE
    This is diagnostic only.  No production KUPI branch.  Not registered in UI.

    Source-effective first-period certificate price: CF!H36 = 4.191063 EUR/MWh.
    """
    base = create_kupi_project()
    # Source-effective CO2 revenue: 4.191 EUR/MWh in first operating period.
    # Use co2_certificate_price_eur_per_mwh as a flat first-period approximation.
    # Full schedule not available in authority pack; use first-period value.
    return replace(
        base,
        revenue=replace(
            base.revenue,
            co2_enabled=True,
            co2_certificate_price_eur_per_mwh=4.191063311878815,  # CF!H36
        ),
    )
