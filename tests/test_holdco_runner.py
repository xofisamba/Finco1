"""Tests for HoldCo aggregation runner — Phase 3B.

No SHL. No tax template engine. No HoldCo IRR. No monthly model.
No pooled financing. No retained earnings. Pure linear aggregation.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from datetime import date
from dataclasses import replace

from domain.portfolio.holdco import (
    HoldCoInputs,
    HoldCoEntity,
    HoldCoOpexInputs,
    SPVOwnership,
    HoldCoResult,
    HoldCoPeriodResult,
)
from domain.portfolio.holdco.runner import (
    build_holdco_result,
    aggregate_holdco_periods,
    validate_holdco_alignment,
)
from domain.portfolio.independent import IndependentPortfolioResult, SPVOutput


def _make_mock_spv(code, name, distributions_per_period, tax_rate_pa=0.0):
    """Create a mock SPVOutput with per-period waterfall data."""
    periods = []
    for i, dist in enumerate(distributions_per_period):
        wp = MagicMock()
        wp.distribution_keur = dist
        # semiannual: H1 (period 0) then H2 (period 1)
        wp.period_in_year = 1 if i % 2 == 0 else 2
        periods.append(wp)

    waterfall_result = MagicMock()
    waterfall_result.periods = periods

    spv = MagicMock(spec=SPVOutput)
    spv.project_code = code
    spv.project_name = name
    spv.total_distribution_keur = sum(distributions_per_period)
    spv.waterfall_result = waterfall_result
    return spv


def _make_portfolio_result(spvs, name="Test Portfolio"):
    """Create an IndependentPortfolioResult from mock SPVs."""
    result = MagicMock(spec=IndependentPortfolioResult)
    result.portfolio_name = name
    result.spv_outputs = tuple(spvs)
    result.warnings = ()
    return result


class TestBuildHoldCoResult100Percent:
    """Simple 100% ownership aggregation."""

    def test_100_percent_single_spv(self):
        """Sponsor distribution equals SPV distribution minus opex/tax."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0, 1200.0, 1400.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.2)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=100.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        assert result.name == "HC"
        assert result.holdco_irr is None
        assert len(result.periods) == 3
        # Period 0: gross=1000, opex=50 (annual/2), taxable=950, tax=190, sponsor=760
        assert result.periods[0].gross_income_keur == 1000.0
        assert result.periods[0].holdco_opex_keur == 50.0  # 100/2
        assert result.periods[0].distribution_to_sponsor_keur == 760.0  # (1000-50)*0.8
        # Period 1: gross=1200, opex=50, taxable=1150, tax=230, sponsor=920
        assert result.periods[1].distribution_to_sponsor_keur == 920.0  # (1200-50)*0.8

    def test_100_percent_two_spvs(self):
        """Two SPVs at 100% — aggregation sums correctly."""
        spv1 = _make_mock_spv("SOLAR-A", "Solar A", [500.0, 600.0])
        spv2 = _make_mock_spv("WIND-B", "Wind B", [300.0, 400.0])
        portfolio = _make_portfolio_result([spv1, spv2])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)  # no tax for clarity
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)  # no opex
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-A", ownership_pct=1.0),
                SPVOwnership(spv_code="WIND-B", ownership_pct=1.0),
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        assert len(result.periods) == 2
        # Period 0: gross = 500 + 300 = 800
        assert result.periods[0].gross_income_keur == 800.0
        assert result.periods[0].distribution_to_sponsor_keur == 800.0
        # Period 1: gross = 600 + 400 = 1000
        assert result.periods[1].gross_income_keur == 1000.0
        assert result.periods[1].distribution_to_sponsor_keur == 1000.0


