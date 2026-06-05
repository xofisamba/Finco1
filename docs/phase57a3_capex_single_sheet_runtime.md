# Phase 57A-3 — CAPEX single-sheet runtime draft (post-feedback revision)

## Status

**DRAFT — visual review required.** Not marked ready, not
auto-merged. This is a runtime UI change. The user must
visually review and explicitly mark the PR ready.

## Post-feedback revision summary

The previous version of 57A-3 used a simplified C.01..C.05
grouping. Per user feedback:

> CAPEX must NOT be reduced to C.01–C.05 categories.
> C.01–C.05 was only part of the screenshot, not the full
> model. The original Excel CAPEX has C.01–C.18 categories
> with sub-lines. The CAPEX sheet must preserve the full
> C.01–C.18 hierarchy and sub-lines.

This revised 57A-3 implementation:

1. Renders all 18 canonical categories (C.01..C.18) with
   sub-lines (C.01.01, C.01.02, ..., C.18.xx).
2. Uses `project_ctx.capex_detail_items` (the existing
   full C.01..C.18 hierarchical data structure from
   `app/ui/project_context.py::_build_capex_detail_items`)
   as the primary data source.
3. Falls back to a C.01..C.18 scaffold with sub-line
   placeholders when `capex_detail_items` is empty (for
   backward compatibility with older test contexts).
4. Treats C.17 (Financing Costs) and C.18 (Reserve
   Accounts) as backend-computed data_financing rows
   (read-only, preserved from 57A-1 Fix A).
5. Documents VAT / WHT / depreciation / payment schedule
   / utilisation as **future model inputs** that will
   feed P&L, Balance Sheet, Cash Flow, Sources & Uses,
   funding drawdown, IDC, and opening debt balances. None
   of these are calculated in this PR.
6. Documents a **Sources & Uses bridge** that describes
   exactly which CAPEX inputs will feed which downstream
   calculations. This is documentation only; no model
   changes in this PR.

## Current main SHA (start of 57A-3)

`b19127da51e5568b4786f3391c56d9e43627bb08` (post-57A-2,
CAPEX single-sheet direction characterization merged)

## Current main SHA (after 57A-3)

Reported in the 57A-3 combined report.

## What this PR does

Promotes the app to be the source of truth for CAPEX and
collapses the two competing CAPEX views (the 57A Summary
view A and the Excel-reconciliation Detail view B) into
a **single Excel-like CAPEX input sheet** rendered as
`app/templates/partials/sheet_capex.html`.

The primary CAPEX tab in `workspace_shell.html` now
includes only `sheet_capex.html`. The previous
`partials/sheet_capex_detail.html` (Excel-vs-App audit
view) is no longer included in the primary CAPEX tab. The
file is kept on disk as a deprecated alias so that any
old direct-path reference does not 404; it can be removed
in a future cleanup PR.

## Canonical C.01..C.18 category hierarchy

The CAPEX sheet renders the canonical C.01..C.18
hierarchy per the user-provided reference screenshot:

| Code | Category |
|---|---|
| C.01 | Production Unit |
| C.02 | EPC Contract |
| C.03 | Grid Connection |
| C.04 | Monitoring & Telecom |
| C.05 | Operation Investments |
| C.06 | Insurances |
| C.07 | Land Securing Costs |
| C.08 | Bank Due Diligence |
| C.09 | Construction Management |
| C.10 | Commissioning |
| C.11 | Audit & Accounting & Legal |
| C.12 | Construction Mgmt |
| C.13 | Contingencies |
| C.14 | Import Taxes |
| C.15 | Project Acquisition / Development |
| C.16 | Project Rights |
| C.17 | Financing Costs (read-only, backend-computed) |
| C.18 | Reserve Accounts (read-only, backend-computed) |

Each category has:
- A section band (read-only header with the C.0X code and
  label)
- Sub-lines (C.01.01, C.01.02, ...) — each editable as an
  `<input name="capex_C_01_01_keur">` in user project mode
  (note: dotted codes are sanitized to underscores in
  the input name; the full dotted code is preserved in
  `data-capex-code-full`)
- A category subtotal row (read-only, derived from the
  sub-lines)

## What happened to the old CAPEX Summary (57A view A)

- The 57A LineItemGrid CAPEX Summary view (formerly
  `sheet_capex.html`) was a 3-column aggregate view
  (Line Item, Code, Amount) that read the same data as
  the 57A-2 Detail view B but at a higher aggregation
  level.
- The 57A Summary view is **removed** as a separate
  competing surface.
- The 57A `lig_render` macro from
  `partials/_line_item_grid.html` is **kept** as the
  technical foundation and **reused** in the new
  `sheet_capex.html`. The 57A macro is unchanged
  (no extension was needed for this PR; the existing
  `data` / `data_financing` / `subtotal` / `total` /
  `section_band` row types cover the new sheet's
  requirements).
- The 57A work is preserved as a technical pilot. The
  visible HTML class set is preserved 1:1.

