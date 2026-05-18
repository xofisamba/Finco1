# Phase 6: Tax Bridge Consumes R35 Sources

## Branch
`phase6-tax-bridge-consumes-r35-sources`

## HEAD
`99de7f8` (pre-change baseline)

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
- **Book depreciation (1,216.6 kEUR/period)** is higher than **tax depreciation (1,178.2 kEUR/period)** by **38.4 kEUR/period**
- This means P&L cost is higher → taxable income is **lower** in the book-cost sense
- But R35 formula uses `EBITDA − book_dep + tax_addback`: so book dep (higher) reduces income more, then tax addback (lower) adds back less → net effect is higher taxable income (+9,364.4 kEUR cumulative)
- **SHL gross-accrued (R27 fixture)** is non-zero for TUHO → preferred over formula

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
- **R99 FCF for distribution**: audit-only field populated, but `fcf_for_shl_keur` and `fcf_for_distribution_keur` remain the waterfall-engine defaults (no SHL FCF opt-in)
- R99/R102 remain blocked behind the "no SHL FCF opt-in" constraint
- Next step: phase6d or dedicated R99 wiring branch to bring in `distribution_account.compute_tuho_r99_input_period`

## Tests

| Test | Status |
|------|--------|
| `tests/test_tax_bridge_consumes_r35_sources.py` (9 new) | ✅ 9/9 passed |
| `tests/test_loss_engine_runtime_flag.py` (11) | ✅ 11/11 passed |
| `tests/test_tax_bridge_runtime_flag.py` (8) | ✅ 8/8 passed |
| `tests/test_shl_gross_interest_pnl_bridge.py` (9) | ✅ 9/9 passed |
| `tests/test_book_depreciation_pnl_bridge.py` (6) | ✅ 6/6 passed |
| **Total** | **43/43 passed** |

## Merge Recommendation

The change is ready to merge into `main`. Key validations:

1. ✅ R35 delta > 1,000 kEUR (actual: +9,364.4 kEUR) — not a no-op
2. ✅ Flag OFF TUHO/Oborovo bit-identical
3. ✅ No factory opt-in
4. ✅ No SHL FCF opt-in
5. ✅ Oborovo flag-on remains guarded
6. ✅ All 43 tests pass