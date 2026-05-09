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
    HoldCoSPVContribution,
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
    spv.adjusted_period_distributions_keur = ()  # empty = HoldCo uses waterfall distributions
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
        """Warning emitted when SPVs have different period counts (max-period alignment)."""
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

        # P1.2: Should use max (2 periods) — longer SPV not truncated
        assert len(result.periods) == 2
        warnings = list(result.warnings)
        assert any("Period count mismatch" in w for w in warnings)
        assert any("max-period" in w for w in warnings)
        # SHORT-SP contributes 0.0 in period 1 (zero-padding)
        assert result.periods[0].gross_income_keur == 300.0  # 100 + 200
        assert result.periods[1].gross_income_keur == 300.0  # 0 + 300 (SHORT-SP ended)

    def test_max_period_longer_spv_not_truncated(self):
        """Longer SPV contributions are preserved when periods differ."""
        spv1 = _make_mock_spv("A", "A", [100.0, 200.0])  # 2 periods
        spv2 = _make_mock_spv("B", "B", [50.0])           # 1 period
        portfolio = _make_portfolio_result([spv1, spv2])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="A", ownership_pct=1.0),
                SPVOwnership(spv_code="B", ownership_pct=1.0),
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        assert len(result.periods) == 2
        # Period 0: A=100 + B=50 = 150
        assert result.periods[0].gross_income_keur == 150.0
        # Period 1: A=200 + B=0 (zero-padding) = 200
        assert result.periods[1].gross_income_keur == 200.0

    def test_zero_padding_for_shorter_spv(self):
        """Shorter SPV contributes 0.0 after its final period."""
        spv = _make_mock_spv("SHORT", "Short", [1000.0])  # 1 period
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        # Add a second SPV to force max-period > 1
        spv2 = _make_mock_spv("LONG", "Long", [500.0, 600.0])
        portfolio2 = _make_portfolio_result([spv, spv2])
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SHORT", ownership_pct=1.0),
                SPVOwnership(spv_code="LONG", ownership_pct=1.0),
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio2)

        assert len(result.periods) == 2
        # SHORT contributes 0 in period 1 (after its last period)
        assert result.periods[1].gross_income_keur == 600.0  # only LONG
        # Verify SHORT SPV contribution in period 1 is 0.0
        short_contrib = next(c for c in result.periods[1].contributions if c.spv_code == "SHORT")
        assert short_contrib.spv_distribution_keur == 0.0


