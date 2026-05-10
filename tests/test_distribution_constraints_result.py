"""Phase 5D.1 tests for distribution constraint result structures."""
from __future__ import annotations

import pytest

from domain.portfolio.distribution_constraints.inputs import DistributionBlockReason
from domain.portfolio.distribution_constraints.result import (
    DistributionConstraintPeriod,
    DistributionConstraintResult,
)


class TestDistributionConstraintPeriod:
    def test_valid_construction(self):
        p = DistributionConstraintPeriod(
            period=0,
            entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=500.0,
            retained_cash_keur=500.0,
            block_reasons=(DistributionBlockReason.NONE,),
            warnings=(),
        )
        assert p.period == 0
        assert p.allowed_distribution_keur == 500.0
        assert p.retained_cash_keur == 500.0

    def test_allowed_cannot_exceed_requested(self):
        with pytest.raises(ValueError, match="allowed_distribution_keur .+ cannot exceed"):
            DistributionConstraintPeriod(
                period=0,
                entity_code="SOLAR-1",
                cash_before_distribution_keur=1000.0,
                requested_distribution_keur=300.0,
                allowed_distribution_keur=500.0,  # exceeds requested
                retained_cash_keur=500.0,
            )

    def test_negative_period_rejected(self):
        with pytest.raises(ValueError, match="period must be >= 0"):
            DistributionConstraintPeriod(
                period=-1,
                entity_code="SOLAR-1",
                cash_before_distribution_keur=1000.0,
                requested_distribution_keur=500.0,
                allowed_distribution_keur=500.0,
                retained_cash_keur=500.0,
            )

    def test_equal_allowed_and_requested_allowed(self):
        """allowed == requested is valid (no constraint applied)."""
        p = DistributionConstraintPeriod(
            period=0,
            entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=500.0,
            retained_cash_keur=500.0,
        )
        assert p.allowed_distribution_keur == p.requested_distribution_keur

    def test_zero_allowed_valid(self):
        """Full block: allowed = 0, retained = cash_before."""
        p = DistributionConstraintPeriod(
            period=0,
            entity_code="SOLAR-1",
            cash_before_distribution_keur=500.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=0.0,
            retained_cash_keur=500.0,
            block_reasons=(DistributionBlockReason.MANUAL_LOCKUP,),
        )
        assert p.allowed_distribution_keur == 0.0
        assert p.retained_cash_keur == 500.0


class TestDistributionConstraintResult:
    def test_empty_result(self):
        r = DistributionConstraintResult(entity_code="SOLAR-1")
        assert r.entity_code == "SOLAR-1"
        assert r.periods == ()
        assert r.total_requested_distribution_keur == 0.0

    def test_totals_computed_from_periods(self):
        p1 = DistributionConstraintPeriod(
            period=0, entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=500.0,
            retained_cash_keur=500.0,
        )
        p2 = DistributionConstraintPeriod(
            period=1, entity_code="SOLAR-1",
            cash_before_distribution_keur=800.0,
            requested_distribution_keur=300.0,
            allowed_distribution_keur=300.0,
            retained_cash_keur=500.0,
        )
        r = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(p1, p2),
            total_requested_distribution_keur=800.0,
            total_allowed_distribution_keur=800.0,
            total_retained_cash_keur=1000.0,
        )
        assert r.total_requested_distribution_keur == 800.0
        assert r.total_allowed_distribution_keur == 800.0
        assert r.total_retained_cash_keur == 1000.0

    def test_warning_tuple_accepted(self):
        p1 = DistributionConstraintPeriod(
            period=0, entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=500.0,
            retained_cash_keur=500.0,
            warnings=("negative cash warning",),
        )
        r = DistributionConstraintResult(
            entity_code="SOLAR-1",
            periods=(p1,),
            warnings=("negative cash warning",),
        )
        assert "negative cash warning" in r.warnings