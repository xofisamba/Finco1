"""Tests for the FincoGPT headless calibration runner."""
from __future__ import annotations

from app.calibration import available_project_keys, debt_rate_schedule_from_engine
from app.calibration_runner import (
    CalibrationRunSpec,
    build_period_engine,
    build_run_config,
    load_project_inputs,
    run_calibration,
)


def test_available_project_keys_include_oborovo_and_tuho() -> None:
    keys = available_project_keys()
    assert "oborovo" in keys
    assert "tuho" in keys


def test_load_project_inputs_oborovo() -> None:
    inputs = load_project_inputs("oborovo")
    assert inputs.info.name
    assert inputs.capex.total_capex > 0


def test_load_project_inputs_tuho() -> None:
    inputs = load_project_inputs("tuho")
    assert inputs.info.name.lower().startswith("tuh")
    assert inputs.capex.total_capex > 70_000
    assert inputs.financing.fixed_debt_keur is not None


def test_build_period_engine_from_oborovo_inputs() -> None:
    inputs = load_project_inputs("oborovo")
    engine = build_period_engine(inputs)
    periods = engine.periods()
    assert periods
    assert any(p.is_operation for p in periods)


def test_build_period_engine_from_tuho_inputs() -> None:
    inputs = load_project_inputs("tuho")
    engine = build_period_engine(inputs)
    periods = engine.periods()
    assert periods
    assert any(p.is_operation for p in periods)


def test_build_run_config_from_oborovo_inputs() -> None:
    inputs = load_project_inputs("oborovo")
    engine = build_period_engine(inputs)
    config = build_run_config(inputs)
    assert config.rate_per_period > 0
    assert config.tenor_periods == inputs.financing.senior_tenor_years * 2
    assert config.sculpt_capex_keur == inputs.capex.sculpt_capex_keur
    assert config.rate_schedule is not None
    assert len(config.rate_schedule) == config.tenor_periods


def test_day_count_debt_rate_schedule_uses_operation_day_fractions() -> None:
    inputs = load_project_inputs("oborovo")
    engine = build_period_engine(inputs)
    config = build_run_config(inputs, engine)
    first_op = engine.operation_periods()[0]

    assert config.rate_schedule is not None
    assert abs(config.rate_schedule[0] - inputs.financing.all_in_rate * first_op.day_fraction) < 1e-12
    assert config.rate_schedule[0] != inputs.financing.all_in_rate / 2


def test_build_run_config_from_tuho_inputs() -> None:
    inputs = load_project_inputs("tuho")
    engine = build_period_engine(inputs)
    config = build_run_config(inputs, engine)
    assert config.rate_per_period > 0
    assert config.fixed_debt_keur == inputs.financing.fixed_debt_keur
    assert config.debt_sizing_method == "fixed"
    assert config.equity_irr_method == "shl_plus_dividends"
    assert config.rate_schedule is not None


def test_calibration_run_spec_defaults() -> None:
    spec = CalibrationRunSpec(project_key="oborovo")
    assert spec.engine_version == "FincoGPT"
    assert spec.calibration_source == "headless"


def test_run_calibration_oborovo_payload_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    assert payload["project_key"] == "oborovo"
    assert payload["calibration_source"] == "pytest"
    assert payload["periods"]
    assert payload["kpis"]["senior_debt_keur"] > 0
    assert payload["revenue_decomposition"]


def test_run_calibration_revenue_decomposition_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    row = next(r for r in payload["revenue_decomposition"] if r["is_operation"])
    assert row["date"]
    assert row["generation_mwh"] > 0
    assert row["ppa_tariff_eur_mwh"] > 0
    assert row["market_price_eur_mwh"] > 0
    assert "energy_revenue_keur" in row
    assert "balancing_cost_pv_keur" in row
    assert "balancing_cost_wind_keur" in row
    assert "co2_revenue_keur" in row
    assert row["revenue_keur"] == (
        row["energy_revenue_keur"]
        - row["balancing_cost_pv_keur"]
        - row["balancing_cost_wind_keur"]
        + row["co2_revenue_keur"]
    )
