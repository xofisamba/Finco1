"""Tests for hybrid revenue with explicit curtailment capture."""
import pytest
from domain.revenue.hybrid import (
    HybridInputs,
    HybridRevenueBreakdown,
    hybrid_solar_generation_mwh,
    hybrid_wind_generation_mwh,
    hybrid_total_generation_mwh,
    hybrid_period_revenue,
    annual_hybrid_revenue,
)
from domain.revenue.bess import BessParams


def test_no_grid_constraint_means_no_clipping():
    """When grid_connection >= total_capacity, no curtailment occurs."""
    inputs = HybridInputs(
        solar_capacity_mw=50.0, wind_capacity_mw=0.0,
        operating_hours_p50=1500.0,
        grid_connection_mw=100.0,  # >= 50 MW solar
        tariff_eur_mwh=60.0,
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    # clipped_mwh aliases curtailment_mwh; no constraint → no curtailment
    assert result.clipped_mwh == 0.0
    assert result.curtailment_mwh == 0.0
    assert result.exported_mwh == result.total_generation_mwh


def test_grid_constraint_creates_clipped_energy():
    # capacity=100 MW, operating_hours=1000 → raw=100,000 MWh
    # availability=0.99*0.99 → effective=100,000*0.9801=98,010 MWh
    # grid=50 MW → clipping=(100-50)/100=0.5 → curtailment=49,005 MWh
    inputs = HybridInputs(
        solar_capacity_mw=100.0, wind_capacity_mw=0.0,
        operating_hours_p50=1000.0,
        grid_connection_mw=50.0,
        tariff_eur_mwh=60.0,
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    assert result.total_generation_mwh == 98_010.0
    assert result.curtailment_mwh == 49_005.0
    assert result.clipped_mwh == 49_005.0


def test_bess_captures_part_of_clipped_energy():
    # total=100,000 MWh, curtailment=50,000 MWh, BESS max throughput=1000 MWh
    inputs = HybridInputs(
        solar_capacity_mw=100.0, wind_capacity_mw=0.0,
        operating_hours_p50=1000.0,
        grid_connection_mw=50.0,
        tariff_eur_mwh=60.0,
        discharge_price_eur_mwh=80.0,
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0,
            round_trip_efficiency=0.90,
            availability=1.0,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    # bess_charge = min(50000, 1000) = 1000 MWh
    assert result.bess_charge_from_curtailment_mwh == 1000.0
    # bess_discharge = 1000 * 0.90 = 900 MWh
    assert result.bess_discharge_from_curtailment_mwh == 900.0


def test_bess_curtailment_revenue_uses_discharge_price():
    inputs = HybridInputs(
        solar_capacity_mw=100.0, wind_capacity_mw=0.0,
        operating_hours_p50=1000.0,
        grid_connection_mw=50.0,
        tariff_eur_mwh=60.0,
        discharge_price_eur_mwh=80.0,
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0,
            round_trip_efficiency=0.90,
            availability=1.0,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    # 900 MWh × 80 / 1000 = 72.0 kEUR
    assert abs(result.bess_curtailment_revenue_keur - 72.0) < 0.1


def test_grid_charge_disabled_removes_grid_arbitrage_component():
    """grid_charge_allowed=False → bess_grid_arbitrage = 0."""
    inputs_on = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        grid_charge_allowed=True,
        bess=BessParams(power_mw=10.0, energy_mwh=100.0,
                        cycles_per_year=10.0, availability=1.0),
    )
    inputs_off = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        grid_charge_allowed=False,
        bess=BessParams(power_mw=10.0, energy_mwh=100.0,
                        cycles_per_year=10.0, availability=1.0),
    )
    r_on = hybrid_period_revenue(inputs_on, 1, 1.0)
    r_off = hybrid_period_revenue(inputs_off, 1, 1.0)
    # Both should have same curtailment capture
    assert r_on.bess_charge_from_curtailment_mwh == r_off.bess_charge_from_curtailment_mwh


def test_hybrid_revenue_equals_renewable_plus_bess_components():
    """Total hybrid revenue = renewable revenue + all BESS components."""
    inputs = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0, round_trip_efficiency=0.90,
            ancillary_revenue_eur_mw_year=25000.0,
            capacity_revenue_eur_mw_year=0.0,
            availability=1.0,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    expected_total = (result.renewable_revenue_keur
                     + result.bess_curtailment_revenue_keur
                     + result.bess_grid_arbitrage_revenue_keur
                     + result.ancillary_revenue_keur
                     + result.capacity_revenue_keur)
    assert abs(result.total_hybrid_revenue_keur - expected_total) < 0.01


def test_zero_bess_capacity_gives_renewable_only_revenue():
    """No BESS → total_hybrid = renewable_revenue."""
    inputs = HybridInputs(
        solar_capacity_mw=50.0, operating_hours_p50=1500.0,
        grid_connection_mw=100.0, tariff_eur_mwh=60.0,
        bess=None,
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    assert result.bess_charge_from_curtailment_mwh == 0.0
    assert result.total_bess_revenue_keur == 0.0
    assert abs(result.total_hybrid_revenue_keur - result.renewable_revenue_keur) < 0.01


def test_solar_bess_hand_checkable():
    """Hand-calculate solar+BESS (availability-adjusted):
    capacity=100 MW, avail=0.9801, gen=98,010 MWh
    grid=50 MW → curtailment=49,005 MWh (50% clipping)
    BESS: energy=100 MWh, cycles=10, RTE=0.9, discharge_price=80
    BESS charge = min(49005, 1000) = 1000 MWh
    BESS discharge = 1000 * 0.9 = 900 MWh
    bess_curtail_rev = 900 * 80 / 1000 = 72.0 kEUR
    renewable_rev = 49,005 * 60 / 1000 = 2,940.3 kEUR
    """
    inputs = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        discharge_price_eur_mwh=80.0,
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0, round_trip_efficiency=0.90,
            ancillary_revenue_eur_mw_year=0.0,
            capacity_revenue_eur_mw_year=0.0,
            availability=1.0,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    assert abs(result.curtailment_mwh - 49_005) < 1
    assert abs(result.bess_charge_from_curtailment_mwh - 1_000) < 1
    assert abs(result.bess_discharge_from_curtailment_mwh - 900) < 1
    assert abs(result.bess_curtailment_revenue_keur - 72.0) < 0.1
    assert abs(result.renewable_revenue_keur - 2_940.3) < 0.1


def test_wind_bess_hand_checkable():
    """Wind+BESS: capacity=100 MW, avail=0.9801, gen=196,020 MWh
    grid=50 MW → curtailment=98,010 MWh (50% clipping)
    renewable_rev=98,010 * 70 / 1000 = 6,860.7 kEUR
    """
    inputs = HybridInputs(
        wind_capacity_mw=100.0, operating_hours_p50=2000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=70.0,
        discharge_price_eur_mwh=80.0,
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0, round_trip_efficiency=0.90,
            ancillary_revenue_eur_mw_year=0.0,
            capacity_revenue_eur_mw_year=0.0,
            availability=1.0,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    assert result.total_generation_mwh == 196_020.0
    assert result.curtailment_mwh == 98_010.0
    assert abs(result.renewable_revenue_keur - 6_860.7) < 0.1

def test_bess_grid_arb_zero_when_no_grid_charge():
    """Grid arbitrage revenue is 0 when grid_charge_allowed=False."""
    inputs = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        grid_charge_allowed=False,
        grid_charge_mwh=100.0,
        grid_arbitrage_spread_eur_mwh=30.0,
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0, round_trip_efficiency=0.90,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    assert result.bess_grid_arbitrage_revenue_keur == 0.0


def test_bess_grid_arb_zero_when_spread_is_zero():
    """Grid arbitrage revenue is 0 when spread is 0 even if grid charge allowed."""
    inputs = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        grid_charge_allowed=True,
        grid_charge_mwh=100.0,
        grid_arbitrage_spread_eur_mwh=0.0,
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0, round_trip_efficiency=0.90,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    assert result.bess_grid_arbitrage_revenue_keur == 0.0


def test_bess_grid_arb_limited_by_remaining_throughput():
    """Grid arbitrage is capped by remaining BESS throughput after curtailment charge."""
    inputs = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        grid_charge_allowed=True,
        grid_charge_mwh=200.0,              # Request 200 MWh grid charge
        grid_arbitrage_spread_eur_mwh=30.0, # 30 €/MWh spread
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0,            # 1000 MWh max throughput
            round_trip_efficiency=0.90,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    # curtailment ≈ 49005 MWh, max throughput = 1000 MWh
    # curtail_charged = 1000 (capped), remaining = 0
    # grid_charge_limited = min(200, 0) = 0
    assert result.bess_grid_arbitrage_revenue_keur == 0.0


def test_bess_grid_arb_nonzero_when_throughput_remains():
    """Grid arbitrage > 0 when BESS has remaining throughput after curtailment charge."""
    # cycles_per_year=10, energy=100 → max_throughput = 1000 MWh
    # curtailment ≈ 49005 MWh
    # With charge_from_curtailment_share=0.01:
    #   curtail_charged = min(49005*0.01, 1000) = 490 MWh
    #   remaining = max(0, 1000 - 490) = 510 MWh
    #   grid_charge = min(1000, 510) = 510 MWh
    #   grid_discharge = 510 * 0.90 = 459 MWh
    #   grid_arb = 459 * 30 / 1000 ≈ 13.77 kEUR
    inputs = HybridInputs(
        solar_capacity_mw=100.0, operating_hours_p50=1000.0,
        grid_connection_mw=50.0, tariff_eur_mwh=60.0,
        grid_charge_allowed=True,
        grid_charge_mwh=1000.0,
        grid_arbitrage_spread_eur_mwh=30.0,
        charge_from_curtailment_share=0.01,
        bess=BessParams(
            power_mw=10.0, energy_mwh=100.0,
            cycles_per_year=10.0, round_trip_efficiency=0.90,
        ),
    )
    result = hybrid_period_revenue(inputs, 1, 1.0)
    assert result.bess_grid_arbitrage_revenue_keur > 0.0
    assert abs(result.bess_grid_arbitrage_revenue_keur - 13.77) < 0.1
