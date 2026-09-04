"""Project input factories — project-specific defaults outside domain schema.

Factories here contain hard-coded project values (Oborovo, TUHO) that were
extracted from domain/inputs.py to keep the domain layer generic.

For generic industry engine defaults, see create_default_solar_project()
(Test 1 — Solar) and create_default_wind_project() (Test 2 — Wind).
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from domain.inputs import (
    AssetClass,
    CapexItem,
    CapexStructure,
    DebtSizingCaseConfig,
    DebtSizingMethod,
    EquityIRRMethod,
    FinancingParams,
    OpexItem,
    PeriodAxisConvention,
    PeriodFrequency,
    ProjectInfo,
    ProjectInputs,
    RevenueAdjustmentSchedule,
    RevenueParams,
    SHLRepaymentMethod,
    TaxParams,
    TaxDepreciationMode,
    ShlInterestDeductibilityMode,
    TaxLossUtilisationGate,
    TaxPeriodisationMode,
    ShlAccountingTreatment,
    ShlPaymentMethod,
    TechnicalParams,
    YieldScenario,
)
from domain.revenue.bess import BessParams
from finco_core.engine.distribution_account.inputs import CovenantGatePolicy
from finco_core.inputs._models import (
    CapitalisationGatePolicyParams,
    DebtSizingMode,
    GearingBasisMode,
    InterestLimitationCombinationMode,
    InterestLimitationCarryforwardMode,
    InterestLimitationPolicyParams,
    ShlConstructionDayCountConvention,
    ShlConstructionInterestMethod,
    SponsorFundingMode,
    SponsorFundingTimingPolicy,
)
from finco_core.inputs.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)
from finco_core.inputs.senior_sculpting import SeniorSculptingConfig

from finco_core.inputs.construction_financing import (
    ConstructionCapexTimingInput,
    ConstructionCommitmentFeeInput,
    ConstructionFinancingInput,
    ConstructionPeriodSpec,
    ConstructionSeniorPricingInput,
    ConstructionStructuringFeeInput,
    ConstructionStructuringFeeBasisMode,
    ConstructionVatFacilityInput,
    VatFacilityCommitmentMode,
)
from finco_core.inputs.valuation import (
    CoverageCalculationDatePolicy,
    CoverageCashflowBasis,
    CoverageCfadsCase,
    CoverageDenominatorBasis,
    DebtCoverageValuationPolicy,
    DiscountConvention,
    PeriodicFirstCashflowTiming,
    PeriodicRateConversion,
    ProjectValuationPolicy,
    ValuationDatePolicy,
    ValuationPolicies,
)
from finco_core.opex.oborovo_config import build_oborovo_opex_capability
from financial_engine.financial_statements.contracts import (
    AccountingPolicyAuthority,
    AccountingPolicyConfig,
    BookCapitalizationTreatment,
    LegalReservePolicy,
)
from finco_core.inputs.cash_reserve_interest_policy import (
    CashReserveInterestPolicy,
    CashReserveInterestAuthority,
    EligibilityStatus,
    BalanceConvention,
    DayCountConvention,
)
from finco_core.inputs.distribution_accounting_policy import (
    DistributionAccountingPolicy,
    DistributionAccountingAuthority,
    OpeningUCAuthority,
)


# =============================================================================
# Accounting policy configs — source-proven per project
# =============================================================================

_BOOK_CAP_COMPONENTS_SOURCE_PROVEN = {
    "hard_capex": BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value,
    "senior_idc": BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value,
    "senior_commitment_fees": BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value,
    "bank_structuring_fees": BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value,
    "vat_facility_financing_costs": BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value,
    "shl_construction_interest": BookCapitalizationTreatment.EXPENSE_PNL.value,
    "dsra_funding": BookCapitalizationTreatment.RESTRICTED_CURRENT_ASSET.value,
    "working_capital": BookCapitalizationTreatment.UNRESTRICTED_CURRENT_ASSET.value,
}

# Legal reserve: §28/§29 — the clean kernel produces 50.0 kEUR total reserve
# for both Oborovo and TUHO (correct cap), but the per-period timing does not
# match the independently established source anchors (Oborovo first partial
# ≈0.7952 kEUR, cap-filling ≈49.2048 kEUR; TUHO: similar two-transfer pattern).
# Until the timing discrepancy is resolved by upstream source-trace audit,
# legal_reserve_authority is UNRESOLVED and the roll-forward is NOT activated.
# LegalReservePolicy(enabled=False) ensures the roll-forward kernel is not called.
_LR_UNRESOLVED = LegalReservePolicy(
    enabled=False,
    cap_fraction=0.10,
    authority=AccountingPolicyAuthority.UNRESOLVED,
)

# Pre-construction retained earnings: both Oborovo and TUHO are newly
# incorporated project SPVs with no pre-project equity history.
# Source evidence: SPV incorporation at first model period → zero opening RE.
# Authority: SOURCE_PROVEN (confirmed newly incorporated SPV structure).
_PRE_CONSTRUCTION_RE_SOURCE_PROVEN = dict(
    preconstruction_retained_earnings_keur=0.0,
    preconstruction_retained_earnings_authority=AccountingPolicyAuthority.SOURCE_PROVEN,
)

_OBOROVO_ACCOUNTING_POLICY = AccountingPolicyConfig(
    book_capitalization_authority=AccountingPolicyAuthority.SOURCE_PROVEN,
    book_capitalization_components=_BOOK_CAP_COMPONENTS_SOURCE_PROVEN,
    shl_construction_accounting_authority=AccountingPolicyAuthority.SOURCE_PROVEN,
    opening_re_authority=AccountingPolicyAuthority.SOURCE_PROVEN,
    legal_reserve_policy=_LR_UNRESOLVED,
    legal_reserve_authority=AccountingPolicyAuthority.UNRESOLVED,
    **_PRE_CONSTRUCTION_RE_SOURCE_PROVEN,
)

_TUHO_ACCOUNTING_POLICY = AccountingPolicyConfig(
    book_capitalization_authority=AccountingPolicyAuthority.SOURCE_PROVEN,
    book_capitalization_components=_BOOK_CAP_COMPONENTS_SOURCE_PROVEN,
    shl_construction_accounting_authority=AccountingPolicyAuthority.SOURCE_PROVEN,
    opening_re_authority=AccountingPolicyAuthority.SOURCE_PROVEN,
    legal_reserve_policy=_LR_UNRESOLVED,
    legal_reserve_authority=AccountingPolicyAuthority.UNRESOLVED,
    **_PRE_CONSTRUCTION_RE_SOURCE_PROVEN,
)

# Generic clean accounting policy for fictional Solar/Wind SPVs.
# Only the four approved dimensions are set to GENERIC_FINCO_POLICY.
# All other dimensions are explicitly UNRESOLVED to prevent dataclass
# defaults from accidentally upgrading unapproved accounting dimensions.
_GENERIC_CLEAN_ACCOUNTING_POLICY = AccountingPolicyConfig(
    # Approved generic dimensions:
    preconstruction_retained_earnings_keur=0.0,
    preconstruction_retained_earnings_authority=AccountingPolicyAuthority.GENERIC_FINCO_POLICY,
    opening_re_authority=AccountingPolicyAuthority.GENERIC_FINCO_POLICY,
    shl_construction_accounting_authority=AccountingPolicyAuthority.GENERIC_FINCO_POLICY,
    # All other dimensions explicitly UNRESOLVED:
    book_capitalization_authority=AccountingPolicyAuthority.UNRESOLVED,
    book_capitalization_components={},
    legal_reserve_policy=None,
    legal_reserve_authority=AccountingPolicyAuthority.UNRESOLVED,
    cash_interest_authority=AccountingPolicyAuthority.UNRESOLVED,
)


# U2 DELIVERED: SOURCE_PROVEN interest policy — rate and eligible-account identity proved
# from workbook source formulas. Unrestricted cash is causally derived through the
# canonical distribution-accounting roll-forward (U2 fixed-point). Opening UC has typed
# authority. Cash reserve interest is produced by the converged U2 transition.
# Source numeric parity exceptions are downstream of upstream financing/tax authority.
_SOURCE_PROVEN_CASH_INTEREST_POLICY = CashReserveInterestPolicy(
    authority=CashReserveInterestAuthority.SOURCE_PROVEN,
    annual_rate=0.01,
    eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
    eligible_dsra=EligibilityStatus.ELIGIBLE,
    balance_convention=BalanceConvention.OPENING,
    day_count_convention=DayCountConvention.ACTUAL_365,
    enabled=True,
)

# O.1: Oborovo cash interest policy — DSRA ELIGIBLE.
# A zero DSRA balance is not an INELIGIBLE account. Provide canonical known-zero
# DSRA schedule via dsra_opening_by_idx (SOURCE_PROVEN authority: zero throughout).
_OBOROVO_CASH_INTEREST_POLICY = CashReserveInterestPolicy(
    authority=CashReserveInterestAuthority.SOURCE_PROVEN,
    annual_rate=0.01,
    eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
    eligible_dsra=EligibilityStatus.ELIGIBLE,
    balance_convention=BalanceConvention.OPENING,
    day_count_convention=DayCountConvention.ACTUAL_365,
    enabled=True,
)


# =============================================================================
# Oborovo Solar PV (53.63 MWp, Croatia, 30-year horizon)
# =============================================================================

def create_default_oborovo() -> ProjectInputs:
    """Create default Oborovo project inputs matching Excel.

    Returns:
        ProjectInputs with Oborovo-specific defaults.
    """
    # ── Oborovo hard CAPEX — source-mapped line items ──────────────────────────
    # Source: Oborovo workbook CAPEX / Depreciation tab (reviewed 2026-07-22).
    # Useful life = 20y for all hard CAPEX (workbook Dep tab column B confirmed).
    # Payment schedules: equal monthly spread (12-month construction) unless
    # workbook proves a different pattern (upfront, milestone, completion).
    # All items are independently auditable to source workbook rows — no residual component.
    # Sum = 55,999.0855 kEUR from exact workbook row precision.
    _OBR_HARD_LIFE = 20  # source: Oborovo Dep tab, column B, confirmed 2026-07-22
    _EQ = tuple(1/12 for _ in range(12))  # equal 12-month construction spread (default)

    # Source row: "Production Units" — solar panels, inverters, trackers
    production_units = CapexItem(
        name="Production Units",
        amount_keur=10912.7,  # source ≈10,913 kEUR
        spending_profile=_EQ,
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "EPC Contract" — main civil/structural EPC
    epc_contract = CapexItem(
        name="EPC Contract",
        amount_keur=26430.0,  # source ≈26,430 kEUR
        spending_profile=_EQ,
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "EPC other costs" — additional EPC scope items
    epc_other = CapexItem(
        name="EPC Other Costs",
        amount_keur=2014.0,  # source ≈2,014 kEUR (previously 3,200 — wrong)
        spending_profile=_EQ,
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Grid connection" — grid infrastructure
    grid_connection = CapexItem(
        name="Grid Connection",
        amount_keur=4050.0,  # source ≈4,050 kEUR (previously 1,800 — wrong)
        spending_profile=_EQ,
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Investments to prepare operation phase"
    ops_prep = CapexItem(
        name="Investments to Prepare Operation Phase",
        amount_keur=150.0,  # source ≈150 kEUR (previously 500 — wrong)
        spending_profile=(0.5, 0.5),  # split across construction: H1/H2
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Insurances"
    insurances = CapexItem(
        name="Insurances",
        amount_keur=320.0,  # source ≈320 kEUR (previously 400 — wrong)
        y0_share=1.0,  # typically upfront at financial close
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Project finance costs due at closing"
    # Compatibility mapping: CapexStructure.lease_tax slot repurposed for this row.
    # These are financing advisory/legal costs capitalised at financial close.
    # Compatibility aggregation note: no lease or property tax is included here.
    lease_tax = CapexItem(
        name="Project Finance Costs at Closing",
        amount_keur=355.0,  # source ≈355 kEUR (previously 200 — wrong, was lease/property tax)
        y0_share=1.0,  # paid at financial close
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Construction Management" — full amount in primary slot
    construction_mgmt_a = CapexItem(
        name="Construction Management",
        amount_keur=1151.134,  # exact source 1,151.134 kEUR
        spending_profile=_EQ,
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Commissioning"
    commissioning = CapexItem(
        name="Commissioning",
        amount_keur=17.0,  # source ≈17 kEUR (previously 300 — wrong)
        spending_profile=(1.0,),  # completion/commissioning at end of construction
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Audit & Accounting & Legal Fees"
    audit_legal = CapexItem(
        name="Audit Accounting and Legal Fees",
        amount_keur=70.0,  # source ≈70 kEUR (previously 200 — wrong)
        spending_profile=(0.5, 0.5),
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: not a separate row — secondary construction mgmt slot unused
    construction_mgmt_b = CapexItem(
        name="Construction Management (Secondary)",
        amount_keur=0.0,  # no separate source row; amount moved to construction_mgmt_a
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Contingencies"
    contingencies = CapexItem(
        name="Contingencies",
        amount_keur=1986.440,  # exact source 1,986.440 kEUR
        y0_share=1.0,
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: no separate "taxes/duties" line in the source depreciation map
    taxes = CapexItem(
        name="Taxes and Duties",
        amount_keur=0.0,  # no separate source row (previously 150 — wrong)
        y0_share=1.0,
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Project Acquisition / Development"
    project_acquisition = CapexItem(
        name="Project Acquisition and Development",
        amount_keur=18.327,  # exact source 18.327 kEUR
        y0_share=1.0,  # pre-construction development cost
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Source row: "Project Rights"
    project_rights = CapexItem(
        name="Project Rights",
        amount_keur=8524.4845,  # exact source 8,524.4845 kEUR
        y0_share=1.0,  # acquired pre-construction
        useful_life_override=_OBR_HARD_LIFE,
    )
    # Hard CAPEX sum check: exact source rows sum to 55,999.0855 kEUR.
    # The former 55,997.7 kEUR narrative was decimal truncation across
    # Construction Management, Contingencies, Project Acquisition/Development,
    # and Project Rights — each row independently sourced, no residual adjustment.

    capex = CapexStructure(
        epc_contract=epc_contract,
        production_units=production_units,
        epc_other=epc_other,
        grid_connection=grid_connection,
        ops_prep=ops_prep,
        insurances=insurances,
        lease_tax=lease_tax,
        construction_mgmt_a=construction_mgmt_a,
        commissioning=commissioning,
        audit_legal=audit_legal,
        construction_mgmt_b=construction_mgmt_b,
        contingencies=contingencies,
        taxes=taxes,
        project_acquisition=project_acquisition,
        project_rights=project_rights,
        # ── SOURCE-DERIVED CALIBRATION VALUES ──────────────────────────────────
        # These financing costs are DERIVED OUTPUTS from the Oborovo workbook
        # construction-funding model (reviewed 2026-07-22). They are carried here
        # as calibration inputs ONLY pending the generic monthly Construction/IDC
        # runtime (Stage B2). They must NOT be treated as permanent primary inputs,
        # hardcoded engine constants, or generic defaults for other projects.
        #
        # Future: ConstructionFinancingEngine → capitalized_financing_costs →
        # → BookDepreciableAssetBasis (automatically computed from rates/schedules).
        idc_keur=0.0,
        commitment_fees_keur=0.0,
        bank_fees_keur=0.0,
        # vat_costs_keur = VAT-facility FINANCING COSTS only (not construction VAT 7,665 kEUR)
        # = vat_facility_idc_keur (208.448) + vat_facility_commitment_fee_keur (13.622) = 222.070
        vat_costs_keur=0.0,
        vat_facility_idc_keur=0.0,
        vat_facility_commitment_fee_keur=0.0,
        reserve_accounts_keur=0.0,
    )

    # OpEx from Excel CF sheet — verified per Sprint 11 brief
    # Target Y1 OpEx = 1,998 kEUR
    # Technical Management = 280 kEUR (not 703 — 703 included sub-items)
    # Infrastructure Maintenance = 427 kEUR (aggregated B.02 + sub-items)
    opex_items = (
        OpexItem(name="Technical Management", y1_amount_keur=198.0, annual_inflation=0.02),
        OpexItem(name="Infrastructure Maintenance", y1_amount_keur=244.0, annual_inflation=0.02,
                 step_changes=((2, 185.64),)),  # B.02.1 active Y1-2→B.02.2 active Y3+; Y2→185.64
        OpexItem(name="Maintain Site", y1_amount_keur=45.2, annual_inflation=0.02),   # B1: XLSM Inputs row 148 authoritative value
        OpexItem(name="Clean Material", y1_amount_keur=40.0, annual_inflation=0.02),
        OpexItem(name="Security", y1_amount_keur=30.1, annual_inflation=0.02),          # B1: XLSM Inputs row 150 authoritative value
        OpexItem(name="Insurance", y1_amount_keur=255.0, annual_inflation=0.02),
        OpexItem(name="Lease & Property Tax", y1_amount_keur=208.08, annual_inflation=0.02),
        OpexItem(name="Power Expenses", y1_amount_keur=176.8608, annual_inflation=0.0),  # B1: XLSM Inputs row 153 authoritative value (flat)
        OpexItem(name="Fees", y1_amount_keur=14.0, annual_inflation=0.0),  # Flat
        OpexItem(name="Audit&Accounting&Legal", y1_amount_keur=24.0, annual_inflation=0.02),
        OpexItem(name="Bank Fees", y1_amount_keur=20.0, annual_inflation=0.02),
        OpexItem(name="Environmental&Social", y1_amount_keur=32.0, annual_inflation=0.02,
                step_changes=((3, 12.4848),)),  # B.12.3/B.12.5 inactive Y3+ → step to 12.4848 (annual, inflation resumes)
        OpexItem(name="Contingencies", y1_amount_keur=51.489632, annual_inflation=0.02,
                percentage_of_opex=0.04),  # B1: XLSM Inputs row 158 authoritative value; 4% of non-contingency OPEX
        OpexItem(name="Taxes", y1_amount_keur=0.0, annual_inflation=0.0),
        OpexItem(name="Salary&Payroll", y1_amount_keur=0.0, annual_inflation=0.0),
    )

    info = ProjectInfo(
        name="Oborovo Solar PV",
        company="AKE Med",
        code="OBR-001",
        country_iso="HR",
        financial_close=date(2029, 6, 29),
        construction_months=12,
        cod_date=date(2030, 6, 29),
        horizon_years=30,
        period_frequency=PeriodFrequency.SEMESTRIAL,
        use_senior_debt_sizing_engine=True,  # Phase 23R: fixture-backed frozen senior DS opt-in after Phase 23Q parity proof
        period_axis_convention=(
            PeriodAxisConvention.OPERATING_BOUNDARY_SINGLE_CONSTRUCTION_COLUMN
        ),
    )

    technical = TechnicalParams(
        capacity_mw=75.26,
        yield_scenario="P_50",
        operating_hours_p50=1494.0,
        operating_hours_p90_10y=1410.0,
        pv_degradation=0.004,
        bess_degradation=0.003,
        plant_availability=0.99,
        grid_availability=0.99,
        bess_enabled=False,
    )

    # Stage C2B — source-correct calendar-year merchant price schedule.
    # Workbook: d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm
    # SHA-256:  15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920
    #
    # Excel formula chain (CF row 30 → Inputs row 106):
    #   CF!G30 = INDEX(Inputs!$D$106:$AH$106, 1, MATCH(YEAR(G3), Inputs!$D$96:$AH$96))
    #   Inputs row 107 = row108 * 1.085  (Central case Trackers = GMPV * 8.5% uplift)
    #   Inputs row 108 = AFRY Q1 2026 4h Degraded GMPV Central (hardcoded)
    #   Inputs row 116 = calendar-year inflation index (CY2030=1.10, rising to CY2060=1.99)
    #   Inputs row 106 = row107 * row116  (selected-scenario nominal prices, CY-indexed)
    #
    # Exact cached values from Inputs row 106 (data_only=True extraction, CY2042–CY2060):
    _merchant_prices_cy2042_cy2060 = (
        75.12095149999999,   # CY2042
        75.83325399999998,   # CY2043
        76.03517249999999,   # CY2044
        74.10767,            # CY2045
        75.790071,           # CY2046
        77.47963299999999,   # CY2047
        79.1593215,          # CY2048
        80.86288,            # CY2049
        82.57359949999999,   # CY2050
        84.78114049999999,   # CY2051
        86.50704999999999,   # CY2052
        88.22135,            # CY2053
        90.4723995,          # CY2054
        92.20113,            # CY2055
        93.63116,            # CY2056
        95.01388399999999,   # CY2057
        95.8876345,          # CY2058
        97.2187125,          # CY2059
        98.543606,           # CY2060
    )

    # C3B3D2B7 bank/debt-sizing source-compatible merchant case.
    # Source chain: Scenarios!E325 selects Central Low case Trackers; Inputs!D111
    # is the raw Central Low curve; Inputs!D116 applies the calendar-year
    # inflation index. Effective bank price = D111_raw * D116[year].
    # These are source INPUT curve values, not solver output vectors.
    _bank_effective_central_low_cy2042_cy2060 = (
        61.313838249999996,  # CY2042
        61.3429705,          # CY2043
        61.0421,             # CY2044
        58.29127237499999,   # CY2045
        59.7844596825,       # CY2046
        61.305710245920004,  # CY2047
        62.86389704800379,   # CY2048
        64.45988903807259,   # CY2049
        66.10343382405546,   # CY2050
        66.97371006887926,   # CY2051
        67.8615725555722,    # CY2052
        68.74875916078739,   # CY2053
        69.65387751604523,   # CY2054
        70.55792040869567,   # CY2055
        71.4203819309633,    # CY2056
        72.28911874595818,   # CY2057
        73.16403688078046,   # CY2058
        74.04503609349726,   # CY2059
        74.9320096599704,    # CY2060
    )

    revenue = RevenueParams(
        ppa_base_tariff=57.0,
        ppa_term_years=12,
        ppa_index=0.02,
        ppa_production_share=1.0,
        market_scenario="Central",
        # Legacy operating-year curve left empty; calendar-year schedule is authoritative.
        market_prices_curve=(),
        market_inflation=0.02,
        # CF row 40: = -Inputs!D114 * Spot_Sales_kEUR; D114 = 0.025
        # Applied to gross merchant/spot electricity revenue only (zero during PPA).
        balancing_cost_pv=0.025,
        balancing_cost_bess=0.025,
        # CF row 46: = CO2_price * total_production_MWh / 1000; CO2_price = 1.5 EUR/MWh (constant)
        # CF row 47: HLOOKUP on Inputs E140:AH141; all values = 1.5 for periods 1-30.
        co2_enabled=True,
        co2_price_eur=1.5,
        co2_certificate_price_eur_per_mwh=1.5,
        balancing_cost_eur_per_mwh=0.0,
        # Stage C2B: calendar-year price schedule (Inputs row 106, CY2042–CY2060).
        market_price_calendar_start_year=2042,
        market_prices_by_calendar_year_eur_mwh=_merchant_prices_cy2042_cy2060,
        # Authoritative Excel calendar-year indexation: 2031 = base year, first escalation 2032.
        ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE",
    )

    # --- C3B3A: canonical all-in annual rates from DS!row44 (P1..P28 → debt periods 2..29) ---
    # Source: excel_oborovo_debt_interest_truth.json workstream_e.ds_row44_annual_sculpting_rate
    # Formula: base_rate(t) + credit_spread(t) + hedge_cost(t), fully source-proven.
    _OBR_ANNUAL_RATES = (
        0.0595136,        # P1  (clean period 2)
        0.0595136,        # P2  (clean period 3)
        0.05838319999,    # P3  (clean period 4)
        0.05838319999,    # P4  (clean period 5)
        0.05793919999,    # P5  (clean period 6)
        0.05793919999,    # P6  (clean period 7)
        0.0578408,        # P7  (clean period 8)
        0.0578408,        # P8  (clean period 9)
        0.0579008,        # P9  (clean period 10)
        0.0579008,        # P10 (clean period 11)
        0.05803279999,    # P11 (clean period 12)
        0.05803279999,    # P12 (clean period 13)
        0.0581936,        # P13 (clean period 14)
        0.0581936,        # P14 (clean period 15)
        0.05834,          # P15 (clean period 16)
        0.05834,          # P16 (clean period 17)
        0.0584624,        # P17 (clean period 18)
        0.0584624,        # P18 (clean period 19)
        0.05856559999,    # P19 (clean period 20)
        0.05856559999,    # P20 (clean period 21)
        0.058628,         # P21 (clean period 22)
        0.058628,         # P22 (clean period 23)
        0.0586208,        # P23 (clean period 24)
        0.0586208,        # P24 (clean period 25)
        0.0585488,        # P25 (clean period 26)
        0.0585488,        # P26 (clean period 27)
        0.05840719999,    # P27 (clean period 28)
        0.05840719999,    # P28 (clean period 29)
    )
    # --- DSCR target schedule: 1.15x for P1..P24, 1.35x for P25..P28 ---
    # Source: DS!row22 (workstream_a.ds_row22_dscr_target)
    _OBR_DSCR_SCHEDULE = (1.15,) * 24 + (1.35,) * 4

    # --- Debt-service availability: EXPLICIT_INPUT (classified C3B3A) ---
    # DS!row9 ops_flag for P28 = 179/181 = 0.988950276243094 (partial final period).
    # NOT derivable from COD + relativedelta(years=14) which yields 1.0.
    # Source: excel_oborovo_debt_interest_truth.json workstream_b.period_vectors.row9_ops_flag
    _OBR_AVAIL_SCHEDULE = (1.0,) * 27 + (0.988950276243094,)

    # Reviewer-confirmed source input facts; no derived workbook series is consumed.
    _construction_dates = (
        (date(2029, 6, 29), date(2029, 6, 30)),
        (date(2029, 7, 1), date(2029, 7, 31)),
        (date(2029, 8, 1), date(2029, 8, 31)),
        (date(2029, 9, 1), date(2029, 9, 30)),
        (date(2029, 10, 1), date(2029, 10, 31)),
        (date(2029, 11, 1), date(2029, 11, 30)),
        (date(2029, 12, 1), date(2029, 12, 31)),
        (date(2030, 1, 1), date(2030, 1, 31)),
        (date(2030, 2, 1), date(2030, 2, 28)),
        (date(2030, 3, 1), date(2030, 3, 31)),
        (date(2030, 4, 1), date(2030, 4, 30)),
        (date(2030, 5, 1), date(2030, 5, 31)),
    )
    _construction_periods = tuple(
        ConstructionPeriodSpec(
            start_date=start,
            end_date=end,
            active_construction=True,
            capex_payment_eligible=True,
            senior_idc_active=index < 11,
            vat_facility_active=True,
        )
        for index, (start, end) in enumerate(_construction_dates)
    )
    _vat_tail_dates = (
        (date(2030, 6, 1), date(2030, 6, 30)),
        (date(2030, 7, 1), date(2030, 7, 31)),
        (date(2030, 8, 1), date(2030, 8, 31)),
        (date(2030, 9, 1), date(2030, 9, 30)),
        (date(2030, 10, 1), date(2030, 10, 31)),
        (date(2030, 11, 1), date(2030, 11, 30)),
    )
    _vat_periods = _construction_periods + tuple(
        ConstructionPeriodSpec(
            start_date=start,
            end_date=end,
            active_construction=False,
            capex_payment_eligible=False,
            senior_idc_active=False,
            vat_facility_active=True,
        )
        for start, end in _vat_tail_dates
    )
    _equal = (1 / 12,) * 12
    _m1 = (1.0,) + (0.0,) * 11
    _p10 = (0.0,) * 9 + (1.0,) + (0.0,) * 2
    _p12 = (0.0,) * 11 + (1.0,)
    _capex_timing = (
        ConstructionCapexTimingInput("production_units", "Production Units", _equal, 0.0,
                                     vat_classification="AGGREGATE_RECONCILIATION_INFERENCE"),
        ConstructionCapexTimingInput("epc_contract", "EPC Contract", _equal, 0.17),
        ConstructionCapexTimingInput("epc_other", "EPC Other Costs", _equal, 0.17),
        ConstructionCapexTimingInput("grid_connection", "Grid Connection", _equal, 0.17),
        ConstructionCapexTimingInput("ops_prep", "Investments to Prepare Operation Phase", _equal, 0.17),
        ConstructionCapexTimingInput("audit_legal", "Audit Accounting and Legal Fees", _equal, 0.17),
        ConstructionCapexTimingInput("insurances", "Insurances", _m1, 0.17),
        ConstructionCapexTimingInput("lease_tax", "Project Finance Costs at Closing", _m1, 0.17),
        ConstructionCapexTimingInput("construction_mgmt_a", "Construction Management", _m1, 0.17),
        ConstructionCapexTimingInput("contingencies", "Contingencies", _m1, 0.17),
        ConstructionCapexTimingInput("project_rights", "Project Rights", _m1, 0.17),
        ConstructionCapexTimingInput("commissioning", "Commissioning", _p10, 0.17),
        ConstructionCapexTimingInput("project_acquisition", "Project Acquisition and Development", _p12, 0.17),
    )
    _construction_financing = ConstructionFinancingInput(
        enabled=True,
        periods=_construction_periods,
        capex_items=_capex_timing,
        senior_pricing=ConstructionSeniorPricingInput(
            mode=SeniorRateMode.HEDGE_BLEND,
            fixed_base_rate=0.03,
            margin_rate=0.0265,
            hedge_pct=0.80,
            swap_margin=0.0020,
            floating_curve_buffer_pct=0.20,
            floating_base_rate_curve=(
                0.02996, 0.02930, 0.02865, 0.02806, 0.02750, 0.02700,
                0.02654, 0.02612, 0.02575, 0.02542, 0.02512, 0.02512,
            ),
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        commitment_fee=ConstructionCommitmentFeeInput(
            rate=0.0105,
            balance_basis="CLOSING_UNDRAWN",
            capitalization_timing="NEXT_PERIOD",
        ),
        structuring_fee=ConstructionStructuringFeeInput(
            rate=0.01,
            basis_keur=47_730.2687,
            payment_weights=_m1,
        ),
        vat_facility=ConstructionVatFacilityInput(
            enabled=True,
            commitment_mode=VatFacilityCommitmentMode.DERIVED_PEAK_REQUIREMENT,
            interest_rate=0.0565,
            commitment_fee_rate=0.009275,
            periods=_vat_periods,
            day_count=SeniorDayCountConvention.ACT_360,
            reimbursement_lag_periods=6,
            commitment_fee_active_periods=12,
            financing_cost_payment_weights=(0.25,) + (0.15,) * 5 + (0.0,) * 6,
        ),
        shl_accrual_tail_periods=(
            ConstructionPeriodSpec(
                start_date=date(2030, 6, 1),
                end_date=date(2030, 6, 28),
                active_construction=False,
                capex_payment_eligible=False,
                senior_idc_active=False,
                vat_facility_active=False,
            ),
        ),
        idc_balance_basis="CLOSING_DRAWN",
        idc_capitalization_timing="NEXT_PERIOD",
        convergence_tolerance_keur=1e-9,
        max_iterations=200,
        vat_deferred=False,
    )

    financing = FinancingParams(
        share_capital_keur=500.0,
        share_premium_keur=0.0,
        shl_amount_keur=13547.2,  # C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN / KNOWN_SOURCE_CONFLICT. Excel Inputs!D325=14620.77 kEUR. PR #309 (34ed6d0b) corrected to 14621; PR #752 (099e4a14) reverted to 13547.2 to match oborovo_baseline.json parity. No runtime value change in D2A.
        shl_rate=0.08,  # Oborovo: 8% SHL rate (different from TUHO 5.95%)
        gearing_ratio=0.7524,  # Excel: 75.24%
        senior_tenor_years=14,
        base_rate=0.03,  # Excel: 3.0%
        margin_bps=265,
        floating_share=0.2,
        fixed_share=0.8,
        hedge_coverage=0.8,
        commitment_fee=0.0105,
        arrangement_fee=0.0,
        structuring_fee=0.01,
        target_dscr=1.15,
        lockup_dscr=1.10,
        min_llcr=1.15,  # Oborovo source: Inputs!D224 = Inputs!C177 = 1.15
        dsra_months=0,  # P.4: Source Inputs!I347=0 (construction) and Inputs!I348=0 (operation) — DSRA absent in source workbook. Zero target, zero balance; eligible_dsra=ELIGIBLE preserved per O.1.
        equity_irr_method="shl_plus_dividends",  # Stack O: Golden Excel equity IRR = SHL interest while SHL outstanding + dividends after; "combined" (capex-debt base, distributions only) gave 6.24% vs golden 10.60%
        debt_sizing_method="gearing_cap",  # legacy field; clean solver uses debt_sizing_mode
        debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,  # C3B3A: clean DSCR-sculpted solver path
        fixed_debt_keur=42852.26672602787,  # Excel senior debt anchor, Outputs!H11 (legacy; clean solver derives this as output)
        shl_idc_keur=0.0,
        shl_tenor_years=20,  # Legacy Python field. Source SHL clears at 2050-06-30 (Excel DS[40]). Source repayment is incremental FCF sweep (DS[25..40]), NOT a contractual bullet. No runtime value change in D2A.
        clean_shl_principal_keur=14620.773894815633,  # C3B3D2B5.2 clean SHL authority: Excel Inputs!D325, separate from legacy baseline-calibrated shl_amount_keur.
        clean_shl_repayment_method=SHLRepaymentMethod.CASH_SWEEP,  # Partial cash/PIK is the natural waterfall outcome; DS25 separately controls principal eligibility.
        shl_day_count_convention="ACT_365_FIXED",  # Source-proven inclusive ACT/365 Fixed operating SHL convention.
        shl_construction_day_count_fraction=1.0,  # Explicit source input; not backsolved from shl_idc_keur.
        shl_principal_eligibility_start_period=25,  # Source DS25 is the first principal repayment period.
        shl_maturity_period_index=40,  # Source DS40 clears the clean SHL balance.
        use_frozen_excel_senior_debt_schedule=False,
        frozen_senior_ds_fixture_path=None,
        sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
        construction_financing=_construction_financing,
        senior_debt_interest_config=SeniorDebtInterestConfig(
            enabled=True,
            rate_schedule=SeniorRateSchedule(
                mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
                explicit_all_in_rates=_OBR_ANNUAL_RATES,
            ),
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        senior_sculpting_config=SeniorSculptingConfig(
            enabled=True,
            target_dscr_schedule=_OBR_DSCR_SCHEDULE,
            debt_service_availability_schedule=_OBR_AVAIL_SCHEDULE,
        ),
        debt_sizing_case=DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P50,
            merchant_price_calendar_start_year=2042,
            merchant_prices_by_calendar_year_eur_mwh=_bank_effective_central_low_cy2042_cy2060,
            tax_periodisation_mode_override=TaxPeriodisationMode.WORKBOOK_MODEL_YEAR_PAIRING,
            source_label=(
                "Oborovo source compatibility: CF bank sizing uses P50 production "
                "plus effective Central Low case Trackers and workbook paired-period CIT timing"
            ),
        ),
    )

    tax = TaxParams(
        corporate_rate=0.10,
        loss_carryforward_years=5,
        loss_carryforward_cap=1.0,
        legal_reserve_cap=0.10,
        thin_cap_enabled=False,
        # C3B3D0: atad_enabled is independent of thin_cap_enabled. Explicit False.
        # Source workbook evidence (C3B1): BS!G45=thin_cap_enabled=False gates ATAD=False
        # for Oborovo. The field is now explicit rather than derived. The legacy waterfall
        # engine applies atad_applies=True with min_threshold=3000kEUR (never binds for
        # Oborovo's senior interest levels), so financial outputs are unaffected.
        atad_enabled=False,
        atad_ebitda_limit=0.30,
        atad_min_interest_keur=3000.0,
        wht_sponsor_dividends=0.05,
        wht_sponsor_shl_interest=0.0,
        shl_cap_applies=True,
        # Oborovo source workbook P&L: no depreciation add-back in Fiscal Reintegration.
        # 100% of book depreciation is tax-deductible for this project.
        # C3B1 fixture proves: excel_tax_dep == excel_book_dep for all 28 debt periods.
        # → book_depreciable_capex_items() (hard capex + financial costs) is the correct
        #   tax depreciation asset basis. tax_dep_basis_source_owned explicitly opts in.
        tax_depreciation_mode=TaxDepreciationMode.BOOK_BASED_PERCENTAGE,
        tax_deductible_book_dep_pct=1.0,
        tax_dep_basis_source_owned=True,
        # C3B1 evidence: cash-tax payment lag relative to source CIT = 0 periods.
        # TAX_YEAR_LAST_PERIOD is the clean engine's convention; the workbook uses
        # H2+H1 pairing — these are structurally different (WORKBOOK_PERIODISATION_MISMATCH).
        # This flag enables the clean convention for Oborovo; it does NOT assert
        # that TAX_YEAR_LAST_PERIOD itself matches the workbook periodisation.
        clean_cash_tax_timing_enabled=True,
        # C3B3C: Oborovo source facts (Section 2C, 2E, 2F, 2G)
        # - foreign SHL cap = TRUE → SHL interest 100% non-deductible for CIT
        # - thin cap = FALSE (no thin-cap formula for Oborovo)
        # - loss utilisation gate = EBT_POSITIVE (workbook uses EBT>0, not TI>0)
        # - tax periodisation = CALENDAR_TAX_YEAR
        # - SHL construction: EXPENSE_TO_PNL + PIK_TO_SHL_BALANCE (not capitalized)
        shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        foreign_shl_interest_cap_enabled=True,
        tax_loss_utilisation_gate=TaxLossUtilisationGate.EBT_POSITIVE,
        tax_periodisation_mode=TaxPeriodisationMode.CALENDAR_TAX_YEAR,
        shl_construction_accounting=ShlAccountingTreatment.EXPENSE_TO_PNL,
        shl_construction_payment=ShlPaymentMethod.PIK_TO_SHL_BALANCE,
    )

    # U2 DELIVERED (Oborovo): Rate=0.01 SOURCE_PROVEN via P&L!B19 =Inputs!$D$455.
    # DSRA (CF rows 91, 105) ELIGIBLE per P&L!G19. Opening UC typed authority.
    # UC causally derived via canonical distribution-accounting roll-forward (U2 fixed-point).
    # Parity exception: OBOROVO_SOURCE_RE_LINEAGE_PARITY_BLOCKED_BY_DISTRIBUTION_CASH_TAX_TIMING_ARCHITECTURE
    # (source distributes EBITDA−bank_cash_tax; clean uses actual corporate-cash-tax timing).
    return ProjectInputs(
        info=info,
        technical=technical,
        capex=capex,
        opex=opex_items,
        revenue=revenue,
        financing=financing,
        tax=tax,
        hierarchical_opex_capability=build_oborovo_opex_capability(),
        accounting_policy_config=_OBOROVO_ACCOUNTING_POLICY,
        cash_reserve_interest_policy=_OBOROVO_CASH_INTEREST_POLICY,
        distribution_accounting_policy=DistributionAccountingPolicy(
            enabled=True,
            authority=DistributionAccountingAuthority.SOURCE_PROVEN,
            dividend_wht_rate=0.05,
            legal_reserve_cap_fraction=0.10,
            # Q.8: Project-level opening UC authority (greenfield axiom O.9)
            opening_uc_authority=OpeningUCAuthority.CAUSALLY_DERIVED_ZERO,
        ),
    )


def create_default_oborovo_legacy_calibration() -> ProjectInputs:
    """Return the explicit historical Oborovo calibration overlay.

    Economic inputs are inherited from the canonical factory. Only the frozen
    legacy authorities needed by the explicit calibration route are restored here.
    """
    clean = create_default_oborovo()
    legacy_capex = replace(
        clean.capex,
        idc_keur=1086.032,
        commitment_fees_keur=188.563,
        bank_fees_keur=477.303,
        vat_costs_keur=222.070,
        vat_facility_idc_keur=208.448,
        vat_facility_commitment_fee_keur=13.622,
    )
    legacy_financing = replace(
        clean.financing,
        sponsor_funding_mode=None,
        gearing_basis_mode=None,
        construction_financing=None,
        shl_idc_keur=1169.0,
        use_frozen_excel_senior_debt_schedule=True,
        frozen_senior_ds_fixture_path=(
            "reports/phase23q_oborovo_senior_debt_sizing_extraction.csv"
        ),
    )
    return replace(clean, capex=legacy_capex, financing=legacy_financing)



# =============================================================================
# TUHO Wind 1 (35 MW, Croatia, 30-year horizon)
# =============================================================================

def _create_default_tuho_wind1_legacy_base() -> ProjectInputs:
    """Create default TUHO Wind 1 project inputs matching Excel.

    TUHO Wind 1 — 35 MW wind farm.
    Financial Close: 2028-06-30, COD: 2029-12-30 (18 months construction).

    Source: 20260330_TUHO_BP_2.xlsm (Excel reference model)
    Key outputs: Debt 43,359 kEUR, IRR 9.47%, DSCR avg 1.45x, CIT = 0 entire tenor.

    Verified from Excel:
    - CFADS Y1 = 5,121 kEUR (H1: 2,540 + H2: 2,582)
    - DSCR Y1-H1 = 1.200x (2,540 / 2,116 = exactly target)
    - CIT row 67 = 0 for all periods (large construction-period carryforward)
    - Hard CapEx = 70,691.54 kEUR, Total CapEx = 72,993.71 kEUR
    """
    from datetime import date

    # CapEx items from Excel CapEx sheet (hard capex = 70,691.54 kEUR)
    # Total CapEx = 72,993.71 kEUR (hard + IDC 1,519.56 + bank fees 782.61)
    capex = CapexStructure(
        epc_contract=CapexItem(
            name="EPC Wind Turbines",
            amount_keur=52_800.0,  # 35 MW × 1,000 EUR/kW × 1.5 (markup)
            y0_share=0.4,
            spending_profile=(0.6,),
        ),
        production_units=CapexItem(name="Grid & Telecom", amount_keur=0.0, y0_share=0.0),
        epc_other=CapexItem(
            name="Development & Permitting",
            amount_keur=2_100.0,
            y0_share=1.0,
        ),
        grid_connection=CapexItem(
            name="Grid Connection",
            amount_keur=6_200.0,  # Grid connection + monitoring
            y0_share=0.5,
            spending_profile=(0.5,),
        ),
        ops_prep=CapexItem(
            name="Construction Management",
            amount_keur=1_200.0,
            y0_share=0.5,
            spending_profile=(0.5,),
        ),
        insurances=CapexItem(name="Insurances", amount_keur=0.0, y0_share=0.0),
        lease_tax=CapexItem(name="Land & Property", amount_keur=0.0, y0_share=0.0),
        construction_mgmt_a=CapexItem(
            name="Civil Works",
            amount_keur=5_400.0,
            y0_share=0.6,
            spending_profile=(0.4,),
        ),
        commissioning=CapexItem(name="Commissioning", amount_keur=0.0, y0_share=0.0),
        audit_legal=CapexItem(name="Audit & Legal", amount_keur=0.0, y0_share=0.0),
        construction_mgmt_b=CapexItem(name="Other Construction", amount_keur=0.0, y0_share=0.0),
        contingencies=CapexItem(
            name="Contingencies",
            amount_keur=2_991.54,
            y0_share=0.5,
            spending_profile=(0.5,),
        ),
        taxes=CapexItem(name="Import Taxes", amount_keur=0.0, y0_share=0.0),
        project_acquisition=CapexItem(name="Project Rights", amount_keur=0.0, y0_share=0.0),
        project_rights=CapexItem(name="Project Rights", amount_keur=0.0, y0_share=0.0),
        # Financing costs (separate from hard CapEx)
        idc_keur=1_519.56,  # Interest During Construction from Excel
        commitment_fees_keur=0.0,  # Included in bank_fees_keur
        bank_fees_keur=782.61,  # Bank fees (all-in, incl. commitment fees)
        vat_costs_keur=0.0,
        reserve_accounts_keur=0.0,
    )

    # OpEx from Excel OpEx sheet Y1 = 1,998 kEUR (H1: 991 + H2: 1,007)
    opex_items = (
        OpexItem(name="Technical Management", y1_amount_keur=279.99, annual_inflation=0.02),
        OpexItem(name="O&M Preventive & Corrective", y1_amount_keur=426.60, annual_inflation=0.02),
        OpexItem(name="Maintain Site", y1_amount_keur=68.00, annual_inflation=0.02),
        OpexItem(name="Clean Material", y1_amount_keur=5.00, annual_inflation=0.02),
        OpexItem(name="Security", y1_amount_keur=50.00, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=468.74, annual_inflation=0.02),
        OpexItem(name="Lease & Property Tax", y1_amount_keur=248.88, annual_inflation=0.02),
        OpexItem(name="Power Expenses", y1_amount_keur=93.72, annual_inflation=0.02),
        OpexItem(name="Audit & Accounting & Legal", y1_amount_keur=23.99, annual_inflation=0.02),
        OpexItem(name="Bank Fees (opex)", y1_amount_keur=20.00, annual_inflation=0.02),
        OpexItem(name="Environmental & Social Management", y1_amount_keur=200.00, annual_inflation=0.02),
        OpexItem(name="Contingencies", y1_amount_keur=113.09, annual_inflation=0.06),
    )

    info = ProjectInfo(
        name="TUHO Wind 1",
        company="Akuo Energy Med",
        code="TUHO-WIND-1",
        country_iso="HR",
        financial_close=date(2029, 7, 1),  # COD = 2030-01-01 (Y1-H1 starts Jan 1, 2030)
        construction_months=6,  # 6 months → COD = 2030-01-01
        cod_date=date(2030, 1, 1),
        horizon_years=30,
        period_frequency=PeriodFrequency.SEMESTRIAL,
        use_senior_debt_sizing_engine=True,  # Phase 23F: canonical SeniorDebtSizing path enabled
        use_tax_bridge_engine=True,  # Stack Z: tax depreciation runtime wiring
    )

    technical = TechnicalParams(
        capacity_mw=35.0,
        yield_scenario="P_50",
        operating_hours_p50=4164.0,  # From TUHO Excel: P50 yield = 145,740 MWh/yr ÷ 35 MW
        operating_hours_p90_10y=3620.0,
        pv_degradation=0.0,  # Wind: no degradation in Excel model
        plant_availability=1.0,  # Wind: operating hours already reflect realistic output
        grid_availability=1.0,   # Wind: no separate availability adjustment
        bess_enabled=False,
    )

    # Market price curve from TUHO Excel CF row 27.
    # Values are annual pairs in Excel; PPA-period entries are retained for
    # diagnostics but unused until the first merchant period, Y13-H1.
    market_prices = (
        94.5540, 100.9690, 102.6256, 104.5038, 105.6042,
        107.1357, 111.2716, 108.2148, 105.5754, 106.9539,
        107.5379, 108.6338, 109.3260, 109.5042, 110.8026,
        112.0560, 115.3512, 117.9612, 120.5820, 123.2293,
        125.8720, 128.5255, 131.7129, 134.1300, 136.5316,
        139.7415, 142.1460, 143.9984, 145.7752, 146.7453,
    )

    revenue = RevenueParams(
        ppa_base_tariff=60.0,  # Tariff Y1 = 60 EUR/MWh
        ppa_term_years=12.0,  # PPA expires at end of Y12-H2 (Dec 2041) — 12 years from COD Dec 2029
        ppa_index=0.02,
        ppa_production_share=1.0,
        market_scenario="Central",
        market_prices_curve=market_prices,
        market_inflation=0.015,  # 1.5%/year post-PPA spot escalation (brief: ~1.5%/yr)
        balancing_cost_pv=0.0,  # Wind: no PV balancing
        balancing_cost_bess=0.0,
        co2_enabled=True,  # TUHO has CO2 certificate revenue
        # Phase 7: explicit EUR/MWh inputs for revenue split display
        # Balancing: TUHO Excel CF row 30 = 8.0 EUR/MWh (constant across all periods)
        # Source: RevenueAdjustmentSchedule(constant_value=8.0) — same value as flat input
        balancing_cost_eur_per_mwh=8.0,
        balancing_cost_schedule=RevenueAdjustmentSchedule(constant_value=8.0),
        first_merchant_operating_period_index=24,
        # CO2: TUHO Excel CF row 31 starts at 4.191 EUR/MWh (Y1-H1/Y1-H2)
        # Source: TUHO Excel CF sheet row 31 semiannual values starting 4.191063312
        co2_certificate_price_eur_per_mwh=4.191063312,  # flat default; schedule overrides
        co2_sales_schedule=RevenueAdjustmentSchedule(semiannual_values=(
            4.191063312, 4.191063312, 3.783032455, 3.783032455,
            3.375001599, 3.375001599, 2.966970742, 2.966970742,
            2.45, 2.45, 2.35, 2.35, 2.2, 2.2, 2.1, 2.1,
            2.05, 2.05, 1.95, 1.95, 1.8, 1.8, 1.7, 1.7,
            1.6, 1.6, 1.5, 1.5, 1.4, 1.4, 1.3, 1.3,
            1.2, 1.2, 1.15, 1.15, 1.05, 1.05, 1.0, 1.0,
            0.95, 0.95, 0.9, 0.9, 0.85, 0.85, 0.8, 0.8,
            0.8, 0.8, 0.8, 0.8, 0.75, 0.75, 0.75, 0.75,
            0.7, 0.7, 0.7, 0.7,
        )),
    )

    financing = FinancingParams(
        share_capital_keur=500.0,
        share_premium_keur=0.0,
        shl_amount_keur=29135.0,   # Shareholder Loan from Excel Inputs (39.91% of 72,994 kEUR)
        shl_rate=0.0793,   # 7.93% — per brief Sprint 22
        senior_tenor_years=14,
        base_rate=0.031,  # Fixed Base Rate from Excel R185 = 3.1%
        margin_bps=265,  # All-in = 5.75% = 3.1% + 2.65%
        floating_share=0.2,
        fixed_share=0.8,
        hedge_coverage=0.8,
        commitment_fee=0.01,
        arrangement_fee=0.0,
        structuring_fee=0.01,
        target_dscr=1.20,  # Target DSCR = 1.20 from Excel
        lockup_dscr=1.10,
        min_llcr=1.15,
        # TUHO Excel CF rows R75-R80 show zero DSRA target/funding/balance — no reserve account
        dsra_months=0,
        # TUHO Excel uses dual-DSCR sculpting:
        #  1.20 during PPA periods 1-24 through 31-Dec-2041,
        #  1.4125 during merchant periods 25-28.
        amortization_type="sculpted",
        fixed_ds_keur=0.0,
        debt_sizing_method="fixed",
        fixed_debt_keur=43359.0,
        dscr_schedule=[1.2] * 24 + [1.4125] * 4,
        equity_irr_method="shl_plus_dividends",  # TUHO: equity CF = SHL interest only (brief Sprint 13)
        shl_repayment_method="pik_then_sweep",  # TUHO: PIK phase Y1-Y14, sweep phase Y15+
        shl_idc_keur=3568.69,  # Construction IDC from Excel — opening SHL balance = 29,135 + 3,569 = 32,704
        use_senior_sweep_cash_cap_for_shl=False,  # TUHO: SHL cap DISABLED — PR B2 uses fcf_waterfall approach
        # PR-2 / P0-4: typed covenant gate policy — TUHO has R99/R102 applicable.
        covenant_gate_policy=CovenantGatePolicy.R99_R102_APPLICABLE,
        use_frozen_excel_senior_debt_schedule=True,  # Phase 23F: frozen senior DS schedule from fixture (CSV)
        frozen_senior_ds_fixture_path="reports/phase7_tuho_senior_debt_sizing_extraction.csv",  # Stack AC: capability-driven fixture path
        # Phase 23F: frozen Excel senior debt service schedule opt-in.
        # TUHO has frozen schedule data from Excel calibration (Macro!R50 / DS!R19).
        # Phase 23D/23E confirmed: no lock-up breach with fixture-backed frozen senior DS.
        # Phase 23F: enabling in factory — parity vs Excel validated by Phase 23E diagnostic.
        frozen_schedule_note="Macro!R50 / DS!R19 frozen per-period debt service (Excel calibration)",
    )

    tax = TaxParams(
        corporate_rate=0.18,  # TUHO > 7.5M EUR prihoda → 18%
        loss_carryforward_years=5,
        loss_carryforward_cap=1.0,
        prior_tax_loss_keur=25_000.0,  # 18m construction → large carryforward
        legal_reserve_cap=0.10,
        thin_cap_enabled=True,
        # C3B3D0: explicit TUHO source/calibration policy setting.
        # ATAD and thin-cap are independent. TUHO SUBJECT_TO_LIMITATIONS mechanics
        # remain source-unproven and fail-closed until the dedicated evidence stage.
        atad_enabled=True,
        atad_ebitda_limit=0.30,
        atad_min_interest_keur=3000.0,
        # L.1B: Source-proven via CF!B118 = 0.00% (TUHO workbook direct extraction).
        # Previous 0.05 was factory default; CF!B118 overrides — dividend WHT = 0%.
        wht_sponsor_dividends=0.00,
        wht_sponsor_shl_interest=0.0,  # 0% WHT on SHL interest per Excel R406
        shl_cap_applies=True,
        cit_cash_tax_start_operating_index=25,  # TUHO Excel: first non-zero R67 at P25
        # C3B3C: TUHO source facts (Section 2D, 2E, 2F, 2G)
        # - foreign SHL cap = FALSE (TUHO uses thin-cap formula, not 100% cap)
        # - thin cap = TRUE but formula unproven → SUBJECT_TO_LIMITATIONS fails closed
        # - loss utilisation gate = EBT_POSITIVE (workbook uses EBT>0, not TI>0)
        # - SHL construction: EXPENSE_TO_PNL + PIK_TO_SHL_BALANCE (not capitalized)
        # WARNING: SUBJECT_TO_LIMITATIONS raises NotImplementedError when called —
        # TUHO thin-cap formula is not yet implemented (C3B3C_BLOCKED_TUHO_THIN_CAP_FORMULA).
        shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
        foreign_shl_interest_cap_enabled=False,
        tax_loss_utilisation_gate=TaxLossUtilisationGate.EBT_POSITIVE,
        tax_periodisation_mode=TaxPeriodisationMode.CALENDAR_TAX_YEAR,
        shl_construction_accounting=ShlAccountingTreatment.EXPENSE_TO_PNL,
        shl_construction_payment=ShlPaymentMethod.PIK_TO_SHL_BALANCE,
    )

    # U2 DELIVERED (TUHO wind1 base): Rate=0.01 SOURCE_PROVEN via P&L!B19 =Inputs!$D$438.
    # DSRA (CF rows 81, 95) ELIGIBLE per P&L!G19. UC causally derived via U2 fixed-point.
    # Parity exception: TUHO_SOURCE_SHL_PARITY_BLOCKED_BY_CANONICAL_G2A_FINANCING_STACK_AUTHORITY
    # (canonical senior solver produces different SHL principal/PIK from source workbook).
    return ProjectInputs(
        info=info,
        technical=technical,
        capex=capex,
        opex=opex_items,
        revenue=revenue,
        financing=financing,
        tax=tax,
        cash_reserve_interest_policy=_SOURCE_PROVEN_CASH_INTEREST_POLICY,
    )


def create_default_tuho_wind1_legacy_calibration() -> ProjectInputs:
    """Return the historical TUHO fixture/calibration authority explicitly."""

    return _create_default_tuho_wind1_legacy_base()


def create_default_tuho_wind1() -> ProjectInputs:
    """Return TUHO with clean typed construction, financing, and tax authority."""

    legacy = _create_default_tuho_wind1_legacy_base()
    eq18 = (1.0 / 18.0,) * 18
    upfront18 = (1.0,) + (0.0,) * 17
    tuho_bank_mid_low_cy2029_cy2060 = (
        74.04, 75.79, 76.355, 76.39, 75.175, 74.755, 75.72, 72.735,
        71.215, 70.485, 69.36, 67.895, 67.3, 65.895, 63.825, 61.145,
        58.825, 58.97, 59.12, 59.27, 59.42, 59.565, 59.2, 58.84,
        58.48, 58.12, 57.755, 57.22, 56.68, 56.15, 55.61, 55.075,
    )
    tuho_market_inflation_index_cy2029_cy2060 = (
        1.08, 1.10, 1.12, 1.14, 1.17, 1.19, 1.21, 1.24,
        1.26, 1.29, 1.31, 1.34, 1.37, 1.39, 1.42, 1.45,
        1.48, 1.51, 1.54, 1.57, 1.60, 1.63, 1.67, 1.70,
        1.73, 1.77, 1.80, 1.84, 1.88, 1.91, 1.95, 1.99,
    )
    tuho_bank_effective_mid_low_cy2029_cy2060 = tuple(
        raw_price * inflation_index
        for raw_price, inflation_index in zip(
            tuho_bank_mid_low_cy2029_cy2060,
            tuho_market_inflation_index_cy2029_cy2060,
        )
    )
    def hard_capex(name: str, amount_keur: float) -> CapexItem:
        return CapexItem(
            name=name,
            amount_keur=amount_keur,
            useful_life_override=20,
        )

    capex = CapexStructure(
        production_units=hard_capex("Production Unit", 35_000.0),
        epc_contract=hard_capex("EPC Contract", 13_560.0),
        epc_other=hard_capex("Grid Connection", 30.0),
        grid_connection=hard_capex("Monitoring and Telecom", 100.0),
        ops_prep=hard_capex("Operation Investments", 1_000.0),
        insurances=hard_capex("Construction Insurances", 468.75),
        lease_tax=hard_capex("Taxable Land Securing", 500.0),
        commissioning=hard_capex("Non-taxable Land Securing", 12.4444444444445),
        construction_mgmt_a=hard_capex("Bank Due Diligence", 420.0),
        audit_legal=hard_capex("Construction Management A", 40.0),
        construction_mgmt_b=hard_capex("Audit Accounting and Legal", 42.0),
        contingencies=hard_capex("Construction Management B", 1_742.25),
        taxes=hard_capex("Contingencies", 3_036.945),
        project_acquisition=hard_capex("Project Rights", 14_739.15),
        project_rights=hard_capex("Unused", 0.0),
        idc_keur=0.0,
        commitment_fees_keur=0.0,
        bank_fees_keur=0.0,
        vat_costs_keur=0.0,
        vat_facility_idc_keur=0.0,
        vat_facility_commitment_fee_keur=0.0,
        reserve_accounts_keur=0.0,
    )

    construction_dates = (
        (date(2028, 6, 30), date(2028, 6, 30)),
        (date(2028, 7, 1), date(2028, 7, 31)),
        (date(2028, 8, 1), date(2028, 8, 31)),
        (date(2028, 9, 1), date(2028, 9, 30)),
        (date(2028, 10, 1), date(2028, 10, 31)),
        (date(2028, 11, 1), date(2028, 11, 30)),
        (date(2028, 12, 1), date(2028, 12, 31)),
        (date(2029, 1, 1), date(2029, 1, 31)),
        (date(2029, 2, 1), date(2029, 2, 28)),
        (date(2029, 3, 1), date(2029, 3, 31)),
        (date(2029, 4, 1), date(2029, 4, 30)),
        (date(2029, 5, 1), date(2029, 5, 31)),
        (date(2029, 6, 1), date(2029, 6, 30)),
        (date(2029, 7, 1), date(2029, 7, 31)),
        (date(2029, 8, 1), date(2029, 8, 31)),
        (date(2029, 9, 1), date(2029, 9, 30)),
        (date(2029, 10, 1), date(2029, 10, 31)),
        (date(2029, 11, 1), date(2029, 11, 30)),
    )
    construction_periods = tuple(
        ConstructionPeriodSpec(
            start_date=start,
            end_date=end,
            active_construction=True,
            capex_payment_eligible=True,
            senior_idc_active=True,
            vat_facility_active=True,
        )
        for start, end in construction_dates
    )
    vat_tail_dates = (
        (date(2029, 12, 1), date(2029, 12, 31)),
        (date(2030, 1, 1), date(2030, 1, 31)),
        (date(2030, 2, 1), date(2030, 2, 28)),
        (date(2030, 3, 1), date(2030, 3, 31)),
        (date(2030, 4, 1), date(2030, 4, 30)),
        (date(2030, 5, 1), date(2030, 5, 31)),
        (date(2030, 6, 1), date(2030, 6, 30)),
        (date(2030, 7, 1), date(2030, 7, 31)),
        (date(2030, 8, 1), date(2030, 8, 31)),
        (date(2030, 9, 1), date(2030, 9, 30)),
        (date(2030, 10, 1), date(2030, 10, 31)),
        (date(2030, 11, 1), date(2030, 11, 30)),
    )
    vat_periods = construction_periods + tuple(
        ConstructionPeriodSpec(
            start_date=start,
            end_date=end,
            active_construction=False,
            capex_payment_eligible=False,
            senior_idc_active=False,
            vat_facility_active=True,
        )
        for start, end in vat_tail_dates
    )
    capex_timing = (
        ConstructionCapexTimingInput("production_units", "Production Unit", eq18, 0.0),
        ConstructionCapexTimingInput("epc_contract", "EPC Contract", eq18, 0.13),
        ConstructionCapexTimingInput("epc_other", "Grid Connection", eq18, 0.13),
        ConstructionCapexTimingInput("grid_connection", "Monitoring and Telecom", eq18, 0.13),
        ConstructionCapexTimingInput("ops_prep", "Operation Investments", eq18, 0.13),
        ConstructionCapexTimingInput("insurances", "Construction Insurances", upfront18, 0.13),
        ConstructionCapexTimingInput("lease_tax", "Taxable Land Securing", upfront18, 0.13),
        ConstructionCapexTimingInput("commissioning", "Non-taxable Land Securing", upfront18, 0.0),
        ConstructionCapexTimingInput("construction_mgmt_a", "Bank Due Diligence", upfront18, 0.13),
        ConstructionCapexTimingInput("audit_legal", "Construction Management A", upfront18, 0.13),
        ConstructionCapexTimingInput("construction_mgmt_b", "Audit Accounting and Legal", eq18, 0.13),
        ConstructionCapexTimingInput("contingencies", "Construction Management B", upfront18, 0.13),
        ConstructionCapexTimingInput("taxes", "Contingencies", upfront18, 0.13),
        ConstructionCapexTimingInput("project_acquisition", "Project Rights", upfront18, 0.13),
    )
    construction = ConstructionFinancingInput(
        enabled=True,
        periods=construction_periods,
        capex_items=capex_timing,
        senior_pricing=ConstructionSeniorPricingInput(
            mode=SeniorRateMode.FIXED_PLUS_MARGIN,
            fixed_base_rate=0.033,
            margin_rate=0.0265,
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        commitment_fee=ConstructionCommitmentFeeInput(
            rate=0.005,
            balance_basis="CLOSING_UNDRAWN",
            capitalization_timing="NEXT_PERIOD",
        ),
        structuring_fee=ConstructionStructuringFeeInput(
            rate=0.01,
            basis_mode=(
                ConstructionStructuringFeeBasisMode.SENIOR_PLUS_VAT_COMMITMENTS
            ),
            payment_weights=upfront18,
        ),
        vat_facility=ConstructionVatFacilityInput(
            enabled=True,
            commitment_mode=VatFacilityCommitmentMode.DERIVED_PEAK_REQUIREMENT,
            interest_rate=0.0575,
            commitment_fee_rate=0.009275,
            periods=vat_periods,
            day_count=SeniorDayCountConvention.ACT_360,
            reimbursement_lag_periods=6,
            commitment_fee_active_periods=18,
            financing_cost_payment_weights=upfront18,
        ),
        shl_accrual_tail_periods=(
            ConstructionPeriodSpec(
                start_date=date(2029, 12, 1),
                end_date=date(2029, 12, 30),
                active_construction=False,
                capex_payment_eligible=False,
                senior_idc_active=False,
                vat_facility_active=False,
            ),
        ),
        idc_balance_basis="CLOSING_DRAWN",
        idc_capitalization_timing="NEXT_PERIOD",
        convergence_tolerance_keur=1e-9,
        max_iterations=200,
        vat_deferred=False,
    )

    info = replace(
        legacy.info,
        financial_close=date(2028, 6, 30),
        construction_months=18,
        cod_date=date(2029, 12, 30),
        period_axis_convention=(
            PeriodAxisConvention.OPERATING_BOUNDARY_SINGLE_CONSTRUCTION_COLUMN
        ),
        use_tax_bridge_engine=False,
    )
    financing = replace(
        legacy.financing,
        # TUHO source covenant: Inputs!D207 = Inputs!C160 = 1.20.
        # Threshold-only C2 authority; it does not drive Senior sizing/sculpting.
        min_llcr=1.20,
        shl_amount_keur=29_135.176217946093,
        shl_rate=0.08,
        gearing_ratio=0.80,
        base_rate=0.033,
        margin_bps=265,
        commitment_fee=0.005,
        structuring_fee=0.01,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value,
        debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,
        fixed_debt_keur=None,
        clean_shl_principal_keur=None,
        clean_shl_repayment_method=SHLRepaymentMethod.CASH_SWEEP,
        shl_day_count_convention="ACT_365_FIXED",
        shl_construction_day_count_fraction=548.0 / 365.0,
        shl_construction_day_count_convention=(
            ShlConstructionDayCountConvention.ELAPSED_ACT_365_FIXED
        ),
        shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
        sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
        shl_principal_eligibility_start_period=25,
        shl_maturity_period_index=36,
        use_frozen_excel_senior_debt_schedule=False,
        frozen_senior_ds_fixture_path=None,
        frozen_schedule_note=None,
        sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
        construction_financing=construction,
        senior_debt_interest_config=SeniorDebtInterestConfig(
            enabled=True,
            rate_schedule=SeniorRateSchedule(
                mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
                explicit_all_in_rates=(0.0595,) * 28,
            ),
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        senior_sculpting_config=SeniorSculptingConfig(
            enabled=True,
            target_dscr_schedule=(1.20,) * 24 + (1.4125,) * 4,
            debt_service_availability_schedule=(1.0,) * 27 + (0.9890710382513661,),
        ),
        debt_sizing_case=DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_price_calendar_start_year=2029,
            merchant_prices_by_calendar_year_eur_mwh=(
                tuho_bank_effective_mid_low_cy2029_cy2060
            ),
            source_label=(
                "TUHO source Bank Case P90-10y + Inputs!D109 MidLow x "
                "Inputs row 111 inflation index and typed DSCR schedule"
            ),
        ),
    )
    tax = replace(
        legacy.tax,
        country_tax_policy_id="HR-approved-source-model-2026-v1",
        corporate_rate_override=None,
        prior_tax_loss_keur=0.0,
        opening_tax_loss_vintages=(),
        thin_cap_enabled=False,
        atad_enabled=False,
        shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
        interest_limitation_policy=InterestLimitationPolicyParams(
            enabled=True,
            absolute_interest_limit_keur=3_000.0,
            ebitda_interest_limit_pct=0.30,
            capitalisation_gate_policy=CapitalisationGatePolicyParams(
                enabled=True,
                threshold=0.80,
                subtotal_is_reincluded_in_denominator=True,
            ),
            combination_mode=InterestLimitationCombinationMode.MAX_DISALLOWED,
            carryforward_mode=InterestLimitationCarryforwardMode.NONE,
            additional_non_deductible_share=0.0,
            source_model_convention="NO_RESTRICTED_INTEREST_CARRYFORWARD_IN_SOURCE_MODEL",
        ),
        cit_cash_tax_start_operating_index=None,
        clean_cash_tax_timing_enabled=True,
        # O.7/Q.1: ConstructionPLStatement absent — no source-proven construction PNL component.
        # The 48.268247 kEUR gap is NOT pre-operational OPEX; it is the SHL construction
        # interest mechanics gap: source SHL draw = 29135.176 kEUR (Excel IDC row 49),
        # clean draw = 28741.109 kEUR (PR-9 senior solver residual), Δ = −394.067 kEUR.
        # Same compound formula (P×((1.08)^(548/365)−1)) on different principal produces
        # PIK gap of −48.268 kEUR. Root cause: PR-9 DSCR-sculpting gives senior=43789.921
        # vs source senior=43359.274 (IDC!D48); residual SHL is smaller; no workbook cell
        # authorises a ConstructionPLStatement to close the gap.
        # Classification: TUHO_SOURCE_SHL_PARITY_BLOCKED_BY_CANONICAL_G2A_FINANCING_STACK_AUTHORITY.
        # Mechanism: construction SHL principal/PIK delta is the immediate numeric vehicle;
        # the canonical G2A financing-stack authority is the root cause.
    )
    # U2 DELIVERED (TUHO wind1 U2): Rate=0.01 SOURCE_PROVEN via P&L!B19 =Inputs!$D$438.
    # DSRA (CF rows 81, 95) ELIGIBLE per P&L!G19. Opening UC typed authority.
    # UC causally derived via canonical distribution-accounting roll-forward (U2 fixed-point).
    # Parity exception: TUHO_SOURCE_SHL_PARITY_BLOCKED_BY_CANONICAL_G2A_FINANCING_STACK_AUTHORITY.
    return replace(
        legacy,
        info=info,
        capex=capex,
        financing=financing,
        tax=tax,
        cash_reserve_interest_policy=_SOURCE_PROVEN_CASH_INTEREST_POLICY,
        distribution_accounting_policy=DistributionAccountingPolicy(
            enabled=True,
            authority=DistributionAccountingAuthority.SOURCE_PROVEN,
            dividend_wht_rate=0.0,
            legal_reserve_cap_fraction=0.10,
            # Q.8: Project-level opening UC authority (greenfield axiom O.9)
            opening_uc_authority=OpeningUCAuthority.CAUSALLY_DERIVED_ZERO,
        ),
        valuation=ValuationPolicies(
            project=ProjectValuationPolicy(
                annual_discount_rate=0.066,
                valuation_date_policy=(
                    ValuationDatePolicy.FIRST_PROJECT_CASHFLOW_DATE
                ),
                discount_convention=DiscountConvention.ACT_365_FIXED,
                authority_label=(
                    "TUHO_SOURCE_INPUTS_D452_PROJECT_NPV_RATE_AND_CF_C125_XNPV"
                ),
            ),
            coverage=DebtCoverageValuationPolicy(
                annual_discount_rate=0.0595,
                cfads_case=CoverageCfadsCase.BASE,
                calculation_date_policy=(
                    CoverageCalculationDatePolicy.FIRST_SENIOR_PERIOD_OPENING
                ),
                discount_convention=DiscountConvention.PERIODIC_COMPOUNDING,
                authority_label=(
                    "TUHO_SOURCE_CF_G129_PERIODIC_NPV_INPUTS_D184_BASE_FCFB_"
                    "SENIOR_OPENING_REFINANCING_DISABLED"
                ),
                llcr_cashflow_basis=(
                    CoverageCashflowBasis.SENIOR_ELIGIBLE_CFADS
                ),
                plcr_cashflow_basis=None,
                denominator_basis=(
                    CoverageDenominatorBasis.SENIOR_OPENING_BALANCE
                ),
                periodic_rate_conversion=(
                    PeriodicRateConversion.AS_QUOTED_PER_MODEL_PERIOD
                ),
                periods_per_year=2,
                first_cashflow_timing=(
                    PeriodicFirstCashflowTiming.END_OF_FIRST_PERIOD
                ),
            ),
        ),
        accounting_policy_config=_TUHO_ACCOUNTING_POLICY,
    )


# =============================================================================
# Generic industry engine factories — simple round numbers for tests/examples
# =============================================================================

def _generic_clean_senior_interest_config(
    *,
    annual_all_in_rate: float,
    tenor_years: int,
) -> SeniorDebtInterestConfig:
    """Explicit clean senior-rate contract for fictional generic projects."""
    return SeniorDebtInterestConfig(
        enabled=True,
        rate_schedule=SeniorRateSchedule(
            mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
            explicit_all_in_rates=(annual_all_in_rate,) * (tenor_years * 2),
        ),
        day_count=SeniorDayCountConvention.ACT_360,
    )


def create_default_solar_project(
    capacity_mw: float = 50.0,
    horizon_years: int = 20,
    construction_months: int = 12,
) -> ProjectInputs:
    """Test 1 — Solar: fictional utility-scale solar project for demos and tests.

    50 MW solar PV, EUR 50/MWh PPA, 20-year horizon. Entirely fictional —
    no real company, no real project, no Excel calibration data.
    """
    z = CapexItem(name="Unused", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)
    modules = CapexItem(name="Solar Modules", amount_keur=20_000.0, y0_share=0.0,
                        spending_profile=(0.5, 0.5), asset_class=AssetClass.SOLAR_PANELS)
    inverters = CapexItem(name="Inverters", amount_keur=3_000.0, y0_share=0.0,
                           spending_profile=(0.5, 0.5), asset_class=AssetClass.SOLAR_PANELS)
    civil = CapexItem(name="Civil Works", amount_keur=5_000.0, y0_share=0.3,
                      spending_profile=(0.4, 0.3), asset_class=AssetClass.CIVIL_GRID)
    grid = CapexItem(name="Grid Connection", amount_keur=2_000.0, y0_share=0.5,
                     spending_profile=(0.5,), asset_class=AssetClass.CIVIL_GRID)
    soft = CapexItem(name="Soft Costs", amount_keur=3_000.0, y0_share=1.0,
                     asset_class=AssetClass.SOFT_COSTS)

    capex = CapexStructure(
        epc_contract=modules, production_units=inverters,
        epc_other=civil, grid_connection=grid,
        ops_prep=z, insurances=z, lease_tax=z,
        construction_mgmt_a=z, commissioning=z,
        audit_legal=soft, construction_mgmt_b=z,
        contingencies=z, taxes=z,
        project_acquisition=z, project_rights=z,
        idc_keur=0.0, bank_fees_keur=0.0,  # S1-C: factory-direct must match resolver (which zeros via _zero_financial_capex_subfields)
    )
    opex = [
        OpexItem(name="Technical Management", y1_amount_keur=150.0, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=100.0, annual_inflation=0.02),
        OpexItem(name="Maintenance", y1_amount_keur=80.0, annual_inflation=0.02),
        OpexItem(name="Lease & Tax", y1_amount_keur=50.0, annual_inflation=0.02),
    ]
    info = ProjectInfo(name="Test 1 — Solar", company="Fictional Solar SpA", code="TEST-SOLAR-1",
        country_iso="DE", financial_close=date(2030, 1, 1),
        construction_months=construction_months, cod_date=date(2031, 1, 1),
        horizon_years=horizon_years, period_frequency=PeriodFrequency.SEMESTRIAL)
    technical = TechnicalParams(capacity_mw=capacity_mw, yield_scenario="P_50",
        operating_hours_p50=1500.0, operating_hours_p90_10y=1400.0,
        pv_degradation=0.004, bess_enabled=False)
    # Market price curve: Y1/Y2 explicit per the G1A reference spec, then 2%/yr
    # compounding from Y2 (matches market_inflation and the bootstrap Excel
    # reference workbook's Revenue-tab formula, =Y2*(1+esc)^(year-2)).
    solar_market_y1, solar_market_y2, solar_market_escalation = 60.0, 61.0, 0.02
    solar_market_curve = (solar_market_y1, solar_market_y2) + tuple(
        solar_market_y2 * (1 + solar_market_escalation) ** (i - 1) for i in range(2, 30)
    )
    # G1C: the G1A reference workbook has no PV-revenue-based balancing
    # deduction (only the flat EUR/MWh row, zero for Solar), so the domain
    # default balancing_cost_pv=0.025 must be zeroed here to match the spec.
    revenue = RevenueParams(ppa_base_tariff=50.0, ppa_term_years=10, ppa_index=0.02,
        market_scenario="Central", market_prices_curve=solar_market_curve,
        market_inflation=0.02, co2_enabled=False, balancing_cost_pv=0.0)
    # G1H compatibility fingerprint: 500 share capital + 7,750 SHL reconciles
    # the 25% sponsor share. G2A derives that SHL from Sources & Uses and does
    # not use either legacy SHL amount as its runtime funding authority.
    financing = FinancingParams(share_capital_keur=500.0, shl_amount_keur=7_750.0, shl_rate=0.08,
        gearing_ratio=0.75, senior_tenor_years=15, base_rate=0.03, margin_bps=250,
        floating_share=0.3, fixed_share=0.7, hedge_coverage=0.8,
        target_dscr=1.20, lockup_dscr=1.10, dsra_months=6,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value,
        debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,
        sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
        senior_debt_interest_config=_generic_clean_senior_interest_config(
            annual_all_in_rate=0.03 + 250 / 10000,
            tenor_years=15,
        ),
        clean_shl_principal_keur=7_750.0,  # compatibility assertion; G2A derives principal
        clean_shl_repayment_method=SHLRepaymentMethod.BULLET,
        shl_day_count_convention="PERIOD_AXIS_ACTUAL_YEAR",
        shl_construction_day_count_fraction=0.0,
    )
    tax = TaxParams(corporate_rate=0.25, loss_carryforward_years=5,
        loss_carryforward_cap=1.0, atad_ebitda_limit=0.30, atad_min_interest_keur=3000.0,
        clean_cash_tax_timing_enabled=True)

    return ProjectInputs(info=info, technical=technical, capex=capex,
        opex=tuple(opex), revenue=revenue, financing=financing, tax=tax,
        accounting_policy_config=_GENERIC_CLEAN_ACCOUNTING_POLICY)


def create_default_wind_project(
    capacity_mw: float = 40.0,
    horizon_years: int = 25,
    construction_months: int = 18,
) -> ProjectInputs:
    """Test 2 — Wind: fictional utility-scale wind project for demos and tests.

    40 MW onshore wind, EUR 60/MWh PPA, 25-year horizon. Entirely fictional —
    no real company, no real project, no Excel calibration data.
    """
    z = CapexItem(name="Unused", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)
    turbines = CapexItem(name="Wind Turbines", amount_keur=30_000.0, y0_share=0.4,
                         spending_profile=(0.6,), asset_class=AssetClass.WIND_TURBINES)
    civil = CapexItem(name="Civil Works", amount_keur=6_000.0, y0_share=0.3,
                      spending_profile=(0.4, 0.3), asset_class=AssetClass.CIVIL_GRID)
    grid = CapexItem(name="Grid Connection", amount_keur=3_000.0, y0_share=0.5,
                     spending_profile=(0.5,), asset_class=AssetClass.CIVIL_GRID)
    soft = CapexItem(name="Soft Costs", amount_keur=4_000.0, y0_share=1.0,
                     asset_class=AssetClass.SOFT_COSTS)

    capex = CapexStructure(
        epc_contract=turbines, production_units=z,
        epc_other=civil, grid_connection=grid,
        ops_prep=z, insurances=z, lease_tax=z,
        construction_mgmt_a=z, commissioning=z,
        audit_legal=soft, construction_mgmt_b=z,
        contingencies=z, taxes=z,
        project_acquisition=z, project_rights=z,
        idc_keur=0.0, bank_fees_keur=0.0,  # S1-C: factory-direct must match resolver (which zeros via _zero_financial_capex_subfields)
    )
    opex = [
        OpexItem(name="Technical Management", y1_amount_keur=200.0, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=150.0, annual_inflation=0.02),
        OpexItem(name="Maintenance", y1_amount_keur=120.0, annual_inflation=0.02),
        OpexItem(name="Lease & Tax", y1_amount_keur=80.0, annual_inflation=0.02),
    ]
    info = ProjectInfo(name="Test 2 — Wind", company="Fictional Wind GmbH", code="TEST-WIND-1",
        country_iso="DE", financial_close=date(2030, 1, 1),
        construction_months=construction_months, cod_date=date(2031, 7, 1),
        horizon_years=horizon_years, period_frequency=PeriodFrequency.SEMESTRIAL)
    technical = TechnicalParams(capacity_mw=capacity_mw, yield_scenario="P_50",
        operating_hours_p50=3000.0, operating_hours_p90_10y=2700.0,
        pv_degradation=0.0, bess_enabled=False)
    # Market price curve: Y1/Y2 explicit per the G1A reference spec, then 2%/yr
    # compounding from Y2 (matches market_inflation and the bootstrap Excel
    # reference workbook's Revenue-tab formula, =Y2*(1+esc)^(year-2)).
    wind_market_y1, wind_market_y2, wind_market_escalation = 65.0, 66.3, 0.02
    wind_market_curve = (wind_market_y1, wind_market_y2) + tuple(
        wind_market_y2 * (1 + wind_market_escalation) ** (i - 1) for i in range(2, 30)
    )
    # G1C: the G1A reference workbook has no PV-revenue-based balancing
    # deduction (only the flat 8 EUR/MWh row, already modeled via
    # balancing_cost_wind_eur_mwh below), so the domain default
    # balancing_cost_pv=0.025 must be zeroed here to match the spec.
    revenue = RevenueParams(ppa_base_tariff=60.0, ppa_term_years=12, ppa_index=0.02,
        market_scenario="Central", market_prices_curve=wind_market_curve,
        market_inflation=0.02, balancing_cost_wind_eur_mwh=8.0,
        co2_enabled=False, co2_price_eur=0.0, balancing_cost_pv=0.0)
    # G1H compatibility fingerprint: 500 share capital + 10,250 SHL reconciles
    # the 25% sponsor share. G2A derives that SHL from Sources & Uses and does
    # not use either legacy SHL amount as its runtime funding authority.
    financing = FinancingParams(share_capital_keur=500.0, shl_amount_keur=10_250.0, shl_rate=0.08,
        gearing_ratio=0.75, senior_tenor_years=15, base_rate=0.03, margin_bps=250,
        floating_share=0.3, fixed_share=0.7, hedge_coverage=0.8,
        target_dscr=1.20, lockup_dscr=1.10, dsra_months=6,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value,
        debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,
        sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
        senior_debt_interest_config=_generic_clean_senior_interest_config(
            annual_all_in_rate=0.03 + 250 / 10000,
            tenor_years=15,
        ),
        clean_shl_principal_keur=10_250.0,  # compatibility assertion; G2A derives principal
        clean_shl_repayment_method=SHLRepaymentMethod.BULLET,
        shl_day_count_convention="PERIOD_AXIS_ACTUAL_YEAR",
        shl_construction_day_count_fraction=0.0,
    )
    tax = TaxParams(corporate_rate=0.25, loss_carryforward_years=5,
        loss_carryforward_cap=1.0, atad_ebitda_limit=0.30, atad_min_interest_keur=3000.0,
        clean_cash_tax_timing_enabled=True)

    return ProjectInputs(info=info, technical=technical, capex=capex,
        opex=tuple(opex), revenue=revenue, financing=financing, tax=tax,
        accounting_policy_config=_GENERIC_CLEAN_ACCOUNTING_POLICY)


def create_default_bess_project(
    power_mw: float = 50.0,
    energy_mwh: float = 200.0,
    cycles_per_year: float = 300,
    horizon_years: int = 25,
    construction_months: int = 12,
) -> ProjectInputs:
    """Generic standalone BESS project — round numbers for tests/examples, not Excel calibration."""
    z = CapexItem(name="Unused", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)
    cells = CapexItem(name="BESS Cells", amount_keur=22_000.0, y0_share=0.0,
                      spending_profile=(0.5, 0.5), asset_class=AssetClass.BESS_CELLS)
    pe = CapexItem(name="Power Electronics", amount_keur=3_000.0, y0_share=0.0,
                   spending_profile=(0.5, 0.5), asset_class=AssetClass.BESS_POWER_ELECTRONICS)
    civil = CapexItem(name="Civil & Grid", amount_keur=2_000.0, y0_share=0.3,
                      spending_profile=(0.4, 0.3), asset_class=AssetClass.CIVIL_GRID)
    soft = CapexItem(name="Soft Costs", amount_keur=1_500.0, y0_share=1.0,
                     asset_class=AssetClass.SOFT_COSTS)

    capex = CapexStructure(
        epc_contract=cells, production_units=pe,
        epc_other=civil, grid_connection=z,
        ops_prep=z, insurances=z, lease_tax=z,
        construction_mgmt_a=z, commissioning=z,
        audit_legal=z, construction_mgmt_b=z,
        contingencies=z, taxes=z,
        project_acquisition=z, project_rights=z,
        idc_keur=0.0, bank_fees_keur=0.0,  # S1-C: factory-direct must match resolver (which zeros via _zero_financial_capex_subfields)
    )
    opex = [
        OpexItem(name="Technical Management", y1_amount_keur=150.0, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=100.0, annual_inflation=0.02),
        OpexItem(name="Maintenance", y1_amount_keur=80.0, annual_inflation=0.02),
        OpexItem(name="Lease & Tax", y1_amount_keur=50.0, annual_inflation=0.02),
    ]
    info = ProjectInfo(
        name="Generic BESS Project", company="BessCo", code="BESS-001",
        country_iso="DE", financial_close=date(2030, 1, 1),
        construction_months=construction_months, cod_date=date(2031, 1, 1),
        horizon_years=horizon_years, period_frequency=PeriodFrequency.SEMESTRIAL)
    bess_params = BessParams(
        power_mw=power_mw,
        energy_mwh=energy_mwh,
        cycles_per_year=cycles_per_year,
        round_trip_efficiency=0.88,
        availability=0.98,
        annual_degradation=0.02,
        arbitrage_spread_eur_mwh=40.0,
        ancillary_revenue_eur_mw_year=25000.0,
        capacity_revenue_eur_mw_year=0.0,
        augmentation_capex_keur=0.0,
    )
    technical = TechnicalParams(
        capacity_mw=power_mw, yield_scenario="P_50",
        operating_hours_p50=0.0, operating_hours_p90_10y=0.0,
        pv_degradation=0.0, bess_enabled=True, bess_degradation=0.02,
        bess=bess_params)
    revenue = RevenueParams(
        ppa_base_tariff=0.0, ppa_term_years=0, ppa_index=0.0,
        market_scenario="Central",
        market_prices_curve=tuple(60.0 + i for i in range(30)),
        market_inflation=0.02, co2_enabled=False)
    financing = FinancingParams(
        share_capital_keur=500.0, shl_amount_keur=5_000.0, shl_rate=0.08,
        gearing_ratio=0.75, senior_tenor_years=15, base_rate=0.03, margin_bps=250,
        floating_share=0.3, fixed_share=0.7, hedge_coverage=0.8,
        target_dscr=1.20, lockup_dscr=1.10, dsra_months=6,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value)
    tax = TaxParams(
        corporate_rate=0.25, loss_carryforward_years=5,
        loss_carryforward_cap=1.0, atad_ebitda_limit=0.30, atad_min_interest_keur=3000.0)

    return ProjectInputs(info=info, technical=technical, capex=capex,
        opex=tuple(opex), revenue=revenue, financing=financing, tax=tax)


def create_default_solar_bess_project(
    solar_capacity_mw: float = 50.0,
    bess_power_mw: float = 10.0,
    bess_energy_mwh: float = 20.0,
    bess_cycles_per_year: float = 365.0,
    horizon_years: int = 25,
    construction_months: int = 12,
) -> ProjectInputs:
    """Generic solar + BESS hybrid project."""
    z = CapexItem(name="Unused", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)
    modules = CapexItem(name="Solar Modules", amount_keur=20_000.0, y0_share=0.0,
                        spending_profile=(0.5, 0.5), asset_class=AssetClass.SOLAR_PANELS)
    inverters = CapexItem(name="Inverters", amount_keur=3_000.0, y0_share=0.0,
                           spending_profile=(0.5, 0.5), asset_class=AssetClass.SOLAR_PANELS)
    cells = CapexItem(name="BESS Cells", amount_keur=5_000.0, y0_share=0.0,
                      spending_profile=(0.5, 0.5), asset_class=AssetClass.BESS_CELLS)
    civil = CapexItem(name="Civil Works", amount_keur=3_000.0, y0_share=0.3,
                      spending_profile=(0.4, 0.3), asset_class=AssetClass.CIVIL_GRID)
    grid = CapexItem(name="Grid Connection", amount_keur=2_000.0, y0_share=0.5,
                     spending_profile=(0.5,), asset_class=AssetClass.CIVIL_GRID)
    capex = CapexStructure(
        epc_contract=modules, production_units=inverters,
        epc_other=civil, grid_connection=grid,
        ops_prep=z, insurances=z, lease_tax=z,
        construction_mgmt_a=z, commissioning=z,
        audit_legal=z, construction_mgmt_b=z,
        contingencies=z, taxes=z,
        project_acquisition=z, project_rights=z,
        idc_keur=0.0, bank_fees_keur=0.0,  # S1-C: factory-direct must match resolver (which zeros via _zero_financial_capex_subfields)
    )
    opex = [
        OpexItem(name="Technical Management", y1_amount_keur=150.0, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=100.0, annual_inflation=0.02),
        OpexItem(name="Maintenance", y1_amount_keur=80.0, annual_inflation=0.02),
        OpexItem(name="Lease & Tax", y1_amount_keur=50.0, annual_inflation=0.02),
    ]
    info = ProjectInfo(
        name="Generic Solar+BESS", company="SolarBessCo", code="SOLBESS-001",
        country_iso="DE", financial_close=date(2030, 1, 1),
        construction_months=construction_months, cod_date=date(2031, 1, 1),
        horizon_years=horizon_years, period_frequency=PeriodFrequency.SEMESTRIAL)
    bess_params = BessParams(
        power_mw=bess_power_mw,
        energy_mwh=bess_energy_mwh,
        cycles_per_year=bess_cycles_per_year,
        round_trip_efficiency=0.88,
        availability=0.98,
        annual_degradation=0.02,
        arbitrage_spread_eur_mwh=40.0,
        ancillary_revenue_eur_mw_year=25000.0,
    )
    technical = TechnicalParams(
        capacity_mw=solar_capacity_mw, yield_scenario="P_50",
        operating_hours_p50=1500.0, operating_hours_p90_10y=1400.0,
        pv_degradation=0.004, bess_degradation=0.02,
        plant_availability=0.99, grid_availability=0.99,
        bess_enabled=True, bess=bess_params)
    revenue = RevenueParams(
        ppa_base_tariff=60.0, ppa_term_years=10, ppa_index=0.02,
        market_scenario="Central", market_prices_curve=tuple(65.0 + i for i in range(30)),
        market_inflation=0.02, co2_enabled=True, co2_price_eur=5.0)
    financing = FinancingParams(
        share_capital_keur=500.0, shl_amount_keur=5_000.0, shl_rate=0.08,
        gearing_ratio=0.75, senior_tenor_years=15, base_rate=0.03, margin_bps=250,
        floating_share=0.3, fixed_share=0.7, hedge_coverage=0.8,
        target_dscr=1.20, lockup_dscr=1.10, dsra_months=6,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value)
    tax = TaxParams(
        corporate_rate=0.25, loss_carryforward_years=5,
        loss_carryforward_cap=1.0, atad_ebitda_limit=0.30, atad_min_interest_keur=3000.0)

    return ProjectInputs(info=info, technical=technical, capex=capex,
        opex=tuple(opex), revenue=revenue, financing=financing, tax=tax)



def create_default_wind_bess_project(
    wind_capacity_mw: float = 80.0,
    bess_power_mw: float = 10.0,
    bess_energy_mwh: float = 20.0,
    bess_cycles_per_year: float = 365.0,
    horizon_years: int = 25,
    construction_months: int = 18,
) -> ProjectInputs:
    """Generic wind + BESS hybrid project."""
    z = CapexItem(name="Unused", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)
    turbines = CapexItem(name="Wind Turbines", amount_keur=30_000.0, y0_share=0.4,
                         spending_profile=(0.6,), asset_class=AssetClass.WIND_TURBINES)
    cells = CapexItem(name="BESS Cells", amount_keur=5_000.0, y0_share=0.0,
                      spending_profile=(0.5, 0.5), asset_class=AssetClass.BESS_CELLS)
    civil = CapexItem(name="Civil Works", amount_keur=4_000.0, y0_share=0.3,
                      spending_profile=(0.4, 0.3), asset_class=AssetClass.CIVIL_GRID)
    grid = CapexItem(name="Grid Connection", amount_keur=3_000.0, y0_share=0.5,
                     spending_profile=(0.5,), asset_class=AssetClass.CIVIL_GRID)
    capex = CapexStructure(
        epc_contract=turbines, production_units=cells,
        epc_other=civil, grid_connection=grid,
        ops_prep=z, insurances=z, lease_tax=z,
        construction_mgmt_a=z, commissioning=z,
        audit_legal=z, construction_mgmt_b=z,
        contingencies=z, taxes=z,
        project_acquisition=z, project_rights=z,
        idc_keur=0.0, bank_fees_keur=0.0,  # S1-C: factory-direct must match resolver (which zeros via _zero_financial_capex_subfields)
    )
    opex = [
        OpexItem(name="Technical Management", y1_amount_keur=200.0, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=150.0, annual_inflation=0.02),
        OpexItem(name="Maintenance", y1_amount_keur=120.0, annual_inflation=0.02),
        OpexItem(name="Lease & Tax", y1_amount_keur=80.0, annual_inflation=0.02),
    ]
    info = ProjectInfo(
        name="Generic Wind+BESS", company="WindBessCo", code="WINDBESS-001",
        country_iso="DE", financial_close=date(2030, 1, 1),
        construction_months=construction_months, cod_date=date(2031, 7, 1),
        horizon_years=horizon_years, period_frequency=PeriodFrequency.SEMESTRIAL)
    bess_params = BessParams(
        power_mw=bess_power_mw,
        energy_mwh=bess_energy_mwh,
        cycles_per_year=bess_cycles_per_year,
        round_trip_efficiency=0.88,
        availability=0.98,
        annual_degradation=0.02,
        arbitrage_spread_eur_mwh=35.0,
        ancillary_revenue_eur_mw_year=25000.0,
    )
    technical = TechnicalParams(
        capacity_mw=wind_capacity_mw, yield_scenario="P_50",
        operating_hours_p50=3000.0, operating_hours_p90_10y=2700.0,
        pv_degradation=0.0, bess_degradation=0.02,
        plant_availability=0.97, grid_availability=0.99,
        bess_enabled=True, bess=bess_params)
    revenue = RevenueParams(
        ppa_base_tariff=65.0, ppa_term_years=12, ppa_index=0.02,
        market_scenario="Central", market_prices_curve=tuple(60.0 + i for i in range(30)),
        market_inflation=0.02, balancing_cost_wind_eur_mwh=8.0,
        co2_enabled=True, co2_price_eur=4.0)
    financing = FinancingParams(
        share_capital_keur=500.0, shl_amount_keur=6_000.0, shl_rate=0.08,
        gearing_ratio=0.75, senior_tenor_years=15, base_rate=0.03, margin_bps=250,
        floating_share=0.3, fixed_share=0.7, hedge_coverage=0.8,
        target_dscr=1.20, lockup_dscr=1.10, dsra_months=6,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value)
    tax = TaxParams(
        corporate_rate=0.25, loss_carryforward_years=5,
        loss_carryforward_cap=1.0, atad_ebitda_limit=0.30, atad_min_interest_keur=3000.0)


    return ProjectInputs(info=info, technical=technical, capex=capex,
        opex=tuple(opex), revenue=revenue, financing=financing, tax=tax)


__all__ = [
    # Golden Excel parity projects — do not modify
    "create_default_oborovo",
    "create_default_oborovo_legacy_calibration",
    "create_default_tuho_wind1",
    # Demo/test projects (Test 1 and Test 2)
    "create_default_solar_project",  # Test 1 — Solar
    "create_default_wind_project",   # Test 2 — Wind
    # Legacy factories — kept for test backward-compatibility only
    # Not registered in the UI catalogue (removed from PROJECT_CONFIGS in Stack J)
    "create_default_bess_project",
    "create_default_solar_bess_project",
    "create_default_wind_bess_project",
]


# ── Backward-compatibility shim ────────────────────────────────────────────────
# Tests and legacy code may call ProjectInputs.create_default_oborovo()
# as a class method. Wire it here so the domain layer stays pure.
ProjectInputs.create_default_oborovo = staticmethod(create_default_oborovo)
ProjectInputs.create_default_tuho_wind1 = staticmethod(create_default_tuho_wind1)
