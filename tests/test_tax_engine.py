"""Tests for tax engine - mathematical property tests."""
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
            atad_ebitda_limit=0.30,
            atad_min_threshold_keur=3000.0,
        )

        assert abs(result.taxable_income_keur - 700.0) < 0.01
        assert abs(result.tax_keur - 70.0) < 0.01
        assert result.atad_addback_keur == 0.0

    def test_depreciation_reduces_tax(self):
        """Higher depreciation → lower taxable income."""
        low_dep = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=100.0,
            senior_interest_keur=100.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )

        high_dep = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=300.0,
            senior_interest_keur=100.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )

        # More depreciation → less tax
        assert high_dep.tax_keur < low_dep.tax_keur
        # taxable_low = 1000 - 100 - 100 = 800 → tax = 80
        # taxable_high = 1000 - 300 - 100 = 600 → tax = 60
        assert abs(low_dep.tax_keur - 80.0) < 0.01
        assert abs(high_dep.tax_keur - 60.0) < 0.01

    def test_atad_addback_when_interest_exceeds_limit(self):
        """When interest > 30% EBITDA + threshold, the excess is added back."""
        # ebitda=10000, interest=4000 (> 30%*10000=3000, also > 3000 threshold)
        result = compute_period_tax(
            ebitda_keur=10000.0,
            depreciation_keur=0.0,
            senior_interest_keur=4000.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_ebitda_limit=0.30,
            atad_min_threshold_keur=3000.0,
        )

        # Deductible interest capped at 3000 (30% of 10000)
        # ATAD addback = 4000 - 3000 = 1000
        assert result.atad_addback_keur == 1000.0
        # taxable = 10000 - 0 - 3000 + 1000 = 8000
        assert abs(result.taxable_income_keur - 8000.0) < 0.01
        assert abs(result.tax_keur - 800.0) < 0.01

    def test_loss_carryforward_reduces_tax(self):
        """Loss carryforward reduces taxable income."""
        no_loss = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=100.0,
            senior_interest_keur=100.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )

        with_loss = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=100.0,
            senior_interest_keur=100.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=200.0,
            tax_rate=0.10,
        )

        assert with_loss.tax_keur < no_loss.tax_keur
        # taxable_no_loss = 1000 - 100 - 100 = 800 → tax = 80
        # taxable_with_loss = max(0, 800 - 200) = 600 → tax = 60
        assert abs(no_loss.tax_keur - 80.0) < 0.01
        assert abs(with_loss.tax_keur - 60.0) < 0.01

    def test_tax_cannot_be_negative(self):
        """Tax is never negative (loss cannot create a refund)."""
        result = compute_period_tax(
            ebitda_keur=100.0,
            depreciation_keur=500.0,  # depreciation > ebitda
            senior_interest_keur=100.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )

        # taxable = max(0, 100 - 500 - 100) = 0
        assert result.taxable_income_keur == 0.0
        assert result.tax_keur == 0.0

    def test_shl_interest_deductible(self):
        """SHL interest is also deductible (counts toward ATAD limit)."""
        result = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=0.0,
            senior_interest_keur=100.0,
            shl_interest_keur=100.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )

        # Total interest = 200, ATAD limit = 300 (30% of 1000)
        # 200 < 300, so fully deductible
        # taxable = 1000 - 0 - 200 = 800
        assert result.atad_addback_keur == 0.0
        assert abs(result.taxable_income_keur - 800.0) < 0.01
        assert abs(result.tax_keur - 80.0) < 0.01

    def test_atad_threshold_kicks_in(self):
        """ATAD min threshold (3000 kEUR) allows interest above 30% EBITDA."""
        # EBITDA = 5000, interest = 2000
        # 30% EBITDA = 1500, threshold = 3000 → higher applies = 3000
        result = compute_period_tax(
            ebitda_keur=5000.0,
            depreciation_keur=0.0,
            senior_interest_keur=2000.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_min_threshold_keur=3000.0,
        )

        # Deductible = max(1500, 3000) = 3000
        # ATAD addback = 2000 - 3000 (negative → 0)
        assert result.atad_addback_keur == 0.0
        # taxable = 5000 - 0 - 2000 = 3000
        assert abs(result.taxable_income_keur - 3000.0) < 0.01
        assert abs(result.tax_keur - 300.0) < 0.01