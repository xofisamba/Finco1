"""P&L / tax Excel-alignment diagnostics.

These tests isolate depreciation, taxable income and corporate tax rows before
project IRR reconciliation. Oborovo first12 rows are anchored to extracted Excel
P&L values until full tax-loss / ATAD / depreciation mechanics are mapped.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import run_project_calibration
from tests.reconciliation_helpers import collect_period_failures, period_by_date


FIXTURE_DIR = Path(__file__).parent / "fixtures"


OBOROVO_PL_TAX_METRIC_SPECS = [
    {
        "excel_sheet": "P&L",
        "excel_metric": "depreciation_keur",
        "app_metric": "depreciation_keur",
        "tolerance_pct": 0.005,
    },
    {
        "excel_sheet": "P&L",
        "excel_metric": "taxable_income_keur",
        "app_metric": "taxable_profit_keur",
        "tolerance_abs": 0.01,
    },
    {
        "excel_sheet": "P&L",
        "excel_metric": "corporate_income_tax_keur",
        "app_metric": "tax_keur",
        "tolerance_abs": 0.01,
    },
]

OBOROVO_DEPRECIATION_METRIC_SPECS = [OBOROVO_PL_TAX_METRIC_SPECS[0]]
OBOROVO_TAXABLE_INCOME_METRIC_SPECS = [OBOROVO_PL_TAX_METRIC_SPECS[1]]
OBOROVO_CORPORATE_TAX_METRIC_SPECS = [OBOROVO_PL_TAX_METRIC_SPECS[2]]


def _period_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["periods"]


def test_oborovo_pl_tax_fixture_has_first_twelve_periods() -> None:
    rows = _period_fixture("excel_oborovo_periods.json")[:12]
    assert len(rows) == 12
    for row in rows:
        assert row["P&L"]["depreciation_keur"] > 0
        assert "taxable_income_keur" in row["P&L"]
        assert row["P&L"]["corporate_income_tax_keur"] >= 0


def test_oborovo_first_twelve_depreciation_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_DEPRECIATION_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_first_twelve_taxable_income_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_TAXABLE_INCOME_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_first_twelve_corporate_tax_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_CORPORATE_TAX_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_first_twelve_pl_tax_lines_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_PL_TAX_METRIC_SPECS,
    )
    assert not failures, failures


def test_tuho_first_three_pl_tax_lines_against_excel() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_tuho_periods.json")[:3],
        metric_specs=OBOROVO_PL_TAX_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_non_anchor_cf_after_tax_reflects_tax_charge() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    row = period_by_date(payload)["2036-12-31"]

    assert row["tax_keur"] > 0.0
    assert row["cf_after_tax_keur"] == pytest.approx(
        row["ebitda_keur"] - row["tax_keur"],
    )


def test_oborovo_full_model_pl_tax_gap_summary_identifies_first_formula_delta() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    summary = payload["engine_pl_tax_gap_before_full_model_calibration"]

    assert summary["source"] == "native_engine_before_full_model_calibration"
    assert summary["type"] == "pl_tax"
    assert summary["compared_rows"] == 59
    assert summary["compared_metrics"] == [
        {
            "native_metric": "depreciation_keur",
            "excel_metric": "P&L.depreciation_keur",
            "excel_sign": 1.0,
        },
        {
            "native_metric": "taxable_profit_keur",
            "excel_metric": "P&L.taxable_income_keur",
            "excel_sign": 1.0,
        },
        {
            "native_metric": "tax_keur",
            "excel_metric": "P&L.corporate_income_tax_keur",
            "excel_sign": 1.0,
        },
    ]
    assert summary["mismatch_count"] == 161
    assert summary["max_abs_delta"] == pytest.approx(1399.6919484904292)
    assert summary["max_abs_delta_location"]["date"] == "2049-12-31"
    assert summary["max_abs_delta_location"]["metric"] == "taxable_profit_keur"
    assert summary["first_mismatch"]["date"] == "2032-06-30"
    assert summary["first_mismatch"]["metric"] == "depreciation_keur"


def test_tuho_non_anchor_cf_after_tax_reflects_tax_charge() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    row = period_by_date(payload)["2037-06-30"]

    assert row["tax_keur"] > 0.0
    assert row["cf_after_tax_keur"] == pytest.approx(
        row["ebitda_keur"] - row["tax_keur"],
    )


def test_tuho_full_model_pl_tax_gap_summary_identifies_first_formula_delta() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    summary = payload["engine_pl_tax_gap_before_full_model_calibration"]

    assert summary["source"] == "native_engine_before_full_model_calibration"
    assert summary["type"] == "pl_tax"
    assert summary["compared_rows"] == 59
    assert summary["mismatch_count"] == 168
    assert summary["max_abs_delta"] == pytest.approx(5045.90874270812)
    assert summary["max_abs_delta_location"]["date"] == "2041-12-31"
    assert summary["max_abs_delta_location"]["metric"] == "taxable_profit_keur"
    assert summary["first_mismatch"]["date"] == "2031-12-31"
    assert summary["first_mismatch"]["metric"] == "depreciation_keur"
