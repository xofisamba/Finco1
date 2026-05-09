"""Tests for SHL inputs — Phase 4A.

No sculpting. No capitalization. No tax logic.
"""
from __future__ import annotations

import pytest

from domain.portfolio.shl.inputs import SHLFacility, SHLPortfolioInputs


class TestSHLFacility:
    """SHLFacility validation."""

    def test_valid_facility(self):
        f = SHLFacility(
            lender_entity_code="HOLDCO",
            borrower_entity_code="SPV-OBOROVO",
            principal_keur=10000.0,
            interest_rate_pa=0.08,
            tenor_years=10,
        )
        assert f.principal_keur == 10000.0
        assert f.interest_rate_pa == 0.08
        assert f.tenor_years == 10
        assert f.sculpted is False
        assert f.capitalization_allowed is False
        assert f.payment_frequency_per_year == 2
        assert f.start_period_index == 0

    def test_valid_facility_annual(self):
        f = SHLFacility(
            lender_entity_code="HOLDCO",
            borrower_entity_code="SPV-TUHO",
            principal_keur=5000.0,
            interest_rate_pa=0.07,
            tenor_years=5,
            payment_frequency_per_year=1,
        )
        assert f.payment_frequency_per_year == 1

    def test_valid_facility_monthly(self):
        f = SHLFacility(
            lender_entity_code="HOLDCO",
            borrower_entity_code="SPV-X",
            principal_keur=2000.0,
            interest_rate_pa=0.06,
            tenor_years=3,
            payment_frequency_per_year=12,
        )
        assert f.payment_frequency_per_year == 12

    def test_valid_facility_with_options(self):
        f = SHLFacility(
            lender_entity_code="HOLDCO",
            borrower_entity_code="SPV-Y",
            principal_keur=8000.0,
            interest_rate_pa=0.10,
            tenor_years=15,
            sculpted=True,
            capitalization_allowed=True,
            payment_frequency_per_year=4,
            start_period_index=2,
        )
        assert f.sculpted is True
        assert f.capitalization_allowed is True
        assert f.start_period_index == 2

    def test_empty_lender_raises(self):
        with pytest.raises(ValueError, match="lender_entity_code is required"):
            SHLFacility(lender_entity_code="", borrower_entity_code="SPV", principal_keur=1000.0, interest_rate_pa=0.08, tenor_years=5)

    def test_empty_borrower_raises(self):
        with pytest.raises(ValueError, match="borrower_entity_code is required"):
            SHLFacility(lender_entity_code="HC", borrower_entity_code="", principal_keur=1000.0, interest_rate_pa=0.08, tenor_years=5)

    def test_negative_principal_raises(self):
        with pytest.raises(ValueError, match="principal_keur must be >= 0"):
            SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV", principal_keur=-100.0, interest_rate_pa=0.08, tenor_years=5)

    def test_zero_principal_allowed(self):
        f = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV", principal_keur=0.0, interest_rate_pa=0.08, tenor_years=5)
        assert f.principal_keur == 0.0

    def test_negative_interest_rate_raises(self):
        with pytest.raises(ValueError, match="interest_rate_pa must be >= 0"):
            SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV", principal_keur=1000.0, interest_rate_pa=-0.05, tenor_years=5)

    def test_zero_interest_allowed(self):
        f = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV", principal_keur=1000.0, interest_rate_pa=0.0, tenor_years=5)
        assert f.interest_rate_pa == 0.0

    def test_zero_tenor_raises(self):
        with pytest.raises(ValueError, match="tenor_years must be > 0"):
            SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV", principal_keur=1000.0, interest_rate_pa=0.08, tenor_years=0)

    def test_negative_tenor_raises(self):
        with pytest.raises(ValueError, match="tenor_years must be > 0"):
            SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV", principal_keur=1000.0, interest_rate_pa=0.08, tenor_years=-2)

    def test_invalid_frequency_raises(self):
        with pytest.raises(ValueError, match="payment_frequency_per_year must be in"):
            SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV", principal_keur=1000.0, interest_rate_pa=0.08, tenor_years=5, payment_frequency_per_year=3)

    def test_negative_opening_balance_raises(self):
        with pytest.raises(ValueError, match="opening_balance_keur must be >= 0"):
            SHLPeriodResult(
                period_index=0, opening_balance_keur=-100.0,
                interest_accrued_keur=5.0, interest_paid_keur=5.0,
                principal_paid_keur=10.0, closing_balance_keur=90.0
            )

    def test_negative_closing_balance_raises(self):
        with pytest.raises(ValueError, match="closing_balance_keur must be >= 0"):
            SHLPeriodResult(
                period_index=0, opening_balance_keur=100.0,
                interest_accrued_keur=5.0, interest_paid_keur=5.0,
                principal_paid_keur=150.0, closing_balance_keur=-50.0
            )


class TestSHLPortfolioInputs:
    """SHLPortfolioInputs validation."""

    def test_empty_portfolio(self):
        p = SHLPortfolioInputs()
        assert p.facilities == ()

    def test_single_facility(self):
        f = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-A", principal_keur=5000.0, interest_rate_pa=0.08, tenor_years=10)
        p = SHLPortfolioInputs(facilities=(f,))
        assert len(p.facilities) == 1

    def test_multiple_facilities(self):
        f1 = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-A", principal_keur=5000.0, interest_rate_pa=0.08, tenor_years=10)
        f2 = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-B", principal_keur=3000.0, interest_rate_pa=0.07, tenor_years=8)
        p = SHLPortfolioInputs(facilities=(f1, f2))
        assert len(p.facilities) == 2

    def test_duplicate_lender_borrower_raises(self):
        f1 = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-A", principal_keur=5000.0, interest_rate_pa=0.08, tenor_years=10)
        f2 = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-A", principal_keur=3000.0, interest_rate_pa=0.07, tenor_years=8)
        with pytest.raises(ValueError, match="Duplicate SHL facility"):
            SHLPortfolioInputs(facilities=(f1, f2))

    def test_same_lender_different_borrower_allowed(self):
        f1 = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-A", principal_keur=5000.0, interest_rate_pa=0.08, tenor_years=10)
        f2 = SHLFacility(lender_entity_code="HC", borrower_entity_code="SPV-B", principal_keur=3000.0, interest_rate_pa=0.07, tenor_years=8)
        p = SHLPortfolioInputs(facilities=(f1, f2))
        assert len(p.facilities) == 2

    def test_different_lender_same_borrower_allowed(self):
        f1 = SHLFacility(lender_entity_code="HC-A", borrower_entity_code="SPV-X", principal_keur=5000.0, interest_rate_pa=0.08, tenor_years=10)
        f2 = SHLFacility(lender_entity_code="HC-B", borrower_entity_code="SPV-X", principal_keur=3000.0, interest_rate_pa=0.07, tenor_years=8)
        p = SHLPortfolioInputs(facilities=(f1, f2))
        assert len(p.facilities) == 2


# Import needed for test_negative_opening_balance_raises / test_negative_closing_balance_raises
from domain.portfolio.shl.result import SHLPeriodResult