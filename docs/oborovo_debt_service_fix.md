# Oborovo Debt-Service Bug Fix

**Date:** 2026-05-08
**Type:** Bug fix — waterfall engine
**Status:** Fixed and tested

## Root Cause

In `domain/waterfall/waterfall_engine.py`, the `fixed_debt_keur` branch (used by Oborovo's `gearing_cap` debt sizing method) incorrectly computed debt service payments as:

```
payment = fixed_debt_keur / target_dscr
```

For Oborovo: `42,852 / 1.15 = 37,263 kEUR/period`

This is **16.7x too large**. The correct payment is derived from scaling the DSCR-sculpted payment schedule:

```
scale = fixed_debt_keur / dscr_debt
payment[t] = payment_sculpted[t] × scale
```

For Oborovo: `2,021 kEUR/period` (matching DSCR target).

## Why the Wrong Formula Was Used

The code was attempting to rescale sculpted balances to fixed debt, but incorrectly computed "allowable debt service" as `fixed_debt / target_dscr` (i.e., total debt divided by target DSCR) instead of scaling the actual period-by-period sculpted payment amounts.

This produced a constant payment of ~37,263 kEUR/period, which:
1. **Far exceeded** EBITDA (~2,575 kEUR/period) → DSCR = 0.069 ❌
2. **Implied debt repayment** in ~1.3 years (not 14 years)
3. **Caused lockup** on all periods → distributions blocked

## Correct Formula

The payment schedule for the `fixed_debt_keur` path should be:

```python
scale = fixed_debt_keur / dscr_debt
balance_schedule = [b * scale for b in sculpt_result.balance_schedule]
payments = [p * scale for p in sculpt_result.payment_schedule]
interest_schedule = [balance_schedule[t] * rate_schedule[t] for t in ...]
principal_schedule = [payments[t] - interest_schedule[t] for t in ...]
```

This preserves the sculpted payment **shape** (front-loaded interest, back-loaded principal) while scaling the absolute amounts to match the fixed debt anchor.

## Before/After KPIs

| KPI | Before (Bug) | After (Fixed) | Reference |
|-----|-------------|---------------|-----------|
| Avg DSCR | 0.181 | **1.250** | 1.147 |
| Min DSCR | 0.068 | **1.182** | — |
| Equity IRR | 9.96% | **10.16%** | 10.60% |
| Project IRR | 9.11% | **8.65%** | 7.96% |
| Total Senior DS | ~1M kEUR (wrong) | **63,935 kEUR** | ~65,000 kEUR |
| Total Debt | 42,852 | 42,852 | 42,852 ✅ |

The **Project IRR shifted** from 9.11% to 8.65% because:
- Old formula used levered tax (interest deductions reduced tax → inflated CF → inflated IRR)
- New unlevered tax fix: `tax = tax_rate × max(0, EBITDA − dep)` (financing-independent)
- TUHO project_irr also shifted from 10.46% → 9.47% (correctly aligned to reference 9.47%)

## Affected Projects

| Project | Method | Impact |
|---------|--------|--------|
| **Oborovo Solar** | `gearing_cap` + `fixed_debt_keur` | ✅ Fixed — DSCR/IRR improved |
| **TUHO Wind** | `fixed` debt_sizing (MIN path) | ✅ No change (different branch) |
| **Generic Solar** | `dscr_sculpt` (no fixed_debt) | ✅ Unaffected |
| **Generic Wind** | `dscr_sculpt` (no fixed_debt) | ✅ Unaffected |

## Remaining Calibration Gap — Project IRR

After fixing both bugs (debt service + unlevered tax), Oborovo project IRR is **8.65%** vs reference **7.96%** (+0.69pp gap).

Known contributors to residual gap:
1. **Merchant curve vintage** — post-PPA market prices differ from Excel reference
2. **Depreciation convention** — 20y vs 30y asset life (deferred, not blocking)
3. **Tax loss carryforward timing** — construction period losses affect early-year tax

These are documented in `docs/known_limitations.md` as P1/P2 roadmap items.

## Files Changed

- `domain/waterfall/waterfall_engine.py` — fixed_debt_keur payment computation + unlevered project tax
- `tests/test_golden_values.py` — updated project_irr golden values (levered → unlevered)
- `tests/test_oborovo_debt_service.py` — new regression test suite
- `docs/oborovo_debt_service_fix.md` — this file