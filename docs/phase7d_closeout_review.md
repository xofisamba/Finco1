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

## 4. Multi-Investor Waterfall Architecture (Updated by PR #60)

**File:** `domain/sponsor/multi_investor_waterfall_runner.py`
**Status:** PR #60 bug fixes merged (2026-05-12)

### Cascade Change (PR #60)

Previous (pre-#60) aggregate cascade was incorrect:
- `[RETURN_OF_CAPITAL, PREFERRED_RETURN, GP_CATCH_UP, PROMOTE, RESIDUAL]`
- PREF was double-counted (per-investor in Step 1 AND tier in aggregate)
- GP_CATCH_UP used proportional shares instead of GP-only
- PROMOTE used proportional ownership instead of explicit carry split

**PR #60 fix — correct 4-tier aggregate cascade:**
- `[RETURN_OF_CAPITAL, GP_CATCH_UP, PROMOTE, RESIDUAL]`
- PREFERRED_RETURN removed from aggregate (computed per-investor in Step 1 only)
- GP_CATCH_UP: sponsor_shares = 100% to GP (not proportional)
- PROMOTE: explicit carry split via `promote_shares` (GP gets `gp_promote_share`; non-GP split proportionally)
- RESIDUAL: same as PROMOTE

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

**Phase 1 — Per-Investor Preferred Return**
Each investor's preferred return is computed independently via `PreferredReturnCalculator` from their own invested capital history. Results are stored in `PerInvestorWaterfallResult.pref_result`. Unpaid PREF accrues as a balance carried forward.

**Phase 2 — Aggregate Waterfall (4 tiers, post-#60)**
A single aggregate waterfall runs via Phase 7C `run_waterfall()` with tiers:
- `[RETURN_OF_CAPITAL, GP_CATCH_UP, PROMOTE, RESIDUAL]`
- ROC: proportional sponsor shares (LP×80%, GP×20%)
- GP_CATCH_UP: sponsor_shares = 100% to GP (GP-only catch-up)
- PROMOTE: explicit carry split (LP×(1−gp_promote_share), GP×gp_promote_share)
- RESIDUAL: same carry split as PROMOTE

**Key fix (PR #60):** `lp_invested_capital_keur` field added to `WaterfallRunnerInputs`. GP catch-up threshold uses LP's committed capital (not first-period invested which was 0.0).

This aggregate waterfall produces correctly distributed totals across all investors.

---

## 8. Known Limitations (Updated by PR #60)

1. **Exactly 1 GP required.** The `InvestorRegistry` validates exactly one GP. Multiple GPs or zero GPs are rejected. This matches the current project scope (single sponsor).

2. **No CO_INVESTOR ROC priority.** CO_INVESTOR is treated identically to LP in the waterfall (same proportional share). No separate ROC priority tier for co-investors exists.

3. **PREF uses aggregate hurdle_rate_pa.** All investors share the same hurdle rate from `MultiInvestorWaterfallInputs.hurdle_rate_pa`. Per-investor hurdle rates are not supported.

4. **RESIDUAL tier now exercised in PR #60 tests.** The aggregate waterfall's RESIDUAL tier is tested in `TestLpGpAllocation` to confirm 80/20 split on final residue.

5. **PROMOTE now uses explicit carry split.** Pre-#60, PROMOTE used proportional ownership shares. Post-#60, PROMOTE uses `promote_shares` (GP gets `gp_promote_share`; non-GP investors split the residual proportionally).

6. **PREF removed from aggregate cascade.** Pre-#60, PREF was double-counted (per-investor Step 1 AND aggregate tier). Post-#60, `pref_result=None` is passed to aggregate `WaterfallRunnerInputs`.

---

## 9. Phase 7E–7F Readiness Assessment

**Phase 7E: Persistence Foundation** — ✅ Complete

| Dependency | Status | Notes |
|---|---|---|
| Investor registry domain | ✅ Ready | Frozen/validated, no persistence coupling |
| Capital stack domain | ✅ Ready | Pure computation, no persistence coupling |
| Multi-investor runner domain | ✅ Ready | Returns plain dataclasses, persistence-agnostic |
| Per-investor result structures | ✅ Ready | `PerInvestorWaterfallResult`, `WaterfallAllocationResult` are plain dataclasses |
| Preferred return per investor | ✅ Ready | `PreferredReturnResult` stored per investor |
| Aggregate waterfall integration | ✅ Ready | Uses Phase 7C `run_waterfall()` unchanged |
| `lp_invested_capital_keur` field | ✅ Ready | Added by PR #60; fixes GP catch-up threshold |
| Explicit promote shares | ✅ Ready | Added by PR #60; PROMOTE/RESIDUAL use carry split not ownership |
| PREF removed from aggregate | ✅ Ready | Added by PR #60; `pref_result=None` passed to aggregate |

**Phase 7F: Sponsor Integration Readiness** — Documentation only in this branch

| Task | Status | Notes |
|---|---|---|
| `docs/phase7f_sponsor_integration_readiness.md` | ✅ Created | This branch |
| App/orchestrator integration | ⏳ Pending | Gap: no code path from project inputs → `run_multi_investor_waterfall()` |
| SponsorSnapshot → ORM | ⏳ Pending | `SponsorSnapshot` exists in `domain/persistence/`, not wired to SQLAlchemy |
| Sponsor → Excel export | ⏳ Pending | `write_sponsor_waterfall_audit_sheets()` exists, not wired to real data |

**No blockers for Phase 7F.** The domain layer is clean and persistence-agnostic.

---

## 10. Recommended Phase 7E–7F Implementation Order

### Phase 7E complete order (reference)

1. ~~Persist `InvestorRegistry`~~ — done in Phase 7E
2. ~~Persist `CapitalStack`~~ — done in Phase 7E
3. ~~Extend `ScenarioModel` with multi-investor fields~~ — done in Phase 7E
4. ~~Update waterfall inputs construction~~ — done in Phase 7E
5. ~~Update `run_sponsor_waterfall`~~ — deferred to Phase 7F (out of 7E scope)
6. ~~Update export/UI~~ — deferred to Phase 7F (out of 7E scope)
7. ~~Add migration~~ — deferred to Phase 7F (out of 7E scope)

### Phase 7F new order (from `docs/phase7f_sponsor_integration_readiness.md`)

1. **Wire sponsor waterfall into app layer** — Create `app/sponsor_runner.py` with `SponsorRunConfig`; call `run_multi_investor_waterfall()`
2. **Wire `SponsorSnapshot` to ORM** — Add `SponsorSnapshotModel`, FK on `Scenario`, update `ScenarioRepository`
3. **Wire sponsor results to Excel export** — Pass per-investor results to `write_sponsor_waterfall_audit_sheets()`
4. **Wire to UI** — Streamlit pages: accept LP/GP config, display per-investor waterfall
5. **Add sponsor IRR** — `run_sponsor_irr()` on cashflow result
6. **Address remaining open issues** — O-1 (Oborovo/TUHO calibration), O-2 (persistence migration), O-3 (typed SponsorSnapshot)
