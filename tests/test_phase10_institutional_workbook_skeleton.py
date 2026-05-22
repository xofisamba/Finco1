from __future__ import annotations

import csv
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from app.export.institutional_workbook import (
    INSTITUTIONAL_SHEET_DEFINITIONS,
    export_institutional_workbook_skeleton,
)
from app.export.registry import default_export_registry


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "phase10_institutional_workbook_skeleton.md"
SHEET_MAP = ROOT / "reports" / "phase10_workbook_sheet_map.csv"
REGISTRY_REPORT = ROOT / "reports" / "phase10_export_registry.csv"


def _open_workbook(project: str):
    return load_workbook(BytesIO(export_institutional_workbook_skeleton(project)), data_only=True)


def _sheet_column_values(sheet, column: int) -> list[object]:
    return [sheet.cell(row=row, column=column).value for row in range(1, sheet.max_row + 1)]


def test_workbook_skeleton_generates_with_required_sheet_names():
    workbook = _open_workbook("tuho")
    assert workbook.sheetnames == [
        definition.sheet_name for definition in INSTITUTIONAL_SHEET_DEFINITIONS
    ]


def test_governance_and_runtime_summary_sheets_exist_with_metadata():
    workbook = _open_workbook("tuho")
    governance = workbook["Governance"]
    runtime = workbook["Runtime Summary"]

    assert governance["A1"].value == "Project"
    assert governance["A6"].value == "Governance Field"
    assert runtime["A1"].value == "Project"
    assert runtime["A6"].value == "Metric"

    governance_values = set(_sheet_column_values(governance, 2))
    assert "BLOCKED" in governance_values
    assert "NOT APPROVED" in governance_values


def test_runtime_summary_values_are_exported_and_projects_differ():
    tuho = _open_workbook("tuho")["Runtime Summary"]
    oborovo = _open_workbook("oborovo")["Runtime Summary"]

    tuho_project = tuho["B7"].value
    oborovo_project = oborovo["B7"].value
    assert tuho_project
    assert oborovo_project
    assert tuho_project != oborovo_project

    metric_names = set(_sheet_column_values(tuho, 1))
    assert "Project IRR" in metric_names
    assert "Equity IRR" in metric_names
    assert "Total revenue" in metric_names
    assert "Total SHL service" in metric_names


def test_placeholder_sheets_are_clearly_labeled():
    workbook = _open_workbook("tuho")
    for sheet_name in [
        "Inputs",
        "Construction",
        "OPEX",
        "CAPEX",
        "Revenue",
        "Senior Debt",
        "SHL",
        "Tax",
        "P&L",
        "Cash Flow",
        "Balance Sheet",
        "Audit",
        "Gap Register",
    ]:
        sheet = workbook[sheet_name]
        assert sheet["A8"].value == "Phase 10 placeholder - runtime binding pending"


def test_export_registry_and_sheet_map_include_workbook_artifact():
    registry = default_export_registry()
    names = {artifact.artifact_name for artifact in registry.artifacts}
    assert "Phase 10 institutional workbook skeleton" in names

    report_rows = list(csv.DictReader(REGISTRY_REPORT.open(newline="", encoding="utf-8")))
    assert any(
        row["artifact_name"] == "Phase 10 institutional workbook skeleton"
        and row["category"] == "workbook"
        for row in report_rows
    )

    sheet_rows = list(csv.DictReader(SHEET_MAP.open(newline="", encoding="utf-8")))
    assert len(sheet_rows) == 16
    assert sheet_rows[0]["sheet_name"] == "Cover"
    assert sheet_rows[2]["sheet_name"] == "Runtime Summary"


def test_docs_and_route_keep_governance_and_runtime_scope():
    text = DOC.read_text(encoding="utf-8")
    assert "No runtime formulas" in text
    assert "G20 remains `BLOCKED`" in text
    assert "R99/R102 remains `NOT APPROVED`" in text

    main_web = (ROOT / "main_web.py").read_text(encoding="utf-8")
    assert '@app.get("/exports/institutional-workbook.xlsx")' in main_web
    assert "export_institutional_workbook_skeleton(project)" in main_web
