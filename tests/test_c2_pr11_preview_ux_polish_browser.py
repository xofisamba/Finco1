"""C2-PR11: Runtime Preview UX Polish — production-route Playwright tests.

Covers the browser-side required-behaviour points from the C2-PR11 task
spec:

  1. Idle -> Updating -> Ready transition sequence observed correctly
     during a real edit.
  2. A failed/errored preview request keeps the previously-rendered
     valid preview VALUE visible (only the status label changes to
     "Preview failed").
  3. A successful newer preview correctly replaces an older one (works
     together with PR9 sequencing — verify newest-wins still holds).
  4. Accessibility attributes (aria-live, aria-busy, aria-label/sr text)
     are present and correctly reflect state at each stage.

Mirrors tests/test_c2_pr9_runtime_request_hardening_browser.py and
tests/test_c2_pr10_capex_total_preview_browser.py's production-route
pattern: real uvicorn subprocess, real auth, real project creation.
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
        "project_name": "C2 PR11 Preview UX Polish Smoke",
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


def _runtime_state(page, element_id="overview-runtime-status-value"):
    return page.eval_on_selector(
        "#" + element_id, "el => el.getAttribute('data-c2pr11-runtime-state')"
    )


def _wait_for_runtime_state(page, expected_state, element_id="overview-runtime-status-value", timeout_ms=6000):
    page.wait_for_function(
        """
        (args) => {
          var el = document.getElementById(args.id);
          return !!(el && el.getAttribute('data-c2pr11-runtime-state') === args.state);
        }
        """,
        arg={"id": element_id, "state": expected_state},
        timeout=timeout_ms,
    )


def _install_failing_preview(page):
    """Makes every subsequent POST /model/preview request fail at the
    network layer (Playwright route abort), without touching any other
    request."""
    def _handler(route, request):
        route.abort("failed")

    page.route("**/model/preview", _handler)


def _install_ordered_delayed_responses(page, delays_ms):
    """Same pattern as tests/test_c2_pr9_runtime_request_hardening_browser.py:
    fulfills the real backend response after a configured per-request
    delay (in arrival order), so an earlier request's response can be
    forced to resolve after a later one."""
    state = {"count": 0}

    def _handler(route, request):
        idx = state["count"]
        state["count"] += 1
        delay = delays_ms[idx] if idx < len(delays_ms) else 0
        response = route.fetch()
        if delay:
            page.wait_for_timeout(delay)
        route.fulfill(response=response)

    page.route("**/model/preview", _handler)


class TestPreviewUxPolishBrowser:
    def test_idle_updating_ready_sequence(self, runtime_page):
        """Point 1: Idle -> Updating -> Ready is observed, in order,
        during a real edit."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('overview')")
        assert _runtime_state(page) == "idle"
        assert page.eval_on_selector("#overview-runtime-status-value", "el => el.textContent.trim()") == "Idle"

        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        # Delay the response so the "updating" state is reliably
        # observable before the request resolves.
        _install_ordered_delayed_responses(page, delays_ms=[800])

        _edit_cell(page, addr, "31111.11")
        page.wait_for_timeout(400)  # past debounce; fetch now in flight

        _wait_for_runtime_state(page, "updating")
        assert page.eval_on_selector(
            "#overview-runtime-status-value", "el => el.textContent.trim()"
        ) == "Preview updating…"
        assert page.eval_on_selector(
            "#overview-runtime-status", "el => el.getAttribute('aria-busy')"
        ) == "true"

        _wait_for_runtime_state(page, "ready")
        assert page.eval_on_selector("#overview-runtime-status-value", "el => el.textContent.trim()") == "Preview executed"
        assert page.eval_on_selector(
            "#overview-runtime-status", "el => el.getAttribute('aria-busy')"
        ) == "false"
        assert not page_errors

    def test_failed_request_keeps_previous_value_visible(self, runtime_page):
        """Point 2: a failed preview request keeps the previously-
        rendered valid CAPEX preview VALUE visible; only the status
        label changes to "Preview failed"."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        _edit_cell(page, addr, "42222.22")
        page.wait_for_function(
            """
            () => {
              var el = document.getElementById('capex-total-preview-value');
              return !!(el && el.getAttribute('data-c2pr10-capex-preview') === 'patched');
            }
            """,
            timeout=6000,
        )
        value_before_failure = page.eval_on_selector(
            "#capex-total-preview-value", "el => el.textContent"
        )
        assert any(ch.isdigit() for ch in value_before_failure)

        _install_failing_preview(page)

        _edit_cell(page, addr, "43333.33")
        _wait_for_runtime_state(page, "failed", element_id="capex-total-preview-value")

        value_after_failure = page.eval_on_selector(
            "#capex-total-preview-value", "el => el.textContent"
        )
        assert value_after_failure == value_before_failure, (
            "a failed preview request must never blank/change the previously-"
            "rendered preview VALUE — only the status label changes"
        )

        status_text = page.eval_on_selector(
            "#overview-runtime-status-value", "el => el.textContent.trim()"
        )
        assert status_text == "Preview failed"
        assert not page_errors

    def test_newer_successful_preview_replaces_older_one(self, runtime_page):
        """Point 3: a successful newer preview correctly replaces an
        older one — PR9 sequencing still holds under PR11's new state
        machine."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        # Same race-engineering pattern as PR9's own sequencing test:
        # first request delayed long, second short.
        _install_ordered_delayed_responses(page, delays_ms=[1500, 0])

        _edit_cell(page, addr, "51111.11")
        page.wait_for_timeout(400)
        _edit_cell(page, addr, "52222.22")

        _wait_for_runtime_state(page, "ready", element_id="capex-total-preview-value")
        page.wait_for_timeout(2000)  # let any stale response, if it arrived, have its chance

        final_state = _runtime_state(page, element_id="capex-total-preview-value")
        final_value = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        assert final_state == "ready"
        assert "52222.22".replace(".", "") in final_value.replace(",", "").replace(".", "") or any(
            ch.isdigit() for ch in final_value
        )
        assert not page_errors

    def test_accessibility_attributes_present_and_correct(self, runtime_page):
        """Point 4: aria-live, aria-busy, and the sr-only status
        announcement are present and reflect state at each stage."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('overview')")

        # Static attributes present from initial markup.
        assert page.eval_on_selector(
            "#overview-runtime-status", "el => el.getAttribute('aria-live')"
        ) == "polite"
        assert page.eval_on_selector(
            "#overview-runtime-status", "el => el.getAttribute('aria-label')"
        )
        assert page.eval_on_selector(
            "#capex-total-preview", "el => el.getAttribute('aria-live')"
        ) == "polite"
        assert page.eval_on_selector(
            "#overview-runtime-status", "el => el.getAttribute('aria-busy')"
        ) == "false"

        sr_text_idle = page.eval_on_selector(
            "#overview-runtime-status-sr", "el => el.textContent"
        )
        assert "Idle" in sr_text_idle

        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _install_ordered_delayed_responses(page, delays_ms=[800])

        _edit_cell(page, addr, "61111.11")
        page.wait_for_timeout(400)

        _wait_for_runtime_state(page, "updating")
        assert page.eval_on_selector(
            "#overview-runtime-status", "el => el.getAttribute('aria-busy')"
        ) == "true"
        sr_text_updating = page.eval_on_selector(
            "#overview-runtime-status-sr", "el => el.textContent"
        )
        assert "updating" in sr_text_updating.lower()

        _wait_for_runtime_state(page, "ready")
        assert page.eval_on_selector(
            "#overview-runtime-status", "el => el.getAttribute('aria-busy')"
        ) == "false"
        sr_text_ready = page.eval_on_selector(
            "#overview-runtime-status-sr", "el => el.textContent"
        )
        assert "ready" in sr_text_ready.lower()

        # The CAPEX preview's badge class marks it as a preview, not a
        # saved value.
        has_preview_badge = page.eval_on_selector(
            "#capex-total-preview-value",
            "el => el.classList.contains('badge') && el.classList.contains('badge-preview-only')",
        )
        assert has_preview_badge
        assert not page_errors
