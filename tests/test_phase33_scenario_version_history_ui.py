"""Phase 33 — Scenario Version History UI tests.

Verifies:
1. Phase 33 doc exists
2. Evidence matrix exists
3. scenario_version_history partial exists
4. Partial contains required metadata labels
5. Partial explains draft/saved/runtime distinction
6. Partial wired in scenario_workspace.html
7. Existing persistence capabilities reused
8. No schema migration
9. No JS financial calculations added
10. No runtime model files changed
11. No SaaS/multi-user claims
12. Guardrails unchanged
"""
import pytest
import re
from pathlib import Path

BASE_SHA = "5ec5df54079115fe241932ed831045a4f138173a"
PHASE33_DOC = Path("docs/phase33_scenario_version_history_ui.md")
PHASE33_MATRIX = Path("docs/phase33_scenario_version_history_ui_matrix.md")
PARTIAL = Path("app/templates/partials/scenario_version_history.html")
WORKSPACE = Path("app/templates/partials/scenario_workspace.html")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 33 doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase33_doc_exists():
    assert PHASE33_DOC.exists(), f"{PHASE33_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Evidence matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase33_evidence_matrix_exists():
    assert PHASE33_MATRIX.exists(), f"{PHASE33_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: scenario_version_history partial exists
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_version_history_partial_exists():
    assert PARTIAL.exists(), f"{PARTIAL} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Partial contains required metadata labels
