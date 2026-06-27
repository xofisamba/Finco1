"""C1-PR8: Spreadsheet Interaction Layer — Undo/Redo Foundation,
JS-execution tests.

Covers, per the C1-PR8 task spec (undo/redo foundation only):
  1. UndoManager initializes idempotently.
  2. Paste creates one transaction (not one per cell).
  3. Undo restores all previous values after paste.
  4. Redo restores pasted values.
  5. Active cell and selection restore consistently after undo/redo.
  6. Ctrl+Z triggers undo only inside registered grid cells.
  7. Ctrl+Y and Ctrl+Shift+Z trigger redo only inside registered grid
     cells.
  8. Normal text input undo is not hijacked.
  9. Undo/redo no-op safely if cells disappear.
  10. Existing PR1-PR7 behaviour (keyboard nav, selection, copy/paste,
      HTMX swap restore) remains unaffected.

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented in tests/test_c1_pr7_clipboard_controller_browser.py.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_undo_redo_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR8 JS tests",
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


def _simulate_swap(page, grid_selector, new_inner_html_js_expr, target_selector=None):
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


class TestUndoManagerJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcUndoManager") == "object"
        assert not page_errors

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcUndoManager.init()")
        second = page.evaluate("window.FcUndoManager.init()")
        assert first is False
        assert second is False
        assert not page_errors

    def test_paste_creates_one_transaction_not_one_per_cell(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('a\\tb\\nc\\td')")

        assert page.evaluate("window.FcUndoManager.canUndo()") is True
        # Undoing once must restore every pasted cell — proving it was
        # recorded as a single transaction, not four separate ones.
        page.evaluate("window.FcUndoManager.undo()")
        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert _cell_text(page, "fixture.r1.c2") == "12"
        assert _cell_text(page, "fixture.r2.c1") == "21"
        assert _cell_text(page, "fixture.r2.c2") == "22"
        # A single further undo (none left) must be a no-op.
        assert page.evaluate("window.FcUndoManager.canUndo()") is False

    def test_undo_restores_previous_values_after_paste(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('a\\tb\\nc\\td')")

        result = page.evaluate("window.FcUndoManager.undo()")
        assert result is True
        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert _cell_text(page, "fixture.r1.c2") == "12"
        assert _cell_text(page, "fixture.r2.c1") == "21"
        assert _cell_text(page, "fixture.r2.c2") == "22"

    def test_redo_restores_pasted_values(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('a\\tb\\nc\\td')")
        page.evaluate("window.FcUndoManager.undo()")

        result = page.evaluate("window.FcUndoManager.redo()")
        assert result is True
        assert _cell_text(page, "fixture.r1.c1") == "a"
        assert _cell_text(page, "fixture.r1.c2") == "b"
        assert _cell_text(page, "fixture.r2.c1") == "c"
        assert _cell_text(page, "fixture.r2.c2") == "d"

    def test_active_cell_and_selection_restore_after_undo_redo(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('a\\tb\\nc\\td')")

        page.evaluate("window.FcUndoManager.undo()")
        assert _active_addr(page) == "fixture.r1.c1"
        sel = _get_selection(page)
        assert sel["activeAddr"] == "fixture.r1.c1"

        page.evaluate("window.FcUndoManager.redo()")
        assert _active_addr(page) == "fixture.r1.c1"
        sel2 = _get_selection(page)
        assert sel2["activeAddr"] == "fixture.r1.c1"
        assert sorted(sel2["addresses"]) == sorted(
            ["fixture.r1.c1", "fixture.r1.c2", "fixture.r2.c1", "fixture.r2.c2"]
        )

    def test_cell_edit_via_real_input_is_undoable(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r3.c1")
        page.evaluate(
            """
            () => {
              var input = document.querySelector('[data-fc-addr="fixture.r3.c1"] input');
              input.focus();
              input.value = '99';
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """
        )
        assert _cell_text(page, "fixture.r3.c1") == "99"
        assert page.evaluate("window.FcUndoManager.canUndo()") is True

        page.evaluate("window.FcUndoManager.undo()")
        assert _cell_text(page, "fixture.r3.c1") == "31"
        assert not page_errors

    def test_ctrl_z_triggers_undo_only_inside_registered_grid_cell(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('zz')")
        assert _cell_text(page, "fixture.r1.c1") == "zz"

        _press(page, "z", ctrl=True)
        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert not page_errors

    def test_ctrl_y_and_ctrl_shift_z_trigger_redo_only_inside_registered_grid_cell(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('zz')")
        _press(page, "z", ctrl=True)
        assert _cell_text(page, "fixture.r1.c1") == "11"

        _press(page, "y", ctrl=True)
        assert _cell_text(page, "fixture.r1.c1") == "zz"

        _press(page, "z", ctrl=True)
        assert _cell_text(page, "fixture.r1.c1") == "11"

        _press(page, "z", ctrl=True, shift=True)
        assert _cell_text(page, "fixture.r1.c1") == "zz"
        assert not page_errors

    def test_normal_text_input_undo_is_not_hijacked(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('zz')")

        page.evaluate(
            """
            () => {
              var el = document.querySelector('#outside-input');
              el.value = 'hello';
              el.focus();
            }
            """
        )
        _press(page, "z", ctrl=True)

        # Our handler must not have claimed the key inside the outside
        # input: the pasted grid value remains untouched (no undo fired).
        assert _cell_text(page, "fixture.r1.c1") == "zz"
        assert not page_errors

    def test_undo_redo_noop_safely_if_cells_disappear(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('a\\tb\\nc\\td')")

        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            """
            grid.innerHTML = '<tbody><tr data-fc-row>' +
              '<td data-fc-cell data-fc-addr="fixture.rX.c1" data-fc-editable="true">x</td>' +
              '</tr></tbody>';
            """,
            "document.querySelector('[data-fc-grid=\"fixture-grid\"]')",
        )

        result = page.evaluate("window.FcUndoManager.undo()")
        assert result is True  # transaction popped, but no cell resolved to write
        assert page.evaluate(
            """
            (() => {
              var el = document.querySelector('[data-fc-addr="fixture.rX.c1"]');
              return el ? el.textContent.trim() : null;
            })()
            """
        ) == "x"
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

    def test_htmx_swap_restore_still_works(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")

        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            "grid.outerHTML = grid.outerHTML;",
            "document.querySelector('[data-fc-grid=\"fixture-grid\"]')",
        )

        assert _active_addr(page) == "fixture.r1.c1"
        sel = _get_selection(page)
        assert sel["activeAddr"] == "fixture.r1.c1"
        assert not page_errors
