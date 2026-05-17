# Phase 6 R35 Row Fix Design

## Executive Summary

The R35 row attribution branch proved that the remaining TUHO taxable-income-before-losses gap is upstream of loss carry-forward and after R34 fiscal reintegration. R34 is calibrated. The remaining R35 delta is dominated by row ownership issues:

| Driver | Total contribution |
| --- | ---: |
| SHL interest gross/net/timing | +10,347.3 kEUR |
| Book/tax depreciation timing | +2,302.2 kEUR |
| OPEX/local tax/minor row timing | -733.5 kEUR |
| Senior interest timing/basis | +355.4 kEUR |
| R34 fiscal reintegration | ~0.0 kEUR |

The minimal safe path is not to patch R35 directly. The model needs explicit ownership for gross accrued SHL interest and book-versus-tax depreciation rows, then the tax bridge can consume those inputs behind a later default-off runtime flag.

Runtime behavior changed in this branch: no. This is docs-only.

## SHL Interest Row Ownership

### Excel R27

Excel P&L R27 is gross accrued shareholder-loan interest. It is a P&L expense row and belongs in EBT before fiscal reintegration.

It should not be confused with:

- SHL cash interest paid;
- PIK-only movement;
- net SHL cash outflow;
- deductible interest after R34 limitation;
- SHL FCF waterfall service.

The current Python R35 bridge is not using an Excel-equivalent gross accrued SHL interest row consistently. The row attribution workbook shows this is the largest R35 driver, especially in early loss years.

### Recommended Ownership

| Concept | Owner | Consumer |
| --- | --- | --- |
| Gross accrued SHL interest schedule | SHL engine or isolated SHL audit bridge | Financial statements P&L R27 |
| Cash SHL interest paid | SHL cash waterfall | PF cash waterfall and cash distribution analysis |
| SHL PIK | SHL balance roll-forward | Balance Sheet and SHL diagnostics |
| Deductibility limitation | Interest limitation engine | Tax bridge R34 |
| R35 taxable income before losses | Tax bridge | Loss engine and CIT |

Recommended rule:

```text
P&L R27 = gross accrued SHL interest
Tax bridge starts from book EBT
R34 then applies fiscal reintegration / interest limitation
SHL FCF waterfall remains cash-only and separate
```

### Runtime Implication

The future implementation must expose gross accrued SHL interest as an auditable period-level row without changing cash waterfall mechanics. The SHL FCF waterfall must not become the source of P&L R27.

## Depreciation Row Ownership

### Excel Rows

Excel distinguishes book P&L depreciation and tax depreciation mechanics:

- P&L R13 should be book depreciation.
- Tax depreciation belongs in the tax bridge as a book-to-tax adjustment.
- R35 should not be built by substituting tax depreciation directly into book EBT unless that is explicitly proven to match the workbook.

The R35 attribution branch shows depreciation contributes about +2,302.2 kEUR to the R35 gap. Late-period deltas are dominated by depreciation timing, which points to book-versus-tax row ownership rather than loss-window mechanics.

### Recommended Ownership

| Concept | Owner | Consumer |
| --- | --- | --- |
| Book depreciation schedule | `domain/depreciation/` ledger | P&L R13, EBIT, EBT, Balance Sheet accumulated depreciation |
| Tax depreciation schedule | `domain/depreciation/` tax ledger | Tax bridge tax depreciation adjustment |
| Book-to-tax depreciation adjustment | Tax bridge | R35 taxable income before losses |
| Fixed asset roll-forward | Balance Sheet assembly | BS net fixed assets and accumulated depreciation |

Recommended rule:

```text
Book EBT = revenue - OPEX - book depreciation - financial earnings
Taxable income before losses = book EBT + explicit tax adjustments
Tax depreciation is consumed by the tax bridge, not by P&L R13
```

## Minimal Fix Sequence

### A. `phase6-shl-gross-interest-pnl-bridge`

Purpose:

- add offline/default-off gross accrued SHL interest bridge;
- compare Excel R27 vs Python gross accrued SHL interest;
- document cash interest, PIK, gross accrual, and deductible interest as separate rows.

Allowed scope:

- diagnostics;
- offline helper if needed;
- tests/docs/workbook.

Forbidden:

- SHL FCF opt-in;
- runtime tax bridge wiring;
- factory opt-in.

Acceptance:

- TUHO R27 gross accrued SHL interest bridge exists for 60 periods;
- R27 delta is quantified;
- no runtime behavior change.

### B. `phase6-depreciation-book-tax-ledger-design`

Purpose:

- design book and tax depreciation schedules as separate ledgers;
- define ownership of P&L R13, tax depreciation, accumulated depreciation, and BS fixed-asset roll-forward.

Acceptance:

- book depreciation and tax depreciation are explicitly separated;
- no runtime formula change.

### C. `phase6-depreciation-book-tax-offline-engine`

Purpose:

- implement offline book/tax depreciation schedules;
- compare Excel P&L book depreciation and tax depreciation rows;
- keep runtime unchanged.

Acceptance:

- TUHO book depreciation bridge exists;
- tax depreciation bridge remains protected;
- no waterfall/tax runtime wiring.

### D. `phase6-r35-row-runtime-flag`

Purpose:

- default-off runtime flag uses corrected R35 inputs;
- no R99/R102 source acceptance;
- no factory opt-in.

Acceptance:

- flag-off bit-identical;
- flag-on R35 within tolerance;
- R34 still calibrated;
- loss engine still not the source of truth unless explicitly enabled.

### E. `phase6-loss-engine-runtime-flag`

Purpose:

- wire vintage loss engine behind a default-off flag;
- support Excel compatibility target and tax-law-correct target.

Acceptance:

- flag-off bit-identical;
- Excel compatibility reproduces workbook loss behavior;
- tax-law-correct mode is available and clearly labeled.

### F. `phase6-r67-dual-target-validation`

Purpose:

- validate R67 against both canonical candidates:
  - Excel compatibility target;
  - tax-law-correct target.

Acceptance:

- sponsor/user decision is documented;
- R99 runtime-source promotion remains blocked until the selected target passes tolerance.

## R99 Readiness Policy

R99/R102 remains blocked until all of the following pass:

| Gate | Required status |
| --- | --- |
| R35 taxable income before losses | Within agreed tolerance |
| R34 fiscal reintegration | Already calibrated; must remain stable |
| Loss engine | Vintage behavior validated for selected target |
| CIT annual trigger | H2 cash-tax timing validated |
| R67 dual target | Excel compatibility and tax-law-correct impacts quantified |
| Runtime safety | Flag-off bit-identical |

No R99/R102 runtime source should be accepted while R35 row ownership remains unresolved.

## Forbidden Scope For Implementation Branches

Future implementation branches must not include:

- broad tax bridge rewrite;
- R99/R102 runtime source acceptance;
- SHL FCF opt-in;
- project factory opt-in;
- new flags outside explicitly approved branches;
- revenue, OPEX, senior debt, SHL cash, or construction formula changes;
- UI/cache/persistence changes.

## Recommendation

Proceed next with `phase6-shl-gross-interest-pnl-bridge`.

That branch should isolate the largest R35 driver first: gross accrued SHL interest ownership for P&L R27. Depreciation ledger work should follow once the SHL interest row is no longer masking the R35 bridge.
