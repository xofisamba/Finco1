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


def _implied_excel_revenue_price(project_key: str, fixture_name: str, limit: int = 3) -> list[dict[str, float | str]]:
    """Return implied Excel revenue €/MWh using app generation as denominator.

    This is diagnostic only. It helps determine whether the remaining gap is
    mainly generation volume or price / certificate / balancing treatment.
    """
    app_by_date = _schedule_by_date(project_key)
    rows: list[dict[str, float | str]] = []
    for excel_period in _period_fixture(fixture_name)[:limit]:
        date_key = excel_period["period_end_date"]
        generation_mwh = app_by_date[date_key]["generation_mwh"]
        excel_revenue_keur = excel_period["CF"]["operating_revenues_keur"]
        rows.append({
            "period_end_date": date_key,
            "app_generation_mwh": generation_mwh,
            "excel_revenue_keur": excel_revenue_keur,
            "implied_excel_eur_mwh": excel_revenue_keur * 1000 / generation_mwh,
            "app_ppa_tariff_eur_mwh": app_by_date[date_key]["ppa_tariff_eur_mwh"],
            "app_market_price_eur_mwh": app_by_date[date_key]["market_price_eur_mwh"],
            "app_co2_eur_mwh": (
                app_by_date[date_key]["co2_revenue_keur"] * 1000 / generation_mwh
                if generation_mwh else 0.0
            ),
            "app_net_revenue_eur_mwh": app_by_date[date_key]["revenue_keur"] * 1000 / generation_mwh,
        })
    return rows


def test_oborovo_first_three_revenue_rows_against_excel() -> None:
    failures = _revenue_failures("oborovo", "excel_oborovo_periods.json", limit=3)
    assert not failures, failures


def test_oborovo_first_twelve_revenue_rows_against_excel() -> None:
    failures = _revenue_failures("oborovo", "excel_oborovo_periods.json", limit=12)
    assert not failures, failures


@pytest.mark.xfail(reason="TUHO first-pass factory still needs exact wind production/PPA/balancing mapping")
def test_tuho_first_three_revenue_rows_against_excel() -> None:
    failures = _revenue_failures("tuho", "excel_tuho_periods.json", limit=3)
    assert not failures, failures


def test_revenue_schedule_contains_excel_fixture_dates() -> None:
    for project_key, fixture_name in [
        ("oborovo", "excel_oborovo_periods.json"),
        ("tuho", "excel_tuho_periods.json"),
    ]:
        app_dates = set(_schedule_by_date(project_key))
        fixture_dates = {p["period_end_date"] for p in _period_fixture(fixture_name)}
        assert fixture_dates <= app_dates


def test_oborovo_revenue_decomposition_explains_total_revenue() -> None:
    app_by_date = _schedule_by_date("oborovo")
    for excel_period in _period_fixture("excel_oborovo_periods.json"):
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


def test_oborovo_implied_excel_price_diagnostics_are_available() -> None:
    rows = _implied_excel_revenue_price("oborovo", "excel_oborovo_periods.json", limit=12)
    assert len(rows) == 12
    for row in rows:
        assert row["implied_excel_eur_mwh"] > 0
        assert row["app_net_revenue_eur_mwh"] > 0


def test_tuho_implied_excel_price_diagnostics_are_available() -> None:
    rows = _implied_excel_revenue_price("tuho", "excel_tuho_periods.json", limit=3)
    assert len(rows) == 3
    for row in rows:
        assert row["implied_excel_eur_mwh"] > 0
        assert row["app_net_revenue_eur_mwh"] > 0
