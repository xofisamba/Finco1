"""Phase 7D — Multi-investor capital stack tests.

Comprehensive tests covering:
- Investor registry validation
- Capital stack building and validation
- Multi-investor waterfall runner
- Per-investor preferred return calculation
- Per-investor capital account generation
- Aggregate reconciliation
- Deterministic equality
- NaN/Inf rejection
- No mutation of inputs
"""
from __future__ import annotations

import pytest
import math

from domain.sponsor.investor_registry import (
    InvestorRole,
    InvestorEntry,
    InvestorRegistry,
)
from domain.sponsor.capital_stack import (
    CapitalContributionEntry,
    CapitalStack,
    build_capital_stack,
)
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
from domain.sponsor.multi_investor_waterfall_runner import (
    MultiInvestorWaterfallInputs,
    PerInvestorPreferredReturnInputs,
    PerInvestorWaterfallInputs,
    run_multi_investor_waterfall,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_investor(
    investor_id: str,
    role: InvestorRole,
    ownership_pct: float,
    committed: float,
) -> InvestorEntry:
    return InvestorEntry(
        investor_id=investor_id,
        role=role,
        ownership_percentage=ownership_pct,
        committed_capital_keur=committed,
    )


def make_registry(
    entries: list[InvestorEntry],
) -> InvestorRegistry:
    total_own = sum(e.ownership_percentage for e in entries)
    total_cap = sum(e.committed_capital_keur for e in entries)
    return InvestorRegistry(
        entries=tuple(entries),
        total_ownership_pct=total_own,
        total_committed_keur=total_cap,
    )


def make_contrib(
    investor_id: str,
    by_period: tuple[float, ...],
) -> CapitalContributionEntry:
    return CapitalContributionEntry(
        investor_id=investor_id,
        contributed_by_period_keur=by_period,
    )


# ── Investor Registry Tests ──────────────────────────────────────────────────

class TestInvestorRole:
    def test_role_values(self):
        assert InvestorRole.LP == "LP"
        assert InvestorRole.GP == "GP"
        assert InvestorRole.CO_INVESTOR == "CO_INVESTOR"

    def test_role_properties(self):
        lp = InvestorRole("LP")
        gp = InvestorRole("GP")
        co = InvestorRole("CO_INVESTOR")
        assert lp.is_lp is True
        assert lp.is_gp is False
        assert gp.is_gp is True
        assert co.is_co_investor is True

    def test_invalid_role_rejected(self):
        with pytest.raises(ValueError, match="InvestorRole must be one of"):
            InvestorRole("INVALID")

    def test_role_equality(self):
        assert InvestorRole("LP") == InvestorRole("LP")
        assert InvestorRole("LP") == "LP"
        assert InvestorRole("GP") != "LP"


class TestInvestorEntry:
    def test_valid_construction(self):
        e = InvestorEntry(
            investor_id="LP-1",
            role=InvestorRole("LP"),
            ownership_percentage=0.80,
            committed_capital_keur=8000.0,
        )
        assert e.investor_id == "LP-1"
        assert e.role == InvestorRole("LP")
        assert e.ownership_percentage == 0.80
        assert e.committed_capital_keur == 8000.0

    def test_rejects_empty_investor_id(self):
        with pytest.raises(ValueError, match="investor_id must be non-empty"):
            InvestorEntry(
                investor_id="",
                role=InvestorRole("LP"),
                ownership_percentage=1.0,
                committed_capital_keur=1000.0,
            )

    def test_rejects_whitespace_investor_id(self):
        with pytest.raises(ValueError, match="investor_id must be non-empty"):
            InvestorEntry(
                investor_id="  ",
                role=InvestorRole("LP"),
                ownership_percentage=1.0,
                committed_capital_keur=1000.0,
            )

    def test_rejects_negative_ownership(self):
        with pytest.raises(ValueError, match="ownership_percentage must be >= 0"):
            InvestorEntry(
                investor_id="LP-1",
                role=InvestorRole("LP"),
                ownership_percentage=-0.1,
                committed_capital_keur=1000.0,
            )

    def test_rejects_nan_commitment(self):
        with pytest.raises(ValueError, match="committed_capital_keur must be finite"):
            InvestorEntry(
                investor_id="LP-1",
                role=InvestorRole("LP"),
                ownership_percentage=1.0,
                committed_capital_keur=float("nan"),
            )

    def test_rejects_negative_commitment(self):
        with pytest.raises(ValueError, match="committed_capital_keur must be >= 0"):
            InvestorEntry(
                investor_id="LP-1",
                role=InvestorRole("LP"),
                ownership_percentage=1.0,
                committed_capital_keur=-100.0,
            )


class TestInvestorRegistry:
    def test_valid_two_investor(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        reg = make_registry([gp, lp])
        assert len(reg) == 2
        assert reg.gp.investor_id == "GP-1"
        assert reg.lps[0].investor_id == "LP-1"

    def test_three_investor_with_co_investor(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.60, 6000.0)
        co = make_investor("CO-1", InvestorRole("CO_INVESTOR"), 0.20, 2000.0)
        reg = make_registry([gp, lp, co])
        assert len(reg) == 3
        assert len(reg.lps) == 1
        assert len(reg.co_investors) == 1

    def test_ownership_must_sum_to_one(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.50, 5000.0)  # 0.20 + 0.50 != 1.0
        with pytest.raises(ValueError, match="Ownership percentages must sum to 1.0"):
            make_registry([gp, lp])

    def test_ownership_sum_within_tolerance(self):
        # 0.33 + 0.33 + 0.34 = 1.0 within tolerance
        gp = make_investor("GP-1", InvestorRole("GP"), 0.33, 3300.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.33, 3300.0)
        co = make_investor("CO-1", InvestorRole("CO_INVESTOR"), 0.34, 3400.0)
        reg = make_registry([gp, lp, co])
        assert len(reg) == 3

    def test_rejects_duplicate_investor_id(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("GP-1", InvestorRole("LP"), 0.80, 8000.0)  # duplicate ID
        with pytest.raises(ValueError, match="Duplicate investor_id"):
            make_registry([gp, lp])

    def test_rejects_no_gp(self):
        lp1 = make_investor("LP-1", InvestorRole("LP"), 0.60, 6000.0)
        lp2 = make_investor("LP-2", InvestorRole("LP"), 0.40, 4000.0)
        with pytest.raises(ValueError, match="Must have exactly one GP"):
            make_registry([lp1, lp2])

    def test_rejects_multiple_gp(self):
        gp1 = make_investor("GP-1", InvestorRole("GP"), 0.10, 1000.0)
        gp2 = make_investor("GP-2", InvestorRole("GP"), 0.10, 1000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        with pytest.raises(ValueError, match="Must have exactly one GP"):
            make_registry([gp1, gp2, lp])

    def test_rejects_empty_registry(self):
        with pytest.raises(ValueError, match="InvestorRegistry must contain at least one investor"):
            InvestorRegistry(entries=(), total_ownership_pct=0.0, total_committed_keur=0.0)

    def test_investor_for(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        reg = make_registry([gp, lp])
        assert reg.investor_for("LP-1").investor_id == "LP-1"
        with pytest.raises(KeyError):
            reg.investor_for("UNKNOWN")

    def test_frozen_immutable(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        reg = make_registry([gp, lp])
        with pytest.raises(Exception):
            reg.entries = ()  # type: ignore


# ── Capital Stack Tests ──────────────────────────────────────────────────────

class TestCapitalContributionEntry:
    def test_valid_construction(self):
        c = CapitalContributionEntry(
            investor_id="LP-1",
            contributed_by_period_keur=(0.0, 5000.0, 8000.0),
        )
        assert c.investor_id == "LP-1"
        assert len(c.contributed_by_period_keur) == 3
        assert c.contribution_delta(0) == 0.0
        assert c.contribution_delta(1) == 5000.0
        assert c.contribution_delta(2) == 3000.0

    def test_rejects_decreasing_cumulative(self):
        with pytest.raises(ValueError, match="contributed_by_period_keur must be non-decreasing"):
            CapitalContributionEntry(
                investor_id="LP-1",
                contributed_by_period_keur=(5000.0, 3000.0, 8000.0),
            )

    def test_rejects_nan(self):
        with pytest.raises(ValueError, match="contributed_by_period_keur.*must be finite"):
            CapitalContributionEntry(
                investor_id="LP-1",
                contributed_by_period_keur=(0.0, float("nan"), 5000.0),
            )

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="contributed_by_period_keur.*must be >= 0"):
            CapitalContributionEntry(
                investor_id="LP-1",
                contributed_by_period_keur=(0.0, -100.0, 5000.0),
            )

    def test_contributed_at_period(self):
        c = CapitalContributionEntry(
            investor_id="LP-1",
            contributed_by_period_keur=(0.0, 5000.0, 8000.0),
        )
        assert c.contributed_at_period(0) == 0.0
        assert c.contributed_at_period(1) == 5000.0
        assert c.contributed_at_period(2) == 8000.0


class TestCapitalStack:
    def test_build_two_investor(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        reg = make_registry([gp, lp])
        stack = build_capital_stack(
            registry=reg,
            contributions_by_investor={
                "GP-1": (0.0, 1000.0, 2000.0),
                "LP-1": (0.0, 4000.0, 8000.0),
            },
        )
        assert stack.num_periods == 3
        assert stack.total_committed_keur == 10000.0
        assert stack.total_contributed_by_period_keur == (0.0, 5000.0, 10000.0)
        assert len(stack) == 2

    def test_total_by_period_reconciles(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        reg = make_registry([gp, lp])
        stack = build_capital_stack(
            registry=reg,
            contributions_by_investor={
                "GP-1": (0.0, 1000.0, 2000.0),
                "LP-1": (0.0, 4000.0, 8000.0),
            },
        )
        # Period 1: 1000 + 4000 = 5000
        assert stack.total_contributed_by_period_keur[1] == 5000.0

    def test_rejects_missing_investor_in_contributions(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        reg = make_registry([gp, lp])
        with pytest.raises(KeyError, match="No contribution data for investor"):
            build_capital_stack(
                registry=reg,
                contributions_by_investor={
                    "GP-1": (0.0, 1000.0, 2000.0),
                    # LP-1 missing
                },
            )

    def test_contribution_for(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        reg = make_registry([gp, lp])
        stack = build_capital_stack(
            registry=reg,
            contributions_by_investor={
                "GP-1": (0.0, 1000.0, 2000.0),
                "LP-1": (0.0, 4000.0, 8000.0),
            },
        )
        c = stack.contribution_for("LP-1")
        assert c.investor_id == "LP-1"
        assert c.contributed_at_period(2) == 8000.0

    def test_num_periods_mismatch_rejected(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
        reg = make_registry([gp, lp])
        with pytest.raises(ValueError, match="has 2 periods, expected 3"):
            build_capital_stack(
                registry=reg,
                contributions_by_investor={
                    "GP-1": (0.0, 1000.0, 2000.0),
                    "LP-1": (0.0, 4000.0),  # Only 2 periods vs 3
                },
            )


# ── Multi-Investor Waterfall Tests ───────────────────────────────────────────

def _make_basic_inputs(
    num_periods=3,
    avail=None,
):
    """Create basic two-investor (GP + LP) waterfall inputs for testing."""
    gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
    lp = make_investor("LP-1", InvestorRole("LP"), 0.80, 8000.0)
    reg = make_registry([gp, lp])
    avail = avail or (5000.0, 5000.0, 5000.0)
    stack = build_capital_stack(
        registry=reg,
        contributions_by_investor={
            "GP-1": (0.0, 1000.0, 2000.0),
            "LP-1": (0.0, 4000.0, 8000.0),
        },
    )
    return MultiInvestorWaterfallInputs(
        capital_stack=stack,
        registry=reg,
        hurdle_rate_pa=0.08,
        compounding_convention=CompoundingConvention.SIMPLE,
        gp_promote_share=0.20,
        available_cash_by_period=avail,
    )


class TestMultiInvestorWaterfallInputs:
    def test_valid_construction(self):
        inputs = _make_basic_inputs()
        assert inputs.hurdle_rate_pa == 0.08
        assert inputs.gp_promote_share == 0.20
        assert len(inputs.available_cash_by_period) == 3

    def test_rejects_invalid_gp_promote_share(self):
        with pytest.raises(ValueError, match="gp_promote_share must be > 0"):
            MultiInvestorWaterfallInputs(
                capital_stack=_make_basic_inputs().capital_stack,
                registry=_make_basic_inputs().registry,
                hurdle_rate_pa=_make_basic_inputs().hurdle_rate_pa,
                compounding_convention=_make_basic_inputs().compounding_convention,
                gp_promote_share=0.0,
                available_cash_by_period=_make_basic_inputs().available_cash_by_period,
            )

    def test_rejects_nan_hurdle(self):
        gp2 = InvestorEntry(investor_id="GP-1", role=InvestorRole("GP"), ownership_percentage=0.20, committed_capital_keur=2000.0)
        lp2 = InvestorEntry(investor_id="LP-1", role=InvestorRole("LP"), ownership_percentage=0.80, committed_capital_keur=8000.0)
        reg2 = InvestorRegistry(entries=(gp2, lp2), total_ownership_pct=1.0, total_committed_keur=10000.0)
        stack2 = build_capital_stack(reg2, {"GP-1": (0.0, 1000.0, 2000.0), "LP-1": (0.0, 4000.0, 8000.0)})
        with pytest.raises(ValueError, match="hurdle_rate_pa must be finite"):
            MultiInvestorWaterfallInputs(
                capital_stack=stack2, registry=reg2,
                hurdle_rate_pa=float("nan"), compounding_convention=CompoundingConvention.SIMPLE,
                gp_promote_share=0.20, available_cash_by_period=(5000.0, 5000.0, 5000.0),
            )

    def test_rejects_num_periods_mismatch(self):
        gp2 = InvestorEntry(investor_id="GP-1", role=InvestorRole("GP"), ownership_percentage=0.20, committed_capital_keur=2000.0)
        lp2 = InvestorEntry(investor_id="LP-1", role=InvestorRole("LP"), ownership_percentage=0.80, committed_capital_keur=8000.0)
        reg2 = InvestorRegistry(entries=(gp2, lp2), total_ownership_pct=1.0, total_committed_keur=10000.0)
        stack2 = build_capital_stack(reg2, {"GP-1": (0.0, 1000.0, 2000.0), "LP-1": (0.0, 4000.0, 8000.0)})
        with pytest.raises(ValueError, match="available_cash_by_period has 1 periods"):
            MultiInvestorWaterfallInputs(
                capital_stack=stack2, registry=reg2,
                hurdle_rate_pa=0.08, compounding_convention=CompoundingConvention.SIMPLE,
                gp_promote_share=0.20, available_cash_by_period=(5000.0,),
            )


class TestRunMultiInvestorWaterfall:
    def test_basic_two_investor_run(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        assert result.registry is not None
        assert len(result.per_investor_results) == 2
        assert result.total_allocated_keur > 0.0

    def test_gp_catch_up_threshold_equals_total_committed(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        # Total committed = GP 2000 + LP 8000 = 10000
        assert result.gp_catch_up_threshold_keur == 10000.0

    def test_per_investor_has_correct_count(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        ids = {r.investor_id for r in result.per_investor_results}
        assert ids == {"GP-1", "LP-1"}

    def test_per_investor_ownership_pct(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        by_id = {r.investor_id: r for r in result.per_investor_results}
        assert by_id["GP-1"].ownership_pct == 0.20
        assert by_id["LP-1"].ownership_pct == 0.80

    def test_per_investor_pref_result_computed(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        by_id = {r.investor_id: r for r in result.per_investor_results}
        # LP has preferred return computed
        assert by_id["LP-1"].pref_result is not None
        assert by_id["LP-1"].pref_result.total_accrued_pref_keur > 0.0

    def test_per_investor_capital_account_generated(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        by_id = {r.investor_id: r for r in result.per_investor_results}
        assert by_id["LP-1"].capital_account is not None
        assert by_id["LP-1"].capital_account.investor_id == "LP-1"

    def test_aggregate_total_allocated_positive(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        assert result.total_allocated_keur > 0.0

    def test_available_cash_echoed_in_result(self):
        inputs = _make_basic_inputs(avail=(3000.0, 5000.0, 7000.0))
        result = run_multi_investor_waterfall(inputs)
        assert result.total_available_by_period_keur == (3000.0, 5000.0, 7000.0)


class TestMultiInvestorAggregateReconciliation:
    def test_aggregate_includes_all_tiers(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        agg = result.aggregate_waterfall_result
        tier_types = {e.tier_type for p in agg.period_results for e in p.tier_entries}
        # Aggregate waterfall has: ROC (proportional), PROMOTE, RESIDUAL
        # NOTE: PREFERRED_RETURN is per-investor (in pref_result), not aggregate
        # NOTE: GP_CATCH_UP is not needed - all ROC is satisfied proportionally
        assert TierType.RETURN_OF_CAPITAL in tier_types
        assert TierType.PROMOTE in tier_types
        assert TierType.RESIDUAL in tier_types

    def test_per_investor_waterfall_result_has_roc_and_promote(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        by_id = {r.investor_id: r for r in result.per_investor_results}
        lp_result = by_id["LP-1"].waterfall_result
        # LP's waterfall result has ROC and PROMOTE (PREF is in pref_result)
        tier_types = {e.tier_type for p in lp_result.period_results for e in p.tier_entries}
        assert TierType.RETURN_OF_CAPITAL in tier_types
        assert TierType.PROMOTE in tier_types
        # PREF is per-investor (stored in pref_result), not in waterfall_result
        assert TierType.PREFERRED_RETURN not in tier_types
        # GP_CATCH_UP is aggregate-only
        assert TierType.GP_CATCH_UP not in tier_types

    def test_deterministic_rerun(self):
        inputs = _make_basic_inputs()
        r1 = run_multi_investor_waterfall(inputs)
        r2 = run_multi_investor_waterfall(inputs)
        assert r1.total_allocated_keur == pytest.approx(r2.total_allocated_keur)
        for p1, p2 in zip(r1.aggregate_waterfall_result.period_results,
                          r2.aggregate_waterfall_result.period_results):
            assert p1.available_cash_keur == pytest.approx(p2.available_cash_keur)


class TestThreeInvestorScenario:
    def test_three_investor_gp_lp_coinvestor(self):
        gp = make_investor("GP-1", InvestorRole("GP"), 0.20, 2000.0)
        lp = make_investor("LP-1", InvestorRole("LP"), 0.60, 6000.0)
        co = make_investor("CO-1", InvestorRole("CO_INVESTOR"), 0.20, 2000.0)
        reg = make_registry([gp, lp, co])
        stack = build_capital_stack(
            registry=reg,
            contributions_by_investor={
                "GP-1": (0.0, 1000.0, 2000.0),
                "LP-1": (0.0, 3000.0, 6000.0),
                "CO-1": (0.0, 1000.0, 2000.0),
            },
        )
        inputs = MultiInvestorWaterfallInputs(
            capital_stack=stack,
            registry=reg,
            hurdle_rate_pa=0.08,
            compounding_convention=CompoundingConvention.SIMPLE,
            gp_promote_share=0.20,
            available_cash_by_period=(5000.0, 5000.0, 5000.0),
        )
        result = run_multi_investor_waterfall(inputs)
        assert len(result.per_investor_results) == 3
        ids = {r.investor_id for r in result.per_investor_results}
        assert ids == {"GP-1", "LP-1", "CO-1"}


class TestNaNInfRejection:
    def test_rejects_nan_available_cash(self):
        inputs = _make_basic_inputs(
            avail=(5000.0, float("nan"), 5000.0)
        )
        with pytest.raises(ValueError, match="available_cash_by_period.*must be finite"):
            run_multi_investor_waterfall(inputs)

    def test_rejects_inf_available_cash(self):
        inputs = _make_basic_inputs(
            avail=(5000.0, float("inf"), 5000.0)
        )
        with pytest.raises(ValueError, match="available_cash_by_period.*must be finite"):
            run_multi_investor_waterfall(inputs)


class TestNoMutation:
    def test_inputs_not_mutated(self):
        inputs = _make_basic_inputs()
        inputs_str_before = str(inputs)
        run_multi_investor_waterfall(inputs)
        assert str(inputs) == inputs_str_before

class TestMultiInvestorAggregateReconciliation:
    def test_multi_roc_no_first_investor_takes_all(self):
        """Regression test: aggregate proportional ROC must not allocate
        everything to the first investor's ROC tier.

        The Phase 7C waterfall runner processes tiers sequentially.
        If ROC tiers are placed sequentially (ROC_A then ROC_B),
        tier A would consume all available cash before tier B gets anything.
        The proportional-share approach solves this by using a SINGLE ROC tier
        with proportional sponsor shares (LP×80%, GP×20%).
        """
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        agg = result.aggregate_waterfall_result

        # In period 1: 5000 available, total invested = 5000
        # ROC should split proportionally: LP=4000 (80%), GP=1000 (20%)
        p1 = agg.period_results[1]
        roc_entries = [e for e in p1.tier_entries if e.tier_type == TierType.RETURN_OF_CAPITAL]
        assert len(roc_entries) == 1, "Should have exactly one ROC tier in aggregate waterfall"

        roc = roc_entries[0]
        lp_roc = roc.allocation_for("LP-1")
        gp_roc = roc.allocation_for("GP-1")
        # Both investors should receive ROC in the same tier
        assert lp_roc > 0, "LP should receive ROC allocation"
        assert gp_roc > 0, "GP should receive ROC allocation"
        # And both should get their proportional share
        assert lp_roc == pytest.approx(4000.0), f"LP ROC should be 4000, got {lp_roc}"
        assert gp_roc == pytest.approx(1000.0), f"GP ROC should be 1000, got {gp_roc}"
        # Total ROC in period 1 = 5000 (all available cash)
        assert lp_roc + gp_roc == pytest.approx(5000.0), "Total ROC should consume all available cash"



class TestPreferredReturnPerInvestor:
    def test_lp_pref_accrued_positive(self):
        inputs = _make_basic_inputs()
        result = run_multi_investor_waterfall(inputs)
        by_id = {r.investor_id: r for r in result.per_investor_results}
        lp_pref = by_id["LP-1"].pref_result
        assert lp_pref is not None
        assert lp_pref.total_accrued_pref_keur > 0.0

    def test_annuity_convention_accepted(self):
        gp2 = InvestorEntry(investor_id="GP-1", role=InvestorRole("GP"), ownership_percentage=0.20, committed_capital_keur=2000.0)
        lp2 = InvestorEntry(investor_id="LP-1", role=InvestorRole("LP"), ownership_percentage=0.80, committed_capital_keur=8000.0)
        reg2 = InvestorRegistry(entries=(gp2, lp2), total_ownership_pct=1.0, total_committed_keur=10000.0)
        stack2 = build_capital_stack(reg2, {"GP-1": (0.0, 1000.0, 2000.0), "LP-1": (0.0, 4000.0, 8000.0)})
        inputs = MultiInvestorWaterfallInputs(
            capital_stack=stack2, registry=reg2,
            hurdle_rate_pa=0.08, compounding_convention=CompoundingConvention.ANNUAL,
            gp_promote_share=0.20, available_cash_by_period=(5000.0, 5000.0, 5000.0),
        )
        result = run_multi_investor_waterfall(inputs)
        by_id = {r.investor_id: r for r in result.per_investor_results}
        assert by_id["LP-1"].pref_result is not None

    def test_semiannual_convention_accepted(self):
        gp2 = InvestorEntry(investor_id="GP-1", role=InvestorRole("GP"), ownership_percentage=0.20, committed_capital_keur=2000.0)
        lp2 = InvestorEntry(investor_id="LP-1", role=InvestorRole("LP"), ownership_percentage=0.80, committed_capital_keur=8000.0)
        reg2 = InvestorRegistry(entries=(gp2, lp2), total_ownership_pct=1.0, total_committed_keur=10000.0)
        stack2 = build_capital_stack(reg2, {"GP-1": (0.0, 1000.0, 2000.0), "LP-1": (0.0, 4000.0, 8000.0)})
        inputs = MultiInvestorWaterfallInputs(
            capital_stack=stack2, registry=reg2,
            hurdle_rate_pa=0.08, compounding_convention=CompoundingConvention.SEMIANNUAL,
            gp_promote_share=0.20, available_cash_by_period=(5000.0, 5000.0, 5000.0),
        )
        result = run_multi_investor_waterfall(inputs)
        by_id = {r.investor_id: r for r in result.per_investor_results}
        assert by_id["LP-1"].pref_result is not None
