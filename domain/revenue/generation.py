"""Generation calculation - period-based production in MWh.

Matches Excel CF sheet row 21 formula:
    G21 = $B21 × G$7 × G$6 × G$20 × (1-G$19) × (1-Degradation)

NOTE: This module contains PURE functions only.
Caching is handled in utils/cache.py at the app layer.
"""
from dataclasses import dataclass
from typing import Sequence, Optional
from domain.inputs import TechnicalParams, ProjectInputs
from domain.period_engine import PeriodEngine, PeriodMeta


@dataclass(frozen=True)
class RevenuePeriodBreakdown:
    """Period-level revenue decomposition for audit and export.

    Fields:
        period_index: Model period index (0-based)
        operating_period_index: 0-based operating period within operating life
        period_end_date: End date of this period (for Excel comparison)
        production_mwh: Generation in MWh
        effective_power_price_eur_per_mwh: PPA or market price for this period
        power_revenue_keur: Generation × price / 1000
        co2_sales_eur_per_mwh: CO2 price from schedule (EUR/MWh)
        co2_sales_revenue_keur: Production × co2_eur / 1000
        balancing_cost_eur_per_mwh: Balancing cost from schedule (EUR/MWh)
        balancing_cost_keur: Production × balancing_eur / 1000
        total_revenue_keur: power_revenue - balancing + co2
    """
    period_index: int
    operating_period_index: int
    period_end_date: 'date'
    production_mwh: float
    effective_power_price_eur_per_mwh: float
    power_revenue_keur: float
    co2_sales_eur_per_mwh: float
    co2_sales_revenue_keur: float
    balancing_cost_eur_per_mwh: float
    balancing_cost_keur: float
    total_revenue_keur: float


def period_generation(
    tech: TechnicalParams,
    periods: Sequence[PeriodMeta],
    year_index: int,
    yield_scenario: str = "P50",
) -> float:
    """Calculate annual generation (sum of H1 + H2) in MWh.

    For semi-annual models, year has 2 periods. Sum both H1 and H2.

    Args:
        tech: Technical parameters
        periods: All periods (for looking up year_index)
        year_index: Year index (1-based, 1=Y1)
        yield_scenario: "P50" or "P90-10y"

    Returns:
        Generation in MWh for this year (H1 + H2)
    """
    # Find all operation periods for this year_index (H1 + H2)
    op_periods = [p for p in periods if p.is_operation and p.year_index == year_index]
    if not op_periods:
        return 0.0

    # Operating hours based on scenario
    if yield_scenario == "P90-10y":
        hours = tech.operating_hours_p90_10y
    else:
        hours = tech.operating_hours_p50

    # Combined availability (plant × grid)
    availability = tech.plant_availability * tech.grid_availability

    # Degradation factor: (1 - degradation)^(year_index - 1)
    degradation_factor = (1 - tech.pv_degradation) ** (year_index - 1)

    # Sum generation for all periods in this year (H1 + H2)
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
    """Calculate annual generation in MWh.
    
    Simplified version that doesn't need period engine.
    Uses P50 or P90-10y hours and assumes full year (no degradation in year 1).
    
    Args:
        tech: Technical parameters
        year_index: Year (1-based, 1=Y1)
        yield_scenario: "P50" or "P90-10y"
    
    Returns:
        Annual generation in MWh
    """
    if yield_scenario == "P90-10y":
        hours = tech.operating_hours_p90_10y
    else:
        hours = tech.operating_hours_p50
    
    availability = tech.plant_availability * tech.grid_availability
    
    # Degradation from previous years
    degradation = (1 - tech.pv_degradation) ** (year_index - 1)
    
    return tech.capacity_mw * hours * availability * degradation


def period_revenue(
    tech: TechnicalParams,
    period: PeriodMeta,
    ppa_tariff_eur_mwh: float,
    market_price_eur_mwh: Optional[float] = None,
    ppa_active: bool = True,
) -> float:
    """Calculate revenue for a single period.
    
    Args:
        tech: Technical parameters
        period: Period metadata
        ppa_tariff_eur_mwh: PPA tariff in EUR/MWh
        market_price_eur_mwh: Market price if not PPA
        ppa_active: Whether PPA tariff applies
    
    Returns:
        Revenue in kEUR for this period
    """
    if not period.is_operation:
        return 0.0
    
    # Generation for this period
    if period.period_in_year == 1:
        # H1
        hours = tech.operating_hours_p50 if tech.yield_scenario == "P_50" else tech.operating_hours_p90_10y
    else:
        # H2 (same hours)
        hours = tech.operating_hours_p50 if tech.yield_scenario == "P_50" else tech.operating_hours_p90_10y
    
    availability = tech.plant_availability * tech.grid_availability
    degradation = (1 - tech.pv_degradation) ** (period.year_index - 1)
    
    generation_mwh = tech.capacity_mw * hours * period.day_fraction * availability * degradation
    
    # Revenue = generation × price
    if ppa_active:
        price = ppa_tariff_eur_mwh
    elif market_price_eur_mwh is not None:
        price = market_price_eur_mwh
    else:
        price = ppa_tariff_eur_mwh  # fallback
    
    revenue_keur = generation_mwh * price / 1000
    
    return revenue_keur


def full_generation_schedule(
    inputs: ProjectInputs,
    engine: PeriodEngine,
    yield_scenario: str = "P50",
) -> dict[int, float]:
    """Generate full schedule of period generation in MWh.
    
    Args:
        inputs: Project inputs
        engine: Period engine
        yield_scenario: "P50" or "P90-10y"
    
    Returns:
        Dict mapping period_index → generation_MWh
    """
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


