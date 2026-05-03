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
)
from app.ui.components import kpi_card, warning_banner

def render_dashboard(result, portfolio_result=None, is_portfolio=False):
    """Render the Dashboard tab with KPI cards."""
    if is_portfolio and portfolio_result is not None:
        kpis = {
            "Total Revenue": _safe_val(portfolio_result, 'total_revenue_keur'),
            "EBITDA": _safe_val(portfolio_result, 'total_ebitda_keur'),
            "Portfolio DSCR": _safe_val(portfolio_result, 'avg_dscr'),
            "Portfolio Senior Debt": _safe_val(portfolio_result, 'portfolio_debt_keur'),
        }
    elif result is not None:
        kpis = {
            "Total Revenue": _safe_val(result, 'total_revenue_keur'),
            "EBITDA": _safe_val(result, 'total_ebitda_keur'),
            "Project IRR": _pct(_safe_val(result, 'project_irr')),
            "Equity IRR": _pct(_safe_val(result, 'equity_irr')),
            "Sponsor IRR": _pct(_safe_val(result, 'sponsor_irr')),
            "Min DSCR": _safe_val(result, 'min_dscr'),
            "Avg DSCR": _safe_val(result, 'avg_dscr'),
            "Senior Debt Service": _safe_val(result, 'total_senior_ds_keur'),
            "Distributions": _safe_val(result, 'total_distribution_keur'),
        }
    else:
        st.info("No results yet. Run a project first.")
        return

    cols = st.columns(min(len(kpis), 4))
    for i, (label, value) in enumerate(kpis.items()):
        with cols[i % 4]:
            kpi_card(label, value)

def render_waterfall(result):
    """Render the Waterfall tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_waterfall_table(result)
    st.dataframe(df, use_container_width=True)

def render_revenue(result):
    """Render the Revenue tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_revenue_table(result)
    st.dataframe(df, use_container_width=True)

def render_debt(result):
    """Render the Debt tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_debt_table(result)
    st.dataframe(df, use_container_width=True)

def render_tax_depreciation(result):
    """Render the Tax & Depreciation tab."""
    if result is None:
        st.info("No results yet.")
        return
    df = build_tax_depreciation_table(result)
    st.dataframe(df, use_container_width=True)

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
    """Render read-only Inputs summary."""
    if project_inputs is None:
        st.info("No inputs available.")
        return
    st.json(_project_inputs_dict(project_inputs), expanded=False)

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

# Helpers
def _safe_val(obj, name, default=None):
    if obj is None:
        return default
    val = getattr(obj, name, None)
    return val if val is not None else default

def _pct(val):
    if val is None:
        return None
    return f"{val*100:.2f}%" if isinstance(val, (int, float)) else val

def _project_inputs_dict(proj):
    if hasattr(proj, '__dict__'):
        return {k: v for k, v in proj.__dict__.items() if not k.startswith('_')}
    return str(proj)