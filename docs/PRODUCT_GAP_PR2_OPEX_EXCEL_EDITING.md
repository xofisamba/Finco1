# Product Gap PR2/PR3/PR4: OPEX Real Excel Editing + Live Operating Totals

## Summary

Brings the OPEX Detail sheet's editing UX to parity with the CAPEX
sheet (Product Gap PR1, merged): typing a number while an editable
OPEX Budget cell is the active cell now starts editing immediately (no
mouse click into the input required), Enter/Tab (with Shift variants)
commit-and-move like Excel, Escape restores the prior value, and
Category Subtotal / Operating Subtotal / Total OPEX (Y1) update live
in the DOM as you type. This PR also lightly clarifies the existing
preview-only governance copy on the OPEX sheet (PR4) so the chain
"editable values → live sheet totals → preview → Save → Run" reads
consistently.

This is an OPEX-sheet-only UI behaviour change plus a markup/copy
clarification. No backend, no financial-engine, no export, no
persistence-write code was touched.

## Before this PR (current behaviour going in)

- OPEX Budget cells were made genuinely editable by C2-PR17 ("OPEX
  Line Editability Bridge"): `data-fc-editable="true"` for
  non-contingency child lines on user projects, with a real
  `<input class="fc-input-native">` and no `name=` attribute (so Save
  cannot persist them).
- But unlike CAPEX, there was no type-to-edit, no Excel-style
  commit/cancel keyboard handling, and no client-side live subtotal/
  total rendering. Editing a Budget cell required clicking directly
  into the `<input>`, and category subtotals / any "Total OPEX"
  figure on the sheet itself did not move as you typed — only the
  separate `#opex-total-preview-value` indicator (built in C2-PR14,
  driven by a debounced `FcLiveModel` flush) eventually reflected the
  edit.
- C2-PR18 added a plain-language governance note
  (`#opex-preview-only-note`) explaining edits are preview-only and
  not yet saved.

## New behaviour (this PR)

### PR2 — Real OPEX Excel editing

State model: an OPEX Budget cell can be **active-but-not-editing**
(DOM focus on the `<td data-fc-cell>` itself, per existing C1
`FcFocusManager`/`FcActiveCellManager`) or **editing** (DOM focus on
the cell's descendant `<input class="fc-input-native">`).

- While **active-but-not-editing** on an editable OPEX Budget cell:
  - Typing a digit, `.`, or `-` immediately opens the cell's `<input>`
    and **replaces** its entire value with the typed character (exact
    Excel "first keystroke replaces" semantics).
  - Backspace/Delete opens the cell's `<input>` with its value cleared
    to `""`.
  - Any other key (arrows, Home/End, Ctrl+Arrow) is left completely
    untouched — owned exclusively by the pre-existing
    `static/interaction/keyboard-router.js` (`FcKeyboardRouter`).
- While **editing**:
  - Every keystroke except Enter/Tab/Escape is handled natively by the
    `<input>`.
  - **Enter** commits and moves the active cell down one row.
  - **Shift+Enter** commits and moves the active cell up one row.
  - **Tab** commits and moves the active cell right one cell.
  - **Shift+Tab** commits and moves the active cell left one cell.
  - **Escape** restores the cell's pre-edit value and exits edit mode
    without committing.
  - A click/tab-away from the input by any other means is treated as
    an implicit commit via the native `focusout`/blur path.

"Commit" always means: dispatch a final native `change` event on the
`<input>`, so the pre-existing `FcLiveModel`'s `change`-based dirty
tracking observes the edit exactly as it already did before this PR
— this PR adds no new dirty-tracking code path.

#### Structural difference from CAPEX (and why)

CAPEX's grid has exactly one editable amount cell per row (`_line_item_
grid.html` only marks the amount `<td>` with `data-fc-cell`). The OPEX
grid's shape is different: each child row has **one** editable cell
(the Y1 "Budget" cell, `data-fc-addr="opex!<code>.budget"`) plus a
separate, always-read-only set of Y1..Yn "year" `<td>` cells in the
same row, derived server-side from the budget via inflation/active-
flags (`_build_opex_detail_items` in `app/ui/project_context.py`).
Inflation % and WHT % cells are also always read-only. This PR does
not change any of that — Tab/Shift+Tab still has no same-row target to
move into (exactly like CAPEX's single-column-per-row shape), and per
the pre-existing `FcGridRegistry.neighbors()` contract the active cell
simply does not move sideways; Tab still **commits** the edit.

Contingency-category child lines (e.g. Oborovo's `B.13.*`) remain
`data-fc-editable="false"` — unchanged from C2-PR17 — because their
budget is formula-derived (`contingency_pct × sum(non-contingency
OPEX)`), never a user input.

### PR3 — Live OPEX sheet totals

On every `input` event from an OPEX Budget cell's `<input>` (live, per
keystroke), `recomputeLiveTotals()` in
`static/modelling/opex-sheet-live-totals.js` recomputes, purely as
in-sheet DOM text/attribute updates, **Y1-column figures only**:

1. **Category Subtotal (Y1)** — the existing per-category subtotal
   `<td>` in the category band row, now additionally marked
   `data-opex-row="cat-subtotal-<code>"` on its Y1 cell only (e.g.
   `[data-opex-row="cat-subtotal-B.01"]`): the sum of the live
   (possibly mid-edit, unsaved) values of every editable OPEX Budget
   cell in that category (grouped via a new `data-opex-cat="<code>"`
   attribute placed directly on each Budget `<td>`, set server-side —
   no address-string parsing needed, unlike CAPEX's
   `capex!C.01.03.amount` → `C.01` derivation).

2. **Operating Subtotal (Y1)** (`[data-opex-row="operating-subtotal"]`,
   a new row added directly below the last category in the grid,
   mirroring CAPEX's "Hard CAPEX Total" row): the sum of the live
   values of **every** editable OPEX Budget cell across the whole
   `opex` grid. Contingency-category lines are never
   `data-fc-editable="true"`, so they are structurally excluded
   without any special-casing — exactly like CAPEX's C.17/C.18
   exclusion from Hard CAPEX Total.

3. **Total OPEX (Y1)** (`[data-opex-row="grand-total"]`, a new row
   added directly below Operating Subtotal, mirroring CAPEX's "Total
   CAPEX" row):

   > **Total OPEX (Y1, live) = Operating Subtotal (live, as computed
   > above) + the value CURRENTLY DISPLAYED IN THE DOM for every
   > contingency category's Y1 subtotal cell, read verbatim from its
   > existing read-only `data-fc-raw` attribute
   > (`[data-opex-row^="cat-subtotal-"][data-opex-contingency="true"]`).**
   >
   > Contingency category subtotals are **never** recomputed,
   > estimated, or fabricated client-side — they always equal exactly
   > what the backend rendered (`contingency_pct × sum(non-contingency
   > Y1 totals)`, computed in `_build_opex_detail_items`). If,
   > defensively, no contingency category subtotal row is present in
   > the DOM at all (does not happen in the production template when a
   > contingency category exists — purely a defensive fallback for
   > unusual/partial markup), that row's contribution is treated as
   > exactly `0`. In other words: the live Total OPEX always sums
   > **exactly the values currently available/rendered**, and never
   > substitutes a guessed or previously-cached number.

#### Why only the Y1 column is live (and Y2..Yn / "Total OPEX Y{n}" are not)

Unlike CAPEX (a single flat Y1 amount per line), OPEX's Y2..Yn values
are derived server-side from the Y1 Budget via a per-line inflation
rate and active-flag schedule:
`effective_budget(y) × (1 + inflation_rate)^(y-1)`, conditional on
`item.is_active(y)`. Recomputing Y2..Yn client-side would require
reproducing that backend formula (including each line's individual
inflation rate and active-year schedule) in JavaScript — exactly the
kind of "fabricate a number client-side" the spec explicitly forbids.
So this PR's live totals are **Y1-column only**. The existing
`#opex-summary-final` "Total OPEX Y{n}" summary card and every Y2..Yn
grid cell are left exactly as the backend rendered them (frozen),
completely untouched by this module — the same "if it can't be
honestly recomputed client-side, leave it frozen" rule CAPEX PR1
established for C.17/C.18, applied here to an entire dimension (years)
rather than two specific rows.

### PR4 — Save/Preview consistency

- The chain **editable values → live sheet totals → preview → Save →
  Run** remains consistent: editing a Budget cell updates (a) the
  sheet's own Category Subtotal / Operating Subtotal / Total OPEX
  rows synchronously and (b) the existing debounced
  `#opex-total-preview-value` preview indicator, both driven from the
  same underlying edit — neither is invented independently of the
  other, and neither becomes authoritative over Save/Run.
- **Preview is not authoritative.** No code path in this PR writes a
  preview-derived value back into a `name=`-attributed input, and
  Save's `hx-include="#main-form"` continues to submit exactly the
  same fields it always did.
- **Save does not silently overwrite/relabel preview values as
  authoritative.** Save remains blind to OPEX Budget edits entirely —
  the `<input>` carries no `name=` attribute (C2-PR17's decision,
  unchanged), so there is nothing for Save to read back from these
  cells, preview-derived or otherwise.
- **Copy simplified:** the existing C2-PR18 governance note's wording
  was lightly extended (not restructured) to mention that edits update
  "the totals on this sheet" in addition to "the live preview", since
  this PR adds the former for the first time. The note still contains
  the exact phrases `"preview-only for now"`, `"not saved yet"`, and
  `"Run uses the saved model inputs"` (regression-tested by
  `tests/test_c2_pr18_opex_preview_only_governance.py`, unchanged) —
  no internal jargon was added, and the note's placement, class names,
  and scoping to the OPEX panel only are all unchanged.

## Exact live-total rule (precision mirror of PR1's Total CAPEX rule)

```
Operating Subtotal (Y1, live)
  = Σ live value of every [data-fc-grid="opex"] Budget cell where
    data-fc-kind="amount" AND data-fc-editable="true"
    (i.e. every non-contingency child line's Y1 Budget, live/unsaved)

Total OPEX (Y1, live)
  = Operating Subtotal (Y1, live)
  + Σ data-fc-raw of every [data-opex-row^="cat-subtotal-"][data-opex-contingency="true"]
    cell, read VERBATIM from the DOM, NEVER recomputed
    (0 if no such row is present in the DOM — defensive fallback only)
```

Category Subtotal for category `<code>` (Y1, live) = the same sum as
above, filtered to Budget cells where `data-opex-cat="<code>"`.

## Files changed

- **New:** `static/modelling/opex-sheet-live-totals.js` — the entire
  PR2/PR3 feature. OPEX-specific, isolated from the generic C1
  interaction layer (`static/interaction/*.js`) and from the C2
  preview pipeline (`static/modelling/recalc-preview.js`,
  `live-model.js`, `runtime-renderer.js`). None of those files were
  modified. Closely mirrors `static/modelling/capex-sheet-live-
  totals.js`'s architecture (same C1 hooks: `FcGridRegistry`,
  `FcActiveCellManager`, `FcFocusManager`, `FcCellIO`).
- **Modified:** `app/templates/base.html` — added one `<script>` tag
  loading the new module, placed immediately after the CAPEX module's
  `<script>` tag.
- **Modified:** `app/templates/partials/sheet_opex_detail.html`:
  - Added `data-opex-row="cat-subtotal-<code>"` and
    `data-opex-contingency="true|false"` to each category's Y1
    subtotal `<td>` only (Y2..Yn cells of the same row are
    unaffected).
  - Added `data-opex-cat="<code>"` to each child's Budget `<td>`.
  - Added two new rows below the category list: Operating Subtotal
    (`data-opex-row="operating-subtotal"`,
    `data-fc-addr="opex!operating-subtotal.Y1"`) and Total OPEX
    (`data-opex-row="grand-total"`,
    `data-fc-addr="opex!grand-total.Y1"`), both `data-fc-editable=
    "false"`, server-rendered with the same Y1 sums the JS module
    later keeps live — so the page is correct even before JS loads,
    and the JS module's first paint is byte-identical to the
    server-rendered value.
  - Lightly extended the existing C2-PR18 governance note's copy (see
    PR4 above) — no structural/class/id changes.
  - No existing row, cell, attribute, or `<input>` was removed or
    restructured. All pre-existing C2-PR17/PR18 markup contracts
    (editability rule, no `name=` attribute, note placement) are
    unchanged.
