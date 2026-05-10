"""Phase 5D.3 tests for SPV retained cash overlay."""
from __future__ import annotations

import pytest

from domain.portfolio.distribution_constraints import (
    DistributionBlockReason,
    DistributionConstraintConfig,
)
from domain.portfolio.distribution_constraints.result import (
    DistributionConstraintPeriod,
    DistributionConstraintResult,
)
from domain.portfolio.distribution_constraints.overlay import (
    SPVRetainedCashPeriod,
    SPVRetainedCashOverlay,
    build_spv_retained_cash_overlay,
    build_spv_retained_cash_overlays_from_portfolio_ledger,
)
from domain.portfolio.cash_ledger import (
    CashLedgerPeriod,
    CashMovement,
    CashMovementType,
    EntityCashLedger,
    PortfolioCashLedger,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def cm(period, entity, mtype, amount):
    return CashMovement(
        period=period, entity_code=entity, movement_type=mtype,
        amount_keur=amount, description="",
    )


def make_entity_ledger(entity_code, periods_data):
    periods = []
    for period_idx, opening, movement_list, closing, retained in periods_data:
        periods.append(CashLedgerPeriod(
            period=period_idx, entity_code=entity_code,
            opening_cash_keur=opening, movements=tuple(movement_list),
            closing_cash_keur=closing, retained_cash_keur=retained, warnings=(),
        ))
    return EntityCashLedger(
        entity_code=entity_code, periods=tuple(periods),
        total_movements_keur=sum(sum(m.amount_keur for m in p.movements) for p in periods),
        ending_cash_keur=periods[-1].closing_cash_keur if periods else 0.0,
        warnings=(),
    )


# ── A. SPVRetainedCashPeriod validation ───────────────────────────────────────

class TestSPVRetainedCashPeriod:
    def test_valid_period_passes(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
        )
        assert p.period == 0

    def test_negative_period_raises(self):
        with pytest.raises(ValueError, match="period must be >= 0"):
            SPVRetainedCashPeriod(
                period=-1, entity_code="SOLAR-1",
                requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
                retained_cash_keur=1500.0, cash_before_distribution_keur=2000.0,
            )

    def test_empty_entity_code_raises(self):
        with pytest.raises(ValueError, match="entity_code must be non-empty"):
            SPVRetainedCashPeriod(
                period=0, entity_code="",
                requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
                retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
            )

    def test_whitespace_entity_code_raises(self):
        with pytest.raises(ValueError, match="entity_code must be non-empty"):
            SPVRetainedCashPeriod(
                period=0, entity_code="   ",
                requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
                retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
            )

    def test_allowed_gt_requested_raises(self):
        with pytest.raises(ValueError, match="allowed_distribution_keur .+ cannot exceed"):
            SPVRetainedCashPeriod(
                period=0, entity_code="SOLAR-1",
                requested_distribution_keur=300.0, allowed_distribution_keur=500.0,
                retained_cash_keur=-200.0, cash_before_distribution_keur=300.0,
            )

    def test_retained_cash_mismatch_raises(self):
        with pytest.raises(ValueError, match="retained_cash_keur .+ must equal"):
            SPVRetainedCashPeriod(
                period=0, entity_code="SOLAR-1",
                requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
                retained_cash_keur=999.0,   # wrong: should be 500.0
                cash_before_distribution_keur=1000.0,
            )

    def test_tiny_float_tolerance_passes(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0 + 1e-9,  # within 1e-6 tolerance
            cash_before_distribution_keur=1000.0,
        )
        assert abs(p.retained_cash_keur - 500.0) <= 1e-6

    def test_block_reasons_and_warnings_accepted(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=0.0,
            retained_cash_keur=1000.0, cash_before_distribution_keur=1000.0,
            block_reasons=(DistributionBlockReason.MANUAL_LOCKUP,),
            warnings=("Distribution locked.",),
        )
        assert DistributionBlockReason.MANUAL_LOCKUP in p.block_reasons
        assert any("Distribution locked" in w for w in p.warnings)


# ── B. SPVRetainedCashOverlay totals ─────────────────────────────────────────

class TestSPVRetainedCashOverlay:
    def test_auto_fill_totals_from_periods(self):
        p1 = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=400.0,
            retained_cash_keur=600.0, cash_before_distribution_keur=1000.0,
        )
        p2 = SPVRetainedCashPeriod(
            period=1, entity_code="SOLAR-1",
            requested_distribution_keur=300.0, allowed_distribution_keur=300.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=800.0,
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p1, p2))
        assert ov.total_requested_distribution_keur == 800.0
        assert ov.total_allowed_distribution_keur == 700.0
        assert ov.total_retained_cash_keur == 1100.0

    def test_correct_explicit_totals_pass(self):
        p1 = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
        )
        ov = SPVRetainedCashOverlay(
            entity_code="SOLAR-1", periods=(p1,),
            total_requested_distribution_keur=500.0,
            total_allowed_distribution_keur=500.0,
            total_retained_cash_keur=500.0,
        )
        assert ov.total_requested_distribution_keur == 500.0

    def test_wrong_requested_total_raises(self):
        p1 = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
        )
        with pytest.raises(ValueError, match="total_requested_distribution_keur"):
            SPVRetainedCashOverlay(
                entity_code="SOLAR-1", periods=(p1,),
                total_requested_distribution_keur=999.0,  # wrong
                total_allowed_distribution_keur=500.0,
                total_retained_cash_keur=500.0,
            )

    def test_wrong_allowed_total_raises(self):
        p1 = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
        )
        with pytest.raises(ValueError, match="total_allowed_distribution_keur"):
            SPVRetainedCashOverlay(
                entity_code="SOLAR-1", periods=(p1,),
                total_requested_distribution_keur=500.0,
                total_allowed_distribution_keur=999.0,  # wrong
                total_retained_cash_keur=500.0,
            )

    def test_wrong_retained_total_raises(self):
        p1 = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
        )
        with pytest.raises(ValueError, match="total_retained_cash_keur"):
            SPVRetainedCashOverlay(
                entity_code="SOLAR-1", periods=(p1,),
                total_requested_distribution_keur=500.0,
                total_allowed_distribution_keur=500.0,
                total_retained_cash_keur=999.0,  # wrong
            )


