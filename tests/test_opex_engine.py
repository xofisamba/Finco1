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

    def test_summary_by_category_uses_entry_category_field(self):
        """summary_by_category groups by entry.category, not by parsing line_item_name."""
        # Custom name that does NOT contain any known category keyword
        item1 = OpexLineItem(
            name="PremiumSupport Package",
            category="operations",
            base_year_amount_keur=100.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        # Another custom name, different category
        item2 = OpexLineItem(
            name="AssetProtection Plan",
            category="insurance",
            base_year_amount_keur=50.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        schedule = generate_opex_schedule((item1, item2), horizon_years=2)
        summary = schedule.summary_by_category(year_index=0)
        # Groups by category field even though names don't contain "Insurance" or "operations"
        assert summary["operations"] == pytest.approx(100.0)
        assert summary["insurance"] == pytest.approx(50.0)

    def test_items_by_category_uses_entry_category_field(self):
        """items_by_category filters by entry.category, not by substring match."""
        item1 = OpexLineItem(
            name="Management Fee",
            category="operations",
            base_year_amount_keur=200.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        item2 = OpexLineItem(
            name="Asset Coverage",
            category="insurance",
            base_year_amount_keur=75.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        schedule = generate_opex_schedule((item1, item2), horizon_years=3)

        ops_entries = schedule.items_by_category("operations", year_index=0)
        assert len(ops_entries) == 1
        assert ops_entries[0].line_item_name == "Management Fee"
        assert ops_entries[0].category == "operations"

        ins_entries = schedule.items_by_category("insurance", year_index=0)
        assert len(ins_entries) == 1
        assert ins_entries[0].line_item_name == "Asset Coverage"
        assert ins_entries[0].category == "insurance"

    def test_manual_overrides_none_means_no_override(self):
        """None in manual_overrides_keur means no override; a float means override."""
        item = OpexLineItem(
            name="Test Mixed",
            category="test",
            base_year_amount_keur=100.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.MIXED,
            manual_overrides_keur=(50.0, None, 200.0),  # Y0=50 (override), Y1=None (base), Y2=200 (override)
        )
        schedule = generate_opex_schedule((item,), horizon_years=3)

        year0_entries = [e for e in schedule.entries if e.year_index == 0]
        year1_entries = [e for e in schedule.entries if e.year_index == 1]
        year2_entries = [e for e in schedule.entries if e.year_index == 2]

        # Year 0: override to 50
        assert year0_entries[0].is_override is True
        assert year0_entries[0].value_keur == 50.0
        # Year 1: None → use base (100)
        assert year1_entries[0].is_override is False
        assert year1_entries[0].value_keur == 100.0
        # Year 2: override to 200
        assert year2_entries[0].is_override is True
        assert year2_entries[0].value_keur == 200.0

        # Only Y0 and Y2 are flagged as overrides (Y1 is not)
        assert schedule.has_manual_overrides is True

    def test_manual_overrides_all_none_no_override_flags(self):
        """All-None manual_overrides_keur means no overrides at all."""
        item = OpexLineItem(
            name="Test Mixed None",
            category="test",
            base_year_amount_keur=100.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.MIXED,
            manual_overrides_keur=(None, None, None),  # All None = no overrides
        )
        schedule = generate_opex_schedule((item,), horizon_years=3)
        # All entries use base value, no override flags
        for entry in schedule.entries:
            assert entry.is_override is False
        assert schedule.has_manual_overrides is False

    def test_schedule_entry_has_category_field(self):
        """OpexScheduleEntry.category is copied from OpexLineItem.category."""
        item = OpexLineItem(
            name="Some Custom Name",
            category="environmental_social",
            base_year_amount_keur=42.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
        )
        schedule = generate_opex_schedule((item,), horizon_years=1)
        entry = schedule.entries[0]
        assert entry.category == "environmental_social"
        assert entry.line_item_name == "Some Custom Name"


class TestHasManualOverrides:
    """OpexLineItem.has_manual_overrides() — must return True only when at least one override is not None."""

    def test_empty_tuple_is_false(self):
        item = OpexLineItem(
            name="Test",
            category="test",
            base_year_amount_keur=100.0,
            manual_overrides_keur=(),
        )
        assert item.has_manual_overrides() is False

    def test_all_none_is_false(self):
        item = OpexLineItem(
            name="Test",
            category="test",
            base_year_amount_keur=100.0,
            manual_overrides_keur=(None, None),
        )
        assert item.has_manual_overrides() is False

    def test_one_non_none_is_true(self):
        item = OpexLineItem(
            name="Test",
            category="test",
            base_year_amount_keur=100.0,
            manual_overrides_keur=(None, 100.0),
        )
        assert item.has_manual_overrides() is True

    def test_is_formula_driven_true_when_all_overrides_none(self):
        """is_formula_driven must stay True when source=FORMULA and all overrides are None."""
        item = OpexLineItem(
            name="Test",
            category="test",
            base_year_amount_keur=100.0,
            source=OpexSource.FORMULA,
            manual_overrides_keur=(None, None, None),
        )
        assert item.has_manual_overrides() is False
        assert item.is_formula_driven() is True


class TestApplyOpexLineItemsToProject:
    """Integration tests for apply_opex_line_items_to_project()."""

    def test_empty_line_items_returns_empty_tuple(self):
        """Empty tuple → empty tuple (caller falls back to legacy path)."""
        result = apply_opex_line_items_to_project((), horizon_years=5)
        assert result == ()

    def test_single_item_annual_totals(self):
        """Single formula item produces correct inflated totals."""
        item = OpexLineItem(
            name="Management",
            category="operations",
            base_year_amount_keur=100.0,
            inflation_rate=0.02,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
            source=OpexSource.FORMULA,
        )
        result = apply_opex_line_items_to_project((item,), horizon_years=3)
        assert len(result) == 3
        assert result[0] == pytest.approx(100.0)
        assert result[1] == pytest.approx(102.0)
        assert result[2] == pytest.approx(104.04)

    def test_multiple_items_sum_correctly(self):
        """Multiple line items are summed per year."""
        item1 = OpexLineItem(
            name="Insurance", category="insurance",
            base_year_amount_keur=200.0, inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
            source=OpexSource.FORMULA,
        )
        item2 = OpexLineItem(
            name="Operations", category="operations",
            base_year_amount_keur=300.0, inflation_rate=0.0,
            calculation_mode=CalculationMode.INFLATED_FROM_BASE,
            source=OpexSource.FORMULA,
        )
        result = apply_opex_line_items_to_project((item1, item2), horizon_years=1)
        assert result[0] == pytest.approx(500.0)

    def test_manual_schedule_item_respected(self):
        """MANUAL_SCHEDULE item uses its explicit annual values."""
        item = OpexLineItem(
            name="Contingency",
            category="other",
            base_year_amount_keur=0.0,
            inflation_rate=0.0,
            calculation_mode=CalculationMode.MANUAL_SCHEDULE,
            annual_values_keur=(150.0, 200.0, 180.0),
            source=OpexSource.MANUAL,
        )
        result = apply_opex_line_items_to_project((item,), horizon_years=3)
        assert result[0] == pytest.approx(150.0)
        assert result[1] == pytest.approx(200.0)
        assert result[2] == pytest.approx(180.0)


class TestAdvancedOpexWarnings:
    """Tests for _advanced_opex_warnings helper in ui_runner."""

    def test_no_items_no_warning(self):
        from app.ui_runner import _advanced_opex_warnings
        assert _advanced_opex_warnings(None) == []
        assert _advanced_opex_warnings(()) == []

    def test_formula_only_items_no_warning(self):
        from app.ui_runner import _advanced_opex_warnings
        from app.opex_engine import OpexLineItem, OpexSource, CalculationMode
        items = (
            OpexLineItem(
                name="Insurance", category="insurance",
                base_year_amount_keur=200.0, inflation_rate=0.0,
                calculation_mode=CalculationMode.INFLATED_FROM_BASE,
                source=OpexSource.FORMULA,
            ),
        )
        assert _advanced_opex_warnings(items) == []

    def test_manual_source_triggers_warning(self):
        from app.ui_runner import _advanced_opex_warnings
        from app.opex_engine import OpexLineItem, OpexSource, CalculationMode
        items = (
            OpexLineItem(
                name="Insurance", category="insurance",
                base_year_amount_keur=200.0, inflation_rate=0.0,
                calculation_mode=CalculationMode.MANUAL_SCHEDULE,
                annual_values_keur=(200.0,),
                source=OpexSource.MANUAL,
            ),
        )
        warnings = _advanced_opex_warnings(items)
        assert len(warnings) == 1
        assert "manual or hardcoded" in warnings[0]

    def test_hardcoded_flag_triggers_warning(self):
        from app.ui_runner import _advanced_opex_warnings
        from app.opex_engine import OpexLineItem, OpexSource, CalculationMode
        items = (
            OpexLineItem(
                name="Insurance", category="insurance",
                base_year_amount_keur=200.0, inflation_rate=0.0,
                calculation_mode=CalculationMode.INFLATED_FROM_BASE,
                source=OpexSource.FORMULA,
                is_hardcoded=True,
            ),
        )
        warnings = _advanced_opex_warnings(items)
        assert len(warnings) == 1
        assert "manual or hardcoded" in warnings[0]

    def test_both_manual_and_hardcoded_one_warning(self):
        from app.ui_runner import _advanced_opex_warnings
        from app.opex_engine import OpexLineItem, OpexSource, CalculationMode
        items = (
            OpexLineItem(
                name="Insurance", category="insurance",
                base_year_amount_keur=200.0, inflation_rate=0.0,
                calculation_mode=CalculationMode.MANUAL_SCHEDULE,
                annual_values_keur=(200.0,),
                source=OpexSource.MANUAL,
                is_hardcoded=True,
            ),
        )
        # Should still produce exactly one warning, not two
        warnings = _advanced_opex_warnings(items)
        assert len(warnings) == 1


class TestWaterfallCoreAdvancedOpex:
    """Integration tests for waterfall_core with advanced_opex_line_items."""

    def test_none_advanced_opex_uses_legacy_path(self):
        """advanced_opex_line_items=None → legacy OpexItem path used."""
        from app.project_factories import create_default_solar_project
        from domain.period_engine import PeriodEngine
        from app.waterfall_core import run_waterfall_v3_core
        proj = create_default_solar_project()
        engine = PeriodEngine(
            financial_close=proj.info.financial_close,
            construction_months=proj.info.construction_months,
            horizon_years=proj.info.horizon_years,
            ppa_years=proj.revenue.ppa_term_years,
        )
        # No crash, legacy path used
        result = run_waterfall_v3_core(
            inputs=proj,
            engine=engine,
            rate_per_period=0.02825,
            tenor_periods=28,
            advanced_opex_line_items=None,
        )
        assert result is not None

    def test_empty_tuple_falls_back_to_legacy(self):
        """Empty tuple → legacy path (no crash)."""
        from app.project_factories import create_default_solar_project
        from domain.period_engine import PeriodEngine
        from app.waterfall_core import run_waterfall_v3_core
        proj = create_default_solar_project()
        engine = PeriodEngine(
            financial_close=proj.info.financial_close,
            construction_months=proj.info.construction_months,
            horizon_years=proj.info.horizon_years,
            ppa_years=proj.revenue.ppa_term_years,
        )
        result = run_waterfall_v3_core(
            inputs=proj,
            engine=engine,
            rate_per_period=0.02825,
            tenor_periods=28,
            advanced_opex_line_items=(),
        )
        assert result is not None

    def test_line_items_produce_expected_annual_totals(self):
        """Line items with known defaults produce annual totals."""
        from app.project_factories import create_default_solar_project
        from domain.period_engine import PeriodEngine
        from app.waterfall_core import run_waterfall_v3_core
        from app.opex_engine import build_opex_line_items_from_defaults
        proj = create_default_solar_project()
        engine = PeriodEngine(
            financial_close=proj.info.financial_close,
            construction_months=proj.info.construction_months,
            horizon_years=proj.info.horizon_years,
            ppa_years=proj.revenue.ppa_term_years,
        )
        items = build_opex_line_items_from_defaults("solar")
        result = run_waterfall_v3_core(
            inputs=proj,
            engine=engine,
            rate_per_period=0.02825,
            tenor_periods=28,
            advanced_opex_line_items=items,
        )
        assert result is not None
        # Smoke test: model ran to completion
        assert hasattr(result, "total_revenue_keur")
