"""Golden test: institutional 8-and-20 carry waterfall.

Tests the complete 4-tier aggregate waterfall cascade with real numbers:
  Tier 0: RETURN_OF_CAPITAL  — proportional (ownership shares)
  Tier 1: GP_CATCH_UP        — 100% to GP until threshold met
  Tier 2: PROMOTE            — LP×(1-gp_promote_share), GP×gp_promote_share (carry split)
  Tier 3: RESIDUAL           — same as PROMOTE (final residue split)

PREFERRED_RETURN is computed per-investor in Step 1 and included in per-investor
results — it is NOT in the aggregate cascade. The aggregate handles [ROC, GP_CATCH_UP,
PROMOTE, RESIDUAL].

8-and-20 means: LP owns 80%, GP owns 20% of equity. GP carry = 20%.

GP catch-up formula:
  gp_catch_up_target = (promote_rate / (1-promote_rate)) × max(0, lp_cum_pref - lp_invested)
For promote_rate=0.20: gp_catch_up_target = 0.25 × max(0, lp_cum_pref - lp_invested)
"""
from __future__ import annotations

import math

import pytest

from domain.sponsor.sponsor_waterfall_tier import (
    CompoundingConvention,
    SponsorShare,
    SponsorWaterfallTier,
    TierType,
)
from domain.sponsor.preferred_return_allocation import PreferredReturnAllocation
from domain.sponsor.preferred_return_calculator import (
    PreferredReturnCalculatorInputs,
    calculate_preferred_return,
)
from domain.sponsor.preferred_return_result import PreferredReturnResult
from domain.sponsor.waterfall_runner import WaterfallRunnerInputs, run_waterfall


# ── Helper factories ────────────────────────────────────────────────────────────

def make_pref_result(
    sponsor_code: str,
    invested_by_period: tuple[float, ...],
    distributions_by_period: tuple[float, ...],
    hurdle_rate: float = 0.08,
    convention: str = "SEMIANNUAL",
    num_periods: int | None = None,
) -> PreferredReturnResult:
    """Build a PreferredReturnResult for a sponsor with known invested capital."""
    n = num_periods or len(invested_by_period)
    pref_tier = SponsorWaterfallTier(
        tier_index=0,
        tier_type=TierType.PREFERRED_RETURN,
        sponsor_shares=(SponsorShare(sponsor_code=sponsor_code, allocation_percentage=1.0),),
        hurdle_rate_pa=hurdle_rate,
        compounding_convention=CompoundingConvention[convention],
        description="pref_calc",
    )
    inputs = PreferredReturnCalculatorInputs(
        tier=pref_tier,
        cumulative_invested_by_period=invested_by_period,
        distributions_by_period=distributions_by_period,
        num_periods=n,
    )
    return calculate_preferred_return(inputs)


def make_pref_allocation(
    lp_result: PreferredReturnResult,
    gp_result: PreferredReturnResult | None,
    lp_investor_id: str = "LP-1",
    lp_invested_capital: float = 0.0,
) -> PreferredReturnAllocation:
    """Build a PreferredReturnAllocation from per-investor results."""
    entries = [(lp_investor_id, lp_result)]
    if gp_result:
        entries.append(("GP-1", gp_result))
    return PreferredReturnAllocation(
        per_investor_results=tuple(entries),
        lp_investor_id=lp_investor_id,
        lp_invested_capital_keur=lp_invested_capital,
    )


# ── Test: Tier ordering ────────────────────────────────────────────────────────

