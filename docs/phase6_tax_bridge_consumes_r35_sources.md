# Phase 6: Tax Bridge Consumes R35 Sources

## Branch
`phase6-tax-bridge-consumes-r35-sources`

## HEADs
- **Implementation commit:** `0bf0ec1cadeb0172c8706e7281ffc8b39a2d7300`
- **Baseline (pre-change):** `99de7f8d2d46fd0ffdbe8c515d79f0897d69ea17`

## What Changed

The TUHO tax bridge's `_tax_bridge_taxable_income_before_losses` function was updated to consume the **R35 source basis** instead of the legacy waterfall formula fields:

### Before (legacy ATAD inputs)
- `depreciation_keur` — waterfall formula (book = tax equal by construction)
- `shl_interest_keur` — formula-derived gross SHL interest

### After (R35 source basis)
- `book_depreciation_keur` — P&L straight-line cost (from book/tax depreciation ledger, BOOK=72,993.7 kEUR / 60 periods)
- `tax_depreciation_keur` — fiscal addback straight-line (from same ledger, TAX=70,691.5 kEUR / 60 periods)
- `shl_interest_formula_keur` — legacy formula fallback
- `shl_interest_gross_accrued_keur` — fixture-extracted Excel R27 (preferred; non-zero for TUHO)

### Files Changed

| File | Change |
|------|--------|
| `app/waterfall_core.py` | `_tuho_shl_gross_accrued_by_period()` helper; `_apply_tuho_tax_bridge_runtime_cash_tax()` wiring; `_tax_bridge_taxable_income_before_losses()` new signature + formula |

## Before/After Numbers

### TUHO R35 (taxable income before losses, total over 60 periods)

| | Flag OFF (legacy) | Flag ON (R35 source) | Δ |
|---|---|---|---|
| R35 total | 245,276.4 kEUR | 254,640.8 kEUR | **+9,364.4 kEUR** |
| R67 total | -39,639.7 kEUR | -45,825.2 kEUR | -6,185.6 kEUR |
| R34 (fixture) | — | -9,242.7 kEUR | — |
| Total CIT | 39,649.8 kEUR | 45,835.3 kEUR | +6,185.6 kEUR |

### Key Driver of Change

R35 movement is the **combined result** of three R35 source basis changes, not depreciation alone:

**1. Depreciation split effect (lowers R35 by ~2,302 kEUR cumulative)**
> Book depreciation (72,993.7 kEUR total / 60 periods) > Tax depreciation (70,691.5 kEUR total / 60 periods)
>
> R35 formula: `EBITDA − book_dep + tax_dep + interest_items + fiscal_reintegration`
>
> Since book_dep > tax_dep, the term `−book_dep + tax_dep` is negative, lowering R35 by the full book-tax cumulative difference of **~2,302 kEUR** over the model life. This effect alone moves R35 in the opposite direction from the total observed movement.

**2. SHL gross-accrued interest source (primary driver of +9,364 kEUR R35 increase)**
> The validated Excel R27 fixture provides per-period gross-accrued SHL interest that differs from the formula-derived amount. This fixture-extracted source is used as the preferred SHL input to the ATAD interest limitation computation in R35.
>
> Because ATAD deductibility is capped at 30% EBITDA (with a 3,000 kEUR floor), and the gross-accrued fixture produces a different interest base than the legacy formula, the combined ATAD disallowed-allowed interest split shifts R35 upward substantially.

**3. Interest limitation mechanics**
> The gross-accrued SHL interest (non-zero for all 60 TUHO operating periods, ranging ~1,297–1,660 kEUR/period) interacts with the ATAD cap. The net effect of the source substitution is an R35 increase of ~9,364 kEUR, which is the dominant driver of the total movement.

**Summary:** The depreciation split alone would lower R35 by ~2,302 kEUR. The combined R35 source basis changes — primarily the SHL gross-accrued fixture substitution — produce a net +9,364 kEUR movement.

## `_tuho_shl_gross_accrued_by_period()` — Calibration Bridge Note

> **This is a temporary TUHO-only fixture-backed calibration bridge.**
>
> - Default-off; activated only inside `_apply_tuho_tax_bridge_runtime_cash_tax` when `use_tax_bridge_engine=True`
> - TUHO-specific; not a generalized production data model
> - Reads the validated Excel R27 fixture (`tests/fixtures/interest_limitation/tuho_interest_limitation_fixture.json`)
> - Should later move to a proper source-data or domain fixture layer before any broader use

## R67 Status

| | Value |
|---|---|
| Excel R67 target | -38,240.9 kEUR |
| Flag ON R67 (new) | -45,825.2 kEUR |
| Residual | **-7,584.3 kEUR (not yet calibrated)** |

- **R35 source consumption is complete** (this branch)
- **R67 is not yet calibrated** — the residual has widened vs the pre-branch state because the R35 basis now uses the correct sources, which changes how losses and tax flow through
- **Next branch:** `phase6-r67-full-calibration-validation`
- **R99/R102:** remain blocked / audit-only (`fcf_for_shl_keur = 0.0` across all periods)

## Default Behavior
- **Unchanged** — flag defaults to `False`; factories do not opt in
- Flag OFF TUHO: bit-identical to default (verified)
- Flag OFF Oborovo: bit-identical to default (verified)

## Remaining Residual

### What Still Uses Legacy Inputs (by design)
- `ebitda_keur` — waterfall engine (not yet replaced by Excel-extracted EBITDA fixture)
- `senior_interest_keur` — waterfall engine (senior debt schedule)
- `shl_interest_formula_keur` — fallback when gross-accrued fixture is 0

### What Is Not Wired (blocked / audit-only)
- **R99 / R102 SHL FCF opt-in** — blocked; `fcf_for_shl_keur` remains 0.0
- **Oborovo tax bridge** — guarded; raises `ValueError` if flag is set

## R99 Readiness Status
- **BLOCKED** — R99/R102 remain audit-only
- `fcf_for_shl_keur` is 0.0 across all periods; no SHL FCF waterfall opt-in
- Next step: `phase6-r67-full-calibration-validation` → subsequent branch for R99 wiring

## Tests

| Test | Status |
|------|--------|
| `tests/test_tax_bridge_consumes_r35_sources.py` (9 new) | ✅ 9/9 passed |
| `tests/test_loss_engine_runtime_flag.py` (11) | ✅ 11/11 passed |
| `tests/test_tax_bridge_runtime_flag.py` (8) | ✅ 8/8 passed |
| `tests/test_shl_gross_interest_pnl_bridge.py` (9) | ✅ 9/9 passed |
| `tests/test_book_depreciation_pnl_bridge.py` (6) | ✅ 6/6 passed |
| `tests/test_r35_full_validation.py` (7) | ✅ 7/7 passed |
| `tests/test_financial_statements_excel_export.py` (5) | ✅ 5/5 passed |
| `tests/test_shl_fcf_waterfall_runtime_flag.py` (10) | ✅ 10/10 passed |
| **Total** | **65/65 passed** |

## Merge Recommendation

The change is ready to merge into `main`. Key validations:

1. ✅ R35 delta > 1,000 kEUR (actual: +9,364.4 kEUR) — not a no-op
2. ✅ Flag OFF TUHO/Oborovo bit-identical
3. ✅ No factory opt-in
4. ✅ No SHL FCF opt-in
5. ✅ Oborovo flag-on remains guarded
6. ✅ All 65 tests pass
7. ✅ R35 source consumption complete; R67 not yet calibrated
8. ✅ R99/R102 remain blocked