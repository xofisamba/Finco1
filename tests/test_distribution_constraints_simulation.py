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


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_result(
    entity_code: str,
    periods: list,
    warnings=(),
):
    return DistributionConstraintResult(
        entity_code=entity_code,
        periods=tuple(periods),
        warnings=warnings,
    )


def make_period(
    period: int,
    entity_code: str,
    cash: float,
    requested: float,
    allowed: float,
    block_reasons=(),
    warnings=(),
) -> DistributionConstraintPeriod:
    return DistributionConstraintPeriod(
        period=period,
        entity_code=entity_code,
        cash_before_distribution_keur=cash,
        requested_distribution_keur=requested,
        allowed_distribution_keur=allowed,
        retained_cash_keur=cash - allowed,
        block_reasons=block_reasons,
        warnings=warnings,
    )


# ------------------------------------------------------------------
# Issue A: effective_allowed_by_entity_period
# ------------------------------------------------------------------

class TestSimulateDefaultUsesPeriodAllowed:
    """Default behavior uses period.allowed_distribution_keur."""

    def test_pass_through_zero_would_restrict(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 500.0),
        ])
        sims = simulate_distribution_enforcement((result,))
        assert sims[0].periods[0].would_restrict_keur == 0.0
        assert sims[0].periods[0].allowed_distribution_keur == 500.0

    def test_constrained_positive_would_restrict(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 300.0),
        ])
        sims = simulate_distribution_enforcement((result,))
        assert sims[0].periods[0].would_restrict_keur == 200.0
        assert sims[0].periods[0].allowed_distribution_keur == 300.0


class TestSimulateEffectiveAllowedOverride:
    """Override effective_allowed creates positive would_restrict even when input allowed=requested."""

    def test_override_creates_would_restrict_when_pass_through(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 500.0),  # allowed=requested (pass-through)
        ])
        # Simulate SOFT_CAP would cap at 300
        override = {("SOLAR-1", 0): 300.0}
        sims = simulate_distribution_enforcement((result,), effective_allowed_by_entity_period=override)
        assert sims[0].periods[0].would_restrict_keur == 200.0
        assert sims[0].periods[0].allowed_distribution_keur == 300.0

    def test_override_recalculated_retained(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 500.0),
        ])
        override = {("SOLAR-1", 0): 300.0}
        sims = simulate_distribution_enforcement((result,), effective_allowed_by_entity_period=override)
        # retained = cash_before - effective_allowed = 1000 - 300 = 700
        assert sims[0].periods[0].retained_cash_keur == 700.0

    def test_override_multiple_entities_and_periods(self):
        r1 = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 500.0),
        ])
        r2 = make_result("WIND-1", [
            make_period(0, "WIND-1", 2000.0, 800.0, 800.0),
            make_period(1, "WIND-1", 2000.0, 600.0, 600.0),
        ])
        override = {
            ("SOLAR-1", 0): 300.0,
            ("WIND-1", 1): 400.0,
        }
        sims = simulate_distribution_enforcement((r1, r2), effective_allowed_by_entity_period=override)
        assert sims[0].periods[0].would_restrict_keur == 200.0
        assert sims[1].periods[0].would_restrict_keur == 0.0  # not overridden
        assert sims[1].periods[1].would_restrict_keur == 200.0  # overridden: 600-400

    def test_empty_override_nothing_overridden(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 300.0),
        ])
        sims = simulate_distribution_enforcement((result,), effective_allowed_by_entity_period={})
        assert sims[0].periods[0].would_restrict_keur == 200.0
        assert sims[0].periods[0].allowed_distribution_keur == 300.0


class TestSimulateNoMutationOfInput:
    """Input constraint results are not mutated."""

    def test_allowed_unchanged_after_call(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 500.0),
        ])
        original = result.periods[0].allowed_distribution_keur
        _ = simulate_distribution_enforcement((result,), effective_allowed_by_entity_period={("SOLAR-1", 0): 200.0})
        assert result.periods[0].allowed_distribution_keur == original

    def test_returns_new_result_objects(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 500.0),
        ])
        sims = simulate_distribution_enforcement((result,))
        assert isinstance(sims[0].periods[0], DistributionConstraintSimulationPeriod)
        assert not isinstance(result.periods[0], DistributionConstraintSimulationPeriod)


