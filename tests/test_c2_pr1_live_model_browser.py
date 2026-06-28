"""C2-PR1: Live Modelling Layer — Live Modelling Foundation,
JS-execution tests.

Covers, per the C2-PR1 task spec (infrastructure foundation only):
  - dirty state is tracked (cell/sheet/project)
  - multiple edits batch correctly (coalesced per cell)
  - scheduler queues events
  - no recalculation occurs
  - no Save/Run behaviour changes
  - session lifecycle (start/end)
  - dirty tracking stays scoped per grid/sheet
  - edits outside the grid are never tracked

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented in tests/test_c1_pr7_clipboard_controller_browser.py.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c2_live_model_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C2-PR1 JS tests",
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


def _edit_cell(page, addr, value):
    page.evaluate(
        """
        (args) => {
          var el = document.querySelector('[data-fc-addr="' + args.addr + '"] input');
          document.activeElement && document.activeElement.blur();
          el.focus();
          el.value = args.value;
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        {"addr": addr, "value": value},
    )


class TestLiveModelJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcLiveModel") == "object"
        assert not page_errors

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcLiveModel.init()")
        second = page.evaluate("window.FcLiveModel.init()")
        assert first is False
        assert second is False
        assert not page_errors

    def test_dirty_state_is_tracked(self, fixture_page):
        page, _ = fixture_page
        assert page.evaluate("window.FcLiveModel.isCellDirty('fixture-grid', 'fixture.r1.c1')") is False

        _edit_cell(page, "fixture.r1.c1", "99")

        assert page.evaluate("window.FcLiveModel.isCellDirty('fixture-grid', 'fixture.r1.c1')") is True
        assert page.evaluate("window.FcLiveModel.isSheetDirty('fixture-grid')") is True
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True
        # A different, untouched grid must not be marked dirty.
        assert page.evaluate("window.FcLiveModel.isSheetDirty('fixture-grid-two')") is False

    def test_multiple_edits_batch_correctly(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "first")
        _edit_cell(page, "fixture.r1.c1", "second")
        _edit_cell(page, "fixture.r1.c2", "other")

        batch = page.evaluate("window.FcLiveModel.getBatch('fixture-grid')")
        assert len(batch) == 2
        c1_entry = next(e for e in batch if e["addr"] == "fixture.r1.c1")
        # Coalesced: before is the original value, after is the latest.
        assert c1_entry["before"] == "11"
        assert c1_entry["after"] == "second"

    def test_flush_batch_clears_pending_batch(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "x")

        flushed = page.evaluate("window.FcLiveModel.flushBatch('fixture-grid')")
        assert len(flushed) == 1
        assert page.evaluate("window.FcLiveModel.getBatch('fixture-grid')") == []
        # Dirty flags are independent of the batch and survive a flush.
        assert page.evaluate("window.FcLiveModel.isCellDirty('fixture-grid', 'fixture.r1.c1')") is True

    def test_scheduler_queues_events(self, fixture_page):
        page, _ = fixture_page
        assert page.evaluate("window.FcLiveModel.scheduler.queueLength()") == 0

        _edit_cell(page, "fixture.r1.c1", "queued")

        assert page.evaluate("window.FcLiveModel.scheduler.queueLength()") == 1
        events = page.evaluate("window.FcLiveModel.scheduler.flush()")
        assert len(events) == 1
        assert events[0]["type"] == "cell-changed"
        assert events[0]["addr"] == "fixture.r1.c1"
        assert page.evaluate("window.FcLiveModel.scheduler.queueLength()") == 0

    def test_no_recalculation_occurs(self, fixture_page):
        page, page_errors = fixture_page
        _edit_cell(page, "fixture.r1.c1", "42")

        # The scheduler only ever holds plain queued event objects —
        # never a function — proving nothing is ever invoked/executed.
        events = page.evaluate("window.FcLiveModel.scheduler.peek()")
        assert all(isinstance(e, dict) for e in events)
        assert not page_errors

    def test_non_editable_cell_is_never_tracked(self, fixture_page):
        page, page_errors = fixture_page
        _edit_cell(page, "fixture.r1.readonly", "changed")

        assert page.evaluate("window.FcLiveModel.isCellDirty('fixture-grid', 'fixture.r1.readonly')") is False
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is False
        assert page.evaluate("window.FcLiveModel.scheduler.queueLength()") == 0
        assert not page_errors

    def test_edit_outside_grid_is_never_tracked(self, fixture_page):
        page, page_errors = fixture_page
        page.evaluate(
            """
            () => {
              var el = document.querySelector('#outside-input');
              el.focus();
              el.value = 'hello';
              el.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """
        )
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is False
        assert page.evaluate("window.FcLiveModel.scheduler.queueLength()") == 0
        assert not page_errors

    def test_session_lifecycle(self, fixture_page):
        page, _ = fixture_page
        assert page.evaluate("window.FcLiveModel.isSessionActive()") is False

        _edit_cell(page, "fixture.r1.c1", "v1")
        assert page.evaluate("window.FcLiveModel.isSessionActive()") is True

        summary = page.evaluate("window.FcLiveModel.endSession()")
        assert summary["batch"][0]["addr"] == "fixture.r1.c1"
        assert page.evaluate("window.FcLiveModel.isSessionActive()") is False

    def test_clear_dirty_resets_state(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "v1")
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True

        page.evaluate("window.FcLiveModel.clearDirty()")
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is False
        assert page.evaluate("window.FcLiveModel.isCellDirty('fixture-grid', 'fixture.r1.c1')") is False

    def test_dirty_tracking_scoped_per_grid(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture2.r1.c1", "x")

        assert page.evaluate("window.FcLiveModel.isSheetDirty('fixture-grid-two')") is True
        assert page.evaluate("window.FcLiveModel.isSheetDirty('fixture-grid')") is False
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True


class TestLiveModelC2PR2DirtyStateUnificationApi:
    """C2-PR2: the canonical dirty-state API surface (clearCellDirty/
    clearSheetDirty/clearAllDirty + 'sheet-clean'/'project-clean'
    pub/sub) that static/app.js now consumes instead of maintaining a
    second, parallel dirty manager."""

    def test_clear_cell_dirty_clears_only_that_cell(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "v1")
        _edit_cell(page, "fixture.r1.c2", "v2")

        page.evaluate("window.FcLiveModel.clearCellDirty('fixture-grid', 'fixture.r1.c1')")

        assert page.evaluate("window.FcLiveModel.isCellDirty('fixture-grid', 'fixture.r1.c1')") is False
        assert page.evaluate("window.FcLiveModel.isCellDirty('fixture-grid', 'fixture.r1.c2')") is True
        # Sheet/project stay dirty because a sibling cell is still dirty.
        assert page.evaluate("window.FcLiveModel.isSheetDirty('fixture-grid')") is True
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True

    def test_clear_cell_dirty_clears_sheet_when_last_cell_cleared(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "v1")

        page.evaluate("window.FcLiveModel.clearCellDirty('fixture-grid', 'fixture.r1.c1')")

        assert page.evaluate("window.FcLiveModel.isSheetDirty('fixture-grid')") is False
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is False

    def test_clear_sheet_dirty_is_alias_of_clear_dirty(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "v1")
        _edit_cell(page, "fixture2.r1.c1", "v2")

        page.evaluate("window.FcLiveModel.clearSheetDirty('fixture-grid')")

        assert page.evaluate("window.FcLiveModel.isSheetDirty('fixture-grid')") is False
        # The other sheet is untouched, so the project is still dirty.
        assert page.evaluate("window.FcLiveModel.isSheetDirty('fixture-grid-two')") is True
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True

    def test_clear_all_dirty_is_alias_of_clear_dirty_no_arg(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "v1")
        _edit_cell(page, "fixture2.r1.c1", "v2")

        page.evaluate("window.FcLiveModel.clearAllDirty()")

        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is False
        assert page.evaluate("window.FcLiveModel.getDirtySheets().length") == 0

    def test_project_clean_event_emitted_on_clear_all_dirty(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "v1")

        page.evaluate(
            """
            () => {
              window.__projectCleanFired = false;
              window.FcLiveModel.on('project-clean', function() { window.__projectCleanFired = true; });
              window.FcLiveModel.clearAllDirty();
            }
            """
        )
        assert page.evaluate("window.__projectCleanFired") is True

    def test_project_clean_event_emitted_when_last_dirty_sheet_clears(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "v1")

        page.evaluate(
            """
            () => {
              window.__projectCleanFired = false;
              window.FcLiveModel.on('project-clean', function() { window.__projectCleanFired = true; });
              window.FcLiveModel.clearSheetDirty('fixture-grid');
            }
            """
        )
        assert page.evaluate("window.__projectCleanFired") is True

    def test_project_clean_not_emitted_while_other_sheet_still_dirty(self, fixture_page):
        page, _ = fixture_page
        _edit_cell(page, "fixture.r1.c1", "v1")
        _edit_cell(page, "fixture2.r1.c1", "v2")

        page.evaluate(
            """
            () => {
              window.__projectCleanFired = false;
              window.FcLiveModel.on('project-clean', function() { window.__projectCleanFired = true; });
              window.FcLiveModel.clearSheetDirty('fixture-grid');
            }
            """
        )
        assert page.evaluate("window.__projectCleanFired") is False
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True
