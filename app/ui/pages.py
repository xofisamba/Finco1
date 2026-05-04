"""Page builders for FincoGPT tabs."""
import streamlit as st
import pandas as pd
from app.output_tables import (
    build_dashboard_kpis,
    build_waterfall_table,
    build_revenue_table,
    build_debt_table,
    build_tax_depreciation_table,
    build_returns_table,
    build_portfolio_table,
    aggregate_period_table_annual,
)
from app.ui.components import kpi_card, render_dataframe_with_download, format_metric_value, status_badge


def _fmt(val, kind=None):
    """Format a value for display, handling None gracefully."""
    if val is None:
        return "n/a"
    return format_metric_value(val, kind)


def _fmt_irr(val):
    """Format IRR as percentage: multiply by 100, show as '12.5%'."""
    if val is None:
        return "n/a"
    try:
        return f"{float(val) * 100:.2f}%"
    except (TypeError, ValueError):
        return str(val)


def _fmt_dscr(val):
    """Format DSCR with 2 decimals, suffix 'x': '1.35x'."""
    if val is None:
        return "n/a"
    try:
        return f"{float(val):.2f}x"
    except (TypeError, ValueError):
        return str(val)


def _fmt_keur(val):
    """Format kEUR values with thousands separator."""
    if val is None:
        return "n/a"
    try:
        v = float(val)
        if abs(v) >= 1_000_000:
            return f"{v / 1_000_000:.2f}M"
        elif abs(v) >= 1_000:
            return f"{v / 1_000:.1f}k"
        return f"{v:.0f}"
    except (TypeError, ValueError):
        return str(val)


def render_validation_panel(issues: list) -> None:
    """Show validation errors and warnings."""
    if not issues:
        st.info("✅ No validation issues found.")
        return
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    for e in errors:
        st.error(f"**{e.field}**: {e.message}")
    for w in warnings:
        st.warning(f"**{w.field}**: {w.message}")


def render_dashboard(result, portfolio_result=None, is_portfolio=False, integration_status="full", integration_note=None):
    """Render the Dashboard tab with KPI cards."""
    # Show status badge at top
    status_badge("Model status", integration_status)
    if integration_note:
        if integration_status == "partial":
            st.warning(integration_note)
        elif integration_status == "experimental":
            st.info(integration_note)

    if is_portfolio and portfolio_result is not None:
        kpis = {
            "Total Revenue": _fmt_keur(portfolio_result.total_revenue_keur),
            "EBITDA": _fmt_keur(portfolio_result.total_ebitda_keur),
            "Min DSCR": _fmt_dscr(portfolio_result.min_dscr),
            "Avg DSCR": _fmt_dscr(portfolio_result.avg_dscr),
            "Portfolio Debt": _fmt_keur(portfolio_result.portfolio_debt_keur),
            "Portfolio Project IRR (%)": _fmt_irr(portfolio_result.portfolio_project_irr) if portfolio_result.portfolio_project_irr not in (None, 0.0) else "n/a",
            "Sponsor IRR (%)": "⏳ Placeholder" if portfolio_result.portfolio_sponsor_irr in (None, 0.0) else _fmt_irr(portfolio_result.portfolio_sponsor_irr),
        }
    elif result is not None:
        kpis = {
            "Total Revenue": _fmt_keur(result.total_revenue_keur),
            "EBITDA": _fmt_keur(result.total_ebitda_keur),
            "Project IRR (%)": _fmt_irr(result.project_irr),
            "Equity IRR (%)": _fmt_irr(result.equity_irr),
            "Sponsor IRR (%)": _fmt_irr(result.sponsor_irr),
            "Min DSCR": _fmt_dscr(result.min_dscr),
            "Avg DSCR": _fmt_dscr(result.avg_dscr),
            "Senior Debt Service": _fmt_keur(result.total_senior_ds_keur),
            "Distributions": _fmt_keur(result.total_distribution_keur),
        }
    else:
        st.info("No results yet. Run a project first.")
        return

    cols = st.columns(min(len(kpis), 4))
    for i, (label, value) in enumerate(kpis.items()):
        with cols[i % 4]:
            st.metric(label=label, value=value)


