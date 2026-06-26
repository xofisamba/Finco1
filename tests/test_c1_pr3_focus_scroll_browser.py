"""C1-PR3: Spreadsheet Interaction Layer — Focus & Scroll Preservation,
JS-execution tests.

Covers, per the C1-PR3 task spec (focus & scroll preservation only):
  - active cell survives a swap when the same grid/cell still exists
  - active cell clears safely when the cell disappears in the swap
  - scroll position restores when the grid's scroll container survives
  - scroll state clears safely when the container disappears
  - FcSwapLifecycle.init() is idempotent

No keyboard, clipboard, or selection tests, per the explicit
prohibitions in the task spec.

These tests run against a standalone static fixture
(tests/fixtures/c1_focus_scroll_fixture.html) via Playwright, not the
real Finco1 app, and are skipped if Playwright/Chromium are
unavailable — mirroring the pattern in
tests/test_c1_pr2_active_cell_browser.py.

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented there.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_focus_scroll_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR3 JS tests",
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


def _active_snapshot(page):
    return page.evaluate(
        """
        (() => {
          var a = window.FcActiveCellManager.getActiveCell();
          return a ? { gridId: a.gridId, addr: a.cell.addr } : null;
        })()
        """
    )


def _simulate_swap(page, grid_selector, new_inner_html_js_expr, target_selector=None):
    """Dispatch htmx:beforeSwap, mutate the DOM, then htmx:afterSwap —
    mirroring the real htmx lifecycle that engine.js / swap-lifecycle.js
    listen for, without depending on htmx itself in the fixture."""
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
          var grid = document.querySelector('%s');
          %s
          var target = %s;
          var evt = new CustomEvent('htmx:afterSwap', { bubbles: true, detail: {} });
          Object.defineProperty(evt, 'target', { value: target });
          document.dispatchEvent(evt);
        })()
        """
        % (
            grid_selector,
            new_inner_html_js_expr,
            target_selector or "grid",
        )
    )


class TestSwapLifecycleJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcSwapLifecycle") == "object"
        assert not page_errors

    def test_active_cell_survives_swap_when_same_cell_remains(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            "grid.outerHTML = grid.outerHTML;",
            "document.querySelector('[data-fc-grid=\"fixture-grid\"]')",
        )

        assert _active_snapshot(page) == {
            "gridId": "fixture-grid",
            "addr": "fixture.row1.amount",
        }
        has_class = page.evaluate(
            """
            document.querySelector('[data-fc-addr="fixture.row1.amount"]')
              .classList.contains('fc-active-cell')
            """
        )
        assert has_class is True

    def test_active_cell_clears_safely_when_cell_disappears(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            """
            grid.innerHTML =
              '<tbody><tr data-fc-row>' +
              '<td data-fc-cell data-fc-addr="fixture.replaced.amount" ' +
              'data-fc-editable="true">99</td></tr></tbody>';
            """,
            "grid",
        )

        assert _active_snapshot(page) is None

    def test_scroll_position_restores_when_container_survives(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        page.evaluate("document.querySelector('#scroll-wrap').scrollTop = 60")

        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            "grid.outerHTML = grid.outerHTML;",
            "document.querySelector('[data-fc-grid=\"fixture-grid\"]')",
        )

        scroll_top = page.evaluate("document.querySelector('#scroll-wrap').scrollTop")
        assert scroll_top == 60

    def test_scroll_state_clears_safely_when_container_disappears(self, fixture_page):
        page, page_errors = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        page.evaluate("document.querySelector('#scroll-wrap').scrollTop = 60")

        # Simulate a swap that removes the scrollable wrapper entirely
        # (the second, non-scrollable grid's swap should not error out
        # trying to restore a now-nonexistent container).
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
              var wrap = document.querySelector('#scroll-wrap');
              wrap.outerHTML = '<div id="scroll-wrap-removed"></div>';
              var evt = new CustomEvent('htmx:afterSwap', { bubbles: true, detail: {} });
              Object.defineProperty(evt, 'target', { value: document.body });
              document.dispatchEvent(evt);
            })()
            """
        )

        # No error should occur even though the scroll container that
        # was snapshotted before the swap no longer exists afterwards
        # (FcGridRegistry doesn't deregister grids that simply aren't
        # found in a given scan — only htmx:beforeSwap/afterSwap
        # robustness is under test here).
        assert not page_errors

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcSwapLifecycle.init()")
        second = page.evaluate("window.FcSwapLifecycle.init()")
        third = page.evaluate("window.FcSwapLifecycle.init()")
        assert first is False
        assert second is False
        assert third is False

        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            "grid.outerHTML = grid.outerHTML;",
            "document.querySelector('[data-fc-grid=\"fixture-grid\"]')",
        )

        assert _active_snapshot(page) == {
            "gridId": "fixture-grid",
            "addr": "fixture.row1.amount",
        }
        assert not page_errors
