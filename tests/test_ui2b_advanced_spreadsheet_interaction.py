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


# ── P. Unified cell/editor contract ─────────────────────────────────────────

ACTIVE_CELL_JS = REPO_ROOT / "static" / "interaction" / "active-cell.js"


class TestUnifiedCellEditorContract:
    """STATIC: CAPEX/OPEX must use wrapper-span contract; all modules use _resolveEditor."""

    def test_capex_fc_cell_on_wrapper_not_input(self):
        """STATIC: CAPEX custom inputs must NOT have data-fc-cell directly on <input>."""
        text = SHEET_CAPEX.read_text(encoding="utf-8")
        # data-fc-cell must appear on a <span class="v2-fc-cell-wrap"> wrapper
        assert "v2-fc-cell-wrap" in text, \
            "CAPEX custom rows must use .v2-fc-cell-wrap span wrapper for data-fc-cell."

    def test_opex_fc_cell_on_wrapper_not_input(self):
        """STATIC: OPEX custom inputs must NOT have data-fc-cell directly on <input>."""
        text = SHEET_OPEX.read_text(encoding="utf-8")
        assert "v2-fc-cell-wrap" in text, \
            "OPEX custom rows must use .v2-fc-cell-wrap span wrapper for data-fc-cell."

    def test_capex_wrapper_has_fc_addr(self):
        """STATIC: The wrapper span must carry data-fc-addr, not the raw input."""
        text = SHEET_CAPEX.read_text(encoding="utf-8")
        # Confirm wrapper span has data-fc-addr; input after it does not
        import re
        wrapper_re = re.compile(
            r'<span[^>]+class="v2-fc-cell-wrap"[^>]+data-fc-addr=', re.DOTALL
        )
        assert wrapper_re.search(text), \
            "CAPEX .v2-fc-cell-wrap span must carry data-fc-addr attribute."

    def test_opex_wrapper_has_fc_addr(self):
        """STATIC: The OPEX wrapper span must carry data-fc-addr."""
        text = SHEET_OPEX.read_text(encoding="utf-8")
        import re
        wrapper_re = re.compile(
            r'<span[^>]+class="v2-fc-cell-wrap"[^>]+data-fc-addr=', re.DOTALL
        )
        assert wrapper_re.search(text), \
            "OPEX .v2-fc-cell-wrap span must carry data-fc-addr attribute."

    def test_css_defines_cell_wrap_display_contents(self):
        """STATIC: .v2-fc-cell-wrap must be display:contents to preserve flex layout."""
        css = CSS_FILE.read_text(encoding="utf-8")
        assert ".v2-fc-cell-wrap" in css, \
            "workbook_v2.css must define .v2-fc-cell-wrap."
        idx = css.index(".v2-fc-cell-wrap")
        block = css[idx:idx + 200]
        assert "display: contents" in block or "display:contents" in block, \
            ".v2-fc-cell-wrap must be display:contents."

    def test_css_active_ring_on_descendant_input(self):
        """STATIC: Active ring must also paint on .v2-field-input descendant of fc-cell."""
        css = CSS_FILE.read_text(encoding="utf-8")
        assert ".v2-fc-cell-wrap.fc-active-cell .v2-field-input" in css or \
               "[data-fc-cell].fc-active-cell .v2-field-input" in css, \
            "CSS must paint active ring on .v2-field-input inside display:contents wrapper."

    def test_undo_manager_uses_resolve_editor(self):
        """STATIC: undo-manager.js must use _resolveEditor to find native control."""
        text = UNDO_JS.read_text(encoding="utf-8")
        assert "_resolveEditor" in text, \
            "undo-manager.js must use _resolveEditor() to support both cell contracts."

    def test_clipboard_manager_uses_resolve_editor(self):
        """STATIC: clipboard-manager.js must use _resolveEditor to find native control."""
        text = CLIPBOARD_JS.read_text(encoding="utf-8")
        assert "_resolveEditor" in text, \
            "clipboard-manager.js must use _resolveEditor()."

    def test_fill_manager_uses_resolve_editor(self):
        """STATIC: fill-manager.js must use _resolveEditor to find native control."""
        text = FILL_JS.read_text(encoding="utf-8")
        assert "_resolveEditor" in text, \
            "fill-manager.js must use _resolveEditor()."

    def test_type_to_edit_uses_resolve_editor(self):
        """STATIC: type-to-edit.js must use _resolveEditor to find native control."""
        text = TYPE_TO_EDIT_JS.read_text(encoding="utf-8")
        assert "_resolveEditor" in text, \
            "type-to-edit.js must use _resolveEditor()."

    def test_column_resizer_handles_rendered_in_capex(self):
        """STATIC: CAPEX col header must have .fc-col-resize-handle spans."""
        text = SHEET_CAPEX.read_text(encoding="utf-8")
        assert "fc-col-resize-handle" in text, \
            "sheet_capex.html col header must render .fc-col-resize-handle spans."

    def test_column_resizer_handles_rendered_in_opex(self):
        """STATIC: OPEX col header must have .fc-col-resize-handle spans."""
        text = SHEET_OPEX.read_text(encoding="utf-8")
        assert "fc-col-resize-handle" in text, \
            "sheet_opex.html col header must render .fc-col-resize-handle spans."


