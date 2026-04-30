"""Shared helpers for Excel-vs-app reconciliation tests.

The helpers intentionally return explicit failure payloads instead of hiding
calibration gaps. Tests can assert on the returned diagnostics or mark them as
xfail while the model is being calibrated.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class ReconciliationFailure:
    period_end_date: str
    metric: str
    app_value: float
    excel_value: float
    delta: float
    pct_delta: float | None
    tolerance_abs: float | None
    tolerance_pct: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_value(
    *,
    period_end_date: str,
    metric: str,
    app_value: float,
    excel_value: float,
    tolerance_abs: float | None = None,
    tolerance_pct: float | None = None,
) -> ReconciliationFailure | None:
    """Compare one app value to Excel and return a failure object if outside tolerance."""
    delta = app_value - excel_value
    pct_delta = delta / excel_value if excel_value else None

    checks: list[bool] = []
    if tolerance_abs is not None:
        checks.append(abs(delta) <= tolerance_abs)
    if tolerance_pct is not None and pct_delta is not None:
        checks.append(abs(pct_delta) <= tolerance_pct)

    passed = all(checks) if checks else False
    if passed:
        return None

    return ReconciliationFailure(
        period_end_date=period_end_date,
        metric=metric,
        app_value=app_value,
        excel_value=excel_value,
        delta=delta,
        pct_delta=pct_delta,
        tolerance_abs=tolerance_abs,
        tolerance_pct=tolerance_pct,
    )


def operation_periods(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return operation periods from a serialized app calibration payload."""
    return [p for p in payload["periods"] if p.get("is_operation")]


def period_by_date(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Map serialized app operation periods by ISO date string."""
    return {p["date"]: p for p in operation_periods(payload)}


def compare_period_metric(
    *,
    app_periods_by_date: Mapping[str, Mapping[str, Any]],
    excel_period: Mapping[str, Any],
    excel_sheet: str,
    excel_metric: str,
    app_metric: str,
    excel_sign: float = 1.0,
    app_sign: float = 1.0,
    tolerance_abs: float | None = None,
    tolerance_pct: float | None = None,
) -> ReconciliationFailure | None:
    """Compare one metric for one Excel period against one serialized app period."""
    period_end_date = str(excel_period["period_end_date"])
    app_period = app_periods_by_date[period_end_date]
    return compare_value(
        period_end_date=period_end_date,
        metric=f"{excel_sheet}.{excel_metric}",
        app_value=float(app_period[app_metric]) * app_sign,
        excel_value=float(excel_period[excel_sheet][excel_metric]) * excel_sign,
        tolerance_abs=tolerance_abs,
        tolerance_pct=tolerance_pct,
    )


def collect_period_failures(
    *,
    app_periods_by_date: Mapping[str, Mapping[str, Any]],
    excel_periods: Iterable[Mapping[str, Any]],
    metric_specs: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Collect reconciliation failures over periods and metric specs."""
    failures: list[dict[str, Any]] = []
    for excel_period in excel_periods:
        for spec in metric_specs:
            failure = compare_period_metric(
                app_periods_by_date=app_periods_by_date,
                excel_period=excel_period,
                excel_sheet=spec["excel_sheet"],
                excel_metric=spec["excel_metric"],
                app_metric=spec["app_metric"],
                excel_sign=spec.get("excel_sign", 1.0),
                app_sign=spec.get("app_sign", 1.0),
                tolerance_abs=spec.get("tolerance_abs"),
                tolerance_pct=spec.get("tolerance_pct"),
            )
            if failure is not None:
                failures.append(failure.to_dict())
    return failures


__all__ = [
    "ReconciliationFailure",
    "collect_period_failures",
    "compare_period_metric",
    "compare_value",
    "operation_periods",
    "period_by_date",
]
