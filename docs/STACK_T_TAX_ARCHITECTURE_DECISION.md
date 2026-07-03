# Stack T — Tax Engine Accuracy: Architecture Decision

**Branch:** `stack-t0-tax-architecture-decision`
**Base:** `main` at Pilot Trust Baseline `2734cac`
**Date:** 2026-07-03
**Status:** Design only — no production code, no engine changes, no parity changes

---

## Executive Summary

Stack T addresses two confirmed DD findings in the tax engine:

1. **SHL deduction missing from CIT** — SHL interest is initialized to zero before
   `compute_period_tax()` is called; the real value is computed afterwards. SHL
   interest receives no tax deductibility in the current runtime.

2. **H1 CIT accrual never settled in cash** — Tax is accrued in H1 but only H2
   tax is collected. H1 tax evaporates; total CIT undercollected by ~50% per year.

Both findings are confirmed by forensic code review and validated by Claude Code.
Neither is a simple reorder: a circular dependency prevents naive resequencing.

**Recommended approach:** Option B — Two-Pass Within Period. This is the minimum
accurate fix achievable without touching the sculpting engine, the SHL mechanic,
or the distribution waterfall sequence. It eliminates the SHL deduction error
exactly. The H1 CIT settlement is addressed separately and is independently safe.

---

## Task 1 — Current Runtime Order

### Period Loop Sequence (`waterfall_engine.py`)

```
For each operating period:

  ┌─ A: EBITDA / revenue / generation / depreciation          (L679–682)
  │
  ├─ B: Senior debt service (si, sp, senior_ds)               (L686–705)
  │     ↳ From pre-sculpted frozen schedule
  │
  ├─ C: SHL placeholder set: shi = 0                          (L731)
  │     ← ORDERING DEFECT: SHL unknown at this point
  │
  ├─ D: total_interest = si + shi   (shi=0, so = si only)     (L739)
  │
  ├─ E: compute_period_tax(                                    (L757–770)
  │       shl_interest_keur = shi   ← 0.0 (placeholder)
  │     )  → tax, taxable_profit, loss_carryforward_update
  │
  ├─ F: CIT cash timing gate                                   (L778–779)
  │       H1: tax_this_period = 0.0   ← H1 accrual LOST
  │       H2: tax_this_period = tax   ← only H2 tax paid
  │
  ├─ G: cf_after_tax = ebitda − tax_this_period               (L785)
  │
  ├─ H: _cf_for_shl determined (pik_then_sweep method:        (L792–799)
  │       cf_after_tax − senior_ds − dsra_contrib)
  │
  ├─ I: SHL PIK trigger evaluated                             (L805–806)
  │
  ├─ J: *** REAL SHL COMPUTED HERE ***                        (L876–884)
  │       (shi, shp, shl_pik, shl_balance) = compute_shl_period(...)
  │       ← Too late: tax already finalized above
  │
  ├─ K: shl_svc = shi + shp                                   (L885)
  │
  ├─ L: cf_after_ds = cf_after_tax − senior_ds − shi          (L888)
  │
  ├─ M: DSRA update                                           (L893–906)
  │
  ├─ N: cf_after_reserves                                     (L906)
  │
  ├─ O: DSCR = (ebitda − tax_this_period) / senior_ds        (L910–911)
  │
  ├─ P: Lockup check                                          (L915–917)
  │
  ├─ Q: Distribution / sweep waterfall                        (L929–1042)
  │
  ├─ R: cash_balance updated                                  (L1059)
  │
  └─ S: WaterfallPeriod assembled (shi stored correctly       (L1095–1155)
          for export; taxable_profit_keur back-computed
          for display only — does not affect tax)
```

### The Circular Dependency

```
cf_after_tax
    ↓  (feeds _cf_for_shl, which determines PIK trigger)
SHL service (shi)
    ↓  (should deduct from taxable income)
CIT tax
    ↓  (determines cf_after_tax)
cf_after_tax        ← loop closed
```

