# Phase 57A-2 — CAPEX 2.0 Design Characterization

> Type: docs / report / test-only
> Auto-merge eligible if all hard no-go gates pass.
> Branch: `phase57a2-capex-2-design-characterization`
> Base: post-57A-3 main (`ef4046aacad1b299842ab6aeac434af1a4d73368`)

## 1. Purpose

The previous 57A / 57A-2 / 57A-3 line of work built a
single CAPEX sheet with the canonical C.01–C.18
hierarchy. After a user visual review, the following
product gaps remain:

1. **Visible backend keys leak into the UI** (snake_case
   codes like `lease_tax`, `epc_contract`,
   `project_rights` are still part of the data
   dictionary and may surface in the Code column under
   edge cases).
2. **Two competing CAPEX views still confuse the
   product** — the workspace shell links to
   `sheet_capex.html` (single sheet, post-57A-3) but the
   deprecated `sheet_capex_detail.html` still lives on
   disk and historically appeared under the same tab.
3. **Add-line-item UX is missing** — there is no way to
   add a new sub-line under C.01, C.02, etc.
4. **Excel-like columns are missing** — the current sheet
   has only Line Item / Code / Amount. The user expects
   at minimum cost per MW, contingency, VAT, WHT,
   depreciation, comments, payment schedule M1–M18,
   utilisation.
5. **G20 / R99 / R102 governance guards** are in the
   pipeline but must not block CAPEX editing in the
   workspace.

This document defines the architecture for the CAPEX 2.0
direction across Phases 57A-2 through 57A-7. The
document is **design only**. The runtime changes are
split into separate draft-only PRs (57A-3 through
57A-7) so each phase can be reviewed in isolation.

## 2. Inventory of the current CAPEX UI

### 2.1 Active template

- `app/templates/partials/sheet_capex.html` (23,429 bytes
  after 57A-3) — the single CAPEX sheet. C.01–C.18
  hierarchy with sub-lines. Hard CAPEX Total
  (C.01–C.16) and Total CAPEX (C.01–C.18) are derived
  read-only subtotals. C.17 (Financing Costs) and C.18
  (Reserve Accounts) are read-only `data_financing` rows.

### 2.2 Deprecated alias

- `app/templates/partials/sheet_capex_detail.html`
  (43,961 bytes) — the original Excel-reconciliation
  Detail view from 57A. Still on disk as a deprecated
  alias but not included by `workspace_shell.html` after
  57A-3.

### 2.3 Backend field dictionary (data model)

From `app/domain/capex/source_model.py` and
`app/project_factories.py`:

| Backend key (snake_case) | Display name | C.01..C.18 mapping |
|---|---|---|
| `epc_contract` | EPC Contract | C.02 |
| `production_units` | Production Unit | C.01 |
| `epc_other` | EPC Other | C.02 |
| `project_acquisition` | Project Acquisition | C.15 |
| `project_rights` | Project Rights | C.16 |
| `ops_prep` | Operations Prep | C.15 |
| `construction_mgmt_a` | Construction Mgmt A | C.09 |
| `construction_mgmt_b` | Construction Mgmt B | C.09 |
| `commissioning` | Commissioning | C.10 |
| `audit_legal` | Audit & Legal | C.11 |
| `lease_tax` | Lease & Tax | C.07 |
| `insurances` | Insurances | C.06 |
| `contingencies` | Contingencies | C.13 |
| `taxes` | Import Taxes | C.14 |

**Each backend key is currently rendered into the
6-section summary `capex_items` list.** The 57A-3
template does a `summary_to_cat` lookup table to map
the snake_case keys to the C.01..C.05 hard categories
(C.06–C.16 only render with empty children in the
fallback path).

## 3. Current UI vs Excel target

### 3.1 Current CAPEX sheet columns (post-57A-3)

| Column | Source | Editable? | Backend key visible? |
|---|---|---|---|
| Line Item | display name | no (label) | no |
| Code | C.01..C.18 code | no (label) | no (Excel-style) |
| Amount | amount_keur | yes (user project) | n/a |

### 3.2 Excel target columns (user expectation)

