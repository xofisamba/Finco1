"""Phase 6B.5 — Tests for tax UI helpers."""
from __future__ import annotations

import copy

import pytest

from domain.tax.templates.inputs import (
    TaxTemplate,
    TaxDepreciationRule,
    CITTier,
)
from domain.tax.templates.resolver import resolve_tax_template
from domain.tax.engine_inputs import SPVTaxEngineInputs
from domain.tax.engine_result import SPVTaxResult, SPVTaxPeriodResult
from domain.tax.engine_runner import run_spv_tax_engine
from app.tax_ui import (
    build_spv_tax_summary_table,
    build_spv_tax_period_table,
    build_tax_audit_note,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_hr_template() -> TaxTemplate:
    return TaxTemplate(
        country_code="HR",
        template_name="HR Flat 10%",
        tax_year=2026,
        cit_tiers=(CITTier(0.0, None, 0.10),),
        depreciation_rules=(
            TaxDepreciationRule(
                asset_category="infra",
                method="straight_line",
                annual_rate=None,
                useful_life_years=20.0,
                max_deductible_rate=None,
                bonus_depreciation_pct=0.0,
                deductible=True,
                notes="HR straight-line",
            ),
        ),
        withholding_tax_dividends=0.0,
        withholding_tax_interest=0.0,
    )


def resolved_config(template: TaxTemplate):
    return resolve_tax_template(template, ())


def make_inputs(n=5):
    template = make_hr_template()
    config = resolved_config(template)
    return SPVTaxEngineInputs(
        entity_code="HR-SPV-001",
        resolved_tax_config=config,
        ebitda_by_period_keur=tuple(1000.0 for _ in range(n)),
        deductible_interest_by_period_keur=tuple(0.0 for _ in range(n)),
        book_depreciation_by_period_keur=tuple(500.0 for _ in range(n)),
        asset_cost_keur=10_000.0,
        depreciation_rule_asset_category="infra",
        non_deductible_addbacks_by_period_keur=(0.0,) * n,
    )


# ── Test: summary table ───────────────────────────────────────────────────────

class TestBuildSpvTaxSummaryTable:
    def test_summary_contains_expected_totals(self):
        """Summary table contains all required columns and correct values."""
        inputs = make_inputs(n=5)
        result = run_spv_tax_engine(inputs)

        df = build_spv_tax_summary_table(result)

        # Check columns
        expected_cols = [
            "Entity Code", "Country Code", "Tax Year",
            "Total Taxable Income Before Losses (kEUR)",
            "Total Loss Used (kEUR)",
            "Total Taxable Income After Losses (kEUR)",
            "Total CIT Payable (kEUR)",
            "Ending Loss Carryforward (kEUR)",
        ]
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

        # Check row values
        assert df.loc[0, "Entity Code"] == "HR-SPV-001"
        assert df.loc[0, "Country Code"] == "HR"
        assert df.loc[0, "Tax Year"] == 2026
        # 5 periods * 500 taxable each = 2500 kEUR total before losses
        assert df.loc[0, "Total Taxable Income Before Losses (kEUR)"] == pytest.approx(2500.0)
        # 5 * (1000 - 500) = 2500 taxable, CIT = 250
        assert df.loc[0, "Total CIT Payable (kEUR)"] == pytest.approx(250.0)

    def test_summary_single_row(self):
        """Summary table is exactly one row per SPV result."""
        inputs = make_inputs(n=3)
        result = run_spv_tax_engine(inputs)
        df = build_spv_tax_summary_table(result)
        assert len(df) == 1

    def test_no_mutation_of_result(self):
        """Running summary table builder does not mutate the SPVTaxResult."""
        inputs = make_inputs(n=2)
        result = run_spv_tax_engine(inputs)
        original_total = result.total_cit_payable_keur

        build_spv_tax_summary_table(result)

        assert result.total_cit_payable_keur == original_total


# ── Test: period table ───────────────────────────────────────────────────────

class TestBuildSpvTaxPeriodTable:
    def test_period_table_contains_expected_columns(self):
        """Period table contains all required columns."""
        inputs = make_inputs(n=4)
        result = run_spv_tax_engine(inputs)

        df = build_spv_tax_period_table(result)

        expected_cols = [
            "Period",
            "EBITDA (kEUR)",
            "Deductible Interest (kEUR)",
            "Book Depreciation (kEUR)",
            "Tax Depreciation (kEUR)",
            "Non-Deductible Depreciation (kEUR)",
            "Taxable Income Before Losses (kEUR)",
            "Loss Used (kEUR)",
            "Taxable Income After Losses (kEUR)",
            "CIT Payable (kEUR)",
            "Closing Loss Carryforward (kEUR)",
            "Effective Tax Rate",
        ]
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_period_table_row_count_matches_periods(self):
        """Period table has one row per period."""
        inputs = make_inputs(n=7)
        result = run_spv_tax_engine(inputs)
        df = build_spv_tax_period_table(result)
        assert len(df) == 7

    def test_period_table_period_values(self):
        """Period column is 0-indexed."""
        inputs = make_inputs(n=3)
        result = run_spv_tax_engine(inputs)
        df = build_spv_tax_period_table(result)
        assert list(df["Period"]) == [0, 1, 2]

    def test_no_mutation_of_result(self):
        """Running period table builder does not mutate the SPVTaxResult."""
        inputs = make_inputs(n=2)
        result = run_spv_tax_engine(inputs)
        original_ebitda = result.periods[0].ebitda_keur

        build_spv_tax_period_table(result)

        assert result.periods[0].ebitda_keur == original_ebitda


# ── Test: audit note ─────────────────────────────────────────────────────────

class TestBuildTaxAuditNote:
    def test_audit_note_text_present(self):
        """Audit note contains required phrase."""
        note = build_tax_audit_note()
        assert "AUDIT-ONLY" in note
        assert "not yet wired into waterfall outputs or IRR metrics" in note

    def test_audit_note_returns_string(self):
        """Audit note returns a non-empty string."""
        note = build_tax_audit_note()
        assert isinstance(note, str)
        assert len(note) > 0

    def test_audit_note_idempotent(self):
        """Calling multiple times returns identical string."""
        note1 = build_tax_audit_note()
        note2 = build_tax_audit_note()
        assert note1 == note2