This prevents any single-pass reorder from producing a correct result. At the
point tax must be known, SHL service is not yet determined. At the point SHL
service is computed, tax is already finalized and cannot be revised.

### H1 CIT Settlement Defect

```
H1 period:
  tax accrued = T₁                (compute_period_tax fires)
  tax_this_period = 0.0           (L779 gate: period_in_year == 1)
  cf_after_tax = ebitda           (no cash deduction)
  T₁ is NEVER collected in any future period.

H2 period:
  tax accrued = T₂
  tax_this_period = T₂            (L779 gate: period_in_year == 2)
  cf_after_tax = ebitda − T₂     (only H2 tax deducted)

Annual CIT undercollection = T₁ per year
```

The Excel-style diagnostic at L780–783 computes `−(T₁ + T₂)` as an audit field
only; this does not affect cash flows or any downstream KPI.

---

## Task 2 — Implementation Strategy Comparison

### Option A — Current Bridge Approach (Previous SHL Balance × Rate)

**Concept:** Approximate SHL interest for tax deduction using the prior-period
SHL balance: `shi_approx = shl_balance_prev × rate`.

| Dimension | Assessment |
|-----------|-----------|
| Accuracy | Medium. Correct for PIK periods (balance grows, rate applied). Diverges at sweep onset when balance drops rapidly — the approximation lags by one period. |
| Complexity | Low. One-line change; no structural reorder. |
| Runtime cost | Negligible. Single multiply per period. |
| Regression risk | Low-medium. Results change from current (introduces SHL deduction for the first time), but the change is bounded and deterministic. |
| Parity impact | KPIs move because SHL deduction reduces CIT, increasing CFADS, changing distributions. Delta is bounded by the SHL balance × rate path. |
| Maintainability | Low. Introduces a persistent approximation that diverges from the true value in non-PIK periods. Requires a comment explaining the lag. Future engineers will not understand why the deduction is off by one period. |

**Verdict:** Rejected. Introduces a permanent inaccuracy as a design choice rather
than as a known approximation to be removed. This is the current state — it was
never implemented, so Option A is not an improvement over the status quo.

---

### Option B — Two-Pass Within Period ✅ RECOMMENDED

**Concept:** For each period, run the period computation twice:
- **Pass 1:** Compute a provisional `shi_approx` using `shl_balance × rate`
  (same as Option A). Use this to compute a provisional `tax_1`.
- **Pass 2:** Use `tax_1` to recompute `cf_after_tax`, recompute SHL service
  (getting the real `shi`), then recompute `compute_period_tax(shl_interest_keur=shi)`.
  The final `tax` uses the correct SHL deduction.

The H1 CIT settlement defect is addressed independently as a sub-change within
the same stack (see Task 4).

| Dimension | Assessment |
|-----------|-----------|
| Accuracy | High. Pass 2 solves the circular dependency exactly for all SHL repayment methods (PIK, sweep, bullet). No residual approximation. |
| Complexity | Medium. Requires isolating the tax + SHL computation block into a callable sub-routine or duplicating ~30 lines per pass. Engine structure is not changed. |
| Runtime cost | ~2× per-period computation for tax+SHL block only (not the full waterfall). Negligible in practice (~10ms on full run). |
| Regression risk | Medium. CIT changes for all periods with SHL outstanding (years 1–7 typically). Parity values move. Regression suite must be updated. |
| Parity impact | Equity IRR, project IRR, DSCR, distributions all expected to change. See Task 5 for quantification. |
| Maintainability | High. The fix is self-documenting (two named passes), no persistent approximation, no TODO left behind. Future engineers can understand immediately why two passes are used. |

**This is the chosen approach.**

---

### Option C — Fixed-Point Iteration

**Concept:** Run the period loop multiple times until `|shi_n − shi_{n−1}| < ε`
converges. Typically 3–5 iterations.

