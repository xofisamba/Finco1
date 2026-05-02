"""TUHO Excel reconciliation scaffold.

TUHO is now wired into the headless runner through a first-pass app-level
project factory. These tests keep the Excel anchors visible while remaining
honest that full period-level calibration is not complete yet.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import compare_metric, run_project_calibration
from tests.reconciliation_helpers import collect_period_failures, period_by_date


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures"
TARGETS = FIXTURE_DIR / "excel_calibration_targets.json"
TUHO_PERIODS = FIXTURE_DIR / "excel_tuho_periods.json"


TUHO_PERIOD_METRIC_SPECS = [
    {
        "excel_sheet": "CF",
        "excel_metric": "operating_revenues_keur",
        "app_metric": "revenue_keur",
        "tolerance_pct": 0.005,
    },
    {
        "excel_sheet": "CF",
        "excel_metric": "ebitda_keur",
        "app_metric": "ebitda_keur",
        "tolerance_pct": 0.005,
    },
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


def _tuho_targets() -> dict:
    payload = json.loads(TARGETS.read_text(encoding="utf-8"))
    return payload["tuho"]["anchors"]


def _tuho_periods() -> list[dict]:
    payload = json.loads(TUHO_PERIODS.read_text(encoding="utf-8"))
    return payload["periods"]


def test_tuho_excel_targets_have_required_anchors() -> None:
    anchors = _tuho_targets()
    for key in ("total_capex_keur", "senior_debt_keur", "project_irr", "equity_irr"):
        assert key in anchors
        assert anchors[key]["value"] > 0
        assert anchors[key]["source"]


def test_tuho_period_fixture_has_reconciliation_rows() -> None:
    periods = _tuho_periods()
    assert len(periods) >= 3
    for period in periods:
        assert period["CF"]["operating_revenues_keur"] > 0
        assert period["CF"]["senior_debt_service_keur"] < 0
        assert period["DS"]["senior_principal_keur"] > 0
        assert period["DS"]["senior_net_interest_keur"] > 0
        assert period["P&L"]["total_revenues_keur"] == period["CF"]["operating_revenues_keur"]


def test_tuho_headless_payload_shape() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    assert payload["project_key"] == "tuho"
    assert payload["calibration_source"] == "pytest"
    assert "kpis" in payload
    assert "periods" in payload
    assert payload["periods"], "period-level output is required for reconciliation"


def test_tuho_senior_debt_against_excel_initial_tolerance() -> None:
    """TUHO senior debt is fixed to the Excel anchor in the first-pass factory."""
    anchors = _tuho_targets()
    payload = run_project_calibration("tuho", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("senior_debt_keur", 0.0),
        excel_value=anchors["senior_debt_keur"]["value"],
        tolerance_pct=0.01,
    )
    assert comparison["passed"], comparison


def test_tuho_project_irr_against_excel_initial_tolerance() -> None:
    anchors = _tuho_targets()
    payload = run_project_calibration("tuho", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("project_irr", 0.0),
        excel_value=anchors["project_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison


def test_tuho_equity_irr_against_excel_initial_tolerance() -> None:
    anchors = _tuho_targets()
    payload = run_project_calibration("tuho", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("equity_irr", 0.0),
        excel_value=anchors["equity_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison


def test_tuho_first_three_periods_core_lines_against_excel() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_tuho_periods()[:3],
        metric_specs=TUHO_PERIOD_METRIC_SPECS,
    )
    assert not failures, failures


def test_tuho_full_horizon_project_cash_flow_gap_is_exposed() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    summary = payload["engine_project_cash_flow_gap_before_full_model_calibration"]

    assert summary["source"] == "native_engine_before_full_model_calibration"
    assert summary["compared_rows"] == 59
    assert summary["first_fcf_for_banks_mismatch"]["date"] == "2031-12-31"
    assert summary["max_abs_fcf_for_banks_delta_keur"] > 0.0


def test_tuho_full_horizon_native_series_are_available_for_period_parity() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")

    assert payload["project_cash_flows"]["source"] == "full_model_extract_bridge"
    assert len(payload["project_cash_flows"]["rows"]) == 61
    assert payload["project_cash_flows"]["rows"][0]["date"] == "2028-06-30"
    assert payload["project_cash_flows"]["rows"][-1]["date"] == "2059-12-31"
    assert payload["shl_lifecycle_decomposition"]["source"] == "full_model_extract_bridge"
    assert len(payload["shl_lifecycle_decomposition"]["rows"]) == 61
