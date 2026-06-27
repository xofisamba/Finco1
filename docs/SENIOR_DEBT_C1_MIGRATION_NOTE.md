# Senior Debt C1 Integration — Fifth Real-Sheet Migration

## Scope

This migrates the production Senior Debt sheet
(`app/templates/partials/sheet_senior_debt.html`, the `{% include %}`
target rendered into `<div class="tab-panel"
id="panel-senior-debt">` in `workspace_shell.html`) onto the C1
Spreadsheet Interaction Layer, using the same `data-fc-*` contract
proven on CAPEX, OPEX, Inputs, and Revenue.

It does **not** start C2, implement recalculation or a dependency
graph, migrate any other sheet, or change persistence, export,
calculations, or project factories. No `domain/*` file,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` was touched.

## Key findings that shaped this migration

Senior Debt is structurally unlike any prior C1 sheet — it is **not**
an item-loop grid. It has four distinct regions:

1. **"Debt Facility Summary" `editable-grid-table`** — 4 rows, each
   with a real, already-editable `<input class="editable-grid-input"
   data-grid-source="...">` (`gearing_pct`, `target_dscr`,
   `interest_rate_pct`, `tenor_years`). Unlike OPEX (zero editable
   cells) or Revenue/CAPEX (mixed), **all 4 of these are genuinely
   editable today, unconditionally** — there is no `is_user_project`
   gate on this table in the production template at all (the
   surrounding card explicitly says "These controls update draft
   workspace state only," i.e. editability is always on, regardless
   of project protection status).
2. **`assumption-grid` of 4–5 read-only `<div class="assumption-
   item">` metric displays** (Facility Amount, Tenor, All-in Rate,
   Target DSCR, and conditionally Indicative Gearing) — always
   non-editable, computed/derived display values.
3. **A read-only "Output Preview" notice card** — static text, no
   data, out of scope (nothing to address).
4. **A JS-driven `<div id="shared-runtime-block">`** populated from
   `sessionStorage.lastRuntimeSummary` by the inline `<script>` block
   — this is dynamic client-side state, not server-rendered
   `project_ctx` data, so (mirroring how OPEX's legacy
   `<details class="opex-legacy-summary">` block was left out of
   scope) it is **explicitly excluded** from the C1 contract. Wrapping
   it would not add real value: `FcGridRegistry` indexes static
   `data-fc-addr` attributes resolved at render time, and this
   block's content only exists after a JS callback fires
   asynchronously post-load.

**Important factual finding on `data-fc-raw` for the draft inputs**:
unlike the original task hypothesis (that draft inputs might have no
server-rendered value and thus need `data-fc-raw=""`), reading the
actual template confirmed each of the 4 `<input
class="editable-grid-input">` elements has **no `value="..."`
attribute on the `<input>` itself** (it is populated/synced
client-side from draft workspace state, e.g. localStorage, by other
JS not touched here) — **but** `project_ctx` does carry a real
server-side value for each of the 4 underlying fields
(`project_ctx.gearing_pct`, `project_ctx.target_dscr`,
`project_ctx.interest_rate_pct`, `project_ctx.senior_tenor_years`),
which is the project's last-saved/runtime value. This migration uses
that `project_ctx` value as `data-fc-raw` on the wrapping `<td>`
(not on the `<input>`), so Copy/Read of these cells through
`FcCellIO` reflects the real saved value, while the `<input>`
itself remains exactly as it was — populated by its own pre-existing
client-side draft logic, untouched. This is a deliberate, documented
choice: `data-fc-raw` is the C1 contract's read surface and is
correctly backed by the real server value; the `<input>`'s
*displayed* value remains the separate, pre-existing draft-workspace
concern.

## What was implemented

`sheet_senior_debt.html` gained, on the existing `.sheet-card`
wrapping both the editable-grid-table and the assumption-grid:

- grid root + scroll container: `data-fc-grid="seniordebt"
  data-fc-scroll-container="true"` — a single shared grid root for
  both the `<table>` rows and the `<div>` rows, rather than two
  separate `data-fc-grid` containers (see "Address scheme" below for
  why a single grid root was sufficient and simpler).
- each `<tr>` in the editable-grid-table: `data-fc-row="true"`.
- each `<td>` wrapping a draft `<input>`: `data-fc-cell="true"`,
  `data-fc-addr`, `data-fc-kind="text"`, `data-fc-editable="true"`,
  `data-fc-raw` (see finding above).
- each `.assumption-item` `<div>`: `data-fc-row="true"`.
- each `.metric-value` `<span>` inside it: `data-fc-cell="true"`,
  `data-fc-addr`, `data-fc-kind="text"`, `data-fc-editable="false"`,
  `data-fc-raw` holding the underlying numeric `project_ctx` value
  (not the formatted display string, e.g. `data-fc-raw="0.05"` while
  the visible text is `"5.00% p.a."`).

**Address scheme** — deterministic, reusing the existing
`data-grid-source` value (kept on the `<input>`, unchanged) as the
draft-input address suffix, and a `_summary` suffix for the
assumption-grid metrics to keep them namespace-distinct from the
draft-input addresses:

