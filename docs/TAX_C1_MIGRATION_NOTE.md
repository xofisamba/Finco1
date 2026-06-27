# Tax C1 Integration — Sixth Real-Sheet Migration

## Scope

This migrates the production Tax sheet
(`app/templates/partials/sheet_tax.html`, the `{% include %}` target
rendered into `<div class="tab-panel" id="panel-tax">` in
`workspace_shell.html`, tab id `tax`) onto the C1 Spreadsheet
Interaction Layer, using the same `data-fc-*` contract proven on
CAPEX, OPEX, Inputs, Revenue, and Senior Debt.

It does **not** start C2, implement recalculation or a dependency
graph, migrate any other sheet, or change persistence, export,
calculations, or project factories. No `domain/*` file,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` was touched.

## Key findings that shaped this migration

The production Tax sheet is small and entirely read-only — it has
**zero `<input>` elements anywhere**. It is a single `.sheet-card`
("CIT Assumptions") with an `.assumption-grid` of `.assumption-item`
`<div>`s, plus a static "Output Preview" notice card (no data) and a
JS-driven `<div id="shared-runtime-block">` (the same
`sessionStorage`-backed pattern already excluded from C1 scope on
Senior Debt and OPEX, for the same reason: it is populated
client-side post-load, not server-rendered `project_ctx` data).

The CIT Assumptions card has:

- **CIT Rate** and **Loss Carryforward** — always rendered.
- **Convention** badge — always rendered, static text
  (`"AUDIT-ONLY"`).
- **G20 Status** / **R99/R102 Status** — only rendered inside the
  template's own `{% if audit_mode %}` block.

This is flatter than the spec's illustrative per-year examples (e.g.
no `tax!taxable_income.Y1`-style breakdown exists in the real
template) — **this migration does not fabricate a per-year structure
that does not exist in the production markup**, exactly as the
Revenue and Senior Debt migrations documented for their own flat
deviations from the spec's illustrative examples.

## Investigation of the pre-existing Jinja-escaping bug (Step 2)

`docs/INPUTS_C1_MIGRATION_NOTE.md` documents a pre-existing,
unrelated Jinja2 escaping bug in `app/templates/partials/
inputs_section.html`'s Tax Summary card: in the `audit_mode=False`
branch, `tax_rows_normal` is built as a Python-style list literal of
`field_row(...)` macro-call return values (`{% set tax_rows_normal =
[field_row(...), field_row(...)] %}`) instead of `{% set X
%}...{% endset %}` block capture, causing Jinja2 to double-escape the
list of `Markup` objects.

**Investigation outcome: not applicable here — confirmed, not just
assumed.** The real, dedicated Tax tab/sheet is
`app/templates/partials/sheet_tax.html`, an entirely different file
from `inputs_section.html`. `sheet_tax.html` does not contain a
`tax_rows_normal` (or any) list-literal `{% set %}` construct at all
— its `audit_mode` branch is a plain `{% if audit_mode %}...{% endif
%}` block directly in the template, not a macro-call-list capture.
This was confirmed directly:

- by reading `sheet_tax.html` in full (reproduced above) — no
  `tax_rows_normal`-style construct exists in it;
- by rendering `sheet_tax.html` standalone with `audit_mode=False`
  and asserting no `&lt;`/`&amp;lt;`/`&#39;data-fc` escape-leak
  substrings appear in the output (see
  `tests/test_tax_c1_markup_contract.py::
  test_audit_mode_false_renders_without_jinja_errors`);
  and
- by a live-route Playwright check against `panel-tax`'s rendered
  `innerText`, confirming no escaped HTML source is visible as text
  on the page (`tests/test_tax_c1_migration_browser.py::
  test_audit_mode_false_renders_without_visible_escaped_markup`).

**Decision: deferred / out of scope, by design — no fix needed for
this sheet.** The bug exists only in `inputs_section.html`'s Tax
Summary *card* (a field-row summary that lives on the Inputs sheet),
not on the dedicated Tax sheet `sheet_tax.html` migrated here. Per
the task's guardrails, no opportunistic fix was made to
`inputs_section.html` since this migration's surface never touches
that code path. The bug remains exactly as documented in
`docs/INPUTS_C1_MIGRATION_NOTE.md`, unfixed and unrelated to this PR.

## What was implemented

`sheet_tax.html`'s `.sheet-card` wrapping the CIT Assumptions
`.assumption-grid` gained `data-fc-grid="tax"
data-fc-scroll-container="true"`.

- each `.assumption-item` `<div>`: `data-fc-row="true"`.
- each `.metric-value` / `.badge` `<span>` inside it: `data-fc-
  cell="true"`, `data-fc-addr`, `data-fc-kind="text"`, `data-fc-
  editable="false"` (every cell — there is no `<input>` anywhere on
  this sheet), `data-fc-raw` holding the underlying raw `project_ctx`
  value (or the literal static string for the Convention/G20/R99
  badges, which are hardcoded display text in the template, not
  `project_ctx`-backed).

**Address scheme** — deterministic, using stable field keys, never
display text:

