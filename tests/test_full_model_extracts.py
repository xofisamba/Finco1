"""Tests for full Excel model extract fixtures.

The raw Excel models are not committed, but compact JSON extracts from those
workbooks are. These tests guard the extracted SHL balance schedule and project
IRR cash-flow series so calibration can move beyond first-12 anchors.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from domain.returns.xirr import xirr


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _targets() -> dict:
    return _fixture("excel_calibration_targets.json")


def test_oborovo_full_model_extract_shape() -> None:
    payload = _fixture("excel_oborovo_full_model_extract.json")
    assert payload["project_key"] == "oborovo"
    assert payload["workbook_sha256"] == "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"
    assert payload["shl_columns"] == [
        "date",
        "opening",
        "closing",
        "gross_interest",
        "principal_flow",
        "paid_net_interest",
        "capitalized_interest",
        "net_dividend",
    ]
    assert len(payload["shl"]) == 61
    assert len(payload["project_cf"]) == 61
    assert len(payload["period_diagnostics"]) == 60
    assert payload["period_diagnostic_columns"][0] == "date"
    assert payload["period_diagnostics"][0][0] == "2030-12-31"
    assert payload["period_diagnostics"][-1][0] == "2060-06-30"


def test_tuho_full_model_extract_shape() -> None:
    payload = _fixture("excel_tuho_full_model_extract.json")
    assert payload["project_key"] == "tuho"
    assert payload["workbook_sha256"] == "780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a"
    assert payload["shl_columns"] == [
        "date",
        "opening",
        "closing",
        "gross_interest",
        "principal_flow",
        "paid_net_interest",
        "capitalized_interest",
        "net_dividend",
    ]
    assert len(payload["shl"]) == 61
    assert len(payload["project_cf"]) == 61
    assert len(payload["period_diagnostics"]) == 60
    assert payload["period_diagnostic_columns"][0] == "date"
    assert payload["period_diagnostics"][0][0] == "2030-06-30"
    assert payload["period_diagnostics"][-1][0] == "2059-12-31"


def test_full_period_diagnostics_cover_existing_period_fixture_dates() -> None:
    checks = [
        ("excel_oborovo_full_model_extract.json", "excel_oborovo_periods.json", 12),
        ("excel_tuho_full_model_extract.json", "excel_tuho_periods.json", 3),
    ]

    for full_name, period_name, limit in checks:
        full = _fixture(full_name)
        period_fixture = _fixture(period_name)["periods"][:limit]
        columns = full["period_diagnostic_columns"]
        rows = [
            {column: value for column, value in zip(columns, row)}
            for row in full["period_diagnostics"]
        ]
        by_date = {row["date"]: row for row in rows}
        for period in period_fixture:
            full_row = by_date[period["period_end_date"]]
            assert full_row["date"] == period["period_end_date"]
            assert "CF.free_cash_flow_for_banks_keur" in full_row
            assert "DS.senior_principal_keur" in full_row
            assert "P&L.taxable_income_keur" in full_row
            assert "Dep.depreciation_keur" in full_row


def test_oborovo_full_period_diagnostics_preserve_known_cfads_gap() -> None:
    full = _fixture("excel_oborovo_full_model_extract.json")
    period_fixture = _fixture("excel_oborovo_periods.json")
    columns = full["period_diagnostic_columns"]
    rows = [
        {column: value for column, value in zip(columns, row)}
        for row in full["period_diagnostics"]
    ]
    by_date = {row["date"]: row for row in rows}
    fixture_by_date = {row["period_end_date"]: row for row in period_fixture["periods"]}

    full_row = by_date["2032-06-30"]
    fixture_row = fixture_by_date["2032-06-30"]

    assert full_row["CF.free_cash_flow_for_banks_keur"] == pytest.approx(2610.818596342869)
    assert fixture_row["CF"]["free_cash_flow_for_banks_keur"] == pytest.approx(2587.225095914724)


def test_oborovo_full_shl_balance_schedule_has_expected_lifecycle() -> None:
    payload = _fixture("excel_oborovo_full_model_extract.json")
    shl = payload["shl"]

    first = shl[0]
    first_operation = shl[1]
    first_principal_repayment = next(row for row in shl if row[4] > 0)
    first_dividend = next(row for row in shl if row[7] > 0)
    final = shl[-1]

    assert first[0] == "2030-06-30"
    assert first[1] == 0.0
    assert first[4] < 0  # initial SHL draw / investment
    assert first[6] == first[3] - first[5]  # capitalized construction-period interest

    assert first_operation[0] == "2030-12-31"
    assert first_operation[1] == first[2]
    assert first_operation[3] > first_operation[5]
    assert first_operation[6] == first_operation[3] - first_operation[5]

    assert first_principal_repayment[0] == "2042-12-31"
    assert first_principal_repayment[4] > 0
    assert first_principal_repayment[6] == 0.0

    assert first_dividend[0] == "2050-06-30"
    assert first_dividend[2] == 0.0
    assert first_dividend[7] > 0

    assert final[0] == "2060-06-30"
    assert final[2] == 0.0
    assert final[7] > 0


def test_tuho_full_shl_balance_schedule_has_expected_lifecycle() -> None:
    payload = _fixture("excel_tuho_full_model_extract.json")
    shl = payload["shl"]

    first = shl[0]
    first_operation = shl[1]
    first_principal_repayment = next(row for row in shl if row[4] > 0)
    first_dividend = next(row for row in shl if row[7] > 0)
    final = shl[-1]

    assert first[0] == "2029-12-31"
    assert first[1] == 0.0
    assert first[4] < 0
    assert first[6] == first[3] - first[5]

    assert first_operation[0] == "2030-06-30"
    assert first_operation[1] == first[2]
    assert first_operation[3] > first_operation[5]
    assert first_operation[6] == first_operation[3] - first_operation[5]

    assert first_principal_repayment[0] == "2042-06-30"
    assert first_principal_repayment[4] > 0
    assert first_principal_repayment[6] == 0.0

    assert first_dividend[0] == "2047-12-31"
    assert first_dividend[2] == 0.0
    assert first_dividend[7] > 0

    assert final[0] == "2059-12-31"
    assert final[2] == 0.0
    assert final[7] > 0


def test_oborovo_full_project_irr_cash_flow_series_matches_excel_anchor() -> None:
    payload = _fixture("excel_oborovo_full_model_extract.json")
    project_cf = payload["project_cf"]

    assert payload["excel_unlevered_project_irr"] == 0.08280167281627655
    assert project_cf[0][0] == "2029-06-29"
    assert project_cf[0][2] == -55644.085499999994
    assert project_cf[1][0] == "2030-12-31"
    assert project_cf[1][2] == 2458.6514621946694
    assert project_cf[-1][0] == "2060-06-30"
    assert project_cf[-1][2] == 3206.8001297015044


def test_oborovo_full_unlevered_project_irr_recomputes_from_fixture_series() -> None:
    payload = _fixture("excel_oborovo_full_model_extract.json")
    project_cf = payload["project_cf"]

    dates = [date.fromisoformat(row[0]) for row in project_cf]
    unlevered_cash_flows = [row[2] for row in project_cf]

    assert payload["excel_unlevered_project_irr"] == 0.08280167281627655
    assert xirr(unlevered_cash_flows, dates) == pytest.approx(
        payload["excel_unlevered_project_irr"],
        abs=1e-8,
    )


def test_tuho_full_unlevered_project_irr_recomputes_from_fixture_series() -> None:
    payload = _fixture("excel_tuho_full_model_extract.json")
    project_cf = payload["project_cf"]

    dates = [date.fromisoformat(row[0]) for row in project_cf]
    unlevered_cash_flows = [row[2] for row in project_cf]

    assert payload["excel_unlevered_project_irr"] == 0.09108280837535859
    assert xirr(unlevered_cash_flows, dates) == pytest.approx(
        payload["excel_unlevered_project_irr"],
        abs=1e-8,
    )


def test_oborovo_full_project_irr_series_is_operating_only_diagnostic() -> None:
    payload = _fixture("excel_oborovo_full_model_extract.json")
    project_cf = payload["project_cf"]

    project_cash_flows = [row[1] for row in project_cf]

    assert payload["excel_project_irr"] == 0.0
    assert project_cash_flows[0] == 0.0
    assert all(value >= 0 for value in project_cash_flows)


def test_tuho_full_project_irr_recomputes_from_fixture_series() -> None:
    payload = _fixture("excel_tuho_full_model_extract.json")
    project_cf = payload["project_cf"]

    dates = [date.fromisoformat(row[0]) for row in project_cf]
    project_cash_flows = [row[1] for row in project_cf]

    assert payload["excel_project_irr"] == pytest.approx(0.09304675757884978)
    assert xirr(project_cash_flows, dates) == pytest.approx(
        payload["excel_project_irr"],
        abs=1e-8,
    )


def test_full_model_irr_extracts_match_calibration_targets() -> None:
    targets = _targets()
    oborovo = _fixture("excel_oborovo_full_model_extract.json")
    tuho = _fixture("excel_tuho_full_model_extract.json")

    assert oborovo["excel_unlevered_project_irr"] == pytest.approx(
        targets["oborovo"]["anchors"]["unlevered_project_irr"]["value"],
        abs=1e-8,
    )
    assert tuho["excel_project_irr"] == pytest.approx(
        targets["tuho"]["anchors"]["project_irr"]["value"],
        abs=1e-8,
    )
    assert tuho["excel_unlevered_project_irr"] == pytest.approx(
        targets["tuho"]["anchors"]["unlevered_project_irr"]["value"],
        abs=1e-8,
    )


def test_oborovo_full_project_cash_flow_series_has_one_initial_outflow() -> None:
    payload = _fixture("excel_oborovo_full_model_extract.json")
    unlevered = [row[2] for row in payload["project_cf"]]

    assert sum(1 for value in unlevered if value < 0) == 1
    assert all(value > 0 for value in unlevered[1:])


def test_tuho_full_project_cash_flow_series_has_one_initial_outflow() -> None:
    payload = _fixture("excel_tuho_full_model_extract.json")
    project = [row[1] for row in payload["project_cf"]]
    unlevered = [row[2] for row in payload["project_cf"]]

    assert sum(1 for value in project if value < 0) == 1
    assert sum(1 for value in unlevered if value < 0) == 1
    assert all(value > 0 for value in project[1:])
    assert all(value > 0 for value in unlevered[1:])


def test_tuho_full_sponsor_shl_cash_flow_series_has_one_initial_outflow() -> None:
    payload = _fixture("excel_tuho_full_model_extract.json")
    sponsor_cash_flows = [row[4] + row[5] + row[7] for row in payload["shl"]]

    assert sum(1 for value in sponsor_cash_flows if value < 0) == 1
    assert sponsor_cash_flows[0] < 0
    assert all(value >= 0 for value in sponsor_cash_flows[1:])