| Cell | Address |
|---|---|
| draft gearing input | `seniordebt!gearing_pct` |
| draft target DSCR input | `seniordebt!target_dscr` |
| draft interest rate input | `seniordebt!interest_rate_pct` |
| draft tenor input | `seniordebt!tenor_years` |
| Facility Amount summary | `seniordebt!facility_amount` |
| Tenor summary | `seniordebt!tenor_summary` |
| All-in Rate summary | `seniordebt!interest_rate_summary` |
| Target DSCR summary | `seniordebt!target_dscr_summary` |
| Indicative Gearing summary (conditional) | `seniordebt!gearing_pct_summary` |

A single grid root (`seniordebt`) covers both regions because
`FcGridRegistry.scan()` already supports `data-fc-row`/`data-fc-cell`
resolution via `.closest()` regardless of whether the row is a
`<tr>` or a `<div>`, and the two regions never collide on address
(draft inputs have no `_summary` suffix; summary cells always do).
Splitting into two `data-fc-grid` containers was considered and
rejected as unnecessary complexity — there is no behavioural reason
(navigation, selection, or addressing) that requires two grids here.

### Scope honesty note

This sheet, being smaller and not item-loop shaped, uses far fewer
addressable cells than CAPEX/OPEX/Revenue (9 total: 4 draft inputs +
4–5 summary cells) — this is expected and accurately reflects the
sheet's actual size, not an under-migration.

### Existing behaviour preserved

No `<input>`, `data-grid-source`, draft-persistence wiring, or the
inline `<script>`'s `sessionStorage`-driven runtime-summary logic was
changed. IDs (`shared-runtime-block`, `runtime-block-kpis`,
`sd-senior-debt`, etc.) are untouched.

### `FcCellIO` reused as-is

No changes to `static/interaction/cell-io.js` were needed.
`writeValue()` already permits writes when `cell.editable` is true
(the draft inputs) and refuses them when false (the summary cells) —
exactly the split this sheet needs.

### Cross-cutting interaction-layer fixes required

None.

## New tests

- `tests/test_senior_debt_c1_markup_contract.py` — static render of
  `sheet_senior_debt.html` standalone with a hand-built `project_ctx`.
  Covers: grid root, scroll container, every cell has
  addr/kind/editable, no duplicate addresses across both regions,
  deterministic addresses, known address examples, draft inputs
  always editable, summary cells always non-editable, draft-input and
  summary `data-fc-raw` values match the real `project_ctx` numeric
  fields (the finding documented above), deterministic ordering
  across renders, and the optional gearing-summary cell correctly
  omitted when `project_ctx.gearing_pct` is falsy (pre-existing `{%
  if %}` untouched). 13/13 passing.
- `tests/test_senior_debt_c1_migration_browser.py` — production-route
  Playwright smoke test seeded from the Oborovo template via
  `/projects/create`, `window.switchTab('senior-debt')`. Covers: grid
  presence, unique addresses, both the `<table>` and `<div>` regions
  registering under the same `seniordebt` grid, draft inputs editable
  with a real `<input>`, summary cells non-editable with no `<input>`,
  Active Cell, Keyboard Navigation, Shift+Arrow selection, Copy reads
  raw, paste writes to a draft input, paste onto a summary cell
  no-ops, a real edit + Undo round trip, raw values on summary cells
  matching the real seeded `project_ctx` (tenor=15), and an htmx-swap
  re-scan. 13/13 passing.

## Test results

Combined regression for this stacked PR (Revenue + Senior Debt):

1. **Markup-contract tests** (no browser dependency):
   `pytest tests/test_revenue_c1_markup_contract.py
   tests/test_senior_debt_c1_markup_contract.py -v` → **26/26 passing**
   (13 Revenue + 13 Senior Debt).
2. **Browser tests** (Playwright/chromium):
   `pytest tests/test_revenue_c1_migration_browser.py
   tests/test_senior_debt_c1_migration_browser.py -v` → **25/25
   passing** (12 Revenue + 13 Senior Debt) — chromium was available in
   this environment, so these ran for real rather than being skipped.
3. **Full C1/C2 + all real-sheet-migration regression**: all C1-PR1
   through C1-PR9, C2-PR1, and the CAPEX/OPEX/Inputs/Revenue/Senior
   Debt C1 migration test files collected and run together — see
   exact pass/fail/skip counts in the PR description and commit
   message, captured at commit time.
4. **Zero financial-logic changes confirmed**: `git diff --stat
   main...HEAD -- domain app/waterfall_core.py app/input_adapter.py
   app/project_factories.py` is empty — none of these files were
   touched by this migration.

## Out of scope / deferred

- Any other sheet (Tax, Compare, dashboard).
- C2, incremental recalculation, a dependency graph, or formula
  evaluation.
- The JS-driven `shared-runtime-block` (sessionStorage-backed runtime
  summary) — not server-rendered `project_ctx` data, so not a fit for
  the static `data-fc-*` contract; left untouched, as OPEX left its
  legacy summary block out of scope.
- The static "Output Preview" notice card — no data to address.
- Any change to `domain/*`, `app/waterfall_core.py`,
  `app/input_adapter.py`, `app/project_factories.py`, persistence, or
  export logic.
- Reconciling the draft-input `<input>`'s own (unsaved,
  client-side-only) displayed value with `data-fc-raw`'s
  server-sourced value — these are two intentionally separate
  concerns (see "Key findings" above); unifying them would be a
  product/behaviour change, not an interaction-layer wrapper.

## Suggested next sheet

With CAPEX, OPEX, Inputs, Revenue, and Senior Debt now migrated, Tax
or the Compare view are reasonable next candidates.
