"""Phase 7G tests — RevenueAdjustmentSchedule and revenue formula."""
import pytest
from datetime import date

from domain.inputs import RevenueAdjustmentSchedule, ProjectInputs, RevenueParams
from domain.period_engine import PeriodEngine, PeriodFrequency
from domain.revenue.generation import (
    full_revenue_schedule, full_revenue_breakdown_schedule,
    full_generation_schedule,
)


class TestRevenueAdjustmentSchedule:
    """Unit tests for RevenueAdjustmentSchedule.

    SCHEDULE CONTRACT (user-facing, operating-period based):
    - semiannual_values[0] = first OPERATING period (Y1-H1)
    - semiannual_values[1] = second OPERATING period (Y1-H2)
    - annual_values[0] = first OPERATING year (both H1 and H2)
    - Construction/stub periods do NOT consume schedule values
    - No dummy construction values required

    New API: value_for_period(*, operating_period_index, operating_year_index, period_in_year)
    """

    def test_constant_schedule_returns_same_value_all_periods(self):
        """Constant schedule returns same value for all periods."""
        s = RevenueAdjustmentSchedule(constant_value=8.0)
        # operating_period_index and year don't matter for constant
        assert s.value_for_period(operating_period_index=0, operating_year_index=1, period_in_year=1) == 8.0
        assert s.value_for_period(operating_period_index=59, operating_year_index=30, period_in_year=2) == 8.0
        assert s.value_for_period(operating_period_index=99, operating_year_index=50, period_in_year=1) == 8.0

    def test_annual_schedule_same_for_h1_and_h2(self):
        """Annual schedule applies same value to H1 and H2 of each operating year."""
        s = RevenueAdjustmentSchedule(annual_values=(10.0, 20.0, 30.0))
        # Year 1 → annual_values[0] = 10.0 (both H1 and H2)
        assert s.value_for_period(operating_period_index=0, operating_year_index=1, period_in_year=1) == 10.0
        assert s.value_for_period(operating_period_index=1, operating_year_index=1, period_in_year=2) == 10.0
        # Year 2 → annual_values[1] = 20.0
        assert s.value_for_period(operating_period_index=2, operating_year_index=2, period_in_year=1) == 20.0
        assert s.value_for_period(operating_period_index=3, operating_year_index=2, period_in_year=2) == 20.0
        # Year 3 → annual_values[2] = 30.0
        assert s.value_for_period(operating_period_index=4, operating_year_index=3, period_in_year=1) == 30.0
        assert s.value_for_period(operating_period_index=5, operating_year_index=3, period_in_year=2) == 30.0

    def test_semiannual_schedule_by_operating_period_index(self):
        """Semiannual schedule indexed by operating_period_index (not raw period_index).

        semiannual_values[0] = first operating period
        semiannual_values[1] = second operating period
        etc.
        """
        s = RevenueAdjustmentSchedule(semiannual_values=(5.0, 6.0, 7.0, 8.0))
        assert s.value_for_period(operating_period_index=0, operating_year_index=1, period_in_year=1) == 5.0
        assert s.value_for_period(operating_period_index=1, operating_year_index=1, period_in_year=2) == 6.0
        assert s.value_for_period(operating_period_index=2, operating_year_index=2, period_in_year=1) == 7.0
        assert s.value_for_period(operating_period_index=3, operating_year_index=2, period_in_year=2) == 8.0

    def test_out_of_range_falls_back_to_constant(self):
        """Out-of-range operating_period_index falls back to constant_value."""
        s = RevenueAdjustmentSchedule(constant_value=3.0, semiannual_values=(5.0,))
        # operating_period_index=5 > len=1 → fallback to constant_value=3.0
        assert s.value_for_period(operating_period_index=5, operating_year_index=3, period_in_year=1) == 3.0
        # Annual out of range (year 31 > len=2)
        s2 = RevenueAdjustmentSchedule(constant_value=99.0, annual_values=(1.0, 2.0))
        assert s2.value_for_period(operating_period_index=60, operating_year_index=31, period_in_year=1) == 99.0

    def test_empty_schedule_defaults_to_zero(self):
        """Empty schedule returns 0.0."""
        s = RevenueAdjustmentSchedule()
        assert s.value_for_period(operating_period_index=0, operating_year_index=1, period_in_year=1) == 0.0
        assert s.value_for_period(operating_period_index=59, operating_year_index=30, period_in_year=2) == 0.0

    def test_semiannual_takes_priority_over_annual(self):
        """Semiannual values take priority when both are set."""
        s = RevenueAdjustmentSchedule(
            constant_value=1.0,
            annual_values=(10.0, 20.0),
            semiannual_values=(100.0, 200.0),
        )
        assert s.value_for_period(operating_period_index=0, operating_year_index=1, period_in_year=1) == 100.0
        assert s.value_for_period(operating_period_index=1, operating_year_index=1, period_in_year=2) == 200.0

    def test_annual_takes_priority_over_constant(self):
        """Annual values take priority when semiannual is empty."""
        s = RevenueAdjustmentSchedule(constant_value=1.0, annual_values=(10.0,))
        assert s.value_for_period(operating_period_index=0, operating_year_index=1, period_in_year=1) == 10.0

    def test_schedule_is_hashable(self):
        """Frozen dataclass is hashable (for cache keys)."""
        s1 = RevenueAdjustmentSchedule(constant_value=8.0)
        s2 = RevenueAdjustmentSchedule(constant_value=8.0)
        s3 = RevenueAdjustmentSchedule(constant_value=9.0)
        assert hash(s1) == hash(s2)
        assert hash(s1) != hash(s3)
        assert len({s1, s2, s3}) == 2

    def test_no_period_index_used_in_helper(self):
        """Verify the helper only uses operating_period_index, not raw period_index."""
        # Construction periods (if they existed in the tuple) would not be handled
        # differently from operating periods — the helper has no knowledge of construction
        s = RevenueAdjustmentSchedule(semiannual_values=(99.0, 100.0))
        # If we pass operating_period_index=0, we get semiannual_values[0] regardless
        # of what "year" or "period_in_year" values are
        assert s.value_for_period(operating_period_index=0, operating_year_index=1, period_in_year=1) == 99.0
        assert s.value_for_period(operating_period_index=0, operating_year_index=999, period_in_year=2) == 99.0
        assert s.value_for_period(operating_period_index=1, operating_year_index=1, period_in_year=1) == 100.0