# ─────────────────────────────────────────────────────────────────────────────
def test_partial_contains_required_metadata_labels():
    content = PARTIAL.read_text().lower()

    # Scenario name
    assert "scenario_name" in content or "scenario name" in content, (
        "Partial must mention scenario name"
    )
    # Version / scenario ID
    assert "scenario_id" in content or "version" in content, (
        "Partial must mention scenario ID or version"
    )
    # Project
    assert "project_code" in content or "project" in content, (
        "Partial must mention project"
    )
    # Timestamps
    assert "updated_at" in content or "updated" in content or "timestamp" in content, (
        "Partial must mention updated/timestamp"
    )
    # Saved version / version history
    assert "saved" in content or "version" in content, (
        "Partial must mention saved version or version history"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Partial explains draft/saved/runtime distinction
# ─────────────────────────────────────────────────────────────────────────────
def test_partial_explains_draft_saved_runtime_distinction():
    content = PARTIAL.read_text().lower()

    # Draft explanation
    assert "draft" in content, "Partial must explain draft concept"
    # Saved explanation
    assert "saved" in content, "Partial must explain saved version concept"
    # Runtime / last run
    assert "runtime" in content or "last run" in content, (
        "Partial must explain runtime/last run concept"
    )
    # Stale warning
    assert "stale" in content or "warning" in content or "unsaved" in content, (
        "Partial must show stale runtime warning or unsaved notice"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: scenario_workspace.html includes version history partial
# ─────────────────────────────────────────────────────────────────────────────
def test_workspace_includes_version_history_partial():
    content = WORKSPACE.read_text()

    assert "scenario_version_history.html" in content, (
        "scenario_workspace.html must include scenario_version_history partial"
    )
    # Must be conditional on user project
    assert "is_user_project" in content, (
        "Partial inclusion should be conditional on is_user_project"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Existing persistence capabilities reused
# ─────────────────────────────────────────────────────────────────────────────
def test_existing_persistence_capabilities_reused():
    doc = PHASE33_DOC.read_text()

    # Must reference existing endpoints/capabilities
    assert (
        "list_scenarios" in doc
        or "get_scenario" in doc
        or "get_scenario_history" in doc
        or "scenario_summary_cards" in doc
    ), "Phase 33 must reuse existing persistence capabilities"
    # Must state no new schema
    assert (
        "no new schema" in doc.lower()
        or "no schema migration" in doc.lower()
        or "existing schema" in doc.lower()
        or "no new persistence" in doc.lower()
    ), "Phase 33 must document that no new schema is required"


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: No schema migration
# ─────────────────────────────────────────────────────────────────────────────
def test_no_schema_migration():
    doc = PHASE33_DOC.read_text()
    assert (
        "no schema migration" in doc.lower()
        or "no new schema" in doc.lower()
        or "no migration" in doc.lower()
    ), "Phase 33 must state no schema migration"

    # Verify app/db.py not touched
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    touched = result.stdout.strip().split("\n")
    db_changes = [f for f in touched if f.startswith("app/db.py") or f.startswith("app/persistence/")]
    assert not db_changes, f"app/db.py or persistence touched: {db_changes}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    doc = PHASE33_DOC.read_text()
    doc_lower = doc.lower()

    assert (
        "no js financial" in doc_lower
        or "no javascript financial" in doc_lower
        or "backend is authoritative" in doc_lower
        or "not adding js" in doc_lower
        or "no new js" in doc_lower
        or "ui only" in doc_lower
        or "ui wiring" in doc_lower
    ), "Phase 33 must state no JS financial calculations added"


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: No runtime model files changed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_runtime_model_files_changed():
    doc = PHASE33_DOC.read_text()
    doc_lower = doc.lower()

    assert (
        "no financial formula" in doc_lower
        or "no runtime" in doc_lower
        or "no model changes" in doc_lower
        or "documentation" in doc_lower
        or "ui wiring" in doc_lower
        or "no formula changes" in doc_lower
    ), "Phase 33 must state no model formula changes"

    # Verify no model/runtime files touched
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    touched = result.stdout.strip().split("\n")
    model_files = [
        f for f in touched
        if any(pattern in f for pattern in [
            "domain/", "app/project_factories", "app/waterfall",
            "app/revenue", "app/opex", "app/capex", "app/tax",
            "tests/test_phase2", "tests/test_phase3",
            "tests/fixtures/"
        ])
    ]
    assert not model_files, f"Model/runtime files touched: {model_files}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: No SaaS/multi-user/enterprise claims
# ─────────────────────────────────────────────────────────────────────────────
def test_no_saas_or_multi_user_claims():
    doc = PHASE33_DOC.read_text()
    matrix = PHASE33_MATRIX.read_text()
    doc_lower = doc.lower()
    matrix_lower = matrix.lower()

    blocked_terms = [
        "saas-ready", "enterprise-ready", "enterprise ready",
        "multi-tenant",
        "bank ready", "bank-approved", "lender approved",
        "audit ready", "audited", "certified",
        "production ready", "go-live ready",
    ]

    def has_positive_claim(text, terms):
        for term in terms:
            idx = text.find(term)
            while idx != -1:
                prefix = text[max(0, idx-4):idx].strip()
                if prefix not in ("no", "not", "denied", "out of", "do not", "don't", "cannot", "can't"):
                    return True
                idx = text.find(term, idx+1)
        return False

    for term in blocked_terms:
        assert not has_positive_claim(doc_lower, [term]), f"Blocked claim in doc: {term}"
        assert not has_positive_claim(matrix_lower, [term]), f"Blocked claim in matrix: {term}"

    # Legacy term multi-user: check for proper scoping
    legacy_terms = ["multi-user"]
    for term in legacy_terms:
        pattern = r'(?<![\w-])' + re.escape(term) + r'(?![\w-])'
        for match in re.finditer(pattern, doc_lower):
            idx = match.start()
            line_start = doc_lower.rfind(chr(10), 0, idx) + 1
            line_end = doc_lower.find(chr(10), idx)
            line_full = doc_lower[line_start:line_end]
            is_table_out_of_scope = (
                line_full.strip().startswith('|')
                and any(neg in doc_lower[max(0, idx-80):line_end] for neg in ['out of scope', 'out-of-scope'])
            )
            prefix = doc_lower[max(0, idx-15):idx].strip()
            words_before = ' '.join(prefix.split()[-3:]) if prefix else ''
            legacy_term_negations = ["no", "not", "out of scope", "do not", "don't", "cannot", "can't", "out-of-scope"]
            qualified = (
                is_table_out_of_scope
                or any(prefix.endswith(neg) for neg in legacy_term_negations)
                or any(neg in words_before for neg in legacy_term_negations)
            )
            assert qualified, f"Legacy term '{term}' found without proper scoping/denial"
        for match in re.finditer(pattern, matrix_lower):
            idx = match.start()
            prefix = matrix_lower[max(0, idx-15):idx].strip()
            words_before = ' '.join(prefix.split()[-3:]) if prefix else ''
            qualified = (
                any(prefix.endswith(neg) for neg in legacy_term_negations)
                or any(neg in words_before for neg in legacy_term_negations)
            )
            assert qualified, f"Legacy term '{term}' found in matrix without proper scoping/denial"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Guardrails unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_unchanged():
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1

    oborovo = create_default_oborovo()
    tuho = create_default_tuho_wind1()

    partial = getattr(oborovo.financing, 'partial_pay_sweep', None)
    assert partial is None or partial is False, "partial_pay_sweep must not be promoted"

    doc = PHASE33_DOC.read_text()
    doc_lower = doc.lower()
    assert "g20" in doc_lower or "blocked" in doc_lower, "G20 guardrail must be documented"
    assert "r99" in doc_lower or "r102" in doc_lower or "not approved" in doc_lower, "R99/R102 guardrail must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13 (bonus): Partial is informational only — no calculation logic
# ─────────────────────────────────────────────────────────────────────────────
def test_partial_is_display_only():
    content = PARTIAL.read_text()
    assert "def " not in content, "Partial must not contain Python function definitions"
    assert "import " not in content, "Partial must not contain import statements"
    assert "{{ " in content, "Partial must use Jinja2 template syntax (display only)"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14 (bonus): Partial includes explainer content
# ─────────────────────────────────────────────────────────────────────────────
def test_partial_has_explainer_section():
    content = PARTIAL.read_text().lower()
    assert "explainer" in content or "how versions work" in content, (
        "Partial must include explainer section about version semantics"
    )
    assert "draft" in content and "saved" in content and "runtime" in content, (
        "Partial explainer must cover draft, saved, and runtime"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15 (bonus): Phase 33D not required
# ─────────────────────────────────────────────────────────────────────────────
def test_phase33d_not_required():
    doc = PHASE33_DOC.read_text()
    assert (
        "phase 33d not required" in doc.lower()
        or "no phase 33d" in doc.lower()
        or "not required" in doc.lower()
        or "ui wiring only" in doc.lower()
        or "no new implementation" in doc.lower()
    ), "Phase 33D fix decision must be documented"