# Phase 21F — CAPEX Line Item Treatment Options Design

## Executive Summary

Defines user-selectable treatment options for each CAPEX line item across accounting, depreciation, tax, funding, and construction timing dimensions. Adds schema stubs for treatment enums and a C.16 Project Rights example showing unresolved treatment state. This is a pure design phase — no runtime calculations change, no CAPEX totals change, nothing is wired to depreciation/tax/funding engines yet.

## Why User Must Choose Treatment

Each CAPEX line item can be treated differently depending on:
- **Accounting policy**: IFRS vs local GAAP determines whether something is an intangible, PP&E, or expensed.
- **Jurisdiction**: BIH, Croatia, and Montenegro have different tax depreciation rules.
- **Financing structure**: Lenders may not accept project rights as collateral.
- **Asset class**: Land is never depreciable; development costs may be amortised or expensed.

Treating all CAPEX the same way would produce incorrect depreciation, wrong tax basis, and invalid funding models.

## Treatment Dimensions

### 1. Accounting Treatment
`AccountingTreatment` enum:
- `DEPRECIABLE_CAPEX` — standard PP&E, subject to depreciation
- `INTANGIBLE_ASSET` — rights, licenses, concessions (amortised)
- `DEVELOPMENT_COST` — capitalised development expenditure
- `ACQUISITION_PREMIUM` — premium over fair value on acquisition
- `LAND_OR_NON_DEPRECIABLE` — land, not depreciable
- `FINANCING_COST` — capitalised financing charges (IDC)
- `RESERVE_ACCOUNT` — reserve / sinking fund
- `EXCLUDED_FROM_CAPEX` — out of scope for capitalisation
- `CUSTOM` — user-defined

### 2. Depreciation / Amortisation Treatment
`DepreciationTreatment` enum:
- `DEPRECIABLE` — straight-line or reducing balance
- `AMORTIZABLE` — amortisation of intangible / right-of-use
- `NON_DEPRECIABLE` — no depreciation (land)
- `EXPENSED` — immediately expensed in year 1
- `EXCLUDED` — excluded from depreciation schedule
- `CUSTOM` — user-defined

### 3. Depreciation Life
`DepreciationLifeYears` enum:
- `USE_TEMPLATE_DEFAULT`, `YEARS_5`, `YEARS_10`, `YEARS_15`, `YEARS_20`, `YEARS_30`, `CUSTOM_YEARS`

### 4. Tax Treatment
`TaxTreatment` enum:
- `TAX_DEPRECIABLE` — tax depreciation (e.g. 5-year MACRS)
- `TAX_AMORTIZABLE` — tax amortisation of intangibles
- `NON_DEDUCTIBLE` — no tax deduction ever
- `IMMEDIATELY_DEDUCTIBLE` — expensed in year 1
- `EXCLUDED_FROM_TAX_BASIS` — excluded from taxable income
- `JURISDICTION_SPECIFIC` — EU/BIH/HR rules apply
- `CUSTOM` — user-defined

### 5. Funding Treatment
`FundingTreatment` enum:
- `SENIOR_DEBT_ELIGIBLE` — eligible for senior debt
- `EQUITY_ONLY` — equity-funded only
- `SHL_ELIGIBLE` — subordinated hybrid loan eligible
- `INCLUDED_IN_TOTAL_FUNDING` — included in total funding need
- `EXCLUDED_FROM_FUNDING` — excluded from funding model
- `CUSTOM` — user-defined

### 6. Construction Timing / IDC
`ConstructionTimingTreatment` enum:
- `INCLUDED_IN_CONSTRUCTION_DRAW` — drawn monthly via M1–M18 schedule
- `EXCLUDED_FROM_IDC` — no interest during construction
- `PAID_AT_FINANCIAL_CLOSE` — paid in full at FC
- `PAID_AT_COD` — paid in full at COD
- `PAID_ON_CUSTOM_SCHEDULE` — user-defined
- `TIMING_ONLY` — schedule used for IDC timing only, not a CAPEX total

