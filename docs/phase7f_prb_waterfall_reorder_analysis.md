# Phase 7F PR B: Waterfall Reorder — Senior Sweep Before SHL

## Problem Statement

The R99-equivalent cap for TUHO SHL was disabled in PR A because it used
`remaining_senior_balance` (a debt balance) instead of a cash-flow amount.

The real R99-equivalent should be:
```
r99_equivalent_cf = cf_after_reserves - senior_sweep_amount
```

where `senior_sweep_amount` is computed in the distribution section (lines ~756-765)
**after** the SHL call. This creates a dependency loop: SHL needs to know the sweep
before the sweep is computed.

## Current Waterfall Order (lines ~620–800)

```
620:  senior_ds computed
636:  _cf_for_shl = cf_after_tax - senior_ds - dsra_contrib   ← SHL cash basis
637:  _pik_trigger = ...
665:  is_shl_disbursement_period check
668:  [TUHO CAP — disabled, using pass]
670:  compute_shl_period(cf_after_senior_ds=_cf_for_shl, ...)   ← SHL CALL
704:  shl_svc = shi + shp
706:  cf_after_ds = cf_after_tax - senior_ds - shi
728:  cf_after_reserves = cf_after_ds + dsra_withdrawal - dsra_contrib
733:  dscr = ebitda_minus_tax / senior_ds
737:  lockup = dscr < lockup_dscr
745:  sweep_dscr_threshold = 1.35
749:  remaining_senior_balance = balance_schedule[period_in_tenor]
752:  if pik_then_sweep:
753:      if lockup: dist=0, sweep=0
756:      elif remaining_senior_balance > 0:
757:          if dscr > sweep_dscr_threshold:
758:              dist, sweep_amount = cash_sweep(cf_after_reserves, ...)   ← SENIOR SWEEP
766:      elif shl_balance > 0:
767:          shl_repayment = max(0, cf_after_reserves)
769:          dist=0, sweep=0
773:      else: dist=max(0, cf_after_reserves), sweep=0
```

## Excel R99 Semantics

Excel R99 = "FCF for Shareholder Loan" = cash available for SHL after senior debt.
In Excel's DS sheet, R117 = R99 - shl_interest (cash available after interest).
The SHL principal formula: = MIN(opening_balance, R117 × %outstanding)

Excel uses **sculpted R99** — constrained cash flow, not raw residual.
Python uses raw `cf_after_reserves` which can exceed sculpted R99.

## Proposed Fix: Reorder to Compute Senior Sweep Before SHL

Move the senior sweep computation **before** the SHL call, using the same
`cash_sweep()` function with `cf_after_reserves` as the cash input.

New order:

```
1.  senior_ds (existing)
2.  cf_after_reserves (existing — after DSRA)
3.  [NEW] senior_sweep_amount = compute_senior_sweep(cf_after_reserves, dscr, ...)
4.  [NEW] r99_equivalent_cf = max(0.0, cf_after_reserves - senior_sweep_amount)
5.  _cf_for_shl = cf_after_tax - senior_ds - dsra_contrib
6.  [TUHO CAP] _cf_for_shl = min(max(0.0, _cf_for_shl), max(0.0, r99_equivalent_cf))
7.  compute_shl_period(..., cf_after_senior_ds=_cf_for_shl, ...)
8.  SHL service recording
9.  cf_after_ds, DSRA, DSCR, lockup
10. Distribution (re-use already-computed senior_sweep_amount)
```

The senior sweep computation needs to move up AND be stored in a variable
that can be reused in the distribution section.

## Senior Sweep Computation Details

Current (lines 756-765):
```python
if dscr > sweep_dscr_threshold:
    dist, sweep_amount = cash_sweep(
        cf_after_reserves=cf_after_reserves,
        senior_debt_balance=remaining_senior_balance,
        sweep_dscr=sweep_dscr_threshold,
        actual_dscr=dscr,
        sweep_pct=1.0,
    )
else:
    dist = 0
    sweep_amount = 0.0
```

