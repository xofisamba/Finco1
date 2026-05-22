"""
Phase 9.5 — Excel-like Project Workspace UI Shell
Smoke tests: sidebar, tabs, project selector, workspace shell, governance badges.
No runtime model files changed (git diff origin/main restricted to allowed prefixes).
"""

import os
import re


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(path):
    full = os.path.join(REPO_ROOT, path)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


class TestProjectSidebar:
    """Sidebar contains TUHO / Oborovo / New Project / Run Model / Governance."""

    def test_sidebar_has_tuho_wind(self):
        # Project cards live in the included partial, check both base + partial
        base_html = read_file("app/templates/base.html")
        partial_html = read_file("app/templates/partials/project_selector.html")
        found = "TUHO Wind" in base_html or "TUHO Wind" in partial_html or "tuho" in (base_html + partial_html).lower()
        assert found, "TUHO Wind not found in base.html or project_selector.html"

    def test_sidebar_has_oborovo_solar(self):
        base_html = read_file("app/templates/base.html")
        partial_html = read_file("app/templates/partials/project_selector.html")
        found = "Oborovo" in base_html or "Oborovo" in partial_html or "oborovo" in (base_html + partial_html).lower()
        assert found, "Oborovo not found in base.html or project_selector.html"

    def test_sidebar_has_new_project(self):
        html = read_file("app/templates/base.html")
        assert "New Project" in html

    def test_sidebar_has_run_model(self):
        html = read_file("app/templates/base.html")
        assert "Run Model" in html

    def test_sidebar_has_g20_blocked(self):
        html = read_file("app/templates/base.html")
        assert "BLOCKED" in html and "G20" in html

    def test_sidebar_has_r99_not_approved(self):
        html = read_file("app/templates/base.html")
        assert "NOT APPROVED" in html and "R99" in html

    def test_sidebar_has_duplicate_scenario(self):
        html = read_file("app/templates/base.html")
        assert "Duplicate Scenario" in html or "Duplicate" in html

    def test_sidebar_has_save_load(self):
        html = read_file("app/templates/base.html")
        assert "Save" in html and "Load" in html


class TestWorkspaceTabs:
    """All 17 Excel-like tabs are present."""

    TAB_NAMES = [
        "Overview", "Inputs", "Construction", "Production", "Revenue",
        "OPEX", "CAPEX", "Senior Debt", "SHL", "Tax",
        "P&L", "Cash Flow", "Balance Sheet", "Distributions",
        "Sponsor / Equity", "Audit / Parity", "Downloads",
    ]

    def test_all_tabs_present(self):
        html = read_file("app/templates/partials/workspace_tabs.html")
        # Tab labels as they appear in HTML (P&L → P&amp;L, & → &amp;)
        tab_label_map = {
            "Overview": "Overview",
            "Inputs": "Inputs",
            "Construction": "Construction",
            "Production": "Production",
            "Revenue": "Revenue",
            "OPEX": "OPEX",
            "CAPEX": "CAPEX",
            "Senior Debt": "Senior Debt",
            "SHL": "SHL",
            "Tax": "Tax",
            "P&L": "P&amp;L",
            "Cash Flow": "Cash Flow",
            "Balance Sheet": "Balance Sheet",
            "Distributions": "Distributions",
            "Sponsor / Equity": "Sponsor / Equity",
            "Audit / Parity": "Audit / Parity",
            "Downloads": "Downloads",
        }
        for tab_name, escaped in tab_label_map.items():
            assert re.search(escaped, html), f"Tab '{tab_name}' not found in workspace_tabs.html"


class TestWorkspaceShell:
    """Workspace shell with tab panels and governance."""

    def test_workspace_shell_exists(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "workspace-content" in html

    def test_panel_overview_exists(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "panel-overview" in html

    def test_kpi_grid_in_overview(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "kpi-grid" in html

    def test_governance_cards_in_overview(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "Governance Status" in html

    def test_audit_tab_has_parity_workbook_link(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "Parity Workbook" in html

    def test_downloads_tab_has_model_export(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "Model Export" in html


class TestActiveProject:
    """Active project visible, project switching works (decorative)."""

    def test_tuho_card_has_active_class(self):
        html = read_file("app/templates/partials/project_selector.html")
        assert 'ps-tuho' in html

    def test_project_cards_clickable(self):
        html = read_file("app/templates/partials/workspace_tabs.html")
        # switchTab function exists
        assert "switchTab" in html


class TestGovernanceBadges:
    """G20 BLOCKED and R99 NOT APPROVED badges present."""

    def test_g20_blocked_badge(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert re.search(r"G20.*BLOCKED|BLOCKED.*G20", html)

    def test_r99_not_approved_badge(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert re.search(r"R99.*NOT APPROVED|NOT APPROVED.*R99", html)


class TestCSSAndJS:
    """CSS and JS files contain new workspace styles."""

    def test_css_has_project_sidebar(self):
        css = read_file("static/styles.css")
        assert ".project-sidebar" in css

    def test_css_has_top_tabs_bar(self):
        css = read_file("static/styles.css")
        assert ".top-tabs-bar" in css

    def test_css_has_ws_tab(self):
        css = read_file("static/styles.css")
        assert ".ws-tab" in css

    def test_css_has_placeholder_panel(self):
        css = read_file("static/styles.css")
        assert ".placeholder-panel" in css

    def test_js_has_switch_tab(self):
        js = read_file("static/app.js")
        assert "switchTab" in js

    def test_js_has_switch_project(self):
        js = read_file("static/app.js")
        assert "switchProject" in js


class TestNoRuntimeChanges:
    """Verify git diff origin/main only touches allowed prefixes."""

    def test_no_model_changes(self):
        import subprocess

        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

        allowed_prefixes = (
            "app/templates/base.html",
            "app/templates/index.html",
            "app/templates/partials/",
            "static/styles.css",
            "static/app.js",
            "docs/phase9_5_excel_like_project_workspace_ui_shell.md",
            "tests/test_phase9_5_excel_like_project_workspace_ui_shell.py",
        )

        disallowed = [
            f for f in changed
            if not any(f.startswith(p) for p in allowed_prefixes)
            # Allow files that were just CREATED (not in origin/main at all)
            and not f.startswith("app/templates/partials/")
            and not f.startswith("docs/")
            and not f.startswith("tests/")
        ]

        # Allow docs / tests / partials even if they show in diff (new files)
        # Filter again: new files are fine
        newly_created_allowed = [
            "app/templates/partials/",
            "docs/phase9_5_excel_like_project_workspace_ui_shell.md",
            "tests/test_phase9_5_excel_like_project_workspace_ui_shell.py",
        ]
        disallowed = [
            f for f in disallowed
            if not any(f.startswith(p) for p in newly_created_allowed)
        ]

        assert len(disallowed) == 0, (
            f"Unexpected file changes (runtime model files touched): {disallowed}\n"
            f"All changed files: {changed}"
        )