| Dimension | Assessment |
|-----------|-----------|
| Accuracy | Highest. Mathematically exact to floating-point precision. Handles any non-linearity in SHL mechanics. |
| Complexity | High. Requires convergence criterion, iteration counter, guard against divergence, tolerance tuning. |
| Runtime cost | ~5× per-period computation. On a 28-period run this is ~280 iterations of the period loop instead of ~56. Measurable but not prohibitive. |
| Regression risk | High. Convergence epsilon choice affects all KPIs. Different platforms may converge differently. Not reproducible across environments without pinned epsilon. |
| Parity impact | Potentially higher precision than Option B; parity must be re-baselined from scratch. |
| Maintainability | Low. Convergence logic is opaque. Engineers must understand the circular dependency to modify any of the converging variables. Test failures are harder to diagnose. |

**Verdict:** Rejected. Two-pass (Option B) achieves the same accuracy for this
specific circular dependency (SHL-tax) without convergence overhead. The SHL-tax
loop is simple enough that a second pass is exact; fixed-point iteration adds
complexity without benefit here.

---

### Option D — Full Period Reorder / Alternative Architecture

**Concept:** Restructure the period loop so that SHL service is computed before
tax. This would require either:
- Computing SHL service from EBITDA alone (before senior DS, DSRA), or
- Moving the entire senior DS + DSRA block before SHL computation.

| Dimension | Assessment |
|-----------|-----------|
| Accuracy | Potentially exact — but only if the reorder is valid for all repayment methods. |
| Complexity | Very high. The period loop has ~500 lines with intricate interdependencies between senior DS, DSRA, SHL PIK/sweep, distribution lockups, and cash waterfall. Reordering any block risks breaking the cascade. |
| Runtime cost | Negligible (single pass). |
| Regression risk | Very high. Any reorder of the core period loop touches every KPI simultaneously. Difficult to bisect failures. |
| Parity impact | Unknown until implemented; high risk of unintended cascades. |
| Maintainability | High if done correctly; catastrophic if incorrect. Requires full re-validation of all 183+ parity tests. |

**Verdict:** Rejected for Stack T. The period loop structure is load-bearing for
all existing parity tests and client deliverables. Option D is the correct
long-term architecture but is out of scope for a targeted tax accuracy fix. It
belongs in a future Stack V (Engine Refactor) after all parity is re-baselined.

---

## Task 3 — Recommendation

**Implement Option B — Two-Pass Within Period.**

### Rationale

The SHL-tax circular dependency is a two-variable loop:
`tax → cf_after_tax → shi → tax`. A single additional pass is sufficient to
break it because the SHL mechanic is not itself tax-dependent (SHL interest
accrues on the balance regardless of tax outcome; the only tax-SHL coupling is
the deduction, not the SHL computation itself).

Option B:
- Is the minimum change that achieves correctness
- Requires no structural reorder of the period loop (guardrail: waterfall_core.py and waterfall_engine.py structure preserved)
- Is auditable: Pass 1 and Pass 2 can be named, logged, and tested independently
- Does not introduce persistent approximations that require future cleanup
- Does not require convergence tuning or tolerance management

Option C (iteration) would be superior if the SHL service itself depended on
tax (creating a genuine non-linear feedback). It does not: `compute_shl_period`
takes `cf_after_senior_ds` as input, which depends on `cf_after_tax`, which
depends on `tax`. Once `tax` is fixed in Pass 2, `shi` is deterministic. A third
pass would produce an identical result to Pass 2. Two passes are exact.

---

## Task 4 — Implementation Sequence

Stack T is split into three independently reviewable PRs:

### T1 — SHL Deduction Fix (Two-Pass)