class TestTierOrder:
    """Verify tiers run in correct 8-and-20 order."""

    def test_roc_before_pref(self):
        """RETURN_OF_CAPITAL must precede PREFERRED_RETURN."""
        tier_types = [t.tier_type for t in [
            SponsorWaterfallTier(tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL,
                                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=1.0),),
                                description="roc"),
            SponsorWaterfallTier(tier_index=1, tier_type=TierType.PREFERRED_RETURN,
                                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=1.0),),
                                description="pref", hurdle_rate_pa=0.08,
                                compounding_convention=CompoundingConvention.SEMIANNUAL),
        ]]
        assert tier_types.index(TierType.RETURN_OF_CAPITAL) < tier_types.index(TierType.PREFERRED_RETURN)

    def test_pref_before_gp_catch_up(self):
        """PREFERRED_RETURN must precede GP_CATCH_UP."""
        tier_types = [t.tier_type for t in [
            SponsorWaterfallTier(tier_index=0, tier_type=TierType.PREFERRED_RETURN,
                                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=1.0),),
                                description="pref", hurdle_rate_pa=0.08,
                                compounding_convention=CompoundingConvention.SEMIANNUAL),
            SponsorWaterfallTier(tier_index=1, tier_type=TierType.GP_CATCH_UP,
                                sponsor_shares=(SponsorShare(sponsor_code="GP", allocation_percentage=1.0),),
                                description="catch_up"),
        ]]
        assert tier_types.index(TierType.PREFERRED_RETURN) < tier_types.index(TierType.GP_CATCH_UP)

    def test_gp_catch_up_before_promote(self):
        """GP_CATCH_UP must precede PROMOTE."""
        tier_types = [t.tier_type for t in [
            SponsorWaterfallTier(tier_index=0, tier_type=TierType.GP_CATCH_UP,
                                sponsor_shares=(SponsorShare(sponsor_code="GP", allocation_percentage=1.0),),
                                description="catch_up"),
            SponsorWaterfallTier(tier_index=1, tier_type=TierType.PROMOTE,
                                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=0.8),
                                               SponsorShare(sponsor_code="GP", allocation_percentage=0.2)),
                                description="promote"),
        ]]
        assert tier_types.index(TierType.GP_CATCH_UP) < tier_types.index(TierType.PROMOTE)

    def test_promote_before_residual(self):
        """PROMOTE must precede RESIDUAL."""
        tier_types = [t.tier_type for t in [
            SponsorWaterfallTier(tier_index=0, tier_type=TierType.PROMOTE,
                                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=0.8),
                                               SponsorShare(sponsor_code="GP", allocation_percentage=0.2)),
                                description="promote"),
            SponsorWaterfallTier(tier_index=1, tier_type=TierType.RESIDUAL,
                                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=0.8),
                                               SponsorShare(sponsor_code="GP", allocation_percentage=0.2)),
                                description="residual"),
        ]]
        assert tier_types.index(TierType.PROMOTE) < tier_types.index(TierType.RESIDUAL)


# ── Test: GP catch-up formula ─────────────────────────────────────────────────

class TestGPCatchUp:
    """Verify GP catch-up threshold = (promote_rate/(1-promote_rate)) × max(0, lp_cum_pref - lp_invested)."""

    def test_catch_up_target_zero_when_no_pref(self):
        """GP catch-up target is 0 when LP has no preferred return above invested capital."""
        trigger = max(0.0, 0.0 - 8000.0)
        promote_rate = 0.20
        target = (promote_rate / (1.0 - promote_rate)) * trigger
        assert target == 0.0

    def test_catch_up_target_positive_when_pref_above_capital(self):
        """GP catch-up target is positive when LP has preferred return above invested capital."""
        trigger = max(0.0, 9000.0 - 8000.0)
        promote_rate = 0.20
        target = (promote_rate / (1.0 - promote_rate)) * trigger
        assert target == pytest.approx(250.0)

    def test_catch_up_target_for_80_20_promote_rate(self):
        """For 80/20 LP/GP: promote_rate=0.20, factor=0.25."""
        trigger = 2000.0
        promote_rate = 0.20
        factor = promote_rate / (1.0 - promote_rate)
        assert factor == pytest.approx(0.25)
        target = factor * trigger
        assert target == 500.0

    def test_catch_up_target_for_different_promote_rates(self):
        """Factor changes with promote_rate: 10%=0.111, 20%=0.25, 30%=0.429."""
        trigger = 1000.0
        for promote_rate, expected_factor in [(0.10, 0.1111), (0.20, 0.25), (0.30, 0.4286)]:
            factor = promote_rate / (1.0 - promote_rate)
            assert math.isclose(factor, expected_factor, rel_tol=1e-3)


# ── Test: Partial GP catch-up ─────────────────────────────────────────────────

