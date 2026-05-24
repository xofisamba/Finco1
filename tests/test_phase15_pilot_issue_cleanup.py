from __future__ import annotations

import csv
import os
from io import StringIO


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_cleanup_doc_confirms_no_defect_path_and_guardrails():
    docs = _read("docs", "phase15_pilot_issue_cleanup.md")

    assert "no-defect path" in docs
    assert "no verified blocking pilot issues requiring app changes" in docs.lower()
    assert "Template example row only" in docs
    assert "no production application changes were made" in docs.lower()
    assert "Runtime remains backend-owned" in docs
    assert "Workbook/export remains descriptive and reviewer-facing." in docs
    assert "Scenario compare remains descriptive only." in docs
    assert "Feedback records remain non-authoritative." in docs
    assert "Feedback records are not governance approvals." in docs
    assert "No replay engine behavior was added." in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs


def test_cleanup_reports_exist_and_capture_template_vs_verified_distinction():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for report_name in (
        "phase15_pilot_issue_cleanup_inventory.csv",
        "phase15_pilot_issue_cleanup_actions.csv",
        "phase15_pilot_issue_cleanup_remaining_risks.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))

    inventory = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_issue_cleanup_inventory.csv"))))
    actions = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_issue_cleanup_actions.csv"))))
    risks = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_issue_cleanup_remaining_risks.csv"))))

    inventory_map = {row["issue_or_source"]: row for row in inventory}
    assert inventory_map["PILOT-001"]["verified_pilot_finding"] == "no"
    assert "Template example row only" in inventory_map["PILOT-001"]["notes"]
    assert inventory_map["SESSION-001"]["verified_pilot_finding"] == "no"
    assert inventory_map["phase15_browser_workflow_remaining_gaps.csv"]["verified_pilot_finding"] == "known_existing_gap"
    assert inventory_map["phase15_numeric_workbook_gap_register.csv"]["verified_pilot_finding"] == "known_existing_gap"

    assert any("No app or doc wording change because the row is a template example" in row["action_taken"] for row in actions)
    assert any("No product change; gaps remain visible for Phase 15 closeout" in row["action_taken"] for row in actions)

    risk_map = {row["risk_or_gap"]: row for row in risks}
    assert risk_map["template_rows_not_real_findings"]["pilot_blocker"] == "no"
    assert risk_map["live_browser_automation_gap"]["pilot_blocker"] == "no"
    assert risk_map["workbook_wide_numeric_audit_gap"]["pilot_blocker"] == "no"


def test_cleanup_pack_preserves_authority_boundaries_and_no_claims():
    docs = _read("docs", "phase15_pilot_issue_cleanup.md").lower()

    assert "lender-ready" in docs
    assert "audit certification" in docs
    assert "multi-user governance" in docs
    assert "no verified pilot issues were recorded" not in docs  # exact stronger claim avoided
    assert "no verified pilot issues were found" in docs
