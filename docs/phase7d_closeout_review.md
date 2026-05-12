# Phase 7D Closeout Review

**Phase:** 7D — Multi-Investor Capital Stack Foundation
**Status:** ✅ Complete — merged to `main`
**Date:** 2026-05-12
**Test Suite:** 2878 passed | 1 skipped | 1 xfailed | 0 failed

---

## 1. Phase 7D Components Completed

| Sub-phase | Module | File | PR |
|-----------|--------|------|-----|
| 7D-1 | Investor registry | `domain/sponsor/investor_registry.py` | #55 |
| 7D-2 | Capital stack | `domain/sponsor/capital_stack.py` | #55 |
| 7D-3 | Multi-investor waterfall runner | `domain/sponsor/multi_investor_waterfall_runner.py` | #55 |
| 7D-4 | Test suite | `tests/test_multi_investor_capital_stack.py` | #55 |

---

## 2. Investor Registry Summary

**File:** `domain/sponsor/investor_registry.py`

### InvestorRole
A string-based role type supporting three roles:
- `LP` — Limited Partner (passive, receives preferred return + ROC + residual)
- `GP` — General Partner (active, receives promote + residual)
- `CO_INVESTOR` — Co-investor alongside LP (same economic terms as LP)

### InvestorEntry
Immutable entry for a single investor:
- `investor_id: str` — unique identifier
- `role: InvestorRole` — LP / GP / CO_INVESTOR
- `ownership_percentage: float` — economic share (0.0–1.0)
- `committed_capital_keur: float` — total committed capital

### InvestorRegistry
Frozen, validated registry of all investors:
- Validates exactly 1 GP per registry
- Validates ownership percentages sum to 1.0 (±1e-6 tolerance)
- Validates no duplicate investor IDs
- Supports CO_INVESTOR role alongside LP (exact 1 GP constraint applies)

---

## 3. Capital Stack Summary

**File:** `domain/sponsor/capital_stack.py`

### CapitalContributionEntry
Immutable record of one investor's capital contributions across periods:
- `investor_id: str`
- `contributed_by_period_keur: tuple[float, ...]` — period-by-period contributions

### CapitalStack
Aggregated capital stack across all investors:
- `total_committed_keur: float` — sum of all committed capital
- `total_contributed_by_period_keur: tuple[float, ...]` — aggregate contributions by period
- `investor_ids: tuple[str, ...]` — ordered list of investor IDs

### build_capital_stack()
Factory that constructs a `CapitalStack` from an `InvestorRegistry` and per-investor contribution maps. Validates all investors have the same number of contribution periods.

---

## 4. Multi-Investor Waterfall Architecture

**File:** `domain/sponsor/multi_investor_waterfall_runner.py`

### Why NOT Sequential Per-Investor ROC Tiers

The Phase 7C waterfall runner processes tiers sequentially. If separate ROC tiers are placed sequentially (ROC_LP then ROC_GP), the first tier would consume ALL available cash before the second tier receives anything. This is incorrect.

**Solution:** A single `RETURN_OF_CAPITAL` tier with proportional sponsor shares `(LP×80%, GP×20%)`. Both investors receive their ROC simultaneously from the same pool, in proportion to their ownership.

### Two-Phase Waterfall

**Phase 1 — Per-Investor Preferred Return**
Each investor's preferred return is computed independently via `PreferredReturnCalculator` from their own invested capital history. Results are stored in `PerInvestorWaterfallResult.pref_result`. Unpaid PREF accrues as a balance carried forward.

**Phase 2 — Aggregate Waterfall**
A single aggregate waterfall runs via Phase 7C `run_waterfall()` with tiers:
- `[RETURN_OF_CAPITAL, PROMOTE, RESIDUAL]`
- ROC uses proportional sponsor shares (LP×80%, GP×20%) — single tier
- PROMOTE uses proportional sponsor shares (LP×80%, GP×20%)
- RESIDUAL uses proportional sponsor shares (LP×80%, GP×20%)

This aggregate waterfall produces correctly distributed totals across all investors.

---

## 5. Per-Investor Preferred Return Handling

Each investor's `PreferredReturnResult` is computed independently using `PreferredReturnCalculator` from:
- That investor's own `contributed_by_period_keur` (from `CapitalContributionEntry`)
- The shared `hurdle_rate_pa` and `compounding_convention`

