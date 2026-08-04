"""financial_engine.adapters.project_inputs — Generic ProjectInputs → OperatingModelInput adapter.

One generic mapping for all projects. No project-code dispatch, no project-name
references, no factory invocation, no file loading.

Depreciation metadata is obtained generically from ProjectInputs.capex.capex_items().
The financing tenor (senior_tenor_years) is mapped explicitly to
financial_cost_useful_life_years so the clean engine carries no financing dependency.
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
from financial_engine.ppa_indexation import PpaIndexationStartPolicy


def from_project_inputs(
    inputs: "ProjectInputs",
    *,
    source_id: str = "",
    baseline_commit_sha: str = "",
) -> OperatingModelInput:
    """Adapt a canonical ProjectInputs to a clean OperatingModelInput.

    Maps capex items generically from inputs.capex.capex_items().
    Maps financing.senior_tenor_years → depreciation.financial_cost_useful_life_years
    explicitly (no silent default).
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

    # Map PPA indexation policy from string attribute on RevenueParams.
    # None (absent or explicit None) = not yet explicitly migrated; legacy path preserved.
    _policy_str = getattr(rev, "ppa_indexation_start_policy", None)
    if _policy_str is None:
        _ppa_policy = None
    else:
        try:
            _ppa_policy = PpaIndexationStartPolicy(_policy_str)
        except ValueError:
            raise ValueError(
                f"Invalid ppa_indexation_start_policy: {_policy_str!r}. "
                f"Valid values: {[e.value for e in PpaIndexationStartPolicy]}"
            )
    _ppa_index_start_date = getattr(rev, "ppa_indexation_start_date", None)

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
        ppa_indexation_start_policy=_ppa_policy,
        ppa_indexation_start_date=_ppa_index_start_date,
        merchant_price_calendar_start_year=rev.market_price_calendar_start_year,
        merchant_prices_by_calendar_year_eur_mwh=tuple(
            rev.market_prices_by_calendar_year_eur_mwh
        ),
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

    # Carry hierarchical OPEX capability through the clean contract when present.
    # Presence is the sole dispatch signal — no project-name or code inspection.
    _hcap = inputs.hierarchical_opex_capability
    _hier_model = _hcap.opex_model if _hcap is not None else None
    _hier_ext: tuple[tuple[str, tuple[float, ...]], ...] = (
        _hcap.external_annual_series if _hcap is not None else ()
    )
    # Map senior debt tenor explicitly from financing — semantically distinct from
    # financial_cost_useful_life_years (depreciation amortization driver).
    # None for flat projects where the field is not consulted by the OPEX leaf.
    _senior_tenor: int | None = (
        inputs.financing.senior_tenor_years if _hcap is not None else None
    )

    def _to_dep_item(item) -> CapexItemForDep:
        return CapexItemForDep(
            name=item.name,
            amount_keur=item.amount_keur,
            asset_class_code=item.asset_class.value,
            useful_life_override=item.useful_life_override,
        )

    # BOOK depreciable basis: hard capex + capitalised bank financing costs.
    # Evidence (Excel Dep sheet): dep_idc_keur, dep_commitment_fees_keur,
    # dep_bank_fees_keur, dep_vat_keur all non-zero. SHL IDC excluded (OPEN).
    book_capex_items_for_dep = tuple(
        _to_dep_item(item) for item in inputs.capex.book_depreciable_capex_items()
    )

    # TAX depreciable basis: hard capex only. Tax treatment of capitalised
    # financing costs is OPEN — no authoritative tax-source evidence validated yet.
    tax_capex_items_for_dep = tuple(
        _to_dep_item(item) for item in inputs.capex.tax_depreciable_capex_items()
    )

    # Explicit mapping of financing tenor → book depreciation driver.
    # OPEN: Excel Dep-sheet formula for useful life is unverified from data_only extraction.
    # No silent default: if the field is absent the AttributeError surfaces immediately.
    financial_cost_useful_life_years: int = inputs.financing.senior_tenor_years

    return OperatingModelInput(
        calendar=calendar,
        technical=technical,
        revenue=revenue,
        opex=OpexInput(
            items=opex_items,
            hierarchical_model=_hier_model,
            hierarchical_external_annual_series=_hier_ext,
            senior_debt_tenor_years=_senior_tenor,
        ),
        depreciation=DepreciationInput(
            book_capex_items_for_depreciation=book_capex_items_for_dep,
            tax_capex_items_for_depreciation=tax_capex_items_for_dep,
            financial_cost_useful_life_years=financial_cost_useful_life_years,
        ),
        source=InputProvenance(
            source_id=source_id,
            baseline_commit_sha=baseline_commit_sha,
        ),
    )
