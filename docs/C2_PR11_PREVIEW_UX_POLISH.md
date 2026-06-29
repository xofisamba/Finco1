# C2-PR11 — Runtime Preview UX Polish

## Scope

C2-PR8 through C2-PR10 wired up a real, automatic `POST /model/preview`
network call per debounced flush, hardened it with abort/sequence
protection (PR9), and gave it its first real numeric content (PR10's
CAPEX total preview). Throughout all three of those PRs, the only
visible "state" the user ever saw was a binary: the static placeholder
text `"Idle"`, or the fixed stub string `"Preview executed"` once any
response had ever successfully landed. There was no visible feedback
while a request was in flight, no visible feedback on failure, and no
way to tell "nothing has happened yet" apart from "the last preview
attempt failed."

This PR replaces that binary with an explicit 5-state machine, adds a
visual "this is an unsaved preview, not the saved model" distinction to
the CAPEX preview value, and adds the accessibility attributes
(`aria-busy`, an explicit screen-reader announcement) the state machine
needs to be meaningfully non-visual-only. It is **UX/state-machine
only**: zero new calculations, zero new backend routes/fields, zero
changes to what data is computed or sent.

## The 5 states

| State | Label shown | When entered |
|---|---|---|
| `idle` | `Idle` | Initial page load (static markup); never re-entered automatically by this PR's logic once a flush has happened — there is no "go back to Idle" transition wired up, by design (see "Why there's no explicit return-to-Idle transition" below). |
| `updating` | `Preview updating…` | The instant a preview fetch is about to be issued — `FcLiveModel.flushScheduledRecalc()` calls `FcRuntimeRenderer.setUpdating()` immediately before calling `fetch()`, after the abort/sequence-capture step (so the sequence token for this request already exists by the time the UI says "updating"). |
| `ready` | `Preview ready` | A response for the **newest** issued request (per C2-PR9's sequence-token guard) resolves with `res.ok` and valid, render-able JSON. Entered from inside `FcRuntimeRenderer.render()`, in the same branch that just patched the value text — never independently of an actual successful value patch. |
| `unavailable` | `Preview unavailable` | A flush happens but there is nothing preview-able to send (no `previewPayload` was built — e.g. `FcRecalcPreview`/`fetch` unavailable in the current environment) — `flushScheduledRecalc()`'s `else` branch calls `FcRuntimeRenderer.setUnavailable()` instead of ever issuing a fetch. |
| `failed` | `Preview failed` | The response for the **newest** issued request is a network error, a non-2xx HTTP status, or a JSON parse failure. Entered via `FcRuntimeRenderer.setFailed()`, called from the fetch promise chain's `!res.ok` branch or its `.catch()`. A response belonging to a now-superseded (non-newest) request is silently discarded exactly as C2-PR9 already discarded it — `setFailed()` is never called for a stale response. |

## Valid transitions

```
idle ──(flush issues a fetch)──────────────► updating
idle ──(flush has nothing to preview)──────► unavailable

updating ──(newest response: success)──────► ready
updating ──(newest response: failure)──────► failed
updating ──(a NEWER flush starts first)────► updating   (re-entrant; the
                                                          newer flush's own
                                                          setUpdating() call
                                                          simply re-applies
                                                          the same state)

ready ──(next flush issues a fetch)─────────► updating
ready ──(next flush has nothing to preview)─► unavailable

failed ──(next flush issues a fetch)────────► updating
failed ──(next flush has nothing to preview)► unavailable

unavailable ──(next flush issues a fetch)───► updating
unavailable ──(next flush has nothing)──────► unavailable (no-op re-entry)
```

Every transition is driven exclusively by `FcLiveModel.flushScheduledRecalc()`
(via `FcRuntimeRenderer.setUpdating()`/`setUnavailable()`) and by the
preview fetch's own promise chain (via `FcRuntimeRenderer.render()`/
`setFailed()`) — no polling, no timer-driven transition, no transition
triggered by Save, Run, or any other workflow.

### Why there's no explicit return-to-`idle` transition

`idle` is exclusively the page's initial static-markup state. Once a
single edit has happened, the workspace is no longer meaningfully
"nothing has ever been attempted" — even a failed or unavailable
preview is informative state, not "no information yet." Introducing an
artificial "go back to idle" transition (e.g. on Save/Discard) would
contradict PR11's own critical invariant (a state transition must never
imply the previously-shown preview VALUE is gone) for no real user
benefit, so this PR deliberately leaves `idle` reachable only via a
fresh page load.

## Never blanking a valid preview on failure — the critical invariant

The single most safety-critical rule in this PR: **a `setFailed()` (or
`setUnavailable()`/`setUpdating()`) call never writes to either
`#overview-runtime-status-value`'s or `#capex-total-preview-value`'s
`textContent`.** All three of those functions go through one shared,
pure state-label helper (`_setState()` in
`static/modelling/runtime-renderer.js`) that only ever touches:

