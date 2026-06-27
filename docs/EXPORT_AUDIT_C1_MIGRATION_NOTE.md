# Export/Audit C1 Integration — Seventh Real-Sheet Migration

## Scope

This migrates two production surfaces onto the C1 Spreadsheet
Interaction Layer, stacked into the same PR as the Tax migration
(`docs/TAX_C1_MIGRATION_NOTE.md`):

1. **Export** — the "Downloads & Audit Artefacts" tab
   (`<div class="tab-panel" id="panel-downloads">`, tab id
   `downloads`, in `workspace_shell.html`), specifically the "Current
   Export Context" lineage card and the real download links.
2. **Audit** — the "Audit / Reference" tab (`<div class="tab-panel"
   id="panel-audit">`, tab id `audit`), specifically the relocated
   governance/lineage content in
   `app/templates/partials/_audit_governance_relocated.html`.

It does **not** start C2, implement recalculation or a dependency
graph, migrate any other sheet, or change persistence, export logic,
download routes, or project factories. No `domain/*` file,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` was touched, and no `/download`,
`/exports/*` route or handler was touched — only template markup.

## Key findings that shaped this migration

Both surfaces are mostly/fully **read-only display and navigation**,
not data-entry grids — there is no real production `panel-export`;
the actual download/export surface lives in `panel-downloads`.
Grepping `workspace_shell.html` confirmed there is no separate
`panel-export` id anywhere in the codebase.

**Export** (`panel-downloads`) has two regions:

- An `.export-lineage-history` lineage card (`export-lineage-grid`)
  showing the current project/scenario/snapshot context, built from
  `export_lineage_ui.current_context` (assembled in `main_web.py`'s
  `_build_export_lineage_ui_context`).
- A `.downloads-grid` of real `<a href="...">` download links (Excel,
  Runtime CSV, Institutional Workbook) plus three permanently
  disabled "Coming Soon" placeholder `<div>`s (Audit Workbook, Gap
  Register, Source Map) that have **no real `href` or data** — these
  are intentionally left unaddressed (nothing to address; they are
  static "not yet available" notices, not data cells).

**Audit** (`panel-audit`) is gated end-to-end by `{% if audit_mode
%}` in `workspace_shell.html` — the entire relocated governance
partial (`_audit_governance_relocated.html`) only renders when
`audit_mode` is true. Within it: an Export Lineage panel (a near-
duplicate of the Export tab's lineage card, by design — "Hidden !=
deleted" relocation, per the file's own header comment), a Governance
Status card (G20 Gate / R99-R102 Promotion / Equity IRR residual),
and a Reference Evidence card (Senior Debt / SHL Opening /
Distributions / Tax-CFADS pass/fail badges).

**Critical confirmed fact about the production route**: grepping
`main_web.py` shows every workspace-rendering code path hardcodes
`"audit_mode": False` literally — there is no query parameter or
toggle that flips it to `True` on the live `/?project=...` route in
this environment. This means the `audit` grid (entirely inside the
`audit_mode` gate) is migrated and statically test-covered, but is
**not reachable on the live browser route** in this environment. This
is documented explicitly (not silently skipped) in the browser test —
see "New tests" below.

## Choice of grid roots — documented

A single `data-fc-grid="export"` root wraps the whole
`.export-lineage-history` lineage card *and* the `.downloads-grid`
links (both inside `panel-downloads`), following the Senior Debt
precedent of one grid root spanning multiple visually-distinct
regions when there is no behavioural reason to split them.

For Audit, a single `data-fc-grid="audit"` root wraps the entire
`.audit-governance-relocated` outer `<div>` — covering the Export
Lineage panel, the Governance Status card, and the Reference Evidence
card. These three regions are visually distinct `<div class="card">`
blocks but functionally identical (all read-only status/lineage
display), so one shared grid root was simpler and consistent with how
Senior Debt unified its table + non-table regions under one grid.

Two separate grids (`export` + `audit`) were used at the top level —
not one combined `exportaudit` grid — because they are genuinely
distinct tab panels (`panel-downloads` vs. `panel-audit`) with
independent visibility/gating (Export is always visible; Audit is
`audit_mode`-gated) and no shared addressing concern; splitting them
matches how CAPEX/OPEX/etc. each got their own grid id per sheet.

## What was implemented

### Export (`workspace_shell.html`, `panel-downloads`)

- `.export-lineage-history`: `data-fc-grid="export"
  data-fc-scroll-container="true"`.
- each `.export-lineage-card` `<div>`: `data-fc-row="true"`.
- the `.export-lineage-card__value` holding real lineage data:
  `data-fc-cell="true"`, `data-fc-addr`, `data-fc-kind="text"`,
  `data-fc-editable="false"`, `data-fc-raw`.
- each real download `<a class="download-item" href="...">`:
  `data-fc-row="true" data-fc-cell="true" data-fc-addr
  data-fc-kind="text" data-fc-editable="false" data-fc-raw`
  added **directly onto the existing `<a>` tag** — no wrapping
  element was inserted in front of it. The `href` and all other
  existing attributes/classes are untouched.
- the three disabled "Coming Soon" `<div class="download-item
  download-item--disabled">` placeholders were **not** given
  `data-fc-*` attributes — they have no real href/data, matching the
  brief's instruction not to fabricate addresses for non-existent
  data.

**Address scheme**:

| Cell | Address |
|---|---|
| Active project | `export!current_context.project` |
| Saved scenario | `export!current_context.scenario` |
| Scenario revision | `export!current_context.scenario_revision` |
| Last runtime snapshot | `export!current_context.runtime_snapshot_id` |
| Runtime generated at | `export!current_context.runtime_generated_at` |
| Values-only Excel download | `export!workbook_download.values_only` |
| Runtime Summary CSV download | `export!workbook_download.runtime_summary_csv` |
| Institutional Workbook download | `export!workbook_download.institutional_workbook` |

### Audit (`_audit_governance_relocated.html`)

- the outer `.audit-governance-relocated` `<div>`: `data-fc-
  grid="audit" data-fc-scroll-container="true"`.
- each `.export-lineage-card` `<div>` (Export Lineage panel, inside
  the audit surface): `data-fc-row="true"`, value `<div>` gets
  `data-fc-cell="true"`/addr/kind/editable="false"/raw.
- each governance-status / reference-evidence row `<div>`
  (`display:flex; justify-content:space-between`): `data-fc-
  row="true"`, the trailing `<span class="badge ...">` value gets
  `data-fc-cell="true"`/addr/kind/editable="false"/raw.

**Address scheme**:

| Cell | Address |
|---|---|
| Active project | `audit!current_context.project` |
| Saved scenario boundary | `audit!current_context.scenario` |
| Last runtime snapshot | `audit!current_context.runtime_snapshot_id` |
| Runtime generated at | `audit!current_context.runtime_generated_at` |
| Governance posture | `audit!governance_posture` |
| G20 Gate | `audit!governance_status.g20_gate` |
| R99/R102 Promotion | `audit!governance_status.r99_r102_promotion` |
| Equity IRR residual | `audit!governance_status.equity_irr_residual` |
| Senior Debt evidence | `audit!reference_evidence.senior_debt` |
| SHL Opening evidence | `audit!reference_evidence.shl_opening` |
| Distributions evidence | `audit!reference_evidence.distributions` |
| Tax/CFADS evidence | `audit!reference_evidence.tax_cfads` |

All cells on both surfaces are `data-fc-editable="false"` — none of
this content was ever editable, and none was made editable by this
migration.

### Existing behaviour preserved — download links remain fully clickable

This was the single most important constraint for this migration: the
real download `<a href="/download">`, `<a href="/exports/runtime-
summary.csv?...">`, and `<a href="/exports/institutional-
workbook.xlsx?...">` links keep their original `href`, classes, and
DOM position — the `data-fc-*` attributes were added as extra
attributes on the same `<a>` tag, never via a new wrapping element
placed in front of the anchor. Verified directly (not just asserted)
by a Playwright test that clicks the values-only download link
through `page.click(...)` and asserts a real browser `download` event
fires (`tests/test_export_audit_c1_migration_browser.py::
test_download_link_click_navigates`), plus a DOM-shape check that the
`data-fc-cell`-bearing element's `tagName` is literally `a`, not a
wrapper `div`/`span`.

### `FcCellIO` reused as-is

No changes to `static/interaction/cell-io.js` were needed.
`writeValue()` already refuses writes when `cell.editable` is false —
the correct behaviour for every cell on both surfaces.

### Cross-cutting interaction-layer fixes required

None. `grid-registry.js` and `focus-manager.js` were spot-checked
(not fully re-read, since this was already confirmed safe for Inputs'
non-table layout and Senior Debt's mixed layout): generic
`.closest()`/attribute-based row/cell discovery has no assumption
that a cell contains an `<input>` or lives in a `<table>`, so a
links-and-badges-only, zero-`<input>` surface needed no JS changes.
`FcGridRegistry.scan()` and the click/keyboard/selection/copy
handlers all operate purely on `data-fc-*` attribute presence.

## New tests

- `tests/test_export_audit_c1_markup_contract.py` — static
  (string-render) test covering both surfaces independently
  (`TestExportMarkupContract` against a workspace_shell.html
  sub-template render of just the Downloads panel,
  `TestAuditMarkupContract` against `_audit_governance_relocated.html`
  rendered standalone with `audit_mode`-style sample data). Covers:
  both grid roots present, scroll containers present, every cell has
  addr/kind/editable="false" (no exceptions), no duplicate addresses,
  deterministic addresses (never display text), known address
  examples present, the download `<a>` elements keep their real
  `href`, and the data-fc-cell attribute is confirmed to sit directly
  on the existing `<a>` tag rather than a new wrapper. 18/18 passing.
- `tests/test_export_audit_c1_migration_browser.py` — production-
  route Playwright smoke test seeded from the Oborovo template via
  `/projects/create`. `TestExportProductionRouteMigration` switches to
  `window.switchTab('downloads')` and covers: grid presence, unique
  addresses, all cells non-editable, Active Cell, Keyboard +
  Shift+Arrow selection, Copy, the values-only download link's `href`
  is unchanged after the markup addition, the link element is
  confirmed to literally be an `<a>` (not wrapped), and **clicking the
  download link still triggers a real browser download event**
  (`page.expect_event("download", ...)` around the click) — the
  explicit click-still-works verification required by the task.
  `TestAuditProductionRouteMigration` documents (via a passing
  assertion, not a silent skip) that the `audit` grid is confirmed
  absent on the live production route in this environment, because
  `main_web.py` hardcodes `audit_mode: False` on every render path —
  this is expected, not a bug, and the `audit` grid's full markup
  contract is covered by the static test file instead. 10/10 passing.

## Test results

- New tests: 18/18 (`test_export_audit_c1_markup_contract.py`) + 10/10
  (`test_export_audit_c1_migration_browser.py`) passing.
- See the PR description / commit for the combined per-category
  regression run (full C1, C2-PR1, CAPEX, OPEX, Inputs, Revenue,
  Senior Debt, Tax, Export/Audit), each run as its own isolated
  `pytest` invocation.
- Zero financial-logic changes confirmed: `git diff --stat
  main -- domain app/waterfall_core.py app/input_adapter.py
  app/project_factories.py` is empty.

## Guardrail diff

This migration touches exactly two production template files
(`app/templates/partials/workspace_shell.html` — only the
`panel-downloads` block — and `app/templates/partials/
_audit_governance_relocated.html`), plus the two new test files and
this document. No `/download`/`/exports/*` route handler, `domain/*`,
`app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, persistence, export, or calculation-engine
file was touched.

## Out of scope / deferred

- The three disabled "Coming Soon" download placeholders (Audit
  Workbook, Gap Register, Source Map) — no real href/data to address.
- The Pilot Limitations Notice, Lifecycle Clarity panel, and Review
  Boundary note inside the Audit tab — purely static descriptive
  text, no `project_ctx`/lineage data to bind.
- The TUHO Reference Audit-Only Status card in `workspace_shell.html`
  (a separate, hardcoded badge table rendered unconditionally near
  the top of `panel-audit`, outside `_audit_governance_relocated.html`)
  — left unmigrated in this PR; it is purely static reference badges
  with no real `project_ctx` binding, a reasonable candidate for a
  later PR if address coverage for it is wanted.
- Enabling an `audit_mode=True` toggle on the live route — that is an
  application-routing/feature-flag decision, not a markup-contract
  concern, and explicitly out of scope for this interaction-layer
  migration.
- C2, incremental recalculation, a dependency graph, or formula
  evaluation.
- Any change to `domain/*`, `app/waterfall_core.py`,
  `app/input_adapter.py`, `app/project_factories.py`, persistence, or
  export/download route logic.

## Suggested next sheet

With CAPEX, OPEX, Inputs, Revenue, Senior Debt, Tax, and Export/Audit
now migrated, the Compare view or dashboard overview are reasonable
next candidates.
