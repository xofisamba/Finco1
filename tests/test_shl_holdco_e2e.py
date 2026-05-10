"""Phase 4C HoldCo end-to-end SHL integration tests.

No sculpting. No capitalization. No HoldCo IRR.
"""
from __future__ import annotations

import pytest

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


class _WFPeriodStub:
    """Minimal real waterfall period stub (avoids MagicMock attr issues)."""
    def __init__(self, period_index, distribution_keur):
        self.period_index = period_index
        self.distribution_keur = distribution_keur


def _make_portfolio_result(spvs):
    result = pytest.importorskip("unittest.mock").MagicMock(spec=IndependentPortfolioResult)
    result.spv_outputs = tuple(spvs)
    result.warnings = ()
    return result


def _make_spv(code, distributions, shl_lookup=None):
    """Create a mock SPVOutput with waterfall periods and optional SHL lookup.

    distributions: list of (period_index, distribution_keur)
    shl_lookup: optional dict[period_index, (interest, principal)] injected
    """
    from unittest.mock import MagicMock

    periods = [_WFPeriodStub(idx, dist) for idx, dist in distributions]
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
    spv.adjusted_period_distributions_keur = ()
    spv.total_distribution_keur = sum(d for _, d in distributions)
    return spv


class TestHoldCoSHLE2E:
    """HoldCo receives dividend + SHL interest + SHL principal from enriched SPVs."""

    def test_holdco_dividend_plus_shl_interest_gross_income(self):
        """gross_income = dividend + SHL interest; principal excluded."""
        spv = _make_spv("SOLAR-1", [(0, 1000.0), (1, 1200.0)])
        # Pre-enrich with SHL: interest=(40,30), principal=(250,250)
        spv = _make_spv(
            "SOLAR-1",
            [(0, 1000.0), (1, 1200.0)],
            shl_lookup={0: (40.0, 250.0), 1: (30.0, 250.0)},
        )
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # Period 0: dividend=1000, interest=40, principal=250
        # gross_income = 1000 + 40 = 1040 (principal excluded)
        assert result.periods[0].gross_income_keur == 1040.0
        assert result.periods[0].dividend_keur == 1000.0
        assert result.periods[0].shl_interest_keur == 40.0
        assert result.periods[0].shl_principal_keur == 250.0

        # Period 1: dividend=1200, interest=30, principal=250
        assert result.periods[1].gross_income_keur == 1230.0
        assert result.periods[1].shl_interest_keur == 30.0
        assert result.periods[1].shl_principal_keur == 250.0

        # Totals
        assert result.total_dividend_keur == 2200.0
        assert result.total_shl_interest_keur == 70.0
        assert result.total_shl_principal_keur == 500.0
        assert result.total_gross_income_keur == 2270.0  # dividend + interest

    def test_holdco_50_percent_ownership_scales_shl(self):
        """50% HoldCo ownership scales both dividend and SHL flows."""
        spv = _make_spv(
            "SOLAR-1",
            [(0, 1000.0)],
            shl_lookup={0: (40.0, 250.0)},
        )
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=0.5)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # 50% of 1000 = 500 dividend, 50% of 40 = 20 interest, 50% of 250 = 125 principal
        assert result.periods[0].gross_income_keur == 520.0   # 500 + 20
        assert result.periods[0].dividend_keur == 500.0
        assert result.periods[0].shl_interest_keur == 20.0
        assert result.periods[0].shl_principal_keur == 125.0

    def test_holdco_principal_excluded_from_gross_income(self):
        """SHL principal is tracked but never appears in gross_income."""
        spv = _make_spv(
            "SOLAR-1",
            [(0, 500.0)],  # small dividend
            shl_lookup={0: (40.0, 2000.0)},  # large principal
        )
        portfolio = _make_portfolio_result([spv])

        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        # gross_income = dividend + interest = 500 + 40 = 540 (principal 2000 excluded)
        assert result.periods[0].gross_income_keur == 540.0
        assert result.periods[0].shl_principal_keur == 2000.0
        assert result.total_shl_principal_keur == 2000.0


class TestHoldCoSHLE2EWithIntegration:
    """Full pipeline: SHL facility → enrich → HoldCo aggregation."""

    def test_full_pipeline_shl_to_holdco(self):
        """Real SHL facility result enriched into portfolio result, then HoldCo."""
        from unittest.mock import MagicMock

        # Step 1: SPV waterfall periods
        spv = _make_spv("SOLAR-1", [(0, 1000.0), (1, 1200.0)])
        portfolio = _make_portfolio_result([spv])

        # Step 2: SHL facility
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-1",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        shl_result = run_shl_facility(f)

        # Step 3: group by borrower
        shl_by_borrower = group_shl_facilities_by_borrower(
            run_shl_portfolio(SHLPortfolioInputs(facilities=(f,)))
        )

        # Step 4: enrich portfolio result (in-place)
        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        # Step 5: HoldCo
        entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="SOLAR-1", ownership_pct=1.0)],
            entity=entity,
        )
        holdco_result = build_holdco_result(inputs, portfolio)

        # Verify: dividend + SHL interest in gross income
        assert holdco_result.periods[0].gross_income_keur > holdco_result.periods[0].dividend_keur
        # SHL interest is present
        assert holdco_result.periods[0].shl_interest_keur > 0.0
        # SHL principal is tracked separately
        assert holdco_result.periods[0].shl_principal_keur > 0.0
        # gross_income = dividend + interest (principal excluded)
        assert holdco_result.total_gross_income_keur == pytest.approx(
            holdco_result.total_dividend_keur + holdco_result.total_shl_interest_keur,
            rel=1e-9,
        )
