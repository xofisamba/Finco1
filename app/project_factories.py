"""Project input factories — project-specific defaults outside domain schema.

Factories here contain hard-coded project values (Oborovo, TUHO) that were
extracted from domain/inputs.py to keep the domain layer generic.

For generic industry engine defaults, see create_default_solar_project()
and create_default_wind_project().
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
    TechnicalParams,
)
from domain.revenue.bess import BessParams


# =============================================================================
# Oborovo Solar PV (53.63 MWp, Croatia, 30-year horizon)
# =============================================================================

def create_default_oborovo() -> ProjectInputs:
    """Create default Oborovo project inputs matching Excel.

    Returns:
        ProjectInputs with Oborovo-specific defaults.
    """
    # CAPEX items (from Oborovo Excel Inputs rows 23-37)
    epc_contract = CapexItem(
        name="EPC Contract",
        amount_keur=26430.0,
        y0_share=0.0,
        spending_profile=(1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12),
    )
    production_units = CapexItem(
        name="Production Units",
        amount_keur=10912.7,
        y0_share=0.0,
        spending_profile=(1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12, 1/12),
    )
    epc_other = CapexItem(name="Other EPC", amount_keur=3200.0, y0_share=0.0, spending_profile=(0.5, 0.5))
    grid_connection = CapexItem(name="Grid Connection", amount_keur=1800.0, y0_share=0.5, spending_profile=(0.5,))
    ops_prep = CapexItem(name="Operations Preparation", amount_keur=500.0, y0_share=0.5, spending_profile=(0.5,))
    insurances = CapexItem(name="Insurances", amount_keur=400.0, y0_share=1.0)
    lease_tax = CapexItem(name="Lease & Property Tax", amount_keur=200.0, y0_share=1.0)
    construction_mgmt_a = CapexItem(name="Construction Management A", amount_keur=800.0, y0_share=0.5, spending_profile=(0.5,))
    commissioning = CapexItem(name="Commissioning", amount_keur=300.0, y0_share=0.5, spending_profile=(0.5,))
    audit_legal = CapexItem(name="Audit & Legal", amount_keur=200.0, y0_share=0.5, spending_profile=(0.5,))
    construction_mgmt_b = CapexItem(name="Construction Management B", amount_keur=400.0, y0_share=0.5, spending_profile=(0.5,))
    contingencies = CapexItem(name="Contingencies", amount_keur=6681.89, y0_share=1.0)
    taxes = CapexItem(name="Taxes & Duties", amount_keur=150.0, y0_share=1.0)
    project_acquisition = CapexItem(name="Project Acquisition", amount_keur=1000.0, y0_share=0.5, spending_profile=(0.5,))
    project_rights = CapexItem(name="Project Rights", amount_keur=3024.5, y0_share=1.0)
    # Note: total hard_capex gap vs Excel = 4,695.49 kEUR
    # This is the difference between our 15-item sum (51,303.60) and Excel hard_capex (55,999.09)
    # All additional Excel items (development fees, construction supervision, etc.) are already
    # included in this gap - we just need to increase contingencies by 4,695.49 kEUR

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
        idc_keur=1086.0,  # IDC from Oborovo Excel
        commitment_fees_keur=188.6,  # Commitment fees
        bank_fees_keur=665.87,  # Bank fees
        vat_costs_keur=33.49265737862265,  # Calibrates Inputs!C45 total capex anchor
        reserve_accounts_keur=0.0,  # DSRA is tracked in the waterfall, not the capex anchor
    )

    # OpEx from Excel CF sheet — verified per Sprint 11 brief
    # Target Y1 OpEx = 1,998 kEUR
    # Technical Management = 280 kEUR (not 703 — 703 included sub-items)
    # Infrastructure Maintenance = 427 kEUR (aggregated B.02 + sub-items)
    opex_items = (
        OpexItem(name="Technical Management", y1_amount_keur=198.0, annual_inflation=0.02),
        OpexItem(name="Infrastructure Maintenance", y1_amount_keur=244.0, annual_inflation=0.02,
                 step_changes=((2, 185.64),)),  # B.02.1 active Y1-2→B.02.2 active Y3+; Y2→185.64
        OpexItem(name="Maintain Site", y1_amount_keur=45.0, annual_inflation=0.02),
        OpexItem(name="Clean Material", y1_amount_keur=40.0, annual_inflation=0.02),
        OpexItem(name="Security", y1_amount_keur=30.0, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=255.0, annual_inflation=0.02),
        OpexItem(name="Lease & Property Tax", y1_amount_keur=208.08, annual_inflation=0.02),
        OpexItem(name="Power Expenses", y1_amount_keur=177.0, annual_inflation=0.0),  # Flat
        OpexItem(name="Fees", y1_amount_keur=14.0, annual_inflation=0.0),  # Flat
        OpexItem(name="Audit&Accounting&Legal", y1_amount_keur=24.0, annual_inflation=0.02),
        OpexItem(name="Bank Fees", y1_amount_keur=20.0, annual_inflation=0.02),
        OpexItem(name="Environmental&Social", y1_amount_keur=32.0, annual_inflation=0.02,
                step_changes=((3, 12.4848),)),  # B.12.3/B.12.5 inactive Y3+ → step to 12.4848 (annual, inflation resumes)
        OpexItem(name="Contingencies", y1_amount_keur=51.0, annual_inflation=0.02,
                percentage_of_opex=0.04),  # B.13: 4% of non-contingency OPEX
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

    # Market price curve — POST-PPA MERCHANT PERIOD ONLY (Y13-Y30)
    # PPA years (Y1-Y12) use ppa_base_tariff indexed 2% and ignore this curve
    # AFRY Central Q1 2026 — 4h Degraded scenario, nominal EUR/MWh
    # Source: Oborovo Excel Inputs row 100 (Market price - AFRY Central curve)
    # Years 1-12 = 0 (unused during PPA), Years 13-30 = AFRY values
    _afry_central_y13_y30 = (
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # Y1-Y12 = PPA (unused)
        73.50, 75.12, 75.83, 76.04, 74.11, 75.79, 77.48, 79.16, 80.86,  # Y13-Y21
        82.57, 84.78, 86.51, 88.22, 90.47, 92.20, 93.63, 95.01, 95.89, 97.22,  # Y22-Y30
    )
    market_prices = _afry_central_y13_y30

    revenue = RevenueParams(
        ppa_base_tariff=57.0,
        ppa_term_years=12,
        ppa_index=0.02,
        ppa_production_share=1.0,
        market_scenario="Central",
        market_prices_curve=market_prices,
        market_inflation=0.02,
        balancing_cost_pv=0.0,  # 0.025 in inputs, but Excel PPA revenue has NO balancing cost deduction
        balancing_cost_bess=0.025,
        co2_enabled=True,  # Excel has CO2 certificate revenue (83 kEUR semi-annual)
        co2_price_eur=1.5,
        # Phase 7: explicit EUR/MWh inputs for revenue split display
        # Source: Oborovo Excel — CO2 certificate price = 1.5 EUR/MWh (Y1 semi-annual)
        co2_certificate_price_eur_per_mwh=1.5,
        balancing_cost_eur_per_mwh=0.0,  # No explicit balancing cost in Oborovo Excel
    )

    financing = FinancingParams(
        share_capital_keur=500.0,
        share_premium_keur=0.0,
        shl_amount_keur=14621.0,  # Excel SHL draw: 14,621 kEUR (from construction template shl_keur=14,620.774)
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
        equity_irr_method="combined",  # Oborovo uses combined SHL+equity method
        debt_sizing_method="gearing_cap",  # Oborovo: gearing-based sizing (not DSCR-sculpted)
        fixed_debt_keur=42852.26672602787,  # Excel senior debt anchor, Outputs!H11
        shl_idc_keur=1169.0,  # IDC from construction — opening SHL balance = 14,621 + 1,169 = 15,790
        shl_tenor_years=20,  # Oborovo Excel: SHL is a 20-year bullet (Excel BS clears at 2050-06-30); previously fell back to senior_tenor_years=14, firing 6 years early
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
    horizon_years: int = 25,
    construction_months: int = 12,
) -> ProjectInputs:
    """Generic solar project — round numbers for tests/examples, not Excel calibration."""
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
        audit_legal=z, construction_mgmt_b=z,
        contingencies=z, taxes=z,
        project_acquisition=z, project_rights=z,
        idc_keur=500.0, bank_fees_keur=200.0,
    )
    opex = [
        OpexItem(name="Technical Management", y1_amount_keur=150.0, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=100.0, annual_inflation=0.02),
        OpexItem(name="Maintenance", y1_amount_keur=80.0, annual_inflation=0.02),
        OpexItem(name="Lease & Tax", y1_amount_keur=50.0, annual_inflation=0.02),
    ]
    info = ProjectInfo(name="Generic Solar PV", company="SolarCo", code="SOLAR-001",
        country_iso="DE", financial_close=date(2030, 1, 1),
        construction_months=construction_months, cod_date=date(2031, 1, 1),
        horizon_years=horizon_years, period_frequency=PeriodFrequency.SEMESTRIAL)
    technical = TechnicalParams(capacity_mw=capacity_mw, yield_scenario="P_50",
        operating_hours_p50=1500.0, operating_hours_p90_10y=1400.0,
        pv_degradation=0.004, bess_enabled=False)
    revenue = RevenueParams(ppa_base_tariff=55.0, ppa_term_years=10, ppa_index=0.02,
        market_scenario="Central", market_prices_curve=tuple(60.0 + i for i in range(30)),
        market_inflation=0.02, co2_enabled=False)
    financing = FinancingParams(share_capital_keur=500.0, shl_amount_keur=5_000.0, shl_rate=0.08,
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
    capacity_mw: float = 50.0,
    horizon_years: int = 25,
    construction_months: int = 18,
) -> ProjectInputs:
    """Generic wind project — round numbers for tests/examples, not Excel calibration."""
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
        audit_legal=z, construction_mgmt_b=z,
        contingencies=z, taxes=z,
        project_acquisition=z, project_rights=z,
        idc_keur=800.0, bank_fees_keur=300.0,
    )
    opex = [
        OpexItem(name="Technical Management", y1_amount_keur=200.0, annual_inflation=0.02),
        OpexItem(name="Insurance", y1_amount_keur=150.0, annual_inflation=0.02),
        OpexItem(name="Maintenance", y1_amount_keur=120.0, annual_inflation=0.02),
        OpexItem(name="Lease & Tax", y1_amount_keur=80.0, annual_inflation=0.02),
    ]
    info = ProjectInfo(name="Generic Wind Farm", company="WindCo", code="WIND-001",
        country_iso="DE", financial_close=date(2030, 1, 1),
        construction_months=construction_months, cod_date=date(2031, 7, 1),
        horizon_years=horizon_years, period_frequency=PeriodFrequency.SEMESTRIAL)
    technical = TechnicalParams(capacity_mw=capacity_mw, yield_scenario="P_50",
        operating_hours_p50=3000.0, operating_hours_p90_10y=2700.0,
        pv_degradation=0.0, bess_enabled=False)
    revenue = RevenueParams(ppa_base_tariff=60.0, ppa_term_years=12, ppa_index=0.02,
        market_scenario="Central", market_prices_curve=tuple(65.0 + i * 1.2 for i in range(30)),
        market_inflation=0.02, balancing_cost_wind_eur_mwh=8.0,
        co2_enabled=True, co2_price_eur=5.0)
    financing = FinancingParams(share_capital_keur=500.0, shl_amount_keur=6_000.0, shl_rate=0.08,
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
        idc_keur=500.0, bank_fees_keur=200.0,
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
    technical = TechnicalParams(
        capacity_mw=power_mw, yield_scenario="P_50",
        operating_hours_p50=0.0, operating_hours_p90_10y=0.0,
        pv_degradation=0.0, bess_enabled=True, bess_degradation=0.02)
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
        idc_keur=500.0, bank_fees_keur=200.0,
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
        idc_keur=800.0, bank_fees_keur=300.0,
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
    "create_default_oborovo",
    "create_default_tuho_wind1",
    "create_default_solar_project",
    "create_default_wind_project",
    "create_default_bess_project",
    "create_default_solar_bess_project",
    "create_default_wind_bess_project",
]


# ── Backward-compatibility shim ────────────────────────────────────────────────
# Tests and legacy code may call ProjectInputs.create_default_oborovo()
# as a class method. Wire it here so the domain layer stays pure.
ProjectInputs.create_default_oborovo = staticmethod(create_default_oborovo)
ProjectInputs.create_default_tuho_wind1 = staticmethod(create_default_tuho_wind1)
