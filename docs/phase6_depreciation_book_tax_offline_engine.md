# Phase 6 Depreciation Book/Tax Offline Engine

## Purpose

This branch adds an offline depreciation ledger that produces book depreciation and tax depreciation separately by asset class.

Runtime behavior changed: no. The ledger is not wired into runtime P&L, the tax bridge, R99/R102, SHL FCF, project factories, UI, cache, or persistence.

## Package Structure

```text
domain/depreciation/
  __init__.py
  asset.py
  schedule.py
  ledger.py
  result.py
  templates/
    __init__.py
    croatia.py
```

## Engine Scope

Implemented now:

- immutable asset, policy, input, period result, and ledger result dataclasses
- straight-line depreciation only
- one ledger row per asset class per period
- separate book and tax depreciable bases
- separate accumulated book and accumulated tax depreciation
- book NBV and tax NBV
- aggregate helper methods by period

Not implemented in this branch:

- runtime P&L wiring
- tax bridge wiring
- ProjectInfo flags
- project factory opt-in
- category-level Excel CAPEX extraction
- VAT facility capitalization
- partial-period depreciation conventions beyond explicit start period
- R99/R102 runtime source acceptance

## TUHO Aggregate Fixture

The current fixture is aggregate-level because category-level Excel CAPEX-to-depreciation mapping is still a future workstream.

| Measure | Excel target | Offline ledger result |
| --- | ---: | ---: |
| Book depreciation / Dep R30 / P&L R13 | 72,993.7 kEUR | 72,993.7 kEUR |
| Tax depreciation / Dep R31 | 70,691.5 kEUR | 70,691.5 kEUR |
| Book less tax depreciation | 2,302.2 kEUR | 2,302.2 kEUR |

The fixture uses a single TUHO aggregate asset class with separate book and tax depreciable bases across 60 semiannual operating periods. This proves the ledger can carry distinct book and tax bases without changing runtime outputs.

## Straight-Line Semantics

For each asset class:

```text
periodic depreciation = depreciable basis / useful life periods
```

Depreciation:

- starts at `depreciation_start_period`
- does not occur before the start period
- stops after the useful life ends
- is capped so NBV cannot go negative
- tracks book and tax accumulated depreciation independently

Gross asset basis is exposed from `placed_in_service_period` onward.

## Known Gaps

| Gap | Status |
| --- | --- |
| TUHO category-level CAPEX mapping | Future fixture extraction |
| Oborovo depreciation fixture | Future parity branch |
| Book depreciation P&L consumption | Future default-off bridge |
| Balance Sheet gross assets / accumulated depreciation / NBV consumption | Future BS bridge |
| Tax bridge consumption of tax depreciation | Future default-off tax bridge branch |
| VAT facility IDC and capitalization basis | Separate VAT/construction workstream |

## Why Runtime Is Unchanged

The new package is standalone and input-driven. No existing app, waterfall, financial-statement, tax, SHL, loss, or factory code imports it. Existing runtime depreciation, P&L, tax bridge, R99/R102, and SHL behavior therefore remains unchanged.

## Next Branch

Recommended next branch:

```text
phase6-book-depreciation-pnl-bridge
```

That branch should add a default-off P&L bridge so financial statements P&L R13 can consume book depreciation from this ledger while preserving legacy behavior when off.
