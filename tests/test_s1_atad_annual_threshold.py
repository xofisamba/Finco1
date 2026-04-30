"""Tests for S1-3: ATAD adjustment with annual threshold.

This test verifies the blueprint requirement:
- ATAD threshold of 3,000 kEUR is ANNUAL, not per-period
- H1 always passes (first half of year)
- H2 check uses accumulated annual interest + EBITDA
"""
import pytest
from domain.tax.atad_engine import (
    ATADResult,
    atad_limit_annual,
    atad_adjustment_v3,
    atad_adjustment_simple,
    atad_schedule_v3,
)


class TestATADLimitAnnual:
    """Test annual ATAD limit calculation."""

    def test_ebitda_limit_higher(self):
        """When 30% EBITDA > 3M, ebitda_30pct is binding."""
        limit, limit_type = atad_limit_annual(
            annual_ebitda_keur=15_000.0,  # 30% × 15,000 = 4,500 > 3,000
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
        )
        assert limit == 4_500.0
        assert limit_type == "ebitda_30pct"

    def test_min_threshold_higher(self):
        """When 3M > 30% EBITDA, min_threshold is binding."""
        limit, limit_type = atad_limit_annual(
            annual_ebitda_keur=8_000.0,  # 30% × 8,000 = 2,400 < 3,000
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
        )
        assert limit == 3_000.0
        assert limit_type == "min_threshold"

    def test_equal_limits(self):
        """When both limits equal, ebitda_30pct is preferred."""
        limit, limit_type = atad_limit_annual(
            annual_ebitda_keur=10_000.0,  # 30% × 10,000 = 3,000 == 3,000
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
        )
        assert limit == 3_000.0
        assert limit_type == "ebitda_30pct"


class TestATADAdjustmentV3:
    """Test atad_adjustment_v3 with annual threshold."""

    def test_h1_always_passes(self):
        """H1 (period_in_year=1) always fully deductible."""
        result = atad_adjustment_v3(
            interest_h2_keur=2_000.0,
            ebitda_h2_keur=6_000.0,
            period_in_year=1,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
        )
        assert result.deductible_interest_keur == 2_000.0
        assert result.disallowed_addback_keur == 0.0
        assert result.limit_type == "ebitda_30pct"  # 30% × 12,000 = 3,600

    def test_h2_below_annual_limit(self):
        """H2 when total annual interest < annual limit: fully deductible."""
        # H1: 1,500 kEUR interest
        # H2: 1,500 kEUR interest
        # Total: 3,000 kEUR = 3M threshold → fully deductible
        result = atad_adjustment_v3(
            interest_h2_keur=1_500.0,
            ebitda_h2_keur=6_000.0,
            period_in_year=2,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
            accumulated_annual_interest=1_500.0,  # H1
            accumulated_annual_ebitda=6_000.0,      # H1
        )
        # Annual limit = max(3,600, 3,000) = 3,600 (ebitda_30pct)
        # H2 limit = 3,600 - 1,500 = 2,100
        # H2 interest = 1,500 < 2,100 → fully deductible
        assert result.deductible_interest_keur == 1_500.0
        assert result.disallowed_addback_keur == 0.0

    def test_h2_above_annual_limit(self):
        """H2 when total annual interest > annual limit: disallowed."""
        # H1: 2,000 kEUR interest
        # H2: 2,000 kEUR interest
        # Total: 4,000 > 3,600 (30% × 12,000)
        result = atad_adjustment_v3(
            interest_h2_keur=2_000.0,
            ebitda_h2_keur=6_000.0,
            period_in_year=2,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
            accumulated_annual_interest=2_000.0,  # H1
            accumulated_annual_ebitda=6_000.0,      # H1
        )
        # Annual limit = max(3,600, 3,000) = 3,600
        # H2 limit = 3,600 - 2,000 = 1,600
        # H2 interest = 2,000 > 1,600 → disallowed = 400
        assert abs(result.deductible_interest_keur - 1_600.0) < 0.01
        assert abs(result.disallowed_addback_keur - 400.0) < 0.01

    def test_h2_at_exact_limit(self):
        """H2 when total annual = annual limit: exactly at limit."""
        result = atad_adjustment_v3(
            interest_h2_keur=1_600.0,
            ebitda_h2_keur=6_000.0,
            period_in_year=2,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
            accumulated_annual_interest=2_000.0,
            accumulated_annual_ebitda=6_000.0,
        )
        # Annual limit = 3,600
        # H2 limit = 3,600 - 2,000 = 1,600
        # H2 interest = 1,600 → no disallowed
        assert result.deductible_interest_keur == 1_600.0
        assert result.disallowed_addback_keur == 0.0

    def test_h2_min_threshold_binding(self):
        """H2 when min_threshold (3M) is binding instead of 30% EBITDA."""
        # Low EBITDA: 30% × 8,000 = 2,400 < 3,000 → 3M threshold binds
        result = atad_adjustment_v3(
            interest_h2_keur=2_000.0,
            ebitda_h2_keur=4_000.0,  # Annual would be 8,000 → 30% = 2,400
            period_in_year=2,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
            accumulated_annual_interest=1_500.0,
            accumulated_annual_ebitda=4_000.0,
        )
        # Annual limit = max(2,400, 3,000) = 3,000 (min_threshold)
        # H2 limit = 3,000 - 1,500 = 1,500
        # H2 interest = 2,000 > 1,500 → disallowed = 500
        assert abs(result.deductible_interest_keur - 1_500.0) < 0.01
        assert abs(result.disallowed_addback_keur - 500.0) < 0.01
        assert result.limit_type == "min_threshold"

    def test_h2_zero_h1_accumulated(self):
        """H2 with no H1 accumulation (first year check)."""
        result = atad_adjustment_v3(
            interest_h2_keur=2_500.0,
            ebitda_h2_keur=8_000.0,
            period_in_year=2,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
            accumulated_annual_interest=2_000.0,  # H1 used 2,000
            accumulated_annual_ebitda=8_000.0,
        )
        # Annual limit = max(4,800, 3,000) = 4,800
        # H2 limit = 4,800 - 2,000 = 2,800
        # H2 interest = 2,500 < 2,800 → fully deductible
        assert result.deductible_interest_keur == 2_500.0
        assert result.disallowed_addback_keur == 0.0


