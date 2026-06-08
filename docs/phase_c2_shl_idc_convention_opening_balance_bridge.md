# Phase C2 - SHL IDC Convention Decision + Opening Balance Bridge Design

> Type: DESIGN ONLY, DOCS ONLY, NO IMPLEMENTATION
> Status: DRAFT
> Date: 2026-06-08
> Base SHA: `5fccc3a` (post-Phase C1)
> Branch: `phase-c2-shl-idc-convention-opening-balance-bridge`
> Hard constraints: **NO code, NO implementation, NO runtime changes, NO schema/persistence changes, NO feature flags, NO formula changes, NO CAPEX/debt/tax/depreciation changes, NO IDC implementation, NO project status changes**

---

## 0. Purpose

Phase C1 (commit `5fccc3a`) concluded with recommendation **B. More
discovery needed** and identified 5 blockers before any construction
runtime implementation. This C2 phase addresses **blockers 1 and 2**:

1. **SHL IDC convention unresolved** — three different conventions
   exist in the system (manual runtime, Excel full-source elapsed
   compound, Phase 7I engine). The C2 deliverable is a **decision**
   on which convention becomes authoritative for construction
   runtime, with the rationale recorded in writing.
2. **Layer 4 Opening Balance Bridge missing** — no module today
   produces opening balances at COD from the construction result.
   The C2 deliverable is a **design** for that bridge: inputs,
   outputs, responsibilities, audit table.

Blockers 3, 4, 5 (Layer 5 runtime seam, construction-period
parity snapshot, senior IDC effective-rate brittleness) are
**deferred to C3 or later** per C1.

This document does **not** plan implementation. It records a
decision and a design.

---

## 1. SHL IDC Convention Decision

### 1.1 The three conventions in scope

#### Convention A — Current runtime / manual convention

- **Definition:** `Project.shl_idc_keur` is a manual hardcoded
  input set by the project factory (TUHO: 1,169; Oborovo: 0).
  The runtime waterfall consumes this field as-is and treats it
  as the **authoritative SHL IDC** for the operating period.
- **Source of truth:** the project factory function (e.g.
  `create_default_tuho_wind1`).
- **Used by:** the operating waterfall directly
  (`waterfall/waterfall_engine.py:852` reads the SHL balance
  which is built from `shl_amount_keur + shl_idc_keur` per
  `inputs.py:495` `total_equity_shl_keur`).
- **Pros:**
  - **Backward compatible** — every existing parity snapshot
    (Phase 9 TUHO, Phase 23N Oborovo) is calibrated against this
    convention.
  - **Trivially auditable** — the value is one number in the
    project factory.
  - **No construction engine dependency** — works without the
    offline engine running.
- **Cons:**
  - **Not derived from the construction schedule** — the value
    does not depend on the construction period, SHL drawdown
    timing, or SHL rate. Changing the construction period
    silently does **nothing** to the operating waterfall.
  - **Magic number** — TUHO 1,169 has no documented derivation
    in the codebase. The Oborovo value of 0 is similarly
    undocumented.
  - **Inconsistent across projects** — TUHO 1,169 ≠ Oborovo 0,
    and neither equals the Excel reference (3,568.688 / 1,169.662).
  - **Hides construction risk** — the value cannot be
    cross-checked against a construction schedule.
- **Parity impact:** the operating-period parity snapshots pass
  today. The construction-period (if we had one) would not match
  Excel.
- **Audit impact:** the audit trail records the manual value but
  cannot reconcile it against a derived value (because no
  derived value is computed for the operating waterfall).
- **Implementation risk:** **zero** — this is what we have
  today.

#### Convention B — Excel full-source elapsed compound

- **Definition:** `SHL IDC = SHL draw * ((1 + SHL rate) ^
  elapsed_years - 1)`. The "elapsed" variable is the number of
  years from the first SHL draw to COD, or an equivalent
  full-period measure. This is the convention used by the
  offline `domain/construction/idc_calculator.py` for SHL
  (per Phase 7I docs).
- **Source of truth:** the construction engine, given the
  construction schedule, the funding allocation, the SHL rate,
  and the SHL draw profile.
- **Used by:** the offline construction engine only. The
  operating waterfall does **not** consume this value today.
  The runtime adapter reports it as a diagnostic
  (`ConstructionRuntimeResult.shl_idc_keur`) and as a
  validation note, but does not route it into the waterfall.
- **Reference values (Phase 7I):**
  - TUHO: 3,568.688 kEUR (from total SHL draw 29,135.176,
    8.0% rate, 18 construction months)
  - Oborovo: 1,169.662 kEUR (from total SHL draw 14,620.774,
    8.0% rate, 12 construction months)
