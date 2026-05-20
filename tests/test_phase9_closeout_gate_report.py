"""Tests for Phase 9 closeout gate report."""
import pytest
from pathlib import Path
import csv


def test_closeout_doc_exists():
    assert Path("docs/phase9_closeout_gate_report.md").exists()


def test_gate_matrix_exists():
    assert Path("reports/phase9_closeout_gate_matrix.csv").exists()


def test_module_status_exists():
    assert Path("reports/phase9_closeout_module_status.csv").exists()


def test_next_steps_exists():
    assert Path("reports/phase9_closeout_next_steps.csv").exists()


def test_gate_matrix_has_required_columns():
    with open("reports/phase9_closeout_gate_matrix.csv") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    required = {"gate_id", "gate_name", "category", "status", "evidence", "blocker", "required_next_action"}
    assert required.issubset(cols), f"Missing: {required - set(cols)}"


def test_module_status_has_required_columns():
    with open("reports/phase9_closeout_module_status.csv") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    required = {"module", "current_status", "runtime_role", "audit_role", "next_action"}
    assert required.issubset(cols), f"Missing: {required - set(cols)}"


def test_next_steps_has_required_columns():
    with open("reports/phase9_closeout_next_steps.csv") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    required = {"sequence", "branch", "type", "purpose", "prerequisite", "risk_level"}
    assert required.issubset(cols), f"Missing: {required - set(cols)}"


def test_pr_inventory_present():
    doc = Path("docs/phase9_closeout_gate_report.md").read_text()
    required_prs = ["#122", "#123", "#124", "#125", "#126", "#127", "#128", "#129", "#130", "#131", "#132", "#133"]
    for pr in required_prs:
        assert pr in doc, f"PR {pr} not found in closeout doc"


def test_g20_r99_r102_blocked():
    rows = list(csv.DictReader(open("reports/phase9_closeout_gate_matrix.csv")))
    g20 = next((r for r in rows if r.get("gate_id", "").strip() == "G20"), None)
    assert g20 is not None, "G20 not found in gate matrix"
    assert g20["status"].strip().upper() == "BLOCKED", f"G20 status is {g20['status']}, expected BLOCKED"


def test_shl_r102_implementation_pending():
    rows = list(csv.DictReader(open("reports/phase9_closeout_gate_matrix.csv")))
    g07 = next((r for r in rows if r.get("gate_id", "").strip() == "G07"), None)
    assert g07 is not None, "G07 not found in gate matrix"
    assert g07["status"].strip().upper() == "PENDING", f"G07 status is {g07['status']}, expected PENDING"


def test_sponsor_handoff_implementation_pending():
    rows = list(csv.DictReader(open("reports/phase9_closeout_gate_matrix.csv")))
    g16 = next((r for r in rows if r.get("gate_id", "").strip() == "G16"), None)
    assert g16 is not None, "G16 not found in gate matrix"
    assert g16["status"].strip().upper() == "PENDING", f"G16 status is {g16['status']}, expected PENDING"


def test_canonical_depreciation_pending_or_blocked():
    rows = list(csv.DictReader(open("reports/phase9_closeout_gate_matrix.csv")))
    canonical = [r for r in rows if "canonical" in r.get("gate_name", "").lower() or "depreciation" in r.get("gate_name", "").lower()]
    assert len(canonical) > 0, "No canonical depreciation gates found"
    for g in canonical:
        assert g["status"].strip().upper() in ("PENDING", "BLOCKED"), \
            f"Gate {g['gate_id']} status is {g['status']}, expected PENDING or BLOCKED"


def test_no_report_claims_r99_r102_approved():
    doc = Path("docs/phase9_closeout_gate_report.md").read_text()
    lines = doc.lower().split("\n")
    for line in lines:
        if "approved" in line and "r99" in line or "r99" in line and "promotion" in line and "approved" in line:
            assert "not approved" in line or "remains blocked" in line or "not" in line, \
                f"Suspicious line: {line}"


def test_next_sequence_shl_before_r99():
    rows = list(csv.DictReader(open("reports/phase9_closeout_next_steps.csv")))
    rows_sorted = sorted(rows, key=lambda r: int(r.get("sequence", "0") or "0"))
    shl_seq = next((int(r["sequence"]) for r in rows_sorted if "shl" in r.get("branch", "").lower()), None)
    r99_seq = next((int(r["sequence"]) for r in rows_sorted if "r99" in r.get("branch", "").lower() and "design" not in r.get("branch", "").lower()), None)
    if shl_seq is not None and r99_seq is not None:
        assert shl_seq < r99_seq, f"SHL ({shl_seq}) should come before R99 ({r99_seq})"


def test_phase9_audit_block_complete():
    doc = Path("docs/phase9_closeout_gate_report.md").read_text()
    assert "phase 9 audit" in doc.lower() or "phase 9" in doc.lower()
    assert any(phrase in doc.lower() for phrase in [
        "phase 9 audit/design/validation/calibration block is complete",
        "phase 9 audit block is complete",
        "phase 9 is complete"
    ]), "Closeout should state Phase 9 is complete"


def test_doc_states_r99_not_approved():
    doc = Path("docs/phase9_closeout_gate_report.md").read_text()
    assert "not approved" in doc.lower() or "remains blocked" in doc.lower()


def test_closeout_doc_has_required_sections():
    doc = Path("docs/phase9_closeout_gate_report.md").read_text()
    required = [
        "Executive Summary",
        "Completed PR Inventory",
        "SeniorDebtSizing Policy Status",
        "DistributionAccount Status",
        "R99/R102 Status",
        "SHL R102 Handoff Status",
        "Sponsor Distribution Handoff Status",
        "Cross-Module Validation Summary",
        "TUHO Calibration Summary",
        "Oborovo Calibration",
        "TaxBridge",
        "Source-of-Truth Map",
        "Gate Matrix Summary",
        "What Is READY",
        "What Is PENDING",
        "What Is BLOCKED",
        "Runtime Promotion Decision",
        "Recommended Next Branch",
        "Non-Goals",
    ]
    for section in required:
        assert section in doc, f"Missing section: {section}"


def test_no_runtime_files_changed():
    import subprocess
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "diff", "--stat", "origin/main...HEAD"],
        cwd=str(repo_root),
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