# ------------------------------------------------------------------
# Issue B: safe block_reason conversion
# ------------------------------------------------------------------

class TestSafeBlockReasonConversion:
    """Block reasons converted safely: enum uses .value, string passed through."""

    def test_enum_reason_converts_correctly(self):
        result = make_result("SOLAR-1", [
            make_period(
                0, "SOLAR-1", 500.0, 400.0, 0.0,
                block_reasons=(DistributionBlockReason.MANUAL_LOCKUP,),
            ),
        ])
        sims = simulate_distribution_enforcement((result,))
        assert sims[0].periods[0].block_reasons == ("MANUAL_LOCKUP",)

    def test_multiple_enum_reasons(self):
        result = make_result("SOLAR-1", [
            make_period(
                0, "SOLAR-1", 500.0, 400.0, 0.0,
                block_reasons=(
                    DistributionBlockReason.MANUAL_LOCKUP,
                    DistributionBlockReason.MINIMUM_CASH_RESERVE,
                ),
            ),
        ])
        sims = simulate_distribution_enforcement((result,))
        assert sims[0].periods[0].block_reasons == (
            "MANUAL_LOCKUP",
            "MINIMUM_CASH_RESERVE",
        )

    def test_string_reason_passes_through(self):
        # Simulate a string block reason (not an enum)
        period = DistributionConstraintPeriod(
            period=0,
            entity_code="SOLAR-1",
            cash_before_distribution_keur=500.0,
            requested_distribution_keur=400.0,
            allowed_distribution_keur=0.0,
            retained_cash_keur=500.0,
            block_reasons=("CUSTOM_REASON",),  # str, not enum
            warnings=(),
        )
        result = DistributionConstraintResult(entity_code="SOLAR-1", periods=(period,))
        sims = simulate_distribution_enforcement((result,))
        assert sims[0].periods[0].block_reasons == ("CUSTOM_REASON",)


# ------------------------------------------------------------------
# Issue C: safer totals validation
# ------------------------------------------------------------------

