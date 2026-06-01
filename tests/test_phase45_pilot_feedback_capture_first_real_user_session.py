"""Phase 45 — Pilot Feedback Capture / First Real-User Session Notes tests.

Verifies:
1. Phase 45 overview doc exists
2. Real-user session agenda exists
3. Feedback form template exists
4. First real-user session notes template exists
5. Feedback triage matrix exists
6. JSON summary parses and includes real_user_evidence_status = framework_ready_not_yet_collected
7. Docs state controlled trusted pilot is GO with conditions
8. Docs state paid pilot is NOT READY
9. Docs state enterprise SaaS is NOT READY
10. Docs state Phase 40 reviewer run was internal
11. Docs state Phase 42 first observed run was internal/controlled
12. Docs state generic solar/wind remain excluded and unvalidated
13. Docs include export hygiene and last clean backend run boundary
14. Docs include issue intake and feedback triage workflow
15. Docs explicitly avoid bank/lender/audit/certification/SaaS/enterprise claims
16. Docs state no financial formula/runtime/model changes
17. Docs include G20 BLOCKED and R99/R102 NOT APPROVED
18. Docs state partial_pay_sweep not promoted, flat/min DSCR not promoted
19. No JS financial calculations added
20. No fake user feedback inserted — templates are placeholders/instructions
"""
import json
import pytest
from pathlib import Path

BASE_SHA = "0c268c38bc0cc75c3830bd98eca8c491cd31a73b"

