# Phase 57A-3 — CAPEX single-sheet runtime draft

## Status

**DRAFT — visual review required.** Not marked ready, not
auto-merged. This is a runtime UI change. The user must
visually review and explicitly mark the PR ready.

## Current main SHA (start of 57A-3)

`b19127da51e5568b4786f3391c56d9e43627bb08` (post-57A-2,
CAPEX single-sheet direction characterization merged)

## Current main SHA (after 57A-3)

Reported in the 57A-3 combined report.

## What this PR does

Promotes the app to be the source of truth for CAPEX and
collapses the two competing CAPEX views (the 57A Summary
view A and the Excel-reconciliation Detail view B) into a
**single Excel-like CAPEX input sheet** rendered as
`app/templates/partials/sheet_capex.html`.

The primary CAPEX tab in `workspace_shell.html` now
includes only `sheet_capex.html`. The previous
`partials/sheet_capex_detail.html` (Excel-vs-App audit
view) is no longer included in the primary CAPEX tab. The
file is kept on disk as a deprecated alias so that any
old direct-path reference does not 404; it can be removed
in a future cleanup PR.

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
  visible HTML class set is preserved 1:1 (the new sheet
  still uses `fc-grid`, `fc-cell`, `fc-cell--code`,
  `fc-cell--amount`, `fc-total-row`, `fc-subtotal-row`,
  `fc-section-band`, `fc-grand-total`,
  `fc-hard-capex-total`, `fc-delta-row`, etc.).

## What happened to the old CAPEX Detail / Excel reconciliation (57A-2 view B)

- The previous `sheet_capex_detail.html` (Excel-vs-App
  audit view) had:
  - "Authority summary strip" with Backend auth. / App
    mapped / Excel ref only / Missing src / Mismatch /
    Scope diff / Deferred counts.
  - "Display only audit banner" warning that the grid
    is an audit/display view.
  - Excel-vs-App columns: Excel kEUR, App kEUR, Delta
    kEUR, plus Status column with Display only / Reference
    only / Pending treatment / Not comparable badges.
  - 18 monthly payment columns (M1..M18) with M1–M6,
    M7–M12, M13–M18, All toggle buttons.
  - Display mode toggle: Values / Schedule / Flags.
  - Collapse all / Expand all controls.
