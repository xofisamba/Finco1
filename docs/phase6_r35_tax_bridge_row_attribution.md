# Phase 6 R35 Tax Bridge Row Attribution

## Purpose

This diagnostic branch attributes the remaining TUHO taxable-income-before-losses gap after R34 fiscal reintegration and loss-window semantics were isolated.

Runtime behavior changed: no. The branch creates a reporting workbook only and does not wire the vintage loss engine into the tax bridge.

Workbook:

```text
reports/phase6_tuho_r35_row_attribution.xlsx
```

## Executive Finding

R34 is not the remaining driver. Across 60 operating periods, the R34 delta is effectively zero.

The R35 gap is upstream, mostly in the EBT construction path:

| Driver | Total contribution |
| --- | ---: |
| SHL interest gross/net/timing | +10,347.3 kEUR |
| Book/tax depreciation timing | +2,302.2 kEUR |
| OPEX/local tax/minor row timing | -733.5 kEUR |
| Senior interest timing/basis | +355.4 kEUR |
| R34 fiscal reintegration | 0.0 kEUR |
| Other/unmapped minor rows | -55.0 kEUR |
| Total R35 delta | +12,216.4 kEUR |

The current R67 residual should therefore be treated as a tax-basis row ownership issue, not a loss-window issue alone.

## Period Clusters

Largest R35 deltas:

| op_idx | R35 delta | Suspected driver |
| ---: | ---: | --- |
| 0 | +2,024.9 kEUR | SHL interest gross/net/timing |
| 23 | +1,506.3 kEUR | SHL interest gross/net/timing |
| 21 | +1,426.8 kEUR | SHL interest gross/net/timing |
| 59 | -1,340.7 kEUR | book/tax depreciation timing |
| 58 | -1,318.9 kEUR | book/tax depreciation timing |
| 57 | -1,317.7 kEUR | book/tax depreciation timing |
| 56 | -1,296.2 kEUR | book/tax depreciation timing |
| 55 | -1,295.7 kEUR | book/tax depreciation timing |
| 54 | -1,274.6 kEUR | book/tax depreciation timing |
| 49 | -1,274.4 kEUR | book/tax depreciation timing |

The early positive deltas point to the Python taxable-income bridge missing or understating the full Excel gross SHL interest path in loss years. The late negative deltas point to depreciation timing and book-versus-tax row ownership.

## Evidence Table

The workbook contains:

- `Summary`
- `R35 Attribution`
- `Upstream Rows`
- `Loss Rows R36-R41`
- `CIT Rows R43-R44`
- `Largest R35 Deltas`
- `Suspected Drivers`

`R35 Attribution` reconciles:

```text
R35 delta =
  revenue delta
+ OPEX delta
+ depreciation delta
+ senior interest delta
+ SHL interest delta
+ R34 delta
+ other/unmapped delta
```

The reconciliation proves R34 is already calibrated and the residual is before loss usage.

## Row Ownership Assessment

| Row | Finding | Recommended owner |
| --- | --- | --- |
| R8 Revenue | Immaterial delta | Revenue runtime output |
| R10 OPEX | Secondary mismatch | OPEX/P&L row ownership |
| R13 Depreciation | Material timing mismatch | Depreciation ledger and P&L bridge |
| R24 Senior interest | Smaller residual | Senior debt interest bridge |
| R27 SHL interest | Largest driver | SHL/tax bridge P&L ownership |
| R30 Financial earnings | Follows R24/R27 | Financial statements P&L assembly |
| R32 EBT | Gap exists before losses | P&L bridge |
| R34 Fiscal reintegration | Calibrated | Interest limitation engine |
| R35 Taxable income before losses | Still high in loss years | Tax bridge row attribution |
| R36-R41 Loss rows | Not the primary remaining source | Loss engine/vintage workstream |
| R43/R44 CIT | Downstream of R35/R36-R41 | Tax bridge |
| R67 Cash CIT | Downstream of annual timing and tax base | Tax bridge |
| R69 FCF banks | Downstream; not ready as R99 source | PF cash waterfall |

## Conclusion

The remaining R35 issue is after EBT construction and before loss carry-forward. It is driven mainly by:

1. SHL interest gross/net/timing treatment.
2. Book/tax depreciation timing.
3. Smaller OPEX/local-tax/minor row differences.

R99/R102 remains blocked. Promoting the runtime source before R35 ownership is resolved would move a known tax-basis mismatch into SHL/distribution logic.

## Recommended Next Branch

`phase6-r35-row-fix-design`

Recommended scope:

- design SHL interest row ownership for P&L R27 and tax bridge R35;
- design book depreciation versus tax depreciation ownership;
- keep R99/R102 audit-only;
- keep default runtime behavior unchanged.
