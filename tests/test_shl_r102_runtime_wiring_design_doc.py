"""Tests for Phase 9 SHL R102 runtime wiring design document."""
import pytest
from pathlib import Path
import csv


def test_design_doc_exists():
    assert Path("docs/phase9_shl_r102_runtime_wiring_design.md").exists()


def test_input_contract_csv_exists():
    assert Path("reports/phase9_shl_r102_input_contract.csv").exists()


def test_input_contract_has_required_columns():
    with open("reports/phase9_shl_r102_input_contract.csv") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    required = {"field_name", "producing_module", "consuming_module", "unit", "timing", "default_value", "blocked_behavior", "runtime_behavior"}
    assert required.issubset(cols), f"Missing columns: {required - set(cols)}"


def test_primary_r102_field_present():
    rows = list(csv.DictReader(open("reports/phase9_shl_r102_input_contract.csv")))
    field_names = {r["field_name"] for r in rows}
    assert any("r102" in f.lower() or "sweep" in f.lower() for f in field_names), \
        "No R102 sweep field found in contract"


def test_distribution_account_produces_field():
    rows = {r["field_name"]: r for r in csv.DictReader(open("reports/phase9_shl_r102_input_contract.csv"))}
    r102 = next((r for n, r in rows.items() if "r102" in n.lower()), None)
    assert r102 is not None, "R102 field not found"
    assert r102["producing_module"] == "DistributionAccountEngine", \
        f"R102 field should be produced by DistributionAccountEngine, got {r102['producing_module']}"
    assert r102["consuming_module"] == "ShlEngine", \
        f"R102 field should be consumed by ShlEngine, got {r102['consuming_module']}"


def test_shl_owns_interest_fields():
    rows = {r["field_name"]: r for r in csv.DictReader(open("reports/phase9_shl_r102_input_contract.csv"))}
    interest_fields = [n for n in rows if "interest" in n.lower() or "pik" in n.lower()]
    for f in interest_fields:
        assert rows[f]["producing_module"] == "ShlEngine", \
            f"Interest field {f} should be produced by ShlEngine"


def test_blocked_behavior_documented():
    rows = list(csv.DictReader(open("reports/phase9_shl_r102_input_contract.csv")))
    r102 = next((r for r in rows if "r102" in r.get("field_name", "").lower()), None)
    assert r102 is not None, "R102 field not found"
    assert r102["blocked_behavior"] != "", "blocked_behavior should be documented"
    assert "internal" in r102["blocked_behavior"].lower(), "blocked_behavior should mention internal computation"


def test_runtime_behavior_documented():
    rows = list(csv.DictReader(open("reports/phase9_shl_r102_input_contract.csv")))
    r102 = next((r for r in rows if "r102" in r.get("field_name", "").lower()), None)
    assert r102 is not None, "R102 field not found"
    assert r102["runtime_behavior"] != "", "runtime_behavior should be documented"


def test_oborovo_guard_documented():
    rows = {r["field_name"]: r for r in csv.DictReader(open("reports/phase9_shl_r102_input_contract.csv"))}
    oborovo = rows.get("is_oborovo")
    assert oborovo is not None, "is_oborovo field not in contract"
    assert "ShlEngine" in oborovo["consuming_module"]


def test_design_doc_has_required_sections():
    doc = Path("docs/phase9_shl_r102_runtime_wiring_design.md").read_text()
    required = [
        "Executive Summary",
        "DistributionAccount Ownership",
        "ShlEngine Ownership",
        "Proposed R102 Input Contract",
        "Cash Routing Order",
        "Blocked/Default-Off Behavior",
        "Future Runtime Behavior",
        "Oborovo Guard",
        "Gate Matrix Update",
        "Recommended Next Branch",
    ]
    for section in required:
        assert section in doc, f"Missing section: {section}"


def test_design_doc_keeps_r99_r102_blocked():
    doc = Path("docs/phase9_shl_r102_runtime_wiring_design.md").read_text()
    assert "BLOCKED" in doc
    assert "G20" in doc


def test_design_doc_defines_field_name():
    doc = Path("docs/phase9_shl_r102_runtime_wiring_design.md").read_text()
    assert "distribution_account_r102_sweep_candidate_keur" in doc


def test_design_doc_mentions_no_runtime_changes():
    doc = Path("docs/phase9_shl_r102_runtime_wiring_design.md").read_text()
    assert any(phrase in doc.lower() for phrase in [
        "no runtime code",
        "docs/design only",
        "design only",
        "no implementation changes"
    ])


def test_design_doc_recommends_next_branch():
    doc = Path("docs/phase9_shl_r102_runtime_wiring_design.md").read_text()
    assert "phase9-sponsor" in doc.lower()


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