"""C1-PR9: Spreadsheet Interaction Layer — Fill Down / Fill Right
Foundation, JS-execution tests.

Covers, per the C1-PR9 task spec (fill foundation only):
  1. Ctrl+D fills down from top row.
  2. Ctrl+R fills right from left column.
  3. Single-cell selection no-ops safely.
  4. Non-editable cells are skipped.
  5. Fill clips safely at bounds.
  6. Fill records one undo transaction.
  7. Undo restores previous values.
  8. Redo restores filled values.
  9. Selection remains stable after fill.
  10. Keyboard shortcuts do not hijack normal inputs.
  11. Existing PR1-PR8 behaviour (keyboard nav, selection, copy/paste,
      undo/redo, HTMX swap restore) remains unaffected.

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented in tests/test_c1_pr7_clipboard_controller_browser.py.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_fill_controller_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR9 JS tests",
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


def _select_range(page, anchor_addr, active_addr):
    page.evaluate(
        """
        (args) => {
          window.FcSelectionManager.selectSingle(
            'fixture-grid', window.FcGridRegistry.getAddr('fixture-grid', args.anchor));
          window.FcSelectionManager.extendTo(
            'fixture-grid', window.FcGridRegistry.getAddr('fixture-grid', args.active));
        }
        """,
        {"anchor": anchor_addr, "active": active_addr},
    )


def _press(page, key, ctrl=False, shift=False):
    parts = []
    if ctrl:
        parts.append("Control")
    if shift:
        parts.append("Shift")
    parts.append(key)
    page.keyboard.press("+".join(parts))


def _cell_text(page, addr):
    return page.evaluate(
        """
        (addr) => {
          var el = document.querySelector('[data-fc-addr="' + addr + '"]');
          if (!el) return null;
          var input = el.querySelector('input, select, textarea');
          if (input) return input.value;
          return el.textContent.trim();
        }
        """,
        addr,
    )


def _get_selection(page):
    return page.evaluate("window.FcSelectionManager.getSelection()")


def _active_addr(page):
    return page.evaluate(
        """
        (() => {
          var a = window.FcActiveCellManager.getActiveCell();
          return a ? a.cell.addr : null;
        })()
        """
    )


class TestFillControllerJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcFillController") == "object"
        assert not page_errors

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcFillController.init()")
        second = page.evaluate("window.FcFillController.init()")
        assert first is False
        assert second is False
        assert not page_errors

    def test_fill_down_from_top_row(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _select_range(page, "fixture.r1.c1", "fixture.r3.c1")

        result = page.evaluate("window.FcFillController.fillDown()")
        assert result is True
        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert _cell_text(page, "fixture.r2.c1") == "11"
        assert _cell_text(page, "fixture.r3.c1") == "11"
        # Untouched neighbour column.
        assert _cell_text(page, "fixture.r2.c2") == "22"

    def test_fill_right_from_left_column(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _select_range(page, "fixture.r1.c1", "fixture.r1.c3")

        result = page.evaluate("window.FcFillController.fillRight()")
        assert result is True
        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert _cell_text(page, "fixture.r1.c2") == "11"
        assert _cell_text(page, "fixture.r1.c3") == "11"
        # Untouched neighbour row.
        assert _cell_text(page, "fixture.r2.c1") == "21"

    def test_single_cell_selection_noops_safely(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")

        result_down = page.evaluate("window.FcFillController.fillDown()")
        result_right = page.evaluate("window.FcFillController.fillRight()")
        assert result_down is False
        assert result_right is False
        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert _cell_text(page, "fixture.r2.c1") == "21"
        assert not page_errors

    def test_non_editable_cells_are_skipped(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r3.c1")
        _select_range(page, "fixture.r3.c1", "fixture.r3.label")

        result = page.evaluate("window.FcFillController.fillRight()")
        assert result is True
        assert _cell_text(page, "fixture.r3.c2") == "31"
        # The non-editable label cell must remain untouched.
        assert _cell_text(page, "fixture.r3.label") == "label"
        assert not page_errors

    def test_fill_clips_safely_at_bounds(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _select_range(page, "fixture.r1.c1", "fixture.r3.label")

        result_down = page.evaluate("window.FcFillController.fillDown()")
        assert result_down is True
        # c3 column: r1.c3 source fills into r2.c3, but r3's third
        # column is the non-editable label cell — clipped/skipped safely.
        assert _cell_text(page, "fixture.r2.c3") == "13"
        assert _cell_text(page, "fixture.r3.label") == "label"
        assert not page_errors

    def test_fill_records_one_undo_transaction(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _select_range(page, "fixture.r1.c1", "fixture.r3.c1")
        page.evaluate("window.FcFillController.fillDown()")

        assert page.evaluate("window.FcUndoManager.canUndo()") is True
        page.evaluate("window.FcUndoManager.undo()")
        # One undo restores every filled cell at once.
        assert _cell_text(page, "fixture.r2.c1") == "21"
        assert _cell_text(page, "fixture.r3.c1") == "31"
        assert page.evaluate("window.FcUndoManager.canUndo()") is False

    def test_undo_restores_previous_values(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _select_range(page, "fixture.r1.c1", "fixture.r3.c1")
        page.evaluate("window.FcFillController.fillDown()")

        result = page.evaluate("window.FcUndoManager.undo()")
        assert result is True
        assert _cell_text(page, "fixture.r2.c1") == "21"
        assert _cell_text(page, "fixture.r3.c1") == "31"

    def test_redo_restores_filled_values(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _select_range(page, "fixture.r1.c1", "fixture.r3.c1")
        page.evaluate("window.FcFillController.fillDown()")
        page.evaluate("window.FcUndoManager.undo()")

        result = page.evaluate("window.FcUndoManager.redo()")
        assert result is True
        assert _cell_text(page, "fixture.r2.c1") == "11"
        assert _cell_text(page, "fixture.r3.c1") == "11"

    def test_selection_remains_stable_after_fill(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _select_range(page, "fixture.r1.c1", "fixture.r3.c1")

        sel_before = _get_selection(page)
        active_before = _active_addr(page)

        page.evaluate("window.FcFillController.fillDown()")

        sel_after = _get_selection(page)
        active_after = _active_addr(page)

        assert sel_after["anchorAddr"] == sel_before["anchorAddr"]
        assert sel_after["activeAddr"] == sel_before["activeAddr"]
        assert sorted(sel_after["addresses"]) == sorted(sel_before["addresses"])
        assert active_after == active_before

    def test_ctrl_d_and_ctrl_r_scoped_to_registered_grid_cell(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _select_range(page, "fixture.r1.c1", "fixture.r3.c1")

        _press(page, "d", ctrl=True)
        assert _cell_text(page, "fixture.r2.c1") == "11"
        assert _cell_text(page, "fixture.r3.c1") == "11"
        assert not page_errors

    def test_ctrl_d_does_not_hijack_normal_input(self, fixture_page):
        page, page_errors = fixture_page
        page.evaluate(
            """
            () => {
              var el = document.querySelector('#outside-input');
              el.value = 'hello';
              el.focus();
            }
            """
        )
        _press(page, "d", ctrl=True)

        # No grid cell was active/focused, so nothing in the grid changes
        # and no fill transaction should have been recorded.
        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert page.evaluate("window.FcUndoManager.canUndo()") is False
        assert not page_errors

    def test_ctrl_r_does_not_hijack_normal_input(self, fixture_page):
        page, page_errors = fixture_page
        page.evaluate(
            """
            () => {
              var el = document.querySelector('#outside-input');
              el.value = 'hello';
              el.focus();
            }
            """
        )
        _press(page, "r", ctrl=True)

        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert page.evaluate("window.FcUndoManager.canUndo()") is False
        assert not page_errors

    def test_keyboard_navigation_still_works(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _press(page, "ArrowRight")
        assert _active_addr(page) == "fixture.r1.c2"

    def test_selection_click_still_works(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r2.c2")
        sel = _get_selection(page)
        assert sel["anchorAddr"] == sel["activeAddr"] == "fixture.r2.c2"

    def test_copy_paste_still_works(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r2.c2")
        tsv = page.evaluate("window.FcClipboardController.copySelection()")
        assert tsv == "22"

    def test_paste_undo_still_works(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('zz')")
        assert _cell_text(page, "fixture.r1.c1") == "zz"

        page.evaluate("window.FcUndoManager.undo()")
        assert _cell_text(page, "fixture.r1.c1") == "11"
