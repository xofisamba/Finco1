"""Phase 6C.2 — Tests for HoldCo / intercompany tax calculation primitives."""
import pytest

from domain.tax.holdco_calculations import (
    calculate_withholding_tax_keur,
    calculate_holdco_taxable_income_before_limitations,
    exclude_shl_principal_from_taxable_income,
    calculate_interest_limitation_keur,
    calculate_deductible_interest_after_limitation_keur,
)


# ── Tests: calculate_withholding_tax_keur ─────────────────────────────────────

class TestCalculateWithholdingTaxKeur:
    def test_zero_rate(self):
        assert calculate_withholding_tax_keur(1000.0, 0.0) == 0.0

    def test_normal_rate(self):
        assert calculate_withholding_tax_keur(1000.0, 0.12) == 120.0

    def test_one_hundred_percent(self):
        assert calculate_withholding_tax_keur(1000.0, 1.0) == 1000.0

    def test_fractional_rate(self):
        assert abs(calculate_withholding_tax_keur(3333.33, 0.03) - 100.0) < 0.01

    def test_zero_amount(self):
        assert calculate_withholding_tax_keur(0.0, 0.12) == 0.0

    def test_invalid_rate_negative_rejected(self):
        with pytest.raises(ValueError, match="withholding_rate"):
            calculate_withholding_tax_keur(1000.0, -0.1)

    def test_invalid_rate_above_one_rejected(self):
        with pytest.raises(ValueError, match="withholding_rate"):
            calculate_withholding_tax_keur(1000.0, 1.5)

    def test_negative_gross_amount_rejected(self):
        with pytest.raises(ValueError, match="gross_amount_keur"):
            calculate_withholding_tax_keur(-100.0, 0.12)

    def test_nan_gross_amount_rejected(self):
        with pytest.raises(ValueError, match="gross_amount_keur.*NaN"):
            calculate_withholding_tax_keur(float("nan"), 0.12)

    def test_inf_rate_rejected(self):
        with pytest.raises(ValueError, match="withholding_rate.*inf"):
            calculate_withholding_tax_keur(1000.0, float("inf"))

    def test_pure_behavior_no_mutation(self):
        """Calling the function does not mutate any input or global state."""
        rate = 0.12
        amount = 1000.0
        result = calculate_withholding_tax_keur(amount, rate)
        assert result == 120.0
        assert rate == 0.12  # unchanged
        assert amount == 1000.0  # unchanged


# ── Tests: calculate_holdco_taxable_income_before_limitations ────────────────

class TestHoldcoTaxableIncomeBeforeLimitations:
    def test_basic_formula(self):
        # taxable = dividend + interest - opex
        result = calculate_holdco_taxable_income_before_limitations(
            dividend_income_keur=1000.0,
            shl_interest_income_keur=200.0,
            holdco_opex_keur=50.0,
        )
        assert result == 1150.0

    def test_zero_opex(self):
        result = calculate_holdco_taxable_income_before_limitations(
            dividend_income_keur=500.0,
            shl_interest_income_keur=100.0,
            holdco_opex_keur=0.0,
        )
        assert result == 600.0

    def test_opex_exceeds_income(self):
        # Can be negative — loss position
        result = calculate_holdco_taxable_income_before_limitations(
            dividend_income_keur=100.0,
            shl_interest_income_keur=50.0,
            holdco_opex_keur=200.0,
        )
        assert result == -50.0

    def test_nan_input_rejected(self):
        with pytest.raises(ValueError, match="dividend_income_keur.*NaN"):
            calculate_holdco_taxable_income_before_limitations(
                float("nan"), 200.0, 50.0
            )

    def test_inf_input_rejected(self):
        with pytest.raises(ValueError, match="shl_interest_income_keur.*Inf"):
            calculate_holdco_taxable_income_before_limitations(
                1000.0, float("inf"), 50.0
            )

    def test_negative_dividend_rejected(self):
        with pytest.raises(ValueError, match="dividend_income_keur.*must be non-negative"):
            calculate_holdco_taxable_income_before_limitations(-100.0, 200.0, 50.0)

    def test_negative_shl_interest_rejected(self):
        with pytest.raises(ValueError, match="shl_interest_income_keur.*must be non-negative"):
            calculate_holdco_taxable_income_before_limitations(1000.0, -50.0, 50.0)

    def test_negative_opex_rejected(self):
        with pytest.raises(ValueError, match="holdco_opex_keur.*must be non-negative"):
            calculate_holdco_taxable_income_before_limitations(1000.0, 200.0, -10.0)

    def test_pure_behavior_no_mutation(self):
        div, int_, opex = 1000.0, 200.0, 50.0
        result = calculate_holdco_taxable_income_before_limitations(div, int_, opex)
        assert result == 1150.0
        assert div == 1000.0  # unchanged
        assert int_ == 200.0  # unchanged
        assert opex == 50.0  # unchanged


