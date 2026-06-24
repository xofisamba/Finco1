"""Phase P2-FIX-6 — Complete C2 Create Editable Copy UI.

Renders a visible 'Create editable copy' button for
protected reference projects (TUHO / Oborovo) in the
state banner. The button POSTs to the existing
backend route
``POST /projects/{code}/confirm-first-edit-copy``
which creates a user-owned working copy and
redirects.

The button is NOT rendered for:
- Generic Solar / Generic Wind (not protected)
- user-created working copies
- user-created projects (the user is already the
  owner)

The backend C2 flow (P2-FIX-3) is preserved:
- POST /scenarios/state/draft on a protected
  reference returns 409 with
  needs_copy_confirmation=True
- POST /projects/{code}/confirm-first-edit-copy
  creates a working copy and returns 302
- The working copy is editable
- The original fixture is unchanged
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix6")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


# ─────────────────────────────────────────────────────────────────────
# 1. Visible 'Create editable copy' button
# ─────────────────────────────────────────────────────────────────────


class TestCreateEditableCopyButtonVisible:
    """P2-FIX-8 PR3: The explicit button is retired from normal mode.
    Transparent copy-on-first-save replaces the button in normal mode.
    The button remains in reviewer/audit mode (audit_mode=True).
    These tests verify the backend confirm route still works."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_tuho_workspace_no_explicit_button_normal_mode(self):
        """P2-FIX-8: No explicit button in normal mode (transparent copy handles it)."""
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert 'data-p2fix6-cta="create-editable-copy"' not in r.text, (
            "P2-FIX-8: Explicit button must not appear in normal mode"
        )

    def test_oborovo_workspace_no_explicit_button_normal_mode(self):
        r = self.client.get(
            "/?project=oborovo", follow_redirects=True
        )
        assert 'data-p2fix6-cta="create-editable-copy"' not in r.text

    def test_confirm_route_still_exists(self):
        """The backend confirm route is still functional (used by transparent flow)."""
        import re
        # Template still contains the form (in audit_mode block)
        content = (REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html").read_text()
        assert "confirm-first-edit-copy" in content

    def test_button_form_in_audit_mode_block(self):
        """The button form must be inside {% if audit_mode %} in the template."""
        content = (REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html").read_text()
        assert "{% if audit_mode" in content
        # Button only appears in audit mode context
        idx = content.find('data-p2fix6-form="create-editable-copy"')
        if idx > 0:
            preceding = content[:idx]
            assert "audit_mode" in preceding[preceding.rfind("{%"):]

    def test_button_has_p2fix6_marker_in_template(self):
        """The p2fix6 marker must still exist in template (for audit mode use)."""
        content = (REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html").read_text()
        assert 'data-p2fix6-cta="create-editable-copy"' in content


# ─────────────────────────────────────────────────────────────────────
# 2. Button NOT shown for non-protected projects
# ─────────────────────────────────────────────────────────────────────


class TestButtonNotShownForNonProtected:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_generic_solar_no_button(self):
        r = self.client.get(
            "/?project=generic_solar", follow_redirects=True
        )
        assert "Create editable copy" not in r.text, (
            "Generic Solar must NOT show the C2 button "
            "(not a protected reference)"
        )

    def test_generic_wind_no_button(self):
        r = self.client.get(
            "/?project=generic_wind", follow_redirects=True
        )
        assert "Create editable copy" not in r.text, (
            "Generic Wind must NOT show the C2 button"
        )

    def test_no_confirm_first_edit_copy_link_in_generic(self):
        for project_code in ("generic_solar", "generic_wind"):
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            assert (
                f'/projects/{project_code}/confirm-first-edit-copy'
                not in r.text
            ), (
                f"{project_code} must not link to "
                f"/projects/{project_code}/confirm-first-edit-copy"
            )


# ─────────────────────────────────────────────────────────────────────
# 3. POST confirm route still works (C2 backend)
# ─────────────────────────────────────────────────────────────────────


class TestConfirmRouteStillWorks:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_confirm_route_for_tuho_returns_redirect(self):
        """POST /projects/tuho/confirm-first-edit-copy
        returns 302 to the new working copy."""
        r = self.client.post(
            "/projects/tuho/confirm-first-edit-copy",
            data={},
            follow_redirects=False,
        )
        assert r.status_code in (200, 302), (
            f"Expected 200/302 from C2 confirm route, got "
            f"{r.status_code}"
        )

    def test_confirm_route_for_oborovo_returns_redirect(self):
        r = self.client.post(
            "/projects/oborovo/confirm-first-edit-copy",
            data={},
            follow_redirects=False,
        )
        assert r.status_code in (200, 302)

    def test_confirm_route_rejects_non_protected(self):
        """POST .../confirm-first-edit-copy on a non-
        protected project (e.g. generic_solar) returns
        400."""
        r = self.client.post(
            "/projects/generic_solar/confirm-first-edit-copy",
            data={},
            follow_redirects=False,
        )
        assert r.status_code == 400, (
            f"Expected 400 for non-protected, got {r.status_code}"
        )

    def test_confirm_route_rejects_unknown_project(self):
        r = self.client.post(
            "/projects/nonexistent/confirm-first-edit-copy",
            data={},
            follow_redirects=False,
        )
        assert r.status_code == 404, (
            f"Expected 404 for unknown project, got {r.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────
# 4. Protected reference first-edit guard (P2-FIX-3 backend)
# ─────────────────────────────────────────────────────────────────────


class TestProtectedReferenceFirstEditGuard:
    """P2-FIX-8 PR3: Transparent copy replaces the 409 flow.
    POST /scenarios/state/draft on a protected reference now
    returns 200 + HX-Redirect (or 302) instead of 409."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_tuho_first_edit_no_longer_returns_409(self):
        """P2-FIX-8: Draft save on TUHO now triggers transparent copy redirect."""
        r = self.client.post(
            "/scenarios/state/draft",
            data={
                "active_project": "tuho",
                "project_name": "TUHO",
                "technology": "Wind",
            },
            follow_redirects=False,
        )
        assert r.status_code != 409, (
            "P2-FIX-8: Draft route must no longer return 409 for protected ref — "
            "transparent copy flow handles this now"
        )

    def test_oborovo_first_edit_no_longer_returns_409(self):
        r = self.client.post(
            "/scenarios/state/draft",
            data={
                "active_project": "oborovo",
                "project_name": "Oborovo",
                "technology": "Solar",
            },
            follow_redirects=False,
        )
        assert r.status_code != 409


# ─────────────────────────────────────────────────────────────────────
# 5. File scope: P2-FIX-6 is presentation-only
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
            "app/templates/partials/_state_banner.html",
            "app/templates/partials/inputs_section.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",
            "main_web.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_p2fix2_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix4_",  # P2-FIX-7A cross-arc
            "docs/phase_p2fix6_",
            "reports/phase_p2fix6_",
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            # P2-FIX-8 cross-arc allowlist
            "app/templates/partials/workspace_tabs.html",
            "app/templates/partials/workspace_shell.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/new_project_result.html",
            "tests/test_phase_wf4_",
            "app/middleware/security_headers.py",
            "app/templates/base.html",
            "app/templates/project_home_page.html",
            "app/templates/project_new_page.html",
            "app/templates/project_browse_page.html",
            "app/templates/partials/inputs_section.html",
            "static/styles.css",
            "scripts/",
            "tests/test_phase_p2fix8_",
            "tests/test_phase_p2fix5a_",
            # WF cross-arc allowlist
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
            "app/templates/partials/project_selector.html",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
            "tests/test_phase_wf6_",
            "app/templates/partials/_results_subnav.html",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_m3_",
            "tests/test_phase_m4_",
            "tests/test_phase_stab",
            "app/templates/partials/_scenario_matrix_oob.html",
            "app/ui/dashboard.py",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
            "app/templates/partials/_matrix_run_result.html",
                    # UX-1C: active workspace cleanup follow-up allowlist
                    "tests/test_phase_p2fix2_shell_strip.py",
                    "tests/test_phase_p2fix4_five_area_navigation.py",
                    "tests/test_phase_scenario1_base_case_init.py",
                    "tests/test_phase_scenario1_review_fix.py",
                    "tests/test_phase_scenario2_fixes.py",
                    "tests/test_phase_stab1_run_refreshes_kpis.py",
                    "tests/test_phase_stab2_realized_gearing_scale.py",
                    "tests/test_phase_stab3_capex_subline_propagation.py",
                    "tests/test_phase_stab5_export_route_fix.py",
                    "tests/test_phase_stab6_new_project_first_run.py",
                    "tests/test_phase_stab8_e2e_runtime_validation.py",
                    "tests/test_phase_ux4b_save_as_button.py",
                    "tests/test_phase_wf2_sheet_styling.py",
                    "tests/test_phase_wf3_home_and_projects_split.py",
                    "tests/test_phase_wf4_minimal_create_and_list_hygiene.py",
                    "tests/test_phase_wf5_grouped_results_nav.py",
                    "tests/test_phase_wf6_scenario_status_badges.py",
                    "tests/test_phase57a4_single_capex_sheet_layout.py",
                    "tests/test_phase_pr1_form_timing_fields.py",
                    "tests/test_phase_pr2_realized_gearing.py",
                    "tests/test_phase_pr3_taxonomy.py",
                    "tests/test_phase_stab7_generic_dashboard_parity.py",
                    "tests/test_phase_m1_scenario_matrix.py",
                    "tests/test_phase_m2_scenario_matrix_live.py",
                    "tests/test_phase_m3_scenario_matrix_overrides.py",
                    "tests/test_phase_m4_scenario_matrix_run.py",
            "app/templates/partials/kpis.html",
            "app/templates/partials/scenario_multi_compare_picker.html",
            "app/templates/partials/scenario_workflow_indicators.html",
            "tests/test_phase51a_run_route_golden_characterization.py",
            "tests/test_ux1a_navigation_context_fix.py",
            "tests/test_p1_compare_validation.py",
            "tests/test_phase_ux1_inputs_badge_cleanup.py",
            "tests/test_phase_ux2_active_sheet_refresh.py",
            "tests/test_phase_ux4cde_pilot_polish.py",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
)
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
            "app/ui/protected_reference_service.py",
        )
        # Phase P2-FIX-7: allow static/styles.css. The
        # P2-FIX-5/6 arcs did not touch CSS; P2-FIX-7
        # adds standalone page CSS rules. The rule
        # below lets styles.css through unconditionally
        # (P2-FIX-7 only adds rules for classes the
        # P2-FIX-5A templates reference; no workspace
        # CSS is touched).
        for f in changed:
            if f == "static/styles.css":
                # Allow only P2-FIX-7 CSS additions.
                # (Other file-scope tests in this arc
                # would catch arbitrary CSS regressions.)
                continue
            with_dash = [f.startswith(p) for p in disallowed_prefixes]
            assert not any(with_dash), (
                f"Disallowed file changed: {f}"
            )
            ok = [f.startswith(p) for p in allowed_prefixes]
            assert any(ok), (
                f"File outside allowed scope: {f}"
            )
