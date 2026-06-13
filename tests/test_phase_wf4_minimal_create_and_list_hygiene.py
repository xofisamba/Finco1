"""Phase WF-4 — Minimal Create & List Hygiene.

Acceptance criteria:
1. Create form has exactly 4 visible fields:
   project_name, project_type, country_market, capacity_mw.
2. Technology badges (ph-tech-badge) render in My Projects table.
3. Auto-dedup: creating a project with the same name twice gives
   a distinct project_code (the second gets a -2 suffix).
4. Create success renders create-form-success, not scenario-message.
5. Create form uses dedicated create-form-* CSS classes.
6. Engine MD5 unchanged.
7. File scope: only allowed files changed.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-wf4")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"


@pytest.fixture(scope="module")
def client():
    c = TestClient(app, follow_redirects=True)
    token = create_session_token(user_id="wf4_user", username="wf4_user")
    c.cookies.set("finco_session", token)
    # Seed factory projects for home table
    c.get("/?project=tuho")
    return c


# ---------------------------------------------------------------------------
# 1. Engine parity
# ---------------------------------------------------------------------------

class TestEngineParity:
    def test_engine_md5_unchanged(self):
        md5 = hashlib.md5(
            (REPO_ROOT / "app" / "waterfall_core.py").read_bytes()
        ).hexdigest()
        assert md5 == ENGINE_MD5


# ---------------------------------------------------------------------------
# 2. Create form — 4 visible fields, dedicated CSS classes
# ---------------------------------------------------------------------------

class TestCreateForm:
    def test_new_project_page_renders(self, client):
        r = client.get("/projects/new")
        assert r.status_code == 200

    def test_form_has_project_name_field(self, client):
        r = client.get("/projects/new")
        assert 'name="project_name"' in r.text

    def test_form_has_project_type_field(self, client):
        r = client.get("/projects/new")
        assert 'name="project_type"' in r.text

    def test_form_has_country_market_field(self, client):
        r = client.get("/projects/new")
        assert 'name="country_market"' in r.text

    def test_form_has_capacity_mw_field(self, client):
        r = client.get("/projects/new")
        assert 'name="capacity_mw"' in r.text

    def test_form_uses_create_form_class(self, client):
        r = client.get("/projects/new")
        assert "create-form" in r.text, (
            "Create form must use create-form CSS class (not borrowed scenario-compare classes)"
        )

    def test_form_does_not_use_scenario_message_class(self, client):
        r = client.get("/projects/new")
        # scenario-message is a borrowed sidebar class — create form must use its own
        assert "scenario-message" not in r.text, (
            "Create form must not use scenario-message class (prod cleanup)"
        )

    def test_form_template_source_is_hidden(self, client):
        r = client.get("/projects/new")
        # template_source must be hidden, not a visible select
        m = re.search(r'<input[^>]*name="template_source"[^>]*>', r.text)
        assert m is not None, "template_source input not found"
        assert 'type="hidden"' in m.group(0), (
            "template_source must be a hidden input in the minimal form"
        )


# ---------------------------------------------------------------------------
# 3. Technology badges in My Projects table
# ---------------------------------------------------------------------------

class TestTechnologyBadges:
    def test_ph_tech_badge_class_present_in_home(self, client):
        # Create a user project so the home table renders
        c2 = TestClient(app, follow_redirects=True)
        token = create_session_token(user_id="wf4_badge_user", username="wf4b")
        c2.cookies.set("finco_session", token)
        c2.get("/?project=tuho")
        c2.post("/projects/tuho/confirm-first-edit-copy", data={})
        r = c2.get("/")
        assert "ph-tech-badge" in r.text, (
            "My Projects home table must render ph-tech-badge pills for technology"
        )

    def test_ph_tech_badge_css_rules_exist(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".ph-tech-badge" in css
        assert "ph-tech-badge--wind" in css
        assert "ph-tech-badge--solar" in css

    def test_wf4_marker_in_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert "WF-4" in css


# ---------------------------------------------------------------------------
# 4. Dedup: two projects with same name get distinct codes
# ---------------------------------------------------------------------------

class TestProjectDedup:
    def test_duplicate_name_gets_suffix(self):
        c = TestClient(app, follow_redirects=False)
        token = create_session_token(user_id="wf4_dedup", username="wf4d")
        c.cookies.set("finco_session", token)
        payload = {
            "project_name": "Dedup Test Project",
            "project_type": "Solar",
            "country_market": "Croatia",
            "capacity_mw": "10",
            "template_source": "generic_solar",
        }
        r1 = c.post("/projects/create", data=payload)
        assert r1.status_code in (200, 302)
        loc1 = r1.headers.get("HX-Redirect") or r1.headers.get("location", "")

        r2 = c.post("/projects/create", data=payload)
        assert r2.status_code in (200, 302)
        loc2 = r2.headers.get("HX-Redirect") or r2.headers.get("location", "")

        # The two project codes must be different
        assert loc1 != loc2, (
            "Two projects with the same name must get distinct codes"
        )


# ---------------------------------------------------------------------------
# 5. Success response uses create-form-success (not scenario-message)
# ---------------------------------------------------------------------------

class TestCreateSuccessResponse:
    def test_result_template_uses_create_form_success(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "new_project_result.html").read_text()
        assert "create-form-success" in tmpl, (
            "new_project_result.html must use create-form-success class"
        )
        assert "scenario-message" not in tmpl, (
            "new_project_result.html must not use scenario-message (prod cleanup)"
        )


# ---------------------------------------------------------------------------
# 6. CSS coverage for new create-form-* classes
# ---------------------------------------------------------------------------

class TestCreateFormCSS:
    def test_create_form_has_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        for cls in (
            ".create-form",
            ".create-form-label",
            ".create-form-input",
            ".create-form-select",
            ".create-form-actions",
            ".create-form-success",
            ".create-form-header",
            ".create-form-errors",
        ):
            assert cls in css, f"Missing CSS rule: {cls}"


# ---------------------------------------------------------------------------
# 7. File scope
# ---------------------------------------------------------------------------

class TestFileScope:
    def test_only_allowed_files_changed(self):
        import shutil
        import subprocess
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        allowed_prefixes = (
            "static/styles.css",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/new_project_result.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/project_selector.html",
            "main_web.py",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf5_",
            "tests/test_phase_wf6_",
            "tests/test_phase_p2fix",
            "app/templates/",
            "docs/phase_wf",
            "reports/phase_wf",
            "scripts/",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_m3_",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
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
            assert not any(f.startswith(p) for p in disallowed_prefixes), (
                f"Disallowed file changed: {f}"
            )
            assert any(f.startswith(p) for p in allowed_prefixes), (
                f"File outside allowed scope: {f}"
            )
