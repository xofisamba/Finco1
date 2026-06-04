# Phase 57A-2 — CAPEX single-sheet direction characterization

## Status

DRAFT → marked ready → squash merged in the 57A-2 branch
(see `reports/phase57a2_capex_single_sheet_direction_characterization.json`
for the merge SHA).

This is a **characterization document only**. 57A-2 does NOT
implement a runtime CAPEX rewrite. The proposed runtime
work is a follow-up PR (57A-3 / 57G, draft-only) that must
be approved by the user before implementation.

## Current main SHA (start of 57A-2)

`88a6de68df1c651904accd5621ef2d8b5047a464` (post-57F, UI-3.2
next-grid readiness plan merged)

## Current main SHA (after 57A-2)

Reported in the 57A-2 combined report.

## 57A merge SHA (PR #487)

`b173355b6021577f6567069ebd748aa3176f2475` — the merge
commit that introduced the LineItemGrid CAPEX Summary
pilot. The 57A work is still useful as a technical
foundation; the dual CAPEX view (Summary + Detail) is
the issue.

## rc1 frozen SHA

`b425a0708719eaa5e1d922b1008e5609758e0ad4` — must
remain untouched throughout the 57A-3 follow-up runtime
work as well.

## Why this phase exists

The user reviewed the merged Phase 57A LineItemGrid CAPEX
Summary pilot and clarified the product direction:

> The app should NOT have two CAPEX views (CAPEX Summary +
> CAPEX Detail / Excel reconciliation). The desired
> product direction is ONE Excel-like CAPEX sheet, similar
> to the source Excel model.

Phase 57A migrated only the **CAPEX Summary** view
(`app/templates/partials/sheet_capex.html`) to use the new
shared `lig_render` macro. The **CAPEX Detail** view
(`app/templates/partials/sheet_capex_detail.html`) remains
the larger, Excel-like grid that mirrors the source Excel
model with monthly payment schedule columns.

Both views are included together in
`app/templates/partials/workspace_shell.html:452-453`:

```html
{% include "partials/sheet_capex.html" %}
{% include "partials/sheet_capex_detail.html" %}
```

This dual-view pattern is confusing for the user (two
competing CAPEX surfaces on the same tab) and is the
explicit reason for this characterization.

## Phase 57A is still useful

The 57A LineItemGrid macro is a **technical foundation**,
not a product dead-end:

- The macro supports row types
  `data` / `data_financing` / `subtotal` / `total` /
  `section_band` / `delta_warning`.
- The macro supports cell kinds
  `label` / `code` / `amount` / `delta_value`.
- The macro supports editable vs read-only per row
  (with `data_financing` always read-only).
- The macro can be extended to support additional column
  types (e.g. monthly payment schedule columns).

The 57A macro is the right technical foundation for the
single-sheet CAPEX. The next step is to **extend the
macro** to cover the full Excel-like CAPEX line grid, not
to replace it.

## 1. Current CAPEX UI inventory

### View A: CAPEX Summary (57A-migrated)
- File: `app/templates/partials/sheet_capex.html`
- LOC: 350
- Rendered via: `lig_render` macro (post-57A)
- Columns: Line Item, Code, Amount (kEUR)
- Row types: section_band, data (hard CAPEX),
  data_financing, subtotal, total, delta_warning
- Editability: data rows editable in user project mode;
  data_financing always read-only; subtotal/total/
  delta_warning always read-only
- Source: derived from `project_ctx.capex_items`
  (aggregated, 6 main sections)
- Sheet banner: "🏗️ CAPEX Detail" (note: even though
  the file is `sheet_capex.html`, the banner reads
  "CAPEX Detail" — this is a pre-57A artifact)

### View B: CAPEX Detail / Excel reconciliation
- File: `app/templates/partials/sheet_capex_detail.html`
- LOC: 883
- Rendered via: hand-written table (not migrated to
  LineItemGrid)
- Columns: Line Item, Code, Amount (kEUR),
  cost per MW, contingency (%), VAT (rate, amount),
  payment schedule (monthly columns M1..Mn),
  WHT (rate, amount), depreciation, comments, test/status
- Editability: in factory reference mode, all cells
  read-only with "backend" badge for runtime-calculated
  values. In user project mode, the line item names and
  amounts are editable; the payment schedule and WHT are
  derived (backend-computed)
- Source: `project_ctx.capex_detail_items` (extended
  per-line data)
- Sheet banner: "🏗️ CAPEX Detail"

### Why two views are confusing

1. **Same tab, two competing surfaces**: the user sees
   both `sheet_capex.html` and `sheet_capex_detail.html`
   on the CAPEX tab, with the same `🏗️ CAPEX Detail`
   banner on each (banner mislabel compounds the
   confusion).
