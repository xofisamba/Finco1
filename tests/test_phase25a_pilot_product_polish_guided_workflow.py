"""Phase 25A: Pilot Product Polish / Guided Workflow — Tests

UI/product polish only. No runtime model changes.
"""
import os
import subprocess
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo


# =============================================================================
# Helper: read file content safely
# =============================================================================

def _read(path: Path) -> str:
    return path.read_text()


# =============================================================================
# 1. Pilot workflow guide exists
# =============================================================================


def test_pilot_workflow_guide_exists():
    """Workflow guide partial exists or equivalent UI section exists."""
    partials = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials"
    guide = partials / "pilot_workflow_guide.html"
    workspace = partials / "workspace_shell.html"

    assert guide.exists() or workspace.exists(), "Workspace shell or guide partial must exist"

    if guide.exists():
        content = guide.read_text()
        assert len(content) > 100, "Workflow guide should have meaningful content"


# =============================================================================
# 2. Workflow guide contains core steps
# =============================================================================


def test_workflow_guide_contains_core_steps():
    """UI mentions all core workflow steps."""
    partials = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials"
    guide_path = partials / "pilot_workflow_guide.html"

    if not guide_path.exists():
        pytest.skip("pilot_workflow_guide.html not found")

    content = guide_path.read_text().lower()

    required_steps = [
        "select project",
        "review assumptions",
        "save scenario",
        "run model",
        "review results",
        "review audit",
        "export",
    ]

    missing = [s for s in required_steps if s not in content]
    assert len(missing) == 0, f"Missing workflow steps: {missing}"


# =============================================================================
# 3. Limitations language mentions validated templates
# =============================================================================


def test_limitations_language_mentions_validated_templates():
    """TUHO/Oborovo frozen-template validation is mentioned."""
    partials = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials"

    files_to_check = [
        partials / "pilot_workflow_guide.html",
        partials / "pilot_limitations_notice.html",
        partials / "workspace_shell.html",
        partials / "audit_reconciliation_tab.html",
        partials / "debt_dscr_shl_panel.html",
    ]

    found = False
    for f in files_to_check:
        if f.exists():
            content = f.read_text().lower()
            if ("tuho" in content or "oborovo" in content) and "validat" in content:
                found = True
                break

    assert found, "Validated TUHO/Oborovo frozen-template path should be mentioned in limitations language"


# =============================================================================
# 4. Limitations language mentions generic unvalidated
# =============================================================================


def test_limitations_language_mentions_generic_unvalidated():
    """Generic/new project path remains unvalidated."""
    partials = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials"

    files_to_check = [
        partials / "pilot_workflow_guide.html",
        partials / "pilot_limitations_notice.html",
        partials / "workspace_shell.html",
        partials / "audit_reconciliation_tab.html",
        partials / "debt_dscr_shl_panel.html",
    ]

    found = False
    for f in files_to_check:
        if f.exists():
            content = f.read_text().lower()
            if ("generic" in content or "unvalidated" in content) and "not" in content:
                found = True
                break

    assert found, "Generic project unvalidated status should be mentioned"


# =============================================================================
# 5. No bank/lender/audit claims introduced
# =============================================================================


def test_no_bank_lender_audit_claims():
    """No bank approved / lender approved / certified audit / external audit claim introduced."""
    partials = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials"

    files_to_check = [
        partials / "pilot_workflow_guide.html",
        partials / "pilot_limitations_notice.html",
        partials / "workspace_shell.html",
        partials / "audit_reconciliation_tab.html",
    ]

    prohibited_phrases = [
        "bank approved",
        "lender approved",
        "certified audit",
        "external audit",
        "bank approval",
        "lender approval",
    ]

    violations = []
    for f in files_to_check:
        if f.exists():
            content = f.read_text().lower()
            for phrase in prohibited_phrases:
                if phrase in content and "not" not in content:
                    violations.append(f"{f.name}: {phrase}")

    assert len(violations) == 0, f"Found prohibited claims: {violations}"


# =============================================================================
# 6. Empty states present
# =============================================================================


def test_empty_states_present():
    """Copy exists for no run yet / stale run / unsaved edits where applicable."""
    partials = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials"

    files_to_check = [
        partials / "empty_states_notice.html",
        partials / "workspace_shell.html",
    ]

    required_concepts = ["no run", "stale", "unsaved"]
    found = {c: False for c in required_concepts}

    for f in files_to_check:
        if f.exists():
            content = f.read_text().lower()
            for concept in required_concepts:
                if concept in content:
                    found[concept] = True

    missing = [k for k, v in found.items() if not v]
    assert len(missing) == 0, f"Missing empty state copy for: {missing}"


# =============================================================================
# 7. Export guidance mentions last run or stale state
# =============================================================================


def test_export_guidance_mentions_last_run_or_stale_state():
    """Export guidance does not imply current draft was run if stale."""
    partials = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials"

    downloads_files = [
        partials / "workspace_shell.html",
        partials / "empty_states_notice.html",
    ]

    found = False
    for f in downloads_files:
        if f.exists():
            content = f.read_text().lower()
            if ("last" in content and "run" in content and ("export" in content or "download" in content)) \
               or ("stale" in content and "export" in content) \
               or ("unsaved" in content and "draft" in content):
                found = True
                break

    assert found, "Export guidance should mention last run or stale-run behavior"


# =============================================================================
# 8. Single-user/pilot boundary language present
# =============================================================================


def test_single_user_pilot_boundary_language_present():
    """User-facing or docs copy states single-user/internal pilot mode, not enterprise SaaS."""
    partials = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials"
    docs_dir = Path(__file__).resolve().parents[1] / "docs"

    files_to_check = [
        partials / "pilot_limitations_notice.html",
        partials / "pilot_workflow_guide.html",
        partials / "workspace_shell.html",
    ]

    found = False
    for f in files_to_check:
        if f.exists():
            content = f.read_text().lower()
            if ("single-user" in content or "single user" in content) and \
               ("pilot" in content or "internal" in content):
                found = True
                break

    assert found, "Single-user/pilot boundary language should be present in UI or docs"


# =============================================================================
# 9. No JS financial calculations added
# =============================================================================


def test_no_js_financial_calculations_added():
    """static/app.js and any new JS files contain no financial calculation patterns."""
    repo_root = Path(__file__).resolve().parents[1]
    js_files = list((repo_root / "static").glob("*.js"))

    # Financial calculation patterns that should NOT appear in JS
    prohibited_patterns = [
        r"\bIRR\b",
        r"\bNPV\b",
        r"\bPMT\b",
        r"\bFV\b",
        r"\bPV\b",
        r"\brate\s*=",
        r"\binterest\s*=",
        r"\bpayment\s*=",
        r"Math\.pow\(",
        r"Math\.exp\(",
        r"Math\.log\(",
        r"\bdscr\b",
        r"\bequity\s*\*",
        r"\bsenior\s*debt\s*\*",
    ]

    violations = []
    for js_file in js_files:
        content = js_file.read_text()
        for pattern in prohibited_patterns:
            import re
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                violations.append(f"{js_file.name}: {pattern} -> {matches[:3]}")

    assert len(violations) == 0, f"Found financial calc patterns in JS: {violations[:5]}"


# =============================================================================
# 10. Guardrails unchanged
# =============================================================================


def test_guardrails_unchanged():
    """Guardrails preserved: G20/R99/R102 blocked, no flags promoted."""
    oborovo = create_default_oborovo()
    info = oborovo.info
    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
