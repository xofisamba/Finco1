# Phase 6 - Interest Limitation Offline Engine

Branch: `phase6-interest-limitation-offline-engine`

Status: offline model component only. No runtime tax calculation, waterfall behavior, ProjectInfo flags, R99/R102 source acceptance, SHL FCF opt-in, or project factory defaults are changed.

## Purpose

This branch adds a pure offline implementation of the Excel fiscal reintegration / interest limitation helper rows:

```text
R57 = IF(thin_cap_active, MAX(gross_shl_interest - absolute_cap, 0), 0)
R58 = IF(thin_cap_active, MAX(gross_shl_interest - ebitda_pct_cap * EBITDA, 0), 0)
R59 = project-specific ratio adjustment
R54 = MIN(MAX(R57, R58) + R59, gross_shl_interest)
R34 = sign_convention applied to R54
```

The module is designed to reproduce Excel P&L R34/R54 audit mechanics for TUHO and Oborovo before any runtime tax bridge consumption.

## Added Module

`domain/tax/interest_limitation.py`

Public API:

- `InterestLimitationSignConvention`
- `InterestLimitationConfig`
- `InterestLimitationPeriodInput`
- `InterestLimitationPeriodResult`
- `InterestLimitationResult`
- `compute_interest_limitation_period(...)`
- `compute_interest_limitation_schedule(...)`

The engine is input-driven. Callers provide:

- gross SHL interest, Excel R27
- EBITDA
- explicit thin-cap active flag
- optional project-specific R59 ratio adjustment

The engine does not read project factories, runtime waterfall results, financial statements, R99/R102 fields, or SHL runtime state.

## TUHO Result

TUHO requires `InterestLimitationSignConvention.SUBTRACT_FROM_TI`.

Fixture period from Excel discovery:

| Field | Value |
|---|---:|
| Gross SHL interest R27 | 1,425.1 |
| EBITDA | 3,209.2 |
| 30% EBITDA cap | 962.8 |
| R57 excess absolute cap | 0.0 |
| R58 excess EBITDA cap | 462.3 |
| R59 ratio adjustment | 0.0 |
| R54 | 462.3 |
| R34 fiscal reintegration | -462.3 |

The negative R34 value decreases taxable income under the TUHO workbook convention. This is intentionally configurable because it is non-standard compared with ordinary addback treatment.

## Oborovo Result

Oborovo requires `InterestLimitationSignConvention.ADD_BACK`.

Fixture period from Excel discovery:

| Field | Value |
|---|---:|
| Gross SHL interest R27 | 636.8 |
| R57 excess absolute cap | 0.0 |
| R58 excess EBITDA cap | 0.0 |
| R59 ratio adjustment | -636.8 |
| R54 | -636.8 |
| R34 fiscal reintegration | +636.8 |

The positive R34 value increases taxable income under the Oborovo workbook convention.

## Sign Convention Behavior

The engine exposes two sign modes:

- `ADD_BACK`: converts the R54 helper amount into a positive taxable income adjustment.
- `SUBTRACT_FROM_TI`: converts the R54 helper amount into a negative taxable income adjustment.

This avoids hardcoding TUHO behavior into Oborovo or vice versa.

## Known Gaps

- The engine does not compute BS R45. The thin-cap gate is an explicit period input.
- The engine does not carry forward disallowed interest.
- The engine does not compute rolling 5-year tax losses.
- The engine does not consume financial statements or depreciation outputs.
- The engine is not wired into `use_tax_bridge_engine`.
- Exact full-horizon TUHO/Oborovo fixtures should be added once the Excel extraction is formalized in repo fixtures.

## Runtime Safety

This branch is offline only:

- no ProjectInfo flag added
- no tax formula changed
- no depreciation formula changed
- no waterfall behavior changed
- no R99/R102 source accepted
- no SHL FCF waterfall enabled
- no project factory defaults changed

## Next Branch Recommendation

Recommended next branch:

```text
phase6-tax-bridge-consumes-interest-limitation
```

Only after full-horizon fixtures are added and TUHO/Oborovo R34 parity is proven should the tax bridge consume this engine behind a default-off runtime path.

Parallel track:

```text
phase6-depreciation-ledger-design
```

That branch should design the book/tax depreciation ledger needed by P&L and balance sheet reporting.
