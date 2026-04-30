"""Tests for OPEX module."""
from datetime import date

import pytest

from domain.inputs import OpexItem, ProjectInputs
from domain.opex.projections import (
    opex_item_amount_at_year,
    opex_year,
    opex_schedule_annual,
    opex_per_mw_y1,
    opex_per_mwh_y1,
    opex_schedule_period,
    opex_breakdown_year,
    total_opex_over_horizon,
    opex_growth_rate,
)
from domain.period_engine import PeriodEngine, PeriodFrequency


class TestOpexCalculation:
    """Test OPEX calculations."""

    @pytest.fixture
    def inputs(self):
        return ProjectInputs.create_default_oborovo()

    def test_opex_y1_total(self, inputs):
        """OPEX Y1 should match the Oborovo input basis within calibration tolerance."""
        opex = opex_year(inputs.opex, 1)
        expected = 1338.08
        assert abs(opex - expected) / expected < 0.002

    def test_opex_items_count(self, inputs):
        """Should have 15 OPEX items."""
        assert len(inputs.opex) == 15

    def test_opex_schedule_annual(self, inputs):
        """Annual OPEX schedule should have 30 years."""
        schedule = opex_schedule_annual(inputs, horizon_years=30)

        assert len(schedule) == 30
        assert 1 in schedule
        assert 30 in schedule

        y1_manual = sum(opex_item_amount_at_year(item, 1) for item in inputs.opex)
        assert abs(schedule[1] - y1_manual) < 0.01

    def test_opex_escalation(self, inputs):
        """OPEX should escalate for most items."""
        y1 = opex_year(inputs.opex, 1)
        y5 = opex_year(inputs.opex, 5)

        assert y5 > y1
        assert y5 / y1 > 1.03

    def test_opex_per_mw(self, inputs):
        """OPEX per MW should be in a reasonable PV-project range."""
        per_mw = opex_per_mw_y1(inputs)
        assert 14 < per_mw < 22

    def test_opex_per_mwh(self, inputs):
        """OPEX per MWh should be in a reasonable range."""
        per_mwh = opex_per_mwh_y1(inputs)
        assert 10 < per_mwh < 25

    def test_opex_breakdown(self, inputs):
        """OPEX breakdown should show all items."""
        breakdown = opex_breakdown_year(inputs, 1)

        assert len(breakdown) == 15
        assert "Technical Management" in breakdown
        assert "Insurance" in breakdown
        assert abs(breakdown["Technical Management"] - 198.0) < 0.01

    def test_opex_item_step_change_is_persistent_new_base(self):
        """Step changes should persist from the step year onward with inflation."""
        item = OpexItem(
            name="Synthetic stepped OpEx",
            y1_amount_keur=100.0,
            annual_inflation=0.02,
            step_changes=((3, 80.0),),
        )

        assert opex_item_amount_at_year(item, 1) == 100.0
        assert abs(opex_item_amount_at_year(item, 2) - 102.0) < 0.01
        assert opex_item_amount_at_year(item, 3) == 80.0
        assert abs(opex_item_amount_at_year(item, 4) - 81.6) < 0.01
        assert abs(opex_item_amount_at_year(item, 5) - 83.232) < 0.01

    def test_opex_growth_rate(self, inputs):
        """Average OPEX growth rate should remain positive."""
        rate = opex_growth_rate(inputs, start_year=1, end_year=10)
        assert 0.01 < rate < 0.025


class TestOpexPeriodSchedule:
    """Test semi-annual period OPEX schedule."""

    @pytest.fixture
    def inputs(self):
        return ProjectInputs.create_default_oborovo()

    @pytest.fixture
    def engine(self):
        return PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
            frequency=PeriodFrequency.SEMESTRIAL,
        )

    def test_period_schedule_length(self, inputs, engine):
        """Period schedule should match engine periods."""
        schedule = opex_schedule_period(inputs, engine)
        assert len(schedule) == len(engine.periods())

    def test_construction_periods_zero_opex(self, inputs, engine):
        """Construction periods should have 0 OPEX."""
        schedule = opex_schedule_period(inputs, engine)
        assert schedule[0] == 0.0
        assert schedule[1] == 0.0

    def test_operation_periods_positive_opex(self, inputs, engine):
        """Operation periods should have positive OPEX."""
        schedule = opex_schedule_period(inputs, engine)
        op_values = [v for k, v in schedule.items() if k >= 2 and v > 0]
        assert len(op_values) >= 59

    def test_y1_periods_sum_to_y1_annual_after_excel_stub_roll(self, inputs, engine):
        """Y1 period OpEx should sum to Y1 annual under Excel day-count convention."""
        schedule = opex_schedule_period(inputs, engine)
        y1_annual = opex_year(inputs.opex, 1)

        period_2 = schedule[2]
        period_3 = schedule[3]
        sum_periods = period_2 + period_3
        assert abs(sum_periods - y1_annual) < 1.0

    def test_total_opex_undiscounted(self, inputs):
        """Total undiscounted OPEX should be sum of annual."""
        total = total_opex_over_horizon(inputs, horizon_years=30)
        annual_sum = sum(opex_year(inputs.opex, y) for y in range(1, 31))
        assert abs(total - annual_sum) < 0.01

    def test_total_opex_discounted(self, inputs):
        """Total discounted OPEX should be less than undiscounted."""
        total_undiscounted = total_opex_over_horizon(inputs, horizon_years=30, discount_rate=0.0)
        total_discounted = total_opex_over_horizon(inputs, horizon_years=30, discount_rate=0.08)
        assert total_discounted < total_undiscounted
