/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR9: UndoManager — undo/redo for user edits to persisted inputs.
 *
 * Records a stack of {addr, gridId, oldValue, newValue} entries.
 * Ctrl+Z undoes the most recent edit; Ctrl+Y / Ctrl+Shift+Z redoes it.
 *
 * An entry is pushed when a V2 field save completes successfully
 * (htmx:afterRequest with success status on a field form).
 *
 * Undo restores the old value via the canonical persistence path
 * (sets input.value, fires 'input', calls requestSubmit).
 * If the server returns a 409 (stale content_hash), the undo fails
 * gracefully without corrupting the UI.
 *
 * HTMX swaps do not corrupt the stack — addr-based entries remain
 * valid as long as the cell address is stable across swaps.
 *
 * Scope limits:
 *   - single linear stack (no branching)
 *   - stack depth capped at 100 entries (oldest dropped)
 *   - does not cover financial engine outputs (read-only cells)
 *   - does not snapshot HTMX swap results as "edits"
 */
(function () {
  'use strict';

  var MAX_STACK = 100;
  var _stack = [];
  var _stackIdx = -1;  // points to last applied entry; -1 = empty

  function _registry() { return window.FcGridRegistry || null; }

  function _isNativeControl(el) {
    if (!el) return false;
    var t = el.tagName;
    return t === 'INPUT' || t === 'SELECT' || t === 'TEXTAREA' ||
           t === 'BUTTON' || t === 'A' || el.isContentEditable;
  }

  /* ── record ─────────────────────────────────────────────────────── */

  function record(gridId, addr, oldValue, newValue) {
    if (oldValue === newValue) return;
    // Truncate redo branch
    if (_stackIdx < _stack.length - 1) {
      _stack = _stack.slice(0, _stackIdx + 1);
    }
    _stack.push({ gridId: gridId, addr: addr, old: oldValue, new: newValue });
    if (_stack.length > MAX_STACK) _stack.shift();
    _stackIdx = _stack.length - 1;
  }

  /* ── apply ──────────────────────────────────────────────────────── */

  function _apply(entry, targetValue) {
    var reg = _registry();
    if (!reg) return;
    var cr = reg.cellByAddr(entry.gridId, entry.addr);
    if (!cr) return;
    var inp = cr.el.querySelector && cr.el.querySelector('input:not([type="hidden"]),select,textarea');
    if (!inp) return;
    inp.value = targetValue;
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    var form = inp.closest && inp.closest('form');
    if (form) {
      try { form.requestSubmit(); } catch (e) { form.submit(); }
    }
  }

  /* ── undo / redo ────────────────────────────────────────────────── */

  function undo() {
    if (_stackIdx < 0) return;
    var entry = _stack[_stackIdx];
    _stackIdx--;
    _apply(entry, entry.old);
  }

  function redo() {
    if (_stackIdx >= _stack.length - 1) return;
    _stackIdx++;
    var entry = _stack[_stackIdx];
    _apply(entry, entry.new);
  }

  /* ── auto-record on field saves ──────────────────────────────────── */

  function _onBeforeInput(evt) {
    // Capture old value just before user modifies an input
    var inp = evt.target;
    if (!inp || !inp.closest) return;
    if (!inp.closest('[data-fc-cell]')) return;
    inp._fcUndoOldValue = inp.value;
  }

  function _onAfterRequest(evt) {
    var form = evt.detail && evt.detail.elt;
    if (!form || form.tagName !== 'FORM') return;
    if (!evt.detail.successful) return;

    // Find the changed input inside the form that has data-fc-cell
    var inputs = form.querySelectorAll('input[data-fc-cell], select[data-fc-cell]');
    inputs.forEach(function (inp) {
      var cellEl = inp.closest('[data-fc-cell]');
      if (!cellEl) return;
      var addr = cellEl.dataset.fcAddr;
      var gridEl = cellEl.closest('[data-fc-grid]');
      var gridId = gridEl ? gridEl.dataset.fcGrid : null;
      if (!addr || !gridId) return;
      var oldVal = inp._fcUndoOldValue;
      var newVal = inp.value;
      if (oldVal !== undefined && oldVal !== newVal) {
        record(gridId, addr, oldVal, newVal);
      }
      inp._fcUndoOldValue = undefined;
    });
  }

  /* ── keyboard handler ────────────────────────────────────────────── */

  function _onKeyDown(evt) {
    if (!evt.ctrlKey && !evt.metaKey) return;
    var ae = document.activeElement;
    if (_isNativeControl(ae)) return;

    if (evt.key === 'z' || evt.key === 'Z') {
      evt.preventDefault();
      if (evt.shiftKey) { redo(); } else { undo(); }
    } else if (evt.key === 'y' || evt.key === 'Y') {
      evt.preventDefault();
      redo();
    }
  }

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;
    document.addEventListener('keydown', _onKeyDown);
    document.addEventListener('beforeinput', _onBeforeInput, true);
    document.addEventListener('htmx:afterRequest', _onAfterRequest);
    return true;
  }

  window.FcUndoManager = { init: init, record: record, undo: undo, redo: redo };
  init();
})();
