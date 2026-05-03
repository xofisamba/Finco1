"""Tax engine — period-based tax computation with ATAD and loss carryforward."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxPeriodResult:
    """Result of tax calculation for a single period."""
    taxable_income_keur: float
    tax_keur: float
    loss_carryforward_remaining_keur: float
    atad_addback_keur: float


def compute_period_tax(
    ebitda_keur: float,
    depreciation_keur: float,
    senior_interest_keur: float,
    shl_interest_keur: float,
    loss_carryforward_keur: float,
    tax_rate: float,
    atad_ebitda_limit: float = 0.30,
    atad_min_threshold_keur: float = 3000.0,
    loss_carryforward_cap: float = 1.0,
) -> TaxPeriodResult:
    """
    Compute tax for a single period.

    Taxable income = EBITDA - depreciation - interest + ATAD addback - loss carryforward
    Tax = max(0, taxable_income) * tax_rate

    Args:
        ebitda_keur: EBITDA in kEUR
        depreciation_keur: Depreciation in kEUR
        senior_interest_keur: Senior debt interest in kEUR
        shl_interest_keur: SHL interest in kEUR (deductible portion)
        loss_carryforward_keur: Prior tax losses available to apply
        tax_rate: Corporate tax rate (e.g., 0.10 for 10%)
        atad_ebitda_limit: ATAD EBITDA limit (default 30%)
        atad_min_threshold_keur: ATAD minimum interest threshold (default 3000.0 kEUR)
        loss_carryforward_cap: Max % of profit that can be offset by losses (default 1.0 = 100%)

    Returns:
        TaxPeriodResult with taxable income, tax, remaining loss CF, ATAD addback
    """
    # Total deductible interest
    total_interest = senior_interest_keur + shl_interest_keur

    # ATAD: limit interest deduction to min(30% EBITDA, 3000 kEUR)
    ebitda_limit = ebitda_keur * atad_ebitda_limit
    deductible_interest_limit = max(ebitda_limit, atad_min_threshold_keur)

    if total_interest <= deductible_interest_limit:
        deductible_interest = total_interest
        atad_addback = 0.0
    else:
        deductible_interest = deductible_interest_limit
        atad_addback = total_interest - deductible_interest_limit

    # Taxable income
    taxable_income = (
        ebitda_keur
        - depreciation_keur
        - deductible_interest
        + atad_addback
        - loss_carryforward_keur
    )
    taxable_income = max(0.0, taxable_income)

    # Tax
    tax_keur = taxable_income * tax_rate

    # Remaining loss carryforward (what wasn't used this period)
    # Loss used = min(loss_carryforward_keur, taxable_before_loss_offset)
    taxable_before_loss = (
        ebitda_keur
        - depreciation_keur
        - deductible_interest
        + atad_addback
    )
    loss_used = min(loss_carryforward_keur, max(0.0, taxable_before_loss))
    remaining_loss_cf = max(0.0, loss_carryforward_keur - loss_used)

    return TaxPeriodResult(
        taxable_income_keur=taxable_income,
        tax_keur=tax_keur,
        loss_carryforward_remaining_keur=remaining_loss_cf,
        atad_addback_keur=atad_addback,
    )
