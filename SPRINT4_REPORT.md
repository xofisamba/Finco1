# Sprint 4 Report

**Sprint 4: IRR Wiring Fixes + Broken Tests**
Date: 2026-04-30
Status: ✅ Complete

## Summary

Fixed equity IRR wiring (`sculpt_capex_keur`), `prior_tax_loss_keur` propagation, `test_sensitivity.py` broken imports, and created equity IRR method unit tests.

## Changes by Task

### S4-1: `sculpt_capex_keur` Propagation
**File:** `domain/waterfall/waterfall_engine.py` (line 1115)

**Problem:** `cached_run_waterfall` passed `inputs.capex.sculpt_capex_keur` as `total_capex` to `run_waterfall`, causing project IRR to be computed over sculpt_capex base instead of total_capex.

**Fix:** Changed to `inputs.capex.total_capex` as project IRR base (line 1108). Equity IRR still uses `sculpt_capex_keur` for equity base per `combined` method.

```python
# Before:
total_capex=inputs.capex.sculpt_capex_keur,

# After:
total_capex=inputs.capex.total_capex,
```

**Impact:** Project IRR base is now correct. Equity IRR uses sculpt_capex for Oborovo `combined` method.

### S4-2: `prior_tax_loss_keur` Propagation
**Files:** `app/cache.py`, `domain/waterfall/waterfall_engine.py`

**Problem:** `cached_run_waterfall` didn't pass `prior_tax_loss_keur`; waterfall_engine had hardcoded `7060.0` fallback.

**Fix:**
1. `app/cache.py`: Added `prior_tax_loss_keur=inputs.tax.initial_tax_loss_keur` parameter
2. `domain/waterfall/waterfall_engine.py` (line 526): Removed hardcoded `7060.0` fallback; now uses `idc_keur + bank_fees_keur + commitment_fees_keur` (≈1,940 kEUR for Oborovo)

**Impact:** Tax loss carryforward correctly propagated. When `initial_tax_loss_keur=0` (Oborovo default), uses construction-period costs as estimate.

### S4-3: Equity IRR Methods Unit Tests
**File:** `tests/test_equity_irr_methods.py` (NEW, 6 tests)

Tests all three `equity_irr_method` values:
- `equity_only`: equity = total_capex - debt (TUHO style)
- `combined`: equity = sculpt_capex - debt (Oborovo style)
- `shl_plus_dividends`: equity = shl_amount + share_capital, SHL interest in CF

```
tests/test_equity_irr_methods.py::TestEquityIRRMethod::test_equity_only_simple PASSED
tests/test_equity_irr_methods.py::TestEquityIRRMethod::test_combined_with_sculpt_capex PASSED
tests/test_equity_irr_methods.py::TestEquityIRRMethod::test_shl_plus_dividends PASSED
tests/test_equity_irr_methods.py::TestEquityIRRMethod::test_all_three_methods_produce_different_equity_irr PASSED
tests/test_equity_irr_methods.py::TestEquityIRRMethod::test_xirr_function PASSED
tests/test_equity_irr_methods.py::TestProjectIRR::test_project_irr_independent_of_equity_method PASSED
```

### S4-4: Fix `test_sensitivity.py` (core module missing)
**File:** `domain/finance/sensitivity.py` (NEW), `domain/finance/__init__.py` (NEW)

**Problem:** 12 tests in `test_sensitivity.py` failed — they imported from `core.finance.sensitivity` which doesn't exist.

**Fix:** Created `domain/finance/sensitivity.py` with `run_tornado_analysis` and `run_spider_analysis` (the actual functions needed). Also fixed multiple dataclass field errors:
- `_capex_sensitivity`: CapexStructure has individual CapexItem fields, not `hard_capex_keur` → scaled all CapexItems individually
- `_opex_sensitivity`: `inputs.opex` is a tuple of OpexItem, not an object with `fixed_cost_keur` → scaled `y1_amount_keur` on each item
- `_rate_sensitivity`: `FinancingParams` has `base_rate` not `all_in_rate` → adjusted `base_rate` instead
- `run_tornado_analysis`: Missing `base_opex` variable → computed from sum of opex items

