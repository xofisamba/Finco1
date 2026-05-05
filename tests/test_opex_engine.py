"""Tests for app/opex_engine.py — OPEX line-item engine."""
from __future__ import annotations

import pytest
from app.opex_engine import (
    CalculationMode,
    OpexSource,
    OpexLineItem,
    OpexScheduleEntry,
    OpexSchedule,
    generate_opex_schedule,
    build_opex_line_items_from_defaults,
    apply_opex_line_items_to_project,
)


class TestGenerateOpexScheduleInflatedFromBase:
    """Inflated-from-base mode: value[year] = base * (1 + rate) ** year."""

    def test_inflated_schedule_grows_with_inflation(self):
        item = OpexLineItem(
            name="Test OPEX",
            category="test",
            base_year_amount_keur=100.0,
            inflation_rate=0.02,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
            source=OpexSource.FORMULA,
        )
        schedule = generate_opex_schedule((item,), horizon_years=5)

        # Year 0: 100 * 1.0 = 100
        assert schedule.total_for_year(0) == pytest.approx(100.0)
        # Year 1: 100 * 1.02 = 102
        assert schedule.total_for_year(1) == pytest.approx(102.0)
        # Year 2: 100 * 1.0404 = 104.04
        assert schedule.total_for_year(2) == pytest.approx(104.04)
        # Year 4: 100 * 1.082432 = 108.24
        assert schedule.total_for_year(4) == pytest.approx(108.2432)

    def test_zero_inflation_is_constant(self):
        item = OpexLineItem(
            name="Fixed Cost",
            category="test",
            base_year_amount_keur=200.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
            source=OpexSource.FORMULA,
        )
        schedule = generate_opex_schedule((item,), horizon_years=3)
        assert schedule.total_for_year(0) == pytest.approx(200.0)
        assert schedule.total_for_year(1) == pytest.approx(200.0)
        assert schedule.total_for_year(2) == pytest.approx(200.0)

    def test_all_entries_are_formula_driven(self):
        item = OpexLineItem(
            name="Operations",
            category="ops",
            base_year_amount_keur=100.0,
            inflation_rate=0.02,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
            source=OpexSource.FORMULA,
        )
        schedule = generate_opex_schedule((item,), horizon_years=3)
        for entry in schedule.entries:
            assert entry.source == OpexSource.FORMULA
            assert not entry.is_override

    def test_no_override_flags_when_all_formula(self):
        item = OpexLineItem(
            name="Test",
            category="test",
            base_year_amount_keur=100.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        schedule = generate_opex_schedule((item,), horizon_years=5)
        assert not schedule.has_manual_overrides
        assert not schedule.has_hardcoded_items


class TestGenerateOpexScheduleManualSchedule:
    """Manual schedule mode: explicit per-year values."""

    def test_manual_schedule_uses_provided_values(self):
        item = OpexLineItem(
            name="Custom OPEX",
            category="test",
            annual_values_keur=(100.0, 110.0, 120.0, 130.0),
            calculation_mode=CalculationMode.MANUAL_SCHEDULE,
            source=OpexSource.MANUAL,
        )
        schedule = generate_opex_schedule((item,), horizon_years=4)
        assert schedule.total_for_year(0) == pytest.approx(100.0)
        assert schedule.total_for_year(1) == pytest.approx(110.0)
        assert schedule.total_for_year(2) == pytest.approx(120.0)
        assert schedule.total_for_year(3) == pytest.approx(130.0)

    def test_manual_schedule_is_flagged_as_override(self):
        item = OpexLineItem(
            name="Custom OPEX",
            category="test",
            annual_values_keur=(100.0, 200.0),
            calculation_mode=CalculationMode.MANUAL_SCHEDULE,
            source=OpexSource.MANUAL,
            override_note="Override based on contract",
        )
        schedule = generate_opex_schedule((item,), horizon_years=2)
        assert schedule.has_manual_overrides
        for entry in schedule.entries:
            assert entry.is_override
            assert entry.source == OpexSource.MANUAL


class TestGenerateOpexScheduleMixed:
    """Mixed mode: inflated base with manual overrides for specific years."""

    def test_mixed_uses_inflated_base_without_override(self):
        item = OpexLineItem(
            name="Mixed OPEX",
            category="test",
            base_year_amount_keur=100.0,
            inflation_rate=0.02,
            calculation_mode=CalculationMode.MIXED,
            manual_overrides_keur=(None, None, 150.0),  # Year 2 overridden
            override_note="Year 3 special",
        )
        schedule = generate_opex_schedule((item,), horizon_years=5)

        # Year 0: no override, use inflated
        assert schedule.total_for_year(0) == pytest.approx(100.0)
        # Year 1: no override, use inflated
        assert schedule.total_for_year(1) == pytest.approx(102.0)
        # Year 2: override to 150.0
        assert schedule.total_for_year(2) == pytest.approx(150.0)
        # Year 3: back to inflated
        assert schedule.total_for_year(3) == pytest.approx(106.1208)
        # Year 4: back to inflated
        assert schedule.total_for_year(4) == pytest.approx(108.2432)

    def test_mixed_override_flagged_correctly(self):
        item = OpexLineItem(
            name="Mixed OPEX",
            category="test",
            base_year_amount_keur=100.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.MIXED,
            manual_overrides_keur=(None, 200.0),  # Year 1 overridden
            override_note="Special year 2",
        )
        schedule = generate_opex_schedule((item,), horizon_years=3)

        year0_entries = [e for e in schedule.entries if e.year_index == 0]
        year1_entries = [e for e in schedule.entries if e.year_index == 1]

        assert not year0_entries[0].is_override
        assert year1_entries[0].is_override
        assert year1_entries[0].override_note == "Special year 2"


class TestHardcodedFlags:
    """Hardcoded items should be flagged for amber UI display."""

    def test_hardcoded_item_sets_flag(self):
        item = OpexLineItem(
            name="Insurance (Hardcoded)",
            category="insurance",
            base_year_amount_keur=300.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
            is_hardcoded=True,
            source=OpexSource.HARDCODED,
            override_note="Manually entered from insurer quote",
        )
        schedule = generate_opex_schedule((item,), horizon_years=2)
        assert schedule.has_hardcoded_items
        for entry in schedule.entries:
            assert entry.source == OpexSource.HARDCODED


class TestMultipleLineItems:
    """Multiple line items should be summed per year."""

    def test_multiple_items_sum_correctly(self):
        item1 = OpexLineItem(
            name="Opex1",
            category="cat1",
            base_year_amount_keur=100.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        item2 = OpexLineItem(
            name="Opex2",
            category="cat2",
            base_year_amount_keur=50.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        schedule = generate_opex_schedule((item1, item2), horizon_years=3)
        assert schedule.total_for_year(0) == pytest.approx(150.0)
        assert schedule.total_for_year(1) == pytest.approx(150.0)
        assert schedule.total_for_year(2) == pytest.approx(150.0)


class TestEmptyLineItems:
    """Empty line items should return empty schedule."""

    def test_empty_line_items_returns_empty_schedule(self):
        schedule = generate_opex_schedule((), horizon_years=5)
        assert schedule.entries == ()
        assert schedule.total_by_year == ()
        assert not schedule.has_manual_overrides
        assert not schedule.has_hardcoded_items


class TestBackwardCompatibility:
    """No line items should preserve legacy/simple OPEX behavior (empty tuple returned)."""

    def test_apply_with_empty_line_items_returns_empty_tuple(self):
        result = apply_opex_line_items_to_project((), horizon_years=10)
        assert result == ()

    def test_build_defaults_solar_returns_items(self):
        items = build_opex_line_items_from_defaults("solar")
        assert len(items) > 0
        names = [i.name for i in items]
        assert "Technical Management (B.01)" in names
        assert "Insurance" in names

    def test_build_defaults_wind_returns_items(self):
        items = build_opex_line_items_from_defaults("wind")
        assert len(items) > 0
        names = [i.name for i in items]
        assert "Technical Management (B.01)" in names

    def test_build_defaults_unknown_technology_returns_empty(self):
        items = build_opex_line_items_from_defaults("unknown_tech")
        assert items == ()


class TestScheduleHelpers:
    """OpexSchedule helper methods."""

    def test_items_for_year(self):
        item = OpexLineItem(
            name="Test",
            category="test",
            base_year_amount_keur=100.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        schedule = generate_opex_schedule((item,), horizon_years=3)
        year1_entries = schedule.items_for_year(1)
        assert len(year1_entries) == 1
        assert year1_entries[0].year_index == 1

    def test_summary_by_category(self):
        item1 = OpexLineItem(
            name="B.01 Technical",
            category="operations",
            base_year_amount_keur=100.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        item2 = OpexLineItem(
            name="Insurance",
            category="insurance",
            base_year_amount_keur=50.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        schedule = generate_opex_schedule((item1, item2), horizon_years=2)
        summary = schedule.summary_by_category(year_index=0)
        assert summary["operations"] == pytest.approx(100.0)
        assert summary["insurance"] == pytest.approx(50.0)
