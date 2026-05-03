"""Pooled-financing portfolio waterfall skeleton.

Scope:
- Aligns periods across project waterfalls
- Pools CFADS (EBITDA - tax) by period
- Computes portfolio DSCR against one pooled debt service
- Returns PortfolioResult with per-project results exposed

Limitations:
- Debt sizing is a skeleton (deterministic schedule for tests)
- No cross-default enforcement logic yet
"""
from dataclasses import dataclass
from typing import Optional
from datetime import date

from domain.waterfall.waterfall_engine import WaterfallResult
from domain.financing.sculpting_iterative import closed_form_sculpt


@dataclass(frozen=True)
class PortfolioPeriod:
    period: int
    date: date
    pooled_revenue_keur: float
    pooled_ebitda_keur: float
    pooled_tax_keur: float
    pooled_cfads_keur: float
    portfolio_senior_interest_keur: float
    portfolio_senior_principal_keur: float
    portfolio_senior_ds_keur: float
    dscr: float


@dataclass(frozen=True)
class PortfolioResult:
    """Result of a portfolio pooled-financing waterfall."""
    periods: tuple[PortfolioPeriod, ...]
    project_results: tuple[tuple[str, WaterfallResult], ...]
    total_revenue_keur: float
    total_ebitda_keur: float
    total_tax_keur: float
    total_senior_ds_keur: float
    avg_dscr: float
    min_dscr: float
    # Aggregated debt schedule
    portfolio_debt_keur: float
    pooled_cfads_schedule: tuple[float, ...]
    portfolio_debt_service_schedule: tuple[float, ...]
    # IRR placeholders (require full cash-flow aggregation — not yet)
    portfolio_project_irr: float = 0.0
    portfolio_sponsor_irr: float = 0.0


def aggregate_project_results(
    project_results: tuple[tuple[str, WaterfallResult], ...],
) -> list[dict]:
    """Align project waterfalls by date, sum revenue/EBITDA/tax/CFADS."""
    # Collect all unique dates across projects
    date_map: dict[date, dict] = {}
    for name, result in project_results:
        for pr in result.periods:
            if not pr.is_operation:
                continue
            d = pr.date
            if d not in date_map:
                date_map[d] = dict(revenue=0.0, ebitda=0.0, tax=0.0, cfads=0.0,
                             senior_interest=0.0, senior_principal=0.0)
            date_map[d]["revenue"] += getattr(pr, "revenue_keur", 0.0)
            date_map[d]["ebitda"] += pr.ebitda_keur
            date_map[d]["tax"] += pr.tax_keur
            date_map[d]["cfads"] += pr.ebitda_keur - pr.tax_keur
            date_map[d]["senior_interest"] += pr.senior_interest_keur
            date_map[d]["senior_principal"] += pr.senior_principal_keur

    periods = []
    for d in sorted(date_map.keys()):
        m = date_map[d]
        periods.append({
            "date": d,
            "pooled_revenue_keur": m["revenue"],
            "pooled_ebitda_keur": m["ebitda"],
            "pooled_tax_keur": m["tax"],
            "pooled_cfads_keur": m["cfads"],
            "portfolio_senior_interest_keur": m["senior_interest"],
            "portfolio_senior_principal_keur": m["senior_principal"],
        })
    return periods


def portfolio_cfads_schedule(pooled_periods: list[dict]) -> list[float]:
    return [p["pooled_cfads_keur"] for p in pooled_periods]


def build_portfolio_debt_service_schedule(
    cfads_schedule: list[float],
    financing,  # shared FinancingParams
    rate_per_period: float,
) -> tuple[float, ...]:
    """Sculpt portfolio debt service from pooled CFADS using closed-form sculpting.

    Uses target_dscr from shared_financing to size debt and compute the schedule.
    """
    target_dscr = financing.target_dscr
    n = len(cfads_schedule)
    result = closed_form_sculpt(
        cfads_schedule=cfads_schedule,
        rate_schedule=[rate_per_period] * n,
        tenor_periods=n,
        target_dscr=target_dscr,
    )
    return tuple(result.payment_schedule)


