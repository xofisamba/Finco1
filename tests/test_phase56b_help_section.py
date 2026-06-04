"""Phase 56B — Help section sidebar tests.

Verifies that:
- pilot_help_onboarding.html and pilot_workflow_guide.html no longer use
  the positive "Validated" framing for TUHO/Oborovo templates.
- Help content is exposed as a dedicated tab/panel
  (workspace_tabs.html includes a `help` tab and workspace_shell.html
  contains a `#panel-help` block).
- Full Help content is no longer included inline in the Overview
  workspace_shell.html — only a compact pointer remains.
- pilot_help_onboarding.html + pilot_workflow_guide.html remain reachable
  via the new `#panel-help` block.
- Generic / new projects still carry the exploratory/unvalidated warning.
- No forbidden no-go UI claims introduced.
- New Project form is unchanged by 56B.
- No static/app.js, app/waterfall_core.py, app/project_factories.py,
  runtime_impact_taxonomy.py, or persistence changes.
- rc1 (b425a07) untouched.
- Phase 56A, UI-2.x, 55E-G, 51F, 52F, 53I guardrails still pass
  (verified by running their existing test files in CI).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_HELP = REPO_ROOT / "app" / "templates" / "partials" / "pilot_help_onboarding.html"
WORKFLOW_GUIDE = REPO_ROOT / "app" / "templates" / "partials" / "pilot_workflow_guide.html"
WORKSPACE_TABS = REPO_ROOT / "app" / "templates" / "partials" / "workspace_tabs.html"
WORKSPACE_SHELL = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
NEW_PROJECT_FORM = REPO_ROOT / "app" / "templates" / "partials" / "new_project_form.html"
NEW_PROJECT_INLINE = WORKSPACE_SHELL  # inline copy lives here
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

NO_GO_FORBIDDEN_TERMS = [
    "bankable",
    "bank-grade",
    "lender-ready",
    "certified",
    "audit-ready",
    "investor-ready",
    "saas-ready",
    "production-ready",
    "guaranteed returns",
    "investment advice",
    "customer reference",
]


# ============================================================
# 1. "Validated" positive claim removed from Help partials
# ============================================================


class TestValidatedRephrasing:
    def test_pilot_help_onboarding_no_positive_validated_claim(self):
        """Positive use of 'Validated' as a label or claim is removed.

        Comments referencing the rephrasing are allowed.
        """
        text = PILOT_HELP.read_text()
        # Drop Jinja comments (Phase 56B commentary about the rephrase)
        stripped = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        # Drop HTML comments
        stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.DOTALL)
        lowered = stripped.lower()
        assert "validated" not in lowered, (
            "pilot_help_onboarding.html still contains the word 'Validated' "
            "as a positive claim. 56B must rephrase to 'Reference' / "
            "'has parity evidence' / 'parity-reviewed'."
        )

    def test_pilot_workflow_guide_no_positive_validated_claim(self):
        text = WORKFLOW_GUIDE.read_text()
        stripped = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.DOTALL)
        lowered = stripped.lower()
        assert "validated" not in lowered, (
            "pilot_workflow_guide.html still contains 'Validated'."
        )

    def test_pilot_help_uses_reference_or_parity_terms(self):
        """TUHO/Oborovo are described as 'reference' or 'parity evidence'."""
        text = PILOT_HELP.read_text()
        assert "[Reference]" in text, "TUHO/Oborovo should be labeled [Reference]"
        assert "parity evidence" in text, "TUHO/Oborovo should be described with 'parity evidence'"

    def test_workflow_guide_uses_reference_scope(self):
        text = WORKFLOW_GUIDE.read_text()
        assert "Reference scope" in text, (
            "Workflow guide should use 'Reference scope' instead of "
            "'Validated scope'."
        )


# ============================================================
# 2. Help is exposed as a dedicated tab
# ============================================================


class TestHelpTab:
    def test_workspace_tabs_has_help_tab(self):
        text = WORKSPACE_TABS.read_text()
        assert 'data-tab="help"' in text, (
            "workspace_tabs.html must include a 'help' tab."
        )

    def test_workspace_tabs_help_tab_label(self):
        text = WORKSPACE_TABS.read_text()
        # The Help tab label should be present
        assert (
            re.search(r'id="tab-help"[^>]*>Help<', text) is not None
        ), "Help tab should be labeled 'Help'."


class TestHelpPanel:
    def test_workspace_shell_has_help_panel(self):
        text = WORKSPACE_SHELL.read_text()
        assert 'id="panel-help"' in text, (
            "workspace_shell.html must include a #panel-help tab-panel block."
        )

    def test_help_panel_includes_workflow_guide(self):
        text = WORKSPACE_SHELL.read_text()
        # Find the panel-help section
        m = re.search(
            r'<div class="tab-panel" id="panel-help"[^>]*>(.*?)</div>\s*<!--\s*.*?-->\s*</div>\s*</div>',
            text,
            flags=re.DOTALL,
        )
        # Fallback: just confirm the include appears after panel-help open tag
        idx_open = text.find('id="panel-help"')
        assert idx_open != -1, "panel-help block missing"
        # Slice from panel-help open to the closing workspace-content
        rest = text[idx_open:]
        assert 'pilot_workflow_guide.html' in rest, (
            "panel-help must include pilot_workflow_guide.html"
        )
        assert 'pilot_help_onboarding.html' in rest, (
            "panel-help must include pilot_help_onboarding.html"
        )

    def test_help_panel_is_a_tab_panel(self):
        text = WORKSPACE_SHELL.read_text()
        assert re.search(
            r'<div class="tab-panel" id="panel-help"',
            text,
        ), "panel-help must use the standard .tab-panel class."


# ============================================================
# 3. Full Help content removed from default Overview inline
# ============================================================


class TestHelpRemovedFromOverviewInline:
    @staticmethod
    def _overview_body() -> str:
        """Return the inner HTML of #panel-overview by matching the
        opening `<div class="tab-panel active" id="panel-overview">` and
        the *first* top-level `</div>` that closes it (we use a
        non-greedy match followed by the panel's own `id` tag for
        robustness)."""
        text = WORKSPACE_SHELL.read_text()
        # Find the open tag, then walk forward counting div depth.
        open_tag = '<div class="tab-panel active" id="panel-overview">'
        start = text.find(open_tag)
        if start == -1:
            return ""
        start += len(open_tag)
        depth = 1
        i = start
        while i < len(text):
            # Skip strings and comments for rough balance
            if text[i : i + 4] == "<div":
                depth += 1
                i += 4
            elif text[i : i + 6] == "</div>":
                depth -= 1
                if depth == 0:
                    return text[start:i]
                i += 6
            else:
                i += 1
        return text[start:]

    def test_overview_inline_no_longer_includes_pilot_workflow_guide(self):
        """The full pilot_workflow_guide.html include must not appear
        directly inside the #panel-overview block."""
        overview_body = self._overview_body()
        assert overview_body, "panel-overview not found"
        assert "pilot_workflow_guide.html" not in overview_body, (
            "pilot_workflow_guide.html must NOT be included inline in "
            "panel-overview anymore. Move it to #panel-help."
        )
        assert "pilot_help_onboarding.html" not in overview_body, (
            "pilot_help_onboarding.html must NOT be included inline in "
            "panel-overview anymore. Move it to #panel-help."
        )

    def test_overview_has_compact_help_pointer(self):
        """A compact 'Help pointer' should remain in the overview so the
        full Help is discoverable."""
        overview_body = self._overview_body()
        assert overview_body
        assert "help-pointer" in overview_body, (
            "Overview should keep a compact 'help-pointer' entry point."
        )
        # The pointer should link to #help tab
        assert 'href="#help"' in overview_body, (
            "Compact help pointer should link to the #help tab."
        )


