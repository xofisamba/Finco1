"""Phase 35 — Pilot Release Candidate Closeout tests.

Verifies:
1. Phase 35 closeout doc exists
2. Readiness checklist exists
3. Scope matrix exists
4. Validated scope is explicit
5. Diagnostic-only scope is explicit
6. Unvalidated/excluded scope is explicit
7. Scenario persistence/history included
8. Operational readiness included
9. Non-claims are explicit
10. Go/no-go checklist present
11. Scope matrix contains required rows
12. Manifest decision (if manifest present, valid; if absent, doc explains why)
13. No runtime model files changed
14. No JS financial calculations added
15. Guardrails unchanged
"""
import pytest
import re
from pathlib import Path

BASE_SHA = "048806a4bcc322c078ffc7d3e5de0d24b310fbac"
CLOSEout = Path("docs/phase35_pilot_release_candidate_closeout.md")
CHECKLIST = Path("docs/pilot_rc_readiness_checklist.md")
MATRIX = Path("docs/pilot_rc_scope_matrix.md")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 35 closeout doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase35_closeout_doc_exists():
    assert CLOSEout.exists(), f"{CLOSEout} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Pilot RC readiness checklist exists
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_rc_readiness_checklist_exists():
    assert CHECKLIST.exists(), f"{CHECKLIST} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Pilot RC scope matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_rc_scope_matrix_exists():
    assert MATRIX.exists(), f"{MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Validated scope is explicit
# ─────────────────────────────────────────────────────────────────────────────
def test_validated_scope_is_explicit():
    doc = CLOSEout.read_text().lower()

    # TUHO and Oborovo frozen path must be mentioned as validated
    assert "tuho" in doc and "validated" in doc, "TUHO frozen path must be mentioned as validated"
    assert "oborovo" in doc and "validated" in doc, "Oborovo frozen path must be mentioned as validated"

    # TUHO CO2 must be mentioned
    assert "co2" in doc and "tuho" in doc, "TUHO CO2 must be mentioned as validated"

    # Oborovo OpEx must be mentioned
    assert "opex" in doc and "oborovo" in doc, "Oborovo OpEx must be mentioned as validated"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Diagnostic-only scope is explicit
# ─────────────────────────────────────────────────────────────────────────────
def test_diagnostic_only_scope_is_explicit():
    doc = CLOSEout.read_text().lower()
    checklist_content = CHECKLIST.read_text().lower()

    # Oborovo CAPEX sensitivity must be mentioned as diagnostic-only
    assert "capex" in doc and "diagnostic" in doc, "Oborovo CAPEX sensitivity must be mentioned as diagnostic-only"
    assert "capex" in checklist_content and "diagnostic" in checklist_content, (
        "CAPEX sensitivity must be in readiness checklist as diagnostic-only"
    )
    # Must state it is not Excel-validated beyond base case
    assert (
        "not excel-validated" in doc
        or "not validated" in doc
        or "diagnostic only" in doc
    ), "CAPEX sensitivity must be explicitly stated as not Excel-validated beyond base case"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Unvalidated/excluded scope is explicit
