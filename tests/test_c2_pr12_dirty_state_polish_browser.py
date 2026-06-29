"""C2-PR12: Dirty State Polish — production-route Playwright tests.

Covers the browser-side required-behaviour points from the C2-PR12 task
spec:

  5. Save immediately clears the dirty strip text (not just the
     banner) with no delay/flicker.
  6. No stale "Unsaved edits" text remains visible after a successful
     Save (assert within a tight time window, not just eventually).
  7. The CAPEX/runtime preview value/state survives a Save (is not
     blanked or reset to Idle by the Save response handling).
  8. Save still triggers zero runtime-recalculation/preview requests
     of its own (regression check).

Mirrors tests/test_c2_pr10_capex_total_preview_browser.py's production-
route pattern: real uvicorn subprocess, real auth, real project
creation.
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
        "project_name": "C2 PR12 Dirty State Polish Smoke",
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


def _click_save_and_wait(page):
    page.click("#btn-save")
    page.wait_for_function(
        """
        () => {
          var banner = document.getElementById('workspace-unsaved-banner');
          return !!(banner && banner.classList.contains('is-hidden'));
        }
        """,
        timeout=6000,
    )


class TestDirtyStatePolishBrowser:
    def test_save_immediately_clears_strip_text(self, runtime_page):
        """Point 5: Save immediately clears the dirty strip text, not
        just the banner."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "71111.11")

        page.wait_for_function(
            "() => window.FcLiveModel.isProjectDirty() === true", timeout=4000
        )
        strip_text_dirty = page.eval_on_selector(
            "#workspace-strip-dirty", "el => el.textContent.trim()"
        )
        assert "unsaved" in strip_text_dirty.lower()

        _click_save_and_wait(page)

        strip_text_after_save = page.eval_on_selector(
            "#workspace-strip-dirty", "el => el.textContent.trim()"
        )
        assert "unsaved" not in strip_text_after_save.lower(), (
            f"strip text still shows an unsaved-state label immediately after "
            f"Save: {strip_text_after_save!r}"
        )
        assert not page_errors

    def test_no_stale_unsaved_text_within_tight_window(self, runtime_page):
        """Point 6: no stale "Unsaved edits" text remains visible after
        a successful Save, checked within a tight time window (not just
        eventually, after some other event refreshes it)."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "72222.22")
        page.wait_for_function(
            "() => window.FcLiveModel.isProjectDirty() === true", timeout=4000
        )

        page.click("#btn-save")
        # Tight window: 300ms, well under the ~"few seconds" the bug
        # report described, and well under anything a subsequent Run
        # could plausibly contribute.
        page.wait_for_timeout(300)

        strip_text = page.eval_on_selector(
            "#workspace-strip-dirty", "el => el.textContent.trim()"
        )
        banner_hidden = page.eval_on_selector(
            "#workspace-unsaved-banner", "el => el.classList.contains('is-hidden')"
        )
        assert "unsaved" not in strip_text.lower(), (
            f"stale unsaved-state strip text within 300ms of Save: {strip_text!r}"
        )
        assert banner_hidden is True
        assert not page_errors

    def test_capex_preview_survives_save(self, runtime_page):
        """Point 7: the CAPEX/runtime preview value/state is not
        blanked or reset to Idle by Save's response handling."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "73333.33")

        page.wait_for_function(
            """
            () => {
              var el = document.getElementById('capex-total-preview-value');
              return !!(el && el.getAttribute('data-c2pr10-capex-preview') === 'patched');
            }
            """,
            timeout=6000,
        )
        value_before_save = page.eval_on_selector(
            "#capex-total-preview-value", "el => el.textContent"
        )
        state_before_save = page.eval_on_selector(
            "#capex-total-preview-value", "el => el.getAttribute('data-c2pr11-runtime-state')"
        )
        assert any(ch.isdigit() for ch in value_before_save)
        assert state_before_save == "ready"

        _click_save_and_wait(page)
        page.wait_for_timeout(300)

        value_after_save = page.eval_on_selector(
            "#capex-total-preview-value", "el => el.textContent"
        )
        state_after_save = page.eval_on_selector(
            "#capex-total-preview-value", "el => el.getAttribute('data-c2pr11-runtime-state')"
        )
        assert value_after_save == value_before_save, (
            "Save must never blank/change the previously-rendered CAPEX preview value"
        )
        assert state_after_save != "idle", (
            "Save must never reset the runtime preview state machine back to Idle"
        )
        assert not page_errors

    def test_save_fires_zero_preview_requests(self, runtime_page):
        """Point 8: Save itself never fires a /model/preview call
        (regression check)."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "74444.44")
        page.wait_for_timeout(1000)  # let the edit's own preview request settle

        preview_requests = []
        page.on("request", lambda req: preview_requests.append(req.url) if "/model/preview" in req.url else None)

        _click_save_and_wait(page)
        page.wait_for_timeout(500)

        assert preview_requests == [], (
            f"Save must never itself trigger a /model/preview request; got {preview_requests}"
        )
        assert not page_errors
