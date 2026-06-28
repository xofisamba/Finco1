# C2-PR9: Runtime Request Hardening — Implementation Note

## Scope

C2-PR8 wired up the first real, automatic network call anywhere in the
C2 chain: `FcLiveModel.flushScheduledRecalc()` fires one
`fetch(POST /model/preview)` per flush, handing the parsed JSON
response to `FcRuntimeRenderer.render()`, which patches exactly one
non-financial DOM element (`#overview-runtime-status-value`).

A post-C2 runtime review found one correctness gap in that wiring: it
had no protection against **overlapping requests**. If a user edits a
cell, waits out the 250ms debounce (so a flush + fetch fires), and
then edits again before that fetch resolves, two `/model/preview`
requests are now in flight. Nothing prevented the **older** request's
response from resolving *after* the **newer** one and overwriting the
fresh status text with stale data — exactly the race C2-PR8's own
"What the next PR should build on top of this" section flagged as
"out of scope here, but worth flagging."

This PR closes that gap, and authorizes the endpoint by project, and
nothing else. No financial calculation, KPI logic, Save/Run changes,
persistence, export, dependency-graph changes, or scheduler redesign
were introduced.

## Why stale-response protection is required

A real, future preview computation (the next PR after this one) will
return values that actually differ request-to-request as the model's
dirty state changes. Without ordering protection, a slow earlier
response landing after a fast newer one would silently roll the
visible runtime status backwards — a real, user-visible correctness
bug, not just a cosmetic flicker. It is far cheaper to fix this now,
while the only thing at stake is a static stub string
(`"Preview executed"`), than after a real computation is layered on
top and a regression here would look like "the preview computed the
wrong answer."

## Full request lifecycle

```
flushScheduledRecalc()
  -> snapshot.execution.previewPayload already built (C2-PR5/PR6, unchanged)
  -> abort-previous:
       if a previous preview AbortController exists, call .abort() on it
  -> sequence-capture:
       _previewRequestSeq += 1
       seq = _previewRequestSeq        (this request's own token)
       _previewLatestSeq = seq         (becomes "the newest issued so far")
  -> fresh AbortController created, assigned to _previewAbortController,
     its .signal passed to fetch()
  -> fetch(POST /model/preview, { signal })
  -> .then(res => res.json())
  -> .then(json => {
       sequence-check:
         if (seq !== _previewLatestSeq) return;   // stale — silently ignored
         FcRuntimeRenderer.render(json);            // only the newest renders
     })
  -> .catch(() => {})   // network error, parse error, or AbortError —
                         // all swallowed identically; never throws,
                         // never touches the DOM
```

Both `_previewAbortController` and `_previewRequestSeq`/
`_previewLatestSeq` are module/closure-level state on
`FcLiveModel` (`static/modelling/live-model.js`), exactly like the
existing `_recalcTimer`/`_recalcReason` scheduler state added in
C2-PR3 — no new module was introduced.

## Abort behaviour

- Before every new preview fetch, the previous in-flight
  `AbortController` (if any) has `.abort()` called on it. This is a
  best-effort optimization: it cancels the underlying network request
  where the browser supports it, but its real purpose here is
  documentation/intent — the **authoritative** correctness guarantee
  is the sequence check below, not the abort signal itself.
- `AbortError` (and any other fetch/parse error) is swallowed by the
  existing `.catch()` exactly as C2-PR8 already did for network
  errors — no new error-handling branch was added. An aborted request
  never reaches `FcRuntimeRenderer.render()`.
- `typeof AbortController === 'function'` is checked defensively
  before constructing one; in an environment without it (extremely
  old browser, an isolated test fixture), `controller` is `null`,
  `signal: undefined` is passed to `fetch()` (a safe no-op for
  `fetch`), and the flow degrades to "no abort, sequencing still
  protects against stale renders" rather than throwing.

## Sequence-token behaviour

- `_previewRequestSeq` is a monotonic integer, incremented once per
  issued preview request, never reset.
- `_previewLatestSeq` always holds the sequence number of the most
  recently *issued* request (captured synchronously, before the
  `fetch()` call), not the most recently *resolved* one.
