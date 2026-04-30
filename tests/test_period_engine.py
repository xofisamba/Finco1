"""Tests for PeriodEngine - validates semi-annual period generation."""
from datetime import date
import pytest
from domain.period_engine import PeriodEngine, PeriodFrequency, PeriodMeta


class TestPeriodEngineBasics:
    """Basic initialization and property tests."""

    def test_oborovo_configuration(self):
        """Test Oborovo project configuration from Excel."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
            frequency=PeriodFrequency.SEMESTRIAL,
        )

        assert engine.cod == date(2030, 6, 29)
        assert engine.ppa_end == date(2042, 6, 29)
        assert engine.horizon_end == date(2060, 6, 29)

    def test_cod_calculation(self):
        """COD should be 12 months after financial close."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )
        assert engine.cod == date(2030, 6, 29)


class TestPeriodEnginePeriods:
    """Tests for period generation."""

    def test_period_count(self):
        """Should have construction + operation periods across the model horizon."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        periods = engine.periods()
        op_periods = [p for p in periods if p.is_operation]

        assert len(op_periods) >= 59
        assert len(op_periods) <= 61

    def test_first_two_periods_construction(self):
        """First two periods should be construction (Y0-H1, Y0-H2)."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        periods = engine.periods()

        assert periods[0].index == 0
        assert periods[0].is_construction is True
        assert periods[0].is_operation is False
        assert periods[0].period_in_year == 1
        assert periods[0].year_index == 0

        assert periods[1].index == 1
        assert periods[1].is_construction is True
        assert periods[1].is_operation is False
        assert periods[1].period_in_year == 2
        assert periods[1].year_index == 0

    def test_operation_starts_at_excel_boundary_after_cod_stub(self):
        """Near-zero COD stubs should roll to Excel semi-annual boundary."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        op_periods = [p for p in engine.periods() if p.is_operation]
        first_op = op_periods[0]
        assert first_op.index == 2
        assert first_op.start_date == date(2030, 6, 30)
        assert first_op.end_date == date(2030, 12, 31)
        assert first_op.days_in_period == 184
        assert first_op.is_ppa_active is True

    def test_ppa_active_24_periods(self):
        """PPA should be active for approximately 12 years of semi-annual periods."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        periods = engine.periods()
        ppa_periods = [p for p in periods if p.is_ppa_active]

        assert 23 <= len(ppa_periods) <= 25

    def test_period_in_year_sequence(self):
        """Semi-annual periods should alternate 1, 2, 1, 2..."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        periods = engine.periods()
        op_periods = [p for p in periods if p.is_operation]

        for i in range(len(op_periods) - 1):
            curr = op_periods[i]
            nxt = op_periods[i + 1]

            if curr.period_in_year == 1:
                assert nxt.period_in_year == 2
            else:
                assert nxt.period_in_year == 1

    def test_day_fraction_calculation(self):
        """Day fraction should match days divided by the period end year day count."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        periods = engine.periods()

        for p in periods:
            expected_fraction = p.days_in_period / (366.0 if p.is_leap_year else 365.0)
            assert abs(p.day_fraction - expected_fraction) < 0.001

    def test_operation_period_dates_match_excel(self):
        """Operation period end dates and day counts should match Oborovo Excel.

        Excel uses period-end boundary day counts after rolling the 1-day COD
        stub to June 30. The first three operating periods are 184, 181, 184
        days respectively.
        """
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        op_periods = [p for p in engine.periods() if p.is_operation]

        assert op_periods[0].end_date == date(2030, 12, 31)
        assert op_periods[0].days_in_period == 184
        assert op_periods[1].end_date == date(2031, 6, 30)
        assert op_periods[1].days_in_period == 181
        assert op_periods[2].end_date == date(2031, 12, 31)
        assert op_periods[2].days_in_period == 184


class TestPeriodEngineHelpers:
    """Test helper methods."""

    def test_operation_periods(self):
        """operation_periods() returns only operation periods."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        op = engine.operation_periods()

        assert all(p.is_operation for p in op)
        assert all(not p.is_construction for p in op)

    def test_ppa_periods(self):
        """ppa_periods() returns only PPA-active periods."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        ppa = engine.ppa_periods()

        assert all(p.is_ppa_active for p in ppa)
        assert 23 <= len(ppa) <= 25

    def test_period_dates(self):
        """period_dates() returns all end dates."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
        )

        dates = engine.period_dates()

        assert len(dates) >= 61


class TestPeriodEngineAnnual:
    """Test annual frequency."""

    def test_annual_frequency(self):
        """Annual frequency should produce annual periods."""
        engine = PeriodEngine(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=30,
            ppa_years=12,
            frequency=PeriodFrequency.ANNUAL,
        )

        periods = engine.periods()
        op_periods = [p for p in periods if p.is_operation]

        assert 29 <= len(op_periods) <= 65