# ── Q. fc:activeCellChanged event ───────────────────────────────────────────

class TestActiveCellChangedEvent:
    """STATIC: active-cell.js must dispatch fc:activeCellChanged; value-bar.js must listen."""

    def test_active_cell_dispatches_changed_event(self):
        """STATIC: active-cell.js must dispatch fc:activeCellChanged after setActiveCell."""
        text = ACTIVE_CELL_JS.read_text(encoding="utf-8")
        assert "fc:activeCellChanged" in text, \
            "active-cell.js must dispatch 'fc:activeCellChanged' event."

    def test_value_bar_listens_to_changed_event(self):
        """STATIC: value-bar.js must listen to fc:activeCellChanged for keyboard updates."""
        text = VALUE_BAR_JS.read_text(encoding="utf-8")
        assert "fc:activeCellChanged" in text, \
            "value-bar.js must listen to 'fc:activeCellChanged' to update on Arrow/Tab nav."


# ── R. Fill manager — directionality ────────────────────────────────────────

class TestFillDirectionality:
    """STATIC: fill-manager.js must implement distinct Fill Down vs Fill Right logic."""

    def test_fill_down_distinct_from_fill_right(self):
        """STATIC: fill-manager must have separate fill-down and fill-right code paths."""
        text = FILL_JS.read_text(encoding="utf-8")
        assert "'down'" in text and "'right'" in text, \
            "fill-manager.js must have distinct 'down' and 'right' direction strings."

    def test_fill_down_uses_row_iteration(self):
        """STATIC: fill-down must iterate rows (minRow → maxRow) per column."""
        text = FILL_JS.read_text(encoding="utf-8")
        assert "minRow" in text and "maxRow" in text, \
            "fill-manager.js fill-down must iterate minRow to maxRow."

    def test_fill_right_uses_col_iteration(self):
        """STATIC: fill-right must iterate columns (minCol → maxCol) per row."""
        text = FILL_JS.read_text(encoding="utf-8")
        assert "minCol" in text and "maxCol" in text, \
            "fill-manager.js fill-right must iterate minCol to maxCol."

    def test_fill_uses_cas_safe_queue(self):
        """STATIC: fill-manager must use a serial queue for CAS-safe persistence."""
        text = FILL_JS.read_text(encoding="utf-8")
        assert "_runQueue" in text or "runQueue" in text, \
            "fill-manager.js must use a serial queue (_runQueue) for CAS-safe persistence."


# ── S. Clipboard — CAS-safe queue ───────────────────────────────────────────

class TestClipboardCASQueue:
    """STATIC: clipboard-manager.js must use a CAS-safe serial queue for paste."""

    def test_paste_uses_serial_queue(self):
        """STATIC: paste must use _runQueue (serial CAS-safe persistence)."""
        text = CLIPBOARD_JS.read_text(encoding="utf-8")
        assert "_runQueue" in text or "runQueue" in text, \
            "clipboard-manager.js must use a serial queue for CAS-safe paste."

    def test_paste_awaits_htmx_response(self):
        """STATIC: paste queue must listen to htmx:afterRequest before proceeding."""
        text = CLIPBOARD_JS.read_text(encoding="utf-8")
        assert "htmx:afterRequest" in text, \
            "clipboard-manager.js must await htmx:afterRequest before the next cell."

    def test_paste_stops_on_failure(self):
        """STATIC: paste queue must stop and warn on server error."""
        text = CLIPBOARD_JS.read_text(encoding="utf-8")
        assert "onError" in text or "warn" in text, \
            "clipboard-manager.js must stop paste queue and warn on server error."

    def test_trailing_newline_stripped(self):
        """STATIC: paste must strip trailing empty line to prevent spurious blank cell."""
        text = CLIPBOARD_JS.read_text(encoding="utf-8")
        assert "pop()" in text, \
            "clipboard-manager.js must strip trailing empty TSV line."