# ── C. build_spv_retained_cash_overlay ─────────────────────────────────────────

class TestBuildSPVRetainedCashOverlay:
    def test_maps_one_constraint_period_correctly(self):
        cp = DistributionConstraintPeriod(
            period=0, entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0,
            requested_distribution_keur=500.0,
            allowed_distribution_keur=500.0,
            retained_cash_keur=500.0,
            block_reasons=(DistributionBlockReason.NONE,),
            warnings=(),
        )
        cr = DistributionConstraintResult(
            entity_code="SOLAR-1", periods=(cp,),
            total_requested_distribution_keur=500.0,
            total_allowed_distribution_keur=500.0,
            total_retained_cash_keur=500.0,
        )
        ov = build_spv_retained_cash_overlay(cr)
        assert ov.entity_code == "SOLAR-1"
        assert len(ov.periods) == 1
        assert ov.periods[0].allowed_distribution_keur == 500.0
        assert ov.periods[0].retained_cash_keur == 500.0

    def test_maps_block_reasons_and_warnings(self):
        cp = DistributionConstraintPeriod(
            period=0, entity_code="SOLAR-1",
            cash_before_distribution_keur=500.0, requested_distribution_keur=500.0,
            allowed_distribution_keur=0.0, retained_cash_keur=500.0,
            block_reasons=(DistributionBlockReason.MANUAL_LOCKUP,),
            warnings=("Period 0 locked.",),
        )
        cr = DistributionConstraintResult(
            entity_code="SOLAR-1", periods=(cp,),
            total_requested_distribution_keur=500.0,
            total_allowed_distribution_keur=0.0,
            total_retained_cash_keur=500.0,
            warnings=("Period 0 locked.",),
        )
        ov = build_spv_retained_cash_overlay(cr)
        assert DistributionBlockReason.MANUAL_LOCKUP in ov.periods[0].block_reasons
        assert any("Period 0 locked" in w for w in ov.warnings)

    def test_no_mutation_of_source_constraint_result(self):
        cp = DistributionConstraintPeriod(
            period=0, entity_code="SOLAR-1",
            cash_before_distribution_keur=1000.0, requested_distribution_keur=500.0,
            allowed_distribution_keur=500.0, retained_cash_keur=500.0,
        )
        cr = DistributionConstraintResult(
            entity_code="SOLAR-1", periods=(cp,),
            total_requested_distribution_keur=500.0,
            total_allowed_distribution_keur=500.0,
            total_retained_cash_keur=500.0,
        )
        build_spv_retained_cash_overlay(cr)
        assert cr.entity_code == "SOLAR-1"
        assert cr.total_requested_distribution_keur == 500.0


