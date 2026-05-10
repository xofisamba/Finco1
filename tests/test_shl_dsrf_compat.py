"""Phase 4C DSRF + SHL HoldCo integration tests.

Verifies that DSRF-adjusted distributions and SHL enrichment coexist
without double-counting or interference.

No sculpting. No capitalization. No tax logic. No HoldCo IRR.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from domain.portfolio.shl.inputs import SHLFacility
from domain.portfolio.shl.runner import run_shl_facility, run_shl_portfolio
from domain.portfolio.shl import SHLPortfolioInputs
from domain.portfolio.shl.integration import (
    group_shl_facilities_by_borrower,
    enrich_portfolio_result_with_shl,
)
from domain.portfolio.holdco import (
    HoldCoInputs,
    HoldCoEntity,
    HoldCoOpexInputs,
    SPVOwnership,
)
from domain.portfolio.holdco.runner import build_holdco_result
from domain.portfolio.independent import IndependentPortfolioResult, SPVOutput
from domain.portfolio.independent.inputs import DSRFConfig


class _WFPeriodStub:
    def __init__(self, period_index, distribution_keur):
        self.period_index = period_index
        self.distribution_keur = distribution_keur


def _make_portfolio_result(spvs):
    result = MagicMock(spec=IndependentPortfolioResult)
    result.spv_outputs = tuple(spvs)
    result.warnings = ()
    return result


def _make_spv_with_dsrf(code, wf_distributions, dsrf_adjustments, shl_lookup=None):
    """Create SPV with DSRF-adjusted period distributions and optional SHL enrichment.

    wf_distributions: list of (period_index, raw_wf_distribution_keur)
    dsrf_adjustments: list of adjusted distribution per period (same length as wf_distributions)
    shl_lookup: optional dict[period_index, (interest, principal)]
    """
    periods = [_WFPeriodStub(idx, raw) for idx, raw in wf_distributions]

    # Apply DSRF adjustments
    adjusted = [
        adj for _, adj in dsrf_adjustments
    ]

    if shl_lookup:
        for p in periods:
            if p.period_index in shl_lookup:
                interest, principal = shl_lookup[p.period_index]
            else:
                interest, principal = 0.0, 0.0
            p.shl_interest_keur = float(interest)
            p.shl_principal_keur = float(principal)

    wf = MagicMock()
    wf.periods = periods

    spv = MagicMock(spec=SPVOutput)
    spv.project_code = code
    spv.project_name = code
    spv.waterfall_result = wf
    spv.adjusted_period_distributions_keur = tuple(adjusted)
    spv.total_distribution_keur = sum(adjusted)
    return spv


class TestDSRFWithSHL:
    """SPV with DSRF-adjusted distributions + SHL enrichment → HoldCo."""

    def test_dsrf_adjusted_dividend_plus_shl_interest(self):
        """HoldCo gross = DSRF-adjusted dividend + SHL interest; total_distribution_keur unchanged."""
        # raw wf distributions: [1000, 1200]; DSRF adjustments: [900, 1100]
        spv = _make_spv_with_dsrf(
            "SOLAR-DSRF",
            wf_distributions=[(0, 1000.0), (1, 1200.0)],
            dsrf_adjustments=[(0, 900.0), (1, 1100.0)],
            shl_lookup={0: (40.0, 200.0), 1: (30.0, 200.0)},
        )
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-DSRF", ownership_pct=1.0)],
            entity=entity,
        )

        holdco_result = build_holdco_result(inputs, portfolio)

        # Period 0: adjusted dividend=900, SHL interest=40
        assert holdco_result.periods[0].dividend_keur == 900.0
        assert holdco_result.periods[0].shl_interest_keur == 40.0
        assert holdco_result.periods[0].gross_income_keur == 940.0  # 900+40
        # total_distribution_keur = 900+1100 = 2000 (DSRF-adjusted sum, unchanged)
        assert spv.total_distribution_keur == 2000.0

        # Period 1: adjusted dividend=1100, SHL interest=30
        assert holdco_result.periods[1].dividend_keur == 1100.0
        assert holdco_result.periods[1].shl_interest_keur == 30.0
        assert holdco_result.periods[1].gross_income_keur == 1130.0

        # Totals
        assert holdco_result.total_dividend_keur == 2000.0
        assert holdco_result.total_shl_interest_keur == 70.0
        assert holdco_result.total_shl_principal_keur == 400.0
        assert holdco_result.total_gross_income_keur == 2070.0  # 2000+70

    def test_dsrf_adjusted_sum_matches_adjusted_period_distributions(self):
        """total_distribution_keur equals sum of adjusted_period_distributions_keur."""
        spv = _make_spv_with_dsrf(
            "SOLAR-DSRF",
            wf_distributions=[(0, 1000.0), (1, 1200.0), (2, 1400.0)],
            dsrf_adjustments=[(0, 900.0), (1, 1100.0), (2, 1300.0)],
        )
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-DSRF", ownership_pct=1.0)],
            entity=entity,
        )

        holdco_result = build_holdco_result(inputs, portfolio)

        # Dividend equals DSRF-adjusted distributions
        assert holdco_result.total_dividend_keur == sum(spv.adjusted_period_distributions_keur)

    def test_dsrf_with_shl_no_double_counting(self):
        """SHL interest added on top of DSRF dividend; no double-counting of SHL principal."""
        spv = _make_spv_with_dsrf(
            "SOLAR-DSRF",
            wf_distributions=[(0, 1000.0)],
            dsrf_adjustments=[(0, 850.0)],  # DSRF reduced by 150
            shl_lookup={0: (50.0, 200.0)},
        )
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-DSRF", ownership_pct=1.0)],
            entity=entity,
        )

        holdco_result = build_holdco_result(inputs, portfolio)

        # dividend=850 (DSRF-adjusted), SHL interest=50, SHL principal=200
        assert holdco_result.periods[0].dividend_keur == 850.0
        assert holdco_result.periods[0].shl_interest_keur == 50.0
        assert holdco_result.periods[0].shl_principal_keur == 200.0
        assert holdco_result.periods[0].gross_income_keur == 900.0  # 850+50

        # SHL principal tracked separately but excluded from gross income
        assert holdco_result.periods[0].gross_income_keur == (
            holdco_result.periods[0].dividend_keur + holdco_result.periods[0].shl_interest_keur
        )
        # principal not in gross income (principal > 0 proves it's tracked; gross < principal is not a required invariant)
        assert holdco_result.periods[0].shl_principal_keur > 0

    def test_dsrf_only_spv_no_shl_still_works(self):
        """DSRF without SHL: HoldCo gross = DSRF-adjusted dividend."""
        spv = _make_spv_with_dsrf(
            "SOLAR-DSRF",
            wf_distributions=[(0, 1000.0)],
            dsrf_adjustments=[(0, 900.0)],
        )
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-DSRF", ownership_pct=1.0)],
            entity=entity,
        )

        holdco_result = build_holdco_result(inputs, portfolio)

        assert holdco_result.periods[0].dividend_keur == 900.0
        assert holdco_result.periods[0].shl_interest_keur == 0.0
        assert holdco_result.periods[0].shl_principal_keur == 0.0
        assert holdco_result.periods[0].gross_income_keur == 900.0


class TestDSRFWithSHLFullPipeline:
    """Full pipeline: DSRF enrich → SHL enrich → HoldCo."""

    def test_dsrf_then_shl_enrichment_sequence(self):
        """Simulate: DSRF runs first (adjusted distributions set), then SHL enriches periods."""
        from unittest.mock import MagicMock

        # SPV with waterfall periods
        raw_distributions = [(i, 1000.0 + i * 100) for i in range(4)]
        periods = [_WFPeriodStub(idx, raw) for idx, raw in raw_distributions]
        wf = MagicMock()
        wf.periods = periods

        spv = MagicMock(spec=SPVOutput)
        spv.project_code = "SOLAR-1"
        spv.project_name = "Solar 1"
        spv.waterfall_result = wf
        # DSRF adjustments: -100 per period
        dsrf_adj = [(i, 1000.0 + i * 100 - 100.0) for i in range(4)]
        spv.adjusted_period_distributions_keur = tuple(a for _, a in dsrf_adj)
        spv.total_distribution_keur = sum(a for _, a in dsrf_adj)

        portfolio = _make_portfolio_result([spv])

        # SHL facility
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-1",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
            start_period_index=0,
        )
        shl_portfolio = run_shl_portfolio(SHLPortfolioInputs(facilities=(f,)))
        shl_by_borrower = group_shl_facilities_by_borrower(shl_portfolio)

        # SHL enrichment (after DSRF)
        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        # HoldCo
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        holdco_result = build_holdco_result(inputs, portfolio)

        # Periods 0, 1 have SHL, periods 2, 3 don't
        # Period 0: dividend=900, interest=40, principal=250
        assert holdco_result.periods[0].dividend_keur == 900.0
        assert holdco_result.periods[0].shl_interest_keur == 40.0
        assert holdco_result.periods[0].shl_principal_keur == 250.0
        assert holdco_result.periods[0].gross_income_keur == 940.0

        # Period 1: dividend=1000, interest=30, principal=250
        assert holdco_result.periods[1].dividend_keur == 1000.0
        assert holdco_result.periods[1].shl_interest_keur == 30.0
        assert holdco_result.periods[1].shl_principal_keur == 250.0
        assert holdco_result.periods[1].gross_income_keur == 1030.0

        # Period 2: facility has SHL (idx=2) — 2yr semiannual = 4 periods
        assert holdco_result.periods[2].shl_interest_keur == 20.0
        assert holdco_result.periods[2].shl_principal_keur == 250.0
        assert holdco_result.periods[2].dividend_keur == 1100.0