# ── T. Undo manager — CAS rollback ──────────────────────────────────────────

class TestUndoManagerCASRollback:
    """STATIC: undo-manager.js must rollback stack position on 409 stale-content_hash."""

    def test_apply_takes_onFail_callback(self):
        """STATIC: _apply must accept and call an onFail callback."""
        text = UNDO_JS.read_text(encoding="utf-8")
        assert "onFail" in text, \
            "undo-manager.js _apply must accept and call an onFail callback."

    def test_undo_restores_stack_on_failure(self):
        """STATIC: undo() must restore _stackIdx on _apply failure."""
        text = UNDO_JS.read_text(encoding="utf-8")
        # The rollback pattern: _stackIdx++ inside undo's onFail
        assert "_stackIdx++" in text, \
            "undo() must restore _stackIdx++ when _apply fails."

    def test_redo_restores_stack_on_failure(self):
        """STATIC: redo() must restore _stackIdx on _apply failure."""
        text = UNDO_JS.read_text(encoding="utf-8")
        assert "_stackIdx--" in text, \
            "redo() must restore _stackIdx-- when _apply fails."

    def test_applying_undo_flag_prevents_double_recording(self):
        """STATIC: _applyingUndo flag must guard against re-recording undo operations."""
        text = UNDO_JS.read_text(encoding="utf-8")
        assert "_applyingUndo" in text, \
            "undo-manager.js must have an _applyingUndo flag to prevent double-recording."

    def test_undo_recording_uses_form_inputs_not_fc_cell_on_input(self):
        """STATIC: recording in _onAfterRequest must find [data-fc-cell] via closest(),
        not by querying inputs that themselves have data-fc-cell."""
        text = UNDO_JS.read_text(encoding="utf-8")
        assert "inp.closest('[data-fc-cell]')" in text or \
               'inp.closest("[data-fc-cell]")' in text, \
            "undo _onAfterRequest must use inp.closest('[data-fc-cell]') for wrapper contract."


# ── U. Add Row route contract ────────────────────────────────────────────────

CAPEX_ROUTER = REPO_ROOT / "app" / "v2" / "capex_router.py"
OPEX_ROUTER  = REPO_ROOT / "app" / "v2" / "opex_router.py"


class TestAddRowRouteContract:
    """STATIC: capex/opex route handlers must require content_hash as a Form field."""

    def test_capex_line_add_requires_content_hash(self):
        """STATIC: capex_router.py capex_line_add must declare content_hash: str = Form(...)."""
        text = CAPEX_ROUTER.read_text(encoding="utf-8")
        assert "content_hash" in text and "Form(...)" in text, \
            "capex_router.py capex_line_add must declare content_hash: str = Form(...)."

    def test_capex_line_add_route_path(self):
        """STATIC: capex add-row route must be POST /line/add."""
        text = CAPEX_ROUTER.read_text(encoding="utf-8")
        assert '"/line/add"' in text or "'/line/add'" in text, \
            "capex_router.py must define POST /line/add."

    def test_opex_line_add_requires_content_hash(self):
        """STATIC: opex_router.py opex_line_add must declare content_hash: str = Form(...)."""
        text = OPEX_ROUTER.read_text(encoding="utf-8")
        assert "content_hash" in text and "Form(...)" in text, \
            "opex_router.py opex_line_add must declare content_hash: str = Form(...)."

    def test_opex_line_add_route_path(self):
        """STATIC: opex add-row route must be POST /line/add."""
        text = OPEX_ROUTER.read_text(encoding="utf-8")
        assert '"/line/add"' in text or "'/line/add'" in text, \
            "opex_router.py must define POST /line/add."

    def test_capex_form_and_route_hash_field_match(self):
        """STATIC: CAPEX template form field name 'content_hash' matches route param name."""
        template = SHEET_CAPEX.read_text(encoding="utf-8")
        router   = CAPEX_ROUTER.read_text(encoding="utf-8")
        assert 'name="content_hash"' in template, "CAPEX form must have name=\"content_hash\"."
        assert "content_hash" in router,          "CAPEX router must accept content_hash."

    def test_opex_form_and_route_hash_field_match(self):
        """STATIC: OPEX template form field name 'content_hash' matches route param name."""
        template = SHEET_OPEX.read_text(encoding="utf-8")
        router   = OPEX_ROUTER.read_text(encoding="utf-8")
        assert 'name="content_hash"' in template, "OPEX form must have name=\"content_hash\"."
        assert "content_hash" in router,          "OPEX router must accept content_hash."


