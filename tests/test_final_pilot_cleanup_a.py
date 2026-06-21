"""FINAL-PILOT-CLEANUP-A.

Presentation-text-only remediation closing the remaining must-fix items
from the Big Claude Review before External Friendly Pilot preparation:

1. No `create_default_*` literal text in user-facing templates intended
   for pilot users (e.g. the new-project form prefill hint).
2. No "golden" wording in user-facing templates intended for pilot users.
3. The external pilot guide documents that Generic Solar/Wind defaults
   were recalibrated during the validation program, and that saved
   Generic outputs from before this recalibration may differ from
   current outputs as a result. Plain finance-user language only --
   no internal phase jargon (G1/G2/G3).
4. The pytest-asyncio dependency addition and the refreshed
   project_factories.py guardrail SHA do not weaken the parity-core
   guardrail mechanism itself (the guardrail still fails on an
   unexpected hash change).

No formula, runtime, export-value, or validation-classification changes
are covered or required by these tests -- this is a presentation-text
and CI-hygiene-only check.
"""
from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _strip_jinja_and_html_comments(text: str) -> str:
    text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text

# Templates that are reachable in normal-mode, pilot-facing surfaces.
PILOT_FACING_TEMPLATES = (
    "app/templates/partials/new_project_form.html",
    "app/templates/index.html",
    "app/templates/project_home_page.html",
    "app/templates/project_browse_page.html",
    "app/templates/project_new_page.html",
    "app/templates/partials/project_home.html",
    "app/templates/partials/project_browser.html",
    "app/templates/partials/workspace_shell.html",
    "app/templates/partials/inputs_section.html",
    "app/templates/partials/export_registry.html",
)

PILOT_FACING_DOCS = (
    "docs/external_pilot_guide.md",
)


class TestNoCreateDefaultLiteralInPilotSurfaces:
    def test_new_project_form_no_create_default_literal(self):
        text = _strip_jinja_and_html_comments(
            (REPO_ROOT / "app/templates/partials/new_project_form.html").read_text()
        )
        assert "create_default_" not in text

    def test_no_create_default_literal_in_any_pilot_facing_template(self):
        for relpath in PILOT_FACING_TEMPLATES:
            text = _strip_jinja_and_html_comments((REPO_ROOT / relpath).read_text())
            assert "create_default_" not in text, (
                f"{relpath} must not contain a literal 'create_default_' "
                f"reference visible to pilot users"
            )


class TestNoGoldenWordingInPilotSurfaces:
    def test_no_golden_in_pilot_facing_templates(self):
        for relpath in PILOT_FACING_TEMPLATES:
            text = _strip_jinja_and_html_comments(
                (REPO_ROOT / relpath).read_text()
            ).lower()
            assert "golden" not in text, (
                f"{relpath} must not contain 'golden' in pilot-facing copy"
            )

    def test_no_golden_in_pilot_facing_docs(self):
        for relpath in PILOT_FACING_DOCS:
            text = (REPO_ROOT / relpath).read_text().lower()
            assert "golden" not in text, (
                f"{relpath} must not contain 'golden' in pilot-facing copy"
            )


class TestNoCalibrationWordingInExportRegistry:
    def test_export_registry_card_name_has_no_calibration_wording(self):
        text = _strip_jinja_and_html_comments(
            (REPO_ROOT / "app/templates/partials/export_registry.html").read_text()
        ).lower()
        assert "calibration" not in text, (
            "export_registry.html must not contain 'calibration' in "
            "user-facing export card copy"
        )


class TestPilotGuideRecalibrationNote:
    def _guide_text(self):
        return (REPO_ROOT / "docs/external_pilot_guide.md").read_text()

    def test_guide_mentions_validation_program_recalibration(self):
        text = self._guide_text()
        assert "validation program" in text
        assert "recalibrated" in text
        # Plain finance-user language only -- no internal phase jargon.
        assert "G1" not in text
        assert "G2" not in text
        assert "G3" not in text

    def test_guide_explains_saved_generic_output_drift_is_expected(self):
        text = self._guide_text()
        lowered = text.lower()
        assert "may differ from" in lowered
        assert "reflects validation improvements" in lowered
        assert "does not indicate model instability" in lowered


class TestGuardrailMechanismNotWeakened:
    def test_parity_core_guardrail_still_fails_on_unexpected_hash(self, tmp_path):
        """The guardrail dict must still contain a real SHA-256 entry
        for app/project_factories.py, and that entry must reflect the
        file's *actual* current content (not a wildcard / disabled
        check)."""
        import hashlib
        import re

        guardrail_src = (
            REPO_ROOT
            / "tests/test_phase51f_parallel_work_guardrails.py"
        ).read_text()
        match = re.search(
            r'"app/project_factories\.py":\s*\(\s*(?:#.*\n\s*)*"([0-9a-f]{64})"',
            guardrail_src,
        )
        assert match, "project_factories.py guardrail entry must be a literal SHA-256 hex string"
        expected_sha = match.group(1)
        actual_sha = hashlib.sha256(
            (REPO_ROOT / "app/project_factories.py").read_bytes()
        ).hexdigest()
        assert expected_sha == actual_sha, (
            "Refreshed guardrail SHA must match the current file content "
            "exactly -- this proves the refresh did not weaken the check "
            "(an arbitrary/incorrect hash would still fail this test)."
        )

    def test_pytest_asyncio_declared_in_requirements_and_constraints(self):
        requirements = (REPO_ROOT / "requirements.txt").read_text()
        constraints = (REPO_ROOT / "constraints.txt").read_text()
        assert "pytest-asyncio" in requirements
        assert "pytest-asyncio" in constraints
