"""Tests for Phase 5A cash ledger adapters."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from domain.portfolio.cash_ledger.inputs import CashMovementType
from domain.portfolio.cash_ledger.adapters import (
    movements_from_holdco_result,
    movements_from_spv_output,
)


class TestMovementsFromHoldCoResult:
    def test_dividends_positive(self):
        holdco = MagicMock()
        p0 = MagicMock()
        p0.period = 0
        p0.dividend_keur = 1000.0
        p0.shl_interest_keur = 0.0
        p0.shl_principal_keur = 0.0
        p0.holdco_opex_keur = 0.0
        p0.tax_keur = 0.0
        p0.distribution_to_sponsor_keur = 0.0
        holdco.name = "HC"
        holdco.periods = [p0]

        movements = movements_from_holdco_result(holdco)
        div = [m for m in movements if m.movement_type == CashMovementType.OPERATING_CASHFLOW]
        assert len(div) == 1
        assert div[0].amount_keur == 1000.0
        assert div[0].amount_keur > 0

    def test_shl_interest_positive(self):
        holdco = MagicMock()
        p0 = MagicMock()
        p0.period = 0
        p0.dividend_keur = 1000.0
        p0.shl_interest_keur = 50.0
        p0.shl_principal_keur = 200.0
        p0.holdco_opex_keur = 0.0
        p0.tax_keur = 0.0
        p0.distribution_to_sponsor_keur = 0.0
        holdco.name = "HC"
        holdco.periods = [p0]

        movements = movements_from_holdco_result(holdco)
        shl_int = [m for m in movements if m.movement_type == CashMovementType.SHL_INTEREST]
        assert len(shl_int) == 1
        assert shl_int[0].amount_keur == 50.0
        assert shl_int[0].amount_keur > 0

    def test_shl_principal_positive(self):
        holdco = MagicMock()
        p0 = MagicMock()
        p0.period = 0
        p0.dividend_keur = 1000.0
        p0.shl_interest_keur = 50.0
        p0.shl_principal_keur = 200.0
        p0.holdco_opex_keur = 0.0
        p0.tax_keur = 0.0
        p0.distribution_to_sponsor_keur = 0.0
        holdco.name = "HC"
        holdco.periods = [p0]

        movements = movements_from_holdco_result(holdco)
        shl_principal = [m for m in movements if m.movement_type == CashMovementType.SHL_PRINCIPAL]
        assert len(shl_principal) == 1
        assert shl_principal[0].amount_keur == 200.0

    def test_opex_negative(self):
        holdco = MagicMock()
        p0 = MagicMock()
        p0.period = 0
        p0.dividend_keur = 0.0
        p0.shl_interest_keur = 0.0
        p0.shl_principal_keur = 0.0
        p0.holdco_opex_keur = 100.0
        p0.tax_keur = 0.0
        p0.distribution_to_sponsor_keur = 0.0
        holdco.name = "HC"
        holdco.periods = [p0]

        movements = movements_from_holdco_result(holdco)
        opex = [m for m in movements if m.movement_type == CashMovementType.HOLDCO_OPEX]
        assert len(opex) == 1
        assert opex[0].amount_keur == -100.0  # negative

    def test_tax_negative(self):
        holdco = MagicMock()
        p0 = MagicMock()
        p0.period = 0
        p0.dividend_keur = 0.0
        p0.shl_interest_keur = 0.0
        p0.shl_principal_keur = 0.0
        p0.holdco_opex_keur = 0.0
        p0.tax_keur = 200.0
        p0.distribution_to_sponsor_keur = 0.0
        holdco.name = "HC"
        holdco.periods = [p0]

        movements = movements_from_holdco_result(holdco)
        tax = [m for m in movements if m.movement_type == CashMovementType.HOLDCO_TAX]
        assert len(tax) == 1
        assert tax[0].amount_keur == -200.0  # negative

    def test_sponsor_distribution_negative(self):
        holdco = MagicMock()
        p0 = MagicMock()
        p0.period = 0
        p0.dividend_keur = 0.0
        p0.shl_interest_keur = 0.0
        p0.shl_principal_keur = 0.0
        p0.holdco_opex_keur = 0.0
        p0.tax_keur = 0.0
        p0.distribution_to_sponsor_keur = 800.0
        holdco.name = "HC"
        holdco.periods = [p0]

        movements = movements_from_holdco_result(holdco)
        sponsor = [m for m in movements if m.movement_type == CashMovementType.SPONSOR_DISTRIBUTION]
        assert len(sponsor) == 1
        assert sponsor[0].amount_keur == -800.0  # negative


class TestMovementsFromSPVOutput:
    def test_equity_distribution_from_adjusted_when_waterfall_missing(self):
        """When waterfall_result is None but adjusted_period_distributions_keur is set,
        equity distribution is emitted from the adjusted array (best-effort audit)."""
        spv = MagicMock()
        spv.project_code = "SOLAR-1"
        spv.adjusted_period_distributions_keur = (1000.0,)
        spv.waterfall_result = None

        movements = movements_from_spv_output(spv)
        eq = [m for m in movements if m.movement_type == CashMovementType.EQUITY_DISTRIBUTION]
        assert len(eq) == 1, f"expected 1 equity dist movement, got {movements}"
        assert eq[0].amount_keur == -1000.0  # negative

    def test_prefers_adjusted_over_raw_waterfall(self):
        spv = MagicMock()
        spv.project_code = "SOLAR-1"
        spv.adjusted_period_distributions_keur = (800.0,)  # DSRF-adjusted
        wf_period = MagicMock()
        wf_period.distribution_keur = 1000.0  # raw
        wf_period.shl_interest_keur = 0.0
        wf_period.shl_principal_keur = 0.0
        spv.waterfall_result = MagicMock()
        spv.waterfall_result.periods = [wf_period]

        movements = movements_from_spv_output(spv)
        eq = [m for m in movements if m.movement_type == CashMovementType.EQUITY_DISTRIBUTION]
        assert len(eq) == 1
        assert eq[0].amount_keur == -800.0  # adjusted, not raw

    def test_shl_interest_negative_from_waterfall(self):
        spv = MagicMock()
        spv.project_code = "SOLAR-1"
        spv.adjusted_period_distributions_keur = ()
        wf_period = MagicMock()
        wf_period.distribution_keur = 1000.0
        wf_period.shl_interest_keur = 40.0
        wf_period.shl_principal_keur = 0.0
        spv.waterfall_result = MagicMock()
        spv.waterfall_result.periods = [wf_period]

        movements = movements_from_spv_output(spv)
        shl_int = [m for m in movements if m.movement_type == CashMovementType.SHL_INTEREST]
        assert len(shl_int) == 1
        assert shl_int[0].amount_keur == -40.0  # negative

    def test_shl_principal_negative_from_waterfall(self):
        spv = MagicMock()
        spv.project_code = "SOLAR-1"
        spv.adjusted_period_distributions_keur = ()
        wf_period = MagicMock()
        wf_period.distribution_keur = 1000.0
        wf_period.shl_interest_keur = 0.0
        wf_period.shl_principal_keur = 250.0
        spv.waterfall_result = MagicMock()
        spv.waterfall_result.periods = [wf_period]

        movements = movements_from_spv_output(spv)
        shl_princ = [m for m in movements if m.movement_type == CashMovementType.SHL_PRINCIPAL]
        assert len(shl_princ) == 1
        assert shl_princ[0].amount_keur == -250.0  # negative
