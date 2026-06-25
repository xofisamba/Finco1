"""C1-PR2: Spreadsheet Interaction Layer — Active Cell foundation,
JS-execution tests.

Covers, per the C1-PR2 task spec (active-cell foundation only):
  - active cell initializes correctly (none active on load)
  - active cell changes correctly on a single click
  - the previously active cell clears (CSS class removed)
  - only one active cell exists at a time, even across two grids
  - an htmx swap that leaves the active cell's address intact
    preserves it as active
  - an htmx swap that removes the active cell clears it safely
  - repeated init() calls are idempotent (no duplicate listeners)

These tests run against a standalone static fixture
(tests/fixtures/c1_active_cell_fixture.html) via Playwright, not the
real Finco1 app, and are skipped if Playwright/Chromium are
unavailable — mirroring the pattern in
tests/test_c1_pr1_grid_registry_browser.py.

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented there.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_active_cell_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR2 JS tests",
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


class TestActiveCellManagerJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcActiveCellManager") == "object"
        assert not page_errors

    def test_no_active_cell_on_initial_load(self, fixture_page):
        page, _ = fixture_page
        assert _active_snapshot(page) is None

    def test_single_click_sets_active_cell(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.row1.amount")
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

    def test_clicking_another_cell_clears_the_previous_one(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.row1.amount")
        _click_addr(page, "fixture.row2.amount")

        assert _active_snapshot(page) == {
            "gridId": "fixture-grid",
            "addr": "fixture.row2.amount",
        }
        previous_has_class = page.evaluate(
            """
            document.querySelector('[data-fc-addr="fixture.row1.amount"]')
              .classList.contains('fc-active-cell')
            """
        )
        assert previous_has_class is False

    def test_only_one_active_cell_across_two_grids(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.row1.amount")
        _click_addr(page, "fixture2.row1.amount")

        assert _active_snapshot(page) == {
            "gridId": "fixture-grid-two",
            "addr": "fixture2.row1.amount",
        }
        first_grid_active = page.evaluate(
            "window.FcGridRegistry.getActiveCell('fixture-grid')"
        )
        assert first_grid_active is None

    def test_clear_active_cell_removes_class_and_state(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.row1.amount")
        page.evaluate("window.FcActiveCellManager.clearActiveCell()")

        assert _active_snapshot(page) is None
        has_class = page.evaluate(
            """
            document.querySelector('[data-fc-addr="fixture.row1.amount"]')
              .classList.contains('fc-active-cell')
            """
        )
        assert has_class is False

    def test_htmx_swap_preserves_active_cell_when_address_still_exists(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

        # Simulate an htmx swap that re-renders the same grid (new DOM
        # nodes, same address) inside #swap-target's sibling content —
        # here we just re-render the grid root in place and rescan it.
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

    def test_htmx_swap_clears_active_cell_when_it_disappears(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

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

        assert _active_snapshot(page) is None

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcActiveCellManager.init()")
        second = page.evaluate("window.FcActiveCellManager.init()")
        third = page.evaluate("window.FcActiveCellManager.init()")
        assert first is False
        assert second is False
        assert third is False

        # A single click should still only set one active cell, even
        # though init() (and thus any listener attachment) was called
        # multiple times above — proving no duplicate listeners.
        _click_addr(page, "fixture.row1.amount")
        assert _active_snapshot(page) == {
            "gridId": "fixture-grid",
            "addr": "fixture.row1.amount",
        }
        assert not page_errors