- **New:** `tests/test_product_gap_pr2_opex_excel_editing.py` —
  static/route-level tests (no browser).
- **New:**
  `tests/test_product_gap_pr2_opex_excel_editing_browser.py` —
  Playwright browser tests.
- **New:** this doc.

## Save/Run separation guarantee

- `opex-sheet-live-totals.js` makes **zero** network requests of any
  kind. It only reads/writes `textContent` and `data-fc-raw`/`value`
  attributes on already-rendered DOM nodes.
- It adds **no** new `name=`-attributed `<input>` elements and does
  not modify the existing ones. Save's behaviour, route, and persisted
  data are completely unchanged.
- `Run` (`POST /run`) is untouched.
- Browser tests (`test_save_not_triggered_by_typing`,
  `test_run_not_triggered_by_typing`) assert no request to
  `/scenarios/save` or `/run` happens from typing alone.

## Relationship to the existing OPEX preview pipeline (C2-PR14/15/16)

The existing `#opex-total-preview-value` indicator (built in C2-PR14,
inside `static/modelling/recalc-preview.js` /
`static/modelling/runtime-renderer.js`, driven by `FcLiveModel`'s
debounced `change`-based dirty tracking and an actual
`POST /model/preview` round trip) is **completely untouched** by this
PR:

- `recalc-preview.js`, `runtime-renderer.js`, `live-model.js`,
  `recalc-executor.js`, and `dependency-graph.js` were not modified.
