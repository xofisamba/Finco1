# C2 Operating Preview — Architecture Checkpoint

A concise handoff/checkpoint document for the next reviewer (human or
Claude) before any further work touches the preview pipeline or any
adjacent module. Written after C2-PR10 through C2-PR23, from direct
reading of the current codebase plus `docs/C2_PR10_*.md` through
`docs/C2_PR20_*.md`.

## C1 interaction layer status

**Editable today** (client-side, via `data-fc-editable="true"` cells
wired to `FcGridRegistry`/`FcCellIO`):

- CAPEX amount cells (`sheet_capex.html`, `data-fc-kind="amount"`).
- Revenue line-item cells (`sheet_revenue.html`, `data-fc-kind="text"`).
- OPEX Budget cells for non-contingency lines on user-owned (duplicated)
  projects (`sheet_opex_detail.html`, `data-fc-kind="amount"`, added by
  C2-PR17). The `<input>` deliberately has **no `name=` attribute** —
  see "Preview-only OPEX boundary" below.

**Still read-only/deferred:**

- OPEX category/section subtotal rows, contingency-category lines,
  Inflation %, WHT %, and per-year (Y1…Yn) columns.
- All cells on protected/reference (non-`is_user_project`) projects.
- Everything in Senior Debt, SHL, Tax, P&L, Cashflow, Balance,
  Distributions, Sponsor, and Audit tabs — none of this has any C1
  editability or C2 preview wiring at all.

## C2 runtime pipeline status

Five preview slices exist today, in dependency order:

1. **CAPEX total preview** (C2-PR10) — client-side sum of editable
   CAPEX amount cells.
2. **Revenue total preview** (C2-PR13) — client-side sum of editable
   Revenue line-item cells.
3. **OPEX total preview** (C2-PR14, unblocked by C2-PR17) — client-side
   sum of editable OPEX Budget cells.
4. **EBITDA preview** (C2-PR15) — `Revenue preview − OPEX preview`,
   pure arithmetic on (2) and (3); `null` unless both are non-null in
   the same flush.
5. **Operating Cash Flow preview** (C2-PR16) — verbatim passthrough of
   (4). **Not authoritative** — see below.

C2-PR21 consolidated all five rendered indicators into one panel
("Operating preview (unsaved)") on the Overview tab; no calculation
logic changed.

## Preview request lifecycle

1. User edits an editable C1 cell → cell is marked dirty
   (`dependency-graph.js`).
2. A debounced scheduler (`live-model.js`) waits for the edit burst to
   settle.
3. On flush, `recalc-preview.js`'s `buildPreviewPayload()` reads every
   dirty cell's live DOM value via `FcCellIO.readValue()`, recomputes
   any of the five totals whose grid was touched by this flush's dirty
   set, and assembles the request payload (`dirtyCells`,
   `affectedGroups`, `capexTotalPreview`, `revenueTotalPreview`,
   `opexTotalPreview`, `ebitdaPreview`, `operatingCashFlowPreview`,
   etc.).
4. `live-model.js` `fetch()`-POSTs the payload to `/model/preview`,
   tagging the request with a monotonically increasing sequence token
   (see "AbortController / stale response protection" below).
5. `main_web.py`'s `model_preview()` route validates each optional
   numeric field (finite or null; reject NaN/Infinity/strings/
   booleans), checks project authorization, and **echoes** each
   present, valid field back rounded to 2dp under matching response
   keys (`capex`, `revenue`, `opex`, `ebitda`, `operating_cash_flow`).
   No financial engine call, no persistence write.
6. On response, `runtime-renderer.js`'s `render()` patches each of the
   five `#*-preview-value` elements independently — a missing/invalid
   field for one slice never blocks another — and updates the 5-state
   machine (Idle / Preview updating… / Preview ready / Preview
   unavailable / Preview failed).

## Project authorization

