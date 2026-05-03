"""Backward-compatible headless calibration runner utilities.

The implementation delegates to app.calibration, which calls the uncached
waterfall core directly and does not import Streamlit or app.cache.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.calibration import (
    build_period_engine,
    build_run_config,
    load_project_inputs,
    run_project_calibration,
)


@dataclass(frozen=True)
class CalibrationRunSpec:
    """Defines one reproducible calibration run."""

    project_key: str
    engine_version: str = "FincoGPT"
    calibration_source: str = "headless"


def run_calibration(spec: CalibrationRunSpec) -> dict[str, Any]:
    """Run one calibration project and return JSON-safe reconciliation payload."""
    return run_project_calibration(
        spec.project_key,
        engine_version=spec.engine_version,
        calibration_source=spec.calibration_source,
    )


__all__ = [
    "CalibrationRunSpec",
    "load_project_inputs",
    "build_period_engine",
    "build_run_config",
    "run_calibration",
]
