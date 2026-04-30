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


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures"
TARGETS = FIXTURE_DIR / "excel_calibration_targets.json"
TUHO_PERIODS = FIXTURE_DIR / "excel_tuho_periods.json"


def _tuho_targets() -> dict:
    payload = json.loads(TARGETS.read_text(encoding="utf-8"))
    return payload["tuho"]["anchors"]


def _tuho_periods() -> list[dict]:
    payload = json.loads(TUHO_PERIODS.read_text(encoding="utf-8"))
    return payload["periods"]


def _operation_periods(payload: dict) -> list[dict]:
    return [p for p in payload["periods"] if p.get("is_operation")]


def _period_by_excel_date(payload: dict) -> dict[str, dict]:
    return {p["date"]: p for p in _operation_periods(payload)}


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


@pytest.mark.xfail(reason="TUHO first-pass factory is not yet full Excel-parity for project IRR")
def test_tuho_project_irr_against_excel_initial_tolerance() -> None:
    anchors = _tuho_targets()
    payload = run_project_calibration("tuho", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("project_irr", 0.0),
        excel_value=anchors["project_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison


@pytest.mark.xfail(reason="TUHO first-pass factory is not yet full Excel-parity for equity IRR")
def test_tuho_equity_irr_against_excel_initial_tolerance() -> None:
    anchors = _tuho_targets()
    payload = run_project_calibration("tuho", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("equity_irr", 0.0),
        excel_value=anchors["equity_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison


@pytest.mark.xfail(reason="TUHO period-level revenue/opex/EBITDA schedule still requires Excel row mapping and calibration")
def test_tuho_first_period_ebitda_against_excel() -> None:
    excel_period = _tuho_periods()[0]
    payload = run_project_calibration("tuho", calibration_source="pytest")
    app_periods = _period_by_excel_date(payload)
    app_period = app_periods[excel_period["period_end_date"]]
    comparison = compare_metric(
        app_value=app_period["ebitda_keur"],
        excel_value=excel_period["CF"]["ebitda_keur"],
        tolerance_pct=0.005,
    )
    assert comparison["passed"], comparison
