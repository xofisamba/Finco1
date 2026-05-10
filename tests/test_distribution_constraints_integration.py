"""Phase 5D.2 integration tests — cash ledger → distribution constraint evaluator."""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from domain.portfolio.cash_ledger import (
    CashLedgerPeriod,
    CashMovement,
    CashMovementType,
    EntityCashLedger,
    PortfolioCashLedger,
)
from domain.portfolio.distribution_constraints import (
    DistributionBlockReason,
    DistributionConstraintConfig,
)
from domain.portfolio.distribution_constraints.integration import (
    cash_available_by_period_from_entity_ledger,
    requested_distributions_from_entity_ledger,
    evaluate_constraints_from_entity_ledger,
    evaluate_constraints_from_portfolio_ledger,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def cm(period, entity, mtype, amount):
    return CashMovement(
        period=period,
        entity_code=entity,
        movement_type=mtype,
        amount_keur=amount,
        description="",
    )


def make_entity_ledger(entity_code, periods_data):
    """periods_data: list of (period, opening, movements, closing, retained)"""
    periods = []
    for period_idx, opening, movement_list, closing, retained in periods_data:
        periods.append(CashLedgerPeriod(
            period=period_idx,
            entity_code=entity_code,
            opening_cash_keur=opening,
            movements=tuple(movement_list),
            closing_cash_keur=closing,
            retained_cash_keur=retained,
            warnings=(),
        ))
    total_movements = sum(
        sum(m.amount_keur for m in p.movements)
        for p in periods
    )
    return EntityCashLedger(
        entity_code=entity_code,
        periods=tuple(periods),
        total_movements_keur=total_movements,
        ending_cash_keur=periods[-1].closing_cash_keur if periods else 0.0,
        warnings=(),
    )


class TestCashAvailableByPeriod:
    """Tests for cash_available_by_period_from_entity_ledger."""

    def test_empty_ledger_returns_empty_tuple(self):
        ledger = make_entity_ledger("SOLAR-1", [])
        assert cash_available_by_period_from_entity_ledger(ledger) == ()

    def test_excludes_equity_distribution(self):
        # Equity distribution of -500 should NOT reduce cash available
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 100.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             600.0, 600.0),
        ])
        cash = cash_available_by_period_from_entity_ledger(ledger)
        # available = opening + non-dist movements = 1000 + 100 = 1100
        assert cash == (1100.0,)

    def test_excludes_sponsor_distribution(self):
        ledger = make_entity_ledger("HOLDCO", [
            (0, 500.0,
             [cm(0, "HOLDCO", CashMovementType.OPERATING_CASHFLOW, 200.0),
              cm(0, "HOLDCO", CashMovementType.SPONSOR_DISTRIBUTION, -300.0)],
             400.0, 400.0),
        ])
        cash = cash_available_by_period_from_entity_ledger(ledger)
        # available = opening + opcf = 500 + 200 = 700
        assert cash == (700.0,)

    def test_includes_operating_cashflow(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 300.0)],
             1300.0, 1300.0),
        ])
        cash = cash_available_by_period_from_entity_ledger(ledger)
        assert cash == (1300.0,)  # opening 1000 + opcf 300

    def test_includes_shl_interest_and_principal(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 500.0,
             [cm(0, "SOLAR-1", CashMovementType.SHL_INTEREST, 50.0),
              cm(0, "SOLAR-1", CashMovementType.SHL_PRINCIPAL, 200.0)],
             750.0, 750.0),
        ])
        cash = cash_available_by_period_from_entity_ledger(ledger)
        # available = opening + 50 + 200 = 750
        assert cash == (750.0,)

    def test_includes_taxes_opex_debt_service(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.TAX, -200.0),
              cm(0, "SOLAR-1", CashMovementType.SENIOR_DEBT_SERVICE, -300.0),
              cm(0, "SOLAR-1", CashMovementType.HOLDCO_OPEX, -50.0)],
             450.0, 450.0),
        ])
        cash = cash_available_by_period_from_entity_ledger(ledger)
        # available = opening -200 -300 -50 = 450
        assert cash == (450.0,)

    def test_multiple_periods_preserve_order(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0, [], 1000.0, 1000.0),
            (1, 1000.0, [cm(1, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 200.0)],
             1200.0, 1200.0),
        ])
        cash = cash_available_by_period_from_entity_ledger(ledger)
        assert cash == (1000.0, 1200.0)


class TestRequestedDistributionsFromEntityLedger:
    """Tests for requested_distributions_from_entity_ledger."""

    def test_empty_ledger_returns_empty_tuple(self):
        ledger = make_entity_ledger("SOLAR-1", [])
        assert requested_distributions_from_entity_ledger(ledger) == ()

    def test_converts_negative_equity_distribution_to_positive(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0, [cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             500.0, 500.0),
        ])
        req = requested_distributions_from_entity_ledger(ledger)
        assert req == (500.0,)

    def test_converts_negative_sponsor_distribution_to_positive(self):
        ledger = make_entity_ledger("HOLDCO", [
            (0, 1000.0, [cm(0, "HOLDCO", CashMovementType.SPONSOR_DISTRIBUTION, -300.0)],
             700.0, 700.0),
        ])
        req = requested_distributions_from_entity_ledger(ledger)
        assert req == (300.0,)

    def test_multiple_distributions_in_same_period_summed(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -200.0),
              cm(0, "SOLAR-1", CashMovementType.SPONSOR_DISTRIBUTION, -300.0)],
             500.0, 500.0),
        ])
        req = requested_distributions_from_entity_ledger(ledger)
        assert req == (500.0,)  # 200 + 300

    def test_no_distribution_returns_zero(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0, [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 100.0)],
             1100.0, 1100.0),
        ])
        req = requested_distributions_from_entity_ledger(ledger)
        assert req == (0.0,)

    def test_multiple_periods_preserve_order(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0, [cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -100.0)],
             900.0, 900.0),
            (1, 900.0, [cm(1, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -200.0)],
             700.0, 700.0),
        ])
        req = requested_distributions_from_entity_ledger(ledger)
        assert req == (100.0, 200.0)


