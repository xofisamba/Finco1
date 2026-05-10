"""Phase 5H tests for distribution constraint enforcement simulation."""
from __future__ import annotations

import pytest

from domain.portfolio.distribution_constraints.inputs import DistributionBlockReason
from domain.portfolio.distribution_constraints.result import (
    DistributionConstraintPeriod,
    DistributionConstraintResult,
)
from domain.portfolio.distribution_constraints.simulation import (
    DistributionConstraintSimulationPeriod,
    DistributionConstraintSimulationResult,
    simulate_distribution_enforcement,
)


class TestSimulateDistributionEnforcementEmpty:
    """Empty input returns empty tuple."""

    def test_empty_input_returns_empty_tuple(self):
        result = simulate_distribution_enforcement(())
        assert result == ()
        assert len(result) == 0


class TestSimulateDistributionEnforcementPassThrough:
    """Pass-through constraint results produce zero would_restrict."""

    def test_pass_through_zero_would_restrict(self):
        """When allowed == requested, would_restrict = 0."""
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0,
                    entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0,
                    allowed_distribution_keur=500.0,
                    retained_cash_keur=500.0,
                    block_reasons=(),
                    warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert len(sims) == 1
        assert sims[0].total_would_restrict_keur == 0.0
        assert sims[0].total_requested_distribution_keur == 500.0
        assert sims[0].total_allowed_distribution_keur == 500.0

    def test_pass_through_multiple_periods(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
                    retained_cash_keur=500.0, block_reasons=(), warnings=(),
                ),
                DistributionConstraintPeriod(
                    period=1, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1200.0,
                    requested_distribution_keur=600.0, allowed_distribution_keur=600.0,
                    retained_cash_keur=600.0, block_reasons=(), warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert len(sims) == 1
        assert sims[0].total_would_restrict_keur == 0.0
        assert sims[0].total_requested_distribution_keur == 1100.0

    def test_pass_through_multiple_entities(self):
        r1 = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(DistributionConstraintPeriod(
                period=0, entity_code="SOLAR-1",
                cash_before_distribution_keur=1000.0,
                requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
                retained_cash_keur=500.0, block_reasons=(), warnings=(),
            ),),
        )
        r2 = DistributionConstraintResult(
            entity_code="WIND-1",
            periods=(DistributionConstraintPeriod(
                period=0, entity_code="WIND-1",
                cash_before_distribution_keur=2000.0,
                requested_distribution_keur=800.0, allowed_distribution_keur=800.0,
                retained_cash_keur=1200.0, block_reasons=(), warnings=(),
            ),),
        )
        sims = simulate_distribution_enforcement((r1, r2))
        assert len(sims) == 2
        assert sims[0].entity_code == "SOLAR-1"
        assert sims[1].entity_code == "WIND-1"
        assert sims[0].total_would_restrict_keur == 0.0
        assert sims[1].total_would_restrict_keur == 0.0


