from __future__ import annotations

import csv
import os
from io import StringIO


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_reviewer_handoff_doc_exists_and_stays_in_guided_internal_pilot_scope():
    docs = _read("docs", "phase15_reviewer_handoff_pack.md")

    assert "single-user guided internal pilot" in docs
    assert "does **not** introduce or claim" in docs
    assert "lender-ready status" in docs
    assert "audit-certified status" in docs
    assert "SaaS or multi-tenant readiness" in docs
    assert "Runtime remains backend-owned" in docs
    assert "Workbook/export remains descriptive and reviewer-facing." in docs
    assert "Scenario compare remains descriptive only." in docs
    assert "Save does not run the model." in docs
    assert "Compare does not auto-save or auto-run." in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs


def test_reviewer_handoff_doc_contains_governance_and_no_claims_guidance():
    docs = _read("docs", "phase15_reviewer_handoff_pack.md")

    assert "`ACCEPTED_CONVENTION` is explanatory, not approval." in docs
    assert "`SOURCE_NOT_AVAILABLE`, `unavailable`, and `not_applicable` must not be read as zero." in docs
    assert "legacy-frozen historical labels must be interpreted using current documentation" in docs
    assert "Why is workbook/export descriptive instead of authoritative?" in docs
    assert "Why does save not run the model?" in docs
    assert "Why does compare not include unsaved drafts?" in docs
    assert "Why is this not lender-ready or audit-certified?" in docs
    assert "What should I do if export provenance is unavailable?" in docs
    assert "What should I do if runtime appears stale?" in docs


def test_reviewer_handoff_reports_and_issue_template_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for report_name in (
        "phase15_reviewer_workflow_checklist.csv",
        "phase15_governance_status_interpretation.csv",
        "phase15_reviewer_issue_template.csv",
        "phase15_reviewer_handoff_no_claims.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))

    checklist = list(csv.DictReader(StringIO(_read("reports", "phase15_reviewer_workflow_checklist.csv"))))
    statuses = list(csv.DictReader(StringIO(_read("reports", "phase15_governance_status_interpretation.csv"))))
    issue_template = list(csv.DictReader(StringIO(_read("reports", "phase15_reviewer_issue_template.csv"))))
    no_claims = list(csv.DictReader(StringIO(_read("reports", "phase15_reviewer_handoff_no_claims.csv"))))

    assert [row["step_id"] for row in checklist[:5]] == [
        "select_project",
        "load_or_create_scenario",
        "edit_assumption",
        "observe_dirty_state",
        "save_scenario",
    ]
    assert any(row["step_id"] == "compare_scenarios" for row in checklist)
    assert any(row["step_id"] == "backup_after_session" for row in checklist)

    status_labels = {row["status_label"] for row in statuses}
    assert {"BLOCKED", "NOT APPROVED", "ACCEPTED_CONVENTION", "SOURCE_NOT_AVAILABLE", "MISSING_EVIDENCE"} <= status_labels
    blocked_row = next(row for row in statuses if row["status_label"] == "BLOCKED")
    assert blocked_row["current_phase15_posture"] == "G20 remains BLOCKED"
    not_approved_row = next(row for row in statuses if row["status_label"] == "NOT APPROVED")
    assert not_approved_row["current_phase15_posture"] == "R99/R102 remain NOT APPROVED"

    issue_fields = {row["field_name"]: row for row in issue_template}
    assert issue_fields["project"]["required"] == "yes"
    assert issue_fields["scenario"]["required"] == "yes"
    assert issue_fields["expected_behavior"]["required"] == "yes"
    assert issue_fields["actual_behavior"]["required"] == "yes"
    assert issue_fields["blocker_yes_no"]["required"] == "yes"
    assert issue_fields["impact_area"]["required"] == "yes"

    no_claim_areas = {row["claim_area"]: row for row in no_claims}
    assert no_claim_areas["pilot_scope"]["current_statement"] == "single-user guided internal pilot only"
    assert no_claim_areas["lender_ready"]["current_statement"] == "No lender-ready claim is made."
    assert no_claim_areas["audit_certified"]["current_statement"] == "No audit-certified claim is made."
    assert no_claim_areas["workbook_authority"]["current_statement"] == "Workbook/export remains descriptive only."
    assert no_claim_areas["scenario_compare_authority"]["current_statement"] == "Scenario compare remains descriptive only."
    assert no_claim_areas["governance_blockers"]["current_statement"] == "G20 remains BLOCKED and R99/R102 remain NOT APPROVED."
    assert no_claim_areas["availability_markers"]["current_statement"] == "SOURCE_NOT_AVAILABLE, unavailable, and not_applicable are not zero."
