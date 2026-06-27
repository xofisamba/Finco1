/*
 * Finco One — Live Modelling Layer
 * C2-PR1: LiveModel (infrastructure foundation only — dirty-state
 * tracking, change batching, live edit session state, a stub
 * recalculation scheduler, and an event pipeline for future
 * incremental recalculation; no financial recalculation, no
 * dependency graph, no formula evaluation, no Save/Run integration)
 *
 * Reference: docs/C1_INTERACTION_LAYER_DESIGN.md,
 *            docs/C1_PR1_IMPLEMENTATION_NOTE.md through
 *            docs/C1_PR9_IMPLEMENTATION_NOTE.md,
 *            docs/C2_PR1_IMPLEMENTATION_NOTE.md.
 *
 * Responsibility in this PR is limited to:
 *   - tracking which cells/sheets/the project are "dirty" (have an
 *     edit that hasn't been accounted for yet)
 *   - batching consecutive edits to the same cell into one net
 *     change ({addr, before (first), after (latest)}) per live edit
 *     session
 *   - tracking a lightweight "live edit session" (started lazily on
 *     the first dirty edit, ended explicitly), summarising what
 *     changed
 *   - a scheduler abstraction that only queues and flushes plain
 *     event objects — it never executes calculation work itself, and
 *     is the seam C2-PR2 (Incremental Recalculation) will consume
 *   - a minimal synchronous pub/sub (on/off/emit) for
 *     'cell-dirty' / 'sheet-dirty' / 'project-dirty' /
 *     'session-started' / 'session-ended' / 'batch-flush'
 *   - observing the one genuinely observable edit path that exists
 *     today: a native `change` event on a real
 *     <input>/<select>/<textarea> living inside a [data-fc-cell].
 *     This is the same event FcClipboardController's `_setCellValue`
 *     (and, via it, paste/undo/redo/fill) already dispatches after
 *     writing a cell, so this module observes every kind of cell
 *     write the C1 interaction layer already performs without
 *     calling into, modifying, or duplicating any of those modules'
 *     state
 *
 * This module does NOT:
 *   - run any financial recalculation, dependency graph, or formula
 *     evaluation — the scheduler only queues/flushes plain event
 *     objects, it never calls a function or computes a value
 *   - trigger Save, Run, persistence, or export — those remain
 *     entirely separate, unaffected workflows
 *   - duplicate FcGridRegistry/FcActiveCellManager/
 *     FcSelectionManager/FcUndoManager state — it only reads cell
 *     identity (gridId/addr) from the DOM event target via the same
 *     [data-fc-grid]/[data-fc-cell]/data-fc-addr markup contract
 *     every other C1 module already uses
 *   - fake dirty tracking for a plain-text cell with no real
 *     input/select/textarea descendant — exactly the same
 *     "don't fake what isn't observable" discipline C1-PR8 applied to
 *     cell-edit capture
 */
