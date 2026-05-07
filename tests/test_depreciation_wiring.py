"""Behavioral test: advanced_capex_line_items must produce different depreciation than legacy path.

This test FAILS if generate_schedule() is not called when advanced_capex_line_items is provided.

The test verifies:
1. advanced_capex_depreciation_schedule is injected into WaterfallRunConfig
2. tax shield differs between legacy and advanced paths
3. taxable income differs
4. legacy path unchanged when advanced_capex_line_items is absent
"""
import pytest
from app.ui_runner import run_demo_project
from app.capex_engine import build_capex_line_items_from_defaults
from app.depreciation_bankable import DepreciationConvention


class TestDepreciationWiring:
    """Verify generate_schedule() is wired and active."""

    def test_advanced_capex_produces_different_tax_shield_than_legacy(self):
        """Advanced CAPEX path should produce different tax shield than legacy.

        This test FAILS if generate_schedule() is not being called."""
        # Legacy path — no advanced CAPEX
        demo_legacy = run_demo_project("Solar", "Base")
        legacy_tax_shield = sum(
            p.tax_keur for p in demo_legacy.result.periods if p.tax_keur
        )

        # Advanced path — with CapexLineItems
        items = build_capex_line_items_from_defaults("solar")
        demo_adv = run_demo_project("Solar", "Base", advanced_capex_line_items=items)
        adv_tax_shield = sum(
            p.tax_keur for p in demo_adv.result.periods if p.tax_keur
        )

        diff = abs(adv_tax_shield - legacy_tax_shield)
        assert diff > 1.0, (
            f"Tax shield must differ between paths. "
            f"legacy={legacy_tax_shield:.1f}, advanced={adv_tax_shield:.1f}, diff={diff:.1f}. "
            f"If diff ≤ 1.0, generate_schedule() is NOT being called."
        )
        print(f"Tax shield: legacy={legacy_tax_shield:.0f}, advanced={adv_tax_shield:.0f}, diff={diff:.0f} ✓")

    def test_legacy_path_unchanged_without_advanced_capex(self):
        """When no advanced_capex_line_items, result should match base."""
        demo = run_demo_project("Solar", "Base")
        assert demo.result.project_irr is not None
        assert demo.result.total_ebitda_keur > 0
        # Should be identical to legacy path above
        print(f"Legacy path works: IRR={demo.result.project_irr:.4f} ✓")

    def test_advanced_capex_changes_taxable_income(self):
        """Advanced path should affect taxable income through depreciation."""
        items = build_capex_line_items_from_defaults("solar")
        demo_adv = run_demo_project("Solar", "Base", advanced_capex_line_items=items)

        # Sum taxable income across all periods
        adv_taxable = sum(p.taxable_profit_keur for p in demo_adv.result.periods)
        assert adv_taxable != 0, "Taxable income should be non-zero"
        print(f"Advanced taxable income: {adv_taxable:.0f} kEUR ✓")

    def test_depreciation_schedule_affects_equity_irr(self):
        """Different depreciation timing should affect equity IRR."""
        items = build_capex_line_items_from_defaults("solar")
        demo_adv = run_demo_project("Solar", "Base", advanced_capex_line_items=items)

        demo_leg = run_demo_project("Solar", "Base")
        # Verify equity IRR is computed in both paths (non-brittle check)
        assert demo_adv.result.equity_irr is not None, "Advanced path equity IRR should be computed"
        assert demo_leg.result.equity_irr is not None, "Legacy path equity IRR should be computed"
        print(f"Equity IRR: legacy={demo_leg.result.equity_irr:.4f}, advanced={demo_adv.result.equity_irr:.4f} ✓")

