"""Tests for integer SHL values and bool rejection in _safe_get_float."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from domain.portfolio.holdco import (
    HoldCoInputs,
    HoldCoEntity,
    HoldCoOpexInputs,
    SPVOwnership,
)
from domain.portfolio.holdco.runner import build_holdco_result
from domain.portfolio.independent import IndependentPortfolioResult, SPVOutput


def _make_portfolio_result(spvs, name="Test Portfolio"):
    """Create an IndependentPortfolioResult from mock SPVs."""
    result = MagicMock(spec=IndependentPortfolioResult)
    result.portfolio_name = name
    result.spv_outputs = tuple(spvs)
    result.warnings = ()
    return result


class TestIntegerSHLValues:
    """_safe_get_float must accept int SHL values and cast to float."""

    def test_integer_shl_interest_and_principal(self):
        """Integer shl_interest_keur=80 and shl_principal_keur=500 are read as floats."""
        # Create a waterfall period with INTEGER shl values (not float)
        wp = MagicMock()
        wp.distribution_keur = 1000.0
        wp.period_in_year = 1
        wp.shl_interest_keur = 80   # int, not float
        wp.shl_principal_keur = 500  # int, not float

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

        # Integer values must be cast to float
        c = result.periods[0].contributions[0]
        assert c.shl_interest_keur == 80.0,   f"Expected 80.0, got {c.shl_interest_keur}"
        assert c.shl_principal_keur == 500.0, f"Expected 500.0, got {c.shl_principal_keur}"
        # SHL interest contributes to gross income
        assert result.periods[0].gross_income_keur == 1080.0, f"Expected 1080.0, got {result.periods[0].gross_income_keur}"
        # SHL principal is tracked separately, excluded from gross income
        assert result.periods[0].shl_principal_keur == 500.0
        assert result.periods[0].shl_interest_keur == 80.0

    def test_integer_shl_with_50_percent_ownership(self):
        """Integer SHL values scale by ownership percentage correctly."""
        wp = MagicMock()
        wp.distribution_keur = 1000.0
        wp.period_in_year = 1
        wp.shl_interest_keur = 80   # int
        wp.shl_principal_keur = 500  # int

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
            ownerships=[SPVOwnership(spv_code="SOLAR", ownership_pct=0.5)],
            entity=entity,
        )

        result = build_holdco_result(inputs, portfolio)

        c = result.periods[0].contributions[0]
        assert c.shl_interest_keur == 40.0,   f"Expected 40.0, got {c.shl_interest_keur}"
        assert c.shl_principal_keur == 250.0, f"Expected 250.0, got {c.shl_principal_keur}"
        # gross_income = (1000 + 80) * 0.5 = 540
        assert result.periods[0].gross_income_keur == 540.0


class TestBoolSHLValuesRejected:
    """_safe_get_float must reject bool values and fall back to default."""

    def test_bool_shl_values_fall_back_to_default(self):
        """Boolean shl_interest_keur=True and shl_principal_keur=False → both 0.0."""
        wp = MagicMock()
        wp.distribution_keur = 1000.0
        wp.period_in_year = 1
        wp.shl_interest_keur = True   # bool — invalid
        wp.shl_principal_keur = False  # bool — invalid

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

        c = result.periods[0].contributions[0]
        # bool values must be rejected → default 0.0
        assert c.shl_interest_keur == 0.0,  f"Expected 0.0, got {c.shl_interest_keur}"
        assert c.shl_principal_keur == 0.0, f"Expected 0.0, got {c.shl_principal_keur}"
        # gross_income = dividend only (1000.0), no SHL interest
        assert result.periods[0].gross_income_keur == 1000.0, f"Expected 1000.0, got {result.periods[0].gross_income_keur}"

    def test_mixed_int_and_bool_int_wins(self):
        """int interest + bool principal → int accepted, bool rejected."""
        wp = MagicMock()
        wp.distribution_keur = 1000.0
        wp.period_in_year = 1
        wp.shl_interest_keur = 80   # int — valid
        wp.shl_principal_keur = False  # bool — invalid

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

        c = result.periods[0].contributions[0]
        assert c.shl_interest_keur == 80.0,   f"Expected 80.0, got {c.shl_interest_keur}"
        assert c.shl_principal_keur == 0.0, f"Expected 0.0, got {c.shl_principal_keur}"
        # gross_income includes int interest but not bool principal
        assert result.periods[0].gross_income_keur == 1080.0