`/model/preview` accepts an optional `project` field in the payload.
When present and non-null, the route calls
`get_project_by_code(user.user_id, project_code)` — the same ownership
lookup used by every other project-scoped route in `main_web.py` — and
returns a safe "forbidden" response if the project code does not
resolve to a project owned by the current user. A `null`/absent
`project` field is accepted (treated as "no project context," used by
most of the backend test suite's payloads) and does not require
ownership resolution.

## AbortController / stale response protection

Established in C2-PR9: each preview flush is tagged with a
monotonically increasing sequence number (`_previewLatestSeq`). When a
response for an older sequence arrives after a newer flush has already
started (e.g. due to network reordering or a slow request), the
renderer's `seq === _previewLatestSeq` check discards it — only the
response for the most recent flush is ever allowed to reach
`render()`/`setFailed()`. This guarantees a fast double-edit can never
have its second edit's preview clobbered by a slower first response
arriving late.

## Preview-only OPEX boundary

C2-PR17 made OPEX Budget cells genuinely editable in the browser
(non-contingency lines, user-owned projects only), specifically to
unblock the OPEX → EBITDA → Operating Cash Flow preview chain. The
decision, confirmed by direct inspection of `main_web.py`'s form-field
list, was that these edits remain **preview-only**: the `<input>` has
no `name=` attribute, so Save structurally cannot persist it (there is
no `opex_{code}_keur` form field/route handler, unlike CAPEX's
`capex_{code}_keur`). C2-PR18 added a plain-language note on the OPEX
sheet ("OPEX line edits are preview-only for now. They update the live
preview, but are not saved yet. Run uses the saved model inputs.") so
this boundary is visible to users, not just to engineers reading code.

## Current operating preview stack

| Slice | Computed from | Null when |
|---|---|---|
| CAPEX preview | DOM sum of editable CAPEX amount cells | grid unavailable / no parseable cells |
| Revenue preview | DOM sum of editable Revenue line cells | grid unavailable / no parseable cells |
| OPEX preview | DOM sum of editable OPEX Budget cells | grid unavailable / no parseable cells (always null on protected projects) |
| EBITDA preview | Revenue preview − OPEX preview | either input null |
| Operating Cash Flow preview | EBITDA preview, verbatim | EBITDA preview null |

EBITDA and Operating Cash Flow only become non-null when both Revenue
and OPEX were edited and settled within the **same** debounce flush —
they are never computed from stale values carried over from an earlier
flush.

## What is real calculation vs preview-only

**None** of the five preview values are computed by the real financial
engine (`domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`). Every one of them is pure client-side
arithmetic (a DOM sum, or a subtraction/passthrough of two other DOM
sums), sent to the server purely for validation and echo — the server
never re-derives, re-sums, or second-guesses the client's numbers.

## What is not yet authoritative

- **OPEX persistence** — OPEX Budget edits never reach the database.
- **Debt, Tax, IRR, DSCR, cash-flow waterfall** — none of these have
  any preview at all today, authoritative or otherwise. Editing a CAPEX/
  Revenue/OPEX cell has zero effect on any debt schedule, tax line, IRR/
  DSCR figure, or waterfall distribution shown anywhere in the app —
  those are only ever recomputed by a real Save+Run.

## Known limitations

- OPEX line edits are not persisted (by design, see above) — a future
  PR would need a new per-line form-field convention plus
  `domain`-level storage-shape changes to `app/ui/project_context.py`'s
  group/contingency total computation.
- Debt/Tax/IRR/DSCR/waterfall have no preview slice of any kind yet.
- Exports (`/exports/runtime-summary.csv`,
  `/exports/institutional-workbook.xlsx`) and Save/Run intentionally
  use only the saved model — confirmed end-to-end by C2-PR22's new
  guardrail tests (`tests/test_c2_pr22_export_run_safety_guardrails.py`),
  which post a sentinel preview value and assert it never appears in
  export output and never mutates the DB.

## Recommended next options

In rough order of likely value/effort tradeoff for the next PR:

1. **Debt preview** — would require a client-side approximation of
   debt sizing/sculpting, which is meaningfully more complex than a
   plain sum (gearing ratio, DSCR-driven sizing); likely the next
   logical and most-requested slice given EBITDA/OCF already exist.
2. **Tax preview** — depends on a chosen depreciation/tax-rate
   approximation; lower complexity than Debt but still a real
   modelling decision, not a pure sum.
3. **OPEX persistence** — closes the PR17/18 gap; primarily
   domain/storage-shape work (`app/ui/project_context.py`), not preview
   pipeline work.
4. **Backend service extraction** — `main_web.py`'s
   `_c2_pr7_validate_preview_payload()`/`model_preview()` have grown
   one validation/response branch per preview slice across 7+ PRs;
   worth extracting into a dedicated `app/services/preview_service.py`
   once a 6th/7th slice is added, to keep the route thin.
5. **A larger Claude review** before touching Debt/Tax/IRR/DSCR/
   waterfall previews specifically, since those are the first previews
   that would require real modelling judgment calls rather than plain
   arithmetic — higher risk of a previewed number silently drifting
   from the authoritative engine's own assumptions if not reviewed
   carefully up front.
