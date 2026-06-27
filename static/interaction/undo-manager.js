/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR8: UndoManager (interaction-layer undo/redo foundation only —
 * no fill-down/fill-right/drag-fill, formula editing, recalculation,
 * or Save/Run integration)
 *
 * Reference: docs/C1_INTERACTION_LAYER_DESIGN.md,
 *            docs/C1_PR1_IMPLEMENTATION_NOTE.md through
 *            docs/C1_PR7_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR8_IMPLEMENTATION_NOTE.md.
 *
 * Responsibility in this PR is limited to:
 *   - maintaining one global undo stack and one global redo stack of
 *     "transaction" objects (the only state this module owns — a
 *     history of values, not a parallel grid/active-cell/selection
 *     model; every restore re-resolves cells fresh via
 *     FcGridRegistry.getAddr() at undo/redo time)
 *   - recordTransaction(tx): called by other modules (today, only
 *     FcClipboardController.pasteText()) when they perform a logical
 *     user action that should be undoable
 *   - observing genuinely observable single-cell edits itself: a
 *     focusin/change pair on a real <input>/<select>/<textarea>
 *     living inside a [data-fc-cell], recorded as a "cell-edit"
 *     transaction
 *   - undo()/redo(): restoring previous/next values for every change
 *     in the popped transaction, then restoring active-cell/selection
 *     state, conservatively and only where it still resolves
 *   - Ctrl+Z/Cmd+Z (undo), Ctrl+Y/Cmd+Y and Ctrl+Shift+Z/Cmd+Shift+Z
 *     (redo), scoped to a registered, currently-active grid cell only
 *     — never hijacking normal browser undo in a real text input
 *     outside the grid
 *
 * This module does NOT:
 *   - implement fill-down/fill-right/drag-fill/autofill
 *   - parse or translate formulas, or trigger recalculation
 *   - persist anything or integrate with Save/Run
 *   - attempt cross-grid or cross-project undo — a transaction is
 *     always scoped to the single gridId it was recorded against
 *   - fake cell-edit capture for plain-text cells that have no real
 *     input/select/textarea descendant — until production templates
 *     adopt the data-fc-* markup contract with real form controls,
 *     the only single-cell edits this module can observe directly are
 *     ones typed into a real input/select/textarea inside a
 *     [data-fc-cell]; everything else flows through recordTransaction()
 *     called by another module (e.g. paste)
 */
