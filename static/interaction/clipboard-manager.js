/*
 * Finco One — Spreadsheet Interaction Layer
 * C1-PR7: ClipboardManager — TSV copy/paste for selected cell ranges.
 *
 * Copy: Ctrl+C on a selection writes TSV text to the system clipboard.
 * Paste: Ctrl+V pastes TSV into the selected range starting at the
 *   active cell, one token per editable cell, using the canonical V2
 *   field persistence path (fires 'input' event so workbook_v2.js marks
 *   cells pending, then calls requestSubmit() per form).
 *
 * Scope limits (this module):
 *   - no multi-range selection (single rectangular range only)
 *   - paste into protected/read-only cells is silently skipped
 *   - rectangular out-of-bounds paste is clipped to available cells
 *   - no formula parsing — raw text values only
 *   - does NOT break UI-2A native-control safety: guard checks
 *     document.activeElement before acting on keyboard events
 */
(function () {
  'use strict';

  /* ── helpers ──────────────────────────────────────────────────── */

  function _selMgr() { return window.FcSelectionManager || null; }
  function _registry() { return window.FcGridRegistry || null; }

  function _isNativeControl(el) {
    if (!el) return false;
    var t = el.tagName;
    return t === 'INPUT' || t === 'SELECT' || t === 'TEXTAREA' ||
           t === 'BUTTON' || t === 'A' || el.isContentEditable;
  }

  function _cellValue(cellEl) {
    var inp = cellEl.querySelector && cellEl.querySelector('input,select,textarea');
    if (inp) return inp.value;
    var val = cellEl.querySelector && cellEl.querySelector('.v2-field-value,.v2-field-empty');
    return val ? val.textContent.trim() : (cellEl.textContent || '').trim();
  }

  /* ── copy ─────────────────────────────────────────────────────── */

  function _copy() {
    var sel = _selMgr() && _selMgr().getSelection();
    if (!sel || !sel.addresses || !sel.addresses.length) return false;

    var reg = _registry();
    var cells = sel.addresses.map(function (addr) {
      var cr = reg && reg.cellByAddr(sel.gridId, addr);
      return cr ? _cellValue(cr.el) : '';
    });

    // Determine grid shape for TSV rows
    // addresses are stored in row-major order by FcGridRegistry
    var rows = [];
    var currentRow = [];
    var prevRow = null;
    sel.addresses.forEach(function (addr, i) {
      var cr = reg && reg.cellByAddr(sel.gridId, addr);
      var rowIdx = cr ? cr.row : i;
      if (prevRow !== null && rowIdx !== prevRow) {
        rows.push(currentRow.join('\t'));
        currentRow = [];
      }
      currentRow.push(cells[i]);
      prevRow = rowIdx;
    });
    if (currentRow.length) rows.push(currentRow.join('\t'));
    var tsv = rows.join('\n');

    navigator.clipboard && navigator.clipboard.writeText(tsv).catch(function () {});
    return true;
  }

  /* ── paste ────────────────────────────────────────────────────── */

  function _paste(text) {
    var sel = _selMgr() && _selMgr().getSelection();
    if (!sel) return;

    var lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
    var reg = _registry();
    var grid = reg && reg.getGrid(sel.gridId);
    if (!grid) return;

    var startCr = reg.cellByAddr(sel.gridId, sel.activeAddr || sel.anchorAddr);
    if (!startCr) return;

    var startRow = startCr.row;
    var startCol = startCr.col;

    lines.forEach(function (line, rowOffset) {
      var tokens = line.split('\t');
      tokens.forEach(function (token, colOffset) {
        var targetCr = reg.cellAt(sel.gridId, startRow + rowOffset, startCol + colOffset);
        if (!targetCr) return;
        var el = targetCr.el;
        if (!el) return;
        if (el.dataset.fcEditable === 'false') return;

        var inp = el.querySelector && el.querySelector('input:not([type="hidden"]),select,textarea');
        if (!inp) return;

        inp.value = token;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        // Submit the enclosing form
        var form = inp.closest && inp.closest('form');
        if (form) {
          try { form.requestSubmit(); } catch (e) { form.submit(); }
        }
      });
    });
  }

  /* ── keyboard handler ─────────────────────────────────────────── */

  function _onKeyDown(evt) {
    if (!evt.ctrlKey && !evt.metaKey) return;
    var ae = document.activeElement;
    if (_isNativeControl(ae)) return;

    if (evt.key === 'c' || evt.key === 'C') {
      if (_copy()) evt.preventDefault();
    } else if (evt.key === 'v' || evt.key === 'V') {
      evt.preventDefault();
      navigator.clipboard && navigator.clipboard.readText().then(_paste).catch(function () {});
    }
  }

  /* ── init ─────────────────────────────────────────────────────── */

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;
    document.addEventListener('keydown', _onKeyDown);
    return true;
  }

  window.FcClipboardManager = { init: init };
  init();
})();