The result (`PreferredReturnResult`) is stored per-investor in `PerInvestorWaterfallResult.pref_result`. This allows each investor to have different invested capital timelines and therefore different PREF accruals.

---

## 6. Aggregate Waterfall Handling

The aggregate waterfall is executed once via Phase 7C `run_waterfall()` with:
- A single ROC tier with proportional sponsor shares
- PROMOTE and RESIDUAL tiers with proportional sponsor shares
- `cumulative_invested_by_period_keur` from the aggregate `CapitalStack`

The aggregate result is stored in `MultiInvestorWaterfallResult.aggregate_waterfall_result` and used as the basis for per-investor result assembly.

---

## 7. Per-Investor Result Assembly

**Option A semantics** (all fields are investor-level):

For each investor, their per-investor `WaterfallAllocationResult` is assembled by filtering the aggregate result:

| Field | Formula |
|---|---|
| `available_cash_before_tier_keur` | `ownership_pct × aggregate.available_before` |
| `allocated_amount_keur` | `entry.allocation_for(inv_id)` |
| `allocated_per_sponsor_keur` | `((inv_id, amount),)` |
| `remaining_cash_after_tier_keur` | `ownership_pct × aggregate.remaining_after` |
| `total_allocated_keur` | sum of investor's allocations (not aggregate total) |
| `total_remaining_cash_keur` | `ownership_pct × aggregate.available − investor_total` |

**Invariant:** `available − allocated = remaining` holds for every tier, every period, every investor.

**Cash conservation:** The sum of all per-investor `total_allocated_keur` equals the aggregate `total_allocated_keur`.

---

## 8. Known Limitations

1. **Exactly 1 GP required.** The `InvestorRegistry` validates exactly one GP. Multiple GPs or zero GPs are rejected. This matches the current project scope (single sponsor).

2. **No CO_INVESTOR ROC priority.** CO_INVESTOR is treated identically to LP in the waterfall (same proportional share). No separate ROC priority tier for co-investors exists.

3. **PREF uses aggregate hurdle_rate_pa.** All investors share the same hurdle rate from `MultiInvestorWaterfallInputs.hurdle_rate_pa`. Per-investor hurdle rates are not supported.

4. **No per-investor capital account persistence.** The capital account is derived from the aggregate result. A separate per-investor capital account display/service layer is not yet built.

5. **RESIDUAL tier not yet wired.** The aggregate waterfall has a RESIDUAL tier but it is not connected to the per-investor result assembly in the current implementation.

---

## 9. Phase 7E Readiness Assessment

**Phase 7E: Persistence Foundation**

| Dependency | Status | Notes |
|---|---|---|
| Investor registry domain | ✅ Ready | Frozen/validated, no persistence coupling |
| Capital stack domain | ✅ Ready | Pure computation, no persistence coupling |
| Multi-investor runner domain | ✅ Ready | Returns plain dataclasses, persistence-agnostic |
| Per-investor result structures | ✅ Ready | `PerInvestorWaterfallResult`, `WaterfallAllocationResult` are plain dataclasses |
| Preferred return per investor | ✅ Ready | `PreferredReturnResult` stored per investor |
| Aggregate waterfall integration | ✅ Ready | Uses Phase 7C `run_waterfall()` unchanged |

**No blockers for Phase 7E.** The domain layer is clean and persistence-agnostic.

---

## 10. Recommended Phase 7E Implementation Order

1. **Persist `InvestorRegistry`** — add `InvestorRegistry` to the scenario model and repository (save/load)
2. **Persist `CapitalStack`** — add `CapitalStack` to scenario model and repository
3. **Extend `ScenarioModel` with multi-investor fields** — add `investor_registry`, `capital_stack`, `hurdle_rate_pa`, `gp_promote_share`, `compounding_convention`
4. **Update waterfall inputs construction** — build `MultiInvestorWaterfallInputs` from persisted scenario model
5. **Update `run_sponsor_waterfall`** — route to `run_multi_investor_waterfall()` when multi-investor mode is active
6. **Update export/UI** — wire per-investor results to Excel export and Streamlit display
7. **Add migration** — migrate existing single-investor scenarios to the multi-investor model

**Note:** Items 6–7 are out of scope for Phase 7E Persistence Foundation per the agreed phase boundaries.
