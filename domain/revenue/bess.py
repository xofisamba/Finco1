"""Pure BESS revenue model — no waterfall dependencies."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BessParams:
    power_mw: float
    energy_mwh: float
    cycles_per_year: float
    round_trip_efficiency: float = 0.88
    availability: float = 0.98
    annual_degradation: float = 0.02
    arbitrage_spread_eur_mwh: float = 40.0
    ancillary_revenue_eur_mw_year: float = 25000.0
    capacity_revenue_eur_mw_year: float = 0.0
    augmentation_capex_keur: float = 0.0


def bess_discharged_mwh(params: BessParams, year_index: int, day_fraction: float = 1.0) -> float:
    """MWh discharged in a period, accounting for degradation and availability.

    effective_energy = energy_mwh * (1 - degradation)^(year_index - 1)
    discharged_mwh = effective_energy * cycles * availability * RTE * day_fraction
    """
    effective_energy = params.energy_mwh * (1 - params.annual_degradation) ** max(year_index - 1, 0)
    return effective_energy * params.cycles_per_year * params.availability * params.round_trip_efficiency * day_fraction


def bess_arbitrage_revenue_keur(params: BessParams, year_index: int, day_fraction: float = 1.0) -> float:
    """Arbitrage revenue in kEUR for a period.

    arbitrage_revenue = discharged_mwh * spread_eur_mwh / 1000
    """
    discharged = bess_discharged_mwh(params, year_index, day_fraction)
    return discharged * params.arbitrage_spread_eur_mwh / 1000


def bess_capacity_revenue_keur(params: BessParams, day_fraction: float = 1.0) -> float:
    """Capacity (steadfast) revenue in kEUR for a period, scaled by day_fraction."""
    return params.power_mw * params.capacity_revenue_eur_mw_year * day_fraction / 1000


def bess_ancillary_revenue_keur(params: BessParams, day_fraction: float = 1.0) -> float:
    """Ancillary services revenue in kEUR for a period, scaled by day_fraction."""
    return params.power_mw * params.ancillary_revenue_eur_mw_year * day_fraction / 1000


def bess_augmentation_cost_keur(params: BessParams, year_index: int) -> float:
    """Augmentation capex allocation for a year (linear over 10 years if capex > 0)."""
    if params.augmentation_capex_keur <= 0 or year_index > 10:
        return 0.0
    return params.augmentation_capex_keur / 10


@dataclass(frozen=True)
class BessRevenueBreakdown:
    """Period-level BESS revenue breakdown."""
    discharged_mwh: float
    arbitrage_revenue_keur: float
    capacity_revenue_keur: float
    ancillary_revenue_keur: float
    augmentation_cost_keur: float
    total_revenue_keur: float  # arbitrage + capacity + ancillary (before augmentation)
    net_revenue_keur: float   # after augmentation cost deduction


def bess_revenue_breakdown(params: BessParams, year_index: int, day_fraction: float = 1.0) -> BessRevenueBreakdown:
    """Compute full revenue breakdown for one period."""
    discharged = bess_discharged_mwh(params, year_index, day_fraction)
    arbitrage = bess_arbitrage_revenue_keur(params, year_index, day_fraction)
    capacity = bess_capacity_revenue_keur(params, day_fraction)
    ancillary = bess_ancillary_revenue_keur(params, day_fraction)
    augmentation = bess_augmentation_cost_keur(params, year_index)
    total = arbitrage + capacity + ancillary
    net = total - augmentation
    return BessRevenueBreakdown(
        discharged_mwh=discharged,
        arbitrage_revenue_keur=arbitrage,
        capacity_revenue_keur=capacity,
        ancillary_revenue_keur=ancillary,
        augmentation_cost_keur=augmentation,
        total_revenue_keur=total,
        net_revenue_keur=net,
    )


def annual_bess_revenue(params: BessParams, year_index: int) -> float:
    """Total annual net BESS revenue in kEUR (two semesters summed)."""
    # Each year has two semesters, each with day_fraction ≈ 0.5
    h1 = bess_revenue_breakdown(params, year_index, day_fraction=0.5)
    h2 = bess_revenue_breakdown(params, year_index, day_fraction=0.5)
    return h1.net_revenue_keur + h2.net_revenue_keur


__all__ = [
    "BessParams",
    "BessRevenueBreakdown",
    "bess_discharged_mwh",
    "bess_arbitrage_revenue_keur",
    "bess_capacity_revenue_keur",
    "bess_ancillary_revenue_keur",
    "bess_augmentation_cost_keur",
    "bess_revenue_breakdown",
    "annual_bess_revenue",
]
