"""
finco_core.sponsor — Sponsor cashflow engine.

Extraction target (V2-3): sponsor cashflow, multi-investor waterfall,
equity IRR computation (XIRR), distribution schedule.

Source: domain/sponsor/, domain/returns/xirr.py, domain/returns/xnpv.py

V2-3: Forward shims to domain sponsor/returns modules.
"""
from domain.returns.xirr import xirr, xirr_bisection, robust_xirr
from domain.returns.xnpv import xnpv, xnpv_schedule
from domain.returns.sponsor_cashflows import build_sponsor_cashflows
from domain.sponsor.sponsor_waterfall_tier import (
    TierType,
    CompoundingConvention,
    SponsorShare,
    SponsorWaterfallTier,
    WaterfallTierValidationResult,
)
from domain.sponsor.preferred_return_calculator import (
    PreferredReturnCalculatorInputs,
    calculate_preferred_return,
)
from domain.sponsor.waterfall_allocation_result import (
    TierAllocationEntry,
    PeriodWaterfallResult,
    WaterfallAllocationResult,
)
from domain.sponsor.xirr import SponsorXirrResult, xirr_with_convergence

__all__ = [
    # Returns
    "xirr",
    "xirr_bisection",
    "robust_xirr",
    "xnpv",
    "xnpv_schedule",
    "build_sponsor_cashflows",
    # Sponsor waterfall tier
    "TierType",
    "CompoundingConvention",
    "SponsorShare",
    "SponsorWaterfallTier",
    "WaterfallTierValidationResult",
    # Preferred return calculator
    "PreferredReturnCalculatorInputs",
    "calculate_preferred_return",
    # Waterfall allocation
    "TierAllocationEntry",
    "PeriodWaterfallResult",
    "WaterfallAllocationResult",
    # Sponsor XIRR
    "SponsorXirrResult",
    "xirr_with_convergence",
]
