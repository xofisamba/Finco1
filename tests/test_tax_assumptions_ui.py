"""Phase 6D.1 — Tests for tax assumptions UI helpers."""
import pytest

from domain.tax.templates.inputs import (
    CITTier,
    TaxDepreciationRule,
    TaxTemplate,
    TaxTemplateOverride,
    ResolvedTaxConfig,
)
from domain.tax.templates.resolver import resolve_tax_template
from app.tax_assumptions_ui import (
    build_tax_template_summary_table,
    build_tax_template_tiers_table,
    build_tax_depreciation_rules_table,
    build_tax_override_table,
    build_resolved_tax_config_summary,
    build_tax_assumptions_audit_note,
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
                bonus_depreciation_pct=0.0, deductible=True, notes="20-year buildings HR",
            ),
        ),
        withholding_tax_dividends=0.12,
        withholding_tax_interest=0.0,
        loss_carryforward_years=5,
        thin_cap_ratio=4.0,
        interest_limitation_pct_ebitda=0.30,
        metadata=(("notes", "standard HR template"),),
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
def template_with_dep_rules():
    return TaxTemplate(
        country_code="BA",
        template_name="BA Solar",
        tax_year=2026,
        cit_tiers=(
            CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=0.10),
        ),
        depreciation_rules=(
            TaxDepreciationRule(
                asset_category="buildings", method="straight_line",
                annual_rate=0.05, useful_life_years=20.0, max_deductible_rate=0.025,
                bonus_depreciation_pct=0.0, deductible=True, notes="buildings BA",
            ),
            TaxDepreciationRule(
                asset_category="equipment", method="declining_balance",
                annual_rate=0.25, useful_life_years=None, max_deductible_rate=None,
                bonus_depreciation_pct=0.0, deductible=True, notes="equipment DB",
            ),
            TaxDepreciationRule(
                asset_category="solar_panels", method="straight_line",
                annual_rate=0.0625, useful_life_years=16.0, max_deductible_rate=None,
                bonus_depreciation_pct=0.0, deductible=True, notes="solar panels BA",
            ),
        ),
        withholding_tax_dividends=0.0,
        withholding_tax_interest=0.0,
        loss_carryforward_years=5,
        thin_cap_ratio=None,
        interest_limitation_pct_ebitda=None,
        metadata=(),
    )


@pytest.fixture
def resolved_config(flat_template):
    override = TaxTemplateOverride(
        override_name="custom_wht_2027",
        field_path="withholding_tax_dividends",
        override_value=0.10,
        reason="Treaty rate HR-ME",
    )
    return resolve_tax_template(flat_template, (override,))


# ── Tests ────────────────────────────────────────────────────────────────────

class TestBuildTaxAssumptionsAuditNote:
    def test_returns_string(self):
        note = build_tax_assumptions_audit_note()
        assert isinstance(note, str)

    def test_contains_audit_only(self):
        note = build_tax_assumptions_audit_note()
        assert "AUDIT-ONLY" in note

    def test_contains_visibility_governance(self):
        note = build_tax_assumptions_audit_note()
        assert "visibility" in note.lower() or "governance" in note.lower()


class TestBuildTaxTemplateSummaryTable:
    def test_flat_template_summary(self, flat_template):
        rows = build_tax_template_summary_table((flat_template,))
        assert len(rows) == 1
        row = rows[0]
        assert row["Template Code"] == "HR Flat 18%"
        assert row["Country Code"] == "HR"
        assert row["Tax Year"] == 2026
        assert row["CIT Structure"] == "Flat"
        assert row["Base CIT Rate"] == 0.18
        assert row["Progressive Tiers Count"] == 1
        assert row["Loss Carryforward Years"] == 5
        assert row["Has Interest Limitation"] is True
        assert row["Has WHT Dividend"] is True
        assert row["Has WHT Interest"] is False

    def test_progressive_template_summary(self, progressive_template):
        rows = build_tax_template_summary_table((progressive_template,))
        assert len(rows) == 1
        row = rows[0]
        assert row["CIT Structure"] == "Progressive"
        assert row["Progressive Tiers Count"] == 2

    def test_multiple_templates(self, flat_template, progressive_template):
        rows = build_tax_template_summary_table((flat_template, progressive_template))
        assert len(rows) == 2

    def test_no_cit_shows_none(self, template_with_dep_rules):
        # template_with_dep_rules has one tier at 10%, so it's "Flat"
        rows = build_tax_template_summary_table((template_with_dep_rules,))
        assert rows[0]["CIT Structure"] == "Flat"

    def test_no_mutation(self, flat_template):
        original_name = flat_template.template_name
        build_tax_template_summary_table((flat_template,))
        assert flat_template.template_name == original_name


