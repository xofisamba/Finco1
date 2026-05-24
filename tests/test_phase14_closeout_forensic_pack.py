from __future__ import annotations

import os


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_closeout_doc_contains_phase14_guardrail_statements():
    doc = _read("docs", "phase14_closeout_forensic_pack.md")

    assert "No production application behavior changes are introduced by this branch." in doc
    assert "No runtime/model formulas changed." in doc
    assert "No workbook calculations changed." in doc
    assert "No export calculation logic changed." in doc
    assert "No persistence behavior changed." in doc
    assert "No governance behavior changed." in doc
    assert "No new editable surfaces were added." in doc
    assert "No JavaScript financial calculations were added." in doc
    assert "No replay engine behavior was added." in doc
    assert "`audit_economic_mode` remains audit/reconciliation-only." in doc
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in doc
    assert "`G20` remains `BLOCKED`." in doc
    assert "`R99/R102` remain `NOT APPROVED`." in doc
    assert "runtime remains backend-authoritative" in doc.lower()
    assert "workbook/export remains descriptive" in doc.lower()
    assert "scenario compare remains descriptive only" in doc.lower()
    assert "provenance and export lineage remain descriptive only" in doc.lower()


def test_closeout_reports_exist_and_capture_phase14_inventory():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_names = (
        "phase14_closeout_change_inventory.csv",
        "phase14_closeout_authority_boundary_matrix.csv",
        "phase14_closeout_pilot_readiness_delta.csv",
        "phase14_claude_review_question_pack.csv",
    )
    for report_name in report_names:
        assert os.path.exists(os.path.join(base, "reports", report_name))

    inventory = _read("reports", "phase14_closeout_change_inventory.csv")
    boundaries = _read("reports", "phase14_closeout_authority_boundary_matrix.csv")
    pilot_delta = _read("reports", "phase14_closeout_pilot_readiness_delta.csv")
    claude_pack = _read("reports", "phase14_claude_review_question_pack.csv")

    assert "phase14a-reviewer-productivity-polish" in inventory
    assert "phase14b-publish-package-workflow-cleanup" in inventory
    assert "phase14c-pilot-readiness-snapshot" in inventory
    assert "phase14-provenance-export-coverage" in inventory
    assert "phase14-reviewer-cover-notes" in inventory
    assert "phase14-export-lineage-ui" in inventory
    assert "phase14-scenario-compare-honesty" in inventory

    assert "runtime_backend_authority,intact" in boundaries
    assert "workbook_export_descriptive_only,intact" in boundaries
    assert "scenario_compare_descriptive_only,intact" in boundaries
    assert "replay_engine_behavior,absent" in boundaries
    assert "g20_blocker,intact" in boundaries
    assert "r99_r102_not_approved,intact" in boundaries

    assert "reviewer_clarity," in pilot_delta
    assert "export_interpretability," in pilot_delta
    assert "publish_workflow_reliability," in pilot_delta
    assert "pilot_safe_no_claims," in pilot_delta
    assert "deployment_and_operations," in pilot_delta

    assert "Did any Phase 14 branch weaken runtime authority?" in claude_pack
    assert "Did workbook/export become calculation authority anywhere?" in claude_pack
    assert "Did provenance or export lineage become replay behavior?" in claude_pack
    assert "Did scenario compare become hidden runtime authority?" in claude_pack
    assert "What are the remaining top 10 risks?" in claude_pack


def test_closeout_pack_stays_docs_reports_tests_only():
    closeout_doc = _read("docs", "phase14_closeout_forensic_pack.md")
    authority_matrix = _read("reports", "phase14_closeout_authority_boundary_matrix.csv")

    assert "This closeout branch is documentation, reports, and tests only." in closeout_doc
    assert "No production application behavior changes are introduced by this branch." in closeout_doc
    assert "clarified but not changed" in authority_matrix
