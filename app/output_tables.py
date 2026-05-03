"""Output table adapters — stable bridge between engine results and UI."""
from __future__ import annotations
import pandas as pd
from typing import Any


def _period_label(period: Any) -> str:
    """Return a period label string from a period object."""
    if hasattr(period, 'end_date'):
        return str(period.end_date)[:10]  # YYYY-MM-DD
    if hasattr(period, 'date'):
        return str(period.date)[:10]
    if hasattr(period, 'period'):
        return str(period.period)
    return str(period) if period is not None else "P?"


def _safe_get(obj: Any, name: str, default: float = 0.0) -> float:
    """Safely get a numeric attribute or dict key."""
    if obj is None:
        return default
    if hasattr(obj, name):
        val = getattr(obj, name)
        return float(val) if val is not None else default
    if isinstance(obj, dict):
        return float(obj.get(name, default))
    return default


def _safe_get_or_none(obj: Any, name: str) -> float | None:
    if obj is None:
        return None
    if hasattr(obj, name):
        val = getattr(obj, name)
        return float(val) if val is not None else None
    if isinstance(obj, dict):
        v = obj.get(name)
        return float(v) if v is not None else None
    return None


def build_dashboard_kpis(result) -> dict[str, float | str | None]:
    if result is None:
        return {}
    return {
        "total_revenue_keur": _safe_get_or_none(result, 'total_revenue_keur'),
        "total_ebitda_keur": _safe_get_or_none(result, 'total_ebitda_keur'),
        "total_tax_keur": _safe_get_or_none(result, 'total_tax_keur'),
        "project_irr": _safe_get_or_none(result, 'project_irr'),
        "equity_irr": _safe_get_or_none(result, 'equity_irr'),
        "sponsor_irr": _safe_get_or_none(result, 'sponsor_irr'),
        "min_dscr": _safe_get_or_none(result, 'min_dscr'),
        "avg_dscr": _safe_get_or_none(result, 'avg_dscr'),
        "total_senior_ds_keur": _safe_get_or_none(result, 'total_senior_ds_keur'),
        "total_distribution_keur": _safe_get_or_none(result, 'total_distribution_keur'),
    }


def build_waterfall_table(result) -> pd.DataFrame:
    if result is None or not hasattr(result, 'periods') or not result.periods:
        return pd.DataFrame(columns=["P1"])

    periods = result.periods
    labels = [_period_label(p) for p in periods]

    def row_values(getter) -> list[float]:
        return [getter(p) for p in periods]

    rows = {
        "Revenue": row_values(lambda p: _safe_get(p, 'revenue_keur')),
        "OpEx": row_values(lambda p: _safe_get(p, 'opex_keur')),
        "EBITDA": row_values(lambda p: _safe_get(p, 'ebitda_keur')),
        "Depreciation": row_values(lambda p: _safe_get(p, 'depreciation_keur')),
        "Taxable Profit": row_values(lambda p: _safe_get(p, 'taxable_profit_keur')),
        "Cash Tax": row_values(lambda p: _safe_get(p, 'cash_tax_keur')),
        "CFADS": row_values(lambda p: _safe_get(p, 'cfads_keur')),
        "Senior Debt Service": row_values(lambda p: _safe_get(p, 'senior_debt_service_keur')),
        "SHL Service": row_values(lambda p: _safe_get(p, 'shl_service_keur')),
        "DSRA Contribution": row_values(lambda p: _safe_get(p, 'dsra_contribution_keur')),
        "Distributions": row_values(lambda p: _safe_get(p, 'distributions_keur')),
        "Cash Balance": row_values(lambda p: _safe_get(p, 'cash_balance_keur')),
        "Senior Debt Balance": row_values(lambda p: _safe_get(p, 'senior_debt_balance_keur')),
        "SHL Balance": row_values(lambda p: _safe_get(p, 'shl_balance_keur')),
    }

    df = pd.DataFrame(rows, index=labels).T
    df.index.name = "Line Item"
    return df


