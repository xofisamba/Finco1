"""Phase 5F tests for UI overlay visibility helpers."""
from __future__ import annotations

import pytest

from domain.portfolio.distribution_constraints.overlay import (
    SPVRetainedCashPeriod,
    SPVRetainedCashOverlay,
)
from domain.portfolio.distribution_constraints.holdco_overlay import (
    HoldCoRetainedCashOverlay,
)
from domain.portfolio.distribution_constraints import (
    DistributionBlockReason,
    DistributionConstraintResult,
)
from app.portfolio_ui_overlay import build_overlay_audit_note
from domain.portfolio.distribution_constraints.result import (
    DistributionConstraintPeriod,
)

from app.portfolio_ui_overlay import (
    build_spv_constraints_table,
    build_holdco_constraints_table,
    build_dist_constraints_table,
    aggregate_spv_warnings,
    aggregate_holdco_warnings,
    summarize_block_reasons,
    has_overlay_warnings,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def make_spv_overlay(entity_code, periods_data):
    """periods_data: list of (period, req, allowed, retained, cash_before, warnings, block_reasons)"""
    periods = []
    for pd_ in periods_data:
        period, req, allowed, retained, cash_before = pd_[:5]
        warnings = pd_[5] if len(pd_) > 5 else ()
        block_reasons = pd_[6] if len(pd_) > 6 else ()
        periods.append(SPVRetainedCashPeriod(
            period=period, entity_code=entity_code,
            requested_distribution_keur=req, allowed_distribution_keur=allowed,
            retained_cash_keur=retained, cash_before_distribution_keur=cash_before,
            warnings=warnings, block_reasons=block_reasons,
        ))
    return SPVRetainedCashOverlay(entity_code=entity_code, periods=tuple(periods))


def make_constraint_result(entity_code, periods_data):
    """periods_data: list of (period, cash_before, req, allowed, retained, block_reasons, warnings)"""
    periods = []
    for pd_ in periods_data:
        period, cb, req, allowed, retained = pd_[:5]
        block_reasons = pd_[5] if len(pd_) > 5 else ()
        warnings = pd_[6] if len(pd_) > 6 else ()
        periods.append(DistributionConstraintPeriod(
            period=period, entity_code=entity_code,
            cash_before_distribution_keur=cb, requested_distribution_keur=req,
            allowed_distribution_keur=allowed, retained_cash_keur=retained,
            block_reasons=block_reasons, warnings=warnings,
        ))
    return DistributionConstraintResult(
        entity_code=entity_code, periods=tuple(periods),
        total_requested_distribution_keur=sum(p.requested_distribution_keur for p in periods),
        total_allowed_distribution_keur=sum(p.allowed_distribution_keur for p in periods),
        total_retained_cash_keur=sum(p.retained_cash_keur for p in periods),
    )


# ── A. build_spv_constraints_table ─────────────────────────────────────────────

class TestBuildSPVConstraintsTable:
    def test_none_returns_none(self):
        assert build_spv_constraints_table(None) is None

    def test_empty_list_returns_none(self):
        assert build_spv_constraints_table([]) is None

    def test_one_overlay_one_row(self):
        ov = make_spv_overlay("SOLAR-1", [(0, 500.0, 400.0, 600.0, 1000.0)])
        df = build_spv_constraints_table([ov])
        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["SPV Code"] == "SOLAR-1"
        assert df.iloc[0]["Total Requested (kEUR)"] == "500"

    def test_delta_restricted_positive_when_constrained(self):
        # req=500, allowed=400 → delta = 100
        ov = make_spv_overlay("SOLAR-1", [(0, 500.0, 400.0, 600.0, 1000.0)])
        df = build_spv_constraints_table([ov])
        assert df is not None
        assert df.iloc[0]["Δ Restricted (kEUR)"] == "100"

    def test_block_reasons_collected(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=0.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=500.0,
            block_reasons=(DistributionBlockReason.MANUAL_LOCKUP,),
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p,))
        df = build_spv_constraints_table([ov])
        assert "MANUAL_LOCKUP" in df.iloc[0]["Block Reasons"]

    def test_warning_count_correct(self):
        p1 = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=400.0,
            retained_cash_keur=600.0, cash_before_distribution_keur=1000.0,
            warnings=("Warning A",),
        )
        p2 = SPVRetainedCashPeriod(
            period=1, entity_code="SOLAR-1",
            requested_distribution_keur=300.0, allowed_distribution_keur=300.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=800.0,
            warnings=(),
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p1, p2))
        df = build_spv_constraints_table([ov])
        assert df.iloc[0]["Warning Count"] == 1


# ── B. build_holdco_constraints_table ─────────────────────────────────────────

class TestBuildHoldcoConstraintsTable:
    def test_none_returns_none(self):
        assert build_holdco_constraints_table(None) is None

    def test_one_period_row(self):
        ov = HoldCoRetainedCashOverlay(
            entity_code="HOLDCO",
            retained_cash_by_period=(100.0,),
            requested_distribution_by_period=(500.0,),
            available_distribution_by_period=(400.0,),
        )
        df = build_holdco_constraints_table(ov)
        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["HoldCo Code"] == "HOLDCO"
        assert df.iloc[0]["Period"] == 0
        assert df.iloc[0]["Requested (kEUR)"] == "500"
        assert df.iloc[0]["Retained (kEUR)"] == "100"
        assert df.iloc[0]["Available (kEUR)"] == "400"

    def test_multiple_periods(self):
        ov = HoldCoRetainedCashOverlay(
            entity_code="HOLDCO",
            retained_cash_by_period=(100.0, 200.0, 150.0),
            requested_distribution_by_period=(500.0, 600.0),
            available_distribution_by_period=(400.0, 400.0),
        )
        df = build_holdco_constraints_table(ov)
        assert df is not None
        assert len(df) == 3  # max(3,2) = 3


