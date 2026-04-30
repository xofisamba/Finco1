"""Generation calculation - period-based production in MWh.

Matches Excel CF sheet row 21 formula:
    G21 = $B21 × G$7 × G$6 × G$20 × (1-G$19) × (1-Degradation)

Where:
- B21: capacity (MW)
- G7: day_fraction (period days / 365 or leap-year denominator)
- G6: operation flag (1 if operating, 0 if not)
- G20: operating hours for yield scenario
- G19: curtailment assumption
- Degradation: annual degradation factor

NOTE: This module contains PURE functions only.
Caching is handled in the app layer.
"""
from typing import Sequence, Optional
from domain.inputs import TechnicalParams, ProjectInputs
from domain.period_engine import PeriodEngine, PeriodMeta


def period_generation(
    tech: TechnicalParams,
    periods: Sequence[PeriodMeta],
    year_index: int,
    yield_scenario: str = "P50",
) -> float:
    """Calculate annual generation (sum of all operating periods in one year)."""
    op_periods = [p for p in periods if p.is_operation and p.year_index == year_index]
    if not op_periods:
        return 0.0

    if yield_scenario == "P90-10y":
        hours = tech.operating_hours_p90_10y
    else:
        hours = tech.operating_hours_p50

    availability = tech.plant_availability * tech.grid_availability
    degradation_factor = (1 - tech.pv_degradation) ** (year_index - 1)

    total_generation = 0.0
    for period in op_periods:
        generation = (
            tech.capacity_mw
            * hours
            * period.day_fraction
            * availability
            * degradation_factor
        )
        total_generation += generation

    return total_generation


def annual_generation_mwh(
    tech: TechnicalParams,
    year_index: int,
    yield_scenario: str = "P50",
) -> float:
    """Calculate annual generation in MWh."""
    if yield_scenario == "P90-10y":
        hours = tech.operating_hours_p90_10y
    else:
        hours = tech.operating_hours_p50

    availability = tech.plant_availability * tech.grid_availability
    degradation = (1 - tech.pv_degradation) ** (year_index - 1)

    return tech.capacity_mw * hours * availability * degradation


def period_revenue(
    tech: TechnicalParams,
    period: PeriodMeta,
    ppa_tariff_eur_mwh: float,
    market_price_eur_mwh: Optional[float] = None,
    ppa_active: bool = True,
) -> float:
    """Calculate revenue for a single period."""
    if not period.is_operation:
        return 0.0

    if period.period_in_year == 1:
        hours = tech.operating_hours_p50 if tech.yield_scenario == "P_50" else tech.operating_hours_p90_10y
    else:
        hours = tech.operating_hours_p50 if tech.yield_scenario == "P_50" else tech.operating_hours_p90_10y

    availability = tech.plant_availability * tech.grid_availability
    degradation = (1 - tech.pv_degradation) ** (period.year_index - 1)

    generation_mwh = tech.capacity_mw * hours * period.day_fraction * availability * degradation

    if ppa_active:
        price = ppa_tariff_eur_mwh
    elif market_price_eur_mwh is not None:
        price = market_price_eur_mwh
    else:
        price = ppa_tariff_eur_mwh

    return generation_mwh * price / 1000


def full_generation_schedule(
    inputs: ProjectInputs,
    engine: PeriodEngine,
    yield_scenario: str = "P50",
) -> dict[int, float]:
    """Generate full schedule of period generation in MWh."""
    schedule = {}

    for period in engine.periods():
        if not period.is_operation:
            schedule[period.index] = 0.0
            continue

        if yield_scenario == "P90-10y":
            hours = inputs.technical.operating_hours_p90_10y
        else:
            hours = inputs.technical.operating_hours_p50

        availability = inputs.technical.combined_availability
        degradation = (1 - inputs.technical.pv_degradation) ** (period.year_index - 1)

        generation = (
            inputs.technical.capacity_mw
            * hours
            * period.day_fraction
            * availability
            * degradation
        )

        schedule[period.index] = generation

    return schedule


