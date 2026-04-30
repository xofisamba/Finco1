"""Unit tests for revenue formula mechanics."""
from __future__ import annotations

from domain.revenue.generation import _period_energy_revenue_keur


def test_period_energy_revenue_full_ppa_matches_legacy_behavior() -> None:
    revenue = _period_energy_revenue_keur(
        generation_mwh=10_000,
        ppa_tariff=60,
        market_price=80,
        ppa_active=True,
        ppa_share=1.0,
    )
    assert revenue == 600.0


def test_period_energy_revenue_partial_ppa_uses_market_for_remaining_generation() -> None:
    revenue = _period_energy_revenue_keur(
        generation_mwh=10_000,
        ppa_tariff=60,
        market_price=80,
        ppa_active=True,
        ppa_share=0.75,
    )
    assert revenue == 650.0


def test_period_energy_revenue_merchant_after_ppa_ignores_ppa_share() -> None:
    revenue = _period_energy_revenue_keur(
        generation_mwh=10_000,
        ppa_tariff=60,
        market_price=80,
        ppa_active=False,
        ppa_share=0.75,
    )
    assert revenue == 800.0


def test_period_energy_revenue_bounds_ppa_share() -> None:
    over_one = _period_energy_revenue_keur(
        generation_mwh=10_000,
        ppa_tariff=60,
        market_price=80,
        ppa_active=True,
        ppa_share=2.0,
    )
    below_zero = _period_energy_revenue_keur(
        generation_mwh=10_000,
        ppa_tariff=60,
        market_price=80,
        ppa_active=True,
        ppa_share=-1.0,
    )
    assert over_one == 600.0
    assert below_zero == 800.0
