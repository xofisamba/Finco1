"""Debt schedule Excel-alignment diagnostics.

These tests isolate senior debt service, principal, interest and implied DSCR
before tax/SHL/equity return mechanics. They are diagnostic until the debt
sculpting schedule matches the Excel workbook.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import run_project_calibration
from tests.reconciliation_helpers import collect_period_failures, period_by_date


FIXTURE_DIR = Path(__file__).parent / "fixtures"


OBOROVO_DEBT_METRIC_SPECS = [
    {
        "excel_sheet": "CF",
        "excel_metric": "senior_debt_service_keur",
        "app_metric": "senior_ds_keur",
        "excel_sign": -1.0,
        "app_sign": 1.0,
        "tolerance_pct": 0.005,
    },
    {
        "excel_sheet": "DS",
        "excel_metric": "senior_principal_keur",
        "app_metric": "senior_principal_keur",
        "tolerance_pct": 0.005,
    },
    {
        "excel_sheet": "DS",
        "excel_metric": "senior_net_interest_keur",
        "app_metric": "senior_interest_keur",
        "tolerance_pct": 0.005,
    },
]


def _period_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["periods"]


def _implied_excel_debt_rows(fixture_name: str, limit: int) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for period in _period_fixture(fixture_name)[:limit]:
        cfads = period["CF"]["free_cash_flow_for_banks_keur"]
        debt_service = -period["CF"]["senior_debt_service_keur"]
        rows.append({
            "period_end_date": period["period_end_date"],
            "excel_cfads_keur": cfads,
            "excel_senior_debt_service_keur": debt_service,
            "excel_senior_principal_keur": period["DS"]["senior_principal_keur"],
            "excel_senior_interest_keur": period["DS"]["senior_net_interest_keur"],
            "excel_implied_dscr": cfads / debt_service if debt_service else 0.0,
            "excel_dscr_target_row": period["DS"]["senior_debt_dscr_target"],
            "excel_average_dscr_row": period["CF"]["average_senior_dscr_period"],
            "excel_minimum_dscr_row": period["CF"]["minimum_senior_dscr_period"],
        })
    return rows


def test_oborovo_excel_debt_fixture_has_first_twelve_periods() -> None:
    rows = _implied_excel_debt_rows("excel_oborovo_periods.json", limit=12)
    assert len(rows) == 12
    for row in rows:
        assert row["excel_senior_debt_service_keur"] > 0
        assert row["excel_senior_principal_keur"] > 0
        assert row["excel_senior_interest_keur"] > 0
        assert abs(row["excel_implied_dscr"] - row["excel_dscr_target_row"]) < 1e-9


def test_oborovo_first_twelve_excel_dscr_target_is_115() -> None:
    """Current extracted Oborovo first12 Excel rows use 1.15 DSCR, not 1.20.

    The PPA=1.20 / merchant-higher hypothesis may still apply to TUHO or later
    Oborovo periods, but it is not visible in the first 12 Oborovo rows currently
    extracted into the fixture.
    """
    rows = _implied_excel_debt_rows("excel_oborovo_periods.json", limit=12)
    assert {round(float(row["excel_dscr_target_row"]), 6) for row in rows} == {1.15}


@pytest.mark.xfail(reason="Oborovo debt schedule still needs Excel sculpting/rate/balance alignment")
def test_oborovo_first_twelve_debt_lines_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_DEBT_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_app_payload_contains_debt_diagnostics() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    app_rows = period_by_date(payload)
    for excel_row in _implied_excel_debt_rows("excel_oborovo_periods.json", limit=12):
        app_row = app_rows[excel_row["period_end_date"]]
        assert "senior_interest_keur" in app_row
        assert "senior_principal_keur" in app_row
        assert "senior_ds_keur" in app_row
        assert "dscr" in app_row