2. **Different levels of detail, different editability**:
   the Summary aggregates to kEUR-rounded section
   subtotals; the Detail shows the full Excel-like
   line grid. Users are unsure which to edit when they
   want to change a CAPEX line.
3. **Different data sources**: Summary reads
   `capex_items` (aggregated); Detail reads
   `capex_detail_items` (extended per-line). The two
   sources are not guaranteed to be in sync.
4. **Different update paths**: changes to one view do
   not necessarily propagate to the other. Users have
   to remember which view is the "source of truth".
5. **Two competing visual hierarchies**: the Summary is
   a 3-column compact table; the Detail is a wide
   Excel-like grid with monthly payment columns. They
   use different CSS class families (`fc-*` for the
   Summary, mixed for the Detail).

## 2. User target CAPEX model

The user wants a **single Excel-like CAPEX sheet** that
mirrors the source Excel model. The target columns are:

| Column | Description | Editability |
|---|---|---|
| Line Item | Description of the CAPEX line | Editable (user project) |
| Amount (kEUR) | Total line amount | Editable (user project) |
| Cost per MW | Cost per installed MW | Editable (user project) |
| Contingency (%) | Contingency percentage | Editable (user project) |
| VAT (rate, amount) | VAT applicability and amount | Read-only (derived from amount + rate) |
| WHT (rate, amount) | Withholding tax rate and amount | Read-only (derived from amount + rate) |
| Depreciation | Depreciation schedule (years) | Read-only (derived) |
| Comments | Free-form notes | Editable (user project) |
| Test / status | Test result, validation status | Read-only (derived from model checks) |
| Payment schedule (M1..Mn) | Monthly payment during construction | Read-only (derived from payment curve) |
| Utilisation during construction | % of CAPEX drawn per month | Read-only (derived from payment curve) |
| Future IDC basis | Field for future IDC calculation | Read-only (placeholder for IDC work) |

The target sheet is closer to the current CAPEX Detail
view (B) than the current CAPEX Summary view (A). The
Summary view (A) should be **removed or hidden** in the
target architecture.

## 3. Gap analysis

| Aspect | Current Summary (A) | Current Detail (B) | Target (single sheet) |
|---|---|---|---|
| Number of CAPEX views | 1 | 1 | 1 (consolidated) |
| Line items | Aggregated (6 sections) | Per-line (full Excel) | Per-line (full Excel) |
| Cost per MW column | ❌ | ✅ | ✅ |
| Contingency column | ❌ | ✅ | ✅ |
| VAT column | ❌ | ✅ | ✅ |
| WHT column | ❌ | ✅ | ✅ |
| Depreciation column | ❌ | ✅ | ✅ |
| Comments column | ❌ | ✅ | ✅ |
| Test / status column | ❌ | ✅ | ✅ |
| Monthly payment schedule | ❌ | ✅ (M1..Mn columns) | ✅ (M1..Mn columns) |
| Utilisation during construction | ❌ | ✅ | ✅ |
| Future IDC basis | ❌ | ❌ | ✅ (new field) |
| Read-only financing rows | ✅ (57A-1 fix) | ❌ (no separate financing) | ✅ (preserved from 57A-1) |
| Sheet banner | "🏗️ CAPEX Detail" (mislabel) | "🏗️ CAPEX Detail" | "🏗️ CAPEX" (single) |
| Rendered via | `lig_render` (57A) | Hand-written table | `lig_render` (extended) |

### Recommended direction

**Promote the Detail view (B) to the single CAPEX sheet
and remove or collapse the Summary view (A).** Reasons:

1. The Detail view (B) already has all the target columns
   (cost per MW, contingency, VAT, WHT, depreciation,
   comments, test/status, monthly payment schedule,
   utilisation during construction) — these are the
   user's stated target.
2. The Summary view (A) is the user-confusing aggregation
   that does not map to the source Excel model.
3. The Detail view (B) is closer to the source Excel
   model, which is the user's stated product direction.
4. The 57A LineItemGrid macro is the technical foundation
   that can be extended to cover the Detail view's wider
   column set (M1..Mn payment schedule columns).
5. The Summary view (A)'s 57A work is not wasted — the
   macro can be reused and extended for the Detail view.

## 4. Recommended product architecture

### Single CAPEX tab
- One `app/templates/partials/sheet_capex.html` file
  (replaces the current two-file pattern).
- Includes the **full Excel-like line-item grid** (the
  current Detail view, B).
- The Summary's section subtotals (Construction,
  Development, etc.) can be derived as read-only
  computed rows in the same grid (not a separate view).

### Compact top summary (optional)
- If the user wants a compact summary (one-row-per-section
  view), it can be derived from the line-item grid
  and shown as a read-only "totals strip" at the top of
  the same sheet.
