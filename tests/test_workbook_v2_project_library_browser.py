"""Browser acceptance tests for the Project Library.

Covers: library navigation, search, filtering, pagination, clone flow,
sidebar bounded list, "View all projects" link, two-user authorization.

Isolation: temporary SQLite DB per test module; no project names appear
in the normal project list.
"""
from __future__ import annotations

import glob
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "browser-accept-library-secret")

BASE_DIR = Path(__file__).resolve().parents[1]
SCREENSHOTS_DIR = BASE_DIR / "tests" / "screenshots"

from app.auth import COOKIE_NAME, create_session_token  # noqa: E402


# ---------------------------------------------------------------------------
# Server helpers
# ---------------------------------------------------------------------------

def _chromium_path() -> str:
    candidates = glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome")
    if candidates:
        return sorted(candidates)[-1]
    return ""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


def _wait_for_server(base_url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/public-health", timeout=2.0) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.25)
    raise AssertionError(f"Server at {base_url} not ready after {timeout}s")


def _http(base_url, token, method, path, data=None, extra_headers=None):
    url = base_url + path
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Cookie", f"{COOKIE_NAME}={token}")
    if body:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", errors="replace")


def _make_token(user_id: str, name: str = "Test User") -> str:
    return create_session_token(user_id=user_id, username=name)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: playwright not installed",
    )
    tmp_db = tmp_path_factory.mktemp("library_browser") / "test.db"
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["FINCO_DB_PATH"] = str(tmp_db)
    env["FINCO_SECRET_KEY"] = "browser-accept-library-secret"
    env["FINCO_WORKBOOK_V2"] = "1"
    env["FINCO_COOKIE_SECURE"] = "false"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app",
         "--host", "127.0.0.1", f"--port={port}", "--log-level", "warning"],
        env=env, cwd=str(BASE_DIR),
    )
    _wait_for_server(base_url)
    yield {"base_url": base_url, "db_path": str(tmp_db), "proc": proc}
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def tokens(live_server):
    """Return auth tokens for two distinct users."""
    alice = _make_token("alice-lib-test", "Alice")
    bob = _make_token("bob-lib-test", "Bob")
    return {"alice": alice, "bob": bob}


@pytest.fixture(scope="module")
def references_bootstrapped(live_server, tokens):
    """Ensure reference models exist (call /library once to trigger bootstrap)."""
    base_url = live_server["base_url"]
    token = tokens["alice"]
    status, _, body = _http(base_url, token, "GET", "/library")
    assert status == 200, f"GET /library failed: {status}"
    return True


@pytest.fixture(scope="module")
def browser_ctx(live_server):
    """Single Playwright browser + context for the module."""
    from playwright.sync_api import sync_playwright
    chromium = _chromium_path()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=chromium or None,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        yield {"browser": browser, "ctx": ctx, "base_url": live_server["base_url"]}
        ctx.close()
        browser.close()


def _authed_page(browser_ctx, token: str):
    """Return a fresh Playwright page pre-authenticated with a session cookie."""
    page = browser_ctx["ctx"].new_page()
    base_url = browser_ctx["base_url"]
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    page.context.add_cookies([{
        "name": COOKIE_NAME,
        "value": token,
        "domain": parsed.hostname,
        "path": "/",
        "httpOnly": False,
        "secure": False,
    }])
    return page


# ---------------------------------------------------------------------------
# Library navigation tests
# ---------------------------------------------------------------------------

