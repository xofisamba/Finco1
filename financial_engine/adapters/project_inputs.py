"""financial_engine.adapters.project_inputs — Generic ProjectInputs → OperatingModelInput adapter.

One generic mapping for all projects. No project-code dispatch, no project-name
references, no factory invocation, no file loading.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finco_core.inputs import ProjectInputs

from financial_engine.inputs import (
    CalendarInput,
    CapexItemForDep,
    DepreciationInput,
    InputProvenance,
    OpexInput,
    OpexLineInput,
    OperatingModelInput,
    RevenueInput,
    TechnicalInput,
    YieldScenario,
)


def from_project_inputs(
    inputs: "ProjectInputs",
    *,
    source_id: str = "",
    baseline_commit_sha: str = "",
    # Legacy params kept for test backward compat — ignored by orchestrator.
    depreciation_period_count: int = 0,
    depreciation_cod_period: int = 0,
) -> OperatingModelInput:
    """Adapt a canonical ProjectInputs to a clean OperatingModelInput.

    Depreciation asset metadata is not carried in ProjectInputs; callers must
    supply `depreciation_period_count` and `depreciation_cod_period` directly.
    Asset-class information must be injected separately if needed.
    """
    info = inputs.info
    tech = inputs.technical
    rev = inputs.revenue

    yield_scenario = (
        YieldScenario.P90_10Y
        if tech.yield_scenario == "P90-10y"
        else YieldScenario.P50
    )

    calendar = CalendarInput(
        financial_close=info.financial_close,
        construction_months=info.construction_months,
        horizon_years=info.horizon_years,
        ppa_years=float(rev.ppa_term_years),
    )

    technical = TechnicalInput(
        capacity_mw=tech.capacity_mw,
        yield_scenario=yield_scenario,
        operating_hours_p50=tech.operating_hours_p50,
        operating_hours_p90_10y=tech.operating_hours_p90_10y,
        pv_degradation=tech.pv_degradation,
        plant_availability=tech.plant_availability,
        grid_availability=tech.grid_availability,
    )

    co2_semiannual: tuple[float, ...] = ()
    if rev.co2_sales_schedule is not None and rev.co2_sales_schedule.semiannual_values:
        co2_semiannual = tuple(rev.co2_sales_schedule.semiannual_values)

    revenue = RevenueInput(
        ppa_base_tariff_eur_mwh=rev.ppa_base_tariff,
        ppa_term_years=float(rev.ppa_term_years),
        ppa_index=rev.ppa_index,
        ppa_production_share=rev.ppa_production_share,
        market_prices_curve_eur_mwh=tuple(rev.market_prices_curve),
        market_inflation=rev.market_inflation,
        balancing_cost_pv_fraction=rev.balancing_cost_pv,
        balancing_cost_wind_eur_mwh=rev.balancing_cost_wind_eur_mwh,
        co2_enabled=rev.co2_enabled,
        co2_price_eur_mwh=rev.co2_price_eur,
        first_merchant_operating_period_index=rev.first_merchant_operating_period_index,
        co2_price_semiannual_eur_mwh=co2_semiannual,
        co2_price_eur_per_mwh_scalar=rev.co2_certificate_price_eur_per_mwh,
        balancing_cost_eur_per_mwh=rev.balancing_cost_eur_per_mwh,
    )

    opex_items = tuple(
        OpexLineInput(
            name=item.name,
            y1_amount_keur=item.y1_amount_keur,
            annual_inflation=item.annual_inflation,
            step_changes=tuple(item.step_changes),
            percentage_of_opex=item.percentage_of_opex,
        )
        for item in inputs.opex
    )

    capex_items_for_dep = tuple(
        CapexItemForDep(
            name=item.name,
            amount_keur=item.amount_keur,
            asset_class_code=item.asset_class.value,
            useful_life_override=item.useful_life_override,
        )
        for item in inputs.capex.capex_items()
    )

    return OperatingModelInput(
        calendar=calendar,
        technical=technical,
        revenue=revenue,
        opex=OpexInput(items=opex_items),
        depreciation=DepreciationInput(
            capex_items_for_depreciation=capex_items_for_dep,
            senior_tenor_years=getattr(inputs.financing, "senior_tenor_years", 14),
        ),
        source=InputProvenance(
            source_id=source_id,
            baseline_commit_sha=baseline_commit_sha,
        ),
    )
