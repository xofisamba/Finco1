"""Phase 6D.2 — Tests for tax assumptions snapshot models and builders."""
import pytest
from datetime import datetime, timezone

from domain.tax.templates.inputs import (
    CITTier,
    TaxDepreciationRule,
    TaxTemplate,
    TaxTemplateOverride,
    ResolvedTaxConfig,
)
from domain.tax.templates.resolver import resolve_tax_template
from domain.tax.assumptions_snapshot import (
    TaxAssumptionSnapshot,
    TaxTemplateSnapshot,
    TaxOverrideSnapshot,
    ResolvedTaxConfigSnapshot,
)
from domain.tax.snapshot_builders import (
    build_tax_assumption_snapshot,
    build_tax_template_snapshot,
    build_tax_override_snapshot,
    build_resolved_tax_config_snapshot,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def flat_template():
    return TaxTemplate(
        country_code="HR",
        template_name="HR Flat 18%",
        tax_year=2026,
        cit_tiers=(CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=0.18),),
        depreciation_rules=(
            TaxDepreciationRule(
                asset_category="buildings", method="straight_line",
                annual_rate=0.05, useful_life_years=20.0, max_deductible_rate=0.025,
                bonus_depreciation_pct=0.0, deductible=True, notes="20yr buildings",
            ),
        ),
        withholding_tax_dividends=0.12,
        withholding_tax_interest=0.0,
        loss_carryforward_years=5,
        thin_cap_ratio=4.0,
        interest_limitation_pct_ebitda=0.30,
        metadata=(("notes", "standard HR"),),
    )


@pytest.fixture
def progressive_template():
    return TaxTemplate(
        country_code="ME",
        template_name="ME Progressive",
        tax_year=2026,
        cit_tiers=(
            CITTier(min_profit_keur=0.0, max_profit_keur=500.0, tax_rate=0.10),
            CITTier(min_profit_keur=500.0, max_profit_keur=None, tax_rate=0.15),
        ),
        depreciation_rules=(),
        withholding_tax_dividends=0.0,
        withholding_tax_interest=0.0,
        loss_carryforward_years=None,
        thin_cap_ratio=None,
        interest_limitation_pct_ebitda=None,
        metadata=(),
    )


@pytest.fixture
def override(flat_template):
    return TaxTemplateOverride(
        override_name="custom_wht",
        field_path="withholding_tax_dividends",
        override_value=0.10,
        reason="Treaty rate HR-ME",
    )


@pytest.fixture
def resolved_config(flat_template, override):
    return resolve_tax_template(flat_template, (override,))


# ── Test builders: HR template ────────────────────────────────────────────────

class TestBuildTaxTemplateSnapshot:
    def test_hr_template_snapshot(self, flat_template):
        snap = build_tax_template_snapshot(flat_template)
        assert isinstance(snap, TaxTemplateSnapshot)
        assert snap.template_name == "HR Flat 18%"
        assert snap.country_code == "HR"
        assert snap.tax_year == 2026
        assert snap.cit_structure == "Flat"
        assert snap.cit_tiers_summary == ("18%",)
        assert snap.loss_carryforward_years == 5
        assert snap.has_interest_limitation is True
        assert snap.has_wht_dividend is True
        assert snap.has_wht_interest is False
        assert snap.depreciation_rules_summary == ("buildings: straight_line: 20yr",)

    def test_hr_template_snapshot_frozen(self, flat_template):
        snap = build_tax_template_snapshot(flat_template)
        with pytest.raises(AttributeError):
            snap.template_name = "Changed"

    def test_snapshot_audit_note(self, flat_template):
        snap = build_tax_template_snapshot(flat_template)
        assert "AUDIT-ONLY" in snap.audit_note


class TestBuildTaxTemplateSnapshotME:
    def test_me_template_snapshot(self, progressive_template):
        snap = build_tax_template_snapshot(progressive_template)
        assert isinstance(snap, TaxTemplateSnapshot)
        assert snap.country_code == "ME"
        assert snap.cit_structure == "Progressive"
        assert snap.cit_tiers_summary == ("10%", "15%")
        assert snap.has_interest_limitation is False