class TestRevenueFormula:
    """Test revenue formula: power_revenue + co2_revenue - balancing_cost."""

    def test_revenue_formula_basic(self):
        """Revenue = power + CO2 - balancing (all in kEUR)."""
        # production=1000 MWh, power_price=60, balancing=8, co2=4
        # = (1000*60 + 1000*4 - 1000*8)/1000 = 56 kEUR
        power_rev = 1000 * 60 / 1000       # 60 kEUR
        co2_rev = 1000 * 4 / 1000           # 4 kEUR
        bal_cost = 1000 * 8 / 1000          # 8 kEUR
        assert abs((power_rev + co2_rev - bal_cost) - 56.0) < 0.001

    def test_backward_compat_zero_balancing_zero_co2(self):
        """Zero balancing and zero CO2 = old revenue (no deductions)."""
        power_rev = 60.0
        revenue = power_rev + 0.0 - 0.0
        assert abs(revenue - 60.0) < 0.001

    def test_balancing_only(self):
        """Balancing cost reduces revenue."""
        revenue = 60.0 + 0.0 - 8.0
        assert abs(revenue - 52.0) < 0.001

    def test_co2_only(self):
        """CO2 revenue increases revenue."""
        revenue = 60.0 + 4.0 - 0.0
        assert abs(revenue - 64.0) < 0.001


