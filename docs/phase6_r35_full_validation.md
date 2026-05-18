# Phase 6 R35 Full Validation

## Purpose

This diagnostic branch reruns TUHO R35 attribution after both default-off P&L attribution bridges are available:

- SHL gross accrued P&L bridge
- book depreciation P&L bridge

Runtime behavior changed: no. The branch creates a workbook and tests only. It does not change runtime formulas, add flags, wire the loss engine into the tax bridge, accept R99/R102 as a runtime source, enable SHL FCF, or opt in factories.

Workbook:

```text
reports/phase6_tuho_r35_full_validation.xlsx
```

## Before And After Sequence

| Stage | Cumulative R35 delta |
| --- | ---: |
| Before SHL bridge | +12,216.4 kEUR |
| After SHL gross accrued bridge | +1,869.1 kEUR |
| After SHL gross + book depreciation bridges | -433.1 kEUR |

The two largest validated source gaps are now closed for attribution:

| Driver | Prior delta | Current status |
| --- | ---: | --- |
| SHL interest gross/net/timing | +10,347.3 kEUR | Closed |
| Book/tax depreciation timing | +2,302.2 kEUR | Closed |
| R34 fiscal reintegration | 0.0 kEUR | Calibrated |

## Remaining R35 Residual

| Metric | Result |
| --- | ---: |
| Final cumulative R35 residual | -433.1 kEUR |
| Max period delta | 152.8 kEUR |
| Material periods above 100 kEUR | 7 |

The remaining residual is small compared with the original R35 gap, but it is not a runtime-source acceptance gate yet because several period-level deltas remain above 100 kEUR.

## Remaining Driver Ranking

| Remaining driver | Delta |
| --- | ---: |
| OPEX/local-tax/minor rows | -733.5 kEUR |
| Senior interest timing/basis | +355.4 kEUR |
| Other/unmapped | -55.0 kEUR |
| Total remaining residual | -433.1 kEUR |

R35 is now close enough to stop treating SHL and depreciation as the dominant blockers. The next work should focus on the remaining tax bridge sequence rather than reopening those closed attribution drivers.

## Workbook Structure

The workbook contains:

- `Summary`
- `R35 Bridge Progression`
- `Row Comparison`
- `Remaining Drivers`
- `Largest Deltas`
- `R99 Readiness`
- `Notes`

## Tolerance Assessment

| Gate | Status | Reason |
| --- | --- | --- |
| Cumulative R35 residual | Near target | -433.1 kEUR residual |
| Period-level materiality | Open | 7 periods remain above 100 kEUR |
| SHL R27 attribution | Passed | Gross accrued bridge closes R27 |
| Book R13 attribution | Passed | Book depreciation bridge closes R13 |
| R34 fiscal reintegration | Passed | R34 remains calibrated |
| R99 runtime source | Blocked | R99/R102 remains audit-only |

## Recommended Next Branch

Recommended next branch:

```text
phase6-loss-engine-runtime-flag
```

Rationale:

- SHL and book depreciation attribution are now closed.
- R35 residual is materially reduced.
- The remaining tax bridge path still needs default-off loss engine runtime wiring and CIT timing validation before R99/R102 can be reconsidered.

R99 readiness status: blocked.
