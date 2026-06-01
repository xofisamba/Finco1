"""Phase 43 — Pilot Ongoing Operations and Issue Triage Cadence tests.

Verifies:
1. Phase 43 operations guide exists
2. Issue triage board template exists
3. Weekly operations checklist exists
4. Pause/escalation policy exists
5. Operations decision matrix exists
6. JSON summary parses and includes required fields
7. Docs define daily/weekly cadence
8. Docs define issue severity levels and triage statuses
9. Docs include continuation and pause criteria
10. Docs include /readyz and backup/auto-backup check cadence
11. Docs state TUHO and Oborovo are validated pilot scope
12. Docs state generic solar/wind remain excluded and unvalidated
13. Docs explicitly avoid bank/lender/audit/certification/SaaS/enterprise claims
14. Docs state no financial formula/runtime/model changes
15. Docs include G20 BLOCKED and R99/R102 NOT APPROVED
16. Docs state partial_pay_sweep not promoted, flat/min DSCR sculpting not promoted
17. No JS financial calculations added
"""
import json
import pytest
from pathlib import Path

BASE_SHA = "07506503e0602e6a8d4bd940be56001b6201906a"

OPS_GUIDE = Path("docs/phase43_pilot_ongoing_operations_issue_triage.md")
TRIAGE_BOARD = Path("docs/pilot_issue_triage_board_template.md")
WEEKLY_CHECKLIST = Path("docs/pilot_operations_weekly_checklist.md")
PAUSE_POLICY = Path("docs/pilot_pause_escalation_policy.md")
DECISION_MATRIX = Path("docs/phase43_pilot_operations_decision_matrix.md")
JSON_SUMMARY = Path("reports/phase43_pilot_operations_summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 43 operations guide exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase43_operations_guide_exists():
    assert OPS_GUIDE.exists(), f"{OPS_GUIDE} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Issue triage board template exists
# ─────────────────────────────────────────────────────────────────────────────
def test_issue_triage_board_template_exists():
    assert TRIAGE_BOARD.exists(), f"{TRIAGE_BOARD} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Weekly operations checklist exists
# ─────────────────────────────────────────────────────────────────────────────
def test_weekly_operations_checklist_exists():
    assert WEEKLY_CHECKLIST.exists(), f"{WEEKLY_CHECKLIST} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Pause/escalation policy exists
# ─────────────────────────────────────────────────────────────────────────────
def test_pause_escalation_policy_exists():
    assert PAUSE_POLICY.exists(), f"{PAUSE_POLICY} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Operations decision matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_operations_decision_matrix_exists():
    assert DECISION_MATRIX.exists(), f"{DECISION_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: JSON summary parses and includes required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses_and_has_required_fields():
    assert JSON_SUMMARY.exists(), f"{JSON_SUMMARY} not found"
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("base_sha") == BASE_SHA, "base_sha must match"
    assert "pilot_operating_status" in data, "must contain pilot_operating_status"
    assert "validated_projects" in data, "must contain validated_projects"
    assert "excluded_scopes" in data, "must contain excluded_scopes"
    assert "blockers_count" in data, "must contain blockers_count"
    assert data.get("no_formula_changes") is True, "no_formula_changes must be True"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Docs define daily/weekly cadence
# ─────────────────────────────────────────────────────────────────────────────
def test_daily_weekly_cadence_defined():
    text = OPS_GUIDE.read_text().lower()
    has_daily = "daily" in text and ("before each session" in text or "readyz" in text)
    has_weekly = "weekly" in text and ("monday" in text or "checklist" in text)
    assert has_daily or has_weekly, (
        f"{OPS_GUIDE.name} must define daily and/or weekly operating cadence"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Docs define issue severity levels and triage statuses
# ─────────────────────────────────────────────────────────────────────────────
def test_severity_levels_and_triage_statuses():
    text = OPS_GUIDE.read_text().lower()
    # Severity levels
    assert "blocker" in text and "major" in text and "minor" in text, (
        f"{OPS_GUIDE.name} must define severity levels (blocker/major/minor)"
    )
    # Triage board statuses
    board_text = TRIAGE_BOARD.read_text().lower()
    assert "new" in board_text and "in review" in board_text and "resolved" in board_text, (
        f"{TRIAGE_BOARD.name} must define triage board statuses"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Docs include continuation and pause criteria
# ─────────────────────────────────────────────────────────────────────────────
def test_continuation_and_pause_criteria():
    text = OPS_GUIDE.read_text().lower()
    assert "continuation" in text and ("criteria" in text or "continue" in text), (
        f"{OPS_GUIDE.name} must state continuation criteria"
    )
    assert "pause" in text, (
        f"{OPS_GUIDE.name} must state pause criteria"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Docs include /readyz and backup/auto-backup check cadence
# ─────────────────────────────────────────────────────────────────────────────
def test_readyz_and_backup_check_cadence():
    text = OPS_GUIDE.read_text().lower()
    assert "readyz" in text, f"{OPS_GUIDE.name} must mention /readyz"
    assert "backup" in text, f"{OPS_GUIDE.name} must mention backup/auto-backup"
    assert "cadence" in text or "before each session" in text or "daily" in text, (
        f"{OPS_GUIDE.name} must specify check cadence for /readyz and backup"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Docs state TUHO and Oborovo are validated pilot scope
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_oborovo_validated_scope():
    for doc in [OPS_GUIDE, PAUSE_POLICY]:
        text = doc.read_text().lower()
        assert "tuho" in text and "oborovo" in text, (
            f"{doc.name} must mention TUHO and Oborovo"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Docs state generic solar/wind remain excluded and unvalidated
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_excluded_and_unvalidated():
    text = OPS_GUIDE.read_text().lower()
    assert "generic solar" in text and "unvalidated" in text, (
        f"{OPS_GUIDE.name} must state generic solar is unvalidated"
    )
    assert "generic wind" in text and "unvalidated" in text, (
        f"{OPS_GUIDE.name} must state generic wind is unvalidated"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Docs explicitly avoid bank/lender/audit/certification/SaaS/enterprise claims
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims_documented():
    text = OPS_GUIDE.read_text().lower()
    for claim in ["bank", "lender", "audit", "certification", "saas-ready", "enterprise"]:
        if claim in text:
            assert "not" in text, (
                f"{OPS_GUIDE.name} must not claim {claim}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Docs state no financial formula/runtime/model changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_formula_runtime_model_changes():
    text = OPS_GUIDE.read_text().lower()
    assert "no formula changes" in text or "no_formula_changes" in text.lower(), (
        f"{OPS_GUIDE.name} must state no formula changes"
    )
    assert "no runtime changes" in text or "no_runtime_changes" in text.lower(), (
        f"{OPS_GUIDE.name} must state no runtime changes"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Docs include G20 BLOCKED and R99/R102 NOT APPROVED
# ─────────────────────────────────────────────────────────────────────────────
def test_g20_r99_r102_guardrails():
    text = OPS_GUIDE.read_text().lower()
    assert "g20" in text and "blocked" in text, (
        f"{OPS_GUIDE.name} must state G20 BLOCKED"
    )
    assert ("r99" in text or "r102" in text) and "not approved" in text, (
        f"{OPS_GUIDE.name} must state R99/R102 NOT APPROVED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: Docs state partial_pay_sweep not promoted, flat/min DSCR not promoted
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_partial_pay_sweep_and_sculpting():
    text = OPS_GUIDE.read_text().lower()
    assert "partial_pay_sweep" in text and "not promoted" in text, (
        f"{OPS_GUIDE.name} must state partial_pay_sweep not promoted"
    )
    assert ("flat" in text or "min dscr" in text or "minimum dscr" in text) and "not promoted" in text, (
        f"{OPS_GUIDE.name} must state flat/min DSCR sculpting not promoted"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Backend source of truth stated
# ─────────────────────────────────────────────────────────────────────────────
def test_backend_source_of_truth():
    text = OPS_GUIDE.read_text().lower()
    assert "backend" in text and "source of truth" in text, (
        f"{OPS_GUIDE.name} must state backend remains source of truth"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: No JS financial calculations added
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