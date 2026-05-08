"""Merchant curve calibration tests for Oborovo.

Tests that:
1. PPA years (Y1-Y12) revenue unchanged when merchant curve changes
2. Merchant years (Y13-Y30) use AFRY profile
3. Oborovo Project IRR calibrated to reference (±0.5pp)
4. Generic Solar/Wind unaffected by merchant curve framework

Scope:
- Task 4 from P1 merchant curve sprint
"""
import pytest
from dataclasses import replace

from app.project_factories import (
    create_default_oborovo,
    create_default_solar_project,
    create_default_wind_project,
)
from app.ui_runner import run_demo_project
from app.merchant_curves import CROATIA_SOLAR_AFRY_CENTRAL_2024


# =============================================================================
# Task 4.1 - PPA Years Revenue Unchanged
# =============================================================================

class TestPpaYearsUnchanged:
    """Verify Y1-Y12 PPA revenue unchanged after merchant curve fix."""

    @pytest.fixture
    def oborovo_result(self):
        oborovo = create_default_oborovo()
        return run_demo_project("Solar", "Base", project_inputs_override=oborovo).result

    def test_y1_revenue_unchanged(self, oborovo_result):
        """Y1 revenue should be ~6,447 kEUR (PPA tariff indexed 57×1.02^0)."""
        y1_periods = [p for p in oborovo_result.periods if p.year_index == 1 and p.is_operation]
        y1_rev = sum(p.revenue_keur for p in y1_periods)
        assert 6_200 < y1_rev < 6_700, (
            f"Y1 revenue {y1_rev:.0f} kEUR outside expected range [6,200, 6,700]"
        )

    def test_y12_revenue_unchanged(self, oborovo_result):
        """Y12 (last PPA year) revenue should be ~7,632 kEUR."""
        y12_periods = [p for p in oborovo_result.periods if p.year_index == 12 and p.is_operation]
        y12_rev = sum(p.revenue_keur for p in y12_periods)
        assert 7_300 < y12_rev < 7_950, (
            f"Y12 revenue {y12_rev:.0f} kEUR outside expected range [7,300, 7,950]"
        )

    def test_y13_merchant_revenue_decreased(self, oborovo_result):
        """Y13 merchant revenue should be lower than old curve (~8,822 kEUR)."""
        y13_periods = [p for p in oborovo_result.periods if p.year_index == 13 and p.is_operation]
        y13_rev = sum(p.revenue_keur for p in y13_periods)
        assert 7_200 < y13_rev < 8_200, (
            f"Y13 revenue {y13_rev:.0f} kEUR - old curve gave ~8,822 kEUR, "
            f"AFRY should reduce to ~7,500-8,000 kEUR"
        )

    def test_ppa_tariff_indexed_correctly(self, oborovo_result):
        """PPA tariff should increase 2%/year from Y1=57 EUR/MWh."""
        y1_periods = [p for p in oborovo_result.periods if p.year_index == 1 and p.is_operation]
        y12_periods = [p for p in oborovo_result.periods if p.year_index == 12 and p.is_operation]
        y1_gen = sum(p.generation_mwh for p in y1_periods)
        y12_gen = sum(p.generation_mwh for p in y12_periods)
        y1_rev = sum(p.revenue_keur for p in y1_periods)
        y12_rev = sum(p.revenue_keur for p in y12_periods)
        y1_price = y1_rev * 1000 / y1_gen if y1_gen > 0 else 0
        y12_price = y12_rev * 1000 / y12_gen if y12_gen > 0 else 0
        expected_y12_price = 57.0 * (1.02 ** 12)
        assert abs(y12_price - expected_y12_price) / expected_y12_price < 0.03, (
            f"Y12 implied price {y12_price:.2f} deviates >3% from indexed tariff "
            f"{expected_y12_price:.2f}"
        )


# =============================================================================
# Task 4.2 - Oborovo Project IRR Calibrated
# =============================================================================