- The summary is **not** a separate competing view; it is
  a derived read-only strip in the same sheet.

### Main Excel-like line-item grid
- The main grid has the columns listed in section 2.
- Each row is one CAPEX line.
- Subtotal rows (per section) and a grand total row
  appear at the bottom of the grid.
- The grid uses the `lig_render` macro from
  `app/templates/partials/_line_item_grid.html`,
  extended to support additional column types
  (e.g. monthly payment schedule columns).

### Payment schedule columns
- The M1..Mn columns are part of the main grid.
- Each M column shows the payment for that construction
  month, derived from the payment curve.
- The columns are read-only.
- The number of columns (n) is dynamic based on
  construction duration.

### Read-only vs editable states
- **Editable (user project mode)**: Line Item, Amount,
  Cost per MW, Contingency (%), Comments.
- **Read-only (always)**: VAT (rate, amount), WHT
  (rate, amount), Depreciation, Test / status,
  Payment schedule (M1..Mn), Utilisation during
  construction, Future IDC basis.
- **Read-only (factory reference mode)**: everything
  (the entire grid is read-only).
- **Read-only (financing rows in user project mode)**:
  financing rows (idc, bank fees, commitment fees,
  other financial, vat costs, reserve accounts) are
  read-only regardless of mode (preserved from 57A-1
  Fix A).

### Audit / reconciliation flags
- Audit / reconciliation flags are **within the same
  sheet**, not a second competing view.
- A "Test / status" column shows the validation status
  per line item.
- A "Comments" column allows free-form notes per line
  item.
- The current CAPEX Detail view's "backend" badge for
  runtime-calculated values is preserved in the same
  column.

## 5. Treatment of current 57A LineItemGrid

### Keep the macro as technical foundation
- The `lig_render` macro in
  `app/templates/partials/_line_item_grid.html` is the
  right technical foundation for the single CAPEX sheet.
- The macro's contract (rows list, columns list,
  editable arg, input_field_template) is extensible.
- The macro's CSS class compatibility (preserving
  `fc-*` classes) means the existing
  `static/styles.css` rules continue to apply.

### Extend the macro for the full CAPEX line grid
The macro may need to be extended to support:

- **Per-row multi-column cells** (e.g. a single row with
  a label, an amount, a cost-per-MW, a contingency, a
  VAT amount, a WHT amount, a depreciation value,
  M1..Mn payment cells, a comments cell, a test/status
  cell). The current macro supports one cell per
  column; the extension may need to support cells that
  span multiple visual columns (e.g. M1..Mn collapsed
  into a single "Payment schedule" cell that expands
  on click).
- **Read-only-vs-editable per cell** (not just per row).
  Some cells in a data row are editable (Amount) and
  others are read-only (VAT, WHT, Payment schedule).
  The current macro's input-render gate is per-row;
  the extension adds per-cell gating.
- **Long horizontal grids**: the M1..Mn columns can
  make the grid very wide. The extension may need to
  support horizontal scroll, column grouping, or a
  "show payment schedule" toggle.

### Do not continue summary-only migration as product direction
The Summary view (A) was a useful technical pilot
(demonstrating the macro can render a structured rows
list) but is not the product direction. Future
migrations should target the **single-sheet CAPEX** with
the wider column set, not more aggregated summary
views.

### Do not migrate OPEX / Revenue before CAPEX single-sheet direction is locked
The 57F plan recommended OPEX as the next candidate
for grid migration. This is now **superseded** by the
57A-2 direction correction:

- The CAPEX single-sheet direction must be locked first.
- Then the LineItemGrid macro must be extended for the
  full CAPEX line grid (M1..Mn columns, per-cell
  editability, etc.).
- Then the single-sheet CAPEX is the next runtime
  migration (57A-3 or 57G).
- **OPEX / Revenue grid migration is deferred** until
  after the CAPEX single-sheet direction is locked
  and the macro extensions are validated.

## 6. Next runtime proposal: Phase 57A-3 (or 57G)

### Objective
Turn CAPEX into a single Excel-like line-item sheet
(promote the current Detail view B, hide/collapse the
current Summary view A).

### Allowed files
- `app/templates/partials/_line_item_grid.html` (only
  if macro extension is needed for M1..Mn columns,
  per-cell editability, etc.)
- `app/templates/partials/sheet_capex.html` (rewrite
  to use the new line-item grid, replacing the current
  Summary content)
- `app/templates/partials/sheet_capex_detail.html`
  (mark as deprecated, remove from
  `workspace_shell.html` include, OR keep as a
  deprecated include for backward compat with a
  deprecation notice)
- `app/templates/partials/workspace_shell.html` (remove
  the second `{% include "partials/sheet_capex_detail.html" %}`)
- `tests/test_phase<phase>_capex_single_sheet.py` (new
  test class)
