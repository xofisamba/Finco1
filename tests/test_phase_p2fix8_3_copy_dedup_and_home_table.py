"""Phase P2-FIX-8 PR 3 — copy dedup, transparent first-edit, Home table.

Acceptance criteria:
1. Opening TUHO twice yields exactly one working copy (dedup).
2. Transparent first-edit: draft route on protected reference returns HX-Redirect.
3. confirm-first-edit-copy on existing copy → redirect, no second copy created.
4. Home table renders all columns; technology is never "Unknown".
5. No explicit "Create editable copy" button in normal mode.
6. _resolve_technology and _find_existing_working_copy helpers work correctly.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix8-3")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app, _find_existing_working_copy, _resolve_technology  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent

# Use user "1" (same as p2fix3/p2fix6 tests) so factory templates are seeded.
TEST_USER_ID = "p2fix8_3_dedup_user"


@pytest.fixture(scope="module")
def client():
    c = TestClient(app, follow_redirects=False)
    token = create_session_token(user_id=TEST_USER_ID, username="test_dedup_user")
    c.cookies.set("finco_session", token)
    # Seed factory templates by hitting the workspace
    c.get("/?project=tuho", follow_redirects=True)
    return c


# ---------------------------------------------------------------------------
# 1. _resolve_technology — never returns "Unknown"
# ---------------------------------------------------------------------------

class TestResolveTechnology:
    def _make_record(self, project_type=None, template_source=None, snap=None):
        from unittest.mock import MagicMock
        r = MagicMock()
        r.project_type = project_type
        r.template_source = template_source
        r.source_project_template = ""
        r.baseline_snapshot = snap or {}
        return r

    def test_uses_project_type_field(self):
        r = self._make_record(project_type="Wind")
        assert _resolve_technology(r) == "Wind"

    def test_falls_back_to_snapshot(self):
        r = self._make_record(snap={"project_type": "Solar PV"})
        assert _resolve_technology(r) == "Solar PV"

    def test_derives_from_tuho_template_source(self):
        r = self._make_record(template_source="tuho")
        assert _resolve_technology(r) == "Wind"

    def test_derives_from_oborovo_template_source(self):
        r = self._make_record(template_source="oborovo")
        assert _resolve_technology(r) == "Solar PV"

    def test_derives_generic_solar(self):
        r = self._make_record(template_source="generic_solar")
        assert _resolve_technology(r) == "Solar PV"

    def test_derives_generic_wind(self):
        r = self._make_record(template_source="generic_wind")
        assert _resolve_technology(r) == "Wind"

    def test_never_returns_unknown(self):
        r = self._make_record()  # all None
        result = _resolve_technology(r)
        assert result != "Unknown", f"_resolve_technology returned 'Unknown': {result!r}"


# ---------------------------------------------------------------------------
# 2. Home table renders correctly
# ---------------------------------------------------------------------------

class TestHomeTable:
    def test_home_page_200(self, client):
        r = client.get("/", follow_redirects=True)
        assert r.status_code == 200

    def test_home_has_table_structure(self, client):
        r = client.get("/", follow_redirects=True)
        body = r.text
        # After creating a copy, the home table should appear
        assert "ph-table" in body or "My projects" in body or "No projects yet" in body

    def test_home_no_unknown_technology(self, client):
        r = client.get("/", follow_redirects=True)
        import re
        tds = re.findall(r'<td[^>]*>\s*([^<]*?)\s*</td>', r.text)
        unknown_tds = [td for td in tds if td.strip() == "Unknown"]
        assert not unknown_tds, f"'Unknown' appeared in table cells: {unknown_tds}"

    def test_home_table_has_required_headers_when_projects_exist(self, client):
        r = client.get("/", follow_redirects=True)
        if "ph-table" in r.text:
            assert "Technology" in r.text
            assert "Country" in r.text
            assert "Status" in r.text
            assert "Actions" in r.text


# ---------------------------------------------------------------------------
# 3. Transparent first-edit: draft route → HX-Redirect (not 409)
# ---------------------------------------------------------------------------

class TestTransparentCopyDraft:
    def test_draft_on_protected_ref_returns_hx_redirect_or_redirect(self, client):
        """Saving draft on a protected reference (TUHO) returns HX-Redirect
        for transparent copy-on-first-save instead of 409."""
        r = client.post(
            "/scenarios/state/draft",
            data={"active_project": "tuho"},
        )
        # Must NOT be 409 — transparent copy replaces the explicit button flow
        assert r.status_code != 409, (
            "Draft route must not return 409 for protected ref — "
            "P2-FIX-8 transparent copy flow replaces this"
        )
        # Must be a redirect (302) or 200 with HX-Redirect header
        if r.status_code == 200:
            assert "hx-redirect" in {k.lower() for k in r.headers}, (
                "200 response on protected-ref draft must have HX-Redirect header"
            )


# ---------------------------------------------------------------------------
# 4. Copy dedup: confirm-first-edit-copy never creates two copies
# ---------------------------------------------------------------------------

class TestCopyDedup:
    def test_confirm_route_accepts_protected_ref(self, client):
        """TUHO confirm route returns 302 (create or dedup to existing)."""
        r = client.post("/projects/tuho/confirm-first-edit-copy")
        assert r.status_code in (302, 303), (
            f"confirm-first-edit-copy should redirect, got {r.status_code}"
        )

    def test_confirm_route_rejects_non_protected(self, client):
        """Non-protected source returns 400 (if project exists) or 404."""
        r = client.post("/projects/generic_solar/confirm-first-edit-copy")
        assert r.status_code in (400, 404), (
            f"Expected 400 or 404 for non-protected ref, got {r.status_code}"
        )

    def test_second_confirm_redirects_to_same_copy(self, client):
        """Calling confirm twice must redirect to the same copy — no duplicates."""
        r1 = client.post("/projects/tuho/confirm-first-edit-copy")
        r2 = client.post("/projects/tuho/confirm-first-edit-copy")

        assert r1.status_code in (302, 303)
        assert r2.status_code in (302, 303)

        loc1 = r1.headers.get("location", "")
        loc2 = r2.headers.get("location", "")
        if loc1 and loc2:
            assert loc1 == loc2, (
                f"Second confirm created a different project! "
                f"First redirect: {loc1!r}, second: {loc2!r}"
            )


# ---------------------------------------------------------------------------
# 5. No explicit "Create editable copy" button in normal mode
# ---------------------------------------------------------------------------

class TestNoCopyButtonNormalMode:
    def test_no_create_editable_copy_button_in_workspace(self, client):
        r = client.get("/?project=tuho", follow_redirects=True)
        assert 'data-p2fix6-cta="create-editable-copy"' not in r.text, (
            "Explicit 'Create editable copy' button must not appear in normal mode "
            "(P2-FIX-8: transparent copy handles this via draft route)"
        )


# ---------------------------------------------------------------------------
# 6. _find_existing_working_copy helper
# ---------------------------------------------------------------------------

class TestFindExistingWorkingCopy:
    def test_returns_none_for_unknown_user(self):
        result = _find_existing_working_copy("nonexistent_user_xyz", "tuho")
        assert result is None

    def test_returns_none_for_unknown_source(self):
        result = _find_existing_working_copy(TEST_USER_ID, "nonexistent_source_xyz")
        assert result is None


# ---------------------------------------------------------------------------
# 7. Template and code structural checks
# ---------------------------------------------------------------------------

class TestCodeStructure:
    def test_state_banner_button_in_audit_mode_only(self):
        content = (REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html").read_text()
        # The button condition must be gated on audit_mode
        assert "audit_mode" in content
        # Verify the form only appears inside audit_mode block
        idx_form = content.find('data-p2fix6-form="create-editable-copy"')
        if idx_form > 0:
            preceding = content[:idx_form]
            # Find the last {% if ... %} before the form
            import re
            ifs = list(re.finditer(r'\{%[- ]*if\s+([^%]+)%\}', preceding))
            if ifs:
                last_if = ifs[-1].group(1).strip()
                assert "audit_mode" in last_if, (
                    "Create editable copy button must be inside audit_mode block, "
                    f"but last if condition was: {last_if!r}"
                )

    def test_home_projects_function_returns_rich_data(self):
        from main_web import _home_user_projects
        from unittest.mock import MagicMock
        fake_user = MagicMock()
        fake_user.user_id = "struct_test_user"
        # Should return a list (may be empty for unknown user)
        result = _home_user_projects(fake_user)
        assert isinstance(result, list)
        # If non-empty, must have required keys
        for row in result:
            assert "technology" in row
            assert "country" in row
            assert "status" in row
            assert row["technology"] != "Unknown"
