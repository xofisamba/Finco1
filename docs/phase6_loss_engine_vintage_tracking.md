# Phase 6 Loss Engine Vintage Tracking

## Summary

This branch prepares the offline loss carry-forward engine for final R67 calibration by making the FIFO model explicitly vintage based. It does not wire the engine into the runtime tax bridge, does not change default runtime behavior, and does not accept R99/R102 as a runtime source.

## Algorithm

Each loss bucket now carries its own vintage metadata:

| Field | Meaning |
| --- | --- |
| `source_period_index` | Period where the loss was generated, or `None` for opening losses. |
| `generated_loss_keur` | Original loss amount for the vintage. |
| `remaining_loss_keur` / `amount_keur` | Unused amount remaining in the vintage. |
| `expiry_period_index` | First period where the bucket is no longer usable. |
| `periods_remaining` | Audit-friendly remaining periods label. |
| `source_label` | Optional source/audit label. |

The period algorithm is:

1. Remove expired opening buckets before any loss usage.
2. If taxable income before losses is positive, consume oldest valid buckets first.
3. Retain partially used buckets with their original vintage metadata.
4. If taxable income before losses is negative, create a new current-period bucket.
5. Current-period generated losses are not used in the same period.
6. Taxable profit after losses is never negative.

For runtime-safety, stricter pre-use expiry is explicit through
`expire_before_use=True`. The existing default remains unchanged so current
flag-on diagnostics keep their previously approved totals until a later branch
wires the vintage engine into the tax bridge deliberately.

## Window Modes

The engine uses `LossCarryforwardConfig.duration_periods`.

| Mode | Configuration | Result |
| --- | --- | ---: |
| Croatia tax-law semiannual | `duration_years=5`, `periods_per_year=2` | 10 periods |
| Excel compatibility | `explicit_override_periods=5` | 5 periods |
| Annual tax-law | `duration_years=5`, `periods_per_year=1` | 5 periods |

No hardcoded five-period or ten-period behavior is used outside fixtures/tests.

## TUHO Scenario Result

The TUHO sensitivity fixture preserves the previous quantified window finding while proving it through vintage expiry rather than a single pooled loss balance.

| Scenario | Window | CIT total | Losses used | Expired losses |
| --- | ---: | ---: | ---: | ---: |
| Excel compatibility | 5 periods | 38,240.9 kEUR | 0.0 kEUR | 3,670.6 kEUR |
| Croatia tax-law-correct | 10 periods | 37,580.2 kEUR | 3,670.6 kEUR | 0.0 kEUR |
| Difference |  | -660.7 kEUR | +3,670.6 kEUR | -3,670.6 kEUR |

The 660.7 kEUR CIT delta remains the window-semantics effect. The unresolved R67 residual is still about 1.49m kEUR and requires R35 row attribution and tax-basis reconciliation.

## Runtime Safety

Runtime behavior changed: no.

This branch changes only the offline loss engine and its tests/docs. It does not:

- wire into `app/waterfall_core.py` or `app/waterfall_runner.py`;
- add `ProjectInfo` flags;
- opt in project factories;
- accept R99/R102 as runtime source;
- enable SHL FCF;
- change revenue, OPEX, senior debt, SHL, or construction formulas.

## Remaining Blockers

R99 remains blocked because the loss-window issue explains only part of the R67 residual. The next branch should address `phase6-r35-tax-bridge-row-attribution`, including:

- R32/R35 taxable income construction;
- book versus tax depreciation ownership;
- local tax/WHT/minor tax rows;
- operating loss generation timing.
