# Phase 8: Depreciation Canonical Wiring — Hardening & Validation

**Branch:** `phase8-depreciation-canonical-wiring`  
**From:** `main` (PR #114 merge)  
**Date:** 2026-05-20

---

## 1. What Was Done

This branch wires the canonical `DepreciationEngine` (domain/depreciation/engine.py)
into the runtime waterfall when `use_depreciation_canonical_engine=True`,
replacing the legacy aggregate `depreciation_keur` and
`tax_depreciation_audit_keur` fields with per-asset-class canonical values.

**Files:**
- `domain/depreciation/canonical_wiring.py` — new module: `CanonicalDepreciationWiringResult`,
  `build_canonical_depreciation_wiring()`, `wire_canonical_depreciation_into_waterfall()`
- `app/waterfall_core.py` — added `use_depreciation_canonical_engine` parameter;
  post-processing canonical call after `run_waterfall()` completes
- `app/waterfall_runner.py` — added flag to `WaterfallRunConfig`; reads from
  `ProjectInfo.use_depreciation_canonical_engine` via `from_inputs()`
- `domain/inputs.py` — added `use_depreciation_canonical_engine` to `ProjectInfo`
- `tests/test_depreciation_canonical_wiring.py` — new test suite (27 tests)

**R99/R102:** BLOCKED — only P&L (depreciation_keur) and tax-shield
(tax_depreciation_audit_keur) fields are affected.

---

## 2. Flag Semantics

`use_depreciation_canonical_engine=False` (default):
```
WaterfallResult ← legacy run_waterfall() with CapexItem-based depreciation
                   → depreciation_keur = aggregate legacy depreciation
                   → tax_depreciation_audit_keur = legacy tax depreciation
```

`use_depreciation_canonical_engine=True`:
```
WaterfallResult ← legacy run_waterfall() with CapexItem-based depreciation
                   ↓  (post-processing)
                 DepreciationEngine.compute(DepreciationEngineInputs
                            built from CapexItem asset classes)
                   ↓  (in-place override of depreciation fields only)
                 WaterfallResult with canonical book + tax depreciation
```

The canonical call is a **post-processing adapter** — it runs after the full
legacy waterfall so all cash-flow feedback loops are preserved. This design
mirrors the SHL canonical wiring pattern from Phase 8.1.

### Fields That Change (when flag=True):
- `WaterfallPeriod.depreciation_keur` ← canonical book depreciation
- `WaterfallPeriod.tax_depreciation_audit_keur` ← canonical tax depreciation
- `result._canonical_depreciation_wiring` ← full `CanonicalDepreciationWiringResult`
  with per-period arrays and audit metadata

### Fields That Do NOT Change:
- Senior debt, SHL, DSRA, distributions, DSCR, IRR
- Tax payable or cash tax (handled separately by `use_tax_bridge_engine`)
- R99/R102 gates

---

## 3. Architecture

### DepreciationEngineInputs
The canonical engine accepts:
- `asset_classes: Tuple[AssetClassConfig, ...]` — one per CapexItem
- `policies: dict[str, DepreciationPolicy]` — derived from CapexItem asset_class
  via `_TAX_LIFE_YEARS_MAP` (Bosnia/Croatia tax regime)
- `period_count: int` — semiannual operating periods = horizon_years × 2
- `cod_period: int` — defaults to 2 (first operating semiannual period)

### Tax vs Book Lives
| Asset Class | Book Life | Tax Life |
|---|---|---|
| solar_panels | 25 yr | 25 yr |
| wind_turbines | 25 yr | 25 yr |
| bess_cells | 10 yr | 10 yr |
| bess_power_electronics | 15 yr | 15 yr |
| civil_grid | 30 yr | 30 yr |
| soft_costs | 5 yr | 5 yr |
| financial_costs | 14 yr | 14 yr |
| land | 0 yr (non-depreciable) | 0 yr (non-depreciable) |
| other/grid/epc/generation | 20 yr fallback | 20 yr fallback |

---

## 4. Test Coverage

| Test Class | Tests | Description |
|---|---|---|
| `TestDepreciationCanonicalFlagDefault` | 2 | Flag defaults to False |
| `TestLegacyBehaviorDepreciationFlagFalse` | 4 | Legacy unchanged when flag=False |
| `TestCanonicalDepreciationSmoke` | 4 | Canonical engine runs when flag=True |
| `TestTuhoDepreciationCanonicalRegression` | 4 | TUHO regression vs baseline |
| `TestOborovoDepreciationCanonicalRegression` | 4 | Oborovo regression vs baseline |
| `TestDepreciationValidation` | 4 | Non-negative book + tax depreciation |
| `TestR99R102BlockedDepreciation` | 2 | R99/R102 not promoted |
| `TestNoOtherWaterfallChanges` | 3 | Senior debt, distributions unchanged |
| `TestDepreciationWiringAudit` | 3 | Audit row totals reconcile |

---

## 5. Validation

See `reports/phase8_depreciation_canonical_wiring_flag_comparison.csv`
for the full comparison table.

Summary:
- TUHO debt: 65,826 kEUR (unchanged ±0.0%)
- TUHO equity IRR: 11.15% (unchanged)
- TUHO avg DSCR: 1.554 (unchanged)
- Oborovo debt: 63,501 kEUR (unchanged ±0.0%)
- Oborovo equity IRR: 9.17% (unchanged)
- Oborovo avg DSCR: 1.229 (unchanged)
- All book and tax depreciation values: non-negative
- R99/R102: BLOCKED (not in result attributes)

---

## 6. Backward Compatibility

- `use_depreciation_canonical_engine=False` is the default — all existing
  code paths are unchanged
- `use_tax_bridge_engine` continues to work independently
- Canonical SHL wiring (`use_shl_canonical_engine`) is independent of
  canonical depreciation wiring
- The canonical DepreciationEngine itself remains unchanged (offline-only
  computation path); only the wiring layer is new

---

## 7. R99/R102 Audit

R99/R102 fields are **not exposed** as runtime `WaterfallResult` attributes
when either canonical engine is enabled. The audit bridge fields in
`WaterfallPeriod` (e.g., `r99_fcf_for_distribution_keur`, `r102_fcf_for_shl_keur`)
are populated by the legacy waterfall engine's internal computation and are
**not modified** by canonical wiring.

This maintains the Phase 8 design constraint: canonical engines are
**post-processing adapters**, not runtime cash-flow routers.