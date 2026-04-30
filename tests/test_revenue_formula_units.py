"""Unit tests for revenue formula mechanics."""
from __future__ import annotations

from dataclasses import replace

from app.calibration import build_period_engine, load_project_inputs
from domain.revenue.generation import _period_energy_revenue_keur, full_generation_schedule


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


def test_full_generation_schedule_defaults_to_project_yield_scenario() -> None:
    base = load_project_inputs("oborovo")
    p90_inputs = replace(
        base,
        technical=replace(base.technical, yield_scenario="P90-10y"),
    )
    engine = build_period_engine(p90_inputs)
    schedule_default = full_generation_schedule(p90_inputs, engine)
    schedule_explicit = full_generation_schedule(p90_inputs, engine, yield_scenario="P90-10y")
    assert schedule_default == schedule_explicit


def test_full_generation_schedule_can_override_project_yield_scenario() -> None:
    base = load_project_inputs("oborovo")
    p90_inputs = replace(
        base,
        technical=replace(base.technical, yield_scenario="P90-10y"),
    )
    engine = build_period_engine(p90_inputs)
    p90_schedule = full_generation_schedule(p90_inputs, engine)
    p50_override = full_generation_schedule(p90_inputs, engine, yield_scenario="P_50")
    first_op = next(p for p in engine.periods() if p.is_operation)
    assert p90_schedule[first_op.index] < p50_override[first_op.index]
