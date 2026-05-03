"""Property + hand-check tests for hybrid revenue model."""
import math
import pytest
from domain.revenue.hybrid import (
    HybridInputs,
    HybridRevenueBreakdown,
    hybrid_solar_generation_mwh,
    hybrid_wind_generation_mwh,
    hybrid_total_generation_mwh,
    hybrid_clipped_generation_mwh,
    hybrid_period_revenue,
    annual_hybrid_revenue,
)
from domain.revenue.bess import BessParams


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def solar_bess_hybrid():
    """Solar PV + BESS hybrid: 50 MW solar + 10 MW / 20 MWh BESS."""
    return HybridInputs(
        solar_capacity_mw=50.0,
        wind_capacity_mw=0.0,
        operating_hours_p50=1500.0,
        operating_hours_p90_10y=1400.0,
        pv_degradation=0.004,
        plant_availability=0.99,
        grid_availability=0.99,
        curtailment_pct=0.0,
        grid_limit_mw=50.0,
        ppa_base_tariff_eur_mwh=60.0,
        ppa_escalation=0.02,
        ppa_term_years=10.0,
        market_price_eur_mwh=65.0,
        co2_price_eur_mwh=5.0,
        co2_enabled=True,
        bess=BessParams(
            power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
            round_trip_efficiency=0.88, availability=0.98, annual_degradation=0.02,
            arbitrage_spread_eur_mwh=40.0, ancillary_revenue_eur_mw_year=25000.0,
        ),
    )


@pytest.fixture
def wind_bess_hybrid():
    """Wind + BESS hybrid: 80 MW wind + 10 MW / 20 MWh BESS."""
    return HybridInputs(
        solar_capacity_mw=0.0,
        wind_capacity_mw=80.0,
        operating_hours_p50=3000.0,
        operating_hours_p90_10y=2700.0,
        wind_degradation=0.005,
        plant_availability=0.97,
        grid_availability=0.99,
        curtailment_pct=0.0,
        grid_limit_mw=None,
        ppa_base_tariff_eur_mwh=65.0,
        ppa_escalation=0.02,
        ppa_term_years=12.0,
        market_price_eur_mwh=60.0,
        co2_price_eur_mwh=4.0,
        co2_enabled=True,
        bess=BessParams(
            power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0,
            round_trip_efficiency=0.88, availability=0.98, annual_degradation=0.02,
            arbitrage_spread_eur_mwh=35.0, ancillary_revenue_eur_mw_year=25000.0,
        ),
    )


# =============================================================================
# Property 1: generation >= 0
# =============================================================================

@pytest.mark.parametrize("year_index", [1, 5, 10, 20])
def test_solar_generation_non_negative(solar_bess_hybrid, year_index):
    result = hybrid_solar_generation_mwh(solar_bess_hybrid, year_index)
    assert result >= 0.0


@pytest.mark.parametrize("year_index", [1, 5, 10, 20])
def test_wind_generation_non_negative(wind_bess_hybrid, year_index):
    result = hybrid_wind_generation_mwh(wind_bess_hybrid, year_index)
    assert result >= 0.0


# =============================================================================
# Property 2: degradation reduces generation
# =============================================================================

def test_solar_generation_decreases_with_degradation():
    inputs = HybridInputs(
        solar_capacity_mw=50.0, operating_hours_p50=1500.0,
        pv_degradation=0.004,
    )
    y1 = hybrid_solar_generation_mwh(inputs, year_index=1, day_fraction=1.0)
    y10 = hybrid_solar_generation_mwh(inputs, year_index=10, day_fraction=1.0)
    assert y10 < y1


def test_solar_generation_zero_degradation_constant():
    inputs = HybridInputs(
        solar_capacity_mw=50.0, operating_hours_p50=1500.0,
        pv_degradation=0.0,
    )
    y1 = hybrid_solar_generation_mwh(inputs, year_index=1, day_fraction=1.0)
    y5 = hybrid_solar_generation_mwh(inputs, year_index=5, day_fraction=1.0)
    assert math.isclose(y1, y5, rel_tol=1e-9)


# =============================================================================
# Property 3: total = solar + wind
# =============================================================================

def test_total_generation_equals_solar_plus_wind(wind_bess_hybrid):
    solar = hybrid_solar_generation_mwh(wind_bess_hybrid, year_index=1)
    wind = hybrid_wind_generation_mwh(wind_bess_hybrid, year_index=1)
    total = hybrid_total_generation_mwh(wind_bess_hybrid, year_index=1)
    assert math.isclose(total, solar + wind, rel_tol=1e-9)


# =============================================================================
# Property 4: grid clipping caps generation
# =============================================================================

def test_grid_clipping_caps_generation():
    inputs = HybridInputs(
        solar_capacity_mw=100.0,
        wind_capacity_mw=0.0,
        operating_hours_p50=1500.0,
        grid_limit_mw=50.0,  # half of capacity → half generation
        ppa_base_tariff_eur_mwh=60.0,
    )
    total = hybrid_total_generation_mwh(inputs, year_index=1, day_fraction=1.0)
    clipped = hybrid_clipped_generation_mwh(inputs, year_index=1, day_fraction=1.0)
    assert clipped <= total
    assert clipped < total  # because limit is tighter than unconstrained


# =============================================================================
# Property 5: revenue breakdown additive
# =============================================================================

