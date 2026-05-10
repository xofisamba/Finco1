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


# ── ResolvedTemplate exposure ─────────────────────────────────────────────────

class TestResolvedTemplateExposure:
    def test_no_overrides_resolved_template_equals_base(self):
        tpl = _hr_template()
        result = resolve_tax_template(tpl, ())
        # resolved_template equals base_template in value
        # (object identity not preserved due to metadata reconstruction)
        assert result.resolved_template == result.base_template
        assert result.resolved_template.country_code == tpl.country_code

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

    def test_top_level_override_in_resolved_template(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="custom_wht",
            field_path="withholding_tax_interest",
            override_value=0.05,
            reason="Treaty rate",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert result.resolved_template.withholding_tax_interest == 0.05
        assert result.base_template.withholding_tax_interest == 0.0

    def test_resolved_template_is_frozen(self):
        tpl = _hr_template()
        result = resolve_tax_template(tpl, ())
        with pytest.raises(Exception):
            result.resolved_template.template_name = "mutated"


# ── Metadata key overrides ────────────────────────────────────────────────────

class TestMetadataKeyOverrides:
    def test_metadata_note_override(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="custom_note",
            field_path="metadata.note",
            override_value="custom override note",
            reason="User specified",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert result.resolved_metadata_dict["note"] == "custom override note"

    def test_metadata_new_key_override(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="add_key",
            field_path="metadata.source",
            override_value="user_defined",
            reason="custom source",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert result.resolved_metadata_dict["source"] == "user_defined"
        # Original metadata still present
        assert "note" in result.resolved_metadata_dict

    def test_metadata_key_override_base_unchanged(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="custom_note",
            field_path="metadata.note",
            override_value="custom override note",
            reason="User specified",
        )
        resolve_tax_template(tpl, (ov,))
        # Base template metadata is unchanged
        base_note = dict(tpl.metadata).get("note", "")
        assert "illustrative" in base_note.lower()

    def test_metadata_key_override_preserves_other_base_metadata(self):
        tpl = _hr_template()
        # Add an extra metadata key to base template
        tpl_with_extra = TaxTemplate(
            country_code="HR", template_name="T", tax_year=2026,
            metadata=(("note", "test note"), ("author", "test author")),
        )
        ov = TaxTemplateOverride(
            override_name="override_note",
            field_path="metadata.note",
            override_value="overridden",
            reason="test",
        )
        result = resolve_tax_template(tpl_with_extra, (ov,))
        assert result.resolved_metadata_dict["note"] == "overridden"
        assert result.resolved_metadata_dict["author"] == "test author"


# ── Invalid field paths at resolve time ──────────────────────────────────────

class TestInvalidFieldPaths:
    def test_invalid_top_level_field_raises(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="bad",
            field_path="nonexistent_field",
            override_value=0.05,
            reason="test",
        )
        with pytest.raises(ValueError, match="Invalid override field_path"):
            resolve_tax_template(tpl, (ov,))

    def test_nested_non_metadata_path_raises_at_resolve(self):
        """TaxTemplateOverride construction allows 'metadata.<key>' only.
        A path like 'cit_tiers.0.tax_rate' is rejected at construction time."""
        with pytest.raises(ValueError, match="not supported"):
            TaxTemplateOverride(
                override_name="nested",
                field_path="cit_tiers.0.tax_rate",
                override_value=0.05,
                reason="test",
            )

    def test_bare_metadata_dot_raises_at_construction(self):
        with pytest.raises(ValueError, match="non-empty key"):
            TaxTemplateOverride(
                override_name="bare_meta_dot",
                field_path="metadata.",
                override_value="value",
                reason="test",
            )


# ── Last override wins ────────────────────────────────────────────────────────

class TestLastOverrideWins:
    def test_duplicate_top_level_field_last_wins(self):
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
        assert result.resolved_template.withholding_tax_interest == 0.07

    def test_duplicate_metadata_key_last_wins(self):
        tpl = _hr_template()
        ov1 = TaxTemplateOverride(
            override_name="first",
            field_path="metadata.note",
            override_value="first value",
            reason="first",
        )
        ov2 = TaxTemplateOverride(
            override_name="second",
            field_path="metadata.note",
            override_value="second value",
            reason="second",
        )
        result = resolve_tax_template(tpl, (ov1, ov2))
        assert result.resolved_metadata_dict["note"] == "second value"


# ── Resolved metadata ─────────────────────────────────────────────────────────

class TestResolvedMetadata:
    def test_resolved_metadata_dict_property(self):
        tpl = _hr_template()
        result = resolve_tax_template(tpl, ())
        assert isinstance(result.resolved_metadata_dict, dict)

    def test_metadata_override_whole_field_still_works(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="whole_meta",
            field_path="metadata",
            override_value={"custom": "user_value"},
            reason="test",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert result.resolved_metadata_dict["custom"] == "user_value"


# ── ResolvedConfig immutability ──────────────────────────────────────────────

class TestResolvedConfigImmutable:
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

    def test_resolved_metadata_is_tuple_of_tuples(self):
        tpl = _hr_template()
        result = resolve_tax_template(tpl, ())
        assert isinstance(result.resolved_metadata, tuple)
        for item in result.resolved_metadata:
            assert isinstance(item, tuple)
            assert len(item) == 2


# ── Edge cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_overrides_tuple(self):
        tpl = _hr_template()
        result = resolve_tax_template(tpl, ())
        assert result.overrides == ()
        # value equality (object identity not preserved due to metadata reconstruction)
        assert result.resolved_template == tpl

    def test_cit_tiers_override(self):
        tpl = _hr_template()
        new_tiers = (
            CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=0.08),
        )
        ov = TaxTemplateOverride(
            override_name="lower_cit",
            field_path="cit_tiers",
            override_value=new_tiers,
            reason="temporary rate",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert result.resolved_template.cit_tiers[0].tax_rate == 0.08

    def test_thin_cap_override(self):
        tpl = _hr_template()
        ov = TaxTemplateOverride(
            override_name="relax_thin_cap",
            field_path="thin_cap_ratio",
            override_value=5.0,
            reason="Project finance",
        )
        result = resolve_tax_template(tpl, (ov,))
        assert result.resolved_template.thin_cap_ratio == 5.0

    def test_combined_top_level_and_metadata_key_override(self):
        tpl = _hr_template()
        ov1 = TaxTemplateOverride(
            override_name="wht",
            field_path="withholding_tax_interest",
            override_value=0.05,
            reason="Treaty rate",
        )
        ov2 = TaxTemplateOverride(
            override_name="meta_note",
            field_path="metadata.note",
            override_value="overridden note",
            reason="User specified",
        )
        result = resolve_tax_template(tpl, (ov1, ov2))
        assert result.resolved_template.withholding_tax_interest == 0.05
        assert result.resolved_metadata_dict["note"] == "overridden note"