**Scope:** `domain/waterfall/waterfall_engine.py` only.
**Change:** Add Pass 1 (provisional tax with `shi_approx = shl_balance × rate`),
then Pass 2 (recompute tax with real `shi` from `compute_shl_period`).
**Guardrails:** No changes to `waterfall_core.py`, `project_factories.py`,
`input_adapter.py`, or any export path.
**Parity:** Equity IRR, project IRR, DSCR expected to move. New parity baseline
established. All 183+ prior tests updated to new values.
**Tests created:** `tests/test_excel_parity_stack_t1.py`
**Risk:** Medium. Engine change, all KPIs move.

### T2 — H1 CIT Cash Settlement Fix

**Scope:** `domain/waterfall/waterfall_engine.py` — the CIT cash timing gate
at L778–779.
**Change:** Carry forward H1 CIT accrual to H2 settlement:
```
H1: tax_this_period = 0.0               (unchanged — no cash yet)
H2: tax_this_period = h1_tax + h2_tax   (H1 accrual now collected)
```
Requires storing `h1_tax_accrual_keur` across the period boundary (simple scalar,
reset at year start).
**Guardrails:** Same as T1.
**Parity:** H2 CFADS reduced, equity IRR and DSCR expected to move further. T2
baseline established on top of T1.
**Tests created:** `tests/test_excel_parity_stack_t2.py`
**Risk:** Low-medium. Mechanical cash timing fix; logic is simple, regression
is one scalar per year.

### T3 — Re-baseline and Acceptance

**Scope:** No engine changes.
**Change:** Update `docs/`, update golden parity tables, update
`test_phase51f_parallel_work_guardrails.py` with new SHA locks if any
parity-core files were touched, update acceptance criteria documentation.
**Tests:** All existing tests must pass against the T2 output. Final acceptance
test `tests/test_excel_parity_stack_t.py` covers both fixes end-to-end.
**Risk:** Low. Documentation and test update only.

### PR Dependency Chain

```
main (Pilot Trust Baseline 2734cac)
  └─ T1 (SHL deduction two-pass)
       └─ T2 (H1 CIT cash settlement)
            └─ T3 (re-baseline + acceptance)
                 └─ merge to main
```

Each PR is independently reviewable. T2 can be reviewed without understanding T1
in detail (it is a cash timing gate change, not a tax computation change). T3
requires both T1 and T2 to be green.

---

## Task 5 — Golden Parity Strategy

### Values Expected to Move (T1)

| Metric | Direction | Rationale |
|--------|-----------|-----------|
| TUHO equity IRR | ↑ | SHL deduction reduces CIT → more CFADS → more distributions → higher equity IRR |
| TUHO project IRR | ↑ (smaller) | Project IRR is pre-equity; SHL deduction affects CIT but not EBITDA directly |
| TUHO avg DSCR | ↑ | CFADS increases post-tax; DSCR numerator grows |
| TUHO distributions | ↑ | Lower CIT → more cash available |
| TUHO total_senior_ds | ✅ Unchanged | Frozen Phase 23A overlay; T1 does not touch sculpting |
| Oborovo equity IRR | ↑ | Same mechanism |
| Oborovo avg DSCR | ↑ | Same mechanism |

### Values Expected to Move Further (T2)

| Metric | Direction | Rationale |
|--------|-----------|-----------|
| All IRRs | ↓ | H1 CIT now collected; more cash out in H2, reducing distributions |
| Avg DSCR | ↓ | H2 CFADS reduced by H1 carryforward CIT |
| Distributions | ↓ | H2 cash available lower |

### Values That Must Never Move

| Metric | Reason |
|--------|--------|
| `total_senior_ds_keur` | Frozen Phase 23A overlay; engine not touching DS schedule |
| `senior_debt_keur` (sculpting output) | Sculpting uses EBITDA × (1−rate) proxy; T1/T2 change actual CIT, not the proxy |
| SHA of `waterfall_core.py` | Guardrail; T1/T2 touch only `waterfall_engine.py` |
| SHA of `project_factories.py` | Not touched in any T sub-PR |

### Tests Requiring Update (after T1 and T2)

