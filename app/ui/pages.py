"""Page builders for FincoGPT tabs."""
import streamlit as st
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
from app.ui.components import kpi_card, render_dataframe_with_download, format_metric_value


def _fmt(val, kind=None):
    """Format a value for display, handling None gracefully."""
    if val is None:
        return "n/a"
    return format_metric_value(val, kind)


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
    if integration_note:
        if integration_status == "partial":
            st.warning(integration_note)
        elif integration_status == "experimental":
            st.info(integration_note)

    if is_portfolio and portfolio_result is not None:
        kpis = {
            "Total Revenue": _fmt(portfolio_result.total_revenue_keur, "currency"),
            "EBITDA": _fmt(portfolio_result.total_ebitda_keur, "currency"),
            "Min DSCR": _fmt(portfolio_result.min_dscr, "ratio"),
            "Avg DSCR": _fmt(portfolio_result.avg_dscr, "ratio"),
            "Portfolio Debt": _fmt(portfolio_result.portfolio_debt_keur, "currency"),
            "Portfolio Project IRR": _fmt(portfolio_result.portfolio_project_irr, "percent") if portfolio_result.portfolio_project_irr not in (None, 0.0) else "n/a",
            "Sponsor IRR": "⏳ Placeholder" if portfolio_result.portfolio_sponsor_irr in (None, 0.0) else _fmt(portfolio_result.portfolio_sponsor_irr, "percent"),
        }
    elif result is not None:
        kpis = {
            "Total Revenue": _fmt(result.total_revenue_keur, "currency"),
            "EBITDA": _fmt(result.total_ebitda_keur, "currency"),
            "Project IRR": _fmt(result.project_irr, "percent"),
            "Equity IRR": _fmt(result.equity_irr, "percent"),
            "Sponsor IRR": _fmt(result.sponsor_irr, "percent"),
            "Min DSCR": _fmt(result.min_dscr, "ratio"),
            "Avg DSCR": _fmt(result.avg_dscr, "ratio"),
            "Senior Debt Service": _fmt(result.total_senior_ds_keur, "currency"),
            "Distributions": _fmt(result.total_distribution_keur, "currency"),
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
    st.dataframe(df, use_container_width=True)


def render_portfolio(portfolio_result):
    """Render the Portfolio tab."""
    if portfolio_result is None:
        st.info("Portfolio view is available for portfolio scenarios.")
        return
    df = build_portfolio_table(portfolio_result)
    st.dataframe(df, use_container_width=True)


def render_inputs(project_inputs):
    """Render read-only Inputs summary as a clean table."""
    if project_inputs is None:
        st.info("No inputs available.")
        return
    if hasattr(project_inputs, 'info'):
        info = project_inputs.info
        data = {
            "Name": getattr(info, 'name', 'n/a'),
            "Code": getattr(info, 'code', 'n/a'),
            "Country": getattr(info, 'country_iso', 'n/a'),
            "Capacity (MW)": getattr(info, 'capacity_mw', 'n/a'),
            "Horizon Years": getattr(info, 'horizon_years', 'n/a'),
            "Financial Close": getattr(info, 'financial_close', 'n/a'),
            "COD Date": getattr(info, 'cod_date', 'n/a'),
        }
        st.json(data, expanded=False)
    else:
        st.json(str(project_inputs), expanded=False)


def render_capex(project_inputs):
    """Render read-only CapEx summary."""
    if project_inputs is None:
        st.info("No inputs available.")
        return
    if hasattr(project_inputs, 'capex'):
        capex = project_inputs.capex
        data = {
            "sculpt_capex_keur": getattr(capex, 'sculpt_capex_keur', 'n/a'),
            "total_capex_keur": getattr(capex, 'total_capex_keur', 'n/a'),
            "construction_periods": getattr(capex, 'construction_periods', 'n/a'),
        }
        st.json(data, expanded=False)
    else:
        st.info("CapEx data not available.")