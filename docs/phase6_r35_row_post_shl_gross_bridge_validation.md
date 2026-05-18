# Phase 6 R35 Row Post-SHL-Gross Bridge Validation

## Purpose

This diagnostic branch reruns the TUHO R35 row attribution after the default-off SHL gross accrued P&L bridge.

Runtime behavior changed: no. The workbook applies the already-merged TUHO P&L R27 bridge for attribution only. It does not change depreciation, tax, loss carry-forward, R99/R102, SHL FCF, or project factory behavior.

Workbook:

```text
reports/phase6_tuho_r35_post_shl_gross_bridge.xlsx
```

## Executive Finding

The SHL gross accrued P&L bridge closes the largest validated R35 source gap.

| Metric | Result |
| --- | ---: |
| R35 delta before SHL gross bridge | +12,216.4 kEUR |
| R35 delta after SHL gross bridge | +1,869.1 kEUR |
| Delta reduction | +10,347.3 kEUR |
| SHL driver closed | Yes |

The remaining R35 attribution blocker is now primarily book-versus-tax depreciation ownership, with smaller OPEX/local-tax/minor-row and senior-interest residuals.

## Workbook Structure

The workbook contains:

- `Summary`
- `R35 Before After`
- `R27 SHL Interest`
- `Remaining Drivers`
- `Largest Remaining Deltas`
- `R67 Impact`
- `Notes`

## R35 Delta Before And After

The diagnostic preserves the Phase 6 R35 source-validation methodology:

```text
R35 delta =
  revenue delta
+ OPEX delta
+ depreciation delta
+ senior interest delta
+ SHL interest delta
+ R34 delta
+ other residual
```

After the SHL gross accrued bridge:

```text
SHL interest delta = 0.0 kEUR
Remaining R35 delta = 1,869.1 kEUR
```

This confirms that the prior +10,347.3 kEUR SHL row source gap was real and is now closed for P&L attribution.

## R27 SHL Interest

| Scenario | TUHO P&L R27 |
| --- | ---: |
| Legacy Python P&L R27 | -39,434.9 kEUR |
| Flag-on Python P&L R27 | -49,782.2 kEUR |
| Excel P&L R27 target | -49,782.2 kEUR |

The workbook's `R27 SHL Interest` sheet shows per-period flag-on deltas of zero against the Excel gross accrued R27 extract.

## Remaining Driver Ranking

| Driver | Before bridge | After bridge | Status |
| --- | ---: | ---: | --- |
| SHL interest gross/net/timing | +10,347.3 kEUR | 0.0 kEUR | Closed |
| Book/tax depreciation timing | +2,302.2 kEUR | +2,302.2 kEUR | Open |
| OPEX/local-tax/minor row timing | -733.5 kEUR | -733.5 kEUR | Open |
| Senior interest timing/basis | +355.4 kEUR | +355.4 kEUR | Open minor |
| R34 fiscal reintegration | 0.0 kEUR | 0.0 kEUR | Calibrated |
| Other/unmapped residual | -55.0 kEUR | -55.0 kEUR | Open minor |

The largest remaining period-level deltas are late-horizon depreciation/book-tax differences.

## R67 Impact

R67 is unchanged by this branch.

Reason:

- the SHL gross bridge is a P&L attribution bridge;
- it does not feed runtime tax;
- it does not accept R99/R102 as a source;
- it does not enable SHL FCF waterfall.

R67 and R99 remain blocked pending the next tax-basis row ownership work.

## Decision

The SHL R27 driver is closed. The next blocker is not SHL cash mechanics, PIK, or WHT. It is depreciation/book-tax row ownership, plus smaller OPEX/local-tax/minor-row and senior-interest cleanup.

R99/R102 remains blocked.

## Recommended Next Branch

```text
phase6-depreciation-book-tax-ledger-design
```

Recommended scope:

- design explicit book and tax depreciation ownership;
- keep P&L R13 on book depreciation;
- keep tax bridge on tax depreciation plus explicit tax adjustments;
- keep R99/R102 audit-only until R35/R67 gates pass.
