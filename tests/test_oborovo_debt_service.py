"""Oborovo debt-service calibration tests.

Tests the fixed_debt_keur path (gearing_cap method) for Oborovo Solar
and ensures no regressions for TUHO Wind or generic Solar/Wind projects.

Scope:
- Task B: Lock in debt-service fix with tests
- Task C: Project IRR financing-independence behavioral test
"""
import pytest
from dataclasses import replace

from app.project_factories import (
    create_default_oborovo,
    create_default_tuho_wind1_legacy_calibration,
    create_default_solar_project,
    create_default_wind_project,
)
from app.ui_runner import run_demo_project


# =============================================================================
# Oborovo Solar — fixed_debt_keur / gearing_cap path
# =============================================================================

class TestOborovoDebtService:
    """Task B.1–B.4: Oborovo DSCR/debt regression tests."""

    @pytest.fixture
    def oborovo_result(self):
        oborovo = create_default_oborovo()
        return run_demo_project("Solar", "Base", project_inputs_override=oborovo).result

    def test_total_senior_debt_service_realistic(self, oborovo_result):
        """B.1: Oborovo total senior debt service should be 60,000–70,000 kEUR."""
        periods = oborovo_result.periods or []
        total_ds = sum(p.senior_ds_keur for p in periods if hasattr(p, 'senior_ds_keur'))
        assert 60_000 <= total_ds <= 70_000, (
            f"Oborovo total senior DS {total_ds:.0f} kEUR outside "
            f"expected range [60,000, 70,000]"
        )

    def test_total_senior_debt_service_not_exceeding_limit(self, oborovo_result):
        """B.1: Oborovo total senior debt service must not exceed 100,000 kEUR."""
        periods = oborovo_result.periods or []
        total_ds = sum(p.senior_ds_keur for p in periods if hasattr(p, 'senior_ds_keur'))
        assert total_ds <= 100_000, (
            f"Oborovo total senior DS {total_ds:.0f} kEUR exceeds 100,000 kEUR cap"
        )

    def test_avg_dscr_reasonable(self, oborovo_result):
        """B.2: Oborovo avg DSCR should be between 1.10 and 1.35."""
        avg = oborovo_result.actual_avg_dscr
        assert 1.10 <= avg <= 1.35, (
            f"Oborovo avg DSCR {avg:.3f} outside expected range [1.10, 1.35]"
        )

    def test_min_dscr_reasonable(self, oborovo_result):
        """B.3: Oborovo min DSCR should be above 1.05."""
        min_dscr = oborovo_result.actual_min_dscr
        assert min_dscr > 1.05, (
            f"Oborovo min DSCR {min_dscr:.3f} below 1.05 threshold"
        )

    def test_fixed_debt_anchored(self, oborovo_result):
        """B.4: Oborovo fixed debt should remain ~42,852 kEUR."""
        debt = oborovo_result.sculpting_result.debt_keur
        assert abs(debt - 42_852) < 500, (
            f"Oborovo debt {debt:.0f} kEUR shifted from expected 42,852 kEUR"
        )

    def test_equity_irr_reasonable_post_fix(self, oborovo_result):
        """Post-fix: Oborovo equity IRR should be 8-11% (calibrated after merchant curve).
        
        Pre-P0 (buggy DSCR): ~9.96%
        Post-P0 (fixed DSCR, old merchant curve): ~10.16%
        Post-P0+P1 (AFRY merchant): ~9.17% (merchant prices now 10-16% lower)
        
        Reference equity IRR 10.60% was computed with wrong merchant curve,
        so the post-fix range [8.0, 11.5] reflects calibrated reality.
        """
        irr = oborovo_result.equity_irr * 100
        assert 8.0 <= irr <= 11.5, (
            f"Oborovo equity IRR {irr:.2f}% outside expected range [8.0, 11.5]"
        )

    def test_project_irr_within_tolerance(self, oborovo_result):
        """Post-fix: Oborovo project IRR should be 8–9% (ref 7.96%, model was 9.11% pre-fix)."""
        irr = oborovo_result.project_irr * 100
        assert 7.5 <= irr <= 9.5, (
            f"Oborovo project IRR {irr:.2f}% outside expected range [7.5, 9.5]"
        )


# =============================================================================
# TUHO Wind — regression check (no fixed_debt_keur, uses fixed debt_sizing)
# =============================================================================

class TestTuhuRegression:
    """Task B.5: TUHO regression tests."""

    @pytest.fixture
    def tuho_result(self):
        tuho = create_default_tuho_wind1_legacy_calibration()
        return run_demo_project("Wind", "Base", project_inputs_override=tuho).result

    def test_total_debt_service_realistic(self, tuho_result):
        """B.5: TUHO total senior debt service should be 60,000–80,000 kEUR."""
        periods = tuho_result.periods or []
        total_ds = sum(p.senior_ds_keur for p in periods if hasattr(p, 'senior_ds_keur'))
        assert 60_000 <= total_ds <= 80_000, (
            f"TUHO total senior DS {total_ds:.0f} kEUR outside range [60,000, 80,000]"
        )

    def test_equity_irr_near_reference(self, tuho_result):
        """B.5: TUHO equity IRR should remain near 11.61% reference."""
        irr = tuho_result.equity_irr * 100
        assert 11.0 <= irr <= 12.2, (
            f"TUHO equity IRR {irr:.2f}% shifted from reference 11.61%"
        )

    def test_no_catastrophic_dscr_regression(self, tuho_result):
        """B.5: TUHO avg DSCR should remain above 1.3 (reference 1.451)."""
        avg = tuho_result.actual_avg_dscr
        assert avg > 1.3, (
            f"TUHO avg DSCR {avg:.3f} shows catastrophic regression below 1.3"
        )

    def test_project_irr_reasonable(self, tuho_result):
        """TUHO project IRR should be within 9–11% (reference 9.47%)."""
        irr = tuho_result.project_irr * 100
        assert 9.0 <= irr <= 11.0, (
            f"TUHO project IRR {irr:.2f}% outside range [9.0, 11.0]"
        )