(function () {
  'use strict';

  // _dirtyCells[gridId] = Set of addr strings
  var _dirtyCells = {};
  // _dirtySheets = Set of gridId strings
  var _dirtySheets = {};
  var _projectDirty = false;

  // _pendingBatch[gridId][addr] = { gridId, addr, before, after }
  var _pendingBatch = {};

  var _session = null; // { id, startedAt } | null
  var _nextSessionId = 1;

  var _listeners = {}; // eventName -> [handler, ...]

  var _schedulerQueue = [];

  function on(eventName, handler) {
    if (!eventName || typeof handler !== 'function') return;
    if (!_listeners[eventName]) _listeners[eventName] = [];
    _listeners[eventName].push(handler);
  }

  function off(eventName, handler) {
    if (!_listeners[eventName]) return;
    var idx = _listeners[eventName].indexOf(handler);
    if (idx !== -1) _listeners[eventName].splice(idx, 1);
  }

  function _emit(eventName, detail) {
    var handlers = _listeners[eventName];
    if (!handlers || !handlers.length) return;
    // Snapshot so a handler removing itself mid-emit is safe.
    handlers.slice().forEach(function (handler) {
      handler(detail);
    });
  }

  function isSessionActive() {
    return !!_session;
  }

  function getSession() {
    if (!_session) return null;
    return { id: _session.id, startedAt: _session.startedAt };
  }

  function startSession() {
    if (_session) return _session.id;
    _session = { id: _nextSessionId++, startedAt: Date.now() };
    _emit('session-started', { id: _session.id });
    return _session.id;
  }

  /**
   * Ends the current live edit session (if any), returning a summary
   * of everything that changed during it. Does not clear dirty state
   * or the pending batch by itself — dirty state intentionally
   * outlives a session until something else (e.g. a future Save
   * integration in a later PR) explicitly clears it.
   */
  function endSession() {
    if (!_session) return null;
    var summary = {
      id: _session.id,
      dirtyCells: getDirtyCells(),
      dirtySheets: getDirtySheets(),
      projectDirty: _projectDirty,
      batch: getBatch()
    };
    _session = null;
    _emit('session-ended', summary);
    return summary;
  }

  function getDirtyCells(gridId) {
    if (gridId) {
      return _dirtyCells[gridId] ? Object.keys(_dirtyCells[gridId]) : [];
    }
    var all = [];
    Object.keys(_dirtyCells).forEach(function (g) {
      Object.keys(_dirtyCells[g]).forEach(function (addr) {
        all.push({ gridId: g, addr: addr });
      });
    });
    return all;
  }

  function getDirtySheets() {
    return Object.keys(_dirtySheets);
  }

  function isCellDirty(gridId, addr) {
    return !!(_dirtyCells[gridId] && _dirtyCells[gridId][addr]);
  }

  function isSheetDirty(gridId) {
    return !!_dirtySheets[gridId];
  }

  function isProjectDirty() {
    return _projectDirty;
  }

  function clearDirty(gridId) {
    if (gridId) {
      delete _dirtyCells[gridId];
      delete _dirtySheets[gridId];
      delete _pendingBatch[gridId];
      _projectDirty = Object.keys(_dirtySheets).length > 0;
      return;
    }
    _dirtyCells = {};
    _dirtySheets = {};
    _pendingBatch = {};
    _projectDirty = false;
  }

  /**
   * Marks a single cell (and transitively its sheet/the project)
   * dirty, accumulates it into the pending batch (coalescing
   * consecutive edits to the same cell into one net before/after
   * pair), queues a plain "cell-changed" event onto the scheduler,
   * and emits the dirty pub/sub events. Never throws; missing
   * gridId/addr is a no-op.
   */
  function markCellDirty(gridId, addr, before, after) {
    if (!gridId || !addr) return;

    startSession();

    if (!_dirtyCells[gridId]) _dirtyCells[gridId] = {};
    _dirtyCells[gridId][addr] = true;

    var sheetWasDirty = !!_dirtySheets[gridId];
    _dirtySheets[gridId] = true;
    _projectDirty = true;

    if (!_pendingBatch[gridId]) _pendingBatch[gridId] = {};
    var existing = _pendingBatch[gridId][addr];
    _pendingBatch[gridId][addr] = {
      gridId: gridId,
      addr: addr,
      before: existing ? existing.before : before,
      after: after
    };

    var event = { type: 'cell-changed', gridId: gridId, addr: addr, before: before, after: after };
    _schedulerQueue.push(event);

    _emit('cell-dirty', { gridId: gridId, addr: addr, before: before, after: after });
    if (!sheetWasDirty) _emit('sheet-dirty', { gridId: gridId });
    _emit('project-dirty', { gridId: gridId });
  }

  function getBatch(gridId) {
    if (gridId) {
      return _pendingBatch[gridId] ? Object.keys(_pendingBatch[gridId]).map(function (addr) {
        return _pendingBatch[gridId][addr];
      }) : [];
    }
    var all = [];
    Object.keys(_pendingBatch).forEach(function (g) {
      Object.keys(_pendingBatch[g]).forEach(function (addr) {
        all.push(_pendingBatch[g][addr]);
      });
    });
    return all;
  }

  /**
   * Returns the pending batch (coalesced net changes since the last
   * flush) and clears it. Does not clear dirty-state flags or the
   * scheduler queue — those are independent, separately-cleared
   * concepts.
   */
  function flushBatch(gridId) {
    var batch = getBatch(gridId);
    if (gridId) {
      delete _pendingBatch[gridId];
    } else {
      _pendingBatch = {};
    }
    _emit('batch-flush', { gridId: gridId || null, batch: batch });
    return batch;
  }

  // --- Scheduler: queues/flushes plain event objects only. No
  // function is ever called, no calculation is ever performed here —
  // this is purely the seam C2-PR2 will consume.
  function schedulerQueueLength() {
    return _schedulerQueue.length;
  }

  function schedulerQueueEvent(event) {
    if (!event) return;
    _schedulerQueue.push(event);
  }

  function schedulerFlush() {
    var drained = _schedulerQueue;
    _schedulerQueue = [];
    return drained;
  }

  function schedulerPeek() {
    return _schedulerQueue.slice();
  }

  var scheduler = {
    queueLength: schedulerQueueLength,
    queueEvent: schedulerQueueEvent,
    flush: schedulerFlush,
    peek: schedulerPeek
  };

  // --- DOM wiring: the one genuinely observable edit path.
  function _isFormField(el) {
    return !!(el && el.matches && el.matches('input, select, textarea'));
  }

  function _findCell(el) {
    var cellEl = el.closest ? el.closest('[data-fc-cell]') : null;
    if (!cellEl) return null;
    var gridEl = cellEl.closest ? cellEl.closest('[data-fc-grid]') : null;
    if (!gridEl) return null;
    var gridId = gridEl.getAttribute('data-fc-grid');
    var addr = cellEl.getAttribute('data-fc-addr');
    if (!gridId || !addr) return null;
    var editable = cellEl.getAttribute('data-fc-editable');
    if (editable === 'false') return null;
    return { gridId: gridId, addr: addr };
  }

  var _editBefore = null; // { el, gridId, addr, value }

  function _onFocusIn(evt) {
    var el = evt.target;
    if (!_isFormField(el)) return;
    var resolved = _findCell(el);
    if (!resolved) return;
    _editBefore = {
      el: el,
      gridId: resolved.gridId,
      addr: resolved.addr,
      value: el.value != null ? String(el.value) : ''
    };
  }

  function _onChange(evt) {
    var el = evt.target;
    if (!_editBefore || _editBefore.el !== el) return;

    var before = _editBefore.value;
    var after = el.value != null ? String(el.value) : '';
    var gridId = _editBefore.gridId;
    var addr = _editBefore.addr;
    // Advance the snapshot rather than clearing it, so a second
    // `change` on the same still-focused field (no refocus in
    // between) is tracked as a further incremental edit instead of
    // being silently dropped.
    _editBefore.value = after;

    if (before === after) return;
    markCellDirty(gridId, addr, before, after);
  }

  var _initialized = false;

  function init() {
    if (_initialized) return false;
    _initialized = true;

    document.addEventListener('focusin', _onFocusIn);
    document.addEventListener('change', _onChange);

    return true;
  }

  window.FcLiveModel = {
    init: init,

    markCellDirty: markCellDirty,
    isCellDirty: isCellDirty,
    isSheetDirty: isSheetDirty,
    isProjectDirty: isProjectDirty,
    getDirtyCells: getDirtyCells,
    getDirtySheets: getDirtySheets,
    clearDirty: clearDirty,

    getBatch: getBatch,
    flushBatch: flushBatch,

    startSession: startSession,
    endSession: endSession,
    isSessionActive: isSessionActive,
    getSession: getSession,

    scheduler: scheduler,

    on: on,
    off: off
  };

  init();
})();
