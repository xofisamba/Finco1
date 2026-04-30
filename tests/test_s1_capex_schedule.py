"""Tests for S1-4: CAPEX cash flow schedule.

This test verifies the blueprint requirement:
- CAPEX is distributed across construction periods per spending_profile
- NOT all deducted at Financial Close (period 0)
- Affects equity IRR timing
"""
import pytest
from datetime import date
from domain.capex.capex_schedule import (
    CapexCashFlowEntry,
    CapexCashFlowSchedule,
    CapexItemWithProfile,
    build_capex_cashflow_schedule,
    aggregate_capex_by_period,
    default_spending_profile,
    total_sculpt_capex,
)


class TestCapexCashFlowEntry:
    """Test CapexCashFlowEntry dataclass."""

    def test_negative_amount_is_outflow(self):
        """Negative amount is marked as outflow."""
        entry = CapexCashFlowEntry(
            period_index=1,
            period_date=date(2027, 6, 30),
            amount_keur=-5_000.0,
            category="epc",
        )
        assert entry.is_outflow is True

    def test_positive_amount_not_outflow(self):
        """Positive amount is not an outflow."""
        entry = CapexCashFlowEntry(
            period_index=1,
            period_date=date(2027, 6, 30),
            amount_keur=1_000.0,  # Positive = refund/inflow
            category="vat_rebate",
        )
        assert entry.is_outflow is False


class TestCapexCashFlowSchedule:
    """Test CapexCashFlowSchedule."""

    def test_total_outflow(self):
        """total_outflow sums all negative entries."""
        schedule = CapexCashFlowSchedule(entries=[
            CapexCashFlowEntry(period_index=0, period_date=date(2026,1,1), amount_keur=-10_000, category="epc"),
            CapexCashFlowEntry(period_index=1, period_date=date(2026,7,1), amount_keur=-5_000, category="epc"),
            CapexCashFlowEntry(period_index=2, period_date=date(2027,1,1), amount_keur=-3_000, category="grid"),
        ])
        assert schedule.total_outflow_keur == -18_000.0

    def test_period_indexes(self):
        """period_indexes returns unique sorted indexes."""
        schedule = CapexCashFlowSchedule(entries=[
            CapexCashFlowEntry(period_index=2, period_date=date(2027,1,1), amount_keur=-1_000, category="epc"),
            CapexCashFlowEntry(period_index=0, period_date=date(2026,1,1), amount_keur=-5_000, category="epc"),
            CapexCashFlowEntry(period_index=2, period_date=date(2027,1,1), amount_keur=-2_000, category="grid"),
        ])
        assert schedule.period_indexes == [0, 2]

    def test_total_for_period(self):
        """total_for_period sums all entries in that period."""
        schedule = CapexCashFlowSchedule(entries=[
            CapexCashFlowEntry(period_index=2, period_date=date(2027,1,1), amount_keur=-1_000, category="epc"),
            CapexCashFlowEntry(period_index=2, period_date=date(2027,1,1), amount_keur=-2_000, category="grid"),
        ])
        assert schedule.total_for_period(2) == -3_000.0
        assert schedule.total_for_period(99) == 0.0  # No entries


class TestCapexItemWithProfile:
    """Test CapexItemWithProfile."""

    def test_amount_for_period(self):
        """amount_for_period = total * fraction."""
        item = CapexItemWithProfile(
            name="epc_contract",
            amount_keur=26_430.0,
            spending_profile={0: 0.0, 1: 0.15, 2: 0.20, 3: 0.20, 4: 0.15, 5: 0.10},
        )
        assert item.amount_for_period(0) == 0.0
        assert item.amount_for_period(1) == 26_430.0 * 0.15
        assert item.amount_for_period(2) == 26_430.0 * 0.20
        assert item.amount_for_period(3) == 26_430.0 * 0.20

    def test_default_zero_for_missing_period(self):
        """Missing period returns 0 (not an error)."""
        item = CapexItemWithProfile(
            name="grid",
            amount_keur=3_300.0,
            spending_profile={4: 1.0},  # Only at period 4 (COD)
        )
        assert item.amount_for_period(0) == 0.0
        assert item.amount_for_period(99) == 0.0