| Test file | What changes |
|-----------|-------------|
| `tests/test_excel_parity_stack_k.py` through `stack_u.py` | Golden KPI assertions (IRR, DSCR, distributions) |
| `tests/test_phase51f_parallel_work_guardrails.py` | Engine-output golden values (first_finite_dscr, distributions) |
| Any test asserting `equity_irr ≈ 0.1159` (TUHO) | New value TBD after T1 run |
| Any test asserting `equity_irr ≈ 0.1066` (Oborovo) | New value TBD after T1 run |

### Tests That Must Not Change

| Test file | Reason |
|-----------|--------|
| `test_phase51f_parallel_work_guardrails.py` SHA locks (waterfall_core, project_factories, CSVs) | These files are not touched |
| Export column name tests (`test_excel_parity_stack_s.py`) | Column renames are not reverted |
| Template safety tests (`test_stack_u_pilot_trust_polish.py` U2/U3) | Template and report hygiene are not touched |

---

## Task 6 — Regression Strategy

### Smoke Tests (after each T sub-PR)
- `run_demo_project("TUHO")` and `run_demo_project("Oborovo")` complete without exception.
- `equity_irr` and `project_irr` are finite, positive, and in `(0.05, 0.25)`.
- `avg_dscr` is finite and in `(1.0, 2.0)`.
- No `NaN` or `inf` in any period's `tax_keur`.

### Golden Validation
- After T1: run both projects, record new golden values, update
  `test_excel_parity_stack_t1.py` with those values.
- After T2: run both projects again, record new golden values, update
  `test_excel_parity_stack_t2.py`.
- Before T3 merge: all 183+ prior parity tests must pass with updated
  golden values. Zero tolerance for regressions outside the tax/distribution path.

### Export Validation (T3 sign-off)
- `export_waterfall_csv` output: `senior_ds_keur`, `senior_interest_keur_engine`,
  `senior_principal_keur_engine` unchanged (Stack S rename preserved).
- `build_excel_export` dashboard: equity IRR and project IRR cells numeric, in
  `(0.05, 0.25)` (Stack U fix preserved).
- `total_senior_ds_keur` in summary CSV: unchanged from pre-T baseline.

### Tax Validation (T1 specific)
- `WaterfallPeriod.tax_keur` is now lower (SHL deduction reduces CIT) for all
  periods with SHL outstanding.
- `WaterfallPeriod.taxable_profit_keur` (display field) equals
  `ebitda − dep − si − shi` and matches the tax basis used in computation (no
  longer a back-computed display artifact).
- `sum(period.tax_keur for period in result.periods)` < pre-T1 value.

### Distribution Validation (T1/T2)
- `total_distribution_keur` increases after T1 (lower CIT → more distributable cash).
- `total_distribution_keur` decreases after T2 (H1 CIT now collected).
- Net direction of `total_distribution_keur` relative to pre-T baseline is TBD
  after T1 and T2 runs.

### Sponsor Validation (T2/T3)
- Sponsor waterfall is downstream of distributions; changes cascade through but
  do not change the sponsor waterfall logic itself.
- Sponsor IRR expected to move in the same direction as equity IRR.

---

## Task 7 — Rollback Strategy

### Trigger for Rollback

Roll back if, after T1 or T2:
- `equity_irr` or `project_irr` is outside `(0.05, 0.25)` for TUHO or Oborovo.
- `avg_dscr` is outside `(1.0, 2.0)`.
- Any period has `tax_keur < 0` without a confirmed loss-carryforward justification.
- `total_senior_ds_keur` moves from its pre-T value (indicates sculpting touched).
- Any non-tax, non-distribution KPI (senior debt, senior DS, DSCR minimum) moves
  unexpectedly.

### Rollback Procedure

1. **T1/T2 not yet merged:** `git checkout origin/main -- domain/waterfall/waterfall_engine.py`.
   No merge, no squash, no rebase required.

