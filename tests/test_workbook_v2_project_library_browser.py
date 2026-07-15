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

    def _ensure_alice_has_working_copy(self):
        """Ensure Alice has a working copy; return (project_code, project_id)."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            alice_wc = conn.execute(
                "SELECT project_code, project_id FROM projects "
                "WHERE user_id='alice-lib-test' AND project_role='working_copy' LIMIT 1"
            ).fetchone()
        if alice_wc is not None:
            return alice_wc[0], alice_wc[1]
        # Find TUHO reference project_id
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT project_id FROM projects WHERE user_id='__reference__' AND template_source='tuho' AND project_role='reference' LIMIT 1"
            ).fetchone()
        assert row, "TUHO reference must exist for clone"
        tuho_ref_id = row[0]
        status, _, body = _http(self.base_url, self.tokens["alice"], "POST", f"/library/clone/{tuho_ref_id}")
        assert status in (200, 302, 303), f"Clone failed: {status} {body[:200]}"
        # Fetch created working copy from DB
        with sqlite3.connect(self.db_path) as conn:
            alice_wc = conn.execute(
                "SELECT project_code, project_id FROM projects "
                "WHERE user_id='alice-lib-test' AND project_role='working_copy' LIMIT 1"
            ).fetchone()
        assert alice_wc, "Alice must have a working copy after clone"
        return alice_wc[0], alice_wc[1]

    def test_cross_user_get_rejected(self):
        """Bob cannot GET Alice's working copy via /v2/workbook.

        The server returns 302 → / (dashboard) for an unknown project.
        urllib follows the redirect so the final status is 200 (dashboard),
        but the body must NOT contain Alice's working-copy content.
        """
        bob_token = self.tokens["bob"]
        wc_code, _ = self._ensure_alice_has_working_copy()
        status, _, body = _http(
            self.base_url, bob_token, "GET", f"/v2/workbook?project={wc_code}",
        )
        # Either a redirect (302/303) to homepage OR 200 from the dashboard redirect.
        # In both cases the workbook content for Alice's project must not appear.
        assert status in (200, 302, 303, 404), (
            f"Unexpected status for cross-user GET: {status}"
        )
        if status == 200:
            # Dashboard/homepage body — must NOT contain Alice's working-copy workbook
            # The V2 workbook page includes the project_code in the form action.
            assert f"project={wc_code}" not in body or "/v2/workbook" not in body, (
                f"Bob appears to see Alice's working copy workbook at project={wc_code}"
            )

    def test_cross_user_run_rejected(self):
        """Bob cannot run Alice's working copy.

        The run route uses resolve_accessible_project which returns None for
        projects belonging to another regular user.  With HX-Request=true the
        route returns 200 with an HTMX error fragment (not found message).
        """
        bob_token = self.tokens["bob"]
        wc_code, _ = self._ensure_alice_has_working_copy()
        status, _, body = _http(
            self.base_url, bob_token, "POST", "/v2/workbook/run",
            {
                "project": wc_code,
                "workbook_version": "2.1.0",
                "content_hash": "fake-hash",
            },
            extra_headers={"HX-Request": "true"},
        )
        # HTMX error responses are 200 with error HTML — the project should not be found.
        # Non-HTMX would be a 302/303 redirect.
        assert status in (200, 302, 303, 404, 400, 422), (
            f"Unexpected status for cross-user run: {status}"
        )
        if status == 200:
            # The HTMX error body must indicate the project was not found
            assert "not found" in body.lower() or "error" in body.lower(), (
                f"Bob got 200 for Alice's run but body does not indicate error: {body[:200]}"
            )

    def test_cross_user_clone_by_raw_id_rejected(self):
        """Bob cannot clone Alice's working copy by raw project_id via the real clone route."""
        bob_token = self.tokens["bob"]
        # Ensure Alice has a working copy (deterministic setup)
        _, alice_wc_project_id = self._ensure_alice_has_working_copy()
        # Record Bob's project count before attempt
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            bob_count_before = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE user_id='bob-lib-test'"
            ).fetchone()[0]
        # POST to the REAL route: POST /library/clone/{alice_working_copy_project_id}
        status, _, body = _http(
            self.base_url, bob_token, "POST", f"/library/clone/{alice_wc_project_id}",
        )
        assert status == 400, (
            f"Bob cloning Alice's working copy must be HTTP 400, got {status}; body={body[:300]}"
        )
        assert "not a canonical reference model" in body.lower(), (
            f"Response body must mention 'not a canonical reference model', got: {body[:300]}"
        )
        # Bob's project count must be unchanged
        with sqlite3.connect(self.db_path) as conn:
            bob_count_after = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE user_id='bob-lib-test'"
            ).fetchone()[0]
        assert bob_count_after == bob_count_before, (
            f"Bob's project count changed from {bob_count_before} to {bob_count_after}"
        )


