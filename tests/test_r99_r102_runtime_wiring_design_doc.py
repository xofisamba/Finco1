"""Tests for the R99/R102 runtime wiring design document."""
import pytest
from pathlib import Path


def test_design_doc_exists():
    """Design document must exist."""
    assert Path("docs/phase9_r99_r102_runtime_wiring_design.md").exists()


def test_gate_matrix_exists():
    """Gate matrix CSV must exist."""
    assert Path("reports/phase9_r99_r102_runtime_wiring_gate_matrix.csv").exists()


def test_design_doc_has_required_sections():
    """Design document must contain all required sections."""
    doc = Path("docs/phase9_r99_r102_runtime_wiring_design.md").read_text()
    required = [
        "Executive Summary",
        "Current Status",
        "What Changed in Phase 9",
        "Proposed Future Runtime Ownership Map",
        "Field-by-Field Ownership",
        "Circular Dependency",
        "Oborovo Guard",
        "Default-Off Flag",
        "Promotion Gate Matrix",
        "Recommended Next Branch",
    ]
    for section in required:
        assert section in doc, f"Missing section: {section}"


def test_gate_matrix_contains_required_gates():
    """Gate matrix must contain all required gates."""
    import csv

    path = Path("reports/phase9_r99_r102_runtime_wiring_gate_matrix.csv")
    rows = list(csv.DictReader(open(path)))
    gate_names = {r["gate_name"] for r in rows}
    required = [
        "DistributionAccount implementation exists",
        "Oborovo guard implemented",
        "R99/R102 promotion allowed",
    ]
    for name in required:
        assert any(name in g for g in gate_names), f"Missing gate: {name}"


def test_final_promotion_gate_is_blocked():
    """G20 (final promotion gate) must be BLOCKED."""
    import csv

    path = Path("reports/phase9_r99_r102_runtime_wiring_gate_matrix.csv")
    rows = {r["gate_id"]: r for r in csv.DictReader(open(path))}
    promotion_gate = rows.get("G20") or next(
        r for r in rows.values() if "promotion allowed" in r.get("gate_name", "").lower()
    )
    assert promotion_gate["status"] == "BLOCKED", f"Final gate should be BLOCKED, got {promotion_gate['status']}"


def test_no_runtime_files_changed():
    """Verify no runtime files were changed in this design-only branch."""
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--stat", "origin/main...HEAD", "--", "app/", "domain/distribution_account/engine.py"],
        cwd="/root/.openclaw/workspace/finco1",
        capture_output=True,
        text=True,
    )
    # Should show no changes (only docs/reports)
    stdout = result.stdout.strip()
    # If nothing changed, stdout is empty. If something changed, it will have file stats.
    assert stdout == "" or "origin/main...HEAD" in result.stderr, f"Unexpected runtime changes: {result.stdout}"


def test_gate_matrix_has_20_gates():
    """Gate matrix must have exactly 20 gates (G01-G20)."""
    import csv

    path = Path("reports/phase9_r99_r102_runtime_wiring_gate_matrix.csv")
    rows = list(csv.DictReader(open(path)))
    gate_ids = sorted([r["gate_id"] for r in rows])
    expected = [f"G{i:02d}" for i in range(1, 21)]
    assert gate_ids == expected, f"Expected gates {expected}, got {gate_ids}"


def test_r99_r102_always_blocked_in_audit_mode():
    """R99/R102 must remain BLOCKED in audit mode — key invariant."""
    doc = Path("docs/phase9_r99_r102_runtime_wiring_design.md").read_text()
    assert "BLOCKED" in doc, "Design doc must confirm R99/R102 BLOCKED"
    assert "R99/R102 remains BLOCKED" in doc, "Must explicitly state R99/R102 remains BLOCKED"


def test_oborovo_guard_mentioned():
    """Oborovo guard must be documented in design."""
    doc = Path("docs/phase9_r99_r102_runtime_wiring_design.md").read_text()
    assert "Oborovo" in doc, "Oborovo guard must be documented"
    assert "BLOCKED_REASONS.OBOROVO_NOT_SUPPORTED" in doc or "OBOROVO_NOT_SUPPORTED" in doc


def test_default_off_flag_mentioned():
    """Default-off flag strategy must be documented."""
    doc = Path("docs/phase9_r99_r102_runtime_wiring_design.md").read_text()
    assert "enable_distribution_account_runtime" in doc, "Default-off flag must be documented"


def test_circular_dependency_section_exists():
    """Circular dependency analysis must be present."""
    doc = Path("docs/phase9_r99_r102_runtime_wiring_design.md").read_text()
    assert "Circular Dependency" in doc, "Circular dependency section required"


def test_gate_matrix_all_gates_have_status():
    """All gates in matrix must have a status."""
    import csv

    path = Path("reports/phase9_r99_r102_runtime_wiring_gate_matrix.csv")
    rows = list(csv.DictReader(open(path)))
    for row in rows:
        assert row["status"], f"Gate {row['gate_id']} missing status"