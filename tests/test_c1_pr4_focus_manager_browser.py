"""C1-PR4: Spreadsheet Interaction Layer — DOM Focus Management,
JS-execution tests.

Covers, per the C1-PR4 task spec (DOM focus management only):
  - the active cell receives DOM focus
  - focus follows the active cell when it changes
  - focus restores after a compatible htmx-like swap
  - focus clears safely (no error, no trap) when the focused cell
    disappears
  - FcFocusManager.init() is idempotent

No keyboard, selection, or clipboard tests, per the explicit
prohibitions in the task spec.

These tests run against a standalone static fixture
(tests/fixtures/c1_focus_manager_fixture.html) via Playwright, not
the real Finco1 app, and are skipped if Playwright/Chromium are
unavailable — mirroring the pattern in
tests/test_c1_pr3_focus_scroll_browser.py.

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented there.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_focus_manager_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR4 JS tests",
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


class TestFocusManagerJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcFocusManager") == "object"
        assert not page_errors

    def test_active_cell_receives_dom_focus(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.row1.amount")
        assert _focused_addr(page) == "fixture.row1.amount"

    def test_focus_follows_active_cell_when_it_changes(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.row1.amount")
        _click_addr(page, "fixture.row2.amount")
        assert _focused_addr(page) == "fixture.row2.amount"

    def test_focus_follows_active_cell_across_grids(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.row1.amount")
        _click_addr(page, "fixture2.row1.amount")
        assert _focused_addr(page) == "fixture2.row1.amount"

    def test_focus_never_traps_an_outside_focusable_element(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.row1.amount")
        page.evaluate("document.querySelector('#outside-input').focus()")
        assert _focused_addr(page) is None
        focused_is_outside_input = page.evaluate(
            "document.activeElement === document.querySelector('#outside-input')"
        )
        assert focused_is_outside_input is True

    def test_focus_restores_after_htmx_swap_when_cell_survives(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

        page.evaluate(
            """
            () => {
              document.dispatchEvent(new CustomEvent('htmx:beforeSwap', { bubbles: true, detail: {} }));
            }
            """
        )
        page.evaluate(
            """
            (() => {
              var grid = document.querySelector('[data-fc-grid="fixture-grid"]');
              grid.outerHTML = grid.outerHTML; // new DOM nodes, same markup/addr
              var fresh = document.querySelector('[data-fc-grid="fixture-grid"]');
              var evt = new CustomEvent('htmx:afterSwap', { bubbles: true, detail: {} });
              Object.defineProperty(evt, 'target', { value: fresh });
              document.dispatchEvent(evt);
            })()
            """
        )

        assert _focused_addr(page) == "fixture.row1.amount"

    def test_focus_clears_safely_when_focused_cell_disappears(self, fixture_page):
        page, page_errors = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

        page.evaluate(
            """
            () => {
              document.dispatchEvent(new CustomEvent('htmx:beforeSwap', { bubbles: true, detail: {} }));
            }
            """
        )
        page.evaluate(
            """
            (() => {
              var grid = document.querySelector('[data-fc-grid="fixture-grid"]');
              grid.innerHTML =
                '<tbody><tr data-fc-row>' +
                '<td data-fc-cell data-fc-addr="fixture.replaced.amount" ' +
                'data-fc-editable="true">99</td></tr></tbody>';
              var evt = new CustomEvent('htmx:afterSwap', { bubbles: true, detail: {} });
              Object.defineProperty(evt, 'target', { value: grid });
              document.dispatchEvent(evt);
            })()
            """
        )

        assert _focused_addr(page) is None
        assert not page_errors

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcFocusManager.init()")
        second = page.evaluate("window.FcFocusManager.init()")
        third = page.evaluate("window.FcFocusManager.init()")
        assert first is False
        assert second is False
        assert third is False

        _click_addr(page, "fixture.row1.amount")
        assert _focused_addr(page) == "fixture.row1.amount"
        assert not page_errors