class TestOborovoProjectIrrCalibrated:
    """Oborovo Project IRR should be within ±0.5pp of reference 7.96%."""

    @pytest.fixture
    def oborovo_result(self):
        oborovo = create_default_oborovo()
        return run_demo_project("Solar", "Base", project_inputs_override=oborovo).result

    def test_project_irr_within_tolerance(self, oborovo_result):
        """Project IRR 7.96% ±0.5pp → range [7.46%, 8.46%]."""
        irr = oborovo_result.project_irr * 100
        assert 7.46 <= irr <= 8.46, (
            f"Oborovo project IRR {irr:.3f}% outside [7.46%, 8.46%] "
            f"(reference: 7.96%)"
        )

    def test_project_irr_reasonable_for_solar(self, oborovo_result):
        """Project IRR for Oborovo solar should be 7-10%."""
        irr = oborovo_result.project_irr * 100
        assert 7.0 <= irr <= 10.0, (
            f"Oborovo project IRR {irr:.2f}% unreasonable for solar"
        )

    def test_debt_anchored(self, oborovo_result):
        """Total debt should remain ~42,852 kEUR."""
        debt = oborovo_result.sculpting_result.debt_keur if oborovo_result.sculpting_result else 0
        assert abs(debt - 42_852) < 500, (
            f"Oborovo debt {debt:.0f} kEUR shifted from expected 42,852 kEUR"
        )


# =============================================================================
# Task 4.3 - Merchant Curve Profile Tests
# =============================================================================

class TestMerchantProfileRegistry:
    """Test that merchant curve registry works correctly."""

    def test_afry_profile_has_30_values(self):
        """AFRY profile should have 30+ values (full horizon)."""
        assert len(CROATIA_SOLAR_AFRY_CENTRAL_2024.curve) >= 30

    def test_afry_profile_y13_y30_nonzero(self):
        """AFRY profile Y13-Y30 (indices 12-29) should be nonzero."""
        curve = CROATIA_SOLAR_AFRY_CENTRAL_2024.curve
        for i in range(12, len(curve)):
            assert curve[i] > 0, f"Year {i+1} (index {i}) has nonzero price"


# =============================================================================
# Task 4.4 - Generic Solar/Wind Unchanged
# =============================================================================

class TestGenericSolarUnchanged:
    """Generic Solar KPIs should be within golden tolerances."""

    @pytest.fixture
    def solar_result(self):
        solar = create_default_solar_project()
        return run_demo_project("Solar", "Base", project_inputs_override=solar).result

    def test_kpis_within_golden_tolerances(self, solar_result):
        """Generic Solar should match golden values."""
        assert 1.40 <= solar_result.actual_avg_dscr <= 1.90
        assert 12.5 <= solar_result.equity_irr * 100 <= 14.5
        assert 8.0 <= solar_result.project_irr * 100 <= 11.0


class TestGenericWindUnchanged:
    """Generic Wind KPIs should remain stable."""

    @pytest.fixture
    def wind_result(self):
        wind = create_default_wind_project()
        return run_demo_project("Wind", "Base", project_inputs_override=wind).result

    def test_kpis_stable(self, wind_result):
        """Generic Wind should remain stable."""
        assert wind_result.actual_avg_dscr > 1.2
        assert 0 < wind_result.equity_irr < 0.20


# =============================================================================
# Task 4.5 - Oborovo Debt-Service Still Fixed After Merchant Change
# =============================================================================

class TestOborovoDebtServiceFixed:
    """Oborovo DSCR should remain healthy after merchant curve change."""

    @pytest.fixture
    def oborovo_result(self):
        oborovo = create_default_oborovo()
        return run_demo_project("Solar", "Base", project_inputs_override=oborovo).result

    def test_avg_dscr_reasonable(self, oborovo_result):
        """Oborovo avg DSCR should be >1.10 (was 0.181 pre-P0 fix)."""
        avg = oborovo_result.actual_avg_dscr
        assert avg > 1.10, (
            f"Oborovo avg DSCR {avg:.3f} below 1.10 - P0 debt-service fix may regress"
        )

    def test_min_dscr_reasonable(self, oborovo_result):
        """Oborovo min DSCR should be >1.05."""
        min_d = oborovo_result.actual_min_dscr
        assert min_d > 1.05, (
            f"Oborovo min DSCR {min_d:.3f} below 1.05 threshold"
        )

    def test_equity_irr_reasonable(self, oborovo_result):
        """Oborovo equity IRR should be >8%."""
        irr = oborovo_result.equity_irr * 100
        assert irr > 8.0, (
            f"Oborovo equity IRR {irr:.2f}% unreasonably low "
            f"(was 9.96% pre-merchant fix)"
        )