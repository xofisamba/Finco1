"""Phase 46 — Real-User Session Execution and Feedback Analysis tests.

Verifies:
1. Phase 46 execution/analysis doc exists
2. Real-user session execution checklist exists
3. Feedback analysis template exists
4. Real-user feedback issue log exists
5. Feedback execution matrix exists
6. JSON summary parses and includes real_user_session_status
7. JSON says real_user_session_status = ready_to_execute_not_yet_completed
8. JSON says real_user_feedback_collected = false
9. Docs do not claim a real-user session was completed
10. No fake user feedback in docs
11. Docs state controlled trusted pilot is GO with conditions
12. Docs state paid pilot is NOT READY
13. Docs state enterprise SaaS is NOT READY
14. Docs state Phase 40 reviewer run was internal
15. Docs state Phase 42 first observed run was internal/controlled
16. Docs state generic solar/wind remain excluded and unvalidated
17. Docs include export hygiene and last clean backend run boundary
18. Docs include issue intake and feedback triage workflow
19. Docs explicitly avoid bank/lender/audit/certification/SaaS/enterprise claims
20. Docs state no financial formula/runtime/model changes
21. Docs include G20 BLOCKED and R99/R102 NOT APPROVED
22. Docs state partial_pay_sweep not promoted, flat/min DSCR not promoted
23. No JS financial calculations added
"""
import json
import pytest
from pathlib import Path

BASE_SHA = "3b220b3ba8581b399486604643a2271cca2f3e2e"

