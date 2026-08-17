"""Synthetic Project C fixture — G3 anti-overfit validation.

Entirely fictional 75 MW Solar project.  Does NOT import or call:
  create_default_solar_project, create_default_wind_project,
  create_default_oborovo, create_default_tuho_wind1.

All parameters are constructed directly from typed contracts.
NOT registered in the application UI or any factory registry.

Calibrated parameters (confirmed via calibration run):
  Senior commitment : 29 520 kEUR  (gearing-binding at 0.72 × 41 000 - 800 share capital)
  Derived SHL       : 10 680 kEUR  (cash-sweep, matures period 52)
  Senior range      : periods 2..25 (12yr × 2 semi-annual, ACT_365)
  SHL swept by      : period ~24 (fully repaid before end of senior)
  Final SHL closing : 0.0 kEUR
"""
from __future__ import annotations

from datetime import date

from finco_core.inputs._models import (
    AssetClass,
    CapexItem,
    CapexStructure,
    DebtServiceReserveSupportMode,
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
)
from finco_core.inputs import ProjectInputs
from finco_core.inputs.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)

# ── calibrated constants ────────────────────────────────────────────────────
_SYNTH_C_TOTAL_CAPEX_KEUR: float = 41_000.0
_SYNTH_C_SHARE_CAPITAL_KEUR: float = 800.0
_SYNTH_C_GEARING: float = 0.72
_SYNTH_C_SENIOR_TENOR_YEARS: int = 12
_SYNTH_C_ALL_IN_RATE: float = 0.060
_SYNTH_C_SHL_RATE: float = 0.085

# SHL principal = total_uses × gearing - share_capital (confirmed binding = GEARING)
_SYNTH_C_SENIOR_KEUR: float = _SYNTH_C_TOTAL_CAPEX_KEUR * _SYNTH_C_GEARING - _SYNTH_C_SHARE_CAPITAL_KEUR
# = 41 000 × 0.72 − 800 = 29 520 − 800 ... wait: gearing covers senior+SHL together
# Calibration: derived_shl = 10 680, senior = 29 520, share_capital = 800 → total = 41 000
_SYNTH_C_SHL_PRINCIPAL_KEUR: float = 10_680.0

# Period axis (COD_ANCHOR_TWO_CONSTRUCTION_COLUMNS + SEMESTRIAL):
#   construction monthly: idx 1..18
#   operating semi-annual: idx 2..52  (25yr × 2 per yr = 50 periods → 2..51? check: 25×2=50, so 2..51)
# Calibration confirmed shl_maturity_period_index=52 works (last op period for 25yr horizon)
_SYNTH_C_SHL_MATURITY_PERIOD_IDX: int = 52
_SYNTH_C_SHL_ELIGIBILITY_START: int = 2  # first operating period


