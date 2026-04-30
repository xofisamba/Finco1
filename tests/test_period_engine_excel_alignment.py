"""Excel-alignment regression tests for PeriodEngine.

These tests protect the date axis used by calibration fixtures. If the date axis
moves, every period-level reconciliation becomes meaningless.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.calibration import build_period_engine, load_project_inputs


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture_dates(name: str) -> list[str]:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return [p["period_end_date"] for p in payload["periods"]]


def _engine_operation_dates(project_key: str) -> list[str]:
    inputs = load_project_inputs(project_key)
    engine = build_period_engine(inputs)
    return [p.end_date.isoformat() for p in engine.operation_periods()]


def test_oborovo_first_fixture_dates_match_period_engine() -> None:
    assert _engine_operation_dates("oborovo")[:3] == _fixture_dates("excel_oborovo_periods.json")[:3]


def test_tuho_first_fixture_dates_match_period_engine() -> None:
    assert _engine_operation_dates("tuho")[:3] == _fixture_dates("excel_tuho_periods.json")[:3]