# ── Tests: exclude_shl_principal_from_taxable_income ─────────────────────────

class TestExcludeShlPrincipalFromTaxableIncome:
    def test_returns_zero(self):
        assert exclude_shl_principal_from_taxable_income(500.0) == 0.0

    def test_zero_principal(self):
        assert exclude_shl_principal_from_taxable_income(0.0) == 0.0

    def test_large_principal_returns_zero(self):
        assert exclude_shl_principal_from_taxable_income(1_000_000.0) == 0.0

    def test_negative_principal_rejected(self):
        with pytest.raises(ValueError, match="shl_principal_keur.*must be non-negative"):
            exclude_shl_principal_from_taxable_income(-100.0)

    def test_nan_principal_rejected(self):
        with pytest.raises(ValueError, match="shl_principal_keur.*NaN"):
            exclude_shl_principal_from_taxable_income(float("nan"))

    def test_pure_behavior_no_mutation(self):
        principal = 500.0
        result = exclude_shl_principal_from_taxable_income(principal)
        assert result == 0.0
        assert principal == 500.0  # unchanged


# ── Tests: calculate_interest_limitation_keur ─────────────────────────────────

class TestCalculateInterestLimitationKeur:
    def test_no_limitation_when_none(self):
        assert calculate_interest_limitation_keur(500.0, 1000.0, None) == 0.0

    def test_no_excess_within_limit(self):
        # limit = 1000 * 0.30 = 300, interest = 200, excess = 0
        assert calculate_interest_limitation_keur(200.0, 1000.0, 0.30) == 0.0

    def test_excess_calculated_correctly(self):
        # limit = 1000 * 0.30 = 300, interest = 400, excess = 100
        assert calculate_interest_limitation_keur(400.0, 1000.0, 0.30) == 100.0

    def test_zero_interest(self):
        assert calculate_interest_limitation_keur(0.0, 1000.0, 0.30) == 0.0

    def test_zero_ebitda(self):
        # ebitda_keur = 0 <= 0, limit = 0, all interest is limited
        assert calculate_interest_limitation_keur(100.0, 0.0, 0.30) == 100.0

    def test_negative_ebitda_accepted_all_limited(self):
        # EBITDA <= 0 → all interest is non-deductible
        assert calculate_interest_limitation_keur(200.0, -100.0, 0.30) == 200.0
        assert calculate_interest_limitation_keur(200.0, -1000.0, 0.30) == 200.0

    def test_negative_ebitda_no_limit_pct(self):
        # no limitation pct → returns 0
        assert calculate_interest_limitation_keur(200.0, -100.0, None) == 0.0

    def test_zero_limit_percent(self):
        # limit = 1000 * 0 = 0, all interest non-deductible
        assert calculate_interest_limitation_keur(200.0, 1000.0, 0.0) == 200.0

    def test_invalid_limit_negative_rejected(self):
        with pytest.raises(ValueError, match="interest_limitation_pct_ebitda"):
            calculate_interest_limitation_keur(200.0, 1000.0, -0.1)

    def test_invalid_limit_above_one_rejected(self):
        with pytest.raises(ValueError, match="interest_limitation_pct_ebitda"):
            calculate_interest_limitation_keur(200.0, 1000.0, 1.5)

    def test_negative_interest_rejected(self):
        with pytest.raises(ValueError, match="interest_amount_keur.*must be non-negative"):
            calculate_interest_limitation_keur(-100.0, 1000.0, 0.30)

    def test_pure_behavior_no_mutation(self):
        interest, ebitda, limit = 200.0, 1000.0, 0.30
        result = calculate_interest_limitation_keur(interest, ebitda, limit)
        assert result == 0.0  # within limit
        assert interest == 200.0  # unchanged
        assert ebitda == 1000.0  # unchanged