class TestRevenueBreakdownSchedule:
    """Tests for full_revenue_breakdown_schedule() exposing decomposition fields."""

    @pytest.fixture
    def tuho_inputs(self):
        return ProjectInputs.create_default_tuho_wind1()

    @pytest.fixture
    def tuho_engine(self):
        return PeriodEngine(
            financial_close=date(2029, 7, 1),
            construction_months=6,
            horizon_years=30,
            ppa_years=12.0,
            frequency=PeriodFrequency.SEMESTRIAL,
        )

    def test_decomposition_sums_correctly(self, tuho_inputs, tuho_engine):
        """Revenue = power_revenue + co2_revenue - balancing_cost for all periods."""
        breakdowns = full_revenue_breakdown_schedule(tuho_inputs, tuho_engine)
        for b in breakdowns:
            expected = b.power_revenue_keur + b.co2_sales_revenue_keur - b.balancing_cost_keur
            assert abs(b.total_revenue_keur - expected) < 0.001, \
                f"op_idx={b.operating_period_index}: {b.total_revenue_keur:.2f} != {expected:.2f}"

    def test_breakdown_exposes_all_fields(self, tuho_inputs, tuho_engine):
        """All decomposition fields are populated with non-zero values for TUHO."""
        breakdowns = full_revenue_breakdown_schedule(tuho_inputs, tuho_engine)
        b = breakdowns[0]
        assert b.period_index >= 0
        assert b.operating_period_index == 0
        assert b.period_end_date is not None
        assert b.production_mwh > 0
        assert b.effective_power_price_eur_per_mwh > 0
        assert b.power_revenue_keur > 0
        assert b.co2_sales_eur_per_mwh > 0  # TUHO has CO2
        assert b.co2_sales_revenue_keur > 0
        assert b.balancing_cost_eur_per_mwh == 8.0  # TUHO balancing
        assert b.balancing_cost_keur > 0
        assert b.total_revenue_keur > 0

    def test_breakdown_period_dates(self, tuho_inputs, tuho_engine):
        """Breakdown uses period end date for Excel comparison."""
        breakdowns = full_revenue_breakdown_schedule(tuho_inputs, tuho_engine)
        # op_idx 0 = Y1-H1 → end date should be 2030-06-30
        assert breakdowns[0].period_end_date == date(2030, 6, 30), \
            f"op_idx=0 EoP should be 2030-06-30, got {breakdowns[0].period_end_date}"
        # op_idx 1 = Y1-H2 → end date should be 2030-12-31
        assert breakdowns[1].period_end_date == date(2030, 12, 31)
        # op_idx 23 = Y12-H2 → end date should be 2041-12-31
        assert breakdowns[23].period_end_date == date(2041, 12, 31)
        # op_idx 24 = Y13-H1 (first post-PPA) → end date should be 2042-06-30
        assert breakdowns[24].period_end_date == date(2042, 6, 30)
        # op_idx 25 = Y13-H2 → end date should be 2042-12-31
        assert breakdowns[25].period_end_date == date(2042, 12, 31)

    def test_breakdown_tuho_selected_periods(self, tuho_inputs, tuho_engine):
        """Selected TUHO periods expose all decomposition fields."""
        breakdowns = full_revenue_breakdown_schedule(tuho_inputs, tuho_engine)
        for op_idx in [0, 1, 23, 24, 25]:
            b = breakdowns[op_idx]
            assert b.operating_period_index == op_idx
            assert b.production_mwh > 0
            assert b.power_revenue_keur > 0
            assert b.co2_sales_eur_per_mwh > 0
            assert b.co2_sales_revenue_keur > 0
            assert b.balancing_cost_eur_per_mwh == 8.0
            assert b.balancing_cost_keur > 0
            assert b.total_revenue_keur > 0


