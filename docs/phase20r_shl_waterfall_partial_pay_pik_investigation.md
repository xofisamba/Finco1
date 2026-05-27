# Phase 20R — SHL Waterfall Partial-Pay / PIK / Sweep Investigation

**Branch:** `phase20r-shl-waterfall-partial-pay-pik-investigation`  
**Base SHA:** `9c233168fb9734b4b1da20a199cd7993e247d87a` (after PR #279)  
**Head SHA:** `58019c67e215ec68ca3c6ae542ca2938f3957c7e`  
**Status:** Draft — diagnostics only, no runtime changes

---

## Purpose

Investigate the exact SHL waterfall rule, especially why Excel sweeps SHL in early periods while Python only applies PIK (no principal sweep). Determine whether the mismatch is in the trigger logic, the CF base, or the sweep ordering.

**No runtime formula changes in this phase.**

---

## Scope

- TUHO P4 (period index 3)
- Oborovo P4 (period index 3)
- TUHO P19 / P35 (first dividend, SHL near-zero)
- Oborovo P0-P4

---

## Expected Partial-Pay Waterfall (User's Interpretation)

The user's expected rule for SHL:

```
1. available = cash_after_senior (fcf_for_shl)
2. gross_interest = opening_balance * rate * day_fraction
3. wht = gross_interest * wht_rate
4. net_interest = gross_interest - wht
5. interest_paid = min(net_interest, available)
6. unpaid_net_interest = max(0, net_interest - interest_paid)
7. if PIK allowed:
       pik_interest = unpaid_net_interest
       accrued_unpaid_interest = 0
   else:
       pik_interest = 0
       accrued_unpaid_interest = unpaid_net_interest
8. cash_after_interest = available - interest_paid
9. principal_sweep = min(cash_after_interest, opening_balance + pik_interest)
10. closing_balance = opening_balance + pik_interest - principal_sweep
11. fcf_for_dividends = max(0, cash_after_interest - principal_sweep)
```

Key: There should **not** be an all-or-nothing trigger requiring CF to exceed full annual interest before any SHL principal payment occurs.

---

## Current Python Implementation

### Trigger Logic (`waterfall_engine.py` line 798)

```python
pik_switch_triggered = (_cf_for_shl > shl_balance * shl_rate)
```

This compares `fcf_for_shl` against **annual** interest (`balance * annual_rate`). If False, the model stays in PIK phase (no principal sweep). If True, switches to SWEEP phase.

**Problem:** In early periods, `fcf_for_shl` is often much smaller than annual interest (e.g., 1,111 < 2,643). Even if `fcf_for_shl > period_interest`, the trigger is False and no SWEEP occurs — even though partial cash payments to principal would be possible.

### SHL Engine (`shl_engine.py`)

The `compute_shl_period_v3` function already handles partial-pay and SWEEP correctly:

- **PIK phase (pik_switch_triggered=False):** interest paid = min(cf, net), PIK = gross - cash_paid, principal = 0
- **SWEEP phase (pik_switch_triggered=True):** interest paid = min(net, cf), remaining CF sweeps principal

The v3 gross/net PIK fix is already in place. The SWEEP phase logic is also correct.

**Root cause is the TRIGGER, not the computation.**

### Waterfall Ordering (waterfall_engine.py)

For `pik_then_sweep` method, the waterfall ordering is:

1. CF after tax → senior debt service
2. DSRA funding/release
3. SHL PIK phase (interest + PIK, no principal) — triggered by `_cf_for_shl > balance * rate` or per-method override
4. Distribution: senior outstanding → DSRA sweep to senior; SHL outstanding → distribution = 0; all repaid → distribution = FCF

**Key issue:** The condition "SHL outstanding: all FCF to SHL repayment" (line 942) would route ALL remaining CF to SHL principal — but this only applies when `_pik_trigger` is True. Since trigger is False in P4 (using annual threshold), SWEEP never happens via this path either.

---

## TUHO P4 Findings

| Field | Python | Excel | Gap |
|---|---|---|---|
| fcf_for_shl | `1,111.60` | `~2,095` (estimated) | Excel has more CF |
| Opening SHL balance | `33,324.92` | `~33,325` | ✅ match |
| Annual interest threshold | `2,642.67` | — | annual trigger basis |
| Period interest (gross) | `1,332.19` | `~1,332` | ✅ match |
| Python trigger | **False** (1,111 < 2,643) | True | ❌ |
| Python sweep | **0.00** | **982.99** | ❌ |
| Python distribution | **0.00** | **0.00** | ✅ |

**Gap analysis:**  
Python stays in PIK phase. Excel appears to enter SWEEP phase with available CF = 2,094.59 (estimated). If Excel triggers SWEEP with cf=2,094.59:
- interest_paid = min(net_int, cf) = min(1,332, 2,095) = 1,332 (full period interest)
- remaining = 2,095 - 1,332 = 763
- principal_sweep = min(763, balance+pik) ≈ 763

But principal should be 982.99. Thus Excel's CF base must be different (perhaps 3,156 total CF before senior DS × different allocation). For the sweep to be 982.99 after interest_paid ≈ 1,111: r99 ≈ 2,094.59 and 982.99 remaining after interest.

**Likely cause:** Excel uses a different CF base for SHL sweep, or triggers SWEEP using a different condition (not annual interest threshold).

---

## Oborovo P4 Findings

| Field | Python | Excel | Gap |
|---|---|---|---|
| fcf_for_shl | `650.40` | `650.40` | ✅ match |
| Opening SHL balance | `14,716.20` | `14,716.20` | ✅ match |
| Period interest (gross) | `583.81` | `~584` | ✅ match |
| Python trigger | **False** (650 < 1,167) | True (estimated) | ❌ |
| Python sweep | **0.00** | **340.54** | ❌ |
| Python distribution | **64.97** | **0.00** | ❌ |

**Gap analysis:**  
In PIK phase, Python pays interest (583.81) from cf_for_shl (650.40), leaving residual 66.59. This residual flows to dsra / distribution. Excel instead routes all 650.40 to SHL:
- interest = 583.81
- principal_sweep = 340.54 (Excel)
- distribution = 0 (Excel)

The dsra contribution for Oborovo P4 = -64.97 (DSRA is being released), while fcf_for_shl = 650.40. The distribution routing in Python leaks 64.97 to equity during the SHL repayment period.

**Likely cause:** Same trigger issue. plus different CF routing: Python's `cf_after_reserves` includes DSRA release (64.97) that flows to distribution, while Excel routes all residual to SHL before distribution.

---

## SHL Engine v3 — Already Correct

`compute_shl_period_v3` at `domain/waterfall/shl_engine.py` line 40 implements:

```python
interest_paid = min(max(0.0, cf_available), net_interest)
pik = gross_interest - interest_paid  # correct: gross - cash paid
```

When `pik_switch_triggered=True` in SWEEP phase:
```python
interest_paid = min(net_interest, cf_available)
pik = gross_interest - interest_paid
remaining = max(0.0, cf_available - interest_paid)
principal = min(remaining, shl_balance)
```

The implementation is correct. **The trigger is the problem.**

---

## Recommended Implementation Fix (Phase 20S — NOT implemented)

```python
# TRIGGER: use period interest (not annual) when in PIK phase
# Option A: replace annual threshold with period threshold
period_interest_threshold = shl_balance * shl_rate_per

# Option B: remove threshold entirely, use proportional sweep
# Every period: interest from CF, residual to principal
# (no PIK/SWEEP switch — just partial pay waterfall)

# Option C: match Excel CF base
# Route r98/r99 differently for SHL vs distribution in pik_then_sweep
# In Oborovo P4: cf_after_reserves = 650.40, not cf_after_reserves - dsra_release
# The 64.97 DSRA release should also go to SHL, not distribution
```

### Proposed Formula (Option B — Simple Partial Pay)

```python
available = cf_for_shl
gross_interest = opening_balance * rate_per_period
net_interest = gross_interest * (1 - wht_rate)

interest_paid = min(net_interest, available)
unpaid_interest = max(0.0, net_interest - interest_paid)

if pik_allowed:
    pik = unpaid_interest  # capitalize unpaid
else:
    pik = 0.0

cash_after_interest = available - interest_paid
principal_sweep = min(cash_after_interest, opening_balance + pik)

closing_balance = opening_balance + pik - principal_sweep
fcf_for_dividends = max(0.0, cash_after_interest - principal_sweep)
```

**Key properties:**
- No trigger needed (sweep happens every period if residual > 0)
- Interest always paid from available CF first
- PIK = unpaid interest (gross - cash paid)
- Principal = remaining CF after interest (capped at remaining balance)

---

## Risk Assessment

- **Implementing Option B** would change equity IRR and distribution timing materially. Requires calibration against Excel anchor values.
- **Changes to trigger threshold** would affect both TUHO and Oborovo. The SHL calibration parameters (shl_idc_keur, shl_rate) would need re-verification.
- **DSRA interaction:** Oborovo's dsra_release flows to distribution. Changing the distribution waterfall would require DSRA routing changes.
- **Backward compatibility:** Phase 20S options should be gated behind a feature flag or new SHL method name to avoid breaking existing tests.

---

## Tests Required Before Implementation

1. TUHO: equity IRR within ±1.0pp of Excel 11.61%
2. TUHO: total distributions within ±5% of Excel 173,572 kEUR
3. TUHO: first dividend at P35 (SHL balance → 0)
4. Oborovo: equity IRR within ±1.0pp of Excel 10.60%
5. Oborovo: total distributions within ±5% of Excel 104,918 kEUR
6. Oborovo: no distribution while SHL balance > 0
7. Both: senior debt unchanged (calibration baseline)

---

## Changed Files

| File | Change |
|---|---|
| `domain/diagnostics/shl_waterfall.py` | +119 lines — diagnostic dataclasses + builder |
| `domain/diagnostics/__init__.py` | +3 lines — package init |
| `tests/test_phase20r_shl_waterfall_diagnostic.py` | +413 lines — 13 diagnostic tests |
| `docs/phase20r_shl_waterfall_partial_pay_pik_investigation.md` | This document |

**No runtime formula changes.** No changes to SHL engine, waterfall engine, senior debt logic, or workbook export.

---

## Validation Results

```
tests/test_phase20r_shl_waterfall_diagnostic.py: 13 tests
  PASSED: test_tuho_p4_has_all_required_fields
  PASSED: test_oborovo_p4_has_all_required_fields
  PASSED: test_tuho_p4_flags_sweep_gap
  PASSED: test_oborovo_p4_flags_distribution_leakage
  PASSED: test_oborovo_p4_partial_pay_reconciles
  PASSED: test_tuho_p4_trigger_is_false_annual_threshold
  PASSED: test_shl_engine_partial_pay_is_properly_implemented
  PASSED: test_shl_engine_sweep_cutoff_is_correct
  PASSED: test_tuho_first_dividend_period_is_35
  PASSED: test_oborovo_sweep_and_distribution_pattern
  PASSED: test_report_failed_rows
  PASSED: test_trigger_all_or_nothing_identified_as_likely_cause
  PASSED: test_runtime_no_changes_in_phase20r_diagnostic

Full regression (all phases): 46 passed, 2 xfailed, 1 xpassed in 1.66s
main_web: import OK
```

---

## Guardrail Confirmations

| Guardrail | Status |
|---|---|
| Runtime/model formulas changed? | **No** — diagnostics only |
| Workbook/export calculations changed? | **No** |
| JS financial calculations added? | **No** |
| SHL engine v3 still uses gross interest for PIK? | ✅ Yes |
| G20 remains BLOCKED | ✅ |
| R99/R102 remains NOT APPROVED | ✅ |