- No new `/model/preview` request/response field was added.
- This PR's live subtotal/total rendering is purely additive,
  synchronous, in-sheet DOM text — it runs on every `input` event
  (far more often than the debounced preview flush), and is visually
  distinct from (and does not replace) the existing Operating Preview
  Panel's OPEX/EBITDA/OCF total preview.
- The only interaction between the two: this PR's commit path
  dispatches a final `change` event identical to what a native blur on
  the `<input>` already produced before this PR — so `FcLiveModel`'s
  pre-existing dirty tracking, and therefore the existing preview
  flush/`#opex-total-preview-value` pipeline, continue to work exactly
  as before (verified by `test_opex_preview_panel_still_updates`).

## Tests added

- `tests/test_product_gap_pr2_opex_excel_editing.py` (static/route-
  level, no browser): static wiring, grid-id isolation, no `/model/
  preview` reference, no financial-engine-file reference, contingency
  lines stay read-only / non-contingency lines stay editable, Y2..Yn
  year cells stay read-only, Operating Subtotal/Total OPEX rows
  present and correctly marked, idempotent rendering, no `name=` on
  budget inputs, governance-note regression check.
- `tests/test_product_gap_pr2_opex_excel_editing_browser.py`
  (Playwright, real-uvicorn-subprocess + real-auth + real-project
  fixture, mirroring the CAPEX PR1 browser test fixture exactly): type-
  to-edit without a mouse click, arrow navigation, Enter/Shift+Enter/
  Tab commit-and-move, Escape cancel, live category subtotal /
  Operating Subtotal / Total OPEX updates, Save/Run not triggered by
  typing alone, existing OPEX preview panel still updates, CAPEX PR1
  behaviour re-verified unregressed from the same live server, and
  smoke checks that Revenue / Debt (senior-debt) / Tax preview panels
  still render without page errors.

