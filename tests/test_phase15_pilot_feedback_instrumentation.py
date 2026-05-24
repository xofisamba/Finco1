from __future__ import annotations

import csv
import os
from io import StringIO


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_feedback_guide_exists_and_stays_non_authoritative():
    docs = _read("docs", "phase15_pilot_feedback_instrumentation.md")

    assert "single-user guided internal pilot" in docs
    assert "does **not** introduce or claim" in docs
    assert "lender-ready operating status" in docs
    assert "audit-certified operating status" in docs
    assert "SaaS or customer-support readiness" in docs
    assert "Feedback records are non-authoritative." in docs
    assert "Feedback records are not governance approvals." in docs
    assert "Feedback records do not alter runtime authority." in docs
    assert "feedback does **not** trigger automatic model changes" in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs


def test_feedback_guide_contains_categories_and_severity_semantics():
    docs = _read("docs", "phase15_pilot_feedback_instrumentation.md")

    for category in (
        "`runtime_trust`",
        "`export_readability`",
        "`workbook_numeric`",
        "`scenario_compare`",
        "`dirty_state_or_stale_runtime`",
        "`governance_label_confusion`",
        "`reviewer_handoff_gap`",
        "`deployment_or_environment`",
        "`browser_or_htmx`",
        "`performance`",
        "`UX_only`",
        "`documentation_only`",
    ):
        assert category in docs

    assert "`LOW`" in docs
    assert "`MEDIUM`" in docs
    assert "`HIGH`" in docs
    assert "`BLOCKER`" in docs
    assert "feedback severity is **not** governance approval" in docs
    assert "feedback blocker is **not** the same as `G20` or `R99/R102` governance state" in docs
    assert "Do **not** record unnecessary personal data." in docs


def test_feedback_templates_and_triage_reports_exist_with_required_fields():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for report_name in (
        "phase15_pilot_feedback_issue_template.csv",
        "phase15_pilot_session_log_template.csv",
        "phase15_pilot_feedback_category_matrix.csv",
        "phase15_pilot_feedback_triage_workflow.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))

    issue_template = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_feedback_issue_template.csv"))))
    session_log = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_session_log_template.csv"))))
    categories = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_feedback_category_matrix.csv"))))
    triage = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_feedback_triage_workflow.csv"))))

    issue_headers = set(issue_template[0].keys())
    assert issue_headers == {
        "issue_id",
        "date_reported",
        "reporter_role",
        "project",
        "scenario_name",
        "scenario_id",
        "runtime_snapshot_id",
        "export_filename",
        "workflow_step",
        "category",
        "severity",
        "blocker_yes_no",
        "expected_behavior",
        "actual_behavior",
        "governance_label_involved",
        "screenshot_or_artifact_reference",
        "reproducible_yes_no",
        "suggested_follow_up",
        "triage_status",
        "owner",
        "resolution_notes",
    }
    assert set(session_log[0].keys()) == {
        "session_id",
        "date",
        "operator",
        "reviewer_role",
        "project_used",
        "scenarios_touched",
        "exports_created",
        "compares_run",
        "smoke_test_passed",
        "issues_logged",
        "backup_completed",
        "notes",
    }

    category_names = {row["category"] for row in categories}
    assert {
        "runtime_trust",
        "export_readability",
        "workbook_numeric",
        "scenario_compare",
        "governance_label_confusion",
        "documentation_only",
    } <= category_names

    triage_steps = {row["triage_step"]: row for row in triage}
    assert "severity is not governance approval" in triage_steps["classify_category_and_severity"]["guardrail"]
    assert "feedback does not approve G20 or promote R99/R102" in triage_steps["preserve_governance_blockers"]["guardrail"]
    assert "feedback records remain non-authoritative" in triage_steps["collect_after_session"]["guardrail"]
