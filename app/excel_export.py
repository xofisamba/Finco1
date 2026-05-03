"""Values-only Excel export — no formulas, no calibration."""
from __future__ import annotations
import pandas as pd
from io import BytesIO

import openpyxl
from openpyxl.styles import Font


def build_excel_export(
    *,
    result=None,
    portfolio_result=None,
    project_inputs=None,
    validation_issues=None,
    integration_status: str = "full",
    integration_note: str | None = None,
    scenario: str = "Base",
    period_view: str = "Semiannual",
) -> bytes:
    """Build a values-only Excel workbook from waterfall results.
    
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
    )
    from app.input_helpers import build_inputs_summary_table, build_capex_summary_table, build_capex_items_table
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Dashboard
        _write_dashboard_sheet(writer, result, portfolio_result, integration_status, integration_note, scenario)
        
        # Inputs
        _write_sheet(writer, "Inputs", build_inputs_summary_table(project_inputs))
        
        # CapEx
        _write_sheet(writer, "CapEx", build_capex_summary_table(project_inputs))
        _write_sheet(writer, "CapEx_Items", build_capex_items_table(project_inputs))
        
        if result is not None:
            # Apply annual aggregation if needed
            if period_view == "Annual":
                rev_df = _aggregate_annual(build_revenue_table(result))
                debt_df = _aggregate_annual(build_debt_table(result))
                tax_df = _aggregate_annual(build_tax_depreciation_table(result))
                wf_df = _aggregate_annual(build_waterfall_table(result))
            else:
                rev_df = build_revenue_table(result)
                debt_df = build_debt_table(result)
                tax_df = build_tax_depreciation_table(result)
                wf_df = build_waterfall_table(result)
            
            _write_sheet(writer, "Revenue", rev_df)
            _write_sheet(writer, "Debt", debt_df)
            _write_sheet(writer, "Tax_Depreciation", tax_df)
            _write_sheet(writer, "Waterfall", wf_df)
            _write_sheet(writer, "Returns", build_returns_table(result))
        
        if portfolio_result is not None:
            _write_sheet(writer, "Portfolio", build_portfolio_table(portfolio_result))
        
        # Validation sheet
        _write_validation_sheet(writer, validation_issues)
        
        # Notes sheet
        _write_notes_sheet(writer, integration_status, integration_note, scenario, period_view)
    
    output.seek(0)
    return output.read()


def _aggregate_annual(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate semiannual DataFrame to annual by summing numeric columns grouped by year."""
    if df is None or df.empty:
        return df
    if df.shape[0] == 0:
        return df
    # Try to extract year from first column (usually a period/date column)
    # Group by year prefix if date-like, otherwise sum everything
    cols = df.columns.tolist()
    if not cols:
        return df
    first_col = cols[0]
    # Check if it looks like a date string
    sample = str(df[first_col].iloc[0]) if len(df) > 0 else ""
    if "/" in sample or "-" in sample:
        # Extract year prefix
        df = df.copy()
        df["_year"] = df[first_col].astype(str).str[:4]
        numeric_cols = [c for c in cols if c != first_col]
        agg_dict = {c: "sum" for c in numeric_cols}
        result = df.groupby("_year", sort=True).agg(agg_dict).reset_index()
        result.rename(columns={"_year": first_col}, inplace=True)
        return result
    # No date pattern — sum all numeric columns
    return df


def _write_sheet(writer, name: str, df: pd.DataFrame) -> None:
    """Write a DataFrame to a sheet with basic formatting."""
    if df is None or df.empty:
        df = pd.DataFrame({"Note": ["No data available"]})
    df.to_excel(writer, sheet_name=name[:31], index=True)
    ws = writer.sheets[name[:31]]
    # Bold header row
    for cell in ws[1]:
        cell.font = Font(bold=True)
    # Freeze panes
    ws.freeze_panes = "A2"
    # Ensure sheet is visible (required by openpyxl)
    ws.sheet_state = "visible"


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
                rows.append((k, v))
    if portfolio_result is not None:
        rows.append(("Pooled Revenue", portfolio_result.total_revenue_keur))
        rows.append(("Pooled EBITDA", portfolio_result.total_ebitda_keur))
        rows.append(("Portfolio DSCR (Avg)", portfolio_result.avg_dscr))
        rows.append(("Portfolio DSCR (Min)", portfolio_result.min_dscr))
    df = pd.DataFrame(rows, columns=["Metric", "Value"])
    df.to_excel(writer, sheet_name="Dashboard", index=False)
    ws = writer.sheets["Dashboard"]
    for cell in ws[1]:
        cell.font = Font(bold=True)


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


def _write_notes_sheet(writer, status, note, scenario, period_view) -> None:
    """Write a Notes sheet."""
    rows = [
        ("Field", "Value"),
        ("Integration Status", status),
        ("Scenario", scenario),
        ("Period View", period_view),
        ("Note", note if note else "n/a"),
        ("Values-only Export", "No formulas used in this workbook."),
        ("BESS/hybrid Status", "Partial integration — not bankable" if status == "partial" else "n/a"),
        ("Portfolio Status", "Experimental — sponsor IRR is placeholder" if status == "experimental" else "n/a"),
    ]
    if scenario != "Base":
        rows.append(("Scenario Note", "Scenario selector is informational only; not yet implemented."))
    df = pd.DataFrame(rows[1:], columns=["Field", "Value"])
    df.to_excel(writer, sheet_name="Notes", index=False)
    ws = writer.sheets["Notes"]
    for cell in ws[1]:
        cell.font = Font(bold=True)