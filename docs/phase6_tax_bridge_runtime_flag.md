# Phase 6 Tax Bridge Runtime Flag

## Purpose

This branch adds a default-off runtime tax bridge flag. It promotes the existing financial statements tax bridge cash-tax timing into runtime cash-tax fields only when explicitly enabled for TUHO.

The default model path remains legacy.

## Flag Behavior

Flag:

`ProjectInfo.use_tax_bridge_engine: bool = False`

Behavior:

- `False`: legacy tax behavior is unchanged.
- `True`: TUHO uses the tax bridge annual H2 cash-tax timing as runtime cash tax.
- Unsupported projects raise `ValueError`.
- Oborovo remains blocked.

The flag is not enabled in project factories.

## TUHO Runtime Behavior

For TUHO flag-on runs:

- accrued CIT remains the existing audited `tax_keur` / `cit_accrual_audit_keur`
- H1 cash tax is `0`
- H2 cash tax is `current period CIT + previous H1 CIT`
- `corporate_tax_cash_keur` and `cash_tax_current_period_audit_keur` use that positive cash-tax amount
- `cf_after_tax_keur` is updated to `EBITDA - tax bridge cash tax`
- C1d R69/R84/R99/R102 audit fields are recomputed to measure the downstream impact

The R99/R102 values remain audit fields. They are not accepted as runtime source of truth.

## TUHO Results

Current diagnostic target:

- Excel R67 total: `-38,240.9 kEUR`
- Python Excel-style H2 diagnostic: `-39,639.7 kEUR`
- residual gap: `-1,398.7 kEUR`

The residual remains a tax-basis mapping gap, not a payment-timing gap.

## Oborovo Guard

Oborovo flag-on raises a clear error. Oborovo tax bridge runtime support should wait for fixture-backed tax-basis evidence.

## R99/R102 Status

R99/R102 remains blocked as a runtime source.

This branch only measures the R99/R102 movement caused by replacing cash tax with the tax bridge annual H2 timing. It does not:

- accept R99/R102
- enable SHL FCF waterfall
- rewrite distribution-account logic
- change project factories

## Remaining Gaps

- TUHO tax-basis residual of about `-1.3m kEUR`
- tax depreciation and SHL interest deductibility still need mapped tax-basis ownership
- Oborovo tax bridge fixtures are not yet proven
- R99/R102 cannot be promoted until tax bridge and PF cash waterfall reconcile

## Next Branch

Recommended next branch:

`phase6-tax-bridge-tuho-tax-basis-runtime-calibration`
