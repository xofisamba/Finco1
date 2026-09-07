/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR12: ColumnResizer — drag-to-resize column headers.
 *
 * Attaches mousedown listeners to .fc-col-resize-handle elements rendered
 * inside column header cells (.v2-capex-col-header span, etc.).
 * Resize state is session-only (no server persistence for MVP).
 *
 * Usage: Add a <span class="fc-col-resize-handle" data-col="desc"> child
 * to each resizable column header cell. The resizer tracks drag delta and
 * applies a CSS custom property --fc-col-<name>-width on the nearest
 * [data-fc-grid] ancestor.
 *
 * Minimum column width: 60px.
 */
(function () {
  'use strict';

  var MIN_WIDTH = 60;
  var _dragging = null;

  function _onMouseMove(evt) {
    if (!_dragging) return;
    var dx = evt.clientX - _dragging.startX;
    var newWidth = Math.max(MIN_WIDTH, _dragging.startWidth + dx);
    _dragging.grid.style.setProperty(
      '--fc-col-' + _dragging.col + '-width',
      newWidth + 'px'
    );
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
