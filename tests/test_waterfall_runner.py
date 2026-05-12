"""Phase 7C-3 — Waterfall allocation runner tests.

Comprehensive tests for the waterfall allocation engine.
Deterministic. Pure function. No mocking.
"""
from __future__ import annotations

import math
import pytest
from dataclasses import dataclass

from domain.sponsor.sponsor_waterfall_tier import (
    TierType,
    CompoundingConvention,
    SponsorShare,
    SponsorWaterfallTier,
)
from domain.sponsor.preferred_return_result import (
    PreferredReturnAccrualEntry,
    PreferredReturnResult,
)
from domain.sponsor.waterfall_allocation_result import (
    TierAllocationEntry,
    PeriodWaterfallResult,
    WaterfallAllocationResult,
)
from domain.sponsor.waterfall_runner import (
    WaterfallRunnerInputs,
    run_waterfall,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_share(sponsor_code: str, allocation: float = 1.0) -> SponsorShare:
    return SponsorShare(sponsor_code=sponsor_code, allocation_percentage=allocation)


def make_tier(
    tier_index: int,
    tier_type: TierType,
    shares: list[SponsorShare] | tuple[SponsorShare, ...],
    hurdle_rate: float | None = None,
    convention: CompoundingConvention | None = None,
    description: str = "test tier",
) -> SponsorWaterfallTier:
    return SponsorWaterfallTier(
        tier_index=tier_index,
        tier_type=tier_type,
        sponsor_shares=tuple(shares),
        description=description,
        hurdle_rate_pa=hurdle_rate,
        compounding_convention=convention,
    )


def make_pref_entry(
    period_index: int,
    opening_invested: float,
    invested_delta: float,
    hurdle_rate: float = 0.08,
    convention: str = "SIMPLE",
    accrual_periods: float = 0.5,
    accrued_pref: float = 0.0,
    cumulative_accrued: float = 0.0,
    cumulative_dist: float = 0.0,
    unpaid_pref: float = 0.0,
    hurdle_satisfied: bool = False,
) -> PreferredReturnAccrualEntry:
    return PreferredReturnAccrualEntry(
        period_index=period_index,
        opening_invested_capital_keur=opening_invested,
        invested_capital_delta_keur=invested_delta,
        hurdle_rate_pa=hurdle_rate,
        compounding_convention=convention,
        accrual_periods=accrual_periods,
        accrued_pref_keur=accrued_pref,
        cumulative_accrued_pref_keur=cumulative_accrued,
        cumulative_distributions_keur=cumulative_dist,
        unpaid_pref_balance_keur=unpaid_pref,
        hurdle_satisfied=hurdle_satisfied,
    )


def make_pref_result(
    sponsor_code: str = "SPONSOR-1",
    hurdle_rate: float = 0.08,
    convention: str = "ANNUAL",
    entries: list[PreferredReturnAccrualEntry] | None = None,
) -> PreferredReturnResult:
    if entries is None:
        entries = [make_pref_entry(0, 10000.0, 10000.0)]
    return PreferredReturnResult(
        sponsor_code=sponsor_code,
        hurdle_rate_pa=hurdle_rate,
        compounding_convention=convention,
        entries=tuple(entries),
        total_accrued_pref_keur=sum(e.accrued_pref_keur for e in entries),
        total_unpaid_pref_keur=entries[-1].unpaid_pref_balance_keur if entries else 0.0,
        all_periods_hurdle_satisfied=entries[-1].hurdle_satisfied if entries else False,
    )


def run(
    tiers: list[SponsorWaterfallTier],
    cash: list[float],
    pref_result: PreferredReturnResult | None = None,
    cumulative_invested: list[float] | None = None,
) -> WaterfallAllocationResult:
    if cumulative_invested is None:
        cumulative_invested = [10000.0] * len(cash)
    inputs = WaterfallRunnerInputs(
        tiers=tuple(tiers),
        available_cash_by_period=tuple(cash),
        pref_result=pref_result,
        cumulative_invested_by_period=tuple(cumulative_invested),
        num_periods=len(cash),
    )
    return run_waterfall(inputs)


# ── Cash conservation ────────────────────────────────────────────────────────

class TestCashConservation:
    def test_exact_cash_conservation_single_tier(self):
        """available_cash = tier1_allocated + remaining_cash for every period."""
        tier = make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")])
        result = run([tier], [1000.0, 2000.0, 3000.0])
        for p in result.period_results:
            conserved = p.available_cash_keur - p.total_allocated_keur - p.total_remaining_cash_keur
            assert abs(conserved) < 1e-6

    def test_exact_cash_conservation_multi_tier(self):
        """Cash conserved across all 5 tiers."""
        tiers = [
            make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")]),
            make_tier(1, TierType.PREFERRED_RETURN, [make_share("SPONSOR-1")],
                      0.08, CompoundingConvention.ANNUAL),
            make_tier(2, TierType.GP_CATCH_UP, [make_share("GP-1")]),
            make_tier(3, TierType.PROMOTE, [make_share("SPONSOR-1")]),
            make_tier(4, TierType.RESIDUAL, [make_share("SPONSOR-1")]),
        ]
        pref = make_pref_result(
            entries=[
                make_pref_entry(i, 10000.0, 0.0, 0.08, "ANNUAL",
                                 accrual_periods=0.0, accrued_pref=0.0,
                                 cumulative_accrued=0.0, unpaid_pref=0.0)
                for i in range(3)
            ]
        )
        result = run(tiers, [5000.0, 5000.0, 5000.0], pref)
        for p in result.period_results:
            conserved = p.available_cash_keur - p.total_allocated_keur - p.total_remaining_cash_keur
            assert abs(conserved) < 1e-6


# ── Return of capital ──────────────────────────────────────────────────────

class TestReturnOfCapital:
    def test_roc_full_repayment_in_single_period(self):
        """When cash >= remaining ROC, full ROC repaid in one period."""
        tier = make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")])
        result = run([tier], [10000.0], cumulative_invested=[10000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == pytest.approx(10000.0)
        assert entry.remaining_cash_after_tier_keur == 0.0

    def test_roc_partial_repayment_split_across_periods(self):
        """When cash < ROC, partial repayment each period until exhausted."""
        tier = make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")])
        result = run(
            [tier], [3000.0, 3000.0, 4000.0],
            cumulative_invested=[10000.0, 10000.0, 10000.0],
        )
        assert result.period_results[0].tier_entries[0].allocated_amount_keur == 3000.0
        assert result.period_results[1].tier_entries[0].allocated_amount_keur == 3000.0
        assert result.period_results[2].tier_entries[0].allocated_amount_keur == 4000.0
        assert result.period_results[2].tier_entries[0].remaining_cash_after_tier_keur == 0.0

    def test_roc_exhausted_no_further_allocation(self):
        """After ROC is fully repaid, subsequent periods allocate 0 to ROC."""
        tier = make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")])
        result = run(
            [tier], [4000.0, 4000.0, 2000.0],
            cumulative_invested=[10000.0, 10000.0, 10000.0],
        )
        assert result.period_results[0].tier_entries[0].allocated_amount_keur == 4000.0
        assert result.period_results[1].tier_entries[0].allocated_amount_keur == 4000.0
        assert result.period_results[2].tier_entries[0].allocated_amount_keur == 2000.0
        assert result.period_results[2].tier_entries[0].remaining_cash_after_tier_keur == 0.0

    def test_roc_excess_rolls_to_next_tier(self):
        """Cash exceeds remaining ROC → excess rolls to next tier."""
        tier = make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")])
        result = run([tier], [10000.0], cumulative_invested=[5000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == pytest.approx(5000.0)
        assert entry.remaining_cash_after_tier_keur == pytest.approx(5000.0)


# ── Preferred return ────────────────────────────────────────────────────────

class TestPreferredReturnAllocation:
    def test_pref_no_cash_zero_allocation(self):
        """Zero cash → no pref allocation despite unpaid balance."""
        tier = make_tier(
            0, TierType.PREFERRED_RETURN,
            [make_share("SPONSOR-1")],
            hurdle_rate=0.08,
            convention=CompoundingConvention.SIMPLE,
        )
        pref = make_pref_result(
            entries=[make_pref_entry(
                0, 10000.0, 10000.0, 0.08, "SIMPLE",
                accrued_pref=400.0, cumulative_accrued=400.0, unpaid_pref=400.0,
            )]
        )
        result = run([tier], [0.0], pref, cumulative_invested=[10000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == 0.0
        assert entry.remaining_cash_after_tier_keur == 0.0

    def test_pref_insufficient_cash_partial(self):
        """Cash < unpaid pref → partial allocation."""
        tier = make_tier(
            0, TierType.PREFERRED_RETURN,
            [make_share("SPONSOR-1")],
            hurdle_rate=0.08,
            convention=CompoundingConvention.SIMPLE,
        )
        pref = make_pref_result(
            entries=[make_pref_entry(
                0, 10000.0, 10000.0, 0.08, "SIMPLE",
                accrued_pref=400.0, cumulative_accrued=400.0, unpaid_pref=400.0,
            )]
        )
        result = run([tier], [150.0], pref, cumulative_invested=[10000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == pytest.approx(150.0)
        assert entry.remaining_cash_after_tier_keur == pytest.approx(0.0)

    def test_pref_sufficient_cash_full(self):
        """Cash >= unpaid pref → full allocation, excess rolls."""
        tier = make_tier(
            0, TierType.PREFERRED_RETURN,
            [make_share("SPONSOR-1")],
            hurdle_rate=0.08,
            convention=CompoundingConvention.SIMPLE,
        )
        pref = make_pref_result(
            entries=[make_pref_entry(
                0, 10000.0, 10000.0, 0.08, "SIMPLE",
                accrued_pref=400.0, cumulative_accrued=400.0, unpaid_pref=400.0,
            )]
        )
        result = run([tier], [600.0], pref, cumulative_invested=[10000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == pytest.approx(400.0)
        assert entry.remaining_cash_after_tier_keur == pytest.approx(200.0)

    def test_pref_zero_unpaid_balance(self):
        """Zero unpaid pref → no allocation, all cash rolls."""
        tier = make_tier(
            0, TierType.PREFERRED_RETURN,
            [make_share("SPONSOR-1")],
            hurdle_rate=0.08,
            convention=CompoundingConvention.SIMPLE,
        )
        pref = make_pref_result(
            entries=[make_pref_entry(
                0, 10000.0, 10000.0, 0.08, "SIMPLE",
                accrued_pref=400.0, cumulative_accrued=400.0,
                cumulative_dist=400.0, unpaid_pref=0.0, hurdle_satisfied=True,
            )]
        )
        result = run([tier], [1000.0], pref, cumulative_invested=[10000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == 0.0
        assert entry.remaining_cash_after_tier_keur == pytest.approx(1000.0)


# ── Tier ordering ───────────────────────────────────────────────────────────

class TestTierOrdering:
    def test_tiers_sorted_by_index(self):
        """Tiers must be processed in tier_index order regardless of input order."""
        tiers = [
            make_tier(2, TierType.GP_CATCH_UP, [make_share("GP-1")]),
            make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")]),
            make_tier(1, TierType.PREFERRED_RETURN, [make_share("SPONSOR-1")],
                      0.08, CompoundingConvention.ANNUAL),
        ]
        pref = make_pref_result(
            entries=[make_pref_entry(0, 10000.0, 10000.0, 0.08, "ANNUAL",
                                     accrued_pref=0.0, unpaid_pref=0.0)]
        )
        result = run(tiers, [5000.0], pref, cumulative_invested=[10000.0])
        indices = [e.tier_index for e in result.period_results[0].tier_entries]
        assert indices == [0, 1, 2]

    def test_excess_roc_rolls_to_pref(self):
        """Cash remaining after ROC allocation rolls to PREFERRED_RETURN."""
        tiers = [
            make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")]),
            make_tier(1, TierType.PREFERRED_RETURN, [make_share("SPONSOR-1")],
                      0.08, CompoundingConvention.SIMPLE),
        ]
        pref = make_pref_result(
            entries=[make_pref_entry(
                0, 10000.0, 10000.0, 0.08, "SIMPLE",
                accrued_pref=400.0, cumulative_accrued=400.0, unpaid_pref=400.0,
            )]
        )
        # cash=10000, ROC needed=5000 → 5000 excess to pref (needs 400)
        result = run(tiers, [10000.0], pref, cumulative_invested=[5000.0])
        roc = result.period_results[0].tier_entries[0]
        pr = result.period_results[0].tier_entries[1]
        assert roc.allocated_amount_keur == pytest.approx(5000.0)
        assert roc.remaining_cash_after_tier_keur == pytest.approx(5000.0)
        assert pr.allocated_amount_keur == pytest.approx(400.0)
        assert pr.remaining_cash_after_tier_keur == pytest.approx(4600.0)


# ── GP catch-up ────────────────────────────────────────────────────────────

class TestGPCatchUp:
    def test_gp_receives_100_percent_until_threshold(self):
        """GP gets 100% of available cash until cumulative >= promote threshold."""
        tiers = [
            make_tier(0, TierType.GP_CATCH_UP, [make_share("GP-1")]),
        ]
        # promote_threshold = 10000 (last period cumulative invested)
        # cash per period = 1000 × 3 = 3000 total < threshold
        result = run(tiers, [1000.0, 1000.0, 1000.0],
                    cumulative_invested=[10000.0, 10000.0, 10000.0])
        gp = result.period_results[0].tier_entries[0]
        assert gp.allocated_amount_keur == 1000.0
        assert gp.remaining_cash_after_tier_keur == 0.0  # all goes to GP

    def test_gp_catch_up_below_threshold_all_to_gp(self):
        """When total GP received < threshold, all cash goes to GP."""
        tiers = [
            make_tier(0, TierType.GP_CATCH_UP, [make_share("GP-1")]),
        ]
        result = run(tiers, [3000.0, 3000.0],
                    cumulative_invested=[10000.0, 10000.0])
        total_gp = sum(
            e.allocated_amount_keur
            for p in result.period_results
            for e in p.tier_entries
            if e.tier_type == TierType.GP_CATCH_UP
        )
        assert total_gp == pytest.approx(6000.0)  # all cash to GP

    def test_gp_catch_up_multi_sponsor(self):
        """GP catch-up with multiple sponsors splits proportionally."""
        tiers = [
            make_tier(0, TierType.GP_CATCH_UP, [
                make_share("GP-1", 0.5),
                make_share("LP-1", 0.5),
            ]),
        ]
        result = run(tiers, [2000.0], cumulative_invested=[10000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == pytest.approx(2000.0)
        alloc = dict(entry.allocated_per_sponsor_keur)
        assert alloc["GP-1"] == pytest.approx(1000.0)
        assert alloc["LP-1"] == pytest.approx(1000.0)


# ── Promote and residual ────────────────────────────────────────────────────

class TestPromoteAndResidual:
    def test_promote_split_proportional(self):
        """PROMOTE tier splits by SponsorShare percentages."""
        tiers = [
            make_tier(0, TierType.PROMOTE, [
                make_share("SPONSOR-1", 0.7),
                make_share("LP-1", 0.3),
            ]),
        ]
        result = run(tiers, [10000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == pytest.approx(10000.0)
        alloc = dict(entry.allocated_per_sponsor_keur)
        assert alloc["SPONSOR-1"] == pytest.approx(7000.0)
        assert alloc["LP-1"] == pytest.approx(3000.0)

    def test_residual_split_proportional(self):
        """RESIDUAL tier splits by SponsorShare percentages."""
        tiers = [
            make_tier(0, TierType.RESIDUAL, [
                make_share("SPONSOR-1", 0.6),
                make_share("LP-1", 0.4),
            ]),
        ]
        result = run(tiers, [5000.0])
        entry = result.period_results[0].tier_entries[0]
        alloc = dict(entry.allocated_per_sponsor_keur)
        assert alloc["SPONSOR-1"] == pytest.approx(3000.0)
        assert alloc["LP-1"] == pytest.approx(2000.0)


# ── Edge cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_zero_cash_all_periods(self):
        """Zero cash → all allocations zero."""
        tier = make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")])
        result = run([tier], [0.0, 0.0, 0.0],
                    cumulative_invested=[10000.0, 10000.0, 10000.0])
        for p in result.period_results:
            assert p.total_allocated_keur == 0.0
            assert p.total_remaining_cash_keur == 0.0


# ── Multi-sponsor ────────────────────────────────────────────────────────────

class TestMultiSponsor:
    def test_multi_sponsor_roc_split(self):
        """ROC splits proportionally to sponsor shares."""
        tiers = [
            make_tier(0, TierType.RETURN_OF_CAPITAL, [
                make_share("SPONSOR-1", 0.6),
                make_share("LP-1", 0.4),
            ]),
        ]
        result = run(tiers, [5000.0], cumulative_invested=[10000.0])
        entry = result.period_results[0].tier_entries[0]
        assert entry.allocated_amount_keur == pytest.approx(5000.0)
        alloc = dict(entry.allocated_per_sponsor_keur)
        assert alloc["SPONSOR-1"] == pytest.approx(3000.0)
        assert alloc["LP-1"] == pytest.approx(2000.0)


# ── Deterministic rerun ────────────────────────────────────────────────────

class TestDeterministicRerun:
    def test_deterministic_results(self):
        """Two runs with identical inputs produce identical results."""
        tiers = [
            make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")]),
            make_tier(1, TierType.PREFERRED_RETURN, [make_share("SPONSOR-1")],
                      0.08, CompoundingConvention.SIMPLE),
        ]
        pref = make_pref_result(
            entries=[
                make_pref_entry(i, 10000.0, 0.0, 0.08, "SIMPLE",
                               accrued_pref=400.0, cumulative_accrued=(i + 1) * 400.0,
                               unpaid_pref=(i + 1) * 400.0, hurdle_satisfied=True)
                for i in range(3)
            ]
        )
        r1 = run(tiers, [5000.0, 5000.0, 5000.0], pref,
                 [10000.0, 10000.0, 10000.0])
        r2 = run(tiers, [5000.0, 5000.0, 5000.0], pref,
                 [10000.0, 10000.0, 10000.0])
        assert r1.total_allocated_keur == pytest.approx(r2.total_allocated_keur)
        for p1, p2 in zip(r1.period_results, r2.period_results):
            assert p1.total_allocated_keur == pytest.approx(p2.total_allocated_keur)


# ── NaN/Inf rejection ───────────────────────────────────────────────────────

class TestNaNInfRejection:
    def test_rejects_nan_cash(self):
        tiers = [make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")])]
        with pytest.raises(ValueError, match="must be finite"):
            WaterfallRunnerInputs(
                tiers=tuple(tiers),
                available_cash_by_period=(float("nan"),),
                pref_result=None,
                cumulative_invested_by_period=(10000.0,),
                num_periods=1,
            )

    def test_rejects_inf_cash(self):
        tiers = [make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")])]
        with pytest.raises(ValueError, match="must be finite"):
            WaterfallRunnerInputs(
                tiers=tuple(tiers),
                available_cash_by_period=(float("inf"),),
                pref_result=None,
                cumulative_invested_by_period=(10000.0,),
                num_periods=1,
            )


# ── Cumulative distributions ─────────────────────────────────────────────────

class TestCumulativeDistributions:
    def test_cumulative_distributions_period_2_equals_period_1_plus_period_2(self):
        tiers = [
            make_tier(0, TierType.RETURN_OF_CAPITAL, [
                make_share("SPONSOR-1", 0.6),
                make_share("LP-1", 0.4),
            ]),
        ]
        # Period 0: cash=3000 -> SPONSOR-1=1800, LP-1=1200
        # Period 1: cash=5000 -> SPONSOR-1=3000, LP-1=2000
        # Period 2: cash=2000 -> SPONSOR-1=1200, LP-1=800
        result = run(tiers, [3000.0, 5000.0, 2000.0],
                     cumulative_invested=[10000.0, 10000.0, 10000.0])
        p0 = result.period_results[0]
        p1 = result.period_results[1]
        p2 = result.period_results[2]
        cum0 = dict(p0.cumulative_distributions_by_sponsor_keur)
        assert cum0["SPONSOR-1"] == pytest.approx(1800.0)
        assert cum0["LP-1"] == pytest.approx(1200.0)
        cum1 = dict(p1.cumulative_distributions_by_sponsor_keur)
        assert cum1["SPONSOR-1"] == pytest.approx(1800.0 + 3000.0)
        assert cum1["LP-1"] == pytest.approx(1200.0 + 2000.0)
        cum2 = dict(p2.cumulative_distributions_by_sponsor_keur)
        assert cum2["SPONSOR-1"] == pytest.approx(4800.0 + 1200.0)
        assert cum2["LP-1"] == pytest.approx(3200.0 + 800.0)

    def test_cumulative_increases_across_periods(self):
        tiers = [
            make_tier(0, TierType.RETURN_OF_CAPITAL, [make_share("SPONSOR-1")]),
        ]
        result = run(tiers, [1000.0, 2000.0, 3000.0],
                    cumulative_invested=[10000.0, 10000.0, 10000.0])
        p0 = dict(result.period_results[0].cumulative_distributions_by_sponsor_keur)
        p1 = dict(result.period_results[1].cumulative_distributions_by_sponsor_keur)
        p2 = dict(result.period_results[2].cumulative_distributions_by_sponsor_keur)
        assert p2["SPONSOR-1"] > p1["SPONSOR-1"]
        assert p1["SPONSOR-1"] > p0["SPONSOR-1"]
