# Phase 57A-10D - CAPEX VAT / WHT / depreciation basis design

> Type: docs / report / test-only
> Branch: `phase57a10d-capex-vat-wht-depreciation-basis-design`
> Requested base: latest main after PR #517 merge
> Prior merge anchor: `fe63fe16d1bfe133a47bbbd2b47801906fd59746`
> rc1: `b425a0708719eaa5e1d922b1008e5609758e0ad4` - untouched
> Status: design-only. No runtime, schema, Run, export, tax engine, depreciation engine, or UI implementation in this phase.

## 1. Purpose

57A-10 established the advanced-column foundation.
57A-10A confirmed comments as safe metadata.
57A-10B defined cost-per-MW as derived evidence only.
57A-10C defined contingency semantics and the funding / IDC boundary.

57A-10D now defines the **VAT / WHT / depreciation basis architecture** for
CAPEX line items before any runtime, schema, export, or tax/depreciation
implementation phase begins.

This phase is intentionally design-only. It does **not**:

- change runtime behavior
- change persistence behavior
- change Run materialization
- change Excel export
- change financial formulas
- change schema or migrations
- change CAPEX UI templates or static assets
- wire tax engine behavior
- wire depreciation engine behavior
- wire IDC or construction time-phasing

## 2. Reviewed inputs

The design was grounded in the merged CAPEX 2.0 arc and the current tax /
depreciation evidence surfaces:

- `docs/phase57a7_capex_advanced_columns_design.md`
- `docs/phase57a10_capex_advanced_columns_foundation_design.md`
- `docs/phase57a10b_capex_cost_per_mw_derived_design.md`
- `docs/phase57a10c_capex_contingency_design.md`
- `docs/pre_depreciation_merge_review.md`
- `docs/runtime_wiring_plan.md`
- `docs/phase9_r99_r102_audit_gate_validation.md`
- `docs/v1_3_bankable_framework_checkpoint.md`
- CAPEX persistence stack 57A-9B through 57A-9H
- `app/ui/project_context.py`
- `app/excel_export.py`
- current TUHO / Oborovo CAPEX reference behavior
- Generic Solar / Wind roadmap constraints

## 3. Current-state findings

### 3.1 CAPEX 2.0 ownership model already exists

Current CAPEX persistence and scenario behavior already establish:

- project-owned CAPEX sub-line identity
- project-owned baseline amount
- scenario override by `sub_line_id`
- replace-baseline semantics, not delta semantics

This is the baseline architecture any future VAT / WHT / depreciation fields
must fit into.

### 3.2 Depreciation already exists elsewhere in the product

The codebase already has tax/book depreciation reporting surfaces and a
depreciation framework, but CAPEX 2.0 line-item advanced columns are **not**
yet the authoritative source for that engine.

That means 57A-10D must preserve a clean separation:

- CAPEX line-level metadata architecture
- future authoritative tax / depreciation wiring

### 3.3 Existing CAPEX detail examples are informative, not authoritative

`app/ui/project_context.py` already exposes illustrative advanced CAPEX rows
with fields like:

- `vat_rate_pct`
- `vat_cost`
- `wth_pct`
- `depreciable`

Those are useful evidence of intended UX/reporting direction, but they are
not yet a canonical persisted CAPEX 2.0 basis contract.

## 4. Question 1 - VAT basis

### Core basis question

What should VAT apply to?

Candidate bases:

1. base amount only
2. base amount + contingency
3. gross total after other taxes/fees

### Preferred VAT basis

**VAT basis should be defined on the taxable CAPEX basis selected by the line,
with the default architectural recommendation being:**

> **VAT applies to effective CAPEX basis before WHT and before depreciation,
> and that basis should normally mean base amount plus any contingency that is
> part of the taxable supplier invoice amount.**

That translates to a future explicit basis choice, not a hidden assumption.

### Architectural recommendation

Future CAPEX line metadata should support:

- `vat_applicability`
- `vat_recoverability`
- `vat_rate_pct`
- `vat_basis_mode`

Recommended basis modes:

- `base_only`
- `base_plus_contingency`

### Recoverable vs non-recoverable VAT

The design must distinguish:

- **recoverable VAT**
  - usually audit / cash-timing / balance-sheet relevant
  - not automatically part of long-term CAPEX economic basis
- **non-recoverable VAT**
  - can become part of effective economic CAPEX

### Should VAT affect Run CAPEX totals?

**Not by default today.**

Future design recommendation:

- line-level VAT should live as CAPEX line treatment metadata
- but whether VAT rolls into economic CAPEX totals should be a later explicit
  policy choice, not implied by the presence of a VAT rate field

### Where VAT belongs

Preferred answer:

- CAPEX line metadata stores the basis inputs
- tax module later decides tax treatment
- export/audit layer shows the resulting basis and disclosure

That is safer than baking VAT directly into current CAPEX totals now.

## 5. Question 2 - WHT basis

### Nature of WHT

WHT should be treated as:

- line-level metadata when it is relevant to a specific supplier/payment line
- jurisdiction / supplier dependent
- primarily a **tax / cash-timing treatment item**

not a universal CAPEX uplift applied blindly to every line.

### Preferred WHT architecture

Future CAPEX line metadata should support:

- `wht_applicability`
- `wht_rate_pct`
- `wht_basis_mode`
- `wht_gross_up_mode`

Recommended basis modes:

- `none`
- `base_only`
- `base_plus_contingency`

Recommended gross-up modes:

- `withheld_from_payment`
- `grossed_up_by_payer`

This keeps the design explicit about whether the withholding is deducted from
the supplier payment or economically borne through gross-up by the payer.

### Should WHT affect CAPEX totals?

Default architectural recommendation:

- WHT should **not** automatically redefine core CAPEX totals
- WHT is primarily tax / cashflow treatment metadata first
- whether it becomes economic CAPEX should require an explicit later policy
  decision

This prevents hidden shifts in CAPEX totals for TUHO / Oborovo parity.

### WHT as cost vs tax vs cash timing

Preferred design answer:

- WHT is fundamentally a tax / settlement treatment
- it may create economic cost in some jurisdictions or contract forms
- but the architecture should preserve that distinction explicitly instead of
  forcing one universal assumption

## 6. Question 3 - depreciation basis

### Required fields

Future CAPEX line metadata should support:

- `depreciable_flag`
- `depreciation_category`
- `useful_life_years`
- `depreciation_basis_mode`

### Preferred depreciation basis

Depreciation should be based on a future explicit basis mode, not an implicit
blend. The recommended supported modes are:

- `base_only`
- `base_plus_nonrecoverable_vat`
- `base_plus_contingency`
- `base_plus_contingency_plus_nonrecoverable_vat`

### Why not one fixed rule now

Because depreciation basis depends on:

- recoverable vs non-recoverable VAT
- whether contingency is capitalizable
- jurisdiction and accounting policy
- tax vs book depreciation conventions

57A-10D should preserve that choice space without pretending it is settled.

### Relationship to current depreciation roadmap

The design must preserve separation from the current tax/book depreciation
framework until a dedicated runtime phase intentionally wires CAPEX 2.0 line
metadata into:

- tax depreciation basis
- book depreciation basis
- canonical depreciation audit flows

## 7. Question 4 - scenario semantics

Scenario behavior should stay aligned with the CAPEX 2.0 architecture:

- override by `sub_line_id`
- replace baseline values, not delta

### Which fields may be scenario-overridden later

Potentially scenario-overrideable:

- `vat_applicability`
- `vat_recoverability`
- `vat_rate_pct`
- `vat_basis_mode`
- `wht_applicability`
- `wht_rate_pct`
- `wht_basis_mode`
- `wht_gross_up_mode`
- `depreciable_flag`
- `depreciation_category`
- `useful_life_years`
- `depreciation_basis_mode`

### Recommended default

For future runtime phases:

- scalar metadata fields may be overrideable if explicitly allowlisted
- overrides replace baseline values, not delta
- no derived tax/depreciation amounts should be directly overridden by default

### Duplicated scenarios

Duplicated scenarios must preserve:

- the same project-owned `sub_line_id`
- copied override metadata

This mirrors the 57A-9H integrity rule.

### Deleted / re-added lines

If a user deletes and re-adds a logical line:

- a new line identity may exist
- tax / depreciation overrides must follow actual `sub_line_id` ownership
- no orphaned override record should silently remap itself

That keeps override semantics explicit and auditable.

## 8. Question 5 - user-added CAPEX rows

For user-added rows such as:

- `C.02.U001`
- `C.08.U001`

VAT / WHT / depreciation metadata **can exist** in the design.

### Ownership

Preferred answer:

- owned at the project-level sub-line
- scenario overrides reference the same `sub_line_id`

### Export

Future export should show:

- baseline metadata
- effective scenario metadata
- any derived audit interpretation

### Scenario override behavior

Future scenario behavior should:

- override by `sub_line_id`
- replace baseline values
- preserve copied overrides on scenario duplication

## 9. Question 6 - export / audit strategy

57A-10D does not implement export changes, but it locks the future structure.

### `CapEx`

Future top-level CAPEX sheet should not become the first place for dense
tax/depreciation detail. It may show compact indicators only when useful.

### `CapEx_Items`

Future read-only columns may show concise line metadata such as:

- VAT applicability / rate
- WHT applicability / rate
- depreciable flag
- depreciation category / life

### `CapEx_SubLines_Audit`

This is the preferred first detailed export surface for CAPEX line tax basis
evidence. Future columns may include:

- `VAT Applicable`
- `VAT Recoverability`
- `VAT Rate %`
- `VAT Basis Mode`
- `WHT Applicable`
- `WHT Rate %`
- `WHT Basis Mode`
- `WHT Gross-Up Mode`
- `Depreciable`
- `Depreciation Category`
- `Useful Life Years`
- `Depreciation Basis Mode`