- `docs/phase<phase>_capex_single_sheet_runtime.md`
  (runtime design doc)
- `reports/phase<phase>_capex_single_sheet_runtime.json`
  (runtime report)
- `tests/test_phase57pre_route_render_smoke.py`
  (update `ALLOWED_57A_TEMPLATE_PATHS` allowlist to
  include the new files)

### Forbidden files
- `main_web.py`
- `app/waterfall_core.py`
- `app/project_factories.py`
- `app/persistence/` (any file)
- `app/services/` (any file)
- `static/app.js`
- `static/styles.css` (unless the user explicitly
  approves a CSS change as part of 57A-3)
- Any schema / migration file
- Any fixture CSV
- Any frontend dependency (`package.json`, etc.)

### Implementation steps (sketch)
1. Extend the `lig_render` macro to support per-cell
   editability (cells with `editable: True` are
   editable; cells with `editable: False` are
   read-only).
2. Extend the macro to support the wider column set
   (cost per MW, contingency, VAT rate, VAT amount,
   WHT rate, WHT amount, depreciation, comments,
   test/status, M1..Mn, utilisation, future IDC basis).
3. Migrate the current CAPEX Detail view (B) to use
   the extended `lig_render` macro.
4. Replace the current `sheet_capex.html` (Summary
   view A) with a thin wrapper that includes the
   migrated Detail view.
5. Update `workspace_shell.html` to include only the
   single CAPEX sheet.
6. Mark `sheet_capex_detail.html` as deprecated (do
   not delete; the file can be referenced in
   deprecation tests).

### Tests required
- All 57A test classes extended for the new column set
  (cost per MW, contingency, VAT, WHT, depreciation,
  comments, test/status, M1..Mn, utilisation,
  future IDC basis).
- `test_financing_rows_readonly_in_user_project` (Fix A
  mirror) — pin that financing rows remain read-only.
- `test_section_bands_escaped` (Fix C mirror).
- `test_no_two_competing_capex_views` — pin that
  `workspace_shell.html` does NOT include
  `sheet_capex.html` AND `sheet_capex_detail.html`
  on the same tab.
- `test_capex_detail_is_primary_view` — pin that the
  Detail view (B) is the primary view, not the
  Summary view (A).
- `test_no_backend_idc_changes` — pin that no IDC
  calculation logic is changed (IDC is a placeholder
  for future work, not implemented in 57A-3).
- `test_no_g20_r99_r102_promotion` — pin the guard
  state.
- `test_56h1_hoist_preserved` — pin the local-variable
  hoist.

### No backend / model / IDC calculation changes
The 57A-3 runtime work is a **UI migration**, not a
backend change:

- The data structures (`project_ctx.capex_detail_items`,
  `project_ctx.capex_items`) are unchanged.
- The model computations (CAPEX totals, VAT, WHT,
  payment schedule) are unchanged.
- The IDC calculation is **not** implemented in
  57A-3. The "Future IDC basis" column is a
  placeholder for future IDC work, not an
  implementation of IDC.
- The persistence layer is unchanged.
- The services layer is unchanged.

### No Tailwind / Alpine
The 57A-3 work uses the existing
`static/styles.css` rules. No Tailwind. No Alpine. No
React / Vue / Svelte. No bundler. No npm.

### DRAFT-only, no auto-merge
57A-3 must be marked DRAFT. The user must visually
review the single CAPEX sheet and explicitly mark the
PR ready before squash merge. The 57A experience
(4 fixes after review) and the dual-view problem
justify the no-auto-merge policy.

## 7. Hard no-go / scope for 57A-2

- No financial model changes.
- No `app/waterfall_core.py` changes.
- No `app/project_factories.py` changes.
- No `app/persistence/` changes.
- No `app/services/` changes.
- No `main_web.py` changes.
- No `static/app.js` changes.
- No `static/styles.css` changes.
- No schema / migration changes.
- No fixture CSV changes.
- No frontend dependency changes.
- No Tailwind / Alpine / React / Vue / Svelte.
- No G20/R99/R102 guard promotion.
- No generic Solar/Wind runtime work.
- No BESS / Hybrid / Portfolio work.
- **No runtime CAPEX rewrite in 57A-2** (this is the
  characterization, not the change).
- **No UI-3.2 OPEX/Revenue migration yet** (deferred
  until after 57A-3 single CAPEX sheet is locked).
- **No IDC calculation changes** (IDC is a
  placeholder, not implemented).
- rc1 frozen.

## 8. Auto-merge policy

57A-2 is `docs/report/test-only`. It is auto-merge
eligible if all hard gates pass. The proposed 57A-3
runtime CAPEX single-sheet migration is **not** part
of 57A-2; it is deferred to a future PR (57A-3) that
the user must approve.
