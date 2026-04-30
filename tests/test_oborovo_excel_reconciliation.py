"""Oborovo Excel reconciliation scaffold.

This test module compares headless app output against first-pass Excel anchors.
It is intentionally explicit about current calibration gaps: the purpose is to
surface deltas, not to hide them behind broad tolerances.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import compare_metric, run_project_calibration


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures"
TARGETS = FIXTURE_DIR / "excel_calibration_targets.json"
OBOROVO_PERIODS = FIXTURE_DIR / "excel_oborovo_periods.json"


def _oborovo_targets() -> dict:
    payload = json.loads(TARGETS.read_text(encoding="utf-8"))
    return payload["oborovo"]["anchors"]


def _oborovo_periods() -> list[dict]:
    payload = json.loads(OBOROVO_PERIODS.read_text(encoding="utf-8"))
    return payload["periods"]


def _operation_periods(payload: dict) -> list[dict]:
    return [p for p in payload["periods"] if p.get("is_operation")]


def _period_by_excel_date(payload: dict) -> dict[str, dict]:
    return {p["date"]: p for p in _operation_periods(payload)}


def test_oborovo_excel_targets_have_required_anchors() -> None:
    anchors = _oborovo_targets()
    for key in ("total_capex_keur", "senior_debt_keur", "unlevered_project_irr"):
        assert key in anchors
        assert anchors[key]["value"] > 0
        assert anchors[key]["source"]


def test_oborovo_period_fixture_has_reconciliation_rows() -> None:
    periods = _oborovo_periods()
    assert len(periods) >= 3
    for period in periods:
        assert period["CF"]["operating_revenues_keur"] > 0
        assert period["CF"]["senior_debt_service_keur"] < 0
        assert period["DS"]["senior_principal_keur"] > 0
        assert period["DS"]["senior_net_interest_keur"] > 0
        assert period["P&L"]["total_revenues_keur"] == period["CF"]["operating_revenues_keur"]


def test_oborovo_headless_payload_shape() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    assert payload["project_key"] == "oborovo"
    assert payload["calibration_source"] == "pytest"
    assert "kpis" in payload
    assert "periods" in payload
    assert payload["periods"], "period-level output is required for reconciliation"


def test_oborovo_senior_debt_against_excel_initial_tolerance() -> None:
    """Senior debt should be close enough to keep reconciliation meaningful."""
    anchors = _oborovo_targets()
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("senior_debt_keur", 0.0),
        excel_value=anchors["senior_debt_keur"]["value"],
        tolerance_pct=0.01,
    )
    assert comparison["passed"], comparison


@pytest.mark.xfail(reason="Known calibration gap: app project IRR does not yet match Oborovo Excel")
def test_oborovo_project_irr_against_excel_initial_tolerance() -> None:
    """Diagnostic xfail until period-by-period revenue/tax/debt reconciliation is complete."""
    anchors = _oborovo_targets()
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("project_irr", 0.0),
        excel_value=anchors["unlevered_project_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison


@pytest.mark.xfail(reason="Known calibration gap: revenue/opex/EBITDA schedule is not yet Excel-parity")
def test_oborovo_first_period_ebitda_against_excel() -> None:
    excel_period = _oborovo_periods()[0]
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    app_periods = _period_by_excel_date(payload)
    app_period = app_periods[excel_period["period_end_date"]]
    comparison = compare_metric(
        app_value=app_period["ebitda_keur"],
        excel_value=excel_period["CF"]["ebitda_keur"],
        tolerance_pct=0.005,
    )
    assert comparison["passed"], comparison


@pytest.mark.xfail(reason="Known calibration gap: debt service schedule still differs from Excel period rows")
def test_oborovo_first_three_period_debt_service_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    app_periods = _period_by_excel_date(payload)
    failures = []
    for excel_period in _oborovo_periods()[:3]:
        app_period = app_periods[excel_period["period_end_date"]]
        comparison = compare_metric(
            app_value=-app_period["senior_ds_keur"],
            excel_value=-excel_period["CF"]["senior_debt_service_keur"],
            tolerance_pct=0.005,
        )
        if not comparison["passed"]:
            failures.append({"period_end_date": excel_period["period_end_date"], **comparison})
    assert not failures, failures
