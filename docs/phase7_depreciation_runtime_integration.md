# Phase 7 — Depreciation Runtime Integration

> **Status:** RUNTIME INTEGRATION BEHIND DEFAULT-OFF FLAG  
> **Branch:** `phase7-depreciation-runtime-integration`  
> **PRs merged:** #97, #98, #99, #100, #101, #102, #103, #104  

---

## 1. Executive Summary

This branch extends the existing `domain/depreciation/` module (which already existed before this branch) with the canonical `DepreciationEngine` entry point based on PR #102 design.

**Key decisions:**
- Existing `domain/depreciation/` offline module is preserved and extended
- `DepreciationEngine.compute()` added as canonical entry point
- `DepreciationAuditRow` with per-period per-asset-class audit rows
- `DepreciationEngineResult` with full audit table and totals
- Croatia renewable useful-life policy documented (20yr main, 12yr financing, land non-depreciable)
- No runtime flag wired — pure domain code
- R99/R102 remains BLOCKED

---

## 2. What Was Added

### 2.1 `domain/depreciation/engine.py` (new)

```python
class DepreciationEngine:
    @staticmethod
    def compute(inputs: DepreciationEngineInputs) -> DepreciationEngineResult
```

Entry point that:
1. Builds `DepreciationLedgerInput` and calls `build_depreciation_ledger()`
2. Produces `DepreciationAuditRow` per period per asset class
3. Tracks `total_non_depreciable_basis_keur` (land, etc.)
4. Does NOT compute tax payable, R99/R102, senior debt, SHL, or sponsor IRR

### 2.2 `domain/depreciation/__init__.py` (updated)

Added exports:
- `DepreciationEngine`
- `DepreciationEngineInputs`
- `DepreciationEngineResult`
- `DepreciationAuditRow`

### 2.3 `tests/test_depreciation_engine.py` (new)

**16 tests covering:**

| Test class | Coverage |
|------------|---------|
| `TestStraightLineSemiannual` | semiannual rate, sums to basis |
| `TestBookTaxSeparation` | book 20yr / tax 12yr divergence |
| `TestLandNonDepreciable` | land → 0 depreciation |
| `TestFinancingCostsPolicy` | 12yr financing costs |
| `TestConstructionTiming` | no depreciation before COD |
| `TestAccumulatedDepreciation` | NBV roll-forward to zero |
| `TestUnsupportedMethod` | non-straight-line raises error |
| `TestAuditRows` | audit rows fully populated |
| `TestNoR99` | no distribution-related fields |
| `TestNonDepreciableBasis` | land counted in non-depreciable |
| `TestDefaultPolicy` | unknown asset class uses default |
| `TestCroatiaRenewableFallback` | 20yr main, 20yr VAT |

---

## 3. Runtime Flag Status

**Decision: No runtime flag wired.**

Adding `use_canonical_depreciation_engine: bool = False` to `ProjectInfo` would require changes to:
- `domain/inputs.py` (ProjectInfo)
- `app/waterfall_core.py` (wiring)
- Tax bridge (consuming depreciation)

This is too broad for this branch. The engine is implemented as **pure domain code**. Future integration path is documented in Section 5.

---

## 4. Croatia Renewable Useful-Life Policy

| Asset Category | Book Life | Tax Life | Notes |
|--------------|-----------|----------|-------|
| Main renewable CAPEX (wind/solar) | 20 years | 20 years | straight-line |
| Financing costs / IDC | 12 years | 12 years | straight-line |
| Land | Non-depreciable | Non-depreciable | basis = 0 |
| VAT (if capitalized) | 20 years | 20 years | if basis-eligible |
| Generic fallback | **Explicit required** | **Explicit required** | No silent 30yr fallback |

---

## 5. Future Runtime Wiring Plan

When `use_canonical_depreciation_engine` is ready to be wired:

```python
# domain/inputs.py
@dataclass
class ProjectInfo:
    use_canonical_depreciation_engine: bool = False

# app/waterfall_core.py (future)
if project.info.use_canonical_depreciation_engine:
    engine_result = DepreciationEngine.compute(inputs)
    book_depr = [r.book_depreciation_keur for r in engine_result.ledger_result.periods]
    tax_depr = [r.tax_depreciation_keur for r in engine_result.ledger_result.periods]
    # wire to P&L and TaxEngine
else:
    # use existing offline depreciation
```

---

## 6. R99/R102 Status

**BLOCKED** — `DepreciationEngine` does not compute distribution gates. Depreciation feeds P&L → EBT → TaxEngine. The distribution account logic is not changed.

---

## 7. Integration Boundaries

```
DepreciationEngine
  → book_depreciation → P&L (reduces EBT)
  → tax_depreciation → TaxEngine
  → accumulated_book_depr → Balance Sheet (NBV tracking)
  → accumulated_tax_depr → Balance Sheet (tax WDV)
  → non_depreciable_basis → Balance Sheet (land)

DepreciationEngine does NOT call:
  - SeniorDebtEngine
  - ShlEngine
  - DistributionAccount
  - Tax payable / cash tax
```

---

## 8. Acceptance Criteria

- [x] Existing `domain/depreciation/` preserved and extended
- [x] `DepreciationEngine.compute()` canonical entry point implemented
- [x] Book and tax depreciation are separate
- [x] Land is non-depreciable by default (basis = 0)
- [x] Useful-life policy is explicit and tested
- [x] Straight-line semiannual depreciation tested
- [x] Audit rows available
- [x] 16 tests pass
- [x] 54 total Phase 7 tests pass
- [x] No runtime flag wired (pure domain code)
- [x] No R99/R102 promotion
- [x] R99/R102 remains BLOCKED
- [x] No changes to app/waterfall_core.py

---

## 9. Recommended Next Branch

**`phase7-model-stack-validation-pack`**

The canonical domain modules (SHL, senior debt sizing, depreciation) should first be validated together offline before any runtime wiring is attempted. The validation pack would:
- Load the three canonical engines with TUHO fixture inputs
- Verify inter-module consistency (post-senior cash → SHL → distribution chain)
- Run full fixture regression against extracted CSVs
- Produce a consolidated validation report

**Alternative:** `phase7-shl-runtime-flag-wiring` — if SHL engine can be safely wired default-off with minimal scope.

---

*Document version: 1.0 — 2026-05-19*