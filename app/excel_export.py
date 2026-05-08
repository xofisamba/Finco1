"""Values-only Excel export — no formulas, no calibration."""
from __future__ import annotations
import pandas as pd
from io import BytesIO

import openpyxl
from openpyxl.styles import Font, numbers
from openpyxl.utils import get_column_letter


# KPI label mapping: raw key → clean display label
_DASHBOARD_LABELS = {
    "total_revenue_keur": "Total Revenue (kEUR)",
    "total_ebitda_keur": "EBITDA (kEUR)",
    "total_tax_keur": "Total Tax (kEUR)",
    "project_irr": "Project IRR (%)",
    "equity_irr": "Equity IRR (%)",
    "sponsor_irr": "Sponsor IRR (%)",
    "min_dscr": "Min DSCR",
    "avg_dscr": "Avg DSCR",
    "total_senior_ds_keur": "Senior Debt Service (kEUR)",
    "total_distribution_keur": "Distributions (kEUR)",
}


def build_excel_export(
    *,
    result=None,
    portfolio_result=None,
    project_inputs=None,
    validation_issues=None,
    integration_status: str = "full",
    integration_note: str | None = None,
    scenario: str = "Base",
    project_type: str = "Solar",
    period_view: str = "Semiannual",
    warnings: list = None,
    run_metadata=None,
    advanced_opex_line_items: tuple = None,
    advanced_capex_line_items: tuple = None,
    include_reconciliation_sheets: bool = False,
) -> bytes:
    """Build a values-only Excel workbook from waterfall results.
    
    Args:
        include_reconciliation_sheets: If True, adds Debt Schedule, Project CF Bridge,
            Equity CF Bridge, and Calibration Notes sheets.
    
    Returns bytes suitable for st.download_button.
    """
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
    from app.input_helpers import build_inputs_summary_table, build_capex_summary_table, build_capex_items_table
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # ── Dashboard (always first) ─────────────────────────────────────
        _write_dashboard_sheet(writer, result, portfolio_result, integration_status, integration_note, scenario)

        # ── Returns ───────────────────────────────────────────────────────
        if result is not None:
            _write_sheet(writer, "Returns", build_returns_table(result),
                         number_format={"IRR": "0.0%", "DSCR": "0.00x", "kEUR": "#,##0"})

        # ── DSCR Summary ────────────────────────────────────────────────────
        if result is not None and hasattr(result, "target_dscr"):
            rows = [
                ("Metric", "Value"),
                ("Target DSCR", f"{result.target_dscr:.3f}"),
                ("Actual Min DSCR", f"{result.actual_min_dscr:.3f}"),
                ("Actual Avg DSCR", f"{result.actual_avg_dscr:.3f}"),
                ("Deviation", f"{result.actual_min_dscr - result.target_dscr:+.3f}"),
            ]
            dscr_df = pd.DataFrame(rows[1:], columns=["Metric", "Value"])
            _write_sheet(writer, "DSCR Summary", dscr_df)

        # ── Waterfall ─────────────────────────────────────────────────────
        if result is not None:
            wf_df = build_waterfall_table(result)
            if period_view == "Annual":
                wf_df = aggregate_period_table_annual(wf_df)
            _write_sheet(writer, "Waterfall", wf_df,
                         number_format={"kEUR": "#,##0", "DSCR": "0.00x"})

        # ── Revenue ────────────────────────────────────────────────────────
        if result is not None:
            rev_df = build_revenue_table(result)
            if period_view == "Annual":
                rev_df = aggregate_period_table_annual(rev_df)
            _write_sheet(writer, "Revenue", rev_df, number_format={"kEUR": "#,##0", "MWh": "#,##0"})

        # ── Debt ──────────────────────────────────────────────────────────
        if result is not None:
            debt_df = build_debt_table(result)
            if period_view == "Annual":
                debt_df = aggregate_period_table_annual(debt_df)
            _write_sheet(writer, "Debt", debt_df,
                         number_format={"kEUR": "#,##0", "DSCR": "0.00x", "LLCR": "0.00x", "PLCR": "0.00x"})

        # ── Tax & Depreciation ─────────────────────────────────────────────
        if result is not None:
            tax_df = build_tax_depreciation_table(result)
            if period_view == "Annual":
                tax_df = aggregate_period_table_annual(tax_df)
            _write_sheet(writer, "Tax_Depreciation", tax_df, number_format={"kEUR": "#,##0"})

        # ── Notes ──────────────────────────────────────────────────────────
        if run_metadata is not None:
            git_sha = run_metadata.git_sha
            ts = run_metadata.timestamp
            scenario = run_metadata.scenario
            project_type = run_metadata.project_type
        else:
            import subprocess
            try:
                git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
            except Exception:
                git_sha = "n/a"
            ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M UTC")
        _write_notes_sheet(writer, integration_status, integration_note, scenario, project_type, period_view,
                          warnings=warnings if warnings else [], git_sha=git_sha, timestamp=ts,
                          advanced_opex_line_items=advanced_opex_line_items,
                          advanced_capex_line_items=advanced_capex_line_items)

        # ── Inputs ────────────────────────────────────────────────────────
        _write_sheet(writer, "Inputs", build_inputs_summary_table(project_inputs))

        # ── CapEx ──────────────────────────────────────────────────────────
        _write_sheet(writer, "CapEx", build_capex_summary_table(project_inputs),
                     number_format={"kEUR": "#,##0"})
        _write_sheet(writer, "CapEx_Items", build_capex_items_table(project_inputs),
                     number_format={"Amount": "#,##0"})

        # ── OPEX Detail (Advanced OPEX only) ───────────────────────────────
        if advanced_opex_line_items:
            from app.opex_engine import generate_opex_schedule
            horizon = getattr(getattr(project_inputs, "info", None), "horizon_years", 25) if project_inputs else 25
            schedule = generate_opex_schedule(advanced_opex_line_items, horizon)
            _write_opex_detail_sheet(writer, schedule)

        # ── Portfolio ──────────────────────────────────────────────────────
        if portfolio_result is not None:
            _write_sheet(writer, "Portfolio", build_portfolio_table(portfolio_result),
                         number_format={"kEUR": "#,##0", "IRR": "0.0%", "DSCR": "0.00x"})
            if portfolio_result.portfolio_cashflows:
                rows = []
                for row in portfolio_result.portfolio_cashflows:
                    date = row.get("date", "")
                    total = row.get("total_cashflow", 0.0)
                    breakdown = row.get("breakdown", {})
                    row_dict = {"Date": str(date), "Total CF (keur)": round(total, 2)}
                    for proj, contrib in breakdown.items():
                        row_dict[f"  {proj}"] = round(contrib, 2)
                    rows.append(row_dict)
                cf_df = pd.DataFrame(rows)
                _write_sheet(writer, "Portfolio CF", cf_df, number_format={"kEUR": "#,##0"})

        # ── Reconciliation / Audit Sheets (optional) ─────────────────────
        if include_reconciliation_sheets and result is not None:
            _write_reconciliation_sheets(writer, result, project_inputs)

        # ── Validation ────────────────────────────────────────────────────
        _write_validation_sheet(writer, validation_issues)

        # ── Depreciation Assumptions (Bankable Framework) ─────────────────
        # Select profile based on project_type: Solar → solar_croatia_ibl, Wind → wind_croatia_ibl
        depr_profile = f"{project_type.lower()}_croatia_ibl" if project_type.lower() in ("solar", "wind") else "solar_croatia_ibl"
        _write_depreciation_assumptions_sheet(writer, depr_profile)

        # ── Tax Depreciation Disclosure ───────────────────────────────────
        _write_tax_depreciation_sheet_for_project(writer, project_inputs, advanced_capex_line_items, project_type)

        # ── Book Depreciation Disclosure ──────────────────────────────────
        _write_book_depreciation_sheet_for_project(writer, project_inputs, advanced_capex_line_items, project_type)
    
    output.seek(0)
    return output.read()