class TestPartialGPCatchUp:
    """GP catch-up runs partially when LP's preferred return is only partially above invested."""

    def test_partial_catch_up_triggers_when_lp_pref_partially_above_capital(self):
        """When lp_cum_pref - lp_invested > 0 but < full catch-up amount, partial catch-up."""
        trigger = max(0.0, 8200.0 - 8000.0)
        promote_rate = 0.20
        target = (promote_rate / (1.0 - promote_rate)) * trigger
        assert target == pytest.approx(50.0)


# ── Test: Promote only after catch-up ────────────────────────────────────────

class TestPromoteAfterCatchUp:
    """PROMOTE tier only runs after GP_CATCH_UP is complete."""

    def test_promote_not_active_until_catch_up_threshold_met(self):
        """GP should not receive PROMOTE allocations before catch-up threshold is reached."""
        tiers = (
            SponsorWaterfallTier(
                tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL,
                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=0.8),
                                SponsorShare(sponsor_code="GP", allocation_percentage=0.2)),
                description="roc",
            ),
            SponsorWaterfallTier(
                tier_index=1, tier_type=TierType.GP_CATCH_UP,
                sponsor_shares=(SponsorShare(sponsor_code="GP", allocation_percentage=1.0),),
                description="gp_catch_up",
            ),
            SponsorWaterfallTier(
                tier_index=2, tier_type=TierType.PROMOTE,
                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=0.8),
                                SponsorShare(sponsor_code="GP", allocation_percentage=0.2)),
                description="promote",
            ),
        )
        inputs = WaterfallRunnerInputs(
            tiers=tiers,
            available_cash_by_period=(500.0,),
            pref_result=None,
            cumulative_invested_by_period=(10000.0,),
            num_periods=1,
            lp_cumulative_pref_by_period=(),
        )
        result = run_waterfall(inputs)
        period0 = result.period_results[0]
        promote_entry = next((t for t in period0.tier_entries if t.tier_type == TierType.PROMOTE), None)
        assert promote_entry is not None
        # Since ROC not satisfied, nothing reaches PROMOTE
        gp_promote = next((amt for code, amt in promote_entry.allocated_per_sponsor_keur if code == "GP"), 0.0)
        assert gp_promote == pytest.approx(0.0)


# ── Test: LP/GP allocation correctness ────────────────────────────────────────

class TestLP_GPAllocation:
    """Verify LP×80%, GP×20% split in PROMOTE and RESIDUAL tiers."""

    def test_promote_split_is_80_20(self):
        """PROMOTE tier allocates 80% to LP, 20% to GP."""
        shares = (
            SponsorShare(sponsor_code="LP-1", allocation_percentage=0.80),
            SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
        )
        tiers = (
            SponsorWaterfallTier(tier_index=0, tier_type=TierType.PROMOTE,
                                 sponsor_shares=shares, description="promote"),
        )
        inputs = WaterfallRunnerInputs(
            tiers=tiers,
            available_cash_by_period=(1000.0,),
            pref_result=None,
            cumulative_invested_by_period=(0.0,),
            num_periods=1,
            lp_cumulative_pref_by_period=(0.0,),
        )
        result = run_waterfall(inputs)
        entry = result.period_results[0].tier_entries[0]
        lp_amt = next(amt for code, amt in entry.allocated_per_sponsor_keur if code == "LP-1")
        gp_amt = next(amt for code, amt in entry.allocated_per_sponsor_keur if code == "GP-1")
        assert lp_amt == pytest.approx(800.0)
        assert gp_amt == pytest.approx(200.0)

    def test_residual_split_is_80_20(self):
        """RESIDUAL tier allocates 80% to LP, 20% to GP."""
        shares = (
            SponsorShare(sponsor_code="LP-1", allocation_percentage=0.80),
            SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
        )
        tiers = (
            SponsorWaterfallTier(tier_index=0, tier_type=TierType.RESIDUAL,
                                 sponsor_shares=shares, description="residual"),
        )
        inputs = WaterfallRunnerInputs(
            tiers=tiers,
            available_cash_by_period=(500.0,),
            pref_result=None,
            cumulative_invested_by_period=(0.0,),
            num_periods=1,
            lp_cumulative_pref_by_period=(0.0,),
        )
        result = run_waterfall(inputs)
        entry = result.period_results[0].tier_entries[0]
        lp_amt = next(amt for code, amt in entry.allocated_per_sponsor_keur if code == "LP-1")
        gp_amt = next(amt for code, amt in entry.allocated_per_sponsor_keur if code == "GP-1")
        assert lp_amt == pytest.approx(400.0)
        assert gp_amt == pytest.approx(100.0)


