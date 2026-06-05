# Phase 57A-6 — CAPEX add-line-item design

> Type: docs / report / test-only
> Auto-merge eligible if all hard no-go gates pass.
> Branch: `phase57a6-capex-add-line-item-design`
> Base: post-57A-5 main (`faa62744a0c3e47b248fbcef0d940b83fef5d5d5`)

## 1. Purpose

Phase 57A-5 introduced the
`data-capex-add-line="<code>"` data-only hook on
each C.01..C.16 category section band. The hook is
intentionally behaviour-less — it is a foundation for
the add-line UX that is designed in this document.

This document defines the design of the add-line
UX in enough detail that a future runtime PR
(57A-8 or later) can implement it without further
design work.

## 2. Goals

1. The user can add a new sub-line under any
   C.01..C.16 category directly in the CAPEX sheet.
2. The new line is assigned the next available code
   in the category (e.g. C.01.04 if C.01.01, C.01.02,
   C.01.03 already exist).
3. The new line affects only:
   - The category's sub-line list.
   - The category's subtotal (derived).
   - The Hard CAPEX Total (C.01–C.16, derived).
   - The Total CAPEX (C.01–C.18, derived).
4. The new line does NOT affect:
   - P&L.
   - Balance Sheet.
   - Cash Flow.
   - IDC.
   - Funding drawdown.
   - Tax engine.
   - Depreciation.
   - C.17 / C.18 read-only rows.

## 3. UX flow

### 3.1 Discovery

The user sees a small `+ Add line` button at the
right edge of each C.01..C.16 category section band.
The button is rendered in the section band
(`<tr data-capex-add-line="C.01">`) and is styled
to be unobtrusive.

### 3.2 Click

When the user clicks `+ Add line`, the JS hook:

1. Reads the parent category code from
   `data-capex-add-line="<code>"`.
2. Reads the existing sub-line codes for that
   category from the rendered grid (e.g. C.01.01,
   C.01.02, C.01.03).
3. Computes the next available code (C.01.04).
4. Inserts a new empty input row in the grid under
   the last existing sub-line of that category.
5. The new row has:
   - A line label (e.g. "New line — C.01.04") that
     the user can rename inline.
   - The Excel-style code C.01.04 (visible).
   - An empty amount input.
6. Focuses the new amount input.

### 3.3 Edit

The user types a label and an amount. The amount
input is wired to the same form submission as the
existing sub-line inputs (the existing
`input_field_template="capex_{code}_keur"` produces
a name like `capex_C_01_04_keur`).

### 3.4 Save

When the user submits the form (clicks Save /
Run / etc.), the backend receives the new line
along with the existing lines. The backend applies
the line as part of the standard CAPEX update flow.

## 4. Numeric impact

The new line is added to the category's sub-line
list. The category subtotal, the Hard CAPEX Total,
and the Total CAPEX are all derived from the
sub-line list and are updated automatically.

| Item | Affected? |
|---|---|
| Category sub-line list | yes (new entry) |
| Category subtotal | yes (derived) |
| Hard CAPEX Total (C.01–C.16) | yes (derived) |
| Total CAPEX (C.01–C.18) | yes (derived) |
| P&L | no |
| Balance Sheet | no |
| Cash Flow | no |
| IDC | no |
| Funding drawdown | no |
| Tax engine | no |
| Depreciation | no |
| C.17 / C.18 | no |

## 5. Persistence approach

### 5.1 Why this is a separate design decision

The current `CapexStructure` data model has a fixed
set of fields (`epc_contract`, `production_units`,
etc.). Adding a dynamic sub-line item requires
either:

- **Option A: Schema change.** Replace the fixed
  field set with a list of sub-line items
  (e.g. `capex.sub_lines: tuple[CapexSubLine, ...]`)
  where each `CapexSubLine` has a code, a name, and
  an amount. This is a breaking change to the
  persistence layer.
- **Option B: In-memory only.** The new line is
  preserved across the user's session but is NOT
  saved to disk. The next time the user opens the
  project, the added line is gone.
- **Option C: Hybrid.** Persist the added lines in
  a separate table (e.g. `capex_sub_lines`) that is
  keyed on `project_id` + `category_code`. This
  requires a new table + migration but does not
  change the existing `CapexStructure` shape.

### 5.2 Recommendation: Option C (Hybrid)

A new table `capex_sub_lines` with columns:

| Column | Type | Notes |
|---|---|---|
| `id` | integer PK | |
| `project_id` | integer FK | |
| `category_code` | text | "C.01", "C.02", ... |
| `sub_line_code` | text | "C.01.04" |
| `name` | text | user-supplied label |
| `amount_keur` | real | |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

The `capex_detail_items` builder in
`app/ui/project_context.py::_build_capex_detail_items`
would read the existing `CapexStructure` fields and
augment each category's `children` tuple with the
rows from `capex_sub_lines` for the current project.

This approach:

- Does NOT change the existing `CapexStructure`
  shape (no breaking change to
  `app/domain/capex/source_model.py`).
- Adds a new table that is migration-friendly.
- Allows the user to add and remove sub-lines
  freely.

### 5.3 Stop-and-document

If Option C is implemented, the migration file and
the persistence-layer changes are **explicitly out
of scope** for any 57A-x PR. The 57A-6 PR is
**design only** — no migration, no persistence
change, no runtime change.

The actual implementation must come in a future
runtime PR (e.g. 57A-8 or later) that explicitly
scopes the migration.

## 6. Out of scope (per spec)

- No implementation in 57A-6. The JS hook,
  the migration, and the persistence changes are
  all in future phases.
- No IDC calculation change.
- No construction funding engine change.
- No senior debt / SHL drawdown logic change.
- No tax engine change.
- No backend financial formula change.
- No G20 / R99 / R102 promotion.
- No Tailwind / Alpine.
- No schema / migration in 57A-6.
- No backend keys visible in UI.

## 7. Test scope

The 57A-6 PR is docs/report/test-only. The tests
pin the design contract:

1. The design document exists.
2. The report JSON exists.
3. The document states:
   - The user can add a line under C.01..C.16.
   - The next available code is assigned.
   - The numeric impact is limited to category
     subtotal, Hard CAPEX Total, Total CAPEX.
   - P&L, Balance Sheet, Cash Flow, IDC, funding
     drawdown, tax engine, depreciation, C.17 / C.18
     are NOT affected.
   - Persistence approach is defined (Option C
     hybrid recommended).
   - Schema / migration is explicitly out of scope
     for 57A-6.
4. The report lists:
   - The recommended persistence approach.
   - The numeric impact matrix.
   - The hard no-go list.

## 8. Hard no-go (preserved throughout)

- No financial formula changes.
- No IDC calculation changes.
- No construction funding changes.
- No G20 / R99 / R102 promotion.
- No Tailwind / Alpine.
- No Portfolio / BESS / Hybrid.
- No schema / migration in 57A-6.
- No backend keys visible in UI.
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)
  frozen.
