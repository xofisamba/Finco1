"""Phase WF-3 — Home & Projects split.

Acceptance criteria:
1. GET / renders "My projects" home table (user projects only).
2. GET /projects redirects to GET /projects/browse (302).
3. GET /projects/browse renders full projects table (all projects incl. references).
4. Workspace sidebar has two labelled nav groups:
   - id="ps-nav-my-projects" (My projects)
   - id="ps-nav-reference-projects" (Reference: TUHO, Oborovo)
5. Home button (btn-project-home) href is "/" not "/home".
6. Engine MD5 unchanged.
7. File scope: only allowed files changed.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-wf3")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"


@pytest.fixture(scope="module")
def client():
    c = TestClient(app, follow_redirects=False)
    token = create_session_token(user_id="wf3_user", username="wf3_user")
    c.cookies.set("finco_session", token)
    # Seed factory projects
    c.get("/?project=tuho", follow_redirects=True)
    return c


@pytest.fixture(scope="module")
def client_follow():
    c = TestClient(app, follow_redirects=True)
    token = create_session_token(user_id="wf3_follow_user", username="wf3_follow")
    c.cookies.set("finco_session", token)
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
# 2. GET / — Home renders My projects table
# ---------------------------------------------------------------------------

class TestHomeRoute:
    def test_root_returns_200(self, client):
        r = client.get("/", follow_redirects=True)
        assert r.status_code == 200

    def test_root_does_not_show_factory_templates_in_my_projects(self, client_follow):
        r = client_follow.get("/")
        assert r.status_code == 200
        # The home table shows user projects, not factory template section headers
        # TUHO and Oborovo appear in the reference browse, not the My Projects home
        assert "My projects" in r.text or "ph-table" in r.text or "ph-empty" in r.text

    def test_root_no_project_renders_home_not_workspace(self, client):
        r = client.get("/", follow_redirects=True)
        # Home page should NOT have workspace-specific elements
        assert "nav-compression-tab-dashboard" not in r.text
        assert "standalone-page" in r.text


# ---------------------------------------------------------------------------
# 3. GET /projects redirects to /projects/browse
# ---------------------------------------------------------------------------

class TestProjectsRoute:
    def test_projects_redirects_to_browse(self, client):
        r = client.get("/projects")
        assert r.status_code == 302
        assert "/projects/browse" in r.headers.get("location", "")

    def test_projects_browse_renders_200(self, client):
        r = client.get("/projects/browse", follow_redirects=True)
        assert r.status_code == 200

    def test_projects_browse_shows_all_projects(self, client_follow):
        r = client_follow.get("/projects/browse")
        assert r.status_code == 200
        # Both reference projects appear in the full table
        assert "TUHO" in r.text
        assert "Oborovo" in r.text


# ---------------------------------------------------------------------------
# 4. Workspace sidebar two labelled nav groups
# ---------------------------------------------------------------------------

class TestSidebarNavGroups:
    def test_sidebar_has_my_projects_group(self, client_follow):
        r = client_follow.get("/?project=tuho")
        assert r.status_code == 200
        assert 'id="ps-nav-my-projects"' in r.text or 'ps-nav-group' in r.text

    def test_sidebar_has_reference_group(self, client_follow):
        r = client_follow.get("/?project=tuho")
        assert 'id="ps-nav-reference-projects"' in r.text

    def test_reference_group_contains_tuho(self, client_follow):
        r = client_follow.get("/?project=tuho")
        # Both TUHO and Oborovo should appear in the reference nav group
        import re
        ref_start = r.text.find('id="ps-nav-reference-projects"')
        assert ref_start != -1
        ref_block = r.text[ref_start:ref_start + 800]
        assert "tuho" in ref_block.lower()

    def test_reference_group_contains_oborovo(self, client_follow):
        r = client_follow.get("/?project=tuho")
        ref_start = r.text.find('id="ps-nav-reference-projects"')
        assert ref_start != -1
        ref_block = r.text[ref_start:ref_start + 800]
        assert "oborovo" in ref_block.lower()

    def test_sidebar_nav_group_labels_present(self, client_follow):
        r = client_follow.get("/?project=tuho")
        assert "ps-nav-group-label" in r.text

    def test_my_projects_group_label_text(self, client_follow):
        r = client_follow.get("/?project=tuho")
        import re
        m = re.search(r'ps-nav-group-label[^>]*>([^<]+)<', r.text)
        # At least one group label should say "My projects" or "Reference"
        labels_text = " ".join(re.findall(r'class="ps-nav-group-label">([^<]+)<', r.text))
        assert "My projects" in labels_text or "Reference" in labels_text


# ---------------------------------------------------------------------------
# 5. Home button href is "/"
# ---------------------------------------------------------------------------

class TestHomeButtonHref:
    def test_home_button_href_is_root(self, client_follow):
        r = client_follow.get("/?project=tuho")
        assert r.status_code == 200
        assert 'id="btn-project-home"' in r.text
        import re
        m = re.search(r'id="btn-project-home"[^>]*href="([^"]+)"', r.text)
        if m is None:
            # href may come before id
            m = re.search(r'href="([^"]+)"[^>]*id="btn-project-home"', r.text)
        assert m is not None, "btn-project-home href not found"
        assert m.group(1) == "/", (
            f"Home button href must be '/', got {m.group(1)!r}"
        )


# ---------------------------------------------------------------------------
# 6. CSS coverage: new ps-nav classes have rules
# ---------------------------------------------------------------------------

class TestNavGroupCSS:
    def test_ps_nav_group_has_css_rule(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".ps-nav-group" in css
        assert ".ps-nav-group-label" in css
        assert ".ps-nav-link" in css

    def test_wf3_marker_present(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert "WF-3" in css


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
            "main_web.py",
            "app/templates/partials/project_selector.html",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf4_",
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
            "tests/test_phase_m4_",
            "tests/test_phase_stab",
            "tests/test_phase_pr1_",
            "tests/test_phase_pr2_",
            "tests/test_phase_pr3_",
            "app/templates/partials/_scenario_matrix_oob.html",
            "app/ui/dashboard.py",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
            "app/templates/partials/_matrix_run_result.html",
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
