"""Phase 41 — Pilot Launch Documentation and Handoff Checklist tests.

Verifies:
1. Phase 41 launch doc exists
2. Pilot handoff checklist exists
3. Pilot scope confirmation note exists
4. Pilot issue intake template exists
5. Launch readiness matrix exists
6. JSON summary parses and contains required fields
7. Docs state Trusted Pilot GO within TUHO/Oborovo frozen-template scope
8. Docs state generic solar/wind remain excluded and unvalidated
9. Docs include non-claims: no bank/lender/audit/certification/SaaS/enterprise
10. Docs mention last clean backend run boundary
11. Docs mention /readyz and backup/auto-backup launch checks
12. Docs mention issue routing/intake
13. Docs state no financial formula/runtime/model changes
14. Decision matrix/checklist includes G20 BLOCKED and R99/R102 NOT APPROVED
15. No JS financial calculations added
16. Guardrails stated: partial_pay_sweep not promoted, flat/min DSCR sculpting not promoted
"""
import json
import pytest
from pathlib import Path

BASE_SHA = "844b0c82b247391a605a2ba76a385611c116d3f9"

LAUNCH_DOC = Path("docs/phase41_pilot_launch_documentation_handoff.md")
HANDOFF = Path("docs/pilot_launch_handoff_checklist.md")
SCOPE_NOTE = Path("docs/pilot_scope_confirmation_note.md")
INTAKE = Path("docs/pilot_issue_intake_template.md")
MATRIX = Path("docs/phase41_pilot_launch_readiness_matrix.md")
JSON_SUMMARY = Path("reports/phase41_pilot_launch_readiness_summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 41 launch doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase41_launch_doc_exists():
    assert LAUNCH_DOC.exists(), f"{LAUNCH_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Pilot handoff checklist exists
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_handoff_checklist_exists():
    assert HANDOFF.exists(), f"{HANDOFF} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Pilot scope confirmation note exists
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_scope_confirmation_note_exists():
    assert SCOPE_NOTE.exists(), f"{SCOPE_NOTE} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Pilot issue intake template exists
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_issue_intake_template_exists():
    assert INTAKE.exists(), f"{INTAKE} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Launch readiness matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_launch_readiness_matrix_exists():
    assert MATRIX.exists(), f"{MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: JSON summary parses and contains required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses_and_has_required_fields():
    assert JSON_SUMMARY.exists(), f"{JSON_SUMMARY} not found"
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("base_sha") == BASE_SHA, "base_sha must match"
    assert "validated_projects" in data, "must contain validated_projects"
    assert "excluded_scopes" in data, "must contain excluded_scopes"
    assert "blockers_count" in data, "must contain blockers_count"
    assert data.get("no_formula_changes") is True, "no_formula_changes must be True"
    assert data.get("no_js_financial_calculations") is True, "no_js_financial_calculations must be True"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Docs state Trusted Pilot GO within TUHO/Oborovo frozen-template scope
# ─────────────────────────────────────────────────────────────────────────────
def test_trusted_pilot_go_stated():
    for doc in [LAUNCH_DOC, HANDOFF, MATRIX]:
        text = doc.read_text().lower()
        assert "go" in text and "tuho" in text and "oborovo" in text, (
            f"{doc.name} must state Trusted Pilot GO with TUHO/Oborovo scope"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Docs state generic solar/wind remain excluded and unvalidated
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_excluded_and_unvalidated():
    for doc in [LAUNCH_DOC, SCOPE_NOTE]:
        text = doc.read_text().lower()
        assert "generic solar" in text and "unvalidated" in text, (
            f"{doc.name} must state generic solar is unvalidated"
        )
        assert "generic wind" in text and "unvalidated" in text, (
            f"{doc.name} must state generic wind is unvalidated"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Docs include non-claims: no bank/lender/audit/certification/SaaS
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims_documented():
    text = SCOPE_NOTE.read_text().lower()
    for claim in ["bank", "lender", "audit", "certification", "saas-ready", "enterprise"]:
        assert claim not in text or "not" in text, (
            f"Non-claims must exclude '{claim}' in {SCOPE_NOTE.name}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Docs mention last clean backend run boundary
# ─────────────────────────────────────────────────────────────────────────────
def test_last_clean_backend_run_mentioned():
    text = SCOPE_NOTE.read_text().lower()
    assert "backend" in text and ("last" in text or "stale" in text), (
        f"{SCOPE_NOTE.name} must mention last clean backend run boundary"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Docs mention /readyz and backup/auto-backup launch checks
# ─────────────────────────────────────────────────────────────────────────────
def test_readyz_and_backup_mentioned():
    text = LAUNCH_DOC.read_text().lower()
    assert "readyz" in text, f"{LAUNCH_DOC.name} must mention /readyz"
    assert "backup" in text, f"{LAUNCH_DOC.name} must mention backup/auto-backup"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Docs mention issue routing/intake
# ─────────────────────────────────────────────────────────────────────────────
def test_issue_intake_routing_mentioned():
    text = LAUNCH_DOC.read_text().lower()
    assert "issue" in text and ("routing" in text or "intake" in text), (
        f"{LAUNCH_DOC.name} must mention issue routing/intake"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Docs state no financial formula/runtime/model changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_formula_runtime_model_changes_stated():
    text = LAUNCH_DOC.read_text().lower()
    assert "no formula changes" in text or "no_formula_changes" in text.lower(), (
        f"{LAUNCH_DOC.name} must state no formula changes"
    )
    assert "no runtime" in text or "no_runtime" in text.lower(), (
        f"{LAUNCH_DOC.name} must state no runtime changes"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: G20 BLOCKED and R99/R102 NOT APPROVED in docs
# ─────────────────────────────────────────────────────────────────────────────
def test_g20_r99_r102_guardrails():
    text = LAUNCH_DOC.read_text().lower()
    assert "g20" in text and "blocked" in text, (
        f"{LAUNCH_DOC.name} must state G20 BLOCKED"
    )
    assert ("r99" in text or "r102" in text) and "not approved" in text, (
        f"{LAUNCH_DOC.name} must state R99/R102 NOT APPROVED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text().lower()
        # JS should not contain financial calculation patterns
        assert not (
            ("irr" in content or "npv" in content or "dscr" in content)
            and ("function" in content or "=>" in content)
            and "display" not in content
        ), f"{js.name} appears to contain financial calculations (JS should be display-only)"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: Guardrails stated: partial_pay_sweep not promoted, flat/min DSCR
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_partial_pay_sweep_and_sculpting():
    text = LAUNCH_DOC.read_text().lower()
    assert "partial_pay_sweep" in text and "not promoted" in text, (
        f"{LAUNCH_DOC.name} must state partial_pay_sweep not promoted"
    )
    assert ("flat" in text or "min dscr" in text or "minimum dscr" in text) and "not promoted" in text, (
        f"{LAUNCH_DOC.name} must state flat/min DSCR sculpting not promoted"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Backend source of truth stated
# ─────────────────────────────────────────────────────────────────────────────
def test_backend_source_of_truth():
    text = LAUNCH_DOC.read_text().lower()
    assert "backend" in text and "source of truth" in text, (
        f"{LAUNCH_DOC.name} must state backend remains source of truth"
    )