# ── Tests: calculate_deductible_interest_after_limitation_keur ───────────────

class TestDeductibleInterestAfterLimitation:
    def test_no_limit_returns_full(self):
        assert calculate_deductible_interest_after_limitation_keur(200.0, 1000.0, None) == 200.0

    def test_within_limit_full_deductible(self):
        result = calculate_deductible_interest_after_limitation_keur(200.0, 1000.0, 0.30)
        assert result == 200.0  # all within 300 limit

    def test_excess_limited(self):
        result = calculate_deductible_interest_after_limitation_keur(400.0, 1000.0, 0.30)
        assert result == 300.0  # only 300 deductible, 100 excess

    def test_zero_interest(self):
        assert calculate_deductible_interest_after_limitation_keur(0.0, 1000.0, 0.30) == 0.0

    def test_zero_ebitda(self):
        # ebitda_keur = 0, limit = 0, all is limited → 0 deductible
        result = calculate_deductible_interest_after_limitation_keur(100.0, 0.0, 0.30)
        assert result == 0.0

    def test_negative_ebitda_with_limit_returns_zero(self):
        # EBITDA <= 0 → all limited → deductible = 0
        result = calculate_deductible_interest_after_limitation_keur(200.0, -100.0, 0.30)
        assert result == 0.0

    def test_result_never_negative(self):
        result = calculate_deductible_interest_after_limitation_keur(500.0, 100.0, 0.30)
        assert result >= 0.0

    def test_negative_interest_rejected(self):
        with pytest.raises(ValueError, match="interest_amount_keur.*must be non-negative"):
            calculate_deductible_interest_after_limitation_keur(-100.0, 1000.0, 0.30)

    def test_pure_behavior_no_mutation(self):
        interest, ebitda, limit = 400.0, 1000.0, 0.30
        result = calculate_deductible_interest_after_limitation_keur(interest, ebitda, limit)
        assert result == 300.0
        assert interest == 400.0  # unchanged

# ── Tests: split_shl_receipt_tax_components ───────────────────────────────────

class TestSplitShlReceiptTaxComponents:
    def test_interest_and_principal_preserved(self):
        from domain.tax.holdco_calculations import split_shl_receipt_tax_components
        taxable_int, non_taxable_principal = split_shl_receipt_tax_components(200.0, 500.0)
        assert taxable_int == 200.0
        assert non_taxable_principal == 500.0

    def test_zero_principal(self):
        from domain.tax.holdco_calculations import split_shl_receipt_tax_components
        taxable_int, non_taxable_principal = split_shl_receipt_tax_components(200.0, 0.0)
        assert taxable_int == 200.0
        assert non_taxable_principal == 0.0

    def test_principal_amount_for_audit(self):
        """Principal amount is returned for audit tracking, not 0."""
        from domain.tax.holdco_calculations import split_shl_receipt_tax_components
        _, non_taxable_principal = split_shl_receipt_tax_components(100.0, 1_000_000.0)
        assert non_taxable_principal == 1_000_000.0

    def test_negative_principal_rejected(self):
        from domain.tax.holdco_calculations import split_shl_receipt_tax_components
        with pytest.raises(ValueError, match="shl_principal_received_keur.*must be non-negative"):
            split_shl_receipt_tax_components(200.0, -50.0)

    def test_negative_interest_rejected(self):
        from domain.tax.holdco_calculations import split_shl_receipt_tax_components
        with pytest.raises(ValueError, match="shl_interest_income_keur.*must be non-negative"):
            split_shl_receipt_tax_components(-50.0, 100.0)

    def test_nan_principal_rejected(self):
        from domain.tax.holdco_calculations import split_shl_receipt_tax_components
        with pytest.raises(ValueError, match="shl_principal_received_keur.*NaN"):
            split_shl_receipt_tax_components(200.0, float("nan"))

    def test_nan_interest_rejected(self):
        from domain.tax.holdco_calculations import split_shl_receipt_tax_components
        with pytest.raises(ValueError, match="shl_interest_income_keur.*NaN"):
            split_shl_receipt_tax_components(float("nan"), 100.0)

    def test_backward_alias_still_works(self):
        """split_shl_tax_treatment is a backward-compatible alias."""
        from domain.tax.holdco_calculations import split_shl_tax_treatment
        taxable_int, non_taxable_principal = split_shl_tax_treatment(200.0, 500.0)
        assert taxable_int == 200.0
        assert non_taxable_principal == 500.0



