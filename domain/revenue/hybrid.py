"""Pure hybrid (solar+BESS or wind+BESS) revenue model.

No LP dispatch, no waterfall dependencies.  Period-level revenue from
generation and BESS stacked.
"""
from dataclasses import dataclass, field
from typing import Optional

from domain.revenue.bess import (
    BessParams,
    BessRevenueBreakdown,
    bess_revenue_breakdown,
)


@dataclass(frozen=True)
class HybridInputs:
    """Combined technical inputs for a hybrid project.

    Contains solar/wind generation params AND BESS params.
    """
    # --- Generation ---
    solar_capacity_mw: float = 0.0
    wind_capacity_mw: float = 0.0
    # Operating hours for yield scenarios (same semantics as TechnicalParams)
    operating_hours_p50: float = 0.0
    operating_hours_p90_10y: float = 0.0
    pv_degradation: float = 0.004
    wind_degradation: float = 0.005
    plant_availability: float = 0.99
    grid_availability: float = 0.99
    # Grid curtailment
    curtailment_pct: float = 0.0
    grid_limit_mw: Optional[float] = None  # None = no limit

    # --- Revenue ---
    ppa_base_tariff_eur_mwh: float = 0.0
    ppa_escalation: float = 0.02
    ppa_term_years: float = 10.0
    market_price_eur_mwh: float = 0.0
    co2_price_eur_mwh: float = 0.0
    co2_enabled: bool = False

    # --- BESS ---
    bess: Optional[BessParams] = None

    @property
    def combined_availability(self) -> float:
        return self.plant_availability * self.grid_availability

    @property
    def total_capacity_mw(self) -> float:
        return self.solar_capacity_mw + self.wind_capacity_mw

    @property
    def effective_grid_limit_mw(self) -> float:
        """Grid limit: grid_limit_mw if set, else total_capacity_mw."""
        if self.grid_limit_mw is not None:
            return self.grid_limit_mw
        return self.total_capacity_mw


@dataclass(frozen=True)
class HybridRevenueBreakdown:
    """Period-level revenue breakdown for a hybrid project."""
    # Generation
    solar_generation_mwh: float
    wind_generation_mwh: float
    total_generation_mwh: float
    clipped_generation_mwh: float
    curtailment_mwh: float
    # Revenue components
    ppa_revenue_keur: float
    merchant_revenue_keur: float
    co2_revenue_keur: float
    # BESS
    bess_breakdown: Optional[BessRevenueBreakdown]
    bess_revenue_keur: float
    # Totals
    gross_revenue_keur: float
    net_revenue_keur: float


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------

def _degradation_factor(degradation: float, year_index: int) -> float:
    return (1 - degradation) ** max(year_index - 1, 0)


def hybrid_solar_generation_mwh(
    inputs: HybridInputs,
    year_index: int,
    day_fraction: float = 1.0,
) -> float:
    """Solar MWh generated in a period before curtailment."""
    if inputs.solar_capacity_mw <= 0 or inputs.operating_hours_p50 <= 0:
        return 0.0
    deg = _degradation_factor(inputs.pv_degradation, year_index)
    avail = inputs.combined_availability
    return (
        inputs.solar_capacity_mw
        * inputs.operating_hours_p50
        * day_fraction
        * avail
        * deg
    )


def hybrid_wind_generation_mwh(
    inputs: HybridInputs,
    year_index: int,
    day_fraction: float = 1.0,
) -> float:
    """Wind MWh generated in a period before curtailment."""
    if inputs.wind_capacity_mw <= 0 or inputs.operating_hours_p50 <= 0:
        return 0.0
    deg = _degradation_factor(inputs.wind_degradation, year_index)
    avail = inputs.combined_availability
    return (
        inputs.wind_capacity_mw
        * inputs.operating_hours_p50
        * day_fraction
        * avail
        * deg
    )


def hybrid_total_generation_mwh(
    inputs: HybridInputs,
    year_index: int,
    day_fraction: float = 1.0,
) -> float:
    """Total (solar + wind) MWh before grid curtailment."""
    solar = hybrid_solar_generation_mwh(inputs, year_index, day_fraction)
    wind = hybrid_wind_generation_mwh(inputs, year_index, day_fraction)
    return solar + wind


def hybrid_clipped_generation_mwh(
    inputs: HybridInputs,
    year_index: int,
    day_fraction: float = 1.0,
) -> float:
    """Generation after grid limit clipping."""
    total = hybrid_total_generation_mwh(inputs, year_index, day_fraction)
    grid_limit = inputs.effective_grid_limit_mw
    if grid_limit <= 0:
        return total
    # Convert limit to MWh equivalent using operating hours
    operating_hours = inputs.operating_hours_p50 or inputs.operating_hours_p90_10y
    if operating_hours <= 0:
        return total
    max_mwh = grid_limit * operating_hours * day_fraction
    clipped = min(total, max_mwh)
    return clipped


