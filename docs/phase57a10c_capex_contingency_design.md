# Phase 57A-10C - CAPEX contingency design

> Type: docs / report / test-only
> Branch: `phase57a10c-capex-contingency-design`
> Requested base: latest main after PR #516 merge
> Prior merge anchor: `5578b02fef3c1d9ddb176cd40099626b97d2e5a9`
> rc1: `b425a0708719eaa5e1d922b1008e5609758e0ad4` - untouched
> Status: design-only. No runtime, schema, Run, export, or UI implementation in this phase.

## 1. Purpose

57A-10 established the advanced-column foundation. 57A-10A verified that
comments were already safe. 57A-10B locked cost-per-MW as derived evidence
only. 57A-10C now defines the canonical architecture for **Contingency**
before any runtime implementation touches CAPEX totals, scenario behavior,
funding, IDC, or export.

This phase is intentionally design-only. It does **not**:

- change runtime behavior
- change persistence behavior
- change Run materialization
- change Excel export
- change formulas
- change schema or migrations
- change CAPEX UI templates or static assets

## 2. Reviewed inputs

The design was grounded in the merged CAPEX 2.0 arc and current product
surfaces:

- `docs/phase57a2_capex_2_design_characterization.md`
- `docs/phase57a7_capex_advanced_columns_design.md`
- `docs/phase57a10_capex_advanced_columns_foundation_design.md`
- `docs/phase57a10b_capex_cost_per_mw_derived_design.md`
- `docs/phase57a9a_capex_add_line_persistence_design_gate.md`
- `docs/phase57a9b_capex_sub_lines_schema.md`
- `docs/phase57a9c_capex_sub_lines_save_load.md`
- `docs/phase57a9d_capex_sub_lines_run_integration.md`
- `docs/phase57a9e_capex_sub_lines_excel_export_audit_integration.md`
- `docs/phase57a9h_scenario_duplication_capex_override_fix.md`
- `app/templates/partials/sheet_capex.html`
- `app/excel_export.py`
- `app/persistence/capex_sub_lines.py`
- `app/persistence/scenarios_repository.py`
- current TUHO / Oborovo CAPEX patterns and the Generic Solar / Wind roadmap

## 3. Current-state findings

### 3.1 Current CAPEX meaning

Current CAPEX persistence and Run semantics already treat:

- `amount_keur` as the authoritative CAPEX baseline value
- scenario amount override as **replace baseline, not delta**
- user-added CAPEX sub-lines as project-owned UUID identities

No contingency runtime field exists yet in the CAPEX persistence stack.

### 3.2 Existing category precedent

The canonical hierarchy includes:

- `C.13` Contingencies

That is useful as a **reference pattern**, but it must not be misread as a
complete future design for user-added sub-lines. CAPEX 2.0 needs a rule that
works for:

- factory reference lines
- user-added sub-lines such as `C.02.U001`
- scenario overrides
- future Sources & Uses / IDC work

## 4. Question 1 - contingency ownership model

### Option A

Contingency is a **category-level** value only.

### Option B

Contingency is a **line-item** value only.

### Option C

Both category-level and line-item contingency are supported.

### Preferred option

**Option B**

Contingency should be defined as a **line-item-level input** that can be
aggregated upward to category and project totals.

### Why Option B wins

1. It aligns with CAPEX 2.0 sub-line ownership and user-added rows.
2. It avoids hiding contingency assumptions inside a category shell.
3. It makes scenario overrides and export evidence easier to audit.
4. It works for factory and generic paths without hardcoding template logic.
5. It creates the cleanest future bridge to funding and IDC because the model
   can later choose whether contingency is funded line-by-line or in aggregate.

### Rejected options

#### Option A rejected

Reasons:

- category-level only is too coarse for user-added rows
- it obscures which sub-lines carry contingency and which do not
- it creates awkward behavior when a user adds `C.02.U001` or `C.08.U001`
- it would likely force brittle category-specific assumptions

#### Option C rejected

Reasons:

- supporting both category-level and line-level contingency introduces double
  counting risk
- it raises validation complexity
- it creates unclear source-of-truth rules for totals and scenarios

## 5. Question 2 - source-of-truth model

Two candidate interpretations matter:

1. base amount authoritative, contingency stored separately, total derived
2. total including contingency authoritative, base amount derived backward

### Preferred source-of-truth

**Base amount remains authoritative.**

Contingency should be stored as a separate line-level treatment input:

