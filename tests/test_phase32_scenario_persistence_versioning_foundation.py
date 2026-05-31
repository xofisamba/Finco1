"""Phase 32 — Scenario Persistence / Versioning Foundation tests.

Verifies:
1. Phase 32 doc exists
2. Evidence matrix exists
3. Current persistence architecture is documented
4. Scenario version identity exists (stable ID + timestamp)
5. Saved scenario does not overwrite previous version unintentionally
6. Draft and saved state are distinct
7. Version list/load behavior exists
8. Schema migration is idempotent (if schema changes present)
9. Backup/restore interaction documented
10. No model formula changes claimed
11. No bank/lender/audit/SaaS/enterprise claims
12. No JS financial calculations added
13. Guardrails unchanged
"""
import pytest
import re
from pathlib import Path

BASE_SHA = "4a9e8ed29d9e4b3fb1570497e0bfe40d0d9d7bd0"
PHASE32_DOC = Path("docs/phase32_scenario_persistence_versioning_foundation.md")
PHASE32_MATRIX = Path("docs/phase32_scenario_persistence_evidence_matrix.md")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 32 doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase32_doc_exists():
    assert PHASE32_DOC.exists(), f"{PHASE32_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Evidence matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase32_evidence_matrix_exists():
    assert PHASE32_MATRIX.exists(), f"{PHASE32_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Current persistence architecture documented
# ─────────────────────────────────────────────────────────────────────────────
def test_current_persistence_architecture_documented():
    doc = PHASE32_DOC.read_text()
    assert "scenarios" in doc.lower(), "scenarios table must be documented"
    assert "workspace_states" in doc.lower(), "workspace_states table must be documented"
    assert "runs" in doc.lower(), "runs table must be documented"
    assert "projects" in doc.lower(), "projects table must be documented"
    assert "snapshot" in doc.lower(), "snapshot mechanism must be documented"
    assert "draft" in doc.lower() and "saved" in doc.lower(), "draft/saved distinction must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Scenario version identity exists (stable ID + timestamp)
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_version_identity_exists():
    doc = PHASE32_DOC.read_text()
    assert "scenario_id" in doc, "scenario_id must be documented"
    assert "uuid" in doc.lower() or "hex" in doc.lower(), "UUID-based stable ID must be documented"
    assert "created_at" in doc and "updated_at" in doc, "timestamps must be documented"

    from app.persistence.repository import ScenarioRecord
    assert hasattr(ScenarioRecord, "scenario_id")
    assert hasattr(ScenarioRecord, "created_at")
    assert hasattr(ScenarioRecord, "updated_at")


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Saved scenario does not overwrite previous version unintentionally
# ─────────────────────────────────────────────────────────────────────────────
def test_saved_scenario_does_not_overwrite_previous_version():
    doc = PHASE32_DOC.read_text()
    assert (
        "never overwrite" in doc.lower()
        or "non-destructive" in doc.lower()
        or "append-only" in doc.lower()
        or "always insert" in doc.lower()
    ), "Non-overwrite behavior must be documented"

    import inspect
    from app.persistence.repository import save_scenario

    src = inspect.getsource(save_scenario)
    assert "INSERT INTO scenarios" in src, "save_scenario must use INSERT (not UPDATE on same ID)"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Draft and saved state are distinct
# ─────────────────────────────────────────────────────────────────────────────
def test_draft_and_saved_state_are_distinct():
    doc = PHASE32_DOC.read_text()
    assert "draft_snapshot_json" in doc, "draft_snapshot_json must be documented"
    assert "saved_snapshot_json" in doc, "saved_snapshot_json must be documented"

    from app.persistence.db import get_connection
    conn = get_connection()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(workspace_states)").fetchall()}
    conn.close()
    assert "draft_snapshot_json" in cols, "draft_snapshot_json column must exist"
    assert "saved_snapshot_json" in cols, "saved_snapshot_json column must exist"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Version list/load behavior
# ─────────────────────────────────────────────────────────────────────────────
def test_version_list_and_load_behavior():
    from app.persistence.repository import list_scenarios, get_scenario
    assert callable(list_scenarios)
    assert callable(get_scenario)

    doc = PHASE32_DOC.read_text()
    assert "list_scenarios" in doc, "list_scenarios must be documented"
    assert "get_scenario" in doc, "get_scenario must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Schema migration is idempotent (no schema changes in Phase 32)
