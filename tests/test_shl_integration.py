"""Tests for Phase 4C SHL end-to-end integration layer.

No sculpting. No capitalization. No tax logic. No HoldCo IRR.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from domain.portfolio.shl.inputs import SHLFacility
from domain.portfolio.shl.runner import run_shl_facility, run_shl_portfolio
from domain.portfolio.shl import SHLPortfolioInputs
from domain.portfolio.shl.result import (
    SHLFacilityResult,
    SHLPortfolioResult,
)
from domain.portfolio.shl.integration import (
    build_shl_period_lookup,
    group_shl_facilities_by_borrower,
    inject_shl_into_waterfall_periods,
    enrich_portfolio_result_with_shl,
)
from domain.portfolio.independent import IndependentPortfolioResult, SPVOutput
from domain.portfolio.holdco import (
    HoldCoInputs,
    HoldCoEntity,
    HoldCoOpexInputs,
    SPVOwnership,
)
from domain.portfolio.holdco.runner import build_holdco_result


# ── helpers ────────────────────────────────────────────────────────────────────

class _WFPeriodStub:
    """Minimal real waterfall period stub for tests (avoids MagicMock attr issues).

    MagicMock auto-creates any attribute accessed, making hasattr always True and
    getattr-default not working for unset attrs. This real stub class solves it.
    """
    def __init__(self, period_index, distribution_keur):
        self.period_index = period_index
        self.distribution_keur = distribution_keur


def _make_spv_with_periods(code, periods_data):
    """Create a mock SPVOutput with waterfall periods.

    periods_data: list of (period_index, distribution_keur)
    """
    periods = [_WFPeriodStub(idx, dist) for idx, dist in periods_data]

    wf = MagicMock()
    wf.periods = periods

    spv = MagicMock(spec=SPVOutput)
    spv.project_code = code
    spv.project_name = code
    spv.waterfall_result = wf
    spv.adjusted_period_distributions_keur = ()
    spv.total_distribution_keur = sum(d for _, d in periods_data)
    return spv


def _make_portfolio_result(spvs):
    result = MagicMock(spec=IndependentPortfolioResult)
    result.spv_outputs = tuple(spvs)
    result.warnings = ()
    return result


# ── A. build_shl_period_lookup ───────────────────────────────────────────────

class TestBuildSHLPeriodLookup:
    def test_single_facility_result(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)
        lookup = build_shl_period_lookup(result)

        assert len(lookup) == 4  # 2 years * 2 = 4 semiannual periods
        assert 0 in lookup
        assert 1 in lookup
        # interest per period = 1000 * 0.08 / 2 = 40
        # principal per period = 1000 / 4 = 250
        assert lookup[0] == (40.0, 250.0)
        assert lookup[1] == (30.0, 250.0)  # interest declines as balance falls

    def test_period_index_respected(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=1,
            payment_frequency_per_year=2,
            start_period_index=3,
        )
        result = run_shl_facility(f)
        lookup = build_shl_period_lookup(result)

        assert 3 in lookup
        assert 4 in lookup
        assert 0 not in lookup
        assert 1 not in lookup

    def test_empty_result_returns_empty_dict(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SPV",
            principal_keur=0.0,  # zero principal → empty result
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        result = run_shl_facility(f)
        assert build_shl_period_lookup(result) == {}


# ── B. group_shl_facilities_by_borrower ─────────────────────────────────────

class TestGroupSHLFacilitiesByBorrower:
    def test_empty_shl_portfolio_returns_empty_dict(self):
        result = SHLPortfolioResult()
        assert group_shl_facilities_by_borrower(result) == {}

    def test_one_facility_grouped_by_borrower(self):
        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-1",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        shl_portfolio = run_shl_portfolio(SHLPortfolioInputs(facilities=(f,)))
        grouped = group_shl_facilities_by_borrower(shl_portfolio)

        assert "SOLAR-1" in grouped
        assert len(grouped["SOLAR-1"]) == 1
        assert grouped["SOLAR-1"][0].facility.borrower_entity_code == "SOLAR-1"

    def test_two_facilities_same_borrower_both_preserved(self):
        # Note: SHLPortfolioInputs rejects duplicate (lender, borrower) pairs.
        # So we use two different lenders for the same borrower.
        f1 = SHLFacility(
            lender_entity_code="HC-1",
            borrower_entity_code="SOLAR-1",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        f2 = SHLFacility(
            lender_entity_code="HC-2",
            borrower_entity_code="SOLAR-1",
            principal_keur=500.0,
            interest_rate_pa=0.10,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        shl_portfolio = run_shl_portfolio(SHLPortfolioInputs(facilities=(f1, f2)))
        grouped = group_shl_facilities_by_borrower(shl_portfolio)

        assert "SOLAR-1" in grouped
        assert len(grouped["SOLAR-1"]) == 2
        borrowers = {fac.facility.borrower_entity_code for fac in grouped["SOLAR-1"]}
        assert borrowers == {"SOLAR-1"}  # same borrower, different lenders

    def test_two_facilities_different_borrowers_split_correctly(self):
        f1 = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-A",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        f2 = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="WIND-B",
            principal_keur=500.0,
            interest_rate_pa=0.10,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        shl_portfolio = run_shl_portfolio(SHLPortfolioInputs(facilities=(f1, f2)))
        grouped = group_shl_facilities_by_borrower(shl_portfolio)

        assert len(grouped) == 2
        assert "SOLAR-A" in grouped
        assert "WIND-B" in grouped
        assert len(grouped["SOLAR-A"]) == 1
        assert len(grouped["WIND-B"]) == 1


# ── C. enrich_portfolio_result_with_shl — one SPV, one facility ─────────────

class TestEnrichOneSPVOneFacility:
    def test_waterfall_periods_receive_shl_values(self):
        spv = _make_spv_with_periods("SOLAR-1", [(0, 1000.0), (1, 1200.0)])
        portfolio = _make_portfolio_result([spv])

        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-1",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        shl_fac_result = run_shl_facility(f)
        shl_by_borrower = {"SOLAR-1": (shl_fac_result,)}

        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        wf_periods = spv.waterfall_result.periods
        # Period 0: interest = 1000 * 0.08/2 = 40, principal = 1000/4 = 250
        assert wf_periods[0].shl_interest_keur == 40.0
        assert wf_periods[0].shl_principal_keur == 250.0
        # Period 1: interest = 30, principal = 250
        assert wf_periods[1].shl_interest_keur == 30.0
        assert wf_periods[1].shl_principal_keur == 250.0

    def test_distribution_keur_unchanged(self):
        spv = _make_spv_with_periods("SOLAR-1", [(0, 1000.0), (1, 1200.0)])
        portfolio = _make_portfolio_result([spv])

        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-1",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        shl_fac_result = run_shl_facility(f)
        shl_by_borrower = {"SOLAR-1": (shl_fac_result,)}

        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        wf_periods = spv.waterfall_result.periods
        assert wf_periods[0].distribution_keur == 1000.0
        assert wf_periods[1].distribution_keur == 1200.0


# ── D. multi-facility overlapping periods ───────────────────────────────────

class TestMultiFacilityOverlappingPeriods:
    def test_same_period_interest_principal_sums_correctly(self):
        spv = _make_spv_with_periods("SOLAR-1", [(0, 1000.0)])
        portfolio = _make_portfolio_result([spv])

        f1 = SHLFacility(
            lender_entity_code="HC-1",
            borrower_entity_code="SOLAR-1",
            principal_keur=500.0,
            interest_rate_pa=0.08,
            tenor_years=1,
            payment_frequency_per_year=1,
        )
        f2 = SHLFacility(
            lender_entity_code="HC-2",
            borrower_entity_code="SOLAR-1",
            principal_keur=500.0,
            interest_rate_pa=0.10,
            tenor_years=1,
            payment_frequency_per_year=1,
        )
        fac1_result = run_shl_facility(f1)
        fac2_result = run_shl_facility(f2)
        shl_by_borrower = {"SOLAR-1": (fac1_result, fac2_result)}

        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        p = spv.waterfall_result.periods[0]
        # f1: interest=500*0.08=40, principal=500; f2: interest=500*0.10=50, principal=500
        assert p.shl_interest_keur == 90.0   # 40 + 50
        assert p.shl_principal_keur == 1000.0  # 500 + 500


# ── E. multi-SPV ─────────────────────────────────────────────────────────────

class TestMultiSPV:
    def test_spv_a_receives_only_a_shl_flows(self):
        spv_a = _make_spv_with_periods("SOLAR-A", [(0, 1000.0)])
        spv_b = _make_spv_with_periods("WIND-B", [(0, 800.0)])
        portfolio = _make_portfolio_result([spv_a, spv_b])

        f_a = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-A",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=1,
            payment_frequency_per_year=2,
        )
        f_b = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="WIND-B",
            principal_keur=500.0,
            interest_rate_pa=0.10,
            tenor_years=1,
            payment_frequency_per_year=2,
        )
        shl_a = run_shl_facility(f_a)
        shl_b = run_shl_facility(f_b)
        shl_by_borrower = {
            "SOLAR-A": (shl_a,),
            "WIND-B": (shl_b,),
        }

        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        p_a = spv_a.waterfall_result.periods[0]
        p_b = spv_b.waterfall_result.periods[0]
        # SOLAR-A: interest=1000*0.08/2=40, principal=1000/2=500
        assert p_a.shl_interest_keur == 40.0
        assert p_a.shl_principal_keur == 500.0
        # WIND-B: interest=500*0.10/2=25, principal=500/2=250
        assert p_b.shl_interest_keur == 25.0
        assert p_b.shl_principal_keur == 250.0

    def test_spv_b_not_affected_by_solar_shl(self):
        spv_a = _make_spv_with_periods("SOLAR-A", [(0, 1000.0)])
        spv_b = _make_spv_with_periods("WIND-B", [(0, 800.0)])
        portfolio = _make_portfolio_result([spv_a, spv_b])

        f_a = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-A",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=1,
            payment_frequency_per_year=2,
        )
        shl_a = run_shl_facility(f_a)
        # Only SOLAR-A has SHL, WIND-B does not
        shl_by_borrower = {"SOLAR-A": (shl_a,)}

        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        p_a = spv_a.waterfall_result.periods[0]
        p_b = spv_b.waterfall_result.periods[0]
        assert p_a.shl_interest_keur == 40.0
        assert p_a.shl_principal_keur == 500.0
        # WIND-B should not have any SHL values set (stays 0.0)
        assert getattr(p_b, "shl_interest_keur", 0.0) == 0.0


# ── F. missing borrower ─────────────────────────────────────────────────────

class TestMissingBorrower:
    def test_no_crash_with_missing_borrower(self):
        spv = _make_spv_with_periods("SOLAR-1", [(0, 1000.0)])
        portfolio = _make_portfolio_result([spv])

        # No SHL for SOLAR-1 in mapping
        shl_by_borrower = {}

        # Must not raise
        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

    def test_unrelated_spv_gets_zero_shl(self):
        spv = _make_spv_with_periods("UNRELATED", [(0, 1000.0)])
        portfolio = _make_portfolio_result([spv])

        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-1",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=2,
            payment_frequency_per_year=2,
        )
        shl_result = run_shl_facility(f)
        # Only SOLAR-1 has SHL, UNRELATED does not
        shl_by_borrower = {"SOLAR-1": (shl_result,)}

        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        p = spv.waterfall_result.periods[0]
        # UNRELATED should not have shl_interest_keur set or default to 0.0
        val = getattr(p, "shl_interest_keur", 0.0)
        assert val == 0.0


# ── G. start_period_index ───────────────────────────────────────────────────

class TestStartPeriodIndex:
    def test_enrichment_injects_at_correct_period_index(self):
        # Waterfall has periods 0-9, SHL facility starts at period 3
        wf_periods_data = [(i, 1000.0) for i in range(10)]
        spv = _make_spv_with_periods("SOLAR-1", wf_periods_data)
        portfolio = _make_portfolio_result([spv])

        f = SHLFacility(
            lender_entity_code="HC",
            borrower_entity_code="SOLAR-1",
            principal_keur=1000.0,
            interest_rate_pa=0.08,
            tenor_years=1,
            payment_frequency_per_year=2,
            start_period_index=3,  # starts at period 3
        )
        shl_result = run_shl_facility(f)
        shl_by_borrower = {"SOLAR-1": (shl_result,)}

        enrich_portfolio_result_with_shl(portfolio, shl_by_borrower)

        wf = spv.waterfall_result.periods
        # Periods 0-2: no SHL → 0.0
        assert wf[0].shl_interest_keur == 0.0
        assert wf[1].shl_interest_keur == 0.0
        assert wf[2].shl_interest_keur == 0.0
        # Period 3: has SHL
        assert wf[3].shl_interest_keur > 0.0
        # Period 4: has SHL
        assert wf[4].shl_interest_keur > 0.0
        # Period 5+: no SHL (facility ended after 2 periods)
        assert wf[5].shl_interest_keur == 0.0
        assert wf[6].shl_interest_keur == 0.0
