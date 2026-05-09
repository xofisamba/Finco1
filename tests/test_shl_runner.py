"""Tests for SHL engine (runner) — Phase 4A.

No sculpting. No capitalization. Straight-line amortization only.
"""
from __future__ import annotations

import pytest

from domain.portfolio.shl.inputs import SHLFacility, SHLPortfolioInputs
from domain.portfolio.shl.runner import run_shl_facility, run_shl_portfolio


class TestRunSHLFacility:
    """run_shl_facility tests — straight-line amortization."""

    def test_straight_line_amortization_5yr_semiannual(self):
        """5-year semiannual (10 periods), 10000 keur at 8% pa."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=10000.0,
            interest_rate_pa=0.08,
            tenor_years=5,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)

        assert len(result.periods) == 10
        # Principal per period = 10000 / 10 = 1000 (regular periods)
        # Last period pays remaining balance after interest
        principals = [p.principal_paid_keur for p in result.periods]
        for p in principals[:-1]:
            assert p == pytest.approx(1000.0, rel=1e-6)
        # Final closing balance should be 0 (within tolerance)
        assert result.periods[-1].closing_balance_keur == pytest.approx(0.0, abs=1e-6)

    def test_interest_declines_over_time(self):
        """Interest paid decreases as opening balance declines."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)

        interests = [p.interest_paid_keur for p in result.periods]
        # First period interest: 1000 * 0.08 / 2 = 40
        assert interests[0] == pytest.approx(40.0, rel=1e-6)
        # Second period interest: lower than first (balance reduced)
        assert interests[1] < interests[0]
        # Third period: lower still
        assert interests[2] < interests[1]
        # Fourth period: lowest
        assert interests[3] < interests[2]
        assert interests[3] > 0

    def test_balances_never_negative(self):
        """Opening and closing balances are never negative."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.10,
            tenor_years=3,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)

        for p in result.periods:
            assert p.opening_balance_keur >= 0.0
            assert p.closing_balance_keur >= 0.0

    def test_final_balance_near_zero(self):
        """Final closing balance is within tolerance of zero."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=5000.0,
            interest_rate_pa=0.075,
            tenor_years=7,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)

        assert result.periods[-1].closing_balance_keur == pytest.approx(0.0, abs=1e-6)

    def test_total_principal_equals_original(self):
        """Sum of principal_paid_keur equals original principal (within rounding)."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=12345.0,
            interest_rate_pa=0.09,
            tenor_years=6,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)

        total_principal = sum(p.principal_paid_keur for p in result.periods)
        assert total_principal == pytest.approx(f.principal_keur, rel=1e-4)

    def test_zero_principal_returns_empty(self):
        """Zero principal facility returns empty periods."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=0.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        result = run_shl_facility(f)

        assert result.periods == ()
        assert result.total_interest_paid_keur == 0.0
        assert result.total_principal_paid_keur == 0.0

    def test_annual_frequency(self):
        """Annual frequency (1 per year) works correctly."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=4,
            payment_frequency_per_year=1,
        )
        result = run_shl_facility(f)

        assert len(result.periods) == 4
        # Principal per regular period = 1000 / 4 = 250
        for p in result.periods[:-1]:
            assert p.principal_paid_keur == pytest.approx(250.0, rel=1e-6)
        assert result.periods[-1].closing_balance_keur == pytest.approx(0.0, abs=1e-6)

    def test_monthly_frequency(self):
        """Monthly frequency (12 per year) works correctly."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=12000.0,
            interest_rate_pa=0.06,
            tenor_years=1,
            payment_frequency_per_year=12,
        )
        result = run_shl_facility(f)

        assert len(result.periods) == 12
        # Principal per regular period = 12000 / 12 = 1000
        for p in result.periods[:-1]:
            assert p.principal_paid_keur == pytest.approx(1000.0, rel=1e-6)
        assert result.periods[-1].closing_balance_keur == pytest.approx(0.0, abs=1e-6)

    def test_interest_accrued_equals_interest_paid_no_capitalization(self):
        """Without capitalization, interest_accrued == interest_paid."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=1,
            capitalization_allowed=False,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)

        for p in result.periods:
            assert p.interest_accrued_keur == p.interest_paid_keur

    def test_opening_equals_previous_closing(self):
        """Each period's opening balance equals prior period's closing balance."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=2000.0,
            interest_rate_pa=0.07,
            tenor_years=3,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)

        for i in range(1, len(result.periods)):
            assert result.periods[i].opening_balance_keur == result.periods[i-1].closing_balance_keur

    def test_zero_interest_rate(self):
        """Zero interest rate — only principal payments."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.0,
            tenor_years=5,
        )
        result = run_shl_facility(f)

        for p in result.periods:
            assert p.interest_accrued_keur == 0.0
            assert p.interest_paid_keur == 0.0
        assert result.periods[-1].closing_balance_keur == pytest.approx(0.0, abs=1e-6)


class TestRunSHLPortfolio:
    """run_shl_portfolio tests — multi-facility aggregation."""

    def test_empty_portfolio(self):
        inputs = SHLPortfolioInputs(facilities=())
        result = run_shl_portfolio(inputs)

        assert result.facilities == ()
        assert result.total_interest_paid_keur == 0.0
        assert result.total_principal_paid_keur == 0.0

    def test_single_facility(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV-A",
            principal_keur=5000.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        inputs = SHLPortfolioInputs(facilities=(f,))
        result = run_shl_portfolio(inputs)

        assert len(result.facilities) == 1
        assert result.facilities[0].facility == f
        assert result.total_principal_paid_keur == pytest.approx(5000.0, rel=1e-4)

    def test_multiple_facilities_aggregate_totals(self):
        f1 = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV-A",
            principal_keur=5000.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        f2 = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV-B",
            principal_keur=3000.0,
            interest_rate_pa=0.07,
            tenor_years=4,
        )
        inputs = SHLPortfolioInputs(facilities=(f1, f2))
        result = run_shl_portfolio(inputs)

        assert len(result.facilities) == 2
        # Total principal = 5000 + 3000 = 8000
        assert result.total_principal_paid_keur == pytest.approx(8000.0, rel=1e-4)
        # Total interest > 0 (both have positive rates)
        assert result.total_interest_paid_keur > 0.0

    def test_different_tenors(self):
        """Facilities with different tenors produce correct period counts."""
        f_short = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV-SHORT",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
        )
        f_long = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV-LONG",
            principal_keur=2000.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        inputs = SHLPortfolioInputs(facilities=(f_short, f_long))
        result = run_shl_portfolio(inputs)

        short_result = result.facilities[0]
        long_result = result.facilities[1]
        assert len(short_result.periods) == 4  # 2yr * 2
        assert len(long_result.periods) == 10  # 5yr * 2

    def test_zero_principal_facility_in_portfolio(self):
        """Zero-principal facility is handled gracefully."""
        f1 = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV-A",
            principal_keur=5000.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        f2 = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV-B",
            principal_keur=0.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        inputs = SHLPortfolioInputs(facilities=(f1, f2))
        result = run_shl_portfolio(inputs)

        assert len(result.facilities) == 2
        assert result.total_principal_paid_keur == pytest.approx(5000.0, rel=1e-4)

    def test_facility_result_reflects_individual_schedule(self):
        """Each facility result has its own period schedule."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=3000.0,
            interest_rate_pa=0.08,
            tenor_years=3,
        )
        inputs = SHLPortfolioInputs(facilities=(f,))
        result = run_shl_portfolio(inputs)

        fr = result.facilities[0]
        assert len(fr.periods) == 6  # 3yr * 2
        assert fr.total_principal_paid_keur == pytest.approx(3000.0, rel=1e-4)
        # Last period closing = 0
        assert fr.periods[-1].closing_balance_keur == pytest.approx(0.0, abs=1e-6)