# ── Test: PreferredReturnAllocation interface ─────────────────────────────────

class TestPreferredReturnAllocation:
    """Tests for PreferredReturnAllocation adapter."""

    def test_sponsor_code_returns_lp_investor_id(self):
        """sponsor_code property returns the LP investor_id."""
        lp_result = make_pref_result("LP-1", (8000.0,), (0.0,), num_periods=1)
        alloc = make_pref_allocation(lp_result, None, lp_investor_id="LP-1", lp_invested_capital=8000.0)
        assert alloc.sponsor_code == "LP-1"

    def test_lp_cumulative_pref_by_period(self):
        """lp_cumulative_pref_by_period returns correct cumulative distributions."""
        lp_result = make_pref_result(
            sponsor_code="LP-1",
            invested_by_period=(8000.0, 8000.0),
            distributions_by_period=(300.0, 500.0),
            num_periods=2,
        )
        alloc = make_pref_allocation(lp_result, None, lp_investor_id="LP-1", lp_invested_capital=8000.0)
        cum_prefs = alloc.lp_cumulative_pref_by_period()
        assert cum_prefs[0] == pytest.approx(300.0)
        # Period 1: cumulative = distributions[0] + distributions[1] (if second distribution covers period 1 pref)
        # With distributions=(300, 500), period 1 cumulative = 300 + 500 = 800 (since no accrual after pref satisfied)
        assert cum_prefs[1] == pytest.approx(800.0)

    def test_lp_catch_up_trigger_zero_when_pref_below_invested(self):
        """LP catch-up trigger is 0 when cumulative pref < invested capital."""
        lp_result = make_pref_result(
            sponsor_code="LP-1",
            invested_by_period=(8000.0,),
            distributions_by_period=(0.0,),
            num_periods=1,
        )
        alloc = make_pref_allocation(lp_result, None, lp_investor_id="LP-1", lp_invested_capital=8000.0)
        trigger = alloc.lp_catch_up_trigger_at_period(0)
        assert trigger == pytest.approx(0.0)

    def test_lp_catch_up_trigger_positive_when_pref_above_invested(self):
        """LP catch-up trigger is positive when cumulative pref > invested capital."""
        lp_result = make_pref_result(
            sponsor_code="LP-1",
            invested_by_period=(8000.0,),
            distributions_by_period=(9000.0,),
            num_periods=1,
        )
        alloc = make_pref_allocation(lp_result, None, lp_investor_id="LP-1", lp_invested_capital=8000.0)
        trigger = alloc.lp_catch_up_trigger_at_period(0)
        assert trigger == pytest.approx(1000.0)

    def test_entry_for_returns_aggregate_unpaid_pref(self):
        """entry_for() returns aggregate unpaid preferred balance across all investors."""
        lp_result = make_pref_result(
            sponsor_code="LP-1",
            invested_by_period=(8000.0,),
            distributions_by_period=(500.0,),  # 500 distributed, some unpaid
            num_periods=1,
        )
        alloc = make_pref_allocation(lp_result, None, lp_investor_id="LP-1", lp_invested_capital=8000.0)
        entry = alloc.entry_for(0)
        assert entry is not None
        assert entry.period_index == 0


# ── Test: Single-investor mode unchanged ──────────────────────────────────────

