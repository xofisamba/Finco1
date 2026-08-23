"""finco_core.construction.allocator — Canonical per-period construction source allocator.

PR9_CANONICAL_CONSTRUCTION_ALLOCATOR: single authority for per-period Senior draw
calculation during construction. Both Stage B2 and the G2A construction schedule
must use this function so Senior draw used for IDC == Senior draw in funding schedule.

Waterfall order (per project-finance convention):
  1. Share Capital
  2. Share Premium
  3. Other Committed Equity (other_committed_equity_keur)
  4. Additional Equity (residual equity derived by G2A fixed point)
  5. SHL (shl_cash_keur)
  6. Junior (junior_keur)
  7. Senior (senior_commitment_keur — drawn last, residual)

Each layer fills in order until its available amount is exhausted or the period
need is met. Senior is the residual after all other sources.

Identity-free. No project-name dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConstructionPeriodAllocation:
    """Canonical per-period source allocation result."""
    period_index: int
    period_uses_keur: float
    share_capital_draw_keur: float
    share_premium_draw_keur: float
    other_committed_equity_draw_keur: float
    additional_equity_draw_keur: float
    shl_draw_keur: float
    junior_draw_keur: float
    senior_draw_keur: float
    total_sources_keur: float
    residual_keur: float  # total_sources - period_uses (should be ~0)


def allocate_construction_sources_per_period(
    period_uses: tuple[float, ...],
    share_capital_keur: float,
    share_premium_keur: float,
    other_committed_equity_keur: float,
    additional_equity_keur: float,
    shl_cash_keur: float,
    junior_keur: float,
    senior_commitment_keur: float,
    tolerance_keur: float = 1e-9,
) -> tuple[ConstructionPeriodAllocation, ...]:
    """Allocate construction sources per period using canonical waterfall.

    Drains each source in waterfall order: Share Capital → Share Premium →
    Other Committed Equity → Additional Equity → SHL → Junior → Senior.

    Returns per-period allocations. The senior_draw per period is the canonical
    value to feed into Stage B2 for IDC computation.

    Raises ValueError if total sources < total uses (funding shortfall).
    """
    n = len(period_uses)
    if n == 0:
        return ()

    total_uses = sum(period_uses)
    total_sources = (
        share_capital_keur + share_premium_keur + other_committed_equity_keur
        + additional_equity_keur + shl_cash_keur + junior_keur + senior_commitment_keur
    )
    if total_sources < total_uses - tolerance_keur:
        raise ValueError(
            f"PR9_CONSTRUCTION_FUNDING_SHORTFALL: "
            f"total_sources={total_sources:.6f} < total_uses={total_uses:.6f}, "
            f"shortfall={total_uses - total_sources:.6f} kEUR"
        )

    # Remaining pool for each source
    remaining = {
        "share_capital": share_capital_keur,
        "share_premium": share_premium_keur,
        "other_committed_equity": other_committed_equity_keur,
        "additional_equity": additional_equity_keur,
        "shl": shl_cash_keur,
        "junior": junior_keur,
        "senior": senior_commitment_keur,
    }
    # Waterfall order
    _order = [
        "share_capital", "share_premium", "other_committed_equity",
        "additional_equity", "shl", "junior", "senior"
    ]

    allocations = []
    for idx, uses in enumerate(period_uses):
        need = uses
        draws: dict[str, float] = {k: 0.0 for k in _order}
        for src in _order:
            if need <= tolerance_keur:
                break
            available = remaining[src]
            draw = min(available, need)
            draws[src] = draw
            remaining[src] -= draw
            need -= draw
        total_s = sum(draws.values())
        allocations.append(ConstructionPeriodAllocation(
            period_index=idx,
            period_uses_keur=uses,
            share_capital_draw_keur=draws["share_capital"],
            share_premium_draw_keur=draws["share_premium"],
            other_committed_equity_draw_keur=draws["other_committed_equity"],
            additional_equity_draw_keur=draws["additional_equity"],
            shl_draw_keur=draws["shl"],
            junior_draw_keur=draws["junior"],
            senior_draw_keur=draws["senior"],
            total_sources_keur=total_s,
            residual_keur=total_s - uses,
        ))

    return tuple(allocations)