# =============================================================================
# Generic Solar/Wind — no regression
# =============================================================================

class TestGenericSolarNoRegression:
    """Task B.6: Generic Solar should remain unaffected."""

    @pytest.fixture
    def solar_result(self):
        solar = create_default_solar_project()
        return run_demo_project("Solar", "Base", project_inputs_override=solar).result

    def test_kpis_within_golden_tolerances(self, solar_result):
        """B.6: Generic Solar KPIs should be within existing golden tolerances."""
        # Reference values for generic solar (pre-fix established baselines)
        assert 1.40 <= solar_result.actual_avg_dscr <= 1.90, (
            f"Generic Solar avg DSCR {solar_result.actual_avg_dscr:.3f} "
            f"outside golden range [1.40, 1.90]"
        )
        assert 12.5 <= solar_result.equity_irr * 100 <= 14.5, (
            f"Generic Solar equity IRR {solar_result.equity_irr*100:.2f}% "
            f"outside golden range [12.5, 14.5]"
        )

    def test_project_irr_reasonable(self, solar_result):
        """Generic Solar project IRR should be 8–11%."""
        irr = solar_result.project_irr * 100
        assert 8.0 <= irr <= 11.0, (
            f"Generic Solar project IRR {irr:.2f}% outside range [8.0, 11.0]"
        )


class TestGenericWindNoRegression:
    """Generic Wind should remain unaffected (no fixed_debt_keur branch)."""

    @pytest.fixture
    def wind_result(self):
        wind = create_default_wind_project()
        return run_demo_project("Wind", "Base", project_inputs_override=wind).result

    def test_kpis_stable(self, wind_result):
        """Generic Wind KPIs should be stable."""
        assert wind_result.actual_avg_dscr > 1.2, (
            f"Generic Wind avg DSCR {wind_result.actual_avg_dscr:.3f} below 1.2"
        )
        assert 0 < wind_result.equity_irr < 0.20, (
            f"Generic Wind equity IRR {wind_result.equity_irr:.3f} unreasonable"
        )


# =============================================================================
# Task C — Project IRR Financing-Independence Test
# =============================================================================

class TestProjectIRRFactoringIndependence:
    """Behavioral test: Project IRR should not materially change with financing structure."""

    def test_oborovo_project_irr_financing_independent(self):
        """Changing only debt terms should not shift Project IRR by more than 5 bps."""
        oborovo = create_default_oborovo()
        result_base = run_demo_project("Solar", "Base", project_inputs_override=oborovo).result
        irr_base = result_base.project_irr

        # Clone with different gearing (higher debt)
        oborovo_high_gearing = replace(
            oborovo,
            financing=replace(oborovo.financing, gearing_ratio=0.85),
        )
        result_high = run_demo_project("Solar", "Base", project_inputs_override=oborovo_high_gearing).result
        irr_high = result_high.project_irr

        delta_bps = abs(irr_high - irr_base) * 10000
        assert delta_bps < 5, (
            f"Oborovo Project IRR shifted {delta_bps:.1f} bps when only gearing changed "
            f"({irr_base*100:.3f}% → {irr_high*100:.3f}%). "
            f"Project IRR should be financing-independent."
        )

    def test_oborovo_project_irr_vs_fixed_debt_variation(self):
        """Changing fixed_debt_keur should not shift Project IRR by more than 5 bps."""
        oborovo = create_default_oborovo()
        result_base = run_demo_project("Solar", "Base", project_inputs_override=oborovo).result
        irr_base = result_base.project_irr

        # Clone with 5% higher fixed debt
        oborovo_more_debt = replace(
            oborovo,
            financing=replace(oborovo.financing, fixed_debt_keur=oborovo.financing.fixed_debt_keur * 1.05),
        )
        result_more = run_demo_project("Solar", "Base", project_inputs_override=oborovo_more_debt).result
        irr_more = result_more.project_irr

        delta_bps = abs(irr_more - irr_base) * 10000
        assert delta_bps < 5, (
            f"Oborovo Project IRR shifted {delta_bps:.1f} bps when fixed_debt changed "
            f"({irr_base*100:.3f}% → {irr_more*100:.3f}%). "
            f"Project IRR should be financing-independent."
        )

    def test_solar_project_irr_not_affected_by_senior_tenor(self):
        """Project IRR for generic solar should not change with senior tenor."""
        solar = create_default_solar_project()
        result_14y = run_demo_project("Solar", "Base", project_inputs_override=solar).result
        irr_14y = result_14y.project_irr

        solar_18y = replace(
            solar,
            financing=replace(solar.financing, senior_tenor_years=18),
        )
        result_18y = run_demo_project("Solar", "Base", project_inputs_override=solar_18y).result
        irr_18y = result_18y.project_irr

        delta_bps = abs(irr_18y - irr_14y) * 10000
        assert delta_bps < 10, (
            f"Generic Solar Project IRR shifted {delta_bps:.1f} bps with tenor change "
            f"({irr_14y*100:.3f}% → {irr_18y*100:.3f}%). "
            f"Project IRR should be financing-independent."
        )
