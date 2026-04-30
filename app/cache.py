"""App-level caching — @st.cache_data ONLY lives here.

S2-1: Moved from utils/cache.py and domain/model_state.py
This is the ONLY place where @st.cache_data lives.
Domain layer must NEVER import Streamlit.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from domain.inputs import ProjectInputs
    from domain.period_engine import PeriodEngine


# =============================================================================
# HASH FUNCTIONS FOR CACHE KEYING
# =============================================================================

def hash_inputs_for_cache(inputs: "ProjectInputs") -> int:
    """Deterministic hash for ProjectInputs — for @st.cache_data hash_funcs."""
    return hash((
        inputs.info.name,
        inputs.info.country_iso,
        inputs.capex.total_capex,
        inputs.financing.gearing_ratio,
        inputs.financing.senior_tenor_years,
        inputs.revenue.ppa_base_tariff,
        inputs.revenue.ppa_term_years,
        inputs.info.cod_date.toordinal() if hasattr(inputs.info.cod_date, 'toordinal') else 0,
    ))


def hash_engine_for_cache(engine: "PeriodEngine") -> int:
    """Deterministic hash for PeriodEngine — for @st.cache_data hash_funcs."""
    return hash((
        engine.anchor_date.toordinal() if hasattr(engine.anchor_date, 'toordinal') else 0,
        engine.num_periods,
        engine.periods_per_year,
    ))


# =============================================================================
# CACHED SCHEDULES (S2-1: moved from utils/cache.py)
# =============================================================================

@st.cache_data(show_spinner=False, hash_funcs={
    "ProjectInputs": hash_inputs_for_cache,
    "PeriodEngine": hash_engine_for_cache,
})
def cached_generation_schedule(
    inputs: "ProjectInputs",
    engine: "PeriodEngine",
    yield_scenario: str = "P50",
) -> dict[int, float]:
    """Cached generation schedule.

    Args:
        inputs: Project inputs
        engine: Period engine
        yield_scenario: "P50" or "P90-10y"

    Returns:
        Dict mapping period_index → generation_MWh
    """
    from domain.revenue.generation import full_generation_schedule
    return full_generation_schedule(inputs, engine, yield_scenario)


@st.cache_data(show_spinner=False, hash_funcs={
    "ProjectInputs": hash_inputs_for_cache,
    "PeriodEngine": hash_engine_for_cache,
})
def cached_revenue_schedule(
    inputs: "ProjectInputs",
    engine: "PeriodEngine",
) -> dict[int, float]:
    """Cached revenue schedule.

    Args:
        inputs: Project inputs
        engine: Period engine

    Returns:
        Dict mapping period_index → revenue_kEUR
    """
    from domain.revenue.generation import full_revenue_schedule
    return full_revenue_schedule(inputs, engine)


@st.cache_data(show_spinner=False, hash_funcs={
    "ProjectInputs": hash_inputs_for_cache,
})
def cached_opex_schedule_annual(
    inputs: "ProjectInputs",
    horizon_years: int = 30,
) -> dict[int, float]:
    """Cached annual OPEX schedule.

    Args:
        inputs: Project inputs
        horizon_years: Number of years to project

    Returns:
        Dict mapping year_index → OPEX in kEUR
    """
    from domain.opex.projections import opex_schedule_annual
    return opex_schedule_annual(inputs, horizon_years)


@st.cache_data(show_spinner=False, hash_funcs={
    "ProjectInputs": hash_inputs_for_cache,
    "PeriodEngine": hash_engine_for_cache,
})
def cached_model_state(
    inputs: "ProjectInputs",
    engine: "PeriodEngine",
):
    """Cached model state with all precomputed schedules.

    Args:
        inputs: Project inputs
        engine: Period engine

    Returns:
        ModelState with all schedules
    """
    from domain.model_state import build_model_state
    return build_model_state(inputs, engine)


# =============================================================================
# CACHED WATERFALL (S2-1: moved from utils/cache.py)
# =============================================================================

@st.cache_data(
    show_spinner="⚙️ Računam waterfall...",
    hash_funcs={
        "ProjectInputs": hash_inputs_for_cache,
        "PeriodEngine": hash_engine_for_cache,
    }
)
def cached_run_waterfall_v3(
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
    """Cached waterfall computation with proper hash_funcs.

    This is the v3 version — uses cached schedules and proper hash_funcs
    for both ProjectInputs and PeriodEngine.

    Args:
        inputs: ProjectInputs instance
        engine: PeriodEngine instance
        rate_per_period: Interest rate per period
        tenor_periods: Senior debt tenor in periods
        target_dscr: Target DSCR for sculpting
        lockup_dscr: Lockup DSCR threshold
        tax_rate: Corporate tax rate
        dsra_months: DSRA reserve months
        shl_amount: Subordinated hybrid loan amount
        shl_rate: SHL interest rate
        shl_idc_keur: SHL IDC amount
        shl_repayment_method: "bullet" | "cash_sweep" | "pik" | "accrued" | "pik_then_sweep"
        shl_tenor_years: SHL tenor (0 = bullet at senior maturity)
        shl_wht_rate: WHT on SHL interest
        discount_rate_project: Discount rate for project NPV
        discount_rate_equity: Discount rate for equity NPV
        fixed_debt_keur: Override sculpted debt
        fixed_ds_keur: Fixed debt service per period (TUHO)
        rate_schedule: Per-period rate schedule (Euribor curve)
        equity_irr_method: "equity_only" | "combined" | "shl_plus_dividends"
        share_capital_keur: Share capital (for combined method)
        sculpt_capex_keur: CAPEX for equity base
        debt_sizing_method: "dscr_sculpt" | "gearing_cap" | "fixed"
        dscr_schedule: Per-period DSCR targets

    Returns:
        WaterfallResult with all computed periods and metrics
    """
    from domain.waterfall.waterfall_engine import run_waterfall

    periods_list = list(engine.periods())
    revenue_dict = cached_revenue_schedule(inputs, engine)
    generation_dict = cached_generation_schedule(inputs, engine)
    opex_annual = cached_opex_schedule_annual(inputs, inputs.info.horizon_years)

    # Depreciation schedule
    horizon_years = inputs.info.horizon_years
    dep_per_year = inputs.capex.total_capex / horizon_years
    depreciation_schedule_annual = [dep_per_year] * horizon_years

    ebitda_schedule = []
    revenue_schedule = []
    generation_schedule = []
    depreciation_schedule = []
    opex_schedule = []

    for p in periods_list:
        rev = revenue_dict.get(p.index, 0)
        gen = generation_dict.get(p.index, 0)
        if p.is_operation:
            opex = opex_annual.get(p.year_index, 0) / 2
            ebitda = max(0, rev - opex)
            annual_dep = depreciation_schedule_annual[p.year_index - 1] if p.year_index <= len(depreciation_schedule_annual) else dep_per_year
            dep = annual_dep / 2
        else:
            opex = 0
            ebitda = 0
            dep = 0

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
        fixed_debt_keur=fixed_debt_keur if fixed_debt_keur is not None else getattr(inputs.financing, 'fixed_debt_keur', None),
        fixed_ds_keur=fixed_ds_keur if fixed_ds_keur is not None else getattr(inputs.financing, 'fixed_ds_keur', None),
        rate_schedule=rate_schedule,
        idc_keur=inputs.capex.idc_keur,
        bank_fees_keur=inputs.capex.bank_fees_keur,
        commitment_fees_keur=inputs.capex.commitment_fees_keur,
        equity_irr_method=equity_irr_method,
        share_capital_keur=share_capital_keur,
        sculpt_capex_keur=sculpt_capex_keur,
        debt_sizing_method=debt_sizing_method,
        dscr_schedule=dscr_schedule if dscr_schedule is not None else getattr(inputs.financing, 'dscr_schedule', None),
    )


def clear_all_caches() -> None:
    """Invalidate all caches — call when inputs change."""
    cached_generation_schedule.clear()
    cached_revenue_schedule.clear()
    cached_opex_schedule_annual.clear()
    cached_model_state.clear()
    cached_run_waterfall_v3.clear()


__all__ = [
    "hash_inputs_for_cache",
    "hash_engine_for_cache",
    "cached_generation_schedule",
    "cached_revenue_schedule",
    "cached_opex_schedule_annual",
    "cached_model_state",
    "cached_run_waterfall_v3",
    "clear_all_caches",
]