class TestDefaultSpendingProfile:
    """Test default spending profile generation."""

    def test_linear_profile(self):
        """Linear profile distributes evenly."""
        profile = default_spending_profile(total_periods=8, construction_periods=4)
        # 4 periods, 25% each
        assert profile == {0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25}
        assert sum(profile.values()) == 1.0

    def test_front_loaded_profile(self):
        """Front-loaded: more spending early."""
        profile = default_spending_profile(total_periods=8, construction_periods=4, profile_type="front_loaded")
        # Weights: [4, 3, 2, 1] → [0.4, 0.3, 0.2, 0.1]
        assert abs(profile[0] - 0.4) < 0.01
        assert abs(profile[1] - 0.3) < 0.01
        assert abs(profile[2] - 0.2) < 0.01
        assert abs(profile[3] - 0.1) < 0.01
        assert sum(profile.values()) == 1.0

    def test_back_loaded_profile(self):
        """Back-loaded: less spending early."""
        profile = default_spending_profile(total_periods=8, construction_periods=4, profile_type="back_loaded")
        # Weights: [1, 2, 3, 4] → [0.1, 0.2, 0.3, 0.4]
        assert abs(profile[0] - 0.1) < 0.01
        assert abs(profile[3] - 0.4) < 0.01

    def test_zero_construction_periods(self):
        """Zero construction periods returns 100% at period 0."""
        profile = default_spending_profile(total_periods=8, construction_periods=0)
        assert profile == {0: 1.0}