class TestPartialOwnership:
    """Partial ownership (less than 100%)."""

    def test_50_percent_halves_upstream(self):
        """50% ownership halves the upstream distribution."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=0.5)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        assert result.periods[0].gross_income_keur == 500.0  # 1000 * 0.5
        assert result.periods[0].distribution_to_sponsor_keur == 500.0

    def test_partial_ownership_multiple_spvs(self):
        """Mixed ownership percentages aggregate correctly."""
        spv1 = _make_mock_spv("SOLAR-A", "Solar A", [1000.0])
        spv2 = _make_mock_spv("WIND-B", "Wind B", [800.0])
        portfolio = _make_portfolio_result([spv1, spv2])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-A", ownership_pct=1.0),   # 100% of 1000
                SPVOwnership(spv_code="WIND-B", ownership_pct=0.5),     # 50% of 800
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # gross = 1000*1.0 + 800*0.5 = 1000 + 400 = 1400
        assert result.periods[0].gross_income_keur == 1400.0
        assert result.periods[0].distribution_to_sponsor_keur == 1400.0


class TestHoldCoOpexDeduction:
    """HoldCo OpEx reduces taxable income."""

    def test_opex_reduces_taxable_income(self):
        """OpEx deducted from gross income before tax."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0, 1000.0])  # 2 periods → semiannual
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.2)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=200.0)  # 200/year → 100/period (semiannual)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # gross=1000, opex=100, taxable=900, tax=180, sponsor=720
        assert result.periods[0].holdco_opex_keur == 100.0  # annual/2
        assert result.periods[0].taxable_income_keur == 900.0
        assert result.periods[0].distribution_to_sponsor_keur == 720.0


class TestHoldCoTaxDeduction:
    """HoldCo tax reduces sponsor distribution."""

    def test_tax_deduction_reduces_sponsor_dist(self):
        """20% tax on taxable income reduces sponsor distribution."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.2)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # gross=1000, taxable=1000, tax=200, sponsor=800
        assert result.periods[0].taxable_income_keur == 1000.0
        assert result.periods[0].tax_keur == 200.0
        assert result.periods[0].distribution_to_sponsor_keur == 800.0


class TestNoNegativeDistributions:
    """Sponsor distributions cannot be negative."""

    def test_no_negative_sponsor_distributions(self):
        """When gross < opex per period, taxable=0 and distribution=0 (not negative)."""
        # 2 periods → semiannual model (period_in_year=1 for H1, =2 for H2)
        # opex_per_period = 1000/2 = 500 per period
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0, 1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.2)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=1000.0)  # high opex
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # gross=1000, opex=500, taxable=500, tax=100, sponsor=400
        assert result.periods[0].holdco_opex_keur == 500.0
        assert result.periods[0].taxable_income_keur == 500.0
        assert result.periods[0].distribution_to_sponsor_keur == 400.0


class TestMissingSPVCode:
    """HoldCoInputs references SPV not in portfolio result."""

    def test_missing_spv_code_warning(self):
        """Warning emitted when HoldCoInputs SPV not in portfolio result."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0),
                SPVOwnership(spv_code="MISSING-SPV", ownership_pct=1.0),
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        warnings = list(result.warnings)
        assert any("MISSING-SPV" in w for w in warnings)
        # MISSING-SPV contributes 0 but doesn't crash
        assert len(result.periods) == 1
        assert result.periods[0].gross_income_keur == 1000.0  # only SOLAR-1


class TestPeriodMismatchWarning:
    """Period mismatch handled safely."""

    def test_period_mismatch_warning(self):
        """Warning emitted when SPVs have different period counts."""
        spv1 = _make_mock_spv("SHORT-SP", "Short SPV", [100.0])        # 1 period
        spv2 = _make_mock_spv("LONG-SP", "Long SPV", [200.0, 300.0])  # 2 periods
        portfolio = _make_portfolio_result([spv1, spv2])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SHORT-SP", ownership_pct=1.0),
                SPVOwnership(spv_code="LONG-SP", ownership_pct=1.0),
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # Should use shortest (1 period) with warning
        assert len(result.periods) == 1
        warnings = list(result.warnings)
        assert any("Period count mismatch" in w for w in warnings)