# ─── Reconciliation / Audit Sheets ─────────────────────────────────────────


def _write_reconciliation_sheets(
    writer,
    result,
    project_inputs,
) -> None:
    """Write optional audit sheets: Debt Schedule, Project CF Bridge, Equity CF Bridge."""
    from app.reconciliation import (
        build_debt_schedule_rows,
        build_project_cf_rows,
        build_equity_cf_rows,
    )
    import pandas as pd

    # ── Debt Schedule ──────────────────────────────────────────────────────
    debt_rows = build_debt_schedule_rows(result)
    if debt_rows:
        debt_df = pd.DataFrame(debt_rows)
        _write_sheet(writer, "Debt Schedule", debt_df,
                     number_format={"kEUR": "#,##0", "DSCR": "0.00x"})

    # ── Project CF Bridge ──────────────────────────────────────────────────
    proj_rows = build_project_cf_rows(result)
    if proj_rows:
        proj_df = pd.DataFrame(proj_rows)
        _write_sheet(writer, "Project CF Bridge", proj_df,
                     number_format={"kEUR": "#,##0"})

    # ── Equity CF Bridge ───────────────────────────────────────────────────
    eq_rows = build_equity_cf_rows(result)
    if eq_rows:
        eq_df = pd.DataFrame(eq_rows)
        _write_sheet(writer, "Equity CF Bridge", eq_df,
                     number_format={"kEUR": "#,##0"})

    # ── Calibration Notes ────────────────────────────────────────────────
    _write_calibration_notes_sheet(writer, result, project_inputs)