| Column | Source | Editable? | Notes |
|---|---|---|---|
| Line Item | display name | no (label) | human-readable |
| Code | C.01..C.18 code | no (label) | Excel-style |
| Amount | amount_keur | yes | currently exists |
| Cost / MW | derived | no | future: `amount_keur / capacity_mw` |
| Contingency % | future model input | yes (deferred) | **not wired** |
| VAT | future model input | yes (deferred) | **not wired** |
| WHT | future model input | yes (deferred) | **not wired** |
| Depreciation | future model input | yes (deferred) | **not wired** |
| Comments | text | yes | free-form note |
| Payment schedule | future model input | yes (deferred) | M1..M18 |
| Utilisation | future model input | yes (deferred) | **not wired** |

The **Comments** column is the only deferred-input
column that is safe to add in the first CAPEX 2.0
runtime PR — it has no model effect and is purely a
display / annotation field.

The remaining deferred columns (Cost/MW, Contingency,
VAT, WHT, Depreciation, Payment schedule, Utilisation)
are **future model inputs**. They will be designed in
57A-7 but **not** wired to the model in any 57A-x
phase. The wiring requires backend changes (IDC engine,
funding drawdown, tax engine, depreciation schedule)
that are explicitly out of scope for the CAPEX 2.0 UI
arc.

## 4. One-sheet CAPEX architecture

### 4.1 Single active template

- `workspace_shell.html` includes only
  `partials/sheet_capex.html`.
- `sheet_capex_detail.html` remains on disk as a
  deprecated alias. It is **not linked from the
  workspace shell**.

### 4.2 Top-card derived totals (compact summary)

The sheet's top region shows three compact derived
cards (read-only):

1. **Hard CAPEX (C.01–C.16)** — derived from sub-lines,
   excludes financing and reserves.
2. **Financing (C.17)** — read-only, backend-computed.
3. **Reserves (C.18)** — read-only, backend-computed.
4. **Total CAPEX (C.01–C.18)** — sum of all 18
   categories.

### 4.3 Detail line grid (main working area)

Below the cards, the full C.01..C.18 hierarchy is
rendered as a single line grid:

- C.01..C.16: editable sub-line amounts in user project
  mode. Backend keys (snake_case) are **not** visible
  to the user; only the Excel-style code (e.g. C.07.01)
  and the display name are visible.
- C.17..C.18: read-only, backend-computed.
- Subtotals and totals: read-only, derived from
  sub-lines.

### 4.4 Detail/audit status block

A footer block in the same sheet shows the audit
status:

- "App is the source of truth."
- "Backend keys are preserved in `data-capex-code`
  attributes (e.g. `data-capex-code="lease_tax"`)."
- "Visible codes follow the Excel CAPEX model
  (C.01..C.18 with sub-lines)."
- "G20 / R99 / R102 governance guards are pipeline-only
  and do not block CAPEX editing."

## 5. Editable vs read-only rows

| Row | Editable in user project mode? | Read-only? |
|---|---|---|
| C.01..C.16 sub-line amount | yes | no |
| C.17 (Financing Costs) sub-line | no | yes (`data_financing`) |
| C.18 (Reserve Accounts) sub-line | no | yes (`data_financing`) |
| Category subtotal (e.g. C.01 sum) | no | yes (derived) |
| Hard CAPEX Total (C.01–C.16) | no | yes (derived) |
| Financing Total (C.17) | no | yes (derived) |
| Reserves Total (C.18) | no | yes (derived) |
| Total CAPEX (C.01–C.18) | no | yes (derived) |
| Comments column (when added) | yes | no |
| Add-line-item button | n/a | n/a |
| All rows in factory reference mode | no | yes |

## 6. Visible business codes vs hidden backend keys

### 6.1 The rule

> **Backend keys (snake_case) are NEVER visible to the
> user.** They are preserved in `data-capex-code`
> attributes for stable identification.

### 6.2 Mapping table

| Backend key | Visible code (Excel-style) | Visible name |
|---|---|---|
| `lease_tax` | C.07.01 | Lease & Property Tax |
| `epc_contract` | C.02.01 | EPC Contract |
| `project_rights` | C.16.01 | Project Rights |
| `production_units` | C.01.01 | Production Unit |
| `epc_other` | C.02.02 | EPC Other |
| `project_acquisition` | C.15.01 | Project Acquisition |
| `ops_prep` | C.15.02 | Operations Prep |
| `construction_mgmt_a` | C.09.01 | Construction Mgmt A |
| `construction_mgmt_b` | C.09.02 | Construction Mgmt B |
| `commissioning` | C.10.01 | Commissioning |
| `audit_legal` | C.11.01 | Audit & Legal |
| `insurances` | C.06.01 | Insurances |
| `contingencies` | C.13.01 | Contingencies |
| `taxes` | C.14.01 | Import Taxes |