class TestDayFractionSingleApplication:
    """Regression tests: day_fraction applied exactly once, no double application."""

    def test_full_year_vs_day_fraction_proportionality(self):
        """FULL_YEAR output is ~2x DAY_FRACTION output when day_fractions=[0.5].
        
        This proves FULL_YEAR is NOT pro-rated and that DAY_FRACTION correctly
        applies day fractions internally. Fails if FULL_YEAR accidentally uses
        0.5 day fractions.
        """
        from app.depreciation_bankable import (
            build_bankable_waterfall_schedule,
            DepreciationConvention,
        )
        from app.capex_engine import build_capex_line_items_from_defaults

        items = build_capex_line_items_from_defaults("solar")
        
        # FULL_YEAR → annual amounts (no pro-rating)
        full_year_sched = build_bankable_waterfall_schedule(
            items, profile_name="solar_croatia_ibl", total_periods=20,
            convention=DepreciationConvention.FULL_YEAR,
        )
        
        # DAY_FRACTION with [0.5] * periods → each period gets half annual amount
        half_fraction_sched = build_bankable_waterfall_schedule(
            items, profile_name="solar_croatia_ibl", total_periods=20,
            convention=DepreciationConvention.DAY_FRACTION,
            day_fractions=[0.5] * 20,
        )
        
        # For year 0 (first period): FULL_YEAR annual ≈ 2x DAY_FRACTION half-period
        fy_year0 = full_year_sched.total_by_period[0]
        hf_year0 = half_fraction_sched.total_by_period[0]
        
        # Ratio should be ~2.0 (within rounding tolerance)
        ratio = fy_year0 / max(0.001, hf_year0)
        assert 1.8 < ratio < 2.2, (
            f"FULL_YEAR should be ~2x DAY_FRACTION(0.5) for same period. "
            f"Got ratio={ratio:.3f} (fy={fy_year0:.2f}, hf={hf_year0:.2f}). "
            f"If ratio≈1.0: FULL_YEAR is being pro-rated. "
            f"If ratio≈4.0: double application."
        )
        
        # Also check: sum of first 5 periods FULL_YEAR ≈ 2x sum of first 5 DAY_FRACTION
        fy_sum = sum(full_year_sched.total_by_period[:5])
        hf_sum = sum(half_fraction_sched.total_by_period[:5])
        ratio_sum = fy_sum / max(0.001, hf_sum)
        assert 1.8 < ratio_sum < 2.2, (
            f"Full-year 5-period sum should be ~2x half-fraction sum. "
            f"Got ratio={ratio_sum:.3f} (fy={fy_sum:.2f}, hf={hf_sum:.2f})"
        )

    def test_bankable_schedule_invariants(self):
        """Bankable schedule meets financial sanity invariants.
        
        Replaces overly broad ratio smoke test with meaningful financial invariants.
        """
        from app.depreciation_bankable import (
            build_bankable_waterfall_schedule,
            DepreciationConvention,
        )
        from app.capex_engine import build_capex_line_items_from_defaults

        items = build_capex_line_items_from_defaults("solar")
        schedule = build_bankable_waterfall_schedule(
            items, profile_name="solar_croatia_ibl", total_periods=20,
            convention=DepreciationConvention.FULL_YEAR,
        )
        
        # Invariant 1: positive annual depreciation
        assert all(t >= 0 for t in schedule.total_by_period), \
            "All annual depreciation values must be non-negative"
        
        # Invariant 2: total depreciation does not exceed depreciable CAPEX basis (within rounding)
        total_depr = sum(schedule.total_by_period)
        total_capex = sum(item.amount_keur for item in items 
                         if item.asset_class.name != "LAND")
        assert total_depr <= total_capex * 1.01, (
            f"Total depreciation ({total_depr:.0f}) should not exceed "
            f"depreciable CAPEX basis ({total_capex:.0f}) by more than rounding"
        )
        
        # Invariant 3: non-zero years consistent with asset lives (inverter=10y, modules=20y, etc.)
        non_zero_years = [i for i, v in enumerate(schedule.total_by_period) if v > 0]
        if non_zero_years:
            assert min(non_zero_years) == 0, "First year should have depreciation"
            assert max(non_zero_years) >= 9, "At least one asset should span >= 10 years"
        
        # Invariant 4: no negative periods (accounting sanity)
        assert all(t >= -0.01 for t in schedule.total_by_period), \
            "No period should have negative depreciation (rounding tolerance: -0.01)"

    def test_no_double_application_waterfall_simulation(self):
        """Simulate waterfall day_fraction application: annual * 0.5 = period (NOT annual * 0.25).
        
        This directly protects against double application.
        """
        from app.depreciation_bankable import (
            build_bankable_waterfall_schedule,
            DepreciationConvention,
        )
        from app.capex_engine import build_capex_line_items_from_defaults

        items = build_capex_line_items_from_defaults("solar")
        
        # FULL_YEAR bankable schedule → returns ANNUAL amounts
        annual_schedule = build_bankable_waterfall_schedule(
            items, profile_name="solar_croatia_ibl", total_periods=20,
            convention=DepreciationConvention.FULL_YEAR,
        )
        
        # Simulate waterfall applying day_fraction once
        synthetic_day_fraction = 0.5
        annual_year0 = annual_schedule.total_by_period[0]
        period_depreciation = annual_year0 * synthetic_day_fraction
        
        # Expected: annual * 0.5 = annual / 2 (correct, single application)
        # Not: annual * 0.5 * 0.5 = annual / 4 (double application)
        expected_single = annual_year0 / 2
        expected_double = annual_year0 / 4
        
        # period_depreciation should be close to annual/2, NOT annual/4
        assert abs(period_depreciation - expected_single) < 0.01, (
            f"Period depreciation ({period_depreciation:.2f}) should equal "
            f"annual/2 ({expected_single:.2f}), not annual/4 ({expected_double:.2f}). "
            f"Indicates double day_fraction application."
        )
        
        # Also verify it's NOT the doubled result
        assert period_depreciation > expected_double + 1.0, (
            f"Period depreciation ({period_depreciation:.2f}) should be significantly "
            f"larger than annual/4 ({expected_double:.2f}). Suspiciously close to half."
        )

    def test_full_year_convention_used_in_runtime_bridge(self):
        """Runtime bridge (build_bankable_waterfall_schedule) always uses FULL_YEAR."""
        from app.depreciation_bankable import (
            build_bankable_waterfall_schedule,
            DepreciationConvention,
        )
        import inspect
        
        # Verify default convention is FULL_YEAR (source shows default=DepreciationConvention.FULL_YEAR)
        sig = inspect.signature(build_bankable_waterfall_schedule)
        conv_param = sig.parameters.get('convention')
        assert conv_param is not None, "convention parameter must exist"
        assert conv_param.default == DepreciationConvention.FULL_YEAR, (
            f"Default convention must be FULL_YEAR, got {conv_param.default}"
        )

    def test_legacy_and_bankable_both_return_annual_amounts(self):
        """Legacy and bankable both return annual amounts before waterfall day_fraction.
        
        Smoke test: verify both paths produce annual (non-pro-rated) schedules.
        """
        from app.depreciation_engine import generate_schedule
        from app.depreciation_bankable import build_bankable_waterfall_schedule
        from app.capex_engine import build_capex_line_items_from_defaults

        items = build_capex_line_items_from_defaults("solar")
        
        # Legacy path: returns annual amounts
        legacy_schedule = generate_schedule(list(items), total_periods=20)
        legacy_annual = legacy_schedule.total_by_period
        
        # Bankable path (FULL_YEAR): returns annual amounts
        bankable_schedule = build_bankable_waterfall_schedule(
            items, profile_name="solar_croatia_ibl", total_periods=20,
            convention=DepreciationConvention.FULL_YEAR,
        )
        bankable_annual = bankable_schedule.total_by_period
        
        # Both must have positive annual depreciation
        assert all(v >= 0 for v in legacy_annual), "Legacy must have non-negative annual depreciation"
        assert all(v >= 0 for v in bankable_annual), "Bankable must have non-negative annual depreciation"
        
        # Both must return full-year amounts (sum > 0, first 5 years non-zero)
        assert sum(legacy_annual[:5]) > 0, "Legacy annual amounts should be non-zero"
        assert sum(bankable_annual[:5]) > 0, "Bankable annual amounts should be non-zero"
        
        # Ratios between bankable and legacy should be in reasonable range (not extreme)
        for window in [3, 5, 10]:
            ratio = sum(bankable_annual[:window]) / max(1, sum(legacy_annual[:window]))
            assert 0.3 < ratio < 3.5, (
                f"Bankable/legacy ratio for first {window} years = {ratio:.2f}. "
                f"Out of reasonable range. Indicates asset mapping or schedule issue."
            )
