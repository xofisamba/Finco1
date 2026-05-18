# Phase 6 Book Depreciation P&L Bridge

## Purpose

This branch adds a default-off P&L attribution bridge so financial statements P&L R13 can consume book depreciation from the offline depreciation ledger for TUHO.

Runtime behavior changed: no. The bridge does not change waterfall formulas, tax bridge calculations, tax depreciation, Balance Sheet assembly, R99/R102 source status, SHL FCF, project factories, UI, cache, or persistence.

## Flag Behavior

ProjectInfo now exposes:

```text
use_book_depreciation_for_pnl: bool = False
```

Default is false for all factories.

When false:

- financial statements P&L R13 preserves the existing source: `tax_depreciation_audit_keur`
- runtime tax and cashflow outputs are unchanged

When true for TUHO attribution:

- financial statements P&L R13 uses the offline depreciation ledger's TUHO aggregate book depreciation fixture
- financial statements P&L R35 is reconstructed from P&L EBT plus R34 for attribution
- tax depreciation audit fields remain unchanged
- tax bridge runtime calculations remain unchanged
- R99/R102 remains audit-only

When true for Oborovo:

- financial statements P&L assembly raises `ValueError`

## Book Versus Tax Depreciation

The offline depreciation ledger preserves separate book and tax bases:

| Measure | Result |
| --- | ---: |
| TUHO book depreciation / Dep R30 / P&L R13 | 72,993.7 kEUR |
| TUHO tax depreciation / Dep R31 | 70,691.5 kEUR |
| Book less tax difference | 2,302.2 kEUR |

The bridge only affects P&L attribution. It does not promote tax depreciation into runtime tax calculations and does not change any accepted cash-tax or R99/R102 source.

## TUHO R13 Before And After

| Scenario | P&L R13 |
| --- | ---: |
| Legacy financial statements P&L | -70,691.5 kEUR |
| Book depreciation bridge | -72,993.7 kEUR |
| Movement | -2,302.2 kEUR |

The current fixture is aggregate-level. Category-level CAPEX-to-depreciation mapping remains future work.

## R35 Attribution

After the SHL gross accrued bridge, the documented R35 delta was:

```text
+1,869.1 kEUR
```

The book depreciation bridge reduces reconstructed P&L R35 by the known book-tax depreciation difference:

```text
1,869.1 - 2,302.2 = -433.1 kEUR
```

Remaining residual drivers are therefore no longer SHL or depreciation:

| Remaining driver | Delta |
| --- | ---: |
| OPEX/local-tax/minor rows | -733.5 kEUR |
| Senior interest timing/basis | +355.4 kEUR |
| Other/unmapped | -55.0 kEUR |
| Remaining residual | -433.1 kEUR |

## Why Tax Bridge Remains Unchanged

The branch intentionally does not wire depreciation into the tax bridge. Tax bridge fields, cash tax, CIT, R67, R99/R102, and distributions remain as produced by the existing runtime and audit paths.

The bridge is an attribution harness for financial statements P&L only. It proves that P&L R13 can use book depreciation without changing runtime behavior.

## R99 Status

R99/R102 remains blocked. R99 should not be promoted until:

- R35 full validation passes after SHL and book depreciation attribution
- loss engine runtime wiring is separately validated
- CIT annual trigger behavior is validated
- R67 dual-target validation passes

## Next Branch

Recommended next branch:

```text
phase6-r35-full-validation
```