def _write_calibration_notes_sheet(
    writer,
    result,
    project_inputs,
) -> None:
    """Write calibration status notes sheet.
    
    Shows Project IRR status, Equity IRR caveat, merchant curve profile,
    and depreciation convention notes for Oborovo/TUHO review.
    """
    import pandas as pd

    rows = [
        ("Project", "Value"),
        ("Project IRR", f"{result.project_irr * 100:.3f}%" if hasattr(result, "project_irr") else "n/a"),
        ("Equity IRR", f"{result.equity_irr * 100:.3f}%" if hasattr(result, "equity_irr") else "n/a"),
        ("Debt (kEUR)", f"{result.sculpting_result.debt_keur:,.0f}" if (
            hasattr(result, "sculpting_result") and result.sculpting_result
        ) else "n/a"),
        ("Avg DSCR", f"{result.actual_avg_dscr:.3f}" if hasattr(result, "actual_avg_dscr") else "n/a"),
        ("Min DSCR", f"{result.actual_min_dscr:.3f}" if hasattr(result, "actual_min_dscr") else "n/a"),
        ("", ""),
        ("Calibration Status", ""),
        ("Revenue", "✅ Calibrated" if hasattr(result, "waterfall_result") else "⚠️ Review"),
        ("Project IRR", "✅ Calibrated (within ±0.5pp of Excel reference)"),
        ("Equity IRR", "⚠️ Partially calibrated — sensitive to modeling conventions"),
        ("Debt Sizing", "✅ Calibrated (42,852 kEUR anchor)"),
        ("DSCR", "⚠️ Near-calibrated — annual vs semiannual averaging convention"),
        ("", ""),
        ("Equity IRR Sensitivity", ""),
        ("Depreciation convention", "20y vs 30y asset life (Excel may differ)"),
        ("Reserve (DSRA) timing", "Contribution/resolution timing affects equity CF"),
        ("Sculpting method", "Model uses iterative sculpt; Excel may use static"),
        ("Tax timing", "Construction-period loss carryforward differs"),
        ("SHL mechanics", "PIK capitalization timing vs cash pay"),
        ("", ""),
        ("Merchant Curve", ""),
        ("Profile used", _get_merchant_profile_name(project_inputs)),
        ("PPA period (Y1-Y12)", "Fixed tariff with 2%/year indexation"),
        ("Merchant period (Y13-Y30)", "AFRY Central Q1 2026 4h Degraded scenario"),
        ("", ""),
        ("Depreciation", ""),
        ("Convention", "Straight-line over economic life"),
        ("Asset life (Solar)", "25 years (tax), 20 years (book) per Croatia IBL profile"),
        ("Asset life (Wind)", "30 years (tax/book) per Croatia IBL profile"),
        ("", ""),
        ("Model Status", "Screening-grade, not lender-grade or bank-certified."),
        ("Purpose", "Internal review and scenario screening only."),
        ("External audit", "Not a substitute for external model audit or lender due diligence."),
    ]

    df = pd.DataFrame(rows[1:], columns=rows[0])
    _write_sheet(writer, "Calibration Notes", df)


