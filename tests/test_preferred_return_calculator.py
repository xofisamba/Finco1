"""Phase 7C-2 — Preferred return calculator tests.

Comprehensive tests for preferred return accrual logic.
Deterministic. Pure function. No mocking.
"""
from __future__ import annotations

import math

import pytest

from domain.sponsor.sponsor_waterfall_tier import (
    TierType,
    CompoundingConvention,
    SponsorShare,
    SponsorWaterfallTier,
)
from domain.sponsor.preferred_return_calculator import (
    PreferredReturnCalculatorInputs,
    calculate_preferred_return,
)
from domain.sponsor.preferred_return_result import (
    PreferredReturnAccrualEntry,
    PreferredReturnResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_pref_tier(
    hurdle_rate: float = 0.08,
    convention: CompoundingConvention = CompoundingConvention.ANNUAL,
    sponsor_code: str = "SPONSOR-1",
    allocation: float = 1.0,
) -> SponsorWaterfallTier:
    return SponsorWaterfallTier(
        tier_index=1,
        tier_type=TierType.PREFERRED_RETURN,
        sponsor_shares=(SponsorShare(sponsor_code=sponsor_code, allocation_percentage=allocation),),
        description="Preferred return tier",
        hurdle_rate_pa=hurdle_rate,
        compounding_convention=convention,
    )


def calc(
    tier: SponsorWaterfallTier,
    cumulative_invested: list[float],
    distributions: list[float],
) -> PreferredReturnResult:
    inputs = PreferredReturnCalculatorInputs(
        tier=tier,
        cumulative_invested_by_period=tuple(cumulative_invested),
        distributions_by_period=tuple(distributions),
        num_periods=len(cumulative_invested),
    )
    return calculate_preferred_return(inputs)


# ── Annual compounding ────────────────────────────────────────────────────────

class TestAnnualCompoundingAccrual:
    def test_even_period_zero_accrual(self):
        """Period 0 (even): no accrual — first half of year, waiting for annual boundary."""
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [10000.0], [0.0])
        entry = result.entries[0]
        assert entry.accrued_pref_keur == 0.0
        assert entry.cumulative_accrued_pref_keur == 0.0
        assert entry.hurdle_satisfied is False  # threshold=800, accrued=0

    def test_odd_period_annual_accrual(self):
        """Period 1 (odd): full annual accrual on opening invested at year boundary.

        p=0: opening=10k, even → 0 accrual (first half of year 1)
        p=1: opening=10k, odd → annual boundary → accrue 10k*0.08=800 (year 1 complete)
        """
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [10000.0, 10000.0], [0.0, 0.0])
        assert result.entries[0].accrued_pref_keur == 0.0        # even → 0
        assert result.entries[1].accrued_pref_keur == pytest.approx(800.0)  # odd → annual
        assert result.total_accrued_pref_keur == pytest.approx(800.0)

    def test_two_annual_periods_correct_total(self):
        """4 periods = 2 annual cycles. 10k at p=0:
        p=0: 0, p=1: 800 (year 1), p=2: 0, p=3: 800 (year 2) → total=1600"""
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [10000.0]*4, [0.0]*4)
        assert result.entries[0].accrued_pref_keur == 0.0
        assert result.entries[1].accrued_pref_keur == pytest.approx(800.0)
        assert result.entries[2].accrued_pref_keur == 0.0
        assert result.entries[3].accrued_pref_keur == pytest.approx(800.0)
        assert result.total_accrued_pref_keur == pytest.approx(1600.0)

    def test_invest_at_period_1_earns_annual_at_period_3(self):
        """10k injected at end of p=1 (cumulative=10k from p=1 onward).

        p=0: opening=0, even → 0
        p=1: opening=0 (invested at end of p=1, not yet earning), odd → annual boundary on 0 = 0
        p=2: opening=10k (from p=1 end), even → 0 (first half of year 2)
        p=3: opening=10k, odd → annual boundary → 800
        """
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [0.0, 10000.0, 10000.0, 10000.0], [0.0]*4)
        assert result.entries[0].accrued_pref_keur == 0.0
        assert result.entries[1].accrued_pref_keur == 0.0   # odd boundary but opening=0
        assert result.entries[2].accrued_pref_keur == 0.0    # even: first half of year 2
        assert result.entries[3].accrued_pref_keur == pytest.approx(800.0)

    def test_hurdle_satisfied_at_annual_boundary(self):
        """Hurdle satisfied when cumulative_accrued >= cumulative_invested * hurdle.

        10k invested at p=0: threshold=800. p=1 accrues 800 → hurdle satisfied."""
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [10000.0, 10000.0], [0.0, 0.0])
        assert result.entries[0].hurdle_satisfied is False   # accrued=0, threshold=800
        assert result.entries[1].hurdle_satisfied is True    # accrued=800, threshold=800
        assert result.all_periods_hurdle_satisfied is True

    def test_annual_vs_semiannual_10k_four_periods(self):
        """10k invested at p=0, 4 periods (2 years):
        ANNUAL: 0 + 800 + 0 + 800 = 1,600
        SEMIANNUAL: ~392 + ~392 + ~392 + ~392 = ~1,568"""
        tier_annual = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        tier_semi = make_pref_tier(0.08, CompoundingConvention.SEMIANNUAL)
        r_annual = calc(tier_annual, [10000.0]*4, [0.0]*4)
        r_semi = calc(tier_semi, [10000.0]*4, [0.0]*4)
        assert r_annual.total_accrued_pref_keur == pytest.approx(1600.0)
        assert r_semi.total_accrued_pref_keur == pytest.approx(1568.0, rel=1e-3)