def render_waterfall(result, period_view="Semiannual"):
    """Render the Waterfall tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_waterfall_table(result)
    if period_view == "Annual":
        df = aggregate_period_table_annual(df)
    render_dataframe_with_download(df, "Waterfall", "waterfall.csv")


def render_revenue(result, period_view="Semiannual"):
    """Render the Revenue tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_revenue_table(result)
    if period_view == "Annual":
        df = aggregate_period_table_annual(df)
    render_dataframe_with_download(df, "Revenue", "revenue.csv")


def render_debt(result, period_view="Semiannual"):
    """Render the Debt tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_debt_table(result)
    if period_view == "Annual":
        df = aggregate_period_table_annual(df)
    render_dataframe_with_download(df, "Debt", "debt.csv")


def render_tax_depreciation(result, period_view="Semiannual"):
    """Render the Tax & Depreciation tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_tax_depreciation_table(result)
    if period_view == "Annual":
        df = aggregate_period_table_annual(df)
    render_dataframe_with_download(df, "Tax & Depreciation", "tax_depreciation.csv")


def render_returns(result):
    """Render the Returns tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_returns_table(result)
    render_dataframe_with_download(df, "Returns", "returns.csv")


def render_portfolio(portfolio_result):
    """Render the Portfolio tab."""
    if portfolio_result is None:
        st.info("Portfolio view is available for portfolio scenarios.")
        return

    # Summary KPIs
    cols = st.columns(3)
    with cols[0]:
        st.metric("Pooled Revenue", f"{portfolio_result.total_revenue_keur/1000:.0f}k" if portfolio_result.total_revenue_keur else "n/a")
    with cols[1]:
        st.metric("Pooled EBITDA", f"{portfolio_result.total_ebitda_keur/1000:.0f}k" if portfolio_result.total_ebitda_keur else "n/a")
    with cols[2]:
        st.metric("Avg DSCR", f"{portfolio_result.avg_dscr:.3f}" if portfolio_result.avg_dscr else "n/a")

    # Sponsor IRR placeholder warning
    if portfolio_result.portfolio_sponsor_irr in (None, 0.0):
        st.warning("Portfolio sponsor IRR is a placeholder until sponsor cash-flow aggregation is implemented.")

    # Project IRR note
    if portfolio_result.portfolio_project_irr in (None, 0.0):
        st.info("Portfolio project IRR is not yet available or could not be calculated.")

    # Portfolio table with CSV
    df = build_portfolio_table(portfolio_result)
    render_dataframe_with_download(df, "Portfolio", "portfolio.csv")

    # Project results count
    if hasattr(portfolio_result, 'project_results') and portfolio_result.project_results:
        st.subheader(f"Projects ({len(portfolio_result.project_results)})")
        project_rows = []
        for code, wf_result in portfolio_result.project_results:
            project_rows.append({
                "Code": code,
                "Revenue (kEUR)": getattr(wf_result, 'total_revenue_keur', 'n/a'),
                "EBITDA (kEUR)": getattr(wf_result, 'total_ebitda_keur', 'n/a'),
                "Project IRR": f"{wf_result.project_irr*100:.2f}%" if getattr(wf_result, 'project_irr', None) else "n/a",
            })
        projects_df = pd.DataFrame(project_rows)
        st.dataframe(projects_df, hide_index=True, use_container_width=True)


def render_inputs(project_inputs):
    """Render read-only Inputs summary as a clean table."""
    if project_inputs is None:
        st.info("No inputs available.")
        return
    from app.input_helpers import build_inputs_summary_table
    df = build_inputs_summary_table(project_inputs)
    st.dataframe(df, hide_index=True, use_container_width=True)


def render_capex(project_inputs):
    """Render read-only CapEx summary."""
    if project_inputs is None:
        st.info("No CapEx data available.")
        return
    from app.input_helpers import build_capex_summary_table, build_capex_items_table
    df = build_capex_summary_table(project_inputs)
    st.dataframe(df, hide_index=True, use_container_width=True)
    items_df = build_capex_items_table(project_inputs)
    if items_df.shape[0] > 0:
        with st.expander("CapEx Items"):
            st.dataframe(items_df, hide_index=True, use_container_width=True)