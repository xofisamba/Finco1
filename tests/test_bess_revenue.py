import pytest
from domain.revenue.bess import (
    BessParams, bess_discharged_mwh, bess_arbitrage_revenue_keur,
    bess_ancillary_revenue_keur, bess_capacity_revenue_keur, bess_revenue_breakdown
)


def test_bess_zero_cycles_has_zero_arbitrage_revenue():
    p = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=0)
    assert bess_arbitrage_revenue_keur(p, 1) == 0.0


def test_bess_higher_spread_increases_arbitrage_revenue():
    p40 = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=300, arbitrage_spread_eur_mwh=40)
    p80 = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=300, arbitrage_spread_eur_mwh=80)
    assert bess_arbitrage_revenue_keur(p80, 1) > bess_arbitrage_revenue_keur(p40, 1)


def test_bess_lower_rte_decreases_discharged_mwh():
    p90 = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=300, round_trip_efficiency=0.90, availability=1.0)
    p80 = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=300, round_trip_efficiency=0.80, availability=1.0)
    assert bess_discharged_mwh(p80, 1) < bess_discharged_mwh(p90, 1)


def test_bess_ancillary_revenue_is_power_based():
    p = BessParams(power_mw=100, energy_mwh=200, cycles_per_year=300, ancillary_revenue_eur_mw_year=25000)
    # day_fraction=1.0: 100 MW * 25000 / 1000 = 2500 kEUR
    assert bess_ancillary_revenue_keur(p, 1.0) == 2500.0
    # day_fraction=0.5: 100 * 25000 * 0.5 / 1000 = 1250 kEUR
    assert bess_ancillary_revenue_keur(p, 0.5) == 1250.0


def test_bess_degradation_reduces_discharged_mwh_over_time():
    p = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=300, annual_degradation=0.02, availability=1.0, round_trip_efficiency=1.0)
    y1 = bess_discharged_mwh(p, 1)
    y10 = bess_discharged_mwh(p, 10)
    assert y10 < y1


def test_bess_revenue_breakdown_sums_to_total():
    p = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=300, availability=1.0, round_trip_efficiency=0.88, arbitrage_spread_eur_mwh=40, ancillary_revenue_eur_mw_year=25000)
    br = bess_revenue_breakdown(p, 1, 1.0)
    expected_total = br.arbitrage_revenue_keur + br.ancillary_revenue_keur + br.capacity_revenue_keur
    assert abs(br.total_revenue_keur - expected_total) < 0.01


def test_bess_first_year_hand_checkable():
    # Hand-check example from spec:
    # power_mw=50, energy_mwh=200, cycles=300, RTE=0.90, availability=1.0, spread=40
    # discharged_mwh = 200 * 300 * 0.90 = 54,000 MWh
    # arbitrage = 54000 * 40 / 1000 = 2,160 kEUR
    p = BessParams(power_mw=50, energy_mwh=200, cycles_per_year=300, round_trip_efficiency=0.90, availability=1.0, arbitrage_spread_eur_mwh=40, ancillary_revenue_eur_mw_year=0, capacity_revenue_eur_mw_year=0)
    br = bess_revenue_breakdown(p, 1, 1.0)
    assert abs(br.discharged_mwh - 54000) < 1
    assert abs(br.arbitrage_revenue_keur - 2160) < 1
    assert br.ancillary_revenue_keur == 0
    assert br.total_revenue_keur == 2160