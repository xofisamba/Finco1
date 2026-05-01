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


def test_oborovo_full_project_cash_flow_series_has_one_initial_outflow() -> None:
    payload = _fixture("excel_oborovo_full_model_extract.json")
    unlevered = [row[2] for row in payload["project_cf"]]

    assert sum(1 for value in unlevered if value < 0) == 1
    assert all(value > 0 for value in unlevered[1:])
