# Phase 6 Tax Bridge Consumes Interest Limitation

## Purpose

This branch wires the offline interest limitation engine into the existing
default-off `use_tax_bridge_engine` runtime tax bridge path for TUHO only.
Default project behavior remains unchanged.

The change is intentionally narrow:

- `use_tax_bridge_engine=False`: legacy tax and cashflow behavior is unchanged.
- `use_tax_bridge_engine=True` and `project.code == "TUHO-WIND-1"`: the tax
  bridge consumes the committed Excel R34 fiscal reintegration fixture through
  `domain.tax.interest_limitation`.
- Oborovo remains guarded and raises `ValueError` when the runtime tax bridge
  flag is enabled.
- R99/R102 remains audit-only and is not accepted as a runtime cash source.
- SHL FCF waterfall remains off unless independently configured by its own flag.

## R34 Integration

The TUHO tax bridge path now builds per-period fiscal reintegration from the
full-horizon Excel extraction:

`tests/fixtures/interest_limitation/tuho_interest_limitation_fixture.json`

The runtime flag path feeds each fixture row into:

`compute_interest_limitation_period(...)`

using:

- `gross_shl_interest_r27`
- `ebitda`
- `thin_cap_gate_r45`
- `r59_ratio_adjustment`
- `InterestLimitationSignConvention.SUBTRACT_FROM_TI`

The resulting `fiscal_reintegration_keur` is written to
`WaterfallPeriod.fiscal_reintegration_audit_keur` and used as the tax bridge
R34 adjustment when recomputing tax audit fields.

The committed TUHO fixture produces cumulative R34 of:

`-9,242.742 kEUR`

The final 61st Python operating stub period has no Excel R34 fixture and is
therefore assigned zero fiscal reintegration.

## Tax Bridge Runtime Behavior

When the TUHO flag is on, the bridge recomputes:

- taxable income before losses
- loss usage using the existing tax engine behavior
- taxable profit after losses
- accrued CIT
- Excel-style annual H2 cash tax diagnostic
- runtime `corporate_tax_cash_keur`
- R69/R84/R98/R99/R100/R102 audit fields

This does not re-run the senior debt schedule, SHL schedule, or distributions.
Those remain unchanged in this branch. R99/R102 fields are refreshed only as
measurement outputs.

## TUHO R67 Before / After

| Measure | Value kEUR |
| --- | ---: |
| Excel R67 cash tax | -38,240.9 |
| Legacy runtime cash tax convention | -20,140.2 |
| Flag-on tax bridge with R34 | -32,091.9 |

The tax bridge plus R34 moves runtime cash tax materially closer to Excel R67
than the legacy runtime cash-tax convention, but it does not yet achieve parity.

## R99/R102 Impact

With the flag on, R99/R102 audit totals move because cash tax changes. These
fields remain diagnostics only:

- no R99/R102 source is accepted
- no SHL FCF waterfall source is accepted
- no factory opt-in is added

## Oborovo Guard

Oborovo remains blocked for runtime tax bridge consumption. Its R34 sign
convention is supported by the offline interest limitation engine, but runtime
tax bridge consumption is TUHO-only until Oborovo tax bridge parity fixtures and
cash-tax timing are proven.

## Remaining Blockers

- Rolling 5-year loss carry-forward is not implemented in the runtime tax
  bridge.
- Book depreciation and balance-sheet depreciation ownership are still separate
  Phase 6 workstreams.
- R99/R102 cannot become runtime source until tax bridge and PF cash waterfall
  reconcile within tolerance.
- SHL FCF waterfall remains fixture-backed until the runtime R99/R102 source is
  accepted in a later branch.

## Next Branch

Recommended next branch:

`phase6-loss-carryforward-rolling-engine`
