"""Tests for asset-class depreciation schedule."""
import pytest
from domain.inputs import CapexItem, AssetClass, ASSET_CLASS_USEFUL_LIFE
from domain.financing.depreciation_schedule import (
    useful_life_for_item,
    build_depreciation_schedule,
    depreciation_per_period,
)
from domain.period_engine import PeriodEngine, PeriodFrequency
from datetime import date


class TestDepreciationSchedule:
    def test_solar_panels_useful_life(self):
        """SOLAR_PANELS has 25-year useful life."""
        assert ASSET_CLASS_USEFUL_LIFE[AssetClass.SOLAR_PANELS] == 25

    def test_solar_panels_40_per_year(self):
        """1000 kEUR solar panels → 40 kEUR/year for 25 years."""
        item = CapexItem(
            name="Solar panels",
            amount_keur=1000.0,
            asset_class=AssetClass.SOLAR_PANELS,
        )
        schedule = build_depreciation_schedule((item,), horizon_years=30)

        # Years 1-25: 40 kEUR
        for y in range(1, 26):
            assert abs(schedule[y] - 40.0) < 0.01, f"Year {y}: expected 40, got {schedule[y]}"

        # Years 26-30: 0
        for y in range(26, 31):
            assert schedule[y] == 0.0

    def test_bess_cells_10_years(self):
        """BESS_CELLS has 10-year useful life."""
        item = CapexItem(
            name="BESS cells",
            amount_keur=1000.0,
            asset_class=AssetClass.BESS_CELLS,
        )
        schedule = build_depreciation_schedule((item,), horizon_years=15)

        # Years 1-10: 100 kEUR/year
        for y in range(1, 11):
            assert abs(schedule[y] - 100.0) < 0.01

        # Years 11-15: 0
        for y in range(11, 16):
            assert schedule[y] == 0.0

    def test_useful_life_override(self):
        """useful_life_override takes precedence over asset class default."""
        item = CapexItem(
            name="Custom",
            amount_keur=500.0,
            asset_class=AssetClass.SOLAR_PANELS,
            useful_life_override=10,
        )
        assert useful_life_for_item(item) == 10

    def test_financial_costs_use_tenor(self):
        """FINANCIAL_COSTS uses senior_tenor_years."""
        item = CapexItem(
            name="IDC",
            amount_keur=1000.0,
            asset_class=AssetClass.FINANCIAL_COSTS,
        )
        schedule = build_depreciation_schedule((item,), horizon_years=20, senior_tenor_years=14)

        # Years 1-14: 1000/14 ≈ 71.43
        for y in range(1, 15):
            expected = 1000.0 / 14
            assert abs(schedule[y] - expected) < 0.01

        # Years 15-20: 0
        for y in range(15, 21):
            assert schedule[y] == 0.0

    def test_multiple_items_accumulate(self):
        """Multiple items accumulate depreciation."""
        items = (
            CapexItem(name="Panels", amount_keur=1000.0, asset_class=AssetClass.SOLAR_PANELS),
            CapexItem(name="Grid", amount_keur=600.0, asset_class=AssetClass.CIVIL_GRID),
        )
        schedule = build_depreciation_schedule(items, horizon_years=30)

        # Solar: 1000/25 = 40/yr, Civil: 600/30 = 20/yr → Year 1: 60
        assert abs(schedule[1] - 60.0) < 0.01

    def test_civil_grid_30_years(self):
        """CIVIL_GRID has 30-year useful life."""
        assert ASSET_CLASS_USEFUL_LIFE[AssetClass.CIVIL_GRID] == 30


