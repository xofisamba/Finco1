"""Phase 5B orchestrator tests — build_cash_ledger_from_results integration."""
from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock
import pytest

from domain.portfolio.cash_ledger import build_cash_ledger_from_results
from domain.portfolio.cash_ledger.inputs import CashMovementType


def _make_spv_output(project_code, adj_dists=None, wf_periods=None):
    """Factory: mock SPVOutput with optional waterfall result."""
    spv = MagicMock()
    spv.project_code = project_code
    spv.adjusted_period_distributions_keur = adj_dists or ()
    if wf_periods is not None:
        wf = MagicMock()
        wf.periods = wf_periods
        spv.waterfall_result = wf
    else:
        spv.waterfall_result = None
    return spv


def _make_wf_period(distribution_keur, shl_interest_keur=0.0, shl_principal_keur=0.0):
    p = MagicMock()
    p.distribution_keur = distribution_keur
    p.shl_interest_keur = shl_interest_keur
    p.shl_principal_keur = shl_principal_keur
    return p


def _make_holdco_result(name, periods_data):
    """Factory: mock HoldCoResult with per-period dividend, opex, tax, sponsor_dist, shl."""
    holdco = MagicMock()
    holdco.name = name
    holdco.periods = []
    for idx, d in enumerate(periods_data):
        p = MagicMock()
        p.period = idx
        p.dividend_keur = d.get("dividend_keur", 0.0)
        p.shl_interest_keur = d.get("shl_interest_keur", 0.0)
        p.shl_principal_keur = d.get("shl_principal_keur", 0.0)
        p.holdco_opex_keur = d.get("holdco_opex_keur", 0.0)
        p.tax_keur = d.get("tax_keur", 0.0)
        p.distribution_to_sponsor_keur = d.get("distribution_to_sponsor_keur", 0.0)
        holdco.periods.append(p)
    return holdco


def _make_portfolio_result(spv_outputs):
    pr = MagicMock()
    pr.spv_outputs = spv_outputs
    return pr