class TestBuildTaxOverrideSnapshot:
    def test_override_snapshot(self, override):
        snap = build_tax_override_snapshot(override)
        assert isinstance(snap, TaxOverrideSnapshot)
        assert snap.override_name == "custom_wht"
        assert snap.field_path == "withholding_tax_dividends"
        assert snap.override_value == 0.10
        assert snap.reason == "Treaty rate HR-ME"

    def test_override_snapshot_frozen(self, override):
        snap = build_tax_override_snapshot(override)
        with pytest.raises(AttributeError):
            snap.override_value = 99.0

    def test_metadata_key_override(self, flat_template):
        meta_override = TaxTemplateOverride(
            override_name="meta_note",
            field_path="metadata.note",
            override_value="custom note",
            reason="User override",
        )
        snap = build_tax_override_snapshot(meta_override)
        assert snap.field_path == "metadata.note"
        assert snap.override_value == "custom note"


class TestBuildResolvedTaxConfigSnapshot:
    def test_resolved_config_snapshot(self, resolved_config):
        snap = build_resolved_tax_config_snapshot(resolved_config)
        assert isinstance(snap, ResolvedTaxConfigSnapshot)
        assert snap.template_name == "HR Flat 18%"
        assert snap.country_code == "HR"
        assert snap.override_count == 1
        assert snap.effective_cit_structure == "Flat"
        assert len(snap.overrides_summary) == 1
        assert "withholding_tax_dividends" in snap.overrides_summary[0]

    def test_resolved_config_snapshot_frozen(self, resolved_config):
        snap = build_resolved_tax_config_snapshot(resolved_config)
        with pytest.raises(AttributeError):
            snap.override_count = 99

    def test_resolved_config_snapshot_no_overrides(self, flat_template):
        resolved = resolve_tax_template(flat_template, ())
        snap = build_resolved_tax_config_snapshot(resolved)
        assert snap.override_count == 0


class TestBuildTaxAssumptionSnapshot:
    def test_top_level_snapshot(self, flat_template, override, resolved_config):
        snap = build_tax_assumption_snapshot(
            templates=(flat_template,),
            resolved_configs=(resolved_config,),
            overrides=(override,),
            snapshot_label="Test v1",
        )
        assert isinstance(snap, TaxAssumptionSnapshot)
        assert snap.snapshot_label == "Test v1"
        assert len(snap.template_snapshots) == 1
        assert len(snap.override_snapshots) == 1
        assert len(snap.resolved_config_snapshots) == 1

    def test_snapshot_stores_original_objects(self, flat_template, resolved_config, override):
        snap = build_tax_assumption_snapshot(
            templates=(flat_template,),
            resolved_configs=(resolved_config,),
            overrides=(override,),
        )
        # Original TaxTemplate objects preserved
        assert snap.templates == (flat_template,)
        assert snap.resolved_configs == (resolved_config,)
        assert snap.overrides == (override,)

    def test_snapshot_frozen(self, flat_template):
        snap = build_tax_assumption_snapshot(templates=(flat_template,))
        with pytest.raises(AttributeError):
            snap.snapshot_label = "Hacked"

    def test_snapshot_has_properties(self, flat_template, override):
        snap = build_tax_assumption_snapshot(
            templates=(flat_template,),
            overrides=(override,),
        )
        assert snap.has_templates is True
        assert snap.has_overrides is True
        assert snap.has_resolved_configs is False

    def test_snapshot_empty_inputs(self):
        snap = build_tax_assumption_snapshot(
            templates=(),
            resolved_configs=(),
            overrides=(),
        )
        assert snap.has_templates is False
        assert snap.has_overrides is False
        assert snap.has_resolved_configs is False

    def test_snapshot_audit_note(self, flat_template):
        snap = build_tax_assumption_snapshot(templates=(flat_template,))
        assert "AUDIT-ONLY" in snap.audit_note

    def test_snapshot_created_at_is_datetime(self, flat_template):
        snap = build_tax_assumption_snapshot(templates=(flat_template,))
        assert isinstance(snap.created_at, datetime)
