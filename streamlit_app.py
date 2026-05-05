"""FincoGPT — Streamlit UI entrypoint."""
from __future__ import annotations
import pandas as pd
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

    st.info("📋 Scenarios apply to Solar/Wind only — BESS & Portfolio show Base case")
    st.divider()
    run_button = st.button("🚀 Run Model", use_container_width=True)

    # Store current op_mode for use in run-condition block
    _curr_op_mode = st.session_state.get("_opex_mode", "Simple")


if run_button or st.session_state.demo_result is not None:
    # Early OPEX mode from session state — defined before invalidation logic
    op_mode = st.session_state.get("_opex_mode", "Simple")
    # Stable OPEX state signature: mode + (advanced sig only if Advanced and Solar/Wind)
    adv_sig = (st.session_state.get("last_advanced_opex_signature")
               if op_mode == "Advanced" and project_type in ("Solar", "Wind") else None)
    op_sig = (op_mode, adv_sig)
    needs_rerun = (
        run_button
        or st.session_state.last_project_type != project_type
        or st.session_state.get("last_scenario") != scenario
        or st.session_state.get("_last_opex_sig") != op_sig
    )
    if needs_rerun:
        st.session_state["_last_opex_sig"] = op_sig
        with st.spinner("Running model..."):
            override = st.session_state.get("editable_inputs") if st.session_state.get("use_editable_inputs") else None
            advanced_opex = (st.session_state.get("advanced_opex_line_items")
                             if op_mode == "Advanced" and project_type in ("Solar", "Wind") else None)
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
            advanced_opex_line_items=(
                st.session_state.get("advanced_opex_line_items")
                if project_type in ("Solar", "Wind") and op_mode == "Advanced" else None
            ),
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
        # Editable project assumptions toggle moved into Inputs tab
        if project_type in ("Solar", "Wind"):
            use_ed, _ = st.session.get("use_editable_inputs", False), None
            use_ed = st.checkbox(
                "Edit project assumptions",
                value=False,
                help="Edit core Solar/Wind assumptions. OPEX assumptions are managed separately in the OPEX tab.",
                key="_inputs_edit_toggle",
            )
            st.session_state["use_editable_inputs"] = use_ed
        if use_ed and project_type in ("Solar", "Wind"):
            from app.input_forms import render_project_input_form
            edited_inputs, was_modified = render_project_input_form(inputs_to_show, project_type)
            if was_modified:
                st.session_state["editable_inputs"] = edited_inputs
                st.session_state["demo_result"] = None
                st.rerun()
        else:
            if project_type not in ("Solar", "Wind") and use_ed:
                st.info("Editable assumptions are available for Solar/Wind in this MVP.")
            render_inputs(inputs_to_show)
    with tabs[2]:
        render_capex(inputs_to_show)
    with tabs[3]:
        # OPEX tab — simple vs advanced mode selector + line-item editor + schedule preview
        from app.opex_engine import build_opex_line_items_from_defaults, OpexLineItem, OpexSource, generate_opex_schedule

        st.subheader("💸 OPEX")
        # Mode selector — detect actual changes to trigger rerun before run block runs
        prev_op_mode = st.session_state.get("_opex_mode", "Simple")
        if project_type in ("Solar", "Wind"):
            op_mode = st.radio(
                "OPEX Mode",
                options=["Simple", "Advanced"],
                index=0 if prev_op_mode != "Advanced" else 1,
                horizontal=True,
                help="Simple = legacy OpexItem path. Advanced = granular line-item engine.",
                key="_opex_mode_radio",
            )
            op_mode_display = "line items" if op_mode == "Advanced" else ""
            if op_mode_display:
                st.caption(f"Mode: Advanced (line items)")
        else:
            op_mode = "Simple"

        # Only invalidate on actual mode change — not on every render
        if op_mode != prev_op_mode:
            st.session_state["_opex_mode"] = op_mode
            st.session_state["demo_result"] = None  # force rerun before run block
            if op_mode == "Simple":
                st.session_state["advanced_opex_line_items"] = None
            # For Advanced, keep items — they will be (re)initialised on next render
            st.rerun()

        # Non-Solar/Wind always use Simple
        if project_type not in ("Solar", "Wind"):
            st.info("Advanced OPEX is available for Solar/Wind only. Using simple OPEX.")

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

            # Stale-state warning: show when OPEX was edited but model not rerun yet
            if st.session_state.get("demo_result") is None and items:
                st.warning("⚠️ OPEX inputs changed — click Run Model to update Dashboard, Debt, DSCR and Returns.")

            horizon = getattr(getattr(demo.project_inputs, "info", None), "horizon_years", 25) if demo.project_inputs else 25

            # Build dataframe for data_editor: Line Item | Budget | Inflation (%) | Y1 ... Yn
            # (WHT removed — not yet applied to data model)
            col_names = ["Line Item", "Budget", "Inflation (%)"] + [f"Y{y}" for y in range(1, horizon + 1)]
            matrix_data = []
            original_items = list(items)

            for item in items:
                # Compute inflated values for Y columns (formula-driven values)
                infl_vals = []
                for y_idx in range(horizon):
                    infl_vals.append(item.base_year_amount_keur * ((1 + item.inflation_rate) ** y_idx))
                # Overlay manual overrides where they exist
                override_vals = list(item.manual_overrides_keur) if item.manual_overrides_keur else []
                row = [
                    item.name,
                    item.base_year_amount_keur,
                    item.inflation_rate * 100,
                ]
                for y_idx in range(horizon):
                    if y_idx < len(override_vals) and override_vals[y_idx] is not None:
                        row.append(override_vals[y_idx])
                    else:
                        row.append(infl_vals[y_idx])
                matrix_data.append(row)

            matrix_df = pd.DataFrame(matrix_data, columns=col_names)

            # Column config — Line Item locked, Budget+Inflation editable, Y cols editable
            col_config = {
                "Line Item": st.column_config.TextColumn("Line Item", disabled=True),
                "Budget": st.column_config.NumberColumn("Budget (kEUR)", min_value=0.0, format="%.1f"),
                "Inflation (%)": st.column_config.NumberColumn("Inflation (%)", min_value=0.0, max_value=100.0, format="%.2f"),
            }
            for y in range(1, horizon + 1):
                col_config[f"Y{y}"] = st.column_config.NumberColumn(f"Y{y}", min_value=0.0, format="%.1f")

            edited_df = st.data_editor(
                matrix_df,
                column_config=col_config,
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                key="_opex_matrix_editor",
            )

            # Diff detection: compare edited rows against originals
            new_items_list = []

            for row_idx, (_, row) in enumerate(edited_df.iterrows()):
                orig = original_items[row_idx]
                new_name = row["Line Item"]
                new_base = row["Budget"]
                new_infl = row["Inflation (%)"] / 100.0

                # Detect Y column changes → manual overrides
                # Compare against NEW base/inflation (not original) so Budget edits don't become overrides
                new_overrides = []
                for y_idx in range(horizon):
                    col_label = f"Y{y_idx + 1}"
                    edited_val = row[col_label]
                    infl_val = new_base * ((1 + new_infl) ** y_idx)
                    if abs(edited_val - infl_val) > 0.01:
                        new_overrides.append(edited_val)
                    else:
                        new_overrides.append(None)
                new_overrides_tuple = tuple(new_overrides)

                new_item = OpexLineItem(
                    name=new_name,
                    category=orig.category,
                    base_year_amount_keur=new_base,
                    inflation_rate=new_infl,
                    calculation_mode=orig.calculation_mode,
                    annual_values_keur=orig.annual_values_keur,
                    manual_overrides_keur=new_overrides_tuple,
                    is_hardcoded=orig.is_hardcoded,
                    override_note=orig.override_note,
                    source=orig.source,
                )
                new_items_list.append(new_item)

            new_items = tuple(new_items_list)
            st.session_state["advanced_opex_line_items"] = new_items

            # Signature update + invalidation
            new_sig = str(tuple(sorted((
                (i.name, i.category, i.base_year_amount_keur, i.inflation_rate,
                 i.source.value, i.is_hardcoded, i.override_note, i.manual_overrides_keur,
                 i.calculation_mode.value)
            ) for i in new_items)))
            if st.session_state.get("last_advanced_opex_signature") != new_sig:
                st.session_state["last_advanced_opex_signature"] = new_sig
                st.session_state["demo_result"] = None

            st.caption(f"{len(new_items)} line items | Mode: {op_mode}")

            # Total OPEX row — shown separately below the matrix, read-only
            schedule = generate_opex_schedule(new_items, horizon)
            total_col_names = ["Line Item"] + [f"Y{y}" for y in range(1, horizon + 1)]
            total_data = [["Total OPEX"] + [f"{v:.0f}" if v > 0 else "—" for v in schedule.total_by_year]]
            total_df = pd.DataFrame(total_data, columns=total_col_names)
            st.dataframe(total_df, hide_index=True, use_container_width=True)
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
    with tabs[5]:
        render_debt(demo.result, period_view)
    with tabs[6]:
        render_tax_depreciation(demo.result, period_view)
    with tabs[7]:
        render_waterfall(demo.result, period_view)
    with tabs[8]:
        render_returns(demo.result)
    with tabs[9]:
        render_portfolio(demo.portfolio_result)

else:
    st.info("👈 Configure a project in the sidebar and click **Run Model** to begin.")