class TestSimulationTotalsValidation:
    """Totals validation: only autofill when ALL totals are 0.0."""

    def test_all_zero_totals_autofill(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 300.0),
            make_period(1, "SOLAR-1", 1500.0, 700.0, 500.0),
        ])
        sims = simulate_distribution_enforcement((result,))
        assert sims[0].total_requested_distribution_keur == 1200.0
        assert sims[0].total_allowed_distribution_keur == 800.0
        assert sims[0].total_would_restrict_keur == 400.0
        assert sims[0].total_retained_cash_keur == 1700.0

    def test_all_zero_totals_autofill(self):
        """All-zero totals → auto-fill from periods."""
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 300.0),
            make_period(1, "SOLAR-1", 1500.0, 700.0, 500.0),
        ])
        sims = simulate_distribution_enforcement((result,))
        s = sims[0]
        assert s.total_requested_distribution_keur == 1200.0
        assert s.total_allowed_distribution_keur == 800.0
        assert s.total_would_restrict_keur == 400.0
        assert s.total_retained_cash_keur == 1700.0

    def test_wrong_allowed_total_validated_when_any_total_nonzero(self):
        """Non-zero allowed total that doesn't match computed raises."""
        sim_period = DistributionConstraintSimulationPeriod(
            period=0,
            entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=300.0,
            would_restrict_keur=200.0,
            retained_cash_keur=700.0,
            block_reasons=(),
            warnings=(),
        )
        # All four totals provided but allowed is wrong → should raise on allowed
        with pytest.raises(ValueError, match="total_allowed"):
            DistributionConstraintSimulationResult(
                entity_code="SOLAR-1",
                periods=(sim_period,),
                total_requested_distribution_keur=500.0,   # correct (matches 500)
                total_allowed_distribution_keur=999.0,    # wrong: should be 300
                total_would_restrict_keur=200.0,         # correct (matches 200)
                total_retained_cash_keur=700.0,          # correct (matches 700)
            )

    def test_wrong_retained_total_validated(self):
        """Wrong non-zero retained total raises."""
        sim_period = DistributionConstraintSimulationPeriod(
            period=0,
            entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=300.0,
            would_restrict_keur=200.0,
            retained_cash_keur=700.0,
            block_reasons=(),
            warnings=(),
        )
        with pytest.raises(ValueError, match="total_retained"):
            DistributionConstraintSimulationResult(
                entity_code="SOLAR-1",
                periods=(sim_period,),
                total_requested_distribution_keur=500.0,   # correct
                total_allowed_distribution_keur=300.0,     # correct
                total_would_restrict_keur=200.0,           # correct
                total_retained_cash_keur=9999.0,           # wrong: should be 700
            )

    def test_all_zero_totals_autofill_direct_construction(self):
        """All-zero simulation result → autofill."""
        sim_period = DistributionConstraintSimulationPeriod(
            period=0, entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=300.0,
            would_restrict_keur=200.0,
            retained_cash_keur=700.0,
            block_reasons=(), warnings=(),
        )
        result = DistributionConstraintSimulationResult(
            entity_code="SOLAR-1",
            periods=(sim_period,),
            # All four zero → auto-fill
            total_requested_distribution_keur=0.0,
            total_allowed_distribution_keur=0.0,
            total_would_restrict_keur=0.0,
            total_retained_cash_keur=0.0,
        )
        assert result.total_requested_distribution_keur == 500.0
        assert result.total_allowed_distribution_keur == 300.0
        assert result.total_would_restrict_keur == 200.0
        assert result.total_retained_cash_keur == 700.0


# ------------------------------------------------------------------
# Basic / regression tests
# ------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_returns_empty_tuple(self):
        assert simulate_distribution_enforcement(()) == ()


class TestPassThroughMultipleEntities:
    def test_two_entities(self):
        r1 = make_result("SOLAR-1", [make_period(0, "SOLAR-1", 1000.0, 500.0, 500.0)])
        r2 = make_result("WIND-1", [make_period(0, "WIND-1", 2000.0, 800.0, 800.0)])
        sims = simulate_distribution_enforcement((r1, r2))
        assert len(sims) == 2
        assert sims[0].entity_code == "SOLAR-1"
        assert sims[1].entity_code == "WIND-1"
        assert all(p.would_restrict_keur == 0.0 for s in sims for p in s.periods)


class TestWouldRestrictReconciliation:
    def test_total_would_restrict_equals_requested_minus_allowed(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", 1000.0, 500.0, 300.0),
            make_period(1, "SOLAR-1", 1500.0, 700.0, 500.0),
        ])
        sims = simulate_distribution_enforcement((result,))
        s = sims[0]
        assert s.total_would_restrict_keur == (
            s.total_requested_distribution_keur - s.total_allowed_distribution_keur
        )


class TestWarningsPreserved:
    def test_top_level_warnings_preserved(self):
        result = make_result(
            "SOLAR-1",
            [make_period(0, "SOLAR-1", 1000.0, 500.0, 500.0)],
            warnings=("Enforcement mode SOFT_CAP not active in Phase 5G",),
        )
        sims = simulate_distribution_enforcement((result,))
        assert sims[0].warnings == ("Enforcement mode SOFT_CAP not active in Phase 5G",)

    def test_period_warnings_preserved(self):
        result = make_result("SOLAR-1", [
            make_period(0, "SOLAR-1", -50.0, 30.0, 30.0, warnings=("negative cash",)),
        ])
        sims = simulate_distribution_enforcement((result,))
        assert sims[0].periods[0].warnings == ("negative cash",)