class TestSHLReadyFields:
    """P1.1: SHL-ready contribution fields with zero defaults."""

    def test_contribution_shl_fields_default_zero(self):
        """HoldCoSPVContribution SHL fields default to 0.0."""
        c = HoldCoSPVContribution(
            period=0, spv_code="X", ownership_pct=1.0,
            spv_distribution_keur=1000.0, holdco_share_keur=1000.0,
        )
        assert c.dividend_keur == 0.0
        assert c.shl_interest_keur == 0.0
        assert c.shl_principal_keur == 0.0

    def test_contribution_dividend_populated_from_distribution(self):
        """Current distributions populate dividend_keur (SHL = 0.0)."""
        c = HoldCoSPVContribution(
            period=0, spv_code="SOLAR", ownership_pct=1.0,
            spv_distribution_keur=1000.0, holdco_share_keur=1000.0,
            dividend_keur=1000.0, shl_interest_keur=0.0, shl_principal_keur=0.0,
        )
        assert c.dividend_keur == 1000.0
        assert c.shl_interest_keur == 0.0
        assert c.shl_principal_keur == 0.0

    def test_holdco_result_shl_totals_default_zero(self):
        """HoldCoResult SHL totals default to 0.0 (no SHL implemented)."""
        r = HoldCoResult(name="HC")
        assert r.total_dividend_keur == 0.0
        assert r.total_shl_interest_keur == 0.0
        assert r.total_shl_principal_keur == 0.0

    def test_dividend_keur_is_ownership_adjusted(self):
        """dividend_keur = holdco_share (ownership-adjusted), not raw spv_dist."""
        spv = _make_mock_spv("SOLAR-1", "Solar", [1000.0])
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC")
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=0.5)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        contrib = result.periods[0].contributions[0]
        assert contrib.spv_distribution_keur == 1000.0   # raw SPV output
        assert contrib.holdco_share_keur == 500.0        # ownership * spv_dist
        assert contrib.dividend_keur == 500.0           # dividend = holdco_share (ownership-adjusted)
        assert contrib.shl_interest_keur == 0.0
        assert contrib.shl_principal_keur == 0.0
        # total_dividend is sum of contribution dividends
        assert result.total_dividend_keur == 500.0
        assert result.total_shl_interest_keur == 0.0
        assert result.total_shl_principal_keur == 0.0

    def test_dividend_with_100_percent_ownership(self):
        """100% ownership: dividend == spv_dist == holdco_share."""
        spv = _make_mock_spv("SOLAR-1", "Solar", [1000.0])
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC")
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        contrib = result.periods[0].contributions[0]
        assert contrib.spv_distribution_keur == 1000.0
        assert contrib.holdco_share_keur == 1000.0
        assert contrib.dividend_keur == 1000.0
        assert result.total_dividend_keur == 1000.0

    def test_period_dividend_summed_from_contributions(self):
        """HoldCoPeriodResult.dividend_keur is sum of contribution dividends."""
        spv1 = _make_mock_spv("SOLAR-A", "Solar A", [800.0])
        spv2 = _make_mock_spv("WIND-B", "Wind B", [600.0])
        portfolio = _make_portfolio_result([spv1, spv2])
        entity = HoldCoEntity(name="HC")
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-A", ownership_pct=0.5),  # 50% → dividend=400
                SPVOwnership(spv_code="WIND-B", ownership_pct=1.0),   # 100% → dividend=600
            ],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)
        # Period dividend = 400 + 600 = 1000
        assert result.periods[0].dividend_keur == 1000.0
        assert result.periods[0].shl_interest_keur == 0.0
        assert result.periods[0].shl_principal_keur == 0.0

    def test_contribution_shl_fields_explicit(self):
        """HoldCoSPVContribution accepts explicit SHL field values."""
        c = HoldCoSPVContribution(
            period=1, spv_code="X", ownership_pct=0.8,
            spv_distribution_keur=1000.0, holdco_share_keur=800.0,
            dividend_keur=800.0, shl_interest_keur=50.0, shl_principal_keur=200.0,
        )
        assert c.dividend_keur == 800.0
        assert c.shl_interest_keur == 50.0
        assert c.shl_principal_keur == 200.0


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

class TestDSRFAdjustedDistributions:
    def test_holdco_uses_adjusted_period_distributions(self):
        """When SPV has adjusted_period_distributions_keur, HoldCo uses those."""
        # Create mock SPV with both waterfall and DSRF-adjusted data
        wp1 = MagicMock(); wp1.distribution_keur = 1000.0
        wp2 = MagicMock(); wp2.distribution_keur = 1200.0
        wf = MagicMock(); wf.periods = [wp1, wp2]
        spv = MagicMock(spec=SPVOutput)
        spv.project_code = "SOLAR"
        spv.waterfall_result = wf
        spv.total_distribution_keur = 2200.0
        spv.adjusted_period_distributions_keur = (800.0, 900.0)  # DSRF reduced these
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(name="HC", ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)], entity=entity)

        result = build_holdco_result(inputs, portfolio)

        # gross = 800 + 900 = 1700 (DSRF-adjusted), NOT 1000 + 1200 = 2200
        assert result.periods[0].gross_income_keur == 800.0
        assert result.periods[1].gross_income_keur == 900.0

    def test_holdco_falls_back_to_waterfall_when_no_adjusted(self):
        """Without adjusted_period_distributions_keur, HoldCo uses waterfall distributions."""
        wp1 = MagicMock(); wp1.distribution_keur = 1000.0
        wf = MagicMock(); wf.periods = [wp1]
        spv = MagicMock(spec=SPVOutput)
        spv.project_code = "SOLAR"
        spv.waterfall_result = wf
        spv.total_distribution_keur = 1000.0
        spv.adjusted_period_distributions_keur = ()  # empty — no DSRF adjustment
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(name="HC", ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)], entity=entity)

        result = build_holdco_result(inputs, portfolio)

        assert result.periods[0].gross_income_keur == 1000.0  # falls back to waterfall