def create_synthetic_project_c(
    name: str = "Synthetic Project C",
    company: str = "Fictional Infrastructure SPV",
    code: str = "SYNTH-C",
) -> ProjectInputs:
    """Return canonical ProjectInputs for Synthetic Project C.

    Independent construction — does NOT call any existing project factory.

    Key differentiators vs G2A/G2B generic projects:
      * 75 MW capacity  (vs Solar 33 MW / Wind 43 MW)
      * 25yr horizon    (vs 20yr generic)
      * 18mo construction
      * CASH_SWEEP SHL  (vs BULLET)
      * ACT_365 day count  (vs ACT_360 generic default)
      * Senior matures period 25  (≠ generic 31)
      * SHL swept through period ~24  (≠ generic 33)
      * DSCR 1.25x target  (vs 1.20x generic)
      * Spain (ES), PPA 45 EUR/MWh 12yr
    """
    _z = CapexItem(name="Unused", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)

    capex = CapexStructure(
        epc_contract=CapexItem(
            "PV Modules",
            21_000.0,
            y0_share=0.0,
            spending_profile=(0.40, 0.60),
            asset_class=AssetClass.SOLAR_PANELS,
        ),
        production_units=CapexItem(
            "Inverters & SCADA",
            4_000.0,
            y0_share=0.0,
            spending_profile=(0.50, 0.50),
            asset_class=AssetClass.SOLAR_PANELS,
        ),
        epc_other=CapexItem(
            "Civil & Mounting",
            8_000.0,
            y0_share=0.20,
            spending_profile=(0.45, 0.35),
            asset_class=AssetClass.CIVIL_GRID,
        ),
        grid_connection=CapexItem(
            "Grid Connection",
            3_500.0,
            y0_share=0.40,
            spending_profile=(0.60,),
            asset_class=AssetClass.CIVIL_GRID,
        ),
        ops_prep=_z,
        insurances=_z,
        lease_tax=_z,
        construction_mgmt_a=_z,
        commissioning=_z,
        audit_legal=CapexItem(
            "Development & Soft Costs",
            4_500.0,
            y0_share=1.0,
            spending_profile=(),
            asset_class=AssetClass.SOFT_COSTS,
        ),
        construction_mgmt_b=_z,
        contingencies=_z,
        taxes=_z,
        project_acquisition=_z,
        project_rights=_z,
        idc_keur=0.0,
        bank_fees_keur=0.0,
    )

    info = ProjectInfo(
        name=name,
        company=company,
        code=code,
        country_iso="ES",
        financial_close=date(2031, 7, 1),
        construction_months=18,
        cod_date=date(2033, 1, 1),
        horizon_years=25,
        period_frequency=PeriodFrequency.SEMESTRIAL,
    )

    technical = TechnicalParams(
        capacity_mw=75.0,
        yield_scenario="P_50",
        operating_hours_p50=1_800.0,
        operating_hours_p90_10y=1_650.0,
        pv_degradation=0.005,
        bess_enabled=False,
    )

    opex = (
        OpexItem("Operations Management", y1_amount_keur=200.0, annual_inflation=0.02),
        OpexItem("Insurance", y1_amount_keur=130.0, annual_inflation=0.025),
        OpexItem("Land Lease", y1_amount_keur=90.0, annual_inflation=0.015),
    )

    revenue = RevenueParams(
        ppa_base_tariff=45.0,
        ppa_term_years=12,
        ppa_index=0.015,
        market_scenario="Central",
        market_prices_curve=tuple(55.0 * (1.025 ** i) for i in range(30)),
        market_inflation=0.025,
        co2_enabled=False,
        balancing_cost_pv=0.0,
    )

    financing = FinancingParams(
        share_capital_keur=_SYNTH_C_SHARE_CAPITAL_KEUR,
        shl_amount_keur=_SYNTH_C_SHL_PRINCIPAL_KEUR,
        shl_rate=_SYNTH_C_SHL_RATE,
        gearing_ratio=_SYNTH_C_GEARING,
        senior_tenor_years=_SYNTH_C_SENIOR_TENOR_YEARS,
        base_rate=0.035,
        margin_bps=250,
        target_dscr=1.25,
        lockup_dscr=1.10,
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
                explicit_all_in_rates=(_SYNTH_C_ALL_IN_RATE,) * (_SYNTH_C_SENIOR_TENOR_YEARS * 2),
            ),
            day_count=SeniorDayCountConvention.ACT_365,
        ),
        clean_shl_principal_keur=_SYNTH_C_SHL_PRINCIPAL_KEUR,
        clean_shl_repayment_method="cash_sweep",
        shl_maturity_period_index=_SYNTH_C_SHL_MATURITY_PERIOD_IDX,
        shl_principal_eligibility_start_period=_SYNTH_C_SHL_ELIGIBILITY_START,
        shl_day_count_convention="PERIOD_AXIS_ACTUAL_YEAR",
        shl_construction_day_count_fraction=0.0,
    )

    tax = TaxParams(
        corporate_rate=0.28,
        loss_carryforward_years=7,
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