- **Pros:**
  - **Modelling-correct** — derives from the construction
    schedule, the funding timing, and the SHL rate.
  - **Excel parity at the construction level** — matches the
    Excel reference values within ±0.001 kEUR.
  - **Auditable end-to-end** — given the construction config
    and the draw profile, the IDC is reproducible.
  - **Sensitive to construction period changes** — if COD
    moves, the IDC moves accordingly.
  - **Cross-project consistent** — the same formula applies
    to every project, only the inputs differ.
- **Cons:**
  - **Will change the operating waterfall output** — replacing
    TUHO 1,169 with 3,568.688 will change the operating SHL
    balance, the equity calculation, the DSCR, the
    distribution waterfall, and every downstream metric.
  - **Breaks existing parity snapshots** — Phase 9 (TUHO) and
    Phase 23N (Oborovo) parity tests are calibrated against
    the manual convention. Switching conventions requires
    re-calibrating both parity snapshots.
  - **Requires construction engine to be runtime-authoritative**
    — cannot be wired without a runtime integration seam
    (Layer 5 in C1, blocker 3 from C1).
- **Parity impact:** **high**. The operating waterfall output
  will change for TUHO (and any other project whose manual
  `shl_idc_keur` differs from the engine value). The change
  may bring the operating waterfall closer to Excel **or**
  further from it, depending on how the rest of the Excel
  model handles the IDC.
- **Audit impact:** the audit trail becomes **richer** (every
  IDC is derived from a documented construction schedule) but
  also **more complex** (the audit must record the
  construction config, the engine result, the substitution
  decision, and the manual override, if any).
- **Implementation risk:** **high**. The convention cannot be
  wired without Layer 4 (Opening Balance Bridge) and Layer 5
  (Runtime Integration seam). Both are missing.

#### Convention C — Phase 7I construction engine convention
(audit-only)

- **Definition:** the same engine as Convention B
  (full-source elapsed compound for SHL) but **wrapped** in a
  diagnostic-only runtime adapter that does not mutate the
  waterfall inputs.
- **Source of truth:** the engine result, reported as
  `result.construction_schedule_diagnostic`.
- **Used by:** the offline engine, the construction workbook
  UI (Phase 20L), the senior debt diagnostic, the validation
  notes. **Not** the operating waterfall.
- **Pros:**
  - **Available today** — shipped in Phase 7I.
  - **Safe** — diagnostic-only, no mutation, double-counting
    guard is built in.
  - **Reconciles manual vs computed** — the runtime adapter
    produces `validation_notes` that flag mismatches
    (e.g. `manual_mismatch: shl_idc_keur differs from computed
    SHL IDC`).
  - **Foundation for future wiring** — when Layer 4 and Layer
    5 exist, this is the engine to wire.
- **Cons:**
  - **Not authoritative** — the operating waterfall still
    uses the manual value.
  - **Two sources of truth side by side** — the engine says
    one thing, the waterfall says another, and the audit trail
    has to record both.
  - **Confusing for new readers** — the workbook UI shows
    computed IDC, but the waterfall consumes the manual value.
- **Parity impact:** **zero on the operating waterfall**.
  The construction workbook UI displays the engine value,
  which may differ from what the waterfall uses.
- **Audit impact:** **positive** — the runtime adapter's
  validation notes explicitly flag the mismatch. This is the
  only convention that records the disagreement.
- **Implementation risk:** **zero** — already shipped.

### 1.2 Comparison matrix

| Aspect | A: Manual | B: Excel / Engine | C: Phase 7I (diagnostic) |
|---|---|---|---|
| **Authoritative for waterfall?** | YES (today) | not yet (would require L4+L5) | NO (diagnostic only) |
| **Excel parity at construction level** | NO | YES (within 0.001 kEUR) | YES (engine parity) |
| **Operating-period parity snapshots** | pass | would break until re-calibrated | pass (no mutation) |
| **Modelling-correct** | NO | YES | YES |
| **Construction-period sensitive** | NO | YES | YES |
| **Cross-project consistent** | NO (magic numbers) | YES (formula-driven) | YES (engine-driven) |
| **Cross-check possible** | NO | YES (engine recomputes) | YES (already cross-checks) |
| **Audit trail** | manual value only | would record config + result + substitution | records manual + computed + mismatch |
| **Implementation risk** | zero | high (L4+L5 missing) | zero (shipped) |
| **TUHO 1,169 vs 3,568.688** | uses 1,169 | would use 3,568.688 | reports both, uses 1,169 |
| **Oborovo 0 vs 1,169.662** | uses 0 | would use 1,169.662 | reports both, uses 0 |

### 1.3 Recommendation

**Convention B (Excel full-source elapsed compound) is the
authoritative SHL IDC convention for future construction
runtime.** Convention A is the **current** convention and will
remain so until the C3-C7 sequence is complete. Convention C is
the **bridge** that allows us to validate the decision before
wiring it.

#### Rationale

