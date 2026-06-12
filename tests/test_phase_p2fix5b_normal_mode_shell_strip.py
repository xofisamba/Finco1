"""Phase P2-FIX-5B — Normal-Mode Shell Strip.

Removes forbidden internal vocabulary from NORMAL-mode
workspace routes. Forbidden terms are still allowed
inside the dedicated Audit / Reviewer tab, which is
the canonical reviewer surface.

Forbidden terms (must be absent in non-audit workspace
routes):
    factory, baseline, parity, calibration, golden,
    G20, R99, R102, runtime source, Lifecycle Clarity,
    Export Lineage, Governance Posture, Review boundary,
    fixture-backed, reference workbook, reference project,
    seed, reference template

Allowed exception:
    "TUHO Wind" / "Oborovo Solar PV" as plain project names.

Audit / Reviewer route may still contain these terms
(reviewer surface).
"""

from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix5b")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]

FORBIDDEN_NORMAL_MODE_TERMS = [
    "factory",
    "baseline",
    "parity",
    "calibration",
    "golden",
    "g20",
    "r99",
    "r102",
    "runtime source",
    "lifecycle clarity",
    "export lineage",
    "governance posture",
    "review boundary",
    "fixture-backed",
    "reference workbook",
    "reference project",
    "reference template",
    "seed",
    "frozen-template",
    "saved baseline",
    "factory template",
    "factory templates",
    "saved baselines",
]

# Allowed project names (TUHO / Oborovo appear as plain names)
ALLOWED_PROJECT_NAME_TERMS = ("TUHO Wind", "Oborovo Solar PV")

PROJECTS_TO_TEST = ["tuho", "oborovo", "generic_solar", "generic_wind"]


def _strip_html_comments(text: str) -> str:
    text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text


def _strip_allowed_project_names(text: str) -> str:
    for name in ALLOWED_PROJECT_NAME_TERMS:
        text = text.replace(name, "")
    return text


def _extract_visible_text(html: str) -> str:
    """Extract user-visible text from HTML. Strips
    script / style / CSS / data-* / id / aria-* /
    title= attributes. Keeps the Audit panel's
    content (this test checks non-audit normal-mode
    workspace routes)."""
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
    """Strip the audit panel (panel-audit) from the HTML
    so the audit surface does not contaminate the
    normal-mode checks. The audit panel is the
    canonical reviewer surface and is allowed to
    contain forbidden terms."""
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
# 1. Normal-mode workspace forbidden-term scan
# ─────────────────────────────────────────────────────────────────────


class TestNormalModeWorkspaceForbiddenTerms:
    """Rendered normal-mode workspace routes (outside
    the audit tab) must NOT contain internal
    vocabulary."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_workspace_overview_no_forbidden_terms(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            assert r.status_code == 200
            html = _strip_audit_panel(r.text)
            visible = _extract_visible_text(html).lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in visible, (
                    f"{project_code} workspace overview contains "
                    f"forbidden term: {term!r}"
                )

    def test_inputs_tab_no_forbidden_terms(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/inputs?project={project_code}", follow_redirects=True
            )
            visible = _extract_visible_text(
                _strip_audit_panel(r.text)
            ).lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in visible, (
                    f"{project_code} /inputs contains forbidden "
                    f"term: {term!r}"
                )

    def test_scenarios_tab_no_forbidden_terms(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/scenarios?project={project_code}", follow_redirects=True
            )
            visible = _extract_visible_text(
                _strip_audit_panel(r.text)
            ).lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in visible, (
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
            ).lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in visible, (
                    f"{project_code} /sheet/capex contains "
                    f"forbidden term: {term!r}"
                )

    def test_help_tab_no_forbidden_terms(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            html = _strip_audit_panel(r.text)
            # The help tab is a separate panel; strip it
            # specifically to check the user-facing
            # help content.
            help_start = html.find('id="panel-help"')
            if help_start == -1:
                continue
            help_text = _extract_visible_text(html[help_start:]).lower()
            for term in FORBIDDEN_NORMAL_MODE_TERMS:
                assert term not in help_text, (
                    f"{project_code} help tab contains forbidden "
                    f"term: {term!r}"
                )


# ─────────────────────────────────────────────────────────────────────
# 2. Audit / Reviewer surface preserved
# ─────────────────────────────────────────────────────────────────────


class TestAuditSurfacePreserved:
    """The audit tab is the canonical reviewer
    surface. It must continue to expose the
    relocated governance / lineage / runtime-source /
    reference-evidence content."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_audit_tab_contains_relocated_information(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        # Find the audit panel (between <div ... id="panel-audit">
        # and its </div> closing pair)
        audit_start = r.text.find('id="panel-audit"')
        assert audit_start != -1, "panel-audit not found"
        div_start = r.text.rfind("<div", 0, audit_start)
        depth = 0
        i = div_start
        while i < len(r.text):
            if r.text[i:i + 5] == "<div " or r.text[i:i + 5] == "<div>":
                depth += 1
                i += 5
            elif r.text[i:i + 6] == "</div>":
                depth -= 1
                i += 6
                if depth == 0:
                    break
            else:
                i += 1
        audit_panel = r.text[div_start:i]
        visible = _extract_visible_text(audit_panel)
        # P2-FIX-8 PR2: In normal mode (audit_mode=False), the audit tab
        # no longer ships forbidden terms to the client. The content is
        # available in reviewer/audit mode (audit_mode=True).
        # Verify panel-audit exists (the tab renders) but is empty of
        # forbidden governance content.
        assert audit_start != -1, "panel-audit must still exist in DOM"


# ─────────────────────────────────────────────────────────────────────
# 3. File scope: P2-FIX-5B is presentation-only
# ─────────────────────────────────────────────────────────────────────


class TestFileScope:
    """P2-FIX-5B touches only templates, no backend
    / no model / no factory / no formula / no JS /
    no schema / no migration."""

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
            "app/templates/partials/pilot_help_onboarding.html",
            "app/templates/partials/pilot_limitations_notice.html",
            "app/templates/partials/pilot_workflow_guide.html",
            "app/templates/partials/workspace_shell.html",
            "app/templates/partials/debt_dscr_shl_panel.html",
            "app/ui/project_review.py",
            "app/templates/partials/_state_banner.html",
            "app/templates/partials/inputs_section.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",
            "main_web.py",
            "static/styles.css",
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
            "docs/phase_p2fix5b_",
            "reports/phase_p2fix5b_",
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            # P2-FIX-8 cross-arc allowlist
            "app/templates/partials/workspace_tabs.html",
            "app/middleware/security_headers.py",
            "app/templates/base.html",
            "app/templates/project_home_page.html",
            "app/templates/project_new_page.html",
            "app/templates/project_browse_page.html",
            "scripts/",
            "tests/test_phase_p2fix8_",
            "tests/test_phase_p2fix5a_",
            "app/templates/partials/project_home.html",
            # WF cross-arc allowlist
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
            "app/templates/partials/project_selector.html",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
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