# ── Simple accrual ────────────────────────────────────────────────────────────

class TestSimpleAccrual:
    def test_simple_acccrues_half_period_hurdle(self):
        """SIMPLE: accrued = opening_invested * hurdle_rate * 0.5 (half-year period).

        10,000 * 0.08 * 0.5 = 400 per period."""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0], [0.0])
        assert result.entries[0].accrued_pref_keur == pytest.approx(400.0)

    def test_simple_vs_annual_first_period(self):
        """SIMPLE accrues hurdle * 0.5 per half-year; ANNUAL accrues full hurdle once per year.

        SIMPLE: 10k * 0.08 * 0.5 = 400 per period (even p=0 accrues since it's half-year)
        ANNUAL: 10k at p=0, p=0=even → 0 (first half of year), p=1=odd → 800 (annual boundary)"""
        tier_simple = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        tier_annual = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        r_simple = calc(tier_simple, [10000.0], [0.0])
        r_annual = calc(tier_annual, [10000.0, 10000.0], [0.0, 0.0])
        assert r_simple.entries[0].accrued_pref_keur == pytest.approx(400.0)
        # ANNUAL: even period 0 → no accrual; odd period 1 → 800 annual accrual
        assert r_annual.entries[0].accrued_pref_keur == 0.0
        assert r_annual.entries[1].accrued_pref_keur == pytest.approx(800.0)

    def test_simple_over_10_periods(self):
        """10 periods × 400 = 4,000 total = 10k * 0.08 * 5 years."""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        invested = [10000.0] * 10
        result = calc(tier, invested, [0.0] * 10)
        assert result.total_accrued_pref_keur == pytest.approx(4000.0)


# ── Semiannual compounding ────────────────────────────────────────────────────

class TestSemiannualCompounding:
    def test_semiannual_periodic_rate(self):
        """SEMIANNUAL: periodic_rate = (1 + hurdle)^0.5 - 1 ≈ 0.03923...

        10,000 * 0.03923... ≈ 392.3 per period."""
        tier = make_pref_tier(0.08, CompoundingConvention.SEMIANNUAL)
        result = calc(tier, [10000.0], [0.0])
        expected_periodic = 10000.0 * ((1 + 0.08) ** 0.5 - 1)
        assert result.entries[0].accrued_pref_keur == pytest.approx(expected_periodic, rel=1e-6)

    def test_semiannual_two_periods_total(self):
        """SEMIANNUAL over 2 periods should give ~1.08^1 - 1 = 8% annual total.

        period 0: 392.3, period 1: 392.3, total ≈ 784.6 vs annual total of 800."""
        tier = make_pref_tier(0.08, CompoundingConvention.SEMIANNUAL)
        result = calc(tier, [10000.0, 10000.0], [0.0, 0.0])
        # (1.08)^1 - 1 = 0.08 → 10k * 0.08 = 800 per year
        # semiannual: ((1.08)^0.5 - 1) * 2 ≈ 0.03923 * 2... no wait
        # total semiannual = (1.08)^1 - 1 = 0.08 applied once for both periods? 
        # Actually per period it's (1.08)^0.5 - 1, and both periods accrue on same base
        # So total = 2 * 10000 * ((1.08)^0.5 - 1) = 2 * 392.3 = 784.6
        assert result.total_accrued_pref_keur == pytest.approx(784.6, rel=1e-3)

    def test_semiannual_over_10_periods(self):
        """10 semiannual periods (5 years) at 8% hurdle.

        Each period: 10k * ((1.08)^0.5 - 1) ≈ 392.3
        Total = 10 * 392.3 ≈ 3,923"""
        tier = make_pref_tier(0.08, CompoundingConvention.SEMIANNUAL)
        result = calc(tier, [10000.0] * 10, [0.0] * 10)
        expected_total = 10 * 10000.0 * ((1 + 0.08) ** 0.5 - 1)
        assert result.total_accrued_pref_keur == pytest.approx(expected_total, rel=1e-3)


