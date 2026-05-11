"""Phase 6C.3 — Tests for HoldCo tax engine runner."""
import pytest

from domain.tax.holdco_inputs import (
    HoldCoTaxInputs,
    WithholdingTaxConfig,
    InterestDeductibilityConfig,
)
from domain.tax.holdco_runner import run_holdco_tax_engine


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_inputs(
    entity_code="HR-HoldCo-001",
    country_code="HR",
    tax_year=2026,
    n_periods=5,
    dividend=1000.0,
    shl_interest=200.0,
    shl_principal=500.0,
    opex=50.0,
    wht_div_rate=0.12,
    wht_int_rate=0.0,
    metadata=None,
):
    if metadata is None:
        metadata = (("source", "test"),)
    return HoldCoTaxInputs(
        entity_code=entity_code,
        country_code=country_code,
        tax_year=tax_year,
        dividend_income_by_period_keur=tuple(dividend for _ in range(n_periods)),
        shl_interest_income_by_period_keur=tuple(shl_interest for _ in range(n_periods)),
        shl_principal_received_by_period_keur=tuple(shl_principal for _ in range(n_periods)),
        holdco_opex_by_period_keur=tuple(opex for _ in range(n_periods)),
        withholding_tax_config=WithholdingTaxConfig(
            rate_dividends=wht_div_rate,
            rate_interest=wht_int_rate,
        ),
        interest_deductibility=InterestDeductibilityConfig(
            thin_cap_ratio=4.0,
            interest_limitation_pct_ebitda=0.30,
        ),
        metadata=metadata,
    )


# ── Tests ────────────────────────────────────────────────────────────────────

