# Phase 6 Loss Engine Runtime Flag

## Overview

Branch `phase6-loss-engine-runtime-flag` wires the vintage loss carry-forward engine (`domain/tax/loss_carryforward.py`) into the TUHO-WIND-1 tax bridge runtime path behind the existing `ProjectInfo.use_tax_bridge_engine` flag.

The change is **minimal and additive**: it replaces the generic default `LossCarryforwardConfig()` (which had `expire_before_use=False` and `country_template="generic"`) with an explicit Croatia tax-law-correct configuration, without altering any other behavior.

## Runtime Flag Behavior

| Flag state | Project | Behavior |
|---|---|---|
| `use_tax_bridge_engine=False` | TUHO | **Bit-identical to main** — legacy tax engine untouched |
| `use_tax_bridge_engine=False` | Oborovo | **Bit-identical to main** — legacy tax engine untouched |
| `use_tax_bridge_engine=True` | TUHO-WIND-1 | Vintage loss engine active, Croatia 10-period semiannual mode |
| `use_tax_bridge_engine=True` | Oborovo | `ValueError` (existing guard preserved) |

## TUHO Tax-Law-Correct 10-Period Mode

When `use_tax_bridge_engine=True` and project is TUHO-WIND-1, the runtime uses:

```python
loss_config = LossCarryforwardConfig(
    duration_years=5,
    periods_per_year=2,
    country_template="croatia",
    expire_before_use=True,
)
```

This implements:
- **5-year rolling loss window** (Croatia corporate tax law)
- **Semiannual periods × 2 = 10-period duration** (Croatia tax-law-correct)
- **FIFO per vintage with `expire_before_use=True`** (buckets expire at start of period `expiry_period_index`, not N+∞)
- **No single-pool no-expiry behavior**

## Excel Compatibility Mode

Excel compatibility mode (`LossCarryforwardConfig.excel_compatibility(override_periods=5)`) is preserved as a non-default diagnostic/config override only. It is **not** the default runtime mode. This branch does not change the Excel compatibility mode behavior.

## Before / After R67

R67 is the annual H2 cash-tax diagnostic (cumulative CIT accrual minus prior period cash tax).

**Before (generic config, `expire_before_use=False`):**
- `PYTHON_TAX_BRIDGE_R67_DIAGNOSTIC_TOTAL_KEUR = -36,091.62`

**After (Croatia config, `expire_before_use=True`):**
- `PYTHON_TAX_BRIDGE_R67_DIAGNOSTIC_TOTAL_KEUR = -36,284.24`

**Delta:** +192.62 kEUR more cash tax collected (closer to Excel's -38,240.92) because losses now correctly expire after 10 periods instead of surviving indefinitely.

The Croatia config reduces the residual vs Excel R67 from 2,149 kEUR to 1,957 kEUR — an improvement, but a remaining gap exists due to other attribution differences (R34 fiscal reintegration calibration, SHL gross bridge, book depreciation bridge) that are handled in separate branches.

## Before / After Loss Usage

The `expire_before_use=True` flag ensures:
1. Buckets are checked for expiry **at the start of each period** before being used to offset taxable income
2. A bucket with `expiry_period_index=10` is **not** available in period 10 or later
3. This eliminates the no-expiry pool behavior where `expire_before_use=False` let old buckets survive indefinitely

The closing loss audit field now correctly reflects the shrinking loss pool as vintages age out.

## Remaining Residual

The remaining R67 residual (~1,957 kEUR) is attributable to factors outside the scope of this branch:
- R34 fiscal reintegration calibration (handled in phase6 R35 attribution)
- SHL gross accrued bridge (closed)
- Book depreciation bridge (closed)
- CIT H2 annual trigger — not yet implemented in this branch

## Why R99 Remains Blocked

R99 (`fcf_for_distribution`) and R102 (`fcf_for_shl`) are computed in `_apply_tuho_tax_bridge_runtime_cash_tax` as **audit fields only**. The `use_tuho_r99_input_engine` flag is **not changed** by this branch and remains `False`. The bridge computes `r99 == r102` as a mirror relationship, but does not accept either as a runtime input source.

The R99/R102 runtime source acceptance is tracked separately and is not part of this branch's scope.

## Scope Discipline

**Allowed files changed:**
- `app/waterfall_core.py` — Croatia config for loss engine
- `tests/test_loss_engine_runtime_flag.py` — new test suite
- `tests/test_tax_bridge_runtime_flag.py` — R67 constants updated to match new Croatia config output

**Hard rejection applied to:**
- ❌ R99/R102 runtime source acceptance
- ❌ SHL FCF opt-in
- ❌ Project factory opt-in
- ❌ Revenue/OPEX/senior/SHL/construction formula changes
- ❌ Depreciation bridge changes
- ❌ SHL gross bridge changes
- ❌ UI/cache/persistence changes
- ❌ Unrelated cleanup/refactors

## Next Branch Recommendation

`phase6-cit-h2-annual-trigger`

This branch should wire the CIT H2 annual cash-tax trigger into the tax bridge runtime, so that CIT is only paid in H2 of each year (matching the Excel `r67_excel_style_cash_tax_diagnostic` logic currently used as audit-only). This will further reduce the R67 residual and bring the Python model closer to Excel cash-tax timing.