# ── Hurdle satisfied transition ───────────────────────────────────────────────

class TestHurdleSatisfiedTransition:
    def test_hurdle_not_satisfied_below_threshold(self):
        """10k at p=0, hurdle=8%, threshold=800. After p=0 accrued=400 (SIMPLE).

        Threshold not reached, hurdle_satisfied=False."""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0], [0.0])
        assert result.entries[0].hurdle_satisfied is False

    def test_hurdle_satisfied_after_accrual_exceeds_threshold(self):
        """SIMPLE: 10k at p=0, 400 accrued in p=0 (half-year). Hurdle = 800.

        After p=0: 400 < 800 threshold → not satisfied.
        After p=1: 800 = threshold → satisfied."""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0, 10000.0], [0.0, 0.0])
        assert result.entries[0].hurdle_satisfied is False
        assert result.entries[1].hurdle_satisfied is True

    def test_hurdle_stays_satisfied(self):
        """Once hurdle is satisfied it stays satisfied."""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0, 10000.0, 10000.0], [0.0, 0.0, 0.0])
        assert result.entries[0].hurdle_satisfied is False
        assert result.entries[1].hurdle_satisfied is True
        assert result.entries[2].hurdle_satisfied is True

    def test_hurdle_satisfied_after_annual_boundary(self):
        """Hurdle satisfied after first annual accrual at p=1.

        10k invested at p=0: threshold=800. p=1 annual accrual=800 → hurdle satisfied."""
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [10000.0, 10000.0], [0.0, 0.0])
        assert result.entries[0].hurdle_satisfied is False   # accrued=0, threshold=800
        assert result.entries[1].hurdle_satisfied is True    # accrued=800, threshold=800


# ── Unpaid pref carry-forward ─────────────────────────────────────────────────

class TestUnpaidPrefCarryForward:
    def test_unpaid_accumulates_without_distribution(self):
        """Without distributions, unpaid_pref grows with each accrual."""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0, 10000.0, 10000.0], [0.0, 0.0, 0.0])
        assert result.entries[0].unpaid_pref_balance_keur == pytest.approx(400.0)
        assert result.entries[1].unpaid_pref_balance_keur == pytest.approx(800.0)
        assert result.entries[2].unpaid_pref_balance_keur == pytest.approx(1200.0)

    def test_distribution_reduces_unpaid(self):
        """Distributions applied reduce unpaid balance."""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        # p=0: 400 accrued, 200 distributed → unpaid = 200
        result = calc(tier, [10000.0], [200.0])
        assert result.entries[0].unpaid_pref_balance_keur == pytest.approx(200.0)

    def test_unpaid_carries_forward_across_periods(self):
        """p=0: 400 accrued, 0 distributed → unpaid=400
        p=1: +400 accrued, 100 distributed → unpaid=700"""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0, 10000.0], [0.0, 100.0])
        assert result.entries[0].unpaid_pref_balance_keur == pytest.approx(400.0)
        assert result.entries[1].unpaid_pref_balance_keur == pytest.approx(700.0)

    def test_unpaid_can_go_negative_if_distributions_exceed_accrued(self):
        """If distributions > accrued balance, unpaid goes negative.

        p=0: 400 accrued, 500 distributed → unpaid = -100"""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0], [500.0])
        assert result.entries[0].unpaid_pref_balance_keur == pytest.approx(-100.0)


# ── Zero-distribution periods ────────────────────────────────────────────────