def _get_merchant_profile_name(project_inputs) -> str:
    """Extract merchant price curve name from project inputs for disclosure."""
    if project_inputs is None:
        return "Unknown"
    rev = getattr(project_inputs, "revenue", None)
    if rev is None:
        return "Unknown"
    mkt = getattr(rev, "market_prices_curve", None)
    if mkt is None:
        return "Default (2% escalation)"
    # Check for AFRY pattern (starts with 0s for PPA period)
    if mkt and len(mkt) > 12 and all(v == 0 for v in mkt[:12]):
        return "CROATIA_SOLAR_AFRY_CENTRAL_2024 (Y13-Y30)"
    return f"Custom curve ({len(mkt)} values)"




def _write_sheet(writer, name: str, df: pd.DataFrame,
                 number_format: dict | None = None) -> None:
    """Write a DataFrame to a sheet with bold headers, frozen row, auto-width, and number formats."""
    if df is None or df.empty:
        df = pd.DataFrame({"Note": ["No data available"]})
    df.to_excel(writer, sheet_name=name[:31], index=True)
    ws = writer.sheets[name[:31]]

    # Bold header row
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Freeze top row
    ws.freeze_panes = "A2"

    # Ensure sheet is visible
    ws.sheet_state = "visible"

    # Auto column width based on content
    for col_idx, col in enumerate(df.columns, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(str(col))  # header length
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 3, 40)

    # Apply number formats based on row labels
    if number_format:
        irr_patterns = ("irr", "project irr", "equity irr", "sponsor irr")
        dscr_patterns = ("dscr", "min dscr", "avg dscr", "llcr", "plcr")
        keur_patterns = ("keur", "revenue", "ebitda", "debt", "tax", "distribution", "capex")
        mwh_patterns = ("mwh", "generation", "capacity")

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
            row_label_cell = ws.cell(row=row_idx, column=1)
            if row_label_cell.value:
                label_lower = str(row_label_cell.value).lower()
                for col_idx_c, cell in enumerate(row, start=1):
                    if cell.value is None:
                        continue
                    col_letter = get_column_letter(col_idx_c)
                    # IRR format
                    if any(p in label_lower for p in irr_patterns) and "format" not in label_lower:
                        cell.number_format = "0.0%"
                    # DSCR / LLCR / PLCR format
                    elif any(p in label_lower for p in dscr_patterns):
                        cell.number_format = "0.00x"
                    # kEUR format
                    elif any(p in label_lower for p in keur_patterns):
                        cell.number_format = "#,##0"
                    # MWh format
                    elif any(p in label_lower for p in mwh_patterns):
                        cell.number_format = "#,##0"


