"""Tests for app/capex_engine.py — CAPEX line-item engine."""
from __future__ import annotations

import pytest
from app.capex_engine import (
    AssetClass,
    TimingProfile,
    CapexLineItem,
    CapexScheduleEntry,
    CapexSchedule,
    generate_capex_schedule,
    build_capex_line_items_from_defaults,
    _draw_fractions,
)


class TestDrawFractions:
    """Tests for _draw_fractions helper."""

    def test_upfront_all_in_period_0(self):
        result = _draw_fractions(TimingProfile.UPFRONT, tenor=5)
        assert result[0] == 1.0
        assert all(v == 0.0 for v in result[1:])

    def test_elevated_80_20_split(self):
        result = _draw_fractions(TimingProfile.ELEVATED, tenor=5)
        assert result[0] == 0.80
        assert result[1] == 0.20
        assert all(v == 0.0 for v in result[2:])

    def test_annuity_equal_fractions(self):
        result = _draw_fractions(TimingProfile.ANNUITY, tenor=4)
        assert len(result) == 4
        assert all(abs(v - 0.25) < 1e-9 for v in result)

    def test_custom_fractions_padded(self):
        result = _draw_fractions(TimingProfile.CUSTOM, tenor=5, custom_fractions=(0.5, 0.3, 0.1))
        assert result[0] == 0.5
        assert result[1] == 0.3
        assert result[2] == 0.1
        assert result[3] == 0.0
        assert result[4] == 0.0

    def test_custom_fractions_trimmed(self):
        result = _draw_fractions(TimingProfile.CUSTOM, tenor=3, custom_fractions=(0.5, 0.3, 0.1, 0.1))
        assert len(result) == 3
        assert result == [0.5, 0.3, 0.1]


class TestCapexLineItem:
    """Tests for CapexLineItem dataclass."""

    def test_create_minimal_item(self):
        item = CapexLineItem(code="TST", name="Test", group="Test", amount_keur=1000.0)
        assert item.code == "TST"
        assert item.amount_keur == 1000.0
        assert item.asset_class == AssetClass.OTHER
        assert item.timing_profile == TimingProfile.UPFRONT
        assert item.is_manual is False

    def test_create_full_item(self):
        item = CapexLineItem(
            code="GRID",
            name="Grid Connection",
            group="Electrical",
            subgroup="Primary",
            description="110kV connection",
            amount_keur=5000.0,
            asset_class=AssetClass.GRID,
            timing_profile=TimingProfile.ELEVATED,
            timing_fractions=(0.7, 0.3),
            is_manual=True,
            notes="Estimated based on proximity to substation",
        )
        assert item.subgroup == "Primary"
        assert item.asset_class == AssetClass.GRID
        assert item.timing_fractions == (0.7, 0.3)
        assert item.is_manual is True
        assert item.notes

    def test_frozen_immutable(self):
        item = CapexLineItem(code="TST", name="Test", group="G", amount_keur=100.0)
        with pytest.raises(Exception):  # frozen dataclass
            item.code = "XXX"


class TestGenerateCapexSchedule:
    """Tests for generate_capex_schedule()."""

    def test_empty_items_returns_empty_schedule(self):
        result = generate_capex_schedule((), tenor_periods=5)
        assert result.entries == ()
        assert result.total_by_period == ()

    def test_upfront_draw_single_period(self):
        item = CapexLineItem(
            code="EPC", name="EPC Contract", group="Construction",
            amount_keur=10000.0, timing_profile=TimingProfile.UPFRONT,
        )
        schedule = generate_capex_schedule((item,), tenor_periods=5)
        assert len(schedule.entries) == 1
        assert schedule.entries[0].period_index == 0
        assert schedule.entries[0].draw_keur == 10000.0

    def test_elevated_draw_two_periods(self):
        item = CapexLineItem(
            code="GRID", name="Grid", group="Electrical",
            amount_keur=1000.0, timing_profile=TimingProfile.ELEVATED,
        )
        schedule = generate_capex_schedule((item,), tenor_periods=5)
        assert len(schedule.entries) == 2
        assert schedule.total_by_period[0] == 800.0  # 80%
        assert schedule.total_by_period[1] == 200.0  # 20%
        assert schedule.total_by_period[2] == 0.0

    def test_annuity_draw_equal_periods(self):
        item = CapexLineItem(
            code="CONT", name="Contingency", group="Risk",
            amount_keur=1000.0, timing_profile=TimingProfile.ANNUITY,
        )
        schedule = generate_capex_schedule((item,), tenor_periods=4)
        assert len(schedule.entries) == 4
        for entry in schedule.entries:
            assert entry.draw_keur == 250.0
        assert schedule.total_by_period == (250.0, 250.0, 250.0, 250.0)

    def test_custom_fractions(self):
        item = CapexLineItem(
            code="LAND", name="Land", group="Land",
            amount_keur=1000.0, timing_profile=TimingProfile.CUSTOM,
            timing_fractions=(0.6, 0.4),
        )
        schedule = generate_capex_schedule((item,), tenor_periods=3)
        assert schedule.entries[0].draw_keur == 600.0
        assert schedule.entries[1].draw_keur == 400.0
        assert len(schedule.entries) == 2

    def test_has_manual_items_true(self):
        item = CapexLineItem(
            code="TST", name="Test", group="G",
            amount_keur=100.0, is_manual=True,
        )
        schedule = generate_capex_schedule((item,), tenor_periods=3)
        assert schedule.has_manual_items is True

    def test_has_manual_items_false(self):
        item = CapexLineItem(code="TST", name="Test", group="G", amount_keur=100.0)
        schedule = generate_capex_schedule((item,), tenor_periods=3)
        assert schedule.has_manual_items is False

    def test_multiple_items_total_by_period(self):
        epc = CapexLineItem(
            code="EPC", name="EPC", group="C",
            amount_keur=10000.0, timing_profile=TimingProfile.UPFRONT,
        )
        grid = CapexLineItem(
            code="GRID", name="Grid", group="E",
            amount_keur=1000.0, timing_profile=TimingProfile.ELEVATED,
        )
        schedule = generate_capex_schedule((epc, grid), tenor_periods=3)
        assert schedule.total_by_period[0] == 10000.0 + 800.0  # EPC upfront + Grid 80%
        assert schedule.total_by_period[1] == 200.0  # Grid 20%
        assert schedule.total_by_period[2] == 0.0


