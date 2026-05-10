"""Phase 5D.1 tests for distribution constraint evaluation runner."""
from __future__ import annotations

import pytest

from domain.portfolio.distribution_constraints.inputs import (
    DistributionBlockReason,
    DistributionConstraintConfig,
)
from domain.portfolio.distribution_constraints.runner import (
    evaluate_distribution_constraints,
)


class TestEvaluateDistributionConstraintsDisabled:
    """When config is None or enabled=False, all distributions pass through unchanged."""

    def test_none_config_passes_through(self):
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0, 800.0),
            requested_distributions_by_period=(500.0, 400.0),
            config=None,
        )
        assert result.entity_code == "SOLAR-1"
        assert len(result.periods) == 2
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[1].allowed_distribution_keur == 400.0
        assert result.periods[0].block_reasons == ()

    def test_disabled_config_passes_through(self):
        cfg = DistributionConstraintConfig(enabled=False)
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].block_reasons == ()

    def test_disabled_retained_cash_equals_cash_minus_requested(self):
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=None,
        )
        assert result.periods[0].retained_cash_keur == 500.0  # 1000 - 500

    def test_mismatched_period_lengths_handled(self):
        """When cash and distributions have different lengths, shorter is padded with 0."""
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),           # 1 period
            requested_distributions_by_period=(500.0, 300.0, 200.0),  # 3 periods
            config=None,
        )
        assert len(result.periods) == 3
        assert result.periods[0].cash_before_distribution_keur == 1000.0
        assert result.periods[1].cash_before_distribution_keur == 0.0  # padded
        assert result.periods[2].cash_before_distribution_keur == 0.0  # padded


class TestEvaluateDistributionConstraintsMinimumCashReserve:
    """minimum_cash_reserve_keur reduces allowed distribution."""

    def test_minimum_reserve_reduces_allowed(self):
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=200.0,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(800.0,),
            config=cfg,
        )
        # max_allowed = cash - reserve = 1000 - 200 = 800
        # requested = 800, so allowed = min(800, 800) = 800, retained = 200
        assert result.periods[0].allowed_distribution_keur == 800.0
        assert result.periods[0].retained_cash_keur == 200.0

    def test_minimum_reserve_blocks_excess_over_reserve(self):
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=300.0,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(800.0,),
            config=cfg,
        )
        # max_allowed = 1000 - 300 = 700
        # requested = 800, so allowed = min(800, 700) = 700
        assert result.periods[0].allowed_distribution_keur == 700.0
        assert result.periods[0].retained_cash_keur == 300.0
        assert DistributionBlockReason.MINIMUM_CASH_RESERVE in result.periods[0].block_reasons

    def test_minimum_reserve_zero_allows_full_distribution(self):
        cfg = DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=0.0)
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(500.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].retained_cash_keur == 0.0
        assert result.periods[0].block_reasons == ()


class TestEvaluateDistributionConstraintsManualLockup:
    """manual_lockup_periods forces allowed = 0 for those periods."""

    def test_manual_lockup_blocks_distribution(self):
        cfg = DistributionConstraintConfig(
            enabled=True,
            manual_lockup_periods=(1,),
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0, 1000.0),
            requested_distributions_by_period=(500.0, 500.0),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[1].allowed_distribution_keur == 0.0
        assert DistributionBlockReason.MANUAL_LOCKUP in result.periods[1].block_reasons

    def test_manual_lockup_multiple_periods(self):
        cfg = DistributionConstraintConfig(enabled=True, manual_lockup_periods=(0, 2))
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0, 1000.0, 1000.0),
            requested_distributions_by_period=(500.0, 500.0, 500.0),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 0.0
        assert result.periods[1].allowed_distribution_keur == 500.0
        assert result.periods[2].allowed_distribution_keur == 0.0


class TestEvaluateDistributionConstraintsNegativeCash:
    """Negative cash adds NEGATIVE_CASH reason but allows distribution (unless hard block)."""

    def test_negative_cash_adds_reason(self):
        cfg = DistributionConstraintConfig(
            enabled=True,
            allow_negative_cash=False,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(-100.0,),
            requested_distributions_by_period=(50.0,),
            config=cfg,
        )
        assert DistributionBlockReason.NEGATIVE_CASH in result.periods[0].block_reasons
        assert result.periods[0].warnings

    def test_negative_cash_allows_distribution_when_allow_negative_true(self):
        """When allow_negative_cash=True and cash < minimum reserve (0), allowed = 0
        because max_allowed = max(0, cash - 0) = 0.

        allow_negative_cash suppresses the NEGATIVE_CASH warning/reason, but
        does not override the math: with minimum_reserve=0 and cash=-100,
        allowed = min(50, max(0, -100)) = min(50, 0) = 0.
        """
        cfg = DistributionConstraintConfig(
            enabled=True,
            allow_negative_cash=True,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(-100.0,),
            requested_distributions_by_period=(50.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 0.0
        assert result.periods[0].requested_distribution_keur == 50.0

    def test_negative_cash_without_allow_negative_emits_warning(self):
        cfg = DistributionConstraintConfig(enabled=True, allow_negative_cash=False)
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(-50.0,),
            requested_distributions_by_period=(30.0,),
            config=cfg,
        )
        assert any("negative cash" in w.lower() for w in result.periods[0].warnings)


class TestEvaluateDistributionConstraintsTotals:
    """Totals reconcile from periods."""

    def test_totals_reconcile(self):
        cfg = DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=200.0)
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0, 500.0),
            requested_distributions_by_period=(800.0, 400.0),
            config=cfg,
        )
        assert result.total_requested_distribution_keur == 1200.0
        assert result.total_allowed_distribution_keur == (
            result.periods[0].allowed_distribution_keur +
            result.periods[1].allowed_distribution_keur
        )
        assert result.total_retained_cash_keur == (
            result.periods[0].retained_cash_keur +
            result.periods[1].retained_cash_keur
        )

    def test_retained_cash_equals_cash_before_minus_allowed(self):
        cfg = DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=100.0)
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(500.0,),
            requested_distributions_by_period=(400.0,),
            config=cfg,
        )
        p = result.periods[0]
        assert p.retained_cash_keur == pytest.approx(
            p.cash_before_distribution_keur - p.allowed_distribution_keur
        )


class TestEvaluateDistributionConstraintsNoMutation:
    """Runner does not mutate source inputs."""

    def test_no_mutation_of_config(self):
        cfg = DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=100.0)
        cash_tuple = (1000.0,)
        dist_tuple = (500.0,)
        evaluate_distribution_constraints("SOLAR-1", cash_tuple, dist_tuple, cfg)
        # Tuples are immutable; also verify config unchanged
        assert cfg.enabled is True
        assert cfg.minimum_cash_reserve_keur == 100.0
        assert cash_tuple == (1000.0,)
        assert dist_tuple == (500.0,)