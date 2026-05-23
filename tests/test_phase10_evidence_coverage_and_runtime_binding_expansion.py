"""Tests for Phase 10 evidence coverage and runtime binding expansion."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import openpyxl

from app.export.calibration_reconciliation import write_calibration_reconciliation_pack


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

WORKBOOK = REPORTS / "phase10_calibration_reconciliation_pack.xlsx"
INVENTORY = REPORTS / "phase10_runtime_binding_inventory.csv"
COVERAGE = REPORTS / "phase10_evidence_coverage_summary.csv"
RUNTIME_GAPS = REPORTS / "phase10_runtime_binding_gap_register.csv"
DOC = DOCS / "phase10_evidence_coverage_and_runtime_binding_expansion.md"


def _generate() -> None:
    write_calibration_reconciliation_pack()


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sheet_text(workbook, sheet_name: str) -> str:
    ws = workbook[sheet_name]
    values: list[str] = []
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                values.append(str(cell.value))
    return " ".join(values)


def test_runtime_binding_reports_exist():
    _generate()
    assert INVENTORY.exists()
    assert COVERAGE.exists()
    assert RUNTIME_GAPS.exists()


def test_runtime_binding_inventory_has_required_columns():
    _generate()
    rows = _csv_rows(INVENTORY)
    assert rows
    required = {
        "section",
        "metric",
        "runtime_source",
        "workbook_target_sheet",
        "currently_bound",
        "currently_missing",
        "reason_if_missing",
        "confidence_level",
        "classification",
        "notes",
    }
    assert required.issubset(rows[0].keys())


def test_evidence_coverage_summary_has_metrics():
    _generate()
    rows = _csv_rows(COVERAGE)
    metrics = {row["metric"] for row in rows}
    assert "runtime_coverage_pct" in metrics
    assert "evidence_coverage_pct" in metrics
    assert "unresolved_gap_count" in metrics
    assert "governance_blocker_count" in metrics
    assert "accepted_convention_count" in metrics


def test_runtime_available_fields_are_bound_or_explained():
    _generate()
    rows = _csv_rows(INVENTORY)
    offenders = [
        row for row in rows
        if row["currently_bound"] == "no" and not row["reason_if_missing"].strip()
    ]
    assert not offenders, offenders


def test_runtime_binding_gap_register_rows_are_explained():
    _generate()
    rows = _csv_rows(RUNTIME_GAPS)
    assert rows
    for row in rows:
        assert row["why_unresolved"].strip(), row
        assert row["recommended_action"].strip(), row
        assert row["expected_roadmap_phase"].strip(), row


def test_shl_tax_cfads_and_distributions_have_runtime_bound_rows():
    _generate()
    rows = _csv_rows(INVENTORY)
    by_metric = {(row["section"], row["metric"]): row for row in rows}
    assert by_metric[("SHL", "Cash Interest Paid")]["currently_bound"] == "yes"
    assert by_metric[("SHL", "PIK Capitalized")]["currently_bound"] == "yes"
    assert by_metric[("SHL", "Total SHL Service")]["currently_bound"] == "yes"
    assert by_metric[("Tax", "Tax Depreciation")]["currently_bound"] == "yes"
    assert by_metric[("Tax", "CIT Accrual")]["currently_bound"] == "yes"
    assert by_metric[("CFADS", "CFADS / R69")]["currently_bound"] == "yes"
    assert by_metric[("Distributions", "DA-Wired / Pre-G20 Staging")]["currently_bound"] == "yes"


def test_workbook_dashboard_and_reconciliation_show_coverage_metrics():
    _generate()
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    dashboard = _sheet_text(wb, "Executive Dashboard")
    assert "Runtime coverage summary" in dashboard
    assert "Evidence coverage summary" in dashboard
    assert "Runtime completeness estimate" in dashboard
    assert "Evidence completeness estimate" in dashboard
    assert "Unresolved material delta summary" in dashboard

    shl_text = _sheet_text(wb, "SHL Reconciliation")
    tax_text = _sheet_text(wb, "Tax R35-R67-R69")
    cfads_text = _sheet_text(wb, "CFADS Waterfall")
    assert "Cash Interest Paid - Model" in shl_text
    assert "PIK Capitalized - Model" in shl_text
    assert "Total SHL Service - Model" in shl_text
    assert "CIT Accrual - Model" in tax_text
    assert "Cash Tax Current Period - Model" in tax_text
    assert "CFADS / R69 - Model" in cfads_text


def test_doc_and_governance_labels_remain_intact():
    content = DOC.read_text(encoding="utf-8")
    assert "runtime binding expansion strategy" in content.lower()
    assert "evidence coverage methodology" in content.lower()
    assert "no runtime formula changes" in content.lower()
    assert "G20 remains `BLOCKED`" in content
    assert "R99/R102 remain `NOT APPROVED`" in content


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