EXECUTION_DOC = Path("docs/phase46_real_user_session_execution_feedback_analysis.md")
CHECKLIST = Path("docs/pilot_real_user_session_execution_checklist.md")
ANALYSIS_TEMPLATE = Path("docs/pilot_feedback_analysis_template.md")
ISSUE_LOG = Path("docs/phase46_real_user_feedback_issue_log.md")
EXECUTION_MATRIX = Path("docs/phase46_feedback_execution_matrix.md")
JSON_SUMMARY = Path("reports/phase46_real_user_session_feedback_summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 46 execution/analysis doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase46_execution_analysis_doc_exists():
    assert EXECUTION_DOC.exists(), f"{EXECUTION_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Real-user session execution checklist exists
# ─────────────────────────────────────────────────────────────────────────────
def test_real_user_session_execution_checklist_exists():
    assert CHECKLIST.exists(), f"{CHECKLIST} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Feedback analysis template exists
# ─────────────────────────────────────────────────────────────────────────────
def test_feedback_analysis_template_exists():
    assert ANALYSIS_TEMPLATE.exists(), f"{ANALYSIS_TEMPLATE} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Real-user feedback issue log exists
# ─────────────────────────────────────────────────────────────────────────────
def test_real_user_feedback_issue_log_exists():
    assert ISSUE_LOG.exists(), f"{ISSUE_LOG} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Feedback execution matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_feedback_execution_matrix_exists():
    assert EXECUTION_MATRIX.exists(), f"{EXECUTION_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: JSON summary parses and includes required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses_and_has_required_fields():
    assert JSON_SUMMARY.exists(), f"{JSON_SUMMARY} not found"
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("base_sha") == BASE_SHA, "base_sha must match"
    assert "real_user_session_status" in data, "must contain real_user_session_status"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: JSON says real_user_session_status = ready_to_execute_not_yet_completed
# ─────────────────────────────────────────────────────────────────────────────
def test_session_status_ready_not_completed():
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("real_user_session_status") == "ready_to_execute_not_yet_completed", (
        "real_user_session_status must be ready_to_execute_not_yet_completed"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: JSON says real_user_feedback_collected = false
# ─────────────────────────────────────────────────────────────────────────────
def test_feedback_not_collected():
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("real_user_feedback_collected") is False, (
        "real_user_feedback_collected must be False"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Docs do not claim a real-user session was completed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_claim_session_completed():
    for doc in [EXECUTION_DOC, CHECKLIST, ISSUE_LOG, EXECUTION_MATRIX]:
        text = doc.read_text().lower()
        if "session" in text and "complet" in text:
            # If "session completed" appears, it must be "not yet completed" or similar
            assert "not yet" in text or "pending" in text or "template" in text, (
                f"{doc.name} must not claim a real-user session was completed"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: No fake user feedback in docs
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fake_user_feedback():
    # Issue log must explicitly state no real issues collected
    issue_log_text = ISSUE_LOG.read_text().lower()
    assert "no real-user" in issue_log_text or "no issues collected" in issue_log_text or "not yet collected" in issue_log_text, (
        f"{ISSUE_LOG.name} must explicitly state no real-user issues collected yet"
    )
    # Analysis template must have placeholder language
    analysis_text = ANALYSIS_TEMPLATE.read_text().lower()
    assert "instructions" in analysis_text or "do not fabricate" in analysis_text or "fill in after" in analysis_text, (
        f"{ANALYSIS_TEMPLATE.name} must contain placeholder/instruction language"
    )
    # Checklist must show READY/COMPLETE statuses — not fabricated observations
    checklist_text = CHECKLIST.read_text().lower()
    # Should not have specific fake user behaviors like "user clicked run model"
    assert "user clicked" not in checklist_text, (
        f"{CHECKLIST.name} must not contain fabricated user behaviors"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Docs state controlled trusted pilot is GO with conditions
# ─────────────────────────────────────────────────────────────────────────────
def test_controlled_trusted_pilot_go_with_conditions():
    text = EXECUTION_DOC.read_text().lower()
    assert "go" in text and ("tuho" in text or "oborovo" in text or "frozen" in text), (
        f"{EXECUTION_DOC.name} must state controlled trusted pilot is GO"
    )
    assert "with conditions" in text or "conditions" in text, (
        f"{EXECUTION_DOC.name} must reference conditions"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Docs state paid pilot is NOT READY
# ─────────────────────────────────────────────────────────────────────────────
def test_paid_pilot_not_ready():
    text = EXECUTION_DOC.read_text().lower()
    assert "paid pilot" in text and "not ready" in text, (
        f"{EXECUTION_DOC.name} must state paid pilot is NOT READY"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Docs state enterprise SaaS is NOT READY
# ─────────────────────────────────────────────────────────────────────────────
def test_enterprise_saas_not_ready():
    text = EXECUTION_DOC.read_text().lower()
    assert ("enterprise" in text or "saas" in text) and "not ready" in text, (
        f"{EXECUTION_DOC.name} must state enterprise SaaS is NOT READY"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Docs state Phase 40 reviewer run was internal
# ─────────────────────────────────────────────────────────────────────────────
def test_phase40_internal():
    text = EXECUTION_DOC.read_text().lower()
    assert "phase 40" in text and "internal" in text, (
        f"{EXECUTION_DOC.name} must state Phase 40 reviewer run was internal"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Docs state Phase 42 first observed run was internal/controlled
# ─────────────────────────────────────────────────────────────────────────────
def test_phase42_internal_controlled():
    text = EXECUTION_DOC.read_text().lower()
    assert "phase 42" in text and ("internal" in text or "controlled" in text), (
        f"{EXECUTION_DOC.name} must state Phase 42 first observed run was internal/controlled"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: Docs state generic solar/wind remain excluded and unvalidated
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_excluded_and_unvalidated():
    text = EXECUTION_DOC.read_text().lower()
    assert "generic solar" in text and "unvalidated" in text, (
        f"{EXECUTION_DOC.name} must state generic solar is unvalidated"
    )
    assert "generic wind" in text and "unvalidated" in text, (
        f"{EXECUTION_DOC.name} must state generic wind is unvalidated"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Docs include export hygiene and last clean backend run boundary
# ─────────────────────────────────────────────────────────────────────────────
def test_export_hygiene_and_last_clean_run():
    text = EXECUTION_DOC.read_text().lower()
    assert "export" in text and "last clean" in text, (
        f"{EXECUTION_DOC.name} must mention last clean backend run for exports"
    )
    checklist_text = CHECKLIST.read_text().lower()
    assert "last clean" in checklist_text or "re-run" in checklist_text, (
        f"{CHECKLIST.name} must mention last clean backend run"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: Docs include issue intake and feedback triage workflow
# ─────────────────────────────────────────────────────────────────────────────
def test_issue_intake_and_triage_workflow():
    text = EXECUTION_DOC.read_text().lower()
    assert "issue" in text and ("intake" in text or "triage" in text), (
        f"{EXECUTION_DOC.name} must mention issue intake/triage workflow"
    )
    assert "pilot_issue_intake_template" in text or "issue intake" in text, (
        f"{EXECUTION_DOC.name} must reference issue intake template"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: Docs explicitly avoid bank/lender/audit/certification/SaaS claims
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims():
    text = EXECUTION_DOC.read_text().lower()
    for claim in ["bank", "lender", "audit", "certification", "saas-ready", "enterprise"]:
        if claim in text:
            assert "not" in text, (
                f"{EXECUTION_DOC.name} must not claim {claim}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: Docs state no financial formula/runtime/model changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_formula_runtime_model_changes():
    text = EXECUTION_DOC.read_text().lower()
    assert "no formula changes" in text or "no_formula_changes" in text.lower(), (
        f"{EXECUTION_DOC.name} must state no formula changes"
    )
    assert "no runtime changes" in text or "no_runtime_changes" in text.lower(), (
        f"{EXECUTION_DOC.name} must state no runtime changes"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 21: Docs include G20 BLOCKED and R99/R102 NOT APPROVED
# ─────────────────────────────────────────────────────────────────────────────
def test_g20_r99_r102_guardrails():
    text = EXECUTION_DOC.read_text().lower()
    assert "g20" in text and "blocked" in text, (
        f"{EXECUTION_DOC.name} must state G20 BLOCKED"
    )
    assert ("r99" in text or "r102" in text) and "not approved" in text, (
        f"{EXECUTION_DOC.name} must state R99/R102 NOT APPROVED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: Docs state partial_pay_sweep not promoted, flat/min DSCR not promoted
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_partial_pay_sweep_and_sculpting():
    text = EXECUTION_DOC.read_text().lower()
    assert "partial_pay_sweep" in text and "not promoted" in text, (
        f"{EXECUTION_DOC.name} must state partial_pay_sweep not promoted"
    )
    assert ("flat" in text or "min dscr" in text or "minimum dscr" in text) and "not promoted" in text, (
        f"{EXECUTION_DOC.name} must state flat/min DSCR sculpting not promoted"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: Backend source of truth stated
# ─────────────────────────────────────────────────────────────────────────────
def test_backend_source_of_truth():
    text = EXECUTION_DOC.read_text().lower()
    assert "backend" in text and "source of truth" in text, (
        f"{EXECUTION_DOC.name} must state backend remains source of truth"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 24: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text().lower()
        assert not (
            ("irr" in content or "npv" in content or "dscr" in content)
            and ("function" in content or "=>" in content)
            and "display" not in content
        ), f"{js.name} appears to contain financial calculations (JS should be display-only)"


# ─────────────────────────────────────────────────────────────────────────────
# Test 25: JSON summary phase 40/42 notes included
# ─────────────────────────────────────────────────────────────────────────────
def test_phase_40_42_notes_in_json():
    data = json.loads(JSON_SUMMARY.read_text())
    assert "phase_40_note" in data, "JSON must contain phase_40_note"
    assert "phase_42_note" in data, "JSON must contain phase_42_note"