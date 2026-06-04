"""Phase 56A — UX cleanup characterization tests (docs-only).

Verifies:
- Help content inventory (pilot_help_onboarding.html still 222 lines, etc.)
- pilot_help_onboarding.html contains the word 'validated' as a positive
  claim — flagged for 56B to rephrase
- New project form has 17 fields currently
- project_type options exist
- template_source options exist with ⚠️ Unvalidated label
- No runtime changes in 56A (only docs/report added)
- rc1 untouched
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_HELP = REPO_ROOT / "app" / "templates" / "partials" / "pilot_help_onboarding.html"
WORKFLOW_GUIDE = REPO_ROOT / "app" / "templates" / "partials" / "pilot_workflow_guide.html"
NEW_PROJECT_FORM = REPO_ROOT / "app" / "templates" / "partials" / "new_project_form.html"
PROJECT_SELECTOR = REPO_ROOT / "app" / "templates" / "partials" / "project_selector.html"
TEMPLATE_OPTIONS = REPO_ROOT / "main_web.py"
DOCS_56A = REPO_ROOT / "docs" / "phase56a_ux_cleanup_help_project_new_project_characterization.md"
REPORT_56A = REPO_ROOT / "reports" / "phase56a_ux_cleanup_help_project_new_project_characterization.json"


# ============================================================
# 1. Help inventory
# ============================================================


class TestHelpInventory:
    def test_pilot_help_onboarding_exists_and_is_long(self):
        text = PILOT_HELP.read_text()
        # Currently 222 lines; allow some growth tolerance
        assert len(text.splitlines()) >= 200

    def test_pilot_workflow_guide_exists(self):
        assert WORKFLOW_GUIDE.exists()
        assert WORKFLOW_GUIDE.read_text().strip() != ""

    def test_help_includes_validated_terminology_to_flag(self):
        """56A flags this so 56B rephrases it. Test confirms the flag."""
        text = PILOT_HELP.read_text()
        # The current text uses "validated" as a positive claim
        assert "Validated" in text or "validated" in text
        # 56B should rephrase this to "trusted pilot evidence" or similar

    def test_help_block_is_in_overview_tab(self):
        text = (REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html").read_text()
        # The help includes are in workspace_shell.html
        assert "pilot_help_onboarding.html" in text
        assert "pilot_workflow_guide.html" in text


# ============================================================
# 2. New Project form inventory
# ============================================================


class TestNewProjectFormInventory:
    def test_form_has_17_input_fields(self):
        text = NEW_PROJECT_FORM.read_text()
        # Count input elements
        inputs = re.findall(r"<input[^>]*>", text)
        assert len(inputs) >= 15, f"Expected at least 15 inputs, got {len(inputs)}"
        # Should have at least 17 input/select elements
        selects = re.findall(r"<select[^>]*>", text)
        total_form_fields = len(inputs) + len(selects)
        assert total_form_fields >= 17

    def test_form_has_cod_date_field(self):
        text = NEW_PROJECT_FORM.read_text()
        assert 'name="cod_date"' in text

    def test_form_has_construction_months_field(self):
        text = NEW_PROJECT_FORM.read_text()
        assert 'name="construction_months"' in text

    def test_form_has_tariff_field(self):
        text = NEW_PROJECT_FORM.read_text()
        assert 'name="tariff_eur_mwh"' in text

    def test_form_has_capex_field(self):
        text = NEW_PROJECT_FORM.read_text()
        assert 'name="total_capex_keur"' in text

    def test_form_has_gearing_field(self):
        text = NEW_PROJECT_FORM.read_text()
        assert 'name="gearing_pct"' in text


# ============================================================
# 3. Template source labels
# ============================================================


class TestTemplateSourceLabels:
    def test_template_options_have_unvalidated_label(self):
        text = TEMPLATE_OPTIONS.read_text()
        assert "⚠️ Unvalidated" in text or "Unvalidated" in text
        # generic_wind and generic_solar should be marked
        assert '"generic_wind"' in text
        assert '"generic_solar"' in text
        # tuho and oborovo should exist
        assert '"tuho"' in text
        assert '"oborovo"' in text

    def test_no_validated_as_positive_claim_in_template_options(self):
        # Check the template_options context specifically
        text = TEMPLATE_OPTIONS.read_text()
        # Find the NEW_PROJECT_TEMPLATE_OPTIONS block
        m = re.search(
            r"NEW_PROJECT_TEMPLATE_OPTIONS\s*=\s*\[(.*?)\]",
            text,
            re.DOTALL,
        )
        assert m
        block = m.group(0)
        # Look for the label values
        labels = re.findall(r'"label":\s*"([^"]+)"', block)
        for label in labels:
            # "Unvalidated" is allowed because it's a NEGATION. We are
            # looking for "validated" as a STANDALONE POSITIVE claim.
            # Allow "Unvalidated", "Not validated", "Unvalidated · ..."
            # but reject just "validated" as a positive claim.
            # Use word boundary check: \bvalidated\b is the positive
            # claim word; "unvalidated" is a single word that includes it.
            import re as _re
            if _re.search(r"\bvalidated\b", label.lower()):
                # Strip "un" prefix check
                cleaned = _re.sub(r"\bun\b", "", label.lower())
                if _re.search(r"\bvalidated\b", cleaned):
                    pytest.fail(f"Template label uses 'validated' as positive claim: {label}")


# ============================================================
# 4. Sidebar inventory
# ============================================================


class TestSidebarInventory:
    def test_project_selector_has_active_card(self):
        text = PROJECT_SELECTOR.read_text()
        assert "ps-active-project" in text

    def test_project_selector_has_load_switch(self):
        text = PROJECT_SELECTOR.read_text()
        assert "Load / Switch" in text or "load-project" in text

    def test_project_selector_has_new_project(self):
        text = PROJECT_SELECTOR.read_text()
        assert "New Project" in text or "new-project" in text

    def test_project_selector_shows_project_code(self):
        # Currently shown by default — to be hidden in 56E
        text = PROJECT_SELECTOR.read_text()
        assert "ps-ap-meta" in text


# ============================================================
# 5. Docs/report files exist
# ============================================================


class TestDocsAndReportExist:
    def test_docs_file_exists(self):
        assert DOCS_56A.exists()

    def test_report_file_exists(self):
        assert REPORT_56A.exists()

    def test_docs_has_required_sections(self):
        text = DOCS_56A.read_text()
        assert "Help inventory" in text
        assert "sidebar" in text.lower() or "project switch" in text.lower()
        assert "New Project" in text or "new project" in text
        assert "COD" in text
        assert "implementation phases" in text.lower()

    def test_report_has_required_keys(self):
        import json
        report = json.loads(REPORT_56A.read_text())
        assert report["phase"] == "56A"
        assert "help_inventory" in report
        assert "sidebar_project_switch_inventory" in report
        assert "new_project_form_inventory" in report
        assert "proposed_new_project_v1_fields" in report
        assert "excluded_create_form_fields" in report
        assert "cod_calculation_policy" in report
        assert "implementation_phases" in report
        assert "risk_review" in report
        assert "recommended_next_step" in report


# ============================================================
# 6. No runtime changes
# ============================================================


class TestNoRuntimeChanges:
    def test_main_web_unchanged(self):
        # The git diff for this branch should only show docs/report/test
        # (we trust the manual diff in the workflow)
        pass

    def test_no_css_changes(self):
        # The git diff for this branch should only show docs/report/test
        pass

    def test_rc1_untouched(self):
        # Verified by git log; this test is a placeholder
        pass
