"""Phase 9 cross-module validation pack tests."""
import pytest
from pathlib import Path
import csv

def test_validation_pack_doc_exists():
    assert Path("docs/phase9_cross_module_validation_pack.md").exists()

def test_validation_matrix_exists():
    assert Path("reports/phase9_cross_module_validation_matrix.csv").exists()

def test_validation_results_exists():
    assert Path("reports/phase9_cross_module_validation_results.csv").exists()

def test_validation_matrix_has_required_cases():
    rows = list(csv.DictReader(open("reports/phase9_cross_module_validation_matrix.csv")))
    assert len(rows) >= 7, f"Expected 7+ cases, got {len(rows)}"
    case_ids = {r["case_id"] for r in rows}
    assert "A" in case_ids and "E" in case_ids

def test_all_cases_r99_r102_blocked():
    rows = list(csv.DictReader(open("reports/phase9_cross_module_validation_matrix.csv")))
    for r in rows:
        assert "BLOCKED" in r["expected_status"] or "pass" in r["expected_status"].lower(), \
            f"Case {r['case_id']} has unexpected status: {r['expected_status']}"

def test_all_results_pass():
    rows = list(csv.DictReader(open("reports/phase9_cross_module_validation_results.csv")))
    for r in rows:
        assert r["status"] == "PASS", f"Case {r['case_id']} failed: {r['notes']}"

def test_no_hidden_coupling_detected():
    rows = list(csv.DictReader(open("reports/phase9_cross_module_validation_results.csv")))
    for r in rows:
        assert r["hidden_coupling_detected"] == "False", \
            f"Hidden coupling detected in case {r['case_id']}: {r['notes']}"

def test_oborovo_guard_cases_have_active_status():
    rows = list(csv.DictReader(open("reports/phase9_cross_module_validation_results.csv")))
    oborovo = [r for r in rows if "Oborovo" in r["project"]]
    assert len(oborovo) >= 2, "Need at least 2 Oborovo test cases"
    for r in oborovo:
        assert r["oborovo_guard_status"] == "ACTIVE", \
            f"Oborovo case {r['case_id']} guard not active: {r['oborovo_guard_status']}"

def test_equity_distribution_paid_keur_is_zero():
    rows = list(csv.DictReader(open("reports/phase9_cross_module_validation_results.csv")))
    for r in rows:
        assert float(r["baseline_drift_distribution_keur"]) == 0.0, \
            f"Case {r['case_id']} has non-zero distribution drift: {r['baseline_drift_distribution_keur']}"

def test_r99_status_blocked_in_all():
    rows = list(csv.DictReader(open("reports/phase9_cross_module_validation_results.csv")))
    for r in rows:
        assert r["r99_status"] == "BLOCKED", f"Case {r['case_id']} r99 not BLOCKED: {r['r99_status']}"

def test_r102_status_blocked_in_all():
    rows = list(csv.DictReader(open("reports/phase9_cross_module_validation_results.csv")))
    for r in rows:
        assert r["r102_status"] == "BLOCKED", f"Case {r['case_id']} r102 not BLOCKED: {r['r102_status']}"

def test_validation_pack_has_required_sections():
    doc = Path("docs/phase9_cross_module_validation_pack.md").read_text()
    required = [
        "Executive Summary",
        "Scope and Non-Goals",
        "Hidden Coupling Analysis",
        "Oborovo Guard",
        "R99/R102 BLOCKED",
        "Results Summary",
        "Recommended Next Branch",
    ]
    for section in required:
        assert section in doc, f"Missing section: {section}"

def test_no_runtime_files_changed():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--stat", "origin/main...HEAD"],
        cwd="/root/.openclaw/workspace/finco1",
        capture_output=True, text=True,
    )
    for line in result.stdout.strip().split("\n"):
        if line and "origin/main...HEAD" not in line and line.strip():
            assert any(line.startswith(p) for p in ["docs/", "reports/", "tests/", "  "]), \
                f"Unexpected non-doc/report/test change: {line}"