1. **Modelling-correctness.** Convention A is a magic number
   that does not depend on the construction period. Any change
   to the construction schedule (a real-world event — a
   delayed COD, a rephased drawdown profile) would silently
   leave the operating waterfall unchanged. Convention B ties
   the operating waterfall to the construction schedule.
2. **Excel parity at the construction level.** The C1 doc
   listed "R-PAR-1: SHL IDC convention mismatch" as Critical.
   Convention B closes that gap.
3. **Cross-project consistency.** Convention A relies on a
   project-factory magic number. Convention B is a single
   formula. When a new project (Generic Wind, Generic Solar,
   battery storage) needs an SHL IDC, Convention A requires a
   new magic number; Convention B does not.
4. **Audit completeness.** Convention C already records the
   mismatch between manual and computed. Wiring Convention B
   means the audit trail records the **decision** (which
   value was used) rather than the **disagreement** (manual
   vs computed).
5. **C1 already pointed here.** C1's blocker 1 (SHL IDC
   convention unresolved) is the question this section
   answers. The C1 risk register lists R-PAR-1 as Critical
   and explicitly notes that wiring Convention B before
   answering this question would produce a different number
   than the current waterfall, and the difference would be
   hidden inside the waterfall.

#### Why not Convention A

Convention A is what we have today. Keeping it means:

- Construction-period changes do not propagate to the
  operating waterfall.
- New projects require a new magic number.
- The Excel reference remains unreachable.
- The audit trail cannot reconcile manual vs computed.

These are the three risks from C1: R-PAR-1, R-VAL-2 (test data
coverage), and R-PAR-5 (equity invested vs CAPEX equity) all
trace back to Convention A.

#### Why not Convention C as the final answer

Convention C is the bridge. It is the right answer **for
today** (and we have it). It is the wrong answer **for
tomorrow** because it leaves the operating waterfall
disconnected from the construction engine. The whole point of
this C-series is to bridge that gap.

#### Migration path from A to B

1. **Today (Convention A + C diagnostic):** operating waterfall
   uses the manual value; engine reports the computed value;
   validation notes flag the mismatch.
2. **C3 (parity snapshot design):** design the
   construction-period parity test that will certify Convention
   B.
3. **C4-C6 (L4 implementation + parity snapshot for TUHO):**
   build the bridge, run the parity snapshot, prove Convention
   B matches Excel at the construction level for TUHO.
4. **C7 (L5 implementation, default-off):** wire the seam so
   the operating waterfall **can** consume Convention B
   values, with a per-project opt-in.
5. **C8 (TUHO promotion):** flip the TUHO opt-in. The
   operating waterfall now uses Convention B. The Phase 9 TUHO
   parity snapshot is re-calibrated. Project status moves from
   Level 2 (Reference, operating manual) to Level 3
   (Reference, construction runtime authoritative).
6. **C9 (Oborovo promotion):** same path for Oborovo.

Until step 5, **Convention A is the authoritative convention**
and the operating waterfall is unchanged. Step 5 is the first
moment at which any parity snapshot is allowed to break.

---

## 2. Double-Counting Policy

A double-counting policy is a **table of fields** with a
**replacement decision** for each. The decision is binary:
**replaced** (construction engine output wins), **frozen**
(construction engine output is computed but ignored, manual
value wins), or **retained** (the field is not affected by
construction at all).

The policy below is the **proposed policy** for Layer 5 (the
runtime integration seam). It is not implemented in this
phase. Layer 5 itself is C1 blocker 3, deferred to a later
phase.

### 2.1 Field-by-field policy