class TestBuildCapexCashFlowSchedule:
    """Test full CAPEX schedule building."""

    def test_build_simple_schedule(self):
        """Build schedule from CAPEX items with spending profiles."""
        # Mock periods
        class MockPeriod:
            def __init__(self, index, start_date):
                self.index = index
                self.start_date = start_date

        periods = [
            MockPeriod(0, date(2026, 1, 1)),
            MockPeriod(1, date(2026, 7, 1)),
            MockPeriod(2, date(2027, 1, 1)),
            MockPeriod(3, date(2027, 7, 1)),
            MockPeriod(4, date(2028, 1, 1)),
        ]

        # Two CAPEX items: EPC (spread) and Grid (at COD)
        epc = CapexItemWithProfile(
            name="epc_contract",
            amount_keur=10_000.0,
            spending_profile={0: 0.2, 1: 0.3, 2: 0.3, 3: 0.2},
        )
        grid = CapexItemWithProfile(
            name="grid_connection",
            amount_keur=3_000.0,
            spending_profile={4: 1.0},  # At COD (period 4)
        )

        schedule = build_capex_cashflow_schedule([epc, grid], periods)

        # Check total outflow
        assert abs(schedule.total_outflow_keur - (-13_000.0)) < 0.01

        # Check periods with CAPEX
        assert 0 in schedule.period_indexes
        assert 4 in schedule.period_indexes

        # EPC period 0: 10,000 * 0.2 = 2,000
        epc_p0 = [e for e in schedule.entries if e.period_index == 0 and e.category == "epc_contract"]
        assert len(epc_p0) == 1
        assert abs(epc_p0[0].amount_keur - (-2_000.0)) < 0.01

        # Grid at period 4: 3,000
        grid_p4 = [e for e in schedule.entries if e.period_index == 4 and e.category == "grid_connection"]
        assert len(grid_p4) == 1
        assert abs(grid_p4[0].amount_keur - (-3_000.0)) < 0.01

    def test_v2_bug_all_at_period_zero(self):
        """Demonstrate v2 bug: all CAPEX at period 0 gives wrong IRR timing."""
        # v2 approach: all CAPEX at FC (period 0)
        v2_total = 60_000.0  # kEUR
        # v3 approach: spread over 4 construction periods
        capex_items = [
            CapexItemWithProfile(name="epc", amount_keur=40_000.0, spending_profile={0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25}),
            CapexItemWithProfile(name="grid", amount_keur=10_000.0, spending_profile={0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25}),
            CapexItemWithProfile(name="idc", amount_keur=10_000.0, spending_profile={0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25}),
        ]

        class MockPeriod:
            def __init__(self, index, start_date):
                self.index = index
                self.start_date = start_date

        periods = [MockPeriod(i, date(2026 + i//2, 1 + 6*(i%2), 1)) for i in range(4)]

        schedule = build_capex_cashflow_schedule(capex_items, periods)

        # v2: all 60,000 at period 0
        v2_outflow_at_0 = -60_000.0

        # v3: distributed
        v3_outflow_at_0 = schedule.total_for_period(0)

        # v2 and v3 should be DIFFERENT
        assert v2_outflow_at_0 != v3_outflow_at_0
        # v3 period 0 outflow is 25% of total = 15,000 (not 60,000)
        assert abs(v3_outflow_at_0 - (-15_000.0)) < 0.01


class TestAggregateCapexByPeriod:
    """Test CAPEX aggregation."""

    def test_aggregate_multiple_items(self):
        """Multiple items in same period are summed."""
        schedule = CapexCashFlowSchedule(entries=[
            CapexCashFlowEntry(period_index=1, period_date=date(2026,7,1), amount_keur=-5_000.0, category="epc"),
            CapexCashFlowEntry(period_index=1, period_date=date(2026,7,1), amount_keur=-2_000.0, category="grid"),
            CapexCashFlowEntry(period_index=2, period_date=date(2027,1,1), amount_keur=-3_000.0, category="epc"),
        ])

        aggregated = aggregate_capex_by_period(schedule)

        assert abs(aggregated[1] - (-7_000.0)) < 0.01  # 5,000 + 2,000
        assert abs(aggregated[2] - (-3_000.0)) < 0.01
        assert 0 not in aggregated  # No CAPEX at period 0


class TestTotalSculptCapex:
    """Test total CAPEX calculation for sculpting."""

    def test_sum_all_items(self):
        """total_sculpt_capex = sum of all item amounts."""
        items = [
            CapexItemWithProfile(name="epc", amount_keur=40_000.0, spending_profile={}),
            CapexItemWithProfile(name="grid", amount_keur=10_000.0, spending_profile={}),
            CapexItemWithProfile(name="idc", amount_keur=10_000.0, spending_profile={}),
        ]
        assert total_sculpt_capex(items) == 60_000.0

    def test_empty_list(self):
        """Empty list returns 0."""
        assert total_sculpt_capex([]) == 0.0


class TestS1Integration:
    """Integration test: CAPEX schedule flows into equity IRR."""

    def test_capex_schedule_for_irr_calculation(self):
        """CAPEX schedule provides cash flows for equity IRR."""
        # Oborovo: 18-month construction, major items
        class MockPeriod:
            def __init__(self, index, start_date):
                self.index = index
                self.start_date = start_date

        periods = [MockPeriod(i, date(2026 + i//2, 1 + 6*(i%2), 1)) for i in range(6)]

        capex_items = [
            CapexItemWithProfile(
                name="epc_contract",
                amount_keur=26_430.0,
                spending_profile={0: 0.1, 1: 0.15, 2: 0.20, 3: 0.20, 4: 0.20, 5: 0.15},
            ),
            CapexItemWithProfile(
                name="grid_connection",
                amount_keur=3_300.0,
                spending_profile={4: 1.0},  # At COD
            ),
            CapexItemWithProfile(
                name="idc",
                amount_keur=1_169.0,
                spending_profile={0: 0.5, 1: 0.5},  # During construction
            ),
        ]

        schedule = build_capex_cashflow_schedule(capex_items, periods)

        # Verify distribution
        for p in range(6):
            outflow = schedule.total_for_period(p)
            if p in [0, 1, 2, 3, 4, 5]:
                assert outflow < 0, f"Period {p} should have negative outflow"

        # Total outflow = sum of all items
        total = sum(e.amount_keur for e in schedule.entries)
        assert abs(total - (-30_899.0)) < 1.0  # 26,430 + 3,300 + 1,169