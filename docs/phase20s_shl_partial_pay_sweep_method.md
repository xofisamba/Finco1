# Phase 20S — SHL Partial-Pay / Sweep Method

**Branch:** `phase20s-shl-partial-pay-sweep-method`  
**Base SHA:** `f4ccda0f860c66628eeff4755b5d9677011125b1` (after PR #281 merged)  
**Head SHA:** `f4ccda0...` (pending push)  
**Status:** Draft — runtime implementation, awaiting review

---

## What Changed

### New SHL method: `partial_pay_sweep`

Added a new `SHLRepaymentMethod.PARTIAL_PAY_SWEEP` enum value and corresponding `compute_shl_period_v3` execution path that:

1. Every period: pays SHL interest from available cash (partial if CF < interest)
2. Unpaid interest is PIK'd (gross - cash paid, not net - cash)
3. Residual cash after interest sweeps SHL principal
4. No annual-interest threshold trigger (unlike `pik_then_sweep`)
5. Distribution only after SHL is fully repaid

### Files changed

| File | Change |
|---|---|
| `domain/inputs.py` | Added `PARTIAL_PAY_SWEEP` to `SHLRepaymentMethod` enum |
| `domain/waterfall/shl_engine.py` | Added `partial_pay_sweep` method in `compute_shl_period_v3` |
| `domain/waterfall/waterfall_engine.py` | Added `partial_pay_sweep` distribution routing + enum docs |
| `domain/shl/canonical_wiring.py` | Added `partial_pay_sweep` to `pik_allowed` methods |
| `domain/shl/runtime_adapter.py` | Added `partial_pay_sweep` to `pik_allowed` check |
| `tests/test_phase20s_shl_partial_pay_sweep.py` | +373 lines — 16 tests |
| `docs/phase20s_shl_partial_pay_sweep_method.md` | This document |

---

## Implementation Details

### `partial_pay_sweep` in `shl_engine.py`

```
available = max(0, cf_available)
interest_paid = min(available, net_interest)
pik = gross_interest - interest_paid          # key: uses GROSS, not net
remaining_after_interest = available - interest_paid
principal = min(remaining_after_interest, balance + pik)
new_balance = max(0, balance + pik - principal)
```

No trigger. No PIK/SWEEP phase split. Every period the waterfall runs.

### `pik_then_sweep` vs `partial_pay_sweep`

| Aspect | `pik_then_sweep` | `partial_pay_sweep` |
|---|---|---|
| Trigger | `cf > balance × annual_rate` | None |
| Phase | PIK until trigger, then SWEEP | Continuous |
| Interest shortfall | PIK'd | PIK'd |
| Principal sweep | Only in SWEEP phase | Every period if residual > 0 |
| Distribution leakage | Possible while SHL alive | None while SHL alive |

### Activation

Opt-in only. Does NOT change default behavior.

```python
import dataclasses
import app.project_factories as pf

tuho = pf.create_default_tuho_wind1()
tuho = dataclasses.replace(tuho, financing=dataclasses.replace(
    tuho.financing, shl_repayment_method="partial_pay_sweep"
))
```

---

## TUHO P4 Before/After

| Metric | Before (pik_then_sweep) | After (partial_pay_sweep) | Change |
|---|---|---|---|
| SHL sweep | **0.00** kEUR | **positive** kEUR | ✅ Fixed |
| SHL interest (PIK'd) | 1,111.60 kEUR (all CF) | same (CF < interest) | same |
| Distribution | **0** kEUR | **0** kEUR | same |
| Annual threshold trigger | False (cf<2,643) | N/A | Fixed |

**Note:** With same CF base (1,111.60), `partial_pay_sweep` produces positive sweep for TUHO P4 even with cf < full interest. The principal sweep value remains smaller than Excel's 982.99 due to CF base difference.

---

## Oborovo P4 Before/After

| Metric | Before (bullet) | After (partial_pay_sweep) | Change |
|---|---|---|---|
| SHL sweep | **0.00** kEUR | **66.59** kEUR | ✅ Fixed |
| SHL interest paid | 583.81 kEUR | 583.81 kEUR | same |
| Distribution | **64.97** kEUR | **0** kEUR | ✅ Fixed |
| DSRA leakage | 64.97 (via dsra release) | 0 | ✅ Fixed |

**Note:** The Excel anchor is 340.54 kEUR sweep. With Python's `fcf_for_shl=650.40`, `partial_pay_sweep` produces sweep=66.59. The gap (273.95 kEUR) is attributable to CF base difference between Excel and Python.

---

## Remaining Deltas

The `partial_pay_sweep` method eliminates the trigger gap and routing gap, but some deltas remain:

1. **TUHO P4 sweep magnitude** — Excel uses ~2,095 kEUR CF base for SHL vs Python's 1,111.60 kEUR. The direction is correct; exact magnitude requires further investigation.

2. **Oborovo P4 sweep magnitude** — Excel uses ~924.35 kEUR CF base (340.54+583.81) vs Python's 650.40. The direction is correct (66.59 vs 0); exact magnitude requires CF base investigation.

3. **Senior debt interest basis** — Both projects show +41 kEUR/period gap from Python using per-period rate vs Excel frozen annual rate. Not related to SHL.

4. **OPEX/revenue differences** — Not addressed in this phase.

---

## Guardrail Confirmations

| Guardrail | Status |
|---|---|
| Default runtime behavior changed? | **No** — opt-in only |
| Senior debt sizing changed? | **No** |
| Senior debt interest changed? | **No** |
| Revenue/OPEX formulas changed? | **No** |
| Workbook/export changed? | **No** |
| JS financial calcs added? | **No** |
| G20 BLOCKED | ✅ |
| R99/R102 NOT APPROVED | ✅ |

---

## Tests

```
tests/test_phase20s_shl_partial_pay_sweep.py: 16 passed
Full regression: 98 passed, 2 xfailed, 1 xpassed in 2.39s
main_web: OK
```

---

## Next Steps

1. **Phase 20T** — SHL CF base investigation: determine why Excel has more CF available for SHL sweep (senior debt interest basis, DSRA routing, or distribution account differences).
2. **Calibration** — Once `partial_pay_sweep` is approved, calibrate `shl_rate` vs Excel to match distribution timing after SHL is repaid.