class TestMixedHorizonMaxPeriod:
    """P1.2 / final-fix: max-period alignment with SPVs of different horizon lengths."""

    def test_60_period_spv_with_50_period_spv(self):
        """SPV1=60 periods, SPV2=50 periods → 60 periods total, zero-padding after 50."""
        # SPV1: 60 periods of 100.0 each
        spv1_dists = [100.0] * 60
        # SPV2: 50 periods of 200.0 each
        spv2_dists = [200.0] * 50
        spv1 = _make_mock_spv("LONG-SP", "Long SPV", spv1_dists)
        spv2 = _make_mock_spv("SHORT-SP", "Short SPV", spv2_dists)
        portfolio = _make_portfolio_result([spv1, spv2])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="LONG-SP", ownership_pct=1.0),
                SPVOwnership(spv_code="SHORT-SP", ownership_pct=1.0),
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        assert len(result.periods) == 60, f"Expected 60, got {len(result.periods)}"
        # Periods 0–49: both SPVs contribute
        for i in range(50):
            assert result.periods[i].gross_income_keur == 300.0, f"Period {i}: {result.periods[i].gross_income_keur}"
        # Periods 50–59: only LONG-SP (SHORT-SP zero-padded)
        for i in range(50, 60):
            assert result.periods[i].gross_income_keur == 100.0, f"Period {i}: {result.periods[i].gross_income_keur}"
        # Warning about period mismatch should mention max-period
        warnings = list(result.warnings)
        assert any("max-period" in w or "max" in w.lower() for w in warnings), f"No max-period warning: {warnings}"

    def test_zero_padding_after_short_spv_ends(self):
        """Shorter SPV contributes 0.0 after its final period."""
        spv1 = _make_mock_spv("SHORT", "Short", [500.0, 600.0])   # 2 periods
        spv2 = _make_mock_spv("LONG", "Long", [100.0, 200.0, 300.0, 400.0])  # 4 periods
        portfolio = _make_portfolio_result([spv1, spv2])

        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SHORT", ownership_pct=1.0),
                SPVOwnership(spv_code="LONG", ownership_pct=1.0),
            ],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        assert len(result.periods) == 4
        # Period 0: 500 + 100 = 600
        assert result.periods[0].gross_income_keur == 600.0
        # Period 1: 600 + 200 = 800
        assert result.periods[1].gross_income_keur == 800.0
        # Period 2: 0 + 300 = 300 (SHORT ended)
        assert result.periods[2].gross_income_keur == 300.0
        # Period 3: 0 + 400 = 400 (SHORT still 0)
        assert result.periods[3].gross_income_keur == 400.0


class TestSHLIncomeComponentBreakdown:
    """Final-fix: income component breakdown for SHL preparation."""

    def test_dividend_share_contributes_to_period_gross(self):
        """dividend_share is the primary contributor to period_gross while SHL=0."""
        spv = _make_mock_spv("SOLAR", "Solar", [1000.0])
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=0.5)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        contrib = result.periods[0].contributions[0]
        # dividend_share = 1000 * 0.5 = 500
        assert contrib.dividend_keur == 500.0
        # shl_interest = 0.0
        assert contrib.shl_interest_keur == 0.0
        # shl_principal = 0.0
        assert contrib.shl_principal_keur == 0.0
        # holdco_share = dividend + SHL interest = 500 + 0 = 500
        assert contrib.holdco_share_keur == 500.0
        # period_gross = 500 (dividend only)
        assert result.periods[0].gross_income_keur == 500.0

    def test_shl_interest_share_is_zero(self):
        """SHL interest share is 0.0 until SHL is implemented."""
        spv = _make_mock_spv("SOLAR", "Solar", [2000.0])
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        for c in result.periods[0].contributions:
            assert c.shl_interest_keur == 0.0, "SHL interest must be 0.0 until SHL implemented"

    def test_shl_principal_share_is_zero(self):
        """SHL principal share is 0.0 (balance-sheet only, not in period_gross)."""
        spv = _make_mock_spv("SOLAR", "Solar", [2000.0])
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        for c in result.periods[0].contributions:
            assert c.shl_principal_keur == 0.0, "SHL principal must be 0.0 (balance-sheet only)"

    def test_holdco_share_equals_dividend_plus_shl_interest(self):
        """holdco_share_keur = dividend_keur + shl_interest_keur (SHL principal excluded)."""
        spv = _make_mock_spv("SOLAR", "Solar", [1000.0])
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC")
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        for c in result.periods[0].contributions:
            assert c.holdco_share_keur == c.dividend_keur + c.shl_interest_keur

    def test_total_gross_income_equals_total_dividend_when_shl_zero(self):
        """total_gross_income == total_dividend_keur while SHL interest is 0.0."""
        spv = _make_mock_spv("SOLAR", "Solar", [1000.0, 2000.0])
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC")
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        assert result.total_gross_income_keur == result.total_dividend_keur
        assert result.total_gross_income_keur == 3000.0
        assert result.total_shl_interest_keur == 0.0
        assert result.total_shl_principal_keur == 0.0


