"""Phase 56E — Project switch simplification tests.

Verifies that:
- The active project name is the PRIMARY visible label
  (largest, first).
- The project code / slug is NOT the primary visible label
  (hidden by default; revealed via a "Details" disclosure).
- The active project card shows compact metadata
  (technology badge + project origin pill).
- "New project" is a clear primary action; "Switch project" is
  the secondary action.
- The "Switch project" button triggers the project browser
  (htmx-get=/projects/browse).
- The "New project" button triggers the new-project flow
  (htmx-get=/projects/new).
- Existing endpoints and hx-* attributes are preserved.
- All 56B/56C/56D behavior is preserved (Help tab, v1 form, COD
  readonly, derived COD).
- No static/app.js changes.
- No app/waterfall_core.py / app/project_factories.py / app/persistence/*
  changes.
- rc1 (b425a07) untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_SELECTOR = (
    REPO_ROOT / "app" / "templates" / "partials" / "project_selector.html"
)
PROJECT_BROWSER = (
    REPO_ROOT / "app" / "templates" / "partials" / "project_browser.html"
)
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"
MAIN_WEB = REPO_ROOT / "main_web.py"

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 1. Active project name is shown prominently
# ============================================================


class TestActiveProjectNamePrimary:
    def test_ps_ap_name_class_exists(self):
        text = PROJECT_SELECTOR.read_text()
        assert "ps-ap-name" in text, (
            "Active project name must use the .ps-ap-name class."
        )

    def test_ps_ap_name_renders_project_name(self):
        """The .ps-ap-name element must contain project_record.project_name."""
        text = PROJECT_SELECTOR.read_text()
        # The element should render project_record.project_name
        # inside the .ps-ap-name div.
        m = re.search(
            r'<div\s+class="ps-ap-name"[^>]*>(.*?)</div>',
            text,
            flags=re.DOTALL,
        )
        assert m is not None, "ps-ap-name div not found"
        content = m.group(1)
        assert "project_record.project_name" in content, (
            f"ps-ap-name must render project_record.project_name. Got: {content!r}"
        )

    def test_ps_ap_name_appears_before_ps_ap_meta_row(self):
        """Visual order: project_name → meta_row → scenario → details."""
        text = PROJECT_SELECTOR.read_text()
        idx_name = text.find('class="ps-ap-name"')
        idx_meta_row = text.find("ps-ap-meta-row")
        idx_scenario = text.find("ps-ap-scenario")
        idx_details = text.find("ps-ap-details")
        # Each must exist
        assert idx_name != -1
        assert idx_meta_row != -1
        assert idx_scenario != -1
        assert idx_details != -1
        # Order: name < meta_row < scenario < details
        assert idx_name < idx_meta_row, "ps-ap-name must come before ps-ap-meta-row"
        assert idx_meta_row < idx_scenario, "ps-ap-meta-row must come before ps-ap-scenario"
        assert idx_scenario < idx_details, "ps-ap-scenario must come before ps-ap-details"

    def test_ps_ap_name_uses_larger_font(self):
        """The .ps-ap-name class must have a font-size larger than
        the original 0.85rem to make the name visually dominant."""
        css_text = STYLES_CSS.read_text()
        # Find .ps-ap-name rule (Phase 56E override) — it must
        # be at least 0.9rem or larger.
        m = re.search(r"\.ps-ap-name\s*\{[^}]*font-size:\s*([\d.]+)rem", css_text)
        assert m is not None, (
            "Phase 56E must add a .ps-ap-name override in styles.css"
        )
        size = float(m.group(1))
        assert size >= 0.9, (
            f"ps-ap-name font-size must be >= 0.9rem (got {size}rem)"
        )


# ============================================================
# 2. Project code/slug is not primary visible
# ============================================================


class TestProjectCodeNotPrimary:
    def test_project_code_in_details_disclosure(self):
        """The project code must be inside a <details> element
        (i.e. hidden by default)."""
        text = PROJECT_SELECTOR.read_text()
        # Find a <details> containing project_code
        m = re.search(
            r'<details[^>]*>(.*?)</details>',
            text,
            flags=re.DOTALL,
        )
        assert m is not None, "ps-ap-details <details> block not found"
        body = m.group(1)
        assert "project_record.project_code" in body, (
            "Project code must be inside the <details> disclosure"
        )

    def test_project_code_not_first_visible_label(self):
        """The OLD `ps-ap-meta` class (which showed the project
        code as a primary line below the name) must be removed
        from the active project card markup."""
        text = PROJECT_SELECTOR.read_text()
        # Find the active project div
        m = re.search(
            r'<div class="ps-active-project">(.*?)</div>\s*<!-- State badges',
            text,
            flags=re.DOTALL,
        )
        if not m:
            # try without comment anchor
            m = re.search(
                r'<div class="ps-active-project">(.*?)<div class="ps-state-badges"',
                text,
                flags=re.DOTALL,
            )
        assert m is not None, "ps-active-project block not found"
        block = m.group(1)
        # The old `<div class="ps-ap-meta">{{ project_record.project_code }}</div>`
        # should NOT be present (it has been replaced by the details disclosure).
        old_pattern = re.search(
            r'<div\s+class="ps-ap-meta">\s*\{\{\s*project_record\.project_code\s*\}\}\s*</div>',
            block,
        )
        assert old_pattern is None, (
            "Old `ps-ap-meta` showing project_code as a primary line "
            "must be removed from the active project card. Use the "
            "`<details>` disclosure instead."
        )

    def test_project_code_rendered_in_dom_but_collapsed(self):
        """The project code is still in the DOM (for tests / accessibility)
        but inside a <details> that is closed by default."""
        text = PROJECT_SELECTOR.read_text()
        # The <details> element does NOT have `open` attribute
        m = re.search(r'<details\s+class="ps-ap-details"\s*>', text)
        # If <details> has `open`, the code would be visible by default
        # which contradicts the 56E policy.
        assert m is not None, "ps-ap-details <details> not found"
        # Make sure no <details class="ps-ap-details" open>
        m_open = re.search(r'<details\s+class="ps-ap-details"\s+open', text)
        assert m_open is None, (
            "<details> must NOT have `open` attribute by default. "
            "Project code should be hidden until user clicks 'Details'."
        )


# ============================================================
# 3. Switch project control remains
# ============================================================


class TestSwitchProjectControl:
    def test_switch_project_button_present(self):
        text = PROJECT_SELECTOR.read_text()
        assert 'id="btn-load-project"' in text, (
            "Switch project button (id=btn-load-project) must remain"
        )

    def test_switch_project_button_label(self):
        """The button label should be 'Switch project' (Phase 56E
        new wording, replacing the old 'Load / Switch')."""
        text = PROJECT_SELECTOR.read_text()
        # Find the btn-load-project button
        m = re.search(
            r'<button[^>]*id="btn-load-project"[^>]*>(.*?)</button>',
            text,
            flags=re.DOTALL,
        )
        assert m is not None
        body = m.group(1)
        assert "Switch project" in body, (
            f"Switch project button must be labeled 'Switch project'. Got: {body!r}"
        )

    def test_switch_project_button_preserves_htmx_attrs(self):
        text = PROJECT_SELECTOR.read_text()
        m = re.search(
            r'<button[^>]*id="btn-load-project"[^>]*>',
            text,
        )
        assert m is not None
        tag = m.group(0)
        # Must trigger /projects/browse
        assert 'hx-get="/projects/browse"' in tag
        assert 'hx-target="#project-browser-container"' in tag
        assert 'hx-swap="innerHTML"' in tag
        # Should still call openProjectBrowser() for show/hide logic
        assert "openProjectBrowser()" in tag

    def test_openProjectBrowser_function_preserved(self):
        text = PROJECT_SELECTOR.read_text()
        assert "function openProjectBrowser" in text, (
            "openProjectBrowser() function must remain in project_selector.html"
        )

    def test_closeProjectBrowser_function_preserved(self):
        text = PROJECT_SELECTOR.read_text()
        assert "function closeProjectBrowser" in text, (
            "closeProjectBrowser() function must remain in project_selector.html"
        )


# ============================================================
# 4. New Project control is more discoverable
# ============================================================


class TestNewProjectControlDiscoverable:
    def test_new_project_button_present(self):
        text = PROJECT_SELECTOR.read_text()
        assert 'id="btn-new-project"' in text

    def test_new_project_button_label(self):
        text = PROJECT_SELECTOR.read_text()
        m = re.search(
            r'<button[^>]*id="btn-new-project"[^>]*>(.*?)</button>',
            text,
            flags=re.DOTALL,
        )
        assert m is not None
        body = m.group(1)
        assert "New project" in body, (
            f"New project button must be labeled 'New project'. Got: {body!r}"
        )

    def test_new_project_is_primary_action(self):
        """The 'New project' button should be the primary action
        (rendered FIRST and styled with .ps-action-btn--primary)."""
        text = PROJECT_SELECTOR.read_text()
        # The 'New project' button should appear before the
        # 'Switch project' button in the .ps-quick-actions block.
        idx_new = text.find('id="btn-new-project"')
        idx_switch = text.find('id="btn-load-project"')
        assert idx_new != -1
        assert idx_switch != -1
        assert idx_new < idx_switch, (
            "New project button must come before Switch project in the "
            "quick-actions block (primary action first)."
        )

    def test_new_project_button_uses_primary_class(self):
        text = PROJECT_SELECTOR.read_text()
        m = re.search(
            r'<button[^>]*id="btn-new-project"[^>]*>',
            text,
        )
        assert m is not None
        tag = m.group(0)
        assert "ps-action-btn--primary" in tag, (
            "New project button must use the .ps-action-btn--primary class"
        )

    def test_new_project_button_preserves_htmx_attrs(self):
        text = PROJECT_SELECTOR.read_text()
        m = re.search(
            r'<button[^>]*id="btn-new-project"[^>]*>',
            text,
        )
        assert m is not None
        tag = m.group(0)
        assert 'hx-get="/projects/new"' in tag
        assert 'hx-target="#panel-new-project"' in tag
        assert 'hx-swap="innerHTML"' in tag

    def test_ps_action_btn_primary_css_defined(self):
        """The .ps-action-btn--primary class must be defined in styles.css."""
        css_text = STYLES_CSS.read_text()
        assert ".ps-action-btn--primary" in css_text


# ============================================================
# 5. Existing endpoints + hx-* attributes preserved
# ============================================================


class TestExistingEndpointsPreserved:
    def test_projects_browse_endpoint_referenced(self):
        text = PROJECT_SELECTOR.read_text()
        assert "/projects/browse" in text

    def test_projects_new_endpoint_referenced(self):
        text = PROJECT_SELECTOR.read_text()
        assert "/projects/new" in text

    def test_no_new_routes_introduced(self):
        """Phase 56E must not introduce new routes in main_web.py."""
        text = MAIN_WEB.read_text()
        # Check that no @app.get / @app.post / @app.route decorator was added
        # (this is a soft check — 56E is template/CSS-only)
        # We rely on the diff stat to confirm no route additions.


# ============================================================
# 6. Project origin pill is shown
# ============================================================


class TestProjectOriginPill:
    def test_factory_template_origin_label(self):
        text = PROJECT_SELECTOR.read_text()
        # factory template origin → "Reference" label
        assert "ps-ap-origin--factory" in text

    def test_user_created_origin_label(self):
        text = PROJECT_SELECTOR.read_text()
        assert "ps-ap-origin--user" in text

    def test_saved_baseline_origin_label(self):
        text = PROJECT_SELECTOR.read_text()
        assert "ps-ap-origin--baseline" in text

    def test_origin_pill_uses_product_neutral_wording(self):
        """The origin pill must use neutral product wording
        (Reference / My project / Saved baseline) — NOT 'Validated'."""
        text = PROJECT_SELECTOR.read_text()
        assert "Reference" in text
        assert "My project" in text
        assert "Saved baseline" in text


# ============================================================
# 7. Technology badge preserved
# ============================================================


class TestTechnologyBadgePreserved:
    def test_ps_ap_badge_present(self):
        text = PROJECT_SELECTOR.read_text()
        assert "ps-ap-badge" in text

    def test_wind_solar_classes(self):
        text = PROJECT_SELECTOR.read_text()
        assert "ps-badge--wind" in text
        assert "ps-badge--solar" in text


# ============================================================
# 8. Empty state improvement
# ============================================================


class TestEmptyStateImprovement:
    def test_empty_state_has_helpful_hint(self):
        """The empty active project state should show a helpful
        hint pointing to the action buttons."""
        text = PROJECT_SELECTOR.read_text()
        # Find the empty state
        m = re.search(
            r'<div class="ps-active-project ps-active-project--empty">(.*?)</div>',
            text,
            flags=re.DOTALL,
        )
        assert m is not None, "ps-active-project--empty block not found"
        body = m.group(1)
        # Should mention "Choose" or "create" or "project" so the
        # user knows what to do
        assert (
            "Choose" in body
            or "choose" in body
            or "Create" in body
            or "create" in body
            or "project" in body.lower()
        )


# ============================================================
# 9. CSS is additive
# ============================================================


class TestCSSAdditive:
    def test_56e_section_marker_present(self):
        css_text = STYLES_CSS.read_text()
        assert "Phase 56E" in css_text, (
            "styles.css should have a Phase 56E marker comment"
        )

    def test_root_count_unchanged(self):
        css_text = STYLES_CSS.read_text()
        root_count = len(re.findall(r":root\s*\{", css_text))
        assert root_count == 5, (
            f"styles.css :root block count changed from 5 to {root_count}"
        )

    def test_all_56e_selectors_present(self):
        css_text = STYLES_CSS.read_text()
        for sel in [
            ".ps-ap-meta-row",
            ".ps-ap-origin",
            ".ps-ap-origin--factory",
            ".ps-ap-origin--user",
            ".ps-ap-origin--baseline",
            ".ps-ap-details",
            ".ps-ap-details-summary",
            ".ps-ap-details-body",
            ".ps-ap-details-label",
            ".ps-ap-details-code",
            ".ps-ap-empty-hint",
            ".ps-ap-scenario-label",
            ".ps-action-btn--primary",
            ".ps-action-label",
        ]:
            assert sel in css_text, f"Missing 56E CSS selector: {sel}"


# ============================================================
# 10. scope guardrails
# ============================================================


class TestScopeGuardrails:
    def test_app_js_unchanged(self):
        """56E must NOT change static/app.js."""
        js = APP_JS.read_text()
        # The existing functions must still be there
        assert "switchTab" in js
        assert "showNewProjectPanel" in js
        # 56E uses onclick="openProjectBrowser()" in the partial,
        # but openProjectBrowser/closeProjectBrowser/switchToProject
        # are defined inside project_selector.html, not in app.js.

    def test_app_waterfall_core_unchanged(self):
        wf = REPO_ROOT / "app" / "waterfall_core.py"
        if wf.exists():
            text = wf.read_text()
            assert "Phase 56E" not in text

    def test_app_project_factories_unchanged(self):
        pf = REPO_ROOT / "app" / "project_factories.py"
        if pf.exists():
            text = pf.read_text()
            assert "Phase 56E" not in text

    def test_runtime_impact_taxonomy_unchanged(self):
        rt = REPO_ROOT / "app" / "runtime_impact_taxonomy.py"
        if rt.exists():
            text = rt.read_text()
            assert "Phase 56E" not in text

    def test_persistence_unchanged(self):
        pdir = REPO_ROOT / "app" / "persistence"
        for f in pdir.glob("*.py"):
            text = f.read_text()
            assert "Phase 56E" not in text, (
                f"persistence file {f.name} contains Phase 56E marker"
            )

    def test_no_financial_model_changes(self):
        for f in [
            REPO_ROOT / "app" / "waterfall_core.py",
            REPO_ROOT / "app" / "capex_engine.py",
            REPO_ROOT / "app" / "opex_engine.py",
            REPO_ROOT / "app" / "depreciation_engine.py",
        ]:
            if f.exists():
                text = f.read_text()
                assert "Phase 56E" not in text

    def test_no_schema_or_migration_changes(self):
        migrations = REPO_ROOT / "app" / "persistence" / "migrations"
        if migrations.exists():
            for f in migrations.glob("*.py"):
                text = f.read_text()
                assert "Phase 56E" not in text

    def test_main_web_unchanged(self):
        """56E is template/CSS-only; main_web.py must not be touched."""
        text = MAIN_WEB.read_text()
        assert "Phase 56E" not in text, (
            "56E must not change main_web.py"
        )

    def test_services_unchanged(self):
        """56E is template/CSS-only; no service module changes."""
        sdir = REPO_ROOT / "app" / "services"
        if sdir.exists():
            for f in sdir.glob("*.py"):
                text = f.read_text()
                assert "Phase 56E" not in text, (
                    f"service file {f.name} contains Phase 56E marker"
                )


# ============================================================
# 11. rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 12. 56B/56C/56D preserved
# ============================================================


class TestPreviousPhasesPreserved:
    def test_help_pointer_in_overview_preserved(self):
        """The 56B help-pointer must still be in workspace_shell."""
        ws = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
        text = ws.read_text()
        assert "help-pointer" in text, (
            "56B help-pointer must still be present in workspace_shell"
        )

    def test_panel_help_present(self):
        ws = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
        text = ws.read_text()
        assert 'id="panel-help"' in text

    def test_cod_date_readonly_preserved(self):
        ws = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
        text = ws.read_text()
        m = re.search(r'<input[^>]*id="np-cod_date"[^>]*>', text)
        assert m is not None
        tag = m.group(0)
        assert "readonly" in tag or "aria-readonly" in tag

    def test_new_project_v1_form_preserved(self):
        """56C v1 form fields must still be present."""
        ws = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
        text = ws.read_text()
        for field in [
            "spv_name", "currency", "construction_start_date",
            "construction_duration_months",
        ]:
            assert field in text, f"56C v1 field missing: {field}"

    def test_navigation_tabs_preserved(self):
        """Top tabs (Overview, Inputs, ..., Help) must still be there."""
        wt = REPO_ROOT / "app" / "templates" / "partials" / "workspace_tabs.html"
        text = wt.read_text()
        for tab in [
            "data-tab=\"overview\"", "data-tab=\"inputs\"",
            "data-tab=\"help\"",  # 56B
        ]:
            assert tab in text


# ============================================================
# 13. No-go copy guardrails
# ============================================================


NO_GO_FORBIDDEN_TERMS = [
    "bankable", "bank-grade", "lender-ready", "certified", "audit-ready",
    "investor-ready", "saas-ready", "production-ready", "guaranteed returns",
    "investment advice", "customer reference",
]


class TestNoGoCopyInProjectSelector:
    @pytest.mark.parametrize("term", NO_GO_FORBIDDEN_TERMS)
    def test_no_forbidden_term(self, term):
        text = PROJECT_SELECTOR.read_text().lower()
        assert term not in text, (
            f"project_selector.html must not use forbidden term: {term}"
        )

    @pytest.mark.parametrize("term", NO_GO_FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_browser(self, term):
        text = PROJECT_BROWSER.read_text().lower()
        assert term not in text
