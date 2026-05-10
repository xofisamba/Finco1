"""Phase 6B.1 tests for tax calculation primitives."""
from __future__ import annotations

import pytest

from domain.tax.templates.inputs import CITTier, TaxDepreciationRule
from domain.tax.templates.calculations import (
    calculate_progressive_cit,
    get_tax_depreciation_rate,
    calculate_tax_depreciation_keur,
    calculate_taxable_income_keur,
)
from domain.tax.templates.registry import HR_SIMPLE_2026, ME_INFRA_2026


# ── calculate_progressive_cit ─────────────────────────────────────────────────

class TestFlatCIT:
    def test_flat_10pct(self):
        tiers = (CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=0.10),)
        assert calculate_progressive_cit(1000.0, tiers) == 100.0

    def test_flat_on_0_profit(self):
        tiers = (CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=0.10),)
        assert calculate_progressive_cit(0.0, tiers) == 0.0

    def test_flat_on_negative_profit(self):
        tiers = (CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=0.10),)
        assert calculate_progressive_cit(-500.0, tiers) == 0.0


class TestProgressiveCIT:
    def test_me_progressive_9_15_pct(self):
        """ME-style progressive: 9% up to 100k, 15% above."""
        tiers = (
            CITTier(min_profit_keur=0.0, max_profit_keur=100_000.0, tax_rate=0.09),
            CITTier(min_profit_keur=100_000.0, max_profit_keur=None, tax_rate=0.15),
        )
        # 100k × 9% = 9,000; remainder 50k × 15% = 7,500 → total 16,500
        assert calculate_progressive_cit(150_000.0, tiers) == 16_500.0

    def test_profit_in_first_tier_only(self):
        tiers = (
            CITTier(min_profit_keur=0.0, max_profit_keur=100_000.0, tax_rate=0.09),
            CITTier(min_profit_keur=100_000.0, max_profit_keur=None, tax_rate=0.15),
        )
        assert calculate_progressive_cit(50_000.0, tiers) == 4_500.0

    def test_exact_tier_boundary(self):
        tiers = (
            CITTier(min_profit_keur=0.0, max_profit_keur=100_000.0, tax_rate=0.09),
            CITTier(min_profit_keur=100_000.0, max_profit_keur=None, tax_rate=0.15),
        )
        # At exactly 100k — first tier fully used, second tier starts at 0
        result = calculate_progressive_cit(100_000.0, tiers)
        assert result == 9_000.0

    def test_three_tier_progressive(self):
        tiers = (
            CITTier(min_profit_keur=0.0, max_profit_keur=200.0, tax_rate=0.10),
            CITTier(min_profit_keur=200.0, max_profit_keur=500.0, tax_rate=0.12),
            CITTier(min_profit_keur=500.0, max_profit_keur=None, tax_rate=0.20),
        )
        # Tier widths: 0-200=200, 200-500=300, 500-600=100
        # Profit=600: 200×10%=20, 300×12%=36, 100×20%=20 → total=76
        assert calculate_progressive_cit(600.0, tiers) == 76.0

    def test_empty_tiers_returns_zero(self):
        assert calculate_progressive_cit(1000.0, ()) == 0.0


# ── get_tax_depreciation_rate ─────────────────────────────────────────────────

class TestGetTaxDepreciationRate:
    def test_non_deductible_returns_zero(self):
        rule = TaxDepreciationRule(
            asset_category="land",
            method="straight_line",
            annual_rate=0.05,
            useful_life_years=20.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=False,
            notes="land",
        )
        assert get_tax_depreciation_rate(rule) == 0.0

    def test_annual_rate_direct(self):
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="declining_balance",
            annual_rate=0.25,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="DB 25%",
        )
        assert get_tax_depreciation_rate(rule) == 0.25

    def test_useful_life_derived_rate(self):
        rule = TaxDepreciationRule(
            asset_category="buildings",
            method="straight_line",
            annual_rate=None,
            useful_life_years=20.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="20-year straight-line",
        )
        assert get_tax_depreciation_rate(rule) == pytest.approx(0.05)

    def test_useful_life_derived_rate_5_year(self):
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="5-year straight-line",
        )
        assert get_tax_depreciation_rate(rule) == pytest.approx(0.20)

    def test_me_infrastructure_2p5_cap(self):
        """ME infrastructure: 20y asset (5%) but capped at 2.5%."""
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        assert infra_rule is not None
        rate = get_tax_depreciation_rate(infra_rule)
        # Base rate from useful_life = 1/20 = 0.05; cap = 0.025
        assert rate == pytest.approx(0.025)
        assert rate < 0.05  # cap is binding

    def test_me_equipment_no_cap(self):
        """ME equipment: DB 25%, no cap."""
        eq_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "equipment"),
            None,
        )
        assert eq_rule is not None
        assert get_tax_depreciation_rate(eq_rule) == 0.25

    def test_hr_buildings_no_cap(self):
        """HR buildings: 20y SL, no cap."""
        bld_rule = next(
            (r for r in HR_SIMPLE_2026.depreciation_rules
             if r.asset_category == "buildings"),
            None,
        )
        assert bld_rule is not None
        assert get_tax_depreciation_rate(bld_rule) == pytest.approx(0.05)

    def test_hr_land_non_deductible(self):
        """HR land: non-deductible → rate 0."""
        land_rule = next(
            (r for r in HR_SIMPLE_2026.depreciation_rules
             if r.asset_category == "land"),
            None,
        )
        assert land_rule is not None
        assert get_tax_depreciation_rate(land_rule) == 0.0

    def test_no_rate_info_returns_zero(self):
        """Deductible but no annual_rate, no useful_life → 0."""
        rule = TaxDepreciationRule(
            asset_category="unknown",
            method="straight_line",
            annual_rate=None,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="no rate info",
        )
        assert get_tax_depreciation_rate(rule) == 0.0

    def test_zero_useful_life_not_used(self):
        """useful_life_years=0 should not be used to derive a rate."""
        rule = TaxDepreciationRule(
            asset_category="test",
            method="straight_line",
            annual_rate=None,
            useful_life_years=0.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="zero life",
        )
        # Should not divide by zero → returns 0.0 (no rate derivable)
        rate = get_tax_depreciation_rate(rule)
        assert rate == 0.0


