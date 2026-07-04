# V2-3 Financial Engine Extraction

**Branch**: `v2-3-financial-engine-extraction`  
**Status**: Complete  
**Pattern**: Forward shim — `finco_core/` re-exports from `domain/`

---

## Approach

V2-3 uses the **forward-shim pattern**:

- `finco_core/*/  __init__.py` files are populated with `from domain.xxx import (...)` statements
- `domain/` modules remain the authoritative definitions — no code was moved or copied
- All financial engine APIs are now accessible under both `domain.*` and `finco_core.*` paths
- Behavioural identity is trivially guaranteed: the same objects are referenced from both paths

This is zero-regression: no financial formula was changed, no object was duplicated.

---

## Modules Extracted

| `finco_core` package | Source domain module(s) | Key exports |
|---|---|---|
| `finco_core.engine` | `domain.period_engine`, `domain.distribution_account` | `PeriodEngine`, `PeriodMeta`, `DistributionAccountEngine`, gate functions |
| `finco_core.waterfall` | `domain.waterfall.*` | `WaterfallPeriod`, `run_waterfall`, `WaterfallResult`, `DSRAEngineResult`, `TaxPeriodResult` |
| `finco_core.tax` | `domain.tax.*` | `SPVTaxEngineInputs`, `run_spv_tax_engine`, LCF, ATAD, HoldCo, templates |
| `finco_core.debt` | `domain.financing.*`, `domain.senior_debt_sizing.*` | `iterative_sculpt_debt`, `AmortizationResult`, `dscr`, `llcr`, `plcr`, `SeniorDebtSizingEngine` |
| `finco_core.depreciation` | `domain.depreciation.*` | `DepreciationEngine`, `build_depreciation_ledger`, `AssetClassConfig` |
| `finco_core.shl` | `domain.shl.*`, `domain.shl_fcf_waterfall` | `ShlEngine`, `SHLFCFWaterfallPeriodResult`, `compute_shl_fcf_waterfall_period` |
| `finco_core.sponsor` | `domain.sponsor.*`, `domain.returns.*` | `xirr`, `xnpv`, `build_sponsor_cashflows`, `SponsorWaterfallTier`, `xirr_with_convergence` |
| `finco_core.validation` | `domain.validation` | `ValidationIssue`, `ModelWarning`, `validate_project_inputs` |

---

## Dependency Graph

```
finco_core.engine
  └── domain.period_engine
  └── domain.distribution_account (→ domain.distribution_account.*)

finco_core.waterfall
  └── domain.waterfall.waterfall_engine
  └── domain.waterfall.cash_flow
  └── domain.waterfall.dsra_engine
  └── domain.waterfall.shl_engine
  └── domain.waterfall.tax_engine
  └── domain.waterfall.reserves

finco_core.tax
  └── domain.tax (→ domain.tax.*)

finco_core.debt
  └── domain.financing (→ domain.financing.*)
  └── domain.senior_debt_sizing (→ domain.senior_debt_sizing.*)

finco_core.depreciation
  └── domain.depreciation (→ domain.depreciation.*)

finco_core.shl
  └── domain.shl (→ domain.shl.*)
  └── domain.shl_fcf_waterfall

finco_core.sponsor
  └── domain.returns.xirr
  └── domain.returns.xnpv
  └── domain.returns.sponsor_cashflows
  └── domain.sponsor.sponsor_waterfall_tier
  └── domain.sponsor.preferred_return_calculator
  └── domain.sponsor.waterfall_allocation_result
  └── domain.sponsor.xirr

finco_core.validation
  └── domain.validation
```

---

## Parity Guarantee

Forward shims produce trivial identity parity:

- `finco_core.waterfall.WaterfallPeriod is domain.waterfall.waterfall_engine.WaterfallPeriod` → `True`
- Same Python object, same memory address, same `__hash__`, same `__eq__`
- No serialization, no copying, no reconstruction

---

## Known Temporary Dependency

At runtime, all `finco_core.*` packages import from `domain/`. This is intentional and expected during V2-3. The dependency direction will be reversed in V2-4.

**V2-4 plan**:
1. Copy authoritative code into `finco_core/*/` submodules
2. Replace `domain/*/` content with `from finco_core.xxx import (...)` shims
3. Verify object identity tests still pass
4. Run full parity suite

---

## Files Changed in V2-3

Only `__init__.py` files were modified. No new non-init `.py` files were created. No `domain/` files were changed.

- `finco_core/engine/__init__.py`
- `finco_core/waterfall/__init__.py`
- `finco_core/tax/__init__.py`
- `finco_core/debt/__init__.py`
- `finco_core/depreciation/__init__.py`
- `finco_core/shl/__init__.py`
- `finco_core/sponsor/__init__.py`
- `finco_core/validation/__init__.py`
- `docs/V2_ENGINE_EXTRACTION.md` (this file)
- `docs/V2_IMPORT_AUDIT.md` (status updated)
