"""OpEx Excel-alignment diagnostics.

These tests isolate operating expense schedule before downstream EBITDA, tax,
and debt mechanics. Oborovo first12 OpEx is active because those periods are
anchored to extracted Excel rows while full line-item mapping is still pending.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import build_period_engine, load_project_inputs
from domain.opex.projections import opex_schedule_period, opex_schedule_annual
from tests.reconciliation_helpers import compare_value


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _period_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["periods"]


def _opex_by_date(project_key: str) -> dict[str, dict[str, float]]:
    inputs = load_project_inputs(project_key)
    engine = build_period_engine(inputs)
    period_opex = opex_schedule_period(inputs, engine)
    annual_opex = opex_schedule_annual(inputs, inputs.info.horizon_years)
    return {
        p.end_date.isoformat(): {
            "opex_keur": period_opex[p.index],
            "annual_opex_keur": annual_opex.get(p.year_index, 0.0),
            "day_fraction": p.day_fraction,
            "year_index": p.year_index,
            "period_in_year": p.period_in_year,
        }
        for p in engine.operation_periods()
    }


def _opex_failures(project_key: str, fixture_name: str, limit: int) -> list[dict]:
    app_by_date = _opex_by_date(project_key)
    failures = []
    for excel_period in _period_fixture(fixture_name)[:limit]:
        date_key = excel_period["period_end_date"]
        # Excel CF row is negative cost; app schedule stores positive cost.
        failure = compare_value(
            period_end_date=date_key,
            metric="CF.operating_expenses_after_bank_tax_keur",
            app_value=-app_by_date[date_key]["opex_keur"],
            excel_value=excel_period["CF"]["operating_expenses_after_bank_tax_keur"],
            tolerance_pct=0.005,
        )
        if failure:
            payload = failure.to_dict()
            payload["opex_decomposition"] = app_by_date[date_key]
            failures.append(payload)
    return failures


def test_oborovo_opex_fixture_has_first_twelve_periods() -> None:
    periods = _period_fixture("excel_oborovo_periods.json")
    assert len(periods) >= 12
    assert all(p["CF"]["operating_expenses_after_bank_tax_keur"] < 0 for p in periods[:12])


def test_oborovo_first_twelve_opex_rows_against_excel() -> None:
    failures = _opex_failures("oborovo", "excel_oborovo_periods.json", limit=12)
    assert not failures, failures


@pytest.mark.xfail(reason="TUHO first-pass factory reuses non-TUHO OpEx assumptions")
def test_tuho_first_three_opex_rows_against_excel() -> None:
    failures = _opex_failures("tuho", "excel_tuho_periods.json", limit=3)
    assert not failures, failures


def test_opex_schedule_contains_excel_fixture_dates() -> None:
    for project_key, fixture_name in [
        ("oborovo", "excel_oborovo_periods.json"),
        ("tuho", "excel_tuho_periods.json"),
    ]:
        app_dates = set(_opex_by_date(project_key))
        fixture_dates = {p["period_end_date"] for p in _period_fixture(fixture_name)}
        assert fixture_dates <= app_dates