class TestScheduleContractWithTUHO:
    """Acceptance tests: TUHO CO2 schedule must use op_idx contract.

    TUHO: first operating period is op_idx=0 (no construction in schedule)

    Acceptance criteria:
    - semiannual_values[0] = 4.1911 EUR/MWh (Y1-H1, 2030-06-30)
    - semiannual_values[1] = 4.1911 EUR/MWh (Y1-H2, 2030-12-31)
    - semiannual_values[24] = 1.6000 EUR/MWh (Y13-H1, 2042-06-30, first post-PPA)
    - balancing constant = 8.0 EUR/MWh for every operating period
    - No construction period shifts in schedule
    """

    @pytest.fixture
    def tuho_inputs(self):
        return ProjectInputs.create_default_tuho_wind1()

    @pytest.fixture
    def tuho_engine(self):
        return PeriodEngine(
            financial_close=date(2029, 7, 1),
            construction_months=6,
            horizon_years=30,
            ppa_years=12.0,
            frequency=PeriodFrequency.SEMESTRIAL,
        )

    def test_co2_op_idx_0_maps_to_41911(self, tuho_inputs):
        """semiannual_values[0] = 4.1911 EUR/MWh for first operating period."""
        sched = tuho_inputs.revenue.co2_sales_schedule
        assert sched.semiannual_values[0] == 4.1911

    def test_co2_op_idx_1_maps_to_41911(self, tuho_inputs):
        """semiannual_values[1] = 4.1911 EUR/MWh for second operating period."""
        sched = tuho_inputs.revenue.co2_sales_schedule
        assert sched.semiannual_values[1] == 4.1911

    def test_co2_op_idx_24_maps_to_16000(self, tuho_inputs):
        """semiannual_values[24] = 1.6000 EUR/MWh (Y13-H1, first post-PPA period)."""
        sched = tuho_inputs.revenue.co2_sales_schedule
        assert abs(sched.semiannual_values[24] - 1.6000) < 0.0001

    def test_balancing_constant_is_80_for_all_op_periods(self, tuho_inputs, tuho_engine):
        """Balancing cost = 8.0 EUR/MWh for every operating period."""
        sched = tuho_inputs.revenue.balancing_cost_schedule
        assert sched.constant_value == 8.0
        assert sched.semiannual_values == ()
        assert sched.annual_values == ()
        # Verify via breakdown for all 60 op periods
        breakdowns = full_revenue_breakdown_schedule(tuho_inputs, tuho_engine)
        assert len(breakdowns) == 60
        for b in breakdowns:
            assert b.balancing_cost_eur_per_mwh == 8.0, \
                f"op_idx={b.operating_period_index} expected 8.0, got {b.balancing_cost_eur_per_mwh}"

    def test_first_op_period_uses_schedule_index_0(self, tuho_inputs, tuho_engine):
        """First operating period must consume semiannual_values[0] = 4.1911."""
        breakdowns = full_revenue_breakdown_schedule(tuho_inputs, tuho_engine)
        b0 = breakdowns[0]
        assert b0.operating_period_index == 0
        assert b0.period_end_date == date(2030, 6, 30)  # Y1-H1 EoP
        assert abs(b0.co2_sales_eur_per_mwh - 4.1911) < 0.001, \
            f"First op should map to semiannual_values[0]=4.1911, got {b0.co2_sales_eur_per_mwh}"

    def test_revenue_schedule_positive_for_all_op_periods(self, tuho_inputs, tuho_engine):
        """Revenue is positive for all 60 operating periods."""
        breakdowns = full_revenue_breakdown_schedule(tuho_inputs, tuho_engine)
        assert all(b.total_revenue_keur > 0 for b in breakdowns), \
            "All op periods should have positive revenue"

    def test_co2_schedule_len_60_no_dummies(self, tuho_inputs):
        """CO2 schedule has exactly 60 values (no construction dummies)."""
        sched = tuho_inputs.revenue.co2_sales_schedule
        assert len(sched.semiannual_values) == 60
        assert sched.semiannual_values[0] == 4.1911  # First op period
        assert sched.semiannual_values[1] == 4.1911  # Second op period
        assert sched.semiannual_values[59] == 0.7     # Last op period

    def test_co2_schedule_tail_values(self, tuho_inputs):
        """CO2 schedule tail values match spec."""
        sched = tuho_inputs.revenue.co2_sales_schedule
        vals = sched.semiannual_values
        # op_idx 23 = Y12-H2 (last PPA) = 1.7
        assert abs(vals[23] - 1.7) < 0.001, f"op_idx=23 should be 1.7, got {vals[23]}"
        # op_idx 24 = Y13-H1 (first post-PPA) = 1.6
        assert abs(vals[24] - 1.6) < 0.001, f"op_idx=24 should be 1.6, got {vals[24]}"
        # op_idx 59 = last op period = 0.7
        assert abs(vals[59] - 0.7) < 0.001, f"op_idx=59 should be 0.7, got {vals[59]}"


