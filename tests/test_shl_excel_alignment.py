"""SHL / sponsor cash-flow Excel-alignment diagnostics.

These tests isolate shareholder-loan cash flows and the sponsor equity + SHL
cash-flow series. Oborovo first12 SHL cash flows are anchored to extracted Eq
and P&L rows until the full SHL balance schedule is mapped.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import run_project_calibration
from tests.reconciliation_helpers import collect_period_failures, period_by_date


FIXTURE_DIR = Path(__file__).parent / "fixtures"


OBOROVO_SHL_CASH_FLOW_METRIC_SPECS = [
    {
        "excel_sheet": "Eq",
        "excel_metric": "shl_principal_flow_keur",
        "app_metric": "shl_principal_keur",
        "tolerance_abs": 0.01,
    },
    {
        "excel_sheet": "Eq",
        "excel_metric": "shl_net_interest_flow_keur",
        "app_metric": "shl_interest_keur",
        "tolerance_abs": 0.01,
    },
    {
        "excel_sheet": "Eq",
        "excel_metric": "net_dividend_flow_keur",
        "app_metric": "distribution_keur",
        "tolerance_abs": 0.01,
    },
]

OBOROVO_SHL_GROSS_INTEREST_METRIC_SPECS = [
    {
        "excel_sheet": "P&L",
        "excel_metric": "shareholder_loan_interests_keur",
        "app_metric": "shl_gross_interest_keur",
        "tolerance_abs": 0.01,
    },
]


def _period_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["periods"]


def _full_model_extract(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_oborovo_shl_fixture_has_first_twelve_eq_and_pl_rows() -> None:
    rows = _period_fixture("excel_oborovo_periods.json")[:12]
    assert len(rows) == 12
    for row in rows:
        assert "Eq" in row
        assert "shl_principal_flow_keur" in row["Eq"]
        assert "shl_net_interest_flow_keur" in row["Eq"]
        assert "net_dividend_flow_keur" in row["Eq"]
        assert "shareholder_loan_interests_keur" in row["P&L"]


def test_oborovo_first_twelve_shl_cash_flows_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_SHL_CASH_FLOW_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_first_twelve_shl_gross_interest_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_SHL_GROSS_INTEREST_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_first_twelve_shl_decomposition_matches_cash_flow_definition() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    shl_rows = payload["shl_decomposition"][:12]
    cf_rows = payload["sponsor_equity_shl_cash_flows"][1:13]

    assert len(shl_rows) == 12
    for shl_row, cf_row in zip(shl_rows, cf_rows):
        assert shl_row["date"] == cf_row["date"]
        assert shl_row["gross_interest_keur"] >= shl_row["cash_interest_paid_keur"]
        assert shl_row["pik_or_capitalized_interest_keur"] == (
            shl_row["gross_interest_keur"] - shl_row["cash_interest_paid_keur"]
        )
        assert cf_row["cash_flow_keur"] == (
            cf_row["distribution_keur"]
            + cf_row["shl_interest_keur"]
            + cf_row["shl_principal_keur"]
        )
        assert cf_row["cash_flow_keur"] == (
            shl_row["cash_interest_paid_keur"]
            + shl_row["principal_paid_keur"]
        )


@pytest.mark.xfail(reason="App SHL bridge does not yet reproduce the full extracted Excel lifecycle")
def test_oborovo_first_twelve_shl_balance_schedule_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    excel = _full_model_extract("excel_oborovo_full_model_extract.json")
    app_by_date = {row["date"]: row for row in payload["shl_decomposition"]}
    failures = []

    for row in excel["shl"][1:13]:
        date_key = row[0]
        app = app_by_date[date_key]
        comparisons = {
            "opening_balance_keur": (app["opening_balance_keur"], row[1]),
            "closing_balance_keur": (app["closing_balance_keur"], row[2]),
            "gross_interest_keur": (app["gross_interest_keur"], row[3]),
            "principal_paid_keur": (app["principal_paid_keur"], row[4]),
            "cash_interest_paid_keur": (app["cash_interest_paid_keur"], row[5]),
            "pik_or_capitalized_interest_keur": (app["pik_or_capitalized_interest_keur"], row[6]),
        }
        for metric, (app_value, excel_value) in comparisons.items():
            if app_value != pytest.approx(excel_value, abs=0.01):
                failures.append({
                    "period_end_date": date_key,
                    "metric": metric,
                    "app_value": app_value,
                    "excel_value": excel_value,
                    "delta": app_value - excel_value,
                })

    assert not failures, failures


def test_tuho_first_three_shl_cash_flows_against_excel() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_tuho_periods.json")[:3],
        metric_specs=OBOROVO_SHL_CASH_FLOW_METRIC_SPECS,
    )
    assert not failures, failures
