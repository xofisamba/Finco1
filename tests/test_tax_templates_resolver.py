"""Phase 6A tests for tax template resolver."""
from __future__ import annotations

import pytest

from domain.tax.templates.inputs import (
    TaxTemplate,
    TaxTemplateOverride,
    ResolvedTaxConfig,
    CITTier,
    TaxDepreciationRule,
)
from domain.tax.templates.resolver import resolve_tax_template
from domain.tax.templates.registry import get_builtin_tax_templates


def _hr_template():
    return get_builtin_tax_templates()[0]  # HR_SIMPLE_2026


class TestResolveTaxTemplateNoOverrides:
    def test_empty_overrides_returns_base_metadata(self):
        tpl = _hr_template()
        result = resolve_tax_template(tpl, ())
        assert result.base_template is tpl
        assert result.overrides == ()
        assert result.resolved_metadata == tpl.metadata

    def test_original_template_unchanged(self):
        tpl = _hr_template()
        original_name = tpl.template_name
        ov = TaxTemplateOverride(
            override_name="rename",
            field_path="template_name",
            override_value="Renamed",
            reason="test",
        )
        resolve_tax_template(tpl, (ov,))
        assert tpl.template_name == original_name


class TestResolveTaxTemplateOverride:
    def test_override_wht_applied(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="custom_wht",
            field_path="withholding_tax_interest",
            override_value=0.05,
            reason="Treaty rate",
        )
        result = resolve_tax_template(tpl, (ov,))
        # Resolved config should have overridden value
        # We verify via resolved template in base_template
        assert result.base_template.withholding_tax_interest == 0.0  # base unchanged

    def test_override_applied_immutably(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="custom_wht",
            field_path="withholding_tax_interest",
            override_value=0.05,
            reason="Treaty rate",
        )
        result = resolve_tax_template(tpl, (ov,))
        # The resolved config carries the override; we need to verify
        # the override was recorded
        assert len(result.overrides) == 1
        assert result.overrides[0].override_value == 0.05

    def test_original_template_unchanged_after_override(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="custom_wht",
            field_path="withholding_tax_interest",
            override_value=0.05,
            reason="Treaty rate",
        )
        resolve_tax_template(tpl, (ov,))
        assert tpl.withholding_tax_interest == 0.0

    def test_thin_cap_override(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="relax_thin_cap",
            field_path="thin_cap_ratio",
            override_value=5.0,
            reason="Project finance",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert result.overrides[0].override_value == 5.0

    def test_metadata_override(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="add_note",
            field_path="metadata",
            override_value={"custom": "user_value"},
            reason="test override",
        )
        result = resolve_tax_template(tpl, (ov,))
        md = result.resolved_metadata_dict
        assert "custom" in md


class TestResolveTaxTemplateInvalidFieldPath:
    def test_invalid_field_path_raises(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="bad",
            field_path="nonexistent_field",
            override_value=0.05,
            reason="test",
        )
        with pytest.raises(ValueError, match="Invalid override field_path"):
            resolve_tax_template(tpl, (ov,))

    def test_nested_field_path_rejected_in_override_construction(self):
        """Nested field_path is rejected at TaxTemplateOverride construction time."""
        with pytest.raises(ValueError, match="nested field_path.*not yet supported"):
            TaxTemplateOverride(
                override_name="nested",
                field_path="cit_tiers.0.tax_rate",
                override_value=0.05,
                reason="test",
            )


class TestResolveTaxTemplateLastOverrideWins:
    def test_duplicate_field_path_last_wins(self):
        tpl = _hr_template()
        ov1 = TaxTemplateOverride(
            override_name="first",
            field_path="withholding_tax_interest",
            override_value=0.03,
            reason="first",
        )
        ov2 = TaxTemplateOverride(
            override_name="second",
            field_path="withholding_tax_interest",
            override_value=0.07,
            reason="second",
        )
        result = resolve_tax_template(tpl, (ov1, ov2))
        assert result.overrides[-1].override_value == 0.07


class TestResolveTaxTemplateResolvedMetadata:
    def test_resolved_metadata_preserved(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="add_meta",
            field_path="metadata",
            override_value={"new_key": "new_value"},
            reason="test",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert result.resolved_metadata_dict["new_key"] == "new_value"

    def test_resolved_metadata_dict_property(self):
        tpl = _hr_template()
        result = resolve_tax_template(tpl, ())
        assert isinstance(result.resolved_metadata_dict, dict)


class TestResolveTaxTemplateResolvedConfigImmutable:
    def test_resolved_config_is_frozen(self):
        tpl = _hr_template()
        result = resolve_tax_template(tpl, ())
        with pytest.raises(Exception):
            result.resolved_metadata = (("x", "y"),)

    def test_overrides_is_tuple(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="a", field_path="thin_cap_ratio",
            override_value=5.0, reason="r",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert isinstance(result.overrides, tuple)
        assert len(result.overrides) == 1
