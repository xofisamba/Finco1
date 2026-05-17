# Phase 6 - Interest Limitation Fixture Parity

Branch: `phase6-interest-limitation-full-horizon-fixtures`

Status: diagnostic tests and documentation only. Runtime behavior is unchanged.

## Purpose

This branch adds fixture-backed parity tests around the offline interest limitation engine before any tax bridge consumption. The goal is to protect the Excel R34/R54/R57/R58/R59 mechanics for TUHO and Oborovo and to make the current fixture coverage explicit.

## Fixture Source

Fixture values come from the Phase 6 depreciation and fiscal reintegration forensic discovery documents supplied for review. The discovery extracted representative Excel formulas and values for:

- P&L R27 gross SHL interest
- EBITDA reconstructed through `R32 - R30 + R13`
- BS R45 thin-cap gate behavior
- P&L R57 absolute-cap excess
- P&L R58 30% EBITDA excess
- P&L R59 4:1 ratio adjustment
- P&L R54 fiscal reintegration helper
- P&L R34 signed fiscal reintegration row

The repository does not yet contain a formal 60-period extracted fixture table. This branch therefore locks representative period parity rather than claiming full-horizon parity.

## TUHO Representative Result

TUHO requires `SUBTRACT_FROM_TI`.

| Period | Scenario | R27 gross SHL interest | EBITDA | Gate | R57 | R58 | R59 | R54 | R34 |
|---:|---|---:|---:|:---:|---:|---:|---:|---:|---:|
| 0 | inactive gate | 1,297.4 | 4,060.9 | false | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 7 | first active EBITDA-cap period | 1,425.1 | 3,209.2 | true | 0.0 | 462.3 | 0.0 | 462.3 | -462.3 |

The period 7 fixture proves TUHO's non-standard subtractive convention: R54 is positive, but R34 decreases taxable income.

Known full-horizon target from discovery:

- TUHO R34 total: approximately `-9,242.7 kEUR`

This branch does not assert that total because the full 60-period fixture table is not yet committed.

## Oborovo Representative Result

Oborovo requires `ADD_BACK`.

| Period | Scenario | R27 gross SHL interest | Gate | R57 | R58 | R59 | R54 | R34 |
|---:|---|---:|:---:|---:|---:|---:|---:|---:|
| 0 | 4:1 ratio active | 636.8 | true | 0.0 | 0.0 | -636.8 | -636.8 | +636.8 |

The Oborovo fixture proves the standard addback convention: R34 increases taxable income.

Known full-horizon target from discovery:

- Oborovo R34 total: approximately `+30,935.2 kEUR`

This branch does not assert that total because the full 60-period fixture table is not yet committed.

## Formula Branch Coverage

The tests also include a synthetic branch case for the absolute-cap path. It is intentionally marked as formula coverage, not an extracted Excel period. This protects the R57/R58 max-combiner behavior without overstating source evidence.

## Full-Horizon Parity Status

Full-horizon parity: **not yet claimed**.

Current coverage:

- TUHO inactive gate period
- TUHO first active 30% EBITDA-cap period
- Oborovo 4:1 ratio active period
- synthetic absolute-cap branch coverage
- R57/R58/R59/R54/R34 audit fields
- no runtime wiring guard
- no R99/R102 acceptance guard
- no SHL FCF opt-in guard

Remaining fixture blocker:

- Commit full TUHO and Oborovo period fixture arrays for all operating periods where Excel R27, EBITDA, BS R45, R57, R58, R59, R54, and R34 are extracted.

## Ambiguities

- No extracted period currently proves a true Excel R57 absolute-cap binding case. The available TUHO material shows the 30% EBITDA cap binding.
- BS R45 is treated as fixture input. The offline engine does not derive this gate.
- Oborovo's R59 sign is fixture-driven; future full-horizon fixtures should keep raw R59 visible.

## Runtime Safety

This branch does not:

- wire `domain/tax/interest_limitation.py` into `tax_bridge`
- add a `ProjectInfo` flag
- accept R99/R102 as a runtime source
- enable SHL FCF waterfall
- change project factories
- change waterfall, tax, revenue, OPEX, debt, or construction formulas

## Remaining Blockers Before Tax Bridge Consumption

Before `tax_bridge` consumes interest limitation:

1. Add full 60-period TUHO and Oborovo fixture tables.
2. Assert TUHO total R34 approximately `-9,242.7 kEUR`.
3. Assert Oborovo total R34 approximately `+30,935.2 kEUR`.
4. Decide whether BS R45 remains an explicit tax fixture input or comes from financial statements BS diagnostics.
5. Keep the runtime path default-off and TUHO-first.

## Recommended Next Branch

Recommended next branch:

```text
phase6-tax-bridge-consumes-interest-limitation
```

If full-horizon fixture extraction is preferred before runtime consumption, insert:

```text
phase6-interest-limitation-full-horizon-excel-extract
```

That branch should add formal 60-period fixture tables only, with no runtime wiring.