- Each response handler captures its own `seq` value as a local
  variable at issue time (closure capture), then compares it against
  the (possibly-since-advanced) `_previewLatestSeq` when the response
  arrives. Only an exact match renders; everything else — including a
  response from a request that was also aborted — is silently
  discarded, with no throw and no DOM mutation.
- This is the defense-in-depth layer described in the task spec: even
  in a hypothetical environment where an aborted fetch's promise still
  resolves (a known edge case across different `fetch`/`AbortController`
  implementations), the sequence check is the final, authoritative
  gate. Abort and sequencing are independent safeguards; either one
  alone would be enough to prevent the user-visible bug, and together
  they make it essentially impossible.

## Authorization behaviour

`POST /model/preview` (`main_web.py`, `model_preview()`) now checks
project authorization, additively, after the existing shape validation
and before building the success response:

- If the payload's `project` field is `None`, behaviour is **unchanged**
  from C2-PR7/PR8 — no authorization check runs at all.
- If `project` is a non-null string, the route calls
  `get_project_by_code(user.user_id, project_code)` — the exact same
  helper every other project-scoped route in `main_web.py` already
  uses (e.g. `runtime_summary_export`, `institutional_workbook_export`)
  to resolve "does this authenticated user own this project_code." No
  new authorization mechanism was invented.
- `get_project_by_code` is itself scoped by `user_id` in its SQL query
  (`WHERE user_id=? AND project_code=?` in
  `app/persistence/projects_repository.py`), so it returns `None`
  both when the project_code doesn't exist at all and when it exists
  but belongs to a different user — the preview route deliberately
  does not distinguish between these two cases in its response, so it
  can never be used to probe whether a given project_code exists for
  someone else.
- On a `None` result, the route returns, at `200`:
  ```json
  {
    "ok": false,
    "status": "forbidden-project",
    "accepted": false,
    "executed": false,
    "warnings": ["Project access denied."]
  }
  ```
  Never a 500, never a traceback, never any field from the
  payload/another user's project echoed back.
- For an authorized (or null-`project`) request, the success response
  is byte-for-byte identical to the C2-PR7/PR8 contract — PR9 adds zero
  new fields to it.

## Why this is the final runtime hardening step before real financial preview work

C2-PR1 through PR9 deliberately built every layer of this pipeline —
dirty tracking, debounced scheduling, dependency resolution, an
execution stub, a payload builder, a backend contract stub, the first
real wired-up network call, and now request-lifecycle safety and
authorization — as independently-tested, side-effect-free seams. The
one thing every prior PR explicitly deferred was "what happens when a
real computation's result needs to be trusted enough to render."
Before this PR, that trust was unconditional (whatever response
arrived, rendered) and unauthorized by project (any authenticated user
could ask about any project_code). Both gaps are exactly the kind of
correctness bug that is cheap to fix against a static stub string and
expensive to retrofit once a real, varying financial preview value
depends on "is this the newest, authorized answer." With both fixed,
a future PR can replace `model_preview()`'s stub body with an actual
read-only recomputation, secure in the knowledge that the client will
never render a stale or cross-project answer, and the server will
never compute (or, in the future, leak) one user's project data into
another user's session.

## Files changed

- `static/modelling/live-model.js` — `flushScheduledRecalc()` gained
  `AbortController` + sequence-counter state and logic, additive only;
  module header comment updated to document this PR.
- `main_web.py` — `model_preview()` gained one additive project-
  authorization check (reusing `get_project_by_code`, already
  imported); no other route or function changed.
- `tests/test_c2_pr7_backend_preview_endpoint.py` — `_valid_payload()`'s
  default `project` field changed from the placeholder string
  `"demo-project"` (never a project any test user actually owned) to
  `None`, preserving this file's original "no project scoping" intent
  under the new authorization check; this is the one pre-existing test
  file this PR had to touch, and it is a fixture-default change, not a
  behavioural assertion change.
- `tests/test_c2_pr9_runtime_request_hardening.py` — new backend test
  file (13 tests, see below).
- `tests/test_c2_pr9_runtime_request_hardening_browser.py` — new
  Playwright test file (7 tests, see below).
- `docs/C2_PR9_RUNTIME_REQUEST_HARDENING.md` — this note.

## Guardrail confirmations

No changes to `domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, `static/app.js`, or any persistence-write
logic. See the PR description for `git diff --stat` output against
`origin/main` confirming this.
