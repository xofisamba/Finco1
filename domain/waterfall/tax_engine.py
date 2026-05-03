"""Tax engine — period-based tax computation with ATAD, loss carryforward, and fiscal reintegration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxPeriodResult:
    """Result of tax calculation for a single period.
    
    All fields in kEUR for auditability.
    """
    # Pre-loss taxable income components
    ebitda_keur: float
    depreciation_keur: float
    deductible_interest_keur: float
    disallowed_interest_keur: float  # ATAD addback
    fiscal_reintegration_keur: float  # Construction-period cost add-back (HR tax law)
    
    # Loss carryforward application
    taxable_income_before_losses_keur: float  # Before loss CF application
    loss_carryforward_applied_keur: float
    loss_carryforward_remaining_keur: float
    
    # Final taxable income and tax
    taxable_income_keur: float  # After loss CF
    tax_keur: float


def compute_period_tax(
    ebitda_keur: float,
    depreciation_keur: float,
    senior_interest_keur: float,
    shl_interest_keur: float,
    loss_carryforward_keur: float,
    tax_rate: float,
    fiscal_reintegration_keur: float = 0.0,
    atad_applies: bool = True,
    atad_ebitda_limit: float = 0.30,
    atad_min_threshold_keur: float = 3000.0,
    loss_carryforward_cap: float = 1.0,
) -> TaxPeriodResult:
    """
    Compute tax for a single period.
    
    Taxable income = EBITDA - depreciation - interest + ATAD addback + fiscal_reintegration - loss_carryforward
    Tax = max(0, taxable_income) * tax_rate
    
    Args:
        ebitda_keur: EBITDA in kEUR
        depreciation_keur: Depreciation in kEUR
        senior_interest_keur: Senior debt interest in kEUR
        shl_interest_keur: SHL interest in kEUR
        loss_carryforward_keur: Prior tax losses available to apply
        tax_rate: Corporate tax rate (e.g., 0.10 for 10%)
        fiscal_reintegration_keur: Construction-period cost add-back (IDC, bank fees, etc.)
        atad_applies: Whether ATAD interest limitation applies (default True)
        atad_ebitda_limit: ATAD EBITDA limit (default 30%)
        atad_min_threshold_keur: ATAD minimum interest threshold (default 3000.0 kEUR)
        loss_carryforward_cap: Max % of profit that can be offset by losses (default 1.0 = 100%)

    Returns:
        TaxPeriodResult with full audit trail
    """
    total_interest = senior_interest_keur + shl_interest_keur
    
    # ATAD: limit interest deduction
    if atad_applies:
        ebitda_limit = ebitda_keur * atad_ebitda_limit
        deductible_interest_limit = max(ebitda_limit, atad_min_threshold_keur)
        
        if total_interest <= deductible_interest_limit:
            deductible_interest = total_interest
            disallowed_interest = 0.0
        else:
            deductible_interest = deductible_interest_limit
            disallowed_interest = total_interest - deductible_interest_limit
    else:
        deductible_interest = total_interest
        disallowed_interest = 0.0
    
    # Taxable income before losses (but after all deductables and addbacks)
    taxable_before_losses = (
        ebitda_keur
        - depreciation_keur
        - deductible_interest
        + disallowed_interest
        + fiscal_reintegration_keur
    )
    
    # Apply loss carryforward (capped at loss_carryforward_cap of profit)
    max_offset = taxable_before_losses * loss_carryforward_cap if taxable_before_losses > 0 else 0.0
    loss_used = min(loss_carryforward_keur, max(0.0, max_offset))
    remaining_loss_cf = max(0.0, loss_carryforward_keur - loss_used)
    
    # Final taxable income
    taxable_income = max(0.0, taxable_before_losses - loss_used)
    
    # Tax
    tax_keur = taxable_income * tax_rate
    
    return TaxPeriodResult(
        ebitda_keur=ebitda_keur,
        depreciation_keur=depreciation_keur,
        deductible_interest_keur=deductible_interest,
        disallowed_interest_keur=disallowed_interest,
        fiscal_reintegration_keur=fiscal_reintegration_keur,
        taxable_income_before_losses_keur=max(0.0, taxable_before_losses),
        loss_carryforward_applied_keur=loss_used,
        loss_carryforward_remaining_keur=remaining_loss_cf,
        taxable_income_keur=taxable_income,
        tax_keur=tax_keur,
    )