(function () {
  'use strict';

  var _undoStack = [];
  var _redoStack = [];

  function _isGridCellFocused() {
    var el = document.activeElement;
    return !!(el && el.closest && el.closest('[data-fc-cell]'));
  }

  function _currentActive() {
    var active = window.FcActiveCellManager && window.FcActiveCellManager.getActiveCell
      ? window.FcActiveCellManager.getActiveCell()
      : null;
    if (!active || !active.cell) return null;
    var el = document.activeElement;
    if (el !== active.cell.el && !(active.cell.el.contains && active.cell.el.contains(el))) return null;
    return active;
  }

  function _applyCellValue(cell, value) {
    if (window.FcCellIO && window.FcCellIO.writeValue) {
      window.FcCellIO.writeValue(cell, value);
    }
  }

  function canUndo() {
    return _undoStack.length > 0;
  }

  function canRedo() {
    return _redoStack.length > 0;
  }

  function recordTransaction(tx) {
    if (!tx || !tx.changes || !tx.changes.length) return;
    _undoStack.push(tx);
    _redoStack = [];
  }

  /**
   * Restore an active-cell/selection snapshot, but only if every
   * address it references still resolves in the stated grid — never
   * corrupts current state by partially restoring or pointing at a
   * cell that no longer exists.
   */
  function _restoreActive(snapshot) {
    if (!snapshot || !snapshot.gridId || !snapshot.addr) return;
    var cell = window.FcGridRegistry.getAddr(snapshot.gridId, snapshot.addr);
    if (!cell) return;
    if (window.FcActiveCellManager && window.FcActiveCellManager.setActiveCell) {
      window.FcActiveCellManager.setActiveCell(snapshot.gridId, cell);
    }
  }

  function _restoreSelection(snapshot) {
    if (!snapshot || !snapshot.gridId || !snapshot.anchorAddr || !snapshot.activeAddr) return;
    var anchor = window.FcGridRegistry.getAddr(snapshot.gridId, snapshot.anchorAddr);
    var active = window.FcGridRegistry.getAddr(snapshot.gridId, snapshot.activeAddr);
    if (!anchor || !active) return;
    if (!window.FcSelectionManager) return;
    window.FcSelectionManager.selectSingle(snapshot.gridId, anchor);
    window.FcSelectionManager.extendTo(snapshot.gridId, active);
  }

  function _applyChanges(tx, useAfter) {
    for (var i = 0; i < tx.changes.length; i++) {
      var change = tx.changes[i];
      var cell = window.FcGridRegistry.getAddr(tx.gridId, change.addr);
      if (!cell) continue; // cell no longer exists — skip safely, never throw
      _applyCellValue(cell, useAfter ? change.after : change.before);
    }
  }

  function _syncFocus() {
    if (window.FcFocusManager && window.FcFocusManager.syncFocus) {
      window.FcFocusManager.syncFocus();
    }
  }

  function undo() {
    if (!_undoStack.length) return false;
    var tx = _undoStack.pop();

    _applyChanges(tx, false);
    _restoreActive(tx.activeBefore);
    _restoreSelection(tx.selectionBefore);
    _syncFocus();

    _redoStack.push(tx);
    return true;
  }

  function redo() {
    if (!_redoStack.length) return false;
    var tx = _redoStack.pop();

    _applyChanges(tx, true);
    _restoreActive(tx.activeAfter);
    _restoreSelection(tx.selectionAfter);
    _syncFocus();

    _undoStack.push(tx);
    return true;
  }

  function _isUndoChord(evt) {
    return (evt.ctrlKey || evt.metaKey) && !evt.shiftKey && !evt.altKey &&
      (evt.key === 'z' || evt.key === 'Z');
  }

  function _isRedoChord(evt) {
    if (evt.altKey) return false;
    if ((evt.ctrlKey || evt.metaKey) && !evt.shiftKey && (evt.key === 'y' || evt.key === 'Y')) {
      return true;
    }
    return (evt.ctrlKey || evt.metaKey) && evt.shiftKey && (evt.key === 'z' || evt.key === 'Z');
  }

  function _onKeyDown(evt) {
    if (!_isUndoChord(evt) && !_isRedoChord(evt)) return;
    if (!_isGridCellFocused()) return;
    if (!_currentActive()) return;

    if (_isUndoChord(evt)) {
      evt.preventDefault();
      undo();
    } else {
      evt.preventDefault();
      redo();
    }
  }

  // Genuinely observable single-cell edit capture: a focusin/change
  // pair on a real input/select/textarea living inside a
  // [data-fc-cell]. This is the only single-cell edit path that is
  // not faked — there is no production markup yet for editing a
  // plain-text <td> directly.
  var _editBefore = null; // { el, cell, gridId, value }

  function _findCell(el) {
    var cellEl = el.closest ? el.closest('[data-fc-cell]') : null;
    if (!cellEl) return null;
    var gridEl = cellEl.closest ? cellEl.closest('[data-fc-grid]') : null;
    if (!gridEl) return null;
    var gridId = gridEl.getAttribute('data-fc-grid');
    var addr = cellEl.getAttribute('data-fc-addr');
    if (!gridId || !addr) return null;
    var cell = window.FcGridRegistry.getAddr(gridId, addr);
    if (!cell) return null;
    return { gridId: gridId, cell: cell };
  }

  function _isFormField(el) {
    return !!(el && el.matches && el.matches('input, select, textarea'));
  }

  function _onFocusIn(evt) {
    var el = evt.target;
    if (!_isFormField(el)) return;
    var resolved = _findCell(el);
    if (!resolved) return;

    _editBefore = {
      el: el,
      gridId: resolved.gridId,
      cell: resolved.cell,
      value: el.value != null ? String(el.value) : ''
    };
  }

  function _onChange(evt) {
    var el = evt.target;
    if (!_editBefore || _editBefore.el !== el) return;

    var before = _editBefore.value;
    var after = el.value != null ? String(el.value) : '';
    var gridId = _editBefore.gridId;
    var cell = _editBefore.cell;
    // Re-arm rather than clear: a real <input> stays focused across
    // consecutive commits (e.g. repeated change events without an
    // intervening blur/focusin), and the next commit's "before" must
    // be this commit's "after", not a stale or missing baseline.
    _editBefore.value = after;

    if (before === after) return;
    if (!cell.addr) return;

    var activeSnapshot = { gridId: gridId, addr: cell.addr };
    var selectionBefore = window.FcSelectionManager && window.FcSelectionManager.getSelection
      ? window.FcSelectionManager.getSelection()
      : null;

    recordTransaction({
      type: 'cell-edit',
      gridId: gridId,
      changes: [{ addr: cell.addr, before: before, after: after }],
      activeBefore: activeSnapshot,
      activeAfter: activeSnapshot,
      selectionBefore: selectionBefore,
      selectionAfter: selectionBefore
    });
  }

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;

    document.addEventListener('keydown', _onKeyDown);
    document.addEventListener('focusin', _onFocusIn);
    document.addEventListener('change', _onChange);

    return true;
  }

  window.FcUndoManager = {
    init: init,
    recordTransaction: recordTransaction,
    undo: undo,
    redo: redo,
    canUndo: canUndo,
    canRedo: canRedo
  };

  init();
})();