class TestRunHoldcoTaxEngine:
    def test_basic_run_with_dividends(self):
        inputs = make_inputs()
        result = run_holdco_tax_engine(inputs)

        assert result.entity_code == "HR-HoldCo-001"
        assert result.country_code == "HR"
        assert result.tax_year == 2026
        assert len(result.period_results) == 5

    def test_shl_interest_included_as_taxable(self):
        """SHL interest income is included as taxable interest income."""
        inputs = make_inputs(shl_interest=200.0, dividend=1000.0)
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            assert pr.taxable_interest_income_keur == 200.0

    def test_shl_principal_excluded_tracked_as_non_taxable(self):
        """SHL principal is excluded from taxable income and tracked as non-taxable."""
        inputs = make_inputs(shl_principal=500.0)
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            assert pr.non_taxable_principal_keur == 0.0  # excluded via function
            assert pr.taxable_interest_income_keur == 200.0  # interest only

        assert result.total_non_taxable_principal_keur == 0.0

    def test_wht_dividends_calculated(self):
        """WHT on dividends is calculated using the applicable rate."""
        inputs = make_inputs(dividend=1000.0, wht_div_rate=0.12)
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            assert pr.withholding_tax_dividends_keur == 120.0

        assert result.total_withholding_tax_dividends_keur == 600.0

    def test_wht_interest_calculated(self):
        """WHT on SHL interest is calculated using the applicable rate."""
        inputs = make_inputs(shl_interest=200.0, wht_int_rate=0.05)
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            assert pr.withholding_tax_interest_keur == 10.0  # 200 * 0.05

        assert result.total_withholding_tax_interest_keur == 50.0

    def test_opex_reduces_taxable_income(self):
        """HoldCo opex reduces taxable income before limitations."""
        inputs = make_inputs(dividend=1000.0, shl_interest=200.0, opex=50.0)
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            expected = 1000.0 + 200.0 - 50.0  # = 1150.0
            assert pr.taxable_income_before_limitations_keur == expected

    def test_totals_reconcile(self):
        """Period totals sum correctly to result totals."""
        inputs = make_inputs(n_periods=5, dividend=1000.0, shl_interest=200.0)
        result = run_holdco_tax_engine(inputs)

        assert result.total_taxable_dividend_keur == sum(
            pr.taxable_dividend_income_keur for pr in result.period_results
        )
        assert result.total_taxable_interest_keur == sum(
            pr.taxable_interest_income_keur for pr in result.period_results
        )
        assert result.total_non_taxable_principal_keur == sum(
            pr.non_taxable_principal_keur for pr in result.period_results
        )
        assert result.total_withholding_tax_dividends_keur == sum(
            pr.withholding_tax_dividends_keur for pr in result.period_results
        )
        assert result.total_withholding_tax_interest_keur == sum(
            pr.withholding_tax_interest_keur for pr in result.period_results
        )

    def test_warnings_and_notes_present(self):
        """Period results contain audit notes about SHL principal and WHT."""
        inputs = make_inputs()
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            assert len(pr.notes) > 0
            assert any("SHL principal excluded" in n for n in pr.notes)
            assert any("WHT stored" in n for n in pr.notes)

        # Top-level notes also present
        assert len(result.notes) > 0

    def test_zero_wht_rates(self):
        """Zero WHT rates result in zero WHT amounts."""
        inputs = make_inputs(wht_div_rate=0.0, wht_int_rate=0.0)
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            assert pr.withholding_tax_dividends_keur == 0.0
            assert pr.withholding_tax_interest_keur == 0.0

    def test_interest_limited_keur_is_zero(self):
        """interest_limited_keur is 0 in Phase 6C.3 (no enforcement)."""
        inputs = make_inputs()
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            assert pr.interest_limited_keur == 0.0

    def test_no_cit_payable(self):
        """Phase 6C.3 does not calculate CIT payable — audit only."""
        inputs = make_inputs()
        result = run_holdco_tax_engine(inputs)

        assert any("no CIT payable" in n.lower() or "audit only" in n.lower()
                   for n in result.notes)

    def test_empty_periods_produce_valid_result(self):
        """n_periods=0 produces a valid result with no period_results."""
        inputs = make_inputs(
            n_periods=0,
            dividend=0.0,
            shl_interest=0.0,
            shl_principal=0.0,
            opex=0.0,
        )
        result = run_holdco_tax_engine(inputs)

        assert len(result.period_results) == 0
        assert result.total_taxable_dividend_keur == 0.0
        assert result.total_taxable_interest_keur == 0.0

    def test_no_mutation_of_inputs(self):
        """run_holdco_tax_engine does not mutate the inputs object."""
        inputs = make_inputs()
        original_metadata = inputs.metadata
        original_entity = inputs.entity_code

        result = run_holdco_tax_engine(inputs)

        assert inputs.entity_code == original_entity
        assert inputs.metadata == original_metadata
        assert result.entity_code == original_entity

    def test_metadata_preserved(self):
        """Input metadata is preserved in the result."""
        inputs = make_inputs(metadata=(("source", "runner-test"), ("ver", "2")))
        result = run_holdco_tax_engine(inputs)

        assert result.metadata_dict["source"] == "runner-test"
        assert result.metadata_dict["ver"] == "2"

    def test_all_wht_rates_combined(self):
        """WHT on both dividends and interest are tracked separately."""
        inputs = make_inputs(
            dividend=1000.0,
            shl_interest=200.0,
            wht_div_rate=0.12,
            wht_int_rate=0.05,
        )
        result = run_holdco_tax_engine(inputs)

        # dividend WHT: 1000 * 0.12 = 120 per period
        # interest WHT: 200 * 0.05 = 10 per period
        for pr in result.period_results:
            assert pr.withholding_tax_dividends_keur == 120.0
            assert pr.withholding_tax_interest_keur == 10.0

        assert result.total_withholding_tax_dividends_keur == 600.0
        assert result.total_withholding_tax_interest_keur == 50.0

    def test_single_period(self):
        """Single period inputs produce correct single-period result."""
        inputs = make_inputs(n_periods=1, dividend=500.0, shl_interest=100.0, opex=30.0)
        result = run_holdco_tax_engine(inputs)

        assert len(result.period_results) == 1
        pr = result.period_results[0]
        assert pr.period_index == 0
        assert pr.taxable_dividend_income_keur == 500.0
        assert pr.taxable_interest_income_keur == 100.0
        assert pr.deductible_opex_keur == 30.0
        assert pr.taxable_income_before_limitations_keur == 570.0  # 500+100-30

    def test_deductible_opex_tracked(self):
        """HoldCo opex is tracked as deductible_opex_keur per period."""
        inputs = make_inputs(opex=75.0)
        result = run_holdco_tax_engine(inputs)

        for pr in result.period_results:
            assert pr.deductible_opex_keur == 75.0