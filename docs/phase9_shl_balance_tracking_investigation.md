# Phase 9: SHL Balance Tracking Investigation

## Executive Summary

**Root cause identified:** The investigation harness was passing `shl_amount=0.0` in the `COMMON` dict to `run_waterfall_v3_core`, causing SHL balance to be initialized at 0 instead of 32,703.69 kEUR (29,135 + 3,568.69). This made `shl_balance_list` all-zeros in `build_sponsor_cashflows`, corrupting the equity IRR computation.

**PR #155 (22.31%) is a double error:** wrong SHL params AND wrong `equity_irr_method=equity_only`.

**Corrected equity IRR with proper SHL params:** see below — still needs investigation against Excel 11.61%.

## Root Cause

In `run_waterfall_v3_core`, line 573 of `domain/waterfall/waterfall_engine.py`:
```python
shl_balance = shl_amount + shl_idc_keur  # Opening balance = disbursed + IDC
```

The harness was passing `shl_amount=0.0` and `shl_idc_keur=0.0`, resulting in `shl_balance=0` for all periods regardless of the model's actual SHL parameters.

## Corrected SHL Balance (TUHO Wind 1)

With correct SHL params from `financing`:
- `shl_amount=29,135.0 kEUR`
- `shl_idc_keur=3,568.69 kEUR`
- `shl_repayment_method=pik_then_sweep`
- `shl_rate=7.93%`
- Opening balance: **32,703.69 kEUR**

| Period | Date | SHL Balance (kEUR) | SHL Interest | SHL Principal |
|--------|------|--------------------:|-------------:|-------------:|
| P2 | 2030-06-30 | 32,703.69 | 0.00 | 0.00 |
| P3 | 2030-12-31 | 30,889.97 | 1,307.36 | 1,813.72 |
| P4 | 2031-06-30 | 28,999.32 | 1,214.72 | 1,890.65 |
| P5 | 2031-12-31 | 27,001.75 | 1,159.27 | 1,997.57 |
| ... | ... | ... | ... | ... |

SHL is fully repaid by period 15 (senior debt sweep begins).

## Equity IRR Results

With corrected SHL params:

| Method | Equity IRR | Issue |
|--------|-----------|-------|
| `shl_plus_dividends` | 0.15% | Broken — distribution wiring issue |
| `equity_only` | 56.73% | Wrong investment base |
| Excel target | **11.61%** | Reference |

The `shl_plus_dividends` method gives 0.15% — this indicates the equity cashflow stream is still wired incorrectly. The equity investment base is correct (32,703.69 kEUR), but the per-period cashflows are wrong.

## Scope

**ANALYSIS / REPORTS / TESTS ONLY** — no runtime code changed.

This PR documents the SHL balance tracking bug and produces:
- `reports/phase9_shl_balance_tracking_detail.csv` (61 periods, corrected SHL data)
- `docs/phase9_shl_balance_tracking_investigation.md` (this doc)
- `tests/test_phase9_shl_balance_tracking_investigation.py`

## Next Steps

1. **Fix `shl_plus_dividends` equity IRR** — per-period equity cashflows are giving 0.15% IRR instead of ~11%
   - Likely issue: `build_sponsor_cashflows` equity CF stream doesn't properly track when SHL is repaid and dividends begin
   - `shl_balance=0` at period 15+ should trigger `dist` cashflows, not `shi`
2. **Verify against Excel** — need to confirm what Excel actually uses for equity IRR method
3. **G20 remains BLOCKED** pending equity IRR parity
