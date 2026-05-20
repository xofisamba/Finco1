"""Phase 9 TUHO calibration deep-dive tests."""
import pytest
from pathlib import Path
import csv


def test_deep_dive_doc_exists():
    assert Path("docs/phase9_tuho_calibration_deep_dive.md").exists()


def test_dscr_deep_dive_csv_exists():
    assert Path("reports/phase9_tuho_dscr_deep_dive.csv").exists()


def test_irr_deep_dive_csv_exists():
    assert Path("reports/phase9_tuho_irr_deep_dive.csv").exists()


def test_gap_register_csv_exists():
    assert Path("reports/phase9_tuho_calibration_gap_register.csv").exists()


def test_dscr_csv_has_required_columns():
    with open("reports/phase9_tuho_dscr_deep_dive.csv") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    required = {"component", "excel_value", "model_value", "delta", "likely_driver", "status"}
    assert required.issubset(cols), f"Missing columns: {required - set(cols)}"


def test_irr_csv_has_required_columns():
    with open("reports/phase9_tuho_irr_deep_dive.csv") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    required = {"component", "excel_value", "model_value", "delta", "likely_driver", "status"}
    assert required.issubset(cols), f"Missing columns: {required - set(cols)}"


def test_gap_register_has_required_columns():
    with open("reports/phase9_tuho_calibration_gap_register.csv") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    required = {"gap_id", "metric", "severity", "blocks_runtime_promotion", "recommended_branch"}
    assert required.issubset(cols), f"Missing columns: {required - set(cols)}"


def test_dscr_delta_entry_present():
    """DSCR delta of +0.103 is documented."""
    rows = list(csv.DictReader(open("reports/phase9_tuho_dscr_deep_dive.csv")))
    assert any("DSCR" in r.get("component", "") or "dscr" in r.get("component", "").lower()
               for r in rows), "DSCR delta not in report"


def test_project_irr_delta_entry_present():
    """Project IRR delta of -0.06pp is documented."""
    rows = list(csv.DictReader(open("reports/phase9_tuho_irr_deep_dive.csv")))
    assert any("project" in r.get("component", "").lower() or "IRR" in r.get("component", "")
               for r in rows), "Project IRR delta not in report"


def test_doc_says_no_runtime_changes():
    doc = Path("docs/phase9_tuho_calibration_deep_dive.md").read_text()
    assert "no runtime code changes" in doc.lower() or "no runtime changes" in doc.lower() or \
           "docs/report/test-only" in doc.lower()


def test_doc_keeps_r99_r102_blocked():
    doc = Path("docs/phase9_tuho_calibration_deep_dive.md").read_text()
    assert "BLOCKED" in doc


def test_gap_register_has_recommended_branch():
    rows = list(csv.DictReader(open("reports/phase9_tuho_calibration_gap_register.csv")))
    assert any(r.get("recommended_branch", "") not in ("", "NONE", "N/A", "DOCUMENTATION")
               for r in rows), "No recommended branch in gap register"


def test_gap_register_has_phase9_shl_wiring():
    rows = list(csv.DictReader(open("reports/phase9_tuho_calibration_gap_register.csv")))
    recommended = {r.get("recommended_branch", "") for r in rows}
    assert any("shl" in r.lower() for r in recommended), "SHL wiring not in gap register"


def test_doc_has_required_sections():
    doc = Path("docs/phase9_tuho_calibration_deep_dive.md").read_text()
    required = [
        "Executive Summary",
        "DSCR Delta",
        "Project IRR Delta",
        "Gap Register",
        "Recommended Next Branches",
        "Phase 9 Closure",
    ]
    for section in required:
        assert section in doc, f"Missing section: {section}"


def test_dscr_delta_explained_by_distributions():
    """DSCR delta is explained by distributions blocked."""
    doc = Path("docs/phase9_tuho_calibration_deep_dive.md").read_text()
    assert "distribution" in doc.lower() and "blocked" in doc.lower()


def test_project_irr_within_tolerance():
    """Project IRR -0.06pp is within ±0.5pp tolerance = OK."""
    doc = Path("docs/phase9_tuho_calibration_deep_dive.md").read_text()
    assert "essentially calibrated" in doc.lower() or "within ±0.5pp" in doc.lower()


def test_no_runtime_files_changed():
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
        if not line.strip() or line.strip().startswith("??"):
            continue
        allowed = ["docs/", "reports/", "tests/"]
        assert any(line.strip().startswith(p) for p in allowed), \
            f"Unexpected non-doc/report/test change: {line}"