The `cash_sweep()` function (sculpting_iterative.py:513):
```python
def cash_sweep(cf_after_reserves, senior_debt_balance, sweep_dscr, actual_dscr, sweep_pct=1.0):
    if senior_debt_balance <= 0 or actual_dscr <= sweep_dscr:
        return max(0.0, cf_after_reserves), 0.0
    sweep = min(cf_after_reserves * sweep_pct, senior_debt_balance)
    distribution = max(0.0, cf_after_reserves - sweep)
    return distribution, sweep
```

Key insight: `sweep_amount` is determined by:
- `remaining_senior_balance` (current senior balance)
- `cf_after_reserves` (cash available)
- `dscr` (current period DSCR)

All three are available BEFORE the SHL call — we just need to compute
`sweep_amount` early and store it for reuse.

## Code Changes Required

### 1. waterfall_engine.py — move senior sweep before SHL

Between line ~728 (`cf_after_reserves = ...`) and line ~737 (`lockup = ...`),
insert:

```python
# ── Senior sweep (moved before SHL to enable R99-equivalent cap) ──
# Compute senior sweep amount early so it can be used as the R99-equivalent
# basis for TUHO SHL cash cap (PR B).
# sweep_dscr_threshold = 1.35 (same as in distribution section)
# senior_sweep_active when: remaining_senior_balance > 0 AND dscr > sweep_dscr_threshold
if remaining_senior_balance > 0 and dscr > sweep_dscr_threshold:
    senior_sweep_amount, _ = cash_sweep(
        cf_after_reserves=cf_after_reserves,
        senior_debt_balance=remaining_senior_balance,
        sweep_dscr=sweep_dscr_threshold,
        actual_dscr=dscr,
        sweep_pct=1.0,
    )
else:
    senior_sweep_amount = 0.0

# ── TUHO SHL cash-cap (Excel R99-equivalent) ──
# r99_equivalent_cf: cash that survives after senior scheduled DS and sweep.
# This is the Excel R99 / FCF for Distribution equivalent.
# TUHO uses this to prevent SHL from consuming cash that Excel would
# hold back as sculpted FCF for senior debt coverage.
if use_senior_sweep_cash_cap_for_shl and shl_repayment_method == "pik_then_sweep":
    r99_equivalent_cf = max(0.0, cf_after_reserves - senior_sweep_amount)
    raw_cf_for_shl = _cf_for_shl
    _cf_for_shl = min(max(0.0, raw_cf_for_shl), max(0.0, r99_equivalent_cf))
```

### 2. In distribution section — reuse senior_sweep_amount

In the pik_then_sweep branch, replace the redundant `cash_sweep()` call with:
```python
dist, sweep_amount = cf_after_reserves - senior_sweep_amount, senior_sweep_amount
```

## Variables Needed at SHL Call Point

| Variable | Defined at | Available at SHL call? |
|---|---|---|
| `cf_after_reserves` | ~728 | YES (after DSRA) |
| `remaining_senior_balance` | ~749 | YES |
| `dscr` | ~733 | YES |
| `sweep_dscr_threshold` | ~746 | YES (1.35 hardcoded) |
| `senior_sweep_amount` | NEW | YES (computed before SHL) |

## Impact on Other SHL Methods

- `bullet`: no change (shl_repayment_method != "pik_then_sweep")
- `cash_sweep`: no change
- `pik`: no change
- `accrued`: no change

## Testing

After reordering, verify:
- TUHO SHL balance P28–P36 moves closer to Excel (target: ±5% at P32)
- TUHO first distribution at index 35 (Excel P36, date 2047-06-30)
- TUHO total distributions within ±10% of 151,709 kEUR
- Oborovo unchanged (flag=False, no impact)
- All existing tests still pass

## Alternatives Considered

**Alternative A (rejected):** Compute `sweep_amount` twice — once before SHL, once in distribution. Wasteful but simple. Chosen path avoids duplication.

**Alternative B (rejected):** Restructure entire waterfall into pre-sweep / post-sweep phases. Large refactor, too risky for a targeted fix.

**Alternative C (rejected):** Use `remaining_senior_balance` as R99-equivalent. Wrong semantics — balance, not cash flow.