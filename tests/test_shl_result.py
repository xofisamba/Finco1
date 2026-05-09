"""Tests for SHL result structures — Phase 4A.

No sculpting. No capitalization. No tax logic.
"""
from __future__ import annotations

import pytest

from domain.portfolio.shl.inputs import SHLFacility
from domain.portfolio.shl.result import SHLPeriodResult, SHLFacilityResult, SHLPortfolioResult


class TestSHLPeriodResult:
    """SHLPeriodResult validation."""

    def test_valid_period(self):
        p = SHLPeriodResult(
            period_index=0,
            opening_balance_keur=1000.0,
            interest_accrued_keur=80.0,
            interest_paid_keur=80.0,
            principal_paid_keur=100.0,
            closing_balance_keur=900.0,
        )
        assert p.period_index == 0
        assert p.opening_balance_keur == 1000.0
        assert p.closing_balance_keur == 900.0
        assert p.interest_paid_keur == 80.0
        assert p.principal_paid_keur == 100.0

    def test_period_negative_index_raises(self):
        with pytest.raises(ValueError, match="period_index must be >= 0"):
            SHLPeriodResult(
                period_index=-1,
                opening_balance_keur=1000.0,
                interest_accrued_keur=80.0,
                interest_paid_keur=80.0,
                principal_paid_keur=100.0,
                closing_balance_keur=900.0,
            )

    def test_final_period_zero_balance(self):
        """Closing balance of 0.0 at final period is valid."""
        p = SHLPeriodResult(
            period_index=19,
            opening_balance_keur=100.0,
            interest_accrued_keur=8.0,
            interest_paid_keur=8.0,
            principal_paid_keur=100.0,
            closing_balance_keur=0.0,
        )
        assert p.closing_balance_keur == 0.0

    def test_zero_interest_period(self):
        """Period with zero interest (balance already paid off)."""
        p = SHLPeriodResult(
            period_index=5,
            opening_balance_keur=0.0,
            interest_accrued_keur=0.0,
            interest_paid_keur=0.0,
            principal_paid_keur=0.0,
            closing_balance_keur=0.0,
        )
        assert p.interest_accrued_keur == 0.0


class TestSHLFacilityResult:
    """SHLFacilityResult validation."""

    def test_valid_result(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        periods = (
            SHLPeriodResult(0, 1000.0, 80.0, 80.0, 200.0, 800.0),
            SHLPeriodResult(1, 800.0, 64.0, 64.0, 200.0, 600.0),
        )
        r = SHLFacilityResult(
            facility=f,
            periods=periods,
            total_interest_paid_keur=144.0,
            total_principal_paid_keur=400.0,
        )
        assert r.facility == f
        assert len(r.periods) == 2
        assert r.total_interest_paid_keur == 144.0
        assert r.total_principal_paid_keur == 400.0

    def test_empty_periods(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=0.0,  # zero principal
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        r = SHLFacilityResult(
            facility=f,
            periods=(),
            total_interest_paid_keur=0.0,
            total_principal_paid_keur=0.0,
        )
        assert r.periods == ()

    def test_negative_interest_raises(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        with pytest.raises(ValueError, match="total_interest_paid_keur must be >= 0"):
            SHLFacilityResult(
                facility=f,
                periods=(),
                total_interest_paid_keur=-10.0,
                total_principal_paid_keur=0.0,
            )


class TestSHLPortfolioResult:
    """SHLPortfolioResult validation."""

    def test_valid_portfolio(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=5,
        )
        fr = SHLFacilityResult(
            facility=f,
            periods=(),
            total_interest_paid_keur=400.0,
            total_principal_paid_keur=1000.0,
        )
        p = SHLPortfolioResult(
            facilities=(fr,),
            total_interest_paid_keur=400.0,
            total_principal_paid_keur=1000.0,
        )
        assert len(p.facilities) == 1
        assert p.total_interest_paid_keur == 400.0
        assert p.total_principal_paid_keur == 1000.0
        assert p.warnings == ()

    def test_empty_portfolio(self):
        p = SHLPortfolioResult()
        assert p.facilities == ()
        assert p.total_interest_paid_keur == 0.0
        assert p.total_principal_paid_keur == 0.0

    def test_multiple_facilities(self):
        f1 = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-A", principal_keur=5000.0, interest_rate_pa=0.08, tenor_years=10)
        f2 = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-B", principal_keur=3000.0, interest_rate_pa=0.07, tenor_years=8)
        fr1 = SHLFacilityResult(facility=f1, periods=(), total_interest_paid_keur=4000.0, total_principal_paid_keur=5000.0)
        fr2 = SHLFacilityResult(facility=f2, periods=(), total_interest_paid_keur=1680.0, total_principal_paid_keur=3000.0)
        p = SHLPortfolioResult(
            facilities=(fr1, fr2),
            total_interest_paid_keur=5680.0,
            total_principal_paid_keur=8000.0,
        )
        assert len(p.facilities) == 2
        assert p.total_interest_paid_keur == 5680.0

    def test_warnings_tuple(self):
        f = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV", principal_keur=1000.0, interest_rate_pa=0.08, tenor_years=5)
        fr = SHLFacilityResult(facility=f, periods=(), total_interest_paid_keur=400.0, total_principal_paid_keur=1000.0)
        p = SHLPortfolioResult(
            facilities=(fr,),
            warnings=("test warning",),
        )
        assert p.warnings == ("test warning",)