class TestSHLStartPeriodIndex:
    """run_shl_facility honors facility.start_period_index."""

    def test_start_period_index_offsets_period_indexes(self):
        """period_index values start at start_period_index."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.0,  # zero rate for clarity
            tenor_years=2,
            payment_frequency_per_year=2,
            start_period_index=4,
        )
        result = run_shl_facility(f)

        assert len(result.periods) == 4
        # Period indexes should be 4, 5, 6, 7
        for i, p in enumerate(result.periods):
            assert p.period_index == 4 + i, f"Expected {4+i}, got {p.period_index}"

    def test_start_period_index_does_not_change_total_interest(self):
        """start_period_index does not affect interest/principal totals."""
        f_offset = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
            start_period_index=10,
        )
        f_zero = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
            start_period_index=0,
        )
        r_offset = run_shl_facility(f_offset)
        r_zero = run_shl_facility(f_zero)

        # Totals must be identical regardless of start index
        assert r_offset.total_interest_paid_keur == r_zero.total_interest_paid_keur
        assert r_offset.total_principal_paid_keur == r_zero.total_principal_paid_keur

    def test_start_period_index_zero_keeps_existing_behavior(self):
        """start_period_index=0 produces period_index starting at 0."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=3,
            payment_frequency_per_year=2,
            start_period_index=0,
        )
        result = run_shl_facility(f)

        assert len(result.periods) == 6
        for i, p in enumerate(result.periods):
            assert p.period_index == i

    def test_start_period_index_late_start(self):
        """start_period_index can be large (e.g., SPV construction delay)."""
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=2000.0,
            interest_rate_pa=0.08,
            tenor_years=1,
            payment_frequency_per_year=2,
            start_period_index=36,  # 18 months of construction
        )
        result = run_shl_facility(f)

        assert len(result.periods) == 2
        assert result.periods[0].period_index == 36
        assert result.periods[1].period_index == 37
        # Opening balance in first SHL period still equals principal
        assert result.periods[0].opening_balance_keur == pytest.approx(2000.0, rel=1e-6)
        # Final balance = 0
        assert result.periods[-1].closing_balance_keur == pytest.approx(0.0, abs=1e-6)
