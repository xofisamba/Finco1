"""CAPEX C1 Migration: production-route Playwright smoke test.

Unlike every prior C1/C2 browser test (which load a dedicated
standalone fixture via `file://` to avoid importing `main_web` inside
an already-active asyncio/anyio event loop — see
tests/test_c1_pr7_clipboard_controller_browser.py and
tests/test_c2_pr1_live_model_browser.py for that documented
constraint), this test exercises the REAL production CAPEX route.

It resolves the asyncio/Playwright-sync-API conflict by never
importing `main_web` in this process at all: it launches the app as a
real `uvicorn` *subprocess* (a separate process, so there is no shared
event loop) and drives it over real HTTP with Playwright, exactly like
tests/test_phase18_live_browser_user_project_smoke.py already does.

Auth: `app.auth.create_session_token()` is imported directly (it does
not import `main_web` and does not start any event loop), used to mint
a valid `finco_session` cookie, which is set both on a plain urllib
request (to create a real user project so the editable C.01-C.18 CAPEX
grid renders) and on the Playwright browser context (so the page
itself is authenticated).
"""
from __future__ import annotations

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
    """POST /projects/create with a valid session cookie, returning the
    new project's code (parsed from the HX-Redirect response header,
    the same contract main_web.py documents for this route)."""
    form = urllib.parse.urlencode({
        "project_name": "CAPEX C1 Migration Smoke",
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
    playwright = pytest.importorskip(
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


@pytest.fixture(scope="module")
def capex_page(live_server):
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

    # The CAPEX sheet renders inside a tab panel that is hidden
    # (display:none) until its tab is activated; switch to it so the
    # grid's cells are actually visible/focusable, matching how a real
    # user reaches this sheet.
    page.evaluate("window.switchTab('capex')")

    try:
        yield page, page_errors
    finally:
        browser.close()
        ctx.stop()


def _first_editable_amount_addr(page):
    return page.evaluate(
        """
        () => {
          var cell = document.querySelector(
            '[data-fc-grid="capex"] [data-fc-cell="true"][data-fc-editable="true"][data-fc-kind="amount"]'
          );
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """
    )


class TestCapexProductionRouteMigration:
    def test_capex_grid_root_present(self, capex_page):
        page, page_errors = capex_page
        assert page.evaluate("!!document.querySelector('[data-fc-grid=\"capex\"]')")
        assert not page_errors

    def test_capex_cells_have_unique_addresses(self, capex_page):
        page, _ = capex_page
        addrs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-fc-grid="capex"] [data-fc-addr]'))
              .map(el => el.getAttribute('data-fc-addr'))
            """
        )
        assert len(addrs) > 0
        assert len(addrs) == len(set(addrs))

    def test_editable_amount_cells_have_real_input_and_raw(self, capex_page):
        page, _ = capex_page
        result = page.evaluate(
            """
            () => Array.from(document.querySelectorAll(
              '[data-fc-grid="capex"] [data-fc-cell="true"][data-fc-editable="true"][data-fc-kind="amount"]'
            )).map(el => ({
              hasInput: !!el.querySelector('input'),
              hasRaw: el.hasAttribute('data-fc-raw'),
            }))
            """
        )
        assert result, "expected at least one editable CAPEX amount cell on the real route"
        for entry in result:
            assert entry["hasInput"] is True
            assert entry["hasRaw"] is True

    def test_clicking_editable_cell_sets_active_cell(self, capex_page):
        page, page_errors = capex_page
        addr = _first_editable_amount_addr(page)
        assert addr

        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input')"
            ".dispatchEvent(new MouseEvent('click', { bubbles: true }))",
            addr,
        )

        active = page.evaluate("window.FcActiveCellManager.getActiveCell()")
        assert active is not None
        assert active["gridId"] == "capex"
        assert active["cell"]["addr"] == addr
        assert page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').classList.contains('fc-active-cell')",
            addr,
        )
        assert not page_errors

    def test_keyboard_navigation_moves_active_cell(self, capex_page):
        page, _ = capex_page
        addr = _first_editable_amount_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').focus()",
            addr,
        )
        before = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        page.keyboard.press("ArrowDown")
        after = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        assert after != before

    def test_edit_marks_dirty_and_undoable(self, capex_page):
        page, _ = capex_page
        addr = _first_editable_amount_addr(page)

        page.evaluate(
            """
            (addr) => {
              var input = document.querySelector('[data-fc-addr="' + addr + '"] input');
              input.dispatchEvent(new MouseEvent('click', { bubbles: true }));
              input.focus();
              input.value = '999.99';
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """,
            addr,
        )

        assert page.evaluate(
            "(addr) => window.FcLiveModel.isCellDirty('capex', addr)", addr
        ) is True
        assert page.evaluate("window.FcUndoManager.canUndo()") is True

    def test_ctrl_z_reverts_the_edit(self, capex_page):
        page, _ = capex_page
        addr = _first_editable_amount_addr(page)
        before_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value", addr
        )

        page.evaluate(
            """
            (addr) => {
              var input = document.querySelector('[data-fc-addr="' + addr + '"] input');
              input.dispatchEvent(new MouseEvent('click', { bubbles: true }));
              input.focus();
              input.value = '12345.67';
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """,
            addr,
        )
        page.keyboard.press("Control+z")

        after_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value", addr
        )
        assert after_value == before_value

    def test_copy_paste_round_trips_raw_value(self, capex_page):
        page, _ = capex_page
        addrs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll(
              '[data-fc-grid="capex"] [data-fc-cell="true"][data-fc-editable="true"][data-fc-kind="amount"]'
            )).map(el => el.getAttribute('data-fc-addr'))
            """
        )
        assert len(addrs) >= 2, "need at least two editable CAPEX amount cells to test copy/paste"
        src_addr, dst_addr = addrs[0], addrs[1]

        src_raw = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            src_addr,
        )

        page.evaluate(
            """
            (args) => {
              document.querySelector('[data-fc-addr="' + args.src + '"] input').focus();
              window.FcSelectionManager.selectSingle('capex',
                window.FcGridRegistry.getAddr('capex', args.src));
            }
            """,
            {"src": src_addr},
        )
        copied = page.evaluate("window.FcClipboardController.copySelection()")
        assert copied

        page.evaluate(
            """
            (args) => {
              document.querySelector('[data-fc-addr="' + args.dst + '"] input').focus();
              window.FcActiveCellManager.setActiveCell('capex',
                window.FcGridRegistry.getAddr('capex', args.dst));
            }
            """,
            {"dst": dst_addr},
        )
        page.evaluate("(text) => window.FcClipboardController.pasteText(text)", copied)

        dst_raw = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            dst_addr,
        )
        assert dst_raw == src_raw