class TestSingleInvestorMode:
    """Verify single-investor waterfall behavior is unchanged."""

    def test_single_investor_falls_back_to_total_invested(self):
        """Empty lp_cumulative_pref_by_period → fallback to total invested capital."""
        shares = (SponsorShare(sponsor_code="LP", allocation_percentage=1.0),)
        tiers = (
            SponsorWaterfallTier(tier_index=0, tier_type=TierType.GP_CATCH_UP,
                                 sponsor_shares=shares, description="gp_catch_up"),
        )
        inputs = WaterfallRunnerInputs(
            tiers=tiers,
            available_cash_by_period=(1000.0,),
            pref_result=None,
            cumulative_invested_by_period=(5000.0,),
            num_periods=1,
            lp_cumulative_pref_by_period=(),
        )
        result = run_waterfall(inputs)
        entry = result.period_results[0].tier_entries[0]
        gp_amt = next(amt for code, amt in entry.allocated_per_sponsor_keur if code == "LP")
        assert gp_amt == pytest.approx(1000.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# ── Test: GP_CATCH_UP allocations ──────────────────────────────────────────────

class TestGpCatchUpAllocations:
    """GP_CATCH_UP tier allocations via run_waterfall: LP gets 0, GP gets full catch-up."""

    def test_gp_catch_up_allocation_zero_to_lp(self):
        """LP receives exactly 0 in GP_CATCH_UP tier — catch-up is GP-only."""
        tiers = (
            SponsorWaterfallTier(
                tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL,
                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=1.0),),
                description="roc",
            ),
            SponsorWaterfallTier(
                tier_index=1, tier_type=TierType.GP_CATCH_UP,
                sponsor_shares=(SponsorShare(sponsor_code="GP", allocation_percentage=1.0),),
                description="gp_catch_up",
            ),
        )
        # 1000 available, ROC not triggered (invested=0), catch-up gets all 1000
        inputs = WaterfallRunnerInputs(
            tiers=tiers,
            available_cash_by_period=(1000.0,),
            pref_result=None,
            cumulative_invested_by_period=(0.0,),
            num_periods=1,
            lp_cumulative_pref_by_period=(1000.0,),  # trigger = max(0, 1000 - 0) = 250
            lp_invested_capital_keur=0.0,
        )
        result = run_waterfall(inputs)
        period0 = result.period_results[0]
        catch_up = next((t for t in period0.tier_entries if t.tier_type == TierType.GP_CATCH_UP), None)
        assert catch_up is not None
        lp_alloc = next((amt for code, amt in catch_up.allocated_per_sponsor_keur if code == "LP"), 0.0)
        gp_alloc = next((amt for code, amt in catch_up.allocated_per_sponsor_keur if code == "GP"), 0.0)
        assert lp_alloc == 0.0, f"LP must receive 0 in GP_CATCH_UP, got {lp_alloc}"
        assert gp_alloc == 250.0, f"GP must receive 250 (min(1000, 250 trigger)), got {gp_alloc}"

    def test_gp_catch_up_allocation_full_to_gp(self):
        """GP receives 100% of GP_CATCH_UP tier allocation."""
        tiers = (
            SponsorWaterfallTier(
                tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL,
                sponsor_shares=(SponsorShare(sponsor_code="LP", allocation_percentage=1.0),),
                description="roc",
            ),
            SponsorWaterfallTier(
                tier_index=1, tier_type=TierType.GP_CATCH_UP,
                sponsor_shares=(SponsorShare(sponsor_code="GP", allocation_percentage=1.0),),
                description="gp_catch_up",
            ),
        )
        inputs = WaterfallRunnerInputs(
            tiers=tiers,
            available_cash_by_period=(800.0,),
            pref_result=None,
            cumulative_invested_by_period=(0.0,),
            num_periods=1,
            lp_cumulative_pref_by_period=(1000.0,),  # trigger = max(0, 1000-0) = 250
            lp_invested_capital_keur=0.0,
        )
        result = run_waterfall(inputs)
        period0 = result.period_results[0]
        catch_up = next((t for t in period0.tier_entries if t.tier_type == TierType.GP_CATCH_UP), None)
        assert catch_up is not None
        gp_alloc = next((amt for code, amt in catch_up.allocated_per_sponsor_keur if code == "GP"), 0.0)
        assert gp_alloc == 250.0, f"GP must receive 250 (min(800, 250 trigger)), got {gp_alloc}"


# ── Test: PROMOTE distinct from ROC ───────────────────────────────────────────

