/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR6: SelectionManager (selection model foundation only — no
 * clipboard, copy/paste, undo, fill, formula editing, or
 * recalculation)
 *
 * Reference: docs/C1_INTERACTION_LAYER_DESIGN.md,
 *            docs/C1_PR1_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR2_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR3_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR4_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR5_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR6_IMPLEMENTATION_NOTE.md.
 *
 * Responsibility in this PR is limited to:
 *   - tracking exactly one selection globally: an anchor cell, the
 *     active cell, and the rectangular range between them
 *   - rendering selected cells with a single CSS class
 *   - collapsing to a single-cell selection on a plain click or on
 *     any non-extending keyboard move (mirrors FcActiveCellManager's
 *     "exactly one active cell" pattern from PR2)
 *   - extending the range when FcKeyboardRouter reports a Shift+Arrow
 *     move, keeping the anchor fixed
 *   - reconciling safely after an htmx swap, once
 *     FcActiveCellManager/FcSwapLifecycle have already resolved (or
 *     cleared) the active cell for the swapped subtree
 *
 * This module does NOT:
 *   - implement clipboard, copy/paste, cut, undo/redo, or
 *     fill-down/drag-fill
 *   - implement a context menu, formula editing, or recalculation
 *   - implement multi-range or Ctrl-click selection (exactly one
 *     contiguous range, globally)
 *   - change click/dblclick/typing behaviour — it never calls
 *     preventDefault()/stopPropagation(), and only reacts to clicks
 *     that land on a registered grid cell
 *
 * It never holds its own notion of "which cell is active" — every
 * operation reads FcActiveCellManager.getActiveCell() and
 * FcGridRegistry's live grid index, so there is no parallel state
 * model to keep in sync.
 */
(function () {
  'use strict';

  var SELECTED_CLASS = 'fc-selected-cell';

  // { gridId, anchor: cellRecord, active: cellRecord, cells: [cellRecord, ...] }
  var _selection = null;

  function _setVisual(cells, on) {
    for (var i = 0; i < cells.length; i++) {
      var el = cells[i].el;
      if (el && el.classList) {
        if (on) el.classList.add(SELECTED_CLASS);
        else el.classList.remove(SELECTED_CLASS);
      }
    }
  }

  function _rectCells(gridId, anchor, active) {
    var grid = window.FcGridRegistry.getGrid(gridId);
    if (!grid) return [];

    var minRow = Math.min(anchor.row, active.row);
    var maxRow = Math.max(anchor.row, active.row);
    var minCol = Math.min(anchor.col, active.col);
    var maxCol = Math.max(anchor.col, active.col);

    var cells = [];
    for (var r = minRow; r <= maxRow; r++) {
      var row = grid.rows[r];
      if (!row) continue;
      for (var c = minCol; c <= maxCol; c++) {
        if (row[c]) cells.push(row[c]);
      }
    }
    return cells;
  }

  function _applySelection(gridId, anchor, active) {
    var cells = _rectCells(gridId, anchor, active);
    if (_selection) _setVisual(_selection.cells, false);
    _setVisual(cells, true);
    _selection = { gridId: gridId, anchor: anchor, active: active, cells: cells };
  }

  function selectSingle(gridId, cell) {
    if (!gridId || !cell) return;
    _applySelection(gridId, cell, cell);
  }

  function extendTo(gridId, cell) {
    if (!gridId || !cell) return;
    if (!_selection || _selection.gridId !== gridId) {
      // No existing anchor to extend from in this grid — conservative
      // fallback to a fresh single-cell selection.
      selectSingle(gridId, cell);
      return;
    }
    _applySelection(gridId, _selection.anchor, cell);
  }

  function clearSelection() {
    if (_selection) _setVisual(_selection.cells, false);
    _selection = null;
  }

  function collapseToActive() {
    var active = window.FcActiveCellManager && window.FcActiveCellManager.getActiveCell
      ? window.FcActiveCellManager.getActiveCell()
      : null;
    if (active && active.cell) {
      selectSingle(active.gridId, active.cell);
    } else {
      clearSelection();
    }
  }

  function getSelection() {
    if (!_selection) return null;
    return {
      gridId: _selection.gridId,
      anchorAddr: _selection.anchor.addr,
      activeAddr: _selection.active.addr,
      addresses: _selection.cells
        .map(function (cell) { return cell.addr; })
        .filter(function (addr) { return !!addr; })
    };
  }

  function _onClick(evt) {
    var cellEl = evt.target && evt.target.closest
      ? evt.target.closest('[data-fc-cell]')
      : null;
    if (!cellEl) return;
    collapseToActive();
  }

  /**
   * Reconcile selection state after the registry has rescanned the
   * swapped subtree and FcActiveCellManager has already resolved (or
   * cleared) the active cell:
   *   - no active cell survives -> clear selection safely
   *   - active cell survives but in a different grid than the
   *     current selection, or the anchor's address no longer
   *     resolves -> collapse to a single-cell selection at the
   *     active cell
   *   - both anchor and active cell resolve in the same grid ->
   *     restore the range between their freshly rebuilt cell records
   */
  function _reconcileAfterScan() {
    var active = window.FcActiveCellManager && window.FcActiveCellManager.getActiveCell
      ? window.FcActiveCellManager.getActiveCell()
      : null;

    if (!active || !active.cell) {
      clearSelection();
      return;
    }

    if (!_selection || _selection.gridId !== active.gridId) {
      selectSingle(active.gridId, active.cell);
      return;
    }

    var anchorAddr = _selection.anchor.addr;
    var anchorCell = anchorAddr
      ? window.FcGridRegistry.getAddr(active.gridId, anchorAddr)
      : null;

    if (anchorCell) {
      _applySelection(active.gridId, anchorCell, active.cell);
    } else {
      selectSingle(active.gridId, active.cell);
    }
  }

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;

    document.addEventListener('click', _onClick);
    document.addEventListener('fc:gridsScanned', _reconcileAfterScan);
    document.addEventListener('fc:engineReady', _reconcileAfterScan);

    return true;
  }

  window.FcSelectionManager = {
    init: init,
    selectSingle: selectSingle,
    extendTo: extendTo,
    collapseToActive: collapseToActive,
    clearSelection: clearSelection,
    getSelection: getSelection
  };

  init();
})();
