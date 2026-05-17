# Phase 6 - Interest Limitation Full-Horizon Excel Extract

Branch: `phase6-interest-limitation-full-horizon-excel-extract`

Status: fixture extraction, diagnostics, and tests only. No runtime behavior is changed.

## Purpose

This branch commits formal 60-period Excel extraction fixtures for the offline interest limitation engine. The fixtures cover the full operating horizon where P&L row 5, Project Life, is `TRUE`.

The extract is a prerequisite for deciding whether `tax_bridge` can consume `domain/tax/interest_limitation.py` in a later default-off runtime branch.

## Extraction Methodology

Workbooks inspected with `openpyxl`:

- TUHO: `20260330_TUHO_BP.xlsm`
- Oborovo: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT (1).xlsm`

Extracted sheet and rows:

- Sheet: `P&L`
- Period start date: row 1
- Period end date: row 2
- Project Life flag: row 5
- Book depreciation for EBITDA reconstruction: row 13
- Financial earnings for EBITDA reconstruction: row 30
- EBT for EBITDA reconstruction: row 32
- Gross SHL interest R27: row 27
- Fiscal reintegration R34: row 34
- Fiscal reintegration helper R54: row 54
- Thin-cap gate R56 / BS R45: row 56
- Absolute cap excess R57: row 57
- EBITDA cap excess R58: row 58
- Ratio adjustment R59: row 59

EBITDA is reconstructed as:

```text
EBITDA = R32 - R30 + R13
```

Each fixture period also stores the relevant Excel formula text for R34, R54, R57, R58, R59, and the BS R45 gate reference.

## Fixture Files

Added:

- `tests/fixtures/interest_limitation/tuho_interest_limitation_fixture.json`
- `tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json`

Each period contains:

- `period_index`
- `excel_period_number`
- `column`
- `start_date`
- `end_date`
- `gross_shl_interest_r27`
- `ebitda`
- `thin_cap_gate_r45`
- `r57_absolute_cap_excess`
- `r58_ebitda_cap_excess`
- `r59_ratio_adjustment`
- `r54_helper`
- `r34_fiscal_reintegration`
- `formulas`

## Coverage Summary

| Project | Extracted periods | Missing periods | Cumulative R34 | Coverage status |
|---|---:|---:|---:|---|
| TUHO-WIND-1 | 60 | 0 | -9,242.7 kEUR | Complete operating horizon |
| Oborovo | 60 | 0 | +30,935.2 kEUR | Complete operating horizon |

## Branch Coverage

| Branch type | Real Excel evidence present? | Notes |
|---|---|---|
| Inactive gate | Yes | TUHO has inactive periods; Oborovo gate is false throughout this extracted operating horizon. |
| Absolute cap binding R57 | No | No extracted period has positive R57. The formula is present in the fixtures, but the branch does not bind. |
| EBITDA cap binding R58 | Yes | TUHO has positive R58 periods and negative R34 under `SUBTRACT_FROM_TI`. |
| Ratio adjustment binding R59 | Yes | Oborovo has non-zero R59 periods and positive R34 under `ADD_BACK`. |

## TUHO Result

TUHO fixture:

- Source workbook: `20260330_TUHO_BP.xlsm`
- Extracted periods: 60
- Missing periods: none
- Ambiguous periods: none
- Sign convention: `SUBTRACT_FROM_TI`
- Cumulative R34: `-9,242.7 kEUR`

The offline engine reproduces R57/R58/R59/R54/R34 within +/-0.5 kEUR for every extracted period.

## Oborovo Result

Oborovo fixture:

- Source workbook: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT (1).xlsm`
- Extracted periods: 60
- Missing periods: none
- Ambiguous periods: none
- Sign convention: `ADD_BACK`
- Cumulative R34: `+30,935.2 kEUR`

The offline engine reproduces R57/R58/R59/R54/R34 within +/-0.5 kEUR for every extracted period.

## Remaining Ambiguities

- No real extracted operating period exercises a positive R57 absolute-cap branch.
- The BS R45 gate is extracted as an Excel value and formula reference. The offline engine still treats it as input and does not derive it.
- Oborovo workbook copies differ. The committed fixture uses the `(1)` workbook copy because it matches the previously discovered cumulative R34 target of approximately `+30,935.2 kEUR`.

## Runtime Safety Confirmation

This branch does not:

- wire interest limitation into `tax_bridge`
- change runtime tax calculations
- add `ProjectInfo` flags
- accept R99/R102 as a runtime source
- enable SHL FCF waterfall
- change project factories
- change waterfall, revenue, OPEX, debt, construction, UI, cache, or persistence behavior

## Runtime Consumption Readiness

Runtime consumption is now justified from an R34/R54 fixture-parity perspective, subject to the next branch remaining default-off and TUHO-first.

Recommended next branch:

```text
phase6-tax-bridge-consumes-interest-limitation
```

That branch should:

- keep legacy behavior default-off
- consume the offline interest limitation result only behind explicit tax bridge runtime control
- preserve R99/R102 as audit-only until separately accepted
- keep Oborovo guarded unless full tax bridge parity is separately approved
