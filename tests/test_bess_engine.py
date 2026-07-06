"""BESS revenue model tests — V4-7 (replaces broken core.engines.bess_engine import)."""
from __future__ import annotations

import pytest
from domain.revenue.bess import (
    BessParams,
    BessRevenueBreakdown,
    bess_discharged_mwh,
    bess_arbitrage_revenue_keur,
    bess_capacity_revenue_keur,
    bess_ancillary_revenue_keur,
    bess_frequency_regulation_revenue_keur,
    bess_reserve_market_revenue_keur,
    bess_fixed_contracted_revenue_keur,
    bess_augmentation_cost_keur,
    bess_state_of_health,
    bess_effective_energy_mwh,
    bess_revenue_breakdown,
    annual_bess_revenue,
)


@pytest.fixture
def standard_bess():
    return BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)


def test_soh_year1(standard_bess):
    """SoH at year 1 should be 1.0 (no degradation yet)."""
    assert bess_state_of_health(standard_bess, 1) == pytest.approx(1.0)


def test_soh_decreases(standard_bess):
    """SoH must decrease monotonically over time."""
    soh_vals = [bess_state_of_health(standard_bess, yi) for yi in range(1, 11)]
    for i in range(len(soh_vals) - 1):
        assert soh_vals[i] > soh_vals[i + 1]


def test_soh_bounded(standard_bess):
    """SoH must stay in [0, 1]."""
    for yi in range(1, 31):
        s = bess_state_of_health(standard_bess, yi)
        assert 0.0 <= s <= 1.0


def test_effective_energy_year1(standard_bess):
    """Effective energy at year 1 equals rated energy."""
    assert bess_effective_energy_mwh(standard_bess, 1) == pytest.approx(20.0)


def test_discharged_mwh_positive(standard_bess):
    """Discharged MWh must be positive for year 1."""
    d = bess_discharged_mwh(standard_bess, 1)
    assert d > 0


def test_discharged_mwh_decreases_with_degradation(standard_bess):
    """Discharged MWh should decrease as battery degrades."""
    d1 = bess_discharged_mwh(standard_bess, 1)
    d10 = bess_discharged_mwh(standard_bess, 10)
    assert d1 > d10


def test_arbitrage_positive(standard_bess):
    assert bess_arbitrage_revenue_keur(standard_bess, 1) > 0


def test_ancillary_positive(standard_bess):
    params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
                        ancillary_revenue_eur_mw_year=25000.0)
    assert bess_ancillary_revenue_keur(params) > 0


def test_capacity_zero_by_default(standard_bess):
    """Capacity revenue is zero when capacity_revenue_eur_mw_year=0."""
    assert bess_capacity_revenue_keur(standard_bess) == pytest.approx(0.0)


def test_frequency_regulation_revenue(standard_bess):
    params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
                        frequency_regulation_eur_mw_year=10000.0)
    assert bess_frequency_regulation_revenue_keur(params) == pytest.approx(10000.0 * 10.0 / 1000)


def test_reserve_market_revenue(standard_bess):
    params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
                        reserve_market_eur_mw_year=5000.0)
    assert bess_reserve_market_revenue_keur(params) == pytest.approx(5000.0 * 10.0 / 1000)


def test_fixed_contracted_revenue(standard_bess):
    params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
                        fixed_contracted_eur_mw_year=20000.0)
    assert bess_fixed_contracted_revenue_keur(params) == pytest.approx(20000.0 * 10.0 / 1000)


def test_augmentation_cost_zero_default(standard_bess):
    assert bess_augmentation_cost_keur(standard_bess, 1) == pytest.approx(0.0)


def test_augmentation_cost_spread_over_10_years():
    params = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
                        augmentation_capex_keur=1000.0)
    assert bess_augmentation_cost_keur(params, 1) == pytest.approx(100.0)
    assert bess_augmentation_cost_keur(params, 10) == pytest.approx(100.0)
    assert bess_augmentation_cost_keur(params, 11) == pytest.approx(0.0)


def test_revenue_breakdown_fields(standard_bess):
    bd = bess_revenue_breakdown(standard_bess, 1)
    assert isinstance(bd, BessRevenueBreakdown)
    assert bd.total_revenue_keur >= 0
    assert bd.net_revenue_keur == pytest.approx(bd.total_revenue_keur - bd.augmentation_cost_keur)
    assert 0.0 <= bd.state_of_health <= 1.0


def test_annual_bess_revenue_positive(standard_bess):
    rev = annual_bess_revenue(standard_bess, 1)
    assert rev > 0


def test_all_revenue_streams():
    """BessParams with all revenue streams non-zero should sum correctly."""
    params = BessParams(
        power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
        ancillary_revenue_eur_mw_year=25000.0,
        capacity_revenue_eur_mw_year=10000.0,
        frequency_regulation_eur_mw_year=5000.0,
        reserve_market_eur_mw_year=3000.0,
        fixed_contracted_eur_mw_year=8000.0,
    )
    bd = bess_revenue_breakdown(params, 1, day_fraction=1.0)
    expected_total = (bd.arbitrage_revenue_keur + bd.capacity_revenue_keur +
                      bd.ancillary_revenue_keur + bd.frequency_regulation_keur +
                      bd.reserve_market_keur + bd.fixed_contracted_keur)
    assert bd.total_revenue_keur == pytest.approx(expected_total)
