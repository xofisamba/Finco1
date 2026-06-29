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
 * C2-PR11 (Runtime Preview UX Polish): the previous binary Idle/
 * "Preview executed" status text is replaced with an explicit 5-state
 * machine — Idle, "Preview updating…", "Preview ready", "Preview
 * unavailable", "Preview failed" — driven by THREE new, additive,
 * non-throwing entry points this module exposes for the request
 * lifecycle's caller (static/modelling/live-model.js) to call at the
 * appropriate moment:
 *
 *   - setUpdating()    — call right before a preview fetch is issued.
 *   - setUnavailable() — call when there is nothing to preview yet
 *                        (e.g. a flush produced no previewPayload, no
 *                        dirty cells, or fetch/FcRecalcPreview isn't
 *                        available) instead of issuing a fetch at all.
 *   - setFailed(seq)   — call from the fetch's .catch()/non-2xx branch.
 *
 * `render(body)` itself becomes the "success" transition (-> "Preview
 * ready"), and is UNCHANGED in its own validation/patch logic — it
 * still patches `#overview-runtime-status-value`'s text to whatever
 * `body.overview.runtime_status` says (still just a status string,
 * still never a financial value) and `#capex-total-preview-value`'s
 * text/badge class to the formatted CAPEX sum, independently, exactly
 * as before. C2-PR11 only adds the explicit state machine bookkeeping
 * (the `data-c2pr11-runtime-state` attribute, the `aria-busy`
 * attribute on the two parent `.runtime-status-indicator` elements,
 * and the `#…-sr` visually-hidden announcement spans) around the
 * existing patches — it does not change what triggers a render or what
 * value gets rendered on success.
 *
 * CRITICAL invariant carried over from C2-PR9's staleness guard,
 * restated here because it is this PR's most safety-critical
 * correctness rule: a `setFailed()` call (or any other non-success
 * state transition) must NEVER blank, reset, or otherwise touch the
 * last successfully-rendered VALUE text of either
 * `#overview-runtime-status-value` or `#capex-total-preview-value` —
 * it only ever changes the STATE label/attributes layered on top of
 * whatever value is already displayed. Only a genuinely newer
 * successful `render()` call is ever allowed to replace a displayed
 * value. `setFailed()`/`setUnavailable()`/`setUpdating()` are pure
 * state-label transitions; they never write to either `__value`
 * element's `textContent` at all — they only touch
 * `data-c2pr11-runtime-state`/`aria-busy`/the `#…-sr` announcement
 * text. The caller (`live-model.js`) is responsible for the existing
 * C2-PR9 sequence-token check that already gates whether a given
 * response is even allowed to reach `render()`/`setFailed()` at all
 * for a given request; this module does not re-implement or weaken
 * that guard — it is a pure consumer of "the caller has already
 * decided this is the response for the newest request."
 *
 * See docs/C2_PR11_PREVIEW_UX_POLISH.md for the full state machine
 * (all 5 states, every valid transition, and exactly what triggers
 * each).
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

  // C2-PR11: the two parent status-region elements (used for aria-busy)
  // and the two visually-hidden screen-reader announcement spans.
  var OVERVIEW_REGION_ELEMENT_ID = 'overview-runtime-status';
  var OVERVIEW_SR_ELEMENT_ID = 'overview-runtime-status-sr';
  var CAPEX_REGION_ELEMENT_ID = 'capex-total-preview';
  var CAPEX_SR_ELEMENT_ID = 'capex-total-preview-sr';

  // C2-PR11: the explicit 5-state machine. See
  // docs/C2_PR11_PREVIEW_UX_POLISH.md for the full description of every
  // valid transition between these states.
  var STATE = {
    IDLE: 'idle',
    UPDATING: 'updating',
    READY: 'ready',
    UNAVAILABLE: 'unavailable',
    FAILED: 'failed'
  };

  var STATE_LABEL = {
    idle: 'Idle',
    updating: 'Preview updating…',
    ready: 'Preview ready',
    unavailable: 'Preview unavailable',
    failed: 'Preview failed'
  };

  function _isNonEmptyString(v) {
    return typeof v === 'string' && v.length > 0;
  }

  function _getEl(id) {
    return (typeof document !== 'undefined' && document.getElementById)
      ? document.getElementById(id)
      : null;
  }

  /**
   * C2-PR11: shared bookkeeping helper for BOTH status regions —
   * always sets `data-c2pr11-runtime-state` on the value element,
   * `aria-busy` on the parent region element, and the visually-hidden
   * `#…-sr` announcement span's text. Never throws; a missing element
   * for any of the three ids involved is a safe partial no-op.
   *
   * Does NOT touch `textContent` itself — callers decide that
   * separately (see `_setOverviewState`/`_setCapexState` below), since
   * the two regions have different value-preservation rules: the
   * Overview status element's "value" IS the state label itself (its
   * one and only content is a plain runtime status string — C2-PR8's
   * own design choice, unchanged here), so it is always safe and
   * correct to update its displayed text on every transition. The
   * CAPEX preview element's value is a real computed number that must
   * NEVER be touched by a non-success transition — only `render()`'s
   * own value-patching code ever writes that element's text.
   */
  function _setBookkeeping(valueElementId, regionElementId, srElementId, state, srPrefix) {
    var label = STATE_LABEL[state] || STATE_LABEL[STATE.IDLE];
    var valueEl = _getEl(valueElementId);
    if (valueEl) {
      valueEl.setAttribute('data-c2pr11-runtime-state', state);
    }
    var regionEl = _getEl(regionElementId);
    if (regionEl) {
      regionEl.setAttribute('aria-busy', state === STATE.UPDATING ? 'true' : 'false');
    }
    var srEl = _getEl(srElementId);
    if (srEl) {
      srEl.textContent = srPrefix + label;
    }
    return { state: state, label: label, valueEl: valueEl };
  }

  /**
   * C2-PR11: transitions the Overview runtime-status region to `state`.
   * Unlike the CAPEX region, this element's displayed text IS the
   * state label (it has never shown anything but a plain status string
   * since C2-PR8), so every transition safely updates
   * `#overview-runtime-status-value`'s `textContent` to the new
   * label — there is no separate "value" to preserve here distinct
   * from the status itself.
   */
  function _setOverviewState(state) {
    var result = _setBookkeeping(
      STATUS_VALUE_ELEMENT_ID, OVERVIEW_REGION_ELEMENT_ID, OVERVIEW_SR_ELEMENT_ID,
      state, 'Runtime preview status: '
    );
    if (result.valueEl) {
      result.valueEl.textContent = result.label;
    }
  }

  /**
   * C2-PR11: transitions the CAPEX preview region's state-machine
   * bookkeeping ONLY — CRITICALLY, this never writes to
   * `#capex-total-preview-value`'s `textContent`. That element's text
   * is a real computed number; only `render()`'s own existing
   * value-patching code (the success edge) is ever allowed to change
   * it. A failed/unavailable/updating transition leaves whatever
   * number (or the initial "—" placeholder) was already displayed
   * completely untouched — only `data-c2pr11-runtime-state`,
   * `aria-busy`, and the `#capex-total-preview-sr` announcement change.
   */
  function _setCapexState(state) {
    _setBookkeeping(
      CAPEX_PREVIEW_VALUE_ELEMENT_ID, CAPEX_REGION_ELEMENT_ID, CAPEX_SR_ELEMENT_ID,
      state, 'CAPEX preview status: '
    );
  }

  /**
   * C2-PR11: call right before a preview fetch is issued (i.e. at the
   * very start of a flush that is about to call fetch(POST
   * /model/preview)). Transitions BOTH the overview and CAPEX status
   * regions to "Preview updating…" / aria-busy="true". Never throws.
   * Never touches `#capex-total-preview-value`'s displayed text.
   */
  function setUpdating() {
    _setOverviewState(STATE.UPDATING);
    _setCapexState(STATE.UPDATING);
  }

  /**
   * C2-PR11: call when the pipeline determines there is nothing to
   * preview yet for this flush (no previewPayload was built, no dirty
   * cells, FcRecalcPreview/fetch unavailable, etc.) — i.e. instead of
   * ever issuing a fetch at all. Transitions to "Preview unavailable".
   * Never throws. Never touches `#capex-total-preview-value`'s
   * displayed text.
   */
  function setUnavailable() {
    _setOverviewState(STATE.UNAVAILABLE);
    _setCapexState(STATE.UNAVAILABLE);
  }

  /**
   * C2-PR11: call from the fetch's failure path (network error, non-2xx
   * status, or a JSON parse failure) for the response belonging to the
   * NEWEST issued request (the caller's existing C2-PR9 sequence-token
   * check is what decides this — this function does not re-check
   * staleness itself, it trusts its caller). Transitions to "Preview
   * failed".
   *
   * CRITICAL: this NEVER blanks, resets, or otherwise alters the
   * previously-rendered CAPEX preview VALUE text — only its state
   * label/aria-busy/sr-announcement change. The Overview status
   * element's text DOES change to "Preview failed" (that element's
   * text has always been a pure status string with no separate "value"
   * to preserve — see `_setOverviewState`). A user who has a valid
   * CAPEX preview number on screen and then experiences one failed
   * request continues to see that exact number, with only the Overview
   * status text and the CAPEX region's state attributes changing.
   * Never throws.
   */
  function setFailed() {
    _setOverviewState(STATE.FAILED);
    _setCapexState(STATE.FAILED);
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
        // C2-PR11: a successful render is the ONLY transition into
        // "Preview ready" — the success edge of the state machine.
        // Uses the shared `_setBookkeeping` helper directly (NOT
        // `_setOverviewState`, which would overwrite the real
        // `runtime_status` text just written above with the generic
        // "Preview ready" label) so only the state-machine bookkeeping
        // (data-c2pr11-runtime-state/aria-busy/sr text) changes here,
        // never the just-written value text.
        _setBookkeeping(STATUS_VALUE_ELEMENT_ID, OVERVIEW_REGION_ELEMENT_ID, OVERVIEW_SR_ELEMENT_ID, STATE.READY, 'Runtime preview status: ');
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
        // C2-PR11: success edge -> "Preview ready" bookkeeping for the
        // CAPEX region, in lockstep with the value patch immediately
        // above. Uses `_setBookkeeping` directly (not `_setCapexState`,
        // though they're equivalent here) for symmetry with the
        // Overview branch above.
        _setBookkeeping(CAPEX_PREVIEW_VALUE_ELEMENT_ID, CAPEX_REGION_ELEMENT_ID, CAPEX_SR_ELEMENT_ID, STATE.READY, 'CAPEX preview status: ');
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
    // C2-PR11: explicit state-machine transitions for the request
    // lifecycle's caller (live-model.js) to drive.
    setUpdating: setUpdating,
    setUnavailable: setUnavailable,
    setFailed: setFailed,
    states: STATE,
    stateLabels: STATE_LABEL,
    statusValueElementId: STATUS_VALUE_ELEMENT_ID,
    capexPreviewValueElementId: CAPEX_PREVIEW_VALUE_ELEMENT_ID
  };
})();
