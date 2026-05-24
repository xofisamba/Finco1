from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def _csv_rows(*parts: str) -> list[dict[str, str]]:
    with ROOT.joinpath(*parts).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_upgrade_pack_docs_and_reports_exist():
    assert (ROOT / "docs" / "phase15_test_marker_upgrade.md").exists()
    assert (ROOT / "reports" / "phase15_test_marker_upgrade_inventory.csv").exists()
    assert (ROOT / "reports" / "phase15_test_behavioral_upgrade_matrix.csv").exists()
    assert (ROOT / "reports" / "phase15_test_marker_remaining_gaps.csv").exists()

    doc = _read("docs", "phase15_test_marker_upgrade.md")
    assert "No authority-boundary tests were weakened." in doc
    assert "Runtime remains backend-authoritative." in doc
    assert "Workbook/export remains descriptive only." in doc
    assert "Scenario compare remains descriptive only." in doc
    assert "`G20` remains `BLOCKED`." in doc
    assert "`R99/R102` remain `NOT APPROVED`." in doc


def test_report_csvs_capture_upgrade_inventory_and_remaining_marker_gaps():
    inventory = _csv_rows("reports", "phase15_test_marker_upgrade_inventory.csv")
    matrix = _csv_rows("reports", "phase15_test_behavioral_upgrade_matrix.csv")
    gaps = _csv_rows("reports", "phase15_test_marker_remaining_gaps.csv")

    assert any(row["test_file"] == "tests/test_phase14_export_lineage_ui.py" and row["status"] == "upgraded" for row in inventory)
    assert any(row["test_file"] == "tests/test_phase14_scenario_compare_honesty.py" and row["status"] == "upgraded" for row in inventory)
    assert any(row["test_file"] == "tests/test_phase15_browser_workflow_verification.py" and row["status"] == "upgraded" for row in inventory)
    assert any("rendered compare rows" in row["stronger_check_added"] for row in matrix)
    assert any("dirty and clean workspaces produce different lineage action notes" in row["stronger_check_added"] for row in matrix)
    assert any(row["test_area"] == "phase15_browser_workflow_verification" for row in gaps)
