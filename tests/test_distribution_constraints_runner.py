"""Phase 5D.1 tests for distribution constraint evaluation runner."""
from __future__ import annotations

import pytest

from domain.portfolio.distribution_constraints.inputs import (
    DistributionBlockReason,
    DistributionConstraintConfig,
    DistributionEnforcementMode,
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

    def test_minimum_reserve_with_off_mode_passes_through(self):
        """Phase 5G OFF: allowed stays requested, no MINIMUM_CASH_RESERVE reason."""
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
        assert result.periods[0].allowed_distribution_keur == 800.0
        assert result.periods[0].retained_cash_keur == 200.0
        assert result.periods[0].block_reasons == ()

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
    """Phase 5G: enabled=True + default OFF passes through (no lockup applied)."""

    def test_manual_lockup_with_off_mode_passes_through(self):
        """Phase 5G OFF: manual lockup not applied, allowed stays requested."""
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
        assert result.periods[1].allowed_distribution_keur == 500.0
        assert result.periods[1].block_reasons == ()

    def test_manual_lockup_multiple_periods_with_off_mode(self):
        """Phase 5G OFF: all periods pass through."""
        cfg = DistributionConstraintConfig(enabled=True, manual_lockup_periods=(0, 2))
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0, 1000.0, 1000.0),
            requested_distributions_by_period=(500.0, 500.0, 500.0),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[1].allowed_distribution_keur == 500.0
        assert result.periods[2].allowed_distribution_keur == 500.0
        assert result.periods[0].block_reasons == ()


