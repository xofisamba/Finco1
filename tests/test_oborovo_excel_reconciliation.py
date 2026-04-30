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
TARGETS = ROOT / "tests" / "fixtures" / "excel_calibration_targets.json"


def _oborovo_targets() -> dict:
    payload = json.loads(TARGETS.read_text(encoding="utf-8"))
    return payload["oborovo"]["anchors"]


def test_oborovo_excel_targets_have_required_anchors() -> None:
    anchors = _oborovo_targets()
    for key in ("total_capex_keur", "senior_debt_keur", "unlevered_project_irr"):
        assert key in anchors
        assert anchors[key]["value"] > 0
        assert anchors[key]["source"]


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


@pytest.mark.xfail(reason="Known Sprint 4 calibration gap: app project IRR does not yet match Oborovo Excel")
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
