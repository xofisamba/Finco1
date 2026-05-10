"""Phase 6A tests for tax template registry."""
from __future__ import annotations

import pytest

from domain.tax.templates.registry import get_builtin_tax_templates, HR_SIMPLE_2026, ME_INFRA_2026


class TestGetBuiltinTaxTemplates:
    def test_returns_tuple(self):
        templates = get_builtin_tax_templates()
        assert isinstance(templates, tuple)

    def test_hr_template_exists(self):
        templates = get_builtin_tax_templates()
        codes = {t.country_code for t in templates}
        assert "HR" in codes

    def test_me_template_exists(self):
        templates = get_builtin_tax_templates()
        codes = {t.country_code for t in templates}
        assert "ME" in codes

    def test_hr_template_name(self):
        templates = get_builtin_tax_templates()
        hr = next(t for t in templates if t.country_code == "HR")
        assert "2026" in hr.template_name

    def test_me_template_name(self):
        templates = get_builtin_tax_templates()
        me = next(t for t in templates if t.country_code == "ME")
        assert "2026" in me.template_name

    def test_hr_flat_cit(self):
        assert len(HR_SIMPLE_2026.cit_tiers) == 1
        assert HR_SIMPLE_2026.cit_tiers[0].tax_rate == 0.10

    def test_me_progressive_cit(self):
        assert len(ME_INFRA_2026.cit_tiers) == 2
        assert ME_INFRA_2026.cit_tiers[0].tax_rate == 0.09
        assert ME_INFRA_2026.cit_tiers[1].tax_rate == 0.15

    def test_me_infrastructure_depreciation_cap(self):
        """ME infrastructure has 2.5% annual deductible cap."""
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        assert infra_rule is not None, "infrastructure rule not found"
        assert infra_rule.max_deductible_rate == 0.025, (
            f"Expected 0.025 (2.5%), got {infra_rule.max_deductible_rate}"
        )
        assert infra_rule.notes is not None and len(infra_rule.notes) > 0

    def test_me_infrastructure_useful_life_20y(self):
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        assert infra_rule is not None
        assert infra_rule.useful_life_years == 20.0

    def test_hr_interest_limitation_atad(self):
        """HR template has ATAD-compliant 30% EBITDA cap."""
        assert HR_SIMPLE_2026.interest_limitation_pct_ebitda == 0.30

    def test_me_thin_cap_ratio(self):
        """ME template has thin_cap_ratio = 4.0."""
        assert ME_INFRA_2026.thin_cap_ratio == 4.0

    def test_templates_are_immutable(self):
        """Builtin templates must be immutable (frozen dataclasses)."""
        templates = get_builtin_tax_templates()
        for t in templates:
            with pytest.raises(Exception):
                t.template_name = "mutated"

    def test_all_templates_illustrative(self):
        """All builtin templates must be marked as illustrative."""
        templates = get_builtin_tax_templates()
        for t in templates:
            note_values = [v for k, v in t.metadata if k == "note"]
            assert any("illustrative" in v.lower() for v in note_values), (
                f"Template {t.template_name} not marked as illustrative"
            )