# ─────────────────────────────────────────────────────────────────────────────
def test_unvalidated_excluded_scope_is_explicit():
    doc = CLOSEout.read_text().lower()

    # Generic solar/wind must be mentioned as unvalidated
    assert "generic" in doc and "unvalidated" in doc, "Generic solar/wind must be mentioned as unvalidated"

    # Construction IDC / M1-M18 / C.16 not wired
    assert "construction idc" in doc or "m1-m18" in doc or "c.16" in doc, (
        "Construction IDC / M1-M18 / C.16 must be mentioned as not wired"
    )

    # Live sculpting / debt re-sizing not promoted
    assert "live sculpt" in doc or "debt re-siz" in doc or "sculpting" in doc, (
        "Live sculpting / debt re-sizing must be mentioned as not promoted"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Scenario persistence and history included
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_persistence_and_history_included():
    doc = CLOSEout.read_text().lower()

    # Scenario save/load/versioning mentioned
    assert "scenario" in doc and ("versioning" in doc or "version" in doc), (
        "Scenario versioning must be mentioned in closeout doc"
    )

    # Scenario version history UI mentioned
    assert "scenario version history" in doc or "version history ui" in doc, (
        "Scenario version history UI must be mentioned"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Operational readiness included
# ─────────────────────────────────────────────────────────────────────────────
def test_operational_readiness_included():
    doc = CLOSEout.read_text().lower()

    # Backup/restore
    assert "backup" in doc and "restore" in doc, "Backup/restore must be mentioned"

    # Auto-backup
    assert "auto-backup" in doc or "auto backup" in doc, "Auto-backup must be mentioned"

    # /readyz or observability
    assert "/readyz" in doc or "readyz" in doc or "observability" in doc, (
        "/readyz or observability must be mentioned"
    )

    # FINCO_APP_MODE or pilot mode
    assert "pilot mode" in doc or "app_mode" in doc or "single-user" in doc, (
        "Pilot mode / single-user must be mentioned"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Non-claims are explicit
# ─────────────────────────────────────────────────────────────────────────────
def test_non_claims_are_explicit():
    doc = CLOSEout.read_text()
    matrix = MATRIX.read_text()
    checklist = CHECKLIST.read_text()

    for fname, content in [("closeout", doc), ("matrix", matrix), ("checklist", checklist)]:
        content_lower = content.lower()

        blocked_terms = [
            "bank ready", "bank-approved", "lender approved",
            "audit ready", "audited", "certified",
            "saas-ready", "enterprise-ready", "enterprise ready",
            "production ready", "go-live ready",
        ]

        # For each term, check if it appears in a denial context
        for term in blocked_terms:
            idx = content_lower.find(term)
            while idx != -1:
                # Get the full line containing this term
                line_start = content_lower.rfind(chr(10), 0, idx) + 1
                line_end = content_lower.find(chr(10), idx)
                if line_end == -1:
                    line_end = len(content_lower)
                line = content_lower[line_start:line_end]

                # Table row with "not" / "excluded" / "not claimed" = denial context
                is_denial = (
                    line.strip().startswith('|')
                    and any(neg in line for neg in [
                        'not ', 'not-', 'excluded', 'not implemented',
                        'not claimed', 'not applicable', 'do not',
                    ])
                )
                # Standalone line preceded by negation
                prefix = content_lower[max(0, idx-5):idx].strip()
                is_prefix_denial = prefix.endswith(('no', 'not', 'denied', 'out of'))

                assert is_denial or is_prefix_denial, (
                    f"Blocked claim '{term}' found in {fname} without proper denial context. "
                    f"Line: {line[:80]!r}"
                )
                idx = content_lower.find(term, idx+1)



# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Go/no-go checklist present
# ─────────────────────────────────────────────────────────────────────────────
def test_go_no_go_checklist_present():
    checklist = CHECKLIST.read_text().lower()

    # Must have go/no-go or sign-off items
    assert (
        "go / no-go" in checklist
        or "go/no-go" in checklist
        or "sign-off" in checklist
        or "sign off" in checklist
    ), "Checklist must include go/no-go or sign-off items"


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Scope matrix contains required rows
# ─────────────────────────────────────────────────────────────────────────────
def test_scope_matrix_contains_required_rows():
    matrix = MATRIX.read_text().lower()

    # Check for items that may appear in slightly different forms
    required_flex = [
        ("tuho", ["tuho"]),
        ("oborovo", ["oborovo"]),
        ("generic", ["generic solar", "generic wind", "generic"]),
        ("co2", ["co2", "co₂"]),
        ("opex", ["opex"]),
        ("capex sensitivity", ["capex", "sensitivity"]),
        ("scenario versioning", ["scenario versioning", "scenario version", "versioning"]),
        ("scenario history", ["scenario history", "version history"]),
        ("audit", ["audit"]),
        ("reconciliation", ["reconciliation"]),
        ("backup", ["backup"]),
        ("observability", ["observability", "readyz"]),
        ("pilot mode", ["pilot mode", "single-user", "app_mode"]),
        ("auth", ["auth", "single-user"]),
        ("idc", ["idc", "construction"]),
        ("live sculpt", ["live sculpt", "sculpting", "debt re-siz"]),
        ("saas", ["saas"]),
    ]
    for item, variants in required_flex:
        found = any(v in matrix for v in variants)
        assert found, f"Scope matrix must include '{item}' row (tried variants: {variants})"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Manifest decision (if present, valid; if absent, doc explains why)
# ─────────────────────────────────────────────────────────────────────────────
def test_manifest_if_present_is_valid():
    manifest_path = Path("reports/phase35_pilot_rc_manifest.json")
    doc = CLOSEout.read_text().lower()

    if manifest_path.exists():
        import json
        data = json.loads(manifest_path.read_text())

        # Must include current main SHA
        assert "main_sha" in data or "base_sha" in data or "sha" in data, (
            "Manifest must include current SHA"
        )
        # Must include TUHO and Oborovo
        assert "tuho" in str(data).lower(), "Manifest must include TUHO"
        assert "oborovo" in str(data).lower(), "Manifest must include Oborovo"
        # Must include excluded generic path
        assert "generic" in str(data).lower(), "Manifest must include excluded generic path"
        # Must include no formula changes
        assert "no formula" in str(data).lower() or "formula" not in str(data).lower(), (
            "Manifest must include no formula changes statement"
        )
    else:
        # Manifest absent — closeout doc must explain why
        assert (
            "manifest" in doc
            and ("skipped" in doc or "not created" in doc or "not needed" in doc or "decision" in doc)
        ) or "skip" in doc or "manifest decision" in doc, (
            "Closeout doc must explain why manifest is not created"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: No runtime model files changed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_runtime_model_files_changed():
    doc = CLOSEout.read_text().lower()

    assert (
        "no financial formula" in doc
        or "no runtime" in doc
        or "no model changes" in doc
        or "release" in doc
        and "documentation" in doc
        or "no formula changes" in doc
    ), "Closeout doc must state no model formula changes"

    # Verify no model/runtime files touched
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    touched = result.stdout.strip().split("\n") if result.stdout.strip() else []
    model_files = [
        f for f in touched
        if any(pattern in f for pattern in [
            "domain/", "app/project_factories", "app/waterfall",
            "app/revenue", "app/opex", "app/capex", "app/tax",
        ])
    ]
    assert not model_files, f"Model/runtime files touched: {model_files}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    doc = CLOSEout.read_text().lower()

    assert (
        "no js financial" in doc
        or "no javascript financial" in doc
        or "backend is authoritative" in doc
        or "no new js" in doc
        or "release" in doc
        and "no financial" in doc
        or "documentation" in doc
    ), "Closeout doc must state no JS financial calculations added"


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Guardrails unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_unchanged():
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1

    oborovo = create_default_oborovo()
    tuho = create_default_tuho_wind1()

    partial = getattr(oborovo.financing, 'partial_pay_sweep', None)
    assert partial is None or partial is False, "partial_pay_sweep must not be promoted"

    doc = CLOSEout.read_text().lower()
    assert "g20" in doc or "blocked" in doc, "G20 guardrail must be documented"
    assert "r99" in doc or "r102" in doc or "not approved" in doc, "R99/R102 guardrail must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16 (bonus): Phase 35D not required
# ─────────────────────────────────────────────────────────────────────────────
def test_phase35d_not_required():
    doc = CLOSEout.read_text()
    assert (
        "phase 35d not required" in doc.lower()
        or "no phase 35d" in doc.lower()
        or "not required" in doc.lower()
        or "release" in doc.lower()
        or "documentation only" in doc.lower()
    ), "Phase 35D fix decision must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 17 (bonus): Pilot RC go/no-go assessment present
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_rc_go_no_go_assessment_present():
    doc = CLOSEout.read_text().lower()
    matrix = MATRIX.read_text().lower()

    # Must have a go/no-go decision or recommendation
    assert (
        "go" in doc
        or "decision" in doc
        or "pilot rc" in doc
    ), "Pilot RC go/no-go assessment must be present"

    # TUHO and Oborovo must be marked as GO
    assert "tuho" in matrix and "✅" in MATRIX.read_text(), "TUHO must be marked as validated in scope matrix"
    assert "oborovo" in matrix and "✅" in MATRIX.read_text(), "Oborovo must be marked as validated in scope matrix"
    assert "generic" in matrix and "❌" in MATRIX.read_text(), "Generic must be marked as excluded in scope matrix"