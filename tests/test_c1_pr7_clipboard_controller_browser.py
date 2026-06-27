"""C1-PR7: Spreadsheet Interaction Layer — Clipboard Foundation,
JS-execution tests.

Covers, per the C1-PR7 task spec (clipboard foundation only):
  Copy:
    1. Single cell copies correctly.
    2. Range copies correctly.
    3. TSV format is Excel-compatible (tab columns, newline rows).
    4. Clipboard contains the expected payload.
  Paste:
    5. Single value pastes correctly.
    6. Multi-cell TSV pastes correctly.
    7. Selection updates after paste.
    8. Active cell updates after paste (top-left of pasted region).
    9. Oversized paste clips safely (no throw, no corruption).
    10. Empty clipboard no-ops safely.
  Integration:
    11. Keyboard navigation still works.
    12. Selection (click) still works.
    13. HTMX swap restore still works (PR3/PR6 behaviour unaffected).
    14. Ctrl+C/Ctrl+V are scoped to grid cells only (no hijack of a
        normal text input).

These tests run against a standalone static fixture
(tests/fixtures/c1_clipboard_controller_fixture.html) via Playwright,
not the real Finco1 app, and are skipped if Playwright/Chromium are
unavailable — mirroring the pattern in
tests/test_c1_pr6_selection_manager_browser.py.

Real OS/browser clipboard reads (navigator.clipboard.readText) are
permission-gated and flaky under headless automation, so paste
assertions exercise FcClipboardController.pasteText() directly (the
same code path the Ctrl+V handler falls back to) rather than depending
on clipboard permissions being granted. Ctrl+C is exercised via a real
keypress, since copySelection() always updates the in-memory fallback
cache synchronously regardless of clipboard permissions.

This module deliberately does NOT import main_web (or anything that
imports it), for the same asyncio/Playwright-sync-API reason
documented there.
"""
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "c1_clipboard_controller_fixture.html")

_FALLBACK_CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run C1-PR7 JS tests",
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
    parts.append(key)
    page.keyboard.press("+".join(parts))