- This Excel-reconciliation framing is **removed** from
  the primary CAPEX input sheet (per user direction:
  "Do NOT show Excel vs App reconciliation in this CAPEX
  sheet. Do NOT show Excel comparison/delta/status
  columns in this CAPEX sheet.").
- The file is **kept on disk** as a deprecated alias so
  that any old direct-path reference does not 404. A
  future cleanup PR can remove it entirely.
- The monthly payment schedule / VAT / WHT / depreciation
  detailed columns are **deferred placeholders** in the
  new sheet (the deferred-columns note at the bottom of
  the new sheet documents this). The detailed logic is
  preserved at the backend level and will be wired in a
  follow-up phase that does not change financial outputs.

## New CAPEX sheet structure (single sheet)

The new `sheet_capex.html` is a single Excel-like CAPEX
input sheet with:

### Sheet banner
- `🏗️ CAPEX` (single label, not "Detail")
- Mode badge: "User Project — editable" or "Factory
  Reference — read-only"

### Derived top summary (NOT a separate competing view)
- Hard CAPEX (sum of C.01..C.05) — derived
- Financing (sum of financing rows) — derived
- Total CAPEX (Hard + Financing) — derived
- CAPEX / MW (Total CAPEX / capacity_mw) — derived
  (only shown if capacity_mw > 0)

### C.01..C.05 category groupings
The category groupings follow the source Excel model:

| Category | Label | Line codes |
|---|---|---|
| C.01 | Construction | epc_contract, production_units, epc_other |
| C.02 | Development | project_acquisition, project_rights, ops_prep |
| C.03 | Construction Management | construction_mgmt_a, construction_mgmt_b, commissioning, audit_legal |
| C.04 | Civil & Land | lease_tax |
| C.05 | Insurances & Risk | insurances, contingencies, taxes |

Each category has:
- A section band (read-only header with the C.0X code and
  label)
- The line items under the category (each editable as an
  `<input name="capex_<code>_keur">` in user project mode)
- A category subtotal row (read-only, derived from the
  line items)

### Financing Costs section
- Section band: "Financing Costs (read-only — backend-computed)"
- Financing line items: idc, bank_fees, commitment_fees,
  other_financial, vat_costs, reserve_accounts
- Each financing row uses the `data_financing` row type
  (read-only regardless of mode, preserved from 57A-1
  Fix A)
- Financing Costs Subtotal (read-only, derived)

### Hard CAPEX Total
- Subtotal row: "Hard CAPEX Total" (sum of C.01..C.05
  subtotals)
- Read-only

### Total CAPEX
- Total row: "Total CAPEX" (Hard CAPEX Total + Financing
  Costs Subtotal)
- Read-only
- Bold (preserved from 57A)

### Editability policy
- **Editable (user project mode)**: ordinary CAPEX line
  items (epc_contract, production_units, etc.)
- **Read-only (always)**: financing / IDC rows (idc,
  bank_fees, etc.) — preserved from 57A-1 Fix A
- **Read-only (always)**: subtotals, totals
- **Read-only (factory reference)**: everything

### Deferred placeholders
The following columns are documented as deferred to a
follow-up phase that will not change financial outputs:

- VAT applicability / amount
- WHT rate / amount
- Depreciation category / years
- Payment schedule by construction month
- Utilisation during construction

The deferred note is rendered as a small text block at
the bottom of the new sheet. The detailed logic is
preserved at the backend level.

## Files changed

- `app/templates/partials/sheet_capex.html` — REWRITTEN
  as the single Excel-like CAPEX input sheet (350 → 320
  lines, but with new content)
- `app/templates/partials/workspace_shell.html` —
  MODIFIED to remove the
  `{% include "partials/sheet_capex_detail.html" %}`
  from the CAPEX panel

## Files NOT changed (kept as deprecated aliases)

- `app/templates/partials/sheet_capex_detail.html` —
  NOT modified; kept on disk as a deprecated alias. A
  future cleanup PR can remove it entirely.

## Files NOT modified (technical foundation reused)

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
- [ ] Confirm the sheet banner says "🏗️ CAPEX" (not
      "CAPEX Detail")
- [ ] Confirm category groupings C.01, C.02, C.03, C.04,
      C.05 are visible
- [ ] Confirm each category has a section band, line
      items, and a subtotal
- [ ] Confirm ordinary CAPEX line items (epc_contract,
      production_units, project_acquisition, lease_tax,
      insurances) render as input fields in user project
      mode
- [ ] Confirm Hard CAPEX Total is read-only and shows
      the sum of C.01..C.05
- [ ] Confirm Financing Costs section is read-only
- [ ] Confirm Total CAPEX is read-only and shows Hard
      CAPEX + Financing
- [ ] Confirm CAPEX / MW is shown in the derived summary
      (when capacity_mw > 0)
- [ ] Confirm no Excel-vs-App comparison / Delta / Status
      columns in the primary CAPEX sheet
- [ ] Confirm the previous CAPEX Detail / Excel
      reconciliation view is not rendered
- [ ] Confirm factory reference mode is fully read-only
- [ ] Confirm GET / still works
- [ ] Confirm Overview / Inputs / Audit tabs all load
- [ ] Confirm no console errors / no network 404s
- [ ] Confirm no horizontal overflow (the new sheet has
      only 3 columns: Line Item, Code, Amount)

## Tests required (and implemented)

- 16 test classes, 50+ parametrized tests in
  `tests/test_phase57a3_capex_single_sheet_runtime.py`:
  - `TestOnlyOnePrimaryCapexSheet` (4)
  - `TestNoExcelVsAppComparison` (8)
  - `TestCategoryGroupings` (10 parametrized + 5)
  - `TestLineItemsEditable` (6)
  - `TestSubtotalsAndTotalsReadOnly` (5)
  - `TestFinancingRowsReadOnly` (8)
  - `TestCostPerMWDerived` (3)
  - `TestDeferredPlaceholders` (2)
  - `TestSheetBanner` (2)
  - `TestFactoryReferenceReadOnly` (2)
  - `TestLineItemSumsToSectionTotal` (3)
  - `TestNoNoGoClaims` (11 parametrized)
  - `TestLigRenderMacroUsed` (3)
  - `TestNoBackendModelPersistenceChanges` (3)
  - `TestLigMacroNotModified` (1)
  - `TestFileScope` (3)
  - `TestRc1Untouched` (2)