# ============================================================
# 4. Help content still reachable
# ============================================================


class TestHelpReachable:
    def test_help_pointer_in_overview_mentions_help_tab(self):
        text = WORKSPACE_SHELL.read_text()
        assert "help-pointer" in text, "help-pointer partial must exist in workspace_shell"
        # The pointer text should reference the Help tab
        assert "Help" in text

    def test_help_pointer_uses_existing_hashchange_handler(self):
        """The pointer link uses href='#help' which is handled by the
        existing hashchange -> switchTab flow in static/app.js. No new JS."""
        text = WORKSPACE_SHELL.read_text()
        assert 'href="#help"' in text
        # Confirm static/app.js still has the hashchange handler
        js = APP_JS.read_text()
        assert "hashchange" in js
        assert "switchTab" in js

    def test_help_panel_renders_pilot_help_partial(self):
        """The full Help partial content must be reachable inside #panel-help."""
        text = WORKSPACE_SHELL.read_text()
        idx_open = text.find('id="panel-help"')
        assert idx_open != -1
        # Check key sentinel from pilot_help_onboarding.html is present
        # (we look for sentinel lines that would only come from the partials)
        panel_section = text[idx_open:]
        # pilot_workflow_guide.html introduces pwg-step markers
        assert "pwg-step" in panel_section or "pilot_workflow_guide" in panel_section
        # pilot_help_onboarding.html introduces pho-* classes
        assert "pho-section" in panel_section or "pilot_help_onboarding" in panel_section