def _cell_text(page, addr):
    return page.evaluate(
        """
        (addr) => {
          var el = document.querySelector('[data-fc-addr="' + addr + '"]');
          return el ? el.textContent.trim() : null;
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


class TestClipboardControllerJs:
    def test_manager_loads_without_errors(self, fixture_page):
        page, page_errors = fixture_page
        assert page.evaluate("typeof window.FcClipboardController") == "object"
        assert not page_errors

    def test_single_cell_copies_correctly(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r2.c2")

        tsv = page.evaluate("window.FcClipboardController.copySelection()")
        assert tsv == "22"
        assert page.evaluate("window.FcClipboardController.getLastCopiedText()") == "22"

    def test_range_copies_correctly_as_excel_compatible_tsv(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        _press(page, "ArrowRight", ctrl=False)
        _press(page, "ArrowDown", ctrl=False)
        page.evaluate(
            """
            window.FcSelectionManager.selectSingle(
              'fixture-grid', window.FcGridRegistry.getAddr('fixture-grid', 'fixture.r1.c1'));
            window.FcSelectionManager.extendTo('fixture-grid',
              window.FcGridRegistry.getAddr('fixture-grid', 'fixture.r2.c2'));
            """
        )
        # Selection now spans fixture.r1.c1 .. fixture.r2.c2 (anchor r1.c1).
        tsv = page.evaluate("window.FcClipboardController.copySelection()")
        assert tsv == "11\t12\n21\t22"

        rows = tsv.split("\n")
        assert len(rows) == 2
        assert all("\t" in row for row in rows)

    def test_clipboard_contains_expected_payload_after_copy(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r3.c1")
        page.evaluate("window.FcClipboardController.copySelection()")
        assert page.evaluate("window.FcClipboardController.getLastCopiedText()") == "31"

    def test_single_value_pastes_correctly(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c2")

        result = page.evaluate("window.FcClipboardController.pasteText('99')")
        assert result is True
        assert _cell_text(page, "fixture.r1.c2") == "99"

    def test_multi_cell_tsv_pastes_correctly(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")

        result = page.evaluate("window.FcClipboardController.pasteText('a\\tb\\nc\\td')")
        assert result is True
        assert _cell_text(page, "fixture.r1.c1") == "a"
        assert _cell_text(page, "fixture.r1.c2") == "b"
        assert _cell_text(page, "fixture.r2.c1") == "c"
        assert _cell_text(page, "fixture.r2.c2") == "d"
        # Untouched neighbour.
        assert _cell_text(page, "fixture.r1.c3") == "13"

    def test_selection_and_active_cell_update_after_paste(self, fixture_page):
        page, _ = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.pasteText('a\\tb\\nc\\td')")

        assert _active_addr(page) == "fixture.r1.c1"

        sel = _get_selection(page)
        assert sel["gridId"] == "fixture-grid"
        assert sorted(sel["addresses"]) == sorted(
            ["fixture.r1.c1", "fixture.r1.c2", "fixture.r2.c1", "fixture.r2.c2"]
        )

    def test_oversized_paste_clips_safely(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r2.c2")

        huge_tsv = "\n".join(
            "\t".join("x{}-{}".format(r, c) for c in range(10)) for r in range(10)
        )
        result = page.evaluate(
            "(tsv) => window.FcClipboardController.pasteText(tsv)", huge_tsv
        )
        assert result is True
        # Only the cells that actually exist from the origin onward were
        # written; nothing outside the 3x3 grid, and no JS error.
        assert _cell_text(page, "fixture.r2.c2") == "x0-0"
        assert _cell_text(page, "fixture.r3.c2") == "x1-0"
        assert not page_errors

    def test_paste_skips_non_editable_cells_without_throwing(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r3.c1")

        result = page.evaluate(
            "window.FcClipboardController.pasteText('a\\tb\\tc')"
        )
        assert result is True
        assert _cell_text(page, "fixture.r3.c1") == "a"
        assert _cell_text(page, "fixture.r3.c2") == "b"
        # fixture.r3.label is data-fc-editable="false" — left untouched.
        assert _cell_text(page, "fixture.r3.label") == "label"
        assert not page_errors

    def test_empty_clipboard_noops_safely(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")

        result_null = page.evaluate("window.FcClipboardController.pasteText(null)")
        result_empty = page.evaluate("window.FcClipboardController.pasteText('')")

        assert result_null is False
        assert result_empty is False
        assert _cell_text(page, "fixture.r1.c1") == "11"
        assert not page_errors

    def test_copy_with_no_selection_noops_safely(self, fixture_page):
        page, page_errors = fixture_page
        # No click yet — no active cell, no selection.
        tsv = page.evaluate("window.FcClipboardController.copySelection()")
        assert tsv is None
        assert not page_errors

    def test_ctrl_c_keypress_updates_clipboard_cache(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c3")

        _press(page, "c", ctrl=True)

        assert page.evaluate("window.FcClipboardController.getLastCopiedText()") == "13"
        assert not page_errors

    def test_ctrl_c_does_not_hijack_normal_input(self, fixture_page):
        page, page_errors = fixture_page
        page.evaluate("document.querySelector('#outside-input').value = 'hello'")
        page.evaluate("document.querySelector('#outside-input').focus()")
        page.evaluate(
            "document.querySelector('#outside-input').setSelectionRange(0, 5)"
        )

        _press(page, "c", ctrl=True)

        # Our handler must not have claimed the key: the clipboard cache
        # used by FcClipboardController stays whatever it was before
        # (null here), proving copySelection() was never invoked.
        assert page.evaluate("window.FcClipboardController.getLastCopiedText()") is None
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

    def test_htmx_swap_restore_still_works(self, fixture_page):
        page, page_errors = fixture_page
        _click_addr(page, "fixture.r1.c1")
        page.evaluate("window.FcClipboardController.copySelection()")

        _simulate_swap(
            page,
            '[data-fc-grid="fixture-grid"]',
            "grid.outerHTML = grid.outerHTML;",
            "document.querySelector('[data-fc-grid=\"fixture-grid\"]')",
        )

        assert _active_addr(page) == "fixture.r1.c1"
        sel = _get_selection(page)
        assert sel["activeAddr"] == "fixture.r1.c1"
        # Clipboard payload is independent of the selection/grid model —
        # it survives the swap untouched, exactly like a real OS clipboard.
        assert page.evaluate("window.FcClipboardController.getLastCopiedText()") == "11"
        assert not page_errors

    def test_repeated_init_is_idempotent(self, fixture_page):
        page, page_errors = fixture_page
        first = page.evaluate("window.FcClipboardController.init()")
        second = page.evaluate("window.FcClipboardController.init()")
        assert first is False
        assert second is False

        _click_addr(page, "fixture.r1.c1")
        assert page.evaluate("window.FcClipboardController.copySelection()") == "11"
        assert not page_errors