- either `contingency_pct`
- or, in a later implementation decision, `contingency_pct` plus an explicit
  derived contingency cost

The authoritative economic base remains:

- `base_amount_keur`

The future effective total becomes derived:

- `effective_total_keur = base_amount_keur + derived_contingency_cost_keur`

### Why this wins

1. It preserves the already-merged `amount_keur` semantics.
2. It keeps contingency transparent instead of hiding it in the amount.
3. It avoids rewriting parity assumptions for TUHO / Oborovo.
4. It supports future audit surfaces that can show base, contingency, and
   effective total separately.

### Total calculation recommendation

Future CAPEX totals should be calculated as:

1. sum of base amounts
2. plus sum of derived contingency costs
3. equals effective CAPEX total

That means contingency should:

- roll into **total CAPEX**
- remain available as a **separate evidence column / subtotal**

This is the safest answer to Question 5 as well: contingency is part of the
economic total, but must stay visible as a separate component.

## 6. Question 3 - scenario semantics

Scenario behavior must stay consistent with the amount override model.

### If scenario changes base amount

Then:

- base amount is replaced for that scenario
- derived contingency cost is recomputed from the scenario-effective base
- effective total updates automatically

### If scenario changes contingency %

Then:

- contingency % is replaced for that scenario
- derived contingency cost is recomputed
- effective total updates automatically

### Core semantic rule

> Scenario overrides replace baseline values. They are not deltas.

### Required future formula

If contingency later becomes a percentage input:

`derived_contingency_cost_keur = effective_base_amount_keur * effective_contingency_pct / 100`

`effective_total_keur = effective_base_amount_keur + derived_contingency_cost_keur`

### Important consequence

There should be **no direct scenario override key for derived contingency cost**
unless a future design intentionally introduces a different mode. The clean
default is:

- override base amount and/or contingency %
- derive contingency cost
- derive effective total

## 7. Question 4 - user-added CAPEX rows

For user-added rows such as:

- `C.02.U001`
- `C.08.U001`

contingency **can exist** in the future design.

### Storage

Future storage should be:

- project-owned baseline field(s) on the project-level sub-line identity
- future scenario override keys for approved contingency fields only

Contingency must reference the same project-level `sub_line_id` used by the
rest of the CAPEX persistence stack.

### Display

Future display should show:

- base amount
- contingency %
- derived contingency cost
- effective total

### Export

Future export should show:

- baseline amount
- effective base amount
- contingency %
- derived contingency cost
- effective total

Contingency for user-added rows should be treated as readably auditable line
evidence, not as a hidden category uplift.

## 8. Question 5 - CAPEX totals

### Recommendation

Contingency should:

- roll into **total CAPEX**
- remain visible as a **separate evidence component**
- not be collapsed so completely that users cannot tell base from uplift

### Preferred future totals view

At category and project level, future reporting should be able to present:

1. base CAPEX subtotal
2. contingency subtotal
3. effective CAPEX subtotal / total

That gives both:

- finance readability
- downstream funding compatibility

## 9. Question 6 - funding / IDC boundary

57A-10C does not implement funding or IDC behavior, but it must define the
boundary clearly.

### Future interaction rule

Contingency should be treated as part of **fundable effective CAPEX** only
when a later dedicated phase explicitly wires it into:

- Sources & Uses
- construction funding
- IDC
- debt sizing

### What 57A-10C does lock

When later wired, the sequence should conceptually be:

1. determine effective CAPEX including contingency
2. apply funding allocation rules
3. derive drawdown timing
4. derive IDC / debt sizing consequences

### What 57A-10C does not allow

- no premature assumption that contingency is automatically debt-funded
- no premature assumption that contingency is excluded from debt sizing
- no premature assumption that contingency is always fully drawn at the same
  timing as the base line

Those are later funding-policy decisions, not part of this architecture pass.

## 10. Question 7 - Generic Solar / Wind compatibility

The contingency design must support:

- TUHO
- Oborovo
- Generic Solar
- Generic Wind

without template-specific hardcoding.

### Compatibility rule

Contingency semantics must rely only on:

- base amount
- contingency treatment field(s)
- project-owned CAPEX sub-line identity

not on:

- template-specific category naming
- TUHO-only or Oborovo-only assumptions
- technology-specific heuristics

### Governance rule

Generic Solar / Wind remain:

- exploratory / unvalidated unless separately validated
- not parity evidence for TUHO / Oborovo

So the architecture supports generic paths, but does not promote them.

## 11. Question 8 - Excel export strategy