def full_revenue_schedule(
    inputs: ProjectInputs,
    engine: PeriodEngine,
) -> dict[int, float]:
    """Generate full schedule of period revenue in kEUR.

    Revenue includes:
    - PPA revenue (during PPA term)
    - Spot/market revenue (after PPA)
    - Balancing cost deduction (PV)
    - CO2 certificates from schedule

    Args:
        inputs: Project inputs
        engine: Period engine

    Returns:
        Dict mapping period_index → revenue_kEUR
    """
    revenue = {}
    operating_period_index = 0  # 0-based index of current operation period

    for period in engine.periods():
        if not period.is_operation:
            revenue[period.index] = 0.0
            continue

        # Generation
        if inputs.technical.yield_scenario == "P_50":
            hours = inputs.technical.operating_hours_p50
        else:
            hours = inputs.technical.operating_hours_p90_10y

        availability = inputs.technical.combined_availability
        degradation = (1 - inputs.technical.pv_degradation) ** (period.year_index - 1)

        generation_mwh = (
            inputs.technical.capacity_mw
            * hours
            * period.day_fraction
            * availability
            * degradation
        )

        # Effective power price (PPA or market)
        if period.is_ppa_active:
            effective_price = inputs.revenue.tariff_at_year(period.year_index)
        else:
            effective_price = inputs.revenue.market_price_at_year(period.year_index)

        power_revenue_keur = generation_mwh * effective_price / 1000

        # Phase 7G: Use generic schedule-based inputs (operating_period_index derived explicitly)
        balancing_eur_mwh = inputs.revenue.balancing_cost_schedule.value_for_period(
            operating_period_index=operating_period_index,
            operating_year_index=period.year_index,
            period_in_year=period.period_in_year,
        )
        co2_eur_mwh = inputs.revenue.co2_sales_schedule.value_for_period(
            operating_period_index=operating_period_index,
            operating_year_index=period.year_index,
            period_in_year=period.period_in_year,
        )

        balancing_cost_keur = generation_mwh * balancing_eur_mwh / 1000
        co2_revenue_keur = generation_mwh * co2_eur_mwh / 1000

        # PV balancing (% of revenue) — still used for solar BESS
        balancing_deduction = power_revenue_keur * inputs.revenue.balancing_cost_pv

        revenue_keur = power_revenue_keur - balancing_deduction - balancing_cost_keur + co2_revenue_keur
        revenue[period.index] = revenue_keur

        operating_period_index += 1

    return revenue


def full_revenue_breakdown_schedule(
    inputs: ProjectInputs,
    engine: PeriodEngine,
) -> list[RevenuePeriodBreakdown]:
    """Generate full schedule of period revenue decomposition.

    Returns a list of RevenuePeriodBreakdown for each operation period.
    Use this for audit/export rather than full_revenue_schedule when
    decomposition fields are needed.

    Args:
        inputs: Project inputs
        engine: Period engine

    Returns:
        List of RevenuePeriodBreakdown ordered by operation period
    """
    breakdowns = []
    operating_period_index = 0

    for period in engine.periods():
        if not period.is_operation:
            continue

        # Generation
        if inputs.technical.yield_scenario == "P_50":
            hours = inputs.technical.operating_hours_p50
        else:
            hours = inputs.technical.operating_hours_p90_10y

        availability = inputs.technical.combined_availability
        degradation = (1 - inputs.technical.pv_degradation) ** (period.year_index - 1)

        generation_mwh = (
            inputs.technical.capacity_mw
            * hours
            * period.day_fraction
            * availability
            * degradation
        )

        # Effective power price
        if period.is_ppa_active:
            effective_price = inputs.revenue.tariff_at_year(period.year_index)
        else:
            effective_price = inputs.revenue.market_price_at_year(period.year_index)

        power_revenue_keur = generation_mwh * effective_price / 1000

        # Schedule values (operating_period_index is explicit, not derived from period_index)
        co2_eur_mwh = inputs.revenue.co2_sales_schedule.value_for_period(
            operating_period_index=operating_period_index,
            operating_year_index=period.year_index,
            period_in_year=period.period_in_year,
        )
        balancing_eur_mwh = inputs.revenue.balancing_cost_schedule.value_for_period(
            operating_period_index=operating_period_index,
            operating_year_index=period.year_index,
            period_in_year=period.period_in_year,
        )

        co2_revenue_keur = generation_mwh * co2_eur_mwh / 1000
        balancing_cost_keur = generation_mwh * balancing_eur_mwh / 1000

        # PV balancing (% of revenue)
        balancing_deduction = power_revenue_keur * inputs.revenue.balancing_cost_pv

        total_revenue_keur = power_revenue_keur - balancing_deduction - balancing_cost_keur + co2_revenue_keur

        breakdowns.append(RevenuePeriodBreakdown(
            period_index=period.index,
            operating_period_index=operating_period_index,
            period_end_date=period.end_date,
            production_mwh=generation_mwh,
            effective_power_price_eur_per_mwh=effective_price,
            power_revenue_keur=power_revenue_keur,
            co2_sales_eur_per_mwh=co2_eur_mwh,
            co2_sales_revenue_keur=co2_revenue_keur,
            balancing_cost_eur_per_mwh=balancing_eur_mwh,
            balancing_cost_keur=balancing_cost_keur,
            total_revenue_keur=total_revenue_keur,
        ))

        operating_period_index += 1

    return breakdowns