# Phase 57A-10E - CAPEX tax metadata persistence design

> Type: docs / report / test-only  
> Branch: `phase57a10e-capex-tax-metadata-persistence-design`  
> Requested base: post-57A-10D main (`61650d50be0468c4305275668b289b3e462f384e`)  
> rc1: `b425a0708719eaa5e1d922b1008e5609758e0ad4` - untouched  
> Status: persistence and validation design only. No runtime, schema, export, Run, tax, depreciation, or IDC implementation in this phase.

## 1. Purpose

57A-10D selected the preferred high-level architecture for VAT, WHT, and
depreciation metadata:

> **Option D - hybrid scalar columns + detail tables**

57A-10E narrows that into a concrete persistence contract. This phase
defines:

- ownership of VAT / WHT / depreciation metadata
- exact future field shortlist
- scenario override semantics
- UUID binding rules
- validation rules
- export authority boundaries
- phased migration sequence for 57A-10F / 10G / 10H

This phase does **not**:

- modify runtime behavior
- modify persistence behavior
- modify schema or migrations
- modify Run
- modify Excel export
- modify formulas
- wire tax or depreciation engines
- wire IDC or time-phasing

## 2. Reviewed inputs

The design is grounded in:

- `docs/phase57a10_capex_advanced_columns_foundation_design.md`
- `docs/phase57a10d_capex_vat_wht_depreciation_basis_design.md`
- `docs/phase57a7_capex_advanced_columns_design.md`
- `app/persistence/capex_sub_lines.py`
- `app/persistence/scenarios_repository.py`
- `app/excel_export.py`
- `app/ui/project_context.py`

## 3. Persistence ownership recommendation

### 3.1 Options considered

**Option A - own all VAT / WHT / depreciation metadata directly on
`capex_sub_lines`**

- Pros: simple joins, easy export lookup, clean linkage to `sub_line_id`
- Cons: too many nullable fields too early; weak fit for future
  jurisdiction- or schedule-heavy detail

**Option B - own all metadata in separate detail tables**

- Pros: flexible, normalized, leaves core CAPEX line small
- Cons: heavier joins, more migration complexity, awkward for simple scalar
  metadata that is truly line-owned

**Option C - hybrid ownership**

- Stable scalar metadata lives with the project-owned CAPEX sub-line
- Richer detail lives in dedicated detail tables if and when needed

### 3.2 Preferred persistence architecture

**Recommendation: Option C - hybrid ownership**

Use a hybrid split:

1. **Project-owned scalar metadata belongs to the project-owned CAPEX
   sub-line identity**
2. **Future detail-heavy structures belong in detail tables keyed by the
   same `sub_line_id`**

This is the concrete 57A-10E form of 57A-10D's selected Option D.

## 4. Ownership model by field family

### 4.1 VAT metadata

Preferred ownership:

- line-owned scalar fields on `capex_sub_lines`
- optional future VAT detail table only for jurisdiction-specific or
  evidence-heavy expansion

### 4.2 WHT metadata

Preferred ownership:

- line-owned scalar fields on `capex_sub_lines` for the core treatment
- optional future WHT detail table for jurisdiction, supplier, or
  documentation-heavy detail

### 4.3 Depreciation metadata

Preferred ownership:

- line-owned scalar classification fields on `capex_sub_lines`
- optional future depreciation detail table for engine-specific mapping or
  richer evidence

### 4.4 Ownership rule

The canonical ownership rule is:

> If a field is a stable attribute of the project-owned CAPEX line, it
> belongs to that line's baseline persistence.  
> If a field becomes detail-heavy, jurisdiction-heavy, or schedule-heavy,
> it belongs in a detail table keyed by the same `sub_line_id`.

## 5. Future field shortlist

### 5.1 VAT fields

| Field | Status | Notes |
|---|---|---|
| `vat_recoverable_flag` | required | boolean baseline classification |
| `vat_rate_pct` | required | scalar numeric rate |
| `vat_basis_mode` | required | explicit enum, no implied formula |
| `vat_jurisdiction_code` | optional | useful where known |
| `vat_note` | future-only | richer audit evidence, not required initially |

### 5.2 WHT fields

| Field | Status | Notes |
|---|---|---|
| `wht_rate_pct` | required | scalar numeric rate |
| `wht_treatment_mode` | required | explicit withholding / gross-up semantics |
| `wht_gross_up_flag` | required | avoids ambiguous interpretation |
| `wht_jurisdiction_code` | optional | useful where known |
| `wht_supplier_reference` | future-only | evidence / documentation field |

### 5.3 Depreciation fields

| Field | Status | Notes |
|---|---|---|
| `depreciation_asset_class` | required | classification anchor |
| `depreciation_useful_life_years` | required | numeric life |
| `depreciable_flag` | required | explicit yes/no |
| `depreciation_basis_mode` | required | explicit basis enum |
| `depreciation_method_code` | future-only | defer until engine wiring |
| `depreciation_note` | future-only | evidence / explanatory note |

## 6. Scenario semantics

### 6.1 Core rule

Scenario overrides, if approved later, must remain:

> **replace-not-delta**

They must be bound by `sub_line_id`, just like CAPEX amount overrides.

### 6.2 Overrideable versus non-overrideable fields

Recommended future split:

- **overrideable**
  - `vat_recoverable_flag`
  - `vat_rate_pct`
  - `vat_basis_mode`
  - `wht_rate_pct`
  - `wht_treatment_mode`
  - `wht_gross_up_flag`
  - `depreciation_asset_class`
  - `depreciation_useful_life_years`
  - `depreciable_flag`
  - `depreciation_basis_mode`

- **non-overrideable by default**
  - jurisdiction identifiers
  - explanatory notes
  - future supplier reference identifiers

