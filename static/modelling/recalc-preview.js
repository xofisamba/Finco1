/*
 * Finco One — Live Modelling Layer
 * C2-PR6: Incremental Recalculation Preview Boundary (infrastructure
 * only — a deterministic, client-only payload BUILDER describing what
 * a FUTURE backend preview/recalc endpoint would need to receive; this
 * module never calls that endpoint, never makes any network request,
 * never evaluates a formula, never mutates the DOM, and never mutates
 * any dirty-state/recalc-scheduler/dependency-graph/execution state
 * owned by FcLiveModel/FcDependencyGraph/FcRecalcExecutor)
 *
 * Reference: docs/C2_PR1_IMPLEMENTATION_NOTE.md,
 *            docs/C2_PR2_DIRTY_STATE_UNIFICATION_NOTE.md,
 *            docs/C2_PR3_RECALC_SCHEDULER_FOUNDATION_NOTE.md,
 *            docs/C2_PR4_DEPENDENCY_GRAPH_FOUNDATION_NOTE.md,
 *            docs/C2_PR5_INCREMENTAL_RECALC_EXECUTION_STUB_NOTE.md,
 *            docs/C2_PR6_INCREMENTAL_RECALC_PREVIEW_BOUNDARY_NOTE.md.
 *
 * This module answers exactly one question: "given a flushed recalc
 * snapshot and its (stubbed) execution result, what request payload
 * WOULD a future backend preview/recalc call need?" It only BUILDS
 * that payload as a plain-data object; it never sends it anywhere.
 *
 * Ownership: window.FcRecalcPreview is a new, standalone module —
 * like FcDependencyGraph (C2-PR4) and FcRecalcExecutor (C2-PR5),
 * deliberately not folded into FcLiveModel. It owns exactly one piece
 * of state: the most recently built payload (`_lastPreviewPayload`),
 * exposed via getLastPreviewPayload()/clearLastPreviewPayload(). It
 * never reads or writes FcLiveModel's dirty state directly, never
 * computes a dependency mapping, and never performs or duplicates any
 * execution logic — it only reads the `snapshot`/`execution` objects
 * it is handed.
 *
 * Input contract:
 *   buildPreviewPayload(snapshot, execution, options)
 *   - snapshot: shaped like
 *     { grids: [{gridId, addrs: [...]}], projectDirty, affectedGroups: [...] }
 *     (i.e. exactly what FcLiveModel.flushScheduledRecalc() produces,
 *     before or after FcRecalcExecutor.execute() is called).
 *   - execution: shaped like FcRecalcExecutor.execute()'s result
 *     ({status, executed, affectedGroups, dirtyCells, reason}), or any
 *     subset thereof, or omitted/null.
 *   - options: optional; reserved for future use (currently unused
 *     beyond defensive handling — no required fields).
 *   Never throws on malformed/missing snapshot or execution — both
 *   degrade to the safest possible payload rather than raising.
 *
 * Output contract: a deterministic, plain-data payload object:
 *   {
 *     valid: true | false,
 *     dirtyCells: [...sorted, deduplicated fully-qualified "gridId!key"
 *                  strings, derived the same way FcRecalcExecutor
 *                  derives its own dirtyCells field],
 *     affectedGroups: [...sorted, deduplicated group strings, preferring
 *                      execution.affectedGroups when present, falling
 *                      back to snapshot.affectedGroups],
 *     projectDirty: <boolean, from snapshot.projectDirty, default false>,
 *     reason: <string, from execution.reason if present, else
 *              options.reason if present, else "manual-flush">,
 *     executionStatus: <string from execution.status, or null if no
 *                       execution object was supplied/it was malformed>,
 *     project: <string project code from window.location's "project"
 *               query parameter, or null if unavailable — see metadata
 *               handling below; never fabricated>
 *   }
 * No timestamp, session id, or other non-reproducible field appears
 * anywhere in the payload. Two logically-equal (snapshot, execution)
 * pairs — however differently ordered their underlying grids/addrs/
 * groups arrays are — always produce deep-equal payloads.
 *
 * Metadata handling decision: the ONLY project/scenario identifier
 * available anywhere in the existing client without inventing new
 * server-rendered markup is the "project" query-string parameter
 * already present on every production workspace URL (confirmed via
 * tests/test_c2_pr5_recalc_executor_browser.py's fixture:
 * `page.goto(f"{live_server}/?project={project_code}", ...)`, and via
 * grepping app/templates/partials for the many `data-project-code`
 * attributes scattered across narrower partials — none of which are
 * guaranteed to be present/rendered on every workspace page, unlike
 * the URL itself). This module reads it defensively from
 * `window.location.search` via the global URLSearchParams
 * constructor (already used elsewhere in this codebase, e.g.
 * static/app.js's `new URLSearchParams(new FormData(form))` calls);
 * if it's missing, empty, or `window`/`window.location` is somehow
 * unavailable (e.g. a non-browser test harness), `project` is set to
 * `null` — never fabricated, never defaulted to a placeholder string.
 * No scenario identifier is included: no reliable, always-rendered
 * scenario id signal was found in the existing DOM/URL that isn't
 * scoped to a single narrow partial (e.g. scenario_tab.html's
 * data-active-scenario-id, which isn't present on every tab), so this
 * PR omits it entirely rather than reading a possibly-absent element
 * and guessing.
 *
 * This module does NOT:
 *   - evaluate any formula or call app/waterfall_core.py, domain/*,
 *     or any other financial code
 *   - make any network/AJAX/htmx call of any kind, to any endpoint,
 *     ever (this is the single most safety-critical invariant of this
 *     module — it only BUILDS a payload, it never transmits it)
 *   - call Save, Run, or any backend endpoint
 *   - mutate FcLiveModel dirty state, the recalc scheduler,
 *     FcDependencyGraph's (stateless) registry, or FcRecalcExecutor's
 *     last-execution state
 *   - touch the DOM or any rendered KPI/output value
 */
