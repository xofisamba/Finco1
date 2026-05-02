"""Project IRR / unlevered cash-flow Excel-alignment diagnostics.

These tests isolate the project cash-flow series before promoting native app
project IRR. Oborovo first12 operating cash flows are compared to the Excel CF
sheet. Full Excel-sourced project IRR is active through the extracted full-model
payload, while native engine IRR remains diagnostic until the engine reproduces
the complete construction/operating/terminal cash-flow series.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.calibration import compare_metric, run_project_calibration
from app.calibration_runner import load_project_inputs
from domain.returns.xirr import xirr
from tests.reconciliation_helpers import collect_period_failures, period_by_date


FIXTURE_DIR = Path(__file__).parent / "fixtures"
TARGETS = FIXTURE_DIR / "excel_calibration_targets.json"


OBOROVO_PROJECT_OPERATING_CF_METRIC_SPECS = [
    {
        "excel_sheet": "CF",
        "excel_metric": "free_cash_flow_for_banks_keur",
        "app_metric": "cf_after_tax_keur",
        "tolerance_pct": 0.005,
    },
]


def _period_fixture(name: str) -> list[dict]:
    full_model_name = name.replace("_periods.json", "_full_model_extract.json")
    full_model_path = FIXTURE_DIR / full_model_name
    if full_model_path.exists():
        extract = json.loads(full_model_path.read_text(encoding="utf-8"))
        columns = extract["period_diagnostic_columns"]
        rows = []
        for raw in extract["period_diagnostics"]:
            row = {column: value for column, value in zip(columns, raw)}
            rows.append({
                "period_end_date": row["date"],
                "CF": {
                    "free_cash_flow_for_banks_keur": row["CF.free_cash_flow_for_banks_keur"],
                },
            })
        return rows
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["periods"]


def _targets(project_key: str) -> dict:
    payload = json.loads(TARGETS.read_text(encoding="utf-8"))
    return payload[project_key]["anchors"]


def _full_model_extract(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _project_cash_flow_rows_from_payload(payload: dict) -> list[dict]:
    """Return explicit project cash-flow rows from serialized payload.

    Definition under test:
    - Initial outflow is total project capex at financial close/construction.
    - Operating inflow is post-tax unlevered project cash flow, proxied here by
      `cf_after_tax_keur` in the calibrated period payload.

    Full IRR parity requires replacing the single initial outflow with the exact
    Excel construction-period capex timing once those rows are extracted.
    """
    return [
        {
            "date": row["date"],
            "cash_flow_keur": row["cf_after_tax_keur"],
            "source": "cf_after_tax_keur",
        }
        for row in payload["periods"]
        if row["is_operation"]
    ]


def test_oborovo_first_twelve_project_operating_cash_flow_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_PROJECT_OPERATING_CF_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_project_cash_flow_rows_use_post_tax_unlevered_cf() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    rows = _project_cash_flow_rows_from_payload(payload)
    assert rows
    assert rows[0]["date"] == "2030-12-31"
    assert rows[0]["cash_flow_keur"] == payload["periods"][0]["cf_after_tax_keur"]
    assert rows[9]["cash_flow_keur"] == (
        payload["periods"][9]["ebitda_keur"] - payload["periods"][9]["tax_keur"]
    )


def test_oborovo_project_initial_capex_anchor_against_excel() -> None:
    inputs = load_project_inputs("oborovo")
    anchors = _targets("oborovo")
    comparison = compare_metric(
        app_value=inputs.capex.total_capex,
        excel_value=anchors["total_capex_keur"]["value"],
        tolerance_pct=0.005,
    )
    assert comparison["passed"], comparison


def test_oborovo_excel_full_model_unlevered_project_irr_payload_matches_anchor() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    extract = _full_model_extract("excel_oborovo_full_model_extract.json")
    excel_full = payload["excel_full_model_project_irr"]

    dates = [date.fromisoformat(row["date"]) for row in excel_full["rows"]]
    unlevered_cash_flows = [row["unlevered_project_irr_cf"] for row in excel_full["rows"]]

    assert excel_full["workbook_sha256"] == extract["workbook_sha256"]
    assert excel_full["columns"] == extract["project_cf_columns"]
    assert len(excel_full["rows"]) == len(extract["project_cf"]) == 61
    assert excel_full["excel_unlevered_project_irr"] == pytest.approx(
        _targets("oborovo")["unlevered_project_irr"]["value"],
        abs=1e-8,
    )
    assert excel_full["computed_unlevered_project_irr"] == pytest.approx(
        excel_full["excel_unlevered_project_irr"],
        abs=1e-8,
    )
    assert xirr(unlevered_cash_flows, dates) == pytest.approx(
        payload["kpis"]["excel_full_model_unlevered_project_irr"],
        abs=1e-8,
    )
    assert payload["project_cash_flows"]["rows"] == excel_full["rows"]
    assert payload["project_cash_flows"]["rows"][0]["date"] == "2029-06-29"
    gap = payload["engine_return_gap_before_full_model_calibration"]
    assert gap["source"] == "native_engine_before_full_model_calibration"
    assert gap["project_irr"]["excel_value"] == pytest.approx(
        excel_full["excel_unlevered_project_irr"],
        abs=1e-8,
    )
    assert gap["project_irr"]["engine_value"] == pytest.approx(
        payload["kpis"]["engine_project_irr_before_full_model_calibration"],
        abs=1e-8,
    )


def test_oborovo_project_cash_flow_gap_summary_identifies_full_model_delta() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    summary = payload["engine_project_cash_flow_gap_before_full_model_calibration"]

    assert summary["source"] == "native_engine_before_full_model_calibration"
    assert summary["compared_rows"] == 59
    assert summary["max_abs_fcf_for_banks_delta_keur"] == pytest.approx(1271.3217453242419)
    first_mismatch = summary["first_fcf_for_banks_mismatch"]
    assert first_mismatch["date"] == "2032-06-30"
    assert first_mismatch["native_fcf_for_banks_keur"] == pytest.approx(2587.2250959147236)
    assert first_mismatch["excel_fcf_for_banks_keur"] == pytest.approx(2610.818596342869)
    assert first_mismatch["delta_keur"] == pytest.approx(-23.59350042814549)


def test_tuho_excel_full_model_project_irr_payload_matches_anchors() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    extract = _full_model_extract("excel_tuho_full_model_extract.json")
    excel_full = payload["excel_full_model_project_irr"]

    assert excel_full["workbook_sha256"] == extract["workbook_sha256"]
    assert excel_full["columns"] == extract["project_cf_columns"]
    assert len(excel_full["rows"]) == len(extract["project_cf"]) == 61
    assert excel_full["excel_project_irr"] == pytest.approx(
        _targets("tuho")["project_irr"]["value"],
        abs=1e-8,
    )
    assert excel_full["excel_unlevered_project_irr"] == pytest.approx(
        _targets("tuho")["unlevered_project_irr"]["value"],
        abs=1e-8,
    )
    assert excel_full["computed_project_irr"] == pytest.approx(
        excel_full["excel_project_irr"],
        abs=1e-8,
    )
    assert excel_full["computed_unlevered_project_irr"] == pytest.approx(
        excel_full["excel_unlevered_project_irr"],
        abs=1e-8,
    )
    assert payload["kpis"]["excel_full_model_project_irr"] == pytest.approx(
        _targets("tuho")["project_irr"]["value"],
        abs=1e-8,
    )
    assert payload["kpis"]["excel_full_model_unlevered_project_irr"] == pytest.approx(
        _targets("tuho")["unlevered_project_irr"]["value"],
        abs=1e-8,
    )
    assert payload["project_cash_flows"]["rows"] == excel_full["rows"]
    assert payload["project_cash_flows"]["rows"][0]["project_irr_cf"] < 0
    gap = payload["engine_return_gap_before_full_model_calibration"]
    assert gap["source"] == "native_engine_before_full_model_calibration"
    assert gap["project_irr"]["excel_value"] == pytest.approx(
        excel_full["excel_project_irr"],
        abs=1e-8,
    )
    assert gap["sponsor_equity_shl_irr"]["excel_value"] == pytest.approx(
        payload["kpis"]["sponsor_equity_shl_irr"],
        abs=1e-8,
    )


def test_tuho_project_cash_flow_gap_summary_identifies_full_model_delta() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    summary = payload["engine_project_cash_flow_gap_before_full_model_calibration"]

    assert summary["source"] == "native_engine_before_full_model_calibration"
    assert summary["compared_rows"] == 59
    assert summary["max_abs_fcf_for_banks_delta_keur"] == pytest.approx(2567.650754178724)
    first_mismatch = summary["first_fcf_for_banks_mismatch"]
    assert first_mismatch["date"] == "2031-12-31"
    assert first_mismatch["native_fcf_for_banks_keur"] == pytest.approx(3901.390057946259)
    assert first_mismatch["excel_fcf_for_banks_keur"] == pytest.approx(3163.2241181486525)
    assert first_mismatch["delta_keur"] == pytest.approx(738.1659397976064)


def test_oborovo_project_irr_against_excel() -> None:
    anchors = _targets("oborovo")
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("project_irr", 0.0),
        excel_value=anchors["unlevered_project_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison


def test_tuho_project_irr_against_excel() -> None:
    anchors = _targets("tuho")
    payload = run_project_calibration("tuho", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("project_irr", 0.0),
        excel_value=anchors["project_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison
