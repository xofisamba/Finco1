from __future__ import annotations

import os


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

    checklist = _read("reports", "phase15_reviewer_workflow_checklist.csv")
    statuses = _read("reports", "phase15_governance_status_interpretation.csv")
    issue_template = _read("reports", "phase15_reviewer_issue_template.csv")
    no_claims = _read("reports", "phase15_reviewer_handoff_no_claims.csv")

    assert "select_project" in checklist
    assert "observe_dirty_state" in checklist
    assert "export_workbook" in checklist
    assert "compare_scenarios" in checklist
    assert "backup_after_session" in checklist

    assert "BLOCKED," in statuses
    assert "NOT APPROVED," in statuses
    assert "ACCEPTED_CONVENTION," in statuses
    assert "SOURCE_NOT_AVAILABLE," in statuses
    assert "MISSING_EVIDENCE," in statuses
    assert "G20 remains BLOCKED" in statuses
    assert "R99/R102 remain NOT APPROVED" in statuses

    assert "project,yes" in issue_template
    assert "scenario,yes" in issue_template
    assert "expected_behavior,yes" in issue_template
    assert "actual_behavior,yes" in issue_template
    assert "blocker_yes_no,yes" in issue_template
    assert "impact_area,yes" in issue_template

    assert "single-user guided internal pilot only" in no_claims
    assert "No lender-ready claim is made." in no_claims
    assert "No audit-certified claim is made." in no_claims
    assert "Workbook/export remains descriptive only." in no_claims
    assert "Scenario compare remains descriptive only." in no_claims
    assert "G20 remains BLOCKED and R99/R102 remain NOT APPROVED." in no_claims
    assert "SOURCE_NOT_AVAILABLE, unavailable, and not_applicable are not zero." in no_claims
