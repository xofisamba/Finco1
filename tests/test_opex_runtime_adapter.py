from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from domain.opex.runtime_adapter import build_runtime_opex_schedule

EXCEL_ANNUAL_TOTALS = (
    1998.05,
    2029.83,
    2147.06,
    2180.13,
    2213.86,
    2378.01,
    2413.10,
    2448.90,
    2485.41,
    2522.65,
    2603.04,
    2641.79,
    2681.31,
    2721.62,
    2734.77,
    2827.03,
    2869.24,
    2912.29,
    2956.21,
    3001.00,
    3131.49,
    3178.09,
    3225.63,
    3274.11,
    3323.57,
    3450.33,
    3501.79,
    3554.27,
    3607.80,
    3662.40,
)


def test_tuho_runtime_adapter_matches_excel_annual_totals():
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)

    result = build_runtime_opex_schedule(project, engine)

    assert result.annual_result.grand_total_keur == pytest.approx(84_674.78, abs=0.01)
    assert result.annual_result.total_by_year_keur == pytest.approx(EXCEL_ANNUAL_TOTALS, abs=0.01)
    assert sum(result.period_schedule_keur.values()) == pytest.approx(84_674.78, abs=0.01)


def test_runtime_adapter_rejects_unsupported_project():
    project = create_default_oborovo()
    engine = _build_period_engine(project)

    with pytest.raises(ValueError, match="only supported for TUHO-WIND-1"):
        build_runtime_opex_schedule(project, engine)


def test_runtime_adapter_does_not_import_waterfall():
    source = Path("domain/opex/runtime_adapter.py").read_text(encoding="utf-8")

    assert "domain.waterfall" not in source