| Cell | Address | Always rendered? |
|---|---|---|
| CIT Rate | `tax!cit_rate` | yes |
| Loss Carryforward | `tax!loss_carryforward` | yes |
| Convention badge | `tax!convention` | yes |
| G20 Status | `tax!g20_status` | only when `audit_mode` |
| R99/R102 Status | `tax!r99_r102_status` | only when `audit_mode` |

### Scope honesty note

This sheet is the smallest yet migrated (5 addressable cells, 3–5
depending on `audit_mode`) — it accurately reflects the sheet's
actual, minimal size (a single small assumptions card), not an
under-migration. Every other element on the page (the runtime-summary
block, the static Output Preview notice, the inline `<script>`) is
out of scope for the same reasons documented on prior migrations (no
server-rendered `project_ctx` data to address, or pure client-side
JS state).

### Existing behaviour preserved

No `<input>` was added (none existed), no `id`, class, or JS hook
(`shared-runtime-block`, `tax-status`, `tax-secondary-metrics`, the
inline `_populateTaxRuntimeBlock` script) was changed. The
`audit_mode` conditionals that gate the G20/R99 fields are entirely
unchanged — the C1 attributes were added inside the existing `{% if
%}` blocks, not by altering their conditions.

### `FcCellIO` reused as-is

No changes to `static/interaction/cell-io.js` were needed.
`writeValue()` already refuses writes when `cell.editable` is false —
exactly the behaviour every cell on this sheet needs, since all of
them are non-editable.

### Cross-cutting interaction-layer fixes required

None. `grid-registry.js` and `focus-manager.js` were spot-checked
(not fully re-read, per the task's guidance, since this was already
confirmed safe for Inputs' non-table layout and Senior Debt's mixed
layout): both `FcGridRegistry.scan()`'s row/cell discovery and
`FcFocusManager`'s `tabindex` assignment use generic `.closest()` /
attribute-based discovery with no table-specific or input-specific
assumption, so an all-`<div>`/`<span>`, zero-`<input>` grid needed no
JS changes.

## New tests

- `tests/test_tax_c1_markup_contract.py` — static render of
  `sheet_tax.html` standalone with a hand-built `project_ctx`
  (`audit_mode` True and False). Covers: grid root, scroll container,
  every cell has addr/kind/editable, no duplicate addresses,
  deterministic addresses, known address examples, every cell is
  non-editable, no real `<input>` anywhere, the audit-only fields
  present only when `audit_mode=True` and absent when `False`,
  deterministic ordering across renders, `audit_mode=False` renders
  without leaking escaped HTML markup (the direct regression check
  tied to the Step 2 investigation above), and raw values match the
  real `project_ctx` numeric fields. 14/14 passing.
- `tests/test_tax_c1_migration_browser.py` — production-route
  Playwright smoke test seeded from the Oborovo template via
  `/projects/create`, `window.switchTab('tax')`. Covers: grid
  presence, unique addresses, every cell non-editable with no
  `<input>`, Active Cell, Keyboard Navigation, Shift+Arrow selection,
  Copy reads raw, paste onto a read-only cell is a no-op, Undo is a
  safe no-op when nothing was ever editable/edited
  (`FcUndoManager.canUndo()` is `false`, `Ctrl+Z` does not throw), an
  `audit_mode=False` visible-text escape-leak check against the real
  rendered `panel-tax` (the production route always renders with
  `audit_mode=False` — see `main_web.py`), and an htmx-swap re-scan.
  11/11 passing.

## Test results

- New tests: 14/14 (`test_tax_c1_markup_contract.py`) + 11/11
  (`test_tax_c1_migration_browser.py`) passing.
- See the PR description / commit for the combined per-category
  regression run (full C1, C2-PR1, CAPEX, OPEX, Inputs, Revenue,
  Senior Debt, Tax, Export/Audit), each run as its own isolated
  `pytest` invocation.
- Zero financial-logic changes confirmed: `git diff --stat
  main -- domain app/waterfall_core.py app/input_adapter.py
  app/project_factories.py` is empty.

## Guardrail diff

This migration touches exactly one production template file
(`app/templates/partials/sheet_tax.html`), plus the two new test
files and this document. No fix was made to `inputs_section.html`
(see Step 2 investigation above — not needed for this sheet). No
`domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, persistence, export, or calculation-engine
file was touched.

## Out of scope / deferred

- Any other sheet (Export/Audit migrated in this same stacked PR;
  Compare, dashboard remain unmigrated).
- C2, incremental recalculation, a dependency graph, or formula
  evaluation.
- The JS-driven `shared-runtime-block` (sessionStorage-backed runtime
  summary) — not server-rendered `project_ctx` data.
- The static "Output Preview" notice card — no data to address.
- Fixing the pre-existing `inputs_section.html` `tax_rows_normal`
  list-literal escaping bug — confirmed not to affect this sheet's
  migration; left exactly as documented in
  `docs/INPUTS_C1_MIGRATION_NOTE.md`.
- Any change to `domain/*`, `app/waterfall_core.py`,
  `app/input_adapter.py`, `app/project_factories.py`, persistence, or
  export logic.

## Suggested next sheet

With CAPEX, OPEX, Inputs, Revenue, Senior Debt, Tax, and Export/Audit
now migrated, the Compare view or dashboard overview are reasonable
next candidates.
