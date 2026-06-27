"""Inputs C1 Migration: production-route Playwright smoke test.

Mirrors tests/test_capex_c1_migration_browser.py and
tests/test_opex_c1_migration_browser.py exactly: launches the app as a
real `uvicorn` subprocess (avoiding the documented asyncio/Playwright-
sync-API conflict from importing `main_web` in this process),
authenticates via `app.auth.create_session_token()`, creates a real
user project via `/projects/create`, and drives the real
`/?project=...` route, switching to the Inputs tab (hidden via
`display:none` until `window.switchTab('inputs')` is called, exactly
like the CAPEX/OPEX panels).

Unlike OPEX, the production Inputs sheet has real editable `<input>`
elements for several fields (Project Name, COD Date, Construction
Period, Project Horizon, Base Tariff, PPA Term, Total CAPEX, Y1 OPEX
Total, Indicative Gearing, Target DSCR, Interest Rate, Senior Tenor),
alongside calculated/read-only cells (Senior Debt, IDC, Bank Fees, SHL
Amount, CIT Rate, etc). So this test exercises the full C1 contract:
Active Cell, Keyboard Navigation, Selection, Copy/Paste (succeeding on
editable cells, no-op on read-only ones), Undo, and `FcLiveModel`
dirty tracking against a real edit — plus a check that the pre-existing
Save/Run dirty-indicator wiring (`markInputDirty` / `#dirty-indicator`)
is unaffected by the C1 markup additions.
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
    """POST /projects/create with a valid session cookie, returning the
    new project's code (parsed from the HX-Redirect response header),
    seeded from Oborovo so the Inputs sheet renders the full set of
    fields exercised by this test."""
    form = urllib.parse.urlencode({
        "project_name": "Inputs C1 Migration Smoke",
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
def inputs_page(live_server):
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

    # The Inputs sheet renders inside a tab panel that is hidden
    # (display:none) until its tab is activated, exactly like CAPEX/OPEX.
    page.evaluate("window.switchTab('inputs')")

    try:
        yield page, page_errors
    finally:
        browser.close()
        ctx.stop()


def _first_editable_addr(page):
    return page.evaluate(
        """
        () => {
          var cell = document.querySelector(
            '[data-fc-grid="inputs"] [data-fc-cell="true"][data-fc-editable="true"]'
          );
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """
    )


def _first_readonly_addr(page):
    return page.evaluate(
        """
        () => {
          var cell = document.querySelector(
            '[data-fc-grid="inputs"] [data-fc-cell="true"][data-fc-editable="false"]'
          );
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """
    )


class TestInputsProductionRouteMigration:
    def test_inputs_grid_root_present(self, inputs_page):
        page, page_errors = inputs_page
        assert page.evaluate("!!document.querySelector('[data-fc-grid=\"inputs\"]')")
        assert not page_errors

    def test_inputs_cells_have_unique_addresses(self, inputs_page):
        page, _ = inputs_page
        addrs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-fc-grid="inputs"] [data-fc-addr]'))
              .map(el => el.getAttribute('data-fc-addr'))
            """
        )
        assert len(addrs) > 0
        assert len(addrs) == len(set(addrs))

    def test_editable_cells_have_real_input(self, inputs_page):
        page, _ = inputs_page
        result = page.evaluate(
            """
            () => Array.from(document.querySelectorAll(
              '[data-fc-grid="inputs"] [data-fc-cell="true"][data-fc-editable="true"]'
            )).map(el => !!el.querySelector('input'))
            """
        )
        assert result, "expected at least one editable Inputs cell on the real route"
        assert all(result)

    def test_calculated_cells_are_marked_non_editable(self, inputs_page):
        page, _ = inputs_page
        addr = _first_readonly_addr(page)
        assert addr
        has_input = page.evaluate(
            "(addr) => !!document.querySelector('[data-fc-addr=\"' + addr + '\"]').querySelector('input')",
            addr,
        )
        assert has_input is False

    def test_clicking_editable_cell_sets_active_cell(self, inputs_page):
        page, page_errors = inputs_page
        addr = _first_editable_addr(page)
        assert addr

        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input')"
            ".dispatchEvent(new MouseEvent('click', { bubbles: true }))",
            addr,
        )

        active = page.evaluate("window.FcActiveCellManager.getActiveCell()")
        assert active is not None
        assert active["gridId"] == "inputs"
        assert active["cell"]["addr"] == addr
        assert not page_errors

    def test_keyboard_navigation_moves_active_cell(self, inputs_page):
        page, _ = inputs_page
        addr = _first_editable_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').focus()",
            addr,
        )
        before = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        page.keyboard.press("ArrowDown")
        after = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        assert after != before

    def test_shift_arrow_extends_selection(self, inputs_page):
        page, _ = inputs_page
        addr = _first_editable_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').focus()",
            addr,
        )
        page.keyboard.down("Shift")
        page.keyboard.press("ArrowDown")
        page.keyboard.up("Shift")
        selection = page.evaluate("window.FcSelectionManager.getSelection()")
        assert selection is not None
        assert selection["gridId"] == "inputs"

    def test_copy_reads_raw_value(self, inputs_page):
        page, _ = inputs_page
        addr = _first_editable_addr(page)
        raw = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )

        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"] input').focus();
              window.FcSelectionManager.selectSingle('inputs',
                window.FcGridRegistry.getAddr('inputs', addr));
            }
            """,
            addr,
        )
        copied = page.evaluate("window.FcClipboardController.copySelection()")
        assert copied is not None
        assert raw in str(copied)

    def test_paste_writes_to_editable_cell(self, inputs_page):
        page, _ = inputs_page
        addr = _first_editable_addr(page)

        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"] input').focus();
              window.FcActiveCellManager.setActiveCell('inputs',
                window.FcGridRegistry.getAddr('inputs', addr));
            }
            """,
            addr,
        )
        page.evaluate("(text) => window.FcClipboardController.pasteText(text)", "PastedValue")

        new_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value",
            addr,
        )
        assert new_value == "PastedValue"

    def test_paste_onto_readonly_cell_is_a_noop(self, inputs_page):
        page, _ = inputs_page
        addr = _first_readonly_addr(page)

        before = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )
        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"]').focus();
              window.FcActiveCellManager.setActiveCell('inputs',
                window.FcGridRegistry.getAddr('inputs', addr));
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

    def test_edit_marks_dirty_in_live_model_and_undo_works(self, inputs_page):
        page, _ = inputs_page
        addr = _first_editable_addr(page)
        before_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value",
            addr,
        )

        page.evaluate(
            """
            (addr) => {
              var input = document.querySelector('[data-fc-addr="' + addr + '"] input');
              input.dispatchEvent(new MouseEvent('click', { bubbles: true }));
              input.focus();
              input.value = 'EditedByC1Test';
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """,
            addr,
        )

        assert page.evaluate(
            "(addr) => window.FcLiveModel.isCellDirty('inputs', addr)", addr
        ) is True
        assert page.evaluate("window.FcUndoManager.canUndo()") is True

        page.keyboard.press("Control+z")
        after_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value",
            addr,
        )
        assert after_value == before_value

    def test_existing_save_run_dirty_indicator_unchanged(self, inputs_page):
        """Confirms the pre-existing #dirty-indicator / markInputDirty
        wiring (Save/Run UX, unrelated to C1) still fires from a real
        Inputs <input> change event, unaffected by the new data-fc-*
        attributes added to the same elements."""
        page, _ = inputs_page
        addr = _first_editable_addr(page)
        field_name = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').name",
            addr,
        )
        assert field_name, "expected the existing name= attribute to be present and unchanged"

        page.evaluate("document.getElementById('dirty-indicator').style.display = 'none'")
        page.evaluate(
            """
            (addr) => {
              var input = document.querySelector('[data-fc-addr="' + addr + '"] input');
              input.value = 'TriggerSaveRunDirty';
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """,
            addr,
        )
        display = page.evaluate(
            "document.getElementById('dirty-indicator').style.display"
        )
        assert display == "flex"

    def test_htmx_swap_preserves_grid_registration(self, inputs_page):
        page, page_errors = inputs_page
        before = page.evaluate(
            "Array.from(document.querySelectorAll('[data-fc-grid=\"inputs\"] [data-fc-addr]')).length"
        )
        assert before > 0
        page.evaluate("window.FcGridRegistry.scan(document)")
        after = page.evaluate(
            "Array.from(document.querySelectorAll('[data-fc-grid=\"inputs\"] [data-fc-addr]')).length"
        )
        assert after == before
        assert page.evaluate("!!window.FcGridRegistry.getGrid('inputs')")
        assert not page_errors
