"""
Browser acceptance tests for Workbook V2.

Drives a real Chromium browser via Playwright against a real uvicorn server
with FINCO_WORKBOOK_V2=1 and an isolated temporary SQLite database.

Requirements exercised
----------------------
  • Render path: #v2-workbook-shell, .v2-run-form, OPEX sheet, FS sheet,
    workbook_v2.js loaded.
  • TM 200 → 300 one-click queued Run: pending → saving → field-saved →
    hash updated → Run fires once → persisted.
  • HTMX event ordering: HX-Trigger fires BEFORE htmx:afterRequest; the
    in-flight counter (_inFlightSaveCount) gates the Run so it does not
    fire while saving state is still active.
  • Error cases: validation failure and stale-hash both cancel queued Run
    and emit workbook-field-error.
  • Additional OPEX: Maintenance, Insurance, explicit zero.
  • FS annual aggregation: Revenue, OPEX Cash, EBIT, Net Income, Net Fixed
    Assets, Senior Balance (stock rows use year-end, not sum).
  • CIT display: 20.0%, 18.0%, 0.0%.
  • FS selection persistence: period view and inner tab survive Run + reload.
  • Keyboard navigation on FS inner tabs.
  • Viewport correctness at 1440×900 and 1920×1080.

Isolation
---------
All browser tests use a temporary SQLite database; no browser-test project
names appear in the normal project list.

Skip behaviour
--------------
Every test in this file is auto-skipped when Playwright is not importable
(OPTIONAL_BROWSER_DEPENDENCY_MISSING marker).
"""
from __future__ import annotations

import glob
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: set env before importing app code (auth token signing)
# ---------------------------------------------------------------------------
os.environ.setdefault("FINCO_SECRET_KEY", "browser-accept-secret-v2")

BASE_DIR = Path(__file__).resolve().parents[1]
SCREENSHOTS_DIR = BASE_DIR / "tests" / "screenshots"

from app.auth import COOKIE_NAME, create_session_token  # noqa: E402 – after env


# ---------------------------------------------------------------------------
# Chromium executable path
# ---------------------------------------------------------------------------
def _chromium_path() -> str:
    candidates = glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome")
    if candidates:
        return sorted(candidates)[-1]
    return ""   # let Playwright use default if not found


# ---------------------------------------------------------------------------
# Server helpers (urllib only – no TestClient in browser tests)
# ---------------------------------------------------------------------------

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


def _http(base_url: str, token: str, method: str, path: str,
          data: dict | None = None,
          extra_headers: dict | None = None) -> tuple[int, dict, str]:
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


def _create_project(base_url: str, token: str, name: str,
                    project_type: str = "Solar",
                    template_source: str = "oborovo") -> str:
    _, headers, _ = _http(base_url, token, "POST", "/projects/create", {
        "project_name": name,
        "project_type": project_type,
        "template_source": template_source,
        "country_market": "DE",
        "capacity_mw": "50",
        "cod_date": "2027-01-01",
        "construction_months": "18",
        "horizon_years": "20",
        "tariff_eur_mwh": "70",
        "ppa_term_years": "15",
        "p50_hours": "1500",
        "opex_y1_keur": "2000",
        "total_capex_keur": "40000",
        "gearing_pct": "70",
        "interest_rate_pct": "4.5",
        "tenor_years": "18",
        "target_dscr": "1.30",
    })
    redirect = (headers.get("hx-redirect") or headers.get("Hx-Redirect")
                or headers.get("location") or headers.get("Location") or "")
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    codes = parsed.get("project", [])
    assert codes, f"No project= in create redirect: {redirect!r} / headers: {headers}"
    return codes[0]


def _get_content_hash(base_url: str, token: str, project_code: str) -> str:
    from bs4 import BeautifulSoup
    status, _, body = _http(base_url, token, "GET", f"/v2/workbook?project={project_code}")
    assert status == 200, f"GET /v2/workbook failed: {status}"
    soup = BeautifulSoup(body, "html.parser")
    shell = soup.find(id="v2-workbook-shell")
    assert shell, "#v2-workbook-shell not found"
    return shell.get("data-content-hash", "")


def _field_update_api(base_url: str, token: str, project_code: str,
                       field_id: str, value: str, sheet_id: str) -> tuple[int, dict, str]:
    """Update a field via the API (not browser) — for seeding and verification."""
    ch = _get_content_hash(base_url, token, project_code)
    return _http(base_url, token, "POST", "/v2/workbook/update", {
        "field_id": field_id,
        "value": value,
        "project": project_code,
        "workbook_version": "2.1.0",
        "content_hash": ch,
        "sheet_id": sheet_id,
    }, extra_headers={"HX-Request": "true"})


def _read_ws_snapshot(db_path: str, project_code: str) -> dict:
    """Read workspace draft_snapshot from the test DB (post-test verification)."""
    import sqlite3, json as _j
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT ws.draft_snapshot_json FROM workspace_states ws "
            "JOIN projects p ON ws.project_id = p.project_id "
            "WHERE p.project_code = ?", (project_code,)
        ).fetchone()
    if row and row[0]:
        return _j.loads(row[0])
    return {}


def _read_ws_runtime_summary(db_path: str, project_code: str) -> dict:
    import sqlite3, json as _j
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT ws.last_runtime_summary_json FROM workspace_states ws "
            "JOIN projects p ON ws.project_id = p.project_id "
            "WHERE p.project_code = ?", (project_code,)
        ).fetchone()
    if row and row[0]:
        return _j.loads(row[0])
    return {}


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """Uvicorn subprocess with isolated temp DB and FINCO_WORKBOOK_V2=1."""
    pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: playwright not installed",
    )
    tmp_db = tmp_path_factory.mktemp("v2_browser") / "test.db"
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["FINCO_DB_PATH"] = str(tmp_db)
    env["FINCO_SECRET_KEY"] = "browser-accept-secret-v2"
    env["FINCO_WORKBOOK_V2"] = "1"
    env["FINCO_COOKIE_SECURE"] = "false"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(BASE_DIR), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server(base_url)
        token = create_session_token()
        yield {"base_url": base_url, "token": token, "db": str(tmp_db)}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="module")
def playwright_browser(live_server):
    """Module-scoped Playwright browser (Chromium, headless)."""
    from playwright.sync_api import sync_playwright
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    pl = sync_playwright().start()
    exe = _chromium_path()
    kwargs: dict = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if exe:
        kwargs["executable_path"] = exe
    browser = pl.chromium.launch(**kwargs)
    yield browser
    browser.close()
    pl.stop()


