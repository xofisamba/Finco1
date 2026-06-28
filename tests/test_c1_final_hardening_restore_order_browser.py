"""C1-Final-Hardening — Task 2: Deterministic Active-Cell Restore
Ordering, JS-execution tests.

Background: prior to this hardening pass, both `FcSwapLifecycle` and
`FcActiveCellManager` independently listened for the `fc:gridsScanned`
event and each could decide to set/clear the active cell — the
*effective* outcome after a swap depended on which of the two
`document.addEventListener('fc:gridsScanned', ...)` registrations ran
first, which in turn depended on `<script>` load order in
`base.html`.

This hardening makes `FcSwapLifecycle` the single authoritative
decision-maker (it owns the pre-swap snapshot and is the only code
that calls `setActiveCell()`/`clearActiveCell()` from it), and
`FcActiveCellManager.reconcileAfterScan()` a pure, idempotent
re-derivation from `FcGridRegistry` with no independent decision
power of its own. `FcSwapLifecycle` now calls
`FcActiveCellManager.reconcileAfterScan()` directly, synchronously,
right after making its restore decision — so there is exactly one
ordering, fixed in code, regardless of which module's `init()` ran
first or which one's `fc:gridsScanned` listener (if any) fires first.

These tests exercise that determinism directly: they manually invoke
the two modules' `fc:gridsScanned` reactions in *both* possible
orders (simulating reversed script-load/listener-registration order,
since real `<script>` tag reordering isn't practical to vary within a
single Playwright page) and assert the end state — active cell
restored, scroll restored, focus restored — is identical either way,
with no duplicate restores and no flicker (no extra DOM class
churn beyond the expected single steady state).

Reuses the existing `tests/fixtures/c1_focus_scroll_fixture.html`
fixture and the `_simulate_swap` / `_click_addr` helper pattern from
tests/test_c1_pr3_focus_scroll_browser.py, mirroring its Playwright
setup (skipped if Playwright/Chromium are unavailable). Deliberately
does NOT import main_web, for the same asyncio/Playwright-sync-API
reason documented there.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_focus_scroll_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-Final-Hardening JS tests",
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
          el.focus();
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


def _active_class_count(page, addr):
    return page.evaluate(
        """
        (addr) => document.querySelectorAll('[data-fc-addr="' + addr + '"].fc-active-cell').length
        """,
        addr,
    )


class TestDeterministicRestoreOrdering:
    def test_swap_lifecycle_first_then_active_cell_manager_reconcile(self, fixture_page):
        """The 'natural' order: FcSwapLifecycle's own htmx:beforeSwap/
        fc:gridsScanned handlers run, which (per the hardening)
        synchronously drive FcActiveCellManager.reconcileAfterScan()
        itself. Calling ActiveCellManager's reconciliation again
        afterwards (simulating its own fc:gridsScanned listener firing
        too, in case both are registered) must be a pure no-op."""
        page, page_errors = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")
        page.evaluate("document.querySelector('#scroll-wrap').scrollTop = 60")

        page.evaluate(
            """
            () => document.dispatchEvent(new CustomEvent('htmx:beforeSwap', { bubbles: true, detail: {} }))
            """
        )
        page.evaluate(
            """
            (() => {
              var grid = document.querySelector('[data-fc-grid="fixture-grid"]');
              grid.outerHTML = grid.outerHTML;
              var target = document.querySelector('[data-fc-grid="fixture-grid"]');
              var evt = new CustomEvent('htmx:afterSwap', { bubbles: true, detail: {} });
              Object.defineProperty(evt, 'target', { value: target });
              document.dispatchEvent(evt);
            })()
            """
        )

        # Explicitly re-invoke ActiveCellManager's own idempotent
        # reconciliation a second and third time, simulating it being
        # called out-of-order/redundantly relative to SwapLifecycle.
        page.evaluate(
            "window.FcActiveCellManager.reconcileAfterScan(window.FcGridRegistry.getGridIds())"
        )
        page.evaluate(
            "window.FcActiveCellManager.reconcileAfterScan(window.FcGridRegistry.getGridIds())"
        )

        assert _active_snapshot(page) == {"gridId": "fixture-grid", "addr": "fixture.row1.amount"}
        assert _active_class_count(page, "fixture.row1.amount") == 1, "duplicate/flickering active-cell class"
        assert page.evaluate("document.querySelector('#scroll-wrap').scrollTop") == 60
        assert not page_errors

    def test_active_cell_manager_reconcile_called_before_swap_lifecycle_restore(self, fixture_page):
        """Reversed order: simulate ActiveCellManager's own
        fc:gridsScanned reconciliation firing *before* SwapLifecycle
        has made its authoritative restore decision (e.g. if
        active-cell.js's <script> tag were loaded/initialised before
        swap-lifecycle.js, the opposite of base.html's real ordering).
        Since reconcileAfterScan() is a pure read of current registry
        state with no decision power of its own, calling it early is
        harmless — SwapLifecycle's subsequent authoritative restore
        must still produce the correct end state, identical to the
        natural-order test above."""
        page, page_errors = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")
        page.evaluate("document.querySelector('#scroll-wrap').scrollTop = 60")

        page.evaluate(
            """
            () => document.dispatchEvent(new CustomEvent('htmx:beforeSwap', { bubbles: true, detail: {} }))
            """
        )
        page.evaluate(
            """
            (() => {
              var grid = document.querySelector('[data-fc-grid="fixture-grid"]');
              grid.outerHTML = grid.outerHTML;
            })()
            """
        )

        # Out-of-order: invoke ActiveCellManager's idempotent
        # reconciliation directly, BEFORE the (still-pending)
        # authoritative fc:gridsScanned dispatch that would normally
        # trigger FcSwapLifecycle's restore first.
        registered_before = page.evaluate("window.FcGridRegistry.scan(document.querySelector('[data-fc-grid=\"fixture-grid\"]').parentElement)")
        page.evaluate(
            "window.FcActiveCellManager.reconcileAfterScan(%r)" % registered_before
        )

        # Now the real fc:gridsScanned dispatch fires (as engine.js
        # would after a real htmx:afterSwap), driving
        # FcSwapLifecycle's authoritative restore + its own explicit
        # call into reconcileAfterScan().
        page.evaluate(
            """
            (() => {
              var target = document.querySelector('[data-fc-grid="fixture-grid"]');
              var evt = new CustomEvent('htmx:afterSwap', { bubbles: true, detail: {} });
              Object.defineProperty(evt, 'target', { value: target });
              document.dispatchEvent(evt);
            })()
            """
        )

        assert _active_snapshot(page) == {"gridId": "fixture-grid", "addr": "fixture.row1.amount"}
        assert _active_class_count(page, "fixture.row1.amount") == 1, "duplicate/flickering active-cell class"
        assert page.evaluate("document.querySelector('#scroll-wrap').scrollTop") == 60
        assert not page_errors

    def test_no_focus_loss_across_repeated_reconciliation(self, fixture_page):
        """Repeated calls to reconcileAfterScan() (idempotent by
        design) must never steal focus away from wherever the browser
        currently has it — this module never calls .focus() at all,
        so focus is exactly whatever it was before these calls."""
        page, page_errors = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

        focused_addr_before = page.evaluate(
            "document.activeElement && document.activeElement.getAttribute('data-fc-addr')"
        )

        for _ in range(5):
            page.evaluate(
                "window.FcActiveCellManager.reconcileAfterScan(window.FcGridRegistry.getGridIds())"
            )

        focused_addr_after = page.evaluate(
            "document.activeElement && document.activeElement.getAttribute('data-fc-addr')"
        )

        assert focused_addr_after == focused_addr_before
        assert not page_errors

    def test_reconcile_after_scan_is_idempotent_function(self, fixture_page):
        page, page_errors = fixture_page
        page.evaluate("window.FcGridRegistry.scanAll()")
        _click_addr(page, "fixture.row1.amount")

        grids = page.evaluate("window.FcGridRegistry.getGridIds()")
        results = [
            page.evaluate("window.FcActiveCellManager.reconcileAfterScan(%r)" % grids)
            for _ in range(3)
        ]
        # reconcileAfterScan() has no return-value contract (void), but
        # it must not throw, and the active-cell state must be
        # unchanged across repeated calls.
        assert _active_snapshot(page) == {"gridId": "fixture-grid", "addr": "fixture.row1.amount"}
        assert _active_class_count(page, "fixture.row1.amount") == 1
        assert not page_errors