## Out of scope (explicitly not implemented)

Revenue cleanup, financial statements, debt, tax, IRR, DSCR,
distribution, sponsor, Excel export, financial engine changes,
persistence changes, preview architecture changes, runtime pipeline
redesign, making Y2..Yn OPEX year cells editable (left for future C1
work, exactly as C2-PR17 already deferred it), restructuring the OPEX
panel/governance-note architecture (only its copy was lightly
extended).

## Judgement calls / ambiguities resolved

- **No pre-existing "Operating Subtotal" / "Total OPEX" rows existed
  in the OPEX grid markup** (unlike CAPEX, which already had Hard
  CAPEX Total / Total CAPEX rows from earlier phases). This PR adds
  two new, server-rendered rows directly below the category list,
  using the exact same Y1 sums the live-totals JS module keeps live,
  so first paint (before JS executes) already shows the correct
  server-computed figures — no flash-of-wrong-content.
- **Live totals scoped to the Y1 column only**, not all Y1..Yn columns
  (see the dedicated explanation above) — judged the only option that
  doesn't fabricate a number client-side, consistent with the spec's
  explicit "if a value cannot honestly be recomputed client-side,
  leave the backend-displayed value frozen" instruction.
- **Tab/Shift+Tab "move right/left"** in the OPEX grid: identical
  judgement call to CAPEX PR1 — each row has exactly one navigable
  Budget column, so there is no same-row target; the pre-existing
  `FcGridRegistry.neighbors()` contract is reused rather than inventing
  new column-wrapping semantics.
- **Governance note copy**: kept the exact three required phrases
  (`"preview-only for now"`, `"not saved yet"`,
  `"Run uses the saved model inputs"`) intact to avoid breaking the
  existing C2-PR18 regression test, while adding "they update the
  totals on this sheet and..." so the note now also covers the new
  in-sheet live totals this PR introduces, per PR4's "review existing
  UI wording... make the sheet read like Excel" instruction.
