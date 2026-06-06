# Phase 57A-10 - CAPEX advanced columns foundation design

> Type: docs / report / test-only
> Branch: `phase57a10-capex-advanced-columns-foundation-design`
> Requested base: post-57A-9H main (`9a37b5ec79369e64d8c1acf0838f247f7b3872d5`)
> rc1: `b425a0708719eaa5e1d922b1008e5609758e0ad4` - untouched
> Status: foundation design only. No runtime, schema, UI, Run, or export implementation in this phase.

## 1. Purpose

57A-7 established the first advanced-column design pass. 57A-10 is the
follow-up foundation pass that answers the architectural questions needed
before any later implementation phase touches persistence, scenario
behavior, Run, IDC, tax, or export wiring.

This phase is intentionally design-only. It does **not**:

- change CAPEX persistence behavior
- change scenario override behavior at runtime
- change Run materialization
- change Excel export
- change formulas
- change schema or migrations
- change CAPEX UI or static assets

The output of 57A-10 is a foundation contract for future phases, not a
feature.

## 2. Reviewed inputs

The design was grounded in the current merged CAPEX 2.0 arc:

- `docs/phase57a2_capex_2_design_characterization.md`
- `docs/phase57a7_capex_advanced_columns_design.md`
- `docs/phase57a9a_capex_add_line_persistence_design_gate.md`
- `docs/phase57a9b_capex_sub_lines_schema.md`
- `docs/phase57a9c_capex_sub_lines_save_load.md`
- `docs/phase57a9d_capex_sub_lines_run_integration.md`
- `docs/phase57a9e_capex_sub_lines_excel_export_audit_integration.md`
- `app/persistence/capex_sub_lines.py`
- `app/persistence/scenarios_repository.py`
- `app/ui/project_context.py`
- `app/excel_export.py`

## 3. Foundation questions answered

57A-10 closes the following unanswered design questions:

1. Which advanced-column values are project-owned baseline facts versus
   per-scenario override facts?
2. Which fields may eventually influence model calculations, and which
   must remain descriptive only?
3. How should advanced columns co-exist with the current CAPEX sub-line
   UUID ownership model?
4. How should scenario copy semantics behave for advanced-column fields?
5. How do VAT, WHT, depreciation, payment schedule, and utilisation fit
   future wiring without leaking premature assumptions into Run today?
6. How should future Excel output expose advanced-column evidence without
   breaking TUHO / Oborovo parity?

## 4. Required columns addressed

57A-10 explicitly addresses all required advanced columns:

- `label`
- `amount_keur`
- `cost_per_mw`
- `contingency_pct`
- `vat_applicability`
- `vat_rate_pct`
- `wht_rate_pct`
- `depreciation_category`
- `depreciation_life_years`
- `comments`
- `payment_schedule`
- `utilisation`

The important split is:

- **descriptive / reference columns**: comments, display labels, read-only
  derived metrics such as cost / MW
- **future model inputs**: contingency, VAT, WHT, depreciation, payment
  schedule, utilisation

## 5. Ownership model

### 5.1 Project-level ownership

The advanced-column foundation keeps the existing project-level CAPEX
sub-line UUID ownership model from 57A-9A through 57A-9H:

- one persisted `sub_line_id` belongs to the project
- the same `sub_line_id` is referenced by all scenarios for that project
- scenario duplication must preserve those project-level references
- factory projects never gain mutable user-owned advanced-column rows

Project-owned baseline fields are the default source of truth for any
future advanced-column storage:

- `label`
- `parent_category_code`
- `business_code`
- `amount_keur`
- `comments`
- default advanced-column facts that describe the underlying CAPEX line

### 5.2 Scenario-level ownership

Scenario records own only **override state**, never the identity of the
sub-line itself.

Future scenario override payloads must continue to:

- reference the project-owned `sub_line_id`
- replace the baseline value for that field in the active scenario
- never create a second logical CAPEX line
- never act as delta math unless a future design explicitly says so

This preserves the 57A-9H integrity rule: UUID identity is project-level;
scenario behavior is override-level.

## 6. Scenario override semantics

### 6.1 Core rule

For advanced-column fields that eventually become scenario-sensitive, the
override semantics must be:

> **scenario override replaces the baseline field value for that
> scenario; it is not a delta.**