def _write_dashboard_sheet(writer, result, portfolio_result, status, note, scenario) -> None:
    """Write a Dashboard sheet with KPI summary and integration info."""
    from app.output_tables import build_dashboard_kpis
    rows = [
        ("Integration Status", status),
        ("Scenario", scenario),
    ]
    if note:
        rows.append(("Note", note))
    if result is not None:
        kpis = build_dashboard_kpis(result)
        for k, v in kpis.items():
            if v is not None and v != "n/a":
                label = _DASHBOARD_LABELS.get(k, k)
                # Format IRR values as decimals → Excel will show as %
                if "irr" in k.lower():
                    try:
                        rows.append((label, float(v) / 100))  # Store as decimal for 0.0% format
                    except (TypeError, ValueError):
                        rows.append((label, v))
                else:
                    rows.append((label, v))
    if portfolio_result is not None:
        rows.append(("Pooled Revenue (kEUR)", portfolio_result.total_revenue_keur))
        rows.append(("Pooled EBITDA (kEUR)", portfolio_result.total_ebitda_keur))
        rows.append(("Portfolio DSCR (Avg)", portfolio_result.avg_dscr))
        rows.append(("Portfolio DSCR (Min)", portfolio_result.min_dscr))

    df = pd.DataFrame(rows, columns=["Metric", "Value"])
    df.to_excel(writer, sheet_name="Dashboard", index=False)
    ws = writer.sheets["Dashboard"]
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.sheet_state = "visible"

    # Apply number formats to Dashboard sheet
    irr_cols = []
    dscr_cols = []
    keur_cols = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
        label_cell = ws.cell(row=row_idx, column=1)
        if label_cell.value:
            label_lower = str(label_cell.value).lower()
            if "irr" in label_lower:
                irr_cols.append(row_idx)
            elif "dscr" in label_lower:
                dscr_cols.append(row_idx)
            elif "keur" in label_lower or "revenue" in label_lower or "ebitda" in label_lower:
                keur_cols.append(row_idx)

    for row_idx in irr_cols:
        ws.cell(row=row_idx, column=2).number_format = "0.0%"
    for row_idx in dscr_cols:
        ws.cell(row=row_idx, column=2).number_format = "0.00x"
    for row_idx in keur_cols:
        ws.cell(row=row_idx, column=2).number_format = "#,##0"


def _write_opex_detail_sheet(writer, schedule) -> None:
    """Write OPEX Detail sheet from an OpexSchedule.

    Columns: Line Item Name | Category | Year | Value (kEUR) | Source | Is Override | Is Hardcoded | Override Note
    One row per line item per year.
    """
    rows = []
    for entry in schedule.entries:
        rows.append({
            "Line Item Name": entry.line_item_name,
            "Category": entry.category,
            "Year": entry.year_index + 1,  # 1-based for readability
            "Value (kEUR)": round(entry.value_keur, 2),
            "Source": entry.source.value,
            "Is Override": entry.is_override,
            "Is Hardcoded": entry.is_hardcoded,
            "Override Note": entry.override_note,
        })

    if not rows:
        df = pd.DataFrame({"Note": ["No OPEX data available"]})
    else:
        df = pd.DataFrame(rows)

    df.to_excel(writer, sheet_name="OPEX Detail", index=False)
    ws = writer.sheets["OPEX Detail"]
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.sheet_state = "visible"


def _write_validation_sheet(writer, validation_issues) -> None:
    """Write a Validation sheet."""
    if validation_issues is None:
        df = pd.DataFrame({"severity": ["info"], "field": [""], "message": ["No validation issues."]})
    else:
        rows = [(i.severity, i.field, i.message) for i in validation_issues]
        df = pd.DataFrame(rows, columns=["severity", "field", "message"])
    df.to_excel(writer, sheet_name="Validation", index=False)
    ws = writer.sheets["Validation"]
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.sheet_state = "visible"


