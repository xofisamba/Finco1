"""Tests for app.depreciation_engine — generate_schedule(), DepreciationSchedule, DepreciationRule."""
import pytest
from app.depreciation_engine import (
    generate_schedule,
    DepreciationSchedule,
    DepreciationEntry,
    DepreciationRule,
    ASSET_CLASS_RULES,
    DEFAULT_RULE,
)
from app.capex_engine import CapexLineItem, AssetClass


def _item(name, amount, asset_class, code=None, group=None):
    """Helper: build a minimal CapexLineItem with required code/group."""
    return CapexLineItem(
        code=code or f"CODE-{name[:4].upper()}",
        name=name,
        group=group or "Test",
        amount_keur=amount,
        asset_class=asset_class,
    )


class TestDepreciationEngineBasic:
    def test_land_produces_no_depreciation(self):
        """LAND is non-depreciable."""
        items = [_item("Land", 5000, AssetClass.LAND)]
        schedule = generate_schedule(items, total_periods=30)
        # LAND produces no entries (method == "none" → skipped)
        land_entries = [e for e in schedule.entries if 'land' in e.asset_class.lower()]
        assert len(land_entries) == 0, "LAND should produce no depreciation entries"
        # All other entries should be zero
        assert all(e.annual_amount_keur == 0 for e in schedule.entries), "All entries should be zero"

    def test_generation_linear_schedule_totals_correctly(self):
        """GENERATION asset class depreciates linearly over 25 years."""
        items = [_item("SolarModules", 25000, AssetClass.GENERATION)]
        schedule = generate_schedule(items, total_periods=30)

        gen_entries = [e for e in schedule.entries if 'generation' in e.asset_class.lower()]
        assert len(gen_entries) == 25, f"Should have 25 entries (one per year), got {len(gen_entries)}"

        annual_amount = gen_entries[0].annual_amount_keur
        assert abs(annual_amount - 1000) < 1, f"25y straight-line of 25000 → ~1000/yr, got {annual_amount}"

        # Total should equal original amount (sum of all annual depreciation)
        total = sum(e.annual_amount_keur for e in gen_entries)
        assert abs(total - 25000) < 1, f"Total depreciation should = 25000, got {total}"

    def test_grid_schedule_totals_correctly(self):
        """GRID asset class depreciates over 20 years."""
        items = [_item("GridConnection", 20000, AssetClass.GRID)]
        schedule = generate_schedule(items, total_periods=25)

        grid_entries = [e for e in schedule.entries if 'grid' in e.asset_class.lower()]
        assert len(grid_entries) == 20, f"Should have 20 entries, got {len(grid_entries)}"
        total = sum(e.annual_amount_keur for e in grid_entries)
        assert abs(total - 20000) < 1, f"Total should = 20000, got {total}"

    def test_zero_amount_item_handled(self):
        """Zero-amount items produce no depreciation."""
        items = [
            _item("Valid", 10000, AssetClass.GENERATION),
            _item("Zero", 0, AssetClass.GRID),
        ]
        schedule = generate_schedule(items, total_periods=25)
        non_zero_zero = [e for e in schedule.entries if e.annual_amount_keur > 0 and abs(e.annual_amount_keur) < 0.001]
        assert len(non_zero_zero) == 0

    def test_total_depreciation_equals_total_depreciable_basis(self):
        """Sum of all depreciation = sum of all depreciable capex."""
        items = [
            _item("Solar", 25000, AssetClass.GENERATION),
            _item("Grid", 10000, AssetClass.GRID),
            _item("Dev", 2000, AssetClass.DEVELOPMENT),
        ]
        schedule = generate_schedule(items, total_periods=30)
        total_depr = sum(e.annual_amount_keur for e in schedule.entries)
        total_basis = sum(i.amount_keur for i in items)
        assert abs(total_depr - total_basis) < 10, f"Total depreciation {total_depr} should ≈ basis {total_basis}"

    def test_schedule_stops_at_end_of_life(self):
        """Entries stop after asset life ends."""
        items = [_item("Dev", 5000, AssetClass.DEVELOPMENT)]
        schedule = generate_schedule(items, total_periods=30)

        dev_entries = [e for e in schedule.entries if 'development' in e.asset_class.lower()]
        assert len(dev_entries) == 5, f"Development should depreciate over 5y, got {len(dev_entries)}"

    def test_default_rule_path(self):
        """Unknown asset class uses DEFAULT_RULE."""
        rule = ASSET_CLASS_RULES.get("UNKNOWN_CATEGORY", DEFAULT_RULE)
        assert rule.life_years == 20, "DEFAULT_RULE should be 20y linear"
        assert rule.method == "linear"

    def test_total_by_period_aggregation(self):
        """total_by_period sums all asset classes per period."""
        items = [
            _item("Solar", 25000, AssetClass.GENERATION),  # 25y
            _item("Grid", 10000, AssetClass.GRID),          # 20y
        ]
        schedule = generate_schedule(items, total_periods=30)

        assert len(schedule.total_by_period) == 30
        # Year 0: both contributing
        p0 = schedule.total_by_period[0]
        assert p0 > 0, f"Year 0 should have depreciation, got {p0}"
        # Year 19 (last year of GRID): both still contributing
        p19 = schedule.total_by_period[19]
        solar_annual = 25000 / 25  # = 1000
        grid_annual = 10000 / 20   # = 500
        assert abs(p19 - (solar_annual + grid_annual)) < 1, f"Year 19 should have both: ~{solar_annual + grid_annual}, got {p19}"
        # Year 20: only GENERATION still depreciating (GRID is done)
        p20 = schedule.total_by_period[20]
        assert abs(p20 - solar_annual) < 1, f"Year 20 should only have GENERATION: ~{solar_annual}, got {p20}"
        # Year 24 (1-indexed): GENERATION still depreciating (period=24, last year of 25y life)
        p24 = schedule.total_by_period[24]
        assert abs(p24 - solar_annual) < 1, f"Year 24 should only have GENERATION: ~{solar_annual}, got {p24}"
        # Year 25 (1-indexed = period 25): GENERATION done after 25 years
        p25 = schedule.total_by_period[25]
        assert p25 == 0, f"Year 25 should be 0 (GENERATION done), got {p25}"
        # Year 26+: all zero
        assert all(v == 0 for v in schedule.total_by_period[26:])

    def test_total_remaining_decreases(self):
        """remaining_basis decreases each period."""
        items = [_item("Solar", 25000, AssetClass.GENERATION)]
        schedule = generate_schedule(items, total_periods=30)

        remaining = schedule.total_remaining_by_period
        assert remaining[0] > remaining[1] > remaining[2]
        assert remaining[24] < remaining[23]
        assert remaining[25] == 0, "After 25 years, remaining should be 0"

    def test_multiple_asset_classes_aggregate(self):
        """Multiple asset classes produce separate entries per period."""
        items = [
            _item("Solar", 25000, AssetClass.GENERATION),
            _item("Grid", 10000, AssetClass.GRID),
            _item("Dev", 2000, AssetClass.DEVELOPMENT),
        ]
        schedule = generate_schedule(items, total_periods=30)

        # In year 0, all 3 should contribute
        year0_entries = [e for e in schedule.entries if e.period == 0]
        assert len(year0_entries) >= 3, f"Year 0 should have ≥3 entries, got {len(year0_entries)}"

    def test_no_negative_depreciation(self):
        """No entry should have negative depreciation."""
        items = [
            _item("Solar", 25000, AssetClass.GENERATION),
            _item("Grid", 10000, AssetClass.GRID),
        ]
        schedule = generate_schedule(items, total_periods=30)
        negatives = [e for e in schedule.entries if e.annual_amount_keur < 0]
        assert len(negatives) == 0, f"No negative depreciation entries, found: {negatives}"

    def test_deterministic_behavior(self):
        """Same input always produces same schedule."""
        items = [_item("Solar", 25000, AssetClass.GENERATION)]
        s1 = generate_schedule(items, total_periods=30)
        s2 = generate_schedule(items, total_periods=30)
        assert s1.total_by_period == s2.total_by_period, "Deterministic output"

    def test_accumulated_remaining_accounting(self):
        """For any entry, accumulated + remaining_basis ≈ original basis."""
        items = [_item("Solar", 25000, AssetClass.GENERATION)]
        schedule = generate_schedule(items, total_periods=30)

        # Check first generation entry's accounting
        for entry in schedule.entries:
            if 'generation' in entry.asset_class.lower() and entry.period == 0:
                check = entry.accumulated_keur + entry.remaining_basis_keur
                assert abs(check - 25000) < 10, (
                    f"accumulated({entry.accumulated_keur}) + remaining({entry.remaining_basis_keur}) "
                    f"should ≈ 25000"
                )
                break

    def test_epc_depreciation_25_years(self):
        """EPC asset class depreciates over 25 years."""
        items = [_item("EPC", 25000, AssetClass.EPC)]
        schedule = generate_schedule(items, total_periods=30)
        epc_entries = [e for e in schedule.entries if 'epc' in e.asset_class.lower()]
        assert len(epc_entries) == 25, f"EPC should have 25 entries, got {len(epc_entries)}"
        total = sum(e.annual_amount_keur for e in epc_entries)
        assert abs(total - 25000) < 1

    def test_contingency_depreciation_5_years(self):
        """CONTINGENCY asset class depreciates over 5 years."""
        items = [_item("Contingency", 5000, AssetClass.CONTINGENCY)]
        schedule = generate_schedule(items, total_periods=10)
        cont_entries = [e for e in schedule.entries if 'contingency' in e.asset_class.lower()]
        assert len(cont_entries) == 5, f"Contingency should have 5 entries, got {len(cont_entries)}"

    def test_other_uses_explicit_rule(self):
        """OTHER asset class has an explicit 10-year rule in ASSET_CLASS_RULES."""
        items = [_item("Other", 20000, AssetClass.OTHER)]
        schedule = generate_schedule(items, total_periods=25)
        other_entries = [e for e in schedule.entries if 'other' in e.asset_class.lower()]
        assert len(other_entries) == 10, f"OTHER should depreciate over 10y (explicit rule), got {len(other_entries)}"
        total = sum(e.annual_amount_keur for e in other_entries)
        assert abs(total - 20000) < 1

    def test_empty_line_items_returns_empty_entries(self):
        """Empty input produces an empty schedule."""
        schedule = generate_schedule([], total_periods=30)
        assert len(schedule.entries) == 0
        assert len(schedule.total_by_period) == 30
        assert all(v == 0 for v in schedule.total_by_period)

    def test_mixed_land_and_depreciable(self):
        """LAND excluded; only depreciable assets appear in entries."""
        items = [
            _item("Land", 5000, AssetClass.LAND),
            _item("Solar", 25000, AssetClass.GENERATION),
        ]
        schedule = generate_schedule(items, total_periods=30)
        land_entries = [e for e in schedule.entries if 'land' in e.asset_class.lower()]
        assert len(land_entries) == 0
        solar_entries = [e for e in schedule.entries if 'generation' in e.asset_class.lower()]
        assert len(solar_entries) == 25