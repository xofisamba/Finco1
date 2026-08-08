"""Tax engine — period-based tax computation with ATAD, loss carryforward, and fiscal reintegration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finco_core.inputs._models import ShlInterestDeductibilityMode


@dataclass(frozen=True)
class TaxPeriodResult:
    """Result of tax calculation for a single period.
    
    All fields in kEUR for auditability.
    """
    # Pre-loss taxable income components
    ebitda_keur: float
    co2_cit_bridge_keur: float  # CO2 revenue included in EBITDA for CIT (Phase 9)
    depreciation_keur: float
    deductible_interest_keur: float
    disallowed_interest_keur: float  # ATAD addback
    fiscal_reintegration_keur: float  # Construction-period cost add-back (HR tax law)
    shl_non_deductible_addback_keur: float  # C3B3C: SHL interest addback per deductibility mode
    
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
    co2_revenue_keur: float = 0.0,  # Phase 9: CO2 CIT bridge — adds to EBITDA for taxable income
    shl_interest_deductibility: "ShlInterestDeductibilityMode | None" = None,
    shl_interest_deductible_pct: float | None = None,
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
        shl_interest_deductibility: C3B3C typed SHL deductibility mode. When None,
            falls back to legacy behavior (SHL fully deductible, included in total_interest).
        shl_interest_deductible_pct: Required for CUSTOM_DEDUCTIBLE_PERCENTAGE mode.

    Returns:
        TaxPeriodResult with full audit trail
    """
    # ── C3B3C: SHL non-deductible addback ──────────────────────────────────────
    # Compute the SHL fiscal addback and how much SHL interest enters the ATAD pool.
    # Senior interest is ALWAYS in the ATAD pool (never non-deductible via SHL rule).
    # SHL interest treatment depends on shl_interest_deductibility mode.
    from finco_core.inputs._models import ShlInterestDeductibilityMode as _ShlMode

    shl_non_deductible_addback = 0.0
    shl_in_atad_pool = shl_interest_keur  # default: SHL enters ATAD pool (legacy)

    if shl_interest_deductibility is not None:
        if shl_interest_deductibility == _ShlMode.FULLY_NON_DEDUCTIBLE:
            # SHL interest is entirely non-deductible: add back full amount,
            # remove from ATAD deductible pool.
            shl_non_deductible_addback = shl_interest_keur
            shl_in_atad_pool = 0.0
        elif shl_interest_deductibility == _ShlMode.FULLY_DEDUCTIBLE:
            # SHL interest is fully deductible: no addback, enters ATAD pool normally.
            shl_non_deductible_addback = 0.0
            shl_in_atad_pool = shl_interest_keur
        elif shl_interest_deductibility == _ShlMode.CUSTOM_DEDUCTIBLE_PERCENTAGE:
            pct = shl_interest_deductible_pct if shl_interest_deductible_pct is not None else 0.0
            non_ded_frac = 1.0 - pct
            shl_non_deductible_addback = shl_interest_keur * non_ded_frac
            shl_in_atad_pool = shl_interest_keur * pct
        elif shl_interest_deductibility == _ShlMode.SUBJECT_TO_LIMITATIONS:
            # FAIL CLOSED: limitation engine (thin-cap/ATAD interaction for SHL)
            # is not yet implemented generically. Callers must resolve SHL
            # deductibility externally and pass the result as CUSTOM mode.
            raise NotImplementedError(
                "C3B3C_BLOCKED_TUHO_THIN_CAP_FORMULA: "
                "SUBJECT_TO_LIMITATIONS SHL deductibility requires an interest "
                "limitation engine that is not yet implemented. "
                "Set thin_cap_enabled=True only when the formula is proven."
            )

    total_interest = senior_interest_keur + shl_in_atad_pool
    
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
    # Phase 9: CO2 CIT bridge — co2_revenue_keur is added to EBITDA for taxable income
    # C3B3C: shl_non_deductible_addback adds back the non-deductible SHL fraction
    taxable_before_losses = (
        ebitda_keur
        + co2_revenue_keur
        - depreciation_keur
        - deductible_interest
        + disallowed_interest
        + fiscal_reintegration_keur
        + shl_non_deductible_addback
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
        co2_cit_bridge_keur=co2_revenue_keur,
        depreciation_keur=depreciation_keur,
        deductible_interest_keur=deductible_interest,
        disallowed_interest_keur=disallowed_interest,
        fiscal_reintegration_keur=fiscal_reintegration_keur,
        shl_non_deductible_addback_keur=shl_non_deductible_addback,
        taxable_income_before_losses_keur=max(0.0, taxable_before_losses),
        loss_carryforward_applied_keur=loss_used,
        loss_carryforward_remaining_keur=remaining_loss_cf,
        taxable_income_keur=taxable_income,
        tax_keur=tax_keur,
    )