def _period_energy_revenue_keur(
    *,
    generation_mwh: float,
    ppa_tariff: float,
    market_price: float,
    ppa_active: bool,
    ppa_share: float,
) -> float:
    """Return energy revenue for one period before balancing and certificates.

    `ppa_production_share` existed in the input schema but was previously
    ignored. Excel models commonly support selling only a portion of generation
    under the PPA and the balance at market. This helper makes that behavior
    explicit while preserving the previous result when ppa_share is 1.0.
    """
    bounded_ppa_share = min(max(ppa_share, 0.0), 1.0)
    if ppa_active:
        ppa_generation = generation_mwh * bounded_ppa_share
        merchant_generation = generation_mwh - ppa_generation
        return (ppa_generation * ppa_tariff + merchant_generation * market_price) / 1000
    return generation_mwh * market_price / 1000


def revenue_decomposition_schedule(
    inputs: ProjectInputs,
    engine: PeriodEngine,
) -> dict[int, dict[str, float | bool]]:
    """Generate period-level revenue decomposition for calibration diagnostics."""
    decompositions: dict[int, dict[str, float | bool]] = {}
    generation_schedule = full_generation_schedule(inputs, engine)

    for period in engine.periods():
        generation_mwh = generation_schedule[period.index]
        if not period.is_operation:
            decompositions[period.index] = {
                "is_operation": False,
                "is_ppa_active": False,
                "generation_mwh": 0.0,
                "ppa_tariff_eur_mwh": 0.0,
                "market_price_eur_mwh": 0.0,
                "energy_revenue_keur": 0.0,
                "balancing_cost_pv_keur": 0.0,
                "balancing_cost_wind_keur": 0.0,
                "co2_revenue_keur": 0.0,
                "revenue_keur": 0.0,
            }
            continue

        tariff = inputs.revenue.tariff_at_year(period.year_index)
        market_price = inputs.revenue.market_price_at_year(period.year_index)
        energy_revenue_keur = _period_energy_revenue_keur(
            generation_mwh=generation_mwh,
            ppa_tariff=tariff,
            market_price=market_price,
            ppa_active=period.is_ppa_active,
            ppa_share=inputs.revenue.ppa_production_share,
        )
        balancing_cost_pv_keur = energy_revenue_keur * inputs.revenue.balancing_cost_pv
        balancing_cost_wind_keur = 0.0
        if inputs.revenue.balancing_cost_wind_eur_mwh > 0:
            balancing_cost_wind_keur = generation_mwh * inputs.revenue.balancing_cost_wind_eur_mwh / 1000
        co2_revenue_keur = 0.0
        if inputs.revenue.co2_enabled:
            co2_revenue_keur = generation_mwh * inputs.revenue.co2_price_eur / 1000

        decompositions[period.index] = {
            "is_operation": True,
            "is_ppa_active": period.is_ppa_active,
            "generation_mwh": generation_mwh,
            "ppa_tariff_eur_mwh": tariff,
            "market_price_eur_mwh": market_price,
            "energy_revenue_keur": energy_revenue_keur,
            "balancing_cost_pv_keur": balancing_cost_pv_keur,
            "balancing_cost_wind_keur": balancing_cost_wind_keur,
            "co2_revenue_keur": co2_revenue_keur,
            "revenue_keur": energy_revenue_keur - balancing_cost_pv_keur - balancing_cost_wind_keur + co2_revenue_keur,
        }

    return decompositions


def full_revenue_schedule(
    inputs: ProjectInputs,
    engine: PeriodEngine,
) -> dict[int, float]:
    """Generate full schedule of period revenue in kEUR."""
    return {
        period_index: float(decomposition["revenue_keur"])
        for period_index, decomposition in revenue_decomposition_schedule(inputs, engine).items()
    }


__all__ = [
    "period_generation",
    "annual_generation_mwh",
    "period_revenue",
    "full_generation_schedule",
    "full_revenue_schedule",
    "revenue_decomposition_schedule",
]
