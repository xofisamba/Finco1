"""Project input factories outside the domain dataclass definitions.

These helpers keep project-specific Excel calibration defaults out of the core
input schema. They are intentionally Streamlit-free and can be used by tests,
CLI calibration, and the app.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from domain.inputs import (
    CapexItem,
    DebtSizingMethod,
    EquityIRRMethod,
    FinancingParams,
    PeriodFrequency,
    ProjectInfo,
    ProjectInputs,
    RevenueParams,
    SHLRepaymentMethod,
    TaxParams,
    TechnicalParams,
)


TUHO_TOTAL_CAPEX_TARGET_KEUR = 72_993.70678606197
TUHO_SENIOR_DEBT_TARGET_KEUR = 43_359.2737822209
TUHO_SHL_PRINCIPAL_KEUR = 29_135.176217946093


def create_default_tuho() -> ProjectInputs:
    """Create a first-pass TUHO input set for headless Excel reconciliation.

    The current app originally only had Oborovo defaults. This factory provides
    a conservative TUHO starting point using the existing input schema plus the
    Excel anchors extracted in FincoGPT fixtures. It is not claimed to be fully
    calibrated yet; period-by-period reconciliation tests document the remaining
    gaps.
    """
    base = ProjectInputs.create_default_oborovo()

    info = ProjectInfo(
        name="Tuhobic Wind",
        company="TUHO SPV",
        code="TUHO-001",
        country_iso="HR",
        financial_close=date(2028, 6, 30),
        construction_months=18,
        cod_date=date(2029, 12, 30),
        horizon_years=30,
        period_frequency=PeriodFrequency.SEMESTRIAL,
    )

    technical = TechnicalParams(
        capacity_mw=72.0,
        yield_scenario="P_50",
        operating_hours_p50=2900.0,
        operating_hours_p90_10y=2700.0,
        pv_degradation=0.0,
        bess_degradation=0.0,
        plant_availability=0.98,
        grid_availability=0.99,
        bess_enabled=False,
    )

    revenue = RevenueParams(
        ppa_base_tariff=57.5,
        ppa_term_years=12,
        ppa_index=0.02,
        ppa_production_share=1.0,
        market_scenario="Central",
        market_prices_curve=base.revenue.market_prices_curve,
        market_inflation=0.02,
        balancing_cost_pv=0.0,
        balancing_cost_bess=0.0,
        balancing_cost_wind_eur_mwh=8.0,
        co2_enabled=False,
        co2_price_eur=0.0,
    )

    capex_delta = TUHO_TOTAL_CAPEX_TARGET_KEUR - base.capex.total_capex
    contingencies = replace(
        base.capex.contingencies,
        amount_keur=base.capex.contingencies.amount_keur + capex_delta,
    )
    capex = replace(base.capex, contingencies=contingencies)

    financing = FinancingParams(
        share_capital_keur=500.0,
        share_premium_keur=0.0,
        shl_amount_keur=TUHO_SHL_PRINCIPAL_KEUR,
        shl_rate=0.0890,
        gearing_ratio=TUHO_SENIOR_DEBT_TARGET_KEUR / TUHO_TOTAL_CAPEX_TARGET_KEUR,
        senior_debt_amount_keur=TUHO_SENIOR_DEBT_TARGET_KEUR,
        senior_tenor_years=14,
        base_rate=0.03,
        margin_bps=275,
        floating_share=0.2,
        fixed_share=0.8,
        hedge_coverage=0.8,
        commitment_fee=0.0105,
        arrangement_fee=0.0,
        structuring_fee=0.01,
        target_dscr=1.20,
        lockup_dscr=1.10,
        min_llcr=1.15,
        amortization_type="fixed_ds",
        fixed_ds_keur=0.0,
        dsra_months=6,
        equity_irr_method=EquityIRRMethod.SHL_PLUS_DIVIDENDS.value,
        debt_sizing_method=DebtSizingMethod.FIXED.value,
        fixed_debt_keur=TUHO_SENIOR_DEBT_TARGET_KEUR,
        dscr_schedule=[1.20] * 24 + [1.40] * 40,
        shl_repayment_method=SHLRepaymentMethod.PIK_THEN_SWEEP.value,
        shl_pik_switch_period=0,
        shl_tenor_years=0,
        shl_idc_keur=0.0,
    )

    tax = TaxParams(
        corporate_rate=0.18,
        loss_carryforward_years=5,
        loss_carryforward_cap=1.0,
        prior_tax_loss_keur=25_000.0,
        legal_reserve_cap=0.10,
        construction_pl=None,
        thin_cap_enabled=False,
        thin_cap_de_ratio=0.8,
        atad_ebitda_limit=0.30,
        atad_min_interest_keur=3_000.0,
        wht_sponsor_dividends=0.0,
        wht_sponsor_shl_interest=0.0,
        shl_cap_applies=False,
    )

    return ProjectInputs(
        info=info,
        technical=technical,
        capex=capex,
        opex=base.opex,
        revenue=revenue,
        financing=financing,
        tax=tax,
    )


__all__ = ["create_default_tuho"]
