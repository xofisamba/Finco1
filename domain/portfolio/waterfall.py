"""Portfolio aggregation — aggregate multiple project waterfalls."""
from dataclasses import dataclass, field
from typing import Optional

from domain.portfolio.inputs import PortfolioInputs, AggregationMethod


@dataclass(frozen=True)
class PortfolioResult:
    """Aggregated portfolio result across all projects."""
    # Per-project summary metrics (name → value)
    project_revenues_keur: dict[str, float]
    project_ebitdas_keur: dict[str, float]
    project_irr: dict[str, float]
    project_npv: dict[str, float]
    # Portfolio-level aggregates
    total_revenue_keur: float
    total_ebitda_keur: float
    total_tax_keur: float
    avg_project_irr: float
    min_project_irr: float
    max_project_irr: float
    equity_irr: float
    sponsor_irr: float
    # Weighted capacity
    capacity_weighted_irr: float


def _weighted_irr(results: list, weights: list[float]) -> float:
    """Return weighted average IRR across projects."""
    if not results:
        return 0.0
    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0
    return sum(r * w for r, w in zip(results, weights)) / total_weight


def run_portfolio_waterfall(
    portfolio: PortfolioInputs,
    project_results: dict[str, dict],
) -> PortfolioResult:
    """Aggregate multiple project waterfall results into a portfolio view.

    Args:
        portfolio: PortfolioInputs describing the projects and weights
        project_results: dict keyed by project name, each containing:
            - 'revenue_keur': total revenue float
            - 'ebitda_keur': total EBITDA float
            - 'tax_keur': total tax float
            - 'project_irr': project IRR float
            - 'equity_irr': equity IRR float
            - 'sponsor_irr': sponsor IRR float
            - 'project_npv': project NPV float

    Returns:
        PortfolioResult with aggregated metrics.

    Aggregation logic:
    - Revenue/EBITDA/tax: summed across all projects
    - IRRs: weighted average by project weight
    """
    project_revenues: dict[str, float] = {}
    project_ebitdas: dict[str, float] = {}
    project_irr: dict[str, float] = {}
    project_npvs: dict[str, float] = {}
    total_revenue = 0.0
    total_ebitda = 0.0
    total_tax = 0.0
    irr_values: list[float] = []
    irr_weights: list[float] = []

    for proj in portfolio.projects:
        name = proj.name
        if name not in project_results:
            continue
        res = project_results[name]

        rev = res.get("revenue_keur", 0.0)
        ebitda = res.get("ebitda_keur", 0.0)
        tax = res.get("tax_keur", 0.0)
        irr = res.get("project_irr", 0.0)
        npv = res.get("project_npv", 0.0)

        project_revenues[name] = rev
        project_ebitdas[name] = ebitda
        project_irr[name] = irr
        project_npvs[name] = npv

        total_revenue += rev
        total_ebitda += ebitda
        total_tax += tax

        if irr != 0.0:
            irr_values.append(irr)
            irr_weights.append(proj.weight)

    # Weighted IRR
    cap_weighted_irr = 0.0
    avg_irr = 0.0
    min_irr = 0.0
    max_irr = 0.0
    if irr_values:
        total_w = sum(irr_weights)
        avg_irr = sum(v * w for v, w in zip(irr_values, irr_weights)) / total_w
        cap_weighted_irr = avg_irr  # same when weighting by project weight
        min_irr = min(irr_values)
        max_irr = max(irr_values)

    return PortfolioResult(
        project_revenues_keur=project_revenues,
        project_ebitdas_keur=project_ebitdas,
        project_irr=project_irr,
        project_npv=project_npvs,
        total_revenue_keur=total_revenue,
        total_ebitda_keur=total_ebitda,
        total_tax_keur=total_tax,
        avg_project_irr=avg_irr,
        min_project_irr=min_irr,
        max_project_irr=max_irr,
        equity_irr=0.0,  # placeholder — requires full equity CF aggregation
        sponsor_irr=0.0,
        capacity_weighted_irr=cap_weighted_irr,
    )


__all__ = [
    "PortfolioResult",
    "run_portfolio_waterfall",
]
