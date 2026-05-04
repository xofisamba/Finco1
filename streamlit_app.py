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
for key in ["demo_result", "last_project_type", "last_scenario", "editable_inputs", "use_editable_inputs"]:
    if key not in st.session_state:
        st.session_state[key] = None

PROJECT_TYPES = ["Solar", "Wind", "BESS", "Solar+BESS", "Wind+BESS", "Portfolio"]
SCENARIOS = ["Base", "Downside", "Upside"]

with st.sidebar:
    st.header("⚙️ Configuration")
    project_type = st.selectbox("Project Type", PROJECT_TYPES)
    scenario = st.selectbox("Scenario", SCENARIOS)
    period_view = st.selectbox("Period View", ["Semiannual", "Annual"])
    st.divider()
    use_editable = st.checkbox("Use editable inputs", value=False, help="Override default Solar/Wind assumptions")
    st.session_state["use_editable_inputs"] = use_editable
    st.divider()
    run_button = st.button("🚀 Run Model", use_container_width=True)


if run_button or st.session_state.demo_result is not None:
    if run_button or st.session_state.last_project_type != project_type or st.session_state.get("last_scenario") != scenario:
        with st.spinner("Running model..."):
            override = st.session_state.get("editable_inputs") if st.session_state.get("use_editable_inputs") else None
            st.session_state.demo_result = run_demo_project(project_type, scenario, project_inputs_override=override)
            st.session_state.last_project_type = project_type
            st.session_state["last_scenario"] = scenario

    demo: DemoResult = st.session_state.demo_result

    # Status banner
    status_map = {
        "full": ("✅ Full integration", "standard solar/wind model"),
        "partial": ("⚠️ Partial integration", "BESS/hybrid: revenue-only shown, waterfall in progress"),
        "experimental": ("🔬 Experimental", "Portfolio IRR is placeholder; do not use for investment decisions"),
    }
    if project_type in ("BESS", "Solar+BESS", "Wind+BESS"):
        badge, detail = status_map["partial"]
    elif project_type == "Portfolio":
        badge, detail = status_map["experimental"]
    else:
        badge, detail = status_map["full"]
    st.caption(f"{badge} | integration_status: {badge.split()[0].lstrip('✅⚠️🔬').strip()}")
    if detail:
        st.caption(f"_{detail}_")

    # Scenario summary table (shown after model run, for non-Base scenarios)
    if scenario != "Base":
        from app.scenarios import scenario_summary
        rows = scenario_summary(scenario)
        has_changes = any(r.get("change") != "0%" for r in rows)
        st.subheader(f"📋 Scenario: {scenario}")
        if has_changes:
            import pandas as pd
            df = pd.DataFrame(rows)
            st.table(df)
            if project_type in ("BESS", "Solar+BESS", "Wind+BESS", "Portfolio"):
                st.info("⚠️ Scenario effects are partial for this project type — revenue model uses scenario, but other modules may not.")
        else:
            st.caption("No changes from Base case")
        st.divider()

    if demo.messages:
        for msg in demo.messages:
            st.warning(msg)

    # Validation panel
    with st.expander("🔍 Validation", expanded=False):
        render_validation_panel(demo.validation_issues)

    # Excel export (only if results exist)
    if demo.result or demo.portfolio_result:
        demo_exp = demo
        from app.excel_export import build_excel_export
        excel_data = build_excel_export(
            result=demo_exp.result,
            portfolio_result=demo_exp.portfolio_result,
            project_inputs=demo_exp.project_inputs,
            validation_issues=demo_exp.validation_issues,
            integration_status=demo_exp.integration_status,
            integration_note=demo_exp.integration_note,
            scenario=scenario,
            period_view=period_view,
        )
        st.download_button(
            "📊 Download Excel Export",
            data=excel_data,
            file_name=f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

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

    use_ed = st.session_state.get("use_editable_inputs", False)
    inputs_to_show = st.session_state.get("editable_inputs") or demo.project_inputs

    with tabs[0]:
        render_dashboard(demo.result, demo.portfolio_result, demo.is_portfolio,
                         demo.integration_status, demo.integration_note)
    with tabs[1]:
        if use_ed and project_type in ("Solar", "Wind"):
            from app.input_forms import render_project_input_form
            edited_inputs, was_modified = render_project_input_form(inputs_to_show, project_type)
            if was_modified:
                st.session_state["editable_inputs"] = edited_inputs
                st.session_state["demo_result"] = None  # clear result to force rerun
                st.rerun()
        else:
            if project_type not in ("Solar", "Wind") and use_ed:
                st.info("Editable inputs are available for Solar/Wind in this MVP.")
            render_inputs(inputs_to_show)
    with tabs[2]:
        render_capex(inputs_to_show)
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