class TestZeroDistributionPeriods:
    def test_all_zeros_distributions(self):
        """Zero distributions throughout: all accrued becomes unpaid."""
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0] * 5, [0.0] * 5)
        for e in result.entries:
            assert e.cumulative_distributions_keur == 0.0
        assert result.entries[-1].unpaid_pref_balance_keur == pytest.approx(2000.0)

    def test_intermittent_distributions(self):
        """Distributions only in some periods.

        p=0: 10k invested, SIMPLE half-year accrual → 400 accrued, 0 distributed → unpaid=400
        p=1: no new investment, 400 accrued, 0 distributed → unpaid=800
        p=2: 10k more invested (cumulative 20k), 400 accrued, 400 distributed → unpaid=800
        """
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0, 10000.0, 20000.0], [0.0, 0.0, 400.0])
        assert result.entries[0].unpaid_pref_balance_keur == pytest.approx(400.0)
        assert result.entries[1].unpaid_pref_balance_keur == pytest.approx(800.0)
        assert result.entries[2].unpaid_pref_balance_keur == pytest.approx(800.0)


# ── Multiple investors (sponsor share < 1.0) ─────────────────────────────────

class TestMultipleInvestors:
    def test_two_sponsors_split(self):
        """Two sponsors with 80/20 split share same preferred return accrual."""
        tier = SponsorWaterfallTier(
            tier_index=1,
            tier_type=TierType.PREFERRED_RETURN,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80),
                SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
            ),
            description="Two-sponsor pref tier",
            hurdle_rate_pa=0.08,
            compounding_convention=CompoundingConvention.SIMPLE,
        )
        result = calc(tier, [10000.0], [0.0])
        # Only SPONSOR-1 is returned as sponsor_code (first share)
        assert result.sponsor_code == "SPONSOR-1"
        assert result.entries[0].accrued_pref_keur == pytest.approx(400.0)


# ── Deterministic rerun equivalence ─────────────────────────────────────────

class TestDeterministicRerunEquivalence:
    def test_same_inputs_produce_same_results(self):
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result1 = calc(tier, [10000.0, 10000.0], [100.0, 200.0])
        result2 = calc(tier, [10000.0, 10000.0], [100.0, 200.0])
        assert result1 == result2
        assert hash(result1) == hash(result2)

    def test_entries_tuple_immutable(self):
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0], [0.0])
        with pytest.raises(Exception):
            result.entries[0].accrued_pref_keur = 999.0

    def test_result_is_frozen(self):
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0], [0.0])
        with pytest.raises(Exception):
            result.total_accrued_pref_keur = 999.0


# ── NaN / Inf rejection ───────────────────────────────────────────────────────

class TestNaNInfRejection:
    def test_rejects_nan_invested(self):
        tier = make_pref_tier()
        with pytest.raises(ValueError, match="must be finite"):
            PreferredReturnCalculatorInputs(
                tier=tier,
                cumulative_invested_by_period=(float("nan"),),
                distributions_by_period=(0.0,),
                num_periods=1,
            )

    def test_rejects_inf_distributions(self):
        tier = make_pref_tier()
        with pytest.raises(ValueError, match="must be finite"):
            PreferredReturnCalculatorInputs(
                tier=tier,
                cumulative_invested_by_period=(10000.0,),
                distributions_by_period=(float("inf"),),
                num_periods=1,
            )

    def test_rejects_negative_invested(self):
        tier = make_pref_tier()
        with pytest.raises(ValueError, match="cumulative_invested_by_period.*must be >= 0"):
            PreferredReturnCalculatorInputs(
                tier=tier,
                cumulative_invested_by_period=(-100.0,),
                distributions_by_period=(0.0,),
                num_periods=1,
            )

    def test_rejects_negative_distributions(self):
        tier = make_pref_tier()
        with pytest.raises(ValueError, match="distributions_by_period.*must be >= 0"):
            PreferredReturnCalculatorInputs(
                tier=tier,
                cumulative_invested_by_period=(10000.0,),
                distributions_by_period=(-50.0,),
                num_periods=1,
            )

    def test_rejects_decreasing_cumulative_invested(self):
        tier = make_pref_tier()
        with pytest.raises(ValueError, match="cumulative_invested_by_period must be non-decreasing"):
            PreferredReturnCalculatorInputs(
                tier=tier,
                cumulative_invested_by_period=(10000.0, 5000.0),
                distributions_by_period=(0.0, 0.0),
                num_periods=2,
            )


# ── Input validation ─────────────────────────────────────────────────────────

