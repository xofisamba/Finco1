"""Headless calibration runner utilities.

This module is the bridge between project fixtures/default inputs and the
uncached waterfall core. It must remain importable without Streamlit so it can
be used by pytest, CLI scripts and future CI calibration jobs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.calibration import serialize_waterfall_result
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.inputs import DebtSizingMethod, EquityIRRMethod, ProjectInputs, SHLRepaymentMethod
from domain.period_engine import PeriodEngine, PeriodFrequency


@dataclass(frozen=True)
class CalibrationRunSpec:
    """Defines one reproducible calibration run."""

    project_key: str
    engine_version: str = "FincoGPT"
    calibration_source: str = "headless"


def _enum_from_value(enum_cls: type, value: Any, default: Any) -> Any:
    """Coerce strings/enums from inputs into the enum type expected by config."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return default
    return default


def load_project_inputs(project_key: str) -> ProjectInputs:
    """Load built-in project inputs for a calibration project.

    The current codebase has a built-in Oborovo default. TUHO targets are already
    captured in JSON, but a complete TUHO ProjectInputs builder still needs to be
    implemented from the uploaded workbook.
    """
    normalized = project_key.strip().lower()
    if normalized == "oborovo":
        return ProjectInputs.create_default_oborovo()
    if normalized in {"tuho", "tuhobic", "tuhobić"}:
        factory = getattr(ProjectInputs, "create_default_tuho", None)
        if factory is None:
            raise NotImplementedError(
                "TUHO calibration targets exist, but ProjectInputs.create_default_tuho() "
                "has not been implemented yet."
            )
        return factory()
    raise ValueError(f"Unknown calibration project: {project_key}")


def build_period_engine(inputs: ProjectInputs) -> PeriodEngine:
    """Build the period engine from ProjectInputs."""
    # Current app defaults are semestrial. Keep this explicit until annual and
    # quarterly parity are implemented and tested.
    return PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
        frequency=PeriodFrequency.SEMESTRIAL,
    )


def build_run_config(inputs: ProjectInputs) -> WaterfallRunConfig:
    """Build WaterfallRunConfig from ProjectInputs."""
    financing = inputs.financing
    tax = inputs.tax

    return WaterfallRunConfig(
        rate_per_period=financing.all_in_rate / 2,
        tenor_periods=financing.senior_tenor_years * 2,
        target_dscr=financing.target_dscr,
        lockup_dscr=financing.lockup_dscr,
        tax_rate=tax.corporate_rate,
        dsra_months=financing.dsra_months,
        shl_amount_keur=financing.shl_amount_keur,
        shl_rate=financing.shl_rate / 2,
        shl_idc_keur=financing.shl_idc_keur,
        shl_repayment_method=_enum_from_value(
            SHLRepaymentMethod,
            financing.shl_repayment_method,
            SHLRepaymentMethod.BULLET,
        ),
        shl_tenor_years=financing.shl_tenor_years,
        shl_wht_rate=tax.wht_sponsor_shl_interest,
        fixed_debt_keur=financing.fixed_debt_keur,
        fixed_ds_keur=financing.fixed_ds_keur,
        equity_irr_method=_enum_from_value(
            EquityIRRMethod,
            financing.equity_irr_method,
            EquityIRRMethod.EQUITY_ONLY,
        ),
        share_capital_keur=financing.share_capital_keur,
        sculpt_capex_keur=inputs.capex.sculpt_capex_keur,
        debt_sizing_method=_enum_from_value(
            DebtSizingMethod,
            financing.debt_sizing_method,
            DebtSizingMethod.DSCR_SCULPT,
        ),
        dscr_schedule=financing.dscr_schedule,
    )


def run_calibration(spec: CalibrationRunSpec) -> dict[str, Any]:
    """Run one calibration project and return JSON-safe reconciliation payload."""
    inputs = load_project_inputs(spec.project_key)
    engine = build_period_engine(inputs)
    config = build_run_config(inputs)
    result = WaterfallRunner(inputs, engine).run(config)
    return serialize_waterfall_result(
        result,
        project_key=spec.project_key,
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
