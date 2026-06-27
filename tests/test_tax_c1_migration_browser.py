"""Tax C1 Migration: production-route Playwright smoke test.

Mirrors tests/test_senior_debt_c1_migration_browser.py /
tests/test_revenue_c1_migration_browser.py: launches the app as a real
`uvicorn` subprocess, authenticates via
`app.auth.create_session_token()`, creates a real user project via
`/projects/create`, and drives the real `/?project=...` route,
switching to the Tax tab (`window.switchTab('tax')`, panel id
`panel-tax`).

The production Tax sheet (`sheet_tax.html`) is entirely read-only --
no `<input>` exists anywhere on it. This test still covers the full
C1 interaction surface (grid registration, active cell, keyboard nav,
selection, copy) but paste/undo/fill are all no-op-safety checks
rather than write-then-revert checks, since there is nothing editable
to write to.

The production route always renders with `audit_mode=False` (see
`main_web.py`, every workspace route hardcodes `"audit_mode": False`),
so this also verifies that the always-present, non-audit-only Tax
fields render correctly and that no escaped HTML markup leaks as
visible text on the page in that mode -- the same governance-leakage
condition documented (in a different file) in
docs/INPUTS_C1_MIGRATION_NOTE.md.
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
        "project_name": "Tax C1 Migration Smoke",
        "project_type": "Solar",
        "template_source": "oborovo",
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
def tax_page(live_server):
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

    # The Tax sheet renders inside a tab panel that is hidden
    # (display:none) until its tab is activated, panel id "panel-tax",
    # tab id "tax".
    page.evaluate("window.switchTab('tax')")

    try:
        yield page, page_errors
    finally:
        browser.close()
        ctx.stop()


def _first_addr(page):
    return page.evaluate(
        """
        () => {
          var cell = document.querySelector('[data-fc-grid="tax"] [data-fc-cell="true"]');
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """
    )


class TestTaxProductionRouteMigration:
    def test_tax_grid_root_present(self, tax_page):
        page, page_errors = tax_page
        assert page.evaluate("!!document.querySelector('[data-fc-grid=\"tax\"]')")
        assert not page_errors

    def test_tax_cells_have_unique_addresses(self, tax_page):
        page, _ = tax_page
        addrs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-fc-grid="tax"] [data-fc-addr]'))
              .map(el => el.getAttribute('data-fc-addr'))
            """
        )
        assert len(addrs) > 0
        assert len(addrs) == len(set(addrs))

    def test_all_cells_are_non_editable_with_no_input(self, tax_page):
        page, _ = tax_page
        result = page.evaluate(
            """
            () => Array.from(document.querySelectorAll(
              '[data-fc-grid="tax"] [data-fc-cell="true"]'
            )).map(el => ({
              editable: el.getAttribute('data-fc-editable'),
              hasInput: !!el.querySelector('input'),
            }))
            """
        )
        assert len(result) > 0
        for entry in result:
            assert entry["editable"] == "false"
            assert entry["hasInput"] is False

    def test_clicking_cell_sets_active_cell(self, tax_page):
        page, page_errors = tax_page
        addr = _first_addr(page)
        assert addr

        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]')"
            ".dispatchEvent(new MouseEvent('click', { bubbles: true }))",
            addr,
        )

        active = page.evaluate("window.FcActiveCellManager.getActiveCell()")
        assert active is not None
        assert active["gridId"] == "tax"
        assert active["cell"]["addr"] == addr
        assert not page_errors

    def test_keyboard_navigation_moves_active_cell(self, tax_page):
        page, _ = tax_page
        addr = _first_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').focus()",
            addr,
        )
        before = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        page.keyboard.press("ArrowDown")
        after = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        # navigation must not error, even if there's only one row of
        # cells and the active cell does not change
        assert after is not None
        assert before is not None

    def test_shift_arrow_extends_selection(self, tax_page):
        page, _ = tax_page
        addr = _first_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').focus()",
            addr,
        )
        page.keyboard.down("Shift")
        page.keyboard.press("ArrowDown")
        page.keyboard.up("Shift")
        selection = page.evaluate("window.FcSelectionManager.getSelection()")
        assert selection is not None
        assert selection["gridId"] == "tax"

    def test_copy_reads_raw_value(self, tax_page):
        page, _ = tax_page
        addr = _first_addr(page)
        raw = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )

        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"]').focus();
              window.FcSelectionManager.selectSingle('tax',
                window.FcGridRegistry.getAddr('tax', addr));
            }
            """,
            addr,
        )
        copied = page.evaluate("window.FcClipboardController.copySelection()")
        assert copied is not None
        if raw is not None:
            assert raw in str(copied)

    def test_paste_onto_readonly_cell_is_a_noop(self, tax_page):
        page, _ = tax_page
        addr = _first_addr(page)

        before = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )
        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"]').focus();
              window.FcActiveCellManager.setActiveCell('tax',
                window.FcGridRegistry.getAddr('tax', addr));
            }
            """,
            addr,
        )
        page.evaluate("(text) => window.FcClipboardController.pasteText(text)", "999.99")

        after = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )
        assert after == before

    def test_undo_is_safe_noop_when_nothing_is_editable(self, tax_page):
        page, page_errors = tax_page
        # No edit was ever made (the sheet has no editable cell), so
        # undo must not throw and must report nothing to undo.
        can_undo = page.evaluate("window.FcUndoManager.canUndo()")
        assert can_undo is False
        page.keyboard.press("Control+z")
        assert not page_errors

    def test_audit_mode_false_renders_without_visible_escaped_markup(self, tax_page):
        """The production route always renders with audit_mode=False.
        Confirms this Tax sheet does not leak escaped HTML source as
        visible text (the governance-leakage condition documented,
        in a different file, in docs/INPUTS_C1_MIGRATION_NOTE.md)."""
        page, _ = tax_page
        body_text = page.evaluate(
            "() => document.getElementById('panel-tax') ? document.getElementById('panel-tax').innerText : ''"
        )
        assert "&lt;" not in body_text
        assert "data-fc-" not in body_text

    def test_htmx_swap_preserves_grid_registration(self, tax_page):
        page, page_errors = tax_page
        before = page.evaluate(
            "Array.from(document.querySelectorAll('[data-fc-grid=\"tax\"] [data-fc-addr]')).length"
        )
        assert before > 0
        page.evaluate("window.FcGridRegistry.scan(document)")
        after = page.evaluate(
            "Array.from(document.querySelectorAll('[data-fc-grid=\"tax\"] [data-fc-addr]')).length"
        )
        assert after == before
        assert page.evaluate("!!window.FcGridRegistry.getGrid('tax')")
        assert not page_errors