class TestBuildCashLedgerFromResults:
    """Tests for build_cash_ledger_from_results()."""

    def test_empty_inputs_return_empty_ledger(self):
        ledger = build_cash_ledger_from_results()
        assert ledger.entities == ()
        assert ledger.total_ending_cash_keur == 0.0

    def test_portfolio_result_only_creates_spv_entity_ledger(self):
        spv = _make_spv_output("SOLAR-1", adj_dists=(1000.0, 1100.0))
        pr = _make_portfolio_result([spv])
        ledger = build_cash_ledger_from_results(portfolio_result=pr)
        assert len(ledger.entities) == 1
        assert ledger.entities[0].entity_code == "SOLAR-1"
        assert ledger.entities[0].periods  # has period data

    def test_holdco_result_only_creates_holdco_entity_ledger(self):
        hc = _make_holdco_result("HOLDCO", [
            {"dividend_keur": 500.0, "shl_interest_keur": 50.0, "shl_principal_keur": 0.0,
             "holdco_opex_keur": 20.0, "tax_keur": 100.0, "distribution_to_sponsor_keur": 430.0},
        ])
        ledger = build_cash_ledger_from_results(holdco_result=hc)
        assert len(ledger.entities) == 1
        assert ledger.entities[0].entity_code == "HOLDCO"

    def test_portfolio_plus_holdco_creates_multiple_entities(self):
        spv = _make_spv_output("WIND-1", adj_dists=(800.0,))
        pr = _make_portfolio_result([spv])
        hc = _make_holdco_result("HOLDCO", [
            {"dividend_keur": 800.0, "holdco_opex_keur": 10.0, "tax_keur": 150.0,
             "distribution_to_sponsor_keur": 640.0},
        ])
        ledger = build_cash_ledger_from_results(portfolio_result=pr, holdco_result=hc)
        entity_codes = {e.entity_code for e in ledger.entities}
        assert "WIND-1" in entity_codes
        assert "HOLDCO" in entity_codes
        assert len(ledger.entities) == 2

    def test_opening_cash_by_entity_is_respected(self):
        spv = _make_spv_output("SOLAR-1", adj_dists=(500.0,))
        pr = _make_portfolio_result([spv])
        ledger = build_cash_ledger_from_results(
            portfolio_result=pr,
            opening_cash_by_entity={"SOLAR-1": 200.0},
        )
        assert ledger.entities[0].periods[0].opening_cash_keur == 200.0

    def test_no_mutation_of_source_results(self):
        spv = _make_spv_output("SOLAR-1", adj_dists=(1000.0,))
        pr = _make_portfolio_result([spv])
        hc = _make_holdco_result("HOLDCO", [
            {"dividend_keur": 500.0, "holdco_opex_keur": 10.0,
             "tax_keur": 100.0, "distribution_to_sponsor_keur": 390.0},
        ])
        build_cash_ledger_from_results(portfolio_result=pr, holdco_result=hc)
        # If we got here without exception, mutation didn't break anything.
        # Check the mocks are unchanged
        assert spv.adjusted_period_distributions_keur == (1000.0,)
        assert hc.periods[0].dividend_keur == 500.0

    def test_dsrf_adjusted_preferred_over_raw_waterfall(self):
        """When adjusted_period_distributions_keur is set, it is used (DSRF-adjusted)."""
        wf_period = _make_wf_period(distribution_keur=1000.0)  # raw = 1000
        spv = _make_spv_output("SOLAR-1", adj_dists=(800.0,), wf_periods=[wf_period])
        pr = _make_portfolio_result([spv])
        ledger = build_cash_ledger_from_results(portfolio_result=pr)
        # Find equity distribution movement
        eq_moves = [
            m for m in ledger.entities[0].periods[0].movements
            if m.movement_type == CashMovementType.EQUITY_DISTRIBUTION
        ]
        assert len(eq_moves) == 1
        assert eq_moves[0].amount_keur == -800.0  # from adjusted (800), not raw (1000)

    def test_shl_interest_and_principal_included(self):
        """SHL interest and principal from waterfall periods appear as movements."""
        wf_period = _make_wf_period(
            distribution_keur=500.0,
            shl_interest_keur=80.0,
            shl_principal_keur=200.0,
        )
        spv = _make_spv_output("SOLAR-1", wf_periods=[wf_period])
        pr = _make_portfolio_result([spv])
        ledger = build_cash_ledger_from_results(portfolio_result=pr)
        movement_types = {m.movement_type for m in ledger.entities[0].periods[0].movements}
        assert CashMovementType.SHL_INTEREST in movement_types
        assert CashMovementType.SHL_PRINCIPAL in movement_types

    def test_portfolio_total_ending_cash_equals_sum_of_entity_ending_cash(self):
        spv1 = _make_spv_output("SOLAR-1", adj_dists=(1000.0,))
        spv2 = _make_spv_output("WIND-1", adj_dists=(800.0,))
        pr = _make_portfolio_result([spv1, spv2])
        ledger = build_cash_ledger_from_results(portfolio_result=pr)
        entity_sum = sum(e.ending_cash_keur for e in ledger.entities)
        assert abs(ledger.total_ending_cash_keur - entity_sum) < 1e-6

    def test_multiple_spvs_each_get_own_entity_ledger(self):
        spv1 = _make_spv_output("SOLAR-1", adj_dists=(1000.0,))
        spv2 = _make_spv_output("WIND-1", adj_dists=(800.0,))
        pr = _make_portfolio_result([spv1, spv2])
        ledger = build_cash_ledger_from_results(portfolio_result=pr)
        codes = {e.entity_code for e in ledger.entities}
        assert codes == {"SOLAR-1", "WIND-1"}

    def test_holdco_dividend_maps_to_operating_cashflow(self):
        hc = _make_holdco_result("HOLDCO", [
            {"dividend_keur": 1000.0, "shl_interest_keur": 0.0, "shl_principal_keur": 0.0,
             "holdco_opex_keur": 0.0, "tax_keur": 0.0, "distribution_to_sponsor_keur": 0.0},
        ])
        ledger = build_cash_ledger_from_results(holdco_result=hc)
        move_types = {m.movement_type for m in ledger.entities[0].periods[0].movements}
        assert CashMovementType.OPERATING_CASHFLOW in move_types

    def test_portfolio_result_without_spv_outputs_attribute_returns_empty(self):
        """portfolio_result without spv_outputs attribute does not crash."""
        pr = MagicMock(spec=["name"])  # no spv_outputs at all
        del pr.spv_outputs
        ledger = build_cash_ledger_from_results(portfolio_result=pr)
        assert ledger.entities == ()
        assert ledger.total_ending_cash_keur == 0.0

    def test_portfolio_result_with_spv_outputs_none_returns_empty(self):
        """portfolio_result with spv_outputs=None does not crash."""
        pr = MagicMock()
        pr.spv_outputs = None
        ledger = build_cash_ledger_from_results(portfolio_result=pr)
        assert ledger.entities == ()
        assert ledger.total_ending_cash_keur == 0.0

    def test_holdco_opex_and_tax_negative(self):
        hc = _make_holdco_result("HOLDCO", [
            {"dividend_keur": 500.0, "shl_interest_keur": 0.0, "shl_principal_keur": 0.0,
             "holdco_opex_keur": 20.0, "tax_keur": 100.0, "distribution_to_sponsor_keur": 380.0},
        ])
        ledger = build_cash_ledger_from_results(holdco_result=hc)
        movements = ledger.entities[0].periods[0].movements
        opex_moves = [m for m in movements if m.movement_type == CashMovementType.HOLDCO_OPEX]
        tax_moves = [m for m in movements if m.movement_type == CashMovementType.HOLDCO_TAX]
        sponsor_moves = [m for m in movements if m.movement_type == CashMovementType.SPONSOR_DISTRIBUTION]
        assert all(m.amount_keur < 0 for m in opex_moves), "opex should be negative"
        assert all(m.amount_keur < 0 for m in tax_moves), "tax should be negative"
        assert all(m.amount_keur < 0 for m in sponsor_moves), "sponsor dist should be negative"