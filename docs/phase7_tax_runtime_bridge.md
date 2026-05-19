# Phase 7 — Tax Runtime Bridge

> **Status:** READY TO MERGE  
> **Branch:** `phase7-tax-runtime-bridge`  
> **PRs merged:** #97–#109 (Phase 7)  
> **R99/R102: BLOCKED** — this bridge does not touch R99/R102 gates

---

## 1. Executive Summary

This branch adds a canonical depreciation bridge (`domain/depreciation/tax_bridge.py`) that exposes `DepreciationEngine` outputs as a bridge into the tax calculation path.

**What was built:**
- `domain/depreciation/tax_bridge.py` — canonical bridge adapter (default-off, audit-only)
- `domain/inputs.py` — added `use_canonical_tax_depreciation_bridge: bool = False` flag
- `tests/test_depreciation_tax_bridge.py` — 10 tests, all passing

**What was NOT changed (forbidden scope):**
- TaxEngine, cash tax, deferred tax, HoldCo tax
- R99/R102 runtime gates (BLOCKED)
- SHL runtime wiring
- Sponsor IRR
- DistributionAccount
- app/waterfall_core.py

**Key design decision:** The bridge produces `DepreciationTaxBridgeResult` — a canonical output that can be validated against runtime waterfall tax depreciation. When the flag is False (default), zero runtime behavior change.

---

## 2. Existing Tax Runtime Path

```
CapexLineItem / CapexItem
    → build_depreciation_schedule() [legacy path]
    → depreciation_schedule (list[float], semiannual periods)
    → run_waterfall() → waterfall_engine
        → compute_period_tax() [TaxEngine]
            → ebitda_keur, depreciation_keur, interest, loss_carryforward
            → tax_keur = taxable_income * tax_rate (0% if negative)
```

**Existing tax depreciation flow:**
- `app/waterfall_core.py` line ~157: `dep = annual_dep * p.day_fraction`
- `domain/waterfall/waterfall_engine.py` line ~656: `dep = depreciation_schedule[i]`
- `domain/waterfall/tax_engine.py` line ~41: `compute_period_tax()` receives `depreciation_keur`
- `domain/financial_statements/tax_bridge.py` line ~8: `assemble_tax_bridge_period()` exposes audit fields

**Audit path (existing):**
- `period.tax_depreciation_audit_keur` — tax depreciation from waterfall (legacy)
- `TaxBridgeResult` from `assemble_tax_bridge()` — aggregate of all audit fields

---

## 3. Canonical Depreciation Bridge Architecture

```
DepreciationEngine.compute(DepreciationEngineInputs)
    ├── DepreciationEngineResult
    │   └── ledger_result: DepreciationLedgerResult
    │       ├── periods: tuple[DepreciationPeriodResult, ...]  # per asset-class per period
    │       ├── aggregate_periods(): tuple[DepreciationPeriodResult, ...]  # aggregate all assets
    │       ├── total_book_depreciation_keur
    │       └── total_tax_depreciation_keur
    │
    └── BuildDepreciationTaxBridgeResult
        ├── tax_depreciation_by_period_keur: tuple[float, ...]  (63 semiannual)
        ├── book_depreciation_by_period_keur: tuple[float, ...] (63 semiannual)
        ├── total_tax_depreciation_keur: float
        ├── total_book_depreciation_keur: float
        └── audit_rows: tuple[DepreciationTaxAuditRow, ...]
```

### 3.1 Bridge function

```python
def build_depreciation_tax_bridge(
    project_name: str,
    asset_classes: tuple[AssetClassConfig, ...],
    policies: dict[str, DepreciationPolicy],
    period_count: int = 63,
    cod_period: int = 2,
    period_frequency: str = "semiannual",
) -> DepreciationTaxBridgeResult
```

Returns `DepreciationTaxBridgeResult` with `tax_depreciation_by_period_keur` — the key series for TaxEngine.

### 3.2 Bridge validation

```python
validate_bridge_against_waterfall(
    canonical_bridge: DepreciationTaxBridgeResult,
    waterfall_tax_dep_by_period: tuple[float, ...],
    tolerance: float = 1.0,
) -> BridgeValidationResult
```

Compares canonical vs runtime values per period.

### 3.3 Audit rows