class TestBuildCapexLineItemsFromDefaults:
    """Tests for build_capex_line_items_from_defaults()."""

    def test_solar_items_count(self):
        items = build_capex_line_items_from_defaults("solar")
        assert len(items) == 5  # grid, bos, epc, dev, contingency

    def test_wind_items_count(self):
        items = build_capex_line_items_from_defaults("wind")
        assert len(items) == 5

    def test_solar_groups(self):
        items = build_capex_line_items_from_defaults("solar")
        groups = {i.group for i in items}
        assert "Electrical" in groups
        assert "Construction" in groups
        assert "Development" in groups
        assert "Risk" in groups

    def test_scale_mw_affects_amounts(self):
        small = build_capex_line_items_from_defaults("solar", scale_mw=10.0)
        large = build_capex_line_items_from_defaults("solar", scale_mw=100.0)
        total_small = sum(i.amount_keur for i in small)
        total_large = sum(i.amount_keur for i in large)
        assert total_large > total_small

    def test_asset_classes_present(self):
        items = build_capex_line_items_from_defaults("solar")
        asset_classes = {i.asset_class for i in items}
        assert AssetClass.GRID in asset_classes
        assert AssetClass.EPC in asset_classes
        assert AssetClass.CONTINGENCY in asset_classes

    def test_timing_profiles_differ(self):
        items = build_capex_line_items_from_defaults("solar")
        profiles = {i.timing_profile for i in items}
        assert TimingProfile.UPFRONT in profiles
        assert TimingProfile.ELEVATED in profiles
        assert TimingProfile.CUSTOM in profiles

    def test_unknown_technology_fallback(self):
        items = build_capex_line_items_from_defaults("bess")
        assert len(items) == 1
        assert items[0].code == "CAP"


class TestCapexScheduleMatrixPreview:
    """Tests for CAPEX schedule matrix preview (mirrors OPEX)."""

    def test_matrix_columns_line_item_plus_periods(self):
        items = build_capex_line_items_from_defaults("solar", scale_mw=50.0)
        schedule = generate_capex_schedule(items, tenor_periods=4)

        # Build matrix
        capex_codes = list(dict.fromkeys(e.capex_code for e in schedule.entries))
        matrix_rows = []
        for code in capex_codes:
            period_vals = [0.0] * 4
            for e in schedule.entries:
                if e.capex_code == code:
                    period_vals[e.period_index] = e.draw_keur
            matrix_rows.append([code] + period_vals)

        total_row = ["Total CAPEX"] + list(schedule.total_by_period)
        matrix_rows.append(total_row)

        import pandas as pd
        cols = ["Capex Code"] + [f"P{y+1}" for y in range(4)]
        df = pd.DataFrame(matrix_rows, columns=cols)

        assert list(df.columns) == cols
        assert len(df) == len(capex_codes) + 1
        assert df.iloc[-1, 0] == "Total CAPEX"

    def test_total_row_matches_schedule_total_by_period(self):
        items = build_capex_line_items_from_defaults("solar", scale_mw=50.0)
        schedule = generate_capex_schedule(items, tenor_periods=4)

        import pandas as pd
        capex_codes = list(dict.fromkeys(e.capex_code for e in schedule.entries))
        matrix_rows = []
        for code in capex_codes:
            period_vals = [0.0] * 4
            for e in schedule.entries:
                if e.capex_code == code:
                    period_vals[e.period_index] = e.draw_keur
            matrix_rows.append([code] + period_vals)
        total_row = ["Total CAPEX"] + list(schedule.total_by_period)
        matrix_rows.append(total_row)
        cols = ["Capex Code"] + [f"P{y+1}" for y in range(4)]
        df = pd.DataFrame(matrix_rows, columns=cols)

        for col_idx in range(1, 5):
            assert df.iloc[-1, col_idx] == schedule.total_by_period[col_idx - 1]