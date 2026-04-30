"""Tests for FincoGPT calibration serialization helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.calibration import compare_metric, serialize_waterfall_result, waterfall_kpis, waterfall_period_rows


@dataclass
class DummyPeriod:
    period: int
    date: date
    year_index: int
    period_in_year: int
    is_operation: bool
    revenue_keur: float
    senior_ds_keur: float
    dscr: float


@dataclass
class DummyResult:
    project_irr: float
    equity_irr: float
    avg_dscr: float
    total_distribution_keur: float
    periods: list[DummyPeriod]


def _dummy_result() -> DummyResult:
    return DummyResult(
        project_irr=0.0828,
        equity_irr=0.1161,
        avg_dscr=1.20,
        total_distribution_keur=1000.0,
        periods=[
            DummyPeriod(
                period=2,
                date=date(2030, 6, 30),
                year_index=1,
                period_in_year=1,
                is_operation=True,
                revenue_keur=3200.0,
                senior_ds_keur=2200.0,
                dscr=1.20,
            )
        ],
    )


def test_waterfall_kpis_extracts_known_fields() -> None:
    kpis = waterfall_kpis(_dummy_result())
    assert kpis["project_irr"] == 0.0828
    assert kpis["equity_irr"] == 0.1161
    assert kpis["avg_dscr"] == 1.20
    assert kpis["total_distribution_keur"] == 1000.0


def test_waterfall_period_rows_are_json_safe() -> None:
    rows = waterfall_period_rows(_dummy_result())
    assert rows == [
        {
            "period": 2,
            "date": "2030-06-30",
            "year_index": 1,
            "period_in_year": 1,
            "is_operation": True,
            "revenue_keur": 3200.0,
            "senior_ds_keur": 2200.0,
            "dscr": 1.20,
        }
    ]


def test_serialize_waterfall_result_shape() -> None:
    payload = serialize_waterfall_result(
        _dummy_result(),
        project_key="tuho",
        engine_version="test",
        calibration_source="unit-test",
    )
    assert payload["project_key"] == "tuho"
    assert payload["engine_version"] == "test"
    assert payload["calibration_source"] == "unit-test"
    assert payload["kpis"]["equity_irr"] == 0.1161
    assert payload["periods"][0]["date"] == "2030-06-30"


def test_compare_metric_abs_and_pct_tolerances() -> None:
    passed = compare_metric(app_value=100.0, excel_value=100.4, tolerance_abs=0.5)
    assert passed["passed"] is True

    failed = compare_metric(app_value=95.0, excel_value=100.0, tolerance_pct=0.01)
    assert failed["passed"] is False
    assert failed["delta"] == -5.0