## What happened to the old CAPEX Detail / Excel reconciliation (57A-2 view B)

- The previous `sheet_capex_detail.html` (Excel-vs-App
  audit view) is no longer included in the primary
  CAPEX tab.
- The file is **kept on disk** as a deprecated alias.
- The "Authority summary strip" (Backend auth. / App
  mapped / Excel ref only / Mismatch / Scope diff /
  Deferred counts) is removed from the primary CAPEX
  sheet.
- The "Display only audit banner" is removed.
- The Excel-vs-App columns (Excel kEUR, App kEUR, Delta
  kEUR, Status) are removed.
- The 18 monthly payment columns (M1..M18) with range
  toggles are documented as future model inputs (see
  "Future model inputs" below) but not rendered as
  editable columns yet. The detailed logic is preserved
  at the backend level.

## New CAPEX sheet structure (single sheet, post-feedback)

The new `sheet_capex.html` is a single Excel-like CAPEX
input sheet with:

### Sheet banner
- `🏗️ CAPEX` (single label, not "Detail")
- Mode badge: "User Project — editable" or "Factory
  Reference — read-only"

### Derived top summary (NOT a separate competing view)
- Hard CAPEX (sum of C.01..C.16 hard categories) — derived
- Financing / Reserve (C.17 + C.18) — derived, read-only
- Total CAPEX (Hard + Financing) — derived
- CAPEX / MW (Total CAPEX / capacity_mw) — derived
  (only shown if capacity_mw > 0)

### C.01..C.18 category groupings
The category groupings follow the source Excel model
(see the canonical table above). Each category has:
- A section band (read-only header with the C.0X code
  and label)
- Sub-lines (C.01.01, C.01.02, ...) — each editable in
  user project mode
- A category subtotal row (read-only, derived from the
  sub-lines)

### Financing / Reserve Accounts sections
- Section band: "C.17  Financing Costs (read-only —
  backend-computed)"
- Section band: "C.18  Reserve Accounts (read-only —
  backend-computed)"
- Each sub-line uses the `data_financing` row type
  (read-only regardless of mode, preserved from 57A-1
  Fix A)

### Hard CAPEX Total
- Subtotal row: "Hard CAPEX Total (C.01–C.16)"
- Read-only

### Total CAPEX
- Total row: "Total CAPEX (C.01–C.18)"
- Read-only
- Bold

### Editability policy
- **Editable (user project mode)**: ordinary CAPEX
  sub-lines (C.01.01, C.01.02, C.02.01, ...)
- **Read-only (always)**: financing / IDC / reserve
  rows (C.17.xx, C.18.xx) — preserved from 57A-1 Fix A
- **Read-only (always)**: subtotals, totals
- **Read-only (factory reference)**: everything

### Future model inputs (deferred placeholders, documented)
The following columns are documented as deferred to a
follow-up phase that will not change financial outputs.
The detailed logic is preserved at the backend level and
will be wired in subsequent PRs.

- **VAT applicability / rate / cost** — future input
  → cash flow / balance sheet / working capital / tax
  receivable logic.
- **WHT rate / cost** — future input → tax / cash flow
  treatment.
- **Depreciation category / useful life / flag** —
  future input → P&L and fixed asset schedule.
- **Payment schedule by construction month** — future
  input → equity drawdown, SHL drawdown, senior debt
  drawdown, IDC, opening balances at COD. See "Sources
  & Uses bridge" below.
- **Utilisation of funds during construction** — derived
  from the payment schedule, feeds the same drawdown /
  IDC chain as the payment schedule.

### Sources & Uses bridge (documented)
The CAPEX sheet documents a "Sources & Uses bridge" that
describes exactly which CAPEX inputs will feed which
downstream calculations:

- **Sources & Uses** — line items + payment schedule +
  funding allocation.
- **Equity drawdown** — from the payment schedule
  (equity-funded portion).
- **Senior loan drawdown** — from the payment schedule
  (senior-debt-funded portion).
- **SHL drawdown** — from the payment schedule
  (SHL-funded portion).
- **Senior IDC + SHL IDC** — derived from the payment
  schedule and outstanding balances.
- **Opening senior debt balance at COD** — cumulative
  senior drawdowns.
- **Opening SHL balance at COD** — cumulative SHL
  drawdowns.
- **Fixed asset base** — total CAPEX net of VAT (where
  applicable).
- **VAT receivable / payable** — from the VAT rate /
  cost column.
- **WHT payable / cash** — from the WHT rate / cost
  column.
- **Depreciation in P&L** — from the depreciation
  category / useful life / flag column.
- **Balance Sheet** — fixed asset base, VAT receivable,
  opening debt balances.
- **Cash Flow** — equity / senior debt / SHL drawdowns,
  IDC, VAT, WHT, opening balances at COD.