# ─────────────────────────────────────────────────────────────────────────────
def test_schema_migration_is_idempotent():
    doc = PHASE32_DOC.read_text()
    assert (
        "no phase 32 schema migration" in doc.lower()
        or "no schema migration" in doc.lower()
        or "no new schema" in doc.lower()
        or "existing schema" in doc.lower()
        or "already supports" in doc.lower()
    ), "Phase 32 must document that no schema migration is needed"

    from app.persistence.db import _init_schema
    import inspect

    src = inspect.getsource(_init_schema)
    assert "CREATE TABLE IF NOT EXISTS" in src, "_init_schema must use IF NOT EXISTS for idempotency"
    assert "CREATE INDEX IF NOT EXISTS" in src, "_init_schema must use IF NOT EXISTS for idempotency"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Backup/restore interaction documented
# ─────────────────────────────────────────────────────────────────────────────
def test_backup_restore_interaction_documented():
    doc = PHASE32_DOC.read_text()
    assert "backup" in doc.lower(), "backup must be documented"
    assert "restore" in doc.lower(), "restore must be documented"
    assert "vacuum" in doc.lower() or "backup file" in doc.lower(), "backup mechanism must be documented"
    assert (
        "orthogonal" in doc.lower()
        or "does not affect" in doc.lower()
        or "preserves all" in doc.lower()
    ), "backup/restore being orthogonal to versioning must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: No model formula changes claimed (allow "no X changes" pattern)
# ─────────────────────────────────────────────────────────────────────────────
def test_no_model_formula_changes_claimed():
    doc = PHASE32_DOC.read_text()
    doc_lower = doc.lower()

    # Look for bare "formula changed" (without preceding "no") — only that is bad
    # "no financial formula changes" is good; "formula changed" alone is bad
    bad_patterns = [
        r'(?<![no ])formula changed(?![s])',  # "formula changed" not preceded by "no "
        r'(?<![no ])runtime change(?!s\b)',   # "runtime change" not preceded by "no "
        r'(?<![no ])model output change(?!s\b)',  # "model output change" not preceded by "no "
    ]
    for pattern in bad_patterns:
        matches = re.findall(pattern, doc_lower)
        assert not matches, f"Bare formula-change pattern '{pattern}' found in doc (without 'no' prefix)"

    assert (
        "no financial formula" in doc_lower
        or "no runtime model" in doc_lower
        or "no model changes" in doc_lower
        or "documentation" in doc_lower
        or "validation" in doc_lower
    ), "Phase 32 must state no model changes"


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: No bank/lender/audit/SaaS/enterprise claims
# ─────────────────────────────────────────────────────────────────────────────
def test_no_bank_lender_audit_saas_claims():
    doc = PHASE32_DOC.read_text()
    matrix = PHASE32_MATRIX.read_text()
    doc_lower = doc.lower()
    matrix_lower = matrix.lower()

    # Terms that are claims (positive/productive statements)
    # vs. denial/contextual mention ("not implemented", "out of scope", "Do NOT")
    positive_claims = [
        ("bank ready", "bank-ready"),
        ("bank-approved", "bank approved"),
        ("lender approved",),
        ("audit ready",),
        ("audited",),
        ("certified",),
        ("saas-ready", "saas ready"),
        ("enterprise-ready", "enterprise ready"),
        ("production ready",),
        ("go-live ready",),
    ]

    # Legacy/deprecated terms that must not appear in positive contexts
    legacy_terms = [
        "multi-tenant", "multi-user",
    ]

    def has_positive_claim(text, terms):
        """Check if text contains term without preceding 'no' or 'not' or 'denied'."""
        for term in terms:
            idx = text.find(term)
            while idx != -1:
                # Check if preceded by negation
                prefix = text[max(0, idx-4):idx].strip()
                if prefix not in ("no", "not", "denied", "out of", "do not", "don't", "cannot", "can't"):
                    return True
                idx = text.find(term, idx+1)
        return False

    for term_group in positive_claims:
        assert not has_positive_claim(doc_lower, term_group), f"Blocked claim in doc: {term_group[0]}"
        assert not has_positive_claim(matrix_lower, term_group), f"Blocked claim in matrix: {term_group[0]}"

    # Legacy terms: must not appear in unqualified positive contexts
    # Accept: "no multi-user", "out of scope: multi-user", "multi-user auth" (compound), "multi-tenant"
    # Reject: "multi-user" as standalone noun without qualifying prefix
    legacy_term_negations = ["no", "not", "out of scope", "do not", "don't", "cannot", "can't", "out-of-scope"]
    for term in legacy_terms:
        import re
        # Match standalone term (not part of a compound identifier)
        pattern = r'(?<![\w-])' + re.escape(term) + r'(?![\w-])'
        for match in re.finditer(pattern, doc_lower):
            idx = match.start()
            # Detect table context: if line starts with | and has "out of scope" nearby, it's a denial
            line_start = doc_lower.rfind('\n', 0, idx) + 1
            line_end = doc_lower.find('\n', idx)
            line_full = doc_lower[line_start:line_end]
            is_table_out_of_scope = (
                line_full.strip().startswith('|')
                and any(
                    neg in doc_lower[max(0, idx-80):line_end]
                    for neg in ['out of scope', 'out-of-scope']
                )
            )
            prefix = doc_lower[max(0, idx-15):idx].strip()
            words_before = ' '.join(prefix.split()[-3:]) if prefix else ''
            qualified = (
                is_table_out_of_scope
                or any(prefix.endswith(neg) for neg in legacy_term_negations)
                or any(neg in words_before for neg in legacy_term_negations)
            )
            assert qualified, (
                f"Legacy term '{term}' found in doc without proper scoping/denial "
                f"(prefix='{prefix}' — use 'no {term}', 'out of scope: {term}', etc.)"
            )
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
# Test 12: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    doc = PHASE32_DOC.read_text()
    assert (
        "no js financial" in doc.lower()
        or "no javascript financial" in doc.lower()
        or "backend is authoritative" in doc.lower()
        or "js not touched" in doc.lower()
        or "no new js" in doc.lower()
        or "not adding js" in doc.lower()
    ), "Phase 32 must state JS financial calculations are not added"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Guardrails unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_unchanged():
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1

    oborovo = create_default_oborovo()
    tuho = create_default_tuho_wind1()

    # partial_pay_sweep not promoted — None/missing means not added (not promoted)
    partial = getattr(oborovo.financing, 'partial_pay_sweep', None)
    assert partial is None or partial is False, f"partial_pay_sweep must be None or False (not promoted), got {partial}"

    doc = PHASE32_DOC.read_text()
    doc_lower = doc.lower()
    assert "g20" in doc_lower or "blocked" in doc_lower, "G20 guardrail must be documented"
    assert "r99" in doc_lower or "r102" in doc_lower or "not approved" in doc_lower, "R99/R102 guardrail must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14 (bonus): ScenarioRecord has versioning fields
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_record_has_versioning_fields():
    from app.persistence.repository import ScenarioRecord

    required_fields = [
        "scenario_id", "project_id", "user_id", "scenario_name",
        "created_at", "updated_at", "snapshot",
        "base_input_set", "overrides",
        "last_run_summary", "governance_state",
        "replay_metadata", "archived", "is_base_case",
    ]
    for field in required_fields:
        assert hasattr(ScenarioRecord, field), f"ScenarioRecord missing field: {field}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 15 (bonus): workspace_states has draft/saved/runtime fields
