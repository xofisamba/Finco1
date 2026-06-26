"""C1-PR5: Spreadsheet Interaction Layer — Keyboard Navigation
Foundation, JS-execution tests.

Covers, per the C1-PR5 task spec (keyboard navigation foundation
only):
  1. Arrow keys move the active cell in the expected directions.
  2. Enter / Shift+Enter move down/up.
  3. Tab / Shift+Tab move right/left, and Tab does not escape the
     browser's normal tab order while focus is on a grid cell.
  4. Home / End move to row boundaries.
  5. Ctrl+Arrow moves to the edge of the current row/column.
  6. Keyboard navigation no-ops when focus is outside a grid cell.
  7. Keyboard navigation does not hijack a normal text input.
  8. (PR1-PR4 regressions covered by their own existing test files.)
  9. No clipboard/selection/undo behaviour exists (asserted via the
     static checks in test_c1_pr5_keyboard_router.py; this file does
     not exercise any since none exists to exercise).

These tests run against a standalone static fixture
(tests/fixtures/c1_keyboard_router_fixture.html) via Playwright, not
the real Finco1 app, and are skipped if Playwright/Chromium are
unavailable — mirroring the pattern in
tests/test_c1_pr4_focus_manager_browser.py.

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented there.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_keyboard_router_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR5 JS tests",
    )
    sync_playwright = playwright.sync_playwright
    ctx = sync_playwright().start()
    try:
        browser = ctx.chromium.launch()
    except Exception:  # pragma: no cover - environment-dependent
        try:
            browser = ctx.chromium.launch(executable_path=_FALLBACK_CHROMIUM_PATH)
        except Exception as exc:  # pragma: no cover - environment-dependent
            ctx.stop()
            pytest.skip(f"OPTIONAL_BROWSER_DEPENDENCY_MISSING_BROWSER_BINARIES: {exc}")
    return ctx, browser


@pytest.fixture
def fixture_page():
    ctx, browser = _launch_browser()
    page_errors = []
    page = browser.new_page()
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.goto("file://" + FIXTURE_PATH)
    try:
        yield page, page_errors
    finally:
        browser.close()
        ctx.stop()


def _click_addr(page, addr):
    page.evaluate(
        """
        (addr) => {
          var el = document.querySelector('[data-fc-addr="' + addr + '"]');
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        }
        """,
        addr,
    )


def _focused_addr(page):
    return page.evaluate(
        """
        (() => {
          var el = document.activeElement;
          return el && el.getAttribute ? el.getAttribute('data-fc-addr') : null;
        })()
        """
    )


def _press(page, key, **modifiers):
    parts = []
    if modifiers.get("ctrl"):
        parts.append("Control")
    if modifiers.get("shift"):
        parts.append("Shift")
    parts.append(key)
    page.keyboard.press("+".join(parts))


class TestKeyboardRouterJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcKeyboardRouter") == "object"
        assert not page_errors

    def test_arrow_keys_move_active_cell_in_expected_directions(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r2.c2")

        _press(page, "ArrowRight")
        assert _focused_addr(page) == "fixture.r2.c3"

        _press(page, "ArrowLeft")
        _press(page, "ArrowLeft")
        assert _focused_addr(page) == "fixture.r2.c1"

        _press(page, "ArrowDown")
        assert _focused_addr(page) == "fixture.r3.c1"

        _press(page, "ArrowUp")
        _press(page, "ArrowUp")
        assert _focused_addr(page) == "fixture.r1.c1"

    def test_enter_and_shift_enter_move_down_and_up(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c2")

        _press(page, "Enter")
        assert _focused_addr(page) == "fixture.r2.c2"

        _press(page, "Enter", shift=True)
        assert _focused_addr(page) == "fixture.r1.c2"

    def test_tab_and_shift_tab_move_right_and_left(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")

        _press(page, "Tab")
        assert _focused_addr(page) == "fixture.r1.c2"

        _press(page, "Tab", shift=True)
        assert _focused_addr(page) == "fixture.r1.c1"

    def test_tab_does_not_escape_browser_focus_while_inside_grid_cell(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c3")

        # Tab past the last column with no neighbour to move to: focus
        # must still remain on a grid cell, never escaping to the
        # outside input or anywhere else.
        _press(page, "Tab")
        focused_is_outside_input = page.evaluate(
            "document.activeElement === document.querySelector('#outside-input')"
        )
        assert focused_is_outside_input is False

    def test_home_and_end_move_to_row_boundaries(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r2.c2")

        _press(page, "Home")
        assert _focused_addr(page) == "fixture.r2.c1"

        _press(page, "End")
        assert _focused_addr(page) == "fixture.r2.c3"

    def test_ctrl_arrow_moves_to_edge_of_row_and_column(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r2.c2")

        _press(page, "ArrowDown", ctrl=True)
        assert _focused_addr(page) == "fixture.r3.c2"

        _press(page, "ArrowUp", ctrl=True)
        assert _focused_addr(page) == "fixture.r1.c2"

        _press(page, "ArrowRight", ctrl=True)
        assert _focused_addr(page) == "fixture.r1.c3"

        _press(page, "ArrowLeft", ctrl=True)
        assert _focused_addr(page) == "fixture.r1.c1"

    def test_keyboard_nav_noops_when_focus_outside_grid_cell(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("document.querySelector('#outside-input').focus()")

        _press(page, "ArrowRight")
        _press(page, "ArrowDown")

        # Active cell (per the registry) is unaffected — keyboard nav
        # only acts while DOM focus is on a registered grid cell.
        snapshot = page.evaluate(
            """
            (() => {
              var a = window.FcActiveCellManager.getActiveCell();
              return a ? a.cell.addr : null;
            })()
            """
        )
        assert snapshot == "fixture.r1.c1"
        focused_is_outside_input = page.evaluate(
            "document.activeElement === document.querySelector('#outside-input')"
        )
        assert focused_is_outside_input is True
        assert not page_errors

    def test_keyboard_nav_does_not_hijack_normal_input_typing(self, fixture_page):
        page, page_errors = fixture_page
        page.evaluate("document.querySelector('#outside-input').focus()")

        page.keyboard.type("abc")
        _press(page, "ArrowLeft")
        page.keyboard.type("d")

        value = page.evaluate("document.querySelector('#outside-input').value")
        assert value == "abdc"
        assert not page_errors

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcKeyboardRouter.init()")
        second = page.evaluate("window.FcKeyboardRouter.init()")
        third = page.evaluate("window.FcKeyboardRouter.init()")
        assert first is False
        assert second is False
        assert third is False

        _click_addr(page, "fixture.r1.c1")
        _press(page, "ArrowRight")
        assert _focused_addr(page) == "fixture.r1.c2"
        assert not page_errors