class TestDepreciationPerPeriod:
    def test_half_year_split(self):
        """Depreciation splits by day_fraction for semi-annual periods."""
        item = CapexItem(
            name="Solar",
            amount_keur=1000.0,
            asset_class=AssetClass.SOLAR_PANELS,  # 25 yr → 40/year
        )
        annual = build_depreciation_schedule((item,), horizon_years=2)

        # Mock periods with different day_fractions
        class MockPeriod:
            def __init__(self, index, year_index, day_fraction, is_operation):
                self.index = index
                self.year_index = year_index
                self.day_fraction = day_fraction
                self.is_operation = is_operation

        periods = [
            MockPeriod(2, 1, 0.5, True),   # Y1-H1: 40 * 0.5 = 20
            MockPeriod(3, 1, 0.5, True),   # Y1-H2: 40 * 0.5 = 20
            MockPeriod(4, 2, 0.5, True),   # Y2-H1: 40 * 0.5 = 20
            MockPeriod(5, 2, 0.5, True),   # Y2-H2: 40 * 0.5 = 20
        ]

        result = depreciation_per_period(annual, periods)

        assert abs(result[2] - 20.0) < 0.01
        assert abs(result[3] - 20.0) < 0.01
        assert abs(result[4] - 20.0) < 0.01
        assert abs(result[5] - 20.0) < 0.01

    def test_non_operation_period_zero(self):
        """Non-operation periods get zero depreciation."""
        annual = {1: 40.0, 2: 40.0}

        class MockPeriod:
            def __init__(self, index, year_index, day_fraction, is_operation):
                self.index = index
                self.year_index = year_index
                self.day_fraction = day_fraction
                self.is_operation = is_operation

        periods = [
            MockPeriod(1, 1, 0.5, False),  # construction → 0
            MockPeriod(2, 1, 0.5, True),    # operation → 40 * 0.5 = 20
        ]

        result = depreciation_per_period(annual, periods)

        assert result[1] == 0.0
        assert abs(result[2] - 20.0) < 0.01

class TestCapexStructureCapexItems:
    """CapexStructure.capex_items() unit tests."""

    def test_capex_items_returns_only_non_zero(self):
        """capex_items() excludes zero-amount entries."""
        from domain.inputs import CapexStructure, CapexItem

        cs = CapexStructure(
            epc_contract=CapexItem(name="EPC", amount_keur=1000.0, asset_class=AssetClass.SOLAR_PANELS),
            production_units=CapexItem(name="Prod", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            epc_other=CapexItem(name="Other", amount_keur=500.0, asset_class=AssetClass.SOLAR_PANELS),
            grid_connection=CapexItem(name="Grid", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            ops_prep=CapexItem(name="Ops", amount_keur=200.0, asset_class=AssetClass.SOLAR_PANELS),
            insurances=CapexItem(name="Ins", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            lease_tax=CapexItem(name="Lease", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            construction_mgmt_a=CapexItem(name="CM_A", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            commissioning=CapexItem(name="Com", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            audit_legal=CapexItem(name="Audit", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            construction_mgmt_b=CapexItem(name="CM_B", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            contingencies=CapexItem(name="Cont", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            taxes=CapexItem(name="Tax", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            project_acquisition=CapexItem(name="Acq", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            project_rights=CapexItem(name="Rights", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
        )

        items = cs.capex_items()
        assert len(items) == 3
        amounts = [item.amount_keur for item in items]
        assert 1000.0 in amounts
        assert 500.0 in amounts
        assert 200.0 in amounts
        assert 0.0 not in amounts

    def test_capex_items_excludes_scalars(self):
        """capex_items() does not include scalar float fields."""
        from domain.inputs import CapexStructure, CapexItem

        cs = CapexStructure(
            epc_contract=CapexItem(name="EPC", amount_keur=1000.0, asset_class=AssetClass.SOLAR_PANELS),
            production_units=CapexItem(name="Prod", amount_keur=350.0, asset_class=AssetClass.SOLAR_PANELS),
            epc_other=CapexItem(name="Other", amount_keur=500.0, asset_class=AssetClass.SOLAR_PANELS),
            grid_connection=CapexItem(name="Grid", amount_keur=100.0, asset_class=AssetClass.SOLAR_PANELS),
            ops_prep=CapexItem(name="Ops", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            insurances=CapexItem(name="Ins", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            lease_tax=CapexItem(name="Lease", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            construction_mgmt_a=CapexItem(name="CM_A", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            commissioning=CapexItem(name="Com", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            audit_legal=CapexItem(name="Audit", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            construction_mgmt_b=CapexItem(name="CM_B", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            contingencies=CapexItem(name="Cont", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            taxes=CapexItem(name="Tax", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            project_acquisition=CapexItem(name="Acq", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            project_rights=CapexItem(name="Rights", amount_keur=0.0, asset_class=AssetClass.SOLAR_PANELS),
            idc_keur=5000.0,  # scalar float, not a CapexItem
            bank_fees_keur=300.0,  # scalar float, not a CapexItem
        )

        items = cs.capex_items()
        from domain.inputs import CapexItem as CI
        assert all(isinstance(item, CI) for item in items)
        amounts = [item.amount_keur for item in items]
        # idc=5000 and bank_fees=300 are scalar floats, should not appear
        assert 5000.0 not in amounts
        assert 300.0 not in amounts
        # But 350 (production_units CapexItem) should appear
        assert 350.0 in amounts
