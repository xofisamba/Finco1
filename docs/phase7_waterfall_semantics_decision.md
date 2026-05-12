# Phase 7 Waterfall Semantics Decision

**Date:** 2026-05-12
**Status:** Decision — Option A selected
**Branch:** `phase7-waterfall-semantics-decision`
**Scope:** Architecture decision only — no implementation

---

## 1. Problem Statement

The current Phase 7D multi-investor waterfall uses proportional allocation across all tiers. The PROMOTE tier allocates `LP=80%, GP=20%` of available cash — the same split as the RETURN_OF_CAPITAL tier.

This is **not** institutional carry/promote economics. In a true 8-and-20 PE waterfall:

1. LP and GP receive their capital back (ROC)
2. LP and GP receive their preferred return (PREF, proportional)
3. **GP CATCH-UP:** 100% of remaining cash goes to GP until GP has received ~20% of total profits
4. **PROMOTE:** LP=80%, GP=20% split of all remaining profits

The current implementation conflates steps 1–4 into proportional allocation, and the GP catch-up phase is absent entirely. The PROMOTE tier is mislabeled — it behaves identically to the ROC tier.

**This is an architecture issue, not a bug.** It was noted in the Phase 7 Architecture Review as requiring a decision before external pilot use.

---

## 2. Current Behavior: Proportional Allocation with Side-Channel Preferred Return

### 2.1 Phase 7D waterfall structure

```
Aggregate tiers (all proportional, same LP=80%/GP=20% split):
  [RETURN_OF_CAPITAL, PROMOTE, RESIDUAL]
  — each tier uses proportional sponsor shares —
```

Per-investor assembly (Option A) correctly splits each aggregate tier entry into investor-level amounts. But the **underlying aggregate tiers are all proportional**, not carry-based.

### 2.2 Preferred return is a side channel

```
Phase 7D:
  Step 1: Per-investor PREF calculated separately (PreferredReturnCalculator)
           → PreferredReturnResult per investor (unpaid balance, accrued amount)
  Step 2: Aggregate waterfall [ROC, PROMOTE, RESIDUAL] — NO PREF tier
           → available_cash goes to ROC (proportional) → PROMOTE (proportional) → RESIDUAL (proportional)
```

In institutional carry, preferred return is **part of the waterfall cascade** — cash flows through ROC first, then PREF, then GP catch-up, then PROMOTE. The GP's promote allocation is computed on profits **above the preferred return threshold**.

In the current Phase 7D implementation, preferred return is computed independently and stored separately. It does not affect the waterfall allocation.

### 2.3 What "PROMOTE" currently means

| Property | Current Phase 7D PROMOTE | True PE PROMOTE |
|----------|--------------------------|-----------------|
| Trigger | All remaining cash after ROC | Cash above preferred return + catch-up threshold |
| LP share | 80% | 80% |
| GP share | 20% | 20% |
| GP catch-up | ❌ Not implemented | ✅ 100% to GP first |
| PREF in cascade | ❌ Side channel | ✅ Part of cascade |

---

## 3. Why Current PROMOTE/RESIDUAL Semantics Are Misleading

### 3.1 Naming is wrong for what it does

Calling a proportional allocation tier "PROMOTE" implies GP is earning carry — a performance fee above a preferred return threshold. The current tier earns GP 20% of all distributions regardless of whether LP has received their preferred return or not. This is not carry; it is just proportional profit-sharing.

### 3.2 GP CATCH-UP is missing

In institutional carry, after ROC and PREF, GP receives **100%** of distributions until GP's total share reaches the promote percentage of the entire profit pool. This is the "catch-up" provision that makes the carry "accelerate" GP's economics.

Current Phase 7D has a `TierType.GP_CATCH_UP` in the schema (`domain/sponsor/sponsor_waterfall_tier.py`) but it is **not used** in the multi-investor runner. The runner only builds `[ROC, PROMOTE, RESIDUAL]` — no GP_CATCH_UP tier.

### 3.3 Preferred return is disconnected from allocation

