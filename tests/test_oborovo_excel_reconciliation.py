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
from tests.reconciliation_helpers import collect_period_failures, period_by_date
from tests.test_debt_excel_alignment import _excel_app_debt_diagnostic_rows


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures"
TARGETS = FIXTURE_DIR / "excel_calibration_targets.json"
OBOROVO_PERIODS = FIXTURE_DIR / "excel_oborovo_periods.json"


OBOROVO_REVENUE_METRIC_SPECS = [
    {
        "excel_sheet": "CF",
        "excel_metric": "operating_revenues_keur",
        "app_metric": "revenue_keur",
        "tolerance_pct": 0.005,
    },
]

OBOROVO_EBITDA_METRIC_SPECS = [
    {
        "excel_sheet": "CF",
        "excel_metric": "ebitda_keur",
        "app_metric": "ebitda_keur",
        "tolerance_pct": 0.005,
    },
]

OBOROVO_DEBT_SERVICE_METRIC_SPECS = [
    {
        "excel_sheet": "CF",
        "excel_metric": "senior_debt_service_keur",
        "app_metric": "senior_ds_keur",
        "excel_sign": -1.0,
        "app_sign": 1.0,
        "tolerance_pct": 0.005,
    },
]

OBOROVO_DEBT_INTEREST_METRIC_SPECS = [
    {
        "excel_sheet": "DS",
        "excel_metric": "senior_net_interest_keur",
        "app_metric": "senior_interest_keur",
        "tolerance_pct": 0.005,
    },
]

OBOROVO_DEBT_PRINCIPAL_METRIC_SPECS = [
    {
        "excel_sheet": "DS",
        "excel_metric": "senior_principal_keur",
        "app_metric": "senior_principal_keur",
        "tolerance_pct": 0.005,
    },
]

OBOROVO_DEBT_SPLIT_METRIC_SPECS = [
    *OBOROVO_DEBT_PRINCIPAL_METRIC_SPECS,
    *OBOROVO_DEBT_INTEREST_METRIC_SPECS,
]


def _oborovo_targets() -> dict:
    payload = json.loads(TARGETS.read_text(encoding="utf-8"))
    return payload["oborovo"]["anchors"]


def _oborovo_periods() -> list[dict]:
    payload = json.loads(OBOROVO_PERIODS.read_text(encoding="utf-8"))
    return payload["periods"]


def test_oborovo_excel_targets_have_required_anchors() -> None:
    anchors = _oborovo_targets()
    for key in ("total_capex_keur", "senior_debt_keur", "unlevered_project_irr"):
        assert key in anchors
        assert anchors[key]["value"] > 0
        assert anchors[key]["source"]


def test_oborovo_period_fixture_has_reconciliation_rows() -> None:
    periods = _oborovo_periods()
    assert len(periods) >= 12
    for period in periods:
        assert period["CF"]["operating_revenues_keur"] > 0
        assert period["CF"]["senior_debt_service_keur"] < 0
        assert period["DS"]["senior_principal_keur"] > 0
        assert period["DS"]["senior_net_interest_keur"] > 0
        assert period["P&L"]["total_revenues_keur"] == period["CF"]["operating_revenues_keur"]
        assert period["CF"]["ebitda_keur"] == (
            period["CF"]["operating_revenues_keur"]
            + period["CF"]["operating_expenses_after_bank_tax_keur"]
        )


def test_oborovo_headless_payload_shape() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    assert payload["project_key"] == "oborovo"
    assert payload["calibration_source"] == "pytest"
    assert "kpis" in payload
    assert "periods" in payload
    assert payload["periods"], "period-level output is required for reconciliation"
    assert all(row["is_operation"] for row in payload["periods"])


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


def test_oborovo_first_twelve_period_revenue_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_oborovo_periods()[:12],
        metric_specs=OBOROVO_REVENUE_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_first_twelve_period_ebitda_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_oborovo_periods()[:12],
        metric_specs=OBOROVO_EBITDA_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_first_twelve_period_debt_service_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_oborovo_periods()[:12],
        metric_specs=OBOROVO_DEBT_SERVICE_METRIC_SPECS,
    )
    assert not failures, failures


@pytest.mark.xfail(reason="Known calibration gap: interest rate / fee convention is not yet Excel-parity")
def test_oborovo_first_twelve_periods_debt_interest_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_oborovo_periods()[:12],
        metric_specs=OBOROVO_DEBT_INTEREST_METRIC_SPECS,
    )
    if failures:
        raise AssertionError({
            "interest_failures": failures,
            "debt_gap_diagnostics": _excel_app_debt_diagnostic_rows(limit=12),
        })


@pytest.mark.xfail(reason="Known calibration gap: principal amortization timing is not yet Excel-parity")
def test_oborovo_first_twelve_periods_debt_principal_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_oborovo_periods()[:12],
        metric_specs=OBOROVO_DEBT_PRINCIPAL_METRIC_SPECS,
    )
    if failures:
        raise AssertionError({
            "principal_failures": failures,
            "debt_gap_diagnostics": _excel_app_debt_diagnostic_rows(limit=12),
        })


@pytest.mark.xfail(reason="Known calibration gap: principal / interest split is not yet Excel-parity")
def test_oborovo_first_twelve_periods_debt_principal_and_interest_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_oborovo_periods()[:12],
        metric_specs=OBOROVO_DEBT_SPLIT_METRIC_SPECS,
    )
    if failures:
        raise AssertionError({
            "line_failures": failures,
            "debt_gap_diagnostics": _excel_app_debt_diagnostic_rows(limit=12),
        })
