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
 * C2-PR10: additionally, when the response body carries a "capex"
 * field ({ capex_total_preview: <number>, currency: "EUR" }), this
 * module ALSO patches a second, separate, always-rendered element,
 * #capex-total-preview-value (inside #capex-total-preview, next to —
 * never replacing or relabelling — the C2-PR8 runtime status
 * indicator). This is the first and only real numeric value this
 * whole runtime path is allowed to render anywhere: a plain CAPEX
 * line-item SUM of the live, unsaved CAPEX grid, computed entirely
 * client-side (static/modelling/recalc-preview.js) and merely echoed
 * back by the server — never a real financial-engine output, and
 * never confused with the saved/Run-derived Total CAPEX figure shown
 * elsewhere on the CAPEX sheet. Missing/malformed "capex" is a safe
 * no-op for this part only — it never clears or invalidates a
 * previously-rendered overview status, and a missing/malformed
 * "overview" field never blocks rendering a present, valid "capex"
 * field (the two are rendered independently). See
 * docs/C2_PR10_CAPEX_TOTAL_PREVIEW.md.
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
  // C2-PR10: separate target element id for the CAPEX total preview.
  var CAPEX_PREVIEW_VALUE_ELEMENT_ID = 'capex-total-preview-value';

  function _isNonEmptyString(v) {
    return typeof v === 'string' && v.length > 0;
  }

  /**
   * C2-PR10: defensive, non-throwing shape-check for a POST
   * /model/preview response body's "capex" field. Returns true only
   * when "capex" is an object with a finite-number
   * "capex_total_preview" field — the only field this module actually
   * renders. "currency" is tolerated as present-or-absent/any type; it
   * is informational metadata only.
   */
  function _hasRenderableCapexPreview(body) {
    if (!body || typeof body !== 'object') return false;
    var capex = body.capex;
    if (!capex || typeof capex !== 'object') return false;
    var total = capex.capex_total_preview;
    return typeof total === 'number' && isFinite(total);
  }

  /**
   * C2-PR10: formats a CAPEX total preview number for display. Plain,
   * fixed 2-decimal formatting with thousands separators — no currency
   * conversion, no rounding beyond presentation, no calculation beyond
   * what was already summed/rounded by the caller.
   */
  function _formatCapexTotal(total, currency) {
    var formatted;
    try {
      formatted = total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } catch (e) {
      formatted = total.toFixed(2);
    }
    return _isNonEmptyString(currency) ? (formatted + ' ' + currency) : formatted;
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

    var overviewRendered = false;
    var overviewReason = 'missing-or-malformed-overview';

    if (_hasRenderableOverview(body)) {
      var statusEl = (typeof document !== 'undefined' && document.getElementById)
        ? document.getElementById(STATUS_VALUE_ELEMENT_ID)
        : null;
      if (statusEl) {
        statusEl.textContent = body.overview.runtime_status;
        statusEl.setAttribute('data-c2pr8-runtime-status', 'patched');
        overviewRendered = true;
        overviewReason = 'ok';
      } else {
        overviewReason = 'target-element-not-found';
      }
    }

    // C2-PR10: independent second patch — a missing/malformed "capex"
    // field never blocks the overview status patch above, and vice
    // versa. Each is rendered (or safely skipped) on its own merits.
    var capexRendered = false;
    var capexReason = 'missing-or-malformed-capex';

    if (_hasRenderableCapexPreview(body)) {
      var capexEl = (typeof document !== 'undefined' && document.getElementById)
        ? document.getElementById(CAPEX_PREVIEW_VALUE_ELEMENT_ID)
        : null;
      if (capexEl) {
        capexEl.textContent = _formatCapexTotal(body.capex.capex_total_preview, body.capex.currency);
        capexEl.setAttribute('data-c2pr10-capex-preview', 'patched');
        capexRendered = true;
        capexReason = 'ok';
      } else {
        capexReason = 'target-element-not-found';
      }
    }

    if (!overviewRendered && !capexRendered) {
      return { rendered: false, reason: overviewReason, capexReason: capexReason };
    }

    return {
      rendered: overviewRendered || capexRendered,
      reason: overviewRendered ? 'ok' : overviewReason,
      capexRendered: capexRendered,
      capexReason: capexReason
    };
  }

  window.FcRuntimeRenderer = {
    render: render,
    statusValueElementId: STATUS_VALUE_ELEMENT_ID,
    capexPreviewValueElementId: CAPEX_PREVIEW_VALUE_ELEMENT_ID
  };
})();
