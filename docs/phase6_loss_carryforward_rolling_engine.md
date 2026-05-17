# Phase 6 Loss Carry-Forward Rolling Engine

## Purpose

This branch adds a standalone 5-year rolling tax loss carry-forward engine and
uses it only inside the already default-off TUHO tax bridge path.

Default runtime behavior is unchanged:

- `use_tax_bridge_engine=False` keeps the legacy tax path.
- project factories remain flag-off.
- R99/R102 remains audit-only.
- SHL FCF remains off unless separately enabled.
- revenue, OPEX, senior debt, SHL, and construction formulas are unchanged.

## Algorithm

`domain.tax.loss_carryforward` tracks tax losses as FIFO buckets.

Each bucket contains:

- loss amount in kEUR
- remaining carry-forward periods
- optional source period index

For each period:

1. Start from signed taxable income before losses.
2. If taxable income is positive, use oldest loss buckets first.
3. If taxable income is negative, create a new loss bucket.
4. Age unused opening buckets by one period.
5. Expire buckets whose remaining period count reaches zero.
6. Taxable profit after losses is never negative.

The default configuration is:

- 5 years
- 2 semiannual periods per year
- FIFO usage

## Excel Row Mapping

| Excel row | Meaning | Engine field |
| --- | --- | --- |
| R36 | Losses N-1 | `losses_n_1_keur` |
| R37 | Allocated losses | `allocated_losses_keur` |
| R38 | Losses N | `losses_n_keur` |
| R39 | Carriable losses | `carriable_losses_keur` |
| R41 | Taxable Profit N | `taxable_profit_after_losses_keur` |

The TUHO tax bridge flag-on path writes these results back to the existing
period audit fields:

- `tax_loss_opening_audit_keur`
- `tax_loss_used_audit_keur`
- `tax_loss_closing_audit_keur`
- `taxable_profit_after_losses_audit_keur`

## TUHO R67 Before / After

| Measure | Value kEUR |
| --- | ---: |
| Excel R67 target | -38,240.9 |
| Legacy runtime cash tax | -20,140.2 |
| TUHO flag-on with R34 + rolling losses | -36,091.6 |

The remaining R67 residual is approximately:

`+2,149.3 kEUR`

The flag-on result is materially closer to Excel than legacy runtime cash tax,
but it is not yet accepted as a complete R99/R102 runtime source.

## R99/R102 Status

R99/R102 fields are recomputed as audit outputs because cash tax changes under
the TUHO tax bridge flag. They remain diagnostics only:

- no runtime source accepted
- no SHL FCF source accepted
- no factory opt-in

## Remaining Gaps

- Opening tax-loss bucket age is treated as a TUHO bridge assumption.
- Excel tax-basis and book/tax depreciation ownership still need the next tax
  bridge calibration pass.
- R99/R102 cannot be promoted until PF cash waterfall and tax bridge diagnostics
  reconcile within tolerance.

## Next Branch

Recommended next branch:

`phase6-r99-runtime-source-from-tax-bridge`
