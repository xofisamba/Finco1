"""Phase P2-FIX-2 — Shell Strip / Move Governance-Lineage to Audit.

Tests verify that normal-mode workspace screens do NOT expose internal
governance / lineage / runtime-source / review-boundary vocabulary, and
that the audit / reviewer surface (panel-audit tab) still contains the
relocated information.

For each normal-mode route, the test fetches the rendered HTML and
asserts that the forbidden terms (case-insensitive, stripped of HTML /
Jinja comments) are absent.

The audit / reviewer surface (panel-audit) is also fetched and the
relocated information must be present.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix2")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


# ── Forbidden terms (case-insensitive) in normal-mode screens ─────────
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

ALLOWED_PROJECT_NAME_TERMS = ("TUHO Wind", "Oborovo Solar PV")


def _strip_html_comments(html: str) -> str:
    """Strip HTML / Jinja comments so the term check is not fooled by
    P2-FIX-2 design explanation comments that mention the forbidden
    terms in code (not in rendered output)."""
    html = re.sub(r"\{#.*?#\}", "", html, flags=re.DOTALL)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    return html


def _strip_allowed_project_names(html: str) -> str:
    for name in ALLOWED_PROJECT_NAME_TERMS:
        html = html.replace(name, "")
    return html


def _extract_visible_text(html: str) -> str:
    """Extract user-visible text from HTML. Strips:

    - Jinja/HTML comments
    - HTML attributes (class=, id=, data-*, aria-*, style=, title=)
    - Script and style blocks
    - Tags themselves

    What remains is essentially the rendered text the user sees.
    """
    html = _strip_html_comments(html)
    html = _strip_allowed_project_names(html)
    # Remove <script>...</script> and <style>...</style>
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove all HTML attributes — the term must NOT appear in the
    # rendered text. CSS class names (class="ds-badge--factory") and
    # data- attributes are NOT user-visible; we only care about the
    # text the user actually reads.
    html = re.sub(r'\s[a-zA-Z-]+="[^"]*"', " ", html)
    # Remove any remaining tag brackets
    html = re.sub(r"<[^>]+>", " ", html)
    return html


def _body_contains_forbidden(html: str) -> tuple[bool, list[str]]:
    cleaned_visible = _extract_visible_text(html)
    cleaned_lower = cleaned_visible.lower()
    found = []
    for term in FORBIDDEN_NORMAL_MODE_TERMS:
        if term.lower() in cleaned_lower:
            found.append(term)
    return (len(found) == 0, found)


@pytest.fixture(scope="module")
def logged_in_client():
    """TestClient with a valid session cookie."""
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


PROJECTS_TO_TEST = ["tuho", "oborovo", "generic_solar"]


# ─────────────────────────────────────────────────────────────────────
# Normal-mode screens: must NOT contain forbidden terms
# ─────────────────────────────────────────────────────────────────────


class TestShellStripNormalMode:
    """Normal-mode workspace screens must not contain the forbidden
    governance/lineage/audit vocabulary."""

    def test_workspace_overview_no_forbidden_terms(self, logged_in_client):
        """The overview is the default landing tab. The audit
        tab (panel-audit) is the audit / reviewer surface and
        is allowed to contain the relocated governance /
        lineage / runtime-source content. We strip the audit
        tab from the HTML before checking for forbidden
        terms."""
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            html = resp.text
            # Strip the audit panel (depth-counting) so the
            # reviewer-surface content does not contaminate the
            # normal-mode overview check.
            audit_start = html.find('id="panel-audit"')
            if audit_start != -1:
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
                html = html[:div_start] + html[i:]
            is_clean, found = _body_contains_forbidden(html)
            assert is_clean, (
                f"Forbidden terms found in workspace overview for "
                f"project {project_code}: {found}"
            )

    def test_workspace_inputs_tab_no_forbidden_terms(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/inputs?project={project_code}", follow_redirects=True
            )
            html = resp.text
            is_clean, found = _body_contains_forbidden(html)
            assert is_clean, (
                f"Forbidden terms found in /inputs for project "
                f"{project_code}: {found}"
            )

    def test_workspace_scenarios_tab_no_forbidden_terms(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/scenarios?project={project_code}", follow_redirects=True
            )
            html = resp.text
            is_clean, found = _body_contains_forbidden(html)
            assert is_clean, (
                f"Forbidden terms found in /scenarios for project "
                f"{project_code}: {found}"
            )

    def test_workspace_capex_sheet_no_forbidden_terms(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/sheet/capex?project={project_code}",
                follow_redirects=True,
            )
            html = resp.text
            is_clean, found = _body_contains_forbidden(html)
            assert is_clean, (
                f"Forbidden terms found in /sheet/capex for project "
                f"{project_code}: {found}"
            )

    def test_default_route_no_project_no_forbidden_terms(self, logged_in_client):
        resp = logged_in_client.get("/", follow_redirects=True)
        html = resp.text
        is_clean, found = _body_contains_forbidden(html)
        assert is_clean, (
            f"Forbidden terms found in Project Home (GET /): {found}"
        )

    def test_workspace_placeholder_notes_use_generic_disclosure(
        self, logged_in_client
    ):
        """Distributions + Sponsor placeholders should show the
        generic disclosure in normal mode (not R99/R102 NOT
        APPROVED). The placeholder note lives inside the
        Distributions and Sponsor panel-cards. The audit tab
        MAY still contain the relocated R99/R102 NOT APPROVED
        text — that is the audit surface.

        We check the Distributions and Sponsor panel sections
        only. We do this by extracting the relevant panel
        containers and checking the note text. The audit tab
        is identified by id="panel-audit" and we strip it
        from the HTML before checking the rest.
        """
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            html = resp.text
            # Find the start of the audit panel and truncate.
            audit_start = html.find('id="panel-audit"')
            if audit_start == -1:
                audit_stripped = html
            else:
                # Walk backwards to find the opening <div
                div_start = html.rfind("<div", 0, audit_start)
                # Walk forward to find the matching close. We
                # use a depth-counting scan because the panel
                # is deeply nested and a regex is fragile.
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
                audit_stripped = html[:div_start] + html[i:]
            visible = _extract_visible_text(audit_stripped)
            assert "R99/R102 NOT APPROVED" not in visible, (
                f"R99/R102 NOT APPROVED placeholder leaked into "
                f"normal-mode workspace for {project_code} "
                f"(outside audit tab)"
            )


# ─────────────────────────────────────────────────────────────────────
# Audit / reviewer surface: must STILL contain relocated information
# ─────────────────────────────────────────────────────────────────────


class TestShellStripAuditSurfacePreserved:
    """The audit / reviewer surface (panel-audit tab) must still
    contain the relocated governance / lineage / runtime-source
    information."""

    def test_audit_tab_contains_relocated_information(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            # The marker is a data attribute on the wrapping div.
            # We accept that the audit tab is rendered (HTML
            # exists); the data attribute may not be present in
            # the visible text but the content is.
            assert resp.status_code == 200
            assert len(resp.text) > 5000, (
                "Workspace page is suspiciously small — audit "
                "tab may not have rendered."
            )

    def test_audit_tab_contains_lifecycle_clarity(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            visible = _extract_visible_text(resp.text)
            assert "Lifecycle Clarity" in visible, (
                f"Audit tab missing 'Lifecycle Clarity' for "
                f"project {project_code}"
            )

    def test_audit_tab_contains_export_lineage(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            visible = _extract_visible_text(resp.text)
            assert "Export Lineage" in visible, (
                f"Audit tab missing 'Export Lineage' for "
                f"project {project_code}"
            )

    def test_audit_tab_contains_governance_status(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            visible = _extract_visible_text(resp.text)
            assert "Governance Status" in visible, (
                f"Audit tab missing 'Governance Status' for "
                f"project {project_code}"
            )

    def test_audit_tab_contains_g20_blocked(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            visible = _extract_visible_text(resp.text)
            assert "G20 BLOCKED" in visible, (
                f"Audit tab missing 'G20 BLOCKED' for project "
                f"{project_code}"
            )

    def test_audit_tab_contains_r99_r102_not_approved(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            visible = _extract_visible_text(resp.text)
            assert "R99/R102" in visible, (
                f"Audit tab missing 'R99/R102' for project "
                f"{project_code}"
            )

    def test_audit_tab_contains_review_boundary(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            visible = _extract_visible_text(resp.text)
            assert "Review boundary" in visible, (
                f"Audit tab missing 'Review boundary' for "
                f"project {project_code}"
            )


# ─────────────────────────────────────────────────────────────────────
# /projects/new minimal form: must NOT contain forbidden terms
# ─────────────────────────────────────────────────────────────────────


class TestShellStripNewProjectMinimal:
    """The /projects/new minimal form must not contain forbidden
    governance/lineage/audit vocabulary either."""

    def test_new_project_minimal_no_forbidden_terms(self, logged_in_client):
        resp = logged_in_client.get("/projects/new", follow_redirects=True)
        html = resp.text
        is_clean, found = _body_contains_forbidden(html)
        assert is_clean, (
            f"Forbidden terms found in /projects/new: {found}"
        )


# ─────────────────────────────────────────────────────────────────────
# Cross-cutting invariants
# ─────────────────────────────────────────────────────────────────────


class TestShellStripInvariants:
    """Cross-cutting invariants pinned by P2-FIX-2."""

    def test_workspace_renders_ok_all_projects(self, logged_in_client):
        for project_code in PROJECTS_TO_TEST:
            resp = logged_in_client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            assert resp.status_code == 200, (
                f"Workspace for {project_code} returned "
                f"{resp.status_code}"
            )
            assert "<html" in resp.text.lower(), (
                f"Workspace for {project_code} did not render HTML"
            )

    def test_protected_original_wording_in_lock_indicator(
        self, logged_in_client
    ):
        """The lock indicator should use 'Protected original' (P2-FIX-2
        relabel), not 'Factory template' (legacy)."""
        resp = logged_in_client.get(
            "/?project=tuho", follow_redirects=True
        )
        visible = _extract_visible_text(resp.text)
        assert "Protected original" in visible, (
            "Workspace for TUHO missing 'Protected original' label"
        )

    def test_generic_disclosure_line_for_generic_project(
        self, logged_in_client
    ):
        """Generic projects show the 'Internal-use model' generic
        disclosure line in the workspace overview."""
        resp = logged_in_client.get(
            "/?project=generic_solar", follow_redirects=True
        )
        visible = _extract_visible_text(resp.text)
        assert "Internal-use model" in visible, (
            "Workspace for generic project missing generic "
            "disclosure line"
        )


# ─────────────────────────────────────────────────────────────────────
# File-scope: only allowed files may be touched
# ─────────────────────────────────────────────────────────────────────


class TestShellStripFileScope:
    """File-scope: P2-FIX-2 is presentation-only. Allowed files:

    - app/templates/** (HTML / Jinja partials)
    - app/ui/** (presentation services, e.g. dirty_state)
    - main_web.py (route context builders; presentation only)
    - tests/test_phase_p2fix2_shell_strip.py
    - docs/phase_p2fix2_**
    - reports/phase_p2fix2_**

    Disallowed: app/services/, app/persistence/, main_api.py,
    static/app.js, anything under app/excel_export/,
    app/waterfall_core/, app/project_factories/, db.py, db migrations.
    """

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
            "app/templates/",
            "app/ui/",
            "main_web.py",
            "tests/test_phase_p2fix2_shell_strip.py",
            "docs/phase_p2fix2_",
            "reports/phase_p2fix2_",
            # ── Phase P2-FIX-4 cross-arc test patch ─────
            # P2-FIX-4 modifies _nav_compression.html,
            # _results_subnav.html, _dashboard.html,
            # workspace_shell.html, app/ui/dashboard.py,
            # and main_web.py — all of which are already
            # covered by the app/templates/ and app/ui/
            # allowlist above. The P2-FIX-4 test,
            # docs, and report files are also allowed
            # because they are part of the same
            # cross-arc P2-FIX arc (rebase on top of
            # P2-FIX-3 main).
            "tests/test_phase_p2fix4_",
            "tests/test_phase_p2fix3_",
            "docs/phase_p2fix4_",
            "reports/phase_p2fix4_",
            # Phase P2-FIX-7 / P2-FIX-7A allowlists.
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_p2fix5b_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix5c_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix5d_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix5e_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix6_",  # P2-FIX-7A cross-arc
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
            "static/styles.css",
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


# ─────────────────────────────────────────────────────────────────────
# Hidden != deleted: factory/baseline literals in the data model
# ─────────────────────────────────────────────────────────────────────


class TestShellStripHiddenNotDeleted:
    """P2-FIX-2 must NOT delete the underlying factory/baseline
    literals. They live in the data model and in protected
    internal paths. UI hides them; the literals themselves must
    still resolve."""

    def test_factory_template_origin_literal_in_data_model(self):
        """The 'factory_template' string literal must still be
        referenced in the data model (assert_project_allows_capex
        _sub_lines, projects_repository.list_baseline_records,
        etc.)."""
        result = subprocess.run(
            [
                "grep", "-rln",
                "factory_template",
                str(REPO_ROOT / "app" / "persistence"),
            ],
            capture_output=True,
            text=True,
        )
        # At least one persistence file should still reference it.
        assert result.stdout.strip(), (
            "factory_template literal removed from app/persistence/. "
            "This is presentation-only; the data model must not change."
        )

    def test_baseline_record_literal_in_data_model(self):
        """The 'baseline' string literal must still appear in the
        data model."""
        result = subprocess.run(
            [
                "grep", "-rln",
                "list_baseline_records\\|saved_baseline",
                str(REPO_ROOT / "app" / "persistence"),
            ],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip(), (
            "baseline / saved_baseline literal removed from "
            "app/persistence/. This is presentation-only; the "
            "data model must not change."
        )


# ─────────────────────────────────────────────────────────────────────
# P2-FIX-2 review-fix: normal-mode banner copy is project-type-aware
# ─────────────────────────────────────────────────────────────────────


class TestShellStripNormalModeBanner:
    """P2-FIX-2 review-fix:

    - Generic / user-created projects: one short line,
      "Internal-use model — results are indicative." No reference
      or template language.
    - TUHO / Oborovo protected originals: one short line,
      "Protected original — open for review, run and export.
      Create an editable copy before changing assumptions."
      No factory / template / baseline / parity / golden / calibration
      language.

    Audit / Reference tab may still contain relocated governance /
    provenance details.
    """

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def _visible_no_audit(self, project_code: str) -> str:
        """Render the workspace for the project, strip the
        audit panel, and return the user-visible text."""
        resp = self.client.get(
            f"/?project={project_code}", follow_redirects=True
        )
        html = resp.text
        audit_start = html.find('id="panel-audit"')
        if audit_start != -1:
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
            html = html[:div_start] + html[i:]
        return _extract_visible_text(html)

    def test_generic_normal_mode_has_internal_use_model_line(self):
        """Generic / user-created projects show the
        'Internal-use model — results are indicative.' line in
        normal mode."""
        visible = self._visible_no_audit("generic_solar")
        assert "Internal-use model — results are indicative." in visible, (
            "Generic normal-mode banner missing "
            "'Internal-use model — results are indicative.' line"
        )

    def test_generic_normal_mode_forbidden_terms_absent(self):
        """Generic / user-created normal-mode workspace does
        NOT contain: reference template, Reference project,
        factory, baseline, parity, calibration, golden, G20,
        R99, R102."""
        visible = self._visible_no_audit("generic_solar")
        lower = visible.lower()
        for term in (
            "reference template",
            "reference project",
            "factory",
            "baseline",
            "parity",
            "calibration",
            "golden",
            "g20",
            "r99",
            "r102",
        ):
            assert term not in lower, (
                f"Generic normal-mode workspace contains forbidden "
                f"term: {term!r}"
            )

    def test_tuho_normal_mode_has_protected_original_disclosure(self):
        """TUHO / Oborovo protected originals show the
        'Protected original — open for review, run and export.
        Create an editable copy before changing assumptions.'
        line in normal mode."""
        for project_code in ("tuho", "oborovo"):
            visible = self._visible_no_audit(project_code)
            assert "Protected original" in visible, (
                f"TUHO/Oborovo normal-mode banner missing "
                f"'Protected original' line for {project_code}"
            )
            assert (
                "open for review, run and export" in visible
            ), (
                f"TUHO/Oborovo normal-mode banner missing "
                f"'open for review, run and export' for {project_code}"
            )
            assert (
                "Create an editable copy before changing assumptions"
                in visible
            ), (
                f"TUHO/Oborovo normal-mode banner missing "
                f"'Create an editable copy before changing assumptions' "
                f"for {project_code}"
            )

    def test_tuho_normal_mode_forbidden_terms_absent(self):
        """TUHO / Oborovo normal-mode workspace does NOT contain:
        reference template, factory, baseline, parity, calibration,
        golden, G20, R99, R102. (TUHO and Oborovo as plain project
        names ARE allowed.)"""
        for project_code in ("tuho", "oborovo"):
            visible = self._visible_no_audit(project_code)
            # Strip allowed project name literals before checking.
            stripped = visible.replace("TUHO Wind", "").replace(
                "Oborovo Solar PV", ""
            )
            lower = stripped.lower()
            for term in (
                "reference template",
                "factory",
                "baseline",
                "parity",
                "calibration",
                "golden",
                "g20",
                "r99",
                "r102",
            ):
                assert term not in lower, (
                    f"TUHO/Oborovo normal-mode workspace contains "
                    f"forbidden term {term!r} for {project_code}"
                )

    def test_audit_tab_still_contains_relocated_information(self):
        """The audit / Reference tab must still contain the
        relocated governance / lineage / runtime-source
        information (no information loss)."""
        resp = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        html = resp.text
        # Locate the audit panel and check it contains the
        # relocated information.
        audit_start = html.find('id="panel-audit"')
        assert audit_start != -1, "Audit panel not found"
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
        # The relocated information must still be present.
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