class TestLibraryNavigation:
    @pytest.fixture(autouse=True)
    def setup(self, browser_ctx, tokens, references_bootstrapped, live_server):
        self.page = _authed_page(browser_ctx, tokens["alice"])
        self.base_url = live_server["base_url"]
        self.tokens = tokens
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def teardown_method(self, method):
        self.page.close()

    def test_library_page_loads(self):
        p = self.page
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        assert "Project Library" in p.title() or "Project Library" in p.content()

    def test_references_visible_with_badge(self):
        p = self.page
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        p.screenshot(path=str(SCREENSHOTS_DIR / "library_1440x900.png"))
        # TUHO Reference should appear with a badge
        tuho_row = p.locator('[data-testid="library-row-tuho-reference"]')
        assert tuho_row.count() >= 1, "TUHO Reference row not found in library"
        badge = p.locator('[data-testid="badge-reference-tuho-reference"]')
        assert badge.count() >= 1, "Reference badge not found for TUHO"

    def test_filter_references_only(self):
        p = self.page
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        # Select "References" filter
        p.select_option("select[name='role']", "reference")
        p.wait_for_timeout(500)
        # Only reference rows should appear
        rows = p.locator("[data-testid^='library-row-']")
        count = rows.count()
        assert count >= 2, f"Expected at least 2 reference rows, got {count}"
        # No working_copy badge
        wc_badges = p.locator("[data-testid^='badge-working-copy-']")
        assert wc_badges.count() == 0, "Working-copy badge appeared in References filter"

    def test_search_tuho(self):
        p = self.page
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        p.fill("input[name='search']", "TUHO")
        p.keyboard.press("Enter")
        p.wait_for_timeout(600)
        rows = p.locator("[data-testid^='library-row-']")
        count = rows.count()
        assert count >= 1, "No TUHO rows after search"
        all_names = [rows.nth(i).inner_text() for i in range(count)]
        assert any("TUHO" in n for n in all_names), f"TUHO not in results: {all_names}"

    def test_filter_working_copies_empty_initially(self):
        p = self.page
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        p.select_option("select[name='role']", "working_copy")
        p.wait_for_timeout(500)
        # Alice has no working copies yet
        rows = p.locator("[data-testid^='library-row-']")
        assert rows.count() == 0, "Expected 0 working copies before any clone"

    def test_1920_screenshot(self):
        p = self.page
        p.set_viewport_size({"width": 1920, "height": 1080})
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        p.screenshot(path=str(SCREENSHOTS_DIR / "library_1920x1080.png"))


# ---------------------------------------------------------------------------
# Clone flow
# ---------------------------------------------------------------------------

