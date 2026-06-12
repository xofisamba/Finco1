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
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_tuho_workspace_has_button(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert "Create editable copy" in r.text, (
            "TUHO workspace must show a 'Create editable copy' "
            "button (Phase P2-FIX-6)"
        )

    def test_oborovo_workspace_has_button(self):
        r = self.client.get(
            "/?project=oborovo", follow_redirects=True
        )
        assert "Create editable copy" in r.text, (
            "Oborovo workspace must show a 'Create editable copy' "
            "button"
        )

    def test_button_posts_to_confirm_route(self):
        """The button form's action must be the C2
        confirm route with the source project code."""
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        # Find the form action
        import re
        m = re.search(
            r'<form[^>]+action="/projects/tuho/confirm-first-edit-copy"',
            r.text,
        )
        assert m is not None, (
            "Form action must POST to "
            "/projects/tuho/confirm-first-edit-copy"
        )

    def test_button_form_has_method_post(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        import re
        m = re.search(
            r'<form[^>]+method="POST"[^>]+action="/projects/tuho/confirm-first-edit-copy"',
            r.text,
        )
        assert m is not None, (
            "Form must be method=POST to "
            "/projects/tuho/confirm-first-edit-copy"
        )

    def test_button_has_p2fix6_marker(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert "data-p2fix6-cta=\"create-editable-copy\"" in r.text, (
            "Button must have data-p2fix6-cta='create-editable-copy' "
            "marker for testability"
        )


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
    """The P2-FIX-3 first-edit guard remains functional:
    POST /scenarios/state/draft on a protected
    reference returns 409."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_tuho_first_edit_returns_409(self):
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
            f"Expected 409 for TUHO first edit, got {r.status_code}"
        )
        body = r.json()
        assert body["error"] == "protected_reference"
        assert body["needs_copy_confirmation"] is True

    def test_oborovo_first_edit_returns_409(self):
        r = self.client.post(
            "/scenarios/state/draft",
            data={
                "active_project": "oborovo",
                "project_name": "Oborovo",
                "technology": "Solar",
            },
            follow_redirects=False,
        )
        assert r.status_code == 409


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
            "main_web.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "docs/phase_p2fix6_",
            "reports/phase_p2fix6_",
        )
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
            "static/styles.css",
            "app/ui/protected_reference_service.py",
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