class TestBuildTaxTemplateTiersTable:
    def test_flat_single_tier(self, flat_template):
        rows = build_tax_template_tiers_table(flat_template)
        assert len(rows) == 1
        assert rows[0]["Tier #"] == 1
        assert rows[0]["Min Profit (kEUR)"] == 0.0
        assert rows[0]["Max Profit (kEUR)"] == "Unlimited"
        assert rows[0]["Tax Rate"] == 0.18

    def test_progressive_two_tiers(self, progressive_template):
        rows = build_tax_template_tiers_table(progressive_template)
        assert len(rows) == 2
        assert rows[0]["Tier #"] == 1
        assert rows[0]["Min Profit (kEUR)"] == 0.0
        assert rows[0]["Max Profit (kEUR)"] == 500.0
        assert rows[0]["Tax Rate"] == 0.10
        assert rows[1]["Tier #"] == 2
        assert rows[1]["Min Profit (kEUR)"] == 500.0
        assert rows[1]["Max Profit (kEUR)"] == "Unlimited"
        assert rows[1]["Tax Rate"] == 0.15

    def test_unbounded_final_tier_display(self, flat_template):
        rows = build_tax_template_tiers_table(flat_template)
        assert rows[0]["Max Profit (kEUR)"] == "Unlimited"


class TestBuildTaxDepreciationRulesTable:
    def test_dep_rules_columns(self, template_with_dep_rules):
        rows = build_tax_depreciation_rules_table(template_with_dep_rules)
        expected_cols = ["Asset Category", "Method", "Useful Life",
                         "Annual Rate", "Max Deductible Rate", "Deductible", "Notes"]
        for col in expected_cols:
            assert col in rows[0], f"Missing column: {col}"

    def test_dep_rules_all_rows(self, template_with_dep_rules):
        rows = build_tax_depreciation_rules_table(template_with_dep_rules)
        assert len(rows) == 3
        categories = {r["Asset Category"] for r in rows}
        assert categories == {"buildings", "equipment", "solar_panels"}

    def test_dep_rules_values(self, template_with_dep_rules):
        rows = build_tax_depreciation_rules_table(template_with_dep_rules)
        buildings = next(r for r in rows if r["Asset Category"] == "buildings")
        assert buildings["Method"] == "straight_line"
        assert buildings["Annual Rate"] == 0.05
        assert buildings["Deductible"] is True

    def test_no_mutation(self, template_with_dep_rules):
        original = template_with_dep_rules.depreciation_rules[0].asset_category
        build_tax_depreciation_rules_table(template_with_dep_rules)
        assert template_with_dep_rules.depreciation_rules[0].asset_category == original


class TestBuildTaxOverrideTable:
    def test_override_table(self, flat_template):
        override = TaxTemplateOverride(
            override_name="custom_wht",
            field_path="withholding_tax_dividends",
            override_value=0.10,
            reason="Treaty rate",
        )
        rows = build_tax_override_table((override,))
        assert len(rows) == 1
        assert rows[0]["Override Path"] == "withholding_tax_dividends"
        assert rows[0]["Override Value"] == 0.10
        assert rows[0]["Source"] == "custom_wht"
        assert rows[0]["Notes"] == "Treaty rate"

    def test_metadata_override(self, flat_template):
        override = TaxTemplateOverride(
            override_name="meta_note",
            field_path="metadata.note",
            override_value="custom note",
            reason="User override",
        )
        rows = build_tax_override_table((override,))
        assert rows[0]["Override Path"] == "metadata.note"


class TestBuildResolvedTaxConfigSummary:
    def test_resolved_config_summary(self, resolved_config):
        rows = build_resolved_tax_config_summary(resolved_config)
        assert len(rows) == 1
        row = rows[0]
        assert row["Template Code"] == "HR Flat 18%"
        assert row["Country Code"] == "HR"
        assert row["Tax Year"] == 2026
        assert row["Override Count"] == 1
        assert row["Effective CIT Structure"] == "Flat"
        assert isinstance(row["Metadata"], dict)

    def test_no_overrides(self, flat_template):
        resolved = resolve_tax_template(flat_template, ())
        rows = build_resolved_tax_config_summary(resolved)
        assert rows[0]["Override Count"] == 0