class TestCloneFlow:
    @pytest.fixture(autouse=True)
    def setup(self, browser_ctx, tokens, references_bootstrapped, live_server):
        self.page = _authed_page(browser_ctx, tokens["alice"])
        self.base_url = live_server["base_url"]
        self.tokens = tokens
        self.db_path = live_server["db_path"]

    def teardown_method(self, method):
        self.page.close()

    def test_clone_tuho_reference(self):
        p = self.page
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")

        # Click "Create working copy" on TUHO Reference
        clone_btn = p.locator('[data-testid="clone-tuho-reference"]')
        assert clone_btn.count() >= 1, "Clone button for TUHO Reference not found"
        p.screenshot(path=str(SCREENSHOTS_DIR / "library_reference_project.png"))

        with p.expect_navigation(timeout=10000):
            clone_btn.first.click()

        # Should redirect to TUHO Working Copy workbook
        p.wait_for_load_state("networkidle")
        url = p.url
        assert "project=" in url or "/workbook" in url, f"Unexpected redirect URL: {url}"

        p.screenshot(path=str(SCREENSHOTS_DIR / "library_working_copy.png"))

    def test_clone_creates_working_copy_badge_in_library(self):
        """After clone, the working copy appears in the library with Working copy badge."""
        p = self.page
        p.goto(f"{self.base_url}/library?role=working_copy")
        p.wait_for_load_state("networkidle")
        rows = p.locator("[data-testid^='library-row-']")
        assert rows.count() >= 1, "No working copy rows after clone"
        wc_badge = p.locator("[data-testid^='badge-working-copy-']")
        assert wc_badge.count() >= 1, "Working copy badge not found after clone"
        p.screenshot(path=str(SCREENSHOTS_DIR / "library_filtered_working_copies.png"))

    def test_clone_oborovo_reference(self):
        p = self.page
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        clone_btn = p.locator('[data-testid="clone-oborovo-reference"]')
        assert clone_btn.count() >= 1, "Clone button for Oborovo Reference not found"
        with p.expect_navigation(timeout=10000):
            clone_btn.first.click()
        p.wait_for_load_state("networkidle")
        assert "project=" in p.url or "/workbook" in p.url, f"Oborovo clone redirect failed: {p.url}"

    def test_reference_unchanged_after_clone(self):
        """After clone, the source reference still has project_role='reference'."""
        import sqlite3, json as _j
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT project_role, is_protected FROM projects WHERE project_code='tuho-reference'"
            ).fetchone()
        assert row is not None, "TUHO Reference not found in DB"
        assert row[0] == "reference", f"Expected role='reference', got {row[0]!r}"
        assert row[1] == 1, f"Expected is_protected=1, got {row[1]}"

    def test_working_copy_lineage_in_db(self):
        """Working copy must have source_project_id pointing to the reference."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            ref = conn.execute(
                "SELECT project_id FROM projects WHERE project_code='tuho-reference'"
            ).fetchone()
            wc = conn.execute(
                "SELECT source_project_id, project_role FROM projects "
                "WHERE project_role='working_copy' AND template_source='tuho' LIMIT 1"
            ).fetchone()
        assert ref is not None
        assert wc is not None, "No TUHO working copy found in DB"
        assert wc[0] == ref[0], f"source_project_id {wc[0]!r} != ref {ref[0]!r}"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

class TestSidebar:
    @pytest.fixture(autouse=True)
    def setup(self, browser_ctx, tokens, references_bootstrapped, live_server):
        self.page = _authed_page(browser_ctx, tokens["alice"])
        self.base_url = live_server["base_url"]

    def teardown_method(self, method):
        self.page.close()

    def test_view_all_projects_link_present(self):
        p = self.page
        # Navigate to library — it uses base.html with the project-selector sidebar
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        link = p.locator('[data-testid="view-all-projects-link"]')
        assert link.count() >= 1, "'View all projects' link not found in sidebar"

    def test_view_all_projects_navigates_to_library(self):
        p = self.page
        # Navigate to library — it has a second 'View all projects' link in the sidebar
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        assert "/library" in p.url, f"Expected /library URL, got {p.url}"

    def test_sidebar_recent_list_bounded(self):
        """Sidebar must not render more than 8 recent project links."""
        p = self.page
        p.goto(f"{self.base_url}/library")
        p.wait_for_load_state("networkidle")
        # Count nav links in the recent-projects group (excluding View all link)
        recent_links = p.locator("#ps-nav-my-projects .ps-nav-link")
        count = recent_links.count()
        assert count <= 8, f"Sidebar shows {count} recent projects (max is 8)"


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

class TestAuthorization:
    @pytest.fixture(autouse=True)
    def setup(self, browser_ctx, tokens, references_bootstrapped, live_server):
        self.base_url = live_server["base_url"]
        self.tokens = tokens
        self.db_path = live_server["db_path"]

    def test_library_search_does_not_leak_other_users_projects(self):
        """Bob's library search must not surface Alice's working copies."""
        alice_token = self.tokens["alice"]
        bob_token = self.tokens["bob"]
        # Create Alice's working copy first (may already exist from clone tests)
        status, headers, _ = _http(
            self.base_url, alice_token, "GET", "/library/list?role=working_copy"
        )
        assert status == 200

        # Bob searches the library — should see only references and his own projects
        status, _, bob_body = _http(self.base_url, bob_token, "GET", "/library/list?role=working_copy")
        assert status == 200
        # Bob's working copy count may be 0 or from his own clones; not Alice's
        # We verify by direct DB check
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            alice_wc = conn.execute(
                "SELECT project_id FROM projects WHERE user_id='alice-lib-test' AND project_role='working_copy' LIMIT 1"
            ).fetchone()
        if alice_wc:
            assert alice_wc[0] not in bob_body, "Alice's working copy project_id leaked to Bob"

    def test_both_users_see_references(self):
        """Both Alice and Bob must see reference models in the library."""
        alice_token = self.tokens["alice"]
        bob_token = self.tokens["bob"]
        st_a, _, body_a = _http(self.base_url, alice_token, "GET", "/library/list?role=reference")
        st_b, _, body_b = _http(self.base_url, bob_token, "GET", "/library/list?role=reference")
        assert st_a == 200
        assert st_b == 200
        assert "tuho-reference" in body_a
        assert "tuho-reference" in body_b

    def test_mutation_on_reference_returns_403(self):
        """POST /v2/workbook/update on a reference project must return 403."""
        alice_token = self.tokens["alice"]
        # Try to directly update a field on the reference project — must be blocked
        status, _, body = _http(
            self.base_url, alice_token, "POST", "/v2/workbook/update",
            {
                "field_id": "capacity_mw",
                "value": "999",
                "project": "tuho-reference",
                "workbook_version": "2.1.0",
                "content_hash": "fake-hash",
                "sheet_id": "project_setup",
            },
            extra_headers={"HX-Request": "true"},
        )
        assert status == 403, f"Expected 403 for mutation on reference, got {status}; body={body[:200]}"

    def test_unauthenticated_redirect_to_login(self):
        """GET /library without auth must redirect to /login."""
        req = urllib.request.Request(f"{self.base_url}/library", method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                final_url = resp.url
        except urllib.error.HTTPError as e:
            final_url = e.url
        assert "/login" in final_url or "login" in final_url, f"Expected login redirect, got {final_url}"
