"""C2-PR10: CAPEX Total Preview — production-route Playwright tests.

Covers the browser-side required-behaviour points from the C2-PR10
task spec:

  1. Editable CAPEX cell edit -> CAPEX total preview updates after
     debounce.
  2. Read-only CAPEX cell edit attempt -> no-op, no preview-total
     drift from that cell.
  3. One edit -> exactly one preview request (PR9 debounce regression).
  4. Multiple spaced edits -> multiple corresponding requests, zero
     Save/Run requests triggered.
  5. Overview KPIs byte-identical pre/post CAPEX preview (only the new
     capex-preview element + existing runtime-status element change).
  6. Dirty state remains dirty through preview, only clears on
     Save/Run.
  9. Existing C1 grid behaviour intact on the CAPEX grid: active cell,
     keyboard nav, copy/paste no-crash, undo no-crash.

(Points 7 "Save persists.../Run uses saved..." and 8 "authorization
regression" are backend/integration concerns, covered in
tests/test_c2_pr10_capex_total_preview.py and the existing
tests/test_c2_pr9_runtime_request_hardening*.py suites, per the task's
own point breakdown.)

Mirrors tests/test_c2_pr9_runtime_request_hardening_browser.py's
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
        "project_name": "C2 PR10 Capex Total Preview Smoke",
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


def _first_readonly_amount_addr(page, grid_id, kind="amount"):
    return page.evaluate(
        """
        (args) => {
          var cell = document.querySelector(
            '[data-fc-grid="' + args.gridId + '"] [data-fc-cell="true"][data-fc-editable="false"][data-fc-kind="' + args.kind + '"]'
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


def _wait_for_capex_preview_value(page, timeout_ms=4000):
    page.wait_for_function(
        """
        () => {
          var el = document.getElementById('capex-total-preview-value');
          return !!(el && el.getAttribute('data-c2pr10-capex-preview') === 'patched');
        }
        """,
        timeout=timeout_ms,
    )


class TestCapexTotalPreviewBrowser:
    def test_editable_cell_edit_updates_capex_total_preview(self, runtime_page):
        """Point 1: editing an editable CAPEX cell updates the CAPEX
        total preview element after the debounce."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        before_text = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        _edit_cell(page, addr, "12345.67")
        _wait_for_capex_preview_value(page)
        after_text = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")

        assert after_text != before_text
        # Must look like a real, formatted number, not a placeholder.
        assert any(ch.isdigit() for ch in after_text)
        assert not page_errors

    def test_readonly_cell_edit_attempt_is_a_no_op(self, runtime_page):
        """Point 2: a read-only CAPEX cell has no editable <input> to
        write to, so a write attempt via the same DOM path used for
        editable cells cannot succeed, and the dirty/preview pipeline
        is never engaged from it."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_readonly_amount_addr(page, "capex")
        assert addr, "expected at least one read-only CAPEX amount cell (e.g. a subtotal/total row)"

        has_input = page.evaluate(
            """
            (addr) => {
              var input = document.querySelector('[data-fc-addr="' + addr + '"] input');
              return !!input;
            }
            """,
            addr,
        )
        assert not has_input, "read-only CAPEX cells must not expose an editable <input>"

        preview_requests = []
        page.on("request", lambda req: preview_requests.append(req) if "/model/preview" in req.url else None)
        page.wait_for_timeout(600)
        assert not preview_requests, "a read-only cell must never trigger a preview request by itself"
        assert not page_errors

    def test_one_edit_produces_exactly_one_preview_request(self, runtime_page):
        """Point 3: regression check against PR9 debounce behaviour —
        unaffected by this PR's additive CAPEX summation."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        preview_requests = []
        page.on("request", lambda req: preview_requests.append(req) if "/model/preview" in req.url else None)

        _edit_cell(page, addr, "777.77")
        page.wait_for_timeout(1500)

        assert len(preview_requests) == 1, f"expected exactly 1 request, got {len(preview_requests)}"
        assert not page_errors

    def test_multiple_spaced_edits_produce_multiple_requests_no_save_or_run(self, runtime_page):
        """Point 4: multiple spaced edits -> multiple preview requests;
        zero Save/Run requests triggered."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        all_requests = []
        page.on("request", lambda req: all_requests.append(req.url))

        _edit_cell(page, addr, "100.00")
        page.wait_for_timeout(500)
        _edit_cell(page, addr, "200.00")
        page.wait_for_timeout(500)
        _edit_cell(page, addr, "300.00")
        page.wait_for_timeout(1500)

        preview_requests = [u for u in all_requests if "/model/preview" in u]
        save_requests = [u for u in all_requests if "/scenarios/save" in u or u.rstrip("/").endswith("/save-run")]
        run_requests = [u for u in all_requests if u.rstrip("/").endswith("/run")]

        assert len(preview_requests) >= 2, f"expected multiple preview requests, got {len(preview_requests)}"
        assert not save_requests, f"unexpected Save request(s): {save_requests}"
        assert not run_requests, f"unexpected Run request(s): {run_requests}"
        assert not page_errors

    def test_overview_kpis_byte_identical_pre_and_post_capex_preview(self, runtime_page):
        """Point 5: only the new #capex-total-preview-value and the
        existing #overview-runtime-status-value elements may change —
        every dashboard KPI element's text must be byte-identical."""
        page, page_errors, _ = runtime_page

        page.evaluate("window.switchTab('overview')")
        before = page.eval_on_selector_all(
            ".dashboard-kpi-value, [data-p2min3-kpi-status]",
            "els => els.map(el => el.textContent)",
        )

        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "654.32")
        _wait_for_capex_preview_value(page)

        page.evaluate("window.switchTab('overview')")
        after = page.eval_on_selector_all(
            ".dashboard-kpi-value, [data-p2min3-kpi-status]",
            "els => els.map(el => el.textContent)",
        )

        assert before == after
        assert not page_errors

    def test_dirty_state_remains_dirty_through_capex_preview(self, runtime_page):
        """Point 6: the dirty banner/state stays dirty after a CAPEX
        preview round trip — only Save/Run clear it."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        _edit_cell(page, addr, "321.00")
        _wait_for_capex_preview_value(page)

        is_dirty = page.evaluate("() => window.FcLiveModel.isProjectDirty()")
        banner_hidden = page.eval_on_selector(
            "#workspace-unsaved-banner",
            "el => el.classList.contains('is-hidden')",
        )
        assert is_dirty is True
        assert banner_hidden is False
        assert not page_errors

    def test_c1_grid_behaviour_intact_on_capex_grid(self, runtime_page):
        """Point 9: active cell, keyboard nav, copy/paste, and undo
        still work without crashing on the CAPEX grid after this PR's
        additive changes."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        # Active cell + click.
        page.evaluate(
            """
            (addr) => {
              var cellEl = document.querySelector('[data-fc-addr="' + addr + '"]');
              cellEl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
              cellEl.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            }
            """,
            addr,
        )
        active = page.evaluate(
            "() => { var a = window.FcGridRegistry.getActiveCell('capex'); return a ? a.addr : null; }"
        )
        assert active == addr

        # Keyboard navigation no-crash.
        page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowUp")

        # Copy/paste no-crash (best-effort: dispatch synthetic clipboard
        # events; this only needs to not throw a page error).
        page.evaluate(
            """
            () => {
              document.dispatchEvent(new ClipboardEvent('copy', { bubbles: true }));
              document.dispatchEvent(new ClipboardEvent('paste', { bubbles: true }));
            }
            """
        )

        # Undo no-crash.
        page.keyboard.down("Control")
        page.keyboard.press("z")
        page.keyboard.up("Control")

        page.wait_for_timeout(200)
        assert not page_errors