The Code column will be made **optional** (collapsed by
default) in 57A-3 to remove the visual clutter; the
backend key remains in `data-capex-code`.

### 6.3 What if a backend key cannot be mapped to a C.01..C.18 code?

If a backend key has no C.01..C.18 mapping (e.g. a
future sub-line added by the user), it is rendered as
`—` in the Code column and the backend key remains
hidden in `data-capex-code`. The display name comes
from the data structure.

## 7. Add-line-item behavior

### 7.1 UX

- Each C.01..C.16 category row in the line grid has a
  small **+ Add line** button at the right edge.
- Clicking the button adds an empty input row under the
  category with the next available code (e.g. C.01.04
  if C.01.01, C.01.02, C.01.03 already exist).
- The new line is **in-memory only** in the first
  prototype; persistence is out of scope.

### 7.2 Numeric impact

- The new line affects:
  - The category's sub-line list.
  - The category's subtotal (derived).
  - The Hard CAPEX Total (C.01–C.16, derived).
  - The Total CAPEX (C.01–C.18, derived).
- The new line does **not** affect:
  - Any other model mechanism (P&L, Balance Sheet,
    Cash Flow, IDC, funding drawdown, tax engine,
    depreciation) unless explicitly mapped.
  - The C.17 / C.18 read-only rows.

### 7.3 Persistence

Persistence is out of scope for the first 57A-x arc.
The in-memory line is preserved across the user's
session but is **not** saved to disk. A follow-up arc
will define the persistence model.

## 8. Payment schedule scope

The payment schedule is a future model input. It is
**not** wired to the model in any 57A-x phase.

- The column header is rendered (e.g.
  `Payment M1..M18`) but the cells are read-only
  placeholders with a tooltip:
  > "Payment schedule is a future model input. The
  > IDC and funding drawdown will be derived from this
  > column in a follow-up arc."
- The IDC engine is **not** changed in 57A-x.
- The construction funding engine is **not** changed
  in 57A-x.

## 9. What remains future / backend-only

| Feature | Status | Reason |
|---|---|---|
| Cost / MW (derived column) | future | formula changes scoped out |
| Contingency column | future | future model input |
| VAT column | future | future model input |
| WHT column | future | future model input |
| Depreciation column | future | future model input |
| Comments column | CAPEX 2.0 (57A-3) | free-form, no model effect |
| Payment schedule M1..M18 | future | future model input |
| Utilisation column | future | future model input |
| Add-line-item persistence | future | schema change required |
| G20 / R99 / R102 promotion | future | out of scope |

## 10. Recommended runtime sequence

| Order | Phase | Type | Branch | Auto-merge? |
|---|---|---|---|---|
| 1 | 57A-2 (this doc) | docs/report/test | `phase57a2-capex-2-design-characterization` | YES |
| 2 | 57A-3 | runtime UI | `phase57a3-capex-hide-backend-keys` | NO (draft) |
| 3 | 57A-4 | runtime UI | `phase57a4-single-capex-sheet-layout` | NO (draft) |
| 4 | 57A-5 | runtime UI + safe data | `phase57a5-capex-line-item-hierarchy-foundation` | NO (draft) |
| 5 | 57A-6 | design first | `phase57a6-capex-add-line-item-design` | YES (docs/report/test) |
| 6 | 57A-7 | docs/report/test | `phase57a7-capex-advanced-columns-design` | YES |

After 57A-7 the design arc is complete. The next
runtime arc (e.g. 57A-8, 57A-9, 57A-10) will implement
the deferred inputs in stages, each scoped narrowly
and reviewed separately.

## 11. Hard no-go (preserved throughout)

- No financial formula changes unless explicitly
  scoped.
- No IDC calculation changes.
- No construction funding changes.
- No G20 / R99 / R102 promotion.
- No Tailwind / Alpine.
- No Portfolio / BESS / Hybrid.
- No schema / migration unless explicitly approved.
- No backend keys visible in UI.
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)
  frozen.
