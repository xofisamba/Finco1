"""Uncached waterfall core used by both Streamlit cache and headless calibration.

This module must not import Streamlit. It is the production calculation path
that CLI scripts, tests, and app/cache.py can all call.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.inputs import ProjectInputs
    from domain.period_engine import PeriodEngine


def run_waterfall_v3_core(
    inputs: "ProjectInputs",
    engine: "PeriodEngine",
    rate_per_period: float,
    tenor_periods: int,
    target_dscr: float = 1.15,
    lockup_dscr: float = 1.10,
    tax_rate: float = 0.10,
    dsra_months: int = 6,
    shl_amount: float = 0.0,
    shl_rate: float = 0.0,
    shl_idc_keur: float = 0.0,
    shl_repayment_method: str = "bullet",
    shl_tenor_years: int = 0,
    shl_wht_rate: float = 0.0,
    discount_rate_project: float = 0.0641,
    discount_rate_equity: float = 0.0965,
    fixed_debt_keur: float | None = None,
    fixed_ds_keur: float | None = None,
    rate_schedule: list[float] | None = None,
    equity_irr_method: str = "equity_only",
    share_capital_keur: float = 0.0,
    sculpt_capex_keur: float = 0.0,
    debt_sizing_method: str = "dscr_sculpt",
    dscr_schedule: list[float] | None = None,
):
    """Run the full waterfall without Streamlit cache dependencies.

    FincoGPT calibration note:
    - `domain.waterfall.run_waterfall()` sculpts debt using the first
      `tenor_periods` entries of the EBITDA schedule.
    - If construction rows are included in that list, sculpting starts with two
      zero-CFADS periods while debt repayment output starts at the first
      operating period. That creates a principal/interest timing mismatch.
    - The headless calibration core therefore passes operation-only periods and
      operation-only schedules into the waterfall engine.
    """
    from domain.waterfall.waterfall_engine import run_waterfall
    from domain.revenue.generation import full_revenue_schedule, full_generation_schedule
    from domain.opex.projections import opex_schedule_period

    all_periods = list(engine.periods())
    periods_list = [p for p in all_periods if p.is_operation]
    revenue_dict = full_revenue_schedule(inputs, engine)
    generation_dict = full_generation_schedule(inputs, engine)
    opex_period = opex_schedule_period(inputs, engine)

    horizon_years = inputs.info.horizon_years
    dep_per_year = inputs.capex.total_capex / horizon_years
    depreciation_schedule_annual = [dep_per_year] * horizon_years

    ebitda_schedule: list[float] = []
    revenue_schedule: list[float] = []
    generation_schedule: list[float] = []
    depreciation_schedule: list[float] = []
    opex_schedule: list[float] = []

    for p in periods_list:
        rev = revenue_dict.get(p.index, 0)
        gen = generation_dict.get(p.index, 0)
        opex = opex_period.get(p.index, 0)
        ebitda = max(0, rev - opex)
        annual_dep = (
            depreciation_schedule_annual[p.year_index - 1]
            if p.year_index <= len(depreciation_schedule_annual)
            else dep_per_year
        )
        dep = annual_dep * p.day_fraction

        revenue_schedule.append(rev)
        generation_schedule.append(gen)
        ebitda_schedule.append(ebitda)
        depreciation_schedule.append(dep)
        opex_schedule.append(opex)

    return run_waterfall(
        ebitda_schedule=ebitda_schedule,
        revenue_schedule=revenue_schedule,
        generation_schedule=generation_schedule,
        depreciation_schedule=depreciation_schedule,
        opex_schedule=opex_schedule,
        periods=periods_list,
        total_capex=inputs.capex.total_capex,
        rate_per_period=rate_per_period,
        tenor_periods=tenor_periods,
        target_dscr=target_dscr,
        lockup_dscr=lockup_dscr,
        tax_rate=tax_rate,
        dsra_months=dsra_months,
        shl_amount=shl_amount,
        shl_rate=shl_rate,
        shl_idc_keur=shl_idc_keur,
        shl_repayment_method=shl_repayment_method,
        shl_tenor_years=shl_tenor_years,
        shl_wht_rate=shl_wht_rate,
        discount_rate_project=discount_rate_project,
        discount_rate_equity=discount_rate_equity,
        financial_close=inputs.info.financial_close,
        gearing_ratio=inputs.financing.gearing_ratio,
        fixed_debt_keur=fixed_debt_keur if fixed_debt_keur is not None else getattr(inputs.financing, "fixed_debt_keur", None),
        fixed_ds_keur=fixed_ds_keur if fixed_ds_keur is not None else getattr(inputs.financing, "fixed_ds_keur", None),
        rate_schedule=rate_schedule,
        idc_keur=inputs.capex.idc_keur,
        bank_fees_keur=inputs.capex.bank_fees_keur,
        commitment_fees_keur=inputs.capex.commitment_fees_keur,
        equity_irr_method=equity_irr_method,
        share_capital_keur=share_capital_keur,
        sculpt_capex_keur=sculpt_capex_keur,
        prior_tax_loss_keur=inputs.tax.initial_tax_loss_keur,
        debt_sizing_method=debt_sizing_method,
        dscr_schedule=dscr_schedule if dscr_schedule is not None else getattr(inputs.financing, "dscr_schedule", None),
    )


__all__ = ["run_waterfall_v3_core"]