This is **documentation only**. The bridge text appears
in the rendered sheet as a reference for users. The
backend model changes that will realize this bridge are
**out of scope for this PR** and will be implemented in
subsequent PRs that do not change financial outputs in
the 57A-3 merge window.

## Files changed

- `app/templates/partials/sheet_capex.html` — REWRITTEN
  as the single C.01..C.18 Excel-like CAPEX input sheet.
- `app/templates/partials/workspace_shell.html` —
  MODIFIED to remove the
  `{% include "partials/sheet_capex_detail.html" %}`
  from the CAPEX panel.
- `tests/test_phase57a3_capex_single_sheet_runtime.py` —
  REWRITTEN with new tests for C.01..C.18, sub-lines,
  Sources & Uses bridge, and the post-feedback fixes.
- `docs/phase57a3_capex_single_sheet_runtime.md` — this
  file, REWRITTEN.
- `reports/phase57a3_capex_single_sheet_runtime.json` —
  REWRITTEN.

## Files NOT changed (kept as deprecated aliases / technical foundation)

- `app/templates/partials/sheet_capex_detail.html` —
  NOT modified; kept on disk as a deprecated alias.
- `app/templates/partials/_line_item_grid.html` — NOT
  modified. The 57A macro is reused as-is. No macro
  extension was needed for the new sheet.

## Hard no-go / scope for 57A-3

- No financial model changes. ✅
- No `app/waterfall_core.py` changes. ✅
- No `app/project_factories.py` changes. ✅
- No `app/persistence/` changes. ✅
- No `app/services/` changes. ✅
- No `main_web.py` changes. ✅
- No `static/app.js` changes. ✅
- No `static/styles.css` changes. ✅
- No schema / migration changes. ✅
- No fixture CSV changes. ✅
- No frontend dependency changes. ✅
- No Tailwind / Alpine / React / Vue / Svelte. ✅
- No G20/R99/R102 guard promotion. ✅
- No generic Solar/Wind runtime work. ✅
- No BESS / Hybrid / Portfolio work. ✅
- No IDC calculation changes. ✅
- No construction funding engine changes. ✅
- No senior debt / SHL drawdown logic changes. ✅
- No tax engine changes. ✅
- No OPEX/Revenue grid migration. ✅
- No Portfolio/BESS/Hybrid. ✅
- No forbidden user-facing claims. ✅
- rc1 frozen. ✅

## Auto-merge policy

**NO auto-merge.** This is a runtime UI change. The PR
is opened as DRAFT. The user must visually review and
explicitly mark the PR ready before squash merge.

## Visual review checklist

- [ ] Open the app in a browser
- [ ] Navigate to the CAPEX tab
- [ ] Confirm there is **one** primary CAPEX sheet
      (not two competing views)
- [ ] Confirm the sheet banner says "🏗️ CAPEX" (single
      label, not "Detail")
- [ ] Confirm all 18 category bands (C.01..C.18) are
      visible
- [ ] Confirm sub-lines (C.01.01, C.01.02, ...) are
      visible under each category
- [ ] Confirm sub-line amounts are editable inputs in
      user project mode
- [ ] Confirm C.17 (Financing Costs) and C.18 (Reserve
      Accounts) are read-only (data_financing)
- [ ] Confirm category subtotals are read-only and
      derived from the sub-lines
- [ ] Confirm Hard CAPEX Total (C.01–C.16) is read-only
- [ ] Confirm Total CAPEX (C.01–C.18) is read-only
- [ ] Confirm CAPEX / MW is shown in the derived summary
      (when capacity_mw > 0)
- [ ] Confirm no Excel-vs-App comparison / Delta /
      Status columns in the primary CAPEX sheet
- [ ] Confirm the previous CAPEX Detail / Excel
      reconciliation view is not rendered
- [ ] Confirm the "Future model inputs" note is visible
      (VAT / WHT / depreciation / payment schedule /
      utilisation)
- [ ] Confirm the "Sources & Uses bridge" note is
      visible and lists all 12+ downstream model
      effects
- [ ] Confirm factory reference mode is fully read-only
- [ ] Confirm GET / still works
- [ ] Confirm Overview / Inputs / Audit tabs all load
- [ ] Confirm no console errors / no network 404s

## Tests implemented

- 16 test classes, 50+ parametrized tests in
  `tests/test_phase57a3_capex_single_sheet_runtime.py`
  covering:
  - Only one primary CAPEX sheet
  - Canonical C.01..C.18 hierarchy (18 parametrized)
  - Sub-lines preserved and editable
  - No Excel-vs-App / Delta / Status columns (8 tests)
  - Subtotals and totals are read-only
  - Financing / IDC rows are read-only
  - VAT / WHT / depreciation / payment schedule are
    documented as future model inputs
  - Sources & Uses bridge is documented
  - Editability (factory reference vs user project)
  - Sheet banner
  - Line item sums match section totals
  - No no-go claims (11 parametrized)
  - lig_render macro used
  - No backend / model / persistence / formula changes
  - File scope
  - rc1 untouched
