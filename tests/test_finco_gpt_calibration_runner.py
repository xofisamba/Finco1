"""Tests for the FincoGPT headless calibration runner."""
from __future__ import annotations

import pytest

from app.calibration_runner import (
    CalibrationRunSpec,
    build_period_engine,
    build_run_config,
    load_project_inputs,
)


def test_load_project_inputs_oborovo() -> None:
    inputs = load_project_inputs("oborovo")
    assert inputs.info.name
    assert inputs.capex.total_capex > 0


def test_load_project_inputs_tuho_is_explicitly_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError):
        load_project_inputs("tuho")


def test_build_period_engine_from_oborovo_inputs() -> None:
    inputs = load_project_inputs("oborovo")
    engine = build_period_engine(inputs)
    periods = engine.periods()
    assert periods
    assert any(p.is_operation for p in periods)


def test_build_run_config_from_oborovo_inputs() -> None:
    inputs = load_project_inputs("oborovo")
    config = build_run_config(inputs)
    assert config.rate_per_period > 0
    assert config.tenor_periods == inputs.financing.senior_tenor_years * 2
    assert config.sculpt_capex_keur == inputs.capex.sculpt_capex_keur


def test_calibration_run_spec_defaults() -> None:
    spec = CalibrationRunSpec(project_key="oborovo")
    assert spec.engine_version == "FincoGPT"
    assert spec.calibration_source == "headless"