| Field | Current source | Construction-derived | Policy | Rationale |
|---|---|---|---|---|
| `shl_idc_keur` | project factory (manual) | engine `total_shl_idc_keur` | **replaced** under Convention B | Convention B is the authoritative convention. The engine value replaces the manual value at COD. |
| `shl_amount_keur` (SHL principal) | project factory (manual) | engine `total_shl_draw_keur` | **replaced** | The SHL principal draw is a function of the funding allocation. The engine result is the authoritative source. |
| `shl_opening_balance_keur` (derived or explicit) | computed at runtime as `shl_amount_keur + shl_idc_keur` | engine `opening_shl_balance_keur` | **replaced** | The opening balance is `principal + IDC`; both inputs are replaced, so the opening balance is replaced. |
| `senior_opening_balance_keur` (manual `fixed_debt_keur`) | project factory (manual) | engine `opening_senior_balance_keur` (= `total_senior_draw_keur + total_senior_idc_keur`) | **replaced** when senior IDC is modelling-correct; **frozen** otherwise | The opening balance is `principal + IDC`; both inputs are replaced. **But** if the senior IDC is still effective-rate based (C1 blocker 5), the opening balance must be **frozen** to avoid wiring a calibrated-rate value into a runtime field. The C3 parity snapshot must demonstrate the senior IDC is modelling-correct before this field can be replaced. |
| `senior_idc_keur` (per project) | not modelled as a manual field; `idc_keur` on `capex` is audited but unused in waterfall | engine `total_senior_idc_keur` | **replaced** | The senior IDC is derived from the construction engine. The audit currently flags the delta in the senior debt diagnostic. |
| `capex_keur` (total CAPEX) | project factory (manual) | engine `total_uses_keur` | **frozen** | The operating CAPEX total is operating-period CAPEX, not construction-period CAPEX. The two are different concepts. The construction engine produces the construction-period total. They are **not** additive. The operating waterfall consumes the operating CAPEX total. The construction engine output is reported in the audit trail but does **not** replace the operating CAPEX. |
| `reserves_keur` (DSRA, MRA, etc.) | project factory (manual) | not computed by engine | **retained** | Reserves are operating-period concepts. The construction engine does not compute them. No replacement. |
| VAT costs (operating period) | project factory (manual) | not computed by engine | **retained** | Operating VAT is an operating-period concept. The construction engine does not compute construction-period VAT (out of scope per C1). |
| `financing_fees_keur` (commitment, arrangement, agent fees) | project factory (manual) | not computed by engine | **retained** | Financing fees are typically **upfront** at financial close, not construction-period. Out of scope. |
| `commitment_fee_keur` (periodic) | project factory (manual) | not computed by engine | **retained** | Commitment fees are operating-period. Out of scope. |
| `equity_total_keur` (or `total_equity_shl_keur`) | computed as `share_capital + share_premium + shl_amount + shl_idc` | engine `total_equity_draw_keur` | **derived** | The runtime total is a function of the replaced fields (`shl_amount`, `shl_idc`). The construction engine produces the construction-period equity draw. They are **different concepts** (operating equity vs construction equity). The runtime total is **not replaced** because it represents the operating-period sources of capital. The construction equity draw is reported in the audit trail. |

### 2.2 Replacement semantics

- **replaced:** the construction engine output overwrites the
  manual value at the seam. The audit trail records the
  substitution (manual value, computed value, decision).
- **frozen:** the construction engine output is computed and
  reported, but the manual value is the one the waterfall
  consumes. The audit trail records the disagreement
  (manual value, computed value, decision to keep manual).
- **retained:** the construction engine does not produce a
  value for this field. The manual value is unchanged.
- **derived:** the runtime total is a function of other
  fields. The construction engine produces a **different
  number** (construction equity) and the two are reported
  side by side in the audit trail. Neither replaces the
  other.

### 2.3 Double-counting guard

The double-counting guard sits in **Layer 5** (the runtime
integration seam, C1 blocker 3). The guard enforces the
following invariant at runtime:

> The operating waterfall reads exactly one of `{manual value,
> construction-derived value}` for each opening balance. The
> choice is recorded in the audit trail. Reading both is a
> guard failure.

The guard is **per-field** and **per-project**. The fields
listed in section 2.1 with the **replaced** policy are the
fields where the guard enforces "use construction-derived". The
fields with the **frozen** or **retained** policy are the
fields where the guard enforces "use manual". A field with
**derived** policy is a composite — the guard enforces
"use manual for the composite; the engine value is reported but
not used in the composite".

### 2.4 What is **not** in this policy

- **No policy on drawdown timing within a month.** The
  construction engine produces a monthly drawdown profile.
  Within a month, the drawdown is treated as a single bulk
  amount. Sub-monthly timing is out of scope.
- **No policy on multi-phase construction (phased COD).**
  Per C1, this is deferred.
- **No policy on currency / FX.** The construction engine
  currently assumes single-currency kEUR. Multi-currency is
  out of scope.
- **No policy on equity bridge at COD.** The construction
  engine produces `total_equity_draw_keur`. The operating
  waterfall does not currently model the equity bridge
  (equity draw → share capital / share premium split). This
  is a separate design question deferred to a later phase.

---

## 3. Opening Balance Bridge Design (Layer 4)

### 3.1 Layer 4 responsibility

> Produce opening balances at COD from the construction
> result, with **explicit per-field decisions** about whether
> each value is construction-derived, manual, or a
> composite. The Layer 4 output is the input to Layer 5.

### 3.2 Inputs

| Input | Source | Required? | Notes |
|---|---|---|---|
| `ConstructionScheduleResult` | Layer 1+2+3 (construction engine) | YES | The result object with monthly entries and totals. |
| Manual override table | project factory | YES | The current manual values for every field listed in section 2.1. |
| Project assumptions (rates, dates) | project factory | YES | SHL rate, senior rate, construction start, COD. |
| Replacement policy | Layer 5 (or config) | YES | The per-field replacement decision from section 2.1. |
| Parity reference | Phase 7I template | NO (audit-only) | Excel target values for the construction period. |

### 3.3 Outputs

