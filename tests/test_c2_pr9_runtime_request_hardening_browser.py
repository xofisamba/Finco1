"""C2-PR9: Runtime Request Hardening — production-route Playwright tests.

Covers the browser-side required-behaviour points from the C2-PR9 task
spec:

  1. Rapid edits generate multiple preview attempts.
  2. Earlier requests are aborted.
  3. Only the newest response patches #overview-runtime-status-value.
  4. Exactly one visible runtime state survives after rapid edits settle.
  5. No Save is triggered by any of this.
  6. No Run is triggered by any of this.
  7. No financial values change anywhere on the page.

Mirrors tests/test_c2_pr8_first_runtime_slice_browser.py's production-
route pattern: real uvicorn subprocess, real auth, real project
creation. Network delay/ordering is engineered via Playwright's
``page.route()`` interception of ``/model/preview`` (the real client
code still issues the real fetch(); only the response timing for the
*test* is controlled, so the AbortController/sequencing logic under
test runs unmodified, production code).
"""
from __future__ import annotations

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

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

from app.auth import create_session_token  # noqa: E402  (after env setup)

COOKIE_NAME = "finco_session"


def _pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_for_health(base_url, timeout=20.0):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/public-health", timeout=2.0) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
        time.sleep(0.25)
    raise AssertionError(f"app did not become healthy at {base_url!r}: {last_error!r}")


def _create_user_project(base_url, token):
    form = urllib.parse.urlencode({
        "project_name": "C2 PR9 Runtime Request Hardening Smoke",
        "project_type": "Solar",
        "template_source": "generic_solar",
        "country_market": "Croatia",
        "capacity_mw": "50",
        "cod_date": "2027-01-01",
        "construction_months": "12",
        "horizon_years": "25",
        "tariff_eur_mwh": "60",
        "ppa_term_years": "15",
        "p50_hours": "1400",
        "opex_y1_keur": "1000",
        "total_capex_keur": "50000",
        "gearing_pct": "70",
        "interest_rate_pct": "5",
        "tenor_years": "15",
        "target_dscr": "1.30",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/projects/create",
        data=form,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": f"{COOKIE_NAME}={token}",
        },
    )
    with urllib.request.urlopen(req, timeout=10.0) as response:
        redirect = response.headers.get("HX-Redirect")
        assert redirect, "expected HX-Redirect header from /projects/create"
    project_code = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query).get("project", [None])[0]
    assert project_code, f"could not parse project code from redirect {redirect!r}"
    return project_code


