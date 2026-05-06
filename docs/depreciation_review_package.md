# Depreciation Branch Review Package

## Branch Identity
- **Branch**: `feature/capex-depreciation-integration`
- **Latest commit**: `35b7e6b` (refactor(tests): split directionality tests...)
- **Status**: NOT merged — awaiting external technical review

---

## Files Added / Modified

### New Files
| File | Purpose |
|---|---|
| `app/depreciation_engine.py` | `generate_schedule()` — asset class → depreciation life mapping, straight-line schedule |
| `tests/test_depreciation_engine.py` | 18 unit tests for `DepreciationEngine` and `CapexLineItem` |
| `tests/test_depreciation_wiring.py` | 4 behavioral tests — proves wiring is active |
| `docs/depreciation_integration_status.md` | Wiring map, simplifications, what's implemented |
| `docs/pre_depreciation_merge_review.md` | Original findings, what was fixed, questions for reviewer |

### Modified Files
| File | Change |
|---|---|
| `app/ui_runner.py` | Calls `generate_schedule()` when `advanced_capex_line_items` provided; injects `advanced_capex_depreciation_schedule` into `WaterfallRunConfig` |
| `app/waterfall_core.py` | Reads `advanced_capex_depreciation_schedule` from `WaterfallRunConfig`; builds `depr_by_period`; applies to tax shield calculation |
| `app/waterfall_runner.py` | Passes `advanced_capex_depreciation_schedule` to `run_waterfall_v3_core()` |

---

## Wiring Flow

```
advanced_capex_line_items
    │
    ▼
generate_schedule(list(advanced_capex_line_items), total_periods=horizon_years)
    │
    ▼  Returns DepreciationSchedule (annual, by asset class)
DepreciationSchedule
    │
    ▼  Injected into WaterfallRunConfig
WaterfallRunConfig(advanced_capex_depreciation_schedule=DepreciationSchedule)
    │
    ▼
run_waterfall_v3_core(..., advanced_capex_depreciation_schedule=DepreciationSchedule)
    │
    ▼  waterfall_core.py lines ~104-108
depr_by_period[p] = sum(depr for each asset active in period p)
tax_shield[p] = depr_by_period[p] * tax_rate
```

---

## Test Coverage

### Unit Tests (18 tests)
- `test_depreciation_engine.py`: engine lifecycle, asset class mapping (GENERATION→25y, GRID→20y, etc.), schedule generation, period ≥ life edge case

### Behavioral/Wiring Tests (4 tests)
- `test_advanced_capex_produces_different_tax_shield_than_legacy` — FAILS if `generate_schedule()` not called
- `test_legacy_path_unchanged_without_advanced_capex`
- `test_advanced_capex_changes_taxable_income`
- `test_depreciation_schedule_affects_equity_irr`

### Smoke Results (verified 2026-05-07)
- Solar Base: IRR=0.1040, tax shield=12,398 kEUR
- Solar Downside: IRR=0.0812
- Solar + AdvCAPEX: IRR=0.0152, tax shield=5,233 kEUR
- **Tax shield diff: 7,165 kEUR** — proves wiring is active ✅

---

## Known Simplifications

| Item | Treatment | Reason |
|---|---|---|
| Inverter | GENERATION → 25y linear | Simplified — not separately modeled |
| Contingency | 5y linear | Conservative, contract-dependent |
| Mid-year convention | None | All depreciation starts at period 0 |
| Financial vs tax depreciation | Not separated | Single straight-line used for both |
| Inflation adjustment | None | Fixed basis, no indexation |

---

## Known Remaining Risks

1. **Golden outputs may drift** — recalibration may be needed vs expected values
2. **Excel export** — doesn't yet show per-asset-class depreciation breakdown
3. **`horizon_years`** — sourced from `project.info.horizon_years` — needs Wind verification
4. **BESS/Portfolio** — not yet supported in depreciation path

---

## Questions for Reviewer

1. Is the inverter grouping under GENERATION (25y) acceptable for MVP, or does it need separate 10y treatment?
2. Should contingency really be 5y, or is this too conservative/aggressive?
3. Any concerns with the tax shield integration approach in `waterfall_core.py`?
4. Should a mid-year convention be added (half-year depreciation in year 1)?
5. Is the single-schedule (no financial/tax split) acceptable for the target tax jurisdiction?