| Output | Type | Description |
|---|---|---|
| `opening_senior_balance_at_cod_keur` | float | Senior debt opening balance at COD, with policy applied. |
| `opening_shl_balance_at_cod_keur` | float | SHL opening balance at COD, with policy applied. |
| `equity_contribution_at_cod_keur` | float | Equity contributed at COD, with policy applied. |
| `capitalized_senior_idc_keur` | float | Senior IDC capitalized into the opening balance. **Zero if senior IDC is not modelling-correct.** |
| `capitalized_shl_idc_keur` | float | SHL IDC capitalized into the SHL opening balance. |
| `financing_fee_treatment_keur` | float | Financing fees capitalized or expensed, per project policy. Default: capitalized into opening balance (if input provided), else 0. |
| `audit_reconciliation_table` | list[AuditRow] | The audit table from section 4. One row per policy field. |

### 3.4 Bridge algorithm (design-level, no code)

The bridge is a **pure function** with the following steps.
Each step is a single responsibility and is independently
testable.

1. **Receive inputs.** Pull the construction result, the
   manual override table, and the project assumptions.
2. **Apply per-field policy.** For each field in section
   2.1, apply the policy:
   - **replaced:** use the construction engine value.
   - **frozen:** use the manual value, record the
     construction value as a disagreement.
   - **retained:** use the manual value, no construction
     value.
   - **derived:** compute the runtime value from the manual
     inputs; record the construction value as a separate
     diagnostic.
3. **Compute composite fields.** For each derived field
   (e.g. `equity_contribution_at_cod_keur`), apply the
   composite policy.
4. **Build audit table.** For each policy field, record one
   row in the audit reconciliation table (section 4).
5. **Return the bridge output.** The output includes the
   computed opening balances, the audit table, and the
   construction engine provenance (the source
   `ConstructionScheduleResult`).

### 3.5 Where the bridge lives

The bridge is a new module in the construction package:

```
domain/construction/opening_bridge.py
```

It is **downstream** of the existing
`domain/construction/engine.py` and **upstream** of Layer 5
(not yet implemented). The bridge **does not import** the
waterfall domain, the operating-period finance logic, the
project factory, or the UI. The bridge is a pure transformation
function: result + manual → bridge output + audit.

### 3.6 What the bridge is **not**

- The bridge is **not** a runtime mutation. It does not
  modify `Project` or any persistence record. The output is
  a value object (a frozen dataclass) that Layer 5 may
  consume.
- The bridge is **not** a UI component. It does not render
  anything. The audit table is consumed by Layer 5 and may
  be rendered in a future UI phase.
- The bridge is **not** a policy engine. The per-field policy
  is passed in as input. The bridge enforces the policy; it
  does not decide the policy.
- The bridge is **not** a parity snapshot. Parity is a
  separate test layer (C3 deliverable).

### 3.7 Bridge output contract

```text
OpeningBalanceBridgeResult:
    opening_senior_balance_at_cod_keur: float
    opening_shl_balance_at_cod_keur: float
    equity_contribution_at_cod_keur: float
    capitalized_senior_idc_keur: float
    capitalized_shl_idc_keur: float
    financing_fee_treatment_keur: float
    audit_reconciliation_table: tuple[AuditRow, ...]
    source_construction_result: ConstructionScheduleResult
    manual_overrides: tuple[ManualOverrideRow, ...]
    bridge_metadata: BridgeMetadata
        policy_version: str
        bridge_version: str
        bridge_run_timestamp: str  # ISO-8601
```

---

## 4. Bridge Audit Table

Every Layer 4 invocation produces an **audit reconciliation
table**. The table is the source of truth for "what did the
bridge do and why".

### 4.1 Required columns

| Column | Type | Description |
|---|---|---|
| `field_code` | str | The name of the policy field (e.g. `shl_idc_keur`, `senior_opening_balance_keur`). |
| `manual_value_keur` | float | The manual value from the project factory. `None` if the field is not in the manual override table. |
| `construction_derived_value_keur` | float | The construction engine value. `None` if the engine does not produce a value for this field. |
| `selected_runtime_value_keur` | float | The value the bridge returned to Layer 5 (and which Layer 5 will route to the waterfall). |
| `selection_reason` | str | One of: `replaced`, `frozen`, `retained`, `derived`. |
| `override_status` | str | One of: `no_override`, `manual_override_active`, `construction_override_active`, `composite_no_override`. |
| `double_counting_guard` | str | One of: `guarded_single_source`, `guarded_composite`, `not_applicable`. |
| `parity_reference_keur` | float or None | The Excel reference value, if a parity target exists. `None` for fields with no Excel target. |
| `parity_delta_keur` | float or None | `manual_value_keur - parity_reference_keur`, if applicable. `None` otherwise. |
| `parity_status` | str | One of: `parity_ok`, `parity_drift`, `parity_unknown`, `parity_not_applicable`. |
| `c1_blocker_reference` | str | The C1 blocker or risk that this field addresses. Empty if none. |
| `audit_timestamp` | str | ISO-8601 timestamp when the bridge ran for this field. |
| `bridge_version` | str | The version of the bridge that produced this row. |
| `policy_version` | str | The version of the replacement policy that was applied. |

