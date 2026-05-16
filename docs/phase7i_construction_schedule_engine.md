# Phase 7I Construction Schedule Engine

This PR adds an offline construction funding bridge. It does not wire
construction funding into runtime waterfall calculations.

## Scope

Added package:

- `domain/construction/config.py`
- `domain/construction/capex_schedule.py`
- `domain/construction/funding_allocation.py`
- `domain/construction/idc_calculator.py`
- `domain/construction/engine.py`
- `domain/construction/result.py`
- `domain/construction/templates/tuho.py`
- `domain/construction/templates/oborovo.py`

Added tests:

- `tests/test_construction_capex_schedule.py`
- `tests/test_construction_funding_allocation.py`
- `tests/test_construction_idc_calculator.py`
- `tests/test_tuho_construction_schedule_bridge.py`
- `tests/test_oborovo_construction_schedule_bridge.py`

No runtime, waterfall, revenue, OPEX, tax, SHL, senior debt, project factory,
cache, or UI code is changed.

## Engine Design

The engine has three separate steps:

1. Build monthly construction uses.
2. Allocate funding with a source waterfall.
3. Calculate SHL IDC and senior IDC.

The result is a diagnostic bridge object with monthly rows and totals. It is
intended for construction schedule parity work before runtime integration.

## Monthly Uses

Supported profile types:

- `linear`
- `custom`

For this PR, TUHO and Oborovo use custom monthly construction cash
requirements from the Phase 7I discovery document.

## Funding Allocation

The default funding logic is source-waterfall, not pro-rata:

1. Equity shares
2. SHL
3. Junior / carbon fund
4. Senior debt

For each month, the allocator:

- calculates cumulative uses,
- allocates cumulative funding through the source caps,
- computes monthly draws as current cumulative funding less prior cumulative
  funding,
- validates that monthly funding equals monthly uses.

## SHL IDC

SHL IDC uses the Excel-observed full-source elapsed compound method:

```text
SHL IDC = SHL draw * ((1 + SHL rate) ^ elapsed_years - 1)
```

This is intentionally not draw-by-draw monthly SHL IDC.

## Senior IDC

Senior IDC uses a monthly cumulative-balance method:

```text
senior IDC month t =
    (senior interest rate + base rate t)
    * prior cumulative senior draw balance
    * monthly interest period fraction t
```

The discovery identified Excel base-rate and day-count details that are not yet
fully modeled. The TUHO and Oborovo templates therefore expose senior interest
rate and period fractions as inputs. The current template rates are effective
rates calibrated to the discovered Excel senior IDC totals:

- TUHO senior IDC target: 1,519.564 kEUR
- Oborovo senior IDC target: 1,086.032 kEUR

This keeps the uncertainty explicit while avoiding any runtime impact.

## TUHO Template

TUHO construction assumptions:

- Construction months: 18
- Construction start proxy: 30-Jun-2028
- COD proxy: 30-Dec-2029
- Total construction cash requirement: 72,994.450 kEUR
- Equity shares: 500.000 kEUR
- SHL draw: 29,135.176 kEUR
- Junior / carbon fund: 0.000 kEUR
- Senior debt draw: 43,359.274 kEUR
- SHL rate: 8.0%
- SHL IDC target: 3,568.688 kEUR
- Opening SHL target: 32,703.864 kEUR
- Senior IDC target: 1,519.564 kEUR

The monthly uses are front-loaded. Month 1 funds equity shares and most of the
SHL. Month 3 completes SHL funding and starts senior debt funding.

## Oborovo Template

Oborovo construction assumptions:

- Construction months: 12
- Construction start proxy: 29-Jun-2029
- COD proxy: 29-Jun-2030
- Total construction cash requirement: 57,973.041 kEUR
- Equity shares: 500.000 kEUR
- SHL draw: 14,620.774 kEUR
- Junior / carbon fund: 0.000 kEUR
- Senior debt draw: 42,852.267 kEUR
- SHL rate: 8.0%
- SHL IDC target: 1,169.662 kEUR
- Opening SHL target: 15,790.436 kEUR
- Senior IDC target: 1,086.032 kEUR

Oborovo exhausts equity shares and SHL in month 1. Senior debt starts in month
1 for the residual construction funding and then funds the remaining months.

## Current Parity

| Metric | TUHO target | TUHO engine | Oborovo target | Oborovo engine |
|---|---:|---:|---:|---:|
| Construction months | 18 | 18 | 12 | 12 |
| Total uses | 72,994.450 | 72,994.450 | 57,973.041 | 57,973.042 |
| Equity draw | 500.000 | 500.000 | 500.000 | 500.000 |
| SHL draw | 29,135.176 | 29,135.176 | 14,620.774 | 14,620.774 |
| Senior draw | 43,359.274 | 43,359.274 | 42,852.267 | 42,852.267 |
| SHL IDC | 3,568.688 | 3,568.688 | 1,169.662 | 1,169.662 |
| Opening SHL | 32,703.864 | 32,703.864 | 15,790.436 | 15,790.436 |
| Senior IDC | 1,519.564 | 1,519.564 | 1,086.032 | 1,086.032 |

Oborovo total uses differ by 0.001 kEUR because the discovered monthly values
sum to 57,973.042 while the rounded workbook total is 57,973.041.

## Non-Goals

This PR does not:

- change runtime waterfall behavior,
- change opening senior or SHL balances in project factories,
- change senior repayment or sculpting,
- change SHL operating waterfall,
- change revenue, OPEX, tax, or R99 logic,
- introduce construction IDC into runtime cash routing.

## Recommended Next Branch

Recommended next branch:

```text
phase7i-construction-runtime-flag
```

Suggested scope for that later branch:

- add a default-off construction schedule feature flag,
- create a runtime adapter for supported projects only,
- prove flag-off equivalence for TUHO and Oborovo,
- prove flag-on opening balance parity in isolated tests,
- keep senior repayment, SHL waterfall, revenue, OPEX, and tax behavior out of
  scope unless explicitly approved.
