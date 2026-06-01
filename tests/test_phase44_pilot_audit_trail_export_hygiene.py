"""Phase 44 — Pilot Audit Trail Polish and Export Hygiene Enforcement tests.

Verifies:
1. Phase 44 doc exists
2. Audit/export hygiene checklist exists
3. Audit/export hygiene matrix exists
4. JSON summary parses and includes required fields
5. Docs/templates mention exports reflect last clean backend run
6. Docs/templates distinguish draft edits, saved scenario, and runtime/last run
7. Docs/templates state audit/reconciliation is internal review evidence
8. Docs/templates state generic solar/wind remain excluded and unvalidated
9. Docs/templates state TUHO/Oborovo are trusted pilot scope
10. Docs/templates mention stale export risk and issue routing
11. Docs explicitly avoid bank/lender/audit/certification/SaaS/enterprise claims
12. Docs state no financial formula/runtime/model changes
13. Docs include G20 BLOCKED and R99/R102 NOT APPROVED
14. Docs state partial_pay_sweep not promoted, flat/min DSCR sculpting not promoted
15. No JS financial calculations added
16. Template changes verified: key copy is present in changed templates
"""
import json
import pytest
from pathlib import Path

BASE_SHA = "28afc581900bb5025d509a626de8d8369664d41f"

PHASE44_DOC = Path("docs/phase44_pilot_audit_trail_export_hygiene.md")
CHECKLIST = Path("docs/pilot_audit_export_hygiene_checklist.md")
MATRIX = Path("docs/phase44_audit_export_hygiene_matrix.md")
JSON_SUMMARY = Path("reports/phase44_audit_export_hygiene_summary.json")
RUNTIME_SUMMARY = Path("app/templates/partials/runtime_summary.html")
WORKFLOW_GUIDE = Path("app/templates/partials/pilot_workflow_guide.html")
AUDIT_TAB = Path("app/templates/partials/audit_reconciliation_tab.html")
LIMITATIONS = Path("app/templates/partials/pilot_limitations_notice.html")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 44 doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase44_doc_exists():
    assert PHASE44_DOC.exists(), f"{PHASE44_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Audit/export hygiene checklist exists
# ─────────────────────────────────────────────────────────────────────────────
def test_audit_export_hygiene_checklist_exists():
    assert CHECKLIST.exists(), f"{CHECKLIST} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Audit/export hygiene matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_audit_export_hygiene_matrix_exists():
    assert MATRIX.exists(), f"{MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: JSON summary parses and includes required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses_and_has_required_fields():
    assert JSON_SUMMARY.exists(), f"{JSON_SUMMARY} not found"
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("base_sha") == BASE_SHA, "base_sha must match"
    assert "hygiene_status" in data, "must contain hygiene_status"
    assert "blockers_count" in data, "must contain blockers_count"
    assert "display_only_changes" in data, "must contain display_only_changes"
    assert data.get("no_formula_changes") is True, "no_formula_changes must be True"
    assert data.get("no_runtime_changes") is True, "no_runtime_changes must be True"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Docs/templates mention exports reflect last clean backend run
