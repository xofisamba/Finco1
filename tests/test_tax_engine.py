"""Tests for domain.waterfall.tax_engine - compute_period_tax properties."""
import pytest
from domain.waterfall.tax_engine import compute_period_tax, TaxPeriodResult


class TestTaxFormula:
    def test_simple_tax_no_atad_no_loss_cf(self):
        """Given ebitda=1000, depreciation=200, interest=100, tax_rate=0.10:
        taxable = 1000 - 200 - 100 = 700
        tax = 70
        """
        result = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=200.0,
            senior_interest_keur=100.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )
        assert abs(result.taxable_income_keur - 700.0) < 0.01
        assert abs(result.tax_keur - 70.0) < 0.01

    def test_depreciation_reduces_tax(self):
        """Higher depreciation → lower taxable income."""
        no_dep = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=0.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
        )
        high_dep = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=300.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
        )
        # no_dep: 1000 - 0 - 100 = 900 → tax = 90
        # high_dep: 1000 - 300 - 100 = 600 → tax = 60
        assert high_dep.tax_keur < no_dep.tax_keur
        assert abs(no_dep.tax_keur - 90.0) < 0.01
        assert abs(high_dep.tax_keur - 60.0) < 0.01

    def test_fiscal_reintegration_increases_taxable_income(self):
        """Fiscal reintegration adds to taxable income before losses."""
        without_fisc = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=100.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
            fiscal_reintegration_keur=0.0,
        )
        with_fisc = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=100.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
            fiscal_reintegration_keur=200.0,
        )
        # without_fisc: 1000 - 100 - 100 = 800 → tax = 80
        # with_fisc: 1000 - 100 - 100 + 200 = 1000 → tax = 100
        assert with_fisc.taxable_income_keur > without_fisc.taxable_income_keur
        assert abs(without_fisc.tax_keur - 80.0) < 0.01
        assert abs(with_fisc.tax_keur - 100.0) < 0.01

    def test_loss_carryforward_reduces_tax(self):
        """Loss carryforward reduces taxable income."""
        no_loss = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=100.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
        )
        with_loss = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=100.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=200.0, tax_rate=0.10,
        )
        # no_loss: 1000 - 100 - 100 = 800 → tax = 80
        # with_loss: 800 - 200 = 600 → tax = 60
        assert with_loss.tax_keur < no_loss.tax_keur
        assert abs(no_loss.tax_keur - 80.0) < 0.01
        assert abs(with_loss.tax_keur - 60.0) < 0.01
        assert with_loss.loss_carryforward_applied_keur == 200.0

    def test_tax_cannot_be_negative(self):
        """Tax is never negative."""
        result = compute_period_tax(
            ebitda_keur=100.0, depreciation_keur=500.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
        )
        # taxable = max(0, 100 - 500 - 100) = 0
        assert result.taxable_income_keur == 0.0
        assert result.tax_keur == 0.0

    def test_shl_interest_deductible(self):
        """SHL interest also counts toward ATAD limit."""
        result = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=0.0,
            senior_interest_keur=100.0, shl_interest_keur=100.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
        )
        # Total interest = 200 < 30%*1000=300, fully deductible
        assert result.disallowed_interest_keur == 0.0
        # taxable = 1000 - 0 - 200 = 800
        assert abs(result.taxable_income_keur - 800.0) < 0.01
        assert abs(result.tax_keur - 80.0) < 0.01

    def test_loss_carryforward_fully_offsets_tax(self):
        """When loss CF fully offsets profit, tax is zero."""
        result = compute_period_tax(
            ebitda_keur=100.0, depreciation_keur=0.0,
            senior_interest_keur=50.0, shl_interest_keur=0.0,
            loss_carryforward_keur=500.0, tax_rate=0.10,
        )
        # taxable_before = 100 - 0 - 50 = 50
        # Loss used = min(500, 50) = 50, taxable = 0, tax = 0
        assert result.taxable_income_keur == 0.0
        assert result.tax_keur == 0.0
        assert result.loss_carryforward_applied_keur == 50.0
        assert result.loss_carryforward_remaining_keur == 450.0

    def test_tax_keur_equals_final_taxable_income_times_rate(self):
        """tax_keur must equal taxable_income_keur * tax_rate."""
        result = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=200.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=100.0, tax_rate=0.10,
            fiscal_reintegration_keur=50.0,
        )
        expected_taxable = max(0.0, 1000.0 - 200.0 - 100.0 + 50.0 - 100.0)
        expected_tax = expected_taxable * 0.10
        assert abs(result.tax_keur - expected_tax) < 0.01
        assert abs(result.taxable_income_keur - expected_taxable) < 0.01

    def test_deductible_and_disallowed_reported_separately(self):
        """Deductible vs disallowed interest must be tracked separately."""
        # Case 1: interest below limit - fully deductible
        result = compute_period_tax(
            ebitda_keur=5000.0, depreciation_keur=0.0,
            senior_interest_keur=2000.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
        )
        # ATAD limit = max(30%*5000, 3000) = max(1500, 3000) = 3000
        # 2000 < 3000 → fully deductible
        assert result.deductible_interest_keur == 2000.0
        assert result.disallowed_interest_keur == 0.0
        # taxable = 5000 - 0 - 2000 + 0 = 3000
        assert abs(result.taxable_income_keur - 3000.0) < 0.01

        # Case 2: interest above limit - disallowed portion tracked
        result2 = compute_period_tax(
            ebitda_keur=5000.0, depreciation_keur=0.0,
            senior_interest_keur=6000.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
        )
        # ATAD limit = max(1500, 3000) = 3000, disallowed = 6000 - 3000 = 3000
        assert result2.deductible_interest_keur == 3000.0
        assert result2.disallowed_interest_keur == 3000.0

    def test_fiscal_reintegration_preserved_in_result(self):
        """fiscal_reintegration_keur field accessible in result."""
        result = compute_period_tax(
            ebitda_keur=1000.0, depreciation_keur=0.0,
            senior_interest_keur=0.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
            fiscal_reintegration_keur=150.0,
        )
        assert result.fiscal_reintegration_keur == 150.0
        assert abs(result.taxable_income_keur - 1150.0) < 0.01

    def test_atad_addback_equivalent_to_disallowed_interest(self):
        """disallowed_interest_keur IS the ATAD addback."""
        result = compute_period_tax(
            ebitda_keur=10000.0, depreciation_keur=0.0,
            senior_interest_keur=4000.0, shl_interest_keur=0.0,
            loss_carryforward_keur=0.0, tax_rate=0.10,
        )
        # ATAD limit = max(30%*10000, 3000) = max(3000, 3000) = 3000
        # interest=4000, deductible=3000, disallowed=1000
        # taxable = 10000 - 0 - 3000 + 1000 = 8000
        assert result.disallowed_interest_keur == 1000.0
        assert abs(result.taxable_income_keur - 8000.0) < 0.01
        assert abs(result.tax_keur - 800.0) < 0.01


class TestFiscalReintegration:
    def test_fiscal_reintegration_before_loss_carryforward(self):
        """Fiscal reintegration consumed before loss carryforward."""
        without = compute_period_tax(
            ebitda_keur=500.0, depreciation_keur=100.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=500.0, tax_rate=0.10,
            fiscal_reintegration_keur=0.0,
        )
        with_fisc = compute_period_tax(
            ebitda_keur=500.0, depreciation_keur=100.0,
            senior_interest_keur=100.0, shl_interest_keur=0.0,
            loss_carryforward_keur=500.0, tax_rate=0.10,
            fiscal_reintegration_keur=200.0,
        )
        # without: 500-100-100=300, loss used=300, taxable=0, tax=0
        # with_fisc: 500-100-100+200=500, loss used=500, taxable=0, tax=0
        assert without.tax_keur == 0.0
        assert with_fisc.tax_keur == 0.0
        # More loss is consumed when fiscal reintegration is present
        assert with_fisc.loss_carryforward_applied_keur > without.loss_carryforward_applied_keur