### Tax / depreciation audit sheets

Preferred future pattern:

- keep CAPEX line metadata evidence in CAPEX audit sheets
- keep tax/depreciation calculation outputs in dedicated audit sheets
- link them by clear basis labels rather than collapsing them into one opaque
  report

### Reconciliation sheets

Reconciliation sheets should treat these fields as:

- basis evidence
- treatment evidence
- not hidden arithmetic

## 10. Question 7 - Generic Solar / Wind compatibility

The design must support:

- TUHO
- Oborovo
- Generic Solar
- Generic Wind

without template-specific hardcoding.

### Compatibility rule

The architecture must rely on:

- line-level basis metadata
- project-owned CAPEX sub-line identity
- scenario override by `sub_line_id`

not on:

- TUHO-only tax assumptions
- Oborovo-only depreciation lives
- technology-specific heuristics hidden in schema

### Governance rule

Generic Solar / Wind remain:

- exploratory / unvalidated unless separately validated
- not parity evidence for TUHO / Oborovo

## 11. Question 8 - implementation options

### Option A - widen `capex_sub_lines` table

Pros:

- simplest query path
- easy export joins
- clear scalar validation for common fields

Cons:

- many nullable columns
- early schema commitment
- awkward if supplier/jurisdiction detail becomes more structured later

Migration impact:

- medium

Validation complexity:

- low to medium

Export compatibility:

- high

Rollback risk:

- medium

### Option B - `capex_sub_line_tax_details` table

Pros:

- strong separation of concerns
- cleaner future normalization for tax-specific metadata

Cons:

- more joins
- more migration surface
- higher complexity for simple fields

Migration impact:

- medium to high

Validation complexity:

- medium

Export compatibility:

- medium

Rollback risk:

- medium

### Option C - JSON metadata on sub-line

Pros:

- flexible
- low schema churn

Cons:

- weaker validation
- harder auditability
- harder long-term reporting/query discipline

Migration impact:

- low

Validation complexity:

- high

Export compatibility:

- medium to low

Rollback risk:

- low to medium

### Option D - hybrid scalar columns + detail tables

Pros:

- stable scalar basis fields live on the sub-line
- more complex supplier/jurisdiction/detail structures can evolve separately
- best long-term fit for export and audit clarity

Cons:

- highest upfront architecture discipline
- more moving parts than a pure widen-table approach

Migration impact:

- medium

Validation complexity:

- medium

Export compatibility:

- high

Rollback risk:

- medium

## 12. Preferred architecture

### Recommendation

**Option D** is preferred.

Preferred structure:

1. keep core scalar basis fields close to the CAPEX sub-line
2. reserve separate detail structures for richer tax / depreciation treatment
   only if and when needed
3. keep scenario overrides keyed by `sub_line_id`
4. keep derived tax/depreciation amounts out of persistence by default

### Why Option D wins

- best balance of validation and flexibility
- strong export/audit compatibility
- avoids overloading a single JSON blob
- avoids prematurely normalizing everything into separate tables

## 13. Rejected alternatives

### Rejected as full default: pure widen-table only

- good for short-term simplicity
- weaker if treatment detail grows

### Rejected as full default: pure tax-details table only

- too heavy for the first CAPEX 2.0 metadata step

### Rejected as full default: JSON-only

- too weak for governance-grade validation and export clarity

## 14. Implementation sequence

Recommended future path:

1. **57A-10E**
   - lock persistence field shortlist and validation rules
2. **57A-10F**
   - add audit/export evidence only
3. **57A-10G**
   - add safe persistence + scenario override support
4. **57A-10H**
   - later tax/depreciation engine wiring if separately approved

## 15. Risk framing

### Parity risk

- low if first rollout is audit-only
- medium if line metadata is allowed to influence runtime too early

### Tax risk

- high if recoverability, WHT gross-up, or depreciation basis are hardcoded
  prematurely

### Excel replacement value

- high, because line-level VAT / WHT / depreciation basis metadata is one of
  the clearest remaining Excel replacement gaps

### Rollback strategy

Because the preferred architecture keeps basis metadata explicit and derived
outputs non-authoritative at first, rollback can remove display/export
evidence without redefining CAPEX amount semantics.

## 16. Design conclusions

- VAT belongs as explicit CAPEX line treatment metadata, not hidden math
- WHT belongs as explicit jurisdiction/supplier treatment metadata, not a
  universal CAPEX uplift
- depreciation basis must remain explicit and mode-driven
- scenario semantics should stay replace-not-delta by `sub_line_id`
- user-added CAPEX rows support the same ownership and override model
- export should surface basis evidence first, not hidden calculation-driving
  totals
- Generic Solar / Wind compatibility is preserved without hardcoding

## 17. Recommendation

**PASS**

Rationale:

- preserves CAPEX 2.0 ownership discipline
- keeps tax and depreciation architecture explicit
- supports TUHO / Oborovo and generic paths without hardcoding
- creates a safer bridge to future implementation than ad hoc field growth
