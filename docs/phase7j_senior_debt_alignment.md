# Phase 7J Senior Debt Alignment

This branch is senior-debt alignment work only. It does not implement SHL
`fcf_waterfall`, does not change revenue, OPEX, tax, R99, sponsor
distributions, or the senior repayment/sculpting engine.

## Current Debt Architecture

Runtime senior debt opening balance is currently controlled by the financing
inputs passed into the waterfall:

- `fixed_debt_keur` overrides sculpted debt when it is positive.
- If no fixed debt is supplied, the waterfall computes debt from DSCR/gearing
  sculpting.
- Senior IDC is passed separately as `idc_keur` for tax/fiscal reintegration
  behavior, not as an automatic addition to the senior opening balance.
- The operating repayment schedule starts in the first operating period.

For TUHO and Oborovo, the current project factories use fixed senior debt
anchors, so runtime opening senior principal is the manual fixed debt amount.

## Construction Diagnostic Comparison

The Phase 7I construction engine computes senior principal draw and senior IDC
separately. It does not currently capitalize senior IDC into runtime senior
debt.

| Project | Manual senior debt | Computed senior principal | Computed senior IDC | Computed senior incl. IDC | Manual minus principal | Manual minus incl. IDC |
|---|---:|---:|---:|---:|---:|---:|
| TUHO | 43,359.000 | 43,359.274 | 1,519.564 | 44,878.838 | -0.274 | -1,519.838 |
| Oborovo | 42,852.267 | 42,852.267 | 1,086.032 | 43,938.299 | 0.000 | -1,086.032 |

The user-provided TUHO review target of 45,878.837 kEUR is 1,000.000 kEUR
above the construction engine's principal-plus-IDC calculation
(43,359.274 + 1,519.564 = 44,878.838). This branch does not force that value
because doing so would fake parity without an identified source.

## What Was Aligned

This branch adds audit-only senior construction diagnostics to
`domain.construction.runtime_adapter`.

New diagnostic fields include:

- opening senior balance source,
- manual opening senior balance,
- computed construction senior principal draw,
- computed construction senior IDC,
- computed opening senior excluding IDC,
- computed opening senior including IDC,
- manual senior IDC value from CAPEX,
- opening balance deltas,
- IDC delta,
- repayment timing notes,
- COD transition notes.

When `use_construction_schedule_engine=True`, these diagnostics are attached to
the waterfall result through the existing construction diagnostic object. They
do not change runtime cash flows.

## Why Replacement Remains Blocked

Replacing runtime senior opening debt with construction outputs is not safe yet:

- Current fixed debt inputs already match construction senior principal within
  rounding.
- Senior IDC is already present in CAPEX/tax inputs as construction IDC.
- Adding computed senior IDC to `fixed_debt_keur` would change senior interest,
  principal, DSCR, DSRA, and distributions.
- It is not yet confirmed whether Excel treats senior IDC as capitalized into
  debt principal, a separately funded construction cost, or both in different
  statements.

Therefore, senior construction balances remain diagnostic-only.

## Debt Timing Review

Current runtime behavior:

- Debt opening timing: fixed senior debt is available at first operating period.
- Repayment start: first operating period.
- Interest accrual: period rate applied to opening balance for each operating
  period.
- Repayment frequency: semiannual operating periods.
- Partial construction periods: not represented in the operating senior
  schedule.
- Construction IDC accrual: modeled offline in the construction engine, not
  routed into runtime senior opening debt.

No repayment timing fix was implemented because the isolated safe change is not
yet identified. The diagnostic notes now make this visible period-by-period at
the construction/runtime boundary.

## Remaining Gaps

- Confirm whether Excel capitalizes senior IDC into senior opening debt or
  treats it as a separately funded construction cost.
- Resolve the TUHO 1,000 kEUR discrepancy between the review target
  45,878.837 kEUR and construction principal-plus-IDC 44,878.838 kEUR.
- Confirm Excel senior debt first repayment date and whether first operating
  interest uses exact actual-day construction/COD transition logic.
- Confirm whether senior commitment fees or bank fees should be part of opening
  senior debt, CAPEX, or tax-only construction reintegration.

## Recommended Next Branch

Recommended next branch:

```text
phase7j-senior-debt-opening-balance-policy
```

That branch should decide, with Excel row evidence, whether runtime senior debt
should use:

- manual principal only,
- principal plus senior IDC,
- principal plus senior IDC plus selected fees,
- or a fully explicit construction funding policy.

Until that policy is proven, senior debt alignment should remain diagnostic.
