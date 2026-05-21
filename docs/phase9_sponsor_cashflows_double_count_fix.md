# Phase 9 Sponsor Cashflows Double-Count Fix

## Purpose

This branch fixes a reporting-layer sponsor cashflow bug identified in PR #158 and reconfirmed in PR #161.

Runtime waterfall behavior changed: no. The branch does not change `domain/waterfall/waterfall_engine.py`, SHL repayment mechanics, DistributionAccount logic, R99/R102 logic, project factories, SeniorDebtSizing, TaxBridge, Oborovo runtime behavior, or runtime flags.

## Bug Mechanism

For `shl_plus_dividends`, the waterfall already builds `equity_cf_per_period` as the intended sponsor/equity cashflow stream:

```text
while SHL outstanding: SHL cash interest
after SHL repayment: dividends/distributions
```

`build_sponsor_cashflows()` then added `shi` and `shp` again:

```text
sponsor_cf = equity_cf + shi + shp
```

That created a double-count of paid SHL cashflows and inflated sponsor/equity IRR.

## Fixed Behavior

For SHL-specific methods, the selected cashflow stream is authoritative:

```text
shl_interest_only: equity_cf_per_period is already SHL interest + principal
shl_plus_dividends: equity_cf_per_period is already the selected SHL/dividend stream
```

The fixed behavior is:

```text
sponsor_cf = equity_cf
```

for `shl_interest_only` and `shl_plus_dividends`.

Existing semantics for non-SHL-specific methods are preserved.

## Before Versus After Example

| Scenario | IRR |
| --- | ---: |
| Corrected stream | 15.10% |
| Old double-count stream | 17.81% |
| Inflation removed | 2.71pp |

The project-specific confirmed diagnostic remains:

| Item | Result |
| --- | ---: |
| Corrected model equity IRR | about 15.13% |
| Excel target | 11.61% |
| Double-count bug contribution | about +2.69pp |
| SHL IDC investment-base contribution | about +1.17pp |

## Affected Methods

| Method | Behavior |
| --- | --- |
| `shl_plus_dividends` | Fixed: no duplicate `shi` / `shp` add-on |
| `shl_interest_only` | Preserved: already no double-count |
| `equity_only` / `combined` | Preserved: existing distribution-plus-SHL semantics remain unchanged |

## Why This Is Reporting-Layer Only

The fix only changes how sponsor cashflows are assembled for return metrics. It does not alter:

- waterfall period calculations
- SHL cash interest
- SHL principal repayment
- SHL balance
- DSCR
- lockup
- DistributionAccount routing
- tax bridge values
- R99/R102 status
- project IRR

## Remaining Known Gap

After removing the double-count bug, the corrected model equity IRR remains above the Excel target:

```text
Corrected model equity IRR: about 15.13%
Excel target: 11.61%
Remaining gap: about 3.52pp
```

Known remaining contributors include SHL IDC investment-base treatment and unresolved G20/R99/R102 items.

## G20 And R99 Status

G20 remains BLOCKED.

R99/R102 runtime promotion is NOT approved and remains blocked.
