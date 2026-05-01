"""Unit tests for full-model extract transformation helpers."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from domain.waterfall.full_model_extract import (
    project_cash_flow_rows,
    project_irr_from_extract,
    shl_lifecycle_by_date,
    shl_lifecycle_rows,
    sponsor_equity_shl_irr_from_extract,
    sponsor_equity_shl_irr_from_financial_close,
    sponsor_equity_shl_rows_from_extract,
    unlevered_project_irr_from_extract,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_project_cash_flow_rows_are_keyed_by_extract_columns() -> None:
    extract = _fixture("excel_tuho_full_model_extract.json")
    rows = project_cash_flow_rows(extract)

    assert rows[0] == {
        "date": "2028-06-30",
        "project_irr_cf": -72993.70678606197,
        "unlevered_project_irr_cf": -70271.53944444444,
        "fcf_for_banks": 0.0,
    }
    assert len(rows) == 61


def test_project_irr_helpers_recompute_full_model_anchors() -> None:
    oborovo = _fixture("excel_oborovo_full_model_extract.json")
    tuho = _fixture("excel_tuho_full_model_extract.json")

    assert unlevered_project_irr_from_extract(oborovo) == pytest.approx(0.08280167281627655)
    assert project_irr_from_extract(tuho) == pytest.approx(0.09304675757884978)
    assert unlevered_project_irr_from_extract(tuho) == pytest.approx(0.09108280837535859)


def test_shl_lifecycle_helpers_return_diagnostic_shape() -> None:
    extract = _fixture("excel_oborovo_full_model_extract.json")
    rows = shl_lifecycle_rows(extract)
    by_date = shl_lifecycle_by_date(extract)

    assert rows[0]["date"] == "2030-06-30"
    assert rows[0]["principal_flow"] < 0
    assert by_date["2030-12-31"]["opening_balance_keur"] == pytest.approx(rows[0]["closing"])
    assert by_date["2042-12-31"]["principal_paid_keur"] > 0
    assert by_date["2050-06-30"]["distribution_keur"] > 0


def test_sponsor_equity_shl_helpers_cover_excel_and_financial_close_timing() -> None:
    extract = _fixture("excel_tuho_full_model_extract.json")
    rows = sponsor_equity_shl_rows_from_extract(extract)

    assert rows[0]["date"] == "2029-12-31"
    assert rows[0]["cash_flow_keur"] < 0
    assert sponsor_equity_shl_irr_from_extract(extract) == pytest.approx(0.1297858541821568)
    assert sponsor_equity_shl_irr_from_financial_close(
        extract,
        date(2028, 6, 30),
    ) == pytest.approx(0.11609521789898895)
