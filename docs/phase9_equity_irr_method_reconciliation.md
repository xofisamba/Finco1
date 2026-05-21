# Phase 9: Equity IRR Method Reconciliation

## Executive Summary

**Primary question:** Why does corrected `shl_plus_dividends` produce 14.96% instead of matching the calibrated 11.15% reference?

**Answer:** The calibrated 11.15% reference from Sprint 21 was computed with a **broken SHL balance** (harness passed `shl_amount=0.0`, making `shl_balance=0` for all 61 periods). PR #157 fixed this. The corrected `shl_plus_dividends` equity IRR is **14.96%** — this is the true model output with correctly tracked SHL.

The gap from 14.96% to Excel 11.61% is a **genuine model-excel difference** that needs further investigation before G20.

## Scope and Non-Goals

**In scope:** Analysis, reports, CSV data, tests.  
**Out of scope (this PR):** R99/R102 runtime implementation, SHL engine changes, Sponsor runtime changes.  
**G20:** BLOCKED pending equity IRR parity.

## Current Known Values

| Source | Equity IRR | Notes |
|--------|-----------|-------|
| `shl_plus_dividends` corrected (no double-count) | **14.96%** | Correct SHL params, correct cashflow stream |
| Model equity_irr (waterfall inline) | **14.74%** | Uses same logic as corrected |
| `build_sponsor_cashflows` XIRR | **26.66%** | BUG: double-counts shi+shp |
| `equity_only` (wrong method) | **56.73%** | Wrong investment base |
| Calibrated reference (Sprint 21) | **11.15%** | Uses DA wiring + `shl_balance=0` bug |
| Excel target | **11.61%** | Reference |

## Root Cause: `build_sponsor_cashflows` Double-Count

For `shl_plus_dividends` method, the waterfall engine computes `equity_cf` inline (lines 1082-1091):
```python
if shl_balance > 0:
    equity_cf = shi   # SHL interest only when balance > 0
else:
    equity_cf = dist  # Distributions after SHL repaid
```

Then `build_sponsor_cashflows` does:
```python
sponsor_cf = equity_cf + shi + shp  # DOUBLE-COUNT for shl_plus_dividends!
```

Since `equity_cf` already equals `shi` when `shl_balance > 0`, the function adds `shi + shp` on top, inflating the per-period cashflow by `shi + shp` (the full SHL service). This causes XIRR of 26.66% instead of 14.96%.

## Cashflow Method Comparison

| Method | Investment Base | Per-Period CF | IRR |
|--------|----------------|---------------|-----|
| `shl_plus_dividends` corrected | -33,203.69 kEUR | shi (while bal>0) or dist | **14.96%** |
| `build_sponsor_cashflows` (buggy) | -33,203.69 kEUR | shi + shi + shp (double-count) | 26.66% |
| `equity_only` (wrong method) | -33,203.69 kEUR | dist only | 56.73% |

**Why `equity_only` gives 56.73%:** The investment base is only 33,203.69 kEUR (SHL + IDC + share capital). With 0 SHL tracking, equity_only equity base = dist. With distributions of 284,342 kEUR spread over 60 periods, XIRR is 56.73% — this is mathematically wrong because equity_only doesn't account for SHL equity.

## Component Bridge: Why 14.96% vs 11.15%

The calibrated 11.15% was computed with `shl_amount=0.0` in the harness, meaning:
- `shl_balance = 0` for all periods
- `shi = 0` for all periods (no SHL interest tracked)
- `equity_cf = dist` for all periods (distributions only)
- Investment base: `-33,203.69` kEUR (SHL + IDC treated as equity)

With correct SHL params (PR #157 fix):
- `shl_balance` starts at 32,703.69 kEUR, repaid by period 16
- `shi = 1,307–0 kEUR` during SHL phase (PIK period)
- `equity_cf = shi` during SHL phase, then `= dist` after
- This increases early cashflows (SHL interest) but doesn't increase investment base
- Result: IRR increases from 11.15% → 14.96%

## Authoritative Method Recommendation

**`shl_plus_dividends` (corrected)** is the correct method for TUHO:
- Matches how Excel models sponsor economics (SHL interest during PIK phase, dividends after)
- Investment base includes SHL + IDC + share capital
- `build_sponsor_cashflows` has a double-count bug that must be fixed separately

**The 14.96% vs Excel 11.61% gap remains open.** Possible causes:
1. Excel may use a different equity base (possibly `equity_only` style, subtracting debt but not SHL)
2. Lockup distribution timing may differ between model and Excel
3. Terminal cash / residual value treatment
4. CO2 revenue inclusion in Excel but not in current model run

## Impact on G20 Readiness

- **G20 remains BLOCKED**
- R99/R102 NOT approved
- The 14.96% vs 11.61% gap must be resolved before G20 can be unblocked
- Recommended next branch: investigate Excel equity IRR methodology and reconcile timing differences

## Deliverables

| File | Description |
|------|-------------|
| `reports/phase9_equity_irr_method_comparison.csv` | 5 methods, IRR values, investment bases |
| `reports/phase9_equity_irr_cashflow_method_bridge.csv` | 61 period-level cashflow comparison |
| `reports/phase9_equity_irr_difference_by_component.csv` | Component-level delta analysis |
| `docs/phase9_equity_irr_method_reconciliation.md` | This doc |
| `tests/test_phase9_equity_irr_method_reconciliation.py` | 10 tests |

## Next Steps (Recommended Next Branch)

1. **Understand Excel equity IRR method** — what is Excel's equity base? Does it subtract debt but not SHL (equity_only style)?
2. **Check lockup distribution timing** — when exactly does Excel release locked distributions?
3. **Verify CO2 revenue impact** — does Excel include CO2 in equity cashflows?
4. **Fix `build_sponsor_cashflows` double-count** — separate bug, not in scope for this PR
5. **Reconcile to within ±1.0pp of Excel 11.61%**

## Explicit Statements

- **R99/R102 NOT approved** — this analysis does not implement or approve R99/R102
- **G20 remains BLOCKED** — equity IRR gap must be resolved
- **No runtime code changed** — all deliverables are analysis/reports/tests only