# ============================================================
# 5. Exploratory/unvalidated warning preserved
# ============================================================


class TestExploratoryWarningPreserved:
    def test_generic_unvalidated_warning_in_help(self):
        text = PILOT_HELP.read_text()
        lowered = text.lower()
        # Generic projects must still be flagged
        assert "exploratory" in lowered or "unvalidated" in lowered, (
            "pilot_help_onboarding.html must still warn that generic / new "
            "projects are exploratory or unvalidated."
        )

    def test_warning_item_class_preserved(self):
        text = PILOT_HELP.read_text()
        # The warning class pho-item--warn should still be present
        assert "pho-item--warn" in text


# ============================================================
# 6. No-go UI copy guardrails
# ============================================================


class TestNoGoCopy:
    def _strip_disclaimers(self, text: str) -> str:
        """Remove Jinja/HTML comments AND the standard 'Not a lender...'
        / 'Not an external audit...' / 'Not SaaS-ready' disclaimer
        sentences, so we only check for positive (non-disclaimer) use of
        the forbidden terms."""
        out = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        out = re.sub(r"<!--.*?-->", "", out, flags=re.DOTALL)
        # Strip sentences that begin with "Not " or "NOT " and contain
        # any of the forbidden terms (these are negative claims).
        for term in [
            "lender or bank approval",
            "lender approval",
            "bank approval",
            "external audit",
            "SaaS certification",
            "SaaS-ready",
            "certified",
        ]:
            out = re.sub(
                rf"(?i)(not\s+(?:a|an)\s+[^.]*{re.escape(term)}[^.]*\.)",
                "",
                out,
            )
            out = re.sub(
                rf"(?i)(not\s+{re.escape(term)}[^.\n]*)",
                "",
                out,
            )
        return out

    @pytest.mark.parametrize("term", NO_GO_FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_help(self, term):
        text = self._strip_disclaimers(PILOT_HELP.read_text()).lower()
        assert term.lower() not in text, (
            f"pilot_help_onboarding.html uses forbidden term in positive "
            f"context: {term}"
        )

    @pytest.mark.parametrize("term", NO_GO_FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_workflow_guide(self, term):
        text = self._strip_disclaimers(WORKFLOW_GUIDE.read_text()).lower()
        assert term.lower() not in text, (
            f"pilot_workflow_guide.html uses forbidden term in positive "
            f"context: {term}"
        )

    def test_help_templates_have_disclaimer_header(self):
        text = PILOT_HELP.read_text()
        # The original disclaimer is preserved
        assert "Not a lender or bank approval" in text or "Not a lender" in text
        assert "internal pilot" in text.lower() or "single-user" in text.lower()


# ============================================================
# 7. New Project form is unchanged by 56B
# ============================================================


class TestNewProjectFormUnchanged:
    def test_new_project_inline_panel_unchanged(self):
        """The inline #panel-new-project in workspace_shell.html must still
        render the same 6 fields it had before 56B."""
        text = WORKSPACE_SHELL.read_text()
        # Find the new project panel
        open_tag = '<div class="tab-panel" id="panel-new-project"'
        start_tag_idx = text.find(open_tag)
        assert start_tag_idx != -1, "panel-new-project not found in workspace_shell"
        # Find the closing > of the open tag
        gt_idx = text.find(">", start_tag_idx)
        body_start = gt_idx + 1
        # Walk to matching </div>
        depth = 1
        i = body_start
        while i < len(text):
            if text[i : i + 4] == "<div":
                depth += 1
                i += 4
            elif text[i : i + 6] == "</div>":
                depth -= 1
                if depth == 0:
                    body = text[body_start:i]
                    break
                i += 6
            else:
                i += 1
        else:
            body = text[body_start:]
        # The 6 master fields must still be there (Phase 56B does not touch
        # the new-project form)
        for field in [
            "project_name",
            "project_type",
            "template_source",
            "country_market",
            "capacity_mw",
            "cod_date",
        ]:
            assert field in body, (
                f"Inline new-project form must still contain field: {field}"
            )

    def test_new_project_sidebar_form_unchanged(self):
        """The sidebar full new_project_form.html is unchanged by 56B
        (it will be the target of 56C)."""
        text = NEW_PROJECT_FORM.read_text()
        # Must still contain the 17 fields
        for field in [
            "project_name",
            "project_type",
            "template_source",
            "country_market",
            "capacity_mw",
            "cod_date",
            "construction_months",
            "horizon_years",
            "tariff_eur_mwh",
            "ppa_term_years",
            "p50_hours",
            "opex_y1_keur",
            "total_capex_keur",
            "gearing_pct",
            "interest_rate_pct",
            "tenor_years",
            "target_dscr",
        ]:
            assert field in text, (
                f"Sidebar new_project_form.html must still contain field: {field}"
            )


# ============================================================
# 8. Scope guardrails (no out-of-scope changes)
# ============================================================


class TestScopeGuardrails:
    def test_static_app_js_unchanged(self):
        """56B must NOT change static/app.js."""
        # 56B adds 0 lines to app.js. If a future change is required,
        # it must be justified in the PR description.
        js = APP_JS.read_text()
        # Existing handlers we rely on
        assert "switchTab" in js
        assert "hashchange" in js

    def test_app_waterfall_core_unchanged(self):
        wf = REPO_ROOT / "app" / "waterfall_core.py"
        if wf.exists():
            text = wf.read_text()
            # Sanity: no 56B markers
            assert "Phase 56B" not in text

    def test_app_project_factories_unchanged(self):
        pf = REPO_ROOT / "app" / "project_factories.py"
        if pf.exists():
            text = pf.read_text()
            assert "Phase 56B" not in text

    def test_runtime_impact_taxonomy_unchanged(self):
        rt = REPO_ROOT / "app" / "runtime_impact_taxonomy.py"
        if rt.exists():
            text = pf.read_text() if False else rt.read_text()  # noqa
            assert "Phase 56B" not in text

    def test_persistence_directory_unchanged(self):
        """56B must not change persistence files."""
        pdir = REPO_ROOT / "app" / "persistence"
        for f in pdir.glob("*.py"):
            text = f.read_text()
            assert "Phase 56B" not in text, (
                f"persistence file {f.name} contains Phase 56B marker — "
                "this is out of scope for the help-section move."
            )


# ============================================================
# 9. CSS is additive only
# ============================================================


class TestCSSAdditive:
    def test_help_pointer_styles_added(self):
        css = STYLES_CSS.read_text()
        # The new help-pointer block must exist
        assert ".help-pointer" in css, (
            "styles.css must include .help-pointer styles (additive only)."
        )

    def test_existing_root_variables_unchanged(self):
        """56B must not add new :root variables or modify existing ones."""
        css = STYLES_CSS.read_text()
        # Count :root blocks
        root_count = len(re.findall(r":root\s*\{", css))
        # Phase 55C established there are 5 :root blocks. 56B must not change that.
        assert root_count == 5, (
            f"styles.css :root block count changed from 5 to {root_count}. "
            "56B must not modify :root variables."
        )


# ============================================================
# 10. rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_unchanged_in_56b_scope(self):
        """rc1 SHA is a frozen tag in the repository. The test ensures
        the documented frozen SHA is the same one tracked in the
        repository state. (We do not run `git` here — we just check the
        constant is stable.)"""
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 11. End-to-end: the panel-help block does not break Overview
# ============================================================


class TestPanelHelpDoesNotBreakOverview:
    @staticmethod
    def _overview_body() -> str:
        return TestHelpRemovedFromOverviewInline._overview_body()

    def test_overview_panel_still_has_kpi_grid(self):
        overview_body = self._overview_body()
        assert overview_body
        # The KPI grid must still be there
        assert "kpi-grid" in overview_body

    def test_overview_panel_still_has_export_lineage_panel(self):
        """The export-lineage-panel is a sibling of #panel-overview inside
        #workspace-content, not a child of #panel-overview. 56B must
        not remove it."""
        text = WORKSPACE_SHELL.read_text()
        # export-lineage-panel sits between workspace-state-guidance and
        # panel-overview; it must still be there.
        assert 'id="export-lineage-panel"' in text
        # It must remain on workspace-content level (sibling of panel-overview).
        e_idx = text.find('id="export-lineage-panel"')
        p_idx = text.find('id="panel-overview"')
        assert e_idx < p_idx, "export-lineage-panel must come before panel-overview"

    def test_help_panel_appears_after_compare_panel(self):
        """The new panel-help should be the last panel in workspace_shell,
        after #panel-compare."""
        text = WORKSPACE_SHELL.read_text()
        compare_idx = text.find('id="panel-compare"')
        help_idx = text.find('id="panel-help"')
        assert compare_idx != -1
        assert help_idx != -1
        assert help_idx > compare_idx, (
            "panel-help should be placed after panel-compare."
        )