This matches the merged CAPEX amount behavior for `_capex_sub_line_overrides`
and avoids split semantics between amount and advanced-column fields.

### 6.2 Field-by-field override policy

| Field | Ownership | Future scenario override? | Notes |
|---|---|---|---|
| `amount_keur` | project baseline | yes | already implemented via override map |
| `comments` | project baseline | optional later | descriptive only; low-risk if ever allowed |
| `cost_per_mw` | derived | no | always recomputed from effective amount + capacity |
| `contingency_pct` | project baseline | yes | replace semantics if later enabled |
| `vat_applicability` | project baseline | yes | replace semantics if later enabled |
| `vat_rate_pct` | project baseline | yes | replace semantics if later enabled |
| `wht_rate_pct` | project baseline | yes | replace semantics if later enabled |
| `depreciation_category` | project baseline | yes with caution | affects later accounting/tax logic |
| `depreciation_life_years` | project baseline | yes with caution | replace semantics only |
| `payment_schedule` | project baseline | yes with caution | replace full schedule, not per-cell deltas |
| `utilisation` | project baseline | yes with caution | replace full schedule, not per-cell deltas |

### 6.3 Unknown-key rule

Phase 20B silent-drop behavior remains in force for unknown override keys.
57A-10 does not weaken that rule. Any future advanced-column override keys
must be introduced intentionally and explicitly.

## 7. Calculation authority matrix

57A-10 separates fields by authority so future phases do not wire them
prematurely.

| Field group | Authority today | Future authority | 57A-10 status |
|---|---|---|---|
| Label / comments | UI + persistence | persistence + export | design only |
| Amount | project baseline + scenario override | Run + export | already implemented in earlier phases |
| Cost / MW | derived display | derived display / export | design only |
| Contingency / VAT / WHT | none at runtime | future Run / tax / funding logic | design only |
| Depreciation fields | none at runtime | future tax / book depreciation logic | design only |
| Payment schedule / utilisation | none at runtime | future IDC / drawdown / COD logic | design only |

## 8. Data model strategy options

57A-10 compares five possible storage strategies for future advanced
columns.

### Option A - widen `capex_sub_lines` table directly

- Pros: simplest query model; aligns with project-owned UUID rows
- Cons: large migration surface; many nullable fields; forces early schema
  commitment across payment schedule / tax semantics

### Option B - JSON blob per sub-line

- Pros: flexible; low migration churn
- Cons: weak column-level validation; harder auditability; awkward future
  export/query behavior

### Option C - hybrid core columns + JSON extension

- Pros: stable core fields in table, flexible future extension
- Cons: mixed validation surface; higher complexity than A or B

### Option D - scenario-owned advanced-column table

- Pros: explicit per-scenario storage
- Cons: wrong ownership model for baseline facts; duplicates project-level
  identity; raises copy-integrity risk

### Option E - staged hybrid with project-owned baseline and
reserved scenario override keys

- Pros: matches current UUID ownership model; preserves replace semantics;
  supports incremental wiring; safest continuation of 57A-9A through 57A-9H
- Cons: requires careful design of allowlisted override keys in later phases

### Preferred direction

**Option E** is the preferred foundation.

Reason:

- preserves project-level UUID ownership
- keeps scenario state as override state only
- supports descriptive fields first
- lets high-risk runtime fields wait until dedicated phases
- keeps TUHO / Oborovo parity protection easier to reason about

## 9. Excel compatibility analysis

57A-10 does not change Excel export behavior, but it defines the future
compatibility contract.

Future export behavior must:

- keep TUHO / Oborovo parity stable by default
- keep factory projects free of user-added advanced-column rows
- expose advanced-column evidence only where the project actually owns such
  data
- continue to separate:
  - baseline value
  - effective scenario value
  - descriptive audit notes

Recommended future sheet placement:

1. keep core CAPEX totals / parity sheets unchanged by default
2. add advanced-column evidence only in dedicated audit/detail sheets
3. never imply that generic Solar/Wind advanced-column output is parity
   evidence

## 10. VAT / WHT design assumptions

57A-10 makes these design assumptions only:

- VAT and WHT are future line-level treatment metadata
- they are **not** wired to current Run
- they are **not** wired to current Excel calculations
- they are **not** wired to IDC, cash tax, or funding in this phase

