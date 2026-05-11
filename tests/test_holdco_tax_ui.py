"""Phase 6C.4 — Tests for HoldCo tax UI helpers."""
import pytest

from domain.tax.holdco_inputs import (
    HoldCoTaxInputs,
    WithholdingTaxConfig,
    InterestDeductibilityConfig,
)
from domain.tax.holdco_runner import run_holdco_tax_engine
from app.holdco_tax_ui import (
    build_holdco_tax_summary_table,
    build_holdco_tax_period_table,
    build_holdco_tax_audit_note,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_inputs(entity_code="HR-HoldCo-001", n_periods=3, **overrides):
    defaults = dict(
        entity_code=entity_code,
        country_code="HR",
        tax_year=2026,
        dividend_income_by_period_keur=tuple(1000.0 for _ in range(n_periods)),
        shl_interest_income_by_period_keur=tuple(200.0 for _ in range(n_periods)),
        shl_principal_received_by_period_keur=tuple(500.0 for _ in range(n_periods)),
        holdco_opex_by_period_keur=tuple(50.0 for _ in range(n_periods)),
        withholding_tax_config=WithholdingTaxConfig(rate_dividends=0.12, rate_interest=0.0),
        interest_deductibility=InterestDeductibilityConfig(thin_cap_ratio=4.0, interest_limitation_pct_ebitda=0.30),
        metadata=(("source", "test"),),
    )
    defaults.update(overrides)
    return HoldCoTaxInputs(**defaults)


def make_result(**overrides):
    inputs = make_inputs(**{k: v for k, v in overrides.items() if k in [
        "entity_code", "n_periods", "dividend_income_by_period_keur",
        "shl_interest_income_by_period_keur", "shl_principal_received_by_period_keur",
        "holdco_opex_by_period_keur"
    ]})
    # Filter to valid kwargs
    valid = {}
    for k, v in overrides.items():
        if k in ["entity_code", "n_periods"]:
            valid[k] = v
    inputs = make_inputs(**valid)
    return run_holdco_tax_engine(inputs)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestBuildHoldcoTaxAuditNote:
    def test_returns_string(self):
        note = build_holdco_tax_audit_note()
        assert isinstance(note, str)

    def test_contains_audit_only(self):
        note = build_holdco_tax_audit_note()
        assert "AUDIT-ONLY" in note

    def test_contains_holdco_reference(self):
        note = build_holdco_tax_audit_note()
        assert "HoldCo" in note or "holdco" in note.lower()


class TestBuildHoldcoTaxSummaryTable:
    def test_summary_table_has_expected_columns(self):
        inputs = make_inputs(entity_code="HR-HoldCo-001", n_periods=3)
        result = run_holdco_tax_engine(inputs)
        rows = build_holdco_tax_summary_table(result)

        assert len(rows) == 1
        row = rows[0]
        assert "Entity Code" in row
        assert "Country Code" in row
        assert "Tax Year" in row
        assert "Total Taxable Dividend Income (kEUR)" in row
        assert "Total Taxable Interest Income (kEUR)" in row
        assert "Total Non-Taxable Principal (kEUR)" in row
        assert "Total WHT Dividends (kEUR)" in row
        assert "Total WHT Interest (kEUR)" in row

    def test_summary_totals_match_result(self):
        inputs = make_inputs(
            entity_code="HR-HoldCo-001",
            n_periods=3,
            dividend_income_by_period_keur=tuple(1000.0 for _ in range(3)),
            shl_interest_income_by_period_keur=tuple(200.0 for _ in range(3)),
            shl_principal_received_by_period_keur=tuple(500.0 for _ in range(3)),
        )
        result = run_holdco_tax_engine(inputs)
        rows = build_holdco_tax_summary_table(result)

        row = rows[0]
        assert row["Entity Code"] == "HR-HoldCo-001"
        assert row["Country Code"] == "HR"
        assert row["Tax Year"] == 2026
        assert row["Total Taxable Dividend Income (kEUR)"] == 3000.0  # 1000 * 3
        assert row["Total Taxable Interest Income (kEUR)"] == 600.0  # 200 * 3
        assert row["Total Non-Taxable Principal (kEUR)"] == 1500.0  # 500 * 3
        assert row["Total WHT Dividends (kEUR)"] == 360.0  # 120 * 3

    def test_no_mutation_of_result(self):
        inputs = make_inputs(n_periods=2)
        result = run_holdco_tax_engine(inputs)
        original_code = result.entity_code

        build_holdco_tax_summary_table(result)

        assert result.entity_code == original_code


class TestBuildHoldcoTaxPeriodTable:
    def test_period_table_has_expected_columns(self):
        inputs = make_inputs(n_periods=3)
        result = run_holdco_tax_engine(inputs)
        rows = build_holdco_tax_period_table(result)

        assert len(rows) == 3
        row = rows[0]
        expected_cols = [
            "Period", "Taxable Dividend Income (kEUR)",
            "Taxable Interest Income (kEUR)", "Non-Taxable Principal (kEUR)",
            "Deductible OPEX (kEUR)", "Taxable Income Before Limitations (kEUR)",
            "WHT Dividends (kEUR)", "WHT Interest (kEUR)",
            "Interest Limited (kEUR)", "Notes", "Warnings",
        ]
        for col in expected_cols:
            assert col in row, f"Missing column: {col}"

    def test_period_indices(self):
        inputs = make_inputs(n_periods=5)
        result = run_holdco_tax_engine(inputs)
        rows = build_holdco_tax_period_table(result)

        for i, row in enumerate(rows):
            assert row["Period"] == i

    def test_principal_tracked_per_period(self):
        inputs = make_inputs(
            n_periods=3,
            shl_principal_received_by_period_keur=tuple(500.0 for _ in range(3)),
        )
        result = run_holdco_tax_engine(inputs)
        rows = build_holdco_tax_period_table(result)

        for row in rows:
            assert row["Non-Taxable Principal (kEUR)"] == 500.0

    def test_notes_and_warnings_joined(self):
        inputs = make_inputs(n_periods=1)
        result = run_holdco_tax_engine(inputs)
        rows = build_holdco_tax_period_table(result)

        assert isinstance(rows[0]["Notes"], str)
        assert "SHL principal excluded" in rows[0]["Notes"]

    def test_no_mutation_of_result(self):
        inputs = make_inputs(n_periods=2)
        result = run_holdco_tax_engine(inputs)
        original = result.period_results[0].period_index

        build_holdco_tax_period_table(result)

        assert result.period_results[0].period_index == original