# ── Tests: alias functions ────────────────────────────────────────────────────

class TestAliasFunctions:
    def test_split_shl_tax_treatment(self):
        from domain.tax.holdco_calculations import split_shl_tax_treatment
        taxable_int, non_taxable_principal = split_shl_tax_treatment(200.0, 500.0)
        assert taxable_int == 200.0
        assert non_taxable_principal == 500.0  # principal amount preserved (not 0)

    def test_split_shl_tax_treatment_zero_principal(self):
        from domain.tax.holdco_calculations import split_shl_tax_treatment
        taxable_int, non_taxable_principal = split_shl_tax_treatment(100.0, 0.0)
        assert taxable_int == 100.0
        assert non_taxable_principal == 0.0

    def test_split_shl_tax_treatment_negative_principal_rejected(self):
        from domain.tax.holdco_calculations import split_shl_tax_treatment
        with pytest.raises(ValueError, match="shl_principal_received_keur.*must be non-negative"):
            split_shl_tax_treatment(100.0, -50.0)

    def test_split_shl_tax_treatment_negative_interest_rejected(self):
        from domain.tax.holdco_calculations import split_shl_tax_treatment
        with pytest.raises(ValueError, match="shl_interest_income_keur.*must be non-negative"):
            split_shl_tax_treatment(-50.0, 100.0)

    def test_calculate_interest_deductibility_limit_with_config(self):
        from domain.tax.holdco_calculations import calculate_interest_deductibility_limit_keur
        from domain.tax.holdco_inputs import InterestDeductibilityConfig
        cfg = InterestDeductibilityConfig(interest_limitation_pct_ebitda=0.30)
        deductible, limited = calculate_interest_deductibility_limit_keur(400.0, 1000.0, cfg)
        assert deductible == 300.0
        assert limited == 100.0

    def test_calculate_interest_deductibility_limit_negative_ebitda(self):
        from domain.tax.holdco_calculations import calculate_interest_deductibility_limit_keur
        from domain.tax.holdco_inputs import InterestDeductibilityConfig
        cfg = InterestDeductibilityConfig(interest_limitation_pct_ebitda=0.30)
        deductible, limited = calculate_interest_deductibility_limit_keur(200.0, -100.0, cfg)
        assert deductible == 0.0
        assert limited == 200.0

    def test_calculate_interest_deductibility_limit_no_limit(self):
        from domain.tax.holdco_calculations import calculate_interest_deductibility_limit_keur
        from domain.tax.holdco_inputs import InterestDeductibilityConfig
        cfg = InterestDeductibilityConfig(interest_limitation_pct_ebitda=None)
        deductible, limited = calculate_interest_deductibility_limit_keur(200.0, 1000.0, cfg)
        assert deductible == 200.0
        assert limited == 0.0

    def test_calculate_holdco_taxable_income_before_cit_alias(self):
        from domain.tax.holdco_calculations import (
            calculate_holdco_taxable_income_before_cit_keur,
            calculate_holdco_taxable_income_before_limitations,
        )
        result = calculate_holdco_taxable_income_before_cit_keur(1000.0, 200.0, 50.0)
        expected = calculate_holdco_taxable_income_before_limitations(1000.0, 200.0, 50.0)
        assert result == expected == 1150.0

    def test_calculate_holdco_taxable_income_before_cit_rejects_negative(self):
        from domain.tax.holdco_calculations import calculate_holdco_taxable_income_before_cit_keur
        with pytest.raises(ValueError, match="dividend_income_keur.*must be non-negative"):
            calculate_holdco_taxable_income_before_cit_keur(-100.0, 200.0, 50.0)
