from __future__ import annotations

import csv
import os
from io import StringIO


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_phase16_execution_docs_and_reports_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in (
        ("docs", "phase16_pilot_session_execution.md"),
        ("reports", "phase16_pilot_session_execution_matrix.csv"),
        ("reports", "phase16_pilot_session_log_tuho.csv"),
        ("reports", "phase16_pilot_session_log_oborovo.csv"),
        ("reports", "phase16_pilot_execution_evidence_register.csv"),
        ("reports", "phase16_pilot_execution_remaining_gaps.csv"),
    ):
        assert os.path.exists(os.path.join(base, *rel))


def test_phase16_pack_honestly_declares_not_executed_environment_path():
    docs = _read("docs", "phase16_pilot_session_execution.md")

    assert "outcome **B: execution-ready pack created but not executed in this environment**" in docs
    assert "NOT_EXECUTED_IN_THIS_ENVIRONMENT" in docs
    assert "No fake `PASS` status was recorded." in docs
    assert "pilot evidence records remain non-authoritative" in docs.lower()
    assert "pilot evidence records are not governance approvals" in docs.lower()
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT_APPROVED`." not in docs  # exact typo should not appear
    assert "`R99/R102` remain `NOT APPROVED`." in docs
    lowered = docs.lower()
    assert "lender-ready" in lowered
    assert "audit-certified" in lowered
    assert "saas" in lowered
    assert "multi-user" in lowered


def test_phase16_logs_matrix_and_evidence_use_explicit_non_execution_markers():
    matrix = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_session_execution_matrix.csv"))))
    tuho = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_session_log_tuho.csv"))))
    oborovo = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_session_log_oborovo.csv"))))
    evidence = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_execution_evidence_register.csv"))))
    gaps = list(csv.DictReader(StringIO(_read("reports", "phase16_pilot_execution_remaining_gaps.csv"))))

    workflow_steps = [row["workflow_step"] for row in matrix]
    assert workflow_steps == [
        "health_check",
        "login",
        "project_select",
        "scenario_load_or_create",
        "supported_assumption_edit",
        "dirty_badge_observed",
        "unsaved_banner_observed",
        "dirty_runtime_block",
        "save_scenario",
        "save_does_not_autorun",
        "run_model",
        "runtime_summary_observed",
        "workbook_export",
        "workbook_readable",
        "export_lineage_observed",
        "scenario_compare",
        "compare_descriptive_only",
        "governance_labels_checked",
        "backup_or_not_applicable",
        "feedback_logged",
    ]
    assert all(row["tuho_status"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT" for row in matrix)
    assert all(row["oborovo_status"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT" for row in matrix)
    assert all(row["evidence_recorded"] == "no" for row in matrix)

    assert tuho[0]["status"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT"
    assert tuho[0]["result"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT"
    assert oborovo[0]["status"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT"
    assert oborovo[0]["result"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT"
    assert tuho[0]["issues_logged_count"] == "unavailable"
    assert oborovo[0]["issues_logged_count"] == "unavailable"
    assert tuho[0]["blocker_found_yes_no"] == "unavailable"
    assert oborovo[0]["blocker_found_yes_no"] == "unavailable"

    assert all(row["status"] == "NOT_EXECUTED_IN_THIS_ENVIRONMENT" for row in evidence)
    assert any(row["artifact_reference"] == "not_applicable" for row in evidence)
    assert any(row["recorded_at"] == "unavailable" for row in evidence)

    gap_map = {row["gap_id"]: row for row in gaps}
    assert gap_map["PH16-GAP-001"]["pilot_blocker_yes_no"] == "no"
    assert gap_map["PH16-GAP-005"]["recommended_follow_up"] == "Populate issue and session artifacts during actual pilot execution"
