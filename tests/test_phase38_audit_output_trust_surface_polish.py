"""Phase 38 - Audit Output Enhancement / Trust-Surface Polish tests."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "phase38_audit_output_trust_surface_polish.md"
MATRIX = ROOT / "docs" / "phase38_audit_output_trust_surface_matrix.md"

TARGET_FILES = [
    ROOT / "app" / "templates" / "partials" / "audit_reconciliation_tab.html",
    ROOT / "app" / "templates" / "partials" / "validation.html",
    ROOT / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html",
    ROOT / "app" / "templates" / "partials" / "runtime_summary.html",
    ROOT / "app" / "templates" / "partials" / "pilot_limitations_notice.html",
    ROOT / "app" / "templates" / "partials" / "pilot_help_onboarding.html",
    ROOT / "app" / "templates" / "partials" / "workspace_shell.html",
    ROOT / "app" / "templates" / "partials" / "scenario_version_history.html",
    ROOT / "app" / "templates" / "index.html",
    ROOT / "docs" / "pilot_user_guide.md",
    ROOT / "docs" / "pilot_ux_walkthrough_checklist.md",
    ROOT / "docs" / "phase37_pilot_ux_walkthrough_friction_audit.md",
    ROOT / "docs" / "phase37_pilot_ux_friction_matrix.md",
    ROOT / "docs" / "pilot_rc_scope_matrix.md",
    ROOT / "docs" / "validation_pack_executive_summary.md",
    ROOT / "docs" / "validation_pack_index.md",
    ROOT / "docs" / "external_reviewer_checklist.md",
]

MOJIBAKE_MARKERS = ["â", "ðŸ", "Â"]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _combined_text() -> str:
    parts = [_read(DOC), _read(MATRIX)]
    for path in TARGET_FILES:
        if path.exists():
            parts.append(_read(path))
    return "\n".join(parts).lower()


def test_phase38_doc_exists():
    assert DOC.exists()


def test_phase38_matrix_exists():
    assert MATRIX.exists()


def test_audit_surface_separates_validated_and_unvalidated_language():
    text = _combined_text()
    assert "validated pilot evidence" in text
    assert "tuho" in text and "oborovo" in text
    assert "pending / unvalidated / future scope" in text
    assert "generic" in text and ("unvalidated" in text or "exploratory" in text)


def test_audit_reconciliation_non_claims_present():
    text = _combined_text()
    assert "internal review tooling" in text or "internal review" in text
    assert "not an external model audit" in text or "not external audit" in text
    assert "not a bank approval" in text or "bank approval" in text
    assert "not a lender approval" in text or "lender approval" in text


def test_export_artifact_purpose_language_present():
    text = _combined_text()
    for phrase in [
        "values-only excel",
        "runtime summary csv",
        "institutional workbook",
        "parity workbook",
        "gap register",
        "source map",
    ]:
        assert phrase in text
    for purpose in [
        "reviewer handoff",
        "machine-readable snapshot",
        "reviewer-facing workbook",
        "validated frozen-template parity evidence",
        "open gaps",
        "provenance",
    ]:
        assert purpose in text


def test_last_clean_backend_run_export_warning_present():
    text = _combined_text()
    assert "last clean backend run" in text
    assert "not unsaved draft edits" in text or "not browser-side draft edits" in text


def test_generic_boundary_remains_strong():
    text = _combined_text()
    assert "generic solar" in text or "generic wind" in text or "generic projects" in text
    assert "exploratory" in text or "unvalidated" in text
    assert "excluded from trusted pilot conclusions" in text


def test_no_runtime_model_files_changed_or_claimed():
    text = _read(DOC).lower()
    assert "no formula changes" in text
    assert "no runtime/model changes" in text or "no runtime calculations" in text

    diff = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    changed = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    disallowed = [
        path
        for path in changed
        if path.startswith("domain/")
        or path.startswith("app/api/")
        or path.startswith("app/project_factories/")
        or path.endswith(".csv")
    ]
    assert not disallowed, f"Unexpected runtime/model/fixture changes: {disallowed}"


def test_no_js_financial_calculations_added():
    js_text = ""
    js_path = ROOT / "static" / "app.js"
    if js_path.exists():
        js_text = _read(js_path).lower()
    for token in ["npv(", "irr(", "calculate irr", "calculate npv"]:
        assert token not in js_text


def test_no_bank_lender_audit_saas_claims():
    text = _combined_text()
    disallowed_positive_patterns = [
        r"\bis bank-approved\b",
        r"\bis lender-approved\b",
        r"\bis approved for lenders\b",
        r"\bis approved for banks\b",
        r"\bis certified for external audit\b",
        r"\bis saas-ready\b",
        r"\bis enterprise-ready\b",
        r"\bis multi-tenant ready\b",
    ]
    for pattern in disallowed_positive_patterns:
        assert re.search(pattern, text) is None
    for non_claim in [
        "not a bank approval",
        "not a lender approval",
        "not saas-ready",
    ]:
        assert non_claim in text
    assert any(
        phrase in text
        for phrase in [
            "not an external model audit",
            "not external audit",
            "not a certified external audit",
            "not a certified audit",
            "not claimed",
        ]
    )


def test_guardrails_unchanged():
    text = _combined_text()
    assert "g20 remains blocked" in text
    assert "r99/r102 remain not approved" in text
    assert "partial_pay_sweep" in text and "not promoted" in text
    assert "flat/min dscr sculpting" in text and "not promoted" in text
    assert "backend remains source of truth" in text


def test_no_trust_surface_mojibake_markers():
    for path in TARGET_FILES + [DOC, MATRIX]:
        text = _read(path)
        for marker in MOJIBAKE_MARKERS:
            assert marker not in text, f"Found mojibake marker {marker!r} in {path}"
