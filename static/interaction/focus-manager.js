/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR4: FocusManager (DOM focus management only — no keyboard
 * navigation, selection, clipboard, or undo)
 *
 * Reference: docs/C1_INTERACTION_LAYER_DESIGN.md,
 *            docs/C1_PR1_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR2_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR3_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR4_IMPLEMENTATION_NOTE.md.
 *
 * Responsibility in this PR is limited to:
 *   - making browser DOM focus follow whichever cell
 *     FcActiveCellManager reports as active (cells are not natively
 *     focusable <td>/<th> elements, so a tabindex="-1" is applied
 *     lazily — once — the first time a given cell becomes active;
 *     this keeps the cell out of the normal Tab order, since Tab
 *     navigation is explicitly out of scope for this PR)
 *   - restoring focus to the active cell after an htmx swap, once
 *     FcSwapLifecycle has resolved (or cleared) the active cell for
 *     the swapped subtree
 *   - blurring safely (never trapping focus) when the active cell is
 *     cleared, e.g. because the focused element disappeared
 *   - idempotent init()
 *
 * This module does NOT:
 *   - handle any keyboard input (no keydown/keyup/keypress listeners)
 *   - implement selection, ranges, or multi-selection
 *   - implement clipboard, undo/redo, or fill-down
 *   - change click/dblclick behaviour — it never calls
 *     preventDefault() or stopPropagation(), and never sets focus on
 *     an element that is not already the active cell
 *   - move scroll position itself (that remains FcSwapLifecycle's
 *     responsibility); el.focus({ preventScroll: true }) is used
 *     everywhere so this module never causes an unexpected jump
 *
 * It deliberately does not modify active-cell.js or swap-lifecycle.js
 * — it only reads FcActiveCellManager.getActiveCell() and reacts to
 * the same click / fc:gridsScanned / fc:engineReady events those
 * modules already use, loaded after both in base.html so its
 * listeners observe the post-resolution state.
 */
(function () {
  'use strict';

  var _focusedEl = null;

  function _blurIfFocused(el) {
    if (el && document.activeElement === el) {
      el.blur();
    }
  }

  function _applyFocus(cell) {
    if (!cell || !cell.el) return;
    var el = cell.el;

    if (!el.hasAttribute('tabindex')) {
      el.setAttribute('tabindex', '-1');
    }

    if (_focusedEl && _focusedEl !== el) {
      _blurIfFocused(_focusedEl);
    }
    _focusedEl = el;

    if (document.activeElement !== el) {
      el.focus({ preventScroll: true });
    }
  }

  function _clearFocus() {
    _blurIfFocused(_focusedEl);
    _focusedEl = null;
  }

  function _sync() {
    var active = window.FcActiveCellManager && window.FcActiveCellManager.getActiveCell
      ? window.FcActiveCellManager.getActiveCell()
      : null;

    if (active && active.cell) {
      _applyFocus(active.cell);
    } else {
      _clearFocus();
    }
  }

  function _onClick(evt) {
    var cellEl = evt.target && evt.target.closest
      ? evt.target.closest('[data-fc-cell]')
      : null;
    if (!cellEl) return;
    _sync();
  }

  function _onGridsScanned() {
    _sync();
  }

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;

    document.addEventListener('click', _onClick);
    document.addEventListener('fc:gridsScanned', _onGridsScanned);
    document.addEventListener('fc:engineReady', _onGridsScanned);

    return true;
  }

  window.FcFocusManager = {
    init: init
  };

  init();
})();