### 7. Schedule Type
`ScheduleType` enum:
- `M1_M18_IMPORTED` — from Excel monthly schedule
- `LINEAR` — equal monthly instalments
- `S_CURVE` — S-curve (front/back-loaded)
- `ONE_OFF` — single payment
- `CUSTOM` — user-defined

## C.16 Project Rights — Why Not Hard-Coded

Excel C.16 total = 14,739 kEUR:
- C.16.01 Akuro Development Rights = 2,739 kEUR
- C.16.02 Other Development Costs = 2,000 kEUR
- C.16.03 Land / Purchase = 10,000 kEUR

**Why treatment is unresolved:**

| Aspect | C.16.01 Akuro | C.16.02 Dev Costs | C.16.03 Land |
|---|---|---|---|
| Accounting | Likely DEVELOPMENT_COST | DEVELOPMENT_COST | Likely LAND_OR_NON_DEPRECIABLE |
| Depreciation | AMORTIZABLE 10yr | EXPENSED or AMORTIZABLE | NON_DEPRECIABLE |
| Tax | JURISDICTION_SPECIFIC (BIH) | IMMEDIATELY_DEDUCTIBLE (BIH) | NON_DEDUCTIBLE |
| Funding | EQUITY_ONLY (unconfirmed) | EQUITY_ONLY | SENIOR_DEBT_ELIGIBLE (land as collateral) |
| Timing | PAID_AT_FINANCIAL_CLOSE | PAID_AT_FINANCIAL_CLOSE | PAID_AT_FINANCIAL_CLOSE |

**Hard-coding any of these would be wrong because:**
1. BIH vs HR jurisdiction changes tax treatment significantly.
2. Lender's acceptance of project rights as collateral is unconfirmed.
3. Acquisition premium treatment under IFRS vs local GAAP is unresolved.
4. No construction draw (paid at FC) — affects IDC calculation.

**Current status:** `affects_runtime = false` — C.16 is a display-only reference row pending user treatment decision.

## Future UI: How Treatment Dropdowns Will Work

Phase 21G (future) will add a "Treatment" column or modal to the CAPEX detail grid:
1. Each CAPEX line shows a "Treatment" badge: `⚠ Unresolved` or `✓ Resolved`.
2. Clicking a row opens a treatment panel with dropdowns for all 7 dimensions.
3. User selections are saved to project inputs (not runtime yet).
4. "Resolve All" button highlights remaining unresolved items.
5. Warning banner appears if C.16 treatment is still unresolved before final model run.

## How Choices Will Later Feed Calculations

| Treatment choice | Affects |
|---|---|
| Accounting + Depreciation | Depreciation schedule in income statement; book capex value |
| Depreciation life | Timing and amount of depreciation expense |
| Tax treatment | Tax depreciation schedule; taxable income calculation |
| Tax jurisdiction | Applicable tax depreciation tables (BIH MACRS, HR rules, EU directives) |
| Funding treatment | Senior debt sizing (eligible capex basis); equity requirement |
| Construction timing | Construction draw schedule; IDC capitalisation |
| Schedule type | Monthly cash flow timing for construction phase |

## What This Phase Does NOT Change

- ❌ No runtime calculations changed
- ❌ No CAPEX totals changed
- ❌ No depreciation engine modified
- ❌ No tax engine modified
- ❌ No funding model modified
- ❌ No construction IDC wired
- ❌ No rows made editable
- ❌ No save endpoints added
- ❌ C.16 remains `affects_runtime = false`
- ❌ G20 **BLOCKED**
- ❌ R99/R102 **NOT APPROVED**

## Schema Inertness

All new enums and `CapexLineTreatment` are in `app/domain/capex/source_model.py`. This file is isolated — it is NOT imported by:
- `app/domain/capex/capex_schedule.py`
- `app/domain/capex/factory.py`
- `app/ui/project_context.py`
- Any runtime calculation module

This ensures Phase 21F is a pure design deliverable with zero runtime impact.

## Recommended Next Phase

**Phase 21G**: Wire treatment options to runtime — add treatment panel UI, persist user selections, start connecting accounting treatment to depreciation schedule and tax treatment to tax basis calculation.