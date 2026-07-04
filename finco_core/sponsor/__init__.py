"""finco_core.sponsor — Sponsor cashflow engine.

V2-4: Authoritative. domain.returns.* and domain.sponsor.* are compatibility shims.

Covers: sponsor cashflow, multi-investor waterfall, equity IRR computation (XIRR),
distribution schedule.
"""
from finco_core.sponsor.xirr import xirr, xirr_bisection, robust_xirr
from finco_core.sponsor.xnpv import xnpv, xnpv_schedule
from finco_core.sponsor.sponsor_cashflows import build_sponsor_cashflows
from finco_core.sponsor.sponsor_waterfall_tier import (
    TierType,
    CompoundingConvention,
    SponsorShare,
    SponsorWaterfallTier,
    WaterfallTierValidationResult,
)
from finco_core.sponsor.preferred_return_calculator import (
    PreferredReturnCalculatorInputs,
    calculate_preferred_return,
)
from finco_core.sponsor.waterfall_allocation_result import (
    TierAllocationEntry,
    PeriodWaterfallResult,
    WaterfallAllocationResult,
)
from finco_core.sponsor.xirr_runner import SponsorXirrResult, xirr_with_convergence

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
