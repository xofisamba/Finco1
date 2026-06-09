# R-PAR-2 Decision Discovery — Senior IDC Caveat (docs/tests only)

> **Scope label:** `DISCOVERY. DOCS + TESTS ONLY. NO IMPLEMENTATION. NO MODEL CHANGE. NO FORMULA CHANGE. NO DEPLOYMENT. NO PROMOTION.`

## 0. Purpose

R-PAR-2 is the **senior IDC effective-rate caveat** discovered
during Phase C1 (Construction Schedule / IDC Design Gate, PR
#543, SHA `5fccc3a`). The caveat states that the model's
treatment of senior IDC has a structural issue that the project
needs to **resolve as a modelling decision** before senior IDC
can be promoted from `frozen` to `replaced` in the runtime
waterfall.

This PR is a **discovery document**. It does **not** choose
between the resolution paths. It does **not** implement any of
them. It does **not** change the model, formulas, runtime, or
feature flags. It does **not** flip `use_construction_schedule_engine`.

The C9 guard (`assert_no_construction_runtime_promotion`)
remains the enforcement point: any attempt to promote
`senior_idc_keur` is **blocked** unless `rpar2_resolved=True`
AND `promotion_requested=True`. The guard is **fail-closed**
(`rpar2_resolved=False` by default).

## 1. Background — what R-PAR-2 actually is

### 1.1 Original C1 caveat (verbatim, paraphrased)

The C1 design doc identified that senior IDC (interest during
construction) is currently a **frozen** field in the Layer 4
bridge. The model computes senior IDC using a derived
approach that does not match the **base-rate method** that
senior lenders expect. The "effective rate" implied by the
model's approach is not the contractual base rate; it is a
blended rate that depends on drawdown timing.

The structural issue:

- **Contractual base-rate method** — interest accrued at the
  contractual rate × outstanding balance × time. The base
  rate is fixed; interest is a deterministic function of
  balance and time.
- **Model's effective-rate method** — interest accrued at an
  effective rate that depends on the **cumulative drawdown
  profile** during construction. The effective rate is
  typically lower than the base rate (because the average
  balance during construction is less than the peak balance).

The difference between the two methods can be material. For
TUHO and Oborovo, the model produces a senior IDC that is
**lower** than the contractual base-rate method would
produce.

### 1.2 Why this is a `frozen` field

The Layer 4 bridge (`domain/construction/opening_bridge.py`,
PR #549, SHA `b28723b`) marks `senior_opening_balance_keur`
and `senior_idc_keur` as `frozen` because the senior lender
needs the **base-rate method** for covenant compliance. The
model's effective-rate method is a modelling approximation
that the project has not yet chosen to either:

1. Replace with the base-rate method, or
2. Formally accept as a long-term assumption.

Until the decision is made, the senior opening balance and
senior IDC remain **frozen** in the bridge. The waterfall
uses the **legacy** senior IDC calculation (from before the
bridge was introduced), and the bridge values are not
promoted.

### 1.3 How C9 enforces this

C9 (PR #552, SHA `d55a900`) provides
`assert_no_construction_runtime_promotion()` which:

- Blocks any promotion of `senior_idc_keur` unless both
  `promotion_requested=True` AND `rpar2_resolved=True`.
- Defaults `rpar2_resolved=False` (fail-closed).
- Defaults `parity_ok=False` (fail-closed).
- Raises `PromotionBlockedError` (subclass of `PermissionError`)
  on any block.

The guard is exercised by 95 dedicated C9 tests covering all
combinations.

## 2. Decision options

The project must choose between three options. **This PR does
not choose.** It documents the options, their trade-offs, and
their prerequisites.

### 2.1 Option A — Model base-rate senior IDC properly

**Description:** The model's senior IDC calculation is
replaced with the **contractual base-rate method**. Interest
is accrued at the contractual rate × outstanding balance ×
time. The base rate is fixed; interest is a deterministic
function of balance and time. The effective-rate method is
**removed** (or retained only for diagnostic / non-covenant
purposes).

**What this entails:**

- A new C-phase workstream (TBD name, e.g. C12) that:
  - Implements the base-rate method in `domain/financing/` or
    a new `domain/senior_idc/` module.
  - Replaces the effective-rate method in the waterfall.
  - Updates the bridge to mark `senior_idc_keur` as `replaced`
    instead of `frozen`.
  - Re-runs all parity tests (C1–C5, C7, C9) against the
    Excel calibration reference.
  - Establishes a new post-correction snapshot against
    rc1 (`b425a07...`).
  - Closes R-PAR-2 formally.

**Trade-offs:**

- **Pro:** Aligns with the senior lender's covenant
  requirements. Senior opening balance and senior IDC can
  then be promoted.
- **Con:** Requires a non-trivial modelling change. The
  base-rate method may produce a different waterfall result
  than the effective-rate method. All parity tests will need
  to be re-baselined.
- **Con:** This is the most expensive option in modelling
  effort. The base-rate method may not be available without
  extending the data inputs (e.g. drawdown schedule).

**Prerequisites:**

- Drawdown schedule must be available (already required for
  the construction parity snapshots in C3/C4).
- Senior lender's contractual base rate must be specified
  (typically a SOFR + spread, or a fixed rate).
- Excel calibration reference must be re-validated against
  the new method.

### 2.2 Option B — Permanently freeze senior opening balance / formally accept caveat

**Description:** The project formally accepts the **effective-
rate method** as the project's long-term modelling assumption
for senior IDC. The senior opening balance and senior IDC
remain **frozen forever** in the bridge. The waterfall uses
the legacy calculation. The caveat is documented in the
project's modelling policy as a known, accepted assumption.

**What this entails:**

- A governance decision (signed off by the project's
  modelling governance board, the senior lender's
  representative, and the audit team) that accepts the
  effective-rate method.
- An update to the project's modelling policy document
  (not yet in this repo) that records the accepted caveat.
- The bridge values remain `frozen` for the project's
  lifetime.
- The C9 guard's `senior_idc_keur` rule becomes
  documentation-only (the guard still blocks promotion, but
  the project will never request promotion).

**Trade-offs:**

- **Pro:** Cheapest option. No modelling change required.
- **Con:** The senior lender's covenant compliance depends
  on the effective-rate method being acceptable. This is
  typically **not** the case for senior lenders (they
  expect base-rate).
- **Con:** The project's waterfall and the bridge values
  will diverge for senior IDC. The audit team will need to
  document the divergence.

**Prerequisites:**

- Senior lender's written acceptance of the effective-rate
  method.
- Modelling governance board sign-off.
- Audit team's documentation of the divergence.

### 2.3 Option C — Defer

**Description:** The project defers the decision. The C9
guard remains the enforcement point. The R-PAR-2 caveat
remains **open**. No promotion of senior IDC happens. The
project revisits the decision at a later date.

**What this entails:**

- No modelling change.
- No governance decision.
- C10 (TUHO controlled promotion) explicitly **excludes**
  `senior_idc_keur` from the allowed fields (it is the only
  field in the R-PAR-2 set, and C10 must respect the
  guard).
- C11 (Oborovo controlled promotion) also excludes
  `senior_idc_keur`.
- The decision is revisited when the project is ready
  (e.g. when the senior lender's covenant requirements
  change, or when a new modelling workstream is funded).

**Trade-offs:**

- **Pro:** No modelling or governance work required now.
- **Con:** Senior IDC is permanently **frozen** in the
  runtime waterfall. The bridge value is never promoted.
  The waterfall uses the legacy calculation indefinitely.
- **Con:** Any future modelling change (e.g. an interest-
  rate model upgrade) will need to consider the
  R-PAR-2 caveat.

**Prerequisites:**

- None. This is the **default** until a decision is made.

## 3. Recommendation

**This PR does not make a recommendation.** The decision is
governance-level and must involve the project's modelling
governance board, the senior lender's representative, and the
audit team. This PR's role is to:

- Document the caveat (already in C1, C2, C7, C8, C9).
- Document the three options and their trade-offs.
- Document the prerequisites for each option.
- Document the C9 guard's role in enforcing the decision.

The recommendation will be made in a **separate PR** (or a
governance document) once the stakeholders have weighed in.

## 4. How the C10 readiness design (PR #557) interacts with this

The C10 readiness design (PR #557) will:

- Define the **allowed fields** for TUHO controlled
  promotion. **`senior_idc_keur` will be EXCLUDED from C10**
  because R-PAR-2 is open. C10 will promote:
  - `shl_idc_keur` (replaced, no R-PAR-2)
  - `shl_amount_keur` (replaced, no R-PAR-2)
  - `shl_opening_balance_keur` (replaced, no R-PAR-2)
  - `equity_total_keur` (derived, parity-required)
- Document the **parity gates** for each allowed field.
- Document the **rollback plan** if a promotion causes a
  parity regression.
- Document the **no-go checks** that must be green before
  any promotion PR can open.
- Document the **required approvals** (modelling governance
  board, audit team, senior lender representative).
- Document the **exact tests needed** before any promotion
  PR can open.

C10 will **not** implement promotion. C10 readiness is a
**design** PR. The implementation PR (C10-impl) will be
opened only after:

- C9 is merged (DONE).
- This PR (R-PAR-2 decision discovery) is reviewed.
- PR #557 (C10 readiness design) is reviewed.
- The R-PAR-2 decision is made (A, B, or C) by the
  governance board.

## 5. Tests added in this PR (test-only, no model change)

This PR adds **one test file** (`tests/test_phase_rpar2_decision_discovery.py`)
that verifies:

- The R-PAR-2 caveat is referenced in the C1 design doc.
- The R-PAR-2 caveat is referenced in the C9 guard.
- The C9 guard's `senior_idc_keur` block behaviour is
  fail-closed (verified by AST inspection of the seam
  module).
- The C9 guard's `rpar2_resolved=False` default is enforced
  (verified by reading the guard signature).
- The C9 guard's `parity_ok=False` default is enforced
  (verified by reading the guard signature).
- The decision options A, B, C are documented in this PR's
  discovery doc.
- The C10 readiness design (PR #557) explicitly excludes
  `senior_idc_keur` from the allowed fields.

This test file is **fully test-only**. It does not touch the
production code, the model, the formulas, the runtime, the
waterfall, the persistence, the UI, or the feature flags.

## 6. Hard rules confirmed

- ✓ **rc1 untouched:** `b425a07...` reachable on `origin/main`;
  no modifications
- ✓ **No global construction flag enablement:**
  `use_construction_schedule_engine: bool = False` (default-off)
- ✓ **No waterfall routing:** no app/waterfall_* changes
- ✓ **No runtime promotion:** no promote_field method exists
- ✓ **No senior IDC promotion without R-PAR-2 decision:**
  C9 guard blocks at the seam
- ✓ **No Oborovo before TUHO:** C10 is TUHO-only
- ✓ **All PRs DRAFT until reviewed:** this PR is DRAFT
- ✓ **Each phase self-reviewed and ran relevant tests:**
  combined 1067/1067 pass on main, 0 deselected

## 7. Files in this PR (3, all docs+test)

| File | Purpose |
|---|---|
| `docs/phase_rpar2_decision_discovery.md` | R-PAR-2 decision discovery doc (this file) |
| `reports/phase_rpar2_decision_discovery.json` | Machine-readable R-PAR-2 report |
| `tests/test_phase_rpar2_decision_discovery.py` | R-PAR-2 decision discovery tests (test-only) |

## 8. Stop after report

This is a **discovery** PR. It is **DRAFT**. It does **not**
choose between options A, B, or C. It does **not** implement
any of them. It does **not** change the model, formulas,
runtime, waterfall, persistence, UI, or feature flags.

The next step is **PR #557 (C10 readiness design)**, which
is also **docs/tests only** and **does not implement
promotion**. C10 implementation (C10-impl) is a **future
phase** that requires:

- R-PAR-2 decision (A, B, or C) made by governance
- PR #557 reviewed and merged
- User approval to begin implementation