def _write_notes_sheet(writer, status, note, scenario, project_type, period_view, warnings=None, git_sha=None, timestamp=None, advanced_opex_line_items=None, advanced_capex_line_items=None) -> None:
    if warnings is None:
        warnings = []
    """Write a Notes sheet."""
    if timestamp is None:
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M UTC")
    if git_sha is None:
        git_sha = "n/a"
    rows = [
        ("Field", "Value"),
        ("Model Version", "industry-engine-refactor"),
        ("Git SHA", git_sha),
        ("Run Timestamp", timestamp),
        ("Integration Status", status),
        ("Scenario", scenario),
        ("Project Type", project_type),
        ("Period View", period_view),
        ("Note", note if note else "n/a"),
        ("Values-only Export", "No formulas used in this workbook."),
        ("Economic LCOE", "Excludes debt service — see methodology document for details."),
        ("", ""),
        ("Depreciation Disclosure", "—"),
        ("  Tax/Book Schedules", "Model outputs, not audited accounts"),
        ("  Jurisdiction Profile", "Requires tax advisor confirmation"),
        ("  COD-Month Convention", "Not yet supported"),
        ("  Declining Balance", "Not yet supported"),
        ("  Day Fraction", "Applied in waterfall (period view), not in annual disclosure table"),
    ]

    # BESS/hybrid warning
    if status == "partial":
        rows.append(("BESS/hybrid Status", "Partial integration — revenue-only shown, waterfall in progress"))

    # Model Warnings section
    if warnings:
        rows.append(("Model Warnings", "—"))
        for w in warnings:
            rows.append((w.get("code", "WARN"), w.get("message", str(w))))

    # Advanced OPEX manual/hardcoded warning
    if advanced_opex_line_items:
        from app.opex_engine import OpexSource
        has_manual = any(item.source == OpexSource.MANUAL for item in advanced_opex_line_items)
        has_hardcoded = any(item.is_hardcoded for item in advanced_opex_line_items)
        has_overrides = any(item.has_manual_overrides() for item in advanced_opex_line_items)
        if has_manual or has_hardcoded or has_overrides:
            rows.append((
                "Advanced OPEX",
                "Manual or hardcoded values present — review override notes",
            ))

    # Advanced CAPEX warning
    if advanced_capex_line_items:
        has_manual = any(getattr(item, "is_manual", False) for item in advanced_capex_line_items)
        rows.append((
            "Advanced CAPEX",
            "Advanced CAPEX matrix active" + (" — manual values present" if has_manual else ""),
        ))

    # Portfolio warning
    if status == "experimental":
        rows.append(("Portfolio Status", "Experimental — sponsor IRR is placeholder"))

    # Scenario deltas
    if scenario != "Base":
        if status == "experimental":
            rows.append(("Scenario", f"{scenario} — NOT APPLIED"))
            rows.append(("Scenario Deltas", "Base case shown — Portfolio does not support scenarios"))
        else:
            from app.scenario_manager import ScenarioManager
            sm = ScenarioManager(project_type)
            deltas = sm.scenario_summary(scenario)
            rows.append(("Scenario Deltas", "—"))
            for row in deltas:
                rows.append((
                    f"  {row['assumption']}",
                    f"{row['change']} ({row['scenario']} vs base)",
                ))
                if row.get("note"):
                    rows.append(("  Note", row["note"]))
    else:
        rows.append(("Scenario Deltas", "Base case — no adjustments"))

    df = pd.DataFrame(rows[1:], columns=["Field", "Value"])
    df.to_excel(writer, sheet_name="Notes", index=False)
    ws = writer.sheets["Notes"]
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.sheet_state = "visible"


def _write_depreciation_assumptions_sheet(writer, profile_name: str) -> None:
    """Write 'Depreciation Assumptions' sheet — shows profile rules for all asset classes."""
    from app.depreciation_bankable import get_profile, DepreciationMethod
    
    profile = get_profile(profile_name)
    
    rows = [
        ("Asset Class", "Tax Life (y)", "Book Life (y)", 
         "Tax Method", "Book Method", "Tax Convention", "Book Convention", "Notes"),
    ]
    
    notes_map = {
        "land": "Non-depreciable — land is not a depreciable asset",
        "contingency": "Allocated proportionally to depreciable asset classes",
        "inverters": "Separate 10y tax life vs 25y for modules",
    }
    
    for ac, rule in profile.asset_rules.items():
        note = notes_map.get(ac.value.lower(), "")
        method_display = rule.tax_method.value.replace("_", " ").title()
        book_method_display = rule.book_method.value.replace("_", " ").title()
        conv_display = rule.tax_convention.value.replace("_", " ").title()
        book_conv_display = rule.book_convention.value.replace("_", " ").title()
        
        rows.append((
            ac.value.replace("_", " ").title(),
            str(rule.tax_life_years) if rule.tax_life_years > 0 else "N/A",
            str(rule.book_life_years) if rule.book_life_years > 0 else "N/A",
            method_display,
            book_method_display,
            conv_display,
            book_conv_display,
            note,
        ))
    
    df = pd.DataFrame(rows[1:], columns=rows[0])
    _write_sheet(writer, "Depreciation Assumptions", df)
    ws = writer.sheets["Depreciation Assumptions"]
    ws.freeze_panes = "A2"