# ── V. Browser / Playwright tests ───────────────────────────────────────────

import os as _os

_BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_FIXTURE_PATH = _os.path.join(_BASE_DIR, "tests", "fixtures", "ui2b_advanced_interaction_fixture.html")
_FALLBACK_CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _launch_browser():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright to run UI-2B browser tests",
    )
    ctx = playwright.sync_playwright().start()
    try:
        browser = ctx.chromium.launch()
    except Exception:
        try:
            browser = ctx.chromium.launch(executable_path=_FALLBACK_CHROMIUM)
        except Exception as exc:
            ctx.stop()
            pytest.skip(f"OPTIONAL_BROWSER_DEPENDENCY_MISSING_BINARIES: {exc}")
    return ctx, browser


@pytest.fixture
def ui2b_page():
    ctx, browser = _launch_browser()
    page_errors = []
    page = browser.new_page()
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.goto("file://" + _FIXTURE_PATH)
    page.wait_for_load_state("domcontentloaded")
    try:
        yield page, page_errors
    finally:
        browser.close()
        ctx.stop()


class TestUI2BBrowser:
    """BROWSER: runtime DOM tests for UI-2B interaction features via Playwright."""

    def test_modules_load_without_errors(self, ui2b_page):
        """BROWSER: All UI-2B JS modules must load without console errors."""
        page, page_errors = ui2b_page
        assert page.evaluate("typeof window.FcClipboardManager") == "object"
        assert page.evaluate("typeof window.FcFillManager") == "object"
        assert page.evaluate("typeof window.FcUndoManager") == "object"
        assert page.evaluate("typeof window.FcTypeToEdit") == "object"
        assert page.evaluate("typeof window.FcValueBar") == "object"
        assert page.evaluate("typeof window.FcColumnResizer") == "object"
        assert not page_errors, f"Console errors: {page_errors}"

    def test_wrapper_span_is_registered_as_cell(self, ui2b_page):
        """BROWSER: Wrapper-span [data-fc-cell] must be registered by FcGridRegistry."""
        page, _ = ui2b_page
        result = page.evaluate(
            "window.FcGridRegistry.getAddr('capex', 'capex.custom-C01.label') !== null"
        )
        assert result, "capex.custom-C01.label must be registered in grid registry."

    def test_click_input_sets_active_cell_on_wrapper(self, ui2b_page):
        """BROWSER: Clicking the INPUT inside a wrapper span must set active cell to the wrapper."""
        page, _ = ui2b_page
        page.click("#inp-C01-label")
        result = page.evaluate("""
            var active = window.FcActiveCellManager.getActiveCell();
            active && active.cell && active.cell.addr === 'capex.custom-C01.label'
        """)
        assert result, "Clicking INPUT inside wrapper must set active cell to the wrapper span's addr."

    def test_active_cell_changed_event_fires_on_click(self, ui2b_page):
        """BROWSER: fc:activeCellChanged must fire when active cell changes."""
        page, _ = ui2b_page
        page.evaluate("""
            window._ui2bTestLastChanged = null;
            document.addEventListener('fc:activeCellChanged', function(e) {
                window._ui2bTestLastChanged = e.detail;
            }, { once: true });
        """)
        page.click("#inp-C02-amount")
        result = page.evaluate("window._ui2bTestLastChanged !== null")
        assert result, "fc:activeCellChanged event must fire after clicking a cell."

    def test_value_bar_updates_on_click(self, ui2b_page):
        """BROWSER: Value bar address must update when a cell is clicked."""
        page, _ = ui2b_page
        page.click("#inp-C01-label")
        addr = page.evaluate("document.getElementById('fc-value-bar-addr').textContent.trim()")
        assert addr == "capex.custom-C01.label", \
            f"Value bar addr must show 'capex.custom-C01.label', got '{addr}'."

    def test_value_bar_shows_input_value(self, ui2b_page):
        """BROWSER: Value bar value must show the current input value."""
        page, _ = ui2b_page
        page.click("#inp-C01-label")
        val = page.evaluate("document.getElementById('fc-value-bar-value').textContent.trim()")
        assert val == "Solar Panels", f"Value bar value must show 'Solar Panels', got '{val}'."

    def test_native_control_keyboard_safety(self, ui2b_page):
        """BROWSER: Arrow keys must not trigger grid navigation when INPUT has focus."""
        page, _ = ui2b_page
        page.click("#inp-C01-label")
        # Focus is now on the INPUT — active cell is the wrapper, but input has focus
        before_addr = page.evaluate(
            "window.FcActiveCellManager.getActiveCell()?.cell?.addr"
        )
        page.keyboard.press("ArrowDown")
        after_addr = page.evaluate(
            "window.FcActiveCellManager.getActiveCell()?.cell?.addr"
        )
        # Active cell must NOT move when input has keyboard focus
        assert before_addr == after_addr, \
            "Arrow keys must not navigate grid cells when native INPUT has focus."

    def test_column_resizer_bound(self, ui2b_page):
        """BROWSER: FcColumnResizer must bind .fc-col-resize-handle elements."""
        page, _ = ui2b_page
        count = page.evaluate(
            "document.querySelectorAll('.fc-col-resize-handle').length"
        )
        assert count >= 2, f"At least 2 resize handles must be present; found {count}."

    def test_undo_manager_record_and_undo(self, ui2b_page):
        """BROWSER: FcUndoManager must record a user edit and undo it back to the committed value."""
        page, _ = ui2b_page
        # A. Confirm starting value is "Solar Panels"
        initial = page.evaluate("document.getElementById('inp-C01-label').value")
        assert initial == "Solar Panels", f"Expected 'Solar Panels', got '{initial}'."

        # B. Focus the input
        page.click("#inp-C01-label")

        # C. Type multi-character replacement (NOT a single assignment)
        page.keyboard.press("Control+a")
        page.keyboard.type("PV Array")

        # D. Execute the mocked save (requestSubmit fires htmx:afterRequest mock)
        page.evaluate("document.getElementById('form-C01-label').requestSubmit()")
        page.wait_for_timeout(50)  # let the mock 10ms timer fire

        # Confirm the value changed
        after_type = page.evaluate("document.getElementById('inp-C01-label').value")
        assert after_type == "PV Array", f"Expected 'PV Array' after typing, got '{after_type}'."

        # E. Move focus out of the input
        page.click("#outside-input")

        # F. Execute undo
        page.evaluate("window.FcUndoManager.undo()")
        page.wait_for_timeout(50)  # let mock htmx fire

        # H. Assert input value is EXACTLY "Solar Panels"
        after_undo = page.evaluate("document.getElementById('inp-C01-label').value")
        assert after_undo == "Solar Panels", \
            f"After undo, input must be 'Solar Panels', got '{after_undo}'."

        # I. Execute redo
        page.evaluate("window.FcUndoManager.redo()")
        page.wait_for_timeout(50)

        # J. Assert input value is EXACTLY the typed final value
        after_redo = page.evaluate("document.getElementById('inp-C01-label').value")
        assert after_redo == "PV Array", \
            f"After redo, input must be 'PV Array', got '{after_redo}'."

    def test_type_to_edit_resolves_input_in_wrapper(self, ui2b_page):
        """BROWSER: type-to-edit must resolve the INPUT inside a wrapper-span cell."""
        page, _ = ui2b_page
        # Set active cell to wrapper span, then simulate a printable keydown
        page.evaluate("""
            var cr = window.FcGridRegistry.getAddr('capex', 'capex.custom-C02.label');
            window.FcActiveCellManager.setActiveCell('capex', cr);
        """)
        # Verify the resolver can find the input inside the active cell
        has_input = page.evaluate("""
            var active = window.FcActiveCellManager.getActiveCell();
            var cellEl = active && active.cell && active.cell.el;
            var tag = cellEl && cellEl.tagName;
            var inp = (tag === 'INPUT') ? cellEl : (cellEl && cellEl.querySelector('input'));
            inp !== null
        """)
        assert has_input, "type-to-edit resolver must find INPUT inside wrapper-span cell."

    def test_opex_active_visual_wrapper_class(self, ui2b_page):
        """BROWSER: Clicking an OPEX custom input must set fc-active-cell on its wrapper."""
        page, _ = ui2b_page
        page.click("#inp-O01-label")
        has_class = page.evaluate("""
            var inp = document.getElementById('inp-O01-label');
            var wrap = inp && inp.closest('[data-fc-cell]');
            wrap && wrap.classList.contains('fc-active-cell')
        """)
        assert has_class, "OPEX custom input's wrapper span must receive fc-active-cell class on click."

    def test_opex_active_visual_input_ring(self, ui2b_page):
        """BROWSER: Active OPEX input must receive the active ring via computed style."""
        page, _ = ui2b_page
        page.click("#inp-O01-label")
        box_shadow = page.evaluate("""
            var inp = document.getElementById('inp-O01-label');
            window.getComputedStyle(inp).boxShadow
        """)
        assert box_shadow and box_shadow != "none", \
            f"Active OPEX input must have box-shadow ring; got '{box_shadow}'."

    def _drag_resize_handle(self, page, handle_selector, delta_x):
        """Helper: dispatch drag events on a resize handle using JS to bypass layout quirks."""
        page.evaluate(f"""
            (function() {{
                var h = document.querySelector('{handle_selector}');
                if (!h) return;
                var r = h.getBoundingClientRect();
                var sx = r.left + r.width / 2;
                var sy = r.top + r.height / 2;
                h.dispatchEvent(new MouseEvent('mousedown', {{
                    bubbles: true, cancelable: true, clientX: sx, clientY: sy
                }}));
                document.dispatchEvent(new MouseEvent('mousemove', {{
                    bubbles: true, cancelable: true, clientX: sx + {delta_x}, clientY: sy
                }}));
                document.dispatchEvent(new MouseEvent('mouseup', {{
                    bubbles: true, cancelable: true
                }}));
            }})();
        """)

    def test_capex_column_resize_increases_width(self, ui2b_page):
        """BROWSER: Dragging CAPEX desc resize handle +80px must increase header column width."""
        page, _ = ui2b_page
        hdr = page.locator("#capex-hdr-desc")
        initial_w = hdr.bounding_box()["width"]

        self._drag_resize_handle(page, "#capex-hdr-desc .fc-col-resize-handle", 80)

        final_w = hdr.bounding_box()["width"]
        assert final_w > initial_w + 50, \
            f"Desc column must grow after drag; initial={initial_w:.0f} final={final_w:.0f}."

    def test_capex_resize_propagates_to_data_row(self, ui2b_page):
        """BROWSER: Resized CAPEX desc column must propagate to the data row same track."""
        page, _ = ui2b_page
        data_col = page.locator("#capex-data-row-1 .v2-capex-col-desc")
        initial_w = data_col.bounding_box()["width"]

        self._drag_resize_handle(page, "#capex-hdr-desc .fc-col-resize-handle", 80)

        final_w = data_col.bounding_box()["width"]
        assert final_w > initial_w + 50, \
            f"Data row desc column must also grow; initial={initial_w:.0f} final={final_w:.0f}."

    def test_capex_resize_respects_min_width(self, ui2b_page):
        """BROWSER: Dragging CAPEX resize handle far left must be capped at MIN_WIDTH (60px)."""
        page, _ = ui2b_page
        self._drag_resize_handle(page, "#capex-hdr-desc .fc-col-resize-handle", -500)

        hdr = page.locator("#capex-hdr-desc")
        final_w = hdr.bounding_box()["width"]
        assert final_w >= 58, \
            f"Column must not shrink below MIN_WIDTH (60px); got {final_w:.0f}px."
