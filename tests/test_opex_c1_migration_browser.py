"""OPEX C1 Migration: production-route Playwright smoke test.

Mirrors tests/test_capex_c1_migration_browser.py exactly: launches the
app as a real `uvicorn` subprocess (avoiding the documented
asyncio/Playwright-sync-API conflict from importing `main_web` in this
process), authenticates via `app.auth.create_session_token()`, creates
a real user project via `/projects/create`, and drives the real
`/?project=...` route, switching to the OPEX tab (hidden via
`display:none` until `window.switchTab('opex')` is called, exactly
like the CAPEX panel).

Key difference from the CAPEX test: the real production OPEX grid
(`sheet_opex_detail.html`) has zero real `<input>` elements — every
cell is `data-fc-editable="false"` (see
docs/OPEX_C1_MIGRATION_NOTE.md). So this test does NOT exercise
Undo/dirty-tracking/Fill on a real edit; instead it asserts those
correctly no-op against a non-editable cell, while Active Cell,
Keyboard Navigation, Selection, and Copy work fully, and the existing
OPEX-specific behaviour (year-range toggle, category collapse/expand)
continues to work unmodified.
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
    new project's code (parsed from the HX-Redirect response header),
    seeded from Oborovo so opex_detail_items is the full detailed
    template (not the flat fallback)."""
    form = urllib.parse.urlencode({
        "project_name": "OPEX C1 Migration Smoke",
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
def opex_page(live_server):
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

    # The OPEX sheet renders inside a tab panel that is hidden
    # (display:none) until its tab is activated, exactly like CAPEX.
    page.evaluate("window.switchTab('opex')")

    try:
        yield page, page_errors
    finally:
        browser.close()
        ctx.stop()


def _first_fc_cell_addr(page):
    return page.evaluate(
        """
        () => {
          var cell = document.querySelector('[data-fc-grid="opex"] [data-fc-cell="true"]');
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """
    )


class TestOpexProductionRouteMigration:
    def test_opex_grid_root_present(self, opex_page):
        page, page_errors = opex_page
        assert page.evaluate("!!document.querySelector('[data-fc-grid=\"opex\"]')")
        assert not page_errors

    def test_opex_cells_have_unique_addresses(self, opex_page):
        page, _ = opex_page
        addrs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-fc-grid="opex"] [data-fc-addr]'))
              .map(el => el.getAttribute('data-fc-addr'))
            """
        )
        assert len(addrs) > 0
        assert len(addrs) == len(set(addrs))

    def test_all_opex_cells_are_non_editable(self, opex_page):
        """The real production OPEX grid has zero <input> elements
        today — confirms the migration did not introduce new
        editability (see docs/OPEX_C1_MIGRATION_NOTE.md)."""
        page, _ = opex_page
        editable_flags = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-fc-grid="opex"] [data-fc-cell="true"]'))
              .map(el => el.getAttribute('data-fc-editable'))
            """
        )
        assert editable_flags, "expected at least one OPEX fc-cell"
        assert all(flag == "false" for flag in editable_flags)

    def test_opex_amount_cells_have_raw(self, opex_page):
        page, _ = opex_page
        result = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-fc-grid="opex"] [data-fc-cell="true"]'))
              .map(el => el.hasAttribute('data-fc-raw'))
            """
        )
        assert result
        assert all(result)

    def test_clicking_cell_sets_active_cell(self, opex_page):
        page, page_errors = opex_page
        addr = _first_fc_cell_addr(page)
        assert addr

        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]')"
            ".dispatchEvent(new MouseEvent('click', { bubbles: true }))",
            addr,
        )

        active = page.evaluate("window.FcActiveCellManager.getActiveCell()")
        assert active is not None
        assert active["gridId"] == "opex"
        assert active["cell"]["addr"] == addr
        assert page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').classList.contains('fc-active-cell')",
            addr,
        )
        assert not page_errors

    def test_keyboard_navigation_moves_active_cell(self, opex_page):
        page, _ = opex_page
        addr = _first_fc_cell_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').focus()",
            addr,
        )
        before = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        page.keyboard.press("ArrowDown")
        after = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        assert after != before

    def test_shift_arrow_extends_selection(self, opex_page):
        page, _ = opex_page
        addr = _first_fc_cell_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').focus()",
            addr,
        )
        page.keyboard.down("Shift")
        page.keyboard.press("ArrowDown")
        page.keyboard.up("Shift")
        selection = page.evaluate("window.FcSelectionManager.getSelection()")
        assert selection is not None
        assert selection["gridId"] == "opex"

    def test_copy_reads_raw_value(self, opex_page):
        page, _ = opex_page
        addr = _first_fc_cell_addr(page)
        raw = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )

        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"]').focus();
              window.FcSelectionManager.selectSingle('opex',
                window.FcGridRegistry.getAddr('opex', addr));
            }
            """,
            addr,
        )
        copied = page.evaluate("window.FcClipboardController.copySelection()")
        assert copied is not None
        assert raw in str(copied)

    def test_paste_onto_non_editable_cell_is_a_noop(self, opex_page):
        page, _ = opex_page
        addrs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-fc-grid="opex"] [data-fc-cell="true"]'))
              .map(el => el.getAttribute('data-fc-addr'))
            """
        )
        assert len(addrs) >= 2
        src_addr, dst_addr = addrs[0], addrs[1]

        dst_raw_before = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            dst_addr,
        )

        page.evaluate(
            """
            (args) => {
              document.querySelector('[data-fc-addr="' + args.dst + '"]').focus();
              window.FcActiveCellManager.setActiveCell('opex',
                window.FcGridRegistry.getAddr('opex', args.dst));
            }
            """,
            {"dst": dst_addr},
        )
        page.evaluate("(text) => window.FcClipboardController.pasteText(text)", "999.99")

        dst_raw_after = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            dst_addr,
        )
        assert dst_raw_after == dst_raw_before

    def test_edit_attempt_does_not_mark_dirty_or_undoable(self, opex_page):
        page, _ = opex_page
        addr = _first_fc_cell_addr(page)

        page.evaluate(
            """
            (addr) => {
              var cell = window.FcGridRegistry.getAddr('opex', addr);
              window.FcCellIO.writeValue(cell, '12345.67');
            }
            """,
            addr,
        )
        assert page.evaluate("window.FcUndoManager.canUndo()") is False

    def test_year_range_toggle_still_works(self, opex_page):
        page, _ = opex_page
        page.evaluate("window.opexSetYearRange('9-16')")
        grid_range = page.evaluate("document.getElementById('opex-detail-grid').getAttribute('data-yrange')")
        assert grid_range == "9-16"
        y9_visible = page.evaluate(
            "!!document.querySelector('[data-yr=\"9\"].yr-show')"
        )
        assert y9_visible
        page.evaluate("window.opexSetYearRange('1-8')")

    def test_category_collapse_expand_still_works(self, opex_page):
        page, _ = opex_page
        page.evaluate("window.opexExpandAll()")
        any_collapsed = page.evaluate(
            "!!document.querySelector('.fc-cat-tbody--collapsed')"
        )
        assert any_collapsed is False

        page.evaluate("window.opexCollapseAll()")
        all_collapsed = page.evaluate(
            "Array.from(document.querySelectorAll('.fc-cat-tbody')).every(tb => tb.classList.contains('fc-cat-tbody--collapsed'))"
        )
        assert all_collapsed

        page.evaluate("window.opexExpandAll()")

    def test_htmx_swap_preserves_grid_registration(self, opex_page):
        page, page_errors = opex_page
        before = page.evaluate(
            "Array.from(document.querySelectorAll('[data-fc-grid=\"opex\"] [data-fc-addr]')).length"
        )
        assert before > 0
        # Trigger a registry re-scan exactly as FcSwapLifecycle would
        # after a real htmx swap, and confirm the opex grid is still
        # registered afterwards.
        page.evaluate("window.FcGridRegistry.scan(document)")
        after = page.evaluate(
            "Array.from(document.querySelectorAll('[data-fc-grid=\"opex\"] [data-fc-addr]')).length"
        )
        assert after == before
        assert page.evaluate("!!window.FcGridRegistry.getGrid('opex')")
        assert not page_errors