The non-overrideable set is deliberately conservative because those fields
behave more like identity/evidence than scenario behavior.

### 6.3 Duplicated scenario behavior

When a scenario is duplicated:

- the copied scenario must keep the same project-level `sub_line_id`
  references
- copied override payload must preserve the same metadata override values
- copied override payload must not create new CAPEX rows

### 6.4 Deleted and re-added line behavior

If a line is deleted and later re-added:

- a newly added line gets a new project-owned `sub_line_id`
- prior scenario overrides must not silently bind to the new line
- stale override IDs should remain explicit audit artifacts, not silently
  rebound

This preserves the Phase 20B and 57A-9H integrity lessons.

## 7. UUID ownership and binding

`sub_line_id` remains the canonical binding key for:

- baseline persistence ownership
- scenario override binding
- audit sheet binding
- future export binding

The line identity remains project-owned. Scenario state remains override
state only.

No tax or depreciation metadata architecture in 57A-10E is allowed to
invent a second competing line identity.

## 8. Validation rules

### 8.1 Allowed ranges

- `vat_rate_pct`: `0` to `100`
- `wht_rate_pct`: `0` to `100`
- `depreciation_useful_life_years`: positive integer greater than `0`

### 8.2 Required combinations

VAT:

- if `vat_recoverable_flag` is present, `vat_rate_pct` and
  `vat_basis_mode` must also be present

WHT:

- if `wht_rate_pct` is present, `wht_treatment_mode` and
  `wht_gross_up_flag` must also be present

Depreciation:

- if `depreciable_flag` is true, `depreciation_asset_class`,
  `depreciation_useful_life_years`, and `depreciation_basis_mode` must be
  present

### 8.3 Invalid combinations

- `depreciable_flag = false` with a non-empty useful life
- `wht_gross_up_flag = true` with a treatment mode that explicitly means
  no gross-up
- VAT or WHT rate present without a basis mode
- unknown basis mode values

## 9. Export authority

Future export ownership should be:

- `CapEx`
  - high-level summarized evidence only
- `CapEx_Items`
  - per-line scalar evidence where useful
- `CapEx_SubLines_Audit`
  - canonical per-line evidence surface for user-added CAPEX rows
- `Tax audit sheets`
  - dedicated evidence surface for VAT and WHT treatment
- `Depreciation audit sheets`
  - dedicated evidence surface for depreciation classification and basis

The authority rule is:

> `CapEx_SubLines_Audit` is the first canonical evidence surface for
> per-line CAPEX metadata. Dedicated tax and depreciation sheets are the
> future deep-audit surfaces.

## 10. Generic Solar / Wind compatibility

The architecture must support:

- TUHO
- Oborovo
- Generic Solar
- Generic Wind

without template-specific assumptions.

That means:

- no hardcoded project-type switch in metadata ownership
- no parity promotion for Generic Solar / Wind
- the same `sub_line_id` ownership and audit model applies across all
  project families

Generic Solar / Wind remain exploratory/unvalidated unless separately
validated. The persistence architecture supports them structurally, not as
parity evidence.

## 11. Migration plan

The recommended path is incremental:

### 57A-10F

- persist the approved scalar baseline fields only
- add validation at persistence boundary
- no engine wiring yet

### 57A-10G

- add export and audit evidence surfaces
- add explicit scenario override allowlist for approved metadata fields
- preserve replace-not-delta semantics

### 57A-10H

- only then consider tax/depreciation runtime wiring
- keep IDC and time-phasing separate unless explicitly approved later

No big-bang implementation is recommended.

## 12. Rejected alternatives

### Rejected alternative 1 - all metadata in `capex_sub_lines`

Rejected because it overcommits the schema too early and mixes stable
scalar metadata with richer future detail.

### Rejected alternative 2 - all metadata in detail tables

Rejected because it makes simple line-owned scalar facts heavier than they
need to be and weakens the straightforward audit story.

### Rejected alternative 3 - JSON-only metadata on the CAPEX line

Rejected because it weakens field-level validation, export clarity, and
future migration discipline.

## 13. Recommendation

**Preferred persistence architecture**

- hybrid ownership
- stable scalar metadata baseline on the project-owned CAPEX line
- richer detail in dedicated detail tables only when required

**Migration complexity**

- medium
- manageable because it preserves current UUID ownership and scenario
  semantics

**Export impact**

- good
- lines up naturally with `CapEx_SubLines_Audit` and future dedicated audit
  sheets

**Parity impact**

- low if future implementation keeps TUHO / Oborovo outputs unchanged by
  default

**Rollback strategy**

- keep scalar fields additive and isolated
- keep detail tables optional and phase-gated
- avoid coupling runtime authority to persistence rollout in the same phase

## 14. What 57A-10E does NOT do

- no runtime file changes
- no schema or migration files changed
- no export logic changes
- no Run changes
- no formula changes
- no tax engine wiring
- no depreciation engine wiring
- no IDC wiring
- no UI or static changes

## 15. Hard no-go preserved

- no `app/waterfall_core.py` changes
- no `app/services/run_service.py` changes
- no `app/services/capex_sub_lines_integration.py` changes
- no `app/excel_export.py` changes
- no `app/persistence/*` changes
- no `app/project_factories.py` changes
- no schema / migration changes
- no `app/templates/*` changes
- no `static/app.js` changes
- no `static/styles.css` changes
- rc1 remains frozen at `b425a0708719eaa5e1d922b1008e5609758e0ad4`

## 16. Recommendation

**PASS**

Rationale:

- ownership model is now explicit
- field shortlist is concrete
- scenario semantics remain aligned with the CAPEX persistence stack
- export authority is clear
- future implementation can proceed incrementally instead of as a risky
  big-bang change