class TestSHLMixedCashflow:
    """P4B: SHL upstream integration — mixed cash flow scenarios."""

    def _make_spv_with_shl(self, code, dist, shl_interest=0.0, shl_principal=0.0):
        """Create mock SPV with SHL fields in waterfall periods."""
        periods = []
        for i, d in enumerate(dist):
            wp = MagicMock()
            wp.distribution_keur = d
            wp.period_in_year = 1 if i % 2 == 0 else 2
            wp.shl_interest_keur = shl_interest[i] if isinstance(shl_interest, list) else shl_interest
            wp.shl_principal_keur = shl_principal[i] if isinstance(shl_principal, list) else shl_principal
            periods.append(wp)
        wf = MagicMock()
        wf.periods = periods
        spv = MagicMock(spec=SPVOutput)
        spv.project_code = code
        spv.waterfall_result = wf
        spv.adjusted_period_distributions_keur = ()
        return spv

    def test_dividend_only_income(self):
        """Scenario 1: Dividend only — gross_income = dividend."""
        spv = self._make_spv_with_shl("SOLAR", [1000.0], shl_interest=0.0, shl_principal=0.0)
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        c = result.periods[0].contributions[0]
        assert c.dividend_keur == 1000.0
        assert c.shl_interest_keur == 0.0
        assert c.shl_principal_keur == 0.0
        assert c.holdco_share_keur == 1000.0  # dividend only
        assert result.periods[0].gross_income_keur == 1000.0
        assert result.periods[0].dividend_keur == 1000.0
        assert result.periods[0].shl_interest_keur == 0.0
        assert result.periods[0].shl_principal_keur == 0.0

    def test_shl_interest_only(self):
        """Scenario 2: SHL interest only — gross_income = interest, dividend=0."""
        spv = self._make_spv_with_shl("SOLAR", [0.0], shl_interest=[80.0], shl_principal=0.0)
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        c = result.periods[0].contributions[0]
        assert c.dividend_keur == 0.0
        assert c.shl_interest_keur == 80.0
        assert c.shl_principal_keur == 0.0
        assert c.holdco_share_keur == 80.0  # interest only
        assert result.periods[0].gross_income_keur == 80.0
        assert result.periods[0].dividend_keur == 0.0
        assert result.periods[0].shl_interest_keur == 80.0
        assert result.periods[0].shl_principal_keur == 0.0

    def test_shl_principal_only_no_gross_income(self):
        """Scenario 3: SHL principal only — gross_income = 0, principal tracked."""
        spv = self._make_spv_with_shl("SOLAR", [0.0], shl_interest=0.0, shl_principal=[500.0])
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        c = result.periods[0].contributions[0]
        assert c.dividend_keur == 0.0
        assert c.shl_interest_keur == 0.0
        assert c.shl_principal_keur == 500.0
        assert c.holdco_share_keur == 0.0  # principal NOT in income
        assert result.periods[0].gross_income_keur == 0.0
        assert result.periods[0].shl_principal_keur == 500.0  # tracked separately

    def test_mixed_dividend_shl_interest_shl_principal(self):
        """Scenario 4: Mixed flow — gross_income excludes principal, totals reconcile."""
        spv = self._make_spv_with_shl(
            "SOLAR",
            [1000.0],  # dividend
            shl_interest=[80.0],  # SHL interest
            shl_principal=[500.0]  # SHL principal (not in income)
        )
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        c = result.periods[0].contributions[0]
        assert c.dividend_keur == 1000.0
        assert c.shl_interest_keur == 80.0
        assert c.shl_principal_keur == 500.0
        assert c.holdco_share_keur == 1080.0  # dividend + interest, NO principal
        # gross_income = dividend + SHL interest (principal excluded)
        assert result.periods[0].gross_income_keur == 1080.0
        # Principal tracked but does not affect taxable income
        assert result.periods[0].dividend_keur == 1000.0
        assert result.periods[0].shl_interest_keur == 80.0
        assert result.periods[0].shl_principal_keur == 500.0

    def test_ownership_scaling_shl(self):
        """Scenario 5: 50% ownership scales all components correctly."""
        spv = self._make_spv_with_shl(
            "SOLAR",
            [1000.0],
            shl_interest=[80.0],
            shl_principal=[500.0]
        )
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=0.5)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        c = result.periods[0].contributions[0]
        assert c.dividend_keur == 500.0      # 1000 * 0.5
        assert c.shl_interest_keur == 40.0   # 80 * 0.5
        assert c.shl_principal_keur == 250.0  # 500 * 0.5
        assert c.holdco_share_keur == 540.0   # (1000+80) * 0.5
        assert result.periods[0].gross_income_keur == 540.0

    def test_multi_period_reconciliation(self):
        """Scenario 6: Period-level totals reconcile with aggregate totals."""
        spv = self._make_spv_with_shl(
            "SOLAR",
            [1000.0, 2000.0],
            shl_interest=[50.0, 100.0],
            shl_principal=[200.0, 400.0]
        )
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        assert len(result.periods) == 2
        # Period 0: dividend=1000, interest=50, principal=200
        assert result.periods[0].dividend_keur == 1000.0
        assert result.periods[0].shl_interest_keur == 50.0
        assert result.periods[0].shl_principal_keur == 200.0
        assert result.periods[0].gross_income_keur == 1050.0  # dividend + interest

        # Period 1: dividend=2000, interest=100, principal=400
        assert result.periods[1].dividend_keur == 2000.0
        assert result.periods[1].shl_interest_keur == 100.0
        assert result.periods[1].shl_principal_keur == 400.0
        assert result.periods[1].gross_income_keur == 2100.0

        # Aggregate totals
        assert result.total_dividend_keur == 3000.0
        assert result.total_shl_interest_keur == 150.0
        assert result.total_shl_principal_keur == 600.0
        assert result.total_gross_income_keur == 3150.0  # dividend + interest total

    def test_shl_principal_excluded_from_gross_income(self):
        """SHL principal must never appear in gross_income_keur."""
        spv = self._make_spv_with_shl(
            "SOLAR",
            [0.0],
            shl_interest=[0.0],
            shl_principal=[1000.0]  # large principal
        )
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        # Principal is tracked but gross income is 0
        assert result.periods[0].shl_principal_keur == 1000.0
        assert result.periods[0].gross_income_keur == 0.0
        assert result.periods[0].shl_interest_keur == 0.0
        # Total principal tracked
        assert result.total_shl_principal_keur == 1000.0

    def test_no_shl_fields_defaults_zero(self):
        """When waterfall periods have no SHL fields, all defaults to 0."""
        # Create SPV without shl_interest_keur/shl_principal_keur attributes
        wp = MagicMock()
        wp.distribution_keur = 1000.0
        wp.period_in_year = 1
        # No shl_interest_keur or shl_principal_keur attributes
        del wp.shl_interest_keur
        del wp.shl_principal_keur
        wf = MagicMock()
        wf.periods = [wp]
        spv = MagicMock(spec=SPVOutput)
        spv.project_code = "SOLAR"
        spv.waterfall_result = wf
        spv.adjusted_period_distributions_keur = ()
        portfolio = _make_portfolio_result([spv])
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=1.0)],
            entity=entity,
        )
        result = build_holdco_result(inputs, portfolio)

        # Should fall back to 0 via getattr(..., 0.0)
        c = result.periods[0].contributions[0]
        assert c.shl_interest_keur == 0.0
        assert c.shl_principal_keur == 0.0
        assert c.holdco_share_keur == 1000.0  # dividend only
        assert result.total_shl_interest_keur == 0.0
        assert result.total_shl_principal_keur == 0.0
