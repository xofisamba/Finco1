"""Phase 4C SHL end-to-end integration layer.

Bridges the SHL engine output to the portfolio/waterfall flow without
direct coupling between SHL engine internals and waterfall engine internals.

No sculpting. No capitalization. No tax logic.
"""
from __future__ import annotations

from typing import Optional

from domain.portfolio.shl.result import (
    SHLFacilityResult,
    SHLPortfolioResult,
    SHLPeriodResult,
)


def build_shl_period_lookup(
    shl_result: SHLFacilityResult,
) -> dict[int, tuple[float, float]]:
    """Build a period-index → (interest_keur, principal_keur) lookup from an SHL facility result.

    This is the integration bridge: SHL engine output is mapped to a simple
    dict that can be used to annotate waterfall periods without coupling
    to SHL engine internals.

    Parameters
    ----------
    shl_result : SHLFacilityResult
        Result from run_shl_facility()

    Returns
    -------
    dict[int, tuple[float, float]]
        Mapping from period_index → (interest_paid_keur, principal_paid_keur).
        Returns empty dict if shl_result has no periods.

    Example
    -------
    >>> lookup = build_shl_period_lookup(facility_result)
    >>> lookup[0]
    (50.0, 200.0)
    >>> lookup[1]
    (45.0, 200.0)
    """
    if not shl_result or not shl_result.periods:
        return {}

    return {
        p.period_index: (p.interest_paid_keur, p.principal_paid_keur)
        for p in shl_result.periods
    }


def inject_shl_into_waterfall_periods(
    wf_periods: list,
    shl_lookup: dict[int, tuple[float, float]],
) -> None:
    """Inject SHL interest/principal into waterfall period objects in-place.

    This is the actual integration hook: SHL cash flows are written directly
    onto waterfall period objects so HoldCo (via _safe_get_float) can read them.

    SHL principal is NOT deducted from distribution_keur in this phase
    (deferred to future retained-earnings / cash-account phase).

    Parameters
    ----------
    wf_periods : list
        List of waterfall period objects (e.g. WaterfallPeriod instances).
        Modified in-place.
    shl_lookup : dict[int, tuple[float, float]]
        Period-index → (interest_keur, principal_keur) lookup.
        Periods not in lookup receive shl_interest_keur=0.0, shl_principal_keur=0.0.
    """
    for p in wf_periods:
        idx = getattr(p, "period_index", None)
        if idx is not None and idx in shl_lookup:
            interest, principal = shl_lookup[idx]
        else:
            interest, principal = 0.0, 0.0
        # Set attributes directly on the period object
        p.shl_interest_keur = float(interest)
        p.shl_principal_keur = float(principal)


__all__ = [
    "build_shl_period_lookup",
    "inject_shl_into_waterfall_periods",
]
