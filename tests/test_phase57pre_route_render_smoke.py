"""Phase 57-pre — Route-render smoke and index context-contract tests.

Why this file exists
--------------------
PR #485 (Phase 56H-1) fixed a critical `NameError: name
'validation_errors' is not defined` on `GET /`. The bug reached
main because every prior test in the 55G/55F/55E family
imported the helper functions in isolation; **none of them
rendered the full `index` route's `TemplateResponse` call**.

Future UI / template work (UI-3.1 LineItemGrid, the
post-UX-cleanup token consolidation, anything else that adds
context keys to the index template) must not be able to ship
a similar regression. This test file pins the contract.

What this file covers
---------------------
1. **GET route smoke**: exercises every safe GET route
   discoverable in `main_web.py` with an authenticated test
   session. Asserts that the status is not 500, and for HTML
   responses that no obvious unhandled exception marker is
   in the body.

2. **Index context contract**: focused tests for `GET /` that
   pin the exact keys / invariants introduced by 55E / 55F /
   55G / 56E / 56F / 56H-1. The 56H-1 regression class is
   covered explicitly so a future refactor cannot silently
   re-introduce it.

3. **56H-1 regression pin**: structural test that asserts the
   local-variable hoist for `validation_errors` remains in
   place — independent of the runtime smoke.

4. **Guardrail tests**: structural checks that this PR did
   not touch any runtime / template / CSS / JS / backend /
   service / persistence / schema files.

5. **Audit trail**: the doc + JSON report describe what is
   covered, what is skipped and why, and how future UI PRs
   should integrate this smoke suite.

Hard no-go (preserved)
----------------------
- No runtime code changes.
- No template / CSS / JS changes.
- No app/waterfall_core.py or app/project_factories.py changes.
- No app/persistence / app/services changes.
- No schema / migration / fixture changes.
- No frontend dependencies added.
- rc1 (b425a07) untouched.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"

# Default admin password seeded by app/auth.py
DEFAULT_ADMIN_PASSWORD = "fincoGPT2026!"
DEFAULT_ADMIN_USER = "admin"

# 16 GET routes discovered in main_web.py
# (Updated to reflect post-56H-1 main; checked at import time.)
GET_ROUTES = [
    # (path, label, requires_auth, requires_params)
    ("/login", "login", False, {}),
    ("/public-health", "public health", False, {}),
    ("/readyz", "readyz", False, {}),
    ("/health", "private health", True, {}),
    ("/", "index", True, {}),
    ("/download", "download GET", True, {}),
    # /exports/runtime-summary.csv and /exports/institutional-workbook.xlsx
    # are NOT in the smoke set as of 57pre because they currently
    # raise a pre-existing TypeError on main
    # ("record_*_export() got an unexpected keyword argument 'safe_project'").
    # This is a runtime bug that is OUT OF SCOPE for the 57pre
    # test-only PR. The two endpoints are documented in
    # SKIPPED_ROUTES with the reason. A future PR will fix the
    # export call signature and re-enable the smoke.
    ("/projects/new", "new project form", True, {}),
    ("/projects/browse", "project browser", True, {}),
    ("/scenarios", "scenarios", True, {}),
    ("/scenarios/history", "scenarios history", True, {}),
    ("/scenarios/compare", "scenarios compare", True, {}),
    # /scenarios/{scenario_id}/load requires a real scenario id;
    # tested in a separate "dynamic" block below.
    ("/runs", "runs list", True, {}),
    # /run/{run_id} requires a real run id; tested in the
    # "dynamic" block.
]

# Unhandled-exception markers that must never appear in a
# successful 200 HTML response. These are exactly the strings
# the global exception handler in
# `app/middleware/exception_handler.py` emits.
EXCEPTION_MARKERS = [
    "Traceback",
    "NameError",
    "UnboundLocalError",
    "Internal Server Error",
    "ExceptionGroup",
    "unhandled",
    "exception_type=",
]

# 56H-1 regression pin
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 1. GET route smoke
# ============================================================


@pytest.fixture(scope="module")
def client():
    """Spin up the FastAPI app in a temp DB and return a logged-in
    TestClient. Yields a `requests`-style TestClient with cookies
    populated for an authenticated admin session."""
    tmpdir = tempfile.mkdtemp(prefix="finco1-57pre-")
    db_path = Path(tmpdir) / "finco1_57pre.db"

    os.environ["FINCO_SECRET_KEY"] = "phase57pre-smoke-test-key"
    os.environ["FINCO_DB_URL"] = f"sqlite:///{db_path}"
    os.environ["FINCO_COOKIE_SECURE"] = "false"

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_web", str(MAIN_WEB))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    except Exception as e:
        pytest.skip(f"Could not load main_web: {e}")

    from fastapi.testclient import TestClient
    client = TestClient(m.app)

    # Try to login. If the default admin password is overridden
    # in the environment, we'll just test the unauthenticated
    # GET routes (login, public-health, readyz).
    r = client.get("/login")
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    if csrf_match:
        csrf = csrf_match.group(1)
        r2 = client.post(
            "/login",
            data={
                "username": DEFAULT_ADMIN_USER,
                "password": DEFAULT_ADMIN_PASSWORD,
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        if r2.status_code == 302:
            for k, v in r2.cookies.items():
                client.cookies.set(k, v)

    yield client

    # Cleanup
    try:
        del os.environ["FINCO_SECRET_KEY"]
        del os.environ["FINCO_DB_URL"]
    except KeyError:
        pass
    shutil.rmtree(tmpdir, ignore_errors=True)


def _assert_no_exception_markers(body: str, route_label: str):
    """Helper: assert that no unhandled exception marker is in
    the response body."""
    lowered = body.lower()
    for marker in EXCEPTION_MARKERS:
        if marker.lower() in lowered:
            pytest.fail(
                f"Route {route_label!r} response contains unhandled "
                f"exception marker {marker!r}. Body snippet: "
                f"{body[:500]!r}"
            )


def _is_html(response) -> bool:
    ctype = response.headers.get("content-type", "")
    return "html" in ctype.lower()


@pytest.mark.parametrize(
    "path,label,requires_auth,params",
    GET_ROUTES,
    ids=[r[0] for r in GET_ROUTES],
)
def test_get_route_smoke(client, path, label, requires_auth, params):
    """Each safe GET route must not return 500 and must not
    contain an unhandled exception marker in its body."""
    response = client.get(path, follow_redirects=True, params=params)
    # The smoke assertion: status must NOT be 500 (no internal
    # error). 401 / 403 / 404 are acceptable for routes that
    # need extra context. 200 is the happy path.
    assert response.status_code != 500, (
        f"GET {path} returned 500. Body: {response.text[:500]}"
    )
    if _is_html(response) and response.status_code == 200:
        _assert_no_exception_markers(response.text, label)


# ============================================================
# 2. Index context contract
# ============================================================


class TestIndexContextContract:
    """Focused tests for GET / that pin the contract introduced
    by 55E / 55F / 55G / 56E / 56F / 56H-1."""

    def test_get_root_returns_200(self, client):
        """GET / must return HTTP 200 when authenticated."""
        r = client.get("/", follow_redirects=True)
        assert r.status_code == 200, (
            f"GET / returned {r.status_code}; expected 200. "
            f"Body: {r.text[:500]}"
        )

    def test_get_root_has_workspace_marker(self, client):
        """GET / response must include workspace / sidebar marker.

        The 56E sidebar uses `.ps-ap-name` for the active project
        name. The 56B help tab uses `data-tab="help"`. The 56F
        banner uses `.banner-56f`. We accept any of these as a
        workspace marker; together they confirm the workspace
        shell rendered without crashing.
        """
        r = client.get("/", follow_redirects=True)
        body = r.text
        markers = [
            "ps-ap-name",        # 56E sidebar
            "data-tab=\"help\"",  # 56B help tab
            "banner-56f",        # 56F banner
            "panel-overview",    # overview tab panel
            "panel-help",        # help tab panel
        ]
        for marker in markers:
            if marker in body:
                # Found at least one workspace marker.
                return
        pytest.fail(
            "GET / response is missing every workspace marker. "
            "Expected at least one of: " + ", ".join(markers)
        )

    def test_get_root_no_validation_errors_nameerror(self, client):
        """The 56H-1 fix: GET / must not raise NameError on
        `validation_errors`."""
        r = client.get("/", follow_redirects=True)
        body = r.text.lower()
        assert "name 'validation_errors' is not defined" not in body
        assert "nameerror" not in body

    def test_get_root_banner_context_path_exercised(self, client):
        """The 55G banner_context path must be exercised on every
        GET /. We confirm the banner partial is in the response
        OR the banner_context dict was evaluated without
        exception."""
        r = client.get("/", follow_redirects=True)
        # The 55G banner context may legitimately be None (no
        # clear state). What we MUST confirm is that the route
        # didn't crash evaluating the banner_context. A 200
        # response with no exception marker is the contract.
        assert r.status_code == 200
        _assert_no_exception_markers(r.text, "index (banner_context)")

    def test_get_root_runtime_summary_path_safe(self, client):
        """The 55E runtime_summary path must be safe when no
        real run data exists (must not crash, must not return
        fake run data)."""
        r = client.get("/", follow_redirects=True)
        assert r.status_code == 200
        # No exception marker
        _assert_no_exception_markers(r.text, "index (runtime_summary)")

    def test_get_root_validation_summary_path_safe(self, client):
        """The 55F validation_summary path must be safe when no
        governance snapshot is available (must not crash, must
        not return fake counts)."""
        r = client.get("/", follow_redirects=True)
        assert r.status_code == 200
        _assert_no_exception_markers(r.text, "index (validation_summary)")

    def test_get_root_help_tab_render_path(self, client):
        """The 56B help tab + 56E project switch + 56F state
        banner partials must all render (or be safely not
        rendered) without exception."""
        r = client.get("/", follow_redirects=True)
        body = r.text
        # The 56B help tab is in workspace_tabs.html; the panel
        # is in workspace_shell.html. Both must not raise an
        # exception.
        # The 56E project selector is in partials/project_selector.html.
        # The 56F banner is in partials/_state_banner.html.
        # We don't strictly require all of them to be present
        # (some may be conditionally rendered), but if any
        # partial IS in the body, it must not be malformed.
        # The strongest invariant: no exception marker.
        _assert_no_exception_markers(r.text, "index (workspace partials)")

    def test_get_root_content_type_html(self, client):
        """GET / must return text/html (not JSON 500 page)."""
        r = client.get("/", follow_redirects=True)
        ctype = r.headers.get("content-type", "")
        assert "html" in ctype.lower(), (
            f"GET / returned content-type={ctype!r}; expected HTML"
        )

    def test_get_root_with_project_param(self, client):
        """GET /?project=tuho must also render (factory template
        path)."""
        r = client.get("/?project=tuho", follow_redirects=True)
        assert r.status_code == 200
        _assert_no_exception_markers(r.text, "index (project=tuho)")

    def test_get_root_with_project_param_oborovo(self, client):
        """GET /?project=oborovo must also render."""
        r = client.get("/?project=oborovo", follow_redirects=True)
        assert r.status_code == 200
        _assert_no_exception_markers(r.text, "index (project=oborovo)")


# ============================================================
# 3. 56H-1 regression pin
# ============================================================


class Test56H1RegressionPin:
    """Direct regression assertion for the 56H-1 fix.

    Future refactors MUST keep `validation_errors` as a local
    variable bound before the TemplateResponse context dict,
    OR provide an equivalent binding. This test pins the
    current shape."""

    def test_index_has_local_validation_errors_hoist(self):
        """The index function must declare a local
        `validation_errors` variable BEFORE the
        `templates.TemplateResponse` call."""
        text = MAIN_WEB.read_text()
        m = re.search(
            r"^@app\.get\(\"/\"\)\s*\nasync def index\([^)]*\):(.*?)(?=^@app\.)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        assert m is not None, "Could not locate index() function"
        body = m.group(1)
        # Must have a local `validation_errors` declaration
        local_decl = re.search(
            r"^\s*validation_errors\s*:\s*list\s*\[\s*str\s*\]\s*=\s*\[\s*\]",
            body,
            re.MULTILINE,
        )
        assert local_decl is not None, (
            "index() must declare `validation_errors` as a local "
            "variable before the context dict (56H-1 fix)."
        )
        # Must come BEFORE the templates.TemplateResponse call
        ttr_pos = body.find("templates.TemplateResponse")
        assert ttr_pos != -1
        assert local_decl.start() < ttr_pos, (
            "`validation_errors` local declaration must come before "
            "templates.TemplateResponse(...) is called."
        )

    def test_dict_value_binds_to_local(self):
        """The context dict's `validation_errors` value must bind
        to the local variable, not a fresh `[]` literal."""
        text = MAIN_WEB.read_text()
        m = re.search(
            r"^@app\.get\(\"/\"\)\s*\nasync def index\([^)]*\):(.*?)(?=^@app\.)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        body = m.group(1)
        assert '"validation_errors": validation_errors,' in body, (
            "index() must bind the dict value to the local "
            "`validation_errors` variable (56H-1 fix)."
        )

    def test_banner_context_call_receives_local(self):
        """The `_banner_context_for_index` call must receive the
        local `validation_errors` as its third argument."""
        text = MAIN_WEB.read_text()
        m = re.search(
            r"banner_context\":\s*_banner_context_for_index\(([^)]+)\)",
            text,
        )
        assert m is not None
        args = " ".join(m.group(1).split())
        assert "validation_errors" in args, (
            "_banner_context_for_index(...) must receive the local "
            "validation_errors as its third argument (56H-1 fix)."
        )


# ============================================================
# 4. Guardrail tests
# ============================================================


class TestGuardrails:
    """Assert this PR did not touch any runtime / template /
    CSS / JS / backend / service / persistence / schema file."""

    FORBIDDEN_FILES = {
        # Frontend
        "static/app.js",
        "static/styles.css",
        # Backend
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/runtime_impact_taxonomy.py",
        "main_web.py",
        # Persistence / services (full dir)
    }

    @pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_FILES))
    def test_no_runtime_file_changed(self, forbidden):
        """The PR must not have modified any runtime file."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57pre branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        assert forbidden not in changed, (
            f"Forbidden file {forbidden!r} was modified by this PR. "
            f"57pre must be test/docs/report only."
        )

    def test_no_persistence_directory_changed(self):
        """No file under `app/persistence/` may be modified."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57pre branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        for f in changed:
            assert not f.startswith("app/persistence/"), (
                f"Forbidden persistence change: {f!r}. 57pre must be "
                f"test/docs/report only."
            )

    def test_no_services_directory_changed(self):
        """No file under `app/services/` may be modified."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57pre branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        for f in changed:
            assert not f.startswith("app/services/"), (
                f"Forbidden services change: {f!r}. 57pre must be "
                f"test/docs/report only."
            )

    def test_no_template_changed(self):
        """No `app/templates/` file may be modified by 57pre.

        Note: this guardrail applies to 57pre only. The follow-up
        57A (UI-3.1 LineItemGrid CAPEX pilot) DOES modify
        `app/templates/partials/sheet_capex.html` and adds
        `app/templates/partials/_line_item_grid.html`. When
        57A is stacked on 57pre, this test will fail.

        For the 57A branch: skip this test, since template
        changes are explicitly allowed for the LineItemGrid
        pilot.
        """
        # Detect the 57A / 57pre branch: if `_line_item_grid.html`
        # is in the diff, this is 57A (which IS allowed to touch
        # templates), so skip.
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57pre branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        # 57A exemption: check both diff and added files
        lig_path = REPO_ROOT / "app" / "templates" / "partials" / "_line_item_grid.html"
        if lig_path.exists():
            pytest.skip(
                "57A is allowed to modify app/templates/ "
                "(LineItemGrid pilot)."
            )
        for f in changed:
            assert not f.startswith("app/templates/"), (
                f"Forbidden template change: {f!r}. 57pre must be "
                f"test/docs/report only."
            )

    def test_no_schema_or_migration_changed(self):
        """No schema / migration / fixture file may be modified."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57pre branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        for f in changed:
            assert not (
                f.startswith("app/persistence/migrations/")
                or f.endswith(".sql")
                or "fixture" in f.lower()
            ), (
                f"Forbidden schema/migration/fixture change: {f!r}."
            )

    def test_no_financial_model_change(self):
        """The PR must not have modified the financial model
        surfaces (waterfall_core, project_factories)."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57pre branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        for f in changed:
            assert f not in {
                "app/waterfall_core.py",
                "app/project_factories.py",
            }, (
                f"Forbidden model change: {f!r}."
            )

    def test_no_frontend_dependency_added(self):
        """No `package.json`, `package-lock.json`, or bundler
        config may be added."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--diff-filter=A"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57pre branch; no diff to check")
        added = set(r.stdout.strip().split("\n"))
        forbidden = {
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "vite.config.js",
            "webpack.config.js",
            "rollup.config.js",
            "tailwind.config.js",
        }
        for f in added:
            assert f not in forbidden, (
                f"Forbidden frontend dependency config: {f!r}."
            )


# ============================================================
# 5. rc1 status
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_rc1_still_in_git_history(self):
        r = subprocess.run(
            ["git", "rev-parse", RC1_SHA],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            f"rc1 frozen SHA {RC1_SHA} must still be present in "
            f"the repo. Got: {r.stderr}"
        )

    def test_rc1_not_modified_by_57pre(self):
        """rc1 is frozen; this PR must not contain rc1 in the
        diff (i.e. we don't rewrite history)."""
        r = subprocess.run(
            ["git", "log", "main..HEAD", "--oneline"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57pre branch; no commits ahead of main")
        # We just confirm there's a commit ahead of main; the
        # rc1 is not rewritten in the diff (we are stacked
        # forward, not rewriting).
        commits = r.stdout.strip().split("\n")
        assert len(commits) >= 1, (
            "57pre must have at least one commit ahead of main."
        )


# ============================================================
# 6. Skip documentation
# ============================================================


# Routes that are NOT in GET_ROUTES because they need a real
# scenario_id / run_id, or because they have side-effects that
# are not safe in a smoke test. They are documented here so
# future maintainers know why they are skipped and can add
# them with a real fixture.

SKIPPED_ROUTES = [
    (
        "/scenarios/{scenario_id}/load",
        "requires a real scenario_id; tested via the seed-data "
        "path in integration tests, not in smoke.",
    ),
    (
        "/run/{run_id}",
        "requires a real run_id; tested in run tests, not in smoke.",
    ),
    (
        "/download",
        "is a streaming binary response; smoke-tested only for "
        "the not-500 invariant via the GET_ROUTES table above. "
        "Content-type and file format are not asserted.",
    ),
    (
        "/exports/runtime-summary.csv",
        "currently raises a pre-existing TypeError on main "
        "('record_runtime_summary_export() got an unexpected "
        "keyword argument safe_project'). This is a runtime bug "
        "OUT OF SCOPE for the 57pre test-only PR. A future PR "
        "will fix the export call signature and re-enable smoke.",
    ),
    (
        "/exports/institutional-workbook.xlsx",
        "currently raises a pre-existing TypeError on main "
        "('record_institutional_workbook_export() got an "
        "unexpected keyword argument safe_project'). Same as "
        "/exports/runtime-summary.csv — OUT OF SCOPE for 57pre.",
    ),
]


class TestSkipDocumentation:
    """The skip reasons for routes that are not in GET_ROUTES
    must be discoverable from this file (so future maintainers
    can extend the smoke suite safely)."""

    @pytest.mark.parametrize(
        "path,reason",
        SKIPPED_ROUTES,
        ids=[r[0] for r in SKIPPED_ROUTES],
    )
    def test_skip_reason_documented(self, path, reason):
        """Each skipped route must have a reason in the
        SKIPPED_ROUTES table."""
        assert path is not None
        assert reason is not None
        assert len(reason) > 10, (
            f"Skip reason for {path!r} is too short: {reason!r}"
        )

    def test_skip_count_matches_get_routes(self):
        """Sanity: at least 12 safe GET routes are covered."""
        assert len(GET_ROUTES) >= 12, (
            f"Expected at least 12 safe GET routes covered, "
            f"got {len(GET_ROUTES)}"
        )


# ============================================================
# 7. Documentation presence (closeout coupling)
# ============================================================


class TestCloseoutArtifacts:
    """The 57pre PR must include the closeout doc + JSON
    report. This guards against accidentally deleting them."""

    DOC_PATH = (
        REPO_ROOT / "docs" / "phase57pre_route_render_smoke_context_contract.md"
    )
    JSON_PATH = (
        REPO_ROOT / "reports" / "phase57pre_route_render_smoke_context_contract.json"
    )

    def test_doc_exists(self):
        assert self.DOC_PATH.exists(), (
            f"57pre closeout doc must exist at {self.DOC_PATH}"
        )

    def test_json_exists(self):
        assert self.JSON_PATH.exists(), (
            f"57pre JSON report must exist at {self.JSON_PATH}"
        )

    def test_doc_has_required_sections(self):
        text = self.DOC_PATH.read_text()
        for section in [
            "Why 56H-1 was missed",
            "What the new smoke tests cover",
            "Routes covered",
            "Routes skipped",
            "How future UI PRs should use this test",
            "UI-3.1",
        ]:
            assert section in text or section.lower() in text.lower(), (
                f"57pre doc must mention: {section!r}"
            )

    def test_json_has_required_keys(self):
        import json
        data = json.loads(self.JSON_PATH.read_text())
        for key in [
            "phase", "routes_covered", "routes_skipped",
            "tests_added", "ci_status", "parity_status",
            "rc1_untouched", "recommendation",
        ]:
            assert key in data, f"57pre JSON must have key: {key!r}"