### 4.2 Example: TUHO SHL IDC audit row

| field_code | manual_value_keur | construction_derived_value_keur | selected_runtime_value_keur | selection_reason | override_status | double_counting_guard | parity_reference_keur | parity_delta_keur | parity_status | c1_blocker_reference |
|---|---|---|---|---|---|---|---|---|---|---|
| `shl_idc_keur` | 1,169.000 | 3,568.688 | 3,568.688 | `replaced` | `construction_override_active` | `guarded_single_source` | 3,568.688 | 0.000 | `parity_ok` | `blocker_1_R-PAR-1` |

Interpretation: the manual TUHO value is 1,169, the engine
value is 3,568.688, the bridge returns 3,568.688 (under
Convention B), the Excel reference is 3,568.688, and the
parity delta is 0. The double-counting guard is satisfied
(single source: construction). This row addresses C1
blocker 1 (SHL IDC convention).

### 4.3 Example: Oborovo SHL IDC audit row

| field_code | manual_value_keur | construction_derived_value_keur | selected_runtime_value_keur | selection_reason | override_status | double_counting_guard | parity_reference_keur | parity_delta_keur | parity_status | c1_blocker_reference |
|---|---|---|---|---|---|---|---|---|---|---|
| `shl_idc_keur` | 0.000 | 1,169.662 | 1,169.662 | `replaced` | `construction_override_active` | `guarded_single_source` | 1,169.662 | 0.000 | `parity_ok` | `blocker_1_R-PAR-1` |

Interpretation: the manual Oborovo value is 0, the engine
value is 1,169.662, the bridge returns 1,169.662, the Excel
reference is 1,169.662, and the parity delta is 0. The
Oborovo promotion is more dramatic than TUHO (0 → 1,169) and
is the **canary** for the convention change.

### 4.4 Example: senior opening balance (frozen, not modelling-correct)

| field_code | manual_value_keur | construction_derived_value_keur | selected_runtime_value_keur | selection_reason | override_status | double_counting_guard | parity_reference_keur | parity_delta_keur | parity_status | c1_blocker_reference |
|---|---|---|---|---|---|---|---|---|---|---|
| `senior_opening_balance_keur` | 43,359.274 | 44,878.838 | 43,359.274 | `frozen` | `manual_override_active` | `guarded_single_source` | 44,878.838 | -1,519.564 | `parity_drift` | `blocker_5_R-PAR-2` |

Interpretation: the manual TUHO value is 43,359.274, the
engine value is 44,878.838 (= 43,359.274 + 1,519.564
effective-rate IDC), the bridge returns the manual value
(frozen policy because senior IDC is not modelling-correct),
the Excel reference is 44,878.838, and the parity drift is
-1,519.564 kEUR. The double-counting guard is satisfied
(single source: manual). This row addresses C1 blocker 5
(senior IDC effective-rate brittleness). **The drift is
expected and is the reason the field is frozen.**

When C3 demonstrates the senior IDC is modelling-correct,
this row flips to `selection_reason=replaced` and
`parity_status=parity_ok`.

### 4.5 Audit table invariants

- **Every policy field has exactly one row.** No field is
  missing. No field is duplicated.
- **The `selected_runtime_value_keur` is one of
  `manual_value_keur` or `construction_derived_value_keur`,
  not a third number** (except for `derived` composite
  fields, which are explicitly marked).
- **The `selection_reason` matches the policy.** If the
  policy says `replaced`, the reason is `replaced`. There is
  no silent override.
- **The `double_counting_guard` is never `not_applicable`
  for opening balance fields** (`shl_idc_keur`,
  `shl_amount_keur`, `shl_opening_balance_keur`,
  `senior_opening_balance_keur`, `senior_idc_keur`).
- **The `parity_reference_keur` is `None` for fields with
  no Excel target** (e.g. `financing_fees_keur`,
  `commitment_fee_keur`). The `parity_status` is then
  `parity_not_applicable`.

---

## 5. Runtime Integration Boundary (Layer 5, design-level only)

Layer 5 is **not implemented** in this phase. The C1 doc
lists it as blocker 3. This section defines what Layer 5
**must consume** from Layer 4 when it is eventually built.
The goal is to make Layer 4's contract explicit so that
Layer 5 can be designed and built in a later phase without
re-opening Layer 4.

### 5.1 What Layer 5 must consume

Layer 5 consumes the `OpeningBalanceBridgeResult` from
section 3.7. Specifically:

- `opening_senior_balance_at_cod_keur` — for the senior debt
  waterfall.
