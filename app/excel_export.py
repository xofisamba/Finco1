"""Values-only Excel export — no formulas, no calibration."""
from __future__ import annotations
import pandas as pd
from io import BytesIO

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def build_excel_export(
    *,
    result=None,
    portfolio_result=None,
    project_inputs=None,
    integration_status: str = "full",
    integration_note: str | None = None,
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
    
    if OPENPYXL_AVAILABLE:
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            _write_dashboard_sheet(writer, result, portfolio_result, integration_status, integration_note)
            _write_sheet(writer, "Inputs", build_inputs_summary_table(project_inputs))
            _write_sheet(writer, "CapEx", build_capex_summary_table(project_inputs))
            if result is not None:
                _write_sheet(writer, "Revenue", build_revenue_table(result))
                _write_sheet(writer, "Debt", build_debt_table(result))
                _write_sheet(writer, "Tax_Depreciation", build_tax_depreciation_table(result))
                _write_sheet(writer, "Waterfall", build_waterfall_table(result))
                _write_sheet(writer, "Returns", build_returns_table(result))
            if portfolio_result is not None:
                _write_sheet(writer, "Portfolio", build_portfolio_table(portfolio_result))
            _write_sheet(writer, "CapEx_Items", build_capex_items_table(project_inputs))
    else:
        # Fallback: CSV as xls
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            _write_dashboard_sheet(writer, result, portfolio_result, integration_status, integration_note)
            _write_sheet(writer, "Inputs", build_inputs_summary_table(project_inputs))
            _write_sheet(writer, "CapEx", build_capex_summary_table(project_inputs))
            if result is not None:
                _write_sheet(writer, "Revenue", build_revenue_table(result))
                _write_sheet(writer, "Debt", build_debt_table(result))
                _write_sheet(writer, "Tax_Depreciation", build_tax_depreciation_table(result))
                _write_sheet(writer, "Waterfall", build_waterfall_table(result))
                _write_sheet(writer, "Returns", build_returns_table(result))
            if portfolio_result is not None:
                _write_sheet(writer, "Portfolio", build_portfolio_table(portfolio_result))
            _write_sheet(writer, "CapEx_Items", build_capex_items_table(project_inputs))
    
    output.seek(0)
    return output.read()


def _write_sheet(writer, name: str, df: pd.DataFrame) -> None:
    """Write a DataFrame to a sheet with basic formatting."""
    if df is None or df.empty:
        df = pd.DataFrame({"Note": ["No data available"]})
    df.to_excel(writer, sheet_name=name[:31], index=True)
    ws = writer.sheets[name[:31]]
    # Bold header row
    for cell in ws[1]:
        if cell.column == 1:
            cell.font = Font(bold=True)


def _write_dashboard_sheet(writer, result, portfolio_result, status, note) -> None:
    """Write a Dashboard sheet with KPI summary and integration info."""
    from app.output_tables import build_dashboard_kpis
    rows = [("Integration Status", status)]
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