class TestSimulateDistributionEnforcementConstrained:
    """Constrained results show positive would_restrict."""

    def test_constrained_shows_positive_would_restrict(self):
        """When allowed < requested, would_restrict = requested - allowed."""
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0,
                    entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0,
                    allowed_distribution_keur=300.0,
                    retained_cash_keur=700.0,
                    block_reasons=(DistributionBlockReason.MINIMUM_CASH_RESERVE,),
                    warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert len(sims) == 1
        assert sims[0].periods[0].would_restrict_keur == 200.0
        assert sims[0].total_would_restrict_keur == 200.0

    def test_constrained_multiple_periods(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0, allowed_distribution_keur=300.0,
                    retained_cash_keur=700.0,
                    block_reasons=(DistributionBlockReason.MINIMUM_CASH_RESERVE,),
                    warnings=(),
                ),
                DistributionConstraintPeriod(
                    period=1, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1500.0,
                    requested_distribution_keur=700.0, allowed_distribution_keur=700.0,
                    retained_cash_keur=800.0,
                    block_reasons=(),
                    warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert sims[0].periods[0].would_restrict_keur == 200.0
        assert sims[0].periods[1].would_restrict_keur == 0.0
        assert sims[0].total_would_restrict_keur == 200.0

    def test_all_periods_constrained(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=500.0,
                    requested_distribution_keur=400.0, allowed_distribution_keur=0.0,
                    retained_cash_keur=500.0,
                    block_reasons=(DistributionBlockReason.MANUAL_LOCKUP,),
                    warnings=(),
                ),
                DistributionConstraintPeriod(
                    period=1, entity_code="SOLAR-1",
                    cash_before_distribution_keur=500.0,
                    requested_distribution_keur=400.0, allowed_distribution_keur=0.0,
                    retained_cash_keur=500.0,
                    block_reasons=(DistributionBlockReason.MANUAL_LOCKUP,),
                    warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert sims[0].periods[0].would_restrict_keur == 400.0
        assert sims[0].periods[1].would_restrict_keur == 400.0
        assert sims[0].total_would_restrict_keur == 800.0


class TestSimulateDistributionEnforcementBlockReasonsPreserved:
    """Block reasons from constraint results are preserved as strings."""

    def test_block_reasons_preserved_as_strings(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0,
                    entity_code="SOLAR-1",
                    cash_before_distribution_keur=500.0,
                    requested_distribution_keur=400.0,
                    allowed_distribution_keur=0.0,
                    retained_cash_keur=500.0,
                    block_reasons=(
                        DistributionBlockReason.MANUAL_LOCKUP,
                        DistributionBlockReason.MINIMUM_CASH_RESERVE,
                    ),
                    warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert sims[0].periods[0].block_reasons == (
            "MANUAL_LOCKUP",
            "MINIMUM_CASH_RESERVE",
        )

    def test_empty_block_reasons_empty_tuple(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
                    retained_cash_keur=500.0, block_reasons=(), warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert sims[0].periods[0].block_reasons == ()


class TestSimulateDistributionEnforcementWarningsPreserved:
    """Warnings from constraint results are preserved."""

    def test_warnings_preserved(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=-50.0,
                    requested_distribution_keur=30.0, allowed_distribution_keur=30.0,
                    retained_cash_keur=-80.0,
                    block_reasons=(),
                    warnings=("negative cash detected",),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert sims[0].periods[0].warnings == ("negative cash detected",)
        # Note: top-level result.warnings is empty here; only period-level warnings are set

    def test_top_level_warnings_preserved(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
                    retained_cash_keur=500.0, block_reasons=(), warnings=(),
                ),
            ),
            warnings=("Enforcement mode SOFT_CAP not active in Phase 5G",),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert sims[0].warnings == ("Enforcement mode SOFT_CAP not active in Phase 5G",)


class TestSimulateDistributionEnforcementTotalsReconcile:
    """Simulation totals reconcile from periods."""

    def test_totals_reconcile(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0, allowed_distribution_keur=300.0,
                    retained_cash_keur=700.0, block_reasons=(), warnings=(),
                ),
                DistributionConstraintPeriod(
                    period=1, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1500.0,
                    requested_distribution_keur=700.0, allowed_distribution_keur=500.0,
                    retained_cash_keur=1000.0, block_reasons=(), warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        s = sims[0]
        assert s.total_requested_distribution_keur == 1200.0
        assert s.total_allowed_distribution_keur == 800.0
        assert s.total_would_restrict_keur == 400.0
        assert s.total_retained_cash_keur == 1700.0
        assert s.total_would_restrict_keur == (
            s.total_requested_distribution_keur - s.total_allowed_distribution_keur
        )

    def test_totals_auto_computed(self):
        """When totals are 0.0, they are auto-computed from periods."""
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0, allowed_distribution_keur=300.0,
                    retained_cash_keur=700.0, block_reasons=(), warnings=(),
                ),
            ),
            # Explicitly set totals to 0.0 (default)
            total_requested_distribution_keur=0.0,
            total_allowed_distribution_keur=0.0,
            total_retained_cash_keur=0.0,
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        assert sims[0].total_requested_distribution_keur == 500.0
        assert sims[0].total_allowed_distribution_keur == 300.0
        assert sims[0].total_would_restrict_keur == 200.0


class TestSimulateDistributionEnforcementNoMutation:
    """Simulation does not mutate input constraint results."""

    def test_no_mutation_of_input(self):
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0, allowed_distribution_keur=300.0,
                    retained_cash_keur=700.0, block_reasons=(), warnings=(),
                ),
            ),
        )
        original_allowed = constraint_result.periods[0].allowed_distribution_keur
        original_requested = constraint_result.periods[0].requested_distribution_keur

        _ = simulate_distribution_enforcement((constraint_result,))

        # Verify no mutation
        assert constraint_result.periods[0].allowed_distribution_keur == original_allowed
        assert constraint_result.periods[0].requested_distribution_keur == original_requested

    def test_returns_new_objects(self):
        """Simulation returns new objects; inputs are not modified."""
        constraint_result = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(
                DistributionConstraintPeriod(
                    period=0, entity_code="SOLAR-1",
                    cash_before_distribution_keur=1000.0,
                    requested_distribution_keur=500.0, allowed_distribution_keur=300.0,
                    retained_cash_keur=700.0, block_reasons=(), warnings=(),
                ),
            ),
        )
        sims = simulate_distribution_enforcement((constraint_result,))
        # The simulation period is a new object
        assert sims[0].periods[0].entity_code == "SOLAR-1"
        assert isinstance(sims[0].periods[0], DistributionConstraintSimulationPeriod)
        # The input result period is unchanged
        assert isinstance(constraint_result.periods[0], DistributionConstraintPeriod)