# ---------------------------------------------------------------------------
# Revenue calculation
# ---------------------------------------------------------------------------

def _indexed_tariff(inputs: HybridInputs, year_index: int) -> float:
    return inputs.ppa_base_tariff_eur_mwh * (1 + inputs.ppa_escalation) ** (year_index - 1)


def hybrid_period_revenue(
    inputs: HybridInputs,
    year_index: int,
    day_fraction: float = 1.0,
    ppa_active: bool = True,
    merchant_price_eur_mwh: Optional[float] = None,
) -> HybridRevenueBreakdown:
    """Compute full revenue breakdown for one period."""
    # Generation
    solar_gen = hybrid_solar_generation_mwh(inputs, year_index, day_fraction)
    wind_gen = hybrid_wind_generation_mwh(inputs, year_index, day_fraction)
    total_gen = solar_gen + wind_gen

    clipped_gen = hybrid_clipped_generation_mwh(inputs, year_index, day_fraction)
    curtailment = max(0.0, total_gen - clipped_gen)

    # PPA vs merchant split
    tariff = _indexed_tariff(inputs, year_index)
    mkt_price = merchant_price_eur_mwh if merchant_price_eur_mwh is not None else inputs.market_price_eur_mwh

    if ppa_active:
        ppa_gen = clipped_gen  # assume all goes to PPA up to grid limit
        merchant_gen = 0.0
    else:
        ppa_gen = 0.0
        merchant_gen = clipped_gen

    ppa_revenue_keur = ppa_gen * tariff / 1000
    merchant_revenue_keur = merchant_gen * mkt_price / 1000

    # CO2 certificates
    co2_rev_keur = 0.0
    if inputs.co2_enabled:
        co2_rev_keur = clipped_gen * inputs.co2_price_eur_mwh / 1000

    # BESS
    bess_breakdown: Optional[BessRevenueBreakdown] = None
    bess_rev_keur = 0.0
    if inputs.bess is not None:
        bess_breakdown = bess_revenue_breakdown(inputs.bess, year_index, day_fraction)
        bess_rev_keur = bess_breakdown.net_revenue_keur

    gross = ppa_revenue_keur + merchant_revenue_keur + co2_rev_keur
    net = gross + bess_rev_keur

    return HybridRevenueBreakdown(
        solar_generation_mwh=solar_gen,
        wind_generation_mwh=wind_gen,
        total_generation_mwh=total_gen,
        clipped_generation_mwh=clipped_gen,
        curtailment_mwh=curtailment,
        ppa_revenue_keur=ppa_revenue_keur,
        merchant_revenue_keur=merchant_revenue_keur,
        co2_revenue_keur=co2_rev_keur,
        bess_breakdown=bess_breakdown,
        bess_revenue_keur=bess_rev_keur,
        gross_revenue_keur=gross,
        net_revenue_keur=net,
    )


# ---------------------------------------------------------------------------
# Annual aggregation helpers
# ---------------------------------------------------------------------------

def annual_hybrid_revenue(
    inputs: HybridInputs,
    year_index: int,
) -> HybridRevenueBreakdown:
    """Aggregate two semi-annual periods into one year."""
    h1 = hybrid_period_revenue(inputs, year_index, day_fraction=0.5, ppa_active=True)
    h2 = hybrid_period_revenue(inputs, year_index, day_fraction=0.5, ppa_active=True)
    return HybridRevenueBreakdown(
        solar_generation_mwh=h1.solar_generation_mwh + h2.solar_generation_mwh,
        wind_generation_mwh=h1.wind_generation_mwh + h2.wind_generation_mwh,
        total_generation_mwh=h1.total_generation_mwh + h2.total_generation_mwh,
        clipped_generation_mwh=h1.clipped_generation_mwh + h2.clipped_generation_mwh,
        curtailment_mwh=h1.curtailment_mwh + h2.curtailment_mwh,
        ppa_revenue_keur=h1.ppa_revenue_keur + h2.ppa_revenue_keur,
        merchant_revenue_keur=h1.merchant_revenue_keur + h2.merchant_revenue_keur,
        co2_revenue_keur=h1.co2_revenue_keur + h2.co2_revenue_keur,
        bess_breakdown=None,  # annual doesn't expose per-period BESS breakdown
        bess_revenue_keur=h1.bess_revenue_keur + h2.bess_revenue_keur,
        gross_revenue_keur=h1.gross_revenue_keur + h2.gross_revenue_keur,
        net_revenue_keur=h1.net_revenue_keur + h2.net_revenue_keur,
    )


__all__ = [
    "HybridInputs",
    "HybridRevenueBreakdown",
    "hybrid_solar_generation_mwh",
    "hybrid_wind_generation_mwh",
    "hybrid_total_generation_mwh",
    "hybrid_clipped_generation_mwh",
    "hybrid_period_revenue",
    "annual_hybrid_revenue",
]
