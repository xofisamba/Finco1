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
    advanced_opex_line_items: tuple | None = None,
    advanced_capex_line_items: tuple | None = None,
    advanced_capex_depreciation_schedule: "DepreciationSchedule | None" = None,
) -> dict:
    """Run the full waterfall without Streamlit cache dependencies.

    FincoGPT calibration note:
    - `domain.waterfall.run_waterfall()` sculpts debt using the first
      `tenor_periods` entries of the EBITDA schedule.
    - If construction rows are included in that list, sculpting starts with two
      zero-CFADS periods while debt repayment output starts at the first
      operating period. That creates a principal/interest timing mismatch.
    - The headless calibration core therefore passes operation-only periods and
      operation-only schedules into the waterfall engine.

    advanced_opex_line_items: if provided (non-empty tuple), the advanced
      OpexLineItem engine is used to generate the OPEX schedule instead of
      the legacy OpexItem/OpexParams path. This enables granular per-line-item
      OPEX modeling with manual/hardcoded override support.

    advanced_capex_depreciation_schedule: if provided (from
      app.depreciation_engine.generate_schedule()), the new asset-class
      depreciation schedule is used for the tax-shield calculation instead of
      the legacy CapexItem-based schedule. This enables per-asset-class
      depreciable lives (solar modules 25 yr, inverters 10 yr, etc.).
    """
    from domain.waterfall.waterfall_engine import run_waterfall
    from domain.revenue.generation import full_revenue_schedule, full_generation_schedule
    from domain.opex.projections import opex_schedule_period
    from domain.financing.depreciation_schedule import build_depreciation_schedule

    all_periods = list(engine.periods())
    periods_list = [p for p in all_periods if p.is_operation]
    revenue_dict = full_revenue_schedule(inputs, engine)
    generation_dict = full_generation_schedule(inputs, engine)

    # OPEX: use advanced line-item engine if provided, otherwise fall back to legacy path
    if advanced_opex_line_items:
        from app.opex_engine import apply_opex_line_items_to_project
        horizon_years = inputs.info.horizon_years
        annual_opex = apply_opex_line_items_to_project(advanced_opex_line_items, horizon_years)
        # Convert annual → per-period using period day fraction
        opex_period: dict[int, float] = {}
        for p in periods_list:
            annual_val = annual_opex[p.year_index] if p.year_index < len(annual_opex) else 0.0
            opex_period[p.index] = annual_val * p.day_fraction
    else:
        opex_period = opex_schedule_period(inputs, engine)

    # CAPEX: use advanced CapexLineItems if provided, otherwise fall back to legacy path
    # Computes total_capex_override from the sum of CapexLineItem amounts.
    # This is passed to run_waterfall() to override inputs.capex.total_capex.
    total_capex_override: float | None = None
    if advanced_capex_line_items:
        from app.capex_engine import generate_capex_schedule
        capex_sched = generate_capex_schedule(advanced_capex_line_items, tenor_periods)
        total_capex_override = sum(capex_sched.total_by_period)
    else:
        total_capex_override = None

    horizon_years = inputs.info.horizon_years

    # Depreciation schedule: use advanced CapexLineItem schedule if provided,
    # otherwise fall back to legacy CapexItem path for backward compatibility.
    if advanced_capex_depreciation_schedule is not None:
        # Map DepreciationSchedule (0-based year index) → {year_index: annual_dep}
        dep_schedule_annual = {
            y + 1: advanced_capex_depreciation_schedule.total_by_period[y]
            for y in range(len(advanced_capex_depreciation_schedule.total_by_period))
        }
    else:
        # Legacy path: derive from CapexItem asset classes
        capex_items = inputs.capex.capex_items()
        dep_schedule_annual = build_depreciation_schedule(
            capex_items=capex_items,
            horizon_years=horizon_years,
            senior_tenor_years=inputs.financing.senior_tenor_years,
        )

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
        annual_dep = dep_schedule_annual.get(p.year_index, 0.0)
        dep = annual_dep * p.day_fraction

        revenue_schedule.append(rev)
        generation_schedule.append(gen)
        ebitda_schedule.append(ebitda)
        depreciation_schedule.append(dep)
        opex_schedule.append(opex)

    # Resolve total_capex — use advanced CAPEX if provided, else fall back to inputs
    total_capex_for_waterfall = (
        total_capex_override if total_capex_override is not None
        else inputs.capex.total_capex
    )

    return run_waterfall(
        ebitda_schedule=ebitda_schedule,
        revenue_schedule=revenue_schedule,
        generation_schedule=generation_schedule,
        depreciation_schedule=depreciation_schedule,
        opex_schedule=opex_schedule,
        periods=periods_list,
        total_capex=total_capex_for_waterfall,
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
