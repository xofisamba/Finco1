"""Project IRR / unlevered cash-flow Excel-alignment diagnostics.

These tests isolate the project cash-flow series before promoting project IRR.
Oborovo first12 operating cash flows are compared to the Excel CF sheet. Full
project IRR remains diagnostic until construction-period capex timing and the
complete operating/terminal cash-flow series are mapped.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import compare_metric, run_project_calibration
from app.calibration_runner import load_project_inputs
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
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["periods"]


def _targets(project_key: str) -> dict:
    payload = json.loads(TARGETS.read_text(encoding="utf-8"))
    return payload[project_key]["anchors"]


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


@pytest.mark.xfail(reason="Full Oborovo project IRR requires exact Excel construction capex timing and complete cash-flow series")
def test_oborovo_project_irr_against_excel() -> None:
    anchors = _targets("oborovo")
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("project_irr", 0.0),
        excel_value=anchors["unlevered_project_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison


@pytest.mark.xfail(reason="TUHO full project IRR requires exact Excel construction capex timing and complete cash-flow series")
def test_tuho_project_irr_against_excel() -> None:
    anchors = _targets("tuho")
    payload = run_project_calibration("tuho", calibration_source="pytest")
    comparison = compare_metric(
        app_value=payload["kpis"].get("project_irr", 0.0),
        excel_value=anchors["project_irr"]["value"],
        tolerance_abs=0.005,
    )
    assert comparison["passed"], comparison
