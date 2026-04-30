"""Calibration serialization helpers for Excel parity work.

This module intentionally contains no Streamlit dependency. It converts a
WaterfallResult into a stable JSON-like structure that can be compared against
Excel-extracted fixtures and rendered in a future Calibration app page.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


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
    """Serialize waterfall output for Excel reconciliation.

    Args:
        result: WaterfallResult-like object.
        project_key: Stable project key, e.g. "oborovo" or "tuho".
        engine_version: Engine/model version label.
        calibration_source: Describes how this result was produced.

    Returns:
        JSON-serializable payload with KPI and period-level sections.
    """
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


__all__ = [
    "KPI_FIELDS",
    "PERIOD_FIELDS",
    "waterfall_kpis",
    "waterfall_period_rows",
    "serialize_waterfall_result",
    "compare_metric",
]