2. **T1 merged, T2 not yet merged:** Revert T1 squash commit on main:
   `git revert <T1-sha>` (safe; T1 is one squash commit).
   All K–U parity tests must still pass after revert.

3. **T2 merged, T3 not yet merged:** Revert T2 squash commit, then T1 squash commit
   if needed. Parity tests must be reverted to pre-T golden values simultaneously.

4. **T3 merged (re-baseline done):** Rollback is a full revert of T1+T2+T3 squash
   commits (three `git revert` commands). This restores pre-T engine behavior and
   restores all pre-T golden parity assertions.

### Pre-Rollback Checklist

Before any merge of T1, T2, or T3:
- [ ] Pre-T golden values recorded and archived in `docs/STACK_T_PRE_BASELINE.md`
- [ ] Pre-T `waterfall_engine.py` SHA recorded
- [ ] All K–U tests green on pre-T main
- [ ] `git tag pilot-trust-baseline 2734cac` applied to main before T1 branch opens

### Safety Properties

- `waterfall_core.py` is not touched in any T sub-PR → Phase 23A overlay, DS
  sculpting, and DSCR recomputation are untouched → rollback does not require
  touching parity-core files.
- `project_factories.py` is not touched → factory-seeded KPIs are stable reference
  points throughout the T stack.
- Each T sub-PR is a single squash commit → rollback is a single `git revert`.

---

## Appendix A — Known Code Locations

| Finding | File | Lines |
|---------|------|-------|
| SHL placeholder `shi = 0` | `domain/waterfall/waterfall_engine.py` | L731 |
| `compute_period_tax(shl_interest_keur=shi)` called with shi=0 | `domain/waterfall/waterfall_engine.py` | L757–770 |
| CIT cash timing gate (H1/H2) | `domain/waterfall/waterfall_engine.py` | L778–779 |
| `cf_after_tax = ebitda − tax_this_period` | `domain/waterfall/waterfall_engine.py` | L785 |
| Real SHL computed: `compute_shl_period(...)` | `domain/waterfall/waterfall_engine.py` | L876–884 |
| `taxable_profit_keur` back-computation (display only) | `domain/waterfall/waterfall_engine.py` | L1108 |
| Excel-style H2 diagnostic (audit only, no cash effect) | `domain/waterfall/waterfall_engine.py` | L780–783 |
| ATAD `total_interest = si + shi` with shi=0 | `domain/waterfall/waterfall_engine.py` | L739 |
| Sculpting CFADS proxy: `ebitda × (1 − tax_rate)` | `domain/waterfall/waterfall_engine.py` | L387–392 |
| Ordering defect TODO (senior sweep cash cap) | `domain/waterfall/waterfall_engine.py` | L837–854 |

---

## Appendix B — Pre-T Pilot Trust Baseline

| Metric | Pre-T value | Source |
|--------|------------|--------|
| TUHO equity IRR | 11.59% | Stack P–U confirmed |
| TUHO project IRR | 9.41% | Stack P–U confirmed |
| TUHO avg DSCR | 1.3786 | Stack P–U confirmed |
| TUHO senior debt | 43,359 kEUR | Stack P–U confirmed |
| TUHO total_senior_ds | 65,826 kEUR | Stack S confirmed |
| Oborovo equity IRR | 10.66% | Stack P–U confirmed |
| Oborovo project IRR | 8.09% | Stack P–U confirmed |
| Oborovo avg DSCR | 1.179 | Stack P–U confirmed |
| Oborovo senior debt | 42,852 kEUR | Stack P–U confirmed |
| Oborovo total_senior_ds | 63,522 kEUR | Stack S confirmed |
| Base commit | `2734cac` | Stack U squash merge |

---

## Confirmation

- ✅ This document contains no production code changes
- ✅ No engine files modified
- ✅ No parity values changed
- ✅ No tests created or modified
- ✅ Stack T implementation has NOT begun
- ✅ Stack T sub-PR T1 is ready to proceed on approval of this design