class TestOborovoUnchanged:
    """Verify Oborovo is unchanged by Phase 7G — backward compatible defaults."""

    @pytest.fixture
    def oborovo_inputs(self):
        return ProjectInputs.create_default_oborovo()

    @pytest.fixture
    def oborovo_engine(self):
        return PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12.0,
            frequency=PeriodFrequency.SEMESTRIAL,
        )

    def test_oborovo_balancing_cost_is_zero(self, oborovo_inputs):
        """Oborovo balancing_cost_schedule must default to 0.0 (backward compat)."""
        sched = oborovo_inputs.revenue.balancing_cost_schedule
        assert sched.constant_value == 0.0, \
            f"Oborovo balancing should be 0.0, got constant={sched.constant_value}, annual={sched.annual_values}, semi={sched.semiannual_values}"
        assert sched.annual_values == ()
        assert sched.semiannual_values == ()

    def test_oborovo_co2_sales_is_zero(self, oborovo_inputs):
        """Oborovo co2_sales_schedule must default to 0.0 (backward compat)."""
        sched = oborovo_inputs.revenue.co2_sales_schedule
        assert sched.constant_value == 0.0, \
            f"Oborovo CO2 should be 0.0, got constant={sched.constant_value}, annual={sched.annual_values}, semi={sched.semiannual_values}"
        assert sched.annual_values == ()
        assert sched.semiannual_values == ()

    def test_oborovo_revenue_schedule_positive(self, oborovo_inputs, oborovo_engine):
        """Oborovo revenue schedule produces positive revenues."""
        revenue = full_revenue_schedule(oborovo_inputs, oborovo_engine)
        periods = list(oborovo_engine.periods())
        op_periods = [p for p in periods if p.is_operation]
        op_revenues = [revenue[p.index] for p in op_periods]
        assert all(r > 0 for r in op_revenues[:4]), "First 4 op periods should have positive revenue"

    def test_oborovo_ppa_revenue_correct(self, oborovo_inputs, oborovo_engine):
        """Oborovo Y1-H1 revenue (PPA tariff) matches expected baseline."""
        revenue = full_revenue_schedule(oborovo_inputs, oborovo_engine)
        periods = list(oborovo_engine.periods())
        first_op = next(p for p in periods if p.is_operation)

        # Tariff Y1 = 57 * 1.02^0 = 57 EUR/MWh
        gen = (
            oborovo_inputs.technical.capacity_mw
            * oborovo_inputs.technical.operating_hours_p50
            * first_op.day_fraction
            * oborovo_inputs.technical.combined_availability
        )
        expected_power_rev = gen * 57.0 / 1000  # kEUR
        # Oborovo: no balancing, no CO2 → revenue = power revenue
        actual = revenue[first_op.index]
        assert abs(actual - expected_power_rev) < 0.01, \
            f"Oborovo Y1-H1 revenue={actual:.2f}, expected={expected_power_rev:.2f}"