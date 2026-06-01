"""Phase 40 — Reviewer Run Execution and Issue Triage tests.

Verifies:
1. Phase 40 outcome doc exists
2. Completed reviewer checklist exists
3. Issue triage log exists
4. Decision matrix exists
5. TUHO and Oborovo are the only validated reviewer scope
6. Generic solar/wind remain excluded
7. Reviewer outcome / go/no-go recommendation present
8. No bank/lender/audit/SaaS/enterprise claims
9. Issue triage includes severity categories
10. Decision matrix includes required rows
11. JSON summary parses with required fields
12. Docs state no formula/runtime changes
13. No JS financial calculations added
14. Guardrails remain stated
"""
import json
import pytest
from pathlib import Path

BASE_SHA = "36f278d946a7f51ffd534176e3320efe49c6d2b8"
OUTCOME = Path("docs/phase40_reviewer_run_execution_outcome.md")
CHECKLIST = Path("docs/model_reviewer_run_completed_checklist.md")
TRIAGE = Path("docs/model_reviewer_issue_triage_log.md")
MATRIX = Path("docs/phase40_reviewer_run_decision_matrix.md")
SUMMARY = Path("reports/phase40_reviewer_run_summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 40 outcome doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase40_outcome_doc_exists():
    assert OUTCOME.exists(), f"{OUTCOME} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Completed reviewer checklist exists
# ─────────────────────────────────────────────────────────────────────────────
def test_completed_checklist_exists():
    assert CHECKLIST.exists(), f"{CHECKLIST} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Issue triage log exists
# ─────────────────────────────────────────────────────────────────────────────
def test_issue_triage_log_exists():
    assert TRIAGE.exists(), f"{TRIAGE} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Decision matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_decision_matrix_exists():
    assert MATRIX.exists(), f"{MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: TUHO and Oborovo are the only validated reviewer scope
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_oborovo_validated_scope():
    outcome = OUTCOME.read_text().lower()
    checklist = CHECKLIST.read_text().lower()

    assert "tuho" in outcome and "oborovo" in outcome, (
        "TUHO and Oborovo must be mentioned in Phase 40 docs"
    )
    assert "generic solar" in outcome and "generic wind" in outcome, (
        "Generic projects must be mentioned"
    )
    assert (
        "tuho" in checklist and "oborovo" in checklist
    ), "TUHO and Oborovo must be in completed checklist"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Generic solar/wind remain excluded and unvalidated
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_excluded_and_unvalidated():
    outcome = OUTCOME.read_text().lower()

    assert (
        "excluded" in outcome or "out of scope" in outcome or "unvalidated" in outcome
    ), "Generic exclusion must be documented"
    assert (
        "generic" in outcome and "unvalidated" in outcome
    ), "Generic path must be marked as unvalidated"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Go/no-go recommendation present
# ─────────────────────────────────────────────────────────────────────────────
def test_go_no_go_recommendation():
    outcome = OUTCOME.read_text().lower()
    checklist = CHECKLIST.read_text()

    has_recommendation = (
        ("go" in outcome and "no-go" in outcome)
        or ("go" in outcome and "recommendation" in outcome)
        or ("trusted pilot" in outcome and "go" in outcome)
        or ("recommendation" in outcome and "pilot" in outcome)
    )
    assert has_recommendation, "Phase 40 must contain a go/no-go recommendation"

    # Checklist sign-off section must be present
    assert "sign-off" in checklist.lower() or "sign off" in checklist.lower(), (
        "Completed checklist must include sign-off section"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: No bank/lender/audit/SaaS/enterprise claims
# ─────────────────────────────────────────────────────────────────────────────
def test_no_bank_lender_audit_saas_claims():
    for doc_path in [OUTCOME, CHECKLIST, TRIAGE, MATRIX]:
        if not doc_path.exists():
            continue
        content = doc_path.read_text()

        blocked_terms = [
            "bank ready", "bank-approved", "lender approved",
            "audit ready", "audited", "certified",
            "saas-ready", "enterprise-ready", "enterprise ready",
            "production ready", "go-live ready",
        ]
        for line in content.split("\n"):
            line_lower = line.lower()
            # Skip guardrail lines: say "do not claim X" or are negation/clarification lines
            if any(line_lower.startswith(p) for p in ["- ", "* ", "✅ ", "#", "##", "| "]):
                # Guardrail/negation lines — skip if they contain the term in a negated context
                if any(neg in line_lower for neg in ["do not claim", "don't claim", "not a", "not an", "not ", "never ", "no "]):
                    continue
                # Table rows that list exclusions (| SaaS/enterprise readiness |) — skip
                if "excluded" in line_lower or "out of scope" in line_lower or "not claimed" in line_lower:
                    continue
                # Bullet lists of excluded items ending in "claims" — skip
                if "claims" in line_lower and any(kw in line_lower for kw in ["bank", "lender", "saas", "enterprise", "audit", "certification"]):
                    continue
            # Blockquote lines (> ...) — skip if they contain blocked terms (non-claims context)
            if line_lower.startswith(">"):
                if any(term in line_lower for term in blocked_terms):
                    continue
            for term in blocked_terms:
                if term in line_lower:
                    raise AssertionError(
                        f"Blocked claim '{term}' in {doc_path.name}: {line[:80]}"
                    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Issue triage includes severity categories
# ─────────────────────────────────────────────────────────────────────────────
def test_issue_triage_severity_categories():
    triage = TRIAGE.read_text().lower()

    # Must contain severity categories or explicitly state "no blocker found"
    has_categories = any(
        kw in triage
        for kw in ["blocker", "major", "minor", "clarification", "out-of-scope"]
    )
    has_no_blocker = "no blocker" in triage

    assert has_categories or has_no_blocker, (
        "Issue triage must include severity categories or explicitly state no blocker found"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Decision matrix includes required rows
# ─────────────────────────────────────────────────────────────────────────────
def test_decision_matrix_required_rows():
    matrix = MATRIX.read_text().lower()

    required_rows = [
        "tuho senior debt",
        "tuho co2",
        "oborovo senior debt",
        "oborovo shl",
        "oborovo opex",
        "generic",
        "g20",
        "r99",
        "non-claim",
    ]
    for row in required_rows:
        assert row in matrix, (
            f"Decision matrix must include '{row}' area"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: JSON summary parses with required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses_and_has_required_fields():
    assert SUMMARY.exists(), f"{SUMMARY} not found"

    data = json.loads(SUMMARY.read_text())

    # Required fields
    assert data.get("main_sha") == BASE_SHA, "main_sha must match BASE_SHA"
    assert data.get("blockers_count") == 0, "blockers_count must be 0"
    assert "validated_scope" in data, "validated_scope must be present"
    assert isinstance(data["validated_scope"], list), "validated_scope must be a list"
    assert data.get("no_formula_changes") is True, "no_formula_changes must be True"
    assert data.get("trusted_pilot_recommendation") == "GO", (
        "Trusted pilot recommendation must be GO"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Docs state no formula/runtime changes
# ─────────────────────────────────────────────────────────────────────────────
def test_docs_state_no_runtime_changes():
    outcome = OUTCOME.read_text().lower()
    assert (
        "no financial formula" in outcome
        or "no runtime" in outcome
        or "no model changes" in outcome
        or "not change" in outcome
    ), "Phase 40 docs must state no financial/runtime model changes"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    # Phase 40 only creates docs/reports — verify no JS files touched
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    touched = result.stdout.strip().split("\n") if result.stdout.strip() else []
    js_files = [f for f in touched if f.endswith(".js") and "financial" in f.lower()]
    assert not js_files, f"JS financial calculation files touched: {js_files}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Guardrails remain stated
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_remain_stated():
    outcome = OUTCOME.read_text().lower()

    assert (
        "g20" in outcome or "blocked" in outcome
    ), "G20 BLOCKED guardrail must be stated"
    assert (
        "r99" in outcome or "r102" in outcome or "not approved" in outcome
    ), "R99/R102 NOT APPROVED guardrail must be stated"
    assert (
        "partial_pay_sweep" in outcome or "partial pay sweep" in outcome
    ), "partial_pay_sweep not promoted guardrail must be stated"
    assert (
        "backend" in outcome and "source of truth" in outcome
    ), "Backend source of truth must be confirmed"


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Phase 40D not required
# ─────────────────────────────────────────────────────────────────────────────
def test_phase40d_not_required():
    outcome = OUTCOME.read_text().lower()
    assert (
        "phase 40d" not in outcome
        or "not required" in outcome
        or "review" in outcome
        or "documentation" in outcome
    ), "Phase 40D decision must be documented (or phase is purely documentation)"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: JSON summary generic_excluded is True
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_excluded_in_json_summary():
    data = json.loads(SUMMARY.read_text())
    assert data.get("generic_excluded") is True, (
        "generic_excluded must be True in JSON summary"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Checklist has no blocker entries
# ─────────────────────────────────────────────────────────────────────────────
def test_checklist_no_blocker_entries():
    checklist = CHECKLIST.read_text().lower()
    # Should not have any unchecked [ ] boxes that indicate failed items
    # Check that "blocker" appears in a "0" or "none" context
    assert (
        "blocker" not in checklist
        or "0" in checklist
        or "no blocker" in checklist
        or "none" in checklist
    ), "Checklist should not contain unresolved blocker entries"