def run_portfolio_waterfall(
    portfolio_inputs,  # PortfolioInputs object
    project_results: tuple[tuple[str, WaterfallResult], ...],
    portfolio_debt_service_schedule: Optional[tuple[float, ...]] = None,
    rate_per_period: float = 0.02825,
) -> PortfolioResult:
    """Run pooled-financing portfolio waterfall.

    Args:
        portfolio_inputs: PortfolioInputs (provides cash_pooling flag and shared_financing)
        project_results: (name, WaterfallResult) tuples
        portfolio_debt_service_schedule: optional explicit debt service
        rate_per_period: Semi-annual interest rate (default 0.02825)

    Returns:
        PortfolioResult with pooled periods, per-project results, DSCR
    """
    pooled = aggregate_project_results(project_results)

    n = len(pooled)
    cfads_list = [p["pooled_cfads_keur"] for p in pooled]

    # Sculpt portfolio debt service from pooled CFADS if not explicitly provided
    if portfolio_debt_service_schedule is None:
        if portfolio_inputs is not None:
            portfolio_debt_service_schedule = build_portfolio_debt_service_schedule(
                cfads_list,
                portfolio_inputs.shared_financing,
                rate_per_period,
            )
        else:
            # Fallback for backward compatibility (only when no portfolio_inputs available)
            portfolio_debt_service_schedule = [1000.0] * n

    ds_schedule = list(portfolio_debt_service_schedule)

    total_rev = sum(p["pooled_revenue_keur"] for p in pooled)
    total_ebitda = sum(p["pooled_ebitda_keur"] for p in pooled)
    total_tax = sum(p["pooled_tax_keur"] for p in pooled)
    total_ds = sum(ds_schedule[:n])

    result_periods = []
    dscrs = []
    portfolio_debt = 0.0
    for i, p in enumerate(pooled):
        ds = ds_schedule[i] if i < len(ds_schedule) else 0.0
        cfads = p["pooled_cfads_keur"]
        dscr = cfads / ds if ds > 0 else 999.0
        dscrs.append(dscr)
        # Interest and principal from aggregate (pooled across projects)
        interest = p.get("portfolio_senior_interest_keur", 0.0)
        principal = p.get("portfolio_senior_principal_keur", 0.0)
        result_periods.append(PortfolioPeriod(
            period=i + 1,
            date=p["date"],
            pooled_revenue_keur=p["pooled_revenue_keur"],
            pooled_ebitda_keur=p["pooled_ebitda_keur"],
            pooled_tax_keur=p["pooled_tax_keur"],
            pooled_cfads_keur=cfads,
            portfolio_senior_interest_keur=interest,
            portfolio_senior_principal_keur=principal,
            portfolio_senior_ds_keur=ds,
            dscr=dscr,
        ))

    avg_d = sum(dscrs) / len(dscrs) if dscrs else 0.0
    min_d = min(dscrs) if dscrs else 0.0

    # Compute portfolio debt from sculpted schedule (or 0 if not available)
    if portfolio_inputs is not None and portfolio_debt_service_schedule:
        sculpted = closed_form_sculpt(
            cfads_list, [rate_per_period] * n, n,
            portfolio_inputs.shared_financing.target_dscr,
        )
        portfolio_debt = sculpted.debt_keur
    else:
        portfolio_debt = 0.0

    return PortfolioResult(
        periods=tuple(result_periods),
        project_results=project_results,
        total_revenue_keur=total_rev,
        total_ebitda_keur=total_ebitda,
        total_tax_keur=total_tax,
        total_senior_ds_keur=total_ds,
        avg_dscr=avg_d,
        min_dscr=min_d,
        portfolio_debt_keur=portfolio_debt,
        pooled_cfads_schedule=tuple(cfads_list),
        portfolio_debt_service_schedule=tuple(ds_schedule),
    )


__all__ = [
    "PortfolioPeriod",
    "PortfolioResult",
    "aggregate_project_results",
    "portfolio_cfads_schedule",
    "run_portfolio_waterfall",
]