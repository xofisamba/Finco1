"""Phase 39 - External Model Review Package tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "phase39_external_model_review_package.md"
CHECKLIST = ROOT / "docs" / "model_reviewer_run_checklist.md"
ISSUE_LOG = ROOT / "docs" / "model_reviewer_issue_log_template.md"
MANIFEST = ROOT / "docs" / "model_reviewer_package_manifest.md"
JSON_MANIFEST = ROOT / "reports" / "phase39_model_reviewer_package_manifest.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _combined_text() -> str:
    parts = [_read(DOC), _read(CHECKLIST), _read(ISSUE_LOG), _read(MANIFEST)]
    if JSON_MANIFEST.exists():
        parts.append(_read(JSON_MANIFEST))
    return "\n".join(parts).lower()


def test_phase39_doc_exists():
    assert DOC.exists()


def test_model_reviewer_run_checklist_exists():
    assert CHECKLIST.exists()


def test_model_reviewer_issue_log_template_exists():
    assert ISSUE_LOG.exists()


def test_model_reviewer_package_manifest_exists():
    assert MANIFEST.exists()


def test_validated_scope_is_limited_to_tuho_oborovo():
    text = _combined_text()
    assert "tuho" in text
    assert "oborovo" in text
    assert "validated review scope" in text or "validated pilot scope" in text
    assert "generic solar / wind remain exploratory and unvalidated" in text or (
        "generic" in text and "unvalidated" in text and "exploratory" in text
    )


def test_anchor_checks_present():
    text = _combined_text()
    required = [
        "tuho senior debt",
        "tuho co2 y1",
        "oborovo senior debt",
        "oborovo shl opening",
        "oborovo opex y1",
        "distribution lock-up",
        "first valid distribution",
    ]
    for item in required:
        assert item in text


def test_non_claims_are_explicit():
    text = _combined_text()
    required = [
        "not a bank approval",
        "not a lender approval",
        "not a certified audit",
        "not a certification",
        "not saas-ready",
        "not enterprise-ready",
    ]
    for item in required:
        assert item in text
    assert "not multi-tenant ready" in text or "not a multi-tenant readiness claim" in text


def test_issue_log_has_required_columns():
    text = _read(ISSUE_LOG)
    required = [
        "Issue ID",
        "Reviewer",
        "Date",
        "Area",
        "Project",
        "Observation",
        "Severity",
        "Evidence/source",
        "Status",
    ]
    for item in required:
        assert item in text


def test_reviewer_manifest_has_required_documents():
    text = _read(MANIFEST).lower()
    required = [
        "validation_pack_executive_summary.md",
        "validation_pack_index.md",
        "external_reviewer_checklist.md",
        "pilot_rc_scope_matrix.md",
        "phase38_audit_output_trust_surface_polish.md",
    ]
    for item in required:
        assert item in text


def test_json_manifest_if_present_is_valid():
    if JSON_MANIFEST.exists():
        data = json.loads(_read(JSON_MANIFEST))
        assert data["main_sha"] == "ae08938e80b3b16055c842cb86689e7e70cbfaec"
        assert "TUHO" in data["validated_projects"]
        assert "Oborovo" in data["validated_projects"]
        assert any("generic" in item.lower() for item in data["excluded_scopes"])
    else:
        assert "manifest decision" in _read(DOC).lower() and "skipped" in _read(DOC).lower()


def test_no_runtime_model_files_changed_or_claimed():
    text = _read(DOC).lower()
    assert "no financial formula changes" in text
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
        or path.startswith("app/project_factories")
        or path.endswith(".csv")
    ]
    assert not disallowed, f"Unexpected runtime/model/fixture changes: {disallowed}"


def test_no_js_financial_calculations_added():
    js_path = ROOT / "static" / "app.js"
    js_text = _read(js_path).lower() if js_path.exists() else ""
    for token in ["npv(", "irr(", "calculate irr", "calculate npv"]:
        assert token not in js_text


def test_guardrails_unchanged():
    text = _combined_text()
    assert "g20 remains blocked" in text
    assert "r99/r102 remain not approved" in text
    assert "partial_pay_sweep" in text and "not promoted" in text
    assert "flat/min dscr sculpting" in text and "not promoted" in text
    assert "backend remains source of truth" in text
