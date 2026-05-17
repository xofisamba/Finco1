# Phase 6 TUHO Tax-Basis Period Comparison

## Purpose

This branch uses the Phase 6 tax audit fields to compare TUHO Excel tax basis against Python period by period.

It is diagnostic only:

- no tax formula changes
- no runtime cashflow changes
- no R99/R102 source acceptance
- no SHL FCF waterfall opt-in
- no project factory changes

## Current Residual

After Phase 7M aligned the cash-tax payment timing diagnostically:

| Measure | Total kEUR |
| --- | ---: |
| Excel R67 | -38,240.9 |
| Python Excel-style R67 diagnostic | -39,575.7 |
| Residual | -1,334.8 |

This residual is now tax-basis related, not R67 payment timing.

## Total Comparison

The comparison uses the explicit senior DS harness, so senior debt is not the source of the tax residual.

| Component | Excel total | Python audit total | Delta |
| --- | ---: | ---: | ---: |
| Depreciation | 72,993.7 | 70,691.5 | -2,302.2 |
| Fiscal reintegration | -9,242.7 | 0.0 | +9,242.7 |
| EBT / Python EBT proxy | 193,569.0 | 205,655.6 | +12,086.6 |
| Taxable income before losses | 184,326.3 | 244,864.9 | +60,538.6 |
| Losses N-1 / opening loss pool | -37,087.2 | 332,915.4 | sign/convention mismatch |
| Allocated losses / loss used | 4,106.0 | 25,000.0 | +20,894.0 |
| Losses N / closing loss pool | -166,716.5 | 307,915.4 | sign/convention mismatch |
| Taxable profit after losses | 180,220.3 | 219,864.9 | +39,644.6 |
| CIT accrual | 38,240.9 | 39,575.7 | +1,334.8 |
| Excel-style H2 cash tax | -38,240.9 | -39,575.7 | -1,334.8 |

## Period Observations

### Early Operating Periods

| op_idx | Date | Excel dep | Python dep | Excel EBT | Python EBT proxy | Excel CIT | Python CIT |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 2030-06-30 | 1,845.4 | 1,168.5 | -1,369.7 | 604.6 | 0.0 | 0.0 |
| 1 | 2030-12-31 | 1,876.0 | 1,187.9 | -1,381.4 | -330.1 | 0.0 | 0.0 |
| 2 | 2031-06-30 | 1,845.4 | 1,168.5 | -1,306.1 | -270.7 | 0.0 | 0.0 |
| 3 | 2031-12-31 | 1,876.0 | 1,187.9 | -1,314.9 | -247.9 | 0.0 | 0.0 |

Python depreciation is lower in early periods, which raises the Python EBT proxy. Python still carries a large positive loss pool, so CIT remains zero.

### Transition / Tax-Payment Periods

| op_idx | Date | Excel cash tax | Python Excel-style cash tax | Delta | Main visible cause |
| ---: | --- | ---: | ---: | ---: | --- |
| 25 | 2042-12-31 | -120.2 | -1,702.9 | -1,582.7 | Excel uses allocated losses; Python does not use loss in this period. |
| 27 | 2043-12-31 | -955.2 | -1,751.3 | -796.1 | Python taxable profit remains higher. |
| 35 | 2047-12-31 | -1,644.9 | -1,960.8 | -315.8 | Python taxable profit exceeds Excel taxable profit. |
| 37 | 2048-12-31 | -1,811.3 | -2,014.1 | -202.8 | Python taxable profit exceeds Excel taxable profit. |

At op_idx 25, Excel uses `1,807.3 kEUR` of allocated losses while Python uses `0.0 kEUR`. This is the clearest period-level signal that loss timing/convention is part of the residual.

### Late Periods

| op_idx | Date | Excel dep | Python dep | Excel cash tax | Python Excel-style cash tax | Delta |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 57 | 2058-12-31 | 0.0 | 1,187.9 | -2,984.2 | -2,513.7 | +470.5 |
| 58 | 2059-06-30 | 0.0 | 1,168.5 | 0.0 | 0.0 | 0.0 |
| 59 | 2059-12-31 | 0.0 | 1,187.9 | -2,999.9 | -2,521.1 | +478.7 |

Python continues depreciation into the final years where the Excel depreciation fixture is zero. This lowers Python taxable profit and partly offsets the earlier over-taxation.

## Residual Decomposition

Visible basis drivers:

| Driver | Delta | Interpretation |
| --- | ---: | --- |
| Depreciation | -2,302.2 | Python total depreciation is lower than Excel, but timing differs sharply: lower early, higher late. |
| Fiscal reintegration | +9,242.7 | Excel has a negative fiscal reintegration row; Python audit currently shows zero because construction tax loss is preloaded. |
| EBT proxy | +12,086.6 | Python pre-tax basis is higher before loss mechanics. |
| Taxable income before losses | +60,538.6 | Python audit basis is much higher under current positive-pool convention. |
| Loss used | +20,894.0 | Python uses more loss in aggregate, but timing differs materially. |
| Taxable profit after losses | +39,644.6 | Python remains higher after losses. |
| CIT accrual | +1,334.8 | Net effect after loss mechanics and annual H2 timing. |

Important convention mismatch:

- Excel loss rows are negative carry-forward rows plus positive allocated losses.
- Python audit fields expose positive opening and closing loss pools.

The totals are therefore not one-to-one without a sign and ageing bridge.

## Root Cause

The remaining R67 residual is a combination of:

1. depreciation timing and total mismatch
2. fiscal reintegration treatment mismatch
3. loss carry-forward sign, timing, and allocation mismatch
4. SHL interest basis mismatch previously identified in the tax-basis bridge

The period data does not support a one-line formula correction.

## Fixability Decision

Classification: **B. Requires Phase 6 tax engine alignment.**

A small safe formula fix is not justified yet because:

- Excel fiscal reintegration is not mapped to Python's preloaded construction loss treatment.
- Excel loss carry-forward rows need a sign/ageing bridge before runtime alignment.
- Python depreciation timing differs from Excel across the horizon, not just by a constant total.
- SHL interest basis differs and is entangled with future SHL waterfall work.

## Recommended Next Branch

Recommended next branch:

`phase6-tuho-tax-loss-fiscal-reintegration-bridge`

Scope:

- Build explicit Excel-vs-Python sign bridge for losses N-1, allocated losses, and losses N.
- Map Excel fiscal reintegration to Python prior-tax-loss initialization and audit fields.
- Keep runtime formulas unchanged.
- Keep R99/R102 source acceptance blocked.

Only after that should a runtime alignment branch be considered.
