"""C1-PR1: Spreadsheet Interaction Layer — GridRegistry JS-execution tests.

Covers, per docs/C1_INTERACTION_LAYER_DESIGN.md (PR1 scope only):
  - the engine loads
  - the registry initializes and grids register correctly
  - repeated registration is safe (idempotent re-scan)
  - the htmx lifecycle hook attaches exactly once

These tests run against a standalone static fixture
(tests/fixtures/c1_grid_registry_fixture.html) via Playwright, not
the real Finco1 app, and are skipped if Playwright/Chromium are
unavailable — mirroring the existing optional-browser-dependency
pattern in tests/test_phase16_playwright_smoke_suite.py.

This module deliberately does NOT import main_web (or anything that
imports it). Playwright's sync API refuses to run inside an already
running asyncio/anyio event loop, and merely importing main_web in
this process is enough to leave one active, which breaks every test
below with "Sync API inside the asyncio loop" instead of exercising
the JS. Static-file/template-wiring checks that do need the app live
in tests/test_c1_pr1_grid_registry.py instead.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_grid_registry_fixture.html")
ENGINE_JS_PATH = os.path.join(BASE_DIR, "static", "interaction", "engine.js")


_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR1 JS tests",
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


class TestGridRegistryJs:
    def test_engine_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcGridRegistry") == "object"
        assert not page_errors

    def test_registry_initializes_and_grids_register(self, fixture_page):
        page, _ = fixture_page
        registered = page.evaluate("window.FcGridRegistry.scanAll()")
        assert sorted(registered) == ["fixture-grid", "fixture-grid-two"]

        row_count = page.evaluate(
            "window.FcGridRegistry.getGrid('fixture-grid').rows.length"
        )
        assert row_count == 3  # two data rows + one subtotal row

        cell = page.evaluate(
            """
            (() => {
              var r = window.FcGridRegistry.getAddr('fixture-grid', 'fixture.row1.amount');
              return { addr: r.addr, row: r.row, col: r.col, editable: r.editable, kind: r.kind };
            })()
            """
        )
        assert cell["row"] == 0
        assert cell["col"] == 1
        assert cell["editable"] is True

    def test_subtotal_row_is_navigable_but_not_editable(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        subtotal_cell = page.evaluate(
            """
            (() => {
              var r = window.FcGridRegistry.getAddr('fixture-grid', 'fixture.subtotal.amount');
              return r ? { addr: r.addr, editable: r.editable } : null;
            })()
            """
        )
        assert subtotal_cell is not None
        assert subtotal_cell["editable"] is False

        # Navigating up from the subtotal row lands on row 2's editable cell.
        neighbor = page.evaluate(
            """
            (() => {
              var subtotal = window.FcGridRegistry.getAddr('fixture-grid', 'fixture.subtotal.amount');
              var n = window.FcGridRegistry.neighbors(subtotal, 'up');
              return n ? { addr: n.addr, editable: n.editable } : null;
            })()
            """
        )
        assert neighbor["addr"] == "fixture.row2.amount"
        assert neighbor["editable"] is True

    def test_neighbors_returns_null_at_grid_edges(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        no_up = page.evaluate(
            "window.FcGridRegistry.neighbors(window.FcGridRegistry.getCell('fixture-grid', 0, 0), 'up')"
        )
        assert no_up is None
        no_left = page.evaluate(
            "window.FcGridRegistry.neighbors(window.FcGridRegistry.getCell('fixture-grid', 0, 0), 'left')"
        )
        assert no_left is None

    def test_repeated_registration_is_safe(self, fixture_page):
        page, _ = fixture_page
        first = page.evaluate("window.FcGridRegistry.scanAll()")
        second = page.evaluate("window.FcGridRegistry.scanAll()")
        third = page.evaluate("window.FcGridRegistry.scanAll()")
        assert sorted(first) == sorted(second) == sorted(third)

        row_count_after_triple_scan = page.evaluate(
            "window.FcGridRegistry.getGrid('fixture-grid').rows.length"
        )
        assert row_count_after_triple_scan == 3  # no duplication/accumulation

    def test_two_grids_on_one_page_stay_isolated(self, fixture_page):
        page, _ = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        grid_one_rows = page.evaluate(
            "window.FcGridRegistry.getGrid('fixture-grid').rows.length"
        )
        grid_two_rows = page.evaluate(
            "window.FcGridRegistry.getGrid('fixture-grid-two').rows.length"
        )
        assert grid_one_rows == 3
        assert grid_two_rows == 1


class TestEngineLifecycleHook:
    def _load_engine(self, page):
        page.add_script_tag(path=ENGINE_JS_PATH)

    def test_hook_attaches_once_even_if_boot_called_repeatedly(self, fixture_page):
        page, page_errors = fixture_page
        self._load_engine(page)
        first_boot = page.evaluate("window.FcInteractionEngine.boot()")
        second_boot = page.evaluate("window.FcInteractionEngine.boot()")
        third_boot = page.evaluate("window.FcInteractionEngine.boot()")
        # First boot() call (the module's own auto-boot on load) has
        # already happened; every explicit call here is a re-call.
        assert first_boot is False
        assert second_boot is False
        assert third_boot is False
        assert page.evaluate("window.FcInteractionEngine.isBooted()") is True
        assert not page_errors

    def test_afterswap_hook_rescans_only_the_swapped_subtree(self, fixture_page):
        page, _ = fixture_page
        self._load_engine(page)
        page.evaluate("window.FcGridRegistry.scanAll()")

        # Simulate an htmx swap landing inside #swap-target with a
        # brand new grid that was not present at initial scan time.
        page.evaluate(
            """
            (() => {
              var target = document.getElementById('swap-target');
              target.innerHTML =
                '<table data-fc-grid="late-grid"><tbody><tr data-fc-row>' +
                '<td data-fc-cell data-fc-addr="late.cell" data-fc-editable="true"></td>' +
                '</tr></tbody></table>';
              var evt = new CustomEvent('htmx:afterSwap', { bubbles: true });
              target.dispatchEvent(evt);
            })()
            """
        )
        late_cell_addr = page.evaluate(
            """
            (() => {
              var g = window.FcGridRegistry.getGrid('late-grid');
              return g ? g.rows[0][0].addr : null;
            })()
            """
        )
        assert late_cell_addr == "late.cell"

        # The grids registered at initial load are untouched by the
        # later, narrowly-scoped rescan.
        original_grid_still_present = page.evaluate(
            "window.FcGridRegistry.getGrid('fixture-grid') !== null"
        )
        assert original_grid_still_present is True

    def test_engine_ready_event_fires_on_boot(self, fixture_page):
        page, _ = fixture_page
        fired = page.evaluate(
            """
            (() => {
              return new Promise((resolve) => {
                document.addEventListener('fc:engineReady', () => resolve(true));
                var s = document.createElement('script');
                s.src = '../../static/interaction/engine.js';
                document.body.appendChild(s);
                setTimeout(() => resolve(false), 2000);
              });
            })()
            """
        )
        assert fired is True
