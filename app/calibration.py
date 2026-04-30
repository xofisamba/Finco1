"""Calibration helpers for Excel parity work.

This module intentionally contains no Streamlit dependency. It converts a
WaterfallResult into a stable JSON-like structure that can be compared against
Excel-extracted fixtures and provides a headless project runner for CLI/pytest
reconciliation work.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.inputs import DebtSizingMethod, EquityIRRMethod, ProjectInputs, SHLRepaymentMethod
from domain.period_engine import PeriodEngine, PeriodFrequency


KPI_FIELDS = (
    "project_irr",
    "equity_irr",
    "project_npv",
    "equity_npv",
    "avg_dscr",
    "min_dscr",
    "max_dscr",
    "total_revenue_keur",
    "total_opex_keur",
    "total_ebitda_keur",
    "total_tax_keur",
    "total_senior_ds_keur",
    "total_shl_service_keur",
    "total_distribution_keur",
)

PERIOD_FIELDS = (
    "period",
    "date",
    "year_index",
    "period_in_year",
    "is_operation",
    "generation_mwh",
    "revenue_keur",
    "opex_keur",
    "ebitda_keur",
    "depreciation_keur",
    "taxable_profit_keur",
    "tax_keur",
    "cf_after_tax_keur",
    "senior_interest_keur",
    "senior_principal_keur",
    "senior_ds_keur",
    "dscr",
    "dsra_contribution_keur",
    "dsra_balance_keur",
    "shl_interest_keur",
    "shl_principal_keur",
    "shl_service_keur",
    "shl_balance_keur",
    "shl_pik_keur",
    "distribution_keur",
    "cash_sweep_keur",
    "cum_distribution_keur",
    "cash_balance_keur",
    "senior_balance_keur",
)


def available_project_keys() -> list[str]:
    """Return project keys currently supported by the headless calibration runner."""
    keys = ["oborovo"]
    if _find_tuho_factory() is not None:
        keys.append("tuho")
    return keys


def load_project_inputs(project_key: str) -> ProjectInputs:
    """Load a default ProjectInputs factory for a calibration project."""
    key = project_key.lower().strip()
    if key == "oborovo":
        return ProjectInputs.create_default_oborovo()
    if key in {"tuho", "tuhobic", "tuhobić"}:
        factory = _find_tuho_factory()
        if factory is None:
            raise ValueError("TUHO default input factory is not implemented yet")
        return factory()
    raise ValueError(f"Unknown project_key: {project_key}")


def build_period_engine(inputs: ProjectInputs) -> PeriodEngine:
    """Build the standard semi-annual PeriodEngine for ProjectInputs."""
    return PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
        frequency=PeriodFrequency.SEMESTRIAL,
    )


def build_run_config(inputs: ProjectInputs) -> WaterfallRunConfig:
    """Build a WaterfallRunConfig from ProjectInputs without Streamlit."""
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
        shl_idc_keur=getattr(financing, "shl_idc_keur", 0.0),
        shl_repayment_method=_enum_value(SHLRepaymentMethod, financing.shl_repayment_method, SHLRepaymentMethod.BULLET),
        shl_tenor_years=getattr(financing, "shl_tenor_years", 0),
        shl_wht_rate=tax.wht_sponsor_shl_interest,
        fixed_debt_keur=getattr(financing, "fixed_debt_keur", None),
        fixed_ds_keur=getattr(financing, "fixed_ds_keur", None),
        equity_irr_method=_enum_value(EquityIRRMethod, financing.equity_irr_method, EquityIRRMethod.EQUITY_ONLY),
        share_capital_keur=financing.share_capital_keur,
        sculpt_capex_keur=inputs.capex.sculpt_capex_keur,
        debt_sizing_method=_enum_value(DebtSizingMethod, financing.debt_sizing_method, DebtSizingMethod.DSCR_SCULPT),
        dscr_schedule=getattr(financing, "dscr_schedule", None),
    )


def run_project_calibration(
    project_key: str,
    *,
    engine_version: str = "FincoGPT",
    calibration_source: str = "headless_runner",
) -> dict[str, Any]:
    """Run one calibration project and return a serializable reconciliation payload."""
    inputs = load_project_inputs(project_key)
    engine = build_period_engine(inputs)
    config = build_run_config(inputs)
    result = WaterfallRunner(inputs, engine).run(config)
    payload = serialize_waterfall_result(
        result,
        project_key=project_key.lower().strip(),
        engine_version=engine_version,
        calibration_source=calibration_source,
    )
    payload["available_project_keys"] = available_project_keys()
    return payload


def _json_safe(value: Any) -> Any:
    """Convert common model values to JSON-safe primitives."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        if value == float("inf"):
            return "Infinity"
        if value == float("-inf"):
            return "-Infinity"
        return value
    if is_dataclass(value):
        return asdict(value)
    return value


def waterfall_kpis(result: Any) -> dict[str, Any]:
    """Return stable KPI dictionary from a WaterfallResult-like object."""
    return {field: _json_safe(getattr(result, field)) for field in KPI_FIELDS if hasattr(result, field)}


def waterfall_period_rows(result: Any) -> list[dict[str, Any]]:
    """Return period-level reconciliation rows from a WaterfallResult-like object."""
    rows: list[dict[str, Any]] = []
    for period in getattr(result, "periods", []):
        row: dict[str, Any] = {}
        for field in PERIOD_FIELDS:
            if hasattr(period, field):
                row[field] = _json_safe(getattr(period, field))
        rows.append(row)
    return rows


def serialize_waterfall_result(
    result: Any,
    *,
    project_key: str,
    engine_version: str = "unknown",
    calibration_source: str = "app",
) -> dict[str, Any]:
    """Serialize waterfall output for Excel reconciliation."""
    return {
        "project_key": project_key,
        "engine_version": engine_version,
        "calibration_source": calibration_source,
        "kpis": waterfall_kpis(result),
        "periods": waterfall_period_rows(result),
    }


def compare_metric(
    *,
    app_value: float,
    excel_value: float,
    tolerance_abs: float | None = None,
    tolerance_pct: float | None = None,
) -> dict[str, Any]:
    """Compare one numeric metric against Excel with explicit tolerances."""
    delta = app_value - excel_value
    pct_delta = delta / excel_value if excel_value else None

    checks: list[bool] = []
    if tolerance_abs is not None:
        checks.append(abs(delta) <= tolerance_abs)
    if tolerance_pct is not None and pct_delta is not None:
        checks.append(abs(pct_delta) <= tolerance_pct)

    passed = all(checks) if checks else False
    return {
        "app_value": app_value,
        "excel_value": excel_value,
        "delta": delta,
        "pct_delta": pct_delta,
        "tolerance_abs": tolerance_abs,
        "tolerance_pct": tolerance_pct,
        "passed": passed,
    }


def _enum_value(enum_cls: type, value: Any, default: Any) -> Any:
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        for member in enum_cls:
            if member.value == value:
                return member
    return default


def _find_tuho_factory():
    for name in ("create_default_tuho", "create_default_tuhobic", "create_default_tuhobić"):
        factory = getattr(ProjectInputs, name, None)
        if callable(factory):
            return factory
    return None


__all__ = [
    "KPI_FIELDS",
    "PERIOD_FIELDS",
    "available_project_keys",
    "build_period_engine",
    "build_run_config",
    "load_project_inputs",
    "run_project_calibration",
    "waterfall_kpis",
    "waterfall_period_rows",
    "serialize_waterfall_result",
    "compare_metric",
]
