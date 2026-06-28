/*
 * Finco One — Live Modelling Layer
 * C2-PR8: First End-to-End Incremental Runtime Slice (client-side
 * RESPONSE RENDERER only — receives the JSON response from a real
 * POST /model/preview network call made elsewhere (see
 * static/modelling/live-model.js's flushScheduledRecalc()), validates
 * it defensively, and patches exactly ONE existing, NON-FINANCIAL
 * Overview status DOM element. This module never makes a network
 * call itself, never evaluates a financial formula, never calls Save
 * or Run, never touches persistence or export, and never throws.)
 *
 * Reference: docs/C2_PR1_IMPLEMENTATION_NOTE.md through
 *            docs/C2_PR7_BACKEND_PREVIEW_ENDPOINT_CONTRACT_STUB_NOTE.md,
 *            docs/C2_PR8_FIRST_RUNTIME_SLICE.md.
 *
 * Ownership: window.FcRuntimeRenderer is a new, standalone module —
 * like FcDependencyGraph (C2-PR4), FcRecalcExecutor (C2-PR5), and
 * FcRecalcPreview (C2-PR6/PR7), deliberately not folded into
 * FcLiveModel. It owns no dirty-state, scheduler, dependency-graph, or
 * execution state of any kind — it is a pure, stateless DOM-patching
 * consumer of a server response object it is handed by its caller.
 *
 * Input contract: render(responseBody) where responseBody is expected
 * to be shaped like the POST /model/preview JSON response (see
 * main_web.py's model_preview() route / docs/C2_PR7_*.md /
 * docs/C2_PR8_FIRST_RUNTIME_SLICE.md), in particular:
 *   {
 *     ok: true,
 *     ...,
 *     overview: { runtime_status: "<string>", updated: <boolean> }
 *   }
 * `render()` NEVER throws, for any input, including `null`/
 * `undefined`/a non-object/a malformed `overview` field/a response
 * with `ok: false`/a response from a network error path (the caller
 * is expected to pass `null` or an error-shaped object on fetch
 * failure — see live-model.js). On anything that doesn't validate, it
 * is a safe no-op: it does not touch the DOM at all, and the existing
 * status text is left exactly as it was.
 *
 * Output: returns a small diagnostic result object
 *   { rendered: <boolean>, reason: <string> }
 * for callers/tests that want to confirm what happened, but this
 * return value is informational only — nothing in this module's own
 * logic depends on a caller reading it.
 *
 * DOM contract: patches exactly one existing element,
 * #overview-runtime-status-value (inside the always-rendered
 * #overview-runtime-status status region in
 * app/templates/partials/workspace_shell.html's Overview tab). This
 * element holds a plain runtime STATUS string (e.g. "Preview
 * executed"), never an IRR/DSCR/revenue/tax/other real KPI number —
 * deliberately chosen so this slice can never be mistaken for a real
 * recalculation having occurred. If the element is not present in the
 * DOM (e.g. an isolated test fixture, or a future page that doesn't
 * render the Overview tab), this is a safe no-op.
 *
 * This module does NOT:
 *   - make any network/AJAX/htmx call of any kind
 *   - evaluate any formula or call app/waterfall_core.py, domain/*,
 *     or any other financial code
 *   - call Save, Run, or any backend endpoint other than reading the
 *     response object it is handed
 *   - mutate FcLiveModel dirty state, the recalc scheduler,
 *     FcDependencyGraph's registry, or FcRecalcExecutor/FcRecalcPreview
 *     state
 *   - touch any other DOM element, KPI value, or persistence/export
 *     surface
 */
(function () {
  'use strict';

  var STATUS_VALUE_ELEMENT_ID = 'overview-runtime-status-value';

  function _isNonEmptyString(v) {
    return typeof v === 'string' && v.length > 0;
  }

  /**
   * Defensive, non-throwing shape-check for a POST /model/preview
   * response body's "overview" field specifically. Returns true only
   * when `overview` is an object with a non-empty string
   * `runtime_status` field (the only field this module actually
   * renders). `updated` is tolerated as present-or-absent/any type —
   * it is informational metadata only, not required for rendering.
   */
  function _hasRenderableOverview(body) {
    if (!body || typeof body !== 'object') return false;
    var overview = body.overview;
    if (!overview || typeof overview !== 'object') return false;
    return _isNonEmptyString(overview.runtime_status);
  }

  /**
   * Renders a parsed POST /model/preview response body by patching
   * the single #overview-runtime-status-value DOM element with the
   * response's overview.runtime_status string. Never throws.
   *
   * Safe-no-op cases (all return { rendered: false, reason: ... }):
   *   - `body` is null/undefined/not an object (e.g. a network error
   *     was passed through by the caller instead of a parsed response)
   *   - `body.overview` is missing or malformed
   *   - `body.overview.runtime_status` is missing or not a non-empty
   *     string
   *   - the target DOM element does not exist on the current page
   *
   * Deterministic: the same valid input always produces the same DOM
   * text content, synchronously, with no animation/timing/randomness
   * involved.
   */
  function render(body) {
    if (!body || typeof body !== 'object') {
      return { rendered: false, reason: 'no-response-body' };
    }

    if (!_hasRenderableOverview(body)) {
      return { rendered: false, reason: 'missing-or-malformed-overview' };
    }

    var el = (typeof document !== 'undefined' && document.getElementById)
      ? document.getElementById(STATUS_VALUE_ELEMENT_ID)
      : null;
    if (!el) {
      return { rendered: false, reason: 'target-element-not-found' };
    }

    var runtimeStatus = body.overview.runtime_status;
    el.textContent = runtimeStatus;
    el.setAttribute('data-c2pr8-runtime-status', 'patched');

    return { rendered: true, reason: 'ok' };
  }

  window.FcRuntimeRenderer = {
    render: render,
    statusValueElementId: STATUS_VALUE_ELEMENT_ID
  };
})();