# ── C. build_dist_constraints_table ────────────────────────────────────────────

class TestBuildDistConstraintsTable:
    def test_none_returns_none(self):
        assert build_dist_constraints_table(None) is None

    def test_empty_list_returns_none(self):
        assert build_dist_constraints_table([]) is None

    def test_one_period_row(self):
        cr = make_constraint_result("SOLAR-1", [
            (0, 1000.0, 500.0, 400.0, 600.0),
        ])
        df = build_dist_constraints_table([cr])
        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["Entity"] == "SOLAR-1"
        assert df.iloc[0]["Requested (kEUR)"] == "500"
        assert df.iloc[0]["Allowed (kEUR)"] == "400"

    def test_block_reasons_column(self):
        cr = make_constraint_result("SOLAR-1", [
            (0, 500.0, 500.0, 0.0, 500.0, (DistributionBlockReason.MANUAL_LOCKUP,),),
        ])
        df = build_dist_constraints_table([cr])
        assert "MANUAL_LOCKUP" in df.iloc[0]["Block Reasons"]


# ── D. aggregate_spv_warnings ─────────────────────────────────────────────────

class TestAggregateSpvWarnings:
    def test_none_returns_empty(self):
        assert aggregate_spv_warnings(None) == []

    def test_empty_list_returns_empty(self):
        assert aggregate_spv_warnings([]) == []

    def test_warnings_collected(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
            warnings=("Retained cash exceeds minimum",),
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p,))
        result = aggregate_spv_warnings([ov])
        assert len(result) == 1
        assert "SOLAR-1" in result[0]
        assert "Retained cash" in result[0]

    def test_multiple_overlays_warnings_merged(self):
        p1 = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
            warnings=("W1",),
        )
        p2 = SPVRetainedCashPeriod(
            period=0, entity_code="WIND-1",
            requested_distribution_keur=300.0, allowed_distribution_keur=300.0,
            retained_cash_keur=300.0, cash_before_distribution_keur=600.0,
            warnings=("W2",),
        )
        ov1 = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p1,))
        ov2 = SPVRetainedCashOverlay(entity_code="WIND-1", periods=(p2,))
        result = aggregate_spv_warnings([ov1, ov2])
        assert len(result) == 2


# ── E. aggregate_holdco_warnings ──────────────────────────────────────────────

class TestAggregateHoldcoWarnings:
    def test_none_returns_empty(self):
        assert aggregate_holdco_warnings(None) == []

    def test_warnings_returned(self):
        ov = HoldCoRetainedCashOverlay(
            entity_code="HOLDCO",
            retained_cash_by_period=(100.0,),
            requested_distribution_by_period=(500.0,),
            available_distribution_by_period=(400.0,),
            warnings=("Length mismatch",),
        )
        result = aggregate_holdco_warnings(ov)
        assert result == ["Length mismatch"]


# ── F. summarize_block_reasons ─────────────────────────────────────────────────

class TestSummarizeBlockReasons:
    def test_none_returns_empty_dict(self):
        assert summarize_block_reasons(None) == {}

    def test_counts_accumulated(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=0.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=500.0,
            block_reasons=(DistributionBlockReason.MANUAL_LOCKUP, DistributionBlockReason.MINIMUM_CASH_RESERVE),
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p,))
        result = summarize_block_reasons([ov])
        assert result["MANUAL_LOCKUP"] == 1
        assert result["MINIMUM_CASH_RESERVE"] == 1


# ── G. has_overlay_warnings ────────────────────────────────────────────────────

class TestHasOverlayWarnings:
    def test_all_none_false(self):
        assert has_overlay_warnings() is False

    def test_spv_warning_true(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
            warnings=("Warning",),
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p,))
        assert has_overlay_warnings(spv_overlays=[ov]) is True

    def test_spv_block_reason_true(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=0.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=500.0,
            block_reasons=(DistributionBlockReason.MANUAL_LOCKUP,),
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p,))
        assert has_overlay_warnings(spv_overlays=[ov]) is True

    def test_spv_clean_false(self):
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
            warnings=(),
            block_reasons=(),
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p,))
        assert has_overlay_warnings(spv_overlays=[ov]) is False

    def test_constraint_result_with_block_true(self):
        cr = make_constraint_result("SOLAR-1", [
            (0, 500.0, 500.0, 0.0, 500.0, (DistributionBlockReason.MANUAL_LOCKUP,),),
        ])
        assert has_overlay_warnings(constraint_results=[cr]) is True


# ── H. No existing behavior regression ─────────────────────────────────────────

class TestNoRegression:
    def test_existing_portfolio_ui_functions_still_importable(self):
        from app.portfolio_ui import (
            build_portfolio_summary_table,
            build_portfolio_spv_table,
            build_portfolio_warnings_table,
            render_portfolio_summary,
        )
        # None of these should be broken by the new imports
        assert callable(build_portfolio_summary_table)
        assert callable(build_portfolio_spv_table)

    def test_overlay_functions_not_mutating(self):
        # Verify the functions don't mutate their inputs
        p = SPVRetainedCashPeriod(
            period=0, entity_code="SOLAR-1",
            requested_distribution_keur=500.0, allowed_distribution_keur=500.0,
            retained_cash_keur=500.0, cash_before_distribution_keur=1000.0,
            warnings=("W",),
        )
        ov = SPVRetainedCashOverlay(entity_code="SOLAR-1", periods=(p,))
        before = ov.periods[0].warnings
        aggregate_spv_warnings([ov])
        after = ov.periods[0].warnings
        assert before == after  # no mutation