# ── calculate_tax_depreciation_keur ─────────────────────────────────────────

class TestCalculateTaxDepreciation:
    def test_positive_cost_annual_rate(self):
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="declining_balance",
            annual_rate=0.25,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="",
        )
        assert calculate_tax_depreciation_keur(1000.0, rule) == 250.0

    def test_me_infrastructure_cap(self):
        """10M EUR asset with ME 2.5% cap → 250k EUR/year."""
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        # 10,000 kEUR cost (10M EUR = 10,000 kEUR)
        assert calculate_tax_depreciation_keur(10_000.0, infra_rule) == pytest.approx(250.0)

    def test_non_deductible_returns_zero(self):
        rule = TaxDepreciationRule(
            asset_category="land",
            method="straight_line",
            annual_rate=0.05,
            useful_life_years=20.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=False,
            notes="",
        )
        assert calculate_tax_depreciation_keur(1000.0, rule) == 0.0

    def test_zero_cost_returns_zero(self):
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=0.20,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="",
        )
        assert calculate_tax_depreciation_keur(0.0, rule) == 0.0

    def test_negative_cost_raises(self):
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=0.20,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="",
        )
        with pytest.raises(ValueError, match="asset_cost_keur must be >= 0"):
            calculate_tax_depreciation_keur(-100.0, rule)

    def test_no_mutation_of_rule(self):
        """Verify the rule object itself is not modified."""
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="declining_balance",
            annual_rate=0.25,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="original",
        )
        original_rate = get_tax_depreciation_rate(rule)
        calculate_tax_depreciation_keur(1000.0, rule)
        assert get_tax_depreciation_rate(rule) == original_rate


# ── calculate_taxable_income_keur ─────────────────────────────────────────────

class TestCalculateTaxableIncome:
    def test_basic_formula(self):
        result = calculate_taxable_income_keur(
            ebitda_keur=1000.0,
            deductible_interest_keur=200.0,
            tax_depreciation_keur=150.0,
        )
        assert result == 650.0

    def test_with_addbacks(self):
        result = calculate_taxable_income_keur(
            ebitda_keur=1000.0,
            deductible_interest_keur=200.0,
            tax_depreciation_keur=150.0,
            non_deductible_addbacks_keur=50.0,
        )
        assert result == 700.0

    def test_zero_interest(self):
        result = calculate_taxable_income_keur(
            ebitda_keur=500.0,
            deductible_interest_keur=0.0,
            tax_depreciation_keur=100.0,
        )
        assert result == 400.0

    def test_negative_taxable_income(self):
        """When deductions exceed EBITDA, taxable income can be negative."""
        result = calculate_taxable_income_keur(
            ebitda_keur=100.0,
            deductible_interest_keur=300.0,
            tax_depreciation_keur=200.0,
        )
        assert result == -400.0

    def test_all_defaults_zero(self):
        result = calculate_taxable_income_keur(
            ebitda_keur=0.0,
            deductible_interest_keur=0.0,
            tax_depreciation_keur=0.0,
        )
        assert result == 0.0

    def test_large_asset_me_infra_cap(self):
        """Large wind turbine: 10M EUR, 20y life, 2.5% cap → 250k EUR/yr deduction."""
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        dep = calculate_tax_depreciation_keur(10_000.0, infra_rule)  # 10M EUR = 10,000 kEUR
        taxable = calculate_taxable_income_keur(
            ebitda_keur=3_000.0,       # 3M EUR EBITDA
            deductible_interest_keur=500.0,
            tax_depreciation_keur=dep,
        )
        # EBITDA 3M - interest 500k - dep 250k = 2,250 kEUR
        assert taxable == 2_250.0