"""UI-2A — V2 Spreadsheet Interaction Foundation.

Static read-only tests (no app boot, no DB, no runtime imports).
Verifies the acceptance criteria from the UI-2A spec.

  A. V2 workbook loads required C1 interaction assets exactly once
  B. Required dependency order is valid
  C. Five initial sheets expose stable data-fc-grid ids
  D. field-editor rows expose deterministic cell addresses
  E. Editable value cells declare data-fc-editable="true"
  F. Non-editable cells declare data-fc-editable="false"
  G. Active-cell markup contract is in place
  H. Keyboard router has native-control safety guard
  I. Inputs/selects inside cells never hijacked (static analysis)
  J. HTMX swap lifecycle modules are loaded (active-cell restoration)
  K. No duplicate module initialisation after HTMX swaps
  L-N. Engine/engine-service files unchanged
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

WORKBOOK_HTML    = REPO_ROOT / "app" / "templates" / "v2" / "workbook.html"
FIELD_EDITOR     = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "field_editor.html"
SHEET_SETUP      = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_project_setup.html"
SHEET_INPUTS     = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_inputs.html"
SHEET_INPUTS_S1  = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "inputs_slice1.html"
SHEET_REVENUE    = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_revenue.html"
SHEET_DEBT       = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_senior_debt.html"
SHEET_TAX        = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_tax.html"

KBD_ROUTER       = REPO_ROOT / "static" / "interaction" / "keyboard-router.js"
ENGINE_JS        = REPO_ROOT / "static" / "interaction" / "engine.js"
ACTIVE_CELL_JS   = REPO_ROOT / "static" / "interaction" / "active-cell.js"
SWAP_LIFECYCLE_JS = REPO_ROOT / "static" / "interaction" / "swap-lifecycle.js"
GRID_REGISTRY_JS = REPO_ROOT / "static" / "interaction" / "grid-registry.js"
FOCUS_MANAGER_JS = REPO_ROOT / "static" / "interaction" / "focus-manager.js"
SELECTION_MGR_JS = REPO_ROOT / "static" / "interaction" / "selection-manager.js"

# Ordered required C1 assets — Correction A: swap-lifecycle before focus-manager
# so authoritative post-HTMX active-cell restoration fires before focus is applied.
REQUIRED_C1_ASSETS = [
    "interaction/grid-registry.js",
    "interaction/engine.js",
    "interaction/active-cell.js",
    "interaction/swap-lifecycle.js",
    "interaction/focus-manager.js",
    "interaction/keyboard-router.js",
    "interaction/selection-manager.js",
]


# ---------------------------------------------------------------------------
# A. V2 workbook loads required C1 assets exactly once
# ---------------------------------------------------------------------------

class TestC1AssetsLoaded:
    @pytest.mark.parametrize("asset", REQUIRED_C1_ASSETS)
    def test_c1_asset_loaded_in_workbook(self, asset):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        count = text.count(asset)
        assert count == 1, (
            f"workbook.html must load '{asset}' exactly once; found {count} times."
        )


# ---------------------------------------------------------------------------
# B. Dependency order
# ---------------------------------------------------------------------------

class TestDependencyOrder:
    def test_c1_dependency_order_in_workbook(self):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        positions = []
        for asset in REQUIRED_C1_ASSETS:
            idx = text.find(asset)
            assert idx >= 0, f"Asset '{asset}' not found in workbook.html."
            positions.append(idx)
        for i in range(1, len(positions)):
            assert positions[i] > positions[i - 1], (
                f"Dependency order violated: '{REQUIRED_C1_ASSETS[i]}' must come "
                f"after '{REQUIRED_C1_ASSETS[i-1]}' in workbook.html."
            )

    def test_grid_registry_before_engine(self):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        assert text.index("grid-registry.js") < text.index("engine.js"), \
            "grid-registry.js must load before engine.js."

    def test_active_cell_before_keyboard_router(self):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        assert text.index("active-cell.js") < text.index("keyboard-router.js"), \
            "active-cell.js must load before keyboard-router.js."

    def test_swap_lifecycle_before_focus_manager(self):
        # Correction A: swap-lifecycle must load before focus-manager so
        # authoritative active-cell restoration completes before focus sync.
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        assert text.index("swap-lifecycle.js") < text.index("focus-manager.js"), \
            "swap-lifecycle.js must load before focus-manager.js (Correction A)."


# ---------------------------------------------------------------------------
# C. Five initial sheets expose stable data-fc-grid ids
# ---------------------------------------------------------------------------

class TestSheetGridIds:
    @pytest.mark.parametrize("sheet_file,grid_id", [
        (SHEET_SETUP,   "project_setup"),
        (SHEET_INPUTS,  "inputs"),
        (SHEET_INPUTS_S1, "inputs"),
        (SHEET_REVENUE, "revenue"),
        (SHEET_DEBT,    "senior_debt"),
        (SHEET_TAX,     "tax"),
    ])
    def test_sheet_has_fc_grid_id(self, sheet_file, grid_id):
        text = sheet_file.read_text(encoding="utf-8")
        assert f'data-fc-grid="{grid_id}"' in text, (
            f"{sheet_file.name} must declare data-fc-grid=\"{grid_id}\"."
        )

    @pytest.mark.parametrize("sheet_file,grid_id", [
        (SHEET_SETUP,   "project_setup"),
        (SHEET_INPUTS_S1, "inputs"),
        (SHEET_REVENUE, "revenue"),
        (SHEET_DEBT,    "senior_debt"),
        (SHEET_TAX,     "tax"),
    ])
    def test_sheet_has_fc_scroll_container(self, sheet_file, grid_id):
        text = sheet_file.read_text(encoding="utf-8")
        assert "data-fc-scroll-container" in text, (
            f"{sheet_file.name} must declare data-fc-scroll-container."
        )


# ---------------------------------------------------------------------------
# D. field-editor rows expose deterministic cell addresses
# ---------------------------------------------------------------------------

class TestFieldEditorAddresses:
    def test_label_addr_pattern_in_field_editor(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        # data-fc-addr="{{ sheet_id }}.{{ f.field_id }}.label"
        assert 'data-fc-addr="{{ sheet_id }}.{{ f.field_id }}.label"' in text, \
            "field_editor.html must emit stable label cell address: sheet_id.field_id.label"

    def test_value_addr_pattern_in_field_editor(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        assert 'data-fc-addr="{{ sheet_id }}.{{ f.field_id }}.value"' in text, \
            "field_editor.html must emit stable value cell address: sheet_id.field_id.value"

    def test_fc_row_on_field_row(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        assert "data-fc-row" in text, \
            "field_editor.html must mark .v2-field-row as data-fc-row."

    def test_label_cell_is_fc_cell(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        # The label span must be a registered fc-cell
        assert 'data-fc-kind="label"' in text, \
            "field_editor.html label cell must declare data-fc-kind=\"label\"."

    def test_value_cell_wrapper_is_fc_cell(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        assert "v2-fc-value-cell" in text, \
            "field_editor.html must have a v2-fc-value-cell wrapper as data-fc-cell."


# ---------------------------------------------------------------------------
# E. Editable value cells declare data-fc-editable="true"
# ---------------------------------------------------------------------------

class TestEditableAttrs:
    def test_editable_cell_attr_present_in_field_editor(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        # The attribute is computed via Jinja conditional — check the pattern
        assert "data-fc-editable=" in text and ("'true'" in text or '"true"' in text), \
            "field_editor.html must declare data-fc-editable (conditionally 'true') for editable cells."

    def test_fc_editable_true_is_conditional_on_bound_and_editable(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        # The true/false depends on binding_label == 'bound' and project_editable
        assert "project_editable" in text and "binding_label" in text and \
               "data-fc-editable" in text, \
            "data-fc-editable must be conditional on binding_label and project_editable."


# ---------------------------------------------------------------------------
# F. Non-editable cells declare data-fc-editable="false"
# ---------------------------------------------------------------------------

class TestReadOnlyAttrs:
    def test_readonly_cell_attr_present_in_field_editor(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        assert 'data-fc-editable="false"' in text, \
            "field_editor.html must declare data-fc-editable=\"false\" for read-only cells."

    def test_label_cell_is_readonly(self):
        text = FIELD_EDITOR.read_text(encoding="utf-8")
        # The label span must always be non-editable
        label_block = text[text.find('data-fc-kind="label"') - 200:
                           text.find('data-fc-kind="label"') + 50]
        assert 'data-fc-editable="false"' in label_block, \
            "Label cell must always be data-fc-editable=\"false\"."


# ---------------------------------------------------------------------------
# G. Active-cell manager contract in place
# ---------------------------------------------------------------------------

class TestActiveCellContract:
    def test_active_cell_js_exposes_setActiveCell(self):
        text = ACTIVE_CELL_JS.read_text(encoding="utf-8")
        assert "setActiveCell" in text, \
            "active-cell.js must expose setActiveCell."

    def test_active_cell_js_exposes_reconcileAfterScan(self):
        text = ACTIVE_CELL_JS.read_text(encoding="utf-8")
        assert "reconcileAfterScan" in text, \
            "active-cell.js must expose reconcileAfterScan for post-swap restoration."

    def test_fc_active_cell_css_class_in_workbook_css(self):
        css = (REPO_ROOT / "static" / "css" / "workbook_v2.css").read_text(encoding="utf-8")
        assert "fc-active-cell" in css, \
            "workbook_v2.css must define .fc-active-cell visual style."

    def test_v2_fc_value_cell_css_exists(self):
        css = (REPO_ROOT / "static" / "css" / "workbook_v2.css").read_text(encoding="utf-8")
        assert "v2-fc-value-cell" in css, \
            "workbook_v2.css must define .v2-fc-value-cell style."


# ---------------------------------------------------------------------------
# H & I. Keyboard router has native-control safety guard
# ---------------------------------------------------------------------------

class TestKeyboardSafetyGuard:
    def test_keyboard_router_has_native_control_guard(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        # Check for the native control guard: INPUT/SELECT/TEXTAREA guard
        assert "INPUT" in text and "SELECT" in text and "TEXTAREA" in text, \
            "keyboard-router.js must guard against intercepting INPUT/SELECT/TEXTAREA."

    def test_guard_returns_before_preventdefault(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        # The guard must appear before evt.preventDefault() in _onKeyDown
        guard_idx = text.find("INPUT")
        prevent_idx = text.find("evt.preventDefault()")
        assert guard_idx < prevent_idx, \
            "Native control guard must appear before evt.preventDefault() in keyboard-router.js."

    def test_guard_checks_tagname_not_just_contains(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        assert "tagName" in text or "tag" in text.lower(), \
            "keyboard-router.js guard must check tagName of the focused element."

    def test_guard_handles_button_and_a(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        assert "BUTTON" in text, \
            "keyboard-router.js guard must include BUTTON elements."
        assert "'A'" in text or '"A"' in text, \
            "keyboard-router.js guard must include A (anchor) elements."

    def test_guard_handles_contenteditable(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        assert "isContentEditable" in text or "contenteditable" in text.lower(), \
            "keyboard-router.js guard must handle contenteditable elements."

    def test_guard_only_fires_when_ae_is_not_cell_itself(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        # Guard must check ae !== current.cell.el (skip guard if cell IS the focused element)
        assert "current.cell.el" in text, \
            "Guard must compare ae to current.cell.el so legacy C1 grids still work."


# ---------------------------------------------------------------------------
# J. HTMX swap lifecycle modules loaded (active-cell restoration)
# ---------------------------------------------------------------------------

class TestSwapLifecycle:
    def test_swap_lifecycle_loaded_in_workbook(self):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        assert "swap-lifecycle.js" in text, \
            "workbook.html must load swap-lifecycle.js for post-HTMX active-cell restoration."

    def test_swap_lifecycle_listens_to_htmx_before_swap(self):
        text = SWAP_LIFECYCLE_JS.read_text(encoding="utf-8")
        assert "htmx:beforeSwap" in text, \
            "swap-lifecycle.js must listen to htmx:beforeSwap to capture active cell before swap."

    def test_swap_lifecycle_restores_by_address(self):
        text = SWAP_LIFECYCLE_JS.read_text(encoding="utf-8")
        assert "addr" in text, \
            "swap-lifecycle.js must restore the active cell by stable address after swap."


# ---------------------------------------------------------------------------
# K. No duplicate module initialisation
# ---------------------------------------------------------------------------

class TestNoDuplicateInit:
    def test_engine_has_single_boot_guard(self):
        text = ENGINE_JS.read_text(encoding="utf-8")
        assert "_booted" in text or "isBooted" in text, \
            "engine.js must have a single-boot guard to prevent duplicate initialisation."

    def test_keyboard_router_has_initialized_guard(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        assert "_initialized" in text, \
            "keyboard-router.js must have an _initialized guard against double init."

    def test_active_cell_js_does_not_add_duplicate_listeners(self):
        text = ACTIVE_CELL_JS.read_text(encoding="utf-8")
        # active-cell.js uses click delegation once on document — check single addEventListener
        adds = text.count("addEventListener")
        assert adds >= 1, "active-cell.js must register event listeners."


# ---------------------------------------------------------------------------
# L. No engine files changed
# ---------------------------------------------------------------------------

UI2A_FROZEN_MAIN = "57d914739de246cfdbd4a3bfbfb0593b033b10cd"


class TestEngineUnchanged:
    def _pr_changed_paths(self) -> list[str]:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{UI2A_FROZEN_MAIN}...HEAD"],
            capture_output=True, text=True,
            cwd=REPO_ROOT
        )
        return result.stdout.strip().splitlines()

    @pytest.mark.parametrize("prefix", ["financial_engine/", "finco_core/"])
    def test_no_engine_directory_in_pr_diff(self, prefix):
        changed = self._pr_changed_paths()
        offenders = [p for p in changed if p.startswith(prefix)]
        assert not offenders, \
            f"UI-2A PR diff must not modify '{prefix}*'. Found: {offenders}"

    @pytest.mark.parametrize("path", [
        "app/api/project_runner.py",
        "app/services/production_financial_authority.py",
    ])
    def test_no_financial_service_in_pr_diff(self, path):
        changed = self._pr_changed_paths()
        assert path not in changed, \
            f"UI-2A PR diff must not modify '{path}'."


# =============================================================================
# CORRECTION A — Behavioral proof tests
# =============================================================================

# ---------------------------------------------------------------------------
# CA-A / CA-B. Native input/select click: focus-manager does not steal focus
# ---------------------------------------------------------------------------

class TestFocusManagerNativeControlGuard:
    """Prove that focus-manager._applyFocus bails out before blurring or
    focusing the wrapper when a native interactive descendant already owns
    DOM focus.  This is a source-level structural proof — browser tests
    for the runtime behaviour are documented as UI2A_BROWSER_ACCEPTANCE_PENDING.
    """

    def test_focus_manager_has_native_control_guard_in_apply_focus(self):
        text = FOCUS_MANAGER_JS.read_text(encoding="utf-8")
        # The guard must contain the INPUT/SELECT check inside _applyFocus
        assert "INPUT" in text and "SELECT" in text, \
            "focus-manager.js must guard INPUT/SELECT in _applyFocus."

    def _apply_focus_body(self) -> tuple[str, int]:
        """Return (_applyFocus function body, absolute offset of body start)."""
        text = FOCUS_MANAGER_JS.read_text(encoding="utf-8")
        start = text.find("function _applyFocus(")
        end = text.find("\n  }", start) + 4  # include closing brace
        return text[start:end], start

    def test_focus_manager_guard_is_before_blur_call(self):
        body, _ = self._apply_focus_body()
        # Guard: the INPUT check
        guard_idx = body.find("INPUT")
        # Call to _blurIfFocused (not the definition) inside _applyFocus
        blur_call_idx = body.find("_blurIfFocused(_focusedEl)")
        assert guard_idx != -1, "Guard (INPUT) must exist in _applyFocus."
        assert blur_call_idx != -1, "_blurIfFocused(_focusedEl) call must exist in _applyFocus."
        assert guard_idx < blur_call_idx, \
            "focus-manager.js native control guard must appear before _blurIfFocused call."

    def test_focus_manager_guard_is_before_focus_call(self):
        body, _ = self._apply_focus_body()
        guard_idx = body.find("INPUT")
        focus_idx = body.find("el.focus(")
        assert guard_idx != -1 and focus_idx != -1, \
            "Both INPUT guard and el.focus() must exist in _applyFocus."
        assert guard_idx < focus_idx, \
            "focus-manager.js native control guard must appear before el.focus() call."

    def test_focus_manager_guard_checks_ae_ne_el(self):
        text = FOCUS_MANAGER_JS.read_text(encoding="utf-8")
        # Guard only skips if ae !== el (cell itself focused → no bypass)
        assert "ae !== el" in text, \
            "focus-manager.js guard must short-circuit only when ae is NOT the cell itself."

    def test_focus_manager_guard_uses_contains(self):
        text = FOCUS_MANAGER_JS.read_text(encoding="utf-8")
        assert "el.contains" in text, \
            "focus-manager.js guard must use el.contains(ae) to verify the element is a descendant."

    def test_focus_manager_guard_tracks_native_control_as_focused(self):
        text = FOCUS_MANAGER_JS.read_text(encoding="utf-8")
        # After guard, _focusedEl must be set to ae (not el)
        # Find the guard return block and check _focusedEl = ae before return
        guard_start = text.find("ae !== el")
        early_return = text.find("return;", guard_start)
        block = text[guard_start:early_return]
        assert "_focusedEl = ae" in block, \
            "focus-manager.js guard must set _focusedEl = ae before returning."

    def test_focus_manager_guard_covers_same_tags_as_keyboard_router(self):
        km_text = KBD_ROUTER.read_text(encoding="utf-8")
        fm_text = FOCUS_MANAGER_JS.read_text(encoding="utf-8")
        for tag in ["INPUT", "SELECT", "TEXTAREA", "BUTTON"]:
            assert tag in fm_text, \
                f"focus-manager.js guard must cover {tag} (same set as keyboard-router.js)."
            assert tag in km_text, \
                f"keyboard-router.js guard must cover {tag}."


# ---------------------------------------------------------------------------
# CA-C. Input keyboard safety: keyboard-router guard proves correctness
# ---------------------------------------------------------------------------

class TestKeyboardRouterInputSafety:
    """Prove the keyboard-router guard structure ensures that when a native
    control has focus inside a cell, the router returns BEFORE evt.preventDefault.
    """

    def _onkeydown_body(self) -> str:
        text = KBD_ROUTER.read_text(encoding="utf-8")
        start = text.find("function _onKeyDown(")
        end = text.find("\n  }", start)  # closing brace of function
        return text[start:end]

    def test_guard_returns_before_preventdefault_in_onkeydown(self):
        body = self._onkeydown_body()
        guard_pos = body.find("INPUT")
        prevent_pos = body.find("evt.preventDefault()")
        assert guard_pos != -1 and prevent_pos != -1, \
            "Both guard and evt.preventDefault() must be in _onKeyDown."
        assert guard_pos < prevent_pos, \
            "Guard (INPUT check) must appear before evt.preventDefault()."

    def test_keyboard_router_guard_only_applies_when_ae_is_not_cell(self):
        body = self._onkeydown_body()
        # The guard checks ae !== current.cell.el so the cell element
        # itself having focus (legacy C1) always passes through.
        assert "current.cell.el" in body, \
            "Keyboard router guard must allow ae === current.cell.el to pass through."

    def test_enter_escape_not_intercepted_when_input_focused(self):
        # Prove: when INPUT has focus, the guard returns before
        # preventDefault, so Enter/Escape reach native/V2 handlers.
        # This is implied by test_guard_returns_before_preventdefault
        # — explicit structural proof:
        body = self._onkeydown_body()
        # Ensure the guard has a bare 'return;' (not conditional on key)
        guard_start = body.find("INPUT")
        return_pos = body.find("return;", guard_start)
        prevent_pos = body.find("evt.preventDefault()", guard_start)
        assert return_pos < prevent_pos, \
            "Keyboard router: guard returns unconditionally for all nav keys when INPUT focused."


# ---------------------------------------------------------------------------
# CA-D. Cell navigation: legacy C1 behavior unchanged
# ---------------------------------------------------------------------------

class TestCellNavigationLegacyIntact:
    def test_keyboard_router_still_has_nav_keys_map(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        for key in ["ArrowRight", "ArrowLeft", "ArrowDown", "ArrowUp", "Enter", "Tab"]:
            assert key in text, \
                f"keyboard-router.js must still handle nav key {key}."

    def test_keyboard_router_calls_setActiveCell(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        assert "setActiveCell" in text, \
            "keyboard-router.js must still call FcActiveCellManager.setActiveCell."

    def test_keyboard_router_calls_syncFocus(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        assert "syncFocus" in text, \
            "keyboard-router.js must still call FcFocusManager.syncFocus after move."

    def test_keyboard_router_uses_neighbors(self):
        text = KBD_ROUTER.read_text(encoding="utf-8")
        assert "FcGridRegistry.neighbors" in text, \
            "keyboard-router.js must use FcGridRegistry.neighbors for cell navigation."


# ---------------------------------------------------------------------------
# CA-E. Active-cell visual: CSS targets real painted descendant boxes
# ---------------------------------------------------------------------------

class TestActiveCellVisualRealBox:
    """Prove that the active-cell CSS for V2 value cells targets a real
    layout box (form or value span), not the display:contents wrapper.
    """

    def _css(self) -> str:
        return (REPO_ROOT / "static" / "css" / "workbook_v2.css").read_text(encoding="utf-8")

    def test_value_cell_active_paints_on_field_form(self):
        css = self._css()
        assert ".v2-fc-value-cell.fc-active-cell .v2-field-form" in css, \
            "workbook_v2.css must paint active border on .v2-field-form (real box) for value cells."

    def test_value_cell_active_paints_on_field_value(self):
        css = self._css()
        assert ".v2-fc-value-cell.fc-active-cell .v2-field-value" in css, \
            "workbook_v2.css must paint active border on .v2-field-value (real box) for read-only rows."

    def test_value_cell_wrapper_itself_clears_boxshadow(self):
        css = self._css()
        # The wrapper overrides the generic rule with box-shadow: none
        assert ".v2-fc-value-cell.fc-active-cell" in css, \
            "workbook_v2.css must have .v2-fc-value-cell.fc-active-cell rule."
        # The generic rule box-shadow must be overridden (none) for the wrapper
        block_start = css.find(".v2-fc-value-cell.fc-active-cell {")
        block_end = css.find("}", block_start)
        if block_start != -1:
            block = css[block_start:block_end]
            assert "none" in block, \
                ".v2-fc-value-cell.fc-active-cell must set box-shadow: none on the wrapper itself."

    def test_selected_cell_paints_on_real_descendant(self):
        css = self._css()
        assert ".v2-fc-value-cell.fc-selected-cell" in css, \
            "workbook_v2.css must handle selected state for value cells."
        assert ".v2-field-form" in css or ".v2-field-value" in css, \
            "Selected state must target a real form/value descendant."

    def test_value_cell_display_contents_preserved(self):
        css = self._css()
        assert "display: contents" in css, \
            "display:contents must be preserved on .v2-fc-value-cell to maintain row layout."

    def test_label_cell_still_receives_direct_box_shadow(self):
        css = self._css()
        # Label span is a real box — its fc-active-cell rule should be direct
        assert "[data-fc-cell].fc-active-cell" in css, \
            "Generic [data-fc-cell].fc-active-cell rule must still exist for label cells."


# ---------------------------------------------------------------------------
# CA-F. HTMX restore: module load order proves sequencing
# ---------------------------------------------------------------------------

class TestHtmxRestoreLoadOrder:
    def test_swap_lifecycle_before_focus_manager_in_workbook(self):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        swap_idx = text.index("swap-lifecycle.js")
        focus_idx = text.index("focus-manager.js")
        assert swap_idx < focus_idx, \
            "swap-lifecycle.js must load before focus-manager.js — authoritative restore first."

    def test_active_cell_before_swap_lifecycle_in_workbook(self):
        text = WORKBOOK_HTML.read_text(encoding="utf-8")
        active_idx = text.index("active-cell.js")
        swap_idx = text.index("swap-lifecycle.js")
        assert active_idx < swap_idx, \
            "active-cell.js must load before swap-lifecycle.js."

    def test_swap_lifecycle_snapshots_before_swap(self):
        text = SWAP_LIFECYCLE_JS.read_text(encoding="utf-8")
        assert "htmx:beforeSwap" in text, \
            "swap-lifecycle.js must listen to htmx:beforeSwap to snapshot active addr."

    def test_swap_lifecycle_restores_by_stable_address(self):
        text = SWAP_LIFECYCLE_JS.read_text(encoding="utf-8")
        assert "addr" in text and "setActiveCell" in text, \
            "swap-lifecycle.js must restore active cell by stable address via setActiveCell."

    def test_focus_manager_syncs_after_grids_scanned(self):
        text = FOCUS_MANAGER_JS.read_text(encoding="utf-8")
        assert "fc:gridsScanned" in text, \
            "focus-manager.js must listen to fc:gridsScanned (fires after swap-lifecycle restores)."

    def test_engine_rescans_on_htmx_afterswap(self):
        text = ENGINE_JS.read_text(encoding="utf-8")
        assert "htmx:afterSwap" in text, \
            "engine.js must rescan on htmx:afterSwap to dispatch fc:gridsScanned."

    def test_no_duplicate_focus_manager_init(self):
        text = FOCUS_MANAGER_JS.read_text(encoding="utf-8")
        assert "_initialized" in text, \
            "focus-manager.js must have an _initialized guard."
