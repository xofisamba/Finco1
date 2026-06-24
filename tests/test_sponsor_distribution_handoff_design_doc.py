"""Tests for Phase 9 sponsor distribution handoff design document."""
import pytest
from pathlib import Path
import csv


def test_design_doc_exists():
    assert Path("docs/phase9_sponsor_distribution_handoff_design.md").exists()


def test_contract_csv_exists():
    assert Path("reports/phase9_sponsor_distribution_handoff_contract.csv").exists()


def test_contract_has_required_columns():
    with open("reports/phase9_sponsor_distribution_handoff_contract.csv") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    required = {"field_name", "producing_module", "consuming_module", "unit", "default_value", "blocked_behavior", "runtime_behavior"}
    assert required.issubset(cols), f"Missing columns: {required - set(cols)}"


def test_primary_distribution_field_present():
    rows = list(csv.DictReader(open("reports/phase9_sponsor_distribution_handoff_contract.csv")))
    field_names = {r["field_name"] for r in rows}
    assert "equity_distribution_paid_keur" in field_names, \
        "equity_distribution_paid_keur not in contract"


def test_distribution_account_produces_primary_field():
    rows = {r["field_name"]: r for r in csv.DictReader(open("reports/phase9_sponsor_distribution_handoff_contract.csv"))}
    da_field = rows.get("equity_distribution_paid_keur")
    assert da_field is not None, "equity_distribution_paid_keur not in contract"
    assert da_field["producing_module"] == "DistributionAccountEngine"
    assert da_field["consuming_module"] == "SponsorCashflowRunner"


def test_sponsor_receives_zero_when_blocked():
    rows = {r["field_name"]: r for r in csv.DictReader(open("reports/phase9_sponsor_distribution_handoff_contract.csv"))}
    dist = rows.get("distribution_received_keur")
    assert dist is not None
    assert "0.0" in dist["default_value"] or "0" in dist["default_value"]
    assert "0.0" in dist["blocked_behavior"]


def test_wht_field_owned_by_sponsor():
    rows = {r["field_name"]: r for r in csv.DictReader(open("reports/phase9_sponsor_distribution_handoff_contract.csv"))}
    wht = rows.get("wht_on_distribution_keur")
    assert wht is not None, "wht_on_distribution_keur not in contract"
    assert "SponsorCashflowRunner" in wht["producing_module"] or "SponsorCashflowRunner" in wht.get("notes", "")


def test_oborovo_guard_documented():
    rows = {r["field_name"]: r for r in csv.DictReader(open("reports/phase9_sponsor_distribution_handoff_contract.csv"))}
    oborovo = rows.get("is_oborovo")
    assert oborovo is not None, "is_oborovo not in contract"


def test_runtime_flag_documented():
    rows = {r["field_name"]: r for r in csv.DictReader(open("reports/phase9_sponsor_distribution_handoff_contract.csv"))}
    flag = rows.get("enable_distribution_account_runtime")
    assert flag is not None, "enable_distribution_account_runtime not in contract"
    assert "False" in flag["default_value"] or "false" in flag["default_value"].lower()


def test_design_doc_has_required_sections():
    doc = Path("docs/phase9_sponsor_distribution_handoff_design.md").read_text()
    required = [
        "Executive Summary",
        "DistributionAccount Ownership",
        "SponsorEngine Ownership",
        "Proposed Sponsor Distribution Input Contract",
        "Timing and Sign Convention",
        "Blocked/Default-Off Behavior",
        "Future Runtime Behavior",
        "Oborovo Guard",
        "Gate Matrix Update",
        "Recommended Next Branch",
    ]
    for section in required:
        assert section in doc, f"Missing section: {section}"


def test_design_doc_keeps_r99_r102_blocked():
    doc = Path("docs/phase9_sponsor_distribution_handoff_design.md").read_text()
    assert "BLOCKED" in doc
    assert "G20" in doc


def test_design_doc_defines_field_pair():
    doc = Path("docs/phase9_sponsor_distribution_handoff_design.md").read_text()
    assert "equity_distribution_paid_keur" in doc
    assert "distribution_received_keur" in doc


def test_design_doc_mentions_no_runtime_changes():
    doc = Path("docs/phase9_sponsor_distribution_handoff_design.md").read_text()
    assert any(phrase in doc.lower() for phrase in [
        "no runtime code",
        "docs/design only",
        "design only",
        "no implementation changes"
    ])


def test_design_doc_recommends_closeout():
    doc = Path("docs/phase9_sponsor_distribution_handoff_design.md").read_text()
    assert "phase9-closeout" in doc.lower() or "closeout" in doc.lower()


def test_no_runtime_files_changed():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--stat", "origin/main...HEAD"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True, text=True,
    )
    output = result.stdout.strip()
    if not output:
        return
    for line in output.split("\n"):
        if (
            not line.strip()
            or line.strip().startswith("??")
            or line.strip().startswith("...")  # UX-2C-1 cross-arc: skip git --stat path truncation
            or "files changed" in line
        ):
            continue
        allowed = [
            "docs/", "reports/", "tests/",
            "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
            "app/ui/dashboard.py",  # UX-2C-1 cross-arc
        ]
        assert any(line.strip().startswith(p) for p in allowed), \
            f"Unexpected non-doc/report/test change: {line}"