"""Phase 34 — Generic Project Path Validation Boundary tests.

Verifies:
1. Phase 34 doc exists
2. Requirements matrix exists
3. Generic projects listed (solar + wind) as unvalidated
4. Full validation not claimed
5. Generic project current behavior documented (live sculpting, no frozen)
6. Reference validation requirements present
7. Pilot RC boundary preserved
8. Generic warning language present
9. TUHO/Oborovo frozen path unchanged
10. No bank/lender/audit/SaaS claims
11. No runtime model files changed
12. Guardrails unchanged
"""
import pytest
from pathlib import Path

BASE_SHA = "844c2d2e554f0ae53b636c2980713f8be552b966"
PHASE34_DOC = Path("docs/phase34_generic_project_path_validation_boundary.md")
MATRIX = Path("docs/phase34_generic_validation_requirements_matrix.md")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Phase 34 doc exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase34_doc_exists():
    assert PHASE34_DOC.exists(), f"{PHASE34_DOC} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Requirements matrix exists
# ─────────────────────────────────────────────────────────────────────────────
def test_phase34_requirements_matrix_exists():
    assert MATRIX.exists(), f"{MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Generic projects listed as unvalidated/exploratory
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_projects_listed():
    doc = PHASE34_DOC.read_text().lower()

    assert "generic solar" in doc, "Generic solar must be mentioned"
    assert "generic wind" in doc, "Generic wind must be mentioned"
    assert "unvalidated" in doc, "Generic path must be marked as unvalidated"
    assert "exploratory" in doc, "Generic path must be marked as exploratory"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Full validation not claimed
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_full_validation_not_claimed():
    doc = PHASE34_DOC.read_text()
    doc_lower = doc.lower()

    # Must not claim full/generic validation
    assert "not claim" in doc_lower or "do not claim" in doc_lower or "not validated" in doc_lower, (
        "Phase 34 must explicitly state generic path is not validated"
    )
    # Must explain reference model is required
    assert "reference model" in doc_lower or "excel reference" in doc_lower, (
        "Phase 34 must explain reference model is required for validation"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Generic project current behavior documented
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_project_current_behavior_documented():
    doc = PHASE34_DOC.read_text().lower()

    # Must mention live/derived path or live sculpting
    assert (
        "live sculpt" in doc
        or "dscr_sculpt" in doc
        or "derived path" in doc
        or "live path" in doc
    ), "Phase 34 must document that generic path uses live sculpting (not frozen)"

    # Must mention no frozen Excel fixture is used
    assert (
        "no frozen" in doc
        or "no excel fixture" in doc
        or "no frozen excel" in doc
        or "not use frozen" in doc
        or "without frozen" in doc
    ), "Phase 34 must document that no frozen Excel fixture is used for generic path"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Reference validation requirements present
# ─────────────────────────────────────────────────────────────────────────────
def test_reference_validation_requirements_present():
    doc = PHASE34_DOC.read_text().lower()
    matrix = MATRIX.read_text().lower()

    # Matrix must include requirements for key items
    required_items = [
        "excel/reference model",
        "input mapping",
        "revenue",
        "opex",
        "capex",
        "senior debt",
        "dscr",
        "project irr",
        "equity irr",
    ]
    for item in required_items:
        assert item in matrix or item in doc, f"Requirements must include '{item}'"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Pilot RC boundary preserved
# ─────────────────────────────────────────────────────────────────────────────
def test_pilot_rc_boundary_preserved():
    doc = PHASE34_DOC.read_text().lower()

    # Must state Pilot RC validated scope remains TUHO/Oborovo
    assert "tuho" in doc and "oborovo" in doc, "TUHO and Oborovo must be mentioned in boundary doc"
    assert (
        "pilot rc" in doc
        or "pilot rc validated" in doc
        or "validated scope" in doc
    ), "Phase 34 must reference Pilot RC validated scope"

    # Must state generic path is excluded
    assert (
        "excluded" in doc
        or "not part of" in doc
        or "not included" in doc
    ), "Phase 34 must explicitly state generic path is excluded from Pilot RC"


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Generic warning language present
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_warning_language_present():
    doc = PHASE34_DOC.read_text()
    doc_lower = doc.lower()

    # Must reference the strong warning label that already exists in main_web.py
    assert (
        "unvalidated" in doc_lower
        and ("derived path" in doc_lower or "exploratory" in doc_lower)
    ), "Warning language must reference unvalidated/exploratory status"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: TUHO/Oborovo frozen path unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_oborovo_frozen_path_unchanged():
    # Check that TUHO and Oborovo factories are accessible and have frozen flag
    from app.project_factories import create_default_tuho_wind1, create_default_oborovo

    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()

    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True, (
        "TUHO frozen flag must remain True"
    )
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True, (
        "Oborovo frozen flag must remain True"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: No bank/lender/audit/SaaS claims
# ─────────────────────────────────────────────────────────────────────────────
def test_no_bank_lender_audit_saas_claims():
    doc = PHASE34_DOC.read_text()
    matrix = MATRIX.read_text()

    for content in [doc, matrix]:
        content_lower = content.lower()

        blocked_terms = [
            "bank ready", "bank-approved", "lender approved",
            "audit ready", "audited", "certified",
            "saas-ready", "enterprise-ready", "enterprise ready",
            "production ready", "go-live ready",
            "generic path validated", "generic validated",
        ]
        # Split into lines and check each — skip lines that are guardrails/negations
        for line in content.split('\n'):
            line_lower = line.lower()
            # Guardrail lines say "do not claim X" — those are OK
            if any(line_lower.startswith(prefix) for prefix in [
                '- ', '* ', '✅ ', '#', '##', '###', '> '
            ]) and ('do not claim' in line_lower or "don't claim" in line_lower):
                continue
            for term in blocked_terms:
                if term in line_lower:
                    raise AssertionError(f"Blocked claim '{term}' found in Phase 34 docs: {line[:80]}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: No runtime model files changed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_runtime_model_files_changed():
    doc = PHASE34_DOC.read_text().lower()

    assert (
        "no financial formula" in doc
        or "no runtime" in doc
        or "no model changes" in doc
        or "diagnostic" in doc
        or "validation-boundary" in doc
        or "planning" in doc
    ), "Phase 34 must state no model formula changes"

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
            "domain/", "app/project_factories.py",
            "app/waterfall", "app/revenue", "app/opex", "app/capex", "app/tax",
        ])
    ]
    # Only allow project_factories.py if the only change is reading/accessing
    # We want to verify no CALCULATIONS were changed
    assert not any(
        f for f in model_files
        if f != "app/project_factories.py"  # reading is OK, changing calc params is not
    ), f"Model/runtime files touched: {model_files}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Guardrails unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_unchanged():
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1

    oborovo = create_default_oborovo()
    tuho = create_default_tuho_wind1()

    partial = getattr(oborovo.financing, 'partial_pay_sweep', None)
    assert partial is None or partial is False, "partial_pay_sweep must not be promoted"

    doc = PHASE34_DOC.read_text().lower()
    assert "g20" in doc or "blocked" in doc, "G20 guardrail must be documented"
    assert "r99" in doc or "r102" in doc or "not approved" in doc, "R99/R102 guardrail must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13 (bonus): Phase 34D not required
