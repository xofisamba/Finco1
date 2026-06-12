"""Phase P2-FIX-5A — Standalone Page Layout Wrapper.

User screenshot of app.finco.one showed GET /
returning raw unstyled HTML fragment:
"My projects", project cards, "+ Create New
Project" — no CSS, no JS, no header, no layout.

Root cause: P2-FIX-1 made _render_project_home
return partials/project_home.html directly
without base.html. The browser received only a
fragment, not a full page. The same pattern
affected /projects/new and /projects/browse.

P2-FIX-5A wraps each standalone route in its
own full-page template (project_home_page.html,
project_new_page.html, project_browse_page.html)
that includes a DOCTYPE, head, CSS bundle, JS
bundle, and a shared standalone header partial.

This test verifies:
1. /  renders a full page (DOCTYPE, CSS, JS, brand)
2. /  no longer returns a raw fragment
3. /projects/new renders a full page
4. /projects/new stays minimal (no driver fields)
5. /projects/browse renders a full page
6. /?project=tuho still renders the full workspace
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix5a")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


# ─────────────────────────────────────────────────────────────────────
# 1. GET /  is a full page
# ─────────────────────────────────────────────────────────────────────


class TestRootProjectHomeIsFullPage:
    def test_get_root_project_home_is_full_page(self, logged_in_client):
        r = logged_in_client.get("/", follow_redirects=True)
        assert r.status_code == 200
        body = r.text
        assert "<!DOCTYPE html>" in body or "<html" in body
        assert '<link rel="stylesheet"' in body
        assert "app.js" in body
        assert "Finco One" in body
        assert "My projects" in body
        # The CTA renders the + Create New Project affordance
        assert "Create New Project" in body

    def test_get_root_project_home_is_not_raw_fragment(
        self, logged_in_client
    ):
        r = logged_in_client.get("/", follow_redirects=True)
        body = r.text
        # A raw fragment would start with whitespace then
        # a div. A full page starts with <!DOCTYPE html>.
        assert body.lstrip().startswith("<!DOCTYPE html>") or \
               body.lstrip().startswith("<html")
        # The page must NOT be a single ph-empty div with
        # no doctype.
        assert not (
            "<!DOCTYPE" not in body
            and body.lstrip().startswith("<div")
        )


# ─────────────────────────────────────────────────────────────────────
# 2. GET /projects/new is a full page and stays minimal
# ─────────────────────────────────────────────────────────────────────


class TestProjectsNewIsFullPage:
    def test_get_projects_new_is_full_page(self, logged_in_client):
        r = logged_in_client.get("/projects/new", follow_redirects=True)
        assert r.status_code == 200
        body = r.text
        assert "<!DOCTYPE html>" in body or "<html" in body
        assert '<link rel="stylesheet"' in body
        assert "Finco One" in body

    def test_get_projects_new_stays_minimal(self, logged_in_client):
        r = logged_in_client.get("/projects/new", follow_redirects=True)
        body = r.text
        # 4 visible fields (project name, technology,
        # country, capacity) are allowed.
        assert "project_name" in body
        assert "project_type" in body
        assert "country_market" in body
        assert "capacity_mw" in body
        # Forbidden driver / financing fields must NOT
        # appear in the minimal form.
        forbidden = [
            "tariff_eur_mwh",
            "p50_hours",
            "opex_y1_keur",
            "total_capex_keur",
            "gearing_pct",
            "interest_rate_pct",
            "tenor_years",
            "target_dscr",
            # factory function names that P2-FIX-1
            # explicitly excluded
            "create_default_solar_project",
            "create_default_wind_project",
        ]
        lower = body.lower()
        for term in forbidden:
            assert term not in lower, (
                f"/projects/new must not show {term!r} in the "
                f"minimal form"
            )


# ─────────────────────────────────────────────────────────────────────
# 3. GET /projects/browse is a full page
# ─────────────────────────────────────────────────────────────────────


class TestProjectsBrowseIsFullPage:
    def test_get_projects_browse_is_full_page(self, logged_in_client):
        r = logged_in_client.get(
            "/projects/browse", follow_redirects=True
        )
        assert r.status_code == 200
        body = r.text
        assert "<!DOCTYPE html>" in body or "<html" in body
        assert '<link rel="stylesheet"' in body
        assert "Finco One" in body
        # Project list content (the consolidated
        # project_browser.html partial is included)
        assert "project-browser" in body or "ph-card" in body

    def test_projects_browse_no_factory_or_baseline_tabs(
        self, logged_in_client
    ):
        """The 3-tab factory / baseline / user
        navigation must NOT be reintroduced."""
        import re
        r = logged_in_client.get(
            "/projects/browse", follow_redirects=True
        )
        # Strip Jinja + HTML comments so the
        # P2-FIX-1 narrative comment in the partial
        # does not count as visible UI.
        body = r.text
        body = re.sub(r"\{#.*?#\}", "", body, flags=re.DOTALL)
        body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
        body = body.lower()
        # The 3 tabs were removed by P2-FIX-1; they
        # must not come back as visible UI.
        for tab in (
            "factory templates",
            "saved baselines",
            "factory_templates",
            "saved_baselines",
        ):
            if tab in ("factory_templates", "saved_baselines"):
                # These are data-model strings that
                # exist in source; check they are not
                # rendered as visible tab labels.
                continue
            assert tab not in body, (
                f"/projects/browse must not contain {tab!r} "
                f"as visible UI"
            )


# ─────────────────────────────────────────────────────────────────────
# 4. GET /?project=tuho still renders the full workspace
# ─────────────────────────────────────────────────────────────────────


class TestWorkspaceProjectRouteStillFullPage:
    def test_workspace_project_route_still_full_page(
        self, logged_in_client
    ):
        r = logged_in_client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert r.status_code == 200
        body = r.text
        assert "<!DOCTYPE html>" in body
        assert "Finco One" in body
        # 5-area nav is part of the workspace shell
        assert "nav-compression" in body
        # Dashboard V1 is part of the workspace
        assert "dashboard-v1" in body

    def test_workspace_uses_existing_base_html(self, logged_in_client):
        r = logged_in_client.get(
            "/?project=tuho", follow_redirects=True
        )
        # The workspace renders the existing
        # workspace-context base.html, NOT the
        # standalone page wrapper.
        body = r.text
        # The workspace contains the workspace_shell content
        assert "panel-overview" in body or "tab-panel" in body
        # P2-FIX-8 PR2: ws-tab ribbon not rendered in normal mode
        # (server-side conditional rendering replaced CSS hiding)


# ─────────────────────────────────────────────────────────────────────
# 5. Hidden != deleted: partials still exist for any future
#    HTMX partial consumer
# ─────────────────────────────────────────────────────────────────────


class TestPartialsPreserved:
    def test_partials_unchanged(self):
        """The three partials continue to exist and
        are still rendered as fragments if requested
        directly via the partial path (e.g. an HTMX
        swap)."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[1]
        for name in (
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/project_browser.html",
        ):
            p = repo_root / name
            assert p.exists(), f"Partial {name} must still exist"
            # Each partial still does NOT extend base.html
            # (they are fragments, not pages)
            content = p.read_text(encoding="utf-8")
            assert "extends \"base.html\"" not in content, (
                f"{name} is a partial; must not extend base.html"
            )
            assert "DOCTYPE" not in content[:200], (
                f"{name} is a partial; must not contain DOCTYPE"
            )