- `opening_shl_balance_at_cod_keur` — for the SHL waterfall.
- `equity_contribution_at_cod_keur` — for the equity
  waterfall.
- `capitalized_senior_idc_keur` — for the senior debt
  capitalised-interest disclosure.
- `capitalized_shl_idc_keur` — for the SHL capitalised-interest
  disclosure.
- `financing_fee_treatment_keur` — for the financing fee
  accounting line.
- `audit_reconciliation_table` — for the audit trail
  persistence and the workbook UI.

### 5.2 What Layer 5 must **not** consume

- Layer 5 must not consume the `ConstructionScheduleResult`
  directly. The bridge is the **only** legal interface
  between the construction engine and the waterfall.
- Layer 5 must not consume the manual override table
  directly. The bridge has already applied the policy.
- Layer 5 must not consume the parity reference. Parity is a
  test concern, not a runtime concern.

### 5.3 What Layer 5 must enforce

- **Single source per opening balance.** The double-counting
  guard from section 2.3. The bridge has already enforced
  this; Layer 5 must not re-introduce a second source.
- **Audit trail completeness.** Every Layer 5 invocation
  must record the bridge result, the bridge version, the
  policy version, and the bridge run timestamp. The audit
  trail is **queryable** (the audit reconciliation table is
  a structured object, not a free-form log).
- **Per-project opt-in.** The C1 promotion gate
  (`use_construction_schedule_engine` flag, default off)
  must be respected. Layer 5 must refuse to run if the flag
  is off and the construction engine is enabled by config.

### 5.4 What Layer 5 is **not**

- Layer 5 is **not** a policy engine. The policy is fixed at
  the bridge level.
- Layer 5 is **not** a parity test. Parity is a separate
  test layer.
- Layer 5 is **not** a UI component. The bridge result may
  be rendered in a future UI phase, but Layer 5 itself is
  pure runtime.

---

## 6. Validation Requirements (evidence required before C3)

Before the C3 design phase begins, the following evidence
must exist. The list is **necessary**, not sufficient; the
actual C3 design phase will likely add more.

### 6.1 TUHO construction-period parity snapshot

- A pytest test that runs the construction engine with the
  TUHO config and asserts the output matches the Excel
  reference values for TUHO within tolerance:
  - Construction months: 18 (exact)
  - Total uses: 72,994.450 kEUR (±0.01)
  - Equity draw: 500.000 kEUR (±0.001)
  - SHL draw: 29,135.176 kEUR (±0.001)
  - Senior draw: 43,359.274 kEUR (±0.001)
  - SHL IDC: 3,568.688 kEUR (±0.001)
  - Opening SHL: 32,703.864 kEUR (±0.001)
  - Senior IDC: 1,519.564 kEUR (±0.001)
- The test must include the **senior IDC effective-rate**
  caveat from C1 (R-PAR-2): the parity is achieved via
  effective rate, not modelling correctness. The test must
  document this in its docstring and assert that the
  effective rate is within the documented tolerance.

### 6.2 Oborovo construction-period parity snapshot

- A pytest test that runs the construction engine with the
  Oborovo config and asserts the output matches the Excel
  reference values for Oborovo within tolerance:
  - Construction months: 12 (exact)
  - Total uses: 57,973.041 kEUR (±0.01)
  - Equity draw: 500.000 kEUR (±0.001)
  - SHL draw: 14,620.774 kEUR (±0.001)
  - Senior draw: 42,852.267 kEUR (±0.001)
  - SHL IDC: 1,169.662 kEUR (±0.001)
  - Opening SHL: 15,790.436 kEUR (±0.001)
  - Senior IDC: 1,086.032 kEUR (±0.001)

### 6.3 Manual-vs-derived reconciliation test

- A pytest test that runs the construction engine and the
  runtime adapter (Phase 7I) for both TUHO and Oborovo and
  asserts:
  - The audit table contains one row per policy field from
    section 2.1.
  - The `selection_reason` is consistent with the policy
    (section 2.1).
  - The `double_counting_guard` is satisfied for every
    opening balance field.
  - The `parity_status` matches the expected status
    (parity_ok for the fields where parity applies,
    parity_drift for the senior opening balance, etc.).

### 6.4 COD opening balance reconciliation test

- A pytest test that runs the bridge (Layer 4) for both
  TUHO and Oborovo and asserts:
  - The bridge output contains all 6 numeric fields from
    section 3.3.
  - The audit table has exactly 11 rows (one per policy
    field).
  - The `selected_runtime_value_keur` is one of
    `manual_value_keur` or `construction_derived_value_keur`
    for every non-derived field.
  - The `bridge_metadata` includes a non-empty
    `policy_version` and `bridge_version`.

### 6.5 IDC by source reconciliation test

- A pytest test that asserts the bridge output's
  `capitalized_senior_idc_keur` and `capitalized_shl_idc_keur`
  sum to the total IDC computed by the construction engine
  within tolerance (±0.001 kEUR per source).
