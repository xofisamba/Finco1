/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR8: FillManager — fill down and fill right for editable cells.
 *
 * Ctrl+D: fill down  — copy active cell's value into selected cells below it.
 * Ctrl+R: fill right — copy active cell's value into selected cells right of it.
 *
 * Uses the canonical V2 persistence path: sets input.value, fires 'input'
 * event (so workbook_v2.js marks it pending), then calls requestSubmit()
 * on the enclosing form.
 *
 * Scope limits:
 *   - single active source cell (the anchor of the selection)
 *   - skips read-only / protected cells silently
 *   - does not fire on native INPUT/SELECT focus (guard in place)
 */
(function () {
  'use strict';

  function _registry() { return window.FcGridRegistry || null; }
  function _selMgr() { return window.FcSelectionManager || null; }
  function _activeMgr() { return window.FcActiveCellManager || null; }

  function _isNativeControl(el) {
    if (!el) return false;
    var t = el.tagName;
    return t === 'INPUT' || t === 'SELECT' || t === 'TEXTAREA' ||
           t === 'BUTTON' || t === 'A' || el.isContentEditable;
  }

  function _getInputValue(cellEl) {
    var inp = cellEl.querySelector && cellEl.querySelector('input:not([type="hidden"]),select,textarea');
    return inp ? inp.value : null;
  }

  function _setAndPersist(cellEl, value) {
    if (!cellEl || cellEl.dataset.fcEditable === 'false') return;
    var inp = cellEl.querySelector && cellEl.querySelector('input:not([type="hidden"]),select,textarea');
    if (!inp) return;
    inp.value = value;
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    var form = inp.closest && inp.closest('form');
    if (form) {
      try { form.requestSubmit(); } catch (e) { form.submit(); }
    }
  }

  function _fill(direction) {
    var amgr = _activeMgr();
    var active = amgr && amgr.getActiveCell();
    if (!active || !active.cell) return;

    var reg = _registry();
    if (!reg) return;
    var sel = _selMgr() && _selMgr().getSelection();

    var sourceEl = active.cell.el;
    var value = _getInputValue(sourceEl);
    if (value === null) return;

    var gridId = active.gridId;

    if (sel && sel.gridId === gridId && sel.addresses && sel.addresses.length > 1) {
      // Fill selected addresses (skip source addr itself)
      var sourceAddr = active.cell.addr;
      sel.addresses.forEach(function (addr) {
        if (addr === sourceAddr) return;
        var cr = reg.cellByAddr(gridId, addr);
        if (cr) _setAndPersist(cr.el, value);
      });
    } else {
      // No multi-selection — fill one step in direction
      var neighbor = reg.neighbors && reg.neighbors(active.cell, direction === 'down' ? 'down' : 'right');
      if (neighbor) _setAndPersist(neighbor.el, value);
    }
  }

  function _onKeyDown(evt) {
    if (!evt.ctrlKey && !evt.metaKey) return;
    var ae = document.activeElement;
    if (_isNativeControl(ae)) return;

    if (evt.key === 'd' || evt.key === 'D') {
      evt.preventDefault();
      _fill('down');
    } else if (evt.key === 'r' || evt.key === 'R') {
      evt.preventDefault();
      _fill('right');
    }
  }

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;
    document.addEventListener('keydown', _onKeyDown);
    return true;
  }

  window.FcFillManager = { init: init };
  init();
})();