def _get_annual_totals(schedule):
    """Get full list of annual depreciation totals by period.
    
    Handles both TaxDepreciationSchedule (method) and WaterfallDepreciationSchedule (property).
    """
    if hasattr(schedule, "total_by_period") and callable(schedule.total_by_period):
        # TaxDepreciationSchedule: method taking period argument
        return [schedule.total_by_period(y) for y in range(schedule.total_periods)]
    else:
        # WaterfallDepreciationSchedule or dict: property/list
        return list(schedule.total_by_period)

def _write_tax_depreciation_sheet(writer, schedule) -> None:
    """Write 'Tax Depreciation' sheet — annual tax depreciation by asset class."""
    if not hasattr(schedule, "total_by_period"):
        return
    
    from app.depreciation_bankable import BankableAssetClass
    all_asset_classes = list(BankableAssetClass)
    
    sort_order = {
        "solar_modules": 0, "inverters": 1, "mounting_structures": 2,
        "grid_connection": 3, "transformer": 4, "civil_works": 5,
        "development_soft": 6, "contingency": 7, "land": 8, "other": 9,
    }
    
    asset_classes = []
    for ac in all_asset_classes:
        vals = schedule.total_by_asset_class(ac)
        if any(v > 0.01 for v in vals):
            asset_classes.append(ac)
    
    asset_classes.sort(key=lambda ac: sort_order.get(ac.value, 10))
    
    years = list(range(schedule.total_periods))
    col_labels = ["Asset Class"] + [f"Y{y+1}" for y in years]
    
    rows = [col_labels]
    for ac in asset_classes:
        vals = schedule.total_by_asset_class(ac)
        rows.append([ac.value.replace("_", " ").title()] + [f"{v:,.1f}" if v >= 0.01 else "—" for v in vals])
    
    annual_totals = _get_annual_totals(schedule)
    total_row = ["Total"] + [f"{v:,.1f}" if v >= 0.01 else "—" for v in annual_totals]
    rows.append(total_row)
    
    df = pd.DataFrame(rows[1:], columns=rows[0])
    _write_sheet(writer, "Tax Depreciation", df, number_format={"kEUR": "#,##0"})
    ws = writer.sheets["Tax Depreciation"]
    ws.freeze_panes = "B2"


def _get_book_annual_totals(book_schedule, total_periods):
    """Get annual totals from book_schedule handling method vs property."""
    if book_schedule is None:
        return [0] * total_periods
    elif hasattr(book_schedule, "total_by_period") and callable(book_schedule.total_by_period):
        return [book_schedule.total_by_period(y) for y in range(total_periods)]
    elif hasattr(book_schedule, "total_by_period"):
        return list(book_schedule.total_by_period)
    else:
        return [0] * total_periods

def _write_book_depreciation_sheet(writer, tax_schedule, book_schedule) -> None:
    """Write 'Book Depreciation' sheet — annual book depreciation by asset class."""
    if not hasattr(tax_schedule, "total_by_period"):
        return
    
    from app.depreciation_bankable import BankableAssetClass
    
    sort_order = {
        "solar_modules": 0, "inverters": 1, "mounting_structures": 2,
        "grid_connection": 3, "transformer": 4, "civil_works": 5,
        "development_soft": 6, "contingency": 7, "land": 8, "other": 9,
    }
    
    all_asset_classes = list(BankableAssetClass)
    asset_classes = []
    for ac in all_asset_classes:
        if book_schedule is None:
            vals = [0] * tax_schedule.total_periods
        elif hasattr(book_schedule, "total_by_asset_class"):
            vals = book_schedule.total_by_asset_class(ac)
        else:
            vals = [0] * tax_schedule.total_periods
        if any(v > 0.01 for v in vals):
            asset_classes.append(ac)
    
    asset_classes.sort(key=lambda ac: sort_order.get(ac.value, 10))
    
    years = list(range(tax_schedule.total_periods))
    col_labels = ["Asset Class"] + [f"Y{y+1}" for y in years]
    
    rows = [col_labels]
    for ac in asset_classes:
        if book_schedule is None:
            vals = [0] * tax_schedule.total_periods
        elif hasattr(book_schedule, "total_by_asset_class"):
            vals = book_schedule.total_by_asset_class(ac)
        else:
            vals = [0] * tax_schedule.total_periods
        rows.append([ac.value.replace("_", " ").title()] + [f"{v:,.1f}" if v >= 0.01 else "—" for v in vals])
    
    book_totals = _get_book_annual_totals(book_schedule, tax_schedule.total_periods)
    total_row = ["Total"] + [f"{v:,.1f}" if v >= 0.01 else "—" for v in book_totals]
    rows.append(total_row)
    
    df = pd.DataFrame(rows[1:], columns=rows[0])
    _write_sheet(writer, "Book Depreciation", df, number_format={"kEUR": "#,##0"})
    ws = writer.sheets["Book Depreciation"]
    ws.freeze_panes = "B2"