Future implementation must decide jurisdiction-specific treatment in a
dedicated runtime phase. 57A-10 only reserves the semantic space.

## 11. Depreciation design assumptions

57A-10 treats depreciation metadata as a future bridge to the existing tax
and book depreciation architecture, not a shortcut around it.

That means:

- no direct wiring into `waterfall_core.py`
- no direct wiring into tax schedules in this phase
- depreciation fields are **not wired to current Run**
- no assumption that CAPEX sub-line depreciation metadata is automatically
  authoritative for finance outputs

Future depreciation wiring must explicitly reconcile:

- tax depreciation treatment
- book depreciation treatment
- useful life
- non-depreciable categories
- reporting-only versus calculation-driving fields

## 12. Payment schedule and utilisation design

57A-10 expands the earlier 57A-7 design by being explicit about time
horizon and IDC boundaries.

### 12.1 Time horizon

The future structure must support:

- at least M1-M18 for the current Excel-like expectation
- extension to M1-M30 without redesigning ownership semantics

### 12.2 Validation rules

Future payment schedule validation should require:

- fractions are non-negative
- total schedule equals 1.0 unless an explicit normalization rule is
  adopted in a later phase
- utilisation values are non-negative
- utilisation cannot exceed the logical schedule for the same period unless
  a later design explicitly allows it

### 12.3 IDC relation

Payment schedule and utilisation remain **design-only** in 57A-10 and are
**not wired to current Run**.

No IDC runtime wiring is introduced here. The future IDC phase must be
explicitly separate because these fields directly affect drawdown timing,
interest during construction, and COD opening balances.

## 13. Validation rules matrix

Future implementation should validate:

| Field | Rule |
|---|---|
| `comments` | free text, bounded length |
| `contingency_pct` | numeric, 0-100 |
| `vat_rate_pct` | numeric, 0-100 |
| `wht_rate_pct` | numeric, 0-100 |
| `depreciation_life_years` | positive integer or empty if non-depreciable |
| `payment_schedule` | sequence length matches configured construction horizon |
| `payment_schedule` | fractions sum to 1.0 |
| `utilisation` | sequence length matches schedule horizon |
| `utilisation` | each value non-negative |

## 14. One-sheet UI grouping design (future only)

57A-10 does not change the current CAPEX UI, but it defines a future
grouping pattern for a one-sheet advanced column experience:

- identity block: line item, code, amount
- descriptive block: comments, cost / MW
- tax / treatment block: contingency, VAT, WHT, depreciation
- timing block: payment schedule, utilisation

This is a future presentation concept only. No template or static change is
part of 57A-10.

## 15. Phase plan

Recommended phased path after 57A-10:

1. **57A-10A / metadata-safe columns**
   - comments
   - optionally read-only cost / MW display evidence
2. **57A-10B / descriptive baseline persistence**
   - project-owned descriptive advanced-column fields only
3. **57A-10C / scenario override extension**
   - explicit allowlist additions for approved advanced-column overrides
4. **57A-10D / export evidence**
   - dedicated audit sheets for advanced-column evidence
5. **57A-10E / high-risk runtime wiring**
   - contingency / VAT / WHT / depreciation / schedule / utilisation
   - only in isolated reviewable phases

## 16. What 57A-10 does NOT do

- no runtime file changes
- no schema files changed
- no UI / static file changes
- no formula changes
- no Excel export changes
- no Run changes
- no IDC wiring
- no scenario redesign
- no CAPEX redesign

## 17. Hard no-go preserved

- no `app/waterfall_core.py` changes
- no `app/services/run_service.py` changes
- no `app/services/capex_sub_lines_integration.py` changes
- no `app/persistence/capex_sub_lines.py` changes
- no `app/excel_export.py` changes
- no `app/project_factories.py` changes
- no schema / migration changes
- no CAPEX UI changes
- no `static/app.js` changes
- no `static/styles.css` changes
- no formula changes
- rc1 remains frozen at `b425a0708719eaa5e1d922b1008e5609758e0ad4`

## 18. Recommendation

**PASS**

Rationale:

- the ownership model is clear
- scenario override semantics are clear
- high-risk fields remain design-only
- IDC / tax / depreciation / payment schedule wiring is explicitly deferred
- later runtime phases can now proceed without reopening the foundation
  questions
