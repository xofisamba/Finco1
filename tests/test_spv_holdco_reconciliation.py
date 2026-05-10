"""Phase 5 post-review: SPV → HoldCo dividend reconciliation test.

M.1: Verifies that ownership-adjusted SPV equity distributions reconcile to
HoldCo dividend inflows across multiple SPVs and periods.

Mapping used:
- SPV equity distribution outflow: CashMovementType.EQUITY_DISTRIBUTION (negative)
- HoldCo dividend inflow: HoldCoResult.periods[].dividend_keur (positive)

The sum over all SPVs of (equity_distribution × ownership_pct) per period
should reconcile to the HoldCo period dividend_keur.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from domain.portfolio.holdco import (
    HoldCoInputs,
    HoldCoEntity,
    HoldCoOpexInputs,
    SPVOwnership,
    build_holdco_result,
)
from domain.portfolio.independent import IndependentPortfolioResult, SPVOutput
from domain.portfolio.cash_ledger.inputs import CashMovementType


def _make_spv(code, distributions_per_period, adjusted_distributions=None):
    """Build a mock SPVOutput with per-period waterfall data.

    Parameters
    ----------
    distributions_per_period : list[float]
        Per-period distribution_keur from waterfall periods.
    adjusted_distributions : list[float] | None
        DSRF-adjusted distributions. If None, uses distributions_per_period.
    """
    periods = []
    for i, dist in enumerate(distributions_per_period):
        wp = MagicMock()
        wp.distribution_keur = dist
        wp.shl_interest_keur = 0.0
        wp.shl_principal_keur = 0.0
        wp.period_in_year = 1 if i % 2 == 0 else 2
        periods.append(wp)

    waterfall = MagicMock()
    waterfall.periods = periods

    spv = MagicMock(spec=SPVOutput)
    spv.project_code = code
    spv.project_name = code
    spv.total_distribution_keur = sum(distributions_per_period)
    spv.waterfall_result = waterfall
    spv.adjusted_period_distributions_keur = tuple(adjusted_distributions or [])
    return spv


def _make_portfolio(spvs):
    result = MagicMock(spec=IndependentPortfolioResult)
    result.portfolio_name = "TestPortfolio"
    result.spv_outputs = tuple(spvs)
    result.warnings = ()
    return result


class TestSPVHoldCoDividendReconciliation:
    """SPV equity distributions × ownership_pct reconcile to HoldCo dividend."""

    def test_single_spv_100pct_reconciliation(self):
        """100% ownership: SPV distribution = HoldCo dividend."""
        spv = _make_spv("SOLAR-1", [1000.0, 1200.0, 800.0])
        portfolio = _make_portfolio([spv])

        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=HoldCoEntity(name="HC", tax_rate_pa=0.0),
        )
        result = build_holdco_result(inputs, portfolio)

        expected = [1000.0, 1200.0, 800.0]
        for i, (got, exp) in enumerate(zip(
            [p.dividend_keur for p in result.periods],
            expected
        )):
            assert abs(got - exp) < 1e-6, (
                f"period {i}: HoldCo dividend {got} != expected {exp}"
            )

    def test_two_spv_partial_ownership_reconciliation(self):
        """Two SPVs, different ownership: each SPV distribution × pct = contribution."""
        spv1 = _make_spv("SOLAR-1", [1000.0, 1200.0])
        spv2 = _make_spv("WIND-1",  [800.0,  900.0])
        portfolio = _make_portfolio([spv1, spv2])

        # SOLAR-1: 80%, WIND-1: 60%
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-1", ownership_pct=0.8),
                SPVOwnership(spv_code="WIND-1",  ownership_pct=0.6),
            ],
            entity=HoldCoEntity(name="HC", tax_rate_pa=0.0),
        )
        result = build_holdco_result(inputs, portfolio)

        # Period 0: 1000*0.8 + 800*0.6 = 800 + 480 = 1280
        # Period 1: 1200*0.8 + 900*0.6 = 960 + 540 = 1500
        expected = [1280.0, 1500.0]
        for i, (got, exp) in enumerate(zip(
            [p.dividend_keur for p in result.periods],
            expected
        )):
            assert abs(got - exp) < 1e-6, (
                f"period {i}: HoldCo dividend {got} != expected {exp}"
            )

    def test_three_spv_mixed_ownership_reconciliation(self):
        """Three SPVs with 100%, 75%, 50% ownership."""
        spv1 = _make_spv("SOLAR-A", [1000.0, 1000.0, 1000.0])
        spv2 = _make_spv("WIND-B",  [800.0,  800.0,  800.0])
        spv3 = _make_spv("SOLAR-C", [500.0,  500.0,  500.0])
        portfolio = _make_portfolio([spv1, spv2, spv3])

        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-A", ownership_pct=1.00),
                SPVOwnership(spv_code="WIND-B",  ownership_pct=0.75),
                SPVOwnership(spv_code="SOLAR-C", ownership_pct=0.50),
            ],
            entity=HoldCoEntity(name="HC", tax_rate_pa=0.0),
        )
        result = build_holdco_result(inputs, portfolio)

        # All SPVs distribute 1000+800+500=2300 in each period
        # P0: 2300 * [1.0, 0.75, 0.50] weighted: (1000*1.0 + 800*0.75 + 500*0.50)
        #   = 1000 + 600 + 250 = 1850
        # P1: same = 1850
        # P2: same = 1850
        expected = [1850.0, 1850.0, 1850.0]
        actual = [p.dividend_keur for p in result.periods]
        for i, (got, exp) in enumerate(zip(actual, expected)):
            assert abs(got - exp) < 1e-6, (
                f"period {i}: HoldCo dividend {got} != expected {exp}"
            )

    def test_dsrf_adjusted_distribution_reconciles(self):
        """DSRF-adjusted SPV distributions used for HoldCo dividend (not waterfall)."""
        # SPV waterfall: [1000, 1200], but DSRF-adjusted: [800, 1000]
        spv = _make_spv(
            "SOLAR-1",
            distributions_per_period=[1000.0, 1200.0],
            adjusted_distributions=[800.0, 1000.0],
        )
        portfolio = _make_portfolio([spv])

        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=HoldCoEntity(name="HC", tax_rate_pa=0.0),
        )
        result = build_holdco_result(inputs, portfolio)

        # Dividend uses DSRF-adjusted: [800, 1000]
        expected = [800.0, 1000.0]
        for i, (got, exp) in enumerate(zip(
            [p.dividend_keur for p in result.periods],
            expected
        )):
            assert abs(got - exp) < 1e-6, (
                f"period {i}: HoldCo dividend {got} != DSRF-adjusted {exp}"
            )

    def test_partial_ownership_with_dsrf_reconciles(self):
        """Partial ownership + DSRF-adjusted distributions combined."""
        spv1 = _make_spv(
            "SOLAR-1",
            distributions_per_period=[1000.0, 1200.0],
            adjusted_distributions=[800.0, 1000.0],
        )
        spv2 = _make_spv(
            "WIND-1",
            distributions_per_period=[600.0, 700.0],
            adjusted_distributions=[500.0, 600.0],
        )
        portfolio = _make_portfolio([spv1, spv2])

        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-1", ownership_pct=0.75),
                SPVOwnership(spv_code="WIND-1",  ownership_pct=0.60),
            ],
            entity=HoldCoEntity(name="HC", tax_rate_pa=0.0),
        )
        result = build_holdco_result(inputs, portfolio)

        # Period 0: 800*0.75 + 500*0.60 = 600 + 300 = 900
        # Period 1: 1000*0.75 + 600*0.60 = 750 + 360 = 1110
        expected = [900.0, 1110.0]
        for i, (got, exp) in enumerate(zip(
            [p.dividend_keur for p in result.periods],
            expected
        )):
            assert abs(got - exp) < 1e-6, (
                f"period {i}: HoldCo dividend {got} != expected {exp}"
            )

    def test_no_spv_data_gives_zero_dividend(self):
        """Portfolio with no SPVs → HoldCo dividend = 0."""
        portfolio = _make_portfolio([])

        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="GHOST", ownership_pct=0.5)],
            entity=HoldCoEntity(name="HC", tax_rate_pa=0.0),
        )
        result = build_holdco_result(inputs, portfolio)

        assert all(abs(p.dividend_keur) < 1e-6 for p in result.periods)

    def test_holdco_dividend_total_reconciles_from_contributions(self):
        """Total HoldCo dividend equals sum of all SPV contribution shares."""
        spv1 = _make_spv("SOLAR-A", [1000.0, 800.0])
        spv2 = _make_spv("WIND-B",  [600.0, 500.0])
        portfolio = _make_portfolio([spv1, spv2])

        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="SOLAR-A", ownership_pct=0.80),
                SPVOwnership(spv_code="WIND-B",  ownership_pct=0.70),
            ],
            entity=HoldCoEntity(name="HC", tax_rate_pa=0.0),
        )
        result = build_holdco_result(inputs, portfolio)

        # Verify total dividend from result matches sum of contributions
        total_dividend = sum(p.dividend_keur for p in result.periods)
        # Period 0: 1000*0.8 + 600*0.7 = 800 + 420 = 1220
        # Period 1: 800*0.8 + 500*0.7 = 640 + 350 = 990
        # Total = 1220 + 990 = 2210
        assert abs(total_dividend - 2210.0) < 1e-6
