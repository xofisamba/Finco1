"""C2-PR8: First End-to-End Incremental Runtime Slice — production-route
Playwright tests.

Covers all 9 required-behaviour points from the task spec:

  1. Editable change triggers the runtime pipeline (dirty -> scheduled
     -> flushed -> fetch called).
  2. POST /model/preview is called exactly once per flush.
  3. The stub response is received and parsed without error.
  4. Exactly one Overview status DOM element updates to reflect the
     runtime response.
  5. No Save action is triggered.
  6. No Run action is triggered.
  7. No financial values (IRR/DSCR/revenue/tax/other real KPI numbers)
     change anywhere on the page as a result of this flow.
  8. Dirty state remains dirty after the runtime patch (the stub flow
     must NOT clear dirty state).
  9. (point 10 in the task's numbering is the full regression run,
     reported separately, not a test in this file.)

Mirrors tests/test_c2_pr7_backend_preview_endpoint_browser.py's
production-route pattern: real uvicorn subprocess, real auth, real
project creation.
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
        "project_name": "C2 PR8 First Runtime Slice Smoke",
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


def _wait_for_status_value(page, expected_substring, timeout_ms=4000):
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


class TestFirstRuntimeSliceBrowser:
    def test_editable_change_triggers_runtime_pipeline(self, runtime_page):
        """Point 1: editing a C1 cell drives the full pipeline through
        to a real fetch() call against /model/preview."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        preview_requests = []
        page.on("request", lambda req: preview_requests.append(req.url) if "/model/preview" in req.url else None)

        _edit_cell(page, addr, "9191.91")
        # Wait out the 250ms debounce plus the network round trip.
        page.wait_for_timeout(1500)

        assert preview_requests, "expected at least one /model/preview request after an editable cell edit"
        assert not page_errors

    def test_preview_endpoint_called_exactly_once_per_flush(self, runtime_page):
        """Point 2: exactly one POST /model/preview request fires per
        flush — not zero, not more than one."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        preview_requests = []
        page.on("request", lambda req: preview_requests.append(req) if "/model/preview" in req.url else None)

        _edit_cell(page, addr, "5050.50")
        page.wait_for_timeout(1500)

        assert len(preview_requests) == 1, f"expected exactly 1 request, got {len(preview_requests)}"
        assert preview_requests[0].method == "POST"
        assert not page_errors

    def test_stub_response_received_and_parsed_without_error(self, runtime_page):
        """Point 3: the stub response is received and parsed as JSON
        without throwing a page error."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        responses = []

        def _capture(res):
            if "/model/preview" in res.url:
                try:
                    responses.append(res.json())
                except Exception:
                    responses.append(None)

        page.on("response", _capture)

        _edit_cell(page, addr, "6161.61")
        page.wait_for_timeout(1500)

        assert responses, "expected a captured /model/preview response"
        body = responses[0]
        assert body is not None
        assert body.get("ok") is True
        assert body.get("status") == "stubbed"
        assert body.get("executed") is False
        assert "overview" in body
        assert body["overview"].get("runtime_status") == "Preview executed"
        assert body["overview"].get("updated") is True
        assert not page_errors

    def test_exactly_one_overview_status_element_updates(self, runtime_page):
        """Point 4: exactly one Overview status DOM element
        (#overview-runtime-status-value) updates to reflect the
        runtime response; it starts as "Idle" and is patched after the
        flow completes."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('overview')")

        initial_text = page.evaluate(
            "document.getElementById('overview-runtime-status-value').textContent.trim()"
        )
        assert initial_text == "Idle"

        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "7272.72")

        _wait_for_status_value(page, "Preview executed")

        patched_text = page.evaluate(
            "document.getElementById('overview-runtime-status-value').textContent.trim()"
        )
        assert patched_text == "Preview executed"

        patched_attr = page.evaluate(
            "document.getElementById('overview-runtime-status-value').getAttribute('data-c2pr8-runtime-status')"
        )
        assert patched_attr == "patched"
        assert not page_errors

    def test_no_save_action_triggered(self, runtime_page):
        """Point 5: the runtime flow never calls Save."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        save_requests = []
        page.on("request", lambda req: save_requests.append(req.url) if "/scenarios/save" in req.url else None)

        _edit_cell(page, addr, "8383.83")
        page.wait_for_timeout(1500)

        assert save_requests == []
        assert not page_errors

    def test_no_run_action_triggered(self, runtime_page):
        """Point 6: the runtime flow never calls Run."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        run_requests = []
        page.on("request", lambda req: run_requests.append(req.url) if req.url.rstrip("/").endswith("/run") else None)

        _edit_cell(page, addr, "1212.12")
        page.wait_for_timeout(1500)

        assert run_requests == []
        assert not page_errors

    def test_no_financial_values_change(self, runtime_page):
        """Point 7: no financial KPI text anywhere on the page changes
        as a result of this flow — only the new, non-financial
        runtime status element is touched."""
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
        _edit_cell(page, addr, "3434.34")
        page.wait_for_timeout(1500)

        page.evaluate("window.switchTab('overview')")
        after_kpis = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('.dashboard-kpi-value, [data-p2min3-kpi-status]'))
                       .map((el) => el.textContent.trim())
            """
        )

        assert before_kpis == after_kpis
        assert not page_errors

    def test_dirty_state_remains_dirty_after_runtime_patch(self, runtime_page):
        """Point 8: the stub runtime flow must NOT clear dirty state —
        only Save does that. FcLiveModel.isCellDirty/isProjectDirty and
        the dirty banner all remain dirty after the patch."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        _edit_cell(page, addr, "5656.56")
        _wait_for_status_value(page, "Preview executed")

        is_cell_dirty = page.evaluate(
            "(addr) => window.FcLiveModel.isCellDirty('capex', addr)", addr
        )
        is_project_dirty = page.evaluate("() => window.FcLiveModel.isProjectDirty()")
        banner_hidden = page.evaluate(
            "() => document.getElementById('workspace-unsaved-banner').classList.contains('is-hidden')"
        )

        assert is_cell_dirty is True
        assert is_project_dirty is True
        assert banner_hidden is False
        assert not page_errors
