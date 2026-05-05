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

    st.info("📋 Scenarios apply to Solar/Wind only — BESS & Portfolio show Base case")
    st.divider()
    run_button = st.button("🚀 Run Model", use_container_width=True)


if run_button or st.session_state.demo_result is not None:
    # Invalidate if project type, scenario, or advanced OPEX state changed
    adv_sig = st.session_state.get("last_advanced_opex_signature") if project_type in ("Solar", "Wind") else None
    needs_rerun = (
        run_button
        or st.session_state.last_project_type != project_type
        or st.session_state.get("last_scenario") != scenario
        or st.session_state.get("_opex_mode") != op_mode
        or (project_type in ("Solar", "Wind") and st.session_state.get("_last_adv_sig") != adv_sig)
    )
    if needs_rerun:
        st.session_state["_last_adv_sig"] = adv_sig
        with st.spinner("Running model..."):
            override = st.session_state.get("editable_inputs") if st.session_state.get("use_editable_inputs") else None
            advanced_opex = st.session_state.get("advanced_opex_line_items") if project_type in ("Solar", "Wind") else None
            st.session_state.demo_result = run_demo_project(project_type, scenario, project_inputs_override=override, advanced_opex_line_items=advanced_opex)
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
    # Scenario guardrail for partial/experimental project types
    NON_SCENARIO_TYPES = {"BESS", "Solar+BESS", "Wind+BESS", "Portfolio"}
    if scenario != "Base" and project_type in NON_SCENARIO_TYPES:
        st.warning(f"⚠️ Scenario '{scenario}' is not supported for {project_type}. Base case results shown.")
    else:
        if scenario != "Base":
            from app.scenarios import scenario_summary
            rows = scenario_summary(scenario)
            has_changes = any(r.get("change") != "0%" for r in rows)
            st.subheader(f"📋 Scenario: {scenario}")
            if has_changes:
                import pandas as pd
                df = pd.DataFrame(rows)
                st.table(df)
            else:
                st.caption("No changes from Base case")
            st.divider()

    if demo.messages:
        for msg in demo.messages:
            st.warning(msg)

    # Validation panel
    with st.expander("🔍 Validation", expanded=False):
        render_validation_panel(demo.validation_issues)

    # Model Warnings section
    if demo.result or demo.portfolio_result:
        demo_exp = demo
        from app.excel_export import build_excel_export
        # Build model warnings for Excel export
        model_warnings = []
        if demo_exp.result is not None:
            from domain.validation import warn_model_unrealistic
            for w in warn_model_unrealistic(demo_exp.result, demo_exp.project_inputs):
                model_warnings.append({"code": w.code, "message": w.message})

        if model_warnings:
            with st.expander("⚠️ Model Warnings", expanded=False):
                for w in model_warnings:
                    st.warning(f"**{w['code']}**: {w['message']}")

        excel_data = build_excel_export(
            result=demo_exp.result,
            portfolio_result=demo_exp.portfolio_result,
            project_inputs=demo_exp.project_inputs,
            validation_issues=demo_exp.validation_issues,
            integration_status=demo_exp.integration_status,
            integration_note=demo_exp.integration_note,
            scenario=scenario,
            period_view=period_view,
            warnings=model_warnings,
            advanced_opex_line_items=st.session_state.get("advanced_opex_line_items") if project_type in ("Solar", "Wind") else None,
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
        "💸 OPEX",
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
        # OPEX tab — simple vs advanced mode selector + line-item editor + schedule preview
        from app.opex_engine import build_opex_line_items_from_defaults, OpexLineItem, OpexSource, generate_opex_schedule

        st.subheader("💸 OPEX")
        # Mode selector
        if project_type in ("Solar", "Wind"):
            op_mode = st.radio(
                "OPEX Mode",
                options=["Simple", "Advanced (line items)"],
                index=0 if st.session_state.get("_opex_mode") != "Advanced" else 1,
                horizontal=True,
                help="Simple = legacy OpexItem path. Advanced = granular line-item engine.",
                key="_opex_mode_radio",
            )
            if op_mode == "Advanced" and project_type in ("Solar", "Wind"):
                st.session_state["_opex_mode"] = "Advanced"
            else:
                st.session_state["_opex_mode"] = "Simple"
        else:
            st.info("Advanced OPEX is available for Solar/Wind only. Using simple OPEX.")
            op_mode = "Simple"
            st.session_state["_opex_mode"] = "Simple"

        if op_mode == "Advanced" and project_type in ("Solar", "Wind"):
            # Initialise or refresh line items
            last_pt = st.session_state.get("_advanced_opex_project_type")
            if last_pt != project_type:
                st.session_state["advanced_opex_line_items"] = build_opex_line_items_from_defaults(project_type.lower())
                st.session_state["_advanced_opex_project_type"] = project_type
            elif not st.session_state.get("advanced_opex_line_items"):
                st.session_state["advanced_opex_line_items"] = build_opex_line_items_from_defaults(project_type.lower())
                st.session_state["_advanced_opex_project_type"] = project_type

            items = st.session_state.get("advanced_opex_line_items", ())

            # Warnings
            from app.opex_engine import OpexSource as OpexSourceCls
            has_manual = any(i.source == OpexSourceCls.MANUAL for i in items)
            has_hardcoded = any(i.is_hardcoded for i in items)
            has_overrides = any(i.has_manual_overrides() for i in items)
            if has_manual or has_hardcoded or has_overrides:
                st.warning("Advanced OPEX contains manual or hardcoded values. Review override notes.")

            st.markdown("**Line Items**")
            horizon = getattr(getattr(demo.project_inputs, "info", None), "horizon_years", 25) if demo.project_inputs else 25

            edited_items = []
            for idx, item in enumerate(items):
                cols = st.columns([3, 2, 1.5, 1.2, 1.2, 1.5])
                new_name = cols[0].text_input("Name", value=item.name, key=f"opex_name_{idx}", label_visibility="collapsed")
                new_category = cols[1].text_input("Category", value=item.category, key=f"opex_cat_{idx}", label_visibility="collapsed")
                new_base = cols[2].number_input("Base (kEUR)", value=item.base_year_amount_keur, key=f"opex_base_{idx}", format="%.1f", label_visibility="collapsed")
                new_infl = cols[3].number_input("Infl %", value=item.inflation_rate * 100, key=f"opex_infl_{idx}", format="%.2f", label_visibility="collapsed") / 100
                src_index = {"formula": 0, "manual": 1, "hardcoded": 2}.get(item.source.value, 0)
                new_source = cols[4].selectbox("Source", options=["formula", "manual", "hardcoded"], index=src_index, key=f"opex_src_{idx}", label_visibility="collapsed")
                new_hardcoded = cols[5].checkbox("HC", value=item.is_hardcoded, key=f"opex_hc_{idx}")
                new_note = st.text_input("Override note", value=item.override_note, key=f"opex_note_{idx}", label_visibility="collapsed")
                updated = OpexLineItem(
                    name=new_name, category=new_category,
                    base_year_amount_keur=new_base, inflation_rate=new_infl,
                    calculation_mode=item.calculation_mode,
                    annual_values_keur=item.annual_values_keur,
                    manual_overrides_keur=item.manual_overrides_keur,
                    is_hardcoded=new_hardcoded,
                    override_note=new_note,
                    source=OpexSource(new_source),
                )
                edited_items.append(updated)
                with st.expander(f"ℹ️ {item.name} — {item.category} | {item.source.value} | HC: {item.is_hardcoded}", expanded=False):
                    st.caption(f"Base: {item.base_year_amount_keur:.1f} kEUR | Inflation: {item.inflation_rate*100:.1f}% | Source: {item.source.value} | Hardcoded: {item.is_hardcoded} | Note: {item.override_note or '—'}")

            st.session_state["advanced_opex_line_items"] = tuple(edited_items)

            # Signature update + invalidation
            new_sig = str(tuple(sorted((
                (i.name, i.category, i.base_year_amount_keur, i.inflation_rate, i.source.value, i.is_hardcoded, i.override_note, i.manual_overrides_keur, i.calculation_mode.value)
            ) for i in edited_items)))
            if st.session_state.get("last_advanced_opex_signature") != new_sig:
                st.session_state["last_advanced_opex_signature"] = new_sig
                st.session_state["demo_result"] = None

            st.caption(f"{len(edited_items)} line items | Mode: {op_mode}")

            # Schedule preview — Excel-style matrix
            schedule = generate_opex_schedule(st.session_state["advanced_opex_line_items"], horizon)
            st.markdown("**Schedule Preview (kEUR)**")
            preview_cols = ["Line Item"] + [f"Y{y+1}" for y in range(horizon)]
            rows_data = []
            for entry in schedule.entries:
                rows_data.append(entry)

            # Build matrix: rows = unique line items, cols = years
            item_names = list(dict.fromkeys(e.line_item_name for e in schedule.entries))
            matrix_rows = []
            for name in item_names:
                year_vals = [0.0] * horizon
                for e in schedule.entries:
                    if e.line_item_name == name:
                        year_vals[e.year_index] = e.value_keur
                matrix_rows.append([name] + [f"{v:.0f}" if v > 0 else "—" for v in year_vals])

            # Total row
            total_by_year = list(schedule.total_by_year)
            total_row = ["**Total OPEX**"] + [f"{v:.0f}" if v > 0 else "—" for v in total_by_year]
            matrix_rows.append(total_row)

            preview_df = pd.DataFrame(matrix_rows, columns=preview_cols)
            st.dataframe(preview_df, hide_index=True, use_container_width=True)
        else:
            # Simple OPEX: show a simple informational message
            if demo.project_inputs and hasattr(demo.project_inputs, "opex"):
                simple_items = demo.project_inputs.opex
                st.markdown("**Simple OPEX items**")
                simple_rows = [{"Name": i.name, "Y1 (kEUR)": i.y1_amount_keur, "Inflation": f"{i.annual_inflation*100:.1f}%"} for i in simple_items]
                st.dataframe(pd.DataFrame(simple_rows), hide_index=True)
            else:
                st.info("No OPEX data available. Run the model first.")

    with tabs[4]:
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