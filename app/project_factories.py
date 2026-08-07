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
    DebtSizingMethod,
    EquityIRRMethod,
    FinancingParams,
    OpexItem,
    PeriodFrequency,
    ProjectInfo,
    ProjectInputs,
    RevenueAdjustmentSchedule,
    RevenueParams,
    SHLRepaymentMethod,
    TaxParams,
    TaxDepreciationMode,
    TechnicalParams,
)
from domain.revenue.bess import BessParams
from finco_core.inputs._models import DebtSizingMode
from finco_core.inputs.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)
from finco_core.inputs.senior_sculpting import SeniorSculptingConfig
from finco_core.opex.oborovo_config import build_oborovo_opex_capability


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
    # NO balancing plug — all items are auditable to source rows.
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
    # and Project Rights — no balancing plug is used.

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
        idc_keur=1086.032,        # DERIVED: Senior Debt IDC (debt draws × rate × day-fraction)
        commitment_fees_keur=188.563,  # DERIVED: Senior Debt commitment fee (undrawn × rate)
        bank_fees_keur=477.303,   # DERIVED: Structuring/arrangement fee (rate × facility basis)
        # vat_costs_keur = VAT-facility FINANCING COSTS only (not construction VAT 7,665 kEUR)
        # = vat_facility_idc_keur (208.448) + vat_facility_commitment_fee_keur (13.622) = 222.070
        vat_costs_keur=222.070,       # total VAT-facility capitalised financing cost
        vat_facility_idc_keur=208.448,      # DERIVED: VAT Facility IDC
        vat_facility_commitment_fee_keur=13.622,  # DERIVED: VAT Facility commitment fee
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

    financing = FinancingParams(
        share_capital_keur=500.0,
        share_premium_keur=0.0,
        shl_amount_keur=13547.2,  # Excel SHL draw: 13,547.2 kEUR (from oborovo_baseline.json fixture; prior value 14,621 had ~1,074 kEUR calibration gap vs Excel)
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
        min_llcr=1.15,
        dsra_months=6,
        equity_irr_method="shl_plus_dividends",  # Stack O: Golden Excel equity IRR = SHL interest while SHL outstanding + dividends after; "combined" (capex-debt base, distributions only) gave 6.24% vs golden 10.60%
        debt_sizing_method="gearing_cap",  # legacy field; clean solver uses debt_sizing_mode
        debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,  # C3B3A: clean DSCR-sculpted solver path
        fixed_debt_keur=42852.26672602787,  # Excel senior debt anchor, Outputs!H11 (legacy; clean solver derives this as output)
        shl_idc_keur=1169.0,  # IDC from construction — opening SHL balance = 14,621 + 1,169 = 15,790
        shl_tenor_years=20,  # Oborovo Excel: SHL is a 20-year bullet (Excel BS clears at 2050-06-30); previously fell back to senior_tenor_years=14, firing 6 years early
        use_frozen_excel_senior_debt_schedule=True,  # Phase 23R: frozen path for legacy engine; clean solver ignores this flag
        frozen_senior_ds_fixture_path="reports/phase23q_oborovo_senior_debt_sizing_extraction.csv",  # Stack AC: capability-driven fixture path
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
    )

    tax = TaxParams(
        corporate_rate=0.10,
        loss_carryforward_years=5,
        loss_carryforward_cap=1.0,
        legal_reserve_cap=0.10,
        thin_cap_enabled=False,
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
        # C3B1 evidence: cash tax timing = TAX_YEAR_LAST_PERIOD, lag=0.
        # This is a clean engine convention for annual CIT accrual in last period
        # of each tax year — not a payment lag. Source-ownership explicitly set.
        cash_tax_timing_source_owned=True,
    )

    return ProjectInputs(
        info=info,
        technical=technical,
        capex=capex,
        opex=opex_items,
        revenue=revenue,
        financing=financing,
        tax=tax,
        hierarchical_opex_capability=build_oborovo_opex_capability(),
    )



# =============================================================================
# TUHO Wind 1 (35 MW, Croatia, 30-year horizon)
# =============================================================================

def create_default_tuho_wind1() -> ProjectInputs:
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
        thin_cap_enabled=False,
        atad_ebitda_limit=0.30,
        atad_min_interest_keur=3000.0,
        wht_sponsor_dividends=0.05,
        wht_sponsor_shl_interest=0.0,  # 0% WHT on SHL interest per Excel R406
        shl_cap_applies=True,
        cit_cash_tax_start_operating_index=25,  # TUHO Excel: first non-zero R67 at P25
    )

    return ProjectInputs(
        info=info,
        technical=technical,
        capex=capex,
        opex=opex_items,
        revenue=revenue,
        financing=financing,
        tax=tax,
    )


# =============================================================================
# Generic industry engine factories — simple round numbers for tests/examples
# =============================================================================

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
    # G1H: share_capital_keur + shl_amount_keur must fund the full
    # non-senior-debt share implied by gearing_ratio=0.75, i.e.
    # 33,000 kEUR total_capex * 0.25 = 8,250 kEUR. Previously only
    # 500 + 5,000 = 5,500 kEUR was funded, leaving a 2,750 kEUR gap that
    # degenerated the equity cash-flow stream (equity_irr computed to 0.0).
    financing = FinancingParams(share_capital_keur=500.0, shl_amount_keur=7_750.0, shl_rate=0.08,
        gearing_ratio=0.75, senior_tenor_years=15, base_rate=0.03, margin_bps=250,
        floating_share=0.3, fixed_share=0.7, hedge_coverage=0.8,
        target_dscr=1.20, lockup_dscr=1.10, dsra_months=6,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value)
    tax = TaxParams(corporate_rate=0.25, loss_carryforward_years=5,
        loss_carryforward_cap=1.0, atad_ebitda_limit=0.30, atad_min_interest_keur=3000.0)

    return ProjectInputs(info=info, technical=technical, capex=capex,
        opex=tuple(opex), revenue=revenue, financing=financing, tax=tax)


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
    # G1H: share_capital_keur + shl_amount_keur must fund the full
    # non-senior-debt share implied by gearing_ratio=0.75, i.e.
    # 43,000 kEUR total_capex * 0.25 = 10,750 kEUR. Previously only
    # 500 + 6,000 = 6,500 kEUR was funded, leaving a 4,250 kEUR gap.
    financing = FinancingParams(share_capital_keur=500.0, shl_amount_keur=10_250.0, shl_rate=0.08,
        gearing_ratio=0.75, senior_tenor_years=15, base_rate=0.03, margin_bps=250,
        floating_share=0.3, fixed_share=0.7, hedge_coverage=0.8,
        target_dscr=1.20, lockup_dscr=1.10, dsra_months=6,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value)
    tax = TaxParams(corporate_rate=0.25, loss_carryforward_years=5,
        loss_carryforward_cap=1.0, atad_ebitda_limit=0.30, atad_min_interest_keur=3000.0)

    return ProjectInputs(info=info, technical=technical, capex=capex,
        opex=tuple(opex), revenue=revenue, financing=financing, tax=tax)


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