class TestEvaluateDistributionConstraintsNegativeCash:
    """Negative cash adds NEGATIVE_CASH reason but allows distribution (unless hard block)."""

    def test_negative_cash_with_off_mode_passes_through(self):
        """OFF mode: negative cash reason NOT recorded, allowed stays requested."""
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
        assert result.periods[0].allowed_distribution_keur == 50.0
        assert result.periods[0].block_reasons == ()

    def test_negative_cash_off_mode_allow_negative_true(self):
        """OFF mode: allowed stays requested even with allow_negative_cash=True."""
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
        assert result.periods[0].allowed_distribution_keur == 50.0
        assert result.periods[0].block_reasons == ()

    def test_negative_cash_off_mode_no_warning(self):
        """OFF mode: negative cash emits no warning."""
        cfg = DistributionConstraintConfig(enabled=True, allow_negative_cash=False)
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(-50.0,),
            requested_distributions_by_period=(30.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 30.0
        assert result.periods[0].warnings == ()


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


class TestEnforcementModeSchema:
    """Phase 5G — enforcement mode is schema only, no active enforcement yet."""

    def test_off_preserves_pass_through_behavior(self):
        """OFF: audit-only pass-through, no reduction, no reasons."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=100.0,
            enforcement_mode=DistributionEnforcementMode.OFF,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        # OFF = pass-through → allowed = requested, no block reasons
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].block_reasons == ()

    def test_warning_only_does_not_reduce_allowed(self):
        """WARNING_ONLY: warnings computed but allowed unchanged."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=100.0,
            enforcement_mode=DistributionEnforcementMode.WARNING_ONLY,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        # allowed = requested (no reduction; min reserve still tracked but not enforced)
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].requested_distribution_keur == 500.0

    def test_soft_cap_emits_warning_not_active(self):
        """SOFT_CAP: emits warning that mode is not active yet."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            enforcement_mode=DistributionEnforcementMode.SOFT_CAP,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        # allowed should still equal requested (not enforced yet)
        assert result.periods[0].allowed_distribution_keur == 500.0
        # Warning should be present
        warning_text = " ".join(result.warnings)
        assert "not active in Phase 5G" in warning_text

    def test_hard_block_emits_warning_not_active(self):
        """HARD_BLOCK: emits warning that mode is not active yet."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            enforcement_mode=DistributionEnforcementMode.HARD_BLOCK,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        # allowed should still equal requested (not enforced yet)
        assert result.periods[0].allowed_distribution_keur == 500.0
        # Warning should be present
        warning_text = " ".join(result.warnings)
        assert "not active in Phase 5G" in warning_text

    def test_off_with_manual_lockup_no_reduction(self):
        """OFF: manual lockup reason NOT recorded, allowed stays requested."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            manual_lockup_periods=(0,),
            enforcement_mode=DistributionEnforcementMode.OFF,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].block_reasons == ()

    def test_warning_only_computes_manual_lockup_reason(self):
        """WARNING_ONLY: manual lockup reason computed, allowed stays requested."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            manual_lockup_periods=(0,),
            enforcement_mode=DistributionEnforcementMode.WARNING_ONLY,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert DistributionBlockReason.MANUAL_LOCKUP in result.periods[0].block_reasons

    def test_warning_only_with_min_cash_reserve_no_reduction(self):
        """WARNING_ONLY: min reserve reduces allowed NO; reason still recorded."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=200.0,
            enforcement_mode=DistributionEnforcementMode.WARNING_ONLY,
        )
        # cash=300, requested=500, min_reserve=200 → potential allowed = 100
        # But WARNING_ONLY: allowed stays as requested = 500
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(300.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].requested_distribution_keur == 500.0
        assert DistributionBlockReason.MINIMUM_CASH_RESERVE in result.periods[0].block_reasons

    def test_warning_only_with_manual_lockup_no_reduction(self):
        """WARNING_ONLY: manual lockup reason recorded but allowed stays requested."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            manual_lockup_periods=(0,),
            enforcement_mode=DistributionEnforcementMode.WARNING_ONLY,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert DistributionBlockReason.MANUAL_LOCKUP in result.periods[0].block_reasons

    def test_soft_cap_min_reserve_no_reduction(self):
        """SOFT_CAP: not active yet, allowed stays as requested."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=200.0,
            enforcement_mode=DistributionEnforcementMode.SOFT_CAP,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(300.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert "not active in Phase 5G" in " ".join(result.warnings)

    def test_hard_block_min_reserve_no_reduction(self):
        """HARD_BLOCK: not active yet, allowed stays as requested."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=200.0,
            enforcement_mode=DistributionEnforcementMode.HARD_BLOCK,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(300.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert "not active in Phase 5G" in " ".join(result.warnings)

    def test_off_with_min_reserve_no_reduction(self):
        """OFF: minimum reserve reason NOT recorded, allowed stays requested."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=200.0,
            enforcement_mode=DistributionEnforcementMode.OFF,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(300.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].block_reasons == ()

    def test_off_default_is_pass_through(self):
        """OFF default: allowed stays requested, no reasons."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            enforcement_mode=DistributionEnforcementMode.OFF,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(500.0,),
            requested_distributions_by_period=(300.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 300.0
        assert result.periods[0].block_reasons == ()

    def test_enabled_true_off_with_min_reserve_no_reduction(self):
        """OFF: enabled=True + min reserve → allowed stays requested, no reasons."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=100.0,
            enforcement_mode=DistributionEnforcementMode.OFF,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(300.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].block_reasons == ()

    def test_enabled_true_off_with_manual_lockup_no_reduction(self):
        """OFF: enabled=True + manual lockup → allowed stays requested, no reasons."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            manual_lockup_periods=(0,),
            enforcement_mode=DistributionEnforcementMode.OFF,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].block_reasons == ()

    def test_off_default_pass_through(self):
        """OFF is the default and passes everything through."""
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=0.0,
            enforcement_mode=DistributionEnforcementMode.OFF,
        )
        result = evaluate_distribution_constraints(
            entity_code="SOLAR-1",
            cash_available_by_period=(1000.0,),
            requested_distributions_by_period=(500.0,),
            config=cfg,
        )
        assert result.periods[0].allowed_distribution_keur == 500.0