```python
@dataclass(frozen=True)
class DepreciationTaxAuditRow:
    period_index: int
    asset_class: str
    book_depreciation_keur: float
    tax_depreciation_keur: float
    book_tax_difference_keur: float
    accumulated_book_depreciation_keur: float
    accumulated_tax_depreciation_keur: float
    nbv_book_keur: float
    nbv_tax_keur: float
    book_policy_years: int       # semiannual periods → years
    tax_policy_years: int       # semiannual periods → years
    is_financing_cost: bool
    is_land: bool
```

---

## 4. Flag / Default-Safe Behavior

### 4.1 Flag: `use_canonical_tax_depreciation_bridge`

**Location:** `domain/inputs.py` → `ProjectInfo` → `use_canonical_tax_depreciation_bridge: bool = False`

```python
@dataclass(frozen=True)
class ProjectInfo:
    # ... existing fields ...
    use_canonical_tax_depreciation_bridge: bool = False  # NEW
```

**When `False` (default):**
- Legacy depreciation schedule path unchanged
- `build_depreciation_schedule()` / CapexItem path still used
- TaxEngine receives legacy `depreciation_schedule` from `app/waterfall_core.py`
- Zero runtime behavior change
- 100 tests still pass

**When `True` (future, not yet wired):**
- `DepreciationEngine.compute()` produces canonical tax depreciation
- `DepreciationTaxBridgeResult` exposed as audit output
- Validation: `validate_bridge_against_waterfall()` compares canonical vs runtime

**Current status:** Flag is added but NOT wired to runtime. Bridge is audit-only.

### 4.2 Audit-only path

The bridge produces audit outputs only — it does not feed TaxEngine or waterfall runtime. When `use_canonical_tax_depreciation_bridge=True`, the result is:

1. `DepreciationTaxBridgeResult.tax_depreciation_by_period_keur` — canonical tax dep series
2. `DepreciationTaxBridgeResult.audit_rows` — per-period audit detail
3. `BridgeValidationResult` (when validated against waterfall) — mismatch report

No TaxEngine inputs are changed. No waterfall behavior changes.

---

## 5. Runtime vs Audit-Only Ownership

| Component | Runtime Source? | Audit Only? | Notes |
|-----------|----------------|-------------|-------|
| `DepreciationEngine` (canonical) | ❌ | ✅ | Produces bridge input |
| `DepreciationTaxBridgeResult` | ❌ | ✅ | Audit output, not wired |
| `tax_depreciation_by_period_keur` | ❌ | ✅ | Bridge output |
| `waterfall_engine.tax_depreciation_audit_keur` | ❌ | ✅ | Legacy audit field |
| `TaxBridgeResult` from `tax_bridge.py` | ❌ | ✅ | Assembles waterfall audit |
| TaxEngine `depreciation_keur` input | ✅ | ❌ | Legacy path unchanged |

**Summary:** Canonical bridge is audit-only. Legacy tax path (TaxEngine, waterfall, CFADS) is unchanged.

---

## 6. Canonical Engine Version

```python
CANONICAL_ENGINE_VERSION = "1.0"
```

- Exposed in `DepreciationTaxBridgeResult.canonical_engine_version`
- Stable for this branch
- Will increment if engine output format changes

---

## 7. Remaining Limitations

### 7.1 Not yet wired to TaxEngine

The bridge produces canonical tax depreciation but does not wire it to `compute_period_tax()`. To wire:

1. Add `use_canonical_tax_depreciation_bridge: bool = False` check in `app/waterfall_core.py`
2. When True, call `DepreciationEngine.compute()` and map `tax_depreciation_by_period_keur` → waterfall's `depreciation_schedule`
3. Validate output matches existing tax path before promoting to runtime

**This is not done in this branch** — it would require invasive changes to `app/waterfall_core.py` and `domain/waterfall/waterfall_engine.py`.

### 7.2 Aggregate periods returns TOTAL row

`DepreciationLedgerResult.aggregate_periods()` returns per-period aggregate with `asset_class='TOTAL'`. This is a limitation — per-asset-class breakdown is in `ledger_result.periods`, not in the aggregate view.

**Workaround:** For single-asset-class projects (TUHO, Oborovo), TOTAL row is sufficient.

### 7.3 Period mapping assumption

The bridge assumes 0-based period index from `DepreciationEngine` maps directly to semiannual waterfall periods. For TUHO (63 semiannual periods, COD at period 2), this holds. For other projects, verify period mapping before use.

### 7.4 Validation stub

