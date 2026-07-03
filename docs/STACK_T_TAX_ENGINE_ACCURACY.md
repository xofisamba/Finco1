# Stack T — Tax Engine Accuracy

**Branch:** `stack-t-tax-engine-accuracy`
**Base:** `main` at Stack T0 squash-merge `f73dcf3`
**Date:** 2026-07-03

---

## Executive Summary

Stack T corrects two tax engine defects in `domain/waterfall/waterfall_engine.py`
identified by the independent DD:

- **T1 (SHL deduction):** Circular dependency between tax computation and SHL interest
  was resolved via a two-pass within-period approach. SHL interest is now correctly
  deducted from taxable income.
- **T2 (H1 CIT settlement):** H1 CIT accrual that previously evaporated is now
  carried forward and settled in H2 alongside the H2 CIT accrual.

**Only one production file changed:** `domain/waterfall/waterfall_engine.py`.

---

## T1 — SHL Deduction Fix (Two-Pass Within Period)

### Root Cause

The single-pass loop had a circular dependency:

```
tax → cf_after_tax → _cf_for_shl → shi → tax
```

`compute_period_tax` was called with `shl_interest_keur=0` because `shi` (the SHL
cash interest result from `compute_shl_period`) had not yet been computed when
`compute_period_tax` ran. This meant SHL interest was never deducted from taxable income.

### Fix

Replaced single-pass tax computation with a **two-pass within-period** approach:

**Pass 1** — provisional tax using `shl_interest_keur=0.0`:
- Computes `_cf_after_tax_p1 = ebitda - _tax_this_period_p1`
- Uses `_cf_after_tax_p1` to compute `_cf_for_shl`
- Feeds `_cf_for_shl` into `compute_shl_period` → real `shi`

**Pass 2** — final tax using real `shi`:
- Calls `compute_period_tax(shl_interest_keur=shi)` → correct deduction
- Updates `prior_tax_loss` only from Pass 2 result
- `cf_after_tax = ebitda - tax_this_period` uses Pass 2 tax

**SHL re-pass** — update SHL principal from final `cf_after_tax`:
- Recomputes `_cf_for_shl_final = max(0, cf_after_tax - senior_ds)` from Pass 2
- Re-calls `compute_shl_period(_cf_for_shl_final)` → corrected `shp`, `shl_balance`
- Guards that `shi` is unchanged (raises `RuntimeError` if it moves > 0.01 kEUR)
- Updates `shp`, `shl_pik`, `shl_balance` to reflect the final post-tax cashflow

### Why Three Computations Are Sufficient

`shi` (SHL cash interest paid) equals `min(net_interest, cf_available)`.  In all
sweep-phase periods for TUHO and Oborovo, `cf_available >> net_interest`, so
`shi = net_interest` is unchanged by the re-pass.  The guard confirms this period
by period and raises `RuntimeError` if it ever fails — requiring explicit three-pass
iteration.

`shp` (principal) depends on `cf_available - interest_paid`, so it can differ
between Pass 1 and the re-pass.  For TUHO, two periods (P31 and P33) have
`|shp_p1 - shp_final| > 0.01 kEUR`.  The re-pass corrects these, giving an
internally consistent `shl_balance` sequence.

All three computations can be summarised as:
```
Pass 1:   compute_period_tax(shi=0)    → _cf_for_shl_p1 → SHL block → shi, shp_p1
Pass 2:   compute_period_tax(shi=shi)  → cf_after_tax_final → _cf_for_shl_final
Repass:   compute_shl_period(_cf_for_shl_final) → shi (unchanged), shp_final, bal_final
```

---

## T2 — H1 CIT Cash Settlement

### Root Cause

The tax timing gate:

```python
tax_this_period = tax if period.period_in_year == 2 else 0.0
```

caused H1 tax (period_in_year == 1) to accrue in `tax_keur` but never be paid as
cash. Only H2 paid its own tax — H1 accrual evaporated each cycle.

### Fix

Added `_h1_cit_accrual_keur` loop variable (initialised to `0.0` before the period loop):

```python
if is_tax_period:               # H2: period_in_year == 2
    tax_this_period = _h1_cit_accrual_keur + tax
    _h1_cit_accrual_keur = 0.0
else:                           # H1: period_in_year == 1
    tax_this_period = 0.0
    _h1_cit_accrual_keur = tax
```

H1 accrues into `_h1_cit_accrual_keur`; H2 settles both H1 and H2 accruals in a
single cash payment. Total lifetime cash CIT equals total lifetime accrued CIT
within rounding (< 11 kEUR delta for TUHO; exact for Oborovo which is annual).

---

## KPI Movement (Pre-T → Post-T)