@pytest.fixture(scope="module")
def live_server():
    pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run this test",
    )
    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
    env.setdefault("FINCO_COOKIE_SECURE", "false")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_health(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture
def runtime_page(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    sync_playwright = playwright.sync_playwright

    token = create_session_token()
    project_code = _create_user_project(live_server, token)

    ctx = sync_playwright().start()
    try:
        browser = ctx.chromium.launch()
    except Exception:
        try:
            browser = ctx.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        except Exception as exc:
            ctx.stop()
            pytest.skip(f"OPTIONAL_BROWSER_DEPENDENCY_MISSING_BROWSER_BINARIES: {exc}")

    browser_context = browser.new_context()
    browser_context.add_cookies([{
        "name": COOKIE_NAME,
        "value": token,
        "url": live_server,
    }])
    page = browser_context.new_page()
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.goto(f"{live_server}/?project={project_code}", wait_until="networkidle")

    try:
        yield page, page_errors, project_code
    finally:
        browser.close()
        ctx.stop()


def _first_editable_amount_addr(page, grid_id, kind="amount"):
    return page.evaluate(
        """
        (args) => {
          var cell = document.querySelector(
            '[data-fc-grid="' + args.gridId + '"] [data-fc-cell="true"][data-fc-editable="true"][data-fc-kind="' + args.kind + '"]'
          );
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """,
        {"gridId": grid_id, "kind": kind},
    )


def _edit_cell(page, addr, value):
    page.evaluate(
        """
        (args) => {
          var input = document.querySelector('[data-fc-addr="' + args.addr + '"] input');
          document.activeElement && document.activeElement.blur();
          input.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          input.focus();
          input.value = args.value;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        {"addr": addr, "value": value},
    )


def _wait_for_status_value(page, expected_substring, timeout_ms=6000):
    page.wait_for_function(
        """
        (expected) => {
          var el = document.getElementById('overview-runtime-status-value');
          return !!(el && el.textContent && el.textContent.indexOf(expected) !== -1);
        }
        """,
        arg=expected_substring,
        timeout=timeout_ms,
    )


def _install_ordered_delayed_responses(page, delays_ms):
    """Intercepts every POST /model/preview request and fulfills it
    with the real backend response, but only after the configured
    per-request delay (in arrival order). This lets a test force an
    *earlier* request's response to resolve *after* a *later* request's
    response, deterministically, without faking the response payload
    itself — the real backend still produced it. Returns a list (filled
    as requests arrive) the test can inspect afterwards."""
    state = {"count": 0}
    seen_urls = []

    def _handler(route, request):
        idx = state["count"]
        state["count"] += 1
        seen_urls.append(request.url)
        delay = delays_ms[idx] if idx < len(delays_ms) else 0
        response = route.fetch()
        if delay:
            page.wait_for_timeout(delay)
        route.fulfill(response=response)

    page.route("**/model/preview", _handler)
    return seen_urls


class TestRuntimeRequestHardeningBrowser:
    def test_rapid_edits_generate_multiple_preview_attempts(self, runtime_page):
        """Point 1: rapid edits (each past the debounce window) each
        generate their own /model/preview attempt."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        preview_requests = []
        page.on("request", lambda req: preview_requests.append(req) if "/model/preview" in req.url else None)

        _edit_cell(page, addr, "1111.11")
        page.wait_for_timeout(400)  # past the 250ms debounce
        _edit_cell(page, addr, "2222.22")
        page.wait_for_timeout(400)
        _edit_cell(page, addr, "3333.33")
        page.wait_for_timeout(1500)

        assert len(preview_requests) >= 2, (
            f"expected multiple preview attempts from rapid edits, got {len(preview_requests)}"
        )
        assert not page_errors

    def test_earlier_requests_are_aborted(self, runtime_page):
        """Point 2: when a new flush fires before a previous preview
        request has resolved, the previous request is aborted (its
        request object reports a 'failed'/aborted outcome rather than
        completing normally)."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        # Delay every response substantially so a second edit's flush
        # is guaranteed to fire while the first request is still
        # in-flight, giving AbortController something real to abort.
        _install_ordered_delayed_responses(page, delays_ms=[1500, 0])

        failed_urls = []
        finished_urls = []
        page.on("requestfailed", lambda req: failed_urls.append(req.url) if "/model/preview" in req.url else None)
        page.on("requestfinished", lambda req: finished_urls.append(req.url) if "/model/preview" in req.url else None)

        _edit_cell(page, addr, "4444.44")
        page.wait_for_timeout(400)  # past debounce; first flush's fetch is now in flight
        _edit_cell(page, addr, "5555.55")
        # Wait long enough for the second flush's fetch to resolve and
        # the (aborted) first one to be reported as failed.
        page.wait_for_timeout(3000)

        assert failed_urls, "expected the earlier, superseded /model/preview request to be reported as aborted/failed"
        assert not page_errors

    def test_only_newest_response_patches_status_element(self, runtime_page):
        """Point 3: even if an earlier request's response could
        theoretically still resolve, only the response belonging to the
        most recent request is ever allowed to patch
        #overview-runtime-status-value — the sequence guard discards
        anything else silently (no throw, no DOM patch from a stale
        response)."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('overview')")
        initial_text = page.evaluate(
            "document.getElementById('overview-runtime-status-value').textContent.trim()"
        )
        assert initial_text == "Idle"

        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        # First request delayed long, second short — if sequencing
        # were broken, the long-delayed first response could land
        # *after* the second and stomp the DOM with a stale render.
        # Since both responses are the same stub shape in this PR,
        # the strongest available DOM-level assertion is "the status
        # element settles, deterministically, to exactly one value and
        # never flips around" — combined with the abort assertion in
        # the previous test (which proves the seq guard's defense in
        # depth actually has stale candidates to discard).
        _install_ordered_delayed_responses(page, delays_ms=[1500, 0])

        _edit_cell(page, addr, "6666.66")
        page.wait_for_timeout(400)
        _edit_cell(page, addr, "7777.77")

        _wait_for_status_value(page, "Preview executed")
        page.wait_for_timeout(2000)  # let any stale response, if it arrived, have its chance

        final_text = page.evaluate(
            "document.getElementById('overview-runtime-status-value').textContent.trim()"
        )
        assert final_text == "Preview executed"
        assert not page_errors

    def test_exactly_one_visible_runtime_state_survives_after_settling(self, runtime_page):
        """Point 4: after a burst of rapid edits settles, exactly one
        runtime status string is visible in the DOM (no leftover/
        duplicate status node, no flicker artifact left behind)."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        for value in ["8881.1", "8882.2", "8883.3", "8884.4"]:
            _edit_cell(page, addr, value)
            page.wait_for_timeout(120)  # within the debounce window — collapses

        page.wait_for_timeout(2000)

        matching_elements = page.evaluate(
            "document.querySelectorAll('#overview-runtime-status-value').length"
        )
        assert matching_elements == 1
        assert not page_errors

    def test_no_save_action_triggered_by_rapid_edits(self, runtime_page):
        """Point 5."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        save_requests = []
        page.on("request", lambda req: save_requests.append(req.url) if "/scenarios/save" in req.url else None)

        for value in ["9991.1", "9992.2", "9993.3"]:
            _edit_cell(page, addr, value)
            page.wait_for_timeout(400)

        page.wait_for_timeout(1000)
        assert save_requests == []
        assert not page_errors

    def test_no_run_action_triggered_by_rapid_edits(self, runtime_page):
        """Point 6."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        run_requests = []
        page.on("request", lambda req: run_requests.append(req.url) if req.url.rstrip("/").endswith("/run") else None)

        for value in ["1101.1", "1102.2", "1103.3"]:
            _edit_cell(page, addr, value)
            page.wait_for_timeout(400)

        page.wait_for_timeout(1000)
        assert run_requests == []
        assert not page_errors

    def test_no_financial_values_change_after_rapid_edits(self, runtime_page):
        """Point 7."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('overview')")
        before_kpis = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('.dashboard-kpi-value, [data-p2min3-kpi-status]'))
                       .map((el) => el.textContent.trim())
            """
        )

        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        for value in ["1201.1", "1202.2", "1203.3"]:
            _edit_cell(page, addr, value)
            page.wait_for_timeout(400)
        page.wait_for_timeout(1000)

        page.evaluate("window.switchTab('overview')")
        after_kpis = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('.dashboard-kpi-value, [data-p2min3-kpi-status]'))
                       .map((el) => el.textContent.trim())
            """
        )

        assert before_kpis == after_kpis
        assert not page_errors
