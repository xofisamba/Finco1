"""C1-PR6: Spreadsheet Interaction Layer — Selection Model Foundation,
JS-execution tests.

Covers, per the C1-PR6 task spec (selection model foundation only):
  1. Clicking a cell creates a single-cell selection.
  2. Clicking another cell clears the previous selection.
  3. Only one selection exists globally (across grids).
  4. Plain keyboard movement collapses the selection to the new
     active cell.
  5. Shift+Arrow extends a rectangular range from a fixed anchor.
  6. Selection clears safely (no JS errors) when the grid/cells
     disappear.
  7. Selection restores (range) or collapses (single cell) safely
     after a compatible htmx swap.
  8. (PR1-PR5 regressions covered by their own existing test files.)
  9. No clipboard/copy/paste/undo/fill behaviour exists (asserted via
     the static checks in test_c1_pr6_selection_manager.py; this file
     does not exercise any since none exists to exercise).

These tests run against a standalone static fixture
(tests/fixtures/c1_selection_manager_fixture.html) via Playwright, not
the real Finco1 app, and are skipped if Playwright/Chromium are
unavailable — mirroring the pattern in
tests/test_c1_pr5_keyboard_router_browser.py.

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented there.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_selection_manager_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR6 JS tests",
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


def _press(page, key, **modifiers):
    parts = []
    if modifiers.get("ctrl"):
        parts.append("Control")
    if modifiers.get("shift"):
        parts.append("Shift")
    parts.append(key)
    page.keyboard.press("+".join(parts))


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
            target_selector or "document.querySelector('%s')" % grid_selector,
        )
    )


def _get_selection(page):
    return page.evaluate("window.FcSelectionManager.getSelection()")


def _selected_addrs(page):
    return page.evaluate(
        """
        Array.prototype.map.call(
          document.querySelectorAll('.fc-selected-cell'),
          function (el) { return el.getAttribute('data-fc-addr'); }
        ).sort()
        """
    )


class TestSelectionManagerJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcSelectionManager") == "object"
        assert not page_errors

    def test_click_creates_single_cell_selection(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r2.c2")

        sel = _get_selection(page)
        assert sel["gridId"] == "fixture-grid"
        assert sel["anchorAddr"] == "fixture.r2.c2"
        assert sel["activeAddr"] == "fixture.r2.c2"
        assert sel["addresses"] == ["fixture.r2.c2"]
        assert _selected_addrs(page) == ["fixture.r2.c2"]

    def test_click_another_cell_clears_previous_selection(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _click_addr(page, "fixture.r3.c3")

        assert _selected_addrs(page) == ["fixture.r3.c3"]
        sel = _get_selection(page)
        assert sel["anchorAddr"] == "fixture.r3.c3"
        assert sel["activeAddr"] == "fixture.r3.c3"

    def test_only_one_selection_exists_globally_across_grids(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        assert _selected_addrs(page) == ["fixture.r1.c1"]

        _click_addr(page, "fixture2.r1.c1")
        assert _selected_addrs(page) == ["fixture2.r1.c1"]
        sel = _get_selection(page)
        assert sel["gridId"] == "fixture-grid-two"

    def test_plain_keyboard_movement_collapses_selection_to_active_cell(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _press(page, "ArrowRight", shift=True)
        _press(page, "ArrowDown", shift=True)
        # Now a 2x2 range is selected; a plain move must collapse it.
        _press(page, "ArrowRight")

        sel = _get_selection(page)
        assert sel["anchorAddr"] == sel["activeAddr"] == "fixture.r2.c3"
        assert sel["addresses"] == ["fixture.r2.c3"]
        assert _selected_addrs(page) == ["fixture.r2.c3"]

    def test_shift_arrow_extends_rectangular_range_from_fixed_anchor(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")

        _press(page, "ArrowRight", shift=True)
        _press(page, "ArrowDown", shift=True)

        sel = _get_selection(page)
        assert sel["anchorAddr"] == "fixture.r1.c1"
        assert sel["activeAddr"] == "fixture.r2.c2"
        assert sorted(sel["addresses"]) == sorted(
            ["fixture.r1.c1", "fixture.r1.c2", "fixture.r2.c1", "fixture.r2.c2"]
        )
        assert _selected_addrs(page) == sorted(
            ["fixture.r1.c1", "fixture.r1.c2", "fixture.r2.c1", "fixture.r2.c2"]
        )

    def test_selection_clears_safely_when_cells_disappear(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")

        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            """
            grid.innerHTML =
              '<tbody><tr data-fc-row>' +
              '<td data-fc-cell data-fc-addr="fixture.replaced.c1" ' +
              'data-fc-editable="true">99</td></tr></tbody>';
            """,
            "grid",
        )

        assert _get_selection(page) is None
        assert _selected_addrs(page) == []
        assert not page_errors

    def test_selection_collapses_after_swap_when_anchor_does_not_survive(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _press(page, "ArrowRight", shift=True)

        # Simulate a swap that re-renders the grid: the active cell
        # survives at the same address, but the anchor's prior address
        # is gone (a fresh single <td> stands in for the whole table).
        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            """
            grid.innerHTML =
              '<tbody><tr data-fc-row>' +
              '<td data-fc-cell data-fc-addr="fixture.r1.c2" data-fc-editable="true">12</td>' +
              '</tr></tbody>';
            """,
            "grid",
        )

        sel = _get_selection(page)
        assert sel["anchorAddr"] == sel["activeAddr"] == "fixture.r1.c2"
        assert sel["addresses"] == ["fixture.r1.c2"]
        assert not page_errors

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcSelectionManager.init()")
        second = page.evaluate("window.FcSelectionManager.init()")
        third = page.evaluate("window.FcSelectionManager.init()")
        assert first is False
        assert second is False
        assert third is False

        _click_addr(page, "fixture.r1.c1")
        assert _get_selection(page)["activeAddr"] == "fixture.r1.c1"
        assert not page_errors
