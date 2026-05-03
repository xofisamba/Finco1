"""FincoGPT — Streamlit UI entrypoint."""
from __future__ import annotations
import streamlit as st
from app.ui_runner import run_demo_project, DemoResult
from app.ui.pages import (
    render_dashboard,
    render_waterfall,
    render_revenue,
    render_debt,
    render_tax_depreciation,
    render_returns,
    render_portfolio,
    render_inputs,
    render_capex,
    render_validation_panel,
)

st.set_page_config(page_title="FincoGPT", layout="wide")
st.title("🏗️ FincoGPT — Financial Model")

# Session state for results
for key in ["demo_result", "last_project_type", "last_scenario"]:
    if key not in st.session_state:
        st.session_state[key] = None

PROJECT_TYPES = ["Solar", "Wind", "BESS", "Solar+BESS", "Wind+BESS", "Portfolio"]
SCENARIOS = ["Base", "Downside", "Upside"]

with st.sidebar:
    st.header("⚙️ Configuration")
    project_type = st.selectbox("Project Type", PROJECT_TYPES)
    scenario = st.selectbox("Scenario", SCENARIOS)
    period_view = st.selectbox("Period View", ["Semiannual", "Annual"])
    run_button = st.button("🚀 Run Model", use_container_width=True)

if run_button or st.session_state.demo_result is not None:
    if run_button or st.session_state.last_project_type != project_type:
        with st.spinner("Running model..."):
            st.session_state.demo_result = run_demo_project(project_type, scenario)
            st.session_state.last_project_type = project_type
            st.session_state.last_scenario = scenario

    demo: DemoResult = st.session_state.demo_result

    if demo.messages:
        for msg in demo.messages:
            st.warning(msg)

    # Validation panel
    with st.expander("🔍 Validation", expanded=False):
        render_validation_panel(demo.validation_issues)

    tabs = st.tabs([
        "📊 Dashboard",
        "📥 Inputs",
        "💰 CapEx",
        "⚡ Revenue",
        "🏦 Debt",
        "📉 Tax & Depreciation",
        "📈 Waterfall",
        "📐 Returns",
        "🌐 Portfolio",
    ])

    with tabs[0]:
        render_dashboard(demo.result, demo.portfolio_result, demo.is_portfolio,
                         demo.integration_status, demo.integration_note)
    with tabs[1]:
        render_inputs(demo.project_inputs)
    with tabs[2]:
        render_capex(demo.project_inputs)
    with tabs[3]:
        render_revenue(demo.result, period_view)
    with tabs[4]:
        render_debt(demo.result, period_view)
    with tabs[5]:
        render_tax_depreciation(demo.result, period_view)
    with tabs[6]:
        render_waterfall(demo.result, period_view)
    with tabs[7]:
        render_returns(demo.result)
    with tabs[8]:
        render_portfolio(demo.portfolio_result)
else:
    st.info("👈 Configure a project in the sidebar and click **Run Model** to begin.")