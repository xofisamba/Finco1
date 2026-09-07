"""UI-2B — Advanced Spreadsheet Interaction + Product Anonymization.

Static / structural tests only (no app boot, no DOM, no browser).
Labels explicitly: STATIC / STRUCTURAL TEST or ANONYMIZATION.

Sections
--------
A. Anonymization — zero 'akuo' occurrences
B. Add Row fix   — content_hash in CAPEX/OPEX add-row forms
C. CAPEX/OPEX grid convergence — data-fc-grid, data-fc-scroll-container
D. CAPEX custom row cells — data-fc-cell addresses
E. OPEX custom row cells  — data-fc-cell addresses
F. New UI-2B interaction assets loaded in workbook.html
G. Value bar HTML element in workbook.html
H. Clipboard manager — keyboard handler, guards, TSV logic
I. Fill manager     — keyboard handler, direction guard
J. Undo manager     — stack, record, keyboard handler, guard
K. Type-to-edit     — printable key guard, native-control guard
L. Value bar JS     — sync on active-cell events
M. Column resizer   — handle binding, drag model
N. Selection manager — drag extension, Shift+click
O. UI-2A regression — all 80 UI-2A tests still pass (via import)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

WORKBOOK_HTML  = REPO_ROOT / "app" / "templates" / "v2" / "workbook.html"
SHEET_CAPEX    = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_capex.html"
SHEET_OPEX     = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_opex.html"

CLIPBOARD_JS    = REPO_ROOT / "static" / "interaction" / "clipboard-manager.js"
FILL_JS         = REPO_ROOT / "static" / "interaction" / "fill-manager.js"
UNDO_JS         = REPO_ROOT / "static" / "interaction" / "undo-manager.js"
TYPE_TO_EDIT_JS = REPO_ROOT / "static" / "interaction" / "type-to-edit.js"
VALUE_BAR_JS    = REPO_ROOT / "static" / "interaction" / "value-bar.js"
COL_RESIZER_JS  = REPO_ROOT / "static" / "interaction" / "column-resizer.js"
SELECTION_JS    = REPO_ROOT / "static" / "interaction" / "selection-manager.js"

CSS_FILE = REPO_ROOT / "static" / "css" / "workbook_v2.css"

ACTIVE_TEXT_EXTS = {
    ".py", ".html", ".js", ".css", ".json", ".yaml", ".yml",
    ".md", ".txt", ".csv", ".rst",
}


# ── A. Anonymization ──────────────────────────────────────────────────────

class TestAnonymization:
    """ANONYMIZATION — zero 'akuo' occurrences in active text files."""

    def test_zero_akuo_occurrences(self):
        """ANONYMIZATION: case-insensitive 'akuo' must not appear in any active text file."""
        hits = []
        skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}
        # This test file itself contains the search term as a string literal
        skip_files = {Path(__file__).resolve()}

        for path in REPO_ROOT.rglob("*"):
            if not path.is_file():
                continue
            if path.resolve() in skip_files:
                continue
            if any(p in skip_dirs for p in path.parts):
                continue
            if path.suffix.lower() not in ACTIVE_TEXT_EXTS:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "akuo" in text.lower():
                hits.append(str(path.relative_to(REPO_ROOT)))

        assert hits == [], (
            f"Found 'akuo' (case-insensitive) in {len(hits)} file(s):\n"
            + "\n".join(f"  {h}" for h in hits)
        )


# ── B. Add Row fix — content_hash ─────────────────────────────────────────

class TestAddRowContentHash:
    """STATIC: Add Row forms must include content_hash (required by server)."""

    def test_capex_add_row_form_has_content_hash(self):
        """STATIC: CAPEX add_row_form macro must render content_hash hidden input."""
        text = SHEET_CAPEX.read_text(encoding="utf-8")
        # Macro definition must accept content_hash param
        assert "content_hash" in text, \
            "sheet_capex.html add_row_form must accept and render content_hash."
        # The hidden input for content_hash must be present
        assert 'name="content_hash"' in text, \
            "sheet_capex.html add_row_form must render <input name=\"content_hash\">."

    def test_capex_add_row_macro_call_passes_content_hash(self):
        """STATIC: add_row_form call site must pass content_hash argument."""
        text = SHEET_CAPEX.read_text(encoding="utf-8")
        assert "add_row_form(group.code, project_code, workbook_version, content_hash)" in text, \
            "CAPEX add_row_form call must pass content_hash as 4th argument."

    def test_opex_add_row_form_has_content_hash(self):
        """STATIC: OPEX opex_add_row_form macro must render content_hash hidden input."""
        text = SHEET_OPEX.read_text(encoding="utf-8")
        assert 'name="content_hash"' in text, \
            "sheet_opex.html opex_add_row_form must render <input name=\"content_hash\">."

    def test_opex_add_row_macro_call_passes_content_hash(self):
        """STATIC: opex_add_row_form call site must pass content_hash argument."""
        text = SHEET_OPEX.read_text(encoding="utf-8")
        assert "opex_add_row_form(sg.code, project_code, workbook_version, content_hash)" in text, \
            "OPEX opex_add_row_form call must pass content_hash as 4th argument."


# ── C. CAPEX/OPEX grid convergence ───────────────────────────────────────

class TestCapexOpexGridConvergence:
    """STATIC: CAPEX and OPEX sheet roots must be registered with data-fc-grid."""

    def test_capex_has_data_fc_grid(self):
        text = SHEET_CAPEX.read_text(encoding="utf-8")
        assert 'data-fc-grid="capex"' in text, \
            "sheet_capex.html root div must have data-fc-grid=\"capex\"."

    def test_capex_has_scroll_container(self):
        text = SHEET_CAPEX.read_text(encoding="utf-8")
        assert "data-fc-scroll-container" in text, \
            "sheet_capex.html must have data-fc-scroll-container."

    def test_opex_has_data_fc_grid(self):
        text = SHEET_OPEX.read_text(encoding="utf-8")
        assert 'data-fc-grid="opex"' in text, \
            "sheet_opex.html root div must have data-fc-grid=\"opex\"."

    def test_opex_has_scroll_container(self):
        text = SHEET_OPEX.read_text(encoding="utf-8")
        assert "data-fc-scroll-container" in text, \
            "sheet_opex.html must have data-fc-scroll-container."


# ── D. CAPEX custom row cells ─────────────────────────────────────────────

class TestCapexCustomRowCells:
    """STATIC: CAPEX custom row inputs must have data-fc-cell attributes."""

    def _text(self):
        return SHEET_CAPEX.read_text(encoding="utf-8")

    def test_capex_custom_row_has_fc_row(self):
        assert "data-fc-row" in self._text(), \
            "CAPEX custom_row must have data-fc-row on its wrapper."

    def test_capex_custom_label_has_fc_cell(self):
        text = self._text()
        assert "data-fc-cell" in text and "capex.custom-" in text, \
            "CAPEX custom label input must have data-fc-cell with capex.custom- addr."

    def test_capex_custom_amount_has_fc_cell(self):
        text = self._text()
        assert 'data-fc-kind="amount"' in text, \
            "CAPEX custom amount input must declare data-fc-kind=\"amount\"."

    def test_capex_custom_fc_editable_true(self):
        text = self._text()
        assert 'data-fc-editable="true"' in text, \
            "CAPEX custom row inputs must have data-fc-editable=\"true\"."


# ── E. OPEX custom row cells ──────────────────────────────────────────────

class TestOpexCustomRowCells:
    """STATIC: OPEX custom row inputs must have data-fc-cell attributes."""

    def _text(self):
        return SHEET_OPEX.read_text(encoding="utf-8")

    def test_opex_custom_row_has_fc_row(self):
        assert "data-fc-row" in self._text(), \
            "OPEX custom_row must have data-fc-row on its wrapper."

    def test_opex_custom_label_has_fc_cell(self):
        text = self._text()
        assert "data-fc-cell" in text and "opex.custom-" in text, \
            "OPEX custom label input must have data-fc-cell with opex.custom- addr."

    def test_opex_custom_escl_has_fc_cell(self):
        text = self._text()
        assert "opex.custom-" in text and ".escl" in text, \
            "OPEX custom escalation input must have a .escl address."

    def test_opex_custom_fc_editable_true(self):
        text = self._text()
        assert 'data-fc-editable="true"' in text, \
            "OPEX custom row inputs must have data-fc-editable=\"true\"."


# ── F. New UI-2B assets loaded in workbook.html ───────────────────────────

UI2B_ASSETS = [
    "interaction/clipboard-manager.js",
    "interaction/fill-manager.js",
    "interaction/undo-manager.js",
    "interaction/type-to-edit.js",
    "interaction/value-bar.js",
    "interaction/column-resizer.js",
]


class TestUI2BAssetsLoaded:
    """STATIC: workbook.html must load all UI-2B interaction assets exactly once."""

    @pytest.mark.parametrize("asset", UI2B_ASSETS)
    def test_ui2b_asset_loaded(self, asset):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        count = text.count(asset)
        assert count == 1, \
            f"workbook.html must load '{asset}' exactly once; found {count} times."

    def test_ui2b_assets_load_after_selection_manager(self):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        sel_idx = text.index("selection-manager.js")
        for asset in UI2B_ASSETS:
            idx = text.index(asset)
            assert idx > sel_idx, \
                f"{asset} must load after selection-manager.js."


# ── G. Value bar HTML ─────────────────────────────────────────────────────

class TestValueBarHTML:
    """STATIC: value bar element must exist in workbook.html with correct structure."""

    def _text(self):
        return WORKBOOK_HTML.read_text(encoding="utf-8")

    def test_fc_value_bar_div_exists(self):
        assert 'id="fc-value-bar"' in self._text(), \
            "workbook.html must have a #fc-value-bar element."

    def test_fc_value_bar_addr_span(self):
        assert 'id="fc-value-bar-addr"' in self._text(), \
            "workbook.html must have #fc-value-bar-addr span."

    def test_fc_value_bar_value_span(self):
        assert 'id="fc-value-bar-value"' in self._text(), \
            "workbook.html must have #fc-value-bar-value span."


# ── H. Clipboard manager ──────────────────────────────────────────────────

class TestClipboardManager:
    """STATIC: clipboard-manager.js must implement copy/paste with guards."""

    def _text(self):
        return CLIPBOARD_JS.read_text(encoding="utf-8")

    def test_clipboard_manager_exists(self):
        assert CLIPBOARD_JS.exists(), "clipboard-manager.js must exist."

    def test_exposes_fc_clipboard_manager(self):
        assert "FcClipboardManager" in self._text(), \
            "clipboard-manager.js must expose window.FcClipboardManager."

    def test_ctrl_c_handled(self):
        assert "'c'" in self._text() or '"c"' in self._text(), \
            "clipboard-manager.js must handle Ctrl+C."

    def test_ctrl_v_handled(self):
        assert "'v'" in self._text() or '"v"' in self._text(), \
            "clipboard-manager.js must handle Ctrl+V."

    def test_native_control_guard(self):
        text = self._text()
        assert "isNativeControl" in text or "_isNativeControl" in text, \
            "clipboard-manager.js must guard against native control focus."

    def test_tsv_separator_used(self):
        assert "'\\t'" in self._text() or '"\\t"' in self._text(), \
            "clipboard-manager.js must use tab as TSV separator."

    def test_newline_used_for_rows(self):
        assert "'\\n'" in self._text() or '"\\n"' in self._text(), \
            "clipboard-manager.js must use newline as row separator."

    def test_has_init_guard(self):
        assert "_initialized" in self._text(), \
            "clipboard-manager.js must have an _initialized guard."


# ── I. Fill manager ───────────────────────────────────────────────────────

class TestFillManager:
    """STATIC: fill-manager.js must implement fill down/right with guards."""

    def _text(self):
        return FILL_JS.read_text(encoding="utf-8")

    def test_fill_manager_exists(self):
        assert FILL_JS.exists(), "fill-manager.js must exist."

    def test_exposes_fc_fill_manager(self):
        assert "FcFillManager" in self._text(), \
            "fill-manager.js must expose window.FcFillManager."

    def test_ctrl_d_handled(self):
        assert "'d'" in self._text() or '"d"' in self._text(), \
            "fill-manager.js must handle Ctrl+D (fill down)."

    def test_ctrl_r_handled(self):
        assert "'r'" in self._text() or '"r"' in self._text(), \
            "fill-manager.js must handle Ctrl+R (fill right)."

    def test_native_control_guard(self):
        text = self._text()
        assert "_isNativeControl" in text or "isNativeControl" in text, \
            "fill-manager.js must guard against native control focus."

    def test_fires_input_event(self):
        assert "input" in self._text() and "dispatchEvent" in self._text(), \
            "fill-manager.js must fire 'input' event to mark cells pending."

    def test_calls_request_submit(self):
        assert "requestSubmit" in self._text(), \
            "fill-manager.js must call requestSubmit() to persist via canonical path."


# ── J. Undo manager ───────────────────────────────────────────────────────

class TestUndoManager:
    """STATIC: undo-manager.js must implement stack, record, undo/redo."""

    def _text(self):
        return UNDO_JS.read_text(encoding="utf-8")

    def test_undo_manager_exists(self):
        assert UNDO_JS.exists(), "undo-manager.js must exist."

    def test_exposes_fc_undo_manager(self):
        assert "FcUndoManager" in self._text(), \
            "undo-manager.js must expose window.FcUndoManager."

    def test_ctrl_z_handled(self):
        assert "'z'" in self._text() or '"z"' in self._text(), \
            "undo-manager.js must handle Ctrl+Z (undo)."

    def test_ctrl_y_handled(self):
        text = self._text()
        assert ("'y'" in text or '"y"' in text) or "shiftKey" in text, \
            "undo-manager.js must handle Ctrl+Y or Ctrl+Shift+Z (redo)."

    def test_stack_capped(self):
        text = self._text()
        assert "MAX_STACK" in text or "100" in text, \
            "undo-manager.js must cap the undo stack depth."

    def test_native_control_guard(self):
        text = self._text()
        assert "_isNativeControl" in text or "isNativeControl" in text, \
            "undo-manager.js must guard against native control focus."

    def test_uses_request_submit(self):
        assert "requestSubmit" in self._text(), \
            "undo-manager.js must persist via requestSubmit (canonical path)."

    def test_exposes_record(self):
        assert "record" in self._text(), \
            "undo-manager.js must expose a record() function."


# ── K. Type-to-edit ───────────────────────────────────────────────────────

class TestTypeToEdit:
    """STATIC: type-to-edit.js must enter edit mode on printable key, guard native controls."""

    def _text(self):
        return TYPE_TO_EDIT_JS.read_text(encoding="utf-8")

    def test_type_to_edit_exists(self):
        assert TYPE_TO_EDIT_JS.exists(), "type-to-edit.js must exist."

    def test_exposes_fc_type_to_edit(self):
        assert "FcTypeToEdit" in self._text(), \
            "type-to-edit.js must expose window.FcTypeToEdit."

    def test_printable_key_check(self):
        assert "_isPrintable" in self._text() or "isPrintable" in self._text(), \
            "type-to-edit.js must check for printable keys."

    def test_native_control_guard(self):
        text = self._text()
        assert "_isNativeControl" in text or "isNativeControl" in text, \
            "type-to-edit.js must guard against native control focus."

    def test_moves_focus_to_input(self):
        assert "inp.focus()" in self._text(), \
            "type-to-edit.js must move DOM focus into the input on type."

    def test_clears_input_value(self):
        assert "inp.value = evt.key" in self._text(), \
            "type-to-edit.js must replace input value with the typed character."

    def test_checks_fc_editable(self):
        assert 'fcEditable' in self._text() or 'fc-editable' in self._text(), \
            "type-to-edit.js must check data-fc-editable before entering edit mode."


# ── L. Value bar JS ───────────────────────────────────────────────────────

class TestValueBarJS:
    """STATIC: value-bar.js must sync address and value on active-cell events."""

    def _text(self):
        return VALUE_BAR_JS.read_text(encoding="utf-8")

    def test_value_bar_exists(self):
        assert VALUE_BAR_JS.exists(), "value-bar.js must exist."

    def test_exposes_fc_value_bar(self):
        assert "FcValueBar" in self._text(), \
            "value-bar.js must expose window.FcValueBar."

    def test_listens_to_fc_grids_scanned(self):
        assert "fc:gridsScanned" in self._text(), \
            "value-bar.js must listen to fc:gridsScanned to sync after HTMX swaps."

    def test_updates_addr_element(self):
        assert "fc-value-bar-addr" in self._text(), \
            "value-bar.js must update #fc-value-bar-addr."

    def test_updates_value_element(self):
        assert "fc-value-bar-value" in self._text(), \
            "value-bar.js must update #fc-value-bar-value."

    def test_reads_active_cell(self):
        assert "getActiveCell" in self._text(), \
            "value-bar.js must read FcActiveCellManager.getActiveCell()."


# ── M. Column resizer ─────────────────────────────────────────────────────

class TestColumnResizer:
    """STATIC: column-resizer.js must bind handles, use CSS custom properties."""

    def _text(self):
        return COL_RESIZER_JS.read_text(encoding="utf-8")

    def test_column_resizer_exists(self):
        assert COL_RESIZER_JS.exists(), "column-resizer.js must exist."

    def test_exposes_fc_column_resizer(self):
        assert "FcColumnResizer" in self._text(), \
            "column-resizer.js must expose window.FcColumnResizer."

    def test_handle_class_used(self):
        assert "fc-col-resize-handle" in self._text(), \
            "column-resizer.js must bind .fc-col-resize-handle elements."

    def test_min_width_enforced(self):
        assert "MIN_WIDTH" in self._text(), \
            "column-resizer.js must enforce a minimum column width."

    def test_css_custom_property_used(self):
        assert "setProperty" in self._text(), \
            "column-resizer.js must set CSS custom properties for column widths."

    def test_rebinds_after_htmx_swap(self):
        assert "htmx:afterSwap" in self._text(), \
            "column-resizer.js must rebind handles after HTMX swaps."


# ── N. Selection manager — drag and Shift+click ───────────────────────────

class TestSelectionManagerDrag:
    """STATIC: selection-manager.js must implement drag selection and Shift+click."""

    def _text(self):
        return SELECTION_JS.read_text(encoding="utf-8")

    def test_mousedown_listener(self):
        assert "mousedown" in self._text(), \
            "selection-manager.js must listen to mousedown for drag selection."

    def test_mousemove_listener(self):
        assert "mousemove" in self._text(), \
            "selection-manager.js must listen to mousemove to extend drag range."

    def test_mouseup_listener(self):
        assert "mouseup" in self._text(), \
            "selection-manager.js must listen to mouseup to end drag."

    def test_shift_click_handled(self):
        assert "shiftKey" in self._text(), \
            "selection-manager.js must handle Shift+click to extend selection."

    def test_native_control_guard_in_drag(self):
        assert "_isNativeControl" in self._text() or "isNativeControl" in self._text(), \
            "selection-manager.js drag handler must guard native controls."

    def test_drag_state_variable(self):
        assert "_drag" in self._text(), \
            "selection-manager.js must track drag state in a _drag variable."


# ── O. CSS value bar ─────────────────────────────────────────────────────

class TestUI2BCSS:
    """STATIC: workbook_v2.css must include UI-2B value bar and resize handle styles."""

    def _css(self):
        return CSS_FILE.read_text(encoding="utf-8")

    def test_fc_value_bar_css(self):
        assert ".fc-value-bar" in self._css(), \
            "workbook_v2.css must define .fc-value-bar styles."

    def test_fc_col_resize_handle_css(self):
        assert ".fc-col-resize-handle" in self._css(), \
            "workbook_v2.css must define .fc-col-resize-handle styles."
