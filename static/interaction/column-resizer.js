/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR12 / UI-2B-CorrA: ColumnResizer — drag-to-resize column headers.
 *
 * Attaches mousedown listeners to .fc-col-resize-handle elements inside
 * column header cells. Handles must have a data-col attribute matching the
 * column name (e.g. data-col="desc").
 *
 * On drag, sets both the CSS custom property --fc-col-<name>-width on the
 * nearest [data-fc-grid] ancestor AND directly sets width/flex on matching
 * column elements (.v2-capex-col-<name>, .v2-opex-col-<name>, etc.) so the
 * layout change is immediately visible regardless of CSS variable fallbacks.
 *
 * Resize state is session-only (no server persistence for MVP).
 * Minimum column width: 60px.
 */
(function () {
  'use strict';

  var MIN_WIDTH = 60;
  var _dragging = null;

  function _applyWidth(gridEl, col, width) {
    var px = width + 'px';
    // CSS custom property (for any rule that consumes it)
    gridEl.style.setProperty('--fc-col-' + col + '-width', px);
    // Direct style on matching column cells for immediate layout effect
    var selector = [
      '.v2-capex-col-' + col,
      '.v2-opex-col-' + col,
      '.v2-col-' + col
    ].join(',');
    var cols = gridEl.querySelectorAll(selector);
    cols.forEach(function (el) {
      el.style.width = px;
      el.style.minWidth = px;
      el.style.maxWidth = px;
      el.style.flex = '0 0 ' + px;
    });
  }

  function _onMouseMove(evt) {
    if (!_dragging) return;
    var dx = evt.clientX - _dragging.startX;
    var newWidth = Math.max(MIN_WIDTH, _dragging.startWidth + dx);
    _applyWidth(_dragging.grid, _dragging.col, newWidth);
  }

  function _onMouseUp() {
    _dragging = null;
    document.removeEventListener('mousemove', _onMouseMove);
    document.removeEventListener('mouseup', _onMouseUp);
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
  }

  function _onHandleMouseDown(evt) {
    evt.preventDefault();
    var handle = evt.currentTarget;
    var col = handle.dataset.col;
    if (!col) return;

    var header = handle.parentElement;
    if (!header) return;
    var startWidth = header.getBoundingClientRect().width;
    var gridEl = handle.closest('[data-fc-grid]');
    if (!gridEl) return;

    _dragging = {
      col: col,
      startX: evt.clientX,
      startWidth: startWidth,
      grid: gridEl,
    };
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';
    document.addEventListener('mousemove', _onMouseMove);
    document.addEventListener('mouseup', _onMouseUp);
  }

  function _bindHandles(root) {
    var handles = (root || document).querySelectorAll('.fc-col-resize-handle');
    handles.forEach(function (h) {
      h.removeEventListener('mousedown', _onHandleMouseDown);
      h.addEventListener('mousedown', _onHandleMouseDown);
    });
  }

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;
    _bindHandles(document);
    document.addEventListener('htmx:afterSwap', function () { _bindHandles(document); });
    return true;
  }

  window.FcColumnResizer = { init: init, bindHandles: _bindHandles };
  init();
})();