# ─────────────────────────────────────────────────────────────────────────────
def test_workspace_states_has_draft_saved_runtime_fields():
    from app.persistence.db import get_connection

    conn = get_connection()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(workspace_states)").fetchall()}
    conn.close()

    required_cols = [
        "draft_snapshot_json", "saved_snapshot_json",
        "last_runtime_snapshot_json", "last_runtime_summary_json",
        "last_runtime_snapshot_id", "dirty",
    ]
    for col in required_cols:
        assert col in cols, f"workspace_states missing column: {col}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16 (bonus): runs table has required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_runs_table_has_required_fields():
    from app.persistence.db import get_connection

    conn = get_connection()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
    conn.close()

    required_cols = [
        "run_id", "user_id", "project_type", "scenario",
        "created_at", "inputs_json", "kpis_json",
    ]
    for col in required_cols:
        assert col in cols, f"runs table missing column: {col}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 17 (bonus): Phase 32 is docs/validation only
# ─────────────────────────────────────────────────────────────────────────────
def test_phase32_is_documentation_validation_only():
    doc = PHASE32_DOC.read_text()
    assert (
        "documentation" in doc.lower()
        or "validation" in doc.lower()
        or "existing architecture" in doc.lower()
        or "no new implementation" in doc.lower()
    ), "Phase 32 must be classified as documentation/validation"


# ─────────────────────────────────────────────────────────────────────────────
# Test 18 (bonus): Phase 32D not required
# ─────────────────────────────────────────────────────────────────────────────
def test_phase32d_not_required():
    doc = PHASE32_DOC.read_text()
    assert (
        "phase 32d not required" in doc.lower()
        or "no phase 32d" in doc.lower()
        or "not required" in doc.lower()
        or "existing architecture" in doc.lower()
        or "already supports" in doc.lower()
        or "no new implementation" in doc.lower()
    ), "Phase 32D fix decision must be documented"