The preferred return accrual (computed by `PreferredReturnCalculator`) is not fed into the waterfall as a tier. This means:
- LP's preferred return is not tracked as a waterfall tier claim
- GP's preferred return is not tracked either (though GP typically has minimal preferred)
- The "unpaid_pref_balance" does not affect waterfall allocation priority

In institutional carry, LP's unpaid preferred return would accumulate and be paid before any GP catch-up or promote allocation.

### 3.4 Implications for pilot use

If this model is used for an actual LP/GP co-investment evaluation:
- GP economics are **overstated** in early periods (GP gets 20% before preferred return is fully paid)
- LP economics are **understated** (LP's preferred return is not protected as a first-priority claim)
- The "promote" does not actually accelerate GP's share above the preferred threshold

---

## 4. Option A: Implement True Institutional Promote/Carry Waterfall

### 4.1 Correct 8-and-20 carry waterfall cascade

```
Tier 0: RETURN_OF_CAPITAL
  - 100% to each investor until their invested capital is repaid
  - Per Phase 7C: proportional by SponsorShare within the tier
  - LP gets 80% of ROC pool, GP gets 20%

Tier 1: PREFERRED_RETURN (inside waterfall cascade)
  - Each investor receives their proportional share of accrued preferred return
  - LP=80%, GP=20% of unpaid_pref_balance
  - Only the unpaid balance receives allocations (not double-paying)
  - LP preferred return is a PRIORITY claim before GP promote

Tier 2: GP_CATCH_UP (Phase 7C tier, currently unused in Phase 7D)
  - 100% of remaining cash to GP
  - Continues until GP has received:
      GP's share of preferred return
      + GP's catch-up portion: (promote_rate / (1 - promote_rate)) × LP's total from ROC + PREF
  - For 20% promote: GP catch-up target = 0.25 × LP's accumulated distributions
  - Formula: GP_catch_up_target = (promote_rate / (1 - promote_rate)) × LP_accumulated
             For 20% promote: target = 0.25 × LP_accumulated

Tier 3: PROMOTE (true carry split)
  - LP=80%, GP=20% of all remaining distributions
  - Only reached after GP has fully caught up

Tier 4: RESIDUAL (fallback)
  - Same proportional split for any remaining cash
```

### 4.2 GP catch-up formula derivation

For a standard 8-and-20 carry with no preferred return to GP:

```
Let:
  LP_pref = LP's accrued preferred return (8% p.a. on LP invested capital)
  LP_roc  = LP's ROC received
  LP_pref_roc = LP_pref + LP_roc  (LP's total from tiers 0+1)

GP catch-up target (for 20% promote):
  GP_target = promote_rate × (LP_pref_roc + GP_pref_roc + remainder) / (1 - promote_rate)
  
  At full catch-up: GP has received promote_rate × total_pool
  For LP_share = 80%, GP_share = 20%:
    GP_catch_up_target = (0.20 / 0.80) × LP_accumulated_from_tiers_0_and_1
                       = 0.25 × LP_accumulated_from_tiers_0_and_1
```

This means: for every €1 LP receives in ROC + PREF, GP is entitled to €0.25 in catch-up (20%/80% = 0.25), before the 80/20 PROMOTE split kicks in.

### 4.3 Required changes for Option A

**Phase 7D runner changes:**
1. Add PREFERRED_RETURN as a proper waterfall tier (tier_index=1), not a side channel
2. Insert GP_CATCH_UP tier (tier_index=2) using `TierType.GP_CATCH_UP`
3. PROMOTE tier moves to tier_index=3
4. RESIDUAL tier moves to tier_index=4
5. `preferred_return_result` becomes `waterfall_inputs.pref_result` (Phase 7C style)
6. `cumulative_invested_by_period` must include all investors' capital for GP catch-up denominator

**Phase 7C changes:**
1. Ensure `TierType.GP_CATCH_UP` tier allocation logic is correct in `run_waterfall()`
2. Confirm catch-up formula: GP gets 100% until `cumulative_to_gp >= (promote_rate / (1-promote_rate)) × cumulative_to_lp`

**Testing changes:**
1. Golden test: 8-and-20 carry on simple 2-period investment
   - Invest 10,000 (LP=8,000, GP=2,000)
   - Period 1: 5,000 cash → ROC only, then PREF, then catch-up
   - Period 2: 15,000 cash → full cascade
   - Verify LP/GP splits match institutional waterfall formulas
2. Verify GP catch-up completes before PROMOTE starts
3. Verify unpaid preferred return accumulates and is paid in correct priority

---

## 5. Option B: Relabel Current Behavior as Proportional Allocation and Defer True Promote

### 5.1 Option B approach

Keep the current implementation but:
1. Rename "PROMOTE" tier → "PROFIT_SHARE" or "RESIDUAL_SHARE"
2. Rename "RESIDUAL" → "OVERFLOW" or remove it
3. Document that the model uses proportional allocation, not institutional carry
4. Add prominent documentation that preferred return is computed separately (side channel)
5. Mark "true carry" as a Phase 8 or Phase 9 future feature

### 5.2 Pros

- No implementation work in Phase 7F
- Ships on schedule
- Matches what the current code actually does

### 5.3 Cons

- The model **cannot be used for real LP/GP negotiations** with correct economics
- "PROMOTE" naming is actively misleading to finance team
- Every future user will need to be warned that the waterfall is proportional, not carry-based
- External pilot with real co-investors would require disclosure that the model doesn't implement standard carry
- Fixing it later (after data model is in production) is harder than doing it now

### 5.4 Decision criteria

| Criteria | Option A | Option B |
|----------|----------|----------|
| Correct PE economics | ✅ | ❌ |
| Ship on Phase 7F schedule | ⚠️ (requires implementation) | ✅ |
| Usable for real LP/GP deals | ✅ | ❌ |
| No misleading naming | ✅ | ❌ |
| Technical debt if deferred | Low | High |

---

## 6. Recommendation

**Option A — Implement true institutional promote/carry waterfall.**

The cost of fixing this after Phase 7F is higher than fixing it now. The current naming is misleading and the economics are wrong for real co-investment use cases. An external pilot with real capital at stake cannot use the current proportional waterfall.

**Key reasons:**
1. **PROMOTE without catch-up is not carry.** The 8-and-20 name implies catch-up provision. Without it, GP earns 20% from period 1 — before LP has even received their preferred return.
2. **Naming misleads.** Any finance team reading "PROMOTE" tier in a model output will assume institutional carry semantics. The current implementation does not deliver this.
3. **Technical debt.** The Phase 7C waterfall schema already has `TierType.GP_CATCH_UP`. Phase 7D just didn't wire it in. The schema is ready; the runner needs the logic.
4. **External pilot readiness.** cofix is targeting Phase 8 for external pilot. Fixing carry semantics after the data model is in production with scenarios and persisted snapshots is harder than doing it now.

---

## 7. Required Implementation Follow-ups

### 7.1 Phase 7F-1: Fix aggregate waterfall tier order

In `multi_investor_waterfall_runner.py`, replace:
```python
aggregate_tiers = (
    SponsorWaterfallTier(tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL, ...),
    SponsorWaterfallTier(tier_index=1, tier_type=TierType.PROMOTE, ...),       # WRONG
    SponsorWaterfallTier(tier_index=2, tier_type=TierType.RESIDUAL, ...),
)
```

With:
```python
aggregate_tiers = (
    SponsorWaterfallTier(tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL, ...),
    SponsorWaterfallTier(tier_index=1, tier_type=TierType.PREFERRED_RETURN, ...),  # ADD
    SponsorWaterfallTier(tier_index=2, tier_type=TierType.GP_CATCH_UP, ...),    # ADD
    SponsorWaterfallTier(tier_index=3, tier_type=TierType.PROMOTE, ...),
    SponsorWaterfallTier(tier_index=4, tier_type=TierType.RESIDUAL, ...),
)
```

### 7.2 Phase 7F-2: Wire PREF result into waterfall inputs

Currently `pref_result=None` in aggregate waterfall. Change to pass per-investor preferred return results into the aggregate waterfall as `WaterfallRunnerInputs.pref_result`. The Phase 7C `PreferredReturnResult` already supports multi-sponsor via `sponsor_code`.

### 7.3 Phase 7F-3: Implement GP catch-up formula

In `preferred_return_calculator.py` or `sponsor_waterfall_tier.py`, implement:
```
GP_catch_up_target = (promote_rate / (1 - promote_rate)) × LP's cumulative from ROC + PREF
```

GP receives 100% of available cash in the GP_CATCH_UP tier until `cumulative_gp >= gp_catch_up_target`.

### 7.4 Phase 7F-4: Add golden 8-and-20 tests

New test file: `tests/test_institutional_carry_waterfall.py`
- 2-period simple carry: LP=8,000, GP=2,000 invested; known profit distribution
- Verify ROC → PREF → GP_CATCH_UP → PROMOTE sequence
- Verify GP catch-up completes before PROMOTE
- Verify LP gets 80%, GP gets 20% in PROMOTE tier
- Edge: what happens if available cash runs out during catch-up (unpaid catch-up)
- Edge: GP preferred return = 0 (GP typically doesn't have pref, confirm this is handled)

### 7.5 Phase 7F-5: Naming audit

- Rename "PROMOTE" → keep "PROMOTE" (correct, just fix the tier order)
- Ensure "GP_CATCH_UP" tier is documented in `sponsor_waterfall_tier.py`
- Update `phase7d_closeout_review.md` with carry semantics correction
- Update `phase7_claude_architecture_review.md` gap list

### 7.6 Phase 7F-6: Validate existing tests still pass

All 59 Phase 7D tests will need review. The aggregate tier ordering changes mean some assertions on tier indices will need updating. Expected test impact: minimal — the per-investor proportional correctness tests (LP=80%, GP=20%) should remain valid as those are about the PROMOTE tier, not the ROC+PREF ordering.

---

## 8. Impact on Phase 7F, Phase 8, and External Pilot Readiness

### Phase 7F (Persistence Foundation — current)

If Option A is chosen, Phase 7F must incorporate the waterfall tier order changes before persistence snapshots are created. Persisting snapshots with the old (incorrect) tier order would create a migration burden.

**Recommendation:** Implement Option A changes in Phase 7F before persistence snapshots are created for the sponsor waterfall.

### Phase 7F scope additions

| Item | Impact |
|------|--------|
| Add GP_CATCH_UP tier | Small — runner change only |
| Add PREF tier to aggregate waterfall | Medium — need to wire pref_result per investor |
| GP catch-up formula | Medium — new allocation logic |
| Golden 8-and-20 tests | Small — new test file |
| Rename/adjust tests | Small — tier index assertions |

**Estimated Phase 7F delta:** +1–2 days of implementation work.

### Phase 8 (External Pilot)

Option A makes the model **usable for real LP/GP co-investment analysis**. Option B limits the model to internal use with prominent disclaimers about proportional economics.

### External Pilot Criteria Met (Option A)

- [x] Correct ROC → PREF → CATCH_UP → PROMOTE cascade
- [x] GP catch-up implemented (accelerates GP before promote)
- [x] LP preferred return has priority over GP promote
- [x] 8-and-20 naming is accurate (not misleading)
- [x] Snapshots persist correct tier structure

---

## 9. Final Decision

**SELECTED: Option A — Implement true institutional promote/carry waterfall.**

**Decision rationale:**
1. The Phase 7C waterfall schema already supports GP_CATCH_UP. The infrastructure is ready.
2. The current PROMOTE tier is misleading — it is proportional allocation, not carry.
3. Fixing carry semantics post-persistence is harder than doing it now.
4. An external pilot cannot use proportional waterfall as a substitute for carry.
5. The Phase 7F delta is manageable (+1–2 days).

**Next steps:**
1. Create Phase 7F branch from `phase7-waterfall-semantics-decision` after merge
2. Implement Option A follow-ups (sections 7.1–7.6)
3. Update `phase7d_closeout_review.md` and `phase7_claude_architecture_review.md`
4. Confirm all 2952 tests pass (with updated golden tests)
5. Proceed to Phase 7F persistence integration with correct waterfall semantics