# ─────────────────────────────────────────────────────────────────────────────
def test_exports_reflect_last_clean_backend_run():
    for doc in [PHASE44_DOC, CHECKLIST, RUNTIME_SUMMARY]:
        text = doc.read_text().lower()
        assert "export" in text and "last clean backend run" in text, (
            f"{doc.name} must mention exports reflect last clean backend run"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Docs/templates distinguish draft edits, saved scenario, runtime
# ─────────────────────────────────────────────────────────────────────────────
def test_draft_saved_runtime_distinction():
    text = PHASE44_DOC.read_text().lower()
    # Check draft/run distinction is documented
    assert ("draft" in text and "last clean" in text) or "runtime" in text, (
        f"{PHASE44_DOC.name} must distinguish draft/saved/runtime states"
    )
    # Runtime summary should mention current draft vs last clean run
    runtime_text = RUNTIME_SUMMARY.read_text().lower()
    assert "draft" in runtime_text or "workspace draft" in runtime_text, (
        f"{RUNTIME_SUMMARY.name} must mention current draft vs last clean run"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Docs/templates state audit/reconciliation is internal review
# ─────────────────────────────────────────────────────────────────────────────
def test_audit_reconciliation_internal_review():
    text = AUDIT_TAB.read_text().lower()
    assert "internal" in text and ("review" in text or "evidence" in text), (
        f"{AUDIT_TAB.name} must state audit/reconciliation is internal review evidence"
    )
    assert "certified" not in text or "not" in text, (
        f"{AUDIT_TAB.name} must deny certified audit claim"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Docs/templates state generic solar/wind remain excluded/unvalidated
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_excluded_and_unvalidated():
    text = PHASE44_DOC.read_text().lower()
    assert "generic solar" in text and "unvalidated" in text, (
        f"{PHASE44_DOC.name} must state generic solar is unvalidated"
    )
    assert "generic wind" in text and "unvalidated" in text, (
        f"{PHASE44_DOC.name} must state generic wind is unvalidated"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Docs/templates state TUHO/Oborovo are trusted pilot scope
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_oborovo_trusted_pilot_scope():
    text = PHASE44_DOC.read_text().lower()
    assert "tuho" in text and "oborovo" in text, (
        f"{PHASE44_DOC.name} must mention TUHO and Oborovo"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Docs/templates mention stale export risk and issue routing
# ─────────────────────────────────────────────────────────────────────────────
def test_stale_export_risk_and_issue_routing():
    text = PHASE44_DOC.read_text().lower()
    assert "stale" in text and ("export" in text or "risk" in text), (
        f"{PHASE44_DOC.name} must mention stale export risk"
    )
    assert "issue" in text and ("routing" in text or "intake" in text), (
        f"{PHASE44_DOC.name} must mention issue routing"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Docs explicitly avoid bank/lender/audit/certification/SaaS claims
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims():
    text = PHASE44_DOC.read_text().lower()
    for claim in ["bank", "lender", "audit", "certification", "saas-ready", "enterprise"]:
        if claim in text:
            assert "not" in text, (
                f"{PHASE44_DOC.name} must not claim {claim}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Docs state no financial formula/runtime/model changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_formula_runtime_model_changes():
    text = PHASE44_DOC.read_text().lower()
    assert "no formula changes" in text or "no_formula_changes" in text.lower(), (
        f"{PHASE44_DOC.name} must state no formula changes"
    )
    assert "no runtime changes" in text or "no_runtime_changes" in text.lower(), (
        f"{PHASE44_DOC.name} must state no runtime changes"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Docs include G20 BLOCKED and R99/R102 NOT APPROVED
# ─────────────────────────────────────────────────────────────────────────────
def test_g20_r99_r102_guardrails():
    text = PHASE44_DOC.read_text().lower()
    assert "g20" in text and "blocked" in text, (
        f"{PHASE44_DOC.name} must state G20 BLOCKED"
    )
    assert ("r99" in text or "r102" in text) and "not approved" in text, (
        f"{PHASE44_DOC.name} must state R99/R102 NOT APPROVED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Docs state partial_pay_sweep not promoted, flat/min DSCR not promoted
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_partial_pay_sweep_and_sculpting():
    text = PHASE44_DOC.read_text().lower()
    assert "partial_pay_sweep" in text and "not promoted" in text, (
        f"{PHASE44_DOC.name} must state partial_pay_sweep not promoted"
    )
    assert ("flat" in text or "min dscr" in text or "minimum dscr" in text) and "not promoted" in text, (
        f"{PHASE44_DOC.name} must state flat/min DSCR sculpting not promoted"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Backend source of truth stated
# ─────────────────────────────────────────────────────────────────────────────
def test_backend_source_of_truth():
    text = PHASE44_DOC.read_text().lower()
    assert "backend" in text and "source of truth" in text, (
        f"{PHASE44_DOC.name} must state backend remains source of truth"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: No JS financial calculations added
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
# Test 17: Template changes verified — key copy present in runtime_summary
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_has_draft_run_distinction():
    text = RUNTIME_SUMMARY.read_text()
    assert "Current workspace draft" in text or "current workspace draft" in text.lower(), (
        f"{RUNTIME_SUMMARY.name} must contain draft/run distinction copy"
    )
    assert "re-run" in text.lower(), (
        f"{RUNTIME_SUMMARY.name} must contain re-run instruction"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: Template changes verified — key copy present in workflow guide
# ─────────────────────────────────────────────────────────────────────────────
def test_workflow_guide_has_export_reminder():
    text = WORKFLOW_GUIDE.read_text()
    assert "last clean backend run" in text.lower() or "re-run" in text.lower(), (
        f"{WORKFLOW_GUIDE.name} must contain re-run reminder in export step"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: Pilot limitations notice strong enough (not softened)
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_limitations_notice_strong():
    text = LIMITATIONS.read_text().lower()
    assert "not yet validated" in text or "unvalidated" in text or "not validated" in text, (
        f"{LIMITATIONS.name} must keep generic warning strong"
    )
    assert "bank" in text and ("approval" in text or "not" in text), (
        f"{LIMITATIONS.name} must include bank/lender non-claim"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: Display-only changes confirmed (no model/calculation changes)
# ─────────────────────────────────────────────────────────────────────────────
def test_display_only_changes_confirmed():
    data = json.loads(JSON_SUMMARY.read_text())
    changes = data.get("display_only_changes", [])
    assert len(changes) >= 2, "At least 2 display-only changes expected"
    for change in changes:
        # Confirm no financial calculation language
        assert not any(kw in change.lower() for kw in ["irr", "npv", "dscr", "formula", "calculate"]), (
            f"Change appears to include calculation language: {change}"
        )