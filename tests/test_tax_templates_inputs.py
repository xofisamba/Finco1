"""Phase 6A tests for tax template inputs."""
from __future__ import annotations

import pytest

from domain.tax.templates.inputs import (
    CITTier,
    TaxDepreciationRule,
    TaxTemplate,
    TaxTemplateOverride,
    ResolvedTaxConfig,
)


# ── CITTier validation ────────────────────────────────────────────────────────

class TestCITTierValidation:
    def test_valid_flat_tier(self):
        t = CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=0.10)
        assert t.tax_rate == 0.10
        assert t.max_profit_keur is None

    def test_valid_bounded_tier(self):
        t = CITTier(min_profit_keur=0.0, max_profit_keur=500.0, tax_rate=0.10)
        assert t.max_profit_keur == 500.0

    def test_invalid_negative_min_profit(self):
        with pytest.raises(ValueError, match="min_profit_keur must be >= 0"):
            CITTier(min_profit_keur=-100.0, max_profit_keur=None, tax_rate=0.10)

    def test_invalid_tax_rate_below_0(self):
        with pytest.raises(ValueError, match="tax_rate must be between 0 and 1"):
            CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=-0.01)

    def test_invalid_tax_rate_above_1(self):
        with pytest.raises(ValueError, match="tax_rate must be between 0 and 1"):
            CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=1.01)

    def test_invalid_max_less_than_min(self):
        with pytest.raises(ValueError, match="max_profit_keur.*must be > min"):
            CITTier(min_profit_keur=500.0, max_profit_keur=100.0, tax_rate=0.15)

    def test_invalid_max_equals_min(self):
        with pytest.raises(ValueError, match="max_profit_keur.*must be > min"):
            CITTier(min_profit_keur=500.0, max_profit_keur=500.0, tax_rate=0.15)


# ── TaxDepreciationRule validation ───────────────────────────────────────────

class TestTaxDepreciationRuleValidation:
    def test_valid_rule(self):
        r = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="5-year equipment",
        )
        assert r.asset_category == "equipment"
        assert r.deductible is True

    def test_valid_with_max_deductible_rate(self):
        r = TaxDepreciationRule(
            asset_category="infrastructure",
            method="straight_line",
            annual_rate=None,
            useful_life_years=20.0,
            max_deductible_rate=0.025,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="2.5% cap",
        )
        assert r.max_deductible_rate == 0.025

    def test_valid_non_deductible(self):
        r = TaxDepreciationRule(
            asset_category="land",
            method="straight_line",
            annual_rate=0.0,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=False,
            notes="non-deductible land",
        )
        assert r.deductible is False

    def test_invalid_negative_max_deductible_rate(self):
        with pytest.raises(ValueError, match="max_deductible_rate must be >= 0"):
            TaxDepreciationRule(
                asset_category="x",
                method="straight_line",
                annual_rate=None,
                useful_life_years=5.0,
                max_deductible_rate=-0.1,
                bonus_depreciation_pct=0.0,
                deductible=True,
                notes="",
            )

    def test_invalid_bonus_out_of_range(self):
        with pytest.raises(ValueError, match="bonus_depreciation_pct must be between 0 and 1"):
            TaxDepreciationRule(
                asset_category="x",
                method="straight_line",
                annual_rate=None,
                useful_life_years=5.0,
                max_deductible_rate=None,
                bonus_depreciation_pct=1.5,  # invalid
                deductible=True,
                notes="",
            )


# ── TaxTemplate validation ───────────────────────────────────────────────────

