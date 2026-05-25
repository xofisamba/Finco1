from __future__ import annotations

import csv
import os
from io import StringIO


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_phase16_feedback_capture_docs_and_reports_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in (
        ("docs", "phase16_pilot_feedback_capture.md"),
        ("reports", "phase16_pilot_feedback_capture_status.csv"),
        ("reports", "phase16_pilot_feedback_issue_log.csv"),
        ("reports", "phase16_pilot_session_evidence_updates.csv"),
        ("reports", "phase16_pilot_feedback_remaining_gaps.csv"),
    ):
        assert os.path.exists(os.path.join(base, *rel))


def test_phase16_feedback_capture_honestly_declares_pending_real_execution():
    docs = _read("docs", "phase16_pilot_feedback_capture.md")

    assert "outcome **B: feedback capture pending**" in docs
    assert "PENDING_REAL_PILOT_EXECUTION" in docs
    assert "TUHO remains `NOT_EXECUTED_IN_THIS_ENVIRONMENT`" in docs
    assert "Oborovo remains `NOT_EXECUTED_IN_THIS_ENVIRONMENT`" in docs
    assert "Pilot feedback records remain non-authoritative." in docs
    assert "Pilot feedback records are not governance approvals." in docs
    assert "Pilot feedback does not alter runtime authority." in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs
    lowered = docs.lower()
    assert "lender-ready" in lowered
    assert "audit-certified" in lowered
    assert "saas" in lowered
    assert "multi-user" in lowered


def test_phase16_feedback_capture_status_issue_log_and_updates_are_explicit():
    status_rows = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_feedback_capture_status.csv"))))
    issue_rows = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_feedback_issue_log.csv"))))
    update_rows = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_session_evidence_updates.csv"))))
    gap_rows = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_feedback_remaining_gaps.csv"))))

    assert len(status_rows) == 2
    for row in status_rows:
        assert row["capture_status"] == "PENDING_REAL_PILOT_EXECUTION"
        assert row["session_status"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT"
        assert row["real_evidence_available_yes_no"] == "no"
        assert row["issue_count"] == "unavailable"
        assert row["blocker_found_yes_no"] == "unavailable"

    assert len(issue_rows) == 1
    assert issue_rows[0]["issue_id"] == "TEMPLATE_EXAMPLE_ONLY"
    assert "Do not treat this row as a real finding" in issue_rows[0]["notes"]
    assert issue_rows[0]["artifact_reference"] == "reports/phase15_pilot_feedback_issue_template.csv"

    for row in update_rows:
        assert row["previous_status"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT"
        assert row["updated_status"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT"
        assert row["real_evidence_available_yes_no"] == "no"

    gap_map = {row["gap_id"]: row for row in gap_rows}
    assert gap_map["PH16-FEEDBACK-GAP-001"]["pilot_blocker_yes_no"] == "no"
    assert gap_map["PH16-FEEDBACK-GAP-003"]["recommended_follow_up"] == "Execute TUHO guided pilot and record real evidence"
    assert gap_map["PH16-FEEDBACK-GAP-004"]["recommended_follow_up"] == "Execute Oborovo guided pilot and record real evidence"