- `data-c2pr11-runtime-state` on the value element (bookkeeping only),
- `aria-busy` on the parent `.runtime-status-indicator` region element,
- the `textContent` of the dedicated, separate, visually-hidden
  `#…-sr` announcement span.

Only `render()`'s own existing value-patching code (unchanged from
C2-PR8/PR10) ever writes a `__value` element's displayed text, and it
only runs when a genuinely successful, newest-sequence response
arrives. This means: if a user has `"12,345.67 EUR"` showing in the
CAPEX preview and the very next preview request fails, the number
stays exactly `"12,345.67 EUR"` on screen — only the status label next
to it (and the `data-c2pr11-runtime-state`/`aria-busy`/sr-announcement
attributes) change to reflect `failed`.

This builds directly on, and does not weaken, C2-PR9's existing
sequencing/abort guarantees: `setFailed()` is only ever called from the
branch that has already confirmed (via the existing `seq ===
_previewLatestSeq` check) that this is the newest request's outcome — a
stale/superseded request's failure is silently discarded exactly as a
stale success already was before this PR, with no new behaviour added
on that path.

## Accessibility

Both status regions (`#overview-runtime-status`,
`#capex-total-preview`) already had `role="status"` and
`aria-live="polite"` from C2-PR8/PR10. This PR adds:

- `aria-busy="true"` on the region element while its state is
  `updating`; `aria-busy="false"` in every other state (set by the same
  `_setState()` helper, on every transition, so it can never be left
  stuck `"true"`).
- A new, separate, visually-hidden (`.sr-only`) span per region —
  `#overview-runtime-status-sr` / `#capex-total-preview-sr` — whose text
  is always `"Runtime preview status: <state label>"` /
  `"CAPEX preview status: <state label>"`. This gives assistive
  technology an explicit, state-labelled announcement distinct from the
  plain visible value text, without changing what's visually shown.
- The existing `aria-label` on each region element is unchanged
  (`"Live runtime preview status"` / `"Unsaved CAPEX total preview, not
  the saved total"`) — it describes what the region IS, while the new
  `#…-sr` span describes its current STATE; the two are complementary,
  not duplicative.

`.sr-only` is the conventional, standard visually-hidden-but-readable
utility class (clip-rect/1px-box/absolute-position pattern), added once
to `static/styles.css` since no equivalent utility class already
existed in this codebase to reuse.

## Visual "unsaved preview" distinction

`#capex-total-preview-value` now also carries `class="badge
badge-preview-only"` — both pre-existing classes already defined in
`static/styles.css` (`badge-preview-only` was already used elsewhere in
this codebase specifically to mean "an unsaved preview value, not the
persisted figure"). No new CSS rule or visual design was invented; this
PR only adds the existing class to the existing element. The class is
never swapped to `badge-saved` (or any "saved" styling) by this preview
path, since this element never displays a saved/persisted value — it is
exclusively, permanently a preview indicator.

## Files changed

- `static/modelling/runtime-renderer.js` — adds the `STATE`/
  `STATE_LABEL` tables, the shared `_setState()` helper, and three new
  exported functions (`setUpdating`, `setUnavailable`, `setFailed`).
  `render()`'s existing value-patching logic is unchanged; it now
  additionally calls `_setState(..., STATE.READY)` in the same branch
  that patches each value, as the success edge of the state machine.
- `static/modelling/live-model.js` — `flushScheduledRecalc()`'s
  existing C2-PR8/PR9 fetch block gained: a `setUpdating()` call right
  before `fetch()` is issued; a `!res.ok` branch that calls
  `setFailed()` (still gated by the existing sequence check); a
  `setFailed()` call in the existing `.catch()` (also gated by the
  sequence check, so a now-stale/aborted request's failure is still
  silently discarded exactly as before); and a new `else` branch (the
  existing no-fetch no-op condition, now made explicit) that calls
  `setUnavailable()`. No abort/sequencing logic itself was changed.
- `app/templates/partials/workspace_shell.html` — both
  `.runtime-status-indicator` elements gained `aria-busy="false"`
  (initial value) and a new `#…-sr` visually-hidden span;
  `#capex-total-preview-value` gained `class="badge badge-preview-only"`;
  both value elements gained an initial `data-c2pr11-runtime-state="idle"`
  attribute.
- `static/styles.css` — one new `.sr-only` utility class.
- `tests/test_c2_pr11_preview_ux_polish_browser.py` — new Playwright
  test file (see PR description / final report for the full list).
- `docs/C2_PR11_PREVIEW_UX_POLISH.md` — this note.

## Guardrail confirmation

No change to `domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, `main_web.py`, or any persistence/export
code path. `git diff --stat origin/main -- domain app/waterfall_core.py
app/input_adapter.py app/project_factories.py main_web.py` is empty —
see the PR description / final report for the actual command output.
