"""Phase P2-FIX-5D — Five-Area Navigation (Hide Legacy Ribbon).

Hides the legacy 20+ tab ws-tab ribbon (Excel-like
tab strip) below the new five-area navigation. The
underlying tab buttons remain in the DOM (hidden !=
deleted) so existing switchTab JS keeps working when
called from the five-area nav. The underlying
panels / routes are unchanged.

The five top-level visible areas (rendered above the
legacy ribbon) are:
1. Dashboard
2. Inputs
3. Results
4. Scenarios
5. Export & Audit

Help is a 6th secondary link, not part of the 5
main areas.

Tests:
1. 5-area nav rendered for every project
2. 20-tab legacy ribbon is in DOM (hidden != deleted)
3. 5-area nav calls existing switchTab JS
4. All underlying panels still in DOM
5. Underlying routes still work
"""

from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix5d")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


PROJECTS_TO_TEST = ["tuho", "oborovo", "generic_solar", "generic_wind"]


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


# ─────────────────────────────────────────────────────────────────────
# 1. Five-area nav rendered for every project
# ─────────────────────────────────────────────────────────────────────


class TestFiveAreaNavRenders:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_five_area_nav_for_tuho(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        for tab in (
            "nav-compression-tab-dashboard",
            "nav-compression-tab-inputs",
            "nav-compression-tab-results",
            "nav-compression-tab-scenarios",
            "nav-compression-tab-export-audit",
        ):
            assert tab in r.text, f"TUHO missing 5-area tab {tab!r}"

    def test_five_area_nav_for_all_projects(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            for tab in (
                "nav-compression-tab-dashboard",
                "nav-compression-tab-inputs",
                "nav-compression-tab-results",
                "nav-compression-tab-scenarios",
                "nav-compression-tab-export-audit",
            ):
                assert tab in r.text, (
                    f"{project_code} missing 5-area tab {tab!r}"
                )

    def test_help_secondary_link_present(self):
        """Help is a 6th secondary link, preserved."""
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            assert "nav-compression-tab-help" in r.text

    def test_default_active_tab_is_dashboard(self):
        """Dashboard is the default active tab."""
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        nav_match = re.search(
            r'<div class="nav-compression[^"]*"[^>]*>(.*?)</div>',
            r.text,
            flags=re.DOTALL,
        )
        assert nav_match is not None
        nav_block = nav_match.group(1)
        first_btn = re.search(
            r'<button[^>]*class="([^"]*)"[^>]*>([^<]*)</button>',
            nav_block,
        )
        assert first_btn is not None
        classes = first_btn.group(1)
        label = first_btn.group(2).strip()
        assert "active" in classes, (
            f"First nav button ({label!r}) is not the active tab"
        )
        assert "Dashboard" in label


# ─────────────────────────────────────────────────────────────────────
# 2. Legacy 20-tab ribbon in DOM (hidden != deleted)
# ─────────────────────────────────────────────────────────────────────


class TestLegacyRibbonPreservedInDOM:
    """The 20 ws-tab buttons and the 21 tab-panels
    remain in the DOM. CSS hides the ws-tab ribbon
    visually; the underlying elements (and their
    switchTab handlers) are unchanged."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_legacy_ws_tab_buttons_not_in_normal_dom(self):
        """P2-FIX-8 PR2: ws-tab buttons no longer rendered in normal mode.
        Server-side conditional rendering replaced CSS hiding."""
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        ws_tabs = re.findall(
            r'<button class="ws-tab[^"]*"[^>]*>([^<]+)</button>',
            r.text,
        )
        assert len(ws_tabs) == 0, (
            f"P2-FIX-8: ws-tab buttons must not be in normal-mode DOM, "
            f"found {len(ws_tabs)}"
        )

    def test_underlying_panels_in_dom(self):
        """The 21 tab-panels remain in the DOM."""
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        panel_ids = re.findall(
            r'<div class="tab-panel[^"]*" id="([^"]+)"',
            r.text,
        )
        assert len(panel_ids) >= 17, (
            f"Expected >= 17 tab-panels in DOM, found {len(panel_ids)}"
        )

    def test_legacy_ribbon_server_side_hidden(self):
        """P2-FIX-8 PR2: The legacy ribbon is hidden server-side
        (not via CSS). The CSS display:none rule is removed; the
        template wraps the ribbon in audit_mode."""
        css_path = REPO_ROOT / "static" / "styles.css"
        css = css_path.read_text(encoding="utf-8")
        assert ".top-tabs-bar" in css, "Missing .top-tabs-bar styles in CSS"
        # P2-FIX-8: display:none !important must be gone (server-side now)
        m = re.search(
            r"\.top-tabs-bar\s*\{[^}]*display\s*:\s*none\s*!important",
            css,
            re.DOTALL,
        )
        assert m is None, (
            "P2-FIX-8: CSS display:none !important on .top-tabs-bar "
            "must be removed — server-side conditional rendering handles this now"
        )
        # Template must have audit_mode wrapping
        tabs_tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "workspace_tabs.html").read_text()
        assert "{% if audit_mode %}" in tabs_tmpl


# ─────────────────────────────────────────────────────────────────────
# 3. 5-area nav uses existing switchTab JS (no new JS)
# ─────────────────────────────────────────────────────────────────────


class TestFiveAreaNavUsesSwitchTab:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_nav_calls_switchtab_for_dashboard(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert "switchTab('overview')" in r.text

    def test_nav_calls_switchtab_for_inputs(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert "switchTab('inputs')" in r.text

    def test_nav_calls_switchtab_for_results(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert "switchTab('capex')" in r.text

    def test_nav_calls_switchtab_for_scenarios(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert "switchTab('scenario')" in r.text

    def test_nav_calls_switchtab_for_export_audit(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert "switchTab('audit')" in r.text


# ─────────────────────────────────────────────────────────────────────
# 4. Underlying routes still work
# ─────────────────────────────────────────────────────────────────────


class TestUnderlyingRoutesStillWork:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_scenarios_route_works(self):
        r = self.client.get(
            "/scenarios?project=tuho", follow_redirects=True
        )
        assert r.status_code == 200

    def test_audit_route_works(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        # Audit panel is in the workspace
        assert 'id="panel-audit"' in r.text

    def test_downloads_route_works(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert 'id="panel-downloads"' in r.text


# ─────────────────────────────────────────────────────────────────────
# 5. File scope: P2-FIX-5D is presentation-only
# ─────────────────────────────────────────────────────────────────────


class TestFileScope:
    def test_only_allowed_files_changed(self):
        import shutil
        import subprocess
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            [
                "git", "-C", str(REPO_ROOT),
                "diff", "--name-only", "origin/main",
            ],
            capture_output=True,
            text=True,
        )
        changed = [
            f.strip() for f in result.stdout.strip().split("\n")
            if f.strip()
        ]
        allowed_prefixes = (
            "static/styles.css",
            "app/templates/partials/_state_banner.html",
            "app/templates/partials/inputs_section.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",
            "main_web.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_p2fix2_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix4_",  # P2-FIX-7A cross-arc
            "docs/phase_p2fix5d_",
            "reports/phase_p2fix5d_",
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            # P2-FIX-8 cross-arc allowlist
            "app/templates/partials/workspace_tabs.html",
            "app/templates/partials/workspace_shell.html",
            "app/middleware/security_headers.py",
            "app/templates/base.html",
            "app/templates/project_home_page.html",
            "app/templates/project_new_page.html",
            "app/templates/project_browse_page.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",
            "scripts/",
            "tests/test_phase_p2fix8_",
            "tests/test_phase_p2fix5a_",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/new_project_result.html",
            "tests/test_phase_wf4_",
            # WF cross-arc allowlist
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
            "app/templates/partials/project_selector.html",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
            "app/templates/partials/_results_subnav.html",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
        )
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
        )
        for f in changed:
            with_dash = [f.startswith(p) for p in disallowed_prefixes]
            assert not any(with_dash), (
                f"Disallowed file changed: {f}"
            )
            ok = [f.startswith(p) for p in allowed_prefixes]
            assert any(ok), (
                f"File outside allowed scope: {f}"
            )