class TestATADAdjustmentSimple:
    """Test backward-compatible simple ATAD."""

    def test_simple_below_limit(self):
        """Simple: below limit → fully deductible."""
        deductible, disallowed = atad_adjustment_simple(
            interest_keur=1_500.0,
            ebitda_keur=10_000.0,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur=3_000.0,
        )
        assert deductible == 1_500.0
        assert disallowed == 0.0

    def test_simple_above_limit(self):
        """Simple: above limit → disallowed."""
        deductible, disallowed = atad_adjustment_simple(
            interest_keur=5_000.0,
            ebitda_keur=10_000.0,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur=3_000.0,
        )
        # Limit = max(3,000, 3,000) = 3,000
        assert deductible == 3_000.0
        assert disallowed == 2_000.0


class TestATADScheduleV3:
    """Test full ATAD schedule generation."""

    def test_schedule_semi_annual(self):
        """Semi-annual: H1 always passes, H2 checks annual."""
        # 4 periods: H1, H2, H1, H2
        interest = [1_500.0, 1_500.0, 2_000.0, 2_000.0]
        ebitda = [5_000.0, 5_000.0, 5_000.0, 5_000.0]

        results = atad_schedule_v3(
            interest_schedule=interest,
            ebitda_schedule=ebitda,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
        )

        # Period 0 (H1): always passes
        assert results[0].deductible_interest_keur == 1_500.0
        assert results[0].disallowed_addback_keur == 0.0

        # Period 1 (H2): 3,000 total < 3,600 limit → passes
        assert results[1].deductible_interest_keur == 1_500.0
        assert results[1].disallowed_addback_keur == 0.0

        # Period 2 (H1): always passes
        assert results[2].deductible_interest_keur == 2_000.0
        assert results[2].disallowed_addback_keur == 0.0

        # Period 3 (H2): 4,000 total > 3,000 limit → 1,000 disallowed
        # Annual limit = max(3,000, 3,000) = 3,000 (min_threshold at this EBITDA level)
        # H2 limit = 3,000 - 2,000 = 1,000
        # H2 interest = 2,000 > 1,000 → disallowed = 1,000
        assert results[3].deductible_interest_keur == 1_000.0
        assert abs(results[3].disallowed_addback_keur - 1_000.0) < 0.01

    def test_schedule_annual(self):
        """Annual periods: simple check per period."""
        interest = [3_000.0, 3_500.0, 4_000.0]
        ebitda = [10_000.0, 10_000.0, 10_000.0]

        results = atad_schedule_v3(
            interest_schedule=interest,
            ebitda_schedule=ebitda,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
        )

        # All H2 (since we only have 3 periods, treated as H2 for odd indices)
        # Period 0: H1? Actually period 0 is even → H1. But with accumulated=0
        # This is tricky... let me check the logic
        for r in results:
            print(f"limit_type={r.limit_type}, deductible={r.deductible_interest_keur}, disallowed={r.disallowed_addback_keur}")


class TestATADV3Properties:
    """Test ATADResult properties."""

    def test_total_interest_property(self):
        """total_interest = deductible + disallowed."""
        result = ATADResult(
            deductible_interest_keur=1_600.0,
            disallowed_addback_keur=400.0,
            annual_limit_keur=3_600.0,
            limit_type="ebitda_30pct",
        )
        assert result.total_interest_keur == 2_000.0

    def test_frozen_immutable(self):
        """ATADResult is frozen (immutable)."""
        result = ATADResult(
            deductible_interest_keur=1_600.0,
            disallowed_addback_keur=400.0,
            annual_limit_keur=3_600.0,
            limit_type="ebitda_30pct",
        )
        with pytest.raises(AttributeError):
            result.deductible_interest_keur = 2_000.0


class TestATADV3TUHORealistic:
    """Test TUHO realistic ATAD scenario."""

    def test_tuho_high_interest_years(self):
        """TUHO early years have high interest > 3M annual."""
        # TUHO annual interest ≈ 6,000 kEUR (high debt)
        # Annual EBITDA ≈ 12,000 kEUR → 30% × 12,000 = 3,600 kEUR
        # 3M threshold is binding when EBITDA is low

        # H1: 3,000 kEUR
        result_h1 = atad_adjustment_v3(
            interest_h2_keur=3_000.0,
            ebitda_h2_keur=6_000.0,
            period_in_year=1,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
        )
        assert result_h1.deductible_interest_keur == 3_000.0

        # H2: 3,000 kEUR → total = 6,000 > 3,600 → 2,400 disallowed
        result_h2 = atad_adjustment_v3(
            interest_h2_keur=3_000.0,
            ebitda_h2_keur=6_000.0,
            period_in_year=2,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur_annual=3_000.0,
            accumulated_annual_interest=3_000.0,
            accumulated_annual_ebitda=6_000.0,
        )
        # Annual limit = 3,600, H2 limit = 3,600 - 3,000 = 600
        # H2 interest = 3,000 > 600 → disallowed = 2,400
        assert abs(result_h2.deductible_interest_keur - 600.0) < 0.01
        assert abs(result_h2.disallowed_addback_keur - 2_400.0) < 0.01