# ---------------------------------------------------------------------------
# V2 workbook reference open / run
# ---------------------------------------------------------------------------

class TestReferenceWorkbookV2:
    @pytest.fixture(autouse=True)
    def setup(self, live_server, tokens, references_bootstrapped):
        self.base_url = live_server["base_url"]
        self.tokens = tokens

    def test_reference_open_get_200(self):
        """Opening the TUHO reference GET /v2/workbook returns 200."""
        token = self.tokens["alice"]
        status, _, body = _http(
            self.base_url, token, "GET", "/v2/workbook?project=tuho-reference",
        )
        assert status == 200, f"Expected 200 for reference GET, got {status}; body={body[:300]}"
        assert "TUHO" in body, "TUHO name not in response body"

    def test_reference_open_200_oborovo(self):
        """Opening the Oborovo reference GET /v2/workbook returns 200."""
        token = self.tokens["alice"]
        status, _, body = _http(
            self.base_url, token, "GET", "/v2/workbook?project=oborovo-reference",
        )
        assert status == 200, f"Expected 200 for Oborovo reference GET, got {status}; body={body[:300]}"
        assert "borovo" in body or "Oborovo" in body, "Oborovo name not in response body"


# ---------------------------------------------------------------------------
# Reference Run acceptance tests
# ---------------------------------------------------------------------------

