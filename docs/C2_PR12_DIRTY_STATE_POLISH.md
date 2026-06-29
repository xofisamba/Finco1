# C2-PR12 — Dirty State Polish

## Scope

A known, previously-logged P1 issue (first documented as a deliberate
fast-follow in `docs/C2_PR10_CAPEX_TOTAL_PREVIEW.md`'s "P1 fast-follow
issue" section): after a successful Save, `#workspace-strip-dirty`'s
TEXT remained stuck at `"Unsaved edits"` for several seconds (in
practice: until the next Run completed), even though
`#workspace-unsaved-banner` correctly hid immediately. This PR fixes
that, and only that — it is a small, localized change to
`static/app.js`, with no change to Save's actual persistence behaviour,
trigger, or request/response contract.

## Root cause

`static/app.js` maintains two parallel notions of "the workspace's
dirty meta":

1. `_lastServerMeta` — the most recent meta object that genuinely came
   from the server (via `/scenarios/state/draft`, `/scenarios/{id}/load`,
   or `/scenarios/state/discard`'s JSON responses). `/scenarios/save`'s
   HTMX response is **not** one of these — it only swaps
   `#saved-scenario-panel`'s HTML and never calls
   `applyWorkspaceStateMeta()` itself (this asymmetry already existed
   before this PR and is unchanged by it — see the inline comment above
   the `btn-save` `htmx:afterRequest` handler).
2. `FcLiveModel`'s own canonical client-side dirty boolean (`true`/
   `false`), unrelated to any server round trip.

The `btn-save` button's `htmx:afterRequest` handler (added in C2-PR2)
correctly calls `window.FcLiveModel.clearAllDirty()` on a successful
Save. That emits FcLiveModel's `'project-clean'` event, which
`_syncDirtyFromLiveModel()` (also from C2-PR2) listens for. That
function rebuilds a merged meta object — `effectiveDirty = liveDirty ||
!!base.dirty` where `base` is `_lastServerMeta` — and correctly computed
`merged.dirty = false` (since both `liveDirty` and `base.dirty` are now
false). **That correctly-computed `false` is exactly why the banner
hid immediately** — `applyWorkspaceStateMeta()`'s banner-toggle line
(`banner.classList.toggle('is-hidden', !meta.dirty)`) reacted to it
correctly, on the spot.

But the bug was in `merged.dirty_label`. The pre-existing code only had
one branch that set `dirty_label` explicitly — the "just went dirty"
case (`if (liveDirty && !base.dirty) { merged.dirty_label = 'Unsaved
edits'; }`). There was **no corresponding branch for "just went
clean"** — so on the clean transition, `merged.dirty_label` silently
fell through to whatever property `_lastServerMeta.dirty_label` already
held, which was still `"Unsaved edits"` from before the Save (because,
as noted above, Save's own response never refreshes
`_lastServerMeta` — only a subsequent `/scenarios/state/draft` debounce
fire, or a Run, would do that). `applyWorkspaceStateMeta()`'s strip-text
line (`if (stripDirty && meta.dirty_label) stripDirty.textContent =
meta.dirty_label;`) is gated only on `dirty_label` being truthy, not on
`dirty` itself — so it dutifully (and incorrectly) kept painting the
stale `"Unsaved edits"` text onto `#workspace-strip-dirty`, even though
`meta.dirty` was already correctly `false` and had already correctly
hidden the banner in the very same function call.

In short: **`meta.dirty` (the banner's gate) was always correct and
immediate; `meta.dirty_label` (the strip text's gate) was the only
stale field, because nothing ever explicitly set it on the clean
transition.** The "lag until the next Run" previously observed was
simply "until the next genuine server meta — which a Run's response
is — overwrites `_lastServerMeta.dirty_label` with a fresh clean
label."

## The fix

One new `else if` branch in `_syncDirtyFromLiveModel()`
(`static/app.js`), entered exactly when the merged state is genuinely
clean (`!effectiveDirty`), which explicitly sets
`merged.dirty_label = 'Clean saved state'` — the same clean-state
wording already used server-side by
`app/services/scenario_state_service.py` and
`app/services/run_service.py`, so no new user-visible wording was
invented:

```js
if (liveDirty && !base.dirty) {
  merged.dirty_label = 'Unsaved edits';
} else if (!effectiveDirty) {
  merged.dirty_label = 'Clean saved state';
}
```

This makes the strip text and the banner update on the exact same
synchronous `applyWorkspaceStateMeta(merged)` call, with no dependency
on a subsequent Run or draft-persist round trip, and no new event,
timer, or polling introduced.

### Why this doesn't poison `_lastServerMeta`

`_syncDirtyFromLiveModel()` calls `applyWorkspaceStateMeta(merged)`
inside the existing `_applyingFromLiveModelSync = true` guard (already
present before this PR). `applyWorkspaceStateMeta()`'s own first lines
only update `_lastServerMeta` when `_applyingFromLiveModelSync` is
`false` — so this synthetic `"Clean saved state"` label is applied to
the DOM but never written back into `_lastServerMeta` itself. The next
genuine server round trip (a Run, a draft-persist tick, a scenario
load/discard) still starts from the real last-known server meta, not
from this overlay's synthetic value — exactly the same non-poisoning
guarantee C2-PR2 already relied on for the "just went dirty" branch.

## Confirmation Save's actual behaviour is unchanged

- The `btn-save` button's `hx-post="/scenarios/save"`, `hx-include`,
  `hx-target`, and `hx-swap` attributes (`app/templates/base.html`) are
  untouched.
- `main_web.py`'s `/scenarios/save` route is untouched — `git diff
  --stat origin/main -- main_web.py` for this route's section is empty
  beyond what PR9 already touched in an unrelated function; no new
  diff was introduced by this PR.
- The only change is what the CLIENT does, client-side, with the
  already-existing `htmx:afterRequest` event fired after a successful
  Save response — it still persists data exactly as before, still
  requires the same button click trigger, and still calls
  `FcLiveModel.clearAllDirty()` exactly as before. This PR adds zero
  new network requests of any kind (confirmed by the regression test
  `test_save_still_fires_zero_preview_requests`, a direct regression
  check that Save itself never fires `/model/preview`).
- C2-PR11's preview value/state is unaffected by this change:
  `FcLiveModel.clearAllDirty()` only ever touches FcLiveModel's own
  dirty bookkeeping and (via the pub/sub chain above) the dirty
  banner/strip text — it has no code path into
  `FcRuntimeRenderer`/`#capex-total-preview-value`/
  `#overview-runtime-status-value` at all, so a Save can never blank or
  reset a previously-rendered preview value or its state label.

## Files changed

- `static/app.js` — one new `else if` branch (6 lines of logic + a
  documentation comment) inside the pre-existing
  `_syncDirtyFromLiveModel()` function. No other function, event
  binding, or behaviour in this file changed.
- `tests/test_c2_pr12_dirty_state_polish_browser.py` — new Playwright
  test file (see PR description / final report for the full list).
- `docs/C2_PR12_DIRTY_STATE_POLISH.md` — this note.

## Guardrail confirmation

`static/app.js` is the one file in this entire PR chain explicitly
expected and required to change for this fix — see the PR description
/ final report for its exact, complete diff. No other guardrailed path
(`domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, `main_web.py`, persistence/export logic)
was touched.
