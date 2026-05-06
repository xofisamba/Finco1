"""Thin wrapper around run_demo_project for API use."""
from app.ui_runner import run_demo_project
from app.output_tables import build_waterfall_table, build_revenue_table, build_debt_table, build_returns_table, aggregate_period_table_annual


def _sanitize_df(df):
    """Replace inf/nan floats in a DataFrame with None for JSON safety.

    Uses astype(object).replace() rather than map() because pandas map()
    silently drops inf values without actually replacing them when the
    dtype is float64.
    """
    return df.astype(object).replace({float('inf'): None, float('-inf'): None, float('nan'): None})


def run_project(project_type: str, scenario: str, period_view: str = "Semiannual"):
    demo = run_demo_project(project_type, scenario)
    result = demo.result

    # Build tables
    wf = build_waterfall_table(result)
    rev = build_revenue_table(result)
    debt = build_debt_table(result)
    returns = build_returns_table(result)

    if period_view == "Annual":
        wf = aggregate_period_table_annual(wf)
        rev = aggregate_period_table_annual(rev)
        debt = aggregate_period_table_annual(debt)

    # Sanitize inf/nan (e.g. DSCR col has inf when debt is fully repaid)
    wf = _sanitize_df(wf)
    rev = _sanitize_df(rev)
    debt = _sanitize_df(debt)
    returns = _sanitize_df(returns)

    return {
        "project_type": project_type,
        "scenario": scenario,
        "period_view": period_view,
        "integration_status": getattr(demo, 'integration_status', 'full'),
        "integration_note": getattr(demo, 'integration_note', None),
        "messages": getattr(demo, 'messages', []),
        "kpis": {
            "total_revenue_keur": result.total_revenue_keur,
            "total_ebitda_keur": result.total_ebitda_keur,
            "project_irr": result.project_irr,
            "equity_irr": result.equity_irr,
            "min_dscr": result.actual_min_dscr,
            "avg_dscr": result.actual_avg_dscr,
        },
        "tables": {
            "waterfall": wf.to_dict(orient="records"),
            "revenue": rev.to_dict(orient="records"),
            "debt": debt.to_dict(orient="records"),
            "returns": returns.to_dict(orient="records"),
        }
    }