57A-10C does not implement export changes, but it locks the future shape.

### `CapEx`

Future top-level CAPEX output may show:

- base CAPEX
- contingency subtotal
- effective CAPEX including contingency

### `CapEx_Items`

If contingency is surfaced later here, it should appear as:

- base amount
- contingency %
- derived contingency cost
- effective total

### `CapEx_SubLines_Audit`

This is the preferred first detailed export surface.

Future line-level contingency evidence should appear here as:

- `Base Amount (kEUR)`
- `Contingency %`
- `Derived Contingency Cost (kEUR)`
- `Effective Total (kEUR)`

### Reconciliation sheets

Reconciliation sheets should treat contingency as:

- explanatory evidence
- visible component of effective CAPEX
- not a hidden adjustment

## 12. Question 9 - future interaction matrix

### Cost per MW

If contingency is later active, future cost/MW evidence should use the
relevant effective amount being displayed:

- base-only cost/MW if the surface is explicitly base-only
- effective cost/MW if the surface is explicitly total including contingency

The label must make that basis explicit.

### VAT / WHT

Contingency must be defined before VAT / WHT wiring so later phases can decide
whether tax treatment applies to:

- base amount only
- or effective amount including contingency

57A-10C does not choose tax law treatment; it only preserves the architecture
space for that later decision.

### Depreciation

Contingency may later affect the depreciable basis only if a dedicated
depreciation phase explicitly says so. No assumption is embedded here.

### Payment schedules / utilisation

If contingency later affects funded effective CAPEX, schedule/utilisation
phases must decide whether contingency follows:

- the same payment schedule as base amount
- or a distinct timing rule

57A-10C does not pre-wire that answer.

## 13. Preferred architecture

### Architecture summary

1. contingency is a **line-item-level** concept
2. base amount remains authoritative
3. contingency is a separate treatment input
4. contingency cost is derived
5. effective total is derived from base plus contingency
6. scenario overrides replace baseline values, not delta
7. contingency rolls into effective CAPEX totals but remains visible as
   separate evidence

## 14. Rejected architectures

### Rejected: category-level-only contingency

- too coarse for CAPEX 2.0 sub-lines
- weak auditability
- awkward for user-added rows

### Rejected: total-including-contingency authoritative

- hides base-versus-uplift meaning
- creates parity and export ambiguity
- weakens funding / IDC transparency later

### Rejected: simultaneous category + line contingency

- double-counting risk
- validation complexity
- unclear source-of-truth behavior

## 15. Implementation complexity and migration impact

### Complexity

- low for a later display-only evidence step
- medium for persistence + scenario override support
- high when contingency is eventually wired into funding / IDC / debt sizing

### Migration impact

- no migration required for this design phase
- a future runtime phase may require schema extension if contingency fields are
  persisted explicitly
- no redesign of UUID ownership is needed

### Parity impact

- TUHO / Oborovo parity remains safest if contingency is kept transparent as
  base + derived uplift
- generic paths keep the same exploratory governance status

### Export impact

- safe if first introduced as read-only audit evidence
- risk increases only when contingency becomes calculation-driving

### Rollback strategy

Because the preferred model keeps base amount authoritative, a future
contingency rollout can be rolled back by:

- removing the contingency field from display/export
- ignoring the derived contingency evidence
- without redefining core CAPEX amount semantics

## 16. Estimated future implementation sequence

Recommended future path:

1. **57A-10D**
   - lock explicit persistence field strategy and safe validation rules
2. **57A-10E**
   - add contingency evidence to audit/export surfaces only
3. **57A-10F**
   - add controlled runtime support for contingency in CAPEX totals
4. **57A-10G**
   - later funding / IDC / debt sizing integration if separately approved

That keeps the first runtime step narrow and audit-friendly.

## 17. Design conclusions

- contingency should be modeled at line-item level
- base amount should remain authoritative
- contingency cost should be derived
- effective total should be derived
- scenario changes should recompute contingency and effective total
- user-added sub-lines should support the same rule as factory lines
- future export should first surface contingency as read-only audit evidence
- funding / IDC consequences must wait for a later dedicated phase

## 18. Recommendation

**PASS**

Rationale:

- aligns with the CAPEX 2.0 UUID ownership model
- keeps source of truth clear
- preserves scenario replace semantics
- stays compatible with TUHO, Oborovo, Generic Solar, and Generic Wind
- creates the safest bridge to future funding / IDC work without sneaking it
  into this phase