def build_revenue_table(result) -> pd.DataFrame:
    if result is None or not hasattr(result, 'periods') or not result.periods:
        return pd.DataFrame(columns=["P1"])

    periods = result.periods
    labels = [_period_label(p) for p in periods]

    rows = {
        "Generation MWh": [_safe_get(p, 'generation_mwh') for p in periods],
        "Revenue kEUR": [_safe_get(p, 'revenue_keur') for p in periods],
        "Total Revenue kEUR": [_safe_get(p, 'total_revenue_keur') for p in periods],
    }

    # BESS and hybrid are optional
    bess_rev = [_safe_get(p, 'bess_revenue_keur') for p in periods]
    if any(v != 0.0 for v in bess_rev):
        rows["BESS Revenue kEUR"] = bess_rev

    hybrid_rev = [_safe_get(p, 'hybrid_revenue_keur') for p in periods]
    if any(v != 0.0 for v in hybrid_rev):
        rows["Hybrid Revenue kEUR"] = hybrid_rev

    df = pd.DataFrame(rows, index=labels).T
    df.index.name = "Line Item"
    return df


def build_debt_table(result) -> pd.DataFrame:
    if result is None or not hasattr(result, 'periods') or not result.periods:
        return pd.DataFrame(columns=["P1"])

    periods = result.periods
    labels = [_period_label(p) for p in periods]

    rows = {
        "Senior Interest": [_safe_get(p, 'senior_interest_keur') for p in periods],
        "Senior Principal": [_safe_get(p, 'senior_principal_keur') for p in periods],
        "Senior Debt Service": [_safe_get(p, 'senior_debt_service_keur') for p in periods],
        "Senior Debt Balance": [_safe_get(p, 'senior_debt_balance_keur') for p in periods],
        "DSCR": [_safe_get(p, 'dscr') for p in periods],
        "LLCR": [_safe_get(p, 'llcr') for p in periods],
        "PLCR": [_safe_get(p, 'plcr') for p in periods],
    }

    df = pd.DataFrame(rows, index=labels).T
    df.index.name = "Line Item"
    return df


def build_tax_depreciation_table(result) -> pd.DataFrame:
    if result is None or not hasattr(result, 'periods') or not result.periods:
        return pd.DataFrame(columns=["P1"])

    periods = result.periods
    labels = [_period_label(p) for p in periods]

    rows = {
        "EBITDA": [_safe_get(p, 'ebitda_keur') for p in periods],
        "Depreciation": [_safe_get(p, 'depreciation_keur') for p in periods],
        "Senior Interest": [_safe_get(p, 'senior_interest_keur') for p in periods],
        "SHL Interest": [_safe_get(p, 'shl_interest_keur') for p in periods],
        "Taxable Profit": [_safe_get(p, 'taxable_profit_keur') for p in periods],
        "Cash Tax": [_safe_get(p, 'cash_tax_keur') for p in periods],
    }

    df = pd.DataFrame(rows, index=labels).T
    df.index.name = "Line Item"
    return df


def build_returns_table(result) -> pd.DataFrame:
    if result is None:
        return pd.DataFrame(columns=["Value"])

    labels = ["Project IRR", "Equity IRR", "Sponsor IRR", "Project NPV", "Equity NPV"]
    values = [
        _safe_get_or_none(result, 'project_irr'),
        _safe_get_or_none(result, 'equity_irr'),
        _safe_get_or_none(result, 'sponsor_irr'),
        _safe_get_or_none(result, 'project_npv'),
        _safe_get_or_none(result, 'equity_npv'),
    ]

    df = pd.DataFrame({"Value": values}, index=labels)
    df.index.name = "Metric"
    return df


def build_portfolio_table(portfolio_result) -> pd.DataFrame:
    if portfolio_result is None:
        return pd.DataFrame(columns=["Value"])

    labels = ["Pooled Revenue", "Pooled EBITDA", "Pooled Tax", "Pooled CFADS",
              "Portfolio Senior Debt Service", "Portfolio DSCR"]
    values = [
        _safe_get_or_none(portfolio_result, 'total_revenue_keur'),
        _safe_get_or_none(portfolio_result, 'total_ebitda_keur'),
        _safe_get_or_none(portfolio_result, 'total_tax_keur'),
        _safe_get_or_none(portfolio_result, 'total_cfads_keur'),
        _safe_get_or_none(portfolio_result, 'portfolio_senior_debt_service_keur'),
        _safe_get_or_none(portfolio_result, 'portfolio_dscr'),
    ]

    df = pd.DataFrame({"Value": values}, index=labels)
    df.index.name = "Metric"
    return df