class TestEvaluateConstraintsFromEntityLedger:
    """Tests for evaluate_constraints_from_entity_ledger."""

    def test_config_none_is_pass_through(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        result = evaluate_constraints_from_entity_ledger(ledger, config=None)
        assert result.entity_code == "SOLAR-1"
        assert result.periods[0].allowed_distribution_keur == 500.0
        assert result.periods[0].block_reasons == ()

    def test_minimum_cash_reserve_reduces_allowed(self):
        cfg = DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=200.0)
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        result = evaluate_constraints_from_entity_ledger(ledger, config=cfg)
        # cash_available = 1000 (opening) + 0 (non-dist movements excluding eq dist)
        # Actually: non-dist = OPERATING_CASHFLOW=500... opening=1000 + 500 = 1500
        # reserve = 200, requested = 500, allowed = min(500, max(0, 1500-200)) = 500
        assert result.periods[0].allowed_distribution_keur == 500.0

    def test_minimum_cash_reserve_blocks_excess(self):
        cfg = DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=800.0)
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -800.0)],
             700.0, 700.0),
        ])
        result = evaluate_constraints_from_entity_ledger(ledger, config=cfg)
        # cash_available = opening + non-dist = 1000 + 500 = 1500
        # max_allowed = max(0, 1500 - 800) = 700
        # requested = 800, allowed = min(800, 700) = 700
        assert result.periods[0].allowed_distribution_keur == 700.0
        assert DistributionBlockReason.MINIMUM_CASH_RESERVE in result.periods[0].block_reasons

    def test_manual_lockup_blocks_distribution(self):
        cfg = DistributionConstraintConfig(enabled=True, manual_lockup_periods=(0,))
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        result = evaluate_constraints_from_entity_ledger(ledger, config=cfg)
        assert result.periods[0].allowed_distribution_keur == 0.0
        assert DistributionBlockReason.MANUAL_LOCKUP in result.periods[0].block_reasons

    def test_no_mutation_of_ledger(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0, [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 100.0),
                         cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -100.0)],
             1000.0, 1000.0),
        ])
        evaluate_constraints_from_entity_ledger(ledger, config=None)
        assert ledger.periods[0].opening_cash_keur == 1000.0
        assert ledger.periods[0].closing_cash_keur == 1000.0


class TestEvaluateConstraintsFromPortfolioLedger:
    """Tests for evaluate_constraints_from_portfolio_ledger."""

    def test_multiple_entities_evaluated(self):
        ledger1 = make_entity_ledger("SOLAR-1", [
            (0, 1000.0, [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 100.0),
                         cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -100.0)],
             1000.0, 1000.0),
        ])
        ledger2 = make_entity_ledger("WIND-1", [
            (0, 800.0, [cm(0, "WIND-1", CashMovementType.OPERATING_CASHFLOW, 200.0),
                        cm(0, "WIND-1", CashMovementType.EQUITY_DISTRIBUTION, -200.0)],
             800.0, 800.0),
        ])
        port = PortfolioCashLedger(entities=(ledger1, ledger2), total_ending_cash_keur=1800.0)
        results = evaluate_constraints_from_portfolio_ledger(port)
        codes = {r.entity_code for r in results}
        assert codes == {"SOLAR-1", "WIND-1"}

    def test_config_by_entity_applies_specific_config(self):
        solar = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        wind = make_entity_ledger("WIND-1", [
            (0, 1000.0,
             [cm(0, "WIND-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "WIND-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        port = PortfolioCashLedger(entities=(solar, wind), total_ending_cash_keur=2000.0)
        solar_cfg = DistributionConstraintConfig(enabled=True, manual_lockup_periods=(0,))
        cfg_by_entity = {"SOLAR-1": solar_cfg}
        results = evaluate_constraints_from_portfolio_ledger(port, config_by_entity=cfg_by_entity)
        solar_result = next(r for r in results if r.entity_code == "SOLAR-1")
        wind_result = next(r for r in results if r.entity_code == "WIND-1")
        assert solar_result.periods[0].allowed_distribution_keur == 0.0
        assert wind_result.periods[0].allowed_distribution_keur == 500.0  # pass-through

    def test_default_config_applies_to_unconfigured_entity(self):
        solar = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        port = PortfolioCashLedger(entities=(solar,), total_ending_cash_keur=1000.0)
        default_cfg = DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=300.0)
        results = evaluate_constraints_from_portfolio_ledger(port, default_config=default_cfg)
        assert results[0].periods[0].allowed_distribution_keur == 500.0  # 500 < 1200

    def test_no_mutation_of_portfolio_ledger(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0, [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 100.0),
                         cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -100.0)],
             1000.0, 1000.0),
        ])
        port = PortfolioCashLedger(entities=(ledger,), total_ending_cash_keur=1000.0)
        evaluate_constraints_from_portfolio_ledger(port)
        assert port.entities[0].periods[0].opening_cash_keur == 1000.0

    def test_empty_portfolio_returns_empty_tuple(self):
        port = PortfolioCashLedger(entities=(), total_ending_cash_keur=0.0)
        results = evaluate_constraints_from_portfolio_ledger(port)
        assert results == ()