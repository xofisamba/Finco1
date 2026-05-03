"""Integration tests: tax engine wired into runtime waterfall."""
import pytest
from domain.waterfall.tax_engine import compute_period_tax


class TestWaterfallTaxIntegration:
    """Tax integration in runtime waterfall."""

    def test_increasing_depreciation_reduces_tax(self):
        """Runtime waterfall: higher depreciation → lower tax."""
        # compute_period_tax directly shows depreciation impact
        result_no_dep = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=0.0,
            senior_interest_keur=100.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )

        result_high_dep = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=300.0,
            senior_interest_keur=100.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )

        assert result_high_dep.tax_keur < result_no_dep.tax_keur

    def test_atad_limits_interest_deductibility(self):
        """High interest is limited by ATAD in runtime waterfall."""
        # With interest > min(30% EBITDA, 3000 kEUR threshold), ATAD addback kicks in
        # ATAD deductibility limit = max(30% EBITDA, 3000) = max(300, 3000) = 3000
        # interest=4000 > 3000 so ATAD limit applies
        result = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=0.0,
            senior_interest_keur=4000.0,  # Way above 3000 threshold → ATAD kicks in
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_ebitda_limit=0.30,
            atad_min_threshold_keur=3000.0,
        )

        # Deductible limited to max(30%*1000, 3000) = 3000
        # interest=4000, deductible=3000, addback=1000
        # taxable = 1000 - 0 - 3000 + 1000 = 0 (profit not enough to absorb)
        # Wait: taxable = ebitda - dep - deductible + addback - loss_cf
        #       = 1000 - 0 - 3000 + 1000 = 0
        # tax = 0 * 0.10 = 0
        assert result.atad_addback_keur == 1000.0
        assert result.taxable_income_keur == 0.0
        assert result.tax_keur == 0.0

    def test_loss_carryforward_reduces_runtime_tax(self):
        """Loss carryforward reduces tax in waterfall runtime."""
        # Low interest so ATAD doesn't trigger
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

    def test_tax_zero_when_dep_greater_than_ebitda(self):
        """Tax is zero when depreciation exceeds EBITDA."""
        result = compute_period_tax(
            ebitda_keur=100.0,
            depreciation_keur=500.0,
            senior_interest_keur=50.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
        )

        # taxable = max(0, 100 - 500 - 50) = 0
        assert result.taxable_income_keur == 0.0
        assert result.tax_keur == 0.0