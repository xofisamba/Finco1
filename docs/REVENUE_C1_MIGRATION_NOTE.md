# Revenue C1 Integration — Fourth Real-Sheet Migration

## Scope

This migrates the production Revenue sheet
(`app/templates/partials/sheet_revenue.html`, the `{% include %}`
target rendered into `<div class="tab-panel" id="panel-revenue">` in
`workspace_shell.html`, driven by `project_ctx.revenue_items`) onto
the C1 Spreadsheet Interaction Layer, using exactly the same
`data-fc-*` contract proven on CAPEX, OPEX, and Inputs.

It does **not** start C2, implement recalculation or a dependency
graph, migrate any other sheet, or change persistence, export,
calculations, or project factories. No `domain/*` file,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` was touched — `app/ui/project_context.py`
was only read (to confirm `item.code` fields and the
`_build_revenue_items()` shape used for addressing), never modified.

## Key findings that shaped this migration

Unlike OPEX (zero real editable cells) and like CAPEX (genuinely
mixed editability), the real Revenue grid is a **mix of editable and
non-editable cells today**, decided per-item by the existing
`item.editable` flag from `_build_revenue_items()`:

- **Editable** (`editable=True`, real `<input>` already exists):
  `ppa_base_tariff` (Base Tariff / PPA), and `co2_price` (CO2 Price
  Y1). These are genuinely user-adjustable assumptions.
- **Non-editable** (technical/derived parameters, read-only
  `<span>` always rendered): `capacity_mw`, `operating_hours_p50`,
  `plant_availability`, `grid_availability`, `pv_degradation` (Wind
  projects omit this row), `ppa_index`, `ppa_term_years`,
  `ppa_production_share`, `balancing_cost`, `first_merchant_period`,
  and the special-case `co2_enabled` flag.
- **`co2_enabled`** is a special case: its cell renders a Yes/No
  `<span>` rather than a numeric value, and is **always**
  non-editable (`editable: False` in `_build_revenue_items()`, so the
  existing `'true' if (is_user_project and item.editable …) else
  'false'` formula already evaluates to `false` for it without any
  extra carve-out being required — the production data already marks
  it non-editable).
- The 4 **summary/subtotal rows** (Tariff Y1 PPA, Y1 PPA Revenue,
  Y1 CO2 Revenue, Est. Total Y1 Revenue) are template-computed
  (`{% set ppa_y1 = ... %}` etc.), informational only ("backend
  computes actual"), and are **always** `data-fc-editable="false"`
  regardless of `is_user_project` — they have no backing `item.code`
  and are never meant to be written to.

As with CAPEX/OPEX, when `is_user_project=False` (a protected
baseline), every cell renders non-editable regardless of
`item.editable`, exactly matching the pre-existing Jinja gate
`is_user_project and item.editable`.

## What was implemented

### 1. C1 markup contract on the production Revenue grid

`sheet_revenue.html` gained:

- grid root + scroll container: `data-fc-grid="revenue"
  data-fc-scroll-container="true"` on the existing `.fc-grid-wrapper`
  div (one single `<table>`, four `{% for item in
  project_ctx.revenue_items %}` loops gated by `item.group`, plus a
  trailing summary section — all inside one `<tbody>`).
- every data row (`<tr class="fc-data-row">`) and summary row
  (`<tr class="fc-subtotal-row">` / `<tr class="fc-grand-total">`)
  gained `data-fc-row="true"`.
- every per-item amount `<td class="fc-cell fc-cell--amount">`
  gained `data-fc-cell="true"`, `data-fc-addr`, `data-fc-kind="text"`,
  `data-fc-editable`, and `data-fc-raw`.
- every summary `<td class="fc-total-cell">` gained the same 5
  attributes, with `data-fc-editable="false"` unconditionally.

**Address scheme** — deterministic:

| Cell | Address |
|---|---|
| per-item cell (any group) | `revenue!{item.code}` (e.g. `revenue!ppa_base_tariff`, `revenue!capacity_mw`) |
| Tariff Y1 (PPA) summary row | `revenue!summary.tariff_y1` |
| Y1 PPA Revenue (kEUR) summary row | `revenue!summary.ppa_revenue_y1` |
| Y1 CO2 Revenue (kEUR) summary row (conditional) | `revenue!summary.co2_revenue_y1` |
| Est. Total Y1 Revenue grand-total row | `revenue!summary.total_revenue_y1` |

Per-item addresses use the existing stable `item.code` field, never
display text. Summary rows use a `summary.` prefix (rather than the
OPEX/CAPEX `.subtotal`/`.total` suffix scheme) since there is no
underlying `code` to suffix — these are template-level aggregates,
not line items, and the prefix makes that origin explicit and
prevents any future collision with a real `item.code` value. `data-
fc-kind="text"` is used uniformly across both per-item and summary
cells (matching the convention already established for this sheet
prior to this migration's completion, rather than introducing
`"amount"`/`"subtotal"` kinds as CAPEX/OPEX did) — all Revenue values
are simple scalar text/number displays, not multi-year grids.

Only label/code/unit/group/notes columns (which carry no addressable
numeric value) were left without the contract.

### 2. Existing behaviour preserved

No `<input>`, `name=`, or Jinja editability condition was changed.
The pre-existing `is_user_project and item.editable` gate for
rendering an `<input>` vs. a `<span class="fc-cell-runtime">` is
untouched; the C1 `data-fc-editable` attribute simply mirrors that
exact same boolean. The `co2_enabled` 3-way branch (Yes/No span /
input / formatted span) keeps all three branches' content exactly
as-is — only the wrapping `<td>` gained the markup contract. Number
formatting (`"%.2f"|format(...)`, `"{:,.1f}".format(...)`, etc.) is
unchanged; `data-fc-raw` holds the underlying raw value, not the
formatted display string.

### 3. `FcCellIO` reused as-is

No changes to `static/interaction/cell-io.js` were needed.
`readValue()` reads `data-fc-raw`; `writeValue()` already respects
`cell.editable`, refusing writes to non-editable cells — exactly the
behaviour this sheet's mixed editability needs, with zero
Revenue-specific JS code.

### 4. Cross-cutting interaction-layer fixes required

None. All fixes from the CAPEX/OPEX/Inputs migrations already cover
Revenue's focusable cells/inputs.

## New tests

- `tests/test_revenue_c1_markup_contract.py` — static render of
  `sheet_revenue.html` standalone with a hand-built
  `project_ctx.revenue_items` fixture covering all 4 groups
  (including `co2_enabled`). Covers grid root, scroll container,
  every cell has addr/kind/editable, no duplicate addresses,
  deterministic addresses (never display text), known address
  examples (per-item + all 4 summary addresses), editable cells match
  the has-a-real-`<input>` convention, `co2_enabled` always
  non-editable, summary cells always non-editable, deterministic
  ordering across renders, and full read-only-project-mode coverage
  (grid root still present, all cells non-editable). 13/13 passing.
- `tests/test_revenue_c1_migration_browser.py` — production-route
  Playwright smoke test seeded from the Oborovo template via
  `/projects/create`, `window.switchTab('revenue')`. Covers: grid
  presence, unique addresses, `co2_enabled` non-editable, Active
  Cell, Keyboard Navigation, Shift+Arrow selection, Copy reads raw,
  paste writes to a real editable cell (`ppa_base_tariff`), paste
  onto a read-only cell no-ops, a real edit + Undo round trip on the
  editable cell, a Fill no-op safety check, and an htmx-swap re-scan.
  12/12 passing.

## Test results

- New tests: 13/13 (`test_revenue_c1_markup_contract.py`) + 12/12
  (`test_revenue_c1_migration_browser.py`) passing.
- Full C1 PR1–PR9 + C2-PR1 + CAPEX/OPEX/Inputs C1 + Revenue C1 + Senior
  Debt C1 regression: see combined results in
  `docs/SENIOR_DEBT_C1_MIGRATION_NOTE.md` (same regression run covers
  both sheets migrated in this stacked PR).
- Pre-existing failures, if any, are documented identically in
  `docs/SENIOR_DEBT_C1_MIGRATION_NOTE.md` and were confirmed via `git
  stash` to be unrelated to this change.

## Out of scope / deferred

- Any other sheet (Tax, Compare, dashboard).
- C2, incremental recalculation, a dependency graph, or formula
  evaluation.
- Any change to `domain/*`, `app/waterfall_core.py`,
  `app/input_adapter.py`, `app/project_factories.py`, persistence, or
  export logic.
- Adding new editable inputs where none exist today (e.g. flipping
  `ppa_index`, `capacity_mw`, etc. to editable) — that is a future
  product decision, not part of this interaction-layer migration.

## Suggested next sheet

With CAPEX, OPEX, Inputs, Revenue, and Senior Debt now migrated, Tax
or the Compare view are reasonable next candidates.
