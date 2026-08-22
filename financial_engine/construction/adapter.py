"""financial_engine.construction.adapter — Build ConstructionRuntimeConfig from typed PR-9 inputs.

Bridges ConstructionFinancingInput (typed contract, finco_core) to
ConstructionRuntimeConfig (canonical runtime, finco_core.construction.stage_b2).
No project-name dispatch. No identity-based branches.
"""
from __future__ import annotations

from finco_core.construction.stage_b2 import (
    ConstructionRuntimeConfig,
    TimelinePeriod,
    CapexPaymentItem,
    CapexScheduleSet,
    FinancingCostFundingPolicy,
)
from finco_core.inputs.construction_financing import ConstructionFinancingInput


def build_construction_runtime_config(
    construction: ConstructionFinancingInput,
    senior_commitment_keur: float,
    equity_available_keur: float,
    shl_available_keur: float,
) -> ConstructionRuntimeConfig:
    """Build a ConstructionRuntimeConfig from typed ConstructionFinancingInput + funding amounts."""
    n = len(construction.periods)
    timeline = tuple(
        TimelinePeriod(
            index=i,
            start_date=p.start_date,
            end_date=p.end_date,
            interest_fraction=p.interest_fraction,
            active_construction=p.active_construction,
            capex_payment_eligible=p.capex_payment_eligible,
            senior_idc_active=p.senior_idc_active,
            vat_facility_active=False,  # PR9_VAT_FACILITY_DEFERRED
        )
        for i, p in enumerate(construction.periods)
    )
    items = tuple(
        CapexPaymentItem(
            code=item.code,
            name=item.name,
            amount_keur=item.amount_keur,
            payment_weights=item.payment_weights,
            vat_rate=0.0,  # VAT deferred
        )
        for item in construction.capex_items
    )
    capex_schedule = CapexScheduleSet(items=items)

    # Structuring fee payment schedule — uniform if not provided
    if construction.structuring_fee and construction.structuring_fee.payment_weights:
        struct_weights = construction.structuring_fee.payment_weights
    else:
        struct_weights = tuple(1.0 / n for _ in range(n))
    funding_policy = FinancingCostFundingPolicy(structuring_fee_payment_schedule=struct_weights)

    # Build rate parameters from ConstructionSeniorPricingInput
    pricing = construction.senior_pricing
    senior_interest_rate = 0.0
    base_rate = 0.0
    hedge_coverage = 0.0
    swap_margin = 0.0
    forward_swap_margin = 0.0
    cva = 0.0
    external_curve_buffer = 0.0
    euribor_fixings: tuple[float, ...] = ()
    rate_schedule: tuple[float, ...] = ()

    if pricing is not None:
        if pricing.mode == "FLAT_ALL_IN":
            senior_interest_rate = pricing.flat_all_in_rate
        elif pricing.mode == "FIXED_PLUS_MARGIN":
            senior_interest_rate = pricing.fixed_base_rate + pricing.margin_rate
        elif pricing.mode == "FLOATING_PLUS_MARGIN":
            senior_interest_rate = pricing.margin_rate
            euribor_fixings = pricing.floating_base_rate_curve
            external_curve_buffer = pricing.floating_curve_buffer_pct
        elif pricing.mode == "HEDGE_BLEND":
            senior_interest_rate = pricing.margin_rate  # margin component
            base_rate = pricing.fixed_base_rate
            hedge_coverage = pricing.hedge_pct
            swap_margin = pricing.swap_margin
            forward_swap_margin = pricing.forward_swap_adjustment
            cva = pricing.cva
            external_curve_buffer = pricing.floating_curve_buffer_pct
            euribor_fixings = pricing.floating_base_rate_curve
        elif pricing.mode == "EXPLICIT_ALL_IN_SCHEDULE":
            rate_schedule = pricing.explicit_all_in_schedule

    # Commitment fee
    commitment_fee_rate = 0.0
    commitment_fee_basis = "OPENING_UNDRAWN"
    commitment_fee_timing = "SAME_PERIOD"
    if construction.commitment_fee is not None:
        commitment_fee_rate = construction.commitment_fee.rate
        commitment_fee_basis = construction.commitment_fee.balance_basis
        commitment_fee_timing = construction.commitment_fee.capitalization_timing

    # Structuring fee
    structuring_fee_rate = 0.0
    structuring_fee_basis = 0.0
    if construction.structuring_fee is not None:
        structuring_fee_rate = construction.structuring_fee.rate
        structuring_fee_basis = construction.structuring_fee.basis_keur

    # Map IDC balance basis to stage_b2 constants
    idc_balance_basis = construction.idc_balance_basis
    if idc_balance_basis == "CLOSING_DRAWN":
        idc_balance_basis = "CURRENT_CLOSING_DRAWN"

    # Map commitment fee balance basis
    if commitment_fee_basis == "CLOSING_UNDRAWN":
        commitment_fee_basis = "CURRENT_CLOSING_UNDRAWN"

    return ConstructionRuntimeConfig(
        timeline=timeline,
        capex_schedule=capex_schedule,
        funding_policy=funding_policy,
        source_total_uses_validation_keur=(),
        equity_available_keur=equity_available_keur,
        shl_available_keur=shl_available_keur,
        senior_commitment_keur=senior_commitment_keur,
        senior_interest_rate=senior_interest_rate,
        senior_commitment_fee_rate=commitment_fee_rate,
        senior_interest_rate_schedule=rate_schedule,
        base_rate=base_rate,
        hedge_coverage=hedge_coverage,
        swap_margin=swap_margin,
        forward_swap_margin=forward_swap_margin,
        cva=cva,
        external_curve_buffer=external_curve_buffer,
        euribor_1m_fixings=euribor_fixings,
        senior_idc_balance_basis=idc_balance_basis,
        senior_commitment_fee_balance_basis=commitment_fee_basis,
        senior_idc_capitalization_timing=construction.idc_capitalization_timing,
        senior_commitment_fee_capitalization_timing=commitment_fee_timing,
        structuring_fee_rate=structuring_fee_rate,
        structuring_fee_basis_keur=structuring_fee_basis,
        vat_facility_interest_rate=0.0,  # PR9_VAT_FACILITY_DEFERRED
        vat_facility_commitment_fee_rate=0.0,
        vat_facility_commitment_keur=0.0,
        convergence_tolerance_keur=construction.convergence_tolerance_keur,
        max_iterations=construction.max_iterations,
    )
