# Phase 57A-10B - CAPEX cost-per-MW derived design

> Type: docs / report / test-only
> Branch: `phase57a10b-capex-cost-per-mw-derived-design`
> Requested base: latest main after PR #515 merge
> Prior merge anchor: `660fe4eb4d8bd7e3735e9120e353cf40c9c1abeb`
> rc1: `b425a0708719eaa5e1d922b1008e5609758e0ad4` - untouched
> Status: design-only. No runtime, schema, Run, export, or UI implementation in this phase.

## 1. Purpose

57A-10 established the advanced-columns foundation and left `cost_per_mw`
as a derived field. 57A-10B narrows that one topic into an explicit
architecture contract so a future implementation phase does not create:

- a second CAPEX source of truth
- scenario-state ambiguity
- export mismatch between baseline and effective values
- template-specific Solar/Wind assumptions
- hidden parity drift for TUHO / Oborovo

This phase is intentionally design-only. It does **not**:

- change runtime behavior
- change persistence behavior
- change Run materialization
- change Excel export
- change formulas
- change schema or migrations
- change CAPEX UI templates or static assets

## 2. Reviewed inputs

The design was grounded in the current merged CAPEX stack and roadmap:

- `docs/phase57a10_capex_advanced_columns_foundation_design.md`
- `reports/phase57a10_capex_advanced_columns_foundation_design.json`
- `docs/phase57a7_capex_advanced_columns_design.md`
- `docs/phase57a2_capex_single_sheet_direction_characterization.md`
- `docs/phase57a3_capex_single_sheet_runtime.md`
- `app/templates/partials/sheet_capex.html`
- `app/excel_export.py`
- `app/persistence/capex_sub_lines.py`
- `app/persistence/scenarios_repository.py`
- `app/ui/project_context.py`

## 3. Current-state findings

### 3.1 Existing display today

Current CAPEX UI already shows a **derived top-card metric**:

- label: `CAPEX / MW`
- formula today: `capex_grand_total / project_ctx.capacity_mw`
- location: `sheet_capex.html`

This means the product already behaves as if cost-per-MW is **derived**,
not user-authored.

### 3.2 Current persistence today

Current CAPEX persistence stores:

- project-owned sub-line identity
- baseline `amount_keur`
- descriptive metadata such as `comments`

It does **not** persist a dedicated authoritative `cost_per_mw` field.

### 3.3 Current scenario model today

Scenario behavior already treats CAPEX amount as:

- baseline project amount
- plus scenario override state
- using **replace baseline, not delta** semantics

There is no separate cost-per-MW override model today.

## 4. Question 1 - source of truth

### Option A

`amount_keur` authoritative, `cost_per_mw` derived.

### Option B

`cost_per_mw` authoritative, `amount_keur` derived.

### Option C

dual-entry model where both can be entered and one reconciles the other.

### Preferred option

**Option A**

`amount_keur` remains authoritative.

`cost_per_mw` remains a **derived display / audit metric**.

### Why Option A wins

1. It matches current runtime reality.
2. It matches current scenario override semantics.
3. It avoids circular ambiguity when project capacity changes.
4. It avoids two user-editable values that can drift apart.
5. It keeps export evidence understandable:
   baseline amount -> effective amount -> derived cost/MW.

### Rejected options

#### Option B rejected

Reasons:

- deriving amount from cost/MW would make project capacity a hidden primary
  driver of CAPEX values
- changing capacity would silently rewrite CAPEX amounts
- this is much riskier for Run, parity, and audit interpretation

#### Option C rejected

Reasons:

- dual-entry creates reconciliation conflict
- requires tie-break rules when amount and cost/MW disagree
- raises user confusion and scenario-copy complexity
- introduces extra validation and migration burden for little benefit

## 5. Question 2 - scenario semantics

If Scenario A changes `amount_keur`, then `cost_per_mw` should:

- **auto-update**
- never remain fixed independently
- not be directly overrideable

### Recommendation

Scenario semantics must be:

> `effective_cost_per_mw = effective_amount_keur / effective_capacity_mw`

That means:

- baseline amount changes -> derived cost/MW updates
- scenario override amount changes -> derived cost/MW updates
- copied scenarios inherit the same amount override semantics and therefore
  the same derived cost/MW semantics

There should be **no dedicated scenario override key** for cost-per-MW.

## 6. Question 3 - user-added sub-lines

For user-added lines such as:

- `C.02.U001`
- `C.08.U001`

the design is:

### Display

- cost/MW may be shown as a read-only derived value beside that sub-line in
  a future UI phase
- it should be clearly labelled as derived

### Export

- export should show:
  - baseline amount
  - effective amount
  - derived cost/MW
- if scenario overrides exist, derived cost/MW must use the **effective**
  amount, not the baseline amount

### Persistence

- cost/MW is **not persisted**
- no authoritative field is added
- no scenario-owned cost/MW record is added

## 7. Question 4 - capacity dependency

The capacity source must be explicit and consistent:

### Recommended capacity source

Use the project technical field:

- `capacity_mw`

Interpretation:

- the project's installed capacity value used elsewhere in runtime and UI

### Rejected capacity sources