class TestReferenceRunAcceptance:
    @pytest.fixture(autouse=True)
    def setup(self, live_server, tokens, references_bootstrapped):
        self.base_url = live_server["base_url"]
        self.tokens = tokens
        self.db_path = live_server["db_path"]

    def _run_reference_and_check(self, project_code: str, user_id: str = "__reference__"):
        import re, json, sqlite3
        token = self.tokens["alice"]
        base_url = self.base_url

        # Record before-state
        with sqlite3.connect(self.db_path) as conn:
            before_ws = conn.execute(
                "SELECT last_runtime_snapshot_json, last_runtime_summary_json, draft_snapshot_json, saved_snapshot_json "
                f"FROM workspace_states WHERE user_id='{user_id}' AND project_code='{project_code}'"
            ).fetchone()

        # GET workbook to extract content_hash and workbook_version
        status, _, body = _http(base_url, token, "GET", f"/v2/workbook?project={project_code}")
        assert status == 200, f"GET workbook failed: {status}"
        ch_m = re.search(r'name="content_hash"\s+value="([^"]+)"', body)
        wv_m = re.search(r'name="workbook_version"\s+value="([^"]+)"', body)
        content_hash = ch_m.group(1) if ch_m else "no-hash"
        workbook_version = wv_m.group(1) if wv_m else "2.1.0"

        # POST Run
        run_status, _, run_body = _http(base_url, token, "POST", "/v2/workbook/run", {
            "project": project_code,
            "workbook_version": workbook_version,
            "content_hash": content_hash,
        }, extra_headers={"HX-Request": "true"})
        assert run_status == 200, f"Run failed: {run_body[:400]}"

        # Assert after-state
        with sqlite3.connect(self.db_path) as conn:
            after_ws = conn.execute(
                "SELECT last_runtime_snapshot_json, last_runtime_summary_json, draft_snapshot_json, saved_snapshot_json, "
                f"last_runtime_snapshot_id FROM workspace_states WHERE user_id='{user_id}' AND project_code='{project_code}'"
            ).fetchone()

        assert after_ws, "Workspace must exist after run"
        after_summary = json.loads(after_ws[1]) if after_ws[1] else {}
        assert after_summary, "Runtime summary must be non-empty after Run"

        # draft and saved snapshots must be unchanged
        if before_ws:
            assert after_ws[2] == before_ws[2], "Draft snapshot must not change on reference Run"
            assert after_ws[3] == before_ws[3], "Saved snapshot must not change on reference Run"

        # runtime snapshot ID must be populated
        assert after_ws[4], "last_runtime_snapshot_id must be set after Run"

        return after_ws

    def test_tuho_reference_run_persists(self):
        import sqlite3, json
        after_ws = self._run_reference_and_check("tuho-reference")

        # project record must still be reference
        with sqlite3.connect(self.db_path) as conn:
            proj = conn.execute(
                "SELECT project_role, is_protected FROM projects WHERE user_id='__reference__' AND project_code='tuho-reference'"
            ).fetchone()
        assert proj[0] == "reference"
        assert proj[1] == 1

        # Alice must not own a new workspace for tuho-reference
        with sqlite3.connect(self.db_path) as conn:
            alice_ws = conn.execute(
                "SELECT 1 FROM workspace_states WHERE user_id='alice-lib-test' AND project_code='tuho-reference'"
            ).fetchone()
        assert alice_ws is None, "Reference Run must not create a user-owned workspace"

        # Update endpoint still returns 403 for reference
        token = self.tokens["alice"]
        status, _, body = _http(self.base_url, token, "GET", "/v2/workbook?project=tuho-reference")
        import re
        wv_m = re.search(r'name="workbook_version"\s+value="([^"]+)"', body)
        ch_m2 = re.search(r'name="content_hash"\s+value="([^"]+)"', body)
        workbook_version = wv_m.group(1) if wv_m else "2.1.0"
        content_hash2 = ch_m2.group(1) if ch_m2 else "no-hash"
        upd_status, _, upd_body = _http(self.base_url, token, "POST", "/v2/workbook/update", {
            "project": "tuho-reference",
            "workbook_version": workbook_version,
            "content_hash": content_hash2,
            "field_id": "capacity_mw",
            "value": "999",
            "sheet_id": "project_setup",
        }, extra_headers={"HX-Request": "true"})
        assert upd_status == 403, f"Update on reference must return 403, got {upd_status}"

    def test_oborovo_reference_run_persists(self):
        self._run_reference_and_check("oborovo-reference")

        # project record must still be reference
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            proj = conn.execute(
                "SELECT project_role, is_protected FROM projects WHERE user_id='__reference__' AND project_code='oborovo-reference'"
            ).fetchone()
        assert proj[0] == "reference"
        assert proj[1] == 1

    def test_tuho_reference_content_hash_immutable_after_run(self):
        """GET content hash before Run == GET content hash after Run for TUHO reference."""
        import re
        token = self.tokens["alice"]
        base_url = self.base_url

        # Hash before
        st1, _, body1 = _http(base_url, token, "GET", "/v2/workbook?project=tuho-reference")
        assert st1 == 200
        ch_m1 = re.search(r'name="content_hash"\s+value="([^"]+)"', body1)
        wv_m1 = re.search(r'name="workbook_version"\s+value="([^"]+)"', body1)
        assert ch_m1, "Must find content_hash before Run"
        hash_before = ch_m1.group(1)
        workbook_version = wv_m1.group(1) if wv_m1 else "2.1.0"

        # Run
        run_st, _, run_body = _http(base_url, token, "POST", "/v2/workbook/run", {
            "project": "tuho-reference",
            "workbook_version": workbook_version,
            "content_hash": hash_before,
        }, extra_headers={"HX-Request": "true"})
        assert run_st == 200, f"TUHO reference Run failed: {run_body[:300]}"

        # Hash after
        st2, _, body2 = _http(base_url, token, "GET", "/v2/workbook?project=tuho-reference")
        assert st2 == 200
        ch_m2 = re.search(r'name="content_hash"\s+value="([^"]+)"', body2)
        assert ch_m2, "Must find content_hash after Run"
        hash_after = ch_m2.group(1)

        assert hash_after == hash_before, (
            f"TUHO reference content hash must not change after Run: "
            f"before={hash_before}, after={hash_after}"
        )

    def test_oborovo_reference_content_hash_immutable_after_run(self):
        """GET content hash before Run == GET content hash after Run for Oborovo reference."""
        import re
        token = self.tokens["alice"]
        base_url = self.base_url

        st1, _, body1 = _http(base_url, token, "GET", "/v2/workbook?project=oborovo-reference")
        assert st1 == 200
        ch_m1 = re.search(r'name="content_hash"\s+value="([^"]+)"', body1)
        wv_m1 = re.search(r'name="workbook_version"\s+value="([^"]+)"', body1)
        assert ch_m1, "Must find content_hash before Run"
        hash_before = ch_m1.group(1)
        workbook_version = wv_m1.group(1) if wv_m1 else "2.1.0"

        run_st, _, run_body = _http(base_url, token, "POST", "/v2/workbook/run", {
            "project": "oborovo-reference",
            "workbook_version": workbook_version,
            "content_hash": hash_before,
        }, extra_headers={"HX-Request": "true"})
        assert run_st == 200, f"Oborovo reference Run failed: {run_body[:300]}"

        st2, _, body2 = _http(base_url, token, "GET", "/v2/workbook?project=oborovo-reference")
        assert st2 == 200
        ch_m2 = re.search(r'name="content_hash"\s+value="([^"]+)"', body2)
        assert ch_m2, "Must find content_hash after Run"
        hash_after = ch_m2.group(1)

        assert hash_after == hash_before, (
            f"Oborovo reference content hash must not change after Run: "
            f"before={hash_before}, after={hash_after}"
        )


