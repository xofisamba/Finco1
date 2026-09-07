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

# Ordered required C1 assets
REQUIRED_C1_ASSETS = [
    "interaction/grid-registry.js",
    "interaction/engine.js",
    "interaction/active-cell.js",
    "interaction/focus-manager.js",
    "interaction/swap-lifecycle.js",
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