(function () {
  'use strict';

  var _lastPreviewPayload = null;

  function _isNonEmptyString(v) {
    return typeof v === 'string' && v.length > 0;
  }

  function _uniqueSorted(arr) {
    var seen = {};
    var out = [];
    (arr || []).forEach(function (v) {
      if (typeof v === 'string' && !seen[v]) {
        seen[v] = true;
        out.push(v);
      }
    });
    out.sort();
    return out;
  }

  /**
   * Derives the deduplicated, sorted, fully-qualified dirty-cell
   * address list from a snapshot, mirroring FcRecalcExecutor's own
   * `_deriveDirtyCells` exactly (addrs are already "gridId!key"
   * strings — not re-prefixed). Never throws.
   */
  function _deriveDirtyCellsFromSnapshot(snapshot) {
    var cells = [];
    if (snapshot && Array.isArray(snapshot.grids)) {
      snapshot.grids.forEach(function (grid) {
        if (!grid || typeof grid !== 'object') return;
        if (!Array.isArray(grid.addrs)) return;
        grid.addrs.forEach(function (addr) {
          if (typeof addr === 'string' && addr.length) {
            cells.push(addr);
          }
        });
      });
    }
    return _uniqueSorted(cells);
  }

  /**
   * Reads the "project" query-string parameter from the current page
   * URL, defensively. Returns null (never a fabricated placeholder)
   * if window/window.location/URLSearchParams is unavailable, or if
   * the parameter is absent/empty.
   */
  function _readProjectFromLocation() {
    try {
      if (typeof window === 'undefined' || !window.location) return null;
      if (typeof URLSearchParams === 'undefined') return null;
      var params = new URLSearchParams(window.location.search || '');
      var value = params.get('project');
      return _isNonEmptyString(value) ? value : null;
    } catch (e) {
      return null;
    }
  }

  /**
   * Defensive, non-throwing shape-check predicate for a payload built
   * by this module (or any plain object claiming to be one). Returns
   * true only if every required field is present with the right
   * primitive/array type; tolerates `project` being null or a string.
   */
  function validatePreviewPayload(payload) {
    if (!payload || typeof payload !== 'object') return false;
    if (typeof payload.valid !== 'boolean') return false;
    if (!Array.isArray(payload.dirtyCells)) return false;
    for (var i = 0; i < payload.dirtyCells.length; i++) {
      if (typeof payload.dirtyCells[i] !== 'string') return false;
    }
    if (!Array.isArray(payload.affectedGroups)) return false;
    for (var j = 0; j < payload.affectedGroups.length; j++) {
      if (typeof payload.affectedGroups[j] !== 'string') return false;
    }
    if (typeof payload.projectDirty !== 'boolean') return false;
    if (typeof payload.reason !== 'string') return false;
    if (payload.executionStatus !== null && typeof payload.executionStatus !== 'string') return false;
    if (payload.project !== null && typeof payload.project !== 'string') return false;
    return true;
  }

  /**
   * Builds a deterministic preview-request payload from a recalc
   * snapshot and (optional) execution result. Never throws — a
   * malformed snapshot/execution degrades to a safe, explicitly
   * `valid: false` payload with empty dirtyCells/affectedGroups,
   * rather than raising. Records the result as the "last preview
   * payload" (see getLastPreviewPayload/clearLastPreviewPayload).
   *
   * This function performs NO calculation, NO network call, and NO
   * mutation of any dirty-state/scheduler/dependency-graph/execution
   * state — it only reads the snapshot/execution objects it is
   * handed and the current page URL.
   */
  function buildPreviewPayload(snapshot, execution, options) {
    var opts = (options && typeof options === 'object') ? options : {};

    var snapshotIsObject = !!(snapshot && typeof snapshot === 'object');
    var gridsIsArray = snapshotIsObject && Array.isArray(snapshot.grids);
    var valid = snapshotIsObject && gridsIsArray;

    var dirtyCells = valid ? _deriveDirtyCellsFromSnapshot(snapshot) : [];

    var executionIsObject = !!(execution && typeof execution === 'object');

    var affectedGroupsSource = null;
    if (executionIsObject && Array.isArray(execution.affectedGroups)) {
      affectedGroupsSource = execution.affectedGroups;
    } else if (snapshotIsObject && Array.isArray(snapshot.affectedGroups)) {
      affectedGroupsSource = snapshot.affectedGroups;
    }
    var affectedGroups = _uniqueSorted(affectedGroupsSource || []);

    var projectDirty = (snapshotIsObject && typeof snapshot.projectDirty === 'boolean')
      ? snapshot.projectDirty
      : false;

    var reason = 'manual-flush';
    if (executionIsObject && _isNonEmptyString(execution.reason)) {
      reason = execution.reason;
    } else if (_isNonEmptyString(opts.reason)) {
      reason = opts.reason;
    }

    var executionStatus = (executionIsObject && _isNonEmptyString(execution.status))
      ? execution.status
      : null;

    var payload = {
      valid: valid,
      dirtyCells: dirtyCells,
      affectedGroups: affectedGroups,
      projectDirty: projectDirty,
      reason: reason,
      executionStatus: executionStatus,
      project: _readProjectFromLocation()
    };

    _lastPreviewPayload = payload;
    return payload;
  }

  function getLastPreviewPayload() {
    return _lastPreviewPayload;
  }

  function clearLastPreviewPayload() {
    _lastPreviewPayload = null;
  }

  // C2-PR7: backend preview endpoint contract stub now exists at
  // POST /model/preview (see main_web.py / docs/
  // C2_PR7_BACKEND_PREVIEW_ENDPOINT_CONTRACT_STUB_NOTE.md). This is
  // metadata ONLY — no code in this file, or anywhere else in this
  // PR, ever reads this constant to actually perform a fetch.
  var PREVIEW_ENDPOINT = '/model/preview';

  /**
   * C2-PR7: builds a plain-data, request-SHAPED object describing
   * what a FUTURE caller would need to send to the backend preview
   * endpoint contract stub (POST /model/preview) in order to submit
   * `payload`. This function does NOT send anything — no fetch, no
   * XMLHttpRequest, no htmx.ajax/htmx.trigger call exists anywhere in
   * this module. It is inert, unused-by-default infrastructure: no
   * existing code path (FcRecalcExecutor.execute(),
   * FcLiveModel.flushScheduledRecalc(), or any other module) calls
   * this helper automatically. A future PR may choose to wire this up
   * to an actual network call; this PR deliberately does not.
   *
   * Never throws. `payload` is not validated here (callers may pass
   * the result of buildPreviewPayload() directly, or anything else);
   * if `payload` is missing, `body` is simply `null`.
   */
  function buildPreviewRequest(payload) {
    return {
      url: PREVIEW_ENDPOINT,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: (payload && typeof payload === 'object') ? payload : null
    };
  }

  window.FcRecalcPreview = {
    buildPreviewPayload: buildPreviewPayload,
    validatePreviewPayload: validatePreviewPayload,
    getLastPreviewPayload: getLastPreviewPayload,
    clearLastPreviewPayload: clearLastPreviewPayload,
    buildPreviewRequest: buildPreviewRequest,
    previewEndpoint: PREVIEW_ENDPOINT
  };
})();