- `net MW` - not a currently standardized persistence/runtime field here
- `export capacity` - too ambiguous and grid-specific for a generic design
- template-specific custom capacity interpretation - incompatible with the
  generic Solar/Wind path

### Resulting formula

`cost_per_mw = effective_amount_keur / capacity_mw`

If `capacity_mw <= 0` or missing:

- no derived cost/MW value should be emitted
- display/export should show blank / N/A, not 0

## 8. Question 5 - Generic Solar / Wind compatibility

The design must work for:

- TUHO
- Oborovo
- Generic Solar
- Generic Wind

without template-specific rules.

### Compatibility rule

Cost/MW derivation must rely only on:

- effective CAPEX amount
- project `capacity_mw`

not on:

- template-specific section naming
- technology-specific heuristics
- parity approval state

### Governance rule

Generic Solar / Wind outputs remain:

- exploratory / unvalidated unless separately validated
- not parity evidence for TUHO / Oborovo

So cost/MW may be **shown**, but must not be framed as validated parity
 evidence for generic paths.

## 9. Question 6 - Excel export strategy

57A-10B does not implement export changes, but it locks the future shape.

### `CapEx` sheet

- keep current totals-oriented summary
- any future top-level CAPEX / MW value should remain derived from total
  effective CAPEX and project capacity
- do not make it an authoritative input cell

### `CapEx_Items`

- if cost/MW is surfaced here later, show it as a derived read-only column
- it should use the row's effective amount and project capacity

### `CapEx_SubLines_Audit`

- this is the preferred place for first detailed export evidence
- future cost/MW export should appear as:
  - `Derived Cost / MW (kEUR / MW)`
- it should be computed from:
  - `Effective Amount (kEUR)`
  - `capacity_mw`
- it should not appear as a persisted field

### Reconciliation sheets

- reconciliation output should treat cost/MW as explanatory evidence only
- never as an independent authoritative metric to reconcile against runtime

## 10. Question 7 - future advanced-column interaction

Future interaction design:

### Contingency

- if contingency later changes effective CAPEX amount, derived cost/MW should
  reflect the resulting effective amount used by the relevant surface
- no separate cost/MW persistence

### VAT / WHT

- if these remain treatment metadata rather than core CAPEX amount, they
  should not silently redefine the meaning of CAPEX / MW
- future phases must explicitly choose whether cost/MW is:
  - pre-tax / pre-VAT CAPEX
  - or all-in CAPEX
- until then, cost/MW should continue to mean amount-based CAPEX only

### Depreciation

- depreciation metadata has no effect on cost/MW derivation

### Payment schedule / utilisation

- these affect timing, drawdown, and future IDC
- they do not change the fundamental static cost/MW formula unless a later
  phase explicitly introduces time-sliced cost/MW reporting

## 11. Preferred architecture

### Architecture summary

1. `amount_keur` remains authoritative.
2. `cost_per_mw` remains derived.
3. scenario amount overrides auto-update cost/MW.
4. no direct cost/MW persistence.
5. no direct cost/MW scenario override key.
6. project `capacity_mw` is the single capacity basis.
7. export treats cost/MW as derived audit evidence only.

## 12. Rejected architectures

### Rejected: authoritative cost/MW

- hidden dependency on capacity
- fragile under capacity edits
- high migration and audit risk

### Rejected: dual-entry amount + cost/MW

- conflicting sources of truth
- validation complexity
- scenario-copy ambiguity
- higher rollback complexity

## 13. Implementation complexity and migration impact

### Complexity

- low for display-only future step
- medium for export evidence step
- high only if future phases try to blend cost/MW with tax / schedule / IDC

### Migration impact

- none for current persistence if kept derived
- no schema migration required for first implementation
- no scenario migration required

### Parity impact

- TUHO / Oborovo parity remains stable if cost/MW is derived from already
  authoritative values
- generic Solar/Wind governance caveat remains unchanged

### Export impact

- safe if limited to derived read-only columns/notes
- risky only if treated as authoritative input

### Rollback strategy

- because cost/MW remains derived, rollback is easy:
  remove the display/export evidence without data migration

## 14. Estimated future implementation sequence

Recommended future path:

1. **57A-10C**
   - add explicit docs/test-backed display strategy only, if needed
2. **57A-10D**
   - add derived cost/MW evidence to `CapEx_SubLines_Audit`
3. **57A-10E**
   - add optional read-only per-line UI display if still wanted
4. only later consider interactions with contingency/VAT/WHT/schedule

That keeps the first runtime step display-only and low risk.

## 15. Design conclusions

- `amount_keur` must stay authoritative.
- `cost_per_mw` must stay derived.
- scenario changes must auto-update cost/MW.
- user-added CAPEX sub-lines use the same derived rule as factory lines.
- project `capacity_mw` is the explicit denominator.
- cost/MW should first appear as read-only audit/display evidence only.
- no persistence, schema, Run, or export authority changes are justified for
  cost/MW at this stage.

## 16. Recommendation

**PASS**

Rationale:

- safest source-of-truth model
- lowest migration risk
- consistent with current CAPEX runtime and scenario architecture
- compatible with TUHO, Oborovo, Generic Solar, and Generic Wind
- easiest rollback if later presentation choices change