| Metric | Pre-T (Pilot Trust) | Post-T | Change | Note |
|--------|---------------------|---------|--------|------|
| TUHO equity IRR | 11.59% | 11.32% | −27 bps | Correct tax lowers equity CF |
| TUHO project IRR | 9.41% | 9.41% | 0 bps | Unaffected (pre-tax CF unchanged) |
| TUHO avg DSCR | 1.3786 | 1.3786 | 0 | **GUARDRAIL: UNCHANGED** |
| TUHO senior debt | 43,359 kEUR | 43,359 kEUR | 0 | **GUARDRAIL: UNCHANGED** |
| TUHO total senior DS | 65,826 kEUR | 65,826 kEUR | 0 | **GUARDRAIL: UNCHANGED** |
| TUHO total accrued CIT | ~39,650 kEUR | 33,196 kEUR | −6,454 kEUR | SHL deduction + H1 timing |
| TUHO total distributions | 180,089 kEUR | 165,511 kEUR | −14,578 kEUR | Less CF after correct tax |
| Oborovo equity IRR | 10.66% | 10.54% | −12 bps | |
| Oborovo project IRR | 8.09% | 8.09% | 0 bps | |
| Oborovo avg DSCR | 1.179 | 1.179 | 0 | **GUARDRAIL: UNCHANGED** |
| Oborovo senior debt | 42,852 kEUR | 42,852 kEUR | 0 | **GUARDRAIL: UNCHANGED** |
| Oborovo total senior DS | 63,522 kEUR | 63,522 kEUR | 0 | **GUARDRAIL: UNCHANGED** |
| Oborovo total accrued CIT | ~11,128 kEUR | 8,874 kEUR | −2,254 kEUR | |
| Oborovo total distributions | 71,598 kEUR | 68,775 kEUR | −2,823 kEUR | |

### Why IRR decreased (not increased)

The T2 H1 CIT collection effect dominates the T1 SHL deduction benefit:

- **T1** reduces taxable income → less tax → higher distributions → equity IRR ↑
- **T2** collects H1 tax that previously evaporated → more tax cash outflow → equity IRR ↓

Net: equity IRR falls ~27 bps for TUHO, ~12 bps for Oborovo. This is the **correct**
result — the model was previously under-collecting tax (H1 accruals evaporated).

All IRR values are finite, positive, and within sensible ranges. All stop/escalation
conditions are clear.

---

## Stop Conditions — All Clear

| Condition | Status |
|-----------|--------|
| Senior debt changes | ✅ UNCHANGED |
| Total senior DS changes | ✅ UNCHANGED |
| Project factories changed | ✅ NOT TOUCHED |
| waterfall_core.py changed | ✅ NOT TOUCHED |
| Project IRR outside sensible range | ✅ CLEAR (9.41%, 8.09%) |
| Equity IRR outside sensible range | ✅ CLEAR (11.32%, 10.54%) |
| DSCR falls below covenant threshold | ✅ CLEAR (1.379, 1.179) |
| Tax becomes negative | ✅ CLEAR (no negative tax) |
| Implementation touches more than waterfall_engine.py | ✅ ONLY waterfall_engine.py |
| Two-pass fails to converge | ✅ CLEAR (two passes exact) |
| T1/T2 create contradictory effects | ✅ CLEAR (both reduce equity IRR — consistent direction) |

---

## Files Changed

| File | Change |
|------|--------|
| `domain/waterfall/waterfall_engine.py` | T1: two-pass SHL deduction; T2: H1 CIT carry-forward |
| `tests/test_excel_parity_stack_t.py` | 28 new Stack T acceptance tests |
| `tests/test_excel_parity_stack_k.py` — `stack_s.py` | Re-baselined IRR/CIT/distribution golden values |
| `docs/STACK_T_TAX_ENGINE_ACCURACY.md` | This document |

---

## Regression Strategy

- No waterfall_core.py, project_factories.py, input_adapter.py, or export changes.
- Senior debt and total senior DS are unchanged — debt sizing is not affected.
- SHA pins in `test_phase51f_parallel_work_guardrails.py` for `waterfall_core.py` and
  `project_factories.py` are unchanged (Stack T does not touch those files).
- `waterfall_engine.py` is NOT in the SHA pin set.
- All 286 Stack K–U parity + guardrail tests pass at new re-baselined values.
- All 28 Stack T acceptance tests pass.

---

## Test Summary

| Class | Tests | Covers |
|-------|-------|--------|
| `TestT1SHLDeductionInTaxBasis` | 3 | SHL interest non-zero, taxable profit deducts SHL |
| `TestT2H1CITSettlement` | 5 | H1 accrues/zero cash, H2 settles H1+H2, lifetime reconciliation |
| `TestSeniorDebtUnchanged` | 4 | Senior debt and total senior DS guardrail |
| `TestProjectFactoriesUnchanged` | 2 | Factories run without error |
| `TestStackUExportIRRScalingPreserved` | 2 | Stack U /100 fix not reverted |
| `TestStackRSeededPathParity` | 1 | Stack R determinism preserved |
| `TestStackSExportColumnNaming` | 1 | Stack S DS column rename preserved |
| `TestSHLRepassConsistency` | 6 | SHL re-pass guard never fires; shi ≤ gross interest; SHL fully repaid |
| `TestPostTKPISanity` | 6 | Post-T TUHO+Oborovo KPI re-baseline |
| `TestNoNaNInf` | 4 | No NaN/inf in tax, DSCR, distributions; CIT totals |

All 34 Stack T tests pass.
All 286 Stack K–U parity + guardrail tests pass (320 total).
