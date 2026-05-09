"""Phase 1 MVP: Independent SPV portfolio result.

No pooled debt sculpting. No shared financing.
"""
from __future__ import annotations

import math

from dataclasses import dataclass, field
from typing import Optional

from domain.waterfall.waterfall_engine import WaterfallResult


@dataclass(frozen=True)
class SPVOutput:
    """Single SPV output — preserved from independent run."""
    project_code: str
    project_name: str
    # Per-SPV KPIs
    project_irr: float          # unlevered project IRR (%)
    equity_irr: float           # levered equity IRR (%)
    total_revenue_keur: float
    total_ebitda_keur: float
    total_tax_keur: float
    total_senior_ds_keur: float
    total_distribution_keur: float
    avg_dscr: float
    min_dscr: float
    # Full period result for audit (None when SPV failed in non-strict mode)
    waterfall_result: Optional[WaterfallResult]
    # Validation warnings from this SPV (if any)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class IndependentPortfolioResult:
    """Result of independent SPV portfolio aggregation. Phase 1 MVP.

    Each SPV runs independently. Results are summed/min'd for portfolio KPIs.
    No portfolio-level debt sculpting. No shared financing.
    """
    portfolio_name: str
    # Per-SPV outputs (preserved)
    spv_outputs: tuple[SPVOutput, ...]

    # Sums across SPVs
    total_revenue_keur: float
    total_ebitda_keur: float
    total_tax_keur: float
    total_senior_ds_keur: float
    total_distribution_keur: float

    # DSCR: min = conservative (lenders), avg = unweighted average
    min_dscr: float
    avg_dscr: float

    spv_project_irrs: tuple[float, ...]
    spv_equity_irrs: tuple[float, ...]

    # Unweighted averages — NOT true portfolio XIRR.
    # True portfolio IRR requires all cash-flows aligned and XIRR computed — deferred.
    simple_avg_project_irr: float = 0.0
    simple_avg_equity_irr: float = 0.0

    # Phase 1: always False
    dsrf_enabled: bool = False

    # Portfolio-level warnings (deduplicated)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def num_spvs(self) -> int:
        return len(self.spv_outputs)

    def warning_summary(self) -> str:
        """Human-readable portfolio-level warning summary."""
        if not self.warnings:
            return "No warnings."
        lines = [f"Warnings ({len(self.warnings)}):"]
        for w in self.warnings:
            lines.append(f"  - {w}")
        return "\n".join(lines)


def aggregate_independent_results(
    portfolio_name: str,
    spv_outputs: tuple[SPVOutput, ...],
    dsrf_enabled: bool = False,
) -> IndependentPortfolioResult:
    """Aggregate per-SPV outputs into portfolio summary.
    Sums: revenue, EBITDA, tax, senior debt service, distributions.
    Min DSCR = conservative min across SPVs.
    Avg DSCR = unweighted average of per-SPV avg DSCRs.
    Unweighted averages — NOT true portfolio IRR.
    """
    total_rev = sum(s.total_revenue_keur for s in spv_outputs)
    total_ebitda = sum(s.total_ebitda_keur for s in spv_outputs)
    total_tax = sum(s.total_tax_keur for s in spv_outputs)
    total_senior_ds = sum(s.total_senior_ds_keur for s in spv_outputs)
    total_dist = sum(s.total_distribution_keur for s in spv_outputs)

    min_dscr = min((s.min_dscr for s in spv_outputs if s.min_dscr > 0), default=0.0)
    avg_dscr_vals = [s.avg_dscr for s in spv_outputs if s.avg_dscr > 0]
    avg_dscr = sum(avg_dscr_vals) / len(avg_dscr_vals) if avg_dscr_vals else 0.0

    # All finite IRRs included — 0, positive, and negative — no silent filtering
    project_irrs = [
        s.project_irr
        for s in spv_outputs
        if math.isfinite(s.project_irr)
    ]
    equity_irrs = [
        s.equity_irr
        for s in spv_outputs
        if math.isfinite(s.equity_irr)
    ]

    avg_proj_irr = sum(project_irrs) / len(project_irrs) if project_irrs else 0.0
    avg_eq_irr = sum(equity_irrs) / len(equity_irrs) if equity_irrs else 0.0

    # Deduplicate portfolio-level warnings
    all_warnings: list[str] = []
    for s in spv_outputs:
        for w in s.warnings:
            if w not in all_warnings:
                all_warnings.append(w)

    return IndependentPortfolioResult(
        portfolio_name=portfolio_name,
        spv_outputs=spv_outputs,
        total_revenue_keur=total_rev,
        total_ebitda_keur=total_ebitda,
        total_tax_keur=total_tax,
        total_senior_ds_keur=total_senior_ds,
        total_distribution_keur=total_dist,
        min_dscr=min_dscr,
        avg_dscr=avg_dscr,
        spv_project_irrs=tuple(project_irrs),
        spv_equity_irrs=tuple(equity_irrs),
        simple_avg_project_irr=avg_proj_irr,
        simple_avg_equity_irr=avg_eq_irr,
        dsrf_enabled=dsrf_enabled,
        warnings=tuple(all_warnings),
    )


__all__ = [
    "SPVOutput",
    "IndependentPortfolioResult",
    "aggregate_independent_results",
]