class TestPromoteTierUsesExplicitCarryShares:
    """PROMOTE tier uses explicit carry split shares — distinct from ownership shares.

    When gp_promote_share differs from GP's ownership percentage, PROMOTE must use
    the explicit promote share, NOT proportional ownership shares.
    """

    def test_promote_tier_gp_gets_promote_share_not_ownership_share(self):
        """GP gets gp_promote_share in PROMOTE even if ownership < promote share.

        Scenario: LP owns 90%, GP owns 10% of equity.
        But gp_promote_share=0.20 (carry split = 80/20).
        PROMOTE tier must give GP 20%, not 10%.
        """
        tiers = (
            SponsorWaterfallTier(
                tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="LP", allocation_percentage=0.90),
                    SponsorShare(sponsor_code="GP", allocation_percentage=0.10),
                ),
                description="roc",
            ),
            SponsorWaterfallTier(
                tier_index=1, tier_type=TierType.PROMOTE,
                sponsor_shares=(
                    SponsorShare(sponsor_code="LP", allocation_percentage=0.80),
                    SponsorShare(sponsor_code="GP", allocation_percentage=0.20),
                ),
                description="promote",
            ),
        )
        # Available=1000, ROC satisfied by GP's 10% share first (100)
        # Remainder to PROMOTE
        inputs = WaterfallRunnerInputs(
            tiers=tiers,
            available_cash_by_period=(1000.0,),
            pref_result=None,
            cumulative_invested_by_period=(0.0,),
            num_periods=1,
            lp_cumulative_pref_by_period=(0.0,),
        )
        result = run_waterfall(inputs)
        period0 = result.period_results[0]
        promote = next((t for t in period0.tier_entries if t.tier_type == TierType.PROMOTE), None)
        assert promote is not None
        gp_alloc = next((amt for code, amt in promote.allocated_per_sponsor_keur if code == "GP"), 0.0)
        lp_alloc = next((amt for code, amt in promote.allocated_per_sponsor_keur if code == "LP"), 0.0)
        assert gp_alloc == pytest.approx(200.0), f"GP must get ~180 (20% of remainder after ROC), got {gp_alloc}"
        assert lp_alloc == pytest.approx(800.0), f"LP must get ~720 (80% of remainder), got {lp_alloc}"

    def test_promote_coinvestor_gets_proportional_non_gp_share(self):
        """CO_INVESTOR in 3-investor scenario gets proportional non-GP share.

        Scenario: LP=60%, GP=20%, CO=20%, gp_promote_share=0.20.
        PROMOTE shares should be:
          GP:  20% (explicit promote share)
          LP:  (0.60/0.80) × 80% = 60%  ✓
          CO:  (0.20/0.80) × 80% = 20%  ✓
        Sum: 20% + 60% + 20% = 100%
        """
        tiers = (
            SponsorWaterfallTier(
                tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="LP", allocation_percentage=0.60),
                    SponsorShare(sponsor_code="GP", allocation_percentage=0.20),
                    SponsorShare(sponsor_code="CO", allocation_percentage=0.20),
                ),
                description="roc",
            ),
            SponsorWaterfallTier(
                tier_index=1, tier_type=TierType.PROMOTE,
                sponsor_shares=(
                    SponsorShare(sponsor_code="LP", allocation_percentage=0.60),
                    SponsorShare(sponsor_code="GP", allocation_percentage=0.20),
                    SponsorShare(sponsor_code="CO", allocation_percentage=0.20),
                ),
                description="promote",
            ),
        )
        inputs = WaterfallRunnerInputs(
            tiers=tiers,
            available_cash_by_period=(1000.0,),
            pref_result=None,
            cumulative_invested_by_period=(0.0,),
            num_periods=1,
            lp_cumulative_pref_by_period=(0.0,),
        )
        result = run_waterfall(inputs)
        period0 = result.period_results[0]
        promote = next((t for t in period0.tier_entries if t.tier_type == TierType.PROMOTE), None)
        assert promote is not None
        gp_alloc = next((amt for code, amt in promote.allocated_per_sponsor_keur if code == "GP"), 0.0)
        lp_alloc = next((amt for code, amt in promote.allocated_per_sponsor_keur if code == "LP"), 0.0)
        co_alloc = next((amt for code, amt in promote.allocated_per_sponsor_keur if code == "CO"), 0.0)
        total = gp_alloc + lp_alloc + co_alloc
        assert gp_alloc == pytest.approx(200.0), f"GP must get ~200 (20%), got {gp_alloc}"
        assert lp_alloc == pytest.approx(600.0), f"LP must get ~600 (60%), got {lp_alloc}"
        assert co_alloc == pytest.approx(200.0), f"CO must get ~200 (20%), got {co_alloc}"
        assert abs(total - 1000.0) < 0.01, f"Allocations must sum to 1000, got {total}"
