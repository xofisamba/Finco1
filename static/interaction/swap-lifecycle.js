/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR3: FcSwapLifecycle (focus & scroll preservation only — no
 * keyboard navigation, selection, clipboard, or undo)
 *
 * Reference: docs/C1_INTERACTION_LAYER_DESIGN.md,
 *            docs/C1_PR1_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR2_IMPLEMENTATION_NOTE.md,
 *            docs/C1_PR3_IMPLEMENTATION_NOTE.md.
 *
 * Responsibility in this PR is limited to:
 *   - capturing the active grid/cell address and the scroll position
 *     of any registered [data-fc-scroll-container] before an htmx
 *     swap (htmx:beforeSwap)
 *   - after the engine has rescanned the swapped subtree
 *     (fc:gridsScanned), restoring the active cell and scroll
 *     position when the same grid/cell/container still exists, or
 *     clearing safely when it does not
 *
 * This module does NOT:
 *   - handle keyboard input of any kind
 *   - implement selection, ranges, or multi-selection
 *   - implement clipboard, undo/redo, or fill-down
 *   - change click/dblclick behaviour — it never calls
 *     preventDefault() or stopPropagation()
 *
 * It is purely additive on top of FcActiveCellManager (PR2): calling
 * setActiveCell()/clearActiveCell() here for a cell that is already
 * active is harmless and idempotent. The new scroll-preservation
 * capability does not exist anywhere else in the codebase.
 */
(function () {
  'use strict';

  var _activeSnapshot = null; // { gridId, addr } or null
  var _scrollSnapshot = {};   // gridId -> { scrollTop, scrollLeft }

  function _onBeforeSwap() {
    var active = window.FcActiveCellManager && window.FcActiveCellManager.getActiveCell
      ? window.FcActiveCellManager.getActiveCell()
      : null;
    _activeSnapshot = (active && active.cell && active.cell.addr)
      ? { gridId: active.gridId, addr: active.cell.addr }
      : null;

    _scrollSnapshot = {};
    var ids = window.FcGridRegistry.getGridIds();
    for (var i = 0; i < ids.length; i++) {
      var gridId = ids[i];
      var grid = window.FcGridRegistry.getGrid(gridId);
      if (grid && grid.container) {
        _scrollSnapshot[gridId] = {
          scrollTop: grid.container.scrollTop,
          scrollLeft: grid.container.scrollLeft
        };
      }
    }
  }

  function _restoreActiveCell(grids) {
    if (!_activeSnapshot) return;
    if (grids.indexOf(_activeSnapshot.gridId) === -1) return;

    var cell = window.FcGridRegistry.getAddr(_activeSnapshot.gridId, _activeSnapshot.addr);
    if (cell) {
      window.FcActiveCellManager.setActiveCell(_activeSnapshot.gridId, cell);
    } else {
      window.FcActiveCellManager.clearActiveCell();
    }
    _activeSnapshot = null;
  }

  function _restoreScroll(grids) {
    for (var i = 0; i < grids.length; i++) {
      var gridId = grids[i];
      var snap = _scrollSnapshot[gridId];
      if (!snap) continue;

      var grid = window.FcGridRegistry.getGrid(gridId);
      if (grid && grid.container) {
        grid.container.scrollTop = snap.scrollTop;
        grid.container.scrollLeft = snap.scrollLeft;
      }
      delete _scrollSnapshot[gridId];
    }
  }

  function _onGridsScanned(evt) {
    var grids = (evt && evt.detail && evt.detail.grids) || [];
    _restoreActiveCell(grids);
    _restoreScroll(grids);
  }

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;

    document.addEventListener('htmx:beforeSwap', _onBeforeSwap);
    document.addEventListener('fc:gridsScanned', _onGridsScanned);

    return true;
  }

  window.FcSwapLifecycle = {
    init: init
  };

  init();
})();