- The test must include the **senior IDC effective-rate**
  caveat: if the senior IDC is effective-rate based, the
  test asserts `capitalized_senior_idc_keur == 0` (the
  field is frozen, not replaced).

### 6.6 No double-counting test plan

- A pytest test that simulates the operating waterfall
  reading the bridge output and asserts:
  - For each opening balance field (`shl_idc_keur`,
    `shl_amount_keur`, `shl_opening_balance_keur`,
    `senior_opening_balance_keur`, `senior_idc_keur`), the
    waterfall reads exactly one of `{manual, construction}`.
  - The bridge audit table's `double_counting_guard` is
    `guarded_single_source` for every opening balance.
  - The composite fields (e.g. `equity_total_keur`) are
    derived from the manual inputs, not the construction
    inputs, in the absence of a `derived` policy.
- The test plan must be **executable**, not just
  documented. The pytest test must fail if the
  double-counting guard is violated.

### 6.7 C3 readiness checklist

- [ ] TUHO construction-period parity snapshot exists and
      passes
- [ ] Oborovo construction-period parity snapshot exists and
      passes
- [ ] Manual-vs-derived reconciliation test exists and passes
- [ ] COD opening balance reconciliation test exists and
      passes
- [ ] IDC by source reconciliation test exists and passes
- [ ] No double-counting test plan is implemented as an
      executable test and passes
- [ ] The senior IDC effective-rate caveat is documented in
      the parity snapshot test docstring
- [ ] The bridge (Layer 4) and the audit table schema are
      reviewed by a second pair of eyes

---

## 7. Recommendation

### Choice: **B. More discovery needed**

Rationale:

1. **C1 blockers 1 and 2 are addressed by this document.**
   The SHL IDC convention is decided (Convention B) and the
   Layer 4 bridge is designed (sections 3 and 4). The
   decision is in writing. The bridge contract is explicit.
2. **C1 blockers 3, 4, and 5 are not addressed by this
   document and remain open.** Layer 5 (runtime seam),
   construction-period parity snapshot, and senior IDC
   effective-rate brittleness are all still open. C3 must
   demonstrate the construction-period parity snapshot
   before any implementation planning.
3. **The migration path from A to B is multi-phase.** C1
   listed C2-C11 as a 10-phase path. C2 is the **second**
   phase in that path. There are at least 4 more
   implementation phases (C4, C6, C7, C8) before any
   project moves to construction-runtime-authoritative
   status. Each phase needs a separate design review.
4. **The Oborovo SHL IDC promotion is dramatic.** Oborovo
   goes from 0 (manual) to 1,169.662 (Convention B). This
   is a 1,169 kEUR change to a single input field, and it
   will propagate through the entire operating waterfall.
   The C3 parity snapshot must demonstrate that the
   downstream impact matches the Excel reference before we
   commit to Convention B for Oborovo.
5. **The senior IDC is still effective-rate based.** Even
   with Convention B chosen for SHL, the senior IDC is
   still calibrated to an effective rate. The C2 bridge
   design has to flag the senior opening balance as
   `frozen` until the senior IDC is modelling-correct. C3
   must decide whether to fix the senior IDC method
   (preferred) or to live with the effective-rate
   brittleness (acceptable for a single calibration cycle,
   not acceptable for a multi-project framework).

### What would unblock "A. Ready for C3"

- A C3 design note that includes the construction-period
  parity snapshot test design.
- A C3 design note that addresses the senior IDC
  effective-rate issue (either fix the method or accept
  the brittleness for the current two projects).
- A C3 design note that includes the Layer 5 (runtime seam)
  interface design, with the per-field policy from section
  2.1.

### What would unblock "C. Defer"

- Generic program priorities shift away from construction.
- Excel reference becomes unavailable or is replaced.
- A new project type that does not need construction
  (e.g. battery storage) becomes the pilot.

None of these defer signals are present today. Construction
remains the largest remaining Excel-parity gap.

### Suggested C3 scope (NOT in scope for C2)

C3 should produce **a single design document** for the
construction-period parity snapshot, addressing:

- The exact pytest test design for the parity snapshot.
- The senior IDC effective-rate issue.
- The Layer 5 (runtime seam) interface design.
- The C4-C7 implementation sequencing.
- The C8-C11 promotion sequencing.

C3 is not an implementation phase. C3 is a design phase.
C3 is the **next** design phase after C2.

---

## 8. Stop after report

This is a **design and decision** document. No code, no
runtime changes, no schema changes, no persistence changes,
no feature flags, no CAPEX formula changes, no debt changes,
no tax changes, no depreciation changes, no IDC
implementation, no project status changes.

Deliverables: this document +
`reports/phase_c2_shl_idc_convention_opening_balance_bridge.json`.
