# R-PAR-2 Decision Pack — Option A / B / C Compared

> Type: REPORT ONLY, DOCS ONLY
> Status: DRAFT
> Date: 2026-06-09
> Base SHA: `233981e4` (post-#559/#560/#561, post-pilot-readiness stack)
> Branch: `rpar2-decision-pack`
> Hard constraints:
> - No code, no implementation, no formula change
> - No runtime promotion
> - No waterfall routing
> - No flag flip
> - No senior IDC promotion
> - No Oborovo before TUHO
> - No persistence/schema changes
> - DRAFT until reviewed
> - rc1 untouched

---

## 0. Purpose

This is a **decision pack** that compares the three resolution
options for the **R-PAR-2 senior IDC effective-rate caveat** (see
PR #556 discovery doc, `docs/phase_rpar2_decision_discovery.md`).

The pack goes one step further than the discovery PR: it produces
a **recommendation** (this document), but **does not** implement
the chosen option. The recommendation is for the human owner
(modelling lead + governance board) to ratify.

If the recommendation is ratified, a follow-up sprint (post-C11)
will implement it. This pack is the **decision record**, not the
implementation.

---

## 1. Recap of the R-PAR-2 caveat

The C1 design gate (`docs/phase_c1_construction_idc_design_gate.md`)
identified that the model computes senior IDC using an
**effective-rate** method (blended rate that depends on cumulative
drawdown profile), not the **contractual base-rate** method that
senior lenders expect for covenant compliance.

For TUHO and Oborovo, the effective-rate method produces a senior
IDC that is **lower** than the base-rate method would produce.
This is a structural modelling gap, not a calibration error.

The C7 implementation marks `senior_idc_keur` and
`senior_opening_balance_keur` as `frozen` in the bridge. The C9
guard (`assert_no_construction_runtime_promotion`) blocks any
promotion of these fields unless `rpar2_resolved=True` AND
`promotion_requested=True` (fail-closed defaults).

**R-PAR-2 must be resolved (or formally deferred) before C10
implementation can begin for TUHO.**

---

## 2. The three options

### 2.1 Option A — Model senior IDC base-rate properly

- **Goal:** Replace the model's effective-rate senior IDC with
  the contractual base-rate method, so the bridge's
  `senior_idc_keur` value can be promoted to the runtime
  waterfall.
- **Mechanics:** Modify the senior IDC accrual to use
  `balance × base_rate × time` for each construction period.
  Re-baseline the senior opening balance at COD accordingly.

### 2.2 Option B — Formally accept / freeze the caveat

- **Goal:** Formally accept the effective-rate method as the
  long-term modelling assumption. Document the deviation from
  the contractual base-rate method as a known modelling choice.
  Reclassify `senior_idc_keur` from `frozen` to `retained`
  (manual override) or keep `frozen` and document the carve-out.
- **Mechanics:** Governance board signs off on the effective-rate
  assumption. Senior lender signs off too (or the carve-out is
  treated as a project-level decision, not a lender decision).
  No model change. `rpar2_resolved=True` is recorded with the
  B-style rationale.

### 2.3 Option C — Defer

- **Goal:** Keep the C9 guard fail-closed. Do not promote
  `senior_idc_keur` or `senior_opening_balance_keur`. Re-evaluate
  R-PAR-2 in a future sprint.
- **Mechanics:** No model change. No governance decision. The
  C9 guard's `rpar2_resolved=False` default remains. C10
  implementation cannot include the 4 allowed fields that
  reference the senior opening balance (none currently do, per
  `phase_c10_readiness_design.md`).

---

## 3. Accounting impact

| Aspect | Option A | Option B | Option C |
|---|---|---|---|
| Senior IDC accrual method | Base-rate (contractual) | Effective-rate (current) | Effective-rate (current) |
| Senior IDC value (TUHO Y1) | Higher (base rate × peak balance × time) | Lower (effective rate × average balance) | Lower (unchanged) |
| Senior opening balance at COD | Re-baselined (higher) | Frozen (current) | Frozen (current) |
| DSCR during operations | Lower (more interest) | Higher (less interest) | Higher (unchanged) |
| SHL PIK / sweep behavior | May shift (more senior IDC ⇒ less CFADS ⇒ more PIK) | Unchanged | Unchanged |
| Tax shield | Higher (more interest) | Lower | Lower |
| Equity IRR | Lower (more senior debt service) | Higher | Higher |
| Project IRR | Unchanged (debt-vs-equity) | Unchanged | Unchanged |

---

## 4. Lender / audit impact

| Aspect | Option A | Option B | Option C |
|---|---|---|---|
| Covenant compliance | Aligned (base-rate is the contractual method) | Deviation requires lender signoff | Deviation noted as known gap |
| External audit | Clean (matches contractual) | Requires disclosure of modelling assumption | Requires disclosure |
| Senior lender relationship | Neutral to positive | Requires formal acceptance | Risk: lender notices gap during due diligence |
| R99 audit chain | Closes cleanly | Closes with documented carve-out | Stays OPEN |
| R102 SHL audit chain | Closes (no SHL change) | Closes | Stays OPEN |
| G20 governance gate | Aligned | Aligned (with memo) | Aligned (with memo) |

---

## 5. Implementation effort

| Aspect | Option A | Option B | Option C |
|---|---|---|---|
| Modelling work | Multi-sprint (re-baseline, recalibrate, regression test) | Sub-sprint (governance memo, lender signoff) | Sub-sprint (governance memo) |
| Code change | Multi-PR (senior IDC accrual, base-rate row, waterfall wiring) | None | None |
| Test change | Multi-PR (base-rate parity, Oborovo/TUHO re-baseline) | None | None |
| Re-calibration | Both projects (TUHO, Oborovo) | None | None |
| Total effort | **L** (multi-quarter) | **S** (sub-sprint) | **S** (sub-sprint) |
| Risk of regression | Medium-High (touches DSCR, SHL, tax) | Low (no model change) | None |
| Risk of new parity gap | Medium-High | Low | None |

---

## 6. Parity impact

| Aspect | Option A | Option B | Option C |
|---|---|---|---|
| Pre-A parity failures | 88 (baseline at #557) | 88 (unchanged) | 88 (unchanged) |
| Expected new failures | -10 (R-PAR-2 family closes) | 0 | 0 |
| Expected remaining failures | ~78 | 88 | 88 |
| R99 chain impact | Closes | Closes (with carve-out) | Stays OPEN |
| R102 chain impact | Closes | Closes (with carve-out) | Stays OPEN |
| Debt sculpting | May improve (senior IDC re-baselined) | Unchanged | Unchanged |
| OPEX | Unchanged | Unchanged | Unchanged |
| Tax | Improves (more interest ⇒ more tax shield) | Unchanged | Unchanged |

---

## 7. Strategic / product impact

| Aspect | Option A | Option B | Option C |
|---|---|---|---|
| Pilot confidence | Higher (closer to Excel base-rate) | Same as today (with memo) | Same as today (with memo) |
| Paid product readiness | Better parity closes paid blockers | Same | Same |
| Enterprise readiness | Required for bank/lender certification | Insufficient for enterprise | Insufficient |
| Competitive positioning | Aligned with market standard | Documented deviation | Documented deviation |
| Future flexibility | Opens door to live sculpting | Locks effective-rate | Locks effective-rate |
| C10 implementation | Unblocked for all 4 allowed fields | Unblocked (rpar2_resolved=True) | Blocked (rpar2_resolved=False) |

---

## 8. Risk score and effort summary

| Option | Risk | Effort | Pilot unlock | Paid unlock | Enterprise unlock |
|---|---|---|---|---|---|
| A | Medium-High | L (multi-quarter) | yes | yes | yes |
| B | Low | S (sub-sprint) | partial (with memo) | partial (with memo) | no (needs A for full) |
| C | None | S (sub-sprint) | no | no | no |

---

## 9. Recommendation

> **Recommended decision: Option B — Formally accept the
> effective-rate caveat as a long-term modelling assumption, with
> a documented carve-out and a deferred Option A re-evaluation
> in a future sprint.**

### 9.1 Why B (not A) for the immediate decision

- A is the **right strategic answer** but the **wrong sprint**
  for the current pilot window. Re-baselining senior IDC is
  multi-quarter work that would block the C10 readiness gate
  for too long.
- B **unblocks C10 implementation immediately** (C10 only
  includes 4 fields: shl_idc_keur, shl_amount_keur,
  shl_opening_balance_keur, equity_total_keur — none of which
  require the senior IDC field to be promoted, per
  `phase_c10_readiness_design.md`).
- B **closes the audit-chain blockers** (R99, R102) with a
  documented carve-out, so the R99/R102 chain can move forward
  in Sprint 24-C without waiting for the A re-baseline.
- B **preserves the option to do A later** without locking the
  project into the effective-rate method permanently.
- B requires only a **governance memo + lender signoff**, both
  of which can be obtained in a sub-sprint.

### 9.2 Why B (not C)

- C is the **default** if no decision is made, but C leaves
  R-PAR-2 perpetually OPEN, which means R99 and R102 cannot
  close, which means paid-tier claim scope is blocked.
- B is a small step beyond C: it makes the carve-out explicit
  and recorded, which unblocks the audit chain.

### 9.3 Why a deferred A matters

- A is the **right strategic answer for enterprise**. The
  effective-rate method is a modelling approximation that
  enterprise customers (banks, funds) will not accept without
  full re-baselining.
- The recommended future roadmap includes a **Sprint 25-D
  "Senior IDC Re-baseline"** as a parallel track to the
  C10 promotion chain. This sprint would do the A work
  in a controlled, single-purpose way.

### 9.4 Conditions for the B recommendation

The B decision is conditional on:

1. **Governance board signoff** on the effective-rate carve-out
2. **Senior lender signoff** (or formal project-level decision
   documented as not requiring lender signoff)
3. **Audit team signoff** on the carve-out as a documented
   modelling assumption
4. **Documented re-evaluation trigger** (e.g. enterprise tier
   reached, or A-sprint scheduled)

If any of these conditions cannot be met, the fallback is
Option C (defer) and the audit chain stays OPEN.

---

## 10. What this document does NOT do

- No implementation of A, B, or C
- No model change
- No formula change
- No runtime change
- No flag flip
- No promotion
- No governance decision (the board picks)
- No test impact (this is a report-only PR)
- No commitment to a specific sprint name/number for A

The machine-readable companion is
`reports/phase_rpar2_decision_pack.json`.

---

## 11. Test footprint

This PR introduces shape-only characterization tests that assert
the document exists, lists all three options (A, B, C), and has
exactly one recommendation that is one of {A, B, C}. They do not
assert content beyond shape.