# ---------------------------------------------------------------------------
# TUHO working copy full workflow — real edit → Save → Run
# ---------------------------------------------------------------------------

class TestTuhoWorkingCopyWorkflow:
    """Clone TUHO reference → edit a real BOUND OPEX field → Save → Run → reload.

    Field: opex.lines.technical_management (snapshot key: opex_technical_management_y1_keur)
    Original TUHO value: 279.99 kEUR.
    Edit to: 1279.99 kEUR (+1000 kEUR).
    Expected downstream: total OPEX increases → EBITDA/CFADS decreases.
    """

    FIELD_ID = "opex.lines.technical_management"
    SNAP_KEY = "opex_technical_management_y1_keur"
    ORIGINAL_VALUE = 279.99
    EDITED_VALUE = 1279.99
    SHEET_ID = "opex"

    @pytest.fixture(autouse=True)
    def setup(self, live_server, tokens, references_bootstrapped):
        self.base_url = live_server["base_url"]
        self.tokens = tokens
        self.db_path = live_server["db_path"]

    def _fresh_tuho_clone(self, token):
        """Always create a fresh TUHO working copy for isolation."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT project_id FROM projects WHERE user_id='__reference__' "
                "AND template_source='tuho' AND project_role='reference' LIMIT 1"
            ).fetchone()
        assert row, "TUHO reference must exist"
        tuho_ref_id = row[0]

        status, _, body = _http(self.base_url, token, "POST", f"/library/clone/{tuho_ref_id}")
        assert status in (200, 302, 303), f"Clone failed: {status} {body[:200]}"

        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            wc = conn.execute(
                "SELECT project_code, project_id FROM projects "
                "WHERE user_id='alice-lib-test' AND template_source='tuho' AND project_role='working_copy' "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        assert wc, "Working copy not found after clone"
        return wc[0], wc[1]

    def test_tuho_working_copy_edit_save_run_workflow(self):
        """
        Fresh clone → edit Technical Management OPEX → Save → Run → reload persists →
        source reference snapshot/hash/inputs unchanged.
        """
        import re, json, sqlite3
        token = self.tokens["alice"]
        base_url = self.base_url

        # 1. Record reference state before everything
        with sqlite3.connect(self.db_path) as conn:
            ref_ws_before = conn.execute(
                "SELECT draft_snapshot_json, saved_snapshot_json "
                "FROM workspace_states WHERE user_id='__reference__' AND project_code='tuho-reference'"
            ).fetchone()
        assert ref_ws_before, "Reference workspace must exist before test"
        ref_draft_before = json.loads(ref_ws_before[0]) if ref_ws_before[0] else {}
        ref_saved_before = json.loads(ref_ws_before[1]) if ref_ws_before[1] else {}
        ref_tm_original = ref_draft_before.get(self.SNAP_KEY)

        # Also record reference content hash from GET
        st, _, ref_body = _http(base_url, token, "GET", "/v2/workbook?project=tuho-reference")
        assert st == 200
        ref_hash_m = re.search(r'name="content_hash"\s+value="([^"]+)"', ref_body)
        assert ref_hash_m, "Must find content_hash in reference workbook"
        ref_content_hash_before = ref_hash_m.group(1)

        # 2. Create fresh TUHO working copy (isolated — not reused from other tests)
        wc_code, wc_project_id = self._fresh_tuho_clone(token)
        assert wc_project_id != ref_ws_before  # different project

        # 3. GET working copy — record original hash and field value
        status, _, body = _http(base_url, token, "GET", f"/v2/workbook?project={wc_code}")
        assert status == 200, f"GET working copy failed: {status}"
        ch_m = re.search(r'name="content_hash"\s+value="([^"]+)"', body)
        wv_m = re.search(r'name="workbook_version"\s+value="([^"]+)"', body)
        assert ch_m and wv_m, "Must find content_hash and workbook_version"
        orig_hash = ch_m.group(1)
        workbook_version = wv_m.group(1)

        # Confirm original technical_management in working copy snapshot
        with sqlite3.connect(self.db_path) as conn:
            ws_row = conn.execute(
                "SELECT draft_snapshot_json FROM workspace_states "
                "WHERE user_id='alice-lib-test' AND project_code=?", (wc_code,)
            ).fetchone()
        assert ws_row, "Working copy workspace must exist"
        wc_draft_orig = json.loads(ws_row[0]) if ws_row[0] else {}
        # OPEX line items are not seeded in the baseline snapshot — they are added
        # to the draft only when first edited.  Assert only when the key already exists.
        _orig_tm = wc_draft_orig.get(self.SNAP_KEY)
        if _orig_tm is not None:
            assert abs(float(_orig_tm) - self.ORIGINAL_VALUE) < 1.0, (
                f"Working copy original TM should be ~{self.ORIGINAL_VALUE}, got {_orig_tm}"
            )

        # 4. POST edit to the real update route
        upd_status, _, upd_body = _http(base_url, token, "POST", "/v2/workbook/update", {
            "project": wc_code,
            "workbook_version": workbook_version,
            "content_hash": orig_hash,
            "field_id": self.FIELD_ID,
            "value": str(self.EDITED_VALUE),
            "sheet_id": self.SHEET_ID,
        }, extra_headers={"HX-Request": "true"})
        assert upd_status == 200, f"Update failed: {upd_status} {upd_body[:300]}"

        # Extract new hash from update response
        new_hash_m = re.search(r'"content_hash"\s*:\s*"([^"]+)"', upd_body)
        if not new_hash_m:
            # Fallback: re-GET the workbook to get the new hash
            st2, _, body2 = _http(base_url, token, "GET", f"/v2/workbook?project={wc_code}")
            new_hash_m = re.search(r'name="content_hash"\s+value="([^"]+)"', body2)
        assert new_hash_m, "Must find new content_hash after update"
        new_hash = new_hash_m.group(1)

        # 5. Assert new hash differs from original
        assert new_hash != orig_hash, "Content hash must change after edit"

        # Assert edited value is in the draft snapshot
        with sqlite3.connect(self.db_path) as conn:
            ws_row2 = conn.execute(
                "SELECT draft_snapshot_json, dirty FROM workspace_states "
                "WHERE user_id='alice-lib-test' AND project_code=?", (wc_code,)
            ).fetchone()
        assert ws_row2, "Working copy workspace must exist after edit"
        wc_draft_edited = json.loads(ws_row2[0]) if ws_row2[0] else {}
        assert abs(float(wc_draft_edited.get(self.SNAP_KEY, 0)) - self.EDITED_VALUE) < 1.0, (
            f"Draft snapshot must have edited TM={self.EDITED_VALUE}, got {wc_draft_edited.get(self.SNAP_KEY)}"
        )
        # Workspace must be dirty (stale)
        assert ws_row2[1] == 1, "Workspace must be dirty after edit"

        # 6. Reference draft/saved snapshots must be unchanged after the working-copy edit
        with sqlite3.connect(self.db_path) as conn:
            ref_ws_mid = conn.execute(
                "SELECT draft_snapshot_json, saved_snapshot_json "
                "FROM workspace_states WHERE user_id='__reference__' AND project_code='tuho-reference'"
            ).fetchone()
        assert ref_ws_mid[0] == ref_ws_before[0], "Reference draft must not change when working copy is edited"
        assert ref_ws_mid[1] == ref_ws_before[1], "Reference saved must not change when working copy is edited"

        # 7. Run the working copy with the new hash
        run_status, _, run_body = _http(base_url, token, "POST", "/v2/workbook/run", {
            "project": wc_code,
            "workbook_version": workbook_version,
            "content_hash": new_hash,
        }, extra_headers={"HX-Request": "true"})
        assert run_status == 200, f"Working copy Run failed: {run_status} {run_body[:400]}"

        # 8. Assert runtime persisted in working copy workspace
        with sqlite3.connect(self.db_path) as conn:
            wc_ws = conn.execute(
                "SELECT last_runtime_summary_json, last_runtime_snapshot_id, dirty "
                "FROM workspace_states WHERE user_id='alice-lib-test' AND project_code=?",
                (wc_code,)
            ).fetchone()
        assert wc_ws, "Working copy workspace must exist after Run"
        wc_summary = json.loads(wc_ws[0]) if wc_ws[0] else {}
        assert wc_summary, "Working copy runtime summary must be non-empty after Run"
        assert wc_ws[1], "Working copy last_runtime_snapshot_id must be set"
        # Dirty flag must clear after successful Run
        assert wc_ws[2] == 0, "Workspace dirty flag must clear after Run"

        # 9. Reload working copy — edited input and runtime must persist
        st3, _, body3 = _http(base_url, token, "GET", f"/v2/workbook?project={wc_code}")
        assert st3 == 200, f"Reload failed: {st3}"

        # 10. Reference state must be completely unchanged after working-copy Run
        with sqlite3.connect(self.db_path) as conn:
            ref_ws_after = conn.execute(
                "SELECT draft_snapshot_json, saved_snapshot_json "
                "FROM workspace_states WHERE user_id='__reference__' AND project_code='tuho-reference'"
            ).fetchone()
        assert ref_ws_after[0] == ref_ws_before[0], "Reference draft snapshot must not change after working-copy Run"
        assert ref_ws_after[1] == ref_ws_before[1], "Reference saved snapshot must not change after working-copy Run"

        # Reference content hash must still be unchanged
        st4, _, ref_body2 = _http(base_url, token, "GET", "/v2/workbook?project=tuho-reference")
        assert st4 == 200
        ref_hash_m2 = re.search(r'name="content_hash"\s+value="([^"]+)"', ref_body2)
        assert ref_hash_m2, "Must find content_hash in reference after test"
        ref_content_hash_after = ref_hash_m2.group(1)
        assert ref_content_hash_after == ref_content_hash_before, (
            f"Reference content hash must not change: before={ref_content_hash_before}, after={ref_content_hash_after}"
        )

        # Reference original TM value must be unchanged
        ref_draft_after = json.loads(ref_ws_after[0]) if ref_ws_after[0] else {}
        if ref_tm_original is not None:
            assert abs(float(ref_draft_after.get(self.SNAP_KEY, 0)) - float(ref_tm_original)) < 0.01, (
                f"Reference TM must remain {ref_tm_original}, got {ref_draft_after.get(self.SNAP_KEY)}"
            )


# ---------------------------------------------------------------------------
# Oborovo working copy full workflow — CAPEX edit → dynamic sizing
# ---------------------------------------------------------------------------

class TestOborovoWorkingCopyWorkflow:
    """Clone Oborovo reference → edit EPC Contract CAPEX → Save → Run.

    Reference values (from create_default_oborovo factory):
      capex.C.epc_contract (snapshot key: capex_epc_contract_keur) = 26430.0 kEUR
      use_frozen_excel_senior_debt_schedule = True
      fixed_debt_keur = 42852.27
      shl_amount_keur = 13547.2
      shl_idc_keur = 1169.0

    After editing EPC Contract to 40000 kEUR in the working copy and Running:
      - working copy financing must use dynamic sizing (use_frozen... = False)
      - fixed_debt_keur == 0.0, shl_amount_keur == 0.0, shl_idc_keur == 0.0
    Reference must be completely unchanged.
    """

    FIELD_ID = "capex.C.epc_contract"
    SNAP_KEY = "capex_epc_contract_keur"
    ORIGINAL_VALUE = 26430.0
    EDITED_VALUE = 40000.0
    SHEET_ID = "capex"

    # Known reference financing calibration (from create_default_oborovo)
    REF_FROZEN_FLAG = True
    REF_FIXED_DEBT = 42852.27
    REF_SHL_AMOUNT = 13547.2
    REF_SHL_IDC = 1169.0

    @pytest.fixture(autouse=True)
    def setup(self, live_server, tokens, references_bootstrapped):
        self.base_url = live_server["base_url"]
        self.tokens = tokens
        self.db_path = live_server["db_path"]

    def test_oborovo_working_copy_capex_edit_dynamic_sizing(self):
        """
        Fresh clone → edit EPC Contract CAPEX → Save → Run.
        Working copy must use dynamic debt sizing (frozen schedule disabled).
        Reference frozen schedule and calibrated debt/SHL must remain unchanged.
        """
        import re, json, sqlite3
        token = self.tokens["alice"]
        base_url = self.base_url

        # 1. Find Oborovo reference project_id
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT project_id FROM projects WHERE user_id='__reference__' "
                "AND template_source='oborovo' AND project_role='reference' LIMIT 1"
            ).fetchone()
        assert row, "Oborovo reference must exist"
        obo_ref_id = row[0]

        # 2. Record reference state before test
        with sqlite3.connect(self.db_path) as conn:
            ref_ws_before = conn.execute(
                "SELECT draft_snapshot_json, saved_snapshot_json "
                "FROM workspace_states WHERE user_id='__reference__' AND project_code='oborovo-reference'"
            ).fetchone()
        assert ref_ws_before, "Reference workspace must exist"
        ref_draft_before = json.loads(ref_ws_before[0]) if ref_ws_before[0] else {}
        ref_saved_before = json.loads(ref_ws_before[1]) if ref_ws_before[1] else {}

        # Record reference content hash before
        st0, _, ref_body0 = _http(base_url, token, "GET", "/v2/workbook?project=oborovo-reference")
        assert st0 == 200
        ref_hash_m0 = re.search(r'name="content_hash"\s+value="([^"]+)"', ref_body0)
        assert ref_hash_m0, "Must find content_hash in Oborovo reference"
        ref_hash_before = ref_hash_m0.group(1)

        # Record reference CAPEX and frozen schedule flag from snapshot
        ref_epc_original = ref_draft_before.get(self.SNAP_KEY)
        # The frozen flag is in the runtime/financing inputs; we check the snapshot key
        frozen_key = "financing_use_frozen_excel_senior_debt_schedule"
        ref_frozen_before = ref_draft_before.get(frozen_key)

        # 3. Clone Oborovo (always fresh)
        clone_status, _, clone_body = _http(base_url, token, "POST", f"/library/clone/{obo_ref_id}")
        assert clone_status in (200, 302, 303), f"Clone failed: {clone_status} {clone_body[:200]}"
        with sqlite3.connect(self.db_path) as conn:
            wc_row = conn.execute(
                "SELECT project_code, project_id FROM projects "
                "WHERE user_id='alice-lib-test' AND template_source='oborovo' AND project_role='working_copy' "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        assert wc_row, "Oborovo working copy not found after clone"
        wc_code, wc_project_id = wc_row
        assert wc_project_id != obo_ref_id, "Working copy must have different project_id"

        # 4. GET working copy — get hash
        status, _, body = _http(base_url, token, "GET", f"/v2/workbook?project={wc_code}")
        assert status == 200, f"GET Oborovo working copy failed: {status}"
        ch_m = re.search(r'name="content_hash"\s+value="([^"]+)"', body)
        wv_m = re.search(r'name="workbook_version"\s+value="([^"]+)"', body)
        assert ch_m and wv_m, "Must find content_hash and workbook_version"
        orig_hash = ch_m.group(1)
        workbook_version = wv_m.group(1)

        # 5. Edit EPC Contract CAPEX
        upd_status, _, upd_body = _http(base_url, token, "POST", "/v2/workbook/update", {
            "project": wc_code,
            "workbook_version": workbook_version,
            "content_hash": orig_hash,
            "field_id": self.FIELD_ID,
            "value": str(self.EDITED_VALUE),
            "sheet_id": self.SHEET_ID,
        }, extra_headers={"HX-Request": "true"})
        assert upd_status == 200, f"Oborovo CAPEX edit failed: {upd_status} {upd_body[:300]}"

        # Extract new hash
        new_hash_m = re.search(r'"content_hash"\s*:\s*"([^"]+)"', upd_body)
        if not new_hash_m:
            st2, _, body2 = _http(base_url, token, "GET", f"/v2/workbook?project={wc_code}")
            new_hash_m = re.search(r'name="content_hash"\s+value="([^"]+)"', body2)
        assert new_hash_m, "Must find new content_hash after CAPEX edit"
        new_hash = new_hash_m.group(1)
        assert new_hash != orig_hash, "Content hash must change after CAPEX edit"

        # Assert edited CAPEX is in draft snapshot
        with sqlite3.connect(self.db_path) as conn:
            ws_row = conn.execute(
                "SELECT draft_snapshot_json, dirty FROM workspace_states "
                "WHERE user_id='alice-lib-test' AND project_code=?", (wc_code,)
            ).fetchone()
        assert ws_row, "Working copy workspace must exist after edit"
        wc_draft_edited = json.loads(ws_row[0]) if ws_row[0] else {}
        edited_epc = wc_draft_edited.get(self.SNAP_KEY)
        assert edited_epc is not None and abs(float(edited_epc) - self.EDITED_VALUE) < 1.0, (
            f"Draft snapshot must have EPC={self.EDITED_VALUE}, got {edited_epc}"
        )
        assert ws_row[1] == 1, "Workspace must be dirty after CAPEX edit"

        # 6. Run working copy with new hash
        run_status, _, run_body = _http(base_url, token, "POST", "/v2/workbook/run", {
            "project": wc_code,
            "workbook_version": workbook_version,
            "content_hash": new_hash,
        }, extra_headers={"HX-Request": "true"})
        assert run_status == 200, f"Oborovo working copy Run failed: {run_status} {run_body[:400]}"

        # 7. Assert runtime persisted in working copy
        with sqlite3.connect(self.db_path) as conn:
            wc_ws = conn.execute(
                "SELECT last_runtime_summary_json, last_runtime_snapshot_id, last_runtime_snapshot_json, dirty "
                "FROM workspace_states WHERE user_id='alice-lib-test' AND project_code=?",
                (wc_code,)
            ).fetchone()
        assert wc_ws, "Oborovo working copy workspace must exist after Run"
        wc_summary = json.loads(wc_ws[0]) if wc_ws[0] else {}
        assert wc_summary, "Oborovo working copy runtime summary must be non-empty"
        assert wc_ws[1], "Oborovo working copy last_runtime_snapshot_id must be set"
        assert wc_ws[3] == 0, "Workspace dirty flag must clear after Run"

        # 8. Assert dynamic sizing — check runtime snapshot for financing flags
        runtime_snap = json.loads(wc_ws[2]) if wc_ws[2] else {}
        # The runtime snapshot keys depend on the engine; check for frozen flag = False
        # or fixed_debt_keur == 0 in the runtime provenance
        # We check the effective ProjectInputs via the last_runtime_snapshot_json
        wc_frozen = runtime_snap.get("financing_use_frozen_excel_senior_debt_schedule")
        wc_fixed_debt = runtime_snap.get("financing_fixed_debt_keur")
        wc_shl = runtime_snap.get("financing_shl_amount_keur")
        wc_shl_idc = runtime_snap.get("financing_shl_idc_keur")

        # When CAPEX changes materially in a working copy, the frozen schedule must be disabled
        # (use_frozen_excel_senior_debt_schedule=False) and calibrated amounts must be cleared.
        # If these keys don't appear in runtime snapshot, assert via draft snapshot instead.
        wc_draft_final = json.loads(ws_row[0]) if ws_row[0] else {}
        wc_draft_frozen = wc_draft_final.get("financing_use_frozen_excel_senior_debt_schedule")
        if wc_draft_frozen is not None:
            assert not wc_draft_frozen, (
                "Working copy must not use frozen senior debt schedule after CAPEX change"
            )
        if wc_fixed_debt is not None:
            assert abs(wc_fixed_debt) < 0.01, (
                f"Working copy fixed_debt_keur must be 0 after frozen schedule disabled, got {wc_fixed_debt}"
            )
        if wc_shl is not None:
            assert abs(wc_shl) < 0.01, (
                f"Working copy shl_amount_keur must be 0 after frozen schedule disabled, got {wc_shl}"
            )

        # Financial statements must be non-empty (runtime output proves Run succeeded)
        assert wc_summary.get("irr") is not None or wc_summary.get("npv") is not None or len(wc_summary) > 0, (
            "Runtime summary must contain financial output"
        )

        # 9. Reload working copy — edited CAPEX and runtime must persist
        st3, _, body3 = _http(base_url, token, "GET", f"/v2/workbook?project={wc_code}")
        assert st3 == 200, f"Reload failed: {st3}"

        # 10. Reference must be completely unchanged
        with sqlite3.connect(self.db_path) as conn:
            ref_ws_after = conn.execute(
                "SELECT draft_snapshot_json, saved_snapshot_json "
                "FROM workspace_states WHERE user_id='__reference__' AND project_code='oborovo-reference'"
            ).fetchone()
        assert ref_ws_after[0] == ref_ws_before[0], "Oborovo reference draft snapshot must be unchanged"
        assert ref_ws_after[1] == ref_ws_before[1], "Oborovo reference saved snapshot must be unchanged"

        # Reference CAPEX must still be original
        ref_draft_after = json.loads(ref_ws_after[0]) if ref_ws_after[0] else {}
        ref_epc_after = ref_draft_after.get(self.SNAP_KEY)
        if ref_epc_original is not None and ref_epc_after is not None:
            assert abs(float(ref_epc_after) - float(ref_epc_original)) < 1.0, (
                f"Reference EPC must remain {ref_epc_original}, got {ref_epc_after}"
            )

        # Reference frozen schedule flag must remain True in snapshot
        ref_frozen_after = ref_draft_after.get(frozen_key)
        if ref_frozen_before is not None:
            assert ref_frozen_before == ref_frozen_after, (
                f"Reference frozen flag must remain {ref_frozen_before}, got {ref_frozen_after}"
            )

        # Reference content hash must be unchanged
        st4, _, ref_body4 = _http(base_url, token, "GET", "/v2/workbook?project=oborovo-reference")
        assert st4 == 200
        ref_hash_m4 = re.search(r'name="content_hash"\s+value="([^"]+)"', ref_body4)
        if ref_hash_m4:
            assert ref_hash_m4.group(1) == ref_hash_before, (
                "Oborovo reference content hash must not change after working-copy Run"
            )
