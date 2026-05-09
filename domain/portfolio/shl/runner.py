"""Phase 4A SHL engine — straight-line amortization schedule generator.

No sculpting. No capitalization. No circular funding.
Simple deterministic schedule for architectural foundation.

Architecture:
  SPV waterfall
    → dividend upstream
    → SHL interest upstream
    → SHL principal upstream
    → HoldCo aggregation
    → future tax engine
    → future sponsor layer
"""
from __future__ import annotations

from dataclasses import replace

from domain.portfolio.shl.inputs import SHLFacility, SHLPortfolioInputs
from domain.portfolio.shl.result import (
    SHLPeriodResult,
    SHLFacilityResult,
    SHLPortfolioResult,
)


def run_shl_facility(facility: SHLFacility) -> SHLFacilityResult:
    """Run straight-line amortization for a single SHL facility.

    No sculpting. No capitalization.
    - Principal paid evenly over tenor periods
    - Interest = opening_balance * rate / frequency
    - Closing balance forced to 0 at end of tenor
    - No negative balances at any point

    Parameters
    ----------
    facility : SHLFacility
        SHL facility definition

    Returns
    -------
    SHLFacilityResult
        Full period-by-period schedule
    """
    num_periods = facility.tenor_years * facility.payment_frequency_per_year

    if num_periods == 0 or facility.principal_keur == 0:
        # No periods needed — return empty result
        return SHLFacilityResult(
            facility=facility,
            periods=(),
            total_interest_paid_keur=0.0,
            total_principal_paid_keur=0.0,
        )

    # Straight-line principal: equal installments each period
    principal_per_period = facility.principal_keur / num_periods
    rate_per_period = facility.interest_rate_pa / facility.payment_frequency_per_year

    periods: list[SHLPeriodResult] = []
    balance = facility.principal_keur
    total_interest = 0.0
    total_principal = 0.0

    for idx in range(num_periods):
        opening = balance

        # Interest on opening balance
        interest = opening * rate_per_period

        # Principal portion (straight-line)
        principal = principal_per_period

        # Ensure we don't overpay — last period pays remaining balance
        if idx == num_periods - 1:
            principal = max(0.0, opening)  # pay off whatever remains
            interest = opening * rate_per_period  # interest on last period opening

        # Safety: prevent negative balance
        total_payment = principal + interest
        if total_payment > opening + 1e-6:
            # Scale proportionally if payment would exceed balance
            scale = opening / total_payment if total_payment > 0 else 0.0
            principal *= scale
            interest *= scale

        closing = max(0.0, opening - principal)
        total_interest += interest
        total_principal += principal
        balance = closing

        periods.append(SHLPeriodResult(
            period_index=idx,
            opening_balance_keur=opening,
            interest_accrued_keur=interest,
            interest_paid_keur=interest,  # no capitalization → accrued = paid
            principal_paid_keur=principal,
            closing_balance_keur=closing,
        ))

    return SHLFacilityResult(
        facility=facility,
        periods=tuple(periods),
        total_interest_paid_keur=total_interest,
        total_principal_paid_keur=total_principal,
    )


def run_shl_portfolio(inputs: SHLPortfolioInputs) -> SHLPortfolioResult:
    """Run SHL schedule for all facilities in portfolio.

    Parameters
    ----------
    inputs : SHLPortfolioInputs
        Portfolio-level SHL configuration

    Returns
    -------
    SHLPortfolioResult
        Aggregated result for all facilities
    """
    facilities_results: list[SHLFacilityResult] = []
    total_interest = 0.0
    total_principal = 0.0

    for facility in inputs.facilities:
        result = run_shl_facility(facility)
        facilities_results.append(result)
        total_interest += result.total_interest_paid_keur
        total_principal += result.total_principal_paid_keur

    return SHLPortfolioResult(
        facilities=tuple(facilities_results),
        total_interest_paid_keur=total_interest,
        total_principal_paid_keur=total_principal,
        warnings=(),
    )