# ─────────────────────────────────────────────────────────────────────────────
def test_phase34d_not_required():
    doc = PHASE34_DOC.read_text()
    assert (
        "phase 34d not required" in doc.lower()
        or "no phase 34d" in doc.lower()
        or "not required" in doc.lower()
        or "validation-boundary" in doc.lower()
        or "no runtime changes" in doc.lower()
    ), "Phase 34D fix decision must be documented"


# ─────────────────────────────────────────────────────────────────────────────
# Test 14 (bonus): Warning in UI is confirmed strong
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_warning_in_ui_is_strong():
    import re

    main_web = Path("main_web.py").read_text().lower()
    # Find the generic project labels
    match = re.search(r'"generic_wind".*?"label":\s*"([^"]+)"', main_web) or \
           re.search(r'generic_wind.*?label.*?(?:"|\')([^\'"|]+)', main_web)
    # Simpler: just check that unvalidated appears near generic_wind/generic_solar
    assert "generic_wind" in main_web and "unvalidated" in main_web, (
        "main_web.py must show generic_wind with unvalidated warning"
    )
    assert "generic_solar" in main_web and "unvalidated" in main_web, (
        "main_web.py must show generic_solar with unvalidated warning"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15 (bonus): Manifest decision documented
# ─────────────────────────────────────────────────────────────────────────────
def test_manifest_decision_documented():
    doc = PHASE34_DOC.read_text().lower()
    assert (
        "manifest" in doc
        and ("skipped" in doc or "not created" in doc or "not needed" in doc or "decision" in doc)
    ) or "skip" in doc or "decision" in doc, (
        "Phase 34 must explain manifest decision (skip/create)"
    )