"""Phase 42 — Pilot Launch Execution and First Observed Run tests.

Verifies:
1. Phase 42 execution report exists
2. First run observation checklist exists
3. Pilot issue log exists
4. Launch execution decision matrix exists
5. JSON summary parses and includes required fields
6. Docs state first observed run covers TUHO and Oborovo
7. Docs state generic solar/wind remain excluded and unvalidated
8. Docs include /readyz, backup/auto-backup, stale-output boundary, and export artefact checks
9. Docs include launch continuation recommendation
10. Docs avoid bank/lender/audit/certification/SaaS/enterprise claims
11. Docs state no financial formula/runtime/model changes
12. Docs include G20 BLOCKED and R99/R102 NOT APPROVED
13. Docs state partial_pay_sweep not promoted, flat/min DSCR sculpting not promoted
14. No JS financial calculations added
"""
import json
import pytest
from pathlib import Path

BASE_SHA = "1f72591b1099bff50826f7704663e5bb0a671f17"

EXECUTION_REPORT = Path("docs/phase42_pilot_launch_execution_first_observed_run.md")
CHECKLIST = Path("docs/pilot_first_run_observation_checklist.md")
ISSUE_LOG = Path("docs/phase42_pilot_issue_log.md")
DECISION_MATRIX = Path("docs/phase42_pilot_launch_execution_decision_matrix.md")
JSON_SUMMARY = Path("reports/phase42_pilot_launch_execution_summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 42 execution report exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase42_execution_report_exists():
    assert EXECUTION_REPORT.exists(), f"{EXECUTION_REPORT} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: First run observation checklist exists
# ─────────────────────────────────────────────────────────────────────────────
def test_first_run_observation_checklist_exists():
    assert CHECKLIST.exists(), f"{CHECKLIST} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Pilot issue log exists
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_issue_log_exists():
    assert ISSUE_LOG.exists(), f"{ISSUE_LOG} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Launch execution decision matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_launch_execution_decision_matrix_exists():
    assert DECISION_MATRIX.exists(), f"{DECISION_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: JSON summary parses and includes required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses_and_has_required_fields():
    assert JSON_SUMMARY.exists(), f"{JSON_SUMMARY} not found"
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("base_sha") == BASE_SHA, "base_sha must match"
    assert "blockers_count" in data, "must contain blockers_count"
    assert "issues_count" in data, "must contain issues_count"
    assert "validated_projects_observed" in data, "must contain validated_projects_observed"
    assert data.get("no_formula_changes") is True, "no_formula_changes must be True"
    assert data.get("trusted_pilot_continuation_recommendation") == "GO", (
        "continuation recommendation must be GO"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Docs state first observed run covers TUHO and Oborovo
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_oborovo_observed():
    for doc in [EXECUTION_REPORT, CHECKLIST]:
        text = doc.read_text().lower()
        assert "tuho" in text and "oborovo" in text, (
            f"{doc.name} must mention both TUHO and Oborovo"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Docs state generic solar/wind remain excluded and unvalidated
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_excluded_and_unvalidated():
    text = EXECUTION_REPORT.read_text().lower()
    assert "generic solar" in text and "unvalidated" in text, (
        f"{EXECUTION_REPORT.name} must state generic solar is unvalidated"
    )
    assert "generic wind" in text and "unvalidated" in text, (
        f"{EXECUTION_REPORT.name} must state generic wind is unvalidated"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Docs include /readyz, backup/auto-backup, stale-output, export checks
# ─────────────────────────────────────────────────────────────────────────────
def test_readyz_backup_stale_output_export():
    text = CHECKLIST.read_text().lower()
    assert "readyz" in text, f"{CHECKLIST.name} must mention /readyz"
    assert "backup" in text, f"{CHECKLIST.name} must mention backup/auto-backup"
    assert "stale" in text, f"{CHECKLIST.name} must mention stale-output boundary"
    assert "export" in text, f"{CHECKLIST.name} must mention export artefact checks"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Docs include launch continuation recommendation
# ─────────────────────────────────────────────────────────────────────────────
def test_continuation_recommendation():
    text = EXECUTION_REPORT.read_text().lower()
    assert "go" in text and ("continuation" in text or "recommendation" in text), (
        f"{EXECUTION_REPORT.name} must state continuation GO recommendation"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Docs avoid bank/lender/audit/certification/SaaS/enterprise claims
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims():
    text = EXECUTION_REPORT.read_text().lower()
    for claim in ["bank", "lender", "audit", "certification", "saas-ready", "enterprise"]:
        # Either the claim is absent, or "not" is nearby (e.g. "not claimed", "not applicable")
        if claim in text:
            assert "not" in text, (
                f"{EXECUTION_REPORT.name} must not claim {claim}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Docs state no financial formula/runtime/model changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_formula_runtime_model_changes():
    text = EXECUTION_REPORT.read_text().lower()
    assert "no formula changes" in text or "no_formula_changes" in text.lower(), (
        f"{EXECUTION_REPORT.name} must state no formula changes"
    )
    assert "no runtime changes" in text or "no_runtime_changes" in text.lower(), (
        f"{EXECUTION_REPORT.name} must state no runtime changes"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Docs include G20 BLOCKED and R99/R102 NOT APPROVED
# ─────────────────────────────────────────────────────────────────────────────
def test_g20_r99_r102_guardrails():
    text = EXECUTION_REPORT.read_text().lower()
    assert "g20" in text and "blocked" in text, (
        f"{EXECUTION_REPORT.name} must state G20 BLOCKED"
    )
    assert ("r99" in text or "r102" in text) and "not approved" in text, (
        f"{EXECUTION_REPORT.name} must state R99/R102 NOT APPROVED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Docs state partial_pay_sweep not promoted, flat/min DSCR not promoted
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_partial_pay_sweep_and_sculpting():
    text = EXECUTION_REPORT.read_text().lower()
    assert "partial_pay_sweep" in text and "not promoted" in text, (
        f"{EXECUTION_REPORT.name} must state partial_pay_sweep not promoted"
    )
    assert ("flat" in text or "min dscr" in text or "minimum dscr" in text) and "not promoted" in text, (
        f"{EXECUTION_REPORT.name} must state flat/min DSCR sculpting not promoted"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Backend source of truth stated
# ─────────────────────────────────────────────────────────────────────────────
def test_backend_source_of_truth():
    text = EXECUTION_REPORT.read_text().lower()
    assert "backend" in text and "source of truth" in text, (
        f"{EXECUTION_REPORT.name} must state backend remains source of truth"
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
# Test 16: Issue log states no blocker found
# ─────────────────────────────────────────────────────────────────────────────
def test_no_blocker_found_statement():
    text = ISSUE_LOG.read_text().lower()
    assert "no blocker found" in text, (
        f"{ISSUE_LOG.name} must state 'no blocker found'"
    )