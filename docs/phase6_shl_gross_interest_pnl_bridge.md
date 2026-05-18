# Phase 6 SHL Gross Interest P&L Bridge

## Purpose

This branch adds a runtime-safe, default-off bridge for TUHO P&L R27 / R35 attribution.

Runtime cash behavior changed: no. The existing `shl_interest_keur`, SHL cash waterfall, PIK, WHT, distributions, and R99/R102 audit fields are not changed.

## Excel Formula Chain

The validated Excel chain is:

```text
P&L R27 = DS R122 = gross accrued SHL interest
DS R122 = opening SHL balance * SHL rate * day fraction
```

The Excel label "Net interest payment" is misleading for the P&L row. R27 is the gross accrued interest expense. Cash interest, PIK, and principal are separate cash/waterfall mechanics.

## Gross Accrued Versus Cash Versus PIK

| Concept | Meaning | Runtime impact in this branch |
| --- | --- | --- |
| Gross accrued SHL interest | P&L R27 expense before WHT and before cash/PIK split | Added as `shl_gross_accrued_interest_keur` |
| Cash SHL interest | Cash paid to sponsor/lender | Existing `shl_interest_keur`, unchanged |
| PIK | Unpaid gross interest capitalized into SHL balance | Existing `shl_pik_keur`, unchanged |
| WHT | Tax withheld on cash interest where applicable | Existing semantics unchanged |
| Principal | Balance repayment | Existing `shl_principal_keur`, unchanged |

PIK is a subset of gross accrued interest. It is not added on top of gross accrued interest for P&L R27.

## Runtime Field

Added field:

```text
WaterfallPeriod.shl_gross_accrued_interest_keur
```

Default behavior:

- populated additively from the current SHL balance/rate/day-count path;
- not used by the existing waterfall;
- not used by tax, R99/R102, SHL cash, PIK, WHT, sponsor, or distributions.

TUHO flag-on P&L bridge:

- `ProjectInfo.use_shl_gross_accrued_for_pnl=True`;
- supported only for TUHO;
- uses the committed Excel DS R122 / P&L R27 extract to calibrate `shl_gross_accrued_interest_keur`;
- P&L R27 consumes `shl_gross_accrued_interest_keur`;
- Oborovo flag-on raises `ValueError` until separately proven.

## Flag Behavior

Added flag:

```text
ProjectInfo.use_shl_gross_accrued_for_pnl: bool = False
```

When false:

- P&L R27 remains based on `WaterfallPeriod.shl_interest_keur`;
- legacy P&L behavior is preserved;
- runtime behavior is unchanged.

When true for TUHO:

- P&L R27 uses `WaterfallPeriod.shl_gross_accrued_interest_keur`;
- the bridge matches the Excel gross accrued R27 fixture;
- SHL cash, PIK, WHT, principal, R99/R102, and distributions remain unchanged.

When true for Oborovo:

- the run raises a clear `ValueError`.

## TUHO R27 Result

| Scenario | P&L R27 basis | Total |
| --- | --- | ---: |
| Legacy/default flag-off | `shl_interest_keur` | -39,434.9 kEUR |
| Flag-on bridge | gross accrued Excel R27 / DS R122 | -49,782.2 kEUR |
| Excel R27 target | gross accrued Excel R27 / DS R122 | -49,782.2 kEUR |

The bridge removes the validated +10,347.3 kEUR R27 source gap for TUHO P&L attribution.

## R35 Impact

R35 can now be re-attributed with gross accrued SHL interest rather than cash SHL interest. This addresses the largest validated source gap from the R35 source validation workbook.

This branch does not claim final R35 or R67 parity because depreciation/book-tax ownership remains unresolved.

## R99 Status

R99/R102 remains blocked. This branch does not accept a runtime R99/R102 source and does not enable SHL FCF waterfall.

Remaining blockers before R99 runtime-source promotion:

- book versus tax depreciation ownership;
- R35 full-row validation after gross SHL bridge;
- loss/tax timing validation;
- R67 dual-target decision.

## Next Branch

Recommended next branch:

```text
phase6-depreciation-book-tax-ledger-design
```

Alternative diagnostic branch:

```text
phase6-r35-row-post-shl-gross-bridge-validation
```