PHASE45_DOC = Path("docs/phase45_pilot_feedback_capture_first_real_user_session.md")
AGENDA = Path("docs/pilot_real_user_session_agenda.md")
FEEDBACK_FORM = Path("docs/pilot_feedback_form_template.md")
SESSION_NOTES = Path("docs/pilot_first_real_user_session_notes_template.md")
TRIAGE_MATRIX = Path("docs/phase45_pilot_feedback_triage_matrix.md")
JSON_SUMMARY = Path("reports/phase45_pilot_feedback_capture_summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 45 overview doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase45_overview_doc_exists():
    assert PHASE45_DOC.exists(), f"{PHASE45_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Real-user session agenda exists
# ─────────────────────────────────────────────────────────────────────────────
def test_real_user_session_agenda_exists():
    assert AGENDA.exists(), f"{AGENDA} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Feedback form template exists
# ─────────────────────────────────────────────────────────────────────────────
def test_feedback_form_template_exists():
    assert FEEDBACK_FORM.exists(), f"{FEEDBACK_FORM} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: First real-user session notes template exists
# ─────────────────────────────────────────────────────────────────────────────
def test_first_real_user_session_notes_template_exists():
    assert SESSION_NOTES.exists(), f"{SESSION_NOTES} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Feedback triage matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_feedback_triage_matrix_exists():
    assert TRIAGE_MATRIX.exists(), f"{TRIAGE_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: JSON summary parses and includes required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses_and_has_required_fields():
    assert JSON_SUMMARY.exists(), f"{JSON_SUMMARY} not found"
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("base_sha") == BASE_SHA, "base_sha must match"
    assert data.get("real_user_evidence_status") == "framework_ready_not_yet_collected", (
        "real_user_evidence_status must be framework_ready_not_yet_collected"
    )
    assert data.get("controlled_trusted_pilot_status") == "GO_with_conditions", (
        "controlled_trusted_pilot_status must be GO_with_conditions"
    )
    assert data.get("paid_pilot_status") == "NOT_READY", (
        "paid_pilot_status must be NOT_READY"
    )
    assert data.get("enterprise_saas_status") == "NOT_READY", (
        "enterprise_saas_status must be NOT_READY"
    )
    assert data.get("no_formula_changes") is True, "no_formula_changes must be True"
    assert data.get("no_runtime_changes") is True, "no_runtime_changes must be True"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Docs state controlled trusted pilot is GO with conditions
# ─────────────────────────────────────────────────────────────────────────────
def test_controlled_trusted_pilot_go_with_conditions():
    text = PHASE45_DOC.read_text().lower()
    assert "go" in text and ("tuho" in text or "oborovo" in text or "frozen" in text), (
        f"{PHASE45_DOC.name} must state controlled trusted pilot is GO with conditions"
    )
    assert "with conditions" in text or "conditions" in text, (
        f"{PHASE45_DOC.name} must reference conditions"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Docs state paid pilot is NOT READY
# ─────────────────────────────────────────────────────────────────────────────
def test_paid_pilot_not_ready():
    text = PHASE45_DOC.read_text().lower()
    assert "paid pilot" in text and "not ready" in text, (
        f"{PHASE45_DOC.name} must state paid pilot is NOT READY"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Docs state enterprise SaaS is NOT READY
# ─────────────────────────────────────────────────────────────────────────────
def test_enterprise_saas_not_ready():
    text = PHASE45_DOC.read_text().lower()
    assert ("enterprise" in text or "saas" in text) and "not ready" in text, (
        f"{PHASE45_DOC.name} must state enterprise SaaS is NOT READY"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Docs state Phase 40 reviewer run was internal
# ─────────────────────────────────────────────────────────────────────────────
def test_phase40_internal_review():
    text = PHASE45_DOC.read_text().lower()
    assert "phase 40" in text and ("internal" in text or "not independent" in text), (
        f"{PHASE45_DOC.name} must state Phase 40 reviewer run was internal"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Docs state Phase 42 first observed run was internal/controlled
# ─────────────────────────────────────────────────────────────────────────────
def test_phase42_internal_controlled():
    text = PHASE45_DOC.read_text().lower()
    assert "phase 42" in text and ("internal" in text or "controlled" in text or "not real-user" in text), (
        f"{PHASE45_DOC.name} must state Phase 42 first observed run was internal/controlled"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Docs state generic solar/wind remain excluded and unvalidated
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_excluded_and_unvalidated():
    text = PHASE45_DOC.read_text().lower()
    assert "generic solar" in text and "unvalidated" in text, (
        f"{PHASE45_DOC.name} must state generic solar is unvalidated"
    )
    assert "generic wind" in text and "unvalidated" in text, (
        f"{PHASE45_DOC.name} must state generic wind is unvalidated"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Docs include export hygiene and last clean backend run boundary
# ─────────────────────────────────────────────────────────────────────────────
def test_export_hygiene_and_last_clean_run():
    text = PHASE45_DOC.read_text().lower()
    assert "export" in text and "last clean" in text, (
        f"{PHASE45_DOC.name} must mention last clean backend run for exports"
    )
    agenda_text = AGENDA.read_text().lower()
    assert "last clean" in agenda_text, (
        f"{AGENDA.name} must mention last clean backend run"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Docs include issue intake and feedback triage workflow
# ─────────────────────────────────────────────────────────────────────────────
def test_issue_intake_and_triage_workflow():
    text = PHASE45_DOC.read_text().lower()
    assert "issue" in text and ("intake" in text or "triage" in text), (
        f"{PHASE45_DOC.name} must mention issue intake/triage workflow"
    )
    matrix_text = TRIAGE_MATRIX.read_text().lower()
    assert "triage" in matrix_text, (
        f"{TRIAGE_MATRIX.name} must include triage workflow"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Docs explicitly avoid bank/lender/audit/certification/SaaS claims
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims():
    text = PHASE45_DOC.read_text().lower()
    for claim in ["bank", "lender", "audit", "certification", "saas-ready", "enterprise"]:
        if claim in text:
            assert "not" in text, (
                f"{PHASE45_DOC.name} must not claim {claim}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: Docs state no financial formula/runtime/model changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_formula_runtime_model_changes():
    text = PHASE45_DOC.read_text().lower()
    assert "no formula changes" in text or "no_formula_changes" in text.lower(), (
        f"{PHASE45_DOC.name} must state no formula changes"
    )
    assert "no runtime changes" in text or "no_runtime_changes" in text.lower(), (
        f"{PHASE45_DOC.name} must state no runtime changes"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Docs include G20 BLOCKED and R99/R102 NOT APPROVED
# ─────────────────────────────────────────────────────────────────────────────
def test_g20_r99_r102_guardrails():
    text = PHASE45_DOC.read_text().lower()
    assert "g20" in text and "blocked" in text, (
        f"{PHASE45_DOC.name} must state G20 BLOCKED"
    )
    assert ("r99" in text or "r102" in text) and "not approved" in text, (
        f"{PHASE45_DOC.name} must state R99/R102 NOT APPROVED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: Docs state partial_pay_sweep not promoted, flat/min DSCR not promoted
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_partial_pay_sweep_and_sculpting():
    text = PHASE45_DOC.read_text().lower()
    assert "partial_pay_sweep" in text and "not promoted" in text, (
        f"{PHASE45_DOC.name} must state partial_pay_sweep not promoted"
    )
    assert ("flat" in text or "min dscr" in text or "minimum dscr" in text) and "not promoted" in text, (
        f"{PHASE45_DOC.name} must state flat/min DSCR sculpting not promoted"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: Backend source of truth stated
# ─────────────────────────────────────────────────────────────────────────────
def test_backend_source_of_truth():
    text = PHASE45_DOC.read_text().lower()
    assert "backend" in text and "source of truth" in text, (
        f"{PHASE45_DOC.name} must state backend remains source of truth"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: No JS financial calculations added
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
# Test 21: No fake user feedback — templates are placeholders/instructions
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fake_user_feedback():
    # Session notes template should contain placeholder/instruction language
    notes_text = SESSION_NOTES.read_text()
    assert "instructions" in notes_text.lower() or "placeholder" in notes_text.lower() or "do not fabricate" in notes_text.lower() or "fill in after" in notes_text.lower(), (
        f"{SESSION_NOTES.name} must contain placeholder/instruction language — no fake feedback"
    )
    # Feedback form should contain instruction language
    form_text = FEEDBACK_FORM.read_text()
    assert "do not fabricate" in form_text.lower() or "record only" in form_text.lower() or "observe" in form_text.lower(), (
        f"{FEEDBACK_FORM.name} must contain instruction language — no fake feedback"
    )
    # Agenda should not claim real session already happened
    agenda_text = AGENDA.read_text()
    assert "first real-user" in agenda_text.lower() or "observe" in agenda_text.lower(), (
        f"{AGENDA.name} must frame session as observation framework"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: Session agenda contains scope disclaimer
# ─────────────────────────────────────────────────────────────────────────────
def test_agenda_scope_disclaimer():
    text = AGENDA.read_text().lower()
    assert "bank" in text and ("not" in text or "lender" in text), (
        f"{AGENDA.name} must include scope disclaimer about bank/lender/audit"
    )
    assert "generic" in text and ("not validated" in text or "unvalidated" in text or "exploratory" in text), (
        f"{AGENDA.name} must include generic warning"
    )
    assert "last clean" in text, (
        f"{AGENDA.name} must mention last clean backend run boundary"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: JSON summary includes Phase 40/42 notes
# ─────────────────────────────────────────────────────────────────────────────
def test_phase_40_42_notes_in_json():
    data = json.loads(JSON_SUMMARY.read_text())
    assert "phase_40_note" in data, "JSON must contain phase_40_note"
    assert "phase_42_note" in data, "JSON must contain phase_42_note"
    assert "internal" in data["phase_40_note"].lower(), "phase_40_note must mention internal"
    assert "internal" in data["phase_42_note"].lower() or "controlled" in data["phase_42_note"].lower(), (
        "phase_42_note must mention internal/controlled"
    )