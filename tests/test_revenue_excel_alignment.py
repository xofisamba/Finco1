"""Revenue/generation Excel-alignment diagnostics.

These tests isolate the revenue schedule before the full waterfall. They make it
clear whether period-level reconciliation failures come from revenue/generation
or from downstream OpEx/debt/tax mechanics.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import build_period_engine, load_project_inputs
from domain.revenue.generation import (
    full_generation_schedule,
    full_revenue_schedule,
    revenue_decomposition_schedule,
)
from tests.reconciliation_helpers import compare_value


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _period_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["periods"]


def _schedule_by_date(project_key: str) -> dict[str, dict[str, float]]:
    inputs = load_project_inputs(project_key)
    engine = build_period_engine(inputs)
    revenue = full_revenue_schedule(inputs, engine)
    generation = full_generation_schedule(inputs, engine)
    decomposition = revenue_decomposition_schedule(inputs, engine)
    return {
        p.end_date.isoformat(): {
            "revenue_keur": revenue[p.index],
            "generation_mwh": generation[p.index],
            "day_fraction": p.day_fraction,
            **decomposition[p.index],
        }
        for p in engine.operation_periods()
    }


def _revenue_failures(project_key: str, fixture_name: str, limit: int = 3) -> list[dict]:
    app_by_date = _schedule_by_date(project_key)
    failures = []
    for excel_period in _period_fixture(fixture_name)[:limit]:
        date_key = excel_period["period_end_date"]
        failure = compare_value(
            period_end_date=date_key,
            metric="CF.operating_revenues_keur",
            app_value=app_by_date[date_key]["revenue_keur"],
            excel_value=excel_period["CF"]["operating_revenues_keur"],
            tolerance_pct=0.005,
        )
        if failure:
            payload = failure.to_dict()
            payload["revenue_decomposition"] = app_by_date[date_key]
            failures.append(payload)
    return failures


@pytest.mark.xfail(reason="Oborovo revenue schedule still needs exact Excel generation/PPA/CO2 mapping")
def test_oborovo_first_three_revenue_rows_against_excel() -> None:
    failures = _revenue_failures("oborovo", "excel_oborovo_periods.json")
    assert not failures, failures


@pytest.mark.xfail(reason="TUHO first-pass factory still needs exact wind production/PPA/balancing mapping")
def test_tuho_first_three_revenue_rows_against_excel() -> None:
    failures = _revenue_failures("tuho", "excel_tuho_periods.json")
    assert not failures, failures


def test_revenue_schedule_contains_excel_fixture_dates() -> None:
    for project_key, fixture_name in [
        ("oborovo", "excel_oborovo_periods.json"),
        ("tuho", "excel_tuho_periods.json"),
    ]:
        app_dates = set(_schedule_by_date(project_key))
        fixture_dates = {p["period_end_date"] for p in _period_fixture(fixture_name)[:3]}
        assert fixture_dates <= app_dates


def test_oborovo_revenue_decomposition_explains_total_revenue() -> None:
    app_by_date = _schedule_by_date("oborovo")
    for excel_period in _period_fixture("excel_oborovo_periods.json")[:3]:
        row = app_by_date[excel_period["period_end_date"]]
        assert row["revenue_keur"] == (
            row["energy_revenue_keur"]
            - row["balancing_cost_pv_keur"]
            - row["balancing_cost_wind_keur"]
            + row["co2_revenue_keur"]
        )


def test_tuho_revenue_decomposition_explains_total_revenue() -> None:
    app_by_date = _schedule_by_date("tuho")
    for excel_period in _period_fixture("excel_tuho_periods.json")[:3]:
        row = app_by_date[excel_period["period_end_date"]]
        assert row["revenue_keur"] == (
            row["energy_revenue_keur"]
            - row["balancing_cost_pv_keur"]
            - row["balancing_cost_wind_keur"]
            + row["co2_revenue_keur"]
        )