class TestInputValidation:
    def test_rejects_non_pref_tier(self):
        tier = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),),
            description="Not a pref tier",
        )
        with pytest.raises(ValueError, match="PREFERRED_RETURN"):
            PreferredReturnCalculatorInputs(
                tier=tier,
                cumulative_invested_by_period=(10000.0,),
                distributions_by_period=(0.0,),
                num_periods=1,
            )

    def test_rejects_length_mismatch(self):
        tier = make_pref_tier()
        with pytest.raises(ValueError, match="length.*must equal num_periods"):
            PreferredReturnCalculatorInputs(
                tier=tier,
                cumulative_invested_by_period=(10000.0, 10000.0),
                distributions_by_period=(0.0,),
                num_periods=1,
            )

    def test_rejects_zero_num_periods(self):
        tier = make_pref_tier()
        with pytest.raises(ValueError, match="num_periods must be positive"):
            PreferredReturnCalculatorInputs(
                tier=tier,
                cumulative_invested_by_period=(),
                distributions_by_period=(),
                num_periods=0,
            )


# ── Edge cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_zero_investment_all_periods(self):
        """Zero invested throughout: no accrual."""
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [0.0] * 5, [0.0] * 5)
        for e in result.entries:
            assert e.accrued_pref_keur == 0.0
            # Hurdle satisfied immediately when invested=0 (threshold=0, accrued=0)
            assert e.hurdle_satisfied is True



    def test_single_period_result(self):
        """num_periods=1 returns result with 1 entry."""
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [10000.0], [100.0])
        assert len(result.entries) == 1
        assert result.num_periods == 1
        assert result.entry_for(0) == result.entries[0]
        assert result.entry_for(99) is None

    def test_invested_delta_calculation(self):
        """invested_capital_delta should equal period-over-period change."""
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        # p=0: invested=10k, delta=10k
        # p=1: invested=15k, delta=5k
        result = calc(tier, [10000.0, 15000.0], [0.0, 0.0])
        assert result.entries[0].invested_capital_delta_keur == pytest.approx(10000.0)
        assert result.entries[1].invested_capital_delta_keur == pytest.approx(5000.0)

    def test_opening_invested_uses_prior_period(self):
        """opening_invested for period p should be cumulative_invested at end of p-1."""
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        # p=0: opening=10k (first investment)
        # p=1: opening=10k (prior cumulative)
        # p=2: opening=15k (prior cumulative)
        result = calc(tier, [10000.0, 10000.0, 15000.0], [0.0]*3)
        assert result.entries[0].opening_invested_capital_keur == pytest.approx(10000.0)
        assert result.entries[1].opening_invested_capital_keur == pytest.approx(10000.0)
        assert result.entries[2].opening_invested_capital_keur == pytest.approx(10000.0)


# ── Serialization-friendly ────────────────────────────────────────────────────

class TestSerializationFriendly:
    def test_all_entry_fields_json_serializable(self):
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [10000.0], [100.0])
        e = result.entries[0]
        # All fields are JSON-native types
        assert isinstance(e.period_index, int)
        assert isinstance(e.opening_invested_capital_keur, float)
        assert isinstance(e.invested_capital_delta_keur, float)
        assert isinstance(e.hurdle_rate_pa, float)
        assert isinstance(e.compounding_convention, str)
        assert isinstance(e.accrual_periods, float)
        assert isinstance(e.accrued_pref_keur, float)
        assert isinstance(e.cumulative_accrued_pref_keur, float)
        assert isinstance(e.cumulative_distributions_keur, float)
        assert isinstance(e.unpaid_pref_balance_keur, float)
        assert isinstance(e.hurdle_satisfied, bool)
        assert isinstance(e.audit_note, str)

    def test_result_fields_json_serializable(self):
        tier = make_pref_tier(0.08, CompoundingConvention.ANNUAL)
        result = calc(tier, [10000.0], [0.0])
        assert isinstance(result.sponsor_code, str)
        assert isinstance(result.hurdle_rate_pa, float)
        assert isinstance(result.compounding_convention, str)
        assert isinstance(result.entries, tuple)
        assert isinstance(result.total_accrued_pref_keur, float)
        assert isinstance(result.total_unpaid_pref_keur, float)
        assert isinstance(result.all_periods_hurdle_satisfied, bool)
        assert isinstance(result.audit_note, str)

    def test_entries_tuple_is_tuple_not_list(self):
        tier = make_pref_tier(0.08, CompoundingConvention.SIMPLE)
        result = calc(tier, [10000.0], [0.0])
        assert isinstance(result.entries, tuple)
