"""Phase 37 — Pilot UX Walkthrough / Friction Audit tests."""

from __future__ import annotations

import subprocess
from pathlib import Path


BASE_SHA = "a46e117f48f4c37c5f600f4828c42763540f139c"
ROOT = Path(__file__).resolve().parent.parent
WALKTHROUGH = ROOT / "docs" / "phase37_pilot_ux_walkthrough_friction_audit.md"
MATRIX = ROOT / "docs" / "phase37_pilot_ux_friction_matrix.md"
CHECKLIST = ROOT / "docs" / "pilot_ux_walkthrough_checklist.md"

PILOT_COPY_FILES = [
    ROOT / "app" / "templates" / "index.html",
    ROOT / "app" / "templates" / "partials" / "pilot_workflow_guide.html",
    ROOT / "app" / "templates" / "partials" / "pilot_help_onboarding.html",
    ROOT / "app" / "templates" / "partials" / "pilot_limitations_notice.html",
    ROOT / "app" / "templates" / "partials" / "scenario_version_history.html",
    ROOT / "app" / "templates" / "partials" / "workspace_shell.html",
    ROOT / "docs" / "pilot_user_guide.md",
]

MOJIBAKE_MARKERS = ["â", "ðŸ", "Â"]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase37_walkthrough_doc_exists():
    assert WALKTHROUGH.exists(), f"{WALKTHROUGH} not found"


def test_phase37_friction_matrix_exists():
    assert MATRIX.exists(), f"{MATRIX} not found"


def test_pilot_ux_walkthrough_checklist_exists():
    assert CHECKLIST.exists(), f"{CHECKLIST} not found"


def test_walkthrough_covers_full_pilot_flow():
    text = (_read(WALKTHROUGH) + "\n" + _read(CHECKLIST)).lower()
    required = [
        "project selection",
        "review assumptions",
        "save scenario",
        "run model",
        "validation",
        "audit / parity",
        "export",
        "stale",
        "generic",
    ]
    for item in required:
        assert item in text, f"Missing pilot walkthrough coverage for: {item}"


def test_validated_and_generic_boundary_included():
    text = (_read(WALKTHROUGH) + "\n" + _read(MATRIX) + "\n" + _read(CHECKLIST)).lower()
    assert "tuho" in text and "validated" in text
    assert "oborovo" in text and "validated" in text
    assert "generic" in text and ("unvalidated" in text or "exploratory" in text)


def test_draft_saved_runtime_distinction_included():
    text = (_read(WALKTHROUGH) + "\n" + _read(MATRIX) + "\n" + _read(CHECKLIST)).lower()
    for item in ["draft", "saved", "runtime", "stale"]:
        assert item in text, f"Missing distinction keyword: {item}"


def test_friction_matrix_has_severity_and_blocker_columns():
    matrix = _read(MATRIX)
    assert "Severity" in matrix
    assert "Trusted pilot blocker?" in matrix


def test_no_major_ui_redesign_claimed():
    text = _read(WALKTHROUGH).lower()
    assert "does not implement a broad ui redesign" in text
    assert "shared lineitemgrid" in text
    assert "deferred" in text


def test_no_bank_lender_audit_saas_claims():
    text = (_read(WALKTHROUGH) + "\n" + _read(MATRIX) + "\n" + _read(CHECKLIST)).lower()
    required_non_claims = [
        "not lender-ready",
        "not bank-approved",
        "not externally audited",
        "not externally audited or certified",
        "not saas-ready",
        "not enterprise-ready",
    ]
    assert any(item in text for item in required_non_claims)


def test_no_runtime_model_files_changed_or_claimed():
    text = _read(WALKTHROUGH).lower()
    assert "no financial formula changes" in text
    assert "no runtime calculation changes" in text
    assert "no model output changes" in text

    # Best-effort git diff assertion when the base commit exists locally.
    has_base = subprocess.run(
        ["git", "cat-file", "-e", f"{BASE_SHA}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if has_base.returncode == 0:
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{BASE_SHA}..HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        changed = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
        disallowed = [
            path for path in changed
            if path.endswith(".csv")
            or path.startswith("domain/")
            or path.startswith("app/project_factories")
            or path.startswith("app/waterfall")
        ]
        assert not disallowed, f"Unexpected runtime/model/fixture changes: {disallowed}"


def test_guardrails_unchanged():
    text = (_read(WALKTHROUGH) + "\n" + _read(CHECKLIST)).lower()
    assert "g20 remains blocked" in text
    assert "r99/r102 remain not approved" in text
    assert "partial_pay_sweep" in text and "not promoted" in text
    assert "dscr sculpting" in text and "not promoted" in text
    assert "backend remains source of truth" in text


def test_copy_only_files_do_not_contain_known_mojibake_markers():
    for path in PILOT_COPY_FILES:
        text = _read(path)
        for marker in MOJIBAKE_MARKERS:
            assert marker not in text, f"Found mojibake marker {marker!r} in {path}"

