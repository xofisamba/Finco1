"""Tests for the Phase 10 calibration reconciliation pack."""

from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path

import openpyxl

from app.export.calibration_reconciliation import write_calibration_reconciliation_pack


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

WORKBOOK = REPORTS / "phase10_calibration_reconciliation_pack.xlsx"
GAP_REGISTER = REPORTS / "phase10_calibration_gap_register.csv"
SOURCE_INVENTORY = REPORTS / "phase10_calibration_source_inventory.csv"
SUMMARY = REPORTS / "phase10_calibration_reconciliation_summary.csv"
DOC = DOCS / "phase10_calibration_gap_reconciliation_pack.md"


def _generate_if_missing() -> None:
    if all(path.exists() for path in (WORKBOOK, GAP_REGISTER, SOURCE_INVENTORY, SUMMARY)):
        return
    write_calibration_reconciliation_pack()


def _sheet_text(workbook, sheet_name: str) -> str:
    ws = workbook[sheet_name]
    values = []
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                values.append(str(cell.value))
    return " ".join(values)


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_workbook_generates():
    write_calibration_reconciliation_pack()
    assert WORKBOOK.exists()


def test_required_sheets_exist():
    _generate_if_missing()
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    expected = [
        "Executive Summary",
        "Governance",
        "Runtime Summary",
        "Revenue Reconciliation",
        "OPEX Reconciliation",
        "Senior Debt Reconciliation",
        "SHL Reconciliation",
        "Tax R35-R67-R69",
        "CFADS Waterfall",
        "Distributions Sponsor",
        "Returns Reconciliation",
        "Gap Register",
        "Source Inventory",
        "Accepted Conventions",
        "Reviewer Notes",
    ]
    assert wb.sheetnames == expected


def test_horizontal_periods_exist():
    _generate_if_missing()
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    ws = wb["Revenue Reconciliation"]
    headers = [ws.cell(row=1, column=col).value for col in range(1, ws.max_column + 1)]
    assert "P1" in headers
    assert "P61" in headers


def test_classification_and_root_cause_columns_exist():
    _generate_if_missing()
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    ws = wb["Revenue Reconciliation"]
    headers = [ws.cell(row=1, column=col).value for col in range(1, ws.max_column + 1)]
    assert "Classification" in headers
    assert "Root Cause" in headers


def test_non_pass_rows_contain_explanations():
    _generate_if_missing()
    rows = _csv_rows(SUMMARY)
    non_pass = [row for row in rows if row["classification"] != "PASS"]
    assert non_pass
    for row in non_pass:
        assert row["root_cause"], row
        assert row["recommended_action"], row


def test_source_inventory_exists_and_has_required_columns():
    _generate_if_missing()
    rows = _csv_rows(SOURCE_INVENTORY)
    assert rows
    required = {
        "metric",
        "source_file",
        "period_level_available",
        "total_available",
        "evidence_side",
        "confidence_level",
        "usable_for_reconciliation",
        "notes",
    }
    assert required.issubset(rows[0].keys())


def test_governance_sheet_contains_gate_status():
    _generate_if_missing()
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    text = _sheet_text(wb, "Governance")
    assert "G20 status BLOCKED" in text
    assert "R99/R102 status NOT APPROVED" in text


def test_runtime_vs_preview_labels_exist():
    _generate_if_missing()
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    text = _sheet_text(wb, "Runtime Summary") + " " + _sheet_text(wb, "Governance")
    assert "Runtime / Preview" in text
    assert "review" in text.lower() or "runtime" in text.lower()


def test_missing_evidence_rows_are_not_zero_filled():
    _generate_if_missing()
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    ws = wb["Revenue Reconciliation"]
    target_row = None
    for row in range(1, ws.max_row + 1):
        label = ws.cell(row=row, column=1).value
        if label == "CO2 Revenue - Excel":
            target_row = row
            break
    assert target_row is not None
    first_period_value = ws.cell(row=target_row, column=3).value
    assert isinstance(first_period_value, str)
    assert first_period_value.startswith("MISSING_EVIDENCE")


def test_doc_states_governance_limits():
    content = DOC.read_text(encoding="utf-8")
    assert "G20 remains `BLOCKED`" in content
    assert "R99/R102 remain `NOT APPROVED`" in content
    assert "no runtime formula changes" in content


def test_no_runtime_model_formula_files_changed():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    forbidden_prefixes = (
        "domain/waterfall",
        "domain/shl",
        "domain/tax",
        "app/waterfall",
        "app/ui_runner.py",
        "app/project_factories.py",
    )
    offenders = [path for path in changed if path.replace("\\", "/").startswith(forbidden_prefixes)]
    assert not offenders, offenders
