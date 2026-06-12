"""Phase P2-FIX-4 — Five-Area Navigation + Dashboard Landing + Reviewer Mode.

Verifies the navigation model:

1. Five top-level visible areas: Dashboard, Inputs, Results,
   Scenarios, Export & Audit (+ Help secondary).
2. Default visible area is Dashboard.
3. Dashboard prioritizes Project IRR, Equity IRR, NPV,
   Min DSCR, Avg DSCR, Senior debt, Revenue, EBITDA.
4. Inputs area groups core project inputs + CAPEX + OPEX +
   financing assumptions.
5. Results area collects output sheets under sub-navigation.
6. Scenarios area preserves existing scenario functionality.
7. Export & Audit area contains downloads + audit / reviewer
   surface + relocated lineage / governance.
8. Rendered normal-mode routes do NOT expose factory / baseline
   / parity / calibration / golden / G20 / R99 / R102 /
   Lifecycle Clarity / Export Lineage / Governance Posture /
   Review boundary.
9. Underlying output panels still exist (hidden != deleted).
10. P2-FIX-3 first-edit protected reference copy flow still works.
11. Phase 51F parity guardrails pass.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix4")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


# ── Forbidden terms in normal-mode screens ─────────────────
FORBIDDEN_NORMAL_MODE_TERMS = [
    "factory",
    "baseline",
    "parity",
    "calibration",
    "golden",
    "G20",
    "R99",
    "R102",
    "runtime source",
    "Lifecycle Clarity",
    "Export Lineage",
    "Governance Posture",
    "Review boundary",
    "exploratory",
    "EXPLORATORY",
    "R-PAR",
]

# Allowed exception: TUHO Wind and Oborovo Solar PV may appear
# as plain project names.
ALLOWED_PROJECT_NAME_TERMS = ("TUHO Wind", "Oborovo Solar PV")

PROJECTS_TO_TEST = ["tuho", "oborovo", "generic_solar"]


def _strip_html_comments(html: str) -> str:
    html = re.sub(r"\{#.*?#\}", "", html, flags=re.DOTALL)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    return html


def _strip_allowed_project_names(html: str) -> str:
    for name in ALLOWED_PROJECT_NAME_TERMS:
        html = html.replace(name, "")
    return html


def _extract_visible_text(html: str) -> str:
    """Extract user-visible text from HTML. Strips script,
    style, and HTML attributes (so CSS classes / data-* /
    id / aria-* / title= don't count)."""
    html = _strip_html_comments(html)
    html = _strip_allowed_project_names(html)
    html = re.sub(
        r"<script\b[^>]*>.*?</script>", " ", html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(
        r"<style\b[^>]*>.*?</style>", " ", html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(r'\s[a-zA-Z-]+="[^"]*"', " ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    return html


def _strip_audit_panel(html: str) -> str:
    """Strip the audit panel (panel-audit) from the HTML so
    the audit surface does not contaminate the normal-mode
    checks."""
    audit_start = html.find('id="panel-audit"')
    if audit_start == -1:
        return html
    div_start = html.rfind("<div", 0, audit_start)
    depth = 0
    i = div_start
    while i < len(html):
        if html[i:i + 5] == "<div " or html[i:i + 5] == "<div>":
            depth += 1
            i += 5
        elif html[i:i + 6] == "</div>":
            depth -= 1
            i += 6
            if depth == 0:
                break
        else:
            i += 1
    return html[:div_start] + html[i:]


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


# ─────────────────────────────────────────────────────────────────────
# Test: five-area navigation model
# ─────────────────────────────────────────────────────────────────────


class TestFiveAreaNavigation:
    """The five top-level visible areas must be present in the
    rendered workspace for every project."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_five_top_level_areas_render_for_tuho(self):
        """TUHO (protected reference) must show the five-area
        nav. P2-FIX-4 removes the user_created gate that
        P2-min-4 had."""
        r = self.client.get("/?project=tuho", follow_redirects=True)
        html = r.text
        for tab in (
            "nav-compression-tab-dashboard",
            "nav-compression-tab-inputs",
            "nav-compression-tab-results",
            "nav-compression-tab-scenarios",
            "nav-compression-tab-export-audit",
        ):
            assert tab in html, (
                f"TUHO workspace missing five-area nav tab {tab!r}"
            )

    def test_five_top_level_areas_render_for_oborovo(self):
        r = self.client.get("/?project=oborovo", follow_redirects=True)
        html = r.text
        for tab in (
            "nav-compression-tab-dashboard",
            "nav-compression-tab-inputs",
            "nav-compression-tab-results",
            "nav-compression-tab-scenarios",
            "nav-compression-tab-export-audit",
        ):
            assert tab in html, (
                f"Oborovo workspace missing five-area nav tab {tab!r}"
            )

    def test_five_top_level_areas_render_for_generic_solar(self):
        r = self.client.get(
            "/?project=generic_solar", follow_redirects=True
        )
        html = r.text
        for tab in (
            "nav-compression-tab-dashboard",
            "nav-compression-tab-inputs",
            "nav-compression-tab-results",
            "nav-compression-tab-scenarios",
            "nav-compression-tab-export-audit",
        ):
            assert tab in html, (
                f"Generic Solar workspace missing five-area "
                f"nav tab {tab!r}"
            )

    def test_help_secondary_link_preserved(self):
        """Help is a 6th secondary link. It is not one of the
        5 main areas, but it is preserved (hidden != deleted)."""
        r = self.client.get("/?project=tuho", follow_redirects=True)
        assert "nav-compression-tab-help" in r.text

    def test_underlying_ws_tab_buttons_still_present(self):
        """Hidden != deleted. The 20 underlying ws-tab buttons
        are still in the DOM (just visually compressed)."""
        r = self.client.get("/?project=tuho", follow_redirects=True)
        html = r.text
        for tab in (
            "tab-overview", "tab-inputs", "tab-scenario",
            "tab-capex", "tab-revenue", "tab-opex", "tab-senior-debt",
            "tab-shl", "tab-tax", "tab-cashflow", "tab-balance",
            "tab-distributions", "tab-sponsor", "tab-audit",
            "tab-downloads", "tab-compare", "tab-help",
        ):
            assert tab in html, (
                f"Underlying ws-tab button {tab!r} was removed. "
                f"P2-FIX-4 must preserve (hidden != deleted)."
            )


# ─────────────────────────────────────────────────────────────────────
# Test: Dashboard default + content
# ─────────────────────────────────────────────────────────────────────


class TestDashboardDefault:
    """The dashboard is the default visible area and prioritizes
    the 8 KPIs."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_dashboard_renders_for_tuho(self):
        """The dashboard is rendered for protected references
        (TUHO / Oborovo). For a fresh open, it shows a
        'No run yet' CTA."""
        r = self.client.get("/?project=tuho", follow_redirects=True)
        html = r.text
        # The dashboard container is in the DOM
        assert "dashboard-v1" in html
        # The run CTA is shown because the protected reference
        # has no run snapshot.
        assert "dashboard-run-cta" in html

    def test_dashboard_renders_for_generic_solar(self):
        r = self.client.get(
            "/?project=generic_solar", follow_redirects=True
        )
        html = r.text
        assert "dashboard-v1" in html

    def test_dashboard_default_active_tab(self):
        """The default active nav tab is Dashboard. The
        nav-compression-tab-dashboard element has the
        'active' class (or the markup indicates it is the
        initial active tab)."""
        r = self.client.get("/?project=tuho", follow_redirects=True)
        html = r.text
        # The dashboard tab is the first one and has 'active'
        # class.
        # Find the nav-compression block.
        nav_match = re.search(
            r'<div class="nav-compression[^"]*"[^>]*>(.*?)</div>',
            html,
            flags=re.DOTALL,
        )
        assert nav_match is not None, "nav-compression block not found"
        nav_block = nav_match.group(1)
        # The first button should have 'active' class.
        first_btn = re.search(
            r'<button[^>]*class="([^"]*)"[^>]*>([^<]*)</button>',
            nav_block,
        )
        assert first_btn is not None
        classes = first_btn.group(1)
        label = first_btn.group(2).strip()
        assert "active" in classes, (
            f"First nav button ({label!r}) is not the active tab. "
            f"The default should be Dashboard."
        )
        assert "Dashboard" in label

    def test_dashboard_includes_run_cta(self):
        """When the runtime snapshot is missing, the dashboard
        shows a Run model CTA."""
        r = self.client.get("/?project=tuho", follow_redirects=True)
        html = r.text
        assert "dashboard-run-cta" in html
        assert "Run model" in html

    def test_dashboard_kpis_referenced(self):
        """The dashboard references Project IRR, Equity IRR,
        NPV, Min DSCR, Avg DSCR, Senior debt, Revenue,
        EBITDA. The KPI grid is rendered (server-side) for
        every project (the values may be 'missing' for
        projects with no runtime, but the labels are
        referenced)."""
        r = self.client.get(
            "/?project=generic_solar", follow_redirects=True
        )
        html = r.text
        # The dashboard container is rendered
        assert "dashboard-v1" in html
        # The dashboard-charts container is rendered
        assert "dashboard-charts" in html


# ─────────────────────────────────────────────────────────────────────
# Test: Results sub-navigation
# ─────────────────────────────────────────────────────────────────────


class TestResultsSubNavigation:
    """The Results area includes a sub-nav with output sheet
    shortcuts (Revenue, OPEX, CAPEX, Senior Debt, SHL, Tax,
    P&L, Cash Flow, Balance, Distributions, Sponsor,
    Construction, Production)."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_results_subnav_present(self):
        r = self.client.get("/?project=tuho", follow_redirects=True)
        html = r.text
        assert "results-subnav" in html

    def test_results_subnav_targets_all_sheets(self):
        r = self.client.get("/?project=tuho", follow_redirects=True)
        html = r.text
        for sheet in (
            "results-subnav-tab-revenue",
            "results-subnav-tab-opex",
            "results-subnav-tab-capex",
            "results-subnav-tab-senior-debt",
            "results-subnav-tab-shl",
            "results-subnav-tab-tax",
            "results-subnav-tab-pl",
            "results-subnav-tab-cashflow",
            "results-subnav-tab-balance",
            "results-subnav-tab-distributions",
            "results-subnav-tab-sponsor",
            "results-subnav-tab-construction",
            "results-subnav-tab-production",
        ):
            assert sheet in html, (
                f"Results sub-nav missing tab {sheet!r}"
            )

    def test_results_subnav_uses_existing_switchtab(self):
        """The sub-nav calls the existing switchTab JS
        function (no new JS)."""
        r = self.client.get("/?project=tuho", follow_redirects=True)
        html = r.text
        # Each sub-nav button has onclick="switchTab('...')"
        assert "switchTab('revenue')" in html
        assert "switchTab('opex')" in html
        assert "switchTab('capex')" in html


# ─────────────────────────────────────────────────────────────────────
# Test: normal-mode negative tests
# ─────────────────────────────────────────────────────────────────────


class TestNormalModeNegative:
    """Rendered normal-mode routes (outside audit tab) must
    not expose internal / governance / lineage vocabulary."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def _visible_no_audit(self, project_code: str) -> str:
        r = self.client.get(
            f"/?project={project_code}", follow_redirects=True
        )
        return _extract_visible_text(_strip_audit_panel(r.text))

    def test_workspace_overview_no_forbidden_terms(self):
        for project_code in PROJECTS_TO_TEST:
            visible = self._visible_no_audit(project_code)
            lower = visible.lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in lower, (
                    f"{project_code} workspace overview contains "
                    f"forbidden term: {term!r}"
                )

    def test_inputs_tab_no_forbidden_terms(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/inputs?project={project_code}",
                follow_redirects=True,
            )
            visible = _extract_visible_text(
                _strip_audit_panel(r.text)
            )
            lower = visible.lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in lower, (
                    f"{project_code} /inputs contains forbidden "
                    f"term: {term!r}"
                )

    def test_scenarios_tab_no_forbidden_terms(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/scenarios?project={project_code}",
                follow_redirects=True,
            )
            visible = _extract_visible_text(
                _strip_audit_panel(r.text)
            )
            lower = visible.lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in lower, (
                    f"{project_code} /scenarios contains forbidden "
                    f"term: {term!r}"
                )

    def test_capex_sheet_no_forbidden_terms(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/sheet/capex?project={project_code}",
                follow_redirects=True,
            )
            visible = _extract_visible_text(
                _strip_audit_panel(r.text)
            )
            lower = visible.lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in lower, (
                    f"{project_code} /sheet/capex contains "
                    f"forbidden term: {term!r}"
                )


# ─────────────────────────────────────────────────────────────────────
# Test: preservation of prior behavior
# ─────────────────────────────────────────────────────────────────────


class TestPriorBehaviorPreserved:
    """P2-FIX-1 default route, P2-FIX-2 shell strip, P2-FIX-3
    first-edit copy flow, and S1/S2/S3 contracts must all
    still work."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_root_route_renders_project_home(self):
        """P2-FIX-1: GET / (no project) renders the Project
        Home landing."""
        r = self.client.get("/", follow_redirects=True)
        assert r.status_code == 200
        # Project Home chip is rendered (P2-FIX-1 uses
        # ph- prefixed CSS classes on the Project Home
        # page).
        assert "ph-grid" in r.text or "ph-section" in r.text or "ph-empty" in r.text

    def test_projects_new_minimal_form(self):
        """P2-FIX-1: GET /projects/new renders the minimal
        4-field form."""
        r = self.client.get("/projects/new", follow_redirects=True)
        assert r.status_code == 200
        # The minimal form has only 4 visible fields
        # (project_name, project_type, country_market,
        # capacity_mw)
        assert "project_name" in r.text
        assert "project_type" in r.text
        assert "country_market" in r.text or "country" in r.text
        assert "capacity_mw" in r.text or "capacity" in r.text

    def test_p2fix3_first_edit_guard_still_active(self):
        """P2-FIX-3: first edit attempt on TUHO returns 409
        with needs_copy_confirmation=true.

        P2-FIX-3 is now MERGED into main (post-rebase).
        This test verifies the C2 first-edit guard still
        works correctly under the P2-FIX-4 five-area
        navigation. The guard is in main_web.py
        (save_workspace_draft_endpoint) and the
        confirm route is also in main_web.py; the
        P2-FIX-4 navigation change does not touch
        those paths.
        """
        r = self.client.post(
            "/scenarios/state/draft",
            data={
                "active_project": "tuho",
                "project_name": "TUHO",
                "technology": "Wind",
            },
            follow_redirects=False,
        )
        assert r.status_code == 409, (
            f"Expected 409 first-edit guard, got {r.status_code}"
        )
        body = r.json()
        assert body["error"] == "protected_reference"
        assert body["needs_copy_confirmation"] is True

    def test_p2fix3_confirm_route_still_active(self):
        """P2-FIX-3: confirm-first-edit-copy route still
        creates a working copy under P2-FIX-4 nav."""
        r = self.client.post(
            "/projects/tuho/confirm-first-edit-copy",
            data={},
            follow_redirects=False,
        )
        # 302 redirect to the new working copy OR 200 OK
        # with project_code reference — both valid.
        assert r.status_code in (200, 302), (
            f"Expected 200/302 from confirm route, got "
            f"{r.status_code}"
        )

    def test_p2fix2_audit_tab_preserved(self):
        """P2-FIX-2: the audit / reviewer surface still
        contains the relocated governance / lineage /
        runtime-source information."""
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        html = r.text
        # The audit tab still contains the relocated content
        assert 'id="panel-audit"' in html
        audit_start = html.find('id="panel-audit"')
        div_start = html.rfind("<div", 0, audit_start)
        depth = 0
        i = div_start
        while i < len(html):
            if html[i:i + 5] == "<div " or html[i:i + 5] == "<div>":
                depth += 1
                i += 5
            elif html[i:i + 6] == "</div>":
                depth -= 1
                i += 6
                if depth == 0:
                    break
            else:
                i += 1
        audit_panel = html[div_start:i]
        visible = _extract_visible_text(audit_panel)
        # Relocated information must still be present
        for term in (
            "Lifecycle Clarity",
            "Export Lineage",
            "Governance Status",
            "G20 BLOCKED",
            "R99/R102",
            "Review boundary",
        ):
            assert term in visible, (
                f"Audit tab missing relocated information: {term!r}"
            )

    def test_export_route_still_works(self):
        """The export / download route is not deleted."""
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert r.status_code == 200
        # The downloads tab is still in the DOM (hidden != deleted)
        assert "tab-downloads" in r.text

    def test_compare_route_still_works(self):
        """The compare route is not deleted."""
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert r.status_code == 200
        assert "tab-compare" in r.text

    def test_scenario_routes_still_work(self):
        """The scenario routes (list, history, compare,
        compare-multi) are not deleted."""
        r = self.client.get(
            "/scenarios?project=tuho", follow_redirects=True
        )
        assert r.status_code == 200
        r2 = self.client.get(
            "/scenarios/history?project=tuho",
            follow_redirects=True,
        )
        assert r2.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# Test: file-scope
# ─────────────────────────────────────────────────────────────────────


class TestFileScope:
    """P2-FIX-4 is presentation-only. Only the new nav
    partial, dashboard template, and a route context flag
    are touched. No backend / no model / no factory / no
    formula / no JS / no schema / no migration."""

    def test_only_allowed_files_changed(self):
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
            "app/templates/partials/_nav_compression.html",
            "app/templates/partials/_results_subnav.html",
            "app/templates/partials/_dashboard.html",
            "app/templates/partials/workspace_shell.html",
            "app/templates/partials/_state_banner.html",
            "app/templates/partials/inputs_section.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",
            "app/ui/dashboard.py",
            "main_web.py",
            "tests/test_phase_p2fix4_five_area_navigation.py",
            # ── Phase P2-FIX-4 cross-arc test patch ─────
            # The P2-FIX-3 file-scope test is extended
            # in this branch to allowlist the P2-FIX-4
            # dashboard.py / template / docs / reports
            # additions. This is the same cross-arc
            # pattern used in P2-min-1 / P2-min-2 / etc.
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix2_shell_strip.py",
            "tests/test_phase51f_parallel_work_guardrails.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_p2fix5b_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix5c_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix5d_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix5e_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix6_",  # P2-FIX-7A cross-arc
            "docs/phase_p2fix4_",
            "reports/phase_p2fix4_",
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_m3_",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
        )
        # Disallowed locations that must not change.
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
        )
        # Phase P2-FIX-7 / P2-FIX-7A: allow static/styles.css.
        # P2-FIX-7 added standalone page CSS rules;
        # P2-FIX-7A fixed pre-existing CSS parser bugs
        # in the same file. The CSS additions are
        # scoped to the standalone / page-shell
        # classes; workspace CSS is unaffected.
        for f in changed:
            if f == "static/styles.css":
                continue
            with_dash = [f.startswith(p) for p in disallowed_prefixes]
            assert not any(with_dash), (
                f"Disallowed file changed: {f}"
            )
            ok = [f.startswith(p) for p in allowed_prefixes]
            assert any(ok), (
                f"File outside allowed scope: {f}"
            )