def test_revenue_breakdown_additive(solar_bess_hybrid):
    """net = ppa + merchant + co2 + bess - clipping_effect (none here)."""
    bd = hybrid_period_revenue(solar_bess_hybrid, year_index=1, day_fraction=1.0)
    expected_gross = (bd.ppa_revenue_keur + bd.merchant_revenue_keur +
                      bd.co2_revenue_keur)
    assert math.isclose(bd.gross_revenue_keur, expected_gross, rel_tol=1e-9)
    assert math.isclose(bd.net_revenue_keur, bd.gross_revenue_keur + bd.bess_revenue_keur, rel_tol=1e-9)


# =============================================================================
# Property 6: annual sums two semi-annual periods
# =============================================================================

def test_annual_revenue_sums_six_monthly(solar_bess_hybrid):
    annual = annual_hybrid_revenue(solar_bess_hybrid, year_index=1)
    h1 = hybrid_period_revenue(solar_bess_hybrid, year_index=1, day_fraction=0.5)
    h2 = hybrid_period_revenue(solar_bess_hybrid, year_index=1, day_fraction=0.5)
    assert math.isclose(annual.net_revenue_keur, h1.net_revenue_keur + h2.net_revenue_keur, rel_tol=1e-9)


# =============================================================================
# Property 7: BESS revenue included when bess param is set
# =============================================================================

def test_bess_revenue_included_when_bess_set(solar_bess_hybrid):
    bd = hybrid_period_revenue(solar_bess_hybrid, year_index=1, day_fraction=1.0)
    assert bd.bess_breakdown is not None
    assert bd.bess_revenue_keur > 0


def test_bess_revenue_zero_when_no_bess():
    inputs = HybridInputs(
        solar_capacity_mw=50.0, operating_hours_p50=1500.0,
        ppa_base_tariff_eur_mwh=60.0,
        bess=None,
    )
    bd = hybrid_period_revenue(inputs, year_index=1, day_fraction=1.0)
    assert bd.bess_breakdown is None
    assert bd.bess_revenue_keur == 0.0


# =============================================================================
# Property 8: no generation when capacity is zero
# =============================================================================

def test_no_solar_when_capacity_zero():
    inputs = HybridInputs(solar_capacity_mw=0.0, operating_hours_p50=1500.0,
                           ppa_base_tariff_eur_mwh=60.0)
    assert hybrid_solar_generation_mwh(inputs, year_index=1) == 0.0


def test_no_wind_when_capacity_zero():
    inputs = HybridInputs(wind_capacity_mw=0.0, operating_hours_p50=3000.0,
                           ppa_base_tariff_eur_mwh=65.0)
    assert hybrid_wind_generation_mwh(inputs, year_index=1) == 0.0


# =============================================================================
# Hand-check: solar_bess_hybrid Y1 H1 full-day
# =============================================================================

def test_hand_check_solar_bess_y1_full_day(solar_bess_hybrid):
    """Hand-calculate solar+ BESS Y1 H1 full-day.

    Solar: 50 MW × 1500 h × 0.99 × 0.99 × (1-0.004)^0 = 50×1500×0.9801 = 73,507.5 MWh
    Tariff: 60 EUR/MWh → PPA rev = 73,507.5 × 60 / 1000 = 4,410.45 kEUR
    CO2:   73,507.5 × 5 / 1000 = 367.54 kEUR
    BESS:  from bess_revenue_breakdown Y1 H1 day_fraction=1.0
    """
    bd = hybrid_period_revenue(solar_bess_hybrid, year_index=1, day_fraction=1.0)
    # Solar generation
    expected_solar_gen = 50.0 * 1500.0 * 0.99 * 0.99  # ≈ 73,507.5 MWh
    assert math.isclose(bd.solar_generation_mwh, expected_solar_gen, rel_tol=0.001)
    # PPA revenue
    assert math.isclose(bd.ppa_revenue_keur, expected_solar_gen * 60.0 / 1000, rel_tol=0.001)
    # CO2 revenue
    assert math.isclose(bd.co2_revenue_keur, expected_solar_gen * 5.0 / 1000, rel_tol=0.001)
    # BESS included
    assert bd.bess_breakdown is not None
    assert bd.bess_revenue_keur > 0


# =============================================================================
# Edge case: wind-only (no solar)
# =============================================================================

def test_wind_only_no_solar(wind_bess_hybrid):
    bd = hybrid_period_revenue(wind_bess_hybrid, year_index=1, day_fraction=1.0)
    assert bd.solar_generation_mwh == 0.0
    assert bd.wind_generation_mwh > 0
    assert bd.bess_breakdown is not None


# =============================================================================
# Edge case: merchant (PPA off) uses market price
# =============================================================================

def test_merchant_uses_market_price():
    inputs = HybridInputs(
        solar_capacity_mw=50.0, operating_hours_p50=1500.0,
        ppa_base_tariff_eur_mwh=60.0, market_price_eur_mwh=80.0,
        bess=None,
    )
    bd_ppa = hybrid_period_revenue(inputs, year_index=1, ppa_active=True)
    bd_mer = hybrid_period_revenue(inputs, year_index=1, ppa_active=False)
    # Merchant revenue should be higher (80 > 60)
    assert bd_mer.merchant_revenue_keur > bd_ppa.merchant_revenue_keur
    assert bd_mer.merchant_revenue_keur > 0
    assert bd_ppa.merchant_revenue_keur == 0.0
