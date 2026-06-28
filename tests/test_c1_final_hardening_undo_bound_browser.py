"""C1-Final-Hardening — Task 1: Bounded Undo Stack, JS-execution tests.

Background: FcUndoManager's undo stack
(`static/interaction/undo-manager.js`) was previously unbounded — a
sufficiently long editing session could grow it without limit. This
hardening introduces a documented `MAX_UNDO = 300` constant and FIFO
eviction of the oldest transaction(s) once the stack would exceed
that bound, with redo behaviour otherwise unchanged.

These tests push synthetic transactions directly via
`FcUndoManager.recordTransaction()` (the same public entry point
`FcClipboardController.pasteText()` already uses) rather than
exercising real paste/edit UI flows, since the bound itself is a
pure stack-management property independent of how a transaction was
produced. Reuses `tests/fixtures/c1_undo_redo_fixture.html`, mirroring
the Playwright setup in tests/test_c1_pr8_undo_redo_browser.py
(skipped if Playwright/Chromium are unavailable). Deliberately does
NOT import main_web, for the same asyncio/Playwright-sync-API reason
documented there.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_undo_redo_fixture.html")

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


_PUSH_N_TRANSACTIONS_JS = """
(n) => {
  for (var i = 0; i < n; i++) {
    window.FcUndoManager.recordTransaction({
      type: 'cell-edit',
      gridId: 'fixture-grid',
      changes: [{ addr: 'fixture.r1.c1', before: 'before-' + i, after: 'after-' + i }],
      activeBefore: null,
      activeAfter: null,
      selectionBefore: null,
      selectionAfter: null
    });
  }
}
"""


def _stack_length(page):
    # FcUndoManager doesn't expose the raw stack publicly (by design —
    # it never leaks internal transaction objects), so length is
    # inferred by repeatedly calling undo() until it returns false,
    # then restoring via redo() the same number of times. This is the
    # only externally-observable way to count entries without adding
    # a test-only backdoor to production code.
    return page.evaluate(
        """
        (() => {
          var count = 0;
          while (window.FcUndoManager.undo()) count++;
          for (var i = 0; i < count; i++) window.FcUndoManager.redo();
          return count;
        })()
        """
    )


class TestBoundedUndoStack:
    def test_max_undo_constant_is_in_documented_range(self, fixture_page):
        page, _ = fixture_page
        max_undo = page.evaluate("window.FcUndoManager.MAX_UNDO")
        assert isinstance(max_undo, int)
        assert 200 <= max_undo <= 500
        assert max_undo == 300

    def test_overflow_discards_oldest_transactions(self, fixture_page):
        page, page_errors = fixture_page
        max_undo = page.evaluate("window.FcUndoManager.MAX_UNDO")
        overflow_by = 50
        page.evaluate(_PUSH_N_TRANSACTIONS_JS, max_undo + overflow_by)

        assert _stack_length(page) == max_undo
        assert not page_errors

    def test_only_oldest_entries_disappear_not_newest(self, fixture_page):
        """Push MAX_UNDO + 50 transactions where transaction i's
        'before' value is the literal string 'before-i'. After
        overflow, undoing all the way down must reach exactly
        'before-50' (the 50 oldest were evicted) and never
        'before-0'."""
        page, page_errors = fixture_page
        max_undo = page.evaluate("window.FcUndoManager.MAX_UNDO")
        overflow_by = 50
        total = max_undo + overflow_by
        page.evaluate(_PUSH_N_TRANSACTIONS_JS, total)

        # Set the cell to a known sentinel value before undoing, so we
        # can observe exactly what the final (oldest surviving) undo
        # restores it to.
        page.evaluate(
            """
            () => {
              document.querySelector('[data-fc-addr="fixture.r1.c1"]').textContent = 'sentinel';
            }
            """
        )

        undo_count = page.evaluate(
            """
            (() => {
              var count = 0;
              while (window.FcUndoManager.undo()) count++;
              return count;
            })()
            """
        )
        final_value = page.evaluate(
            """document.querySelector('[data-fc-addr="fixture.r1.c1"]').textContent"""
        )

        assert undo_count == max_undo
        # The oldest *surviving* transaction is index `overflow_by`
        # (0-indexed), whose "before" value is 'before-50' — the
        # newest-discarded-last guarantee. The very first ever pushed
        # transaction ('before-0') must be unreachable.
        assert final_value == "before-%d" % overflow_by
        assert not page_errors

    def test_newest_entries_still_undo_correctly_after_overflow(self, fixture_page):
        """The most recently pushed transaction (guaranteed to survive
        eviction) must still undo to its correct 'before' value."""
        page, page_errors = fixture_page
        max_undo = page.evaluate("window.FcUndoManager.MAX_UNDO")
        total = max_undo + 75
        page.evaluate(_PUSH_N_TRANSACTIONS_JS, total)

        page.evaluate(
            """
            () => {
              document.querySelector('[data-fc-addr="fixture.r1.c1"]').textContent = 'sentinel';
            }
            """
        )
        ok = page.evaluate("window.FcUndoManager.undo()")
        value_after_first_undo = page.evaluate(
            """document.querySelector('[data-fc-addr="fixture.r1.c1"]').textContent"""
        )

        assert ok is True
        assert value_after_first_undo == "before-%d" % (total - 1)
        assert not page_errors

    def test_redo_unaffected_by_bound(self, fixture_page):
        """Redo behaviour is unchanged by the bound: undoing once and
        redoing once must round-trip to the same 'after' value as
        before introducing MAX_UNDO."""
        page, page_errors = fixture_page
        max_undo = page.evaluate("window.FcUndoManager.MAX_UNDO")
        total = max_undo + 10
        page.evaluate(_PUSH_N_TRANSACTIONS_JS, total)

        page.evaluate("window.FcUndoManager.undo()")
        redo_ok = page.evaluate("window.FcUndoManager.redo()")
        value_after_redo = page.evaluate(
            """document.querySelector('[data-fc-addr="fixture.r1.c1"]').textContent"""
        )

        assert redo_ok is True
        assert value_after_redo == "after-%d" % (total - 1)
        assert not page_errors

    def test_no_overflow_below_bound_is_unaffected(self, fixture_page):
        """Pushing fewer than MAX_UNDO transactions must not trigger
        any eviction — exact stack length is preserved."""
        page, page_errors = fixture_page
        max_undo = page.evaluate("window.FcUndoManager.MAX_UNDO")
        n = max_undo - 20
        page.evaluate(_PUSH_N_TRANSACTIONS_JS, n)

        assert _stack_length(page) == n
        assert not page_errors