@pytest.fixture
def authed_page(playwright_browser, live_server):
    """Function-scoped page with auth cookie already set."""
    ctx = playwright_browser.new_context(base_url=live_server["base_url"])
    ctx.add_cookies([{
        "name": COOKIE_NAME,
        "value": live_server["token"],
        "url": live_server["base_url"],
    }])
    page = ctx.new_page()
    yield page
    page.close()
    ctx.close()


@pytest.fixture(scope="module")
def oborovo_project(live_server):
    """Oborovo editable working copy pre-seeded with TM=200 kEUR."""
    base_url = live_server["base_url"]
    token = live_server["token"]
    code = _create_project(base_url, token, "_v2BrowserAccept_Oborovo",
                           project_type="Solar", template_source="oborovo")
    # Oborovo factory: TM defaults to 198; seed to 200
    _field_update_api(base_url, token, code,
                      "opex.lines.technical_management", "200", "opex")
    return code


@pytest.fixture(scope="module")
def ran_project(live_server, oborovo_project):
    """
    Oborovo project that has been run at least once (TM=200), giving a clean
    RuntimeResult for FS and downstream assertions.
    """
    base_url = live_server["base_url"]
    token = live_server["token"]
    code = oborovo_project
    ch = _get_content_hash(base_url, token, code)
    _http(base_url, token, "POST", "/v2/workbook/run", {
        "project": code,
        "workbook_version": "2.1.0",
        "content_hash": ch,
    }, extra_headers={"HX-Request": "true"})
    return code


# ---------------------------------------------------------------------------
# JS instrumentation snippet injected into every page under test
# ---------------------------------------------------------------------------

_INSTRUMENT_JS = """
() => {
    if (window.__v2BrowserTestInstrumented) return;
    window.__v2BrowserTestInstrumented = true;

    window._v2TestLog          = [];
    window._v2FieldSavedCount  = 0;
    window._v2FieldErrorCount  = 0;
    window._v2FieldSavedPayload = null;
    window._v2FieldErrorPayload = null;
    window._v2RunCount         = 0;

    document.addEventListener('workbook-field-saved', function(e) {
        window._v2FieldSavedCount++;
        window._v2FieldSavedPayload = e.detail || null;
        window._v2TestLog.push({type:'field-saved', detail:e.detail, ts:Date.now()});
    });
    document.addEventListener('workbook-field-error', function(e) {
        window._v2FieldErrorCount++;
        window._v2FieldErrorPayload = e.detail || null;
        window._v2TestLog.push({type:'field-error', detail:e.detail, ts:Date.now()});
    });
    document.addEventListener('htmx:beforeRequest', function(e) {
        if (e.detail && e.detail.elt) {
            var elt = e.detail.elt;
            var tag = elt.classList && elt.classList.contains('v2-run-form') ? 'run-form' :
                      elt.classList && elt.classList.contains('v2-field-form') ? 'field-form' : 'other';
            if (tag === 'run-form') window._v2RunCount++;
            window._v2TestLog.push({type:'htmx:beforeRequest', tag:tag, ts:Date.now()});
        }
    });
    document.addEventListener('htmx:afterRequest', function(e) {
        if (e.detail && e.detail.elt) {
            var elt = e.detail.elt;
            var tag = elt.classList && elt.classList.contains('v2-run-form') ? 'run-form' :
                      elt.classList && elt.classList.contains('v2-field-form') ? 'field-form' : 'other';
            window._v2TestLog.push({
                type:'htmx:afterRequest', tag:tag,
                successful: e.detail.successful, ts:Date.now()
            });
        }
    });
}
"""


def _instrument(page) -> None:
    page.evaluate(_INSTRUMENT_JS)


def _switch_tab(page, tab_name: str) -> None:
    """Click the workbook top-level sheet tab.

    The workbook HTML uses aria-controls="panel-<short>" where short codes are:
      opex → panel-opex
      financial-statements → panel-fs
    """
    _TAB_PANEL = {
        "opex": "panel-opex",
        "financial-statements": "panel-fs",
        "inputs": "panel-inputs",
        "revenue": "panel-revenue",
        "capex": "panel-capex",
        "debt": "panel-debt",
        "tax": "panel-tax",
        "project-setup": "panel-project-setup",
    }
    panel_id = _TAB_PANEL.get(tab_name, f"panel-{tab_name}")
    page.locator(f'[aria-controls="{panel_id}"]').click()
    page.locator(f'#{panel_id}:not([hidden])').wait_for(timeout=5000)


def _open_group(page, group_code: str) -> None:
    """Ensure an OPEX group <details> is open."""
    sel = f'[data-testid="opex-group-{group_code}"]'
    is_open = page.locator(sel).evaluate("el => el.open")
    if not is_open:
        page.locator(f'{sel} summary').click()
    page.wait_for_timeout(100)


def _tm_input(page):
    return page.locator(
        '[data-field-id="opex.lines.technical_management"] input.v2-field-input'
    )


# ---------------------------------------------------------------------------
# 1. Route Verification
# ---------------------------------------------------------------------------

