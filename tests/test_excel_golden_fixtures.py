"""Integrity tests for Excel golden calibration fixtures.

These tests intentionally validate the fixture schema and source-cell provenance
before the app is forced to match every Excel number. They prevent silent edits
to calibration anchors and make each target traceable to a workbook cell.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_FILES = [
    FIXTURE_DIR / "excel_golden_oborovo.json",
    FIXTURE_DIR / "excel_golden_tuho.json",
]
PERIOD_FIXTURE_FILES = [
    FIXTURE_DIR / "excel_oborovo_periods.json",
    FIXTURE_DIR / "excel_tuho_periods.json",
]


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES)
def test_excel_golden_fixture_has_required_top_level_keys(fixture_path: Path) -> None:
    data = json.loads(fixture_path.read_text())

    assert data["project"] in {"oborovo", "tuho"}
    assert data["source_workbook"].endswith(".xlsm")
    assert "raw workbook is intentionally not committed" in data["extraction_note"].lower()
    assert isinstance(data["worksheets"], dict)
    assert isinstance(data["golden_cells"], dict)
    assert isinstance(data["initial_tolerances"], dict)


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES)
def test_excel_golden_fixture_tracks_workbook_core_sheets(fixture_path: Path) -> None:
    data = json.loads(fixture_path.read_text())
    worksheets = data["worksheets"]

    required_sheets = {
        "Inputs",
        "Outputs",
        "CapEx",
        "OpEx",
        "IDC",
        "CF",
        "P&L",
        "BS",
        "Dep",
        "DS",
        "Eq",
        "Flags",
        "FID deck outputs",
    }

    missing = required_sheets - worksheets.keys()
    assert not missing, f"{fixture_path.name} missing worksheet mappings: {sorted(missing)}"

    for sheet_name, metadata in worksheets.items():
        assert metadata["rid"].startswith("rId"), sheet_name
        assert metadata["target"].startswith("xl/worksheets/sheet"), sheet_name
        assert metadata["role"], sheet_name


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES)
def test_excel_golden_cells_are_traceable_to_formula_cells(fixture_path: Path) -> None:
    data = json.loads(fixture_path.read_text())

    for metric, cell_info in data["golden_cells"].items():
        assert cell_info["sheet"] in data["worksheets"], metric
        assert cell_info["cell"], metric
        assert isinstance(cell_info["formula"], str) and cell_info["formula"], metric
        assert isinstance(cell_info["value"], (int, float)), metric


@pytest.mark.parametrize("fixture_path", PERIOD_FIXTURE_FILES)
def test_period_fixture_shape_and_core_rows(fixture_path: Path) -> None:
    data = json.loads(fixture_path.read_text())

    assert data["project"] in {"oborovo", "tuho"}
    assert data["source_workbook"].endswith(".xlsm")
    assert "raw xlsm" in data["extraction_note"].lower()
    assert data["period_scope"]
    assert set(data["row_mapping"]) == {"CF", "DS", "P&L", "Eq"}
    assert len(data["periods"]) >= 3

    for period in data["periods"]:
        assert period["period_index"] >= 1
        assert period["excel_column"]
        assert period["period_end_date"]
        assert set(period) >= {"CF", "DS", "P&L", "Eq"}
        assert period["CF"]["operating_revenues_keur"] > 0
        assert period["CF"]["senior_debt_service_keur"] < 0
        assert period["DS"]["senior_principal_keur"] > 0
        assert period["DS"]["senior_net_interest_keur"] > 0
        assert period["P&L"]["total_revenues_keur"] == period["CF"]["operating_revenues_keur"]


def test_oborovo_first_pass_anchors_match_known_excel_values() -> None:
    data = json.loads((FIXTURE_DIR / "excel_golden_oborovo.json").read_text())
    cells = data["golden_cells"]

    assert abs(cells["total_capex_keur"]["value"] - 57973.052657378626) < 1e-9
    assert abs(cells["senior_debt_keur"]["value"] - 42852.26672602787) < 1e-9
    assert abs(cells["unlevered_project_irr"]["value"] - 0.08280167281627655) < 1e-12


def test_tuho_first_pass_anchors_match_known_excel_values() -> None:
    data = json.loads((FIXTURE_DIR / "excel_golden_tuho.json").read_text())
    cells = data["golden_cells"]

    assert abs(cells["total_capex_inputs_keur"]["value"] - 72993.70678606197) < 1e-9
    assert abs(cells["senior_debt_outputs_keur"]["value"] - 43359.2737822209) < 1e-9
    assert abs(cells["project_irr"]["value"] - 0.09304675757884978) < 1e-12
    assert abs(cells["equity_irr"]["value"] - 0.11609525084495542) < 1e-12
    assert abs(cells["average_dscr_ppa"]["value"] - 1.2) < 1e-12
    assert abs(cells["average_dscr_market"]["value"] - 1.4) < 1e-12