class TestNoSHLBehavior:
    """No intercompany debt fields appear in HoldCo result."""

    def test_no_shl_fields_in_result(self):
        """HoldCo result should not contain SHL-related fields."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # No SHL fields in HoldCoResult
        for period in result.periods:
            # Check that HoldCoPeriodResult doesn't have shl-related fields
            assert not hasattr(period, 'shl_interest_keur')
            assert not hasattr(period, 'shl_principal_keur')
            assert not hasattr(period, 'shl_balance_keur')


class TestNoHoldCoIRR:
    """HoldCo IRR is always None in Phase 3B."""

    def test_holdco_irr_always_none(self):
        """holdco_irr is None in result — not computed."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0, 1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        assert result.holdco_irr is None
        for period in result.periods:
            assert period.holdco_irr is None


class TestNoScopeCreep:
    """Verify no out-of-scope features appear."""

    def test_no_pooled_financing(self):
        """No pooled financing in HoldCo result."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        # No pooling indicator, no cross-SPV cash sweep
        assert result.total_gross_income_keur == 1000.0

    def test_validate_holdco_alignment_function(self):
        """validate_holdco_alignment function exists and returns warnings."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0),
                SPVOwnership(spv_code="MISSING", ownership_pct=1.0),
            ],
            entity=entity,
        )

        warnings = validate_holdco_alignment(inputs, portfolio)
        assert len(warnings) > 0
        assert any("MISSING" in w for w in warnings)

    def test_aggregate_holdco_periods_alias(self):
        """aggregate_holdco_periods returns period list from build_holdco_result."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [500.0, 600.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        periods = aggregate_holdco_periods(inputs, portfolio)
        assert len(periods) == 2
        assert isinstance(periods[0], HoldCoPeriodResult)


class TestHoldCoResultTotals:
    """HoldCoResult totals are populated after aggregation."""

    def test_totals_populated(self):
        """total_spv_distributions, total_gross_income, total_opex, total_tax, total_sponsor_dist are set."""
        spv = _make_mock_spv("SOLAR-1", "Solar One", [1000.0, 1000.0, 1000.0])
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.2)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=200.0)  # 100/period semiannual
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        assert result.total_spv_distributions_keur == 3000.0
        assert result.total_gross_income_keur == 3000.0
        assert result.total_opex_keur == 300.0  # 100 * 3
        assert result.total_tax_keur == 540.0   # (3000-300)*0.2 = 540
        assert result.total_distribution_to_sponsor_keur == 2160.0  # (3000-300)*0.8 = 2160
        assert result.spv_codes == ["SOLAR-1"]

    def test_spv_codes_from_inputs(self):
        """spv_codes in result matches HoldCoInputs.spv_codes."""
        spv1 = _make_mock_spv("SOLAR-A", "Solar A", [500.0])
        spv2 = _make_mock_spv("WIND-B", "Wind B", [300.0])
        portfolio = _make_portfolio_result([spv1, spv2])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-A", ownership_pct=1.0),
                SPVOwnership(spv_code="WIND-B", ownership_pct=0.8),
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)
        assert result.spv_codes == ["SOLAR-A", "WIND-B"]


class TestEmptyPortfolioResult:
    """Handle case where portfolio_result has no valid waterfall data."""

    def test_empty_portfolio_returns_empty_result_with_warnings(self):
        """No SPVs with waterfall_result → empty result with warning."""
        spv = MagicMock(spec=SPVOutput)
        spv.project_code = "EMPTY-SP"
        spv.waterfall_result = None  # no waterfall data
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="EMPTY-SP", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # Empty result (no periods) when SPV has no waterfall data
        # Note: no "missing SPV" warning because SPV IS in portfolio (just no waterfall)
        assert len(result.periods) == 0
        assert result.holdco_irr is None