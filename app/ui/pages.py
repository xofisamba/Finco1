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
    if hasattr(project_inputs, 'info'):
        info = project_inputs.info
        technical = getattr(project_inputs, 'technical', None)
        rows = []
        rows.append(("Name", getattr(info, 'name', 'n/a')))
        rows.append(("Code", getattr(info, 'code', 'n/a')))
        rows.append(("Technology", getattr(technical, 'technology', 'n/a') if technical else 'n/a'))
        rows.append(("Country", getattr(info, 'country_iso', 'n/a')))
        rows.append(("Capacity (MW)", getattr(technical, 'capacity_mw', getattr(info, 'capacity_mw', 'n/a'))))
        rows.append(("Horizon Years", getattr(info, 'horizon_years', 'n/a')))
        rows.append(("Construction Months", getattr(info, 'construction_months', 'n/a')))
        rows.append(("PPA Term (years)", getattr(info, 'ppa_term_years', 'n/a')))
        rows.append(("Financial Close", getattr(info, 'financial_close', 'n/a')))
        df = pd.DataFrame(rows, columns=["Field", "Value"])
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.json(str(project_inputs), expanded=False)


def render_capex(project_inputs):
    """Render read-only CapEx summary."""
    if project_inputs is None:
        st.info("No inputs available.")
        return
    capex = getattr(project_inputs, 'capex', None)
    if capex is None:
        st.info("CapEx data not available.")
        return

    total_capex = getattr(capex, 'total_capex_keur', getattr(capex, 'total_capex', 'n/a'))
    sculpt_capex = getattr(capex, 'sculpt_capex_keur', 'n/a')
    construction_months = getattr(project_inputs.info, 'construction_months', 'n/a') if hasattr(project_inputs, 'info') else 'n/a'

    summary = [
        ("Total CapEx (kEUR)", total_capex),
        ("Sculpt CapEx (kEUR)", sculpt_capex),
        ("Construction Months", construction_months),
    ]
    df = pd.DataFrame(summary, columns=["Field", "Value"])
    st.dataframe(df, hide_index=True, use_container_width=True)

    # Asset items if available
    asset_items = getattr(capex, 'asset_items', None) or getattr(capex, 'capex_items', None)
    if asset_items:
        item_rows = []
        for item in asset_items:
            item_rows.append((
                getattr(item, 'name', getattr(item, 'description', 'n/a')),
                getattr(item, 'asset_class', 'n/a'),
                getattr(item, 'amount_keur', getattr(item, 'total_keur', 'n/a')),
                getattr(item, 'useful_life_years', 'n/a'),
            ))
        items_df = pd.DataFrame(item_rows, columns=["Name", "Asset Class", "Amount (kEUR)", "Life (years)"])
        with st.expander("CapEx Items"):
            st.dataframe(items_df, hide_index=True, use_container_width=True)