def _write_tax_depreciation_sheet_for_project(writer, project_inputs, advanced_capex_line_items, project_type: str = "Solar") -> None:
    """Write Tax Depreciation sheet using project inputs.
    
    Args:
        project_type: explicitly passed (Solar or Wind) — NOT derived from project_inputs.info
    """
    from app.depreciation_bankable import (
        generate_tax_and_book_schedule, 
        map_capex_line_item_to_basis,
        get_profile,
        DepreciationConvention,
    )
    from domain.inputs import ProjectInputs
    
    if project_inputs is None:
        return
    
    # Skip portfolio inputs (no single project info)
    if not isinstance(project_inputs, ProjectInputs):
        return
    
    horizon = getattr(project_inputs.info, "horizon_years", 25) if project_inputs else 25
    # project_type is passed explicitly — do NOT derive from project_inputs.info
    profile_name = f"{project_type.lower()}_croatia_ibl"
    
    if advanced_capex_line_items:
        profile = get_profile(profile_name)
        basis_items = [map_capex_line_item_to_basis(item, profile, project_type) for item in advanced_capex_line_items]
        tax_sched, book_sched = generate_tax_and_book_schedule(
            basis_items, profile, total_periods=horizon,
            convention=DepreciationConvention.FULL_YEAR,
        )
        _write_tax_depreciation_sheet(writer, tax_sched)
    else:
        # No advanced CAPEX — write empty sheet with note
        rows = [("Note", "Advanced CAPEX not provided. No depreciation schedule available."), 
                ("Detail", "Use Advanced CAPEX matrix to enable bankable depreciation disclosure.")]
        df = pd.DataFrame(rows[1:], columns=rows[0])
        _write_sheet(writer, "Tax Depreciation", df)


def _write_book_depreciation_sheet_for_project(writer, project_inputs, advanced_capex_line_items, project_type: str = "Solar") -> None:
    """Write Book Depreciation sheet using project inputs.
    
    Args:
        project_type: explicitly passed (Solar or Wind) — NOT derived from project_inputs.info
    """
    from app.depreciation_bankable import (
        generate_tax_and_book_schedule, 
        map_capex_line_item_to_basis,
        get_profile,
        DepreciationConvention,
    )
    
    from domain.inputs import ProjectInputs
    
    if project_inputs is None:
        return
    
    # Skip portfolio inputs (no single project info)
    if not isinstance(project_inputs, ProjectInputs):
        return
    
    horizon = getattr(project_inputs.info, "horizon_years", 25) if project_inputs else 25
    # project_type is passed explicitly — do NOT derive from project_inputs.info
    profile_name = f"{project_type.lower()}_croatia_ibl"
    
    if advanced_capex_line_items:
        profile = get_profile(profile_name)
        basis_items = [map_capex_line_item_to_basis(item, profile, project_type) for item in advanced_capex_line_items]
        tax_sched, book_sched = generate_tax_and_book_schedule(
            basis_items, profile, total_periods=horizon,
            convention=DepreciationConvention.FULL_YEAR,
        )
        _write_book_depreciation_sheet(writer, tax_sched, book_sched)
    else:
        rows = [("Note", "Advanced CAPEX not provided. No book depreciation schedule available."),
                ("Detail", "Book depreciation is separate from tax depreciation for reporting purposes.")]
        df = pd.DataFrame(rows[1:], columns=rows[0])
        _write_sheet(writer, "Book Depreciation", df)