# ── D. build overlays from portfolio ledger ───────────────────────────────────

class TestBuildSPVRetainedCashOverlaysFromPortfolioLedger:
    def test_one_spv_ledger_produces_one_overlay(self):
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        port = PortfolioCashLedger(entities=(ledger,), total_ending_cash_keur=1000.0)
        overlays = build_spv_retained_cash_overlays_from_portfolio_ledger(port)
        assert len(overlays) == 1
        assert overlays[0].entity_code == "SOLAR-1"

    def test_minimum_cash_reserve_reduces_allowed(self):
        cfg = DistributionConstraintConfig(
            enabled=True, minimum_cash_reserve_keur=300.0,
        )
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        port = PortfolioCashLedger(entities=(ledger,), total_ending_cash_keur=1000.0)
        overlays = build_spv_retained_cash_overlays_from_portfolio_ledger(
            port, config_by_entity={"SOLAR-1": cfg},
        )
        # cash_available = opening + non-dist = 1000 + 500 = 1500
        # max_allowed = 1500 - 300 = 1200, requested = 500, allowed = 500
        assert overlays[0].periods[0].allowed_distribution_keur == 500.0

    def test_manual_lockup_blocks_distribution(self):
        cfg = DistributionConstraintConfig(enabled=True, manual_lockup_periods=(0,))
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
        ])
        port = PortfolioCashLedger(entities=(ledger,), total_ending_cash_keur=1000.0)
        overlays = build_spv_retained_cash_overlays_from_portfolio_ledger(
            port, config_by_entity={"SOLAR-1": cfg},
        )
        assert overlays[0].periods[0].allowed_distribution_keur == 0.0
        assert DistributionBlockReason.MANUAL_LOCKUP in overlays[0].periods[0].block_reasons

    def test_multiple_entities_produce_multiple_overlays(self):
        l1 = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 100.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -100.0)],
             1000.0, 1000.0),
        ])
        l2 = make_entity_ledger("WIND-1", [
            (0, 800.0,
             [cm(0, "WIND-1", CashMovementType.OPERATING_CASHFLOW, 200.0),
              cm(0, "WIND-1", CashMovementType.EQUITY_DISTRIBUTION, -200.0)],
             800.0, 800.0),
        ])
        port = PortfolioCashLedger(entities=(l1, l2), total_ending_cash_keur=1800.0)
        overlays = build_spv_retained_cash_overlays_from_portfolio_ledger(port)
        codes = {o.entity_code for o in overlays}
        assert codes == {"SOLAR-1", "WIND-1"}

    def test_totals_reconcile(self):
        cfg = DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=200.0)
        ledger = make_entity_ledger("SOLAR-1", [
            (0, 1000.0,
             [cm(0, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 500.0),
              cm(0, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -500.0)],
             1000.0, 1000.0),
            (1, 1000.0,
             [cm(1, "SOLAR-1", CashMovementType.OPERATING_CASHFLOW, 300.0),
              cm(1, "SOLAR-1", CashMovementType.EQUITY_DISTRIBUTION, -400.0)],
             900.0, 900.0),
        ])
        port = PortfolioCashLedger(entities=(ledger,), total_ending_cash_keur=1900.0)
        overlays = build_spv_retained_cash_overlays_from_portfolio_ledger(
            port, config_by_entity={"SOLAR-1": cfg},
        )
        ov = overlays[0]
        assert ov.total_requested_distribution_keur == 900.0
        period_sum_allowed = sum(p.allowed_distribution_keur for p in ov.periods)
        period_sum_retained = sum(p.retained_cash_keur for p in ov.periods)
        assert abs(ov.total_allowed_distribution_keur - period_sum_allowed) < 1e-6
        assert abs(ov.total_retained_cash_keur - period_sum_retained) < 1e-6

    def test_empty_portfolio_returns_empty_tuple(self):
        port = PortfolioCashLedger(entities=(), total_ending_cash_keur=0.0)
        overlays = build_spv_retained_cash_overlays_from_portfolio_ledger(port)
        assert overlays == ()