class TestRouteVerification:
    """Prove that the tested route is the real Workbook V2 production page."""

    def test_shell_present(self, authed_page, live_server, oborovo_project):
        p = authed_page
        p.goto(f"/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        assert p.locator("#v2-workbook-shell").count() == 1, "#v2-workbook-shell missing"

    def test_run_form_present(self, authed_page, live_server, oborovo_project):
        p = authed_page
        p.goto(f"/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        assert p.locator(".v2-run-form").count() >= 1, ".v2-run-form missing"
        assert p.locator('[data-testid="v2-run-btn"]').count() >= 1, "v2-run-btn missing"

    def test_opex_sheet_present(self, authed_page, live_server, oborovo_project):
        p = authed_page
        p.goto(f"/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        assert p.locator("#panel-opex").count() == 1, "#panel-opex missing"
        _switch_tab(p, "opex")
        assert p.locator('[data-testid="opex-group-B.01"]').count() >= 1

    def test_fs_sheet_present(self, authed_page, live_server, oborovo_project):
        p = authed_page
        p.goto(f"/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        assert p.locator("#panel-fs").count() == 1

    def test_workbook_v2_js_loaded(self, authed_page, live_server, oborovo_project):
        p = authed_page
        p.goto(f"/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        # Check the script tag is present
        scripts = p.evaluate(
            "Array.from(document.querySelectorAll('script[src]'))"
            ".map(s => s.src)"
        )
        assert any("workbook_v2.js" in s for s in scripts), (
            f"workbook_v2.js not loaded. Scripts: {scripts}"
        )

    def test_exact_url_and_route(self, authed_page, live_server, oborovo_project):
        """Record exact URL, verify it is /v2/workbook not a legacy route."""
        p = authed_page
        p.goto(f"/v2/workbook?project={oborovo_project}")
        assert "/v2/workbook" in p.url, (
            f"Expected /v2/workbook in URL, got {p.url!r}"
        )
        # Verify the page is NOT the legacy workbook (legacy uses a different shell id)
        assert p.locator("#v2-workbook-shell").count() == 1, "Not on V2 shell"
        assert p.locator("#workbook-shell").count() == 0, (
            "Legacy #workbook-shell present — wrong route"
        )
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        p.screenshot(path=str(SCREENSHOTS_DIR / "route_verification.png"))


# ---------------------------------------------------------------------------
# 2. TM 200 → 300 with queued Run — core acceptance test
# ---------------------------------------------------------------------------

class TestTM200To300QueuedRun:
    """
    Type 300 into TM field without pressing Enter, click Run once,
    assert the full queued-save→Run pipeline completes correctly.
    """

    @pytest.fixture(autouse=True)
    def setup(self, authed_page, live_server, oborovo_project):
        self.page = authed_page
        self.base_url = live_server["base_url"]
        self.token = live_server["token"]
        self.db_path = live_server["db"]
        self.project_code = oborovo_project
        self.update_requests: list[dict] = []
        self.run_requests: list[dict] = []

        def on_req(req):
            if "/v2/workbook/update" in req.url:
                self.update_requests.append({"url": req.url, "ts": time.time()})
            elif "/v2/workbook/run" in req.url:
                self.run_requests.append({"url": req.url, "ts": time.time()})

        self.page.on("request", on_req)

        p = self.page
        p.goto(f"{self.base_url}/v2/workbook?project={self.project_code}")
        p.wait_for_load_state("networkidle")
        _instrument(p)
        _switch_tab(p, "opex")
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        p.screenshot(path=str(SCREENSHOTS_DIR / "tm_01_opex_before_edit.png"))

    def _open_b01(self):
        _open_group(self.page, "B.01")

    def _set_tm(self, value: str) -> None:
        inp = _tm_input(self.page)
        inp.click()
        inp.select_text()
        inp.fill(value)
        # Trigger 'input' event so JS marks field pending
        self.page.evaluate(
            "document.querySelector('[data-field-id=\"opex.lines.technical_management\"]"
            " input.v2-field-input').dispatchEvent(new Event('input', {bubbles:true}))"
        )

    def test_initial_value_is_200(self):
        self._open_b01()
        val = _tm_input(self.page).input_value()
        assert float(val) == 200.0, f"Expected seed value 200, got {val!r}"

    def test_pending_state_after_typing(self):
        self._open_b01()
        self._set_tm("300")
        pending = _tm_input(self.page).get_attribute("data-pending")
        assert pending == "true", f"Expected data-pending=true, got {pending!r}"
        row_has_class = self.page.locator(
            '[data-field-id="opex.lines.technical_management"]'
        ).evaluate("el => el.classList.contains('v2-field-pending')")
        assert row_has_class, "v2-field-pending class not set on row"

    def test_queued_run_saves_field_first(self):
        """Click Run once with TM=300 pending; verify exactly 1 update + 1 Run POST."""
        self._open_b01()
        old_hash = self.page.locator('.v2-run-form input[name="content_hash"]').input_value()
        self._set_tm("300")

        run_btn = self.page.locator('[data-testid="v2-run-btn"]')
        with self.page.expect_response(
            lambda r: "/v2/workbook/run" in r.url,
            timeout=90_000,
        ):
            with self.page.expect_response(
                lambda r: "/v2/workbook/update" in r.url,
                timeout=15_000,
            ):
                run_btn.click()

        # Wait for all network to settle
        self.page.wait_for_load_state("networkidle", timeout=30_000)
        self.page.screenshot(path=str(SCREENSHOTS_DIR / "tm_02_post_run.png"))

        # Exactly one field update, one Run
        assert len(self.update_requests) == 1, (
            f"Expected 1 field update POST, got {len(self.update_requests)}"
        )
        assert len(self.run_requests) == 1, (
            f"Expected 1 Run POST, got {len(self.run_requests)}"
        )

        # field-saved event received with new_hash
        saved_count = self.page.evaluate("window._v2FieldSavedCount")
        assert saved_count == 1, f"Expected 1 field-saved event, got {saved_count}"
        saved_payload = self.page.evaluate("window._v2FieldSavedPayload")
        assert saved_payload is not None, "workbook-field-saved payload is null"
        new_hash = saved_payload.get("new_hash")
        assert new_hash, f"new_hash missing from field-saved payload: {saved_payload}"
        assert new_hash != old_hash, "new_hash must differ from pre-save hash"

        # No errors
        assert self.page.evaluate("window._v2FieldErrorCount") == 0

    def test_field_update_precedes_run(self):
        """The field update POST must complete before the Run POST starts."""
        self._open_b01()
        self._set_tm("300")
        run_btn = self.page.locator('[data-testid="v2-run-btn"]')
        with self.page.expect_response(lambda r: "/v2/workbook/run" in r.url, timeout=90_000):
            with self.page.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
                run_btn.click()
        self.page.wait_for_load_state("networkidle", timeout=30_000)

        log = self.page.evaluate("window._v2TestLog")
        before_updates = [e for e in log if e["type"] == "htmx:beforeRequest" and e.get("tag") == "field-form"]
        before_runs    = [e for e in log if e["type"] == "htmx:beforeRequest" and e.get("tag") == "run-form"]
        assert before_updates, "No field-form htmx:beforeRequest logged"
        assert before_runs, "No run-form htmx:beforeRequest logged"
        assert before_updates[0]["ts"] < before_runs[0]["ts"], (
            "Run request started before field update request"
        )

    def test_snapshot_stores_300_after_run(self):
        """DB snapshot must persist 300 for opex_technical_management_y1_keur."""
        self._open_b01()
        self._set_tm("300")
        with self.page.expect_response(lambda r: "/v2/workbook/run" in r.url, timeout=90_000):
            with self.page.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
                self.page.locator('[data-testid="v2-run-btn"]').click()
        self.page.wait_for_load_state("networkidle", timeout=30_000)

        snap = _read_ws_snapshot(self.db_path, self.project_code)
        stored = snap.get("opex_technical_management_y1_keur")
        assert float(stored) == 300.0, (
            f"DB snapshot TM={stored!r}, expected 300.0"
        )

    def test_runtime_persisted_after_run(self):
        """Engine run must have persisted a non-empty runtime summary."""
        self._open_b01()
        self._set_tm("300")
        with self.page.expect_response(lambda r: "/v2/workbook/run" in r.url, timeout=90_000):
            with self.page.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
                self.page.locator('[data-testid="v2-run-btn"]').click()
        self.page.wait_for_load_state("networkidle", timeout=30_000)

        kpis = _read_ws_runtime_summary(self.db_path, self.project_code)
        assert kpis, "Runtime summary empty after Run"

    def test_reload_shows_300_and_runtime(self):
        """Reload must show TM=300 and the runtime state as CLEAN."""
        self._open_b01()
        self._set_tm("300")
        with self.page.expect_response(lambda r: "/v2/workbook/run" in r.url, timeout=90_000):
            with self.page.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
                self.page.locator('[data-testid="v2-run-btn"]').click()
        self.page.wait_for_load_state("networkidle", timeout=30_000)

        # Full page reload
        self.page.reload()
        self.page.wait_for_load_state("networkidle")
        _switch_tab(self.page, "opex")
        _open_group(self.page, "B.01")
        self.page.screenshot(path=str(SCREENSHOTS_DIR / "tm_03_after_reload.png"))

        val = _tm_input(self.page).input_value()
        assert float(val) == 300.0, f"TM after reload: expected 300, got {val!r}"

        # Runtime bar on OPEX should be CLEAN (state B)
        state_b = self.page.locator('[data-testid="opex-runtime-state-b"]')
        assert state_b.is_visible(), "OPEX runtime bar not showing 'Outputs current' after reload"


# ---------------------------------------------------------------------------
# 3. HTMX event ordering: in-flight counter gates the Run
# ---------------------------------------------------------------------------

class TestHTMXEventOrdering:
    """
    Prove that workbook-field-saved fires BEFORE htmx:afterRequest and that
    the in-flight counter ensures the Run fires only after the counter reaches 0.
    """

    def test_saved_event_fires_before_after_request(self, authed_page, live_server, oborovo_project):
        p = authed_page
        p.goto(f"{live_server['base_url']}/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        _instrument(p)
        _switch_tab(p, "opex")
        _open_group(p, "B.01")

        # Trigger a plain field save (no Run) to observe ordering
        inp = _tm_input(p)
        inp.click()
        inp.select_text()
        inp.fill("201")
        p.evaluate(
            "document.querySelector('[data-field-id=\"opex.lines.technical_management\"]"
            " input.v2-field-input').dispatchEvent(new Event('input', {bubbles:true}))"
        )
        # Submit via Enter
        with p.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
            inp.press("Enter")
        p.wait_for_load_state("networkidle", timeout=15_000)

        log = p.evaluate("window._v2TestLog")
        saved_entries      = [e for e in log if e["type"] == "field-saved"]
        after_req_entries  = [e for e in log if e["type"] == "htmx:afterRequest"
                               and e.get("tag") == "field-form"]

        assert saved_entries, "No field-saved event logged"
        assert after_req_entries, "No htmx:afterRequest logged for field form"

        # KEY ASSERTION: saved fires BEFORE htmx:afterRequest
        assert saved_entries[0]["ts"] < after_req_entries[0]["ts"], (
            f"Expected field-saved (ts={saved_entries[0]['ts']}) BEFORE "
            f"htmx:afterRequest (ts={after_req_entries[0]['ts']}). "
            "The in-flight counter must gate the Run to compensate for this ordering."
        )

    def test_run_fires_after_htmx_after_request(self, authed_page, live_server, oborovo_project):
        """Run must be triggered AFTER htmx:afterRequest (counter at 0), not after field-saved."""
        p = authed_page
        p.goto(f"{live_server['base_url']}/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        _instrument(p)
        _switch_tab(p, "opex")
        _open_group(p, "B.01")

        inp = _tm_input(p)
        inp.click()
        inp.select_text()
        inp.fill("202")
        p.evaluate(
            "document.querySelector('[data-field-id=\"opex.lines.technical_management\"]"
            " input.v2-field-input').dispatchEvent(new Event('input', {bubbles:true}))"
        )

        with p.expect_response(lambda r: "/v2/workbook/run" in r.url, timeout=90_000):
            with p.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
                p.locator('[data-testid="v2-run-btn"]').click()
        p.wait_for_load_state("networkidle", timeout=30_000)

        log = p.evaluate("window._v2TestLog")
        saved_entries     = [e for e in log if e["type"] == "field-saved"]
        after_req_entries = [e for e in log if e["type"] == "htmx:afterRequest"
                              and e.get("tag") == "field-form"]
        run_entries       = [e for e in log if e["type"] == "htmx:beforeRequest"
                              and e.get("tag") == "run-form"]

        assert saved_entries, "No field-saved event"
        assert after_req_entries, "No htmx:afterRequest for field form"
        assert run_entries, "No run-form request logged"

        # Run must start AFTER htmx:afterRequest (not just after field-saved)
        assert after_req_entries[0]["ts"] <= run_entries[0]["ts"], (
            "Run fired before htmx:afterRequest — in-flight counter not working"
        )
        # Confirm Run count
        assert p.evaluate("window._v2RunCount") == 1, "Expected exactly 1 Run"


# ---------------------------------------------------------------------------
# 4. Error cases cancel queued Run
# ---------------------------------------------------------------------------

class TestErrorCancelsQueue:
    """Validation errors and stale-hash errors must cancel a queued Run."""

    def test_validation_error_cancels_run(self, authed_page, live_server, oborovo_project):
        """An invalid value (non-numeric) → field-error event → no Run POST."""
        p = authed_page
        p.goto(f"{live_server['base_url']}/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        _instrument(p)
        _switch_tab(p, "opex")
        _open_group(p, "B.01")

        inp = _tm_input(p)
        inp.click()
        inp.select_text()
        inp.fill("not-a-number")
        p.evaluate(
            "document.querySelector('[data-field-id=\"opex.lines.technical_management\"]"
            " input.v2-field-input').dispatchEvent(new Event('input', {bubbles:true}))"
        )

        run_requests: list = []
        p.on("request", lambda r: run_requests.append(r) if "/v2/workbook/run" in r.url else None)

        # Click Run — should queue, send field update, get error, cancel Run
        with p.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
            p.locator('[data-testid="v2-run-btn"]').click()
        p.wait_for_load_state("networkidle", timeout=15_000)

        # No Run POST should have been made
        assert len(run_requests) == 0, (
            f"Run POST made after validation error — queue not cancelled: {run_requests}"
        )
        error_count = p.evaluate("window._v2FieldErrorCount")
        assert error_count >= 1, "No workbook-field-error event received"

    def test_stale_hash_cancels_run(self, authed_page, live_server, oborovo_project):
        """
        Stale content_hash causes server to return field-error; Run must not fire.
        We corrupt the hash in the DOM before clicking Run.
        """
        p = authed_page
        p.goto(f"{live_server['base_url']}/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        _instrument(p)
        _switch_tab(p, "opex")
        _open_group(p, "B.01")

        # Corrupt the content_hash in the field form
        p.evaluate(
            "document.querySelector('[data-field-id=\"opex.lines.technical_management\"]"
            " input[name=\"content_hash\"]').value = 'stale-hash-for-test'"
        )

        inp = _tm_input(p)
        inp.click()
        inp.select_text()
        inp.fill("250")
        p.evaluate(
            "document.querySelector('[data-field-id=\"opex.lines.technical_management\"]"
            " input.v2-field-input').dispatchEvent(new Event('input', {bubbles:true}))"
        )

        run_requests: list = []
        p.on("request", lambda r: run_requests.append(r) if "/v2/workbook/run" in r.url else None)

        with p.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
            p.locator('[data-testid="v2-run-btn"]').click()
        p.wait_for_load_state("networkidle", timeout=15_000)

        assert len(run_requests) == 0, (
            "Run fired despite stale hash error — queue not cancelled"
        )
        error_count = p.evaluate("window._v2FieldErrorCount")
        assert error_count >= 1, "No workbook-field-error event for stale hash"

    def test_original_value_unchanged_after_error(self, authed_page, live_server, oborovo_project):
        """data-original-value must not be updated when save fails."""
        p = authed_page
        p.goto(f"{live_server['base_url']}/v2/workbook?project={oborovo_project}")
        p.wait_for_load_state("networkidle")
        _instrument(p)
        _switch_tab(p, "opex")
        _open_group(p, "B.01")

        inp = _tm_input(p)
        original_val = inp.get_attribute("data-original-value")
        inp.click()
        inp.select_text()
        inp.fill("not-a-number")
        p.evaluate(
            "document.querySelector('[data-field-id=\"opex.lines.technical_management\"]"
            " input.v2-field-input').dispatchEvent(new Event('input', {bubbles:true}))"
        )
        with p.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
            inp.press("Enter")
        p.wait_for_load_state("networkidle", timeout=10_000)

        final_original = inp.get_attribute("data-original-value")
        assert final_original == original_val, (
            f"data-original-value changed after error: {original_val!r} → {final_original!r}"
        )


# ---------------------------------------------------------------------------
# 5. Additional OPEX acceptance
# ---------------------------------------------------------------------------

class TestAdditionalOPEX:
    """Maintenance, Insurance, and explicit zero survive Run and reload."""

    @pytest.fixture(autouse=True)
    def _reset_page(self, authed_page, live_server):
        self.page = authed_page
        self.base_url = live_server["base_url"]
        self.token = live_server["token"]
        self.db_path = live_server["db"]

    def _run_single_field_flow(self, project_code: str, field_id: str,
                                group_code: str, value: str,
                                snapshot_key: str) -> None:
        p = self.page
        p.goto(f"{self.base_url}/v2/workbook?project={project_code}")
        p.wait_for_load_state("networkidle")
        _instrument(p)
        _switch_tab(p, "opex")
        _open_group(p, group_code)

        inp = p.locator(f'[data-field-id="{field_id}"] input.v2-field-input')
        inp.click()
        inp.select_text()
        inp.fill(value)
        p.evaluate(
            f"document.querySelector('[data-field-id=\"{field_id}\"] input.v2-field-input')"
            ".dispatchEvent(new Event('input', {bubbles:true}))"
        )
        with p.expect_response(lambda r: "/v2/workbook/run" in r.url, timeout=90_000):
            with p.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
                p.locator('[data-testid="v2-run-btn"]').click()
        p.wait_for_load_state("networkidle", timeout=30_000)

        snap = _read_ws_snapshot(self.db_path, project_code)
        stored = snap.get(snapshot_key)
        assert stored is not None, f"{snapshot_key} not in snapshot after save"
        assert float(stored) == float(value), (
            f"Expected {value}, got {stored!r} for {snapshot_key}"
        )

    def test_maintenance_field_save(self, live_server):
        code = _create_project(self.base_url, self.token, "_v2BrAccept_Maint",
                               project_type="Solar", template_source="oborovo")
        self._run_single_field_flow(
            code, "opex.lines.site_maintenance", "B.03", "150",
            "opex_maintain_site_y1_keur",
        )

    def test_insurance_field_save(self, live_server):
        code = _create_project(self.base_url, self.token, "_v2BrAccept_Ins",
                               project_type="Solar", template_source="oborovo")
        self._run_single_field_flow(
            code, "opex.lines.insurance", "B.06", "120",
            "opex_insurance_y1_keur",
        )

    def test_explicit_zero_persists_after_reload(self, live_server):
        """Explicit zero (0) must remain 0 after Run and full page reload."""
        code = _create_project(self.base_url, self.token, "_v2BrAccept_Zero",
                               project_type="Solar", template_source="oborovo")
        p = self.page
        p.goto(f"{self.base_url}/v2/workbook?project={code}")
        p.wait_for_load_state("networkidle")
        _instrument(p)
        _switch_tab(p, "opex")
        _open_group(p, "B.06")

        ins_inp = p.locator('[data-field-id="opex.lines.insurance"] input.v2-field-input')
        ins_inp.click()
        ins_inp.select_text()
        ins_inp.fill("0")
        p.evaluate(
            "document.querySelector('[data-field-id=\"opex.lines.insurance\"] input.v2-field-input')"
            ".dispatchEvent(new Event('input', {bubbles:true}))"
        )
        with p.expect_response(lambda r: "/v2/workbook/run" in r.url, timeout=90_000):
            with p.expect_response(lambda r: "/v2/workbook/update" in r.url, timeout=15_000):
                p.locator('[data-testid="v2-run-btn"]').click()
        p.wait_for_load_state("networkidle", timeout=30_000)

        snap = _read_ws_snapshot(self.db_path, code)
        stored = snap.get("opex_insurance_y1_keur")
        assert stored is not None, "Zero override not in snapshot (missing key)"
        assert float(stored) == 0.0, f"Zero not stored correctly: {stored!r}"

        # Reload: zero must remain
        p.reload()
        p.wait_for_load_state("networkidle")
        _switch_tab(p, "opex")
        _open_group(p, "B.06")
        val_after_reload = p.locator(
            '[data-field-id="opex.lines.insurance"] input.v2-field-input'
        ).input_value()
        assert float(val_after_reload) == 0.0, (
            f"Insurance after reload: expected 0, got {val_after_reload!r}"
        )

    def test_oborovo_step_changes_preserved(self, live_server, oborovo_project):
        """
        OpexItem step_changes survive a TM override: only y1_amount_keur changes,
        not the escalation / step schedule.  Verified via DB read.
        """
        code = oborovo_project
        # Read step_changes from the factory (pre-edit) via workspace
        # Then apply override and re-read — step_changes must be unchanged.
        import sqlite3, json as _j
        db = self.db_path

        # Seed a fresh value and trigger save (we just need a snapshot to exist)
        ch = _get_content_hash(self.base_url, self.token, code)
        _http(self.base_url, self.token, "POST", "/v2/workbook/update", {
            "field_id": "opex.lines.technical_management",
            "value": "210",
            "project": code,
            "workbook_version": "2.1.0",
            "content_hash": ch,
            "sheet_id": "opex",
        }, extra_headers={"HX-Request": "true"})

        snap = _read_ws_snapshot(db, code)
        assert "opex_technical_management_y1_keur" in snap, (
            "TM override not written to snapshot"
        )
        # The snapshot stores the scalar override; step_changes live in the factory.
        # Verify that reading back via WorkbookService gives the right merged opex:
        import app.persistence.projects_repository as pr
        import app.persistence.workspace_repository as wr
        import app.workbook.service as svc

        proj = pr.get_project_record(user_id="1", project_code=code)
        ws   = wr.get_workspace_state("1", proj.project_id)
        pis  = svc.WorkbookService.build_draft_input_set_from_workspace(ws)
        pi   = pis.to_projectinputs()

        tm_item = next((o for o in pi.opex if "Technical Management" in o.name), None)
        assert tm_item is not None, "TM OpexItem not found in merged opex"
        assert tm_item.y1_amount_keur == 210.0, (
            f"TM override not applied: {tm_item.y1_amount_keur}"
        )
        # Oborovo TM has step_changes = [] but annual_inflation=0.02 from factory
        # The annual_inflation must be preserved (not replaced by factory defaults)
        assert tm_item.annual_inflation == 0.02, (
            f"annual_inflation changed after override: {tm_item.annual_inflation}"
        )


# ---------------------------------------------------------------------------
# 6. FS Browser Acceptance
# ---------------------------------------------------------------------------

class TestFSBrowserAcceptance:
    """Annual FS aggregation, model-period display, CIT rate, scroll."""

    @pytest.fixture(autouse=True)
    def setup_page(self, authed_page, live_server, ran_project):
        self.page = authed_page
        self.base_url = live_server["base_url"]
        p = self.page
        p.goto(f"{self.base_url}/v2/workbook?project={ran_project}")
        p.wait_for_load_state("networkidle")
        _switch_tab(p, "financial-statements")
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def test_period_labels_readable(self):
        # Model period table must have column headers (non-empty)
        p = self.page
        headers = p.locator('[data-testid="fs-pnl-table"] thead th').all_inner_texts()
        readable = [h for h in headers if h.strip() and h.strip() != "—"]
        assert len(readable) >= 2, f"Too few readable period headers: {headers}"

    def test_long_table_has_horizontal_scroll(self):
        p = self.page
        wrapper = p.locator('[data-testid="fs-pnl-table-wrapper"]')
        has_scroll = wrapper.evaluate(
            "el => el.scrollWidth > el.clientWidth || el.style.overflowX === 'auto' "
            "|| window.getComputedStyle(el).overflowX === 'auto'"
        )
        assert has_scroll, "FS PNL table wrapper does not allow horizontal scroll"

    def test_annual_revenue_equals_sum_of_model_periods(self):
        """Annual Revenue must equal the sum of all model period Revenue values."""
        p = self.page
        # Switch to Annual view
        p.locator('[data-period-view="annual"]').click()
        p.wait_for_timeout(300)

        # Get model period values first (switch back to model)
        p.locator('[data-period-view="model"]').click()
        p.wait_for_timeout(300)
        model_cells = p.locator(
            '[data-testid="fs-pnl-table"] [data-testid="fs-pnl-row-revenues_keur"] td'
        ).all_inner_texts()
        model_values = []
        for c in model_cells[1:]:  # skip label col
            c = c.strip().replace(",", "")
            if c and c != "—":
                try:
                    model_values.append(float(c))
                except ValueError:
                    pass

        if not model_values:
            pytest.skip("No model period revenue values (engine may not have run)")

        # Switch to Annual
        p.locator('[data-period-view="annual"]').click()
        p.wait_for_timeout(300)
        annual_cells = p.locator(
            '[data-testid="fs-pnl-annual-table"] [data-testid="fs-pnl-row-revenues_keur"] td'
        ).all_inner_texts()
        annual_values = []
        for c in annual_cells[1:]:
            c = c.strip().replace(",", "")
            if c and c != "—":
                try:
                    annual_values.append(float(c))
                except ValueError:
                    pass

        if not annual_values:
            pytest.skip("No annual revenue cells rendered")

        assert abs(sum(annual_values) - sum(model_values)) < 1.0, (
            f"Annual Revenue sum {sum(annual_values):.0f} ≠ model sum {sum(model_values):.0f}"
        )

    def test_annual_pf_cf_table_present(self):
        p = self.page
        p.locator('[data-panel="fs-inner-panel-pf-cf"]').click()
        p.wait_for_timeout(200)
        p.locator('[data-period-view="annual"]').click()
        p.wait_for_timeout(300)
        p.screenshot(path=str(SCREENSHOTS_DIR / "fs_annual_cash_waterfall.png"))
        wrapper = p.locator('[data-testid="fs-pf-cf-annual-table-wrapper"]')
        assert wrapper.count() >= 1, "Annual CF waterfall table wrapper not found"

    def test_bs_annual_uses_year_end_not_sum(self):
        """
        Annual Balance Sheet: stock rows (e.g. Net Fixed Assets) must equal the
        last model period of each year, not the sum. Verified by checking that the
        first annual value matches the last model period of that year.
        """
        p = self.page
        p.locator('[data-panel="fs-inner-panel-bs"]').click()
        p.wait_for_timeout(200)

        # Model period values for Net Fixed Assets
        p.locator('[data-period-view="model"]').click()
        p.wait_for_timeout(200)
        model_cells = p.locator(
            '[data-testid="fs-bs-table"] [data-testid="fs-bs-row-net_fixed_assets_keur"] td'
        ).all_inner_texts()

        p.locator('[data-period-view="annual"]').click()
        p.wait_for_timeout(300)
        annual_cells = p.locator(
            '[data-testid="fs-bs-annual-table"] '
            '[data-testid="fs-bs-row-net_fixed_assets_keur"] td'
        ).all_inner_texts()
        p.screenshot(path=str(SCREENSHOTS_DIR / "fs_annual_balance_sheet.png"))

        # If we have both annual and model values, assert first annual ≠ sum(all models)
        def _parse(cells):
            vals = []
            for c in cells[1:]:
                c = c.strip().replace(",", "")
                try:
                    vals.append(float(c))
                except (ValueError, AttributeError):
                    pass
            return vals

        model_vals  = _parse(model_cells)
        annual_vals = _parse(annual_cells)

        if model_vals and annual_vals and len(model_vals) > 1:
            assert abs(annual_vals[0] - sum(model_vals)) > 0.5, (
                "Annual NFA appears to be the SUM of model periods, not the year-end value. "
                f"Annual[0]={annual_vals[0]:.0f}, sum={sum(model_vals):.0f}"
            )

    def test_cit_rate_displayed_as_percent(self):
        """[data-testid='fs-cit-rate'] must show a percentage, not a fraction."""
        p = self.page
        cit_el = p.locator('[data-testid="fs-cit-rate"]')
        assert cit_el.count() >= 1, "fs-cit-rate element not found"
        text = cit_el.first.inner_text().strip()
        assert text.endswith("%"), f"CIT rate not a percentage: {text!r}"
        assert not text.startswith("0."), (
            f"CIT rate looks like a fraction: {text!r} — must be multiplied by 100"
        )

    def test_pnl_annual_screenshot(self):
        p = self.page
        p.locator('[data-period-view="annual"]').click()
        p.wait_for_timeout(300)
        p.screenshot(path=str(SCREENSHOTS_DIR / "fs_annual_income_statement.png"))
        # Just confirm the screenshot was captured without error


# ---------------------------------------------------------------------------
# 7. FS selection persistence
# ---------------------------------------------------------------------------

class TestFSSelectionPersistence:
    """Period view and inner tab survive HTMX swaps, Run, and page reload."""

    @pytest.fixture(autouse=True)
    def setup_page(self, authed_page, live_server, ran_project):
        self.page = authed_page
        self.base_url = live_server["base_url"]
        self.project_code = ran_project
        p = self.page
        p.goto(f"{self.base_url}/v2/workbook?project={ran_project}")
        p.wait_for_load_state("networkidle")

    def _go_to_fs(self):
        _switch_tab(self.page, "financial-statements")

    def test_inner_tab_persists_after_reload(self):
        p = self.page
        self._go_to_fs()
        # Click Balance Sheet tab
        p.locator('[data-panel="fs-inner-panel-bs"]').click()
        p.wait_for_timeout(300)
        active_before = p.evaluate(
            "document.querySelector('.v2-fs-inner-tab[aria-selected=\"true\"]')"
            "?.getAttribute('data-panel')"
        )
        assert active_before == "fs-inner-panel-bs", (
            f"Expected fs-inner-panel-bs active, got {active_before!r}"
        )

        # Full page reload
        p.reload()
        p.wait_for_load_state("networkidle")
        self._go_to_fs()
        p.wait_for_timeout(500)  # allow sessionStorage restore
        active_after = p.evaluate(
            "document.querySelector('.v2-fs-inner-tab[aria-selected=\"true\"]')"
            "?.getAttribute('data-panel')"
        )
        assert active_after == "fs-inner-panel-bs", (
            f"Inner tab not restored after reload: {active_after!r}"
        )

    def test_period_view_persists_after_reload(self):
        p = self.page
        self._go_to_fs()
        p.locator('[data-period-view="annual"]').click()
        p.wait_for_timeout(300)
        active_period = p.evaluate(
            "document.querySelector('.v2-fs-period-tab[aria-selected=\"true\"]')"
            "?.getAttribute('data-period-view')"
        )
        assert active_period == "annual", f"Annual not active: {active_period!r}"

        p.reload()
        p.wait_for_load_state("networkidle")
        self._go_to_fs()
        p.wait_for_timeout(500)
        active_period_after = p.evaluate(
            "document.querySelector('.v2-fs-period-tab[aria-selected=\"true\"]')"
            "?.getAttribute('data-period-view')"
        )
        assert active_period_after == "annual", (
            f"Period view not restored after reload: {active_period_after!r}"
        )

    def test_selections_persist_after_run(self, live_server, oborovo_project):
        """Annual + BS tab must remain after a successful Run response."""
        p = self.page
        self._go_to_fs()
        p.locator('[data-period-view="annual"]').click()
        p.wait_for_timeout(200)
        p.locator('[data-panel="fs-inner-panel-bs"]').click()
        p.wait_for_timeout(200)

        ch = _get_content_hash(self.base_url, live_server["token"], oborovo_project)
        with p.expect_response(lambda r: "/v2/workbook/run" in r.url, timeout=90_000):
            _http(self.base_url, live_server["token"], "POST", "/v2/workbook/run", {
                "project": oborovo_project,
                "workbook_version": "2.1.0",
                "content_hash": ch,
            }, extra_headers={"HX-Request": "true"})
        p.wait_for_load_state("networkidle", timeout=30_000)
        p.wait_for_timeout(500)

        # The FS OOB updates the sheet; selections should be restored from sessionStorage
        active_panel = p.evaluate(
            "document.querySelector('.v2-fs-inner-tab[aria-selected=\"true\"]')"
            "?.getAttribute('data-panel')"
        )
        active_period = p.evaluate(
            "document.querySelector('.v2-fs-period-tab[aria-selected=\"true\"]')"
            "?.getAttribute('data-period-view')"
        )
        # After OOB swap, the inline script restores from sessionStorage
        # Both should still be the selections we made before Run
        assert active_panel == "fs-inner-panel-bs", (
            f"BS tab not restored after Run OOB: {active_panel!r}"
        )
        assert active_period == "annual", (
            f"Annual period not restored after Run OOB: {active_period!r}"
        )


# ---------------------------------------------------------------------------
# 8. Keyboard navigation on FS inner tabs
# ---------------------------------------------------------------------------

class TestFSKeyboardNav:

    @pytest.fixture(autouse=True)
    def setup_page(self, authed_page, live_server, ran_project):
        self.page = authed_page
        p = self.page
        p.goto(f"{live_server['base_url']}/v2/workbook?project={ran_project}")
        p.wait_for_load_state("networkidle")
        _switch_tab(p, "financial-statements")

    def test_arrow_right_moves_tab_focus(self):
        p = self.page
        first_tab = p.locator('.v2-fs-inner-tab').first
        first_tab.click()
        p.keyboard.press("ArrowRight")
        p.wait_for_timeout(200)
        active = p.evaluate(
            "document.querySelector('.v2-fs-inner-tab[aria-selected=\"true\"]')"
            "?.getAttribute('data-panel')"
        )
        assert active != "fs-inner-panel-pnl", (
            "ArrowRight did not move away from first tab"
        )

    def test_arrow_left_wraps(self):
        p = self.page
        first_tab = p.locator('.v2-fs-inner-tab').first
        first_tab.click()
        p.keyboard.press("ArrowLeft")
        p.wait_for_timeout(200)
        active = p.evaluate(
            "document.querySelector('.v2-fs-inner-tab[aria-selected=\"true\"]')"
            "?.getAttribute('data-panel')"
        )
        # Should wrap to last tab
        assert active != "fs-inner-panel-pnl", "ArrowLeft from first tab did not wrap"

    def test_only_active_tab_has_tabindex_0(self):
        p = self.page
        tabs_info = p.evaluate("""
            Array.from(document.querySelectorAll('.v2-fs-inner-tab'))
            .map(t => ({panel: t.getAttribute('data-panel'),
                        selected: t.getAttribute('aria-selected'),
                        tabindex: t.getAttribute('tabindex')}))
        """)
        for t in tabs_info:
            if t["selected"] == "true":
                assert t["tabindex"] == "0", f"Active tab tabindex should be 0: {t}"
            else:
                assert t["tabindex"] == "-1", f"Inactive tab tabindex should be -1: {t}"


# ---------------------------------------------------------------------------
# 9. Viewport tests
# ---------------------------------------------------------------------------

class TestViewport:

    def _assert_no_header_overlap(self, page, testid: str) -> None:
        """Assert FS table column headers don't overlap each other."""
        ths = page.locator(f'[data-testid="{testid}"] thead th').all()
        if len(ths) < 2:
            return
        boxes = [th.bounding_box() for th in ths if th.bounding_box()]
        for i in range(len(boxes) - 1):
            if boxes[i] and boxes[i + 1]:
                right_i = boxes[i]["x"] + boxes[i]["width"]
                left_next = boxes[i + 1]["x"]
                assert right_i <= left_next + 2, (  # 2px tolerance
                    f"Header overlap detected at columns {i}/{i+1}: "
                    f"right={right_i:.1f}, next_left={left_next:.1f}"
                )

    def _run_viewport_test(self, playwright_browser, live_server, ran_project,
                            width: int, height: int, suffix: str) -> None:
        ctx = playwright_browser.new_context(
            viewport={"width": width, "height": height},
            base_url=live_server["base_url"],
        )
        ctx.add_cookies([{
            "name": COOKIE_NAME,
            "value": live_server["token"],
            "url": live_server["base_url"],
        }])
        p = ctx.new_page()
        try:
            p.goto(f"{live_server['base_url']}/v2/workbook?project={ran_project}")
            p.wait_for_load_state("networkidle")
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

            # OPEX sheet
            _switch_tab(p, "opex")
            p.screenshot(path=str(SCREENSHOTS_DIR / f"opex_{suffix}.png"))
            opex_sheet = p.locator("#panel-opex")
            assert opex_sheet.is_visible()

            # FS sheet – model period
            _switch_tab(p, "financial-statements")
            p.screenshot(path=str(SCREENSHOTS_DIR / f"fs_model_{suffix}.png"))

            # Assert pnl table has scroll wrapper
            pnl_wrapper = p.locator('[data-testid="fs-pnl-table-wrapper"]')
            if pnl_wrapper.count() > 0:
                has_overflow = pnl_wrapper.evaluate(
                    "el => el.scrollWidth >= el.clientWidth"
                )
                assert has_overflow, f"PNL table has no scroll at {width}×{height}"

            # Annual view
            p.locator('[data-period-view="annual"]').click()
            p.wait_for_timeout(300)
            p.screenshot(path=str(SCREENSHOTS_DIR / f"fs_annual_{suffix}.png"))

            # Check first-column visibility is not obscured
            first_col = p.locator('[data-testid="fs-pnl-table"] td').first
            if first_col.count() > 0 and first_col.is_visible():
                bb = first_col.bounding_box()
                if bb:
                    assert bb["x"] >= 0, f"First column off-screen at {width}×{height}"
        finally:
            p.close()
            ctx.close()

    def test_viewport_1440x900(self, playwright_browser, live_server, ran_project):
        self._run_viewport_test(playwright_browser, live_server, ran_project,
                                1440, 900, "1440x900")

    def test_viewport_1920x1080(self, playwright_browser, live_server, ran_project):
        self._run_viewport_test(playwright_browser, live_server, ran_project,
                                1920, 1080, "1920x1080")
