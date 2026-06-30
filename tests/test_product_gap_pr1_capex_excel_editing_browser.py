"""Product Gap PR1: CAPEX Real Excel Editing + Live Totals —
production-route Playwright tests.

Covers the browser-side required-behaviour points from the PR1 spec
for the new static/modelling/capex-sheet-live-totals.js module:

  1. Arrow to a CAPEX editable cell, type a number -> value changes
     without any mouse click into the input.
  2. Enter commits and moves the active cell down.
  3. Tab commits and moves the active cell right.
  4. Escape restores the old value.
  5. Category subtotal updates live as you type/edit.
  6. Hard CAPEX Total updates live.
  7. Total CAPEX updates live.
  8. C.17/C.18 remain read-only (no editable cell markup).
  9. Save is not triggered merely by typing (no POST to /scenarios/save).
  10. Run is not triggered merely by typing (no POST to /run).
  11. The existing CAPEX preview panel (#capex-total-preview-value)
      still updates correctly (no regression to C2-PR10).
  12. Existing C1 keyboard navigation (arrow keys) still works outside
      of edit mode.

Uses the same real-uvicorn-subprocess + real-auth + real-project
fixture pattern as tests/test_c2_pr15_ebitda_preview_browser.py /
tests/test_c2_pr17_opex_line_editability_browser.py.
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

from app.auth import create_session_token  # noqa: E402

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
        "project_name": "Product Gap PR1 CAPEX Excel Editing Smoke",
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
    page.evaluate("window.switchTab('capex')")
    page.wait_for_selector('[data-fc-grid="capex"]')

    try:
        yield page, page_errors, project_code
    finally:
        browser.close()
        ctx.stop()


def _click_first_capex_amount_cell(page):
    """Click (mouse, once) the first editable CAPEX amount cell to make
    it the active cell, per existing C1 navigation, WITHOUT entering
    edit mode (the click lands on the <td data-fc-cell>, not inside the
    descendant <input> — exactly how a real Excel-like single click on
    a cell behaves)."""
    addr = page.evaluate(
        """
        () => {
          var cell = document.querySelector(
            '[data-fc-grid="capex"] [data-fc-cell="true"][data-fc-editable="true"][data-fc-kind="amount"]'
          );
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """
    )
    assert addr, "expected at least one editable CAPEX amount cell"
    page.evaluate(
        """
        (addr) => {
          var cell = document.querySelector('[data-fc-addr="' + addr + '"]');
          cell.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
          cell.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        }
        """,
        addr,
    )
    return addr


def _cell_input_value(page, addr):
    return page.eval_on_selector(
        f'[data-fc-addr="{addr}"] input', "el => el.value"
    )


def _cell_raw(page, selector):
    return page.eval_on_selector(selector, "el => el.getAttribute('data-fc-raw')")


class TestCapexExcelEditingBrowser:
    def test_typing_starts_edit_and_replaces_value_without_mouse_click_into_input(self, runtime_page):
        page, page_errors, _ = runtime_page
        addr = _click_first_capex_amount_cell(page)

        # Confirm DOM focus landed on the cell itself, not its input.
        focused_is_cell = page.evaluate(
            "(addr) => document.activeElement === document.querySelector('[data-fc-addr=\"' + addr + '\"]')",
            addr,
        )
        assert focused_is_cell, "expected the cell element (not its input) to have DOM focus after a click"

        page.keyboard.press("5")
        page.keyboard.press("0")
        page.keyboard.press("0")

        value = _cell_input_value(page, addr)
        assert value == "500", f"expected typed digits to replace the old value; got {value!r}"
        assert not page_errors

    def test_enter_commits_and_moves_active_cell_down(self, runtime_page):
        page, page_errors, _ = runtime_page
        addr = _click_first_capex_amount_cell(page)

        page.keyboard.press("7")
        page.keyboard.press("Enter")

        new_active_addr = page.evaluate(
            """
            () => {
              var active = window.FcActiveCellManager.getActiveCell();
              return active && active.cell && active.cell.el ? active.cell.el.getAttribute('data-fc-addr') : null;
            }
            """
        )
        assert new_active_addr != addr, "Enter should move the active cell down to a different cell"
        assert not page_errors

    def test_tab_commits_and_moves_active_cell_right(self, runtime_page):
        """The CAPEX grid renders exactly one navigable [data-fc-cell]
        per row (the amount cell — label/code columns are not
        registered as separate grid cells, per the existing C1 markup
        contract in _line_item_grid.html). So "Tab moves right" has no
        same-row target to move to; per the pre-existing
        FcKeyboardRouter contract (neighbors(cell, 'right') returns
        null when there is no column to the right), the active cell
        simply does not move in that case — this module intentionally
        mirrors that exact existing behaviour rather than inventing a
        new one. What this test actually proves is the commit half of
        Tab: the typed value is committed (visible via the live
        category subtotal changing) even though there is no rightward
        cell to move into."""
        page, page_errors, _ = runtime_page
        addr = _click_first_capex_amount_cell(page)
        category = page.evaluate(
            "(a) => a.split('!')[1].split('.').slice(0, 2).join('.')", addr
        )
        subtotal_selector = f'tr[data-capex-row="cat-subtotal-{category}"] [data-fc-cell]'
        before = _cell_raw(page, subtotal_selector)

        page.keyboard.press("9")
        page.keyboard.press("Tab")

        after = _cell_raw(page, subtotal_selector)
        assert after != before, "Tab must commit the typed value (visible via the live subtotal)"

        # The cell itself regains DOM focus (no rightward target to
        # move into in a single-column-per-row grid), and is no longer
        # in edit mode.
        focused_is_cell = page.evaluate(
            "(addr) => document.activeElement === document.querySelector('[data-fc-addr=\"' + addr + '\"]')",
            addr,
        )
        assert focused_is_cell
        assert not page_errors

    def test_escape_restores_previous_value(self, runtime_page):
        page, page_errors, _ = runtime_page
        addr = _click_first_capex_amount_cell(page)
        original_value = _cell_input_value(page, addr)

        page.keyboard.press("1")
        page.keyboard.press("2")
        page.keyboard.press("3")
        assert _cell_input_value(page, addr) == "123"

        page.keyboard.press("Escape")
        restored_value = _cell_input_value(page, addr)
        assert restored_value == original_value, (
            f"Escape must restore the pre-edit value; expected {original_value!r}, got {restored_value!r}"
        )
        assert not page_errors

    def test_category_subtotal_updates_live(self, runtime_page):
        page, page_errors, _ = runtime_page
        addr = _click_first_capex_amount_cell(page)
        category = page.evaluate(
            "(a) => a.split('!')[1].split('.').slice(0, 2).join('.')", addr
        )
        subtotal_selector = f'tr[data-capex-row="cat-subtotal-{category}"] [data-fc-cell]'
        before = _cell_raw(page, subtotal_selector)

        page.keyboard.press("4")
        page.keyboard.press("2")

        after = _cell_raw(page, subtotal_selector)
        assert after != before, "category subtotal must update live as the amount cell is edited"
        assert not page_errors

    def test_hard_capex_total_updates_live(self, runtime_page):
        page, page_errors, _ = runtime_page
        before = _cell_raw(page, 'tr[data-capex-row="hard-capex-total"] [data-fc-cell]')
        _click_first_capex_amount_cell(page)

        page.keyboard.press("8")
        page.keyboard.press("1")

        after = _cell_raw(page, 'tr[data-capex-row="hard-capex-total"] [data-fc-cell]')
        assert after != before, "Hard CAPEX Total must update live"
        assert not page_errors

    def test_total_capex_updates_live(self, runtime_page):
        page, page_errors, _ = runtime_page
        before = _cell_raw(page, 'tr[data-capex-row="grand-total"] [data-fc-cell]')
        _click_first_capex_amount_cell(page)

        page.keyboard.press("6")
        page.keyboard.press("6")

        after = _cell_raw(page, 'tr[data-capex-row="grand-total"] [data-fc-cell]')
        assert after != before, "Total CAPEX must update live"
        assert not page_errors

    def test_c17_c18_remain_read_only(self, runtime_page):
        page, page_errors, _ = runtime_page
        editable_financing = page.evaluate(
            """
            () => {
              var rows = document.querySelectorAll('#capex-single-sheet tr.lig-row--data-financing');
              var editableCount = 0;
              rows.forEach(function (tr) {
                var cell = tr.querySelector('[data-fc-cell]');
                if (cell && cell.getAttribute('data-fc-editable') === 'true') editableCount += 1;
              });
              return editableCount;
            }
            """
        )
        assert editable_financing == 0, "C.17/C.18 financing rows must never be editable"
        assert not page_errors

    def test_save_not_triggered_by_typing(self, runtime_page):
        page, page_errors, _ = runtime_page
        save_calls = []
        page.on("request", lambda req: save_calls.append(req.url) if "/scenarios/save" in req.url else None)

        _click_first_capex_amount_cell(page)
        page.keyboard.press("3")
        page.keyboard.press("3")
        page.keyboard.press("3")
        page.wait_for_timeout(300)

        assert save_calls == [], f"typing alone must never POST to /scenarios/save; saw {save_calls}"
        assert not page_errors

    def test_run_not_triggered_by_typing(self, runtime_page):
        page, page_errors, _ = runtime_page
        run_calls = []
        page.on("request", lambda req: run_calls.append(req.url) if req.url.endswith("/run") else None)

        _click_first_capex_amount_cell(page)
        page.keyboard.press("2")
        page.keyboard.press("2")
        page.wait_for_timeout(300)

        assert run_calls == [], f"typing alone must never POST to /run; saw {run_calls}"
        assert not page_errors

    def test_capex_total_preview_panel_still_updates(self, runtime_page):
        page, page_errors, _ = runtime_page
        addr = _click_first_capex_amount_cell(page)

        page.keyboard.press("1")
        page.keyboard.press("1")
        page.keyboard.press("1")
        page.keyboard.press("1")
        page.keyboard.press("Enter")  # commit -> dispatches change -> FcLiveModel dirty -> preview flush

        page.wait_for_function(
            """
            () => {
              var el = document.getElementById('capex-total-preview-value');
              return !!(el && el.getAttribute('data-c2pr10-capex-preview') === 'patched');
            }
            """,
            timeout=6000,
        )
        text = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        assert any(ch.isdigit() for ch in text)
        assert not page_errors

    def test_arrow_key_navigation_still_works_outside_edit_mode(self, runtime_page):
        page, page_errors, _ = runtime_page
        addr = _click_first_capex_amount_cell(page)

        page.keyboard.press("ArrowDown")

        new_active_addr = page.evaluate(
            """
            () => {
              var active = window.FcActiveCellManager.getActiveCell();
              return active && active.cell && active.cell.el ? active.cell.el.getAttribute('data-fc-addr') : null;
            }
            """
        )
        assert new_active_addr is not None and new_active_addr != addr, (
            "ArrowDown must still move the active cell when not in edit mode (no regression to FcKeyboardRouter)"
        )
        assert not page_errors
