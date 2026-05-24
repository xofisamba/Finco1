from __future__ import annotations

import csv
import os
from io import StringIO


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_closeout_doc_exists_and_confirms_guided_internal_pilot_posture():
    docs = _read("docs", "phase15_closeout_review.md")

    assert "Guided internal pilot readiness: READY" in docs
    assert "No production application code changed in this closeout branch." in docs
    assert "No runtime/model formulas changed." in docs
    assert "No workbook calculations changed." in docs
    assert "No export calculation logic changed." in docs
    assert "No persistence behavior changed." in docs
    assert "No governance behavior changed." in docs
    assert "No replay engine behavior was added." in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs
    assert "Workbook/export remains descriptive and reviewer-facing." in docs
    assert "Scenario compare remains descriptive only." in docs
    assert "real pilot evidence is still needed beyond template/example rows" in docs.lower()


def test_closeout_reports_exist_and_capture_phase15_inventory_and_no_claims():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for report_name in (
        "phase15_closeout_change_inventory.csv",
        "phase15_pilot_readiness_scorecard.csv",
        "phase15_remaining_limitations_no_claims.csv",
        "phase15_claude_review_question_pack.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))

    inventory = list(csv.DictReader(StringIO(_read("reports", "phase15_closeout_change_inventory.csv"))))
    scorecard = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_readiness_scorecard.csv"))))
    limitations = list(csv.DictReader(StringIO(_read("reports", "phase15_remaining_limitations_no_claims.csv"))))
    claude_pack = list(csv.DictReader(StringIO(_read("reports", "phase15_claude_review_question_pack.csv"))))

    branch_names = {row["phase15_branch"] for row in inventory}
    assert {
        "phase15-e2e-integration-suite",
        "phase15-browser-workflow-verification",
        "phase15-deployment-runbook",
        "phase15-numeric-workbook-validation",
        "phase15-reviewer-handoff-pack",
        "phase15-pilot-feedback-instrumentation",
        "phase15-test-marker-upgrade",
        "phase15-pilot-issue-cleanup",
    } <= branch_names
    assert all(row["production_code_changed"] == "no" for row in inventory)

    score_map = {row["dimension"]: row for row in scorecard}
    assert score_map["guided_internal_pilot_workflow"]["score_1_to_10"] == "9"
    assert score_map["runtime_authority_discipline"]["score_1_to_10"] == "9"
    assert score_map["external_pilot_readiness"]["score_1_to_10"] == "6"
    assert score_map["lender_audit_readiness"]["score_1_to_10"] == "2"
    assert score_map["multi_user_saas_readiness"]["score_1_to_10"] == "2"

    limitation_rows = {row["limitation_or_no_claim"]: row for row in limitations}
    assert "not_lender_ready" in limitation_rows
    assert "not_audit_certified" in limitation_rows
    assert "not_saas_multi_tenant_ready" in limitation_rows
    assert "no_r99_r102_promotion" in limitation_rows
    assert "no_g20_approval" in limitation_rows
    assert "real_pilot_evidence_needed_beyond_template_rows" in limitation_rows

    questions = {row["review_question"] for row in claude_pack}
    assert "Did Phase 15 preserve runtime authority?" in questions
    assert "Did Phase 15 accidentally introduce any production behavior changes?" in questions
    assert "Is reviewer handoff adequate for use without chat history?" in questions
    assert "Was the no-defect cleanup conclusion justified by the available evidence?" in questions
    assert "Is the product ready for actual guided internal pilot use?" in questions


def test_closeout_pack_preserves_no_claims_and_non_authoritative_feedback_language():
    docs = _read("docs", "phase15_closeout_review.md").lower()

    assert "not lender-ready" in docs
    assert "not audit-certified" in docs
    assert "not saas or multi-tenant ready" in docs
    assert "feedback instrumentation" in docs
    assert "feedback records must not become runtime authority or governance approval" in docs
    assert "scenario compare remains descriptive only" in docs
    assert "export provenance and export lineage remain descriptive only" in docs
