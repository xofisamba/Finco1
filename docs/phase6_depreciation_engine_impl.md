# Phase 6 — Depreciation Engine Implementation (Stage 2)

## Branch
`phase6-depreciation-engine-impl`

## Status
**Stage 2: Offline engine only. No runtime integration. No waterfall changes.**

---

## 1. What This Branch Does

Implements the Stage 2 offline depreciation engine as designed in `docs/phase6_depreciation_engine_design.md`.

Creates a new **standalone** package at `domain/depreciation_offline/` with:
- Per-category `useful_life_years` sourced from project inputs or Croatia template defaults
- Straight-line depreciation with `zero_after_life` behavior
- Semiannual and annual frequency support
- Residual value support
- Aggregate schedule generation
- Offline-only: no runtime waterfall integration

---

## 2. What This Branch Does NOT Do

- ❌ No runtime integration (not used by `waterfall_core.py`, `waterfall_runner.py`, or factories)
- ❌ No modification to existing `domain/depreciation/` (the pre-existing offline ledger)
- ❌ No R99/R102 promotion
- ❌ No SHL FCF opt-in
- ❌ No scalar residual plugs
- ❌ No factory opt-in

---

## 3. Package Structure

```
domain/depreciation_offline/
 __init__.py              # Public API exports
 config.py               # DepreciationConfig, DepreciationTemplate
 categories.py           # AssetCategoryRule, CROATIA_TEMPLATE, DEFAULT_TEMPLATE, get_template
 result.py               # DepreciationScheduleEntry, DepreciationScheduleResult
 engine.py               # DepreciationEngine, aggregate()
 templates/
   __init__.py
   croatia.py            # Croatia template re-export
```

---

## 4. Implemented Dataclasses

### AssetCategoryRule
- `category_id: str`
- `category_name: str`
- `capex_amount_keur: float`
- `useful_life_years: int`
- `depreciation_method: str` ("straight_line" | "zero_after_life")
- `start_period: int`
- `end_period: int | None`
- `residual_value_keur: float = 0.0`
- `is_financing_cost: bool = False`
- `source_reference: str = ""`
- `frequency: str = "semiannual"`

### DepreciationConfig
- `asset_categories: list[AssetCategoryRule]`
- `period_count: int`
- `period_frequency: str = "semiannual"`
- `country_template: str = "croatia"`
- `fallback_warning_enabled: bool = True`

### DepreciationScheduleEntry
- `period_index: int`
- `book_depreciation_keur: float`
- `tax_depreciation_keur: float`
- `cumulative_book_keur: float`
- `cumulative_tax_keur: float`
- `remaining_book_basis_keur: float`
- `remaining_tax_basis_keur: float`
- `is_zero_after_life: bool = False`

### DepreciationScheduleResult
- `category_id: str`
- `entries: list[DepreciationScheduleEntry]`
- `total_book_depreciation_keur: float`
- `total_tax_depreciation_keur: float`
- `frequency: str`

### DepreciationTemplate
- `template_id: str`
- `template_name: str`
- `defaults: dict[str, int]`
- `notes: str = ""`

---

## 5. Croatia Template Defaults

| Category | Useful Life |
|----------|------------:|
| turbines | 20 years |
| epc | 20 years |
| grid_connection | 20 years |
| project_rights | 20 years |
| idc | 12 years |
| commitment_fees | 12 years |
| bank_fees | 12 years |
| other | 20 years |

---

## 6. Engine Rules

- `useful_life_years` → `useful_life_periods`:
  - semiannual: `useful_life_years * 2`
  - annual: `useful_life_years`
- Per-period depreciation = `(capex_amount_keur - residual_value_keur) / useful_life_periods`
- Depreciation = 0 after useful life ends
- `start_period` controls first depreciation period
- `end_period` optionally caps the schedule
- Cumulative depreciation capped at depreciable basis
- Remaining basis never below residual value

---

## 7. TUHO Parity Status

**DEP R30/R31 parity: NOT achieved**

### Reason
The exact category-level CAPEX breakdown for TUHO (how much of the 72,993.7 kEUR total belongs to turbines vs grid vs EPC vs IDC vs other) is **not available** in the extracted data. Without this breakdown, the offline engine cannot reproduce the Excel Dep R30/R31 pattern precisely.

### TUHO Book vs Tax Totals (from Python fixtures)
- Book depreciation total (TUHO_BOOK_TOTAL): **72,993.7 kEUR**
- Tax depreciation total (TUHO_TAX_TOTAL): **70,691.5 kEUR**
- Difference: 2,302.2 kEUR (= IDC/commitment/bank fees 12yr vs 20yr timing)

### Diagnostic Test
`test_tuho_dep_r30_synthetic_parity` runs against the extracted CSV from `reports/phase6_dep_r30_excel_crosscheck.csv` and is marked **xfail** with a documented explanation. The test compares a synthetic single-category 20-year schedule (using TUHO_BOOK_TOTAL = 72,993.7 kEUR) against the extracted Excel Dep R30 totals. Mismatches of 60–70 kEUR per period are expected because the synthetic model lacks the actual category-level CAPEX split.

### What Is Needed for Exact Parity
- Source data: per-category CAPEX amounts from the Excel model (Inputs sheet D358–D379 or equivalent)
- Or: a breakdown of 72,993.7 kEUR into turbines / grid / EPC / IDC / bank fees categories

---

## 8. Test Results

### New Depreciation Offline Tests (`tests/test_depreciation_engine_offline.py`)
**13 passed, 1 xfailed**

| Test | Result |
|------|--------|
| `test_straight_line_semiannual_40_periods` | ✅ PASS |
| `test_residual_value_not_below_residual` | ✅ PASS |
| `test_start_period_delays_depreciation` | ✅ PASS |
| `test_zero_after_life` | ✅ PASS |
| `test_aggregate_multiple_categories` | ✅ PASS |
| `test_croatia_template_defaults` | ✅ PASS |
| `test_get_template_croatia` | ✅ PASS |
| `test_get_template_default_fallback` | ✅ PASS |
| `test_no_runtime_imports` | ✅ PASS |
| `test_tuho_dep_r30_synthetic_parity` | ⚠️ XFAIL (diagnostic — missing category CAPEX split) |
| `test_fallback_warning_emitted` | ✅ PASS |
| `test_no_warning_when_disabled` | ✅ PASS |
| `test_end_period_caps_schedule` | ✅ PASS |
| `test_non_depreciable_asset` | ✅ PASS |

### Existing Test Suites (unaffected)
**54 passed** ✅ — all existing tests unaffected by this branch

---

## 9. Files Created / Changed

### New Files
- `domain/depreciation_offline/__init__.py`
- `domain/depreciation_offline/config.py`
- `domain/depreciation_offline/categories.py`
- `domain/depreciation_offline/result.py`
- `domain/depreciation_offline/engine.py`
- `domain/depreciation_offline/templates/__init__.py`
- `domain/depreciation_offline/templates/croatia.py`
- `tests/test_depreciation_engine_offline.py`
- `docs/phase6_depreciation_engine_impl.md`

### Unchanged (preserved from main)
- `domain/depreciation/` (pre-existing offline ledger — untouched)
- `domain/depreciation/templates/` (restored from HEAD)
- `tests/test_depreciation_engine.py` (restored to HEAD version — app-level dep engine tests)

### No Production Runtime Files Changed
- `app/waterfall_core.py` — **NOT MODIFIED**
- `app/waterfall_runner.py` — **NOT MODIFIED**
- `app/project_factories.py` — **NOT MODIFIED**

---

## 10. Namespace Decision / Temporary Isolation

The Stage 1 design (`docs/phase6_depreciation_engine_design.md`) proposed `domain/depreciation/` as the package name. This implementation uses `domain/depreciation_offline/` instead.

**Reason:** `domain/depreciation/` already exists on `main` and contains the pre-existing offline book/tax depreciation ledger (asset.py, ledger.py, schedule.py, result.py). That package and its `__init__.py` public API are **untouched** by this branch. Creating a new top-level package avoids breaking the existing depreciation APIs consumed by `waterfall_core.py` and the existing test suite.

`domain/depreciation_offline/` is a **temporary isolated namespace** for Stage 2. Before Stage 3 (runtime adapter), one of the following must be decided:

- **Option A:** Migrate the new engine into `domain/depreciation/` safely (requires API design review)
- **Option B:** Keep `depreciation_offline` as a separate experimental package permanently
- **Option C:** Create a facade that makes source ownership explicit (new engine → `depreciation_offline`; legacy → `depreciation`)

The runtime adapter **must not consume both packages ambiguously**. This decision is pending and must be resolved before Stage 3.

---

## 11. R99/R102 Status

**BLOCKED.** The depreciation offline engine does **not** unblock R99/R102.

The useful-life canonical decision is **NOT** resolved by this offline engine. The engine enables testing 20y/30y/category-specific configurations, but the canonical policy decision remains pending until:
1. Category-level CAPEX extraction (next branch: `phase6-dep-category-capex-extraction`)
2. TUHO Dep R30/R31 parity recheck
3. External reviewer sign-off on Phase 6 validation pack

R99 promotion is only authorized after all of the above plus the loss-window canonical decision.

---

## 12. TUHO Parity — xfail Test Clarification

`test_tuho_dep_r30_synthetic_parity` is **xfail / expected failure**.

This is **not a failed implementation**. The xfail documents that:
- Exact TUHO Dep R30/R31 parity is blocked by missing category-level CAPEX split
- No scalar plugs or synthetic fitting should be used to force parity
- The offline engine is functionally correct; parity requires source data that is not yet extracted

---

## 13. Next Branch

**`phase6-dep-category-capex-extraction`** (or `phase6-dep-category-capex-source-mapping`)

Goal: Extract TUHO category-level CAPEX split from Excel Inputs D358–D379 (or equivalent source rows) so the offline engine can reproduce Dep R30/R31 without synthetic approximation.

Stage 3 (runtime adapter) is explicitly deferred until:
- Category-level CAPEX split is extracted
- Offline engine achieves TUHO Dep R30/R31 parity within ±1 kEUR/period or documents why not
- Useful-life canonical decision is made
- R99 remains BLOCKED throughout

**Alternative:** `phase6-loss-window-design` — resolve the 5-year Croatian loss window rolling SUMIF vs pool design before integrating the depreciation engine.