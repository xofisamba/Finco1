"""Tests for HoldCo result structures — Phase 3A skeleton only.

No cash flow tests. No SHL. No tax template.
"""
from __future__ import annotations

import pytest

from domain.portfolio.holdco import (
    HoldCoResult,
    HoldCoPeriodResult,
    HoldCoSPVContribution,
)


class TestHoldCoSPVContribution:
    """HoldCoSPVContribution validation."""

    def test_valid_contribution(self):
        c = HoldCoSPVContribution(
            period=1,
            spv_code="OBOROVO",
            ownership_pct=1.0,
            spv_distribution_keur=1000.0,
            holdco_share_keur=1000.0,
        )
        assert c.period == 1
        assert c.spv_code == "OBOROVO"
        assert c.holdco_share_keur == 1000.0

    def test_period_negative_raises(self):
        with pytest.raises(ValueError, match="period must be >= 0"):
            HoldCoSPVContribution(period=-1, spv_code="X", ownership_pct=1.0)

    def test_ownership_pct_out_of_range_raises(self):
        with pytest.raises(ValueError, match="ownership_pct must be in"):
            HoldCoSPVContribution(period=0, spv_code="X", ownership_pct=1.5)

    def test_negative_distribution_raises(self):
        with pytest.raises(ValueError, match="spv_distribution_keur must be >= 0"):
            HoldCoSPVContribution(
                period=0, spv_code="X", ownership_pct=1.0, spv_distribution_keur=-10.0
            )


class TestHoldCoPeriodResult:
    """HoldCoPeriodResult validation."""

    def test_valid_period_result(self):
        p = HoldCoPeriodResult(
            period=5,
            contributions=[
                HoldCoSPVContribution(
                    period=5, spv_code="OBOROVO", ownership_pct=1.0,
                    spv_distribution_keur=500.0, holdco_share_keur=500.0
                )
            ],
            gross_income_keur=500.0,
            holdco_opex_keur=50.0,
            taxable_income_keur=450.0,
            tax_keur=90.0,
            distribution_to_sponsor_keur=360.0,
        )
        assert p.period == 5
        assert len(p.contributions) == 1
        assert p.distribution_to_sponsor_keur == 360.0

    def test_period_negative_raises(self):
        with pytest.raises(ValueError, match="period must be >= 0"):
            HoldCoPeriodResult(period=-1)

    def test_gross_negative_raises(self):
        with pytest.raises(ValueError, match="gross_income_keur must be >= 0"):
            HoldCoPeriodResult(period=0, gross_income_keur=-1.0)

    def test_opex_negative_raises(self):
        with pytest.raises(ValueError, match="holdco_opex_keur must be >= 0"):
            HoldCoPeriodResult(period=0, holdco_opex_keur=-1.0)

    def test_tax_negative_raises(self):
        with pytest.raises(ValueError, match="tax_keur must be >= 0"):
            HoldCoPeriodResult(period=0, tax_keur=-1.0)

    def test_distribution_negative_raises(self):
        with pytest.raises(ValueError, match="distribution_to_sponsor_keur must be >= 0"):
            HoldCoPeriodResult(period=0, distribution_to_sponsor_keur=-1.0)

    def test_holdco_irr_none_by_default(self):
        p = HoldCoPeriodResult(period=0)
        assert p.holdco_irr is None

    def test_multiple_contributions(self):
        p = HoldCoPeriodResult(
            period=3,
            contributions=[
                HoldCoSPVContribution(
                    period=3, spv_code="A", ownership_pct=1.0,
                    spv_distribution_keur=300.0, holdco_share_keur=300.0
                ),
                HoldCoSPVContribution(
                    period=3, spv_code="B", ownership_pct=0.8,
                    spv_distribution_keur=200.0, holdco_share_keur=160.0
                ),
            ],
            gross_income_keur=460.0,
        )
        assert len(p.contributions) == 2


class TestHoldCoResult:
    """HoldCoResult validation."""

    def test_valid_result(self):
        r = HoldCoResult(
            name="Test HoldCo",
            periods=[
                HoldCoPeriodResult(
                    period=1,
                    gross_income_keur=1000.0,
                    distribution_to_sponsor_keur=700.0,
                )
            ],
            total_spv_distributions_keur=1000.0,
            total_gross_income_keur=1000.0,
            total_opex_keur=100.0,
            total_tax_keur=200.0,
            total_distribution_to_sponsor_keur=700.0,
            spv_codes=["OBOROVO", "TUHO"],
        )
        assert r.name == "Test HoldCo"
        assert len(r.periods) == 1
        assert r.spv_codes == ["OBOROVO", "TUHO"]
        assert r.holdco_irr is None
        assert r.spv_count == 2

    def test_name_required_empty_raises(self):
        with pytest.raises(ValueError, match="HoldCoResult.name is required"):
            HoldCoResult(name="")

    def test_name_required_whitespace_raises(self):
        with pytest.raises(ValueError, match="HoldCoResult.name is required"):
            HoldCoResult(name="   ")

    def test_negative_totals_raise(self):
        with pytest.raises(ValueError, match="total_spv_distributions_keur must be >= 0"):
            HoldCoResult(name="HC", total_spv_distributions_keur=-1.0)

    def test_holdco_irr_always_none(self):
        r = HoldCoResult(name="HC")
        assert r.holdco_irr is None

    def test_is_placeholder_true(self):
        r = HoldCoResult(name="HC")
        assert r.is_placeholder is True

    def test_spv_count(self):
        r = HoldCoResult(name="HC", spv_codes=["A", "B", "C"])
        assert r.spv_count == 3

    def test_empty_spv_codes(self):
        r = HoldCoResult(name="HC", spv_codes=[])
        assert r.spv_count == 0

    def test_multiple_periods(self):
        r = HoldCoResult(
            name="Multi Period HC",
            periods=[
                HoldCoPeriodResult(period=i, distribution_to_sponsor_keur=100.0 * i)
                for i in range(5)
            ],
            total_distribution_to_sponsor_keur=1000.0,
            spv_codes=["X"],
        )
        assert len(r.periods) == 5
        assert r.periods[0].period == 0
        assert r.periods[4].distribution_to_sponsor_keur == 400.0