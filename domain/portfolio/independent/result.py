"""Phase 1 MVP: Independent SPV portfolio result.

Preserves per-SPV outputs and provides aggregate summary.
No pooled debt sculpting, no shared financing.
"""
from __future__ import annotations

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
    equity_irr: float            # levered equity IRR (%)
    total_revenue_keur: float
    total_ebitda_keur: float
    total_tax_keur: float
    total_senior_ds_keur: float
    total_distribution_keur: float
    avg_dscr: float
    min_dscr: float
    # Full period result for audit
    waterfall_result: WaterfallResult
    # Validation warnings (if any assumptions incomplete)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class IndependentPortfolioResult:
    """Result of independent SPV portfolio aggregation (Phase 1 MVP).

    Each SPV runs independently. Results are summed/min'd for portfolio-level KPIs.

    No portfolio-level debt sculpting. No shared financing.
    Per-SPV waterfall results are preserved for audit.

    IRR semantics:
    - simple_avg_project_irr and simple_avg_equity_irr are UNWEIGHTED
      averages of per-SPV IRRs. They are NOT true portfolio XIRR values.
    - True portfolio IRR requires date-aligned cash flow aggregation and
      is deferred to a later phase.
    """
    portfolio_name: str

    # Per-SPV outputs (preserved)
    spv_outputs: tuple[SPVOutput, ...]

    # Aggregate summary (sum across SPVs where applicable)
    total_revenue_keur: float
    total_ebitda_keur: float
    total_tax_keur: float
    total_senior_ds_keur: float
    total_distribution_keur: float

    # DSCR aggregation
    min_dscr: float              # minimum across all SPVs (conservative)
    avg_dscr: float             # unweighted average of per-SPV avg DSCRs

    # Per-SPV IRRs (available from waterfall result)
    spv_project_irrs: tuple[float, ...]   # per-SPV project IRR
    spv_equity_irrs: tuple[float, ...]    # per-SPV equity IRR

    # Simple averages of per-SPV IRRs — NOT true portfolio IRR values.
    # These are computed as unweighted averages of individual SPV IRRs
    # for convenience only. True portfolio IRR requires XIRR over the
    # full portfolio cash flow timeline and is NOT implemented in Phase 1.
    simple_avg_project_irr: float = 0.0
    simple_avg_equity_irr: float = 0.0

    # DSRF status (Phase 1: always disabled)
    dsrf_enabled: bool = False

    # Portfolio-level validation warnings accumulated from all SPV runs.
    # These are deduplicated across SPVs.
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def num_spvs(self) -> int:
        return len(self.spv_outputs)

    def warning_summary(self) -> str:
        """Human-readable warning summary."""
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

    Sums revenue, EBITDA, tax, debt service, distributions.
    Min DSCR = minimum across SPVs (conservative for lenders).
    Avg DSCR = unweighted average of per-SPV average DSCRs.
    Simple-average IRRs: unweighted average of per-SPV IRRs (NOT true portfolio IRR).
    """
    total_rev = sum(s.total_revenue_keur for s in spv_outputs)
    total_ebitda = sum(s.total_ebitda_keur for s in spv_outputs)
    total_tax = sum(s.total_tax_keur for s in spv_outputs)
    total_senior_ds = sum(s.total_senior_ds_keur for s in spv_outputs)
    total_dist = sum(s.total_distribution_keur for s in spv_outputs)

    dscrs = [s.avg_dscr for s in spv_outputs if s.avg_dscr > 0]
    min_dscr = min((s.min_dscr for s in spv_outputs if s.min_dscr > 0), default=0.0)
    avg_dscr = sum(dscrs) / len(dscrs) if dscrs else 0.0

    project_irrs = [s.project_irr for s in spv_outputs if s.project_irr > 0]
    equity_irrs = [s.equity_irr for s in spv_outputs if s.equity_irr > 0]

    avg_proj_irr = sum(project_irrs) / len(project_irrs) if project_irrs else 0.0
    avg_eq_irr = sum(equity_irrs) / len(equity_irrs) if equity_irrs else 0.0

    # Collect portfolio-level warnings from all SPVs (deduplicated)
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