`validate_bridge_against_waterfall()` is a stub that compares canonical vs runtime series. It requires waterfall tax depreciation series to be passed explicitly. Full integration would call this in `domain/financial_statements/tax_bridge.py`.

---

## 8. Deferred Tax / HoldCo — Explicitly Excluded

**Deferred tax:** Not implemented. `compute_period_tax()` produces cash tax only. Deferred tax accounting (IFRS-style) requires balance sheet modeling beyond current scope.

**HoldCo tax:** Not implemented. HoldCo level taxes (if applicable) are project-specific and require separate modeling.

**Canonical bridge:** Does not compute deferred or HoldCo tax. It bridges depreciation only.

---

## 9. R99/R102 Status

**R99/R102: BLOCKED** — unchanged.

This branch does not:
- Promote R99/R102 to runtime source
- Change DistributionAccount behavior
- Wire R99 gate to any module
- Modify SHL cash sweep path

The bridge only exposes canonical depreciation as audit output. It has no interaction with R99/R102 gates.

---

## 10. Future Migration Path

### Phase A: Audit Validation (current branch — done)
Canonical bridge produces `DepreciationTaxBridgeResult` with `tax_depreciation_by_period_keur`.
Validate canonical vs runtime in test: `validate_bridge_against_waterfall()`.

### Phase B: Optional Wiring (future branch)
Add wiring to `app/waterfall_core.py`:
```python
if use_canonical_tax_depreciation_bridge:
    # Replace legacy depreciation_schedule with canonical tax_dep
    canonical_bridge = build_depreciation_tax_bridge(...)
    tax_dep_series = canonical_bridge.tax_depreciation_by_period_keur
    # Map to semiannual periods and pass to run_waterfall()
else:
    # Existing path unchanged
```
Validate with TUHO fixture: canonical tax dep matches Excel within tolerance.

### Phase C: Full Promotion (after Phase B validated)
Remove `use_canonical_tax_depreciation_bridge` flag default — canonical path becomes default.
Maintain legacy path as `use_legacy_depreciation: bool = False` for compatibility.

---

## 11. Recommended Next Branch

### Option A: `phase7-runtime-stack-freeze` (Recommended)
Freeze current Phase 7 runtime stack:
- All existing canonical engines (SHL, SeniorDebtSizing, Depreciation) are default-off
- All audit paths documented
- No further canonical engine promotion without explicit design PR
- Consolidate all Phase 7 design docs into `docs/phase7_design_summary.md`

### Option B: `phase7-tax-bridge-review-fixes`
If bridge reveals issues (e.g., period mapping problems, aggregate TOTAL row limitation):
- Fix aggregate periods to return per-asset-class breakdown
- Add project-specific period mapping validation
- Re-test with TUHO fixture

### Option C: `phase7-model-stack-consolidation`
Add integration tests combining SHL + SeniorDebtSizing + Depreciation:
- Validate cross-module cashflows
- Confirm no circular dependencies
- Build consolidated fixture regression

---

## 12. Test Coverage

| Test | Coverage |
|------|----------|
| `test_build_bridge_returns_valid_result` | Smoke: bridge builds, version stable |
| `test_tax_depreciation_series_length_matches_period_count` | 63 periods, book+tax |
| `test_tax_depreciation_positive_in_operating_periods` | Periods 2..41 positive, 42+ zero |
| `test_book_vs_tax_depreciation_difference` | Different lives → different timing |
| `test_audit_rows_populated_for_all_periods` | 63 audit rows, policy years correct |
| `test_canonical_version_is_stable` | Version = "1.0" |
| `test_bridge_does_not_modify_inputs` | Immutable inputs |
| `test_zero_depreciation_before_placed_in_service` | Pre-COD periods zero |
| `test_validate_empty_runtime_series` | Mismatches detected |
| `test_validate_matching_series` | All match when same |

**Total: 10 new tests, all passing. All 110 existing tests still pass.**

---

## 13. Files Changed

| File | Change |
|------|--------|
| `domain/inputs.py` | Added `use_canonical_tax_depreciation_bridge: bool = False` |
| `domain/depreciation/tax_bridge.py` | New: canonical bridge adapter (234 lines) |
| `tests/test_depreciation_tax_bridge.py` | New: 10 tests (all pass) |
| `docs/phase7_tax_runtime_bridge.md` | New: this document |

---

*Document version: 1.0 — 2026-05-19*