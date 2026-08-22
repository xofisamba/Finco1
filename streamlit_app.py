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
    # Stable CAPEX signature: total capex from line items (when available)
    capex_items = st.session_state.get("capex_line_items", ())
    capex_total = sum(i.amount_keur for i in capex_items) if capex_items else None
    op_sig = (op_mode, adv_sig, capex_total)
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
            advanced_capex = (st.session_state.get("capex_line_items")
                              if project_type in ("Solar", "Wind") else None)
            # PR-8 production authority: Solar/Wind run the clean G2C engine
            # exactly once. Advanced OPEX/CAPEX line items are legacy
            # side-channel inputs that do not exist on the clean route — a
            # clean-ready project with active advanced items fails closed
            # with an explicit message instead of silently running legacy.
            from app.services.production_waterfall_seam import (
                execute_production_demo,
                classify_or_fail,
            )
            _advanced_active = advanced_opex is not None or advanced_capex is not None
            _probe = override if override is not None else None
            if _advanced_active and project_type in ("Solar", "Wind", "Test 1", "Test 2"):
                from app import project_factories as _pf
                _probe = _probe or {
                    "Solar": _pf.create_default_solar_project,
                    "Wind": _pf.create_default_wind_project,
                    "Test 1": _pf.create_default_solar_project,
                    "Test 2": _pf.create_default_wind_project,
                }[project_type]()
                _decision = classify_or_fail(_probe)
                if _decision.promoted:
                    st.error(
                        "Advanced OPEX/CAPEX line items are a legacy-calibration "
                        "input channel and are not available on the clean "
                        "production authority that now serves this project. "
                        "Switch to Basic OPEX mode or edit the canonical "
                        "project inputs. (PR8_ADVANCED_LINE_ITEMS_UNAVAILABLE"
                        "_ON_CLEAN_RUNTIME)"
                    )
                    st.session_state.last_project_type = project_type
                    st.session_state["last_scenario"] = scenario
                    st.session_state.demo_result = None
                    st.stop()
            st.session_state.demo_result, _authority_meta = execute_production_demo(
                project_type, scenario, project_inputs_override=override
            )
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
            from app.scenario_manager import ScenarioManager
            sm = ScenarioManager(project_type)
            rows = sm.scenario_summary(scenario)
            has_changes = any(r.get("change") != "0%" for r in rows)
            st.subheader(f"📋 Scenario: {scenario}")
            if has_changes:
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
            project_type=project_type,
            period_view=period_view,
            warnings=model_warnings,
            advanced_opex_line_items=(
                st.session_state.get("advanced_opex_line_items")
                if project_type in ("Solar", "Wind") and op_mode == "Advanced" else None
            ),
            advanced_capex_line_items=(
                st.session_state.get("capex_line_items")
                if project_type in ("Solar", "Wind") else None
            ),
            include_reconciliation_sheets=st.checkbox(
                "📋 Include Reconciliation Sheets (Debt Schedule, CF Bridges, Calibration Notes)",
                value=False,
                help="Adds audit-ready disclosure sheets: Debt Schedule, Project CF Bridge, Equity CF Bridge, and Calibration Notes.",
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
        # Use matrix editor for Solar/Wind, existing read-only for others
        if project_type in ("Solar", "Wind") and demo.project_inputs:
            horizon = getattr(getattr(demo.project_inputs, "info", None), "horizon_years", 28)
            from app.ui.pages import render_capex_matrix
            render_capex_matrix(project_type, scale_mw=getattr(getattr(demo.project_inputs, "info", None), "capacity_mw", 50.0), tenor_periods=horizon)
        else:
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

            # Column config — Line Item locked, Budget+Inflation editable, Y cols compact integer
            col_config = {
                "Line Item": st.column_config.TextColumn("Line Item", disabled=True),
                "Budget": st.column_config.NumberColumn("Budget (kEUR)", min_value=0.0, format="%.1f"),
                "Inflation (%)": st.column_config.NumberColumn("Inflation (%)", min_value=0.0, max_value=100.0, format="%.2f"),
            }
            for y in range(1, horizon + 1):
                col_config[f"Y{y}"] = st.column_config.NumberColumn(f"Y{y}", min_value=0.0, format="%.0f")

            edited_df = st.data_editor(
                matrix_df,
                column_config=col_config,
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                key="_opex_matrix_editor",
            )

            # --- Shadow styled preview (highlight override cells in amber) ---
            # Build a display dataframe with amber bg for override cells
            # Only computed for display; does not affect data_editor values
            def _override_mask(row_items, row_overrides):
                """Return dict {col: True} for cells that are manual overrides."""
                mask = {}
                for y_idx in range(horizon):
                    if y_idx < len(row_overrides) and row_overrides[y_idx] is not None:
                        mask[f"Y{y_idx+1}"] = True
                return mask

            def _format_val(v):
                return "" if v == 0 else str(int(v)) if v == int(v) else f"{v:.1f}"

            display_cols = ["Line Item"] + [f"Y{y}" for y in range(1, horizon + 1)]
            preview_rows = []
            for item_idx, item in enumerate(items):
                row_vals = [_format_val(v) for v in edited_df.iloc[item_idx, 3:3+horizon].tolist()]
                row_overrides = []
                for y_idx in range(horizon):
                    col_label = f"Y{y_idx+1}"
                    edited_val = edited_df.iloc[item_idx][col_label]
                    infl_val = item.base_year_amount_keur * ((1 + item.inflation_rate) ** y_idx)
                    row_overrides.append(edited_val if abs(edited_val - infl_val) > 0.01 else None)
                preview_rows.append((item.name, row_vals, row_overrides))

            # Build display dataframe with formatted strings for preview
            preview_data = [[name] + vals for name, vals, _ in preview_rows]
            preview_df = pd.DataFrame(preview_data, columns=display_cols)

            def _highlight_overrides(row, overrides_per_row, horizon):
                """Return CSS style string for amber background if any Y cell is override."""
                item_idx = list(preview_df.index).index(row.name) if row.name in preview_df.index else 0
                _, _, overrides = preview_rows[item_idx]
                for y_idx in range(horizon):
                    if y_idx < len(overrides) and overrides[y_idx] is not None:
                        return ["background-color: #fff3cd"] * (horizon + 1)
                return [""] * (horizon + 1)

            styled = preview_df.style.apply(
                lambda row: _highlight_overrides(row, None, horizon),
                axis=1
            )
            styled = styled.set_table_styles([
                {"selector": "td", "props": [("font-size", "13px"), ("text-align", "right")]},
                {"selector": "th", "props": [("font-size", "13px"), ("text-align", "right")]},
            ])

            st.markdown("**Override preview** *(amber = manual override)*")
            st.dataframe(styled, hide_index=True, use_container_width=True)

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

            # Total OPEX row — shown separately below the matrix, read-only, compact integer display
            schedule = generate_opex_schedule(new_items, horizon)
            total_col_names = ["Line Item"] + [f"Y{y}" for y in range(1, horizon + 1)]
            total_vals = [f"{int(v)}" if v > 0 else "—" for v in schedule.total_by_year]
            total_data = [["Total OPEX"] + total_vals]
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