class TestTaxTemplateValidation:
    def test_valid_minimal_template(self):
        t = TaxTemplate(
            country_code="HR",
            template_name="Test",
            tax_year=2026,
        )
        assert t.country_code == "HR"
        assert t.withholding_tax_dividends == 0.0

    def test_invalid_empty_country_code(self):
        with pytest.raises(ValueError, match="country_code must be non-empty"):
            TaxTemplate(country_code="", template_name="Test", tax_year=2026)

    def test_invalid_country_code_too_long(self):
        with pytest.raises(ValueError, match="country_code must be 2 characters"):
            TaxTemplate(country_code="HRV", template_name="Test", tax_year=2026)

    def test_invalid_country_code_lowercase(self):
        with pytest.raises(ValueError, match="country_code must be uppercase"):
            TaxTemplate(country_code="hr", template_name="Test", tax_year=2026)

    def test_invalid_wht_dividends_out_of_range(self):
        with pytest.raises(ValueError, match="withholding_tax_dividends must be 0-1"):
            TaxTemplate(
                country_code="HR", template_name="Test", tax_year=2026,
                withholding_tax_dividends=-0.01,
            )

    def test_invalid_wht_interest_out_of_range(self):
        with pytest.raises(ValueError, match="withholding_tax_interest must be 0-1"):
            TaxTemplate(
                country_code="HR", template_name="Test", tax_year=2026,
                withholding_tax_interest=2.0,
            )

    def test_duplicate_depreciation_asset_category(self):
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=None, useful_life_years=5.0,
            max_deductible_rate=None, bonus_depreciation_pct=0.0,
            deductible=True, notes="",
        )
        with pytest.raises(ValueError, match="duplicate asset_category"):
            TaxTemplate(
                country_code="HR", template_name="Test", tax_year=2026,
                depreciation_rules=(rule, rule),
            )

    def test_overlapping_cit_tiers_rejected(self):
        t1 = CITTier(min_profit_keur=0.0, max_profit_keur=500.0, tax_rate=0.10)
        t2 = CITTier(min_profit_keur=400.0, max_profit_keur=None, tax_rate=0.15)  # overlaps at 400-500
        with pytest.raises(ValueError, match="overlap"):
            TaxTemplate(
                country_code="HR", template_name="Test", tax_year=2026,
                cit_tiers=(t1, t2),
            )

    def test_metadata_dict_property(self):
        t = TaxTemplate(
            country_code="HR", template_name="Test", tax_year=2026,
            metadata=(("note", "test"), ("author", "me")),
        )
        assert t.metadata_dict == {"note": "test", "author": "me"}

    def test_metadata_accepts_dict(self):
        t = TaxTemplate(
            country_code="HR", template_name="Test", tax_year=2026,
            metadata={"note": "test"},
        )
        assert t.metadata_dict == {"note": "test"}


# ── TaxTemplateOverride validation ──────────────────────────────────────────

class TestTaxTemplateOverrideValidation:
    def test_valid_override(self):
        o = TaxTemplateOverride(
            override_name="custom_wht",
            field_path="withholding_tax_dividends",
            override_value=0.05,
            reason="Treaty rate",
        )
        assert o.override_name == "custom_wht"

    def test_empty_field_path_rejected(self):
        with pytest.raises(ValueError, match="field_path must be non-empty"):
            TaxTemplateOverride(
                override_name="x",
                field_path="",
                override_value=0.05,
                reason="",
            )

    def test_nested_field_path_rejected(self):
        with pytest.raises(ValueError, match="nested field_path.*not yet supported"):
            TaxTemplateOverride(
                override_name="x",
                field_path="cit_tiers.0.tax_rate",
                override_value=0.08,
                reason="",
            )


# ── ResolvedTaxConfig ─────────────────────────────────────────────────────────

class TestResolvedTaxConfig:
    def test_metadata_dict_property(self):
        t = TaxTemplate(country_code="HR", template_name="T", tax_year=2026)
        r = ResolvedTaxConfig(
            base_template=t,
            overrides=(),
            resolved_metadata=(("note", "test"),),
        )
        assert r.resolved_metadata_dict == {"note": "test"}

    def test_overrides_tuple_normalized(self):
        t = TaxTemplate(country_code="HR", template_name="T", tax_year=2026)
        o = TaxTemplateOverride("a", "withholding_tax_dividends", 0.05, "r")
        r = ResolvedTaxConfig(
            base_template=t,
            overrides=[o],  # list input
            resolved_metadata=(),
        )
        assert isinstance(r.overrides, tuple)
