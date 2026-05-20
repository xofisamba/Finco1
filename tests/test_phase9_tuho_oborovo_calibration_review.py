"""Phase 9 TUHO + Oborovo calibration review tests."""
import pytest
from pathlib import Path
import csv


def test_calibration_review_doc_exists():
    assert Path("docs/phase9_tuho_oborovo_calibration_review.md").exists()


def test_calibration_comparison_csv_exists():
    assert Path("reports/phase9_tuho_oborovo_calibration_comparison.csv").exists()


def _rows_by_project_metric():
    rows = {}
    for r in csv.DictReader(open("reports/phase9_tuho_oborovo_calibration_comparison.csv")):
        key = (r["project"], r["metric"])
        rows[key] = r
    return rows


def test_tuho_debt_ok():
    rows = _rows_by_project_metric()
    assert rows[("TUHO", "Debt (kEUR)")]["status"] == "OK"


def test_tuho_equity_irr_within_tolerance():
    rows = _rows_by_project_metric()
    assert rows[("TUHO", "Equity IRR")]["status"] == "OK"


def test_tuho_co2_calibrated():
    rows = _rows_by_project_metric()
    assert rows[("TUHO", "CO2 Y1 (kEUR)")]["status"] == "OK"


def test_tuho_project_irr_ok():
    rows = _rows_by_project_metric()
    assert rows[("TUHO", "Project IRR")]["status"] == "OK"


def test_tuho_avg_dscr_warn_noted():
    rows = _rows_by_project_metric()
    assert rows[("TUHO", "Avg DSCR")]["status"] == "WARN"


def test_tuho_lp_distributions_ok():
    rows = _rows_by_project_metric()
    assert rows[("TUHO", "Full-horizon LP distributions (kEUR)")]["status"] == "OK"


def test_oborovo_debt_ok():
    rows = _rows_by_project_metric()
    assert rows[("OBOROVO", "Debt (kEUR)")]["status"] == "OK"


def test_oborovo_opex_ok_documented():
    rows = _rows_by_project_metric()
    assert rows[("OBOROVO", "OpEx Y1 (kEUR)")]["status"] == "OK"


def test_oborovo_total_distributions_ok_documented():
    rows = _rows_by_project_metric()
    assert rows[("OBOROVO", "Total Distributions (kEUR)")]["status"] == "OK"


def test_oborovo_avg_dscr_warn_documented():
    rows = _rows_by_project_metric()
    assert rows[("OBOROVO", "Avg DSCR")]["status"] == "WARN"


def test_oborovo_equity_irr_warn_documented():
    rows = _rows_by_project_metric()
    assert rows[("OBOROVO", "Equity IRR")]["status"] == "WARN"


def test_calibration_review_has_required_sections():
    doc = Path("docs/phase9_tuho_oborovo_calibration_review.md").read_text()
    required = [
        "Executive Summary",
        "TUHO Calibration Status",
        "Oborovo Calibration Status",
        "Phase 9 Safety Invariants",
        "What Remains Before R99/R102 Promotion",
        "Known Gaps",
        "Recommended Next Actions",
        "Summary",
    ]
    for section in required:
        assert section in doc, f"Missing section: {section}"


def test_calibration_review_documents_distribution_account_blocked():
    doc = Path("docs/phase9_tuho_oborovo_calibration_review.md").read_text()
    assert "R99/R102 BLOCKED" in doc
    assert "equity_distribution_paid_keur = 0" in doc


def test_calibration_review_documents_oborovo_guard():
    doc = Path("docs/phase9_tuho_oborovo_calibration_review.md").read_text()
    assert "OBOROVO_NOT_SUPPORTED" in doc or "Oborovo guard" in doc


def test_calibration_review_documents_oborovo_opex_gap():
    doc = Path("docs/phase9_tuho_oborovo_calibration_review.md").read_text()
    assert "B.01" in doc and "B.02" in doc
    assert "OpEx" in doc


def test_csv_has_both_projects():
    rows = list(csv.DictReader(open("reports/phase9_tuho_oborovo_calibration_comparison.csv")))
    projects = {r["project"] for r in rows}
    assert "TUHO" in projects
    assert "OBOROVO" in projects


def test_no_runtime_files_changed():
    """Verify only doc/report/test files are changed."""
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--stat", "origin/main...HEAD"],
        cwd="/root/.openclaw/workspace/finco1",
        capture_output=True, text=True,
    )
    output = result.stdout.strip()
    if not output:
        return
    for line in output.split("\n"):
        if not line.strip():
            continue
        allowed_prefixes = ["docs/", "reports/", "tests/", "  "]
        if any(line.strip().startswith(p) for p in allowed_prefixes):
            continue
        if "files changed" in line or "insertion" in line or "deletion" in line:
            continue
        if line.strip().startswith("??") and any(
            line.strip().endswith(ext) for ext in [".md", ".csv", ".py"]
        ):
            continue
        assert False, f"Unexpected non-doc/report/test change: {line}"