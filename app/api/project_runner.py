"""Thin wrapper around run_demo_project for API use."""
from app.ui_runner import run_demo_project
from app.output_tables import build_waterfall_table, build_revenue_table, build_debt_table, build_returns_table, aggregate_period_table_annual


def _period_label(period) -> str:
    """Build a human-readable period label from the backend period object."""
    year_index = getattr(period, "year_index", None)
    period_in_year = getattr(period, "period_in_year", None)
    period_number = getattr(period, "period", None)

    if year_index is not None and period_in_year is not None:
        return f"Y{int(year_index)}-H{int(period_in_year)}"
    if period_number is not None:
        return f"P{int(period_number)}"
    return "Selected period"


def _build_runtime_derivation_evidence(result):
    """Return read-only DSCR / CFADS / EBITDA evidence sourced from WaterfallResult."""
    periods = [
        period
        for period in getattr(result, "periods", [])
        if getattr(period, "is_operation", False) and float(getattr(period, "senior_ds_keur", 0.0) or 0.0) > 0.0
    ]
    if not periods:
        return {}

    period_count = len(periods)
    representative_period = min(periods, key=lambda period: getattr(period, "period", 0))
    total_cfads = sum(float(getattr(period, "cf_after_tax_keur", 0.0) or 0.0) for period in periods)
    total_senior_ds = sum(float(getattr(period, "senior_ds_keur", 0.0) or 0.0) for period in periods)

    return {
        "dscr": {
            "display_value": getattr(result, "actual_avg_dscr", None),
            "summary_method": "Average of operating-period DSCR values with positive senior debt service.",
            "period_formula": "DSCR_t = CFADS_t / Senior Debt Service_t",
            "period_count": period_count,
            "total_cfads_keur": total_cfads,
            "total_senior_debt_service_keur": total_senior_ds,
            "sample_period_label": _period_label(representative_period),
            "sample_cfads_keur": getattr(representative_period, "cf_after_tax_keur", None),
            "sample_senior_debt_service_keur": getattr(representative_period, "senior_ds_keur", None),
            "sample_dscr": getattr(representative_period, "dscr", None),
            "audit_source": "WaterfallResult.periods[].cf_after_tax_keur, senior_ds_keur, dscr",
        },
        "cfads": {
            "display_value_keur": total_cfads,
            "summary_method": "Total CFADS across operating periods with positive senior debt service.",
            "period_formula": "CFADS_t = WaterfallPeriod.cf_after_tax_keur",
            "period_count": period_count,
            "sample_period_label": _period_label(representative_period),
            "sample_ebitda_keur": getattr(representative_period, "ebitda_keur", None),
            "sample_tax_keur": getattr(representative_period, "tax_keur", None),
            "sample_cfads_keur": getattr(representative_period, "cf_after_tax_keur", None),
            "audit_source": "WaterfallResult.periods[].cf_after_tax_keur (supporting fields shown: ebitda_keur, tax_keur)",
        },
        "ebitda": {
            "display_value_keur": getattr(result, "total_ebitda_keur", None),
            "summary_method": "Total EBITDA from backend operating periods.",
            "period_formula": "EBITDA_t = Revenue_t - OPEX_t",
            "period_count": period_count,
            "sample_period_label": _period_label(representative_period),
            "sample_revenue_keur": getattr(representative_period, "revenue_keur", None),
            "sample_opex_keur": getattr(representative_period, "opex_keur", None),
            "sample_ebitda_keur": getattr(representative_period, "ebitda_keur", None),
            "audit_source": "WaterfallResult.total_ebitda_keur and WaterfallResult.periods[].revenue_keur, opex_keur, ebitda_keur",
        },
    }


def _sanitize_df(df):
    """Replace inf/nan floats in a DataFrame with None for JSON safety.

    Uses astype(object).replace() rather than map() because pandas map()
    silently drops inf values without actually replacing them when the
    dtype is float64.
    """
    return df.astype(object).replace({float('inf'): None, float('-inf'): None, float('nan'): None})


def run_project(project_type: str, scenario: str, period_view: str = "Semiannual",
               project_inputs_override=None, use_dualrun_validation: bool = False):
    demo = run_demo_project(project_type, scenario,
                            project_inputs_override=project_inputs_override,
                            use_dualrun_validation=use_dualrun_validation)
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
            "total_opex_keur": getattr(result, 'total_opex_keur', None),
            "total_distributions_keur": getattr(result, 'total_distribution_keur', None),
            "project_irr": result.project_irr,
            "equity_irr": result.equity_irr,
            "min_dscr": result.actual_min_dscr,
            "avg_dscr": result.actual_avg_dscr,
        },
        "dualrun_validation": getattr(result, '_dualrun_validation', None),
        "derivation_evidence": _build_runtime_derivation_evidence(result),
        "tables": {
            "waterfall": wf.to_dict(orient="records"),
            "revenue": rev.to_dict(orient="records"),
            "debt": debt.to_dict(orient="records"),
            "returns": returns.to_dict(orient="records"),
        }
    }