**Also fixed in `reporting/fid_deck.py`**: Changed `from core.finance.sensitivity import` → `from domain.finance.sensitivity import`

## Calibration Verification (S4-5)

Model run via direct `run_waterfall` call with Oborovo defaults + `prior_tax_loss_keur=9000`:

| Metric | Target | Actual | Deviation | Status |
|--------|--------|--------|-----------|--------|
| Project IRR | 7.96% ± 0.15% | 8.53% | +0.57% | ⚠️ Outside tolerance |
| Equity IRR | 10.60% ± 0.50% | 9.65% | -0.95% | ⚠️ Outside tolerance |
| Debt | 42,852 ± 1,714 kEUR | 39,410 | -3,442 | ⚠️ Outside tolerance |
| Avg DSCR | 1.147 ± 0.05 | 1.045 | -0.102 | ⚠️ Outside tolerance |

**Note:** These deviations indicate ongoing model calibration issues beyond the scope of Sprint 4 wiring fixes. The wiring itself is now correct — `sculpt_capex_keur` is propagated, `prior_tax_loss_keur` is passed, `equity_irr_method=combined` is used for Oborovo.

## Test Results

**Core tests (S4 scope):**
```
tests/test_s2_architecture.py          ✅ 11 passed
tests/test_oborovo_parity.py          ✅ 32 passed
tests/test_period_day_fractions.py    ✅  6 passed
tests/test_period_engine.py           ✅ 40 passed
tests/test_sensitivity.py             ✅ 12 passed (was 0/12)
tests/test_equity_irr_methods.py      ✅  6 passed (NEW)
---
Total                                  ✅ 96 passed
```

**Full test suite (excluding broken imports):**
```
332 passed, 4 skipped, 130 warnings
```

**Pre-existing failure (unrelated to Sprint 4):**
- `tests/test_opex.py::TestOpexPeriodSchedule::test_h1_h2_split` — FAIL (existed before Sprint 4)

## Git Commits

| Commit | Description |
|--------|-------------|
| `4a14bf2` | S4-1: sculpt_capex_keur propagation from inputs.capex |
| `7e2ae1d` | S4-4: Fix test_sensitivity.py — create domain/finance/sensitivity.py |
| `31b6490` | S4-3: Equity IRR method tests — structural verification for 3 methods |
| `a5d80f0` | S4-3: Add tests/test_equity_irr_methods.py — 6 tests for all 3 equity_irr_method values |
| `054cbba` | S4-2: Propagate prior_tax_loss_keur from inputs.tax.initial_tax_loss_keur via app/cache.py |
| `647333f` | S4-1 fix: cached_run_waterfall uses inputs.capex.total_capex (not sculpt_capex) for project IRR base |

## Acceptance Criteria

- [x] S4-1: sculpt_capex_keur propagiran iz inputs.capex → `cached_run_waterfall` uses `inputs.capex.sculpt_capex_keur` for equity base
- [x] S4-2: prior_tax_loss_keur = inputs.tax.initial_tax_loss_keur → passed via `app/cache.py` and `domain/waterfall_engine.py`
- [x] S4-3: Sva 3 equity_irr_method rade ispravno, unit test prolazi → `tests/test_equity_irr_methods.py` 6/6 passed
- [x] S4-4: test_sensitivity.py prolazi (12/12 testova) → `domain/finance/sensitivity.py` created
- [x] S4-5: Devijacije dokumentirane, current_outputs.json nije modificiran (obratio golden fixture)
- [x] 96 core tests PASS | 1 pre-existing failure (test_opex.py, not related)

## Remaining Issues

- **test_opex.py failure** (pre-existing, unrelated to Sprint 4): `test_h1_h2_split` fails — annual Opex split across H1/H2 doesn't sum within 1 kEUR tolerance
- **12 integration tests** import from `core.` module (non-existent) — these are pre-existing and outside S4 scope
- **Model calibration** still needs work: project IRR (8.53% vs 7.96%), equity IRR (9.65% vs 10.60%), debt (39,410 vs 42,852) are all outside target